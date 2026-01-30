"""Cluster Detector agent for finding similar memories.

This agent scans for memories that could be clustered together based on
content similarity, shared entities, or embedding similarity. It identifies
memory groups for potential consolidation.

From data-model.md:
    - ClusterResult: Output with cluster_id, memory_ids, cohesion, action, confidence
    - ClusterAction thresholds: MERGE (>=0.75), LINK (0.4-0.75), IGNORE (<0.4)

From contracts/agent-api.md:
    - scan(): Returns memory IDs that can form clusters
    - process_item(): Returns ClusterResult for a memory's cluster
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import ClusterAction, ClusterResult
from cortexgraph.agents.storage_utils import get_storage
from cortexgraph.core.clustering import cluster_memories_simple
from cortexgraph.storage.models import ClusterConfig

if TYPE_CHECKING:
    from cortexgraph.storage.jsonl_storage import JSONLStorage

logger = logging.getLogger(__name__)


# =============================================================================
# Thresholds (documented constants for testing)
# =============================================================================

# Cohesion thresholds for action recommendation
MERGE_THRESHOLD = 0.75  # Cohesion >= 0.75 → MERGE
LINK_THRESHOLD = 0.40  # Cohesion 0.40-0.75 → LINK
# Below 0.40 → IGNORE

# Minimum cluster size for scan results
MIN_CLUSTER_SIZE = 2

# Default similarity threshold for clustering
DEFAULT_SIMILARITY_THRESHOLD = 0.40


class ClusterDetector(ConsolidationAgent[ClusterResult]):
    """Agent that detects memory clusters for consolidation (T039-T044).

    Scans memories and identifies groups with high content similarity,
    shared entities, or embedding proximity. Returns ClusterResult with
    recommended actions based on cohesion scores.

    From spec.md:
        - Uses existing cluster_memories_simple() for detection
        - Cohesion-based action: MERGE, LINK, or IGNORE
        - Confidence based on cluster quality metrics

    Attributes:
        dry_run: If True, preview without creating relations
        similarity_threshold: Minimum similarity for clustering (0.0-1.0)
        min_cluster_size: Minimum memories per cluster

    Example:
        >>> detector = ClusterDetector(dry_run=True)
        >>> memory_ids = detector.scan()
        >>> for mem_id in memory_ids:
        ...     result = detector.process_item(mem_id)
        ...     print(f"{result.cluster_id}: {result.action}")
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        min_cluster_size: int = MIN_CLUSTER_SIZE,
    ) -> None:
        """Initialize ClusterDetector.

        Args:
            dry_run: If True, preview without making changes
            rate_limit: Max operations per minute
            similarity_threshold: Minimum similarity for clustering
            min_cluster_size: Minimum memories per cluster
        """
        super().__init__(dry_run=dry_run, rate_limit=rate_limit)
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self._storage: "JSONLStorage" = get_storage()
        self._cached_clusters: dict[str, list[str]] = {}  # memory_id -> cluster memory_ids
        self._cached_cohesion: dict[str, float] = {}  # cluster_key -> cohesion

    def scan(self) -> list[str]:
        """Scan for memories that can form clusters.

        Returns:
            List of memory IDs that belong to detected clusters

        Contract:
            - MUST return list (may be empty)
            - MUST NOT modify any data
            - SHOULD complete within 5 seconds
        """
        logger.debug("Scanning for clusterable memories")

        # Get all memories from storage
        memories = list(self._storage.memories.values())

        if len(memories) < self.min_cluster_size:
            logger.debug(f"Not enough memories for clustering: {len(memories)}")
            return []

        # Run clustering algorithm
        config = ClusterConfig(
            threshold=self.similarity_threshold,
            min_cluster_size=self.min_cluster_size,
            max_cluster_size=10,  # Reasonable default
        )

        try:
            clusters = cluster_memories_simple(memories, config)
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return []

        if not clusters:
            logger.debug("No clusters found")
            return []

        # Build cache mapping memory_id -> cluster members
        self._cached_clusters.clear()
        self._cached_cohesion.clear()
        clusterable_memory_ids: set[str] = set()

        for cluster in clusters:
            # Get memory IDs in this cluster
            member_ids = [m.id for m in cluster.memories]
            cluster_key = self._cluster_key(member_ids)

            # Cache cohesion for later use in process_item
            self._cached_cohesion[cluster_key] = cluster.cohesion

            # Map each memory to its cluster members
            for mem_id in member_ids:
                self._cached_clusters[mem_id] = member_ids
                clusterable_memory_ids.add(mem_id)

        logger.info(
            f"Found {len(clusters)} clusters with {len(clusterable_memory_ids)} total memories"
        )

        return list(clusterable_memory_ids)

    def process_item(self, memory_id: str) -> ClusterResult:
        """Process a memory and return its cluster result.

        Args:
            memory_id: UUID of memory to process

        Returns:
            ClusterResult with cluster info and recommended action

        Contract:
            - MUST return ClusterResult or raise exception
            - If dry_run=True, MUST NOT modify any data
            - SHOULD complete within 5 seconds

        Raises:
            KeyError: If memory_id not found or not in a cluster
        """
        # Verify memory exists
        if memory_id not in self._storage.memories:
            raise KeyError(f"Memory not found: {memory_id}")

        # Get cluster from cache (populated by scan)
        if memory_id not in self._cached_clusters:
            # Memory wasn't in any cluster from scan - re-run scan or raise
            # For robustness, try to find cluster for this memory
            self._find_cluster_for_memory(memory_id)

        if memory_id not in self._cached_clusters:
            raise KeyError(f"Memory not in any cluster: {memory_id}")

        member_ids = self._cached_clusters[memory_id]
        cluster_key = self._cluster_key(member_ids)
        cohesion = self._cached_cohesion.get(cluster_key, 0.5)

        # Determine action based on cohesion thresholds
        action = self._determine_action(cohesion)

        # Calculate confidence based on cluster quality
        confidence = self._calculate_confidence(cohesion, len(member_ids))

        # Generate cluster ID
        cluster_id = f"cluster-{uuid.uuid4().hex[:8]}"

        result = ClusterResult(
            cluster_id=cluster_id,
            memory_ids=member_ids,
            cohesion=cohesion,
            action=action,
            confidence=confidence,
            beads_issue_id=None,  # Would be set if not dry_run
        )

        logger.debug(
            f"Processed cluster {cluster_id}: cohesion={cohesion:.2f}, action={action.value}"
        )

        return result

    def _determine_action(self, cohesion: float) -> ClusterAction:
        """Determine action based on cohesion score.

        Args:
            cohesion: Cluster cohesion score (0.0-1.0)

        Returns:
            ClusterAction enum value

        Thresholds from data-model.md:
            - MERGE: cohesion >= 0.75
            - LINK: cohesion 0.40-0.75
            - IGNORE: cohesion < 0.40
        """
        if cohesion >= MERGE_THRESHOLD:
            return ClusterAction.MERGE
        elif cohesion >= LINK_THRESHOLD:
            return ClusterAction.LINK
        else:
            return ClusterAction.IGNORE

    def _calculate_confidence(self, cohesion: float, cluster_size: int) -> float:
        """Calculate confidence in cluster recommendation.

        Args:
            cohesion: Cluster cohesion score (0.0-1.0)
            cluster_size: Number of memories in cluster

        Returns:
            Confidence score (0.0-1.0)

        Confidence factors:
            - Higher cohesion = higher confidence
            - Larger clusters (up to a point) = higher confidence
            - Very small or very large clusters = lower confidence
        """
        # Base confidence from cohesion
        base_confidence = cohesion

        # Size factor: optimal is 3-5 members
        if cluster_size == 2:
            size_factor = 0.8  # Small cluster, less confident
        elif cluster_size <= 5:
            size_factor = 1.0  # Optimal size
        elif cluster_size <= 8:
            size_factor = 0.9  # Getting large
        else:
            size_factor = 0.7  # Very large, might be too broad

        confidence = base_confidence * size_factor

        # Clamp to valid range
        return max(0.0, min(1.0, confidence))

    def _cluster_key(self, member_ids: list[str]) -> str:
        """Generate a consistent key for a cluster.

        Args:
            member_ids: List of memory IDs in cluster

        Returns:
            Sorted, joined string as cluster key
        """
        return "|".join(sorted(member_ids))

    def _find_cluster_for_memory(self, memory_id: str) -> None:
        """Try to find a cluster for a specific memory.

        This is called when process_item is called for a memory
        that wasn't found in scan(). Re-runs clustering on demand.

        Args:
            memory_id: Memory to find cluster for
        """
        if memory_id not in self._storage.memories:
            return

        memories = list(self._storage.memories.values())

        if len(memories) < self.min_cluster_size:
            return

        config = ClusterConfig(
            threshold=self.similarity_threshold,
            min_cluster_size=self.min_cluster_size,
            max_cluster_size=10,
        )

        try:
            clusters = cluster_memories_simple(memories, config)
        except Exception:
            return

        for cluster in clusters:
            member_ids = [m.id for m in cluster.memories]
            if memory_id in member_ids:
                cluster_key = self._cluster_key(member_ids)
                self._cached_cohesion[cluster_key] = cluster.cohesion
                for mid in member_ids:
                    self._cached_clusters[mid] = member_ids
                return
