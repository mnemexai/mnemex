"""Integration tests for DecayAnalyzer (T027).

End-to-end tests with real (test) storage to verify the full
decay triage workflow.

Note: Decay scores are computed dynamically based on use_count, last_used,
and strength. To get specific score ranges, we set last_used far in the past
and use_count low for low scores, or recent last_used and high use_count
for high scores.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cortexgraph.agents.decay_analyzer import DecayAnalyzer
from cortexgraph.agents.models import DecayAction, DecayResult, Urgency
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
    """Create real JSONL storage with test data.

    Creates memories with specific use_count/last_used values that will
    result in desired decay scores when computed.
    """
    storage = JSONLStorage(str(temp_storage_dir))
    now = int(time.time())

    # To get specific decay score ranges, we manipulate last_used.
    # With default decay (3-day half-life), score decays roughly:
    # - 3 days ago: ~0.5
    # - 7 days ago: ~0.25
    # - 10+ days ago: < 0.1

    # Critical memory - very old, low use = very low score
    critical_memory = Memory(
        id="mem-critical",
        content="Critical preference that should be reinforced",
        entities=["Test User"],
        created_at=now - 86400 * 30,  # 30 days ago
        last_used=now - 86400 * 14,  # 14 days ago
        use_count=0,  # Never used
        strength=1.0,
    )

    # Medium-old memory - moderate decay
    danger_memory = Memory(
        id="mem-danger",
        content="Database configuration details",
        entities=["PostgreSQL"],
        created_at=now - 86400 * 10,  # 10 days ago
        last_used=now - 86400 * 6,  # 6 days ago
        use_count=1,  # Used once
        strength=1.0,
    )

    # Recently used memory - low decay
    low_memory = Memory(
        id="mem-low",
        content="Project meeting notes",
        entities=["Team"],
        created_at=now - 86400 * 5,  # 5 days ago
        last_used=now - 86400 * 3,  # 3 days ago
        use_count=2,  # Used twice
        strength=1.0,
    )

    # Healthy memory - recent and high use = high score
    healthy_memory = Memory(
        id="mem-healthy",
        content="Recent API design decision",
        entities=["REST", "GraphQL"],
        created_at=now - 86400,  # 1 day ago
        last_used=now - 3600,  # 1 hour ago
        use_count=10,  # Heavily used
        strength=1.5,
    )

    # Add memories to storage
    storage.memories = {
        "mem-critical": critical_memory,
        "mem-danger": danger_memory,
        "mem-low": low_memory,
        "mem-healthy": healthy_memory,
    }

    return storage


@pytest.fixture
def decay_analyzer_with_storage(test_storage: JSONLStorage) -> DecayAnalyzer:
    """Create DecayAnalyzer with real test storage."""
    with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=test_storage):
        analyzer = DecayAnalyzer(dry_run=True)
        analyzer._storage = test_storage
        return analyzer


# =============================================================================
# T027: Integration Test - End-to-End Decay Triage
# =============================================================================


class TestDecayTriageEndToEnd:
    """End-to-end integration tests for decay triage workflow."""

    def test_full_triage_workflow(
        self, decay_analyzer_with_storage: DecayAnalyzer, test_storage: JSONLStorage
    ) -> None:
        """Test complete decay triage from scan to results."""
        analyzer = decay_analyzer_with_storage

        # Execute full run
        results = analyzer.run()

        # All results should be DecayResult
        for result in results:
            assert isinstance(result, DecayResult)

        # Healthy memory (recent, high use) should NOT be in results
        result_ids = {r.memory_id for r in results}
        assert "mem-healthy" not in result_ids

        # At least some decayed memories should be found
        assert len(results) >= 1

    def test_urgency_based_on_computed_score(
        self, decay_analyzer_with_storage: DecayAnalyzer, test_storage: JSONLStorage
    ) -> None:
        """Test urgency is classified based on computed decay scores."""
        analyzer = decay_analyzer_with_storage
        results = analyzer.run()

        # Get result for critical memory (14 days old, never used)
        critical_results = [r for r in results if r.memory_id == "mem-critical"]
        if critical_results:
            # Very old, unused memory should have very low score
            assert critical_results[0].score < 0.35
            # With such low score, urgency should be HIGH or MEDIUM
            assert critical_results[0].urgency in (Urgency.HIGH, Urgency.MEDIUM)

    def test_action_based_on_memory_state(self, decay_analyzer_with_storage: DecayAnalyzer) -> None:
        """Test actions are recommended based on memory state."""
        analyzer = decay_analyzer_with_storage
        results = analyzer.run()

        # All results should have valid actions
        for result in results:
            assert result.action in DecayAction

    def test_score_in_valid_range(self, decay_analyzer_with_storage: DecayAnalyzer) -> None:
        """Test computed scores are in valid range [0, 1]."""
        analyzer = decay_analyzer_with_storage
        results = analyzer.run()

        for result in results:
            assert 0.0 <= result.score <= 1.0, f"Score {result.score} out of range"

    def test_dry_run_no_mutations(
        self, decay_analyzer_with_storage: DecayAnalyzer, test_storage: JSONLStorage
    ) -> None:
        """Test dry_run mode doesn't mutate storage."""
        analyzer = decay_analyzer_with_storage

        # Capture original state (use_count and last_used are the key fields)
        original_use_counts = {mid: m.use_count for mid, m in test_storage.memories.items()}
        original_last_used = {mid: m.last_used for mid, m in test_storage.memories.items()}

        # Run analyzer
        analyzer.run()

        # Verify no mutations
        for mid, original_count in original_use_counts.items():
            assert test_storage.memories[mid].use_count == original_count
        for mid, original_time in original_last_used.items():
            assert test_storage.memories[mid].last_used == original_time

    def test_stats_reflect_run(self, decay_analyzer_with_storage: DecayAnalyzer) -> None:
        """Test statistics are updated correctly after run."""
        analyzer = decay_analyzer_with_storage

        # Initial stats should be zero
        initial_stats = analyzer.get_stats()
        assert initial_stats["processed"] == 0

        # Run analyzer
        results = analyzer.run()

        # Stats should reflect processed count
        final_stats = analyzer.get_stats()
        assert final_stats["processed"] == len(results)
        assert final_stats["errors"] == 0


class TestDecayAnalyzerEdgeCases:
    """Integration tests for edge cases."""

    def test_empty_storage(self, temp_storage_dir: Path) -> None:
        """Test behavior with empty storage."""
        storage = JSONLStorage(str(temp_storage_dir))
        storage.memories = {}

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = storage

            results = analyzer.run()

            assert results == []
            assert analyzer.get_stats()["processed"] == 0

    def test_all_healthy_memories(self, temp_storage_dir: Path) -> None:
        """Test behavior when all memories are healthy (recent, high use)."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Very healthy memory - recent and heavily used
        healthy = Memory(
            id="healthy",
            content="Very healthy memory",
            created_at=now - 3600,  # 1 hour ago
            last_used=now - 60,  # 1 minute ago
            use_count=50,  # Heavily used
            strength=2.0,
        )

        storage.memories = {"healthy": healthy}

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = storage

            results = analyzer.run()

            # Healthy memory should not be scanned (score too high)
            assert results == []

    def test_memory_with_high_use_count(self, temp_storage_dir: Path) -> None:
        """Test heavily used memory gets REINFORCE even at low computed score."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Memory that's old but heavily used
        heavily_used = Memory(
            id="heavy",
            content="Frequently accessed memory",
            created_at=now - 86400 * 30,  # 30 days old
            last_used=now - 86400 * 10,  # 10 days since last use
            use_count=20,  # Very high use count boosts score
            strength=1.0,
        )

        storage.memories = {"heavy": heavily_used}

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=storage):
            analyzer = DecayAnalyzer(dry_run=True)
            analyzer._storage = storage

            results = analyzer.run()

            # If scanned (score < 0.35), high use count should favor REINFORCE
            if results:
                assert results[0].action == DecayAction.REINFORCE

    def test_custom_threshold(self, temp_storage_dir: Path) -> None:
        """Test custom scan threshold captures more or fewer memories."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Memory with moderate decay
        moderate = Memory(
            id="moderate",
            content="Moderately decayed",
            created_at=now - 86400 * 5,
            last_used=now - 86400 * 4,  # 4 days ago
            use_count=1,
            strength=1.0,
        )

        storage.memories = {"moderate": moderate}

        with patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=storage):
            # High threshold - should capture the memory
            analyzer_high = DecayAnalyzer(dry_run=True, scan_threshold=0.50)
            analyzer_high._storage = storage
            results_high = analyzer_high.run()

            # Very low threshold - might not capture it
            analyzer_low = DecayAnalyzer(dry_run=True, scan_threshold=0.05)
            analyzer_low._storage = storage
            results_low = analyzer_low.run()

            # Higher threshold should capture more (or same) memories
            assert len(results_high) >= len(results_low)
