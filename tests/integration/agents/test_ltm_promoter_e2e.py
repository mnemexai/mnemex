"""Integration tests for LTMPromoter (T061).

End-to-end tests with real (test) storage to verify the full
promotion workflow from scan to vault write.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.ltm_promoter import LTMPromoter
from cortexgraph.agents.models import PromotionResult
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Memory, MemoryStatus

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_vault_dir():
    """Create temporary directory for vault output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_storage(temp_storage_dir: Path) -> JSONLStorage:
    """Create real JSONL storage with test data.

    Creates memories with specific attributes that will
    meet or not meet promotion criteria.
    """
    storage = JSONLStorage(str(temp_storage_dir))
    now = int(time.time())

    # High-value memory - meets score threshold (0.65+)
    # Recent, high use_count, high strength
    high_score_memory = Memory(
        id="mem-high-score",
        content="Critical PostgreSQL production database configuration",
        entities=["PostgreSQL", "Database", "Production"],
        tags=["database", "config", "production"],
        created_at=now - 86400 * 3,  # 3 days ago
        last_used=now - 3600,  # 1 hour ago
        use_count=15,  # High use count
        strength=1.5,  # High strength
        status=MemoryStatus.ACTIVE,
    )

    # High use count memory - meets use_count threshold (5+ in 14 days)
    high_use_memory = Memory(
        id="mem-high-use",
        content="JWT authentication workflow for API security",
        entities=["JWT", "Authentication", "API"],
        tags=["security", "auth", "api"],
        created_at=now - 86400 * 10,  # 10 days ago (within 14 day window)
        last_used=now - 86400 * 2,  # 2 days ago
        use_count=8,  # High use count
        strength=1.2,
        status=MemoryStatus.ACTIVE,
    )

    # Low-value memory - should NOT be promoted
    # Old, low use, low strength
    low_value_memory = Memory(
        id="mem-low-value",
        content="Random note about the weather",
        entities=["Weather"],
        tags=["misc"],
        created_at=now - 86400 * 60,  # 60 days ago
        last_used=now - 86400 * 45,  # 45 days ago
        use_count=1,
        strength=1.0,
        status=MemoryStatus.ACTIVE,
    )

    # Already promoted - should be excluded from scan
    already_promoted = Memory(
        id="mem-promoted",
        content="Previously promoted configuration",
        entities=["Config"],
        tags=["config"],
        created_at=now - 86400 * 7,
        last_used=now - 86400,
        use_count=20,
        strength=1.8,
        status=MemoryStatus.PROMOTED,
    )

    # Archived memory - should be excluded from scan
    archived_memory = Memory(
        id="mem-archived",
        content="Archived old notes",
        entities=["Archive"],
        tags=["archive"],
        created_at=now - 86400 * 90,
        last_used=now - 86400 * 80,
        use_count=2,
        strength=1.0,
        status=MemoryStatus.ARCHIVED,
    )

    storage.memories = {
        "mem-high-score": high_score_memory,
        "mem-high-use": high_use_memory,
        "mem-low-value": low_value_memory,
        "mem-promoted": already_promoted,
        "mem-archived": archived_memory,
    }

    return storage


@pytest.fixture
def mock_vault_writer():
    """Create mock vault writer."""
    writer = MagicMock()
    writer.write_note = MagicMock(return_value="memories/test-memory.md")
    writer.find_note_by_title = MagicMock(return_value=None)  # No duplicates
    return writer


@pytest.fixture
def mock_beads_integration():
    """Mock beads integration for tracking."""
    return {
        "create_consolidation_issue": MagicMock(return_value="cortexgraph-test-001"),
        "close_issue": MagicMock(),
    }


@pytest.fixture
def ltm_promoter_with_storage(
    test_storage: JSONLStorage,
    mock_vault_writer: MagicMock,
    mock_beads_integration: dict,
    temp_vault_dir: Path,
) -> LTMPromoter:
    """Create LTMPromoter with real storage and mocked vault writer."""
    with (
        patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=test_storage),
        patch(
            "cortexgraph.agents.ltm_promoter.MarkdownWriter",
            return_value=mock_vault_writer,
        ),
        patch(
            "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
            mock_beads_integration["create_consolidation_issue"],
        ),
        patch(
            "cortexgraph.agents.ltm_promoter.close_issue",
            mock_beads_integration["close_issue"],
        ),
    ):
        promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
        promoter._storage = test_storage
        promoter._writer = mock_vault_writer
        return promoter


# =============================================================================
# T061: Integration Test - Full Promotion Workflow
# =============================================================================


class TestPromotionEndToEnd:
    """End-to-end integration tests for promotion workflow."""

    def test_full_promotion_workflow(
        self, ltm_promoter_with_storage: LTMPromoter, test_storage: JSONLStorage
    ) -> None:
        """Test complete promotion from scan to results."""
        promoter = ltm_promoter_with_storage

        # Execute full run
        results = promoter.run()

        # All results should be PromotionResult
        for result in results:
            assert isinstance(result, PromotionResult)

        # Should have found some promotion candidates
        assert len(results) >= 1

        # Low-value memory should NOT be promoted
        result_ids = {r.memory_id for r in results}
        assert "mem-low-value" not in result_ids

    def test_excludes_already_promoted(self, ltm_promoter_with_storage: LTMPromoter) -> None:
        """Test already-promoted memories are excluded from scan."""
        promoter = ltm_promoter_with_storage

        # Scan for candidates
        candidates = promoter.scan()

        # Already promoted memory should not appear
        assert "mem-promoted" not in candidates

    def test_excludes_archived_memories(self, ltm_promoter_with_storage: LTMPromoter) -> None:
        """Test archived memories are excluded from scan."""
        promoter = ltm_promoter_with_storage

        candidates = promoter.scan()

        assert "mem-archived" not in candidates

    def test_promotion_result_fields(self, ltm_promoter_with_storage: LTMPromoter) -> None:
        """Test PromotionResult has correct field values."""
        promoter = ltm_promoter_with_storage

        results = promoter.run()

        if results:
            result = results[0]

            # Required fields
            assert result.memory_id is not None
            assert isinstance(result.criteria_met, list)
            assert len(result.criteria_met) >= 1
            assert isinstance(result.success, bool)

            # Criteria should be valid
            valid_criteria = {
                "score_threshold",
                "use_count_threshold",
                "review_count_threshold",
            }
            for criterion in result.criteria_met:
                assert criterion in valid_criteria

    def test_dry_run_no_vault_writes(
        self,
        test_storage: JSONLStorage,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
        temp_vault_dir: Path,
    ) -> None:
        """Test dry_run mode doesn't write to vault."""
        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
            promoter._storage = test_storage
            promoter._writer = mock_vault_writer

            promoter.run()

            # Vault writer should NOT be called in dry_run mode
            mock_vault_writer.write_note.assert_not_called()

    def test_dry_run_no_status_updates(
        self,
        test_storage: JSONLStorage,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
        temp_vault_dir: Path,
    ) -> None:
        """Test dry_run mode doesn't update memory status."""
        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
            promoter._storage = test_storage
            promoter._writer = mock_vault_writer

            # Capture original statuses
            original_statuses = {mid: m.status for mid, m in test_storage.memories.items()}

            promoter.run()

            # Status should NOT change in dry_run
            for mid, original_status in original_statuses.items():
                assert test_storage.memories[mid].status == original_status

    def test_stats_reflect_run(self, ltm_promoter_with_storage: LTMPromoter) -> None:
        """Test statistics are updated correctly after run."""
        promoter = ltm_promoter_with_storage

        # Initial stats should be zero
        initial_stats = promoter.get_stats()
        assert initial_stats["processed"] == 0

        # Run promoter
        results = promoter.run()

        # Stats should reflect processed count
        final_stats = promoter.get_stats()
        assert final_stats["processed"] == len(results)
        assert final_stats["errors"] == 0


class TestPromotionEdgeCases:
    """Integration tests for edge cases."""

    def test_empty_storage(
        self,
        temp_storage_dir: Path,
        temp_vault_dir: Path,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
    ) -> None:
        """Test behavior with empty storage."""
        storage = JSONLStorage(str(temp_storage_dir))
        storage.memories = {}

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
            promoter._storage = storage

            results = promoter.run()

            assert results == []
            assert promoter.get_stats()["processed"] == 0

    def test_all_already_promoted(
        self,
        temp_storage_dir: Path,
        temp_vault_dir: Path,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
    ) -> None:
        """Test behavior when all memories are already promoted."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        promoted = Memory(
            id="promoted",
            content="Already in vault",
            created_at=now - 86400,
            last_used=now - 3600,
            use_count=10,
            strength=1.5,
            status=MemoryStatus.PROMOTED,
        )

        storage.memories = {"promoted": promoted}

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
            promoter._storage = storage

            results = promoter.run()

            assert results == []

    def test_no_promotable_memories(
        self,
        temp_storage_dir: Path,
        temp_vault_dir: Path,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
    ) -> None:
        """Test behavior when no memories meet promotion criteria."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Low-value memory that won't meet criteria
        low_value = Memory(
            id="low",
            content="Unimportant note",
            created_at=now - 86400 * 60,  # 60 days old
            last_used=now - 86400 * 50,  # 50 days since use
            use_count=1,
            strength=1.0,
            status=MemoryStatus.ACTIVE,
        )

        storage.memories = {"low": low_value}

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
            promoter._storage = storage

            results = promoter.run()

            assert results == []

    def test_memory_with_empty_entities(
        self,
        temp_storage_dir: Path,
        temp_vault_dir: Path,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
    ) -> None:
        """Test promotion handles memory without entities."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        # Promotable memory with empty entities
        no_entities = Memory(
            id="no-entities",
            content="Important content without entities",
            entities=[],  # Empty entities
            tags=["test"],
            created_at=now - 86400 * 3,
            last_used=now - 3600,
            use_count=15,
            strength=1.5,
            status=MemoryStatus.ACTIVE,
        )

        storage.memories = {"no-entities": no_entities}

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=True, vault_path=temp_vault_dir)
            promoter._storage = storage

            # Should not crash even with empty entities
            results = promoter.run()

            # Memory should still be processed if it meets criteria
            if results:
                assert results[0].memory_id == "no-entities"
                assert results[0].success is True


class TestPromotionLiveMode:
    """Integration tests for live (non-dry-run) mode with mocked dependencies."""

    def test_live_mode_calls_vault_writer(
        self,
        test_storage: JSONLStorage,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
        temp_vault_dir: Path,
    ) -> None:
        """Test live mode actually calls vault writer."""
        # Add update_memory to storage mock
        test_storage.update_memory = MagicMock()

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=False, vault_path=temp_vault_dir)  # Live mode
            promoter._storage = test_storage
            promoter._writer = mock_vault_writer

            results = promoter.run()

            if results:
                # Vault writer should be called in live mode
                assert mock_vault_writer.write_note.call_count == len(results)

    def test_live_mode_creates_beads_issue(
        self,
        test_storage: JSONLStorage,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
        temp_vault_dir: Path,
    ) -> None:
        """Test live mode creates beads issues for audit trail."""
        test_storage.update_memory = MagicMock()

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=False, vault_path=temp_vault_dir)
            promoter._storage = test_storage
            promoter._writer = mock_vault_writer

            results = promoter.run()

            if results:
                # Beads issue should be created for each promotion
                assert mock_beads_integration["create_consolidation_issue"].call_count == len(
                    results
                )
                # Issue should be closed after successful promotion
                assert mock_beads_integration["close_issue"].call_count == len(results)

    def test_live_mode_updates_memory_status(
        self,
        test_storage: JSONLStorage,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
        temp_vault_dir: Path,
    ) -> None:
        """Test live mode updates memory status to PROMOTED."""
        test_storage.update_memory = MagicMock()

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=False, vault_path=temp_vault_dir)
            promoter._storage = test_storage
            promoter._writer = mock_vault_writer

            results = promoter.run()

            if results:
                # update_memory should be called with status=PROMOTED
                for result in results:
                    test_storage.update_memory.assert_any_call(
                        result.memory_id, status=MemoryStatus.PROMOTED
                    )

    def test_live_mode_result_has_vault_path(
        self,
        test_storage: JSONLStorage,
        mock_vault_writer: MagicMock,
        mock_beads_integration: dict,
        temp_vault_dir: Path,
    ) -> None:
        """Test live mode result includes vault path."""
        test_storage.update_memory = MagicMock()
        mock_vault_writer.write_note = MagicMock(return_value="memories/promoted-note.md")

        with (
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.MarkdownWriter",
                return_value=mock_vault_writer,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration["create_consolidation_issue"],
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration["close_issue"],
            ),
        ):
            promoter = LTMPromoter(dry_run=False, vault_path=temp_vault_dir)
            promoter._storage = test_storage
            promoter._writer = mock_vault_writer

            results = promoter.run()

            if results:
                # Live mode results should have vault path
                assert results[0].vault_path is not None
                assert results[0].vault_path == "memories/promoted-note.md"
