"""Decay Analyzer agent for memory triage (T028-T033).

This agent identifies memories approaching the forget threshold and
creates beads issues for triage. It's the MVP agent that prevents
memory loss.

From spec.md US1:
    As a knowledge worker, I want memories approaching forget threshold
    to be automatically flagged so I can decide whether to reinforce,
    consolidate, or let them decay.

Urgency Classification:
    - HIGH: score < 0.10 (near-forget, needs immediate attention)
    - MEDIUM: score 0.10-0.25 (danger zone peak, review soon)
    - LOW: score 0.25-0.35 (entering decay, can wait)

Action Recommendations:
    - REINFORCE: Touch memory to reset decay
    - CONSOLIDATE: Group with similar memories
    - PROMOTE: Move to long-term storage if high value
    - GC: Allow to expire (low value)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import DecayAction, DecayResult, Urgency
from cortexgraph.agents.storage_utils import get_storage
from cortexgraph.core.decay import calculate_score

if TYPE_CHECKING:
    from cortexgraph.storage.jsonl_storage import JSONLStorage
    from cortexgraph.storage.models import Memory

logger = logging.getLogger(__name__)

# Default threshold for scanning (memories below this are candidates)
SCAN_THRESHOLD = 0.35

# Urgency boundaries
URGENCY_HIGH_THRESHOLD = 0.10
URGENCY_MEDIUM_THRESHOLD = 0.25


class DecayAnalyzer(ConsolidationAgent[DecayResult]):
    """Agent for identifying memories needing triage due to decay (T028).

    Scans for memories with score below threshold and classifies them
    by urgency, recommending appropriate actions.

    Example:
        >>> analyzer = DecayAnalyzer(dry_run=True)
        >>> results = analyzer.run()
        >>> for result in results:
        ...     print(f"{result.memory_id}: {result.urgency} - {result.action}")
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
        scan_threshold: float = SCAN_THRESHOLD,
    ) -> None:
        """Initialize DecayAnalyzer.

        Args:
            dry_run: If True, preview without making changes
            rate_limit: Max operations per minute
            scan_threshold: Score threshold for scanning (default 0.35)
        """
        super().__init__(dry_run=dry_run, rate_limit=rate_limit)
        self.scan_threshold = scan_threshold
        self._storage: "JSONLStorage | None" = None

    @property
    def storage(self) -> "JSONLStorage":
        """Get storage, initializing lazily."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def _compute_score(self, memory: Memory) -> float:
        """Compute current decay score for a memory.

        Uses the decay module's calculate_score function which considers
        use_count, last_used, and strength.
        """
        return calculate_score(
            use_count=memory.use_count,
            last_used=memory.last_used,
            strength=memory.strength,
        )

    def scan(self) -> list[str]:
        """Find memories with score below threshold (T029).

        Returns:
            List of memory IDs needing triage

        Contract (from contracts/agent-api.md):
            - MUST return list (may be empty)
            - MUST NOT modify any data
            - SHOULD complete within 5 seconds
        """
        memory_ids: list[str] = []

        # Get all memories and filter by computed score
        for mem_id, memory in self.storage.memories.items():
            try:
                score = self._compute_score(memory)
                if score < self.scan_threshold:
                    memory_ids.append(mem_id)
            except (AttributeError, TypeError):
                # Skip memories with missing attributes
                logger.debug(f"Skipping memory {mem_id} - cannot compute score")
                continue

        logger.info(f"DecayAnalyzer scan found {len(memory_ids)} memories below threshold")
        return memory_ids

    def process_item(self, memory_id: str) -> DecayResult:
        """Process a single memory, determining urgency and action (T030).

        Args:
            memory_id: UUID of memory to process

        Returns:
            DecayResult with urgency classification and recommended action

        Raises:
            KeyError: If memory_id not found
            ValueError: If memory has invalid data

        Contract (from contracts/agent-api.md):
            - MUST return DecayResult or raise exception
            - If dry_run=True, MUST NOT modify any data
            - SHOULD complete within 5 seconds
        """
        # Get memory from storage
        memory = self.storage.memories.get(memory_id)
        if memory is None:
            raise KeyError(f"Memory not found: {memory_id}")

        # Compute score using decay calculation
        try:
            score = self._compute_score(memory)
        except (AttributeError, TypeError) as e:
            raise ValueError(f"Memory {memory_id} has invalid data: {e}") from e

        # Classify urgency (T025)
        urgency = self._classify_urgency(score)

        # Recommend action (T026)
        action = self._recommend_action(score, memory)

        # Create beads issue for urgent items (T032) - only if not dry_run
        beads_issue_id = None
        if not self.dry_run and urgency == Urgency.HIGH:
            beads_issue_id = self._create_beads_issue(memory_id, score, urgency, action)

        return DecayResult(
            memory_id=memory_id,
            score=score,
            urgency=urgency,
            action=action,
            beads_issue_id=beads_issue_id,
        )

    def _classify_urgency(self, score: float) -> Urgency:
        """Classify urgency based on score (T025).

        Thresholds from research.md danger zone analysis:
            - HIGH: < 0.10 (near forget threshold)
            - MEDIUM: 0.10-0.25 (danger zone peak)
            - LOW: 0.25-0.35 (entering decay)
        """
        if score < URGENCY_HIGH_THRESHOLD:
            return Urgency.HIGH
        elif score < URGENCY_MEDIUM_THRESHOLD:
            return Urgency.MEDIUM
        else:
            return Urgency.LOW

    def _recommend_action(self, score: float, memory: object) -> DecayAction:
        """Recommend action based on score and memory attributes (T026).

        Logic:
            - score < 0.05: GC (too late to save unless high value)
            - score < 0.10 & high use_count: REINFORCE (worth saving)
            - score < 0.10 & low use_count: GC (let it go)
            - score < 0.20: CONSOLIDATE (group with similar)
            - score >= 0.20 & high strength: PROMOTE (move to LTM)
            - otherwise: REINFORCE (default safe action)
        """
        use_count = getattr(memory, "use_count", 0)
        strength = getattr(memory, "strength", 1.0)

        # Near forget threshold
        if score < 0.05:
            # Only save if heavily used
            if use_count >= 5:
                return DecayAction.REINFORCE
            return DecayAction.GC

        # High urgency zone
        if score < URGENCY_HIGH_THRESHOLD:
            if use_count >= 3:
                return DecayAction.REINFORCE
            return DecayAction.GC

        # Medium urgency - good candidates for consolidation
        if score < 0.20:
            return DecayAction.CONSOLIDATE

        # Low urgency with high strength - promote
        if strength >= 1.5:
            return DecayAction.PROMOTE

        # Default: reinforce to prevent further decay
        return DecayAction.REINFORCE

    def _create_beads_issue(
        self,
        memory_id: str,
        score: float,
        urgency: Urgency,
        action: DecayAction,
    ) -> str | None:
        """Create beads issue for urgent memory (T032).

        Only creates issues for HIGH urgency memories to avoid noise.
        """
        try:
            from cortexgraph.agents.beads_integration import create_consolidation_issue

            issue_id = create_consolidation_issue(
                agent="decay",
                memory_ids=[memory_id],
                action=action.value,
                urgency=urgency.value,
            )
            logger.info(f"Created beads issue {issue_id} for memory {memory_id}")
            return issue_id
        except Exception as e:
            logger.warning(f"Failed to create beads issue: {e}")
            return None
