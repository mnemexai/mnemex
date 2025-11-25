"""Contract tests for SemanticMerge (T045-T046).

These tests verify the SemanticMerge agent conforms to the ConsolidationAgent
contract defined in contracts/agent-api.md.

Contract Requirements (SemanticMerge-specific):
- scan() MUST only process from beads issues (not free scan)
- scan() MUST filter for consolidation:merge label
- process_item() MUST return MergeResult or raise exception
- process_item() MUST preserve all unique entities
- process_item() MUST preserve all unique content
- process_item() MUST create consolidated_from relations
- process_item() MUST archive (not delete) originals
- process_item() MUST close beads issue on success
- If dry_run=True, process_item() MUST NOT modify any data
- process_item() SHOULD complete within 5 seconds
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import MergeResult

# Mark all tests in this module as requiring beads CLI
pytestmark = pytest.mark.requires_beads

if TYPE_CHECKING:
    from cortexgraph.agents.semantic_merge import SemanticMerge


# =============================================================================
# Contract Test Fixtures
# =============================================================================


# Mock beads issues representing merge candidates from ClusterDetector
MOCK_MERGE_ISSUES = [
    {
        "id": "cortexgraph-merge-001",
        "title": "Merge: PostgreSQL cluster (3 memories)",
        "status": "open",
        "labels": ["consolidation:merge", "urgency:medium"],
        "notes": '{"memory_ids": ["mem-1", "mem-2", "mem-3"], "cluster_id": "cluster-pg", "cohesion": 0.85}',
    },
    {
        "id": "cortexgraph-merge-002",
        "title": "Merge: JWT cluster (2 memories)",
        "status": "open",
        "labels": ["consolidation:merge", "urgency:low"],
        "notes": '{"memory_ids": ["mem-4", "mem-5"], "cluster_id": "cluster-jwt", "cohesion": 0.78}',
    },
]


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock storage with test memories to merge."""
    storage = MagicMock()

    # PostgreSQL cluster memories
    storage.memories = {
        "mem-1": MagicMock(
            id="mem-1",
            content="PostgreSQL database configuration for production",
            entities=["PostgreSQL", "Database"],
            tags=["database", "config"],
            strength=1.0,
            status="active",
        ),
        "mem-2": MagicMock(
            id="mem-2",
            content="PostgreSQL connection pooling settings",
            entities=["PostgreSQL", "ConnectionPool"],
            tags=["database", "performance"],
            strength=1.0,
            status="active",
        ),
        "mem-3": MagicMock(
            id="mem-3",
            content="PostgreSQL index optimization tips",
            entities=["PostgreSQL", "Index"],
            tags=["database", "optimization"],
            strength=1.0,
            status="active",
        ),
        # JWT cluster memories
        "mem-4": MagicMock(
            id="mem-4",
            content="JWT token validation workflow",
            entities=["JWT", "Authentication"],
            tags=["security", "auth"],
            strength=1.0,
            status="active",
        ),
        "mem-5": MagicMock(
            id="mem-5",
            content="JWT refresh token strategy",
            entities=["JWT", "RefreshToken"],
            tags=["security", "auth"],
            strength=1.0,
            status="active",
        ),
    }

    # Mock get method
    def get_memory(memory_id: str) -> MagicMock | None:
        return storage.memories.get(memory_id)

    storage.get = get_memory
    storage.get_memory = get_memory

    return storage


@pytest.fixture
def mock_beads_integration() -> MagicMock:
    """Create mock beads integration that returns merge issues."""
    beads = MagicMock()

    # query_consolidation_issues returns merge candidates
    beads.query_consolidation_issues = MagicMock(return_value=MOCK_MERGE_ISSUES)

    # claim_issue succeeds
    beads.claim_issue = MagicMock(return_value=True)

    # close_issue succeeds
    beads.close_issue = MagicMock()

    return beads


@pytest.fixture
def semantic_merge(mock_storage: MagicMock, mock_beads_integration: MagicMock) -> SemanticMerge:
    """Create SemanticMerge with mocked dependencies."""
    from cortexgraph.agents.semantic_merge import SemanticMerge

    with (
        patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
        patch(
            "cortexgraph.agents.semantic_merge.query_consolidation_issues",
            mock_beads_integration.query_consolidation_issues,
        ),
        patch(
            "cortexgraph.agents.semantic_merge.claim_issue",
            mock_beads_integration.claim_issue,
        ),
        patch(
            "cortexgraph.agents.semantic_merge.close_issue",
            mock_beads_integration.close_issue,
        ),
    ):
        merge = SemanticMerge(dry_run=True)
        merge._storage = mock_storage
        merge._beads = mock_beads_integration
        return merge


# =============================================================================
# T045: Contract Test - scan() Reads from Beads Issues
# =============================================================================


class TestSemanticMergeScanContract:
    """Contract tests for SemanticMerge.scan() method (T045)."""

    def test_scan_returns_list(self, semantic_merge: SemanticMerge) -> None:
        """scan() MUST return a list."""
        result = semantic_merge.scan()
        assert isinstance(result, list)

    def test_scan_returns_string_ids(self, semantic_merge: SemanticMerge) -> None:
        """scan() MUST return list of string beads issue IDs."""
        result = semantic_merge.scan()
        for item in result:
            assert isinstance(item, str)

    def test_scan_may_return_empty(
        self, mock_storage: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """scan() MAY return empty list when no merge issues found."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # No pending merge issues
        mock_beads_integration.query_consolidation_issues.return_value = []

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads_integration.query_consolidation_issues,
            ),
        ):
            merge = SemanticMerge(dry_run=True)
            result = merge.scan()
            assert result == []

    def test_scan_queries_beads_for_merge_issues(
        self, mock_storage: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """scan() MUST query beads for consolidation:merge issues."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Create fresh instance with tracked mock
        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads_integration.query_consolidation_issues,
            ),
        ):
            merge = SemanticMerge(dry_run=True)
            merge.scan()

            # Verify beads was queried
            mock_beads_integration.query_consolidation_issues.assert_called()

    def test_scan_returns_beads_issue_ids(self, semantic_merge: SemanticMerge) -> None:
        """scan() MUST return beads issue IDs (not memory IDs)."""
        result = semantic_merge.scan()

        # Issue IDs should match the mock data
        expected_ids = [issue["id"] for issue in MOCK_MERGE_ISSUES]
        for issue_id in result:
            assert issue_id in expected_ids

    def test_scan_does_not_modify_data(
        self, semantic_merge: SemanticMerge, mock_storage: MagicMock
    ) -> None:
        """scan() MUST NOT modify any data."""
        # Take snapshot before
        original_count = len(mock_storage.memories)

        # Run scan
        semantic_merge.scan()

        # Verify no changes
        assert len(mock_storage.memories) == original_count

    def test_scan_is_subclass_of_consolidation_agent(self, semantic_merge: SemanticMerge) -> None:
        """SemanticMerge MUST inherit from ConsolidationAgent."""
        assert isinstance(semantic_merge, ConsolidationAgent)


# =============================================================================
# T046: Contract Test - process_item() Returns MergeResult
# =============================================================================


class TestSemanticMergeProcessItemContract:
    """Contract tests for SemanticMerge.process_item() method (T046)."""

    def test_process_item_returns_merge_result(self, semantic_merge: SemanticMerge) -> None:
        """process_item() MUST return MergeResult."""
        issue_ids = semantic_merge.scan()
        if issue_ids:
            result = semantic_merge.process_item(issue_ids[0])
            assert isinstance(result, MergeResult)

    def test_process_item_result_has_required_fields(self, semantic_merge: SemanticMerge) -> None:
        """MergeResult MUST have all required fields."""
        issue_ids = semantic_merge.scan()
        if issue_ids:
            result = semantic_merge.process_item(issue_ids[0])

            # Required fields from contracts/agent-api.md
            assert hasattr(result, "new_memory_id")
            assert hasattr(result, "source_ids")
            assert hasattr(result, "relation_ids")
            assert hasattr(result, "content_diff")
            assert hasattr(result, "entities_preserved")
            assert hasattr(result, "success")

            # Types
            assert isinstance(result.new_memory_id, str)
            assert isinstance(result.source_ids, list)
            assert len(result.source_ids) >= 2  # Min 2 source memories
            assert isinstance(result.relation_ids, list)
            assert isinstance(result.content_diff, str)
            assert isinstance(result.entities_preserved, int)
            assert isinstance(result.success, bool)

    def test_process_item_source_ids_minimum_two(self, semantic_merge: SemanticMerge) -> None:
        """MergeResult.source_ids MUST have at least 2 memories."""
        issue_ids = semantic_merge.scan()
        if issue_ids:
            result = semantic_merge.process_item(issue_ids[0])
            assert len(result.source_ids) >= 2

    def test_process_item_entities_preserved_non_negative(
        self, semantic_merge: SemanticMerge
    ) -> None:
        """MergeResult.entities_preserved MUST be >= 0."""
        issue_ids = semantic_merge.scan()
        if issue_ids:
            result = semantic_merge.process_item(issue_ids[0])
            assert result.entities_preserved >= 0

    def test_process_item_raises_on_invalid_issue_id(self, semantic_merge: SemanticMerge) -> None:
        """process_item() MUST raise exception for invalid beads issue ID."""
        with pytest.raises((ValueError, KeyError, RuntimeError)):
            semantic_merge.process_item("nonexistent-issue")

    def test_process_item_dry_run_no_side_effects(
        self, mock_storage: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """If dry_run=True, process_item() MUST NOT modify any data."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads_integration.query_consolidation_issues,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.claim_issue",
                mock_beads_integration.claim_issue,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.close_issue",
                mock_beads_integration.close_issue,
            ),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            merge._beads = mock_beads_integration

            # Track calls that would modify data
            mock_storage.save = MagicMock()
            mock_storage.archive = MagicMock()
            mock_storage.create_relation = MagicMock()

            issue_ids = merge.scan()
            if issue_ids:
                merge.process_item(issue_ids[0])

                # In dry_run mode, no modifications should occur
                mock_storage.save.assert_not_called()
                mock_storage.archive.assert_not_called()
                mock_storage.create_relation.assert_not_called()
                mock_beads_integration.close_issue.assert_not_called()

    def test_process_item_completes_within_timeout(self, semantic_merge: SemanticMerge) -> None:
        """process_item() SHOULD complete within 5 seconds."""
        issue_ids = semantic_merge.scan()
        if issue_ids:
            start = time.time()
            semantic_merge.process_item(issue_ids[0])
            elapsed = time.time() - start

            assert elapsed < 5.0, f"process_item took {elapsed:.2f}s (limit: 5s)"


# =============================================================================
# Contract Integration Tests
# =============================================================================


class TestSemanticMergeFullContract:
    """Integration tests verifying full contract compliance."""

    def test_run_method_uses_scan_and_process_item(self, semantic_merge: SemanticMerge) -> None:
        """run() MUST call scan() then process_item() for each result."""
        results = semantic_merge.run()

        # All results should be MergeResult
        for result in results:
            assert isinstance(result, MergeResult)

    def test_content_diff_describes_merge(self, semantic_merge: SemanticMerge) -> None:
        """MergeResult.content_diff MUST describe the merge operation."""
        issue_ids = semantic_merge.scan()
        if issue_ids:
            result = semantic_merge.process_item(issue_ids[0])

            # content_diff should be non-empty and descriptive
            assert result.content_diff
            assert len(result.content_diff) > 0

    def test_run_handles_errors_gracefully(
        self, mock_storage: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """run() MUST handle errors per-item without aborting all."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Add a bad issue that will cause an error
        bad_issues = MOCK_MERGE_ISSUES + [
            {
                "id": "cortexgraph-merge-bad",
                "title": "Merge: Bad cluster",
                "status": "open",
                "labels": ["consolidation:merge"],
                "notes": '{"memory_ids": ["nonexistent-1", "nonexistent-2"], "cluster_id": "bad"}',
            }
        ]
        mock_beads_integration.query_consolidation_issues.return_value = bad_issues

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads_integration.query_consolidation_issues,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.claim_issue",
                mock_beads_integration.claim_issue,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.close_issue",
                mock_beads_integration.close_issue,
            ),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            merge._beads = mock_beads_integration

            # Should not raise - should skip error and continue
            results = merge.run()

            # Should still produce some results from valid issues
            assert isinstance(results, list)
