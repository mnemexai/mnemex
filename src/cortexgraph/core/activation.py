"""Memory activation service for automatic context-based retrieval.

This module implements spreading activation and relevance scoring for
surfacing relevant memories during conversations.
"""

import logging
import time

from ..config import get_config
from ..context import db
from ..core.decay import calculate_score
from ..storage.activation_index import ActivationGraph, build_activation_graph
from ..storage.models import (
    ActivationContext,
    ActivationResult,
    ActivationScore,
    ActivationSource,
    Memory,
)
from .nlp import KeywordExtractor

logger = logging.getLogger(__name__)


class ActivationService:
    """Service for activating relevant memories based on conversation context.

    Implements:
    - Keyword-based matching against memory tags/entities/content
    - Spreading activation through memory graph relations
    - Temporal scoring based on decay and recency
    - Two-tier fallback (full → keyword-only → silent degradation)
    """

    def __init__(self) -> None:
        """Initialize activation service with indexes and configuration."""
        self.keyword_extractor = KeywordExtractor()
        self.graph: ActivationGraph | None = None
        self.config = get_config()
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild activation index from current memory storage."""
        try:
            # Get all active memories and relations from storage
            memories = db.list_memories()
            relations = db.get_all_relations()

            # Build graph using keyword extractor
            self.graph = build_activation_graph(
                memories=memories,
                relations=relations,
                extract_keywords_fn=lambda text: self.keyword_extractor.extract_keywords(
                    text, max_keywords=10
                ),
            )

            logger.info(
                f"Built activation graph: {self.graph.memory_count} memories, "
                f"{self.graph.relation_count} relations"
            )
        except Exception as e:
            logger.error(f"Failed to rebuild activation index: {e}")
            # Create empty graph as fallback
            self.graph = ActivationGraph(last_updated=int(time.time()))

    async def activate(self, context: ActivationContext) -> ActivationResult:
        """Activate relevant memories based on conversation context.

        Args:
            context: Activation context with message, keywords, and settings

        Returns:
            Activation result with ranked memory IDs and scores

        Process:
            1. Extract keywords from message (if not provided)
            2. Match keywords against graph indexes
            3. Calculate base relevance scores
            4. Apply spreading activation (if enabled)
            5. Apply temporal decay scoring
            6. Rank, filter by threshold, return top-k

        Fallback Strategy:
            - Full: Complete activation with spreading (default)
            - Keyword-only: Direct matches only, no spreading (if spreading fails)
            - Error: Silent degradation, return empty result (if all fails)
        """
        start_time = time.perf_counter()
        now = int(time.time())
        fallback_tier = "full"

        try:
            # Ensure graph is built
            if self.graph is None or self.graph.memory_count == 0:
                self._rebuild_index()

            # Extract keywords from message if not provided
            keywords = (
                context.keywords
                if context.keywords
                else self.keyword_extractor.extract_keywords(context.message, max_keywords=20)
            )

            # Find candidate memories using graph indexes
            candidate_ids = self._find_candidates(keywords, context)

            # Remove already-activated memories
            candidate_ids = candidate_ids - context.already_activated

            if not candidate_ids:
                latency_ms = (time.perf_counter() - start_time) * 1000
                return ActivationResult(
                    activated_memories=[],
                    activation_scores={},
                    direct_matches=[],
                    spread_matches=[],
                    total_candidates=0,
                    activation_latency_ms=latency_ms,
                    fallback_tier="full",
                )

            # Get Memory objects
            memory_map: dict[str, Memory] = {}
            for mem_id in candidate_ids:
                mem = db.get_memory(mem_id)
                if mem:
                    memory_map[mem_id] = mem

            # Calculate activation scores
            activation_scores: dict[str, ActivationScore] = {}
            direct_matches: set[str] = set()

            for mem_id, memory in memory_map.items():
                # Calculate base relevance (keyword matching)
                base_relevance, matched_keywords = self._calculate_keyword_relevance(
                    memory, keywords
                )

                # Calculate temporal score using existing decay system
                temporal_score = calculate_score(
                    use_count=memory.use_count,
                    last_used=memory.last_used,
                    strength=memory.strength,
                    now=now,
                )
                # Normalize to 0-1 range (temporal scores are typically 0-2)
                temporal_score = min(temporal_score / 2.0, 1.0)

                # For direct matches (no spreading yet)
                source = ActivationSource.DIRECT
                spreading_score = 0.0

                # Calculate combined score
                activation_scores[mem_id] = ActivationScore.calculate(
                    memory_id=mem_id,
                    base_relevance=base_relevance,
                    temporal_score=temporal_score,
                    spreading_score=spreading_score,
                    source=source,
                    matched_keywords=matched_keywords,
                )

                direct_matches.add(mem_id)

            # Apply spreading activation if enabled (with fallback to keyword-only)
            spread_matches: set[str] = set()
            if context.enable_spreading and self.graph is not None:
                try:
                    spread_matches = self._apply_spreading_activation(
                        direct_matches, activation_scores, memory_map, context, now
                    )
                except Exception as e:
                    logger.warning(f"Spreading activation failed, using keyword-only: {e}")
                    fallback_tier = "keyword_only"
                    # Continue with direct matches only (spread_matches stays empty)

            # Rank by final_score and filter by threshold
            ranked_scores = sorted(
                activation_scores.items(), key=lambda x: x[1].final_score, reverse=True
            )

            # Filter by threshold
            filtered = [
                (mem_id, score)
                for mem_id, score in ranked_scores
                if score.final_score >= context.activation_threshold
            ]

            # Take top-k
            top_k = filtered[: context.max_memories]

            # Build result
            activated_memories = [mem_id for mem_id, _ in top_k]
            final_scores = dict(top_k)

            latency_ms = (time.perf_counter() - start_time) * 1000

            return ActivationResult(
                activated_memories=activated_memories,
                activation_scores=final_scores,
                direct_matches=list(direct_matches),
                spread_matches=list(spread_matches),
                total_candidates=len(candidate_ids),
                activation_latency_ms=latency_ms,
                fallback_tier=fallback_tier,
            )

        except Exception as e:
            logger.error(f"Activation failed: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000
            # Return empty result on error (silent degradation)
            return ActivationResult(
                activated_memories=[],
                activation_scores={},
                direct_matches=[],
                spread_matches=[],
                total_candidates=0,
                activation_latency_ms=latency_ms,
                fallback_tier="error",
            )

    def _find_candidates(self, keywords: list[str], context: ActivationContext) -> set[str]:
        """Find candidate memory IDs using graph indexes.

        Args:
            keywords: Keywords extracted from message
            context: Activation context

        Returns:
            Set of candidate memory IDs
        """
        if self.graph is None:
            return set()

        candidate_ids: set[str] = set()

        # Match by keywords (from content extraction)
        keyword_matches = self.graph.find_by_keywords(keywords)
        candidate_ids.update(keyword_matches)

        # Match by entities (named entities in memory)
        # Use keywords as potential entities (lowercase matching)
        entity_matches = self.graph.find_by_entities([k.lower() for k in keywords])
        candidate_ids.update(entity_matches)

        # Match by tags
        tag_matches = self.graph.find_by_tags([k.lower() for k in keywords])
        candidate_ids.update(tag_matches)

        return candidate_ids

    def _calculate_keyword_relevance(
        self, memory: Memory, keywords: list[str]
    ) -> tuple[float, list[str]]:
        """Calculate how well a memory matches the keywords.

        Args:
            memory: Memory to score
            keywords: Keywords to match against

        Returns:
            Tuple of (relevance_score 0.0-1.0, matched_keywords)
        """
        if not keywords:
            return 0.0, []

        # Normalize keywords and memory fields to lowercase for matching
        keywords_lower = {k.lower() for k in keywords}

        # Collect all matchable text from memory
        memory_tags = {t.lower() for t in memory.meta.tags}
        memory_entities = {e.lower() for e in memory.entities}

        # Extract keywords from content using same extractor
        content_keywords = {
            k.lower()
            for k in self.keyword_extractor.extract_keywords(memory.content, max_keywords=20)
        }

        # Union of all matchable terms in memory
        memory_terms = memory_tags | memory_entities | content_keywords

        # Find matches
        matched = keywords_lower & memory_terms
        matched_keywords = list(matched)

        # Calculate relevance score
        # Simple approach: ratio of matched keywords to total keywords
        if not keywords_lower:
            return 0.0, []

        relevance = len(matched) / len(keywords_lower)

        return min(relevance, 1.0), matched_keywords

    def _apply_spreading_activation(
        self,
        direct_matches: set[str],
        activation_scores: dict[str, ActivationScore],
        memory_map: dict[str, Memory],
        context: ActivationContext,
        now: int,
    ) -> set[str]:
        """Apply spreading activation through memory graph.

        Args:
            direct_matches: Memory IDs from direct keyword matching
            activation_scores: Current activation scores (will be updated)
            memory_map: Cache of Memory objects
            context: Activation context
            now: Current timestamp

        Returns:
            Set of memory IDs activated via spreading
        """
        if self.graph is None:
            return set()

        spread_matches: set[str] = set()

        # BFS through relations from direct matches
        # 1-hop: Direct relations (decay = 0.5)
        # 2-hop: Second-degree (decay = 0.25)
        # 3-hop: Third-degree (decay = 0.125)

        max_hops = 3
        decay_per_hop = 0.5

        # Track visited to avoid cycles
        visited: set[str] = set(direct_matches)

        # Queue: (memory_id, hop_distance, source_score)
        queue: list[tuple[str, int, float]] = []

        # Initialize queue with direct matches
        for mem_id in direct_matches:
            if mem_id in activation_scores:
                queue.append((mem_id, 0, activation_scores[mem_id].final_score))

        while queue:
            current_id, hop_distance, source_score = queue.pop(0)

            # Don't spread beyond max hops
            if hop_distance >= max_hops:
                continue

            # Get related memories
            related_ids = self.graph.get_related_memories(current_id)

            for related_id in related_ids:
                if related_id in visited:
                    continue

                visited.add(related_id)

                # Get memory object
                if related_id not in memory_map:
                    mem = db.get_memory(related_id)
                    if mem:
                        memory_map[related_id] = mem
                    else:
                        continue
                else:
                    mem = memory_map[related_id]

                # Calculate spreading score (exponential decay)
                spreading_score = source_score * (decay_per_hop ** (hop_distance + 1))

                # Calculate temporal score
                temporal_score = calculate_score(
                    use_count=mem.use_count,
                    last_used=mem.last_used,
                    strength=mem.strength,
                    now=now,
                )
                temporal_score = min(temporal_score / 2.0, 1.0)

                # Base relevance is 0 for spread-only memories
                base_relevance = 0.0

                # Determine source
                if hop_distance == 0:
                    source = ActivationSource.SPREAD_1HOP
                elif hop_distance == 1:
                    source = ActivationSource.SPREAD_2HOP
                else:
                    source = ActivationSource.SPREAD_3HOP

                # Create activation score
                activation_scores[related_id] = ActivationScore.calculate(
                    memory_id=related_id,
                    base_relevance=base_relevance,
                    temporal_score=temporal_score,
                    spreading_score=spreading_score,
                    source=source,
                    matched_keywords=[],
                )

                spread_matches.add(related_id)

                # Add to queue for further spreading
                queue.append((related_id, hop_distance + 1, spreading_score))

        return spread_matches

    def rebuild_index(self) -> None:
        """Rebuild activation index from current memory storage.

        Called on:
        - Server startup
        - After bulk memory operations
        - Manual index refresh
        """
        self._rebuild_index()
