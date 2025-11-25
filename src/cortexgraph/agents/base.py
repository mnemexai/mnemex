"""Abstract base class for consolidation agents.

This module provides the ConsolidationAgent base class that all five
specialized agents inherit from. It implements:

- Dry-run mode (FR-010)
- Rate limiting (FR-014)
- Confidence-based processing (FR-016)
- Beads audit trail integration (FR-007)

From research.md:
    Agent base class uses ABC with Generic result types. Consistent
    interface across all five agents with dry-run mode and rate limiting.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from cortexgraph.agents.models import ProcessingDecision
from cortexgraph.agents.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Type variable for agent-specific result models
T = TypeVar("T", bound=BaseModel)


class ConfidenceConfig(BaseModel):
    """Configuration for confidence-based processing decisions (T007).

    From data-model.md:
        - auto_threshold: Auto-process above this (default 0.9)
        - log_threshold: Log-only above this (default 0.7)
        - wait_below: Wait for human below log_threshold

    From spec.md FR-016:
        - confidence >= 0.9 → auto-process immediately
        - confidence 0.7-0.9 → process with detailed logging
        - confidence < 0.7 → create beads issue, wait for human
    """

    auto_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Auto-process above this threshold",
    )
    log_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Log-only processing above this threshold",
    )

    @property
    def wait_below(self) -> float:
        """Derived: wait for human below log_threshold."""
        return self.log_threshold

    def decide(self, confidence: float) -> ProcessingDecision:
        """Determine processing decision based on confidence.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            ProcessingDecision enum value
        """
        if confidence >= self.auto_threshold:
            return ProcessingDecision.AUTO
        elif confidence >= self.log_threshold:
            return ProcessingDecision.LOG_ONLY
        else:
            return ProcessingDecision.WAIT_HUMAN


class AgentResult(BaseModel):
    """Wrapper for agent run results with statistics."""

    results: list[BaseModel] = Field(default_factory=list)
    processed_count: int = Field(default=0)
    skipped_count: int = Field(default=0)
    error_count: int = Field(default=0)
    dry_run: bool = Field(default=False)


class ConsolidationAgent(ABC, Generic[T]):
    """Abstract base class for all consolidation agents (T006).

    All agents MUST inherit from this class and implement:
        - scan(): Find items needing processing
        - process_item(): Process a single item

    From contracts/agent-api.md:
        - run() executes agent on all scanned items
        - dry_run mode previews without making changes
        - rate_limit prevents overwhelming the system

    Attributes:
        dry_run: If True, preview without making changes
        rate_limit: Max operations per minute
        confidence_config: Thresholds for auto/log/wait decisions

    Example:
        >>> class MyAgent(ConsolidationAgent[MyResult]):
        ...     def scan(self) -> list[str]:
        ...         return ["mem-1", "mem-2"]
        ...     def process_item(self, memory_id: str) -> MyResult:
        ...         return MyResult(...)
        >>> agent = MyAgent(dry_run=True)
        >>> results = agent.run()
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
        confidence_config: ConfidenceConfig | None = None,
    ) -> None:
        """Initialize agent (T006).

        Args:
            dry_run: If True, preview without making changes
            rate_limit: Max operations per minute
            confidence_config: Thresholds for auto/log/wait decisions
        """
        self.dry_run = dry_run
        self.rate_limit = rate_limit
        self.confidence_config = confidence_config or ConfidenceConfig()
        self._rate_limiter = RateLimiter(max_ops=rate_limit, window_seconds=60)
        self._processed_count = 0
        self._skipped_count = 0
        self._error_count = 0

        logger.info(
            f"Initialized {self.__class__.__name__} (dry_run={dry_run}, rate_limit={rate_limit})"
        )

    @property
    def agent_name(self) -> str:
        """Return agent name for logging and beads labels."""
        # Convert class name to lowercase agent type
        # e.g., DecayAnalyzer -> decay, ClusterDetector -> cluster
        name = self.__class__.__name__
        mapping = {
            "DecayAnalyzer": "decay",
            "ClusterDetector": "cluster",
            "SemanticMerge": "merge",
            "LTMPromoter": "promote",
            "RelationshipDiscovery": "relations",
        }
        return mapping.get(name, name.lower())

    @abstractmethod
    def scan(self) -> list[str]:
        """Scan for items needing processing.

        Returns:
            List of memory IDs to process

        Contract (from contracts/agent-api.md):
            - MUST return list (may be empty)
            - MUST NOT modify any data
            - SHOULD complete within 5 seconds
        """
        ...

    @abstractmethod
    def process_item(self, memory_id: str) -> T:
        """Process a single memory.

        Args:
            memory_id: UUID of memory to process

        Returns:
            Result model (agent-specific)

        Contract (from contracts/agent-api.md):
            - MUST return result model or raise exception
            - If dry_run=True, MUST NOT modify any data
            - MUST create beads issue for audit trail
            - SHOULD complete within 5 seconds
        """
        ...

    def should_process(self, confidence: float) -> tuple[bool, ProcessingDecision]:
        """Determine if item should be processed based on confidence.

        Args:
            confidence: Confidence score for this operation

        Returns:
            Tuple of (should_process, decision)
        """
        decision = self.confidence_config.decide(confidence)

        if decision == ProcessingDecision.WAIT_HUMAN:
            logger.info(f"Confidence {confidence:.2f} below threshold - waiting for human")
            return False, decision

        if decision == ProcessingDecision.LOG_ONLY:
            logger.info(f"Confidence {confidence:.2f} - processing with detailed logging")

        return True, decision

    def run(self) -> list[T]:
        """Execute agent on all scanned items (T008, T009).

        Returns:
            List of results from process_item calls

        Contract (from contracts/agent-api.md):
            - MUST respect rate_limit
            - MUST call scan() then process_item() for each
            - MUST handle exceptions per-item (don't abort all)
        """
        logger.info(f"Starting {self.__class__.__name__} run (dry_run={self.dry_run})")

        # Scan for items
        items = self.scan()
        logger.info(f"Found {len(items)} items to process")

        if not items:
            return []

        results: list[T] = []
        self._processed_count = 0
        self._skipped_count = 0
        self._error_count = 0

        for item_id in items:
            # Rate limiting (T008)
            if not self._rate_limiter.acquire():
                wait_time = self._rate_limiter.time_until_available()
                logger.warning(
                    f"Rate limit exceeded. Waiting {wait_time:.2f}s "
                    f"(processed {self._processed_count}/{len(items)})"
                )
                if not self._rate_limiter.wait_and_acquire(timeout=wait_time + 1):
                    logger.error("Rate limit timeout - stopping execution")
                    break

            try:
                # Process item (respects dry_run mode in subclass)
                result = self.process_item(item_id)
                results.append(result)
                self._processed_count += 1

                if self.dry_run:
                    logger.debug(f"[DRY RUN] Would process: {item_id}")
                else:
                    logger.debug(f"Processed: {item_id}")

            except Exception as e:
                self._error_count += 1
                logger.error(f"Error processing {item_id}: {e}", exc_info=True)
                # Continue with next item (don't abort all)
                continue

        logger.info(
            f"Completed {self.__class__.__name__} run: "
            f"processed={self._processed_count}, "
            f"skipped={self._skipped_count}, "
            f"errors={self._error_count}"
        )

        return results

    def get_stats(self) -> dict[str, int]:
        """Return execution statistics."""
        return {
            "processed": self._processed_count,
            "skipped": self._skipped_count,
            "errors": self._error_count,
            "rate_limit_remaining": self._rate_limiter.remaining,
        }
