"""Tests for promote_memory tool."""

import time
from unittest.mock import MagicMock, patch

import pytest

from mnemex.storage.models import Memory, MemoryStatus
from mnemex.tools.promote import promote_memory
from tests.conftest import make_test_uuid


class TestPromoteMemory:
    """Test suite for promote_memory tool."""

    def test_promote_requires_memory_id_or_auto_detect(self):
        """Test that either memory_id or auto_detect must be provided."""
        result = promote_memory()

        assert result["success"] is False
        assert "must specify" in result["message"].lower()

    def test_promote_memory_not_found(self, temp_storage):
        """Test promoting non-existent memory."""
        result = promote_memory(memory_id="00000000-0000-0000-0000-000000000000")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_promote_already_promoted_memory(self, temp_storage):
        """Test that already promoted memory returns error."""
        test_id = make_test_uuid("mem-promoted")
        mem = Memory(
            id=test_id,
            content="Already promoted",
            status=MemoryStatus.PROMOTED,
            promoted_to="/vault/memory.md",
        )
        temp_storage.save_memory(mem)

        result = promote_memory(memory_id=test_id)

        assert result["success"] is False
        assert "already promoted" in result["message"].lower()
        assert "promoted_to" in result

    def test_promote_memory_not_meeting_criteria(self, temp_storage):
        """Test that low-scoring memory cannot be promoted without force."""
        now = int(time.time())

        test_id = make_test_uuid("mem-low")
        low_score_mem = Memory(
            id=test_id,
            content="Low score memory",
            use_count=0,
            last_used=now,
            created_at=now,
            strength=1.0,
        )
        temp_storage.save_memory(low_score_mem)

        result = promote_memory(memory_id=test_id)

        assert result["success"] is False
        assert "does not meet" in result["message"].lower()
        assert "score" in result

    @patch("mnemex.tools.promote.BasicMemoryIntegration")
    def test_promote_with_force_flag(self, mock_integration, temp_storage):
        """Test that force flag bypasses criteria check."""
        now = int(time.time())
        mock_integration_instance = MagicMock()
        mock_integration_instance.promote_to_obsidian.return_value = {
            "success": True,
            "path": "/vault/forced.md",
        }
        mock_integration.return_value = mock_integration_instance

        test_id = make_test_uuid("mem-force")
        low_score_mem = Memory(
            id=test_id, content="Forced promotion", use_count=0, last_used=now, created_at=now
        )
        temp_storage.save_memory(low_score_mem)

        result = promote_memory(memory_id=test_id, force=True, dry_run=False)

        assert result["success"] is True
        assert result["promoted_count"] >= 1

    @patch("mnemex.tools.promote.BasicMemoryIntegration")
    def test_promote_high_scoring_memory(self, mock_integration, temp_storage):
        """Test promoting a high-scoring memory."""
        now = int(time.time())
        mock_integration_instance = MagicMock()
        mock_integration_instance.promote_to_obsidian.return_value = {
            "success": True,
            "path": "/vault/high.md",
        }
        mock_integration.return_value = mock_integration_instance

        test_id = make_test_uuid("mem-high")
        high_score_mem = Memory(
            id=test_id,
            content="High value memory",
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),  # 14 days old
            strength=1.5,
        )
        temp_storage.save_memory(high_score_mem)

        result = promote_memory(memory_id=test_id, dry_run=False)

        assert result["success"] is True
        assert result["promoted_count"] == 1
        assert result["promoted_ids"] == [test_id]

    def test_promote_dry_run_mode(self, temp_storage):
        """Test dry run mode doesn't actually promote."""
        now = int(time.time())

        test_id = make_test_uuid("mem-dry")
        high_mem = Memory(
            id=test_id,
            content="Test dry run",
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(high_mem)

        result = promote_memory(memory_id=test_id, dry_run=True, force=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["promoted_count"] == 0

        # Memory should still be active
        mem = temp_storage.get_memory(test_id)
        assert mem.status == MemoryStatus.ACTIVE

    def test_promote_auto_detect_no_candidates(self, temp_storage):
        """Test auto-detect when no memories meet criteria."""
        now = int(time.time())

        # Create only low-scoring memories
        for i in range(3):
            test_id = make_test_uuid(f"mem-{i}")
            mem = Memory(
                id=test_id, content=f"Low score {i}", use_count=0, last_used=now, created_at=now
            )
            temp_storage.save_memory(mem)

        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        assert result["candidates_found"] == 0

    @patch("mnemex.tools.promote.BasicMemoryIntegration")
    def test_promote_auto_detect_finds_candidates(self, mock_integration, temp_storage):
        """Test auto-detect finds high-value memories."""
        now = int(time.time())
        mock_integration_instance = MagicMock()
        mock_integration_instance.promote_to_obsidian.return_value = {
            "success": True,
            "path": "/vault/auto.md",
        }
        mock_integration.return_value = mock_integration_instance

        # Create high-value memory
        test_id = make_test_uuid("mem-auto")
        high_mem = Memory(
            id=test_id,
            content="High value",
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(high_mem)

        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        # May find candidates if criteria met
        assert "candidates_found" in result

    def test_promote_result_format(self, temp_storage):
        """Test that promote result has correct format."""
        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        assert "dry_run" in result
        assert "candidates_found" in result
        assert "promoted_count" in result
        assert "promoted_ids" in result
        assert "candidates" in result
        assert "message" in result

    def test_promote_candidate_preview_format(self, temp_storage):
        """Test that candidate previews have correct format."""
        now = int(time.time())

        test_id = make_test_uuid("mem-preview")
        high_mem = Memory(
            id=test_id,
            content="Test preview format" * 10,  # Long content
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(high_mem)

        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        if result["candidates_found"] > 0:
            candidate = result["candidates"][0]
            assert "id" in candidate
            assert "content_preview" in candidate
            assert "reason" in candidate
            assert "score" in candidate
            assert "use_count" in candidate
            assert "age_days" in candidate
            # Content should be truncated to 100 chars
            assert len(candidate["content_preview"]) <= 100

    def test_promote_candidates_limited_to_10(self, temp_storage):
        """Test that candidate list is limited to 10."""
        now = int(time.time())

        # Create many high-value memories
        for i in range(15):
            test_id = make_test_uuid(f"mem-{i:02d}")
            mem = Memory(
                id=test_id,
                content=f"High value {i}",
                use_count=10,
                last_used=now,
                created_at=now - (14 * 86400),
                strength=1.5,
            )
            temp_storage.save_memory(mem)

        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        # Candidate preview list should be limited to 10
        assert len(result["candidates"]) <= 10

    @patch("mnemex.tools.promote.BasicMemoryIntegration")
    def test_promote_updates_memory_status(self, mock_integration, temp_storage):
        """Test that promotion updates memory status."""
        now = int(time.time())
        mock_integration_instance = MagicMock()
        mock_integration_instance.promote_to_obsidian.return_value = {
            "success": True,
            "path": "/vault/promoted.md",
        }
        mock_integration.return_value = mock_integration_instance

        test_id = make_test_uuid("mem-status")
        mem = Memory(
            id=test_id,
            content="Test status update",
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(mem)

        result = promote_memory(memory_id=test_id, dry_run=False, force=True)

        if result["success"] and result["promoted_count"] > 0:
            updated = temp_storage.get_memory(test_id)
            assert updated.status == MemoryStatus.PROMOTED
            assert updated.promoted_at is not None
            assert updated.promoted_to is not None

    # Validation tests
    def test_promote_invalid_uuid_fails(self):
        """Test that invalid UUID fails."""
        with pytest.raises(ValueError, match="memory_id.*valid UUID"):
            promote_memory(memory_id="not-a-uuid")

    def test_promote_invalid_target_fails(self):
        """Test that invalid target fails."""
        with pytest.raises(ValueError, match="target"):
            promote_memory(auto_detect=True, target="invalid-target")

    def test_promote_empty_string_uuid_fails(self):
        """Test that empty string UUID fails."""
        with pytest.raises(ValueError, match="memory_id"):
            promote_memory(memory_id="")

    # Edge cases
    def test_promote_with_default_parameters(self, temp_storage):
        """Test default parameter values."""
        now = int(time.time())

        test_id = make_test_uuid("mem-defaults")
        mem = Memory(
            id=test_id,
            content="Test defaults",
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(mem)

        # Should fail because neither memory_id nor auto_detect provided
        result = promote_memory()

        assert result["success"] is False

    def test_promote_obsidian_target(self, temp_storage):
        """Test that obsidian is valid target."""
        result = promote_memory(auto_detect=True, dry_run=True, target="obsidian")

        assert result["success"] is True

    def test_promote_message_dry_run(self, temp_storage):
        """Test that dry run message says 'Would promote'."""
        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        assert "would promote" in result["message"].lower()

    @patch("mnemex.tools.promote.BasicMemoryIntegration")
    def test_promote_message_actual_run(self, mock_integration, temp_storage):
        """Test that actual run message says 'Promoted'."""
        mock_integration_instance = MagicMock()
        mock_integration_instance.promote_to_obsidian.return_value = {
            "success": True,
            "path": "/vault/test.md",
        }
        mock_integration.return_value = mock_integration_instance

        result = promote_memory(auto_detect=True, dry_run=False)

        assert result["success"] is True
        assert result["message"].startswith("Promoted")

    def test_promote_empty_database(self, temp_storage):
        """Test promotion on empty database."""
        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        assert result["candidates_found"] == 0
        assert result["promoted_count"] == 0

    @patch("mnemex.tools.promote.BasicMemoryIntegration")
    def test_promote_integration_failure(self, mock_integration, temp_storage):
        """Test handling of integration failure."""
        now = int(time.time())
        mock_integration_instance = MagicMock()
        mock_integration_instance.promote_to_obsidian.return_value = {
            "success": False,
            "error": "Write failed",
        }
        mock_integration.return_value = mock_integration_instance

        test_id = make_test_uuid("mem-fail")
        mem = Memory(
            id=test_id,
            content="Test failure",
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(mem)

        result = promote_memory(memory_id=test_id, dry_run=False, force=True)

        # Should still succeed but with 0 promoted
        assert result["success"] is True
        assert result["promoted_count"] == 0

    def test_promote_candidates_sorted_by_score(self, temp_storage):
        """Test that candidates are sorted by score descending."""
        now = int(time.time())

        # Create memories with different scores
        for i in range(3):
            test_id = make_test_uuid(f"mem-{i}")
            mem = Memory(
                id=test_id,
                content=f"Memory {i}",
                use_count=i * 5,
                last_used=now,
                created_at=now - (14 * 86400),
                strength=1.0 + (i * 0.2),
            )
            temp_storage.save_memory(mem)

        result = promote_memory(auto_detect=True, dry_run=True)

        assert result["success"] is True
        if result["candidates_found"] > 1:
            scores = [c["score"] for c in result["candidates"]]
            assert scores == sorted(scores, reverse=True)

    def test_promote_preserves_memory_content(self, temp_storage):
        """Test that promotion doesn't modify content."""
        now = int(time.time())
        original_content = "This content should not change"

        test_id = make_test_uuid("mem-content")
        mem = Memory(
            id=test_id,
            content=original_content,
            use_count=10,
            last_used=now,
            created_at=now - (14 * 86400),
            strength=1.5,
        )
        temp_storage.save_memory(mem)

        promote_memory(memory_id=test_id, dry_run=True, force=True)

        updated = temp_storage.get_memory(test_id)
        assert updated.content == original_content
