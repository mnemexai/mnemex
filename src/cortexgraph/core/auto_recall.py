"""Auto-recall system for conversational memory reinforcement.

This module implements automatic memory recall and reinforcement based on
conversation topics. Memories are searched and reinforced in the background
to prevent important context from decaying through disuse.

Phase 1 (MVP): Silent reinforcement - no surfacing, just prevent decay
Phase 2 (Future): Subtle surfacing - inject context naturally
Phase 3 (Future): Interactive mode - user-controlled surfacing
Phase 4 (Future): Cross-domain detection (Maslow effect)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from cortexgraph.config import get_config
from cortexgraph.storage.models import Memory


class RecallMode(str, Enum):
    """Auto-recall surfacing modes."""

    SILENT = "silent"  # Reinforce without surfacing
    SUBTLE = "subtle"  # Natural context injection
    INTERACTIVE = "interactive"  # User-controlled


@dataclass
class RecallResult:
    """Result of auto-recall processing."""

    topics_found: list[str]
    memories_found: list[Memory]
    memories_reinforced: list[str]  # Memory IDs
    should_surface: bool
    surfacing_hint: str | None = None


class ConversationAnalyzer:
    """Analyze messages for recall opportunities.

    Extracts topics, entities, and determines when to trigger memory search.
    """

    # Common words to ignore when extracting topics
    STOP_WORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "about",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "what",
        "which",
        "who",
        "when",
        "where",
        "why",
        "how",
        "working",  # Common verb
        "testing",  # Common verb
    }

    # Patterns that indicate high-value topics (proper nouns, technical terms)
    TOPIC_PATTERNS = [
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",  # Proper nouns (Title Case)
        r"\b[A-Z]{2,}\b",  # Acronyms (STOPPER, API, JWT)
        r"\b\w+(?:-\w+)+\b",  # Hyphenated terms (auto-recall, spaced-repetition)
        r"\b(?:function|class|method|module|system|protocol|framework|algorithm)\s+\w+",  # Technical terms
    ]

    def extract_topics(self, message: str) -> list[str]:
        """Extract topics/entities from message.

        Uses pattern matching to identify:
        - Proper nouns (Title Case multi-word phrases)
        - Acronyms (ALL CAPS 2+ letters)
        - Hyphenated technical terms
        - Technical phrases (function X, class Y)

        Args:
            message: User message text

        Returns:
            List of extracted topic strings (lowercased for matching)
        """
        topics: set[str] = set()

        # Extract pattern-based topics
        for pattern in self.TOPIC_PATTERNS:
            matches = re.finditer(pattern, message)
            for match in matches:
                topic = match.group(0).strip().lower()
                # Filter stop words even from pattern matches
                if topic and topic not in self.STOP_WORDS:
                    topics.add(topic)

        # Extract significant words (3+ chars, not stop words)
        words = re.findall(r"\b\w{3,}\b", message.lower())
        for word in words:
            if word not in self.STOP_WORDS:
                topics.add(word)

        return sorted(topics)

    def should_trigger_recall(
        self,
        message: str,
        min_topic_count: int = 2,
        min_message_length: int = 10,
    ) -> bool:
        """Decide if this message warrants memory search.

        Triggers recall if:
        - Message is substantial (>= min_message_length chars)
        - Contains multiple topics (>= min_topic_count)
        - Doesn't look like a command/query

        Args:
            message: User message text
            min_topic_count: Minimum topics to trigger (default 2)
            min_message_length: Minimum characters to trigger (default 10)

        Returns:
            True if should search for related memories
        """
        # Too short - likely a command or simple response
        if len(message) < min_message_length:
            return False

        # Extract topics
        topics = self.extract_topics(message)

        # Need multiple topics to indicate substantive discussion
        if len(topics) < min_topic_count:
            return False

        # Don't trigger on pure questions (may be handled by analyze_for_recall)
        # But do trigger on statements with questions (discussion)
        question_count = message.count("?")
        sentence_count = max(
            len([s for s in message.split(".") if s.strip()]),
            1,
        )
        if question_count == sentence_count:  # Pure question
            return False

        return True

    def get_context_tags(self, message: str) -> list[str]:
        """Extract tags representing current conversation context.

        These tags are used for cross-domain usage detection and
        reinforcement metadata.

        Args:
            message: User message text

        Returns:
            List of context tags (topics extracted from message)
        """
        return self.extract_topics(message)


class AutoRecallEngine:
    """Orchestrate automatic memory recall and reinforcement.

    Phase 1 (MVP): Silent reinforcement only - no surfacing
    """

    def __init__(self, mode: RecallMode = RecallMode.SILENT):
        """Initialize auto-recall engine.

        Args:
            mode: Surfacing mode (silent, subtle, interactive)
        """
        self.mode = mode
        self.analyzer = ConversationAnalyzer()
        self.config = get_config()

        # Rate limiting - prevent too-frequent recalls
        self._last_recall_time = 0.0
        self._min_interval = float(self.config.auto_recall_min_interval)

    def process_message(
        self,
        message: str,
        storage: Any,  # JSONLStorage instance
    ) -> RecallResult:
        """Main entry point - analyze message and recall related memories.

        Args:
            message: User message text
            storage: Storage instance for memory search/update

        Returns:
            RecallResult with topics, memories, and reinforcement actions
        """
        # Check cooldown
        now = time.time()
        if now - self._last_recall_time < self._min_interval:
            return RecallResult(
                topics_found=[],
                memories_found=[],
                memories_reinforced=[],
                should_surface=False,
            )

        # Update rate limiter immediately after cooldown passes
        self._last_recall_time = now

        # Decide if we should trigger recall
        if not self.analyzer.should_trigger_recall(message):
            return RecallResult(
                topics_found=[],
                memories_found=[],
                memories_reinforced=[],
                should_surface=False,
            )

        # Extract topics
        topics = self.analyzer.extract_topics(message)
        if not topics:
            return RecallResult(
                topics_found=[],
                memories_found=[],
                memories_reinforced=[],
                should_surface=False,
            )

        # Search for related memories
        related = self._search_related(topics, storage)
        if not related:
            return RecallResult(
                topics_found=topics,
                memories_found=[],
                memories_reinforced=[],
                should_surface=False,
            )

        # Phase 1 (MVP): Silent reinforcement only
        context_tags = self.analyzer.get_context_tags(message)
        reinforced_ids = self._reinforce_silently(related, context_tags, storage)

        # Phase 1: Never surface (silent mode)
        should_surface = self.mode != RecallMode.SILENT and self._should_surface(related)

        return RecallResult(
            topics_found=topics,
            memories_found=related,
            memories_reinforced=reinforced_ids,
            should_surface=should_surface,
            surfacing_hint=self._generate_hint(related) if should_surface else None,
        )

    def _search_related(
        self,
        topics: list[str],
        storage: Any,
        relevance_threshold: float | None = None,
        max_results: int | None = None,
    ) -> list[Memory]:
        """Search for memories related to topics.

        Args:
            topics: List of topic strings to search for
            storage: Storage instance
            relevance_threshold: Minimum relevance score (uses config default if None)
            max_results: Maximum results to return (uses config default if None)

        Returns:
            List of related memories, sorted by relevance
        """
        if relevance_threshold is None:
            relevance_threshold = self.config.auto_recall_relevance_threshold
        if max_results is None:
            max_results = self.config.auto_recall_max_results

        # Build search query from topics
        query = " ".join(topics)

        # Get all active and promoted memories
        from cortexgraph.storage.models import MemoryStatus

        memories = storage.search_memories(
            status=[MemoryStatus.ACTIVE, MemoryStatus.PROMOTED],
            limit=max_results * 10,  # Get more for filtering
        )

        # Calculate relevance for each memory
        from cortexgraph.core.clustering import text_similarity

        scored_memories: list[tuple[Memory, float]] = []
        for mem in memories:
            # Use text similarity (Jaccard) for relevance
            similarity = text_similarity(query, mem.content)

            # Only consider memories above relevance threshold
            if similarity >= relevance_threshold:
                scored_memories.append((mem, similarity))

        # Sort by similarity and return top results
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        filtered = [mem for mem, _score in scored_memories[:max_results]]

        return filtered

    def _reinforce_silently(
        self,
        memories: list[Memory],
        context_tags: list[str],
        storage: Any,
    ) -> list[str]:
        """Reinforce memories without surfacing to user.

        Updates last_used, use_count, review_priority via observe_memory_usage.

        Args:
            memories: Memories to reinforce
            context_tags: Current conversation context
            storage: Storage instance

        Returns:
            List of reinforced memory IDs
        """
        if not memories:
            return []

        from cortexgraph.core.review import detect_cross_domain_usage, reinforce_memory

        reinforced_ids = []
        for mem in memories:
            # Detect cross-domain usage
            is_cross_domain = detect_cross_domain_usage(mem, context_tags)

            # Reinforce the memory
            reinforced = reinforce_memory(mem, cross_domain=is_cross_domain)

            # Update in storage
            storage.save_memory(reinforced)
            reinforced_ids.append(reinforced.id)

        return reinforced_ids

    def _should_surface(self, memories: list[Memory]) -> bool:
        """Decide if memories should be surfaced to user.

        Phase 1 (MVP): Always returns False (silent mode)
        Phase 2+: Implement surfacing logic based on mode

        Args:
            memories: Candidate memories

        Returns:
            True if memories should be surfaced
        """
        # Phase 1: Silent mode - never surface
        if self.mode == RecallMode.SILENT:
            return False

        # Future phases: Add surfacing logic
        # - Check relevance scores
        # - Check memory importance (strength, use_count)
        # - Consider user preferences
        return False

    def _generate_hint(self, memories: list[Memory]) -> str | None:
        """Generate hint for surfaced memories.

        Phase 1 (MVP): Not used (silent mode)
        Phase 2+: Generate natural language hints

        Args:
            memories: Memories to generate hint for

        Returns:
            Hint string or None
        """
        if not memories:
            return None

        # Phase 2+: Generate natural hint
        # Example: "Based on your earlier note about STOPPER timing windows..."
        return None
