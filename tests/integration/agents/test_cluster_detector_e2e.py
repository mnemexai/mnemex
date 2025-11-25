"""Integration tests for ClusterDetector (T038).

End-to-end tests with real (test) storage to verify the full
cluster detection workflow.

Note: For clustering to work without embeddings, we rely on entity-based
similarity. Memories with overlapping entities will cluster together.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cortexgraph.agents.cluster_detector import ClusterDetector
from cortexgraph.agents.models import ClusterAction, ClusterResult
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Memory

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_storage(temp_storage_dir: Path) -> JSONLStorage:
    """Create real JSONL storage with clusterable test data.

    Creates memories with overlapping entities that will cluster together
    based on entity similarity in cluster_memories_simple.
    """
    storage = JSONLStorage(str(temp_storage_dir))
    now = int(time.time())

    # PostgreSQL cluster - 3 memories with shared "PostgreSQL" entity
    # Should form a cohesive cluster
    postgres_mem_1 = Memory(
        id="pg-1",
        content="PostgreSQL database configuration for production",
        entities=["PostgreSQL", "Database"],
        created_at=now - 86400,
        last_used=now - 3600,
        use_count=5,
        strength=1.0,
    )
    postgres_mem_2 = Memory(
        id="pg-2",
        content="PostgreSQL connection pooling settings",
        entities=["PostgreSQL", "Connection"],
        created_at=now - 86400 * 2,
        last_used=now - 7200,
        use_count=3,
        strength=1.0,
    )
    postgres_mem_3 = Memory(
        id="pg-3",
        content="PostgreSQL query optimization tips",
        entities=["PostgreSQL", "Query"],
        created_at=now - 86400 * 3,
        last_used=now - 10800,
        use_count=2,
        strength=1.0,
    )

    # API authentication cluster - 2 memories with shared "JWT" entity
    jwt_mem_1 = Memory(
        id="jwt-1",
        content="JWT token generation process",
        entities=["JWT", "Authentication"],
        created_at=now - 86400,
        last_used=now - 1800,
        use_count=4,
        strength=1.2,
    )
    jwt_mem_2 = Memory(
        id="jwt-2",
        content="JWT token validation middleware",
        entities=["JWT", "Middleware"],
        created_at=now - 86400 * 2,
        last_used=now - 3600,
        use_count=3,
        strength=1.1,
    )

    # Isolated memory - won't cluster (no shared entities)
    isolated_mem = Memory(
        id="isolated",
        content="Random unrelated thought about cats",
        entities=["Cats"],
        created_at=now - 86400,
        last_used=now - 1800,
        use_count=1,
        strength=1.0,
    )

    # Add memories to storage
    storage.memories = {
        "pg-1": postgres_mem_1,
        "pg-2": postgres_mem_2,
        "pg-3": postgres_mem_3,
        "jwt-1": jwt_mem_1,
        "jwt-2": jwt_mem_2,
        "isolated": isolated_mem,
    }

    return storage


@pytest.fixture
def cluster_detector_with_storage(test_storage: JSONLStorage) -> ClusterDetector:
    """Create ClusterDetector with real test storage."""
    with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=test_storage):
        detector = ClusterDetector(dry_run=True)
        detector._storage = test_storage
        return detector


# =============================================================================
# T038: Integration Test - End-to-End Cluster Detection
# =============================================================================


class TestClusterDetectionEndToEnd:
    """End-to-end integration tests for cluster detection workflow."""

    def test_full_cluster_workflow(
        self, cluster_detector_with_storage: ClusterDetector, test_storage: JSONLStorage
    ) -> None:
        """Test complete cluster detection from scan to results."""
        detector = cluster_detector_with_storage

        # Execute full run
        results = detector.run()

        # All results should be ClusterResult
        for result in results:
            assert isinstance(result, ClusterResult)

    def test_isolated_memory_not_clustered(
        self, cluster_detector_with_storage: ClusterDetector
    ) -> None:
        """Test isolated memory doesn't appear in clusters."""
        detector = cluster_detector_with_storage

        # Scan for clusterable memories
        memory_ids = detector.scan()

        # Isolated memory should not be in results (no shared entities)
        assert "isolated" not in memory_ids

    def test_action_based_on_cohesion(self, cluster_detector_with_storage: ClusterDetector) -> None:
        """Test actions are recommended based on cohesion thresholds."""
        detector = cluster_detector_with_storage
        results = detector.run()

        # All results should have valid actions matching cohesion thresholds
        for result in results:
            assert result.action in ClusterAction
            # Verify action matches cohesion
            if result.cohesion >= 0.75:
                assert result.action == ClusterAction.MERGE
            elif result.cohesion >= 0.40:
                assert result.action == ClusterAction.LINK
            else:
                assert result.action == ClusterAction.IGNORE

    def test_cohesion_in_valid_range(self, cluster_detector_with_storage: ClusterDetector) -> None:
        """Test cohesion scores are in valid range [0, 1]."""
        detector = cluster_detector_with_storage
        results = detector.run()

        for result in results:
            assert 0.0 <= result.cohesion <= 1.0, f"Cohesion {result.cohesion} out of range"

    def test_confidence_in_valid_range(
        self, cluster_detector_with_storage: ClusterDetector
    ) -> None:
        """Test confidence scores are in valid range [0, 1]."""
        detector = cluster_detector_with_storage
        results = detector.run()

        for result in results:
            assert 0.0 <= result.confidence <= 1.0, f"Confidence {result.confidence} out of range"

    def test_cluster_has_minimum_members(
        self, cluster_detector_with_storage: ClusterDetector
    ) -> None:
        """Test all clusters meet minimum size requirement."""
        detector = cluster_detector_with_storage
        results = detector.run()

        for result in results:
            assert len(result.memory_ids) >= 2, "Cluster must have at least 2 members"

    def test_dry_run_no_mutations(
        self, cluster_detector_with_storage: ClusterDetector, test_storage: JSONLStorage
    ) -> None:
        """Test dry_run mode doesn't mutate storage."""
        detector = cluster_detector_with_storage

        # Capture original state
        original_count = len(test_storage.memories)
        original_ids = set(test_storage.memories.keys())

        # Run detector
        detector.run()

        # Verify no mutations
        assert len(test_storage.memories) == original_count
        assert set(test_storage.memories.keys()) == original_ids

    def test_stats_reflect_run(self, cluster_detector_with_storage: ClusterDetector) -> None:
        """Test statistics are updated correctly after run."""
        detector = cluster_detector_with_storage

        # Initial stats should be zero
        initial_stats = detector.get_stats()
        assert initial_stats["processed"] == 0

        # Run detector
        results = detector.run()

        # Stats should reflect processed count
        final_stats = detector.get_stats()
        assert final_stats["processed"] == len(results)
        assert final_stats["errors"] == 0


class TestClusterDetectorEdgeCases:
    """Integration tests for edge cases."""

    def test_empty_storage(self, temp_storage_dir: Path) -> None:
        """Test behavior with empty storage."""
        storage = JSONLStorage(str(temp_storage_dir))
        storage.memories = {}

        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage):
            detector = ClusterDetector(dry_run=True)
            detector._storage = storage

            results = detector.run()

            assert results == []
            assert detector.get_stats()["processed"] == 0

    def test_single_memory(self, temp_storage_dir: Path) -> None:
        """Test behavior with only one memory (can't cluster)."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        single = Memory(
            id="single",
            content="A lonely memory",
            entities=["Test"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )

        storage.memories = {"single": single}

        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage):
            detector = ClusterDetector(dry_run=True)
            detector._storage = storage

            results = detector.run()

            # Single memory can't form a cluster
            assert results == []

    def test_no_overlapping_entities(self, temp_storage_dir: Path) -> None:
        """Test behavior when memories have no overlapping entities."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        mem_1 = Memory(
            id="mem-1",
            content="About cats",
            entities=["Cats"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )
        mem_2 = Memory(
            id="mem-2",
            content="About dogs",
            entities=["Dogs"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )
        mem_3 = Memory(
            id="mem-3",
            content="About birds",
            entities=["Birds"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )

        storage.memories = {"mem-1": mem_1, "mem-2": mem_2, "mem-3": mem_3}

        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage):
            detector = ClusterDetector(dry_run=True)
            detector._storage = storage

            results = detector.run()

            # No shared entities = no clusters
            assert results == []

    def test_custom_similarity_threshold(self, temp_storage_dir: Path) -> None:
        """Test custom similarity threshold affects clustering."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Create memories with partial entity overlap
        mem_1 = Memory(
            id="mem-1",
            content="Database config",
            entities=["Database", "Config"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )
        mem_2 = Memory(
            id="mem-2",
            content="Database backup",
            entities=["Database", "Backup"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )

        storage.memories = {"mem-1": mem_1, "mem-2": mem_2}

        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage):
            # Lower threshold should be more permissive
            detector_low = ClusterDetector(dry_run=True, similarity_threshold=0.20)
            detector_low._storage = storage

            # Higher threshold should be stricter
            detector_high = ClusterDetector(dry_run=True, similarity_threshold=0.80)
            detector_high._storage = storage

            results_low = detector_low.run()
            results_high = detector_high.run()

            # Lower threshold should capture more (or same) clusters
            assert len(results_low) >= len(results_high)

    def test_custom_min_cluster_size(self, temp_storage_dir: Path) -> None:
        """Test custom minimum cluster size."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Create 2 memories with shared entity
        mem_1 = Memory(
            id="mem-1",
            content="Python basics",
            entities=["Python"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )
        mem_2 = Memory(
            id="mem-2",
            content="Python advanced",
            entities=["Python"],
            created_at=now,
            last_used=now,
            use_count=1,
            strength=1.0,
        )

        storage.memories = {"mem-1": mem_1, "mem-2": mem_2}

        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage):
            # Default min_cluster_size=2 should find cluster
            detector_default = ClusterDetector(dry_run=True, min_cluster_size=2)
            detector_default._storage = storage

            # Higher min_cluster_size=3 should not find cluster
            detector_strict = ClusterDetector(dry_run=True, min_cluster_size=3)
            detector_strict._storage = storage

            results_default = detector_default.run()
            results_strict = detector_strict.run()

            # Strict threshold should find fewer clusters
            assert len(results_strict) <= len(results_default)
