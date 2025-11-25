"""Unit tests for hybrid scheduler.

Tests for T088: Create hybrid scheduler at src/cortexgraph/agents/scheduler.py

The scheduler provides:
1. Programmatic interface for running consolidation agents
2. Event-driven hook (post_save_check) for urgent decay detection
3. Pipeline orchestration with configurable agent order
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


class TestSchedulerInit:
    """Tests for Scheduler initialization."""

    def test_scheduler_init_default(self) -> None:
        """Scheduler initializes with default settings."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()
        assert scheduler.dry_run is False
        assert scheduler.urgent_threshold == 0.10

    def test_scheduler_init_custom_threshold(self) -> None:
        """Scheduler accepts custom urgent threshold."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(urgent_threshold=0.15)
        assert scheduler.urgent_threshold == 0.15

    def test_scheduler_init_dry_run(self) -> None:
        """Scheduler accepts dry_run mode."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)
        assert scheduler.dry_run is True


class TestSchedulerRunAgent:
    """Tests for running individual agents."""

    def test_run_agent_decay(self) -> None:
        """run_agent executes decay analyzer."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch("cortexgraph.agents.decay_analyzer.DecayAnalyzer") as mock_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = []
            mock_class.return_value = mock_agent

            result = scheduler.run_agent("decay")

            mock_class.assert_called_once_with(dry_run=True)
            mock_agent.run.assert_called_once()
            assert result == []

    def test_run_agent_cluster(self) -> None:
        """run_agent executes cluster detector."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch("cortexgraph.agents.cluster_detector.ClusterDetector") as mock_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = []
            mock_class.return_value = mock_agent

            result = scheduler.run_agent("cluster")

            mock_class.assert_called_once_with(dry_run=True)
            assert result == []

    def test_run_agent_merge(self) -> None:
        """run_agent executes semantic merge."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch("cortexgraph.agents.semantic_merge.SemanticMerge") as mock_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = []
            mock_class.return_value = mock_agent

            result = scheduler.run_agent("merge")

            mock_class.assert_called_once_with(dry_run=True)
            assert result == []

    def test_run_agent_promote(self) -> None:
        """run_agent executes LTM promoter."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch("cortexgraph.agents.ltm_promoter.LTMPromoter") as mock_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = []
            mock_class.return_value = mock_agent

            result = scheduler.run_agent("promote")

            mock_class.assert_called_once_with(dry_run=True)
            assert result == []

    def test_run_agent_relations(self) -> None:
        """run_agent executes relationship discovery."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch("cortexgraph.agents.relationship_discovery.RelationshipDiscovery") as mock_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = []
            mock_class.return_value = mock_agent

            result = scheduler.run_agent("relations")

            mock_class.assert_called_once_with(dry_run=True)
            assert result == []

    def test_run_agent_unknown_raises(self) -> None:
        """run_agent raises ValueError for unknown agent."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()

        with pytest.raises(ValueError, match="Unknown agent"):
            scheduler.run_agent("unknown_agent")


class TestSchedulerRunPipeline:
    """Tests for running full consolidation pipeline."""

    def test_run_pipeline_executes_all_agents(self) -> None:
        """run_pipeline executes all agents in order."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch.object(scheduler, "run_agent") as mock_run:
            mock_run.return_value = []

            results = scheduler.run_pipeline()

            # Verify all agents called in order
            assert mock_run.call_count == 5
            calls = [call[0][0] for call in mock_run.call_args_list]
            assert calls == ["decay", "cluster", "merge", "promote", "relations"]
            assert "decay" in results
            assert "cluster" in results
            assert "merge" in results
            assert "promote" in results
            assert "relations" in results

    def test_run_pipeline_returns_results_dict(self) -> None:
        """run_pipeline returns dict mapping agent names to results."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch.object(scheduler, "run_agent") as mock_run:
            mock_run.side_effect = [
                ["decay_result"],
                ["cluster_result"],
                ["merge_result"],
                ["promote_result"],
                ["relations_result"],
            ]

            results = scheduler.run_pipeline()

            assert results["decay"] == ["decay_result"]
            assert results["cluster"] == ["cluster_result"]
            assert results["merge"] == ["merge_result"]
            assert results["promote"] == ["promote_result"]
            assert results["relations"] == ["relations_result"]

    def test_run_pipeline_stops_on_error(self) -> None:
        """run_pipeline stops and raises on first agent error."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with patch.object(scheduler, "run_agent") as mock_run:
            mock_run.side_effect = [
                [],  # decay succeeds
                RuntimeError("Cluster failed"),  # cluster fails
            ]

            with pytest.raises(RuntimeError, match="Cluster failed"):
                scheduler.run_pipeline()

            # Only decay and cluster were attempted
            assert mock_run.call_count == 2


class TestSchedulerPostSaveCheck:
    """Tests for event-driven urgent decay detection."""

    def test_post_save_check_no_action_above_threshold(self) -> None:
        """post_save_check does nothing when score >= threshold."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(urgent_threshold=0.10)

        with patch("cortexgraph.agents.scheduler.calculate_score") as mock_calc:
            mock_calc.return_value = 0.50  # Above threshold

            result = scheduler.post_save_check("memory-123")

            assert result is None

    def test_post_save_check_triggers_urgent_below_threshold(self) -> None:
        """post_save_check triggers urgent processing when score < threshold."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(urgent_threshold=0.10, dry_run=True)

        with (
            patch("cortexgraph.agents.scheduler.calculate_score") as mock_calc,
            patch.object(scheduler, "_handle_urgent_memory") as mock_handle,
        ):
            mock_calc.return_value = 0.08  # Below threshold

            result = scheduler.post_save_check("memory-123")

            mock_handle.assert_called_once_with("memory-123", 0.08)
            assert result is not None

    def test_post_save_check_custom_threshold(self) -> None:
        """post_save_check respects custom urgent threshold."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(urgent_threshold=0.20, dry_run=True)

        with (
            patch("cortexgraph.agents.scheduler.calculate_score") as mock_calc,
            patch.object(scheduler, "_handle_urgent_memory") as mock_handle,
        ):
            mock_calc.return_value = 0.15  # Below 0.20 threshold

            scheduler.post_save_check("memory-456")

            mock_handle.assert_called_once()


class TestSchedulerHandleUrgentMemory:
    """Tests for urgent memory handling."""

    def test_handle_urgent_memory_dry_run(self) -> None:
        """_handle_urgent_memory logs but doesn't act in dry_run mode."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        result = scheduler._handle_urgent_memory("memory-123", 0.05)

        # In dry_run, returns info dict but doesn't create issues
        assert result["memory_id"] == "memory-123"
        assert result["score"] == 0.05
        assert result["dry_run"] is True
        assert result["action"] == "would_flag_urgent"

    def test_handle_urgent_memory_live_mode(self) -> None:
        """_handle_urgent_memory creates urgent flag in live mode."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=False)

        result = scheduler._handle_urgent_memory("memory-789", 0.03)

        # In live mode, returns info about the action taken
        assert result["memory_id"] == "memory-789"
        assert result["score"] == 0.03
        assert result["dry_run"] is False
        assert result["action"] == "flagged_urgent"


class TestSchedulerConstants:
    """Tests for scheduler constants and configuration."""

    def test_agent_order_constant(self) -> None:
        """AGENT_ORDER contains all consolidation agents."""
        from cortexgraph.agents.scheduler import AGENT_ORDER

        assert AGENT_ORDER == ["decay", "cluster", "merge", "promote", "relations"]

    def test_default_urgent_threshold(self) -> None:
        """DEFAULT_URGENT_THRESHOLD is 0.10."""
        from cortexgraph.agents.scheduler import DEFAULT_URGENT_THRESHOLD

        assert DEFAULT_URGENT_THRESHOLD == 0.10


class TestSchedulerGetStorage:
    """Tests for storage access."""

    def test_scheduler_uses_get_db(self) -> None:
        """Scheduler gets storage via get_db for consistency."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()

        with patch("cortexgraph.context.get_db") as mock_get_db:
            mock_storage = MagicMock()
            mock_get_db.return_value = mock_storage

            storage = scheduler.get_storage()

            mock_get_db.assert_called_once()
            assert storage == mock_storage
