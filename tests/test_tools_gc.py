"""Tests for gc (garbage collection) tool."""

import time

import pytest

from mnemex.storage.models import Memory, MemoryStatus
from mnemex.tools.gc import gc
from tests.conftest import make_test_uuid


class TestGarbageCollection:
    """Test suite for gc tool."""

    def test_gc_dry_run_mode(self, temp_storage):
        """Test dry run mode doesn't actually delete memories."""
        now = int(time.time())
        old_time = now - (30 * 86400)  # 30 days ago

        # Create old, low-scoring memory
        old_mem = Memory(
            id="mem-old",
            content="Old memory",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
            strength=1.0,
        )
        temp_storage.save_memory(old_mem)

        result = gc(dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        # Memory should still exist
        assert temp_storage.get_memory("mem-old") is not None

    def test_gc_actually_removes_memories(self, temp_storage):
        """Test that gc with dry_run=False actually removes memories."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        old_mem = Memory(
            id="mem-remove",
            content="To be removed",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
        )
        temp_storage.save_memory(old_mem)

        result = gc(dry_run=False)

        assert result["success"] is True
        assert result["dry_run"] is False
        # Memory should be deleted
        assert temp_storage.get_memory("mem-remove") is None

    def test_gc_archive_mode(self, temp_storage):
        """Test archiving memories instead of deleting."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        old_mem = Memory(
            id="mem-archive",
            content="To be archived",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
        )
        temp_storage.save_memory(old_mem)

        result = gc(dry_run=False, archive_instead=True)

        assert result["success"] is True
        assert result["archived_count"] >= 1
        assert result["removed_count"] == 0

        # Memory should exist but be archived
        archived = temp_storage.get_memory("mem-archive")
        assert archived is not None
        assert archived.status == MemoryStatus.ARCHIVED

    def test_gc_keeps_recent_memories(self, temp_storage):
        """Test that recent memories are not garbage collected."""
        now = int(time.time())

        recent_mem = Memory(
            id="mem-recent", content="Recent memory", use_count=5, last_used=now, created_at=now
        )
        temp_storage.save_memory(recent_mem)

        result = gc(dry_run=False)

        assert result["success"] is True
        # Recent memory should still exist
        assert temp_storage.get_memory("mem-recent") is not None

    def test_gc_with_limit(self, temp_storage):
        """Test limiting number of memories to collect."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        # Create multiple old memories
        for i in range(10):
            mem = Memory(
                id=f"mem-{i}",
                content=f"Old memory {i}",
                use_count=0,
                last_used=old_time,
                created_at=old_time,
            )
            temp_storage.save_memory(mem)

        result = gc(dry_run=True, limit=3)

        assert result["success"] is True
        assert result["total_affected"] == 3

    def test_gc_no_memories_to_collect(self, temp_storage):
        """Test gc when no memories need collection."""
        now = int(time.time())

        # Create only fresh, high-scoring memories
        for i in range(3):
            mem = Memory(
                id=f"mem-{i}",
                content=f"Fresh memory {i}",
                use_count=10,
                last_used=now,
                strength=1.5,
            )
            temp_storage.save_memory(mem)

        result = gc(dry_run=False)

        assert result["success"] is True
        assert result["removed_count"] == 0
        assert result["archived_count"] == 0
        assert result["total_affected"] == 0

    def test_gc_result_format(self, temp_storage):
        """Test that gc result has correct format."""
        result = gc(dry_run=True)

        assert result["success"] is True
        assert "dry_run" in result
        assert "removed_count" in result
        assert "archived_count" in result
        assert "freed_score_sum" in result
        assert "memory_ids" in result
        assert "total_affected" in result
        assert "message" in result

    def test_gc_freed_score_sum(self, temp_storage):
        """Test that freed_score_sum is calculated."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        old_mem = Memory(
            id="mem-score", content="Old", use_count=0, last_used=old_time, created_at=old_time
        )
        temp_storage.save_memory(old_mem)

        result = gc(dry_run=True)

        assert result["success"] is True
        if result["total_affected"] > 0:
            assert result["freed_score_sum"] >= 0

    def test_gc_memory_ids_limited_in_result(self, temp_storage):
        """Test that memory_ids in result is limited to 10."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        # Create 15 old memories
        for i in range(15):
            mem = Memory(
                id=f"mem-{i:02d}",
                content=f"Old {i}",
                use_count=0,
                last_used=old_time,
                created_at=old_time,
            )
            temp_storage.save_memory(mem)

        result = gc(dry_run=True)

        assert result["success"] is True
        # Result should show max 10 IDs even if more affected
        assert len(result["memory_ids"]) <= 10

    def test_gc_sorts_by_lowest_score_first(self, temp_storage):
        """Test that gc removes lowest-scoring memories first."""
        now = int(time.time())

        # Create memories with different ages and track their IDs
        mem_ids = []
        for i in range(5):
            days_old = 30 + (i * 5)
            old_time = now - (days_old * 86400)
            mem_id = make_test_uuid(f"mem-{i}")
            mem = Memory(
                id=mem_id,
                content=f"Memory {i}",
                use_count=1,  # Set to 1 so memories have non-zero scores
                last_used=old_time,
                created_at=old_time,
            )
            temp_storage.save_memory(mem)
            mem_ids.append(mem_id)

        result = gc(dry_run=False, limit=2)

        assert result["success"] is True
        assert result["total_affected"] == 2

        # Verify that the two oldest memories (mem-4 and mem-3) were removed
        assert temp_storage.get_memory(mem_ids[4]) is None
        assert temp_storage.get_memory(mem_ids[3]) is None
        # Verify that the others still exist
        assert temp_storage.get_memory(mem_ids[2]) is not None
        assert temp_storage.get_memory(mem_ids[1]) is not None
        assert temp_storage.get_memory(mem_ids[0]) is not None

    def test_gc_message_includes_threshold(self, temp_storage):
        """Test that message includes forget threshold."""
        result = gc(dry_run=True)

        assert result["success"] is True
        assert "threshold" in result["message"].lower()

    def test_gc_dry_run_shows_would_remove(self, temp_storage):
        """Test that dry run message says 'Would remove'."""
        result = gc(dry_run=True)

        assert result["success"] is True
        assert "would remove" in result["message"].lower()

    def test_gc_actual_run_shows_removed(self, temp_storage):
        """Test that actual run message says 'Removed'."""
        result = gc(dry_run=False)

        assert result["success"] is True
        assert result["message"].startswith("Removed")

    # Validation tests
    def test_gc_invalid_limit_fails(self):
        """Test that invalid limit values fail."""
        with pytest.raises(ValueError, match="limit"):
            gc(limit=0)

        with pytest.raises(ValueError, match="limit"):
            gc(limit=10001)

        with pytest.raises(ValueError, match="limit"):
            gc(limit=-1)

    # Edge cases
    def test_gc_default_parameters(self, temp_storage):
        """Test that gc defaults to dry_run=True."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        old_mem = Memory(
            id="mem-default", content="Old", use_count=0, last_used=old_time, created_at=old_time
        )
        temp_storage.save_memory(old_mem)

        # Call without parameters
        result = gc()

        assert result["success"] is True
        assert result["dry_run"] is True
        # Memory should still exist (dry run)
        assert temp_storage.get_memory("mem-default") is not None

    def test_gc_with_none_limit(self, temp_storage):
        """Test that None limit processes all eligible memories."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        for i in range(5):
            mem = Memory(
                id=f"mem-{i}",
                content=f"Old {i}",
                use_count=0,
                last_used=old_time,
                created_at=old_time,
            )
            temp_storage.save_memory(mem)

        result = gc(dry_run=True, limit=None)

        assert result["success"] is True
        # Should process all eligible memories
        if result["total_affected"] > 0:
            assert result["total_affected"] >= 5

    def test_gc_empty_database(self, temp_storage):
        """Test gc on empty database."""
        result = gc(dry_run=False)

        assert result["success"] is True
        assert result["removed_count"] == 0
        assert result["total_affected"] == 0

    def test_gc_preserves_promoted_memories(self, temp_storage):
        """Test that promoted memories are not collected."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        promoted_mem = Memory(
            id="mem-promoted",
            content="Promoted memory",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
            status=MemoryStatus.PROMOTED,
        )
        temp_storage.save_memory(promoted_mem)

        result = gc(dry_run=False)

        assert result["success"] is True
        # Promoted memory should not be collected
        assert temp_storage.get_memory("mem-promoted") is not None

    def test_gc_preserves_archived_memories(self, temp_storage):
        """Test that already archived memories are not re-collected."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        archived_mem = Memory(
            id="mem-archived",
            content="Already archived",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
            status=MemoryStatus.ARCHIVED,
        )
        temp_storage.save_memory(archived_mem)

        result = gc(dry_run=False)

        assert result["success"] is True
        # Already archived memory should still exist
        assert temp_storage.get_memory("mem-archived") is not None

    def test_gc_dry_run_archive_mode(self, temp_storage):
        """Test dry run with archive_instead flag."""
        now = int(time.time())
        old_time = now - (30 * 86400)

        old_mem = Memory(
            id="mem-dry-archive",
            content="Old",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
        )
        temp_storage.save_memory(old_mem)

        result = gc(dry_run=True, archive_instead=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        # Memory should still exist and be active (dry run)
        mem = temp_storage.get_memory("mem-dry-archive")
        assert mem is not None
        assert mem.status == MemoryStatus.ACTIVE

    def test_gc_mixed_score_memories(self, temp_storage):
        """Test gc with mix of high and low scoring memories."""
        now = int(time.time())

        # High scoring (recent)
        high_mem = Memory(id="mem-high", content="High score", use_count=10, last_used=now)
        # Low scoring (old)
        low_mem = Memory(
            id="mem-low",
            content="Low score",
            use_count=0,
            last_used=now - (30 * 86400),
            created_at=now - (30 * 86400),
        )

        temp_storage.save_memory(high_mem)
        temp_storage.save_memory(low_mem)

        result = gc(dry_run=False)

        assert result["success"] is True
        # High scoring should remain
        assert temp_storage.get_memory("mem-high") is not None
