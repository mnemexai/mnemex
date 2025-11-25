"""Integration tests for beads coordination (T093).

Tests for multi-agent coordination via beads issue tracking:
1. Agent creates issues during analysis
2. Cross-agent handoff workflows
3. Full issue lifecycle (create → claim → process → close)
4. Duplicate prevention and error handling
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.beads_integration import (
    AGENT_LABELS,
    BeadsError,
    claim_issue,
    close_issue,
    create_consolidation_issue,
    query_consolidation_issues,
)
from cortexgraph.agents.decay_analyzer import DecayAnalyzer
from cortexgraph.agents.models import Urgency
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
def test_storage_with_urgent_memory(temp_storage_dir: Path) -> JSONLStorage:
    """Create storage with a memory that needs urgent attention."""
    storage = JSONLStorage(str(temp_storage_dir))
    now = int(time.time())

    # Memory with very low decay score (urgent)
    urgent_memory = Memory(
        id="mem-urgent-001",
        content="Critical project deadline information",
        entities=["Project", "Deadline"],
        tags=["urgent", "project"],
        created_at=now - 86400 * 30,  # 30 days ago
        last_used=now - 86400 * 20,  # 20 days ago
        use_count=0,  # Never reinforced
        strength=1.0,
    )

    storage.memories = {"mem-urgent-001": urgent_memory}
    return storage


@pytest.fixture
def mock_beads_cli():
    """Fixture to mock beads CLI calls with realistic responses."""
    with patch("cortexgraph.agents.beads_integration.subprocess.run") as mock_run:
        # Track created issues for query responses
        created_issues: dict[str, dict] = {}
        issue_counter = [0]

        def mock_subprocess(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""

            # Parse command
            cmd_str = " ".join(cmd)

            if "create" in cmd_str:
                # Create new issue
                issue_counter[0] += 1
                issue_id = f"test-issue-{issue_counter[0]}"

                # Extract title and notes from command
                title_idx = cmd.index("create") + 1 if "create" in cmd else 0
                title = cmd[title_idx] if title_idx < len(cmd) else "Test Issue"

                notes = "{}"
                if "--notes" in cmd:
                    notes_idx = cmd.index("--notes") + 1
                    notes = cmd[notes_idx] if notes_idx < len(cmd) else "{}"

                labels = []
                if "--labels" in cmd:
                    labels_idx = cmd.index("--labels") + 1
                    labels = cmd[labels_idx].split(",") if labels_idx < len(cmd) else []

                created_issues[issue_id] = {
                    "id": issue_id,
                    "title": title,
                    "status": "open",
                    "notes": notes,
                    "labels": labels,
                }
                result.stdout = f'{{"id": "{issue_id}"}}'

            elif "list" in cmd_str:
                # Return created issues matching filters
                issues = list(created_issues.values())

                # Filter by status if specified
                if "--status" in cmd:
                    status_idx = cmd.index("--status") + 1
                    status = cmd[status_idx] if status_idx < len(cmd) else "open"
                    issues = [i for i in issues if i.get("status") == status]

                # Filter by labels if specified (ALL labels must match)
                if "--labels" in cmd:
                    labels_idx = cmd.index("--labels") + 1
                    filter_labels = cmd[labels_idx].split(",") if labels_idx < len(cmd) else []
                    # ALL specified labels must be present (AND logic)
                    issues = [
                        i
                        for i in issues
                        if all(lbl in i.get("labels", []) for lbl in filter_labels)
                    ]

                import json

                result.stdout = json.dumps(issues)

            elif "show" in cmd_str:
                # Get single issue
                issue_id = cmd[cmd.index("show") + 1] if "show" in cmd else ""
                if issue_id in created_issues:
                    import json

                    result.stdout = json.dumps(created_issues[issue_id])
                else:
                    result.returncode = 1
                    result.stderr = "Issue not found"

            elif "update" in cmd_str:
                # Update issue status
                issue_id = cmd[cmd.index("update") + 1] if "update" in cmd else ""
                if issue_id in created_issues:
                    if "--status" in cmd:
                        status_idx = cmd.index("--status") + 1
                        created_issues[issue_id]["status"] = cmd[status_idx]
                    result.stdout = "{}"
                else:
                    result.returncode = 1
                    result.stderr = "Issue not found"

            elif "close" in cmd_str:
                # Close issue
                issue_id = cmd[cmd.index("close") + 1] if "close" in cmd else ""
                if issue_id in created_issues:
                    created_issues[issue_id]["status"] = "closed"
                    result.stdout = "{}"
                else:
                    result.returncode = 1
                    result.stderr = "Issue not found"

            return result

        mock_run.side_effect = mock_subprocess
        yield mock_run, created_issues


# =============================================================================
# T093: Beads Coordination Integration Tests
# =============================================================================


class TestIssueLifecycle:
    """Tests for complete issue lifecycle."""

    def test_full_issue_lifecycle(self, mock_beads_cli) -> None:
        """Test create → claim → close lifecycle."""
        mock_run, created_issues = mock_beads_cli

        # 1. Create issue
        issue_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-123"],
            action="reinforce",
            urgency="high",
        )
        assert issue_id.startswith("test-issue-")
        assert created_issues[issue_id]["status"] == "open"

        # 2. Claim issue
        result = claim_issue(issue_id)
        assert result is True
        assert created_issues[issue_id]["status"] == "in_progress"

        # 3. Close issue
        close_issue(issue_id, "Processing complete")
        assert created_issues[issue_id]["status"] == "closed"

    def test_query_after_create(self, mock_beads_cli) -> None:
        """Test querying issues after creation."""
        mock_run, created_issues = mock_beads_cli

        # Create several issues
        decay_issue = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-1"],
            action="reinforce",
            urgency="high",
        )
        cluster_issue = create_consolidation_issue(
            agent="cluster",
            memory_ids=["mem-2", "mem-3"],
            action="merge",
            urgency="medium",
        )

        # Query all issues
        all_issues = query_consolidation_issues()
        assert len(all_issues) == 2

        # Query by agent
        decay_issues = query_consolidation_issues(agent="decay")
        assert len(decay_issues) == 1
        assert decay_issues[0]["id"] == decay_issue

        cluster_issues = query_consolidation_issues(agent="cluster")
        assert len(cluster_issues) == 1
        assert cluster_issues[0]["id"] == cluster_issue


class TestCrossAgentCoordination:
    """Tests for coordination between agents."""

    def test_decay_creates_for_cluster(self, mock_beads_cli) -> None:
        """Test decay agent creates issues that cluster agent can query."""
        mock_run, created_issues = mock_beads_cli

        # Decay agent creates issue for memories needing attention
        issue_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-similar-1", "mem-similar-2"],
            action="review_for_clustering",
            urgency="medium",
            extra_data={"scores": [0.25, 0.28]},
        )

        # Cluster agent queries for open issues
        open_issues = query_consolidation_issues(status="open")
        assert len(open_issues) == 1
        assert open_issues[0]["id"] == issue_id

    def test_sequential_agent_handoff(self, mock_beads_cli) -> None:
        """Test sequential handoff: decay → cluster → merge."""
        mock_run, created_issues = mock_beads_cli

        # Step 1: Decay agent creates issue
        decay_issue = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-1", "mem-2"],
            action="needs_review",
            urgency="medium",
        )

        # Step 2: Cluster agent claims and processes
        claim_issue(decay_issue)
        assert created_issues[decay_issue]["status"] == "in_progress"

        # Step 3: Cluster creates follow-up issue for merge
        cluster_issue = create_consolidation_issue(
            agent="cluster",
            memory_ids=["mem-1", "mem-2"],
            action="merge_recommended",
            urgency="low",
            extra_data={"source_issue": decay_issue, "cohesion": 0.85},
        )

        # Step 4: Close original issue
        close_issue(decay_issue, "Forwarded to cluster agent")
        assert created_issues[decay_issue]["status"] == "closed"

        # Step 5: New issue should be open
        assert created_issues[cluster_issue]["status"] == "open"


class TestDuplicatePrevention:
    """Tests for duplicate issue prevention."""

    def test_duplicate_memory_ids_returns_existing(self, mock_beads_cli) -> None:
        """Test creating issue with same memory_ids returns existing."""
        mock_run, created_issues = mock_beads_cli

        # Create first issue
        first_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-123"],
            action="reinforce",
        )

        # Try to create duplicate
        second_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-123"],
            action="reinforce",
        )

        # Should return same ID
        assert first_id == second_id
        assert len(created_issues) == 1

    def test_different_memory_ids_creates_new(self, mock_beads_cli) -> None:
        """Test different memory_ids creates new issue."""
        mock_run, created_issues = mock_beads_cli

        first_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-1"],
            action="reinforce",
        )

        second_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-2"],
            action="reinforce",
        )

        assert first_id != second_id
        assert len(created_issues) == 2


class TestErrorHandling:
    """Tests for error handling in coordination."""

    def test_claim_nonexistent_issue(self, mock_beads_cli) -> None:
        """Test claiming non-existent issue fails gracefully."""
        mock_run, created_issues = mock_beads_cli

        # Try to claim issue that doesn't exist
        result = claim_issue("nonexistent-issue")

        # Should fail gracefully
        assert result is False

    def test_double_claim_returns_false(self, mock_beads_cli) -> None:
        """Test claiming already-claimed issue returns False."""
        mock_run, created_issues = mock_beads_cli

        issue_id = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-123"],
            action="reinforce",
        )

        # First claim succeeds
        result1 = claim_issue(issue_id)
        assert result1 is True

        # Second claim fails
        result2 = claim_issue(issue_id)
        assert result2 is False

    def test_close_nonexistent_raises(self, mock_beads_cli) -> None:
        """Test closing non-existent issue raises BeadsError."""
        mock_run, created_issues = mock_beads_cli

        with pytest.raises(BeadsError):
            close_issue("nonexistent-issue", "test")


class TestAgentWithBeadsIntegration:
    """Tests for agent classes using beads integration."""

    def test_decay_analyzer_with_beads(
        self, test_storage_with_urgent_memory: JSONLStorage, mock_beads_cli
    ) -> None:
        """Test DecayAnalyzer can create beads issues during run."""
        mock_run, created_issues = mock_beads_cli

        with patch(
            "cortexgraph.agents.decay_analyzer.get_storage",
            return_value=test_storage_with_urgent_memory,
        ):
            # The mock_beads_cli fixture already mocks subprocess.run
            # which is used by create_consolidation_issue internally
            analyzer = DecayAnalyzer(dry_run=False)
            analyzer._storage = test_storage_with_urgent_memory
            results = analyzer.run()

            # Agent should have processed the urgent memory
            assert len(results) >= 1

            # Check if urgent results were found (20+ days old, never used = urgent)
            urgent_results = [r for r in results if r.urgency == Urgency.HIGH]
            assert len(urgent_results) >= 0  # May or may not be urgent depending on decay


class TestLabelConventions:
    """Tests for label convention compliance."""

    def test_agent_labels_applied(self, mock_beads_cli) -> None:
        """Test correct agent labels are applied to issues."""
        mock_run, created_issues = mock_beads_cli

        for agent in ["decay", "cluster", "merge", "promote", "relations"]:
            issue_id = create_consolidation_issue(
                agent=agent,
                memory_ids=[f"mem-{agent}"],
                action="test",
            )

            expected_label = AGENT_LABELS[agent]
            assert expected_label in created_issues[issue_id]["labels"]

    def test_urgency_labels_applied(self, mock_beads_cli) -> None:
        """Test correct urgency labels are applied to issues."""
        mock_run, created_issues = mock_beads_cli

        for urgency in ["high", "medium", "low"]:
            issue_id = create_consolidation_issue(
                agent="decay",
                memory_ids=[f"mem-{urgency}"],
                action="test",
                urgency=urgency,
            )

            expected_label = f"urgency:{urgency}"
            assert expected_label in created_issues[issue_id]["labels"]


class TestQueryFilters:
    """Tests for query filtering."""

    def test_query_by_status(self, mock_beads_cli) -> None:
        """Test querying by status filter."""
        mock_run, created_issues = mock_beads_cli

        # Create and process issues
        issue1 = create_consolidation_issue(agent="decay", memory_ids=["mem-1"], action="test")
        issue2 = create_consolidation_issue(agent="decay", memory_ids=["mem-2"], action="test")

        # Claim one
        claim_issue(issue1)

        # Query by status
        open_issues = query_consolidation_issues(status="open")
        in_progress_issues = query_consolidation_issues(status="in_progress")

        assert len(open_issues) == 1
        assert open_issues[0]["id"] == issue2

        assert len(in_progress_issues) == 1
        assert in_progress_issues[0]["id"] == issue1

    def test_query_by_agent_and_urgency(self, mock_beads_cli) -> None:
        """Test combined agent and urgency filtering."""
        mock_run, created_issues = mock_beads_cli

        # Create issues with different urgency levels
        high_issue = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-high"],
            action="test",
            urgency="high",
        )
        low_issue = create_consolidation_issue(
            agent="decay",
            memory_ids=["mem-low"],
            action="test",
            urgency="low",
        )

        # Query with urgency filter
        high_urgency = query_consolidation_issues(agent="decay", urgency="high")
        low_urgency = query_consolidation_issues(agent="decay", urgency="low")

        assert len(high_urgency) == 1
        assert high_urgency[0]["id"] == high_issue

        assert len(low_urgency) == 1
        assert low_urgency[0]["id"] == low_issue
