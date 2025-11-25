"""Contract tests for DecayAnalyzer (T023-T024).

These tests verify the DecayAnalyzer conforms to the ConsolidationAgent
contract defined in contracts/agent-api.md.

Contract Requirements:
- scan() MUST return list of memory IDs (may be empty)
- scan() MUST NOT modify any data
- process_item() MUST return DecayResult or raise exception
- If dry_run=True, process_item() MUST NOT modify any data
- process_item() SHOULD complete within 5 seconds
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import DecayAction, DecayResult, Urgency

if TYPE_CHECKING:
    from cortexgraph.agents.decay_analyzer import DecayAnalyzer


# =============================================================================
# Contract Test Fixtures
# =============================================================================


# Score mapping used by mock_compute_score
MOCK_SCORES = {
    "mem-critical": 0.05,  # Critical - near forget
    "mem-danger": 0.20,  # Danger zone
    "mem-low": 0.30,  # Low urgency
    "mem-healthy": 0.75,  # Healthy - should NOT be scanned
}


def mock_compute_score(memory) -> float:
    """Mock score computation to return controlled values."""
    return MOCK_SCORES.get(memory.id, 0.5)


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock storage with test memories."""
    storage = MagicMock()
    # Create test memories with various decay scores
    storage.memories = {
        "mem-critical": MagicMock(
            id="mem-critical",
            content="Critical memory",
            last_used=int(time.time()) - 86400 * 7,  # 7 days ago
            use_count=1,
            strength=1.0,
        ),
        "mem-danger": MagicMock(
            id="mem-danger",
            content="Danger zone memory",
            last_used=int(time.time()) - 86400 * 3,  # 3 days ago
            use_count=2,
            strength=1.0,
        ),
        "mem-low": MagicMock(
            id="mem-low",
            content="Low urgency memory",
            last_used=int(time.time()) - 86400,  # 1 day ago
            use_count=3,
            strength=1.0,
        ),
        "mem-healthy": MagicMock(
            id="mem-healthy",
            content="Healthy memory",
            last_used=int(time.time()),
            use_count=10,
            strength=1.5,
        ),
    }
    return storage


@pytest.fixture
def decay_analyzer(mock_storage: MagicMock) -> DecayAnalyzer:
    """Create DecayAnalyzer with mock storage and controlled score computation."""
    from cortexgraph.agents.decay_analyzer import DecayAnalyzer

    with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
        analyzer = DecayAnalyzer(dry_run=True)
        analyzer._storage = mock_storage
        # Patch _compute_score to return controlled values
        analyzer._compute_score = mock_compute_score
        return analyzer


# =============================================================================
# T023: Contract Test - scan() Returns Memory IDs
# =============================================================================


class TestDecayAnalyzerScanContract:
    """Contract tests for DecayAnalyzer.scan() method (T023)."""

    def test_scan_returns_list(self, decay_analyzer: DecayAnalyzer) -> None:
        """scan() MUST return a list."""
        result = decay_analyzer.scan()
        assert isinstance(result, list)

    def test_scan_returns_string_ids(self, decay_analyzer: DecayAnalyzer) -> None:
        """scan() MUST return list of string memory IDs."""
        result = decay_analyzer.scan()
        for item in result:
            assert isinstance(item, str)

    def test_scan_may_return_empty(self, mock_storage: MagicMock) -> None:
        """scan() MAY return empty list when no memories need triage."""
        from cortexgraph.agents.decay_analyzer import DecayAnalyzer

        # All memories healthy
        mock_storage.memories = {
            "mem-healthy": MagicMock(id="mem-healthy", score=0.9),
        }
        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = mock_storage
            result = analyzer.scan()
            assert result == []

    def test_scan_only_returns_low_score_memories(
        self, decay_analyzer: DecayAnalyzer, mock_storage: MagicMock
    ) -> None:
        """scan() MUST only return memories with score < threshold (0.35)."""
        result = decay_analyzer.scan()

        # Should include mem-critical (0.05), mem-danger (0.20), mem-low (0.30)
        # Should NOT include mem-healthy (0.75)
        assert "mem-healthy" not in result
        assert len(result) == 3

    def test_scan_does_not_modify_data(
        self, decay_analyzer: DecayAnalyzer, mock_storage: MagicMock
    ) -> None:
        """scan() MUST NOT modify any data."""
        # Take snapshot before
        original_scores = {k: v.score for k, v in mock_storage.memories.items()}

        # Run scan
        decay_analyzer.scan()

        # Verify no changes
        for mem_id, original_score in original_scores.items():
            assert mock_storage.memories[mem_id].score == original_score

    def test_scan_is_subclass_of_consolidation_agent(self, decay_analyzer: DecayAnalyzer) -> None:
        """DecayAnalyzer MUST inherit from ConsolidationAgent."""
        assert isinstance(decay_analyzer, ConsolidationAgent)


# =============================================================================
# T024: Contract Test - process_item() Returns DecayResult
# =============================================================================


class TestDecayAnalyzerProcessItemContract:
    """Contract tests for DecayAnalyzer.process_item() method (T024)."""

    def test_process_item_returns_decay_result(self, decay_analyzer: DecayAnalyzer) -> None:
        """process_item() MUST return DecayResult."""
        result = decay_analyzer.process_item("mem-critical")
        assert isinstance(result, DecayResult)

    def test_process_item_result_has_required_fields(self, decay_analyzer: DecayAnalyzer) -> None:
        """DecayResult MUST have all required fields."""
        result = decay_analyzer.process_item("mem-danger")

        # Required fields
        assert hasattr(result, "memory_id")
        assert hasattr(result, "score")
        assert hasattr(result, "urgency")
        assert hasattr(result, "action")

        # Types
        assert isinstance(result.memory_id, str)
        assert isinstance(result.score, float)
        assert isinstance(result.urgency, Urgency)
        assert isinstance(result.action, DecayAction)

    def test_process_item_score_in_range(self, decay_analyzer: DecayAnalyzer) -> None:
        """DecayResult.score MUST be in range [0.0, 1.0]."""
        result = decay_analyzer.process_item("mem-critical")
        assert 0.0 <= result.score <= 1.0

    def test_process_item_memory_id_matches_input(self, decay_analyzer: DecayAnalyzer) -> None:
        """DecayResult.memory_id MUST match input memory_id."""
        result = decay_analyzer.process_item("mem-danger")
        assert result.memory_id == "mem-danger"

    def test_process_item_raises_on_invalid_id(self, decay_analyzer: DecayAnalyzer) -> None:
        """process_item() MUST raise exception for invalid memory ID."""
        with pytest.raises((ValueError, KeyError, RuntimeError)):
            decay_analyzer.process_item("nonexistent-memory")

    def test_process_item_dry_run_no_side_effects(self, mock_storage: MagicMock) -> None:
        """If dry_run=True, process_item() MUST NOT modify any data."""
        from cortexgraph.agents.decay_analyzer import DecayAnalyzer

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = mock_storage

            # Track calls that would modify data
            mock_storage.update_memory = MagicMock()
            mock_storage.delete_memory = MagicMock()

            analyzer.process_item("mem-critical")

            # In dry_run mode, no modifications should occur
            mock_storage.update_memory.assert_not_called()
            mock_storage.delete_memory.assert_not_called()

    def test_process_item_completes_within_timeout(self, decay_analyzer: DecayAnalyzer) -> None:
        """process_item() SHOULD complete within 5 seconds."""
        start = time.time()
        decay_analyzer.process_item("mem-critical")
        elapsed = time.time() - start

        assert elapsed < 5.0, f"process_item took {elapsed:.2f}s (limit: 5s)"


# =============================================================================
# Contract Integration Tests
# =============================================================================


class TestDecayAnalyzerFullContract:
    """Integration tests verifying full contract compliance."""

    def test_run_method_uses_scan_and_process_item(self, decay_analyzer: DecayAnalyzer) -> None:
        """run() MUST call scan() then process_item() for each result."""
        results = decay_analyzer.run()

        # Should have processed all scanned memories
        assert len(results) == 3  # mem-critical, mem-danger, mem-low

        # All results should be DecayResult
        for result in results:
            assert isinstance(result, DecayResult)

    def test_run_respects_rate_limit(self, mock_storage: MagicMock) -> None:
        """run() MUST respect rate_limit setting (adds delays, doesn't cap count)."""
        from cortexgraph.agents.decay_analyzer import DecayAnalyzer

        # Create a small number of memories to avoid long test
        mock_storage.memories = {}  # Clear existing memories
        for i in range(3):
            mock_storage.memories[f"mem-{i}"] = MagicMock(
                id=f"mem-{i}",
                content=f"Memory {i}",
                use_count=1,
                strength=1.0,
            )

        def rate_test_scores(memory) -> float:
            """Return danger zone score for all test memories."""
            return 0.10  # All in danger zone

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=mock_storage):
            analyzer = DecayAnalyzer(dry_run=True, rate_limit=100)  # High limit
            analyzer._storage = mock_storage
            analyzer._compute_score = rate_test_scores

            # Rate limiting doesn't cap results - it adds delays
            # All memories should still be processed
            results = analyzer.run()
            assert len(results) == 3  # All should be processed

    def test_run_handles_errors_gracefully(
        self, decay_analyzer: DecayAnalyzer, mock_storage: MagicMock
    ) -> None:
        """run() MUST handle errors per-item without aborting all."""
        # Add a memory that will cause an error during score computation
        mock_storage.memories["mem-error"] = MagicMock(
            id="mem-error",
            use_count=None,  # Invalid - will cause error during score computation
            strength=1.0,
        )

        # Update _compute_score to raise for mem-error
        original_scores = dict(MOCK_SCORES)
        original_scores["mem-error"] = 0.10  # Would be scanned if no error

        def score_with_error(memory) -> float:
            if memory.id == "mem-error":
                raise TypeError("Cannot compute score for invalid memory")
            return original_scores.get(memory.id, 0.5)

        # Apply the error-causing score function
        decay_analyzer._compute_score = score_with_error

        # Should not raise - should skip error and continue
        results = decay_analyzer.run()

        # The 3 original memories should still succeed
        assert len(results) >= 3
