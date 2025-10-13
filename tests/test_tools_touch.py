"""Tests for touch_memory tool."""

import time

import pytest

from mnemex.storage.models import Memory, MemoryMetadata
from mnemex.tools.touch import touch_memory
from tests.conftest import make_test_uuid


class TestTouchMemory:
    """Test suite for touch_memory tool."""

    def test_touch_basic_reinforcement(self, temp_storage):
        """Test basic memory reinforcement without strength boost."""
        test_id = make_test_uuid("test-123")

        # Create memory with old timestamp to ensure touch updates it
        old_time = int(time.time()) - 10  # 10 seconds ago
        mem = Memory(
            id=test_id, content="Test memory", use_count=0, strength=1.0, last_used=old_time
        )
        temp_storage.save_memory(mem)

        # Get the saved memory to check its timestamp
        saved_mem = temp_storage.get_memory(test_id)
        original_last_used = saved_mem.last_used

        result = touch_memory(memory_id=test_id, boost_strength=False)

        assert result["success"] is True
        assert result["memory_id"] == test_id
        assert result["use_count"] == 1
        assert result["strength"] == pytest.approx(1.0)

        # Verify memory was updated
        updated = temp_storage.get_memory(test_id)
        assert updated.use_count == 1
        assert updated.last_used > original_last_used

    def test_touch_increments_use_count(self, temp_storage):
        """Test that touch increments use_count correctly."""
        test_id = make_test_uuid("test-456")
        mem = Memory(id=test_id, content="Test", use_count=5)
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert result["use_count"] == 6

        updated = temp_storage.get_memory(test_id)
        assert updated.use_count == 6

    def test_touch_with_strength_boost(self, temp_storage):
        """Test touching with strength boost."""
        test_id = make_test_uuid("test-789")
        mem = Memory(id=test_id, content="Test", strength=1.0)
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id, boost_strength=True)

        assert result["success"] is True
        assert result["strength"] == pytest.approx(1.1)

        updated = temp_storage.get_memory(test_id)
        assert updated.strength == pytest.approx(1.1)

    def test_touch_strength_capped_at_2(self, temp_storage):
        """Test that strength is capped at 2.0."""
        test_id = make_test_uuid("test-cap")
        mem = Memory(id=test_id, content="Test", strength=1.95)
        temp_storage.save_memory(mem)

        # First boost: 1.95 + 0.1 = 2.05, capped to 2.0
        result = touch_memory(memory_id=test_id, boost_strength=True)

        assert result["success"] is True
        assert result["strength"] == pytest.approx(2.0)

        # Second boost: should stay at 2.0
        result2 = touch_memory(memory_id=test_id, boost_strength=True)

        assert result2["success"] is True
        assert result2["strength"] == pytest.approx(2.0)

        updated = temp_storage.get_memory(test_id)
        assert updated.strength == pytest.approx(2.0)

    def test_touch_multiple_times(self, temp_storage):
        """Test touching same memory multiple times."""
        test_id = make_test_uuid("test-multi")
        mem = Memory(id=test_id, content="Test", use_count=0)
        temp_storage.save_memory(mem)

        for i in range(1, 6):
            result = touch_memory(memory_id=test_id)
            assert result["success"] is True
            assert result["use_count"] == i

        updated = temp_storage.get_memory(test_id)
        assert updated.use_count == 5

    def test_touch_improves_score(self, temp_storage):
        """Test that touching improves the decay score."""
        now = int(time.time())
        old_time = now - (7 * 86400)  # 7 days ago

        test_id = make_test_uuid("test-score")
        mem = Memory(
            id=test_id,
            content="Old memory",
            use_count=1,
            last_used=old_time,
            created_at=old_time,
        )
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert result["new_score"] > result["old_score"]

    def test_touch_memory_not_found(self, temp_storage):
        """Test touching non-existent memory."""
        result = touch_memory(memory_id="00000000-0000-0000-0000-000000000000")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_touch_result_format(self, temp_storage):
        """Test that touch result has correct format."""
        test_id = make_test_uuid("test-format")
        mem = Memory(id=test_id, content="Test")
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert "memory_id" in result
        assert "old_score" in result
        assert "new_score" in result
        assert "use_count" in result
        assert "strength" in result
        assert "message" in result

    def test_touch_updates_last_used_timestamp(self, temp_storage):
        """Test that last_used timestamp is updated."""
        before = int(time.time())
        test_id = make_test_uuid("test-time")
        mem = Memory(id=test_id, content="Test", last_used=before - 1000)
        temp_storage.save_memory(mem)

        time.sleep(0.1)
        result = touch_memory(memory_id=test_id)
        after = int(time.time())

        assert result["success"] is True

        updated = temp_storage.get_memory(test_id)
        assert before <= updated.last_used <= after

    def test_touch_with_tags_preserves_metadata(self, temp_storage):
        """Test that touching preserves memory metadata."""
        test_id = make_test_uuid("test-meta")
        mem = Memory(
            id=test_id,
            content="Test with metadata",
            meta=MemoryMetadata(
                tags=["important", "project"], source="user-input", context="Testing"
            ),
            entities=["TestEntity"],
        )
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id, boost_strength=True)

        assert result["success"] is True

        updated = temp_storage.get_memory(test_id)
        assert updated.meta.tags == ["important", "project"]
        assert updated.meta.source == "user-input"
        assert updated.meta.context == "Testing"
        assert updated.entities == ["TestEntity"]

    # Validation tests
    def test_touch_invalid_uuid_fails(self):
        """Test that invalid UUID fails validation."""
        with pytest.raises(ValueError, match="memory_id.*valid UUID"):
            touch_memory(memory_id="not-a-uuid")

    def test_touch_empty_string_fails(self):
        """Test that empty string fails validation."""
        with pytest.raises(ValueError, match="memory_id"):
            touch_memory(memory_id="")

    # Edge cases
    def test_touch_with_default_boost_strength(self, temp_storage):
        """Test that boost_strength defaults to False."""
        test_id = make_test_uuid("test-default")
        mem = Memory(id=test_id, content="Test", strength=1.0)
        temp_storage.save_memory(mem)

        # Call without boost_strength parameter
        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert result["strength"] == pytest.approx(1.0)

    def test_touch_at_max_strength(self, temp_storage):
        """Test touching memory already at max strength."""
        test_id = make_test_uuid("test-max")
        mem = Memory(id=test_id, content="Test", strength=2.0)
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id, boost_strength=True)

        assert result["success"] is True
        assert result["strength"] == pytest.approx(2.0)

    def test_touch_incremental_strength_boosts(self, temp_storage):
        """Test multiple incremental strength boosts."""
        test_id = make_test_uuid("test-incr")
        mem = Memory(id=test_id, content="Test", strength=1.0)
        temp_storage.save_memory(mem)

        expected_strengths = [1.1, 1.2, 1.3, 1.4, 1.5]

        for expected in expected_strengths:
            result = touch_memory(memory_id=test_id, boost_strength=True)
            assert result["success"] is True
            assert result["strength"] == pytest.approx(expected, rel=0.01)

    def test_touch_with_high_use_count(self, temp_storage):
        """Test touching memory with high use count."""
        test_id = make_test_uuid("test-high")
        mem = Memory(id=test_id, content="Test", use_count=999)
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert result["use_count"] == 1000

    def test_touch_recently_created_memory(self, temp_storage):
        """Test touching memory that was just created."""
        test_id = make_test_uuid("test-new")
        mem = Memory(id=test_id, content="Just created")
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert result["use_count"] == 1

    def test_touch_preserves_content(self, temp_storage):
        """Test that touching doesn't modify memory content."""
        original_content = "This content should not change"
        test_id = make_test_uuid("test-content")
        mem = Memory(id=test_id, content=original_content)
        temp_storage.save_memory(mem)

        touch_memory(memory_id=test_id, boost_strength=True)

        updated = temp_storage.get_memory(test_id)
        assert updated.content == original_content

    def test_touch_score_message(self, temp_storage):
        """Test that message includes score change."""
        test_id = make_test_uuid("test-msg")
        mem = Memory(id=test_id, content="Test")
        temp_storage.save_memory(mem)

        result = touch_memory(memory_id=test_id)

        assert result["success"] is True
        assert "reinforced" in result["message"].lower()
        assert "->" in result["message"]
