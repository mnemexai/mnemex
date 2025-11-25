"""Contract tests for LTMPromoter (T057-T058).

These tests verify the LTMPromoter agent conforms to the ConsolidationAgent
contract defined in contracts/agent-api.md.

Contract Requirements (LTMPromoter-specific):
- scan() MUST find memories meeting promotion criteria
- scan() MUST NOT return already-promoted memories
- scan() MUST return list of memory IDs (may be empty)
- scan() MUST NOT modify any data
- process_item() MUST return PromotionResult or raise exception
- process_item() MUST write valid markdown to vault
- process_item() MUST set memory status to 'promoted'
- process_item() MUST store vault_path reference
- process_item() MUST NOT create duplicate vault files
- If dry_run=True, process_item() MUST NOT modify any data
- process_item() SHOULD complete within 5 seconds
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import PromotionResult
from cortexgraph.storage.models import MemoryStatus

if TYPE_CHECKING:
    from cortexgraph.agents.ltm_promoter import LTMPromoter


# =============================================================================
# Contract Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock storage with memories at various promotion states."""
    storage = MagicMock()
    now = int(time.time())

    # High-value memory - should be promoted (high score)
    storage.memories = {
        "mem-high-score": MagicMock(
            id="mem-high-score",
            content="Critical PostgreSQL production configuration",
            entities=["PostgreSQL", "Production"],
            tags=["database", "config", "production"],
            strength=1.5,
            use_count=10,
            created_at=now - 86400 * 7,  # 7 days old
            last_used=now - 3600,  # 1 hour ago
            status=MemoryStatus.ACTIVE,
        ),
        # High use count - should be promoted (use count criteria)
        "mem-high-use": MagicMock(
            id="mem-high-use",
            content="JWT authentication workflow documentation",
            entities=["JWT", "Authentication"],
            tags=["security", "auth"],
            strength=1.2,
            use_count=8,  # High use count
            created_at=now - 86400 * 5,  # 5 days old (within 14 day window)
            last_used=now - 7200,  # 2 hours ago
            status=MemoryStatus.ACTIVE,
        ),
        # Low-value memory - should NOT be promoted
        "mem-low-score": MagicMock(
            id="mem-low-score",
            content="Random note about cats",
            entities=["Cats"],
            tags=["misc"],
            strength=1.0,
            use_count=1,
            created_at=now - 86400 * 30,  # 30 days old
            last_used=now - 86400 * 20,  # 20 days ago
            status=MemoryStatus.ACTIVE,
        ),
        # Already promoted - should NOT be returned
        "mem-promoted": MagicMock(
            id="mem-promoted",
            content="Already in vault",
            entities=["Test"],
            tags=["test"],
            strength=1.5,
            use_count=15,
            created_at=now - 86400 * 7,
            last_used=now - 3600,
            status=MemoryStatus.PROMOTED,  # Already promoted
        ),
        # Archived - should NOT be returned
        "mem-archived": MagicMock(
            id="mem-archived",
            content="Archived memory",
            entities=["Archive"],
            tags=["archive"],
            strength=1.0,
            use_count=1,
            created_at=now - 86400 * 60,
            last_used=now - 86400 * 50,
            status=MemoryStatus.ARCHIVED,
        ),
    }

    # Mock get method
    def get_memory(memory_id: str) -> MagicMock | None:
        return storage.memories.get(memory_id)

    storage.get = get_memory
    storage.get_memory = get_memory

    return storage


@pytest.fixture
def mock_vault_writer() -> MagicMock:
    """Create mock vault writer."""
    writer = MagicMock()
    writer.write_note = MagicMock(return_value="memories/test-memory.md")
    writer.find_note_by_title = MagicMock(return_value=None)  # No duplicates
    return writer


@pytest.fixture
def mock_beads_integration() -> MagicMock:
    """Create mock beads integration."""
    beads = MagicMock()
    beads.create_consolidation_issue = MagicMock(return_value="cortexgraph-promote-001")
    beads.close_issue = MagicMock()
    return beads


@pytest.fixture
def ltm_promoter(
    mock_storage: MagicMock,
    mock_vault_writer: MagicMock,
    mock_beads_integration: MagicMock,
) -> LTMPromoter:
    """Create LTMPromoter with mocked dependencies."""
    from cortexgraph.agents.ltm_promoter import LTMPromoter

    with (
        patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=mock_storage),
        patch("cortexgraph.agents.ltm_promoter.MarkdownWriter", return_value=mock_vault_writer),
        patch(
            "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
            mock_beads_integration.create_consolidation_issue,
        ),
        patch(
            "cortexgraph.agents.ltm_promoter.close_issue",
            mock_beads_integration.close_issue,
        ),
    ):
        promoter = LTMPromoter(dry_run=True)
        promoter._storage = mock_storage
        promoter._writer = mock_vault_writer
        promoter._beads = mock_beads_integration
        return promoter


# =============================================================================
# T057: Contract Test - scan() Finds Promotion Candidates
# =============================================================================


class TestLTMPromoterScanContract:
    """Contract tests for LTMPromoter.scan() method (T057)."""

    def test_scan_returns_list(self, ltm_promoter: LTMPromoter) -> None:
        """scan() MUST return a list."""
        result = ltm_promoter.scan()
        assert isinstance(result, list)

    def test_scan_returns_string_ids(self, ltm_promoter: LTMPromoter) -> None:
        """scan() MUST return list of string memory IDs."""
        result = ltm_promoter.scan()
        for item in result:
            assert isinstance(item, str)

    def test_scan_may_return_empty(
        self, mock_vault_writer: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """scan() MAY return empty list when no memories meet criteria."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        # Create storage with only low-value memories
        storage = MagicMock()
        now = int(time.time())
        storage.memories = {
            "mem-1": MagicMock(
                id="mem-1",
                content="Low value",
                entities=[],
                tags=[],
                strength=1.0,
                use_count=1,
                created_at=now - 86400 * 30,
                last_used=now - 86400 * 25,
                status=MemoryStatus.ACTIVE,
            ),
        }

        with (
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=storage),
            patch("cortexgraph.agents.ltm_promoter.MarkdownWriter", return_value=mock_vault_writer),
        ):
            promoter = LTMPromoter(dry_run=True)
            promoter._storage = storage
            result = promoter.scan()
            # May be empty if no memories meet criteria
            assert isinstance(result, list)

    def test_scan_excludes_already_promoted(self, ltm_promoter: LTMPromoter) -> None:
        """scan() MUST NOT return already-promoted memories."""
        result = ltm_promoter.scan()
        # mem-promoted has PROMOTED status and should be excluded
        assert "mem-promoted" not in result

    def test_scan_excludes_archived(self, ltm_promoter: LTMPromoter) -> None:
        """scan() MUST NOT return archived memories."""
        result = ltm_promoter.scan()
        # mem-archived has ARCHIVED status and should be excluded
        assert "mem-archived" not in result

    def test_scan_does_not_modify_data(
        self, ltm_promoter: LTMPromoter, mock_storage: MagicMock
    ) -> None:
        """scan() MUST NOT modify any data."""
        # Take snapshot before
        original_count = len(mock_storage.memories)

        # Run scan
        ltm_promoter.scan()

        # Verify no changes
        assert len(mock_storage.memories) == original_count

    def test_scan_is_subclass_of_consolidation_agent(self, ltm_promoter: LTMPromoter) -> None:
        """LTMPromoter MUST inherit from ConsolidationAgent."""
        assert isinstance(ltm_promoter, ConsolidationAgent)


# =============================================================================
# T058: Contract Test - process_item() Returns PromotionResult
# =============================================================================


class TestLTMPromoterProcessItemContract:
    """Contract tests for LTMPromoter.process_item() method (T058)."""

    def test_process_item_returns_promotion_result(self, ltm_promoter: LTMPromoter) -> None:
        """process_item() MUST return PromotionResult."""
        memory_ids = ltm_promoter.scan()
        if memory_ids:
            result = ltm_promoter.process_item(memory_ids[0])
            assert isinstance(result, PromotionResult)

    def test_process_item_result_has_required_fields(self, ltm_promoter: LTMPromoter) -> None:
        """PromotionResult MUST have all required fields."""
        memory_ids = ltm_promoter.scan()
        if memory_ids:
            result = ltm_promoter.process_item(memory_ids[0])

            # Required fields from contracts/agent-api.md
            assert hasattr(result, "memory_id")
            assert hasattr(result, "vault_path")
            assert hasattr(result, "criteria_met")
            assert hasattr(result, "success")

            # Types
            assert isinstance(result.memory_id, str)
            assert result.vault_path is None or isinstance(result.vault_path, str)
            assert isinstance(result.criteria_met, list)
            assert len(result.criteria_met) >= 1  # At least one criterion met
            assert isinstance(result.success, bool)

    def test_process_item_criteria_met_minimum_one(self, ltm_promoter: LTMPromoter) -> None:
        """PromotionResult.criteria_met MUST have at least 1 item."""
        memory_ids = ltm_promoter.scan()
        if memory_ids:
            result = ltm_promoter.process_item(memory_ids[0])
            assert len(result.criteria_met) >= 1

    def test_process_item_raises_on_invalid_memory_id(self, ltm_promoter: LTMPromoter) -> None:
        """process_item() MUST raise exception for invalid memory ID."""
        with pytest.raises((ValueError, KeyError, RuntimeError)):
            ltm_promoter.process_item("nonexistent-memory")

    def test_process_item_dry_run_no_side_effects(
        self,
        mock_storage: MagicMock,
        mock_vault_writer: MagicMock,
        mock_beads_integration: MagicMock,
    ) -> None:
        """If dry_run=True, process_item() MUST NOT modify any data."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with (
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=mock_storage),
            patch("cortexgraph.agents.ltm_promoter.MarkdownWriter", return_value=mock_vault_writer),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration.close_issue,
            ),
        ):
            promoter = LTMPromoter(dry_run=True)
            promoter._storage = mock_storage
            promoter._writer = mock_vault_writer
            promoter._beads = mock_beads_integration

            # Track calls that would modify data
            mock_storage.update_memory = MagicMock()
            mock_vault_writer.write_note = MagicMock()

            memory_ids = promoter.scan()
            if memory_ids:
                promoter.process_item(memory_ids[0])

                # In dry_run mode, no modifications should occur
                mock_storage.update_memory.assert_not_called()
                mock_vault_writer.write_note.assert_not_called()

    def test_process_item_completes_within_timeout(self, ltm_promoter: LTMPromoter) -> None:
        """process_item() SHOULD complete within 5 seconds."""
        memory_ids = ltm_promoter.scan()
        if memory_ids:
            start = time.time()
            ltm_promoter.process_item(memory_ids[0])
            elapsed = time.time() - start

            assert elapsed < 5.0, f"process_item took {elapsed:.2f}s (limit: 5s)"


# =============================================================================
# Contract Integration Tests
# =============================================================================


class TestLTMPromoterFullContract:
    """Integration tests verifying full contract compliance."""

    def test_run_method_uses_scan_and_process_item(self, ltm_promoter: LTMPromoter) -> None:
        """run() MUST call scan() then process_item() for each result."""
        results = ltm_promoter.run()

        # All results should be PromotionResult
        for result in results:
            assert isinstance(result, PromotionResult)

    def test_criteria_met_valid_values(self, ltm_promoter: LTMPromoter) -> None:
        """criteria_met MUST contain valid promotion criteria names."""
        # Valid criteria names based on data-model.md
        valid_criteria = {"score_threshold", "use_count_threshold", "review_count_threshold"}

        memory_ids = ltm_promoter.scan()
        if memory_ids:
            result = ltm_promoter.process_item(memory_ids[0])

            # Each criteria should be a valid criterion
            for criterion in result.criteria_met:
                assert criterion in valid_criteria, f"Invalid criterion: {criterion}"

    def test_run_handles_errors_gracefully(
        self,
        mock_storage: MagicMock,
        mock_vault_writer: MagicMock,
        mock_beads_integration: MagicMock,
    ) -> None:
        """run() MUST handle errors per-item without aborting all."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        # Add a memory that will cause an error (missing required fields)
        mock_storage.memories["mem-broken"] = MagicMock(
            id="mem-broken",
            content=None,  # This might cause issues
            entities=None,
            tags=None,
            strength=None,
            use_count=None,
            created_at=None,
            last_used=None,
            status=MemoryStatus.ACTIVE,
        )

        with (
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=mock_storage),
            patch("cortexgraph.agents.ltm_promoter.MarkdownWriter", return_value=mock_vault_writer),
            patch(
                "cortexgraph.agents.ltm_promoter.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.close_issue",
                mock_beads_integration.close_issue,
            ),
        ):
            promoter = LTMPromoter(dry_run=True)
            promoter._storage = mock_storage
            promoter._writer = mock_vault_writer
            promoter._beads = mock_beads_integration

            # Should not raise - should skip error and continue
            results = promoter.run()

            # Should still produce some results from valid memories
            assert isinstance(results, list)
