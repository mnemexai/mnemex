"""Unit tests for ClusterDetector (T036-T037).

Tests the action determination and confidence calculation logic
in isolation from storage and clustering algorithms.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.cluster_detector import (
    LINK_THRESHOLD,
    MERGE_THRESHOLD,
    MIN_CLUSTER_SIZE,
    ClusterDetector,
)
from cortexgraph.agents.models import ClusterAction

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def detector() -> ClusterDetector:
    """Create ClusterDetector with mock storage."""
    mock_storage = MagicMock()
    mock_storage.memories = {}

    with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=mock_storage):
        d = ClusterDetector(dry_run=True)
        d._storage = mock_storage
        return d


# =============================================================================
# T036: Unit Tests for Action Determination
# =============================================================================


class TestActionDetermination:
    """Tests for _determine_action() method (T036)."""

    def test_merge_action_high_cohesion(self, detector: ClusterDetector) -> None:
        """Cohesion >= 0.75 should return MERGE action."""
        assert detector._determine_action(0.75) == ClusterAction.MERGE
        assert detector._determine_action(0.80) == ClusterAction.MERGE
        assert detector._determine_action(0.90) == ClusterAction.MERGE
        assert detector._determine_action(1.0) == ClusterAction.MERGE

    def test_merge_action_boundary(self, detector: ClusterDetector) -> None:
        """Test MERGE threshold boundary."""
        # Just below threshold - LINK
        assert detector._determine_action(0.749) == ClusterAction.LINK
        # At threshold - MERGE
        assert detector._determine_action(MERGE_THRESHOLD) == ClusterAction.MERGE

    def test_link_action_medium_cohesion(self, detector: ClusterDetector) -> None:
        """Cohesion 0.40-0.75 should return LINK action."""
        assert detector._determine_action(0.40) == ClusterAction.LINK
        assert detector._determine_action(0.50) == ClusterAction.LINK
        assert detector._determine_action(0.60) == ClusterAction.LINK
        assert detector._determine_action(0.70) == ClusterAction.LINK

    def test_link_action_boundary(self, detector: ClusterDetector) -> None:
        """Test LINK threshold boundary."""
        # Just below threshold - IGNORE
        assert detector._determine_action(0.399) == ClusterAction.IGNORE
        # At threshold - LINK
        assert detector._determine_action(LINK_THRESHOLD) == ClusterAction.LINK

    def test_ignore_action_low_cohesion(self, detector: ClusterDetector) -> None:
        """Cohesion < 0.40 should return IGNORE action."""
        assert detector._determine_action(0.0) == ClusterAction.IGNORE
        assert detector._determine_action(0.10) == ClusterAction.IGNORE
        assert detector._determine_action(0.20) == ClusterAction.IGNORE
        assert detector._determine_action(0.30) == ClusterAction.IGNORE
        assert detector._determine_action(0.39) == ClusterAction.IGNORE

    def test_thresholds_documented(self) -> None:
        """Verify thresholds match documentation."""
        assert MERGE_THRESHOLD == 0.75
        assert LINK_THRESHOLD == 0.40
        assert MIN_CLUSTER_SIZE == 2


# =============================================================================
# T037: Unit Tests for Confidence Calculation
# =============================================================================


class TestConfidenceCalculation:
    """Tests for _calculate_confidence() method (T037)."""

    def test_confidence_increases_with_cohesion(self, detector: ClusterDetector) -> None:
        """Higher cohesion should produce higher confidence."""
        conf_low = detector._calculate_confidence(0.30, 3)
        conf_mid = detector._calculate_confidence(0.50, 3)
        conf_high = detector._calculate_confidence(0.80, 3)

        assert conf_low < conf_mid < conf_high

    def test_confidence_in_valid_range(self, detector: ClusterDetector) -> None:
        """Confidence should always be in [0.0, 1.0] range."""
        # Test various combinations
        test_cases = [
            (0.0, 2),
            (0.5, 3),
            (1.0, 5),
            (0.9, 10),  # Very large cluster
            (0.1, 2),  # Low cohesion small cluster
        ]

        for cohesion, size in test_cases:
            confidence = detector._calculate_confidence(cohesion, size)
            assert 0.0 <= confidence <= 1.0, f"Failed for cohesion={cohesion}, size={size}"

    def test_confidence_optimal_cluster_size(self, detector: ClusterDetector) -> None:
        """Optimal cluster size (3-5) should have highest confidence factor."""
        cohesion = 0.80

        # Small cluster (size 2) - lower confidence
        conf_small = detector._calculate_confidence(cohesion, 2)

        # Optimal cluster (size 3-5) - higher confidence
        conf_optimal = detector._calculate_confidence(cohesion, 4)

        # Large cluster (size 10) - lower confidence
        conf_large = detector._calculate_confidence(cohesion, 10)

        assert conf_optimal > conf_small
        assert conf_optimal > conf_large

    def test_confidence_small_cluster_penalty(self, detector: ClusterDetector) -> None:
        """Clusters of size 2 should have reduced confidence."""
        cohesion = 0.80

        conf_size_2 = detector._calculate_confidence(cohesion, 2)
        conf_size_3 = detector._calculate_confidence(cohesion, 3)

        # Size 2 should be less confident than size 3
        assert conf_size_2 < conf_size_3

    def test_confidence_large_cluster_penalty(self, detector: ClusterDetector) -> None:
        """Very large clusters should have reduced confidence."""
        cohesion = 0.80

        conf_size_5 = detector._calculate_confidence(cohesion, 5)
        conf_size_9 = detector._calculate_confidence(cohesion, 9)
        conf_size_15 = detector._calculate_confidence(cohesion, 15)

        # Larger clusters should be less confident
        assert conf_size_5 >= conf_size_9 >= conf_size_15

    def test_confidence_zero_cohesion(self, detector: ClusterDetector) -> None:
        """Zero cohesion should produce zero or near-zero confidence."""
        confidence = detector._calculate_confidence(0.0, 3)
        assert confidence == 0.0

    def test_confidence_perfect_cohesion(self, detector: ClusterDetector) -> None:
        """Perfect cohesion with optimal size should produce high confidence."""
        confidence = detector._calculate_confidence(1.0, 4)
        # Should be very high (1.0 * 1.0 = 1.0 for optimal size)
        assert confidence >= 0.9


# =============================================================================
# Additional Unit Tests
# =============================================================================


class TestClusterKeyGeneration:
    """Tests for _cluster_key() method."""

    def test_cluster_key_sorted(self, detector: ClusterDetector) -> None:
        """Cluster key should be sorted for consistency."""
        key1 = detector._cluster_key(["mem-3", "mem-1", "mem-2"])
        key2 = detector._cluster_key(["mem-1", "mem-2", "mem-3"])
        key3 = detector._cluster_key(["mem-2", "mem-3", "mem-1"])

        # All should produce same key
        assert key1 == key2 == key3

    def test_cluster_key_format(self, detector: ClusterDetector) -> None:
        """Cluster key should be pipe-separated sorted IDs."""
        key = detector._cluster_key(["b", "a", "c"])
        assert key == "a|b|c"


class TestProcessItemWithCache:
    """Tests for process_item() using cached values."""

    def test_process_item_uses_cached_cohesion(self, detector: ClusterDetector) -> None:
        """process_item() should use cached cohesion values."""
        # Set up cache
        detector._storage.memories = {
            "mem-1": MagicMock(id="mem-1"),
            "mem-2": MagicMock(id="mem-2"),
        }
        detector._cached_clusters = {
            "mem-1": ["mem-1", "mem-2"],
            "mem-2": ["mem-1", "mem-2"],
        }
        detector._cached_cohesion = {
            "mem-1|mem-2": 0.85,  # High cohesion
        }

        result = detector.process_item("mem-1")

        assert result.cohesion == 0.85
        assert result.action == ClusterAction.MERGE

    def test_process_item_returns_correct_members(self, detector: ClusterDetector) -> None:
        """process_item() should return correct cluster members."""
        # Set up cache
        detector._storage.memories = {
            "mem-1": MagicMock(id="mem-1"),
            "mem-2": MagicMock(id="mem-2"),
            "mem-3": MagicMock(id="mem-3"),
        }
        detector._cached_clusters = {
            "mem-1": ["mem-1", "mem-2", "mem-3"],
            "mem-2": ["mem-1", "mem-2", "mem-3"],
            "mem-3": ["mem-1", "mem-2", "mem-3"],
        }
        detector._cached_cohesion = {
            "mem-1|mem-2|mem-3": 0.55,
        }

        result = detector.process_item("mem-2")

        assert set(result.memory_ids) == {"mem-1", "mem-2", "mem-3"}
        assert result.action == ClusterAction.LINK


class TestInitialization:
    """Tests for ClusterDetector initialization."""

    def test_default_values(self) -> None:
        """Test default initialization values."""
        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=MagicMock()):
            detector = ClusterDetector()

            assert detector.dry_run is False
            assert detector.similarity_threshold == 0.40
            assert detector.min_cluster_size == 2

    def test_custom_values(self) -> None:
        """Test custom initialization values."""
        with patch("cortexgraph.agents.cluster_detector.get_storage", return_value=MagicMock()):
            detector = ClusterDetector(
                dry_run=True,
                rate_limit=50,
                similarity_threshold=0.60,
                min_cluster_size=3,
            )

            assert detector.dry_run is True
            assert detector.rate_limit == 50
            assert detector.similarity_threshold == 0.60
            assert detector.min_cluster_size == 3
