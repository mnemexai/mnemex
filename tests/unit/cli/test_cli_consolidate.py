"""Unit tests for CLI consolidate commands (T091).

These tests verify the consolidation CLI interface including:
- run command with agent selection
- run --all for full pipeline
- status command for queue inspection
- process command for specific issue
- --dry-run and --json global options
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    return {
        "decay": MagicMock(),
        "cluster": MagicMock(),
        "merge": MagicMock(),
        "promote": MagicMock(),
        "relations": MagicMock(),
    }


@pytest.fixture
def mock_storage():
    """Create mock storage for testing."""
    storage = MagicMock()
    storage.connect = MagicMock()
    return storage


# =============================================================================
# T091: Unit Tests - CLI Run Command
# =============================================================================


class TestCLIRunCommand:
    """Unit tests for the 'run' command."""

    def test_run_single_agent_decay(self, mock_agents: dict) -> None:
        """run decay - runs only DecayAnalyzer."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run(agent="decay", dry_run=True, json_output=False)

            # Should return success
            assert result == 0
            # Should have called run() on decay agent
            mock_agents["decay"].run.assert_called_once()

    def test_run_single_agent_cluster(self, mock_agents: dict) -> None:
        """run cluster - runs only ClusterDetector."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run(agent="cluster", dry_run=True, json_output=False)

            assert result == 0
            mock_agents["cluster"].run.assert_called_once()

    def test_run_single_agent_merge(self, mock_agents: dict) -> None:
        """run merge - runs only SemanticMerge."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run(agent="merge", dry_run=True, json_output=False)

            assert result == 0
            mock_agents["merge"].run.assert_called_once()

    def test_run_single_agent_promote(self, mock_agents: dict) -> None:
        """run promote - runs only LTMPromoter."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run(agent="promote", dry_run=True, json_output=False)

            assert result == 0
            mock_agents["promote"].run.assert_called_once()

    def test_run_single_agent_relations(self, mock_agents: dict) -> None:
        """run relations - runs only RelationshipDiscovery."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run(agent="relations", dry_run=True, json_output=False)

            assert result == 0
            mock_agents["relations"].run.assert_called_once()

    def test_run_invalid_agent_returns_error(self) -> None:
        """run invalid_agent - returns error code."""
        from cortexgraph.cli.consolidate import cmd_run

        result = cmd_run(agent="invalid_agent", dry_run=True, json_output=False)

        assert result != 0  # Non-zero = error

    def test_run_passes_dry_run_to_agent(self, mock_agents: dict) -> None:
        """run --dry-run passes dry_run=True to agent."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ) as mock_get:
            cmd_run(agent="decay", dry_run=True, json_output=False)

            # get_agent should be called with dry_run=True
            mock_get.assert_called_with("decay", dry_run=True)


class TestCLIRunAllCommand:
    """Unit tests for the 'run --all' command."""

    def test_run_all_executes_all_agents(self, mock_agents: dict) -> None:
        """run --all - executes all agents in order."""
        from cortexgraph.cli.consolidate import cmd_run_all

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run_all(dry_run=True, json_output=False)

            assert result == 0
            # All agents should have been run
            for agent in mock_agents.values():
                agent.run.assert_called_once()

    def test_run_all_correct_order(self, mock_agents: dict) -> None:
        """run --all - executes agents in correct order (decay -> cluster -> merge -> promote -> relations)."""
        from cortexgraph.cli.consolidate import cmd_run_all

        call_order = []

        def track_agent(name: str, **kwargs) -> MagicMock:
            agent = mock_agents[name]
            agent.run.side_effect = lambda: call_order.append(name)
            return agent

        with patch("cortexgraph.cli.consolidate.get_agent", side_effect=track_agent):
            cmd_run_all(dry_run=True, json_output=False)

            # Order matters for pipeline
            expected_order = ["decay", "cluster", "merge", "promote", "relations"]
            assert call_order == expected_order

    def test_run_all_stops_on_error(self, mock_agents: dict) -> None:
        """run --all - stops if an agent fails."""
        from cortexgraph.cli.consolidate import cmd_run_all

        # Make cluster agent raise an exception
        mock_agents["cluster"].run.side_effect = RuntimeError("Cluster failed")

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            result = cmd_run_all(dry_run=True, json_output=False)

            # Should return error
            assert result != 0
            # Decay should have run, but merge/promote/relations should not
            mock_agents["decay"].run.assert_called_once()
            mock_agents["cluster"].run.assert_called_once()
            mock_agents["merge"].run.assert_not_called()


# =============================================================================
# T091: Unit Tests - CLI Status Command
# =============================================================================


class TestCLIStatusCommand:
    """Unit tests for the 'status' command."""

    def test_status_returns_queue_info(self) -> None:
        """status - returns current queue information."""
        from cortexgraph.cli.consolidate import cmd_status

        mock_queue = {
            "pending": 5,
            "in_progress": 2,
            "completed": 10,
            "failed": 1,
        }

        with patch(
            "cortexgraph.cli.consolidate.get_queue_status",
            return_value=mock_queue,
        ):
            result, output = cmd_status(json_output=False)

            assert result == 0
            assert "pending" in output.lower() or "5" in output

    def test_status_json_output(self) -> None:
        """status --json - returns JSON formatted output."""
        from cortexgraph.cli.consolidate import cmd_status

        mock_queue = {
            "pending": 5,
            "in_progress": 2,
            "completed": 10,
            "failed": 1,
        }

        with patch(
            "cortexgraph.cli.consolidate.get_queue_status",
            return_value=mock_queue,
        ):
            result, output = cmd_status(json_output=True)

            assert result == 0
            # Should be valid JSON
            parsed = json.loads(output)
            assert parsed["pending"] == 5
            assert parsed["in_progress"] == 2


class TestCLIProcessCommand:
    """Unit tests for the 'process' command."""

    def test_process_specific_issue(self) -> None:
        """process <issue_id> - processes a specific beads issue."""
        from cortexgraph.cli.consolidate import cmd_process

        mock_result = {
            "success": True,
            "issue_id": "cortexgraph-abc",
            "action": "merged",
        }

        with patch(
            "cortexgraph.cli.consolidate.process_issue",
            return_value=mock_result,
        ):
            result = cmd_process(issue_id="cortexgraph-abc", dry_run=False, json_output=False)

            assert result == 0

    def test_process_invalid_issue_returns_error(self) -> None:
        """process <invalid_id> - returns error for non-existent issue."""
        from cortexgraph.cli.consolidate import cmd_process

        with patch(
            "cortexgraph.cli.consolidate.process_issue",
            side_effect=ValueError("Issue not found"),
        ):
            result = cmd_process(issue_id="nonexistent-123", dry_run=False, json_output=False)

            assert result != 0

    def test_process_dry_run(self) -> None:
        """process --dry-run - previews without executing."""
        from cortexgraph.cli.consolidate import cmd_process

        mock_result = {
            "success": True,
            "dry_run": True,
            "would_do": "merge memories",
        }

        with patch(
            "cortexgraph.cli.consolidate.process_issue",
            return_value=mock_result,
        ) as mock_process:
            result = cmd_process(issue_id="cortexgraph-abc", dry_run=True, json_output=False)

            assert result == 0
            mock_process.assert_called_with("cortexgraph-abc", dry_run=True)


# =============================================================================
# T091: Unit Tests - CLI Global Options
# =============================================================================


class TestCLIGlobalOptions:
    """Unit tests for global CLI options (--dry-run, --json)."""

    def test_dry_run_flag_propagates(self, mock_agents: dict) -> None:
        """--dry-run flag propagates to all operations."""
        from cortexgraph.cli.consolidate import cmd_run

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ) as mock_get:
            cmd_run(agent="decay", dry_run=True, json_output=False)

            mock_get.assert_called_with("decay", dry_run=True)

    def test_json_flag_formats_output(self, mock_agents: dict) -> None:
        """--json flag formats all output as JSON."""
        from cortexgraph.cli.consolidate import cmd_run

        mock_agents["decay"].run.return_value = [
            MagicMock(to_dict=lambda: {"id": "test", "status": "analyzed"})
        ]

        with patch(
            "cortexgraph.cli.consolidate.get_agent",
            side_effect=lambda name, **kwargs: mock_agents[name],
        ):
            # This should format output as JSON (captured via stdout)
            result = cmd_run(agent="decay", dry_run=True, json_output=True)

            assert result == 0


# =============================================================================
# T091: Unit Tests - CLI Entry Point
# =============================================================================


class TestCLIEntryPoint:
    """Unit tests for the CLI entry point (main function)."""

    def test_main_parses_run_command(self) -> None:
        """main() parses 'run <agent>' correctly."""
        from cortexgraph.cli.consolidate import main

        with (
            patch("sys.argv", ["cortexgraph-consolidate", "run", "decay", "--dry-run"]),
            patch("cortexgraph.cli.consolidate.cmd_run", return_value=0) as mock_cmd,
        ):
            result = main()

            assert result == 0
            mock_cmd.assert_called_once()

    def test_main_parses_run_all_command(self) -> None:
        """main() parses 'run --all' correctly."""
        from cortexgraph.cli.consolidate import main

        with (
            patch("sys.argv", ["cortexgraph-consolidate", "run", "--all", "--dry-run"]),
            patch("cortexgraph.cli.consolidate.cmd_run_all", return_value=0) as mock_cmd,
        ):
            result = main()

            assert result == 0
            mock_cmd.assert_called_once()

    def test_main_parses_status_command(self) -> None:
        """main() parses 'status' correctly."""
        from cortexgraph.cli.consolidate import main

        with (
            patch("sys.argv", ["cortexgraph-consolidate", "status"]),
            patch("cortexgraph.cli.consolidate.cmd_status", return_value=(0, "")) as mock_cmd,
        ):
            result = main()

            assert result == 0
            mock_cmd.assert_called_once()

    def test_main_parses_process_command(self) -> None:
        """main() parses 'process <issue_id>' correctly."""
        from cortexgraph.cli.consolidate import main

        with (
            patch(
                "sys.argv",
                ["cortexgraph-consolidate", "process", "cortexgraph-abc"],
            ),
            patch("cortexgraph.cli.consolidate.cmd_process", return_value=0) as mock_cmd,
        ):
            result = main()

            assert result == 0
            mock_cmd.assert_called_once()

    def test_main_handles_json_flag(self) -> None:
        """main() handles --json flag."""
        from cortexgraph.cli.consolidate import main

        with (
            patch(
                "sys.argv",
                ["cortexgraph-consolidate", "status", "--json"],
            ),
            patch("cortexgraph.cli.consolidate.cmd_status", return_value=(0, "{}")) as mock_cmd,
        ):
            result = main()

            assert result == 0
            # json_output should be True
            mock_cmd.assert_called_with(json_output=True)


# =============================================================================
# T091: Unit Tests - Agent Factory
# =============================================================================


class TestAgentFactory:
    """Unit tests for agent factory function."""

    def test_get_agent_returns_decay_analyzer(self) -> None:
        """get_agent('decay') returns DecayAnalyzer instance."""
        from cortexgraph.cli.consolidate import get_agent

        with patch("cortexgraph.agents.storage_utils.get_storage"):
            agent = get_agent("decay", dry_run=True)

            from cortexgraph.agents.decay_analyzer import DecayAnalyzer

            assert isinstance(agent, DecayAnalyzer)
            assert agent.dry_run is True

    def test_get_agent_returns_cluster_detector(self) -> None:
        """get_agent('cluster') returns ClusterDetector instance."""
        from cortexgraph.cli.consolidate import get_agent

        with patch("cortexgraph.agents.storage_utils.get_storage"):
            agent = get_agent("cluster", dry_run=True)

            from cortexgraph.agents.cluster_detector import ClusterDetector

            assert isinstance(agent, ClusterDetector)

    def test_get_agent_returns_semantic_merge(self) -> None:
        """get_agent('merge') returns SemanticMerge instance."""
        from cortexgraph.cli.consolidate import get_agent

        with patch("cortexgraph.agents.storage_utils.get_storage"):
            agent = get_agent("merge", dry_run=True)

            from cortexgraph.agents.semantic_merge import SemanticMerge

            assert isinstance(agent, SemanticMerge)

    def test_get_agent_returns_ltm_promoter(self) -> None:
        """get_agent('promote') returns LTMPromoter instance."""
        from cortexgraph.cli.consolidate import get_agent

        with patch("cortexgraph.agents.storage_utils.get_storage"):
            agent = get_agent("promote", dry_run=True)

            from cortexgraph.agents.ltm_promoter import LTMPromoter

            assert isinstance(agent, LTMPromoter)

    def test_get_agent_returns_relationship_discovery(self) -> None:
        """get_agent('relations') returns RelationshipDiscovery instance."""
        from cortexgraph.cli.consolidate import get_agent

        with patch("cortexgraph.agents.storage_utils.get_storage"):
            agent = get_agent("relations", dry_run=True)

            from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

            assert isinstance(agent, RelationshipDiscovery)

    def test_get_agent_raises_for_unknown(self) -> None:
        """get_agent('unknown') raises ValueError."""
        from cortexgraph.cli.consolidate import get_agent

        with pytest.raises(ValueError, match="Unknown agent"):
            get_agent("unknown", dry_run=True)
