"""Hybrid scheduler for consolidation agents.

This module provides the Scheduler class which coordinates:
1. Programmatic execution of consolidation agents
2. Pipeline orchestration (decay → cluster → merge → promote → relations)
3. Event-driven hooks for urgent decay detection (post_save_check)

The scheduler is designed for two modes of operation:
- Scheduled: External cron/launchd calls cortexgraph-consolidate CLI
- Event-driven: post_save_check() hook detects urgent decay (score < 0.10)

Example:
    # Run full pipeline
    scheduler = Scheduler(dry_run=True)
    results = scheduler.run_pipeline()

    # Run single agent
    scheduler.run_agent("decay")

    # Check for urgent decay after saving
    scheduler.post_save_check("memory-123")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from cortexgraph.agents.base import ConsolidationAgent
    from cortexgraph.storage.jsonl_storage import JSONLStorage

logger = logging.getLogger(__name__)

# Pipeline execution order
AGENT_ORDER = ["decay", "cluster", "merge", "promote", "relations"]

# Default threshold for urgent decay detection
DEFAULT_URGENT_THRESHOLD = 0.10

# Default interval between scheduled runs (1 hour)
DEFAULT_INTERVAL_SECONDS = 3600

# Filename for storing last run timestamp
LAST_RUN_FILENAME = ".consolidation_last_run"


def post_save_hook(memory_id: str) -> dict[str, Any] | None:
    """Event-driven hook to check for urgent decay after save_memory.

    This function is called after a memory is saved to detect if it
    needs urgent attention (score < threshold). It's designed to be
    fast and fail-safe - errors are logged but don't propagate.

    Args:
        memory_id: ID of the newly saved memory

    Returns:
        None if no urgent action needed, otherwise dict with action details
    """
    try:
        scheduler = Scheduler()
        return scheduler.post_save_check(memory_id)
    except Exception as e:
        logger.warning(f"post_save_hook error for {memory_id}: {e}")
        return None


def calculate_score(memory_id: str) -> float:
    """Calculate current decay score for a memory.

    This is a wrapper around the core decay calculation that fetches
    the memory from storage first.

    Args:
        memory_id: Memory ID to check

    Returns:
        Current decay score (0.0-1.0)
    """
    from cortexgraph.context import get_db
    from cortexgraph.core.decay import calculate_score as core_calculate_score

    storage = get_db()
    memory = storage.memories.get(memory_id)

    if memory is None:
        # Memory not found, return high score (no action needed)
        return 1.0

    return core_calculate_score(
        use_count=memory.use_count,
        last_used=memory.last_used,
        strength=memory.strength,
    )


class Scheduler:
    """Hybrid scheduler for consolidation pipeline.

    Coordinates agent execution and provides event-driven hooks for
    urgent decay detection. Designed to work with external scheduling
    (cron/launchd) for periodic execution.

    Attributes:
        dry_run: If True, agents preview changes without modifying data
        urgent_threshold: Score threshold below which memory is urgent (default: 0.10)
        interval_seconds: Minimum seconds between scheduled runs (default: 3600)
    """

    def __init__(
        self,
        dry_run: bool = False,
        urgent_threshold: float = DEFAULT_URGENT_THRESHOLD,
        interval_seconds: int | None = None,
        interval_hours: float | None = None,
    ) -> None:
        """Initialize the scheduler.

        Args:
            dry_run: If True, agents preview changes without modifying data
            urgent_threshold: Score threshold for urgent detection (default: 0.10)
            interval_seconds: Minimum seconds between scheduled runs
            interval_hours: Alternative way to specify interval (converted to seconds)
        """
        self.dry_run = dry_run
        self.urgent_threshold = urgent_threshold

        # Handle interval - hours takes precedence if both specified
        if interval_hours is not None:
            self.interval_seconds = int(interval_hours * 3600)
        elif interval_seconds is not None:
            self.interval_seconds = interval_seconds
        else:
            self.interval_seconds = DEFAULT_INTERVAL_SECONDS

    def get_storage(self) -> JSONLStorage:
        """Get the storage instance.

        Uses get_db() for consistent access across the application.

        Returns:
            Configured JSONLStorage instance
        """
        from cortexgraph.context import get_db

        return get_db()

    def _get_agent(self, name: str) -> ConsolidationAgent[Any]:
        """Factory method to create agent instances.

        Args:
            name: Agent name (decay, cluster, merge, promote, relations)

        Returns:
            Configured agent instance

        Raises:
            ValueError: If agent name is unknown
        """
        # Import agents lazily to avoid circular imports
        from cortexgraph.agents.cluster_detector import ClusterDetector
        from cortexgraph.agents.decay_analyzer import DecayAnalyzer
        from cortexgraph.agents.ltm_promoter import LTMPromoter
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery
        from cortexgraph.agents.semantic_merge import SemanticMerge

        if name == "decay":
            return DecayAnalyzer(dry_run=self.dry_run)
        elif name == "cluster":
            return ClusterDetector(dry_run=self.dry_run)
        elif name == "merge":
            return SemanticMerge(dry_run=self.dry_run)
        elif name == "promote":
            return LTMPromoter(dry_run=self.dry_run)
        elif name == "relations":
            return RelationshipDiscovery(dry_run=self.dry_run)
        else:
            raise ValueError(f"Unknown agent: {name}")

    def run_agent(self, name: str) -> list[Any]:
        """Run a single consolidation agent.

        Args:
            name: Agent name (decay, cluster, merge, promote, relations)

        Returns:
            List of results from the agent's run() method

        Raises:
            ValueError: If agent name is unknown
        """
        agent = self._get_agent(name)
        logger.info(f"Running agent: {name} (dry_run={self.dry_run})")

        results = agent.run()
        logger.info(f"Agent {name} completed: {len(results) if results else 0} items processed")

        return results if results else []

    def run_pipeline(self) -> dict[str, list[Any]]:
        """Run all consolidation agents in pipeline order.

        Executes agents in order: decay → cluster → merge → promote → relations.
        Stops immediately if any agent raises an error.

        Returns:
            Dictionary mapping agent names to their results

        Raises:
            Exception: Re-raises any exception from an agent
        """
        logger.info(f"Starting consolidation pipeline (dry_run={self.dry_run})")
        results: dict[str, list[Any]] = {}

        for agent_name in AGENT_ORDER:
            # Run each agent, let exceptions propagate
            agent_results = self.run_agent(agent_name)
            results[agent_name] = agent_results

        logger.info("Consolidation pipeline completed successfully")
        return results

    def post_save_check(self, memory_id: str) -> dict[str, Any] | None:
        """Check if a newly saved memory needs urgent attention.

        This is the event-driven hook that can be called after save_memory
        to detect memories that are decaying rapidly and need immediate
        processing.

        Args:
            memory_id: ID of the memory to check

        Returns:
            None if no action needed, otherwise dict with action details
        """
        score = calculate_score(memory_id)

        if score >= self.urgent_threshold:
            # Score is above threshold, no urgent action needed
            logger.debug(f"Memory {memory_id} score {score:.3f} >= {self.urgent_threshold}")
            return None

        # Score is below threshold - urgent!
        logger.warning(
            f"Urgent decay detected: memory {memory_id} score {score:.3f} < {self.urgent_threshold}"
        )

        return self._handle_urgent_memory(memory_id, score)

    def _handle_urgent_memory(self, memory_id: str, score: float) -> dict[str, Any]:
        """Handle a memory with urgent decay score.

        In dry_run mode, returns what would happen without taking action.
        In live mode, flags the memory for immediate processing.

        Args:
            memory_id: ID of the urgent memory
            score: Current decay score

        Returns:
            Dictionary with action details
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would flag memory {memory_id} as urgent (score={score:.3f})")
            return {
                "memory_id": memory_id,
                "score": score,
                "dry_run": True,
                "action": "would_flag_urgent",
            }

        # Live mode - flag memory for urgent processing
        logger.info(f"Flagging memory {memory_id} as urgent (score={score:.3f})")
        # TODO: Integration with beads for issue creation
        # For now, just return the action taken
        return {
            "memory_id": memory_id,
            "score": score,
            "dry_run": False,
            "action": "flagged_urgent",
        }

    # =========================================================================
    # Scheduled Execution Methods (T089)
    # =========================================================================

    def _get_last_run_file(self) -> Path:
        """Get the path to the last run timestamp file.

        Returns:
            Path to the timestamp file in the storage directory
        """
        from pathlib import Path

        from cortexgraph.config import get_config

        config = get_config()
        return Path(config.storage_path) / LAST_RUN_FILENAME

    def _get_last_run_time(self) -> int | None:
        """Get the timestamp of the last scheduled run.

        Returns:
            Unix timestamp of last run, or None if never run
        """
        last_run_file = self._get_last_run_file()

        if not last_run_file.exists():
            return None

        try:
            content = last_run_file.read_text().strip()
            return int(content)
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to read last run time: {e}")
            return None

    def _save_last_run_time(self, timestamp: int) -> None:
        """Save the timestamp of the current run.

        Args:
            timestamp: Unix timestamp to save
        """
        last_run_file = self._get_last_run_file()

        try:
            # Ensure parent directory exists
            last_run_file.parent.mkdir(parents=True, exist_ok=True)
            last_run_file.write_text(str(timestamp))
        except OSError as e:
            logger.error(f"Failed to save last run time: {e}")

    def should_run(self, force: bool = False) -> bool:
        """Check if a scheduled run should execute.

        Args:
            force: If True, always return True regardless of interval

        Returns:
            True if run should execute, False if interval hasn't elapsed
        """
        if force:
            return True

        last_run = self._get_last_run_time()

        if last_run is None:
            # Never run before
            return True

        import time

        elapsed = int(time.time()) - last_run
        return elapsed >= self.interval_seconds

    def record_run(self) -> None:
        """Record the current time as the last run time."""
        import time

        self._save_last_run_time(int(time.time()))

    def run_scheduled(self, force: bool = False) -> dict[str, Any]:
        """Run the consolidation pipeline if the interval has elapsed.

        This is the main entry point for cron/launchd scheduled execution.
        It checks if enough time has passed since the last run and either
        executes the pipeline or skips.

        Args:
            force: If True, run regardless of interval elapsed

        Returns:
            Dictionary with execution results or skip information
        """
        if not force and not self.should_run():
            logger.info(f"Scheduled run skipped: interval ({self.interval_seconds}s) not elapsed")
            return {
                "skipped": True,
                "reason": "Interval not due - last run was too recent",
                "interval_seconds": self.interval_seconds,
            }

        # Execute the pipeline
        logger.info(f"Starting scheduled consolidation (force={force})")
        results = self.run_pipeline()

        # Record this run
        self.record_run()

        return {
            "skipped": False,
            "results": results,
            "interval_seconds": self.interval_seconds,
        }
