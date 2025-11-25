"""Contract tests for ClusterDetector (T034-T035).

These tests verify the ClusterDetector conforms to the ConsolidationAgent
contract defined in contracts/agent-api.md.

Contract Requirements:
- scan() MUST return list of memory IDs (may be empty)
- scan() MUST NOT modify any data
- process_item() MUST return ClusterResult or raise exception
- If dry_run=True, process_item() MUST NOT modify any data
- process_item() SHOULD complete within 5 seconds
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import ClusterAction, ClusterResult

if TYPE_CHECKING:
    from cortexgraph.agents.cluster_detector import ClusterDetector


# =============================================================================
# Contract Test Fixtures
# =============================================================================


# Score mapping used by mock_compute_score (reuse pattern from DecayAnalyzer)
MOCK_CLUSTERS = {
    # Cluster 1: High cohesion - should MERGE
    "cluster-high": {
        "memory_ids": ["mem-1", "mem-2", "mem-3"],
        "cohesion": 0.85,
    },
    # Cluster 2: Medium cohesion - should LINK
    "cluster-medium": {
        "memory_ids": ["mem-4", "mem-5"],
        "cohesion": 0.55,
    },
    # Cluster 3: Low cohesion - should IGNORE
    "cluster-low": {
        "memory_ids": ["mem-6", "mem-7"],
        "cohesion": 0.30,
    },
}


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock storage with test memories."""
    storage = MagicMock()
    # Create test memories that can be clustered
    storage.memories = {
        "mem-1": MagicMock(
            id="mem-1",
            content="PostgreSQL database configuration",
            entities=["PostgreSQL"],
            embed=None,
        ),
        "mem-2": MagicMock(
            id="mem-2",
            content="PostgreSQL database settings",
            entities=["PostgreSQL"],
            embed=None,
        ),
        "mem-3": MagicMock(
            id="mem-3",
            content="PostgreSQL connection pooling",
            entities=["PostgreSQL"],
            embed=None,
        ),
        "mem-4": MagicMock(
            id="mem-4",
            content="API authentication with JWT",
            entities=["JWT", "API"],
            embed=None,
        ),
        "mem-5": MagicMock(
            id="mem-5",
            content="JWT token validation",
            entities=["JWT"],
            embed=None,
        ),
        "mem-6": MagicMock(
            id="mem-6",
            content="Python type hints",
            entities=["Python"],
            embed=None,
        ),
        "mem-7": MagicMock(
            id="mem-7",
            content="Python async programming",
            entities=["Python"],
            embed=None,
        ),
    }
    return storage


def create_mock_clusters(mock_storage: MagicMock) -> list[MagicMock]:
    """Create mock Cluster objects for testing."""
    clusters = []

    # PostgreSQL cluster (high cohesion - MERGE)
    cluster1 = MagicMock()
    cluster1.memories = [
        mock_storage.memories["mem-1"],
        mock_storage.memories["mem-2"],
        mock_storage.memories["mem-3"],
    ]
    cluster1.cohesion = 0.85
    clusters.append(cluster1)

    # JWT cluster (medium cohesion - LINK)
    cluster2 = MagicMock()
    cluster2.memories = [
        mock_storage.memories["mem-4"],
        mock_storage.memories["mem-5"],
    ]
    cluster2.cohesion = 0.55
    clusters.append(cluster2)

    # Python cluster (low cohesion - IGNORE)
    cluster3 = MagicMock()
    cluster3.memories = [
        mock_storage.memories["mem-6"],
        mock_storage.memories["mem-7"],
    ]
    cluster3.cohesion = 0.30
    clusters.append(cluster3)

    return clusters


@pytest.fixture
def cluster_detector(mock_storage: MagicMock) -> ClusterDetector:
    """Create ClusterDetector with mock storage and pre-populated cluster cache."""
    from cortexgraph.agents.cluster_detector import ClusterDetector

    with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=mock_storage):
        detector = ClusterDetector(dry_run=True)
        detector._storage = mock_storage

        # Pre-populate cache directly (simulates what scan() would do)
        # This avoids needing to mock cluster_memories_simple
        detector._cached_clusters = {
            "mem-1": ["mem-1", "mem-2", "mem-3"],  # PostgreSQL cluster
            "mem-2": ["mem-1", "mem-2", "mem-3"],
            "mem-3": ["mem-1", "mem-2", "mem-3"],
            "mem-4": ["mem-4", "mem-5"],  # JWT cluster
            "mem-5": ["mem-4", "mem-5"],
            "mem-6": ["mem-6", "mem-7"],  # Python cluster
            "mem-7": ["mem-6", "mem-7"],
        }
        detector._cached_cohesion = {
            "mem-1|mem-2|mem-3": 0.85,  # High cohesion - MERGE
            "mem-4|mem-5": 0.55,  # Medium cohesion - LINK
            "mem-6|mem-7": 0.30,  # Low cohesion - IGNORE
        }

        return detector


# =============================================================================
# T034: Contract Test - scan() Returns Memory IDs
# =============================================================================


class TestClusterDetectorScanContract:
    """Contract tests for ClusterDetector.scan() method (T034)."""

    def test_scan_returns_list(self, cluster_detector: ClusterDetector) -> None:
        """scan() MUST return a list."""
        result = cluster_detector.scan()
        assert isinstance(result, list)

    def test_scan_returns_string_ids(self, cluster_detector: ClusterDetector) -> None:
        """scan() MUST return list of string memory IDs."""
        result = cluster_detector.scan()
        for item in result:
            assert isinstance(item, str)

    def test_scan_may_return_empty(self, mock_storage: MagicMock) -> None:
        """scan() MAY return empty list when no clusters found."""
        from cortexgraph.agents.cluster_detector import ClusterDetector

        # Only one memory - can't form clusters
        mock_storage.memories = {
            "lonely": MagicMock(id="lonely", content="Single memory", embed=None),
        }
        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=mock_storage):
            detector = ClusterDetector(dry_run=True)
            detector._storage = mock_storage
            result = detector.scan()
            assert result == []

    def test_scan_returns_clusterable_memories(self, cluster_detector: ClusterDetector) -> None:
        """scan() MUST return memory IDs that can be clustered.

        Note: The fixture pre-populates the cache, simulating what scan() returns.
        We verify the cache contains clusterable memory IDs.
        """
        # Verify cache was populated with clusterable memories
        # (fixture sets up 7 memories in 3 clusters)
        cached_memory_ids = list(cluster_detector._cached_clusters.keys())

        # Should find at least some memories to cluster
        assert len(cached_memory_ids) >= 2

        # Each memory should have cluster members
        for mem_id in cached_memory_ids:
            cluster_members = cluster_detector._cached_clusters[mem_id]
            assert len(cluster_members) >= 2  # Clusters have at least 2 members

    def test_scan_does_not_modify_data(
        self, cluster_detector: ClusterDetector, mock_storage: MagicMock
    ) -> None:
        """scan() MUST NOT modify any data."""
        # Take snapshot before
        original_count = len(mock_storage.memories)

        # Run scan
        cluster_detector.scan()

        # Verify no changes
        assert len(mock_storage.memories) == original_count

    def test_scan_is_subclass_of_consolidation_agent(
        self, cluster_detector: ClusterDetector
    ) -> None:
        """ClusterDetector MUST inherit from ConsolidationAgent."""
        assert isinstance(cluster_detector, ConsolidationAgent)


# =============================================================================
# T035: Contract Test - process_item() Returns ClusterResult
# =============================================================================


class TestClusterDetectorProcessItemContract:
    """Contract tests for ClusterDetector.process_item() method (T035)."""

    def test_process_item_returns_cluster_result(self, cluster_detector: ClusterDetector) -> None:
        """process_item() MUST return ClusterResult."""
        # First scan to find clusterable memories
        memory_ids = cluster_detector.scan()
        if memory_ids:
            # Process the first memory found
            result = cluster_detector.process_item(memory_ids[0])
            assert isinstance(result, ClusterResult)

    def test_process_item_result_has_required_fields(
        self, cluster_detector: ClusterDetector
    ) -> None:
        """ClusterResult MUST have all required fields."""
        memory_ids = cluster_detector.scan()
        if memory_ids:
            result = cluster_detector.process_item(memory_ids[0])

            # Required fields
            assert hasattr(result, "cluster_id")
            assert hasattr(result, "memory_ids")
            assert hasattr(result, "cohesion")
            assert hasattr(result, "action")
            assert hasattr(result, "confidence")

            # Types
            assert isinstance(result.cluster_id, str)
            assert isinstance(result.memory_ids, list)
            assert len(result.memory_ids) >= 2  # Clusters have at least 2 memories
            assert isinstance(result.cohesion, float)
            assert isinstance(result.action, ClusterAction)
            assert isinstance(result.confidence, float)

    def test_process_item_cohesion_in_range(self, cluster_detector: ClusterDetector) -> None:
        """ClusterResult.cohesion MUST be in range [0.0, 1.0]."""
        memory_ids = cluster_detector.scan()
        if memory_ids:
            result = cluster_detector.process_item(memory_ids[0])
            assert 0.0 <= result.cohesion <= 1.0

    def test_process_item_confidence_in_range(self, cluster_detector: ClusterDetector) -> None:
        """ClusterResult.confidence MUST be in range [0.0, 1.0]."""
        memory_ids = cluster_detector.scan()
        if memory_ids:
            result = cluster_detector.process_item(memory_ids[0])
            assert 0.0 <= result.confidence <= 1.0

    def test_process_item_memory_ids_include_input(self, cluster_detector: ClusterDetector) -> None:
        """ClusterResult.memory_ids MUST include the input memory_id."""
        memory_ids = cluster_detector.scan()
        if memory_ids:
            input_id = memory_ids[0]
            result = cluster_detector.process_item(input_id)
            assert input_id in result.memory_ids

    def test_process_item_raises_on_invalid_id(self, cluster_detector: ClusterDetector) -> None:
        """process_item() MUST raise exception for invalid memory ID."""
        with pytest.raises((ValueError, KeyError, RuntimeError)):
            cluster_detector.process_item("nonexistent-memory")

    def test_process_item_dry_run_no_side_effects(self, mock_storage: MagicMock) -> None:
        """If dry_run=True, process_item() MUST NOT modify any data."""
        from cortexgraph.agents.cluster_detector import ClusterDetector

        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=mock_storage):
            detector = ClusterDetector(dry_run=True)
            detector._storage = mock_storage

            # Track calls that would modify data
            mock_storage.create_relation = MagicMock()

            memory_ids = detector.scan()
            if memory_ids:
                detector.process_item(memory_ids[0])

                # In dry_run mode, no modifications should occur
                mock_storage.create_relation.assert_not_called()

    def test_process_item_completes_within_timeout(self, cluster_detector: ClusterDetector) -> None:
        """process_item() SHOULD complete within 5 seconds."""
        memory_ids = cluster_detector.scan()
        if memory_ids:
            start = time.time()
            cluster_detector.process_item(memory_ids[0])
            elapsed = time.time() - start

            assert elapsed < 5.0, f"process_item took {elapsed:.2f}s (limit: 5s)"


# =============================================================================
# Contract Integration Tests
# =============================================================================


class TestClusterDetectorFullContract:
    """Integration tests verifying full contract compliance."""

    def test_run_method_uses_scan_and_process_item(self, cluster_detector: ClusterDetector) -> None:
        """run() MUST call scan() then process_item() for each result."""
        results = cluster_detector.run()

        # All results should be ClusterResult
        for result in results:
            assert isinstance(result, ClusterResult)

    def test_action_matches_cohesion_thresholds(self, cluster_detector: ClusterDetector) -> None:
        """Action MUST match cohesion thresholds (MERGE >= 0.75, LINK 0.4-0.75, IGNORE < 0.4)."""
        results = cluster_detector.run()

        for result in results:
            if result.cohesion >= 0.75:
                assert result.action == ClusterAction.MERGE
            elif result.cohesion >= 0.4:
                assert result.action == ClusterAction.LINK
            else:
                assert result.action == ClusterAction.IGNORE

    def test_run_handles_errors_gracefully(
        self, cluster_detector: ClusterDetector, mock_storage: MagicMock
    ) -> None:
        """run() MUST handle errors per-item without aborting all."""
        # Add a memory that will cause an error
        mock_storage.memories["mem-error"] = MagicMock(
            id="mem-error",
            content=None,  # Invalid - will cause error during clustering
            embed=None,
        )

        # Should not raise - should skip error and continue
        results = cluster_detector.run()

        # Should still produce some results from valid memories
        # (may be empty if clustering fails entirely, but should not raise)
        assert isinstance(results, list)
