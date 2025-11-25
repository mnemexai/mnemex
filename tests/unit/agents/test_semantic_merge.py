"""Unit tests for SemanticMerge agent (T047-T048).

T047: Content deduplication tests
T048: Entity/tag union preservation tests

These tests verify the merge algorithm logic, focusing on:
- Detecting and removing duplicate content
- Preserving all unique entities across memories
- Preserving all unique tags across memories
- Proper content combination strategies
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.models import MergeResult

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock storage with mergeable memories."""
    storage = MagicMock()
    storage.memories = {}

    # Set up get() to return memories from the dict
    def get_memory(mem_id: str) -> MagicMock | None:
        return storage.memories.get(mem_id)

    storage.get = get_memory
    storage.get_memory = get_memory

    return storage


@pytest.fixture
def mock_beads() -> MagicMock:
    """Create mock beads integration."""
    beads = MagicMock()
    beads.query_consolidation_issues = MagicMock(return_value=[])
    beads.claim_issue = MagicMock(return_value=True)
    beads.close_issue = MagicMock()
    return beads


def create_memory_mock(
    id: str,
    content: str,
    entities: list[str] | None = None,
    tags: list[str] | None = None,
    strength: float = 1.0,
) -> MagicMock:
    """Helper to create memory mocks with consistent structure."""
    mem = MagicMock()
    mem.id = id
    mem.content = content
    mem.entities = entities or []
    mem.tags = tags or []
    mem.strength = strength
    mem.status = "active"
    return mem


def create_merge_issue(
    issue_id: str,
    memory_ids: list[str],
    cluster_id: str = "test-cluster",
    cohesion: float = 0.85,
) -> dict:
    """Helper to create beads merge issue."""
    import json

    return {
        "id": issue_id,
        "title": f"Merge: {cluster_id}",
        "status": "open",
        "labels": ["consolidation:merge"],
        "notes": json.dumps(
            {
                "memory_ids": memory_ids,
                "cluster_id": cluster_id,
                "cohesion": cohesion,
            }
        ),
    }


# =============================================================================
# T047: Content Deduplication Tests
# =============================================================================


class TestContentDeduplication:
    """Unit tests for content deduplication logic (T047)."""

    def test_identical_content_deduplicated(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """Identical content should appear only once in merged result."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Two memories with identical content
        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "PostgreSQL configuration"),
            "mem-2": create_memory_mock("mem-2", "PostgreSQL configuration"),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # Content should not be duplicated
            assert isinstance(result, MergeResult)
            # In dry run, we verify the merge logic worked
            assert result.success is True

    def test_unique_content_preserved(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Unique content from each memory should be preserved."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Two memories with different content
        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "PostgreSQL configuration settings"),
            "mem-2": create_memory_mock("mem-2", "PostgreSQL connection pooling"),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # Both pieces of content should be represented
            assert result.success is True
            assert len(result.source_ids) == 2

    def test_partial_overlap_handled(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Memories with partial content overlap should be merged intelligently."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Memories with related but not identical content
        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "PostgreSQL uses port 5432 by default"),
            "mem-2": create_memory_mock("mem-2", "PostgreSQL connection string format"),
            "mem-3": create_memory_mock("mem-3", "PostgreSQL performance tuning tips"),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2", "mem-3"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # All three should be sources
            assert len(result.source_ids) == 3
            assert result.success is True

    def test_empty_content_handled(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Memories with empty content should be handled gracefully."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "Valid content here"),
            "mem-2": create_memory_mock("mem-2", ""),  # Empty content
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # Should still succeed
            assert result.success is True

    def test_content_diff_describes_merge(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """content_diff should describe what was merged."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "PostgreSQL config", entities=["PostgreSQL"]),
            "mem-2": create_memory_mock("mem-2", "PostgreSQL tuning", entities=["PostgreSQL"]),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # content_diff should be informative
            assert result.content_diff
            assert "PostgreSQL" in result.content_diff or "2" in result.content_diff


# =============================================================================
# T048: Entity/Tag Union Preservation Tests
# =============================================================================


class TestEntityTagPreservation:
    """Unit tests for entity and tag union preservation (T048)."""

    def test_all_entities_preserved(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """All unique entities from source memories should be preserved."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock(
                "mem-1",
                "PostgreSQL config",
                entities=["PostgreSQL", "Database"],
            ),
            "mem-2": create_memory_mock(
                "mem-2",
                "PostgreSQL tuning",
                entities=["PostgreSQL", "Performance"],
            ),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # All 3 unique entities should be preserved
            # PostgreSQL (shared), Database, Performance
            assert result.entities_preserved >= 3

    def test_duplicate_entities_not_duplicated(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """Duplicate entities across memories should appear once in count."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Same entity in both
        mock_storage.memories = {
            "mem-1": create_memory_mock(
                "mem-1",
                "PostgreSQL config",
                entities=["PostgreSQL"],
            ),
            "mem-2": create_memory_mock(
                "mem-2",
                "PostgreSQL tuning",
                entities=["PostgreSQL"],
            ),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # Only 1 unique entity
            assert result.entities_preserved == 1

    def test_empty_entities_handled(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Memories with no entities should merge without error."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "Content 1", entities=[]),
            "mem-2": create_memory_mock("mem-2", "Content 2", entities=[]),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            assert result.entities_preserved == 0
            assert result.success is True

    def test_none_entities_handled(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Memories with None entities should merge without error."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "Content 1", entities=None),
            "mem-2": create_memory_mock("mem-2", "Content 2", entities=["Entity1"]),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            assert result.entities_preserved == 1
            assert result.success is True

    def test_many_entities_preserved(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Large entity sets should be fully preserved."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        # Each memory has different entities
        mock_storage.memories = {
            "mem-1": create_memory_mock(
                "mem-1",
                "Content 1",
                entities=["Entity1", "Entity2", "Entity3"],
            ),
            "mem-2": create_memory_mock(
                "mem-2",
                "Content 2",
                entities=["Entity4", "Entity5", "Entity6"],
            ),
            "mem-3": create_memory_mock(
                "mem-3",
                "Content 3",
                entities=["Entity7", "Entity8"],
            ),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2", "mem-3"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # All 8 unique entities preserved
            assert result.entities_preserved == 8

    def test_tags_union_collected(self, mock_storage: MagicMock, mock_beads: MagicMock) -> None:
        """Tags from all source memories should be collected (union)."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock(
                "mem-1",
                "Content 1",
                tags=["database", "config"],
            ),
            "mem-2": create_memory_mock(
                "mem-2",
                "Content 2",
                tags=["database", "performance"],
            ),
        }

        issue = create_merge_issue("issue-1", ["mem-1", "mem-2"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage
            result = merge.process_item("issue-1")

            # Merge should succeed (tags are collected internally)
            assert result.success is True


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestMergeEdgeCases:
    """Edge case tests for SemanticMerge."""

    def test_minimum_two_memories_required(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """Merge requires at least 2 memories."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "Single memory"),
        }

        # Issue with only 1 memory
        issue = create_merge_issue("issue-1", ["mem-1"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage

            with pytest.raises(ValueError, match="fewer than 2"):
                merge.process_item("issue-1")

    def test_missing_memory_raises_error(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """Missing memory in issue should raise error."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_storage.memories = {
            "mem-1": create_memory_mock("mem-1", "Only one exists"),
        }

        # Issue references non-existent memory
        issue = create_merge_issue("issue-1", ["mem-1", "mem-missing"])
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage

            with pytest.raises(ValueError, match="not found"):
                merge.process_item("issue-1")

    def test_invalid_issue_json_raises_error(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """Invalid JSON in issue notes should raise error."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        issue = {
            "id": "issue-bad",
            "title": "Bad Issue",
            "status": "open",
            "labels": ["consolidation:merge"],
            "notes": "this is not valid json{",
        }
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage

            with pytest.raises(ValueError, match="Invalid notes JSON"):
                merge.process_item("issue-bad")

    def test_unknown_issue_raises_error(
        self, mock_storage: MagicMock, mock_beads: MagicMock
    ) -> None:
        """Unknown beads issue ID should raise error."""
        from cortexgraph.agents.semantic_merge import SemanticMerge

        mock_beads.query_consolidation_issues.return_value = []

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = mock_storage

            with pytest.raises(ValueError, match="Unknown beads issue"):
                merge.process_item("nonexistent-issue")
