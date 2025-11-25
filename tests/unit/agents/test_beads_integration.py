"""Unit tests for beads integration (T021).

Tests the beads CLI wrapper functions. Uses mocking to avoid
requiring actual beads installation during testing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.beads_integration import (
    AGENT_LABELS,
    URGENCY_LABELS,
    BeadsError,
    _run_bd_command,
    block_issue,
    claim_issue,
    close_issue,
    create_consolidation_issue,
    query_consolidation_issues,
)

# =============================================================================
# _run_bd_command Tests
# =============================================================================


class TestRunBdCommand:
    """Tests for _run_bd_command helper."""

    @patch("cortexgraph.agents.beads_integration.subprocess.run")
    def test_successful_command(self, mock_run: MagicMock) -> None:
        """Test successful command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"id": "test-123"}',
            stderr="",
        )

        result = _run_bd_command(["show", "test-123"])

        assert result == {"id": "test-123"}
        mock_run.assert_called_once()
        # Verify --json flag is added
        assert "--json" in mock_run.call_args[0][0]

    @patch("cortexgraph.agents.beads_integration.subprocess.run")
    def test_command_failure(self, mock_run: MagicMock) -> None:
        """Test command failure raises BeadsError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: issue not found",
        )

        with pytest.raises(BeadsError, match="Beads command failed"):
            _run_bd_command(["show", "nonexistent"])

    @patch("cortexgraph.agents.beads_integration.subprocess.run")
    def test_command_failure_no_check(self, mock_run: MagicMock) -> None:
        """Test command failure with check=False returns empty."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: issue not found",
        )

        result = _run_bd_command(["show", "nonexistent"], check=False)
        assert result == {}

    @patch("cortexgraph.agents.beads_integration.subprocess.run")
    def test_json_parse_error(self, mock_run: MagicMock) -> None:
        """Test JSON parse error raises BeadsError."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json",
            stderr="",
        )

        with pytest.raises(BeadsError, match="Failed to parse"):
            _run_bd_command(["list"])

    @patch("cortexgraph.agents.beads_integration.subprocess.run")
    def test_bd_not_found(self, mock_run: MagicMock) -> None:
        """Test bd CLI not found raises BeadsError."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(BeadsError, match="bd.*not found"):
            _run_bd_command(["list"])


# =============================================================================
# Label Constants Tests
# =============================================================================


class TestLabelConstants:
    """Tests for label constant mappings."""

    def test_agent_labels(self) -> None:
        """Test all agent labels are defined."""
        assert "decay" in AGENT_LABELS
        assert "cluster" in AGENT_LABELS
        assert "merge" in AGENT_LABELS
        assert "promote" in AGENT_LABELS
        assert "relations" in AGENT_LABELS

        # Verify label format
        for label in AGENT_LABELS.values():
            assert label.startswith("consolidation:")

    def test_urgency_labels(self) -> None:
        """Test all urgency labels are defined."""
        assert "high" in URGENCY_LABELS
        assert "medium" in URGENCY_LABELS
        assert "low" in URGENCY_LABELS

        # Verify label format
        for label in URGENCY_LABELS.values():
            assert label.startswith("urgency:")


# =============================================================================
# create_consolidation_issue Tests
# =============================================================================


class TestCreateConsolidationIssue:
    """Tests for create_consolidation_issue function."""

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    @patch("cortexgraph.agents.beads_integration.query_consolidation_issues")
    def test_create_issue(self, mock_query: MagicMock, mock_bd: MagicMock) -> None:
        """Test successful issue creation."""
        mock_query.return_value = []  # No duplicates
        mock_bd.return_value = {"id": "cortexgraph-001"}

        issue_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-123"],
            action="reinforce",
            urgency="high",
        )

        assert issue_id == "cortexgraph-001"
        mock_bd.assert_called_once()

        # Verify command includes correct labels
        call_args = mock_bd.call_args[0][0]
        assert "consolidation:decay" in str(call_args)
        assert "urgency:high" in str(call_args)

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    @patch("cortexgraph.agents.beads_integration.query_consolidation_issues")
    def test_prevent_duplicate(self, mock_query: MagicMock, mock_bd: MagicMock) -> None:
        """Test duplicate prevention returns existing issue."""
        mock_query.return_value = [
            {
                "id": "existing-001",
                "notes": {"memory_ids": ["mem-123"]},
            }
        ]

        issue_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-123"],
            action="reinforce",
        )

        assert issue_id == "existing-001"
        mock_bd.assert_not_called()  # Should not create new

    def test_invalid_agent(self) -> None:
        """Test invalid agent raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent"):
            create_consolidation_issue(
                agent="invalid",
                memory_ids=["mem-123"],
                action="test",
            )

    def test_invalid_urgency(self) -> None:
        """Test invalid urgency raises ValueError."""
        with pytest.raises(ValueError, match="Invalid urgency"):
            create_consolidation_issue(
                agent="decay",
                memory_ids=["mem-123"],
                action="test",
                urgency="critical",  # Invalid
            )

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    @patch("cortexgraph.agents.beads_integration.query_consolidation_issues")
    def test_title_format_single_memory(self, mock_query: MagicMock, mock_bd: MagicMock) -> None:
        """Test title format for single memory."""
        mock_query.return_value = []
        mock_bd.return_value = {"id": "test"}

        create_consolidation_issue(
            agent="decay",
            memory_ids=["abc-12345678"],
            action="reinforce",
        )

        # Check title includes truncated memory ID
        call_args = mock_bd.call_args[0][0]
        title_arg_idx = call_args.index("create") + 1
        title = call_args[title_arg_idx]
        assert "abc-1234" in title  # First 8 chars

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    @patch("cortexgraph.agents.beads_integration.query_consolidation_issues")
    def test_title_format_multiple_memories(
        self, mock_query: MagicMock, mock_bd: MagicMock
    ) -> None:
        """Test title format for multiple memories."""
        mock_query.return_value = []
        mock_bd.return_value = {"id": "test"}

        create_consolidation_issue(
            agent="cluster",
            memory_ids=["mem-1", "mem-2", "mem-3"],
            action="merge",
        )

        call_args = mock_bd.call_args[0][0]
        title_arg_idx = call_args.index("create") + 1
        title = call_args[title_arg_idx]
        assert "3 memories" in title


# =============================================================================
# query_consolidation_issues Tests
# =============================================================================


class TestQueryConsolidationIssues:
    """Tests for query_consolidation_issues function."""

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_query_all(self, mock_bd: MagicMock) -> None:
        """Test query all consolidation issues."""
        mock_bd.return_value = [
            {"id": "issue-1", "labels": ["consolidation:decay"], "notes": "{}"},
            {"id": "issue-2", "labels": ["consolidation:cluster"], "notes": "{}"},
        ]

        results = query_consolidation_issues()

        assert len(results) == 2
        mock_bd.assert_called_once()

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_query_by_agent(self, mock_bd: MagicMock) -> None:
        """Test query filtered by agent."""
        mock_bd.return_value = [
            {"id": "issue-1", "labels": ["consolidation:decay"], "notes": "{}"},
        ]

        results = query_consolidation_issues(agent="decay")

        assert len(results) == 1
        # Verify label filter in command
        call_args = mock_bd.call_args[0][0]
        assert "consolidation:decay" in str(call_args)

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_parse_notes_json(self, mock_bd: MagicMock) -> None:
        """Test notes JSON is parsed."""
        mock_bd.return_value = [
            {
                "id": "issue-1",
                "labels": ["consolidation:decay"],
                "notes": '{"memory_ids": ["mem-1"]}',
            },
        ]

        results = query_consolidation_issues()

        assert results[0]["notes"]["memory_ids"] == ["mem-1"]

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_empty_results(self, mock_bd: MagicMock) -> None:
        """Test empty results returns empty list."""
        mock_bd.return_value = []

        results = query_consolidation_issues()

        assert results == []

    def test_invalid_agent_filter(self) -> None:
        """Test invalid agent filter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent"):
            query_consolidation_issues(agent="invalid")


# =============================================================================
# claim_issue Tests
# =============================================================================


class TestClaimIssue:
    """Tests for claim_issue function."""

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_successful_claim(self, mock_bd: MagicMock) -> None:
        """Test successful issue claim."""
        mock_bd.side_effect = [
            {"id": "test-123", "status": "open"},  # show
            {},  # update
        ]

        result = claim_issue("test-123")

        assert result is True
        assert mock_bd.call_count == 2

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_already_in_progress(self, mock_bd: MagicMock) -> None:
        """Test claiming already in-progress issue."""
        mock_bd.return_value = {"id": "test-123", "status": "in_progress"}

        result = claim_issue("test-123")

        assert result is False
        assert mock_bd.call_count == 1  # Only show, no update

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_blocked_issue(self, mock_bd: MagicMock) -> None:
        """Test cannot claim blocked issue."""
        mock_bd.return_value = {"id": "test-123", "status": "blocked"}

        result = claim_issue("test-123")

        assert result is False


# =============================================================================
# close_issue Tests
# =============================================================================


class TestCloseIssue:
    """Tests for close_issue function."""

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_successful_close(self, mock_bd: MagicMock) -> None:
        """Test successful issue close."""
        mock_bd.return_value = {}

        close_issue("test-123", "Completed successfully")

        mock_bd.assert_called_once()
        call_args = mock_bd.call_args[0][0]
        assert "close" in call_args
        assert "test-123" in call_args
        assert "Completed successfully" in call_args

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_close_failure(self, mock_bd: MagicMock) -> None:
        """Test close failure raises BeadsError."""
        mock_bd.side_effect = BeadsError("Close failed")

        with pytest.raises(BeadsError):
            close_issue("test-123", "reason")


# =============================================================================
# block_issue Tests
# =============================================================================


class TestBlockIssue:
    """Tests for block_issue function."""

    @patch("cortexgraph.agents.beads_integration._run_bd_command")
    def test_successful_block(self, mock_bd: MagicMock) -> None:
        """Test successful issue block."""
        mock_bd.return_value = {}

        block_issue("test-123", "Processing error occurred")

        mock_bd.assert_called_once()
        call_args = mock_bd.call_args[0][0]
        assert "update" in call_args
        assert "--status" in call_args
        assert "blocked" in call_args
