"""Unit tests for DecayAnalyzer (T025-T026).

Tests the urgency classification and action recommendation logic
in isolation from storage and beads integration.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.decay_analyzer import (
    SCAN_THRESHOLD,
    URGENCY_HIGH_THRESHOLD,
    URGENCY_MEDIUM_THRESHOLD,
    DecayAnalyzer,
)
from cortexgraph.agents.models import DecayAction, Urgency

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def analyzer() -> DecayAnalyzer:
    """Create DecayAnalyzer with mock storage."""
    mock_storage = MagicMock()
    mock_storage.memories = {}

    with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
        a = DecayAnalyzer(dry_run=True)
        a._storage = mock_storage
        return a


# =============================================================================
# T025: Unit Tests for Urgency Classification
# =============================================================================


class TestUrgencyClassification:
    """Tests for _classify_urgency() method (T025)."""

    def test_high_urgency_near_zero(self, analyzer: DecayAnalyzer) -> None:
        """Score near 0 should be HIGH urgency."""
        assert analyzer._classify_urgency(0.01) == Urgency.HIGH
        assert analyzer._classify_urgency(0.05) == Urgency.HIGH
        assert analyzer._classify_urgency(0.09) == Urgency.HIGH

    def test_high_urgency_boundary(self, analyzer: DecayAnalyzer) -> None:
        """Score exactly at HIGH threshold boundary."""
        # Just below threshold - HIGH
        assert analyzer._classify_urgency(0.099) == Urgency.HIGH
        # At threshold - MEDIUM (boundary is exclusive)
        assert analyzer._classify_urgency(URGENCY_HIGH_THRESHOLD) == Urgency.MEDIUM

    def test_medium_urgency_range(self, analyzer: DecayAnalyzer) -> None:
        """Scores in 0.10-0.25 range should be MEDIUM urgency."""
        assert analyzer._classify_urgency(0.10) == Urgency.MEDIUM
        assert analyzer._classify_urgency(0.15) == Urgency.MEDIUM
        assert analyzer._classify_urgency(0.20) == Urgency.MEDIUM
        assert analyzer._classify_urgency(0.24) == Urgency.MEDIUM

    def test_medium_urgency_boundary(self, analyzer: DecayAnalyzer) -> None:
        """Score exactly at MEDIUM threshold boundary."""
        # Just below threshold - MEDIUM
        assert analyzer._classify_urgency(0.249) == Urgency.MEDIUM
        # At threshold - LOW (boundary is exclusive)
        assert analyzer._classify_urgency(URGENCY_MEDIUM_THRESHOLD) == Urgency.LOW

    def test_low_urgency_range(self, analyzer: DecayAnalyzer) -> None:
        """Scores in 0.25-0.35 range should be LOW urgency."""
        assert analyzer._classify_urgency(0.25) == Urgency.LOW
        assert analyzer._classify_urgency(0.30) == Urgency.LOW
        assert analyzer._classify_urgency(0.34) == Urgency.LOW

    def test_low_urgency_at_scan_threshold(self, analyzer: DecayAnalyzer) -> None:
        """Score at scan threshold is still LOW urgency."""
        # Just below scan threshold - LOW
        assert analyzer._classify_urgency(0.349) == Urgency.LOW
        # At scan threshold - technically LOW (but won't be scanned)
        assert analyzer._classify_urgency(SCAN_THRESHOLD) == Urgency.LOW

    def test_urgency_thresholds_documented(self) -> None:
        """Verify thresholds match documentation."""
        assert URGENCY_HIGH_THRESHOLD == 0.10
        assert URGENCY_MEDIUM_THRESHOLD == 0.25
        assert SCAN_THRESHOLD == 0.35


# =============================================================================
# T026: Unit Tests for Action Recommendation
# =============================================================================


class TestActionRecommendation:
    """Tests for _recommend_action() method (T026)."""

    def test_gc_when_near_zero_low_use(self, analyzer: DecayAnalyzer) -> None:
        """Very low score with low use_count should recommend GC."""
        memory = MagicMock(use_count=1, strength=1.0)
        assert analyzer._recommend_action(0.04, memory) == DecayAction.GC

    def test_reinforce_when_near_zero_high_use(self, analyzer: DecayAnalyzer) -> None:
        """Very low score but high use_count should recommend REINFORCE."""
        memory = MagicMock(use_count=5, strength=1.0)
        assert analyzer._recommend_action(0.04, memory) == DecayAction.REINFORCE

    def test_gc_when_high_urgency_low_use(self, analyzer: DecayAnalyzer) -> None:
        """High urgency (< 0.10) with low use should recommend GC."""
        memory = MagicMock(use_count=2, strength=1.0)
        assert analyzer._recommend_action(0.08, memory) == DecayAction.GC

    def test_reinforce_when_high_urgency_moderate_use(self, analyzer: DecayAnalyzer) -> None:
        """High urgency with moderate use should recommend REINFORCE."""
        memory = MagicMock(use_count=3, strength=1.0)
        assert analyzer._recommend_action(0.08, memory) == DecayAction.REINFORCE

    def test_consolidate_when_medium_urgency(self, analyzer: DecayAnalyzer) -> None:
        """Medium urgency (0.10-0.20) should recommend CONSOLIDATE."""
        memory = MagicMock(use_count=2, strength=1.0)
        assert analyzer._recommend_action(0.15, memory) == DecayAction.CONSOLIDATE
        assert analyzer._recommend_action(0.19, memory) == DecayAction.CONSOLIDATE

    def test_promote_when_low_urgency_high_strength(self, analyzer: DecayAnalyzer) -> None:
        """Low urgency (>= 0.20) with high strength should recommend PROMOTE."""
        memory = MagicMock(use_count=5, strength=1.5)
        assert analyzer._recommend_action(0.25, memory) == DecayAction.PROMOTE

    def test_reinforce_when_low_urgency_normal_strength(self, analyzer: DecayAnalyzer) -> None:
        """Low urgency with normal strength should recommend REINFORCE."""
        memory = MagicMock(use_count=5, strength=1.0)
        assert analyzer._recommend_action(0.25, memory) == DecayAction.REINFORCE

    def test_reinforce_is_default_safe_action(self, analyzer: DecayAnalyzer) -> None:
        """REINFORCE should be default when no clear recommendation."""
        memory = MagicMock(use_count=10, strength=1.4)  # Just below promote threshold
        assert analyzer._recommend_action(0.30, memory) == DecayAction.REINFORCE

    def test_action_uses_use_count_attribute(self, analyzer: DecayAnalyzer) -> None:
        """Action should read use_count from memory."""
        memory = MagicMock(use_count=0, strength=1.0)
        # With 0 use_count at low score, should GC
        assert analyzer._recommend_action(0.05, memory) == DecayAction.GC

    def test_action_uses_strength_attribute(self, analyzer: DecayAnalyzer) -> None:
        """Action should read strength from memory."""
        memory = MagicMock(use_count=5, strength=2.0)  # High strength
        # High strength at low urgency should promote
        assert analyzer._recommend_action(0.30, memory) == DecayAction.PROMOTE

    def test_action_handles_missing_attributes(self, analyzer: DecayAnalyzer) -> None:
        """Action should handle memories missing use_count/strength."""
        memory = MagicMock(spec=[])  # No attributes

        # Should default to safe values and not crash
        action = analyzer._recommend_action(0.30, memory)
        assert action in DecayAction


# =============================================================================
# Additional Unit Tests for DecayAnalyzer
# =============================================================================


class TestDecayAnalyzerScan:
    """Unit tests for scan() filtering logic.

    Note: These tests mock _compute_score to control the score values,
    isolating the filtering logic from score computation.
    """

    def test_scan_filters_by_threshold(self) -> None:
        """scan() should only return memories below threshold."""
        mock_storage = MagicMock()
        mock_storage.memories = {
            "below": MagicMock(id="below"),
            "above": MagicMock(id="above"),
            "at_threshold": MagicMock(id="at_threshold"),
        }

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = mock_storage

            # Mock _compute_score to return controlled values
            def score_for_memory(memory):
                scores = {"below": 0.20, "above": 0.50, "at_threshold": SCAN_THRESHOLD}
                return scores.get(memory.id, 0.5)

            with patch.object(analyzer, "_compute_score", side_effect=score_for_memory):
                result = analyzer.scan()

            assert "below" in result
            assert "above" not in result
            assert "at_threshold" not in result

    def test_scan_with_custom_threshold(self) -> None:
        """scan() should use custom threshold."""
        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem1": MagicMock(id="mem1"),
            "mem2": MagicMock(id="mem2"),
        }

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True, scan_threshold=0.50)
            analyzer._storage = mock_storage

            def score_for_memory(memory):
                scores = {"mem1": 0.40, "mem2": 0.60}
                return scores.get(memory.id, 0.5)

            with patch.object(analyzer, "_compute_score", side_effect=score_for_memory):
                result = analyzer.scan()

            assert "mem1" in result
            assert "mem2" not in result

    def test_scan_handles_invalid_memory(self) -> None:
        """scan() should skip memories that fail score computation."""
        mock_storage = MagicMock()
        mock_storage.memories = {
            "valid": MagicMock(id="valid"),
            "invalid": MagicMock(id="invalid"),
        }

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = mock_storage

            def score_for_memory(memory):
                if memory.id == "invalid":
                    raise TypeError("Invalid memory data")
                return 0.20  # Valid memory below threshold

            with patch.object(analyzer, "_compute_score", side_effect=score_for_memory):
                result = analyzer.scan()

            assert "valid" in result
            assert "invalid" not in result


class TestDecayAnalyzerProcessItem:
    """Unit tests for process_item() integration.

    Note: These tests mock _compute_score to control the score values,
    isolating the processing logic from score computation.
    """

    def test_process_item_integrates_urgency_and_action(self) -> None:
        """process_item() should combine urgency and action correctly."""
        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem": MagicMock(id="mem", use_count=2, strength=1.0),
        }

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = mock_storage

            # Mock _compute_score to return a controlled value
            with patch.object(analyzer, "_compute_score", return_value=0.15):
                result = analyzer.process_item("mem")

            # Score 0.15 = MEDIUM urgency, CONSOLIDATE action
            assert result.urgency == Urgency.MEDIUM
            assert result.action == DecayAction.CONSOLIDATE

    def test_process_item_no_beads_issue_in_dry_run(self) -> None:
        """process_item() should not create beads issues in dry_run mode."""
        mock_storage = MagicMock()
        mock_storage.memories = {
            "urgent": MagicMock(id="urgent", use_count=1, strength=1.0),
        }

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            with patch(
                "cortexgraph.agents.decay_analyzer.DecayAnalyzer._create_beads_issue"
            ) as mock_beads:
                analyzer = DecayAnalyzer(dry_run=True)
                analyzer._storage = mock_storage

                # Mock _compute_score to return HIGH urgency score
                with patch.object(analyzer, "_compute_score", return_value=0.05):
                    result = analyzer.process_item("urgent")

                # In dry_run, should not call beads
                mock_beads.assert_not_called()
                assert result.beads_issue_id is None


class TestDecayAnalyzerStats:
    """Unit tests for stats and counters.

    Note: These tests mock _compute_score to control the score values,
    isolating the stats logic from score computation.
    """

    def test_stats_after_run(self) -> None:
        """get_stats() should return correct counts after run."""
        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem1": MagicMock(id="mem1", use_count=1, strength=1.0),
            "mem2": MagicMock(id="mem2", use_count=1, strength=1.0),
        }

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = mock_storage

            # Mock _compute_score to return scores below threshold
            def score_for_memory(memory):
                scores = {"mem1": 0.20, "mem2": 0.25}
                return scores.get(memory.id, 0.5)

            with patch.object(analyzer, "_compute_score", side_effect=score_for_memory):
                analyzer.run()
            stats = analyzer.get_stats()

            assert stats["processed"] == 2
            assert stats["errors"] == 0
