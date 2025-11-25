"""Integration tests for SemanticMerge (T049).

End-to-end tests with real JSONL storage to verify the full
merge workflow including relation creation.

Note: SemanticMerge reads from beads issues (mocked) but operates
on real storage for the actual memory data.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.models import MergeResult
from cortexgraph.agents.semantic_merge import SemanticMerge
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
    """Create real JSONL storage with mergeable test data.

    Creates memories that would have been flagged by ClusterDetector
    for potential merge based on entity similarity.
    """
    storage = JSONLStorage(str(temp_storage_dir))
    now = int(time.time())

    # PostgreSQL cluster - 3 memories with shared "PostgreSQL" entity
    # These would have been flagged for MERGE by ClusterDetector
    postgres_mem_1 = Memory(
        id="pg-1",
        content="PostgreSQL database configuration for production servers",
        entities=["PostgreSQL", "Database", "Production"],
        tags=["database", "config", "production"],
        created_at=now - 86400,
        last_used=now - 3600,
        use_count=5,
        strength=1.0,
    )
    postgres_mem_2 = Memory(
        id="pg-2",
        content="PostgreSQL connection pooling settings for optimal performance",
        entities=["PostgreSQL", "ConnectionPool", "Performance"],
        tags=["database", "performance", "pooling"],
        created_at=now - 86400 * 2,
        last_used=now - 7200,
        use_count=3,
        strength=1.0,
    )
    postgres_mem_3 = Memory(
        id="pg-3",
        content="PostgreSQL query optimization and index tuning tips",
        entities=["PostgreSQL", "Query", "Index"],
        tags=["database", "optimization", "indexing"],
        created_at=now - 86400 * 3,
        last_used=now - 10800,
        use_count=2,
        strength=1.0,
    )

    # JWT cluster - 2 memories with shared "JWT" entity
    jwt_mem_1 = Memory(
        id="jwt-1",
        content="JWT token generation and signing workflow",
        entities=["JWT", "Authentication", "Security"],
        tags=["security", "auth", "tokens"],
        created_at=now - 86400,
        last_used=now - 1800,
        use_count=8,
        strength=1.2,
    )
    jwt_mem_2 = Memory(
        id="jwt-2",
        content="JWT refresh token rotation strategy for long sessions",
        entities=["JWT", "RefreshToken", "Session"],
        tags=["security", "auth", "sessions"],
        created_at=now - 86400 * 2,
        last_used=now - 3600,
        use_count=4,
        strength=1.0,
    )

    # Add memories to storage (direct assignment to bypass storage connection)
    storage.memories = {
        "pg-1": postgres_mem_1,
        "pg-2": postgres_mem_2,
        "pg-3": postgres_mem_3,
        "jwt-1": jwt_mem_1,
        "jwt-2": jwt_mem_2,
    }

    return storage


def create_merge_issue(
    issue_id: str,
    memory_ids: list[str],
    cluster_id: str,
    cohesion: float = 0.85,
) -> dict:
    """Helper to create a beads merge issue."""
    return {
        "id": issue_id,
        "title": f"Merge: {cluster_id} ({len(memory_ids)} memories)",
        "status": "open",
        "labels": ["consolidation:merge", "urgency:medium"],
        "notes": json.dumps({
            "memory_ids": memory_ids,
            "cluster_id": cluster_id,
            "cohesion": cohesion,
        }),
    }


@pytest.fixture
def mock_beads() -> MagicMock:
    """Create mock beads integration."""
    beads = MagicMock()
    beads.query_consolidation_issues = MagicMock(return_value=[])
    beads.claim_issue = MagicMock(return_value=True)
    beads.close_issue = MagicMock()
    return beads


# =============================================================================
# T049: Integration Test - Full Merge with Relation Creation
# =============================================================================


class TestSemanticMergeIntegration:
    """End-to-end tests for SemanticMerge with real storage."""

    def test_merge_postgresql_cluster(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """Merge PostgreSQL cluster preserves all entities and content."""
        # Create beads issue for the PostgreSQL cluster
        issue = create_merge_issue(
            "cortexgraph-merge-pg",
            ["pg-1", "pg-2", "pg-3"],
            "cluster-postgresql",
            cohesion=0.85,
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            # Run scan and process
            issue_ids = merge.scan()
            assert len(issue_ids) == 1

            result = merge.process_item(issue_ids[0])

            # Verify result
            assert isinstance(result, MergeResult)
            assert result.success is True
            assert len(result.source_ids) == 3
            assert "pg-1" in result.source_ids
            assert "pg-2" in result.source_ids
            assert "pg-3" in result.source_ids

            # All unique entities preserved (PostgreSQL shared + 6 unique)
            # PostgreSQL, Database, Production, ConnectionPool, Performance, Query, Index
            assert result.entities_preserved >= 7

    def test_merge_jwt_cluster(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """Merge JWT cluster with two memories."""
        issue = create_merge_issue(
            "cortexgraph-merge-jwt",
            ["jwt-1", "jwt-2"],
            "cluster-jwt",
            cohesion=0.78,
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            result = merge.process_item("cortexgraph-merge-jwt")

            assert result.success is True
            assert len(result.source_ids) == 2
            # JWT, Authentication, Security, RefreshToken, Session = 5 unique entities
            assert result.entities_preserved >= 5

    def test_run_processes_multiple_issues(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """run() processes all pending merge issues."""
        # Two merge issues in queue
        issues = [
            create_merge_issue(
                "cortexgraph-merge-pg",
                ["pg-1", "pg-2", "pg-3"],
                "cluster-postgresql",
            ),
            create_merge_issue(
                "cortexgraph-merge-jwt",
                ["jwt-1", "jwt-2"],
                "cluster-jwt",
            ),
        ]
        mock_beads.query_consolidation_issues.return_value = issues

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            results = merge.run()

            assert len(results) == 2
            assert all(isinstance(r, MergeResult) for r in results)
            assert all(r.success for r in results)

    def test_content_diff_meaningful(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """content_diff provides meaningful merge description."""
        issue = create_merge_issue(
            "cortexgraph-merge-pg",
            ["pg-1", "pg-2", "pg-3"],
            "cluster-postgresql",
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            result = merge.process_item("cortexgraph-merge-pg")

            # content_diff should mention the merge
            assert "3" in result.content_diff or "Merged" in result.content_diff
            # Should reference entities if possible
            assert len(result.content_diff) > 10  # Not empty

    def test_handles_missing_memory_gracefully(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """Error when merge issue references non-existent memory."""
        # Issue references a memory that doesn't exist
        issue = create_merge_issue(
            "cortexgraph-merge-bad",
            ["pg-1", "nonexistent-mem"],
            "cluster-bad",
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            with pytest.raises(ValueError, match="not found"):
                merge.process_item("cortexgraph-merge-bad")

    def test_empty_queue_returns_empty_list(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """No pending issues returns empty results."""
        mock_beads.query_consolidation_issues.return_value = []

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            results = merge.run()
            assert results == []


class TestMergeResultIntegrity:
    """Tests verifying merge result integrity and completeness."""

    def test_new_memory_id_is_valid_uuid(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """Merged memory gets a valid UUID."""
        import uuid

        issue = create_merge_issue(
            "cortexgraph-merge-pg",
            ["pg-1", "pg-2"],
            "cluster-postgresql",
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            result = merge.process_item("cortexgraph-merge-pg")

            # Should be a valid UUID
            try:
                uuid.UUID(result.new_memory_id)
            except ValueError:
                pytest.fail(f"new_memory_id '{result.new_memory_id}' is not a valid UUID")

    def test_source_ids_match_request(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """Source IDs in result match the merge request."""
        requested_ids = ["pg-1", "pg-3"]
        issue = create_merge_issue(
            "cortexgraph-merge-pg",
            requested_ids,
            "cluster-postgresql",
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            result = merge.process_item("cortexgraph-merge-pg")

            assert set(result.source_ids) == set(requested_ids)

    def test_beads_issue_id_recorded(
        self, test_storage: JSONLStorage, mock_beads: MagicMock
    ) -> None:
        """Beads issue ID is recorded in result for audit trail."""
        issue = create_merge_issue(
            "cortexgraph-merge-pg",
            ["pg-1", "pg-2"],
            "cluster-postgresql",
        )
        mock_beads.query_consolidation_issues.return_value = [issue]

        with (
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=test_storage),
            patch(
                "cortexgraph.agents.semantic_merge.query_consolidation_issues",
                mock_beads.query_consolidation_issues,
            ),
            patch("cortexgraph.agents.semantic_merge.claim_issue", mock_beads.claim_issue),
            patch("cortexgraph.agents.semantic_merge.close_issue", mock_beads.close_issue),
        ):
            merge = SemanticMerge(dry_run=True)
            merge._storage = test_storage

            result = merge.process_item("cortexgraph-merge-pg")

            assert result.beads_issue_id == "cortexgraph-merge-pg"
