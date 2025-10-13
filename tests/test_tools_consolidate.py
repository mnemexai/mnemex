"""Tests for consolidate_memories tool."""

import pytest

from mnemex.storage.models import Memory
from mnemex.tools.consolidate import consolidate_memories
from tests.conftest import make_test_uuid


class TestConsolidateMemories:
    """Test suite for consolidate_memories tool."""

    def test_consolidate_auto_detect_preview_empty(self, temp_storage):
        """Test auto-detect preview mode with empty database."""
        result = consolidate_memories(auto_detect=True, mode="preview")

        assert result["success"] is True
        assert result["mode"] == "auto_detect_preview"
        assert result["candidates_found"] == 0
        assert result["showing"] == 0
        assert result["previews"] == []

    def test_consolidate_auto_detect_preview_basic(self, temp_storage):
        """Test auto-detect preview mode with some memories."""
        # Create a few similar memories
        for i in range(3):
            mem = Memory(
                id=make_test_uuid(f"mem-{i}"),
                content=f"Python programming tutorial part {i}",
                use_count=1,
            )
            temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="preview")

        assert result["success"] is True
        assert result["mode"] == "auto_detect_preview"
        assert "candidates_found" in result
        assert "showing" in result
        assert "previews" in result
        assert isinstance(result["previews"], list)

    def test_consolidate_auto_detect_apply_empty(self, temp_storage):
        """Test auto-detect apply mode with empty database."""
        result = consolidate_memories(auto_detect=True, mode="apply")

        assert result["success"] is True
        assert result["mode"] == "auto_detect_apply"
        assert result["consolidated_clusters"] == 0
        assert result["total_memories_saved"] == 0
        assert result["results"] == []

    def test_consolidate_auto_detect_apply_basic(self, temp_storage):
        """Test auto-detect apply mode with some memories."""
        # Create similar memories
        for i in range(3):
            mem = Memory(
                id=make_test_uuid(f"mem-{i}"),
                content=f"Similar content {i}",
                use_count=1,
            )
            temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="apply")

        assert result["success"] is True
        assert result["mode"] == "auto_detect_apply"
        assert "consolidated_clusters" in result
        assert "total_memories_saved" in result
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_consolidate_custom_cohesion_threshold(self, temp_storage):
        """Test auto-detect with custom cohesion threshold."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test 1", use_count=1)
        temp_storage.save_memory(mem1)

        result = consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=0.9)

        assert result["success"] is True
        assert result["mode"] == "auto_detect_preview"

    def test_consolidate_cohesion_boundaries(self, temp_storage):
        """Test cohesion threshold at boundaries."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        # Test minimum threshold
        result_min = consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=0.0)
        assert result_min["success"] is True

        # Test maximum threshold
        result_max = consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=1.0)
        assert result_max["success"] is True

    def test_consolidate_result_format_auto_preview(self, temp_storage):
        """Test result format for auto-detect preview mode."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="preview")

        # Verify all expected keys
        assert "success" in result
        assert "mode" in result
        assert "candidates_found" in result
        assert "showing" in result
        assert "previews" in result
        assert "message" in result

        assert result["success"] is True
        assert result["mode"] == "auto_detect_preview"
        assert isinstance(result["candidates_found"], int)
        assert isinstance(result["showing"], int)
        assert isinstance(result["previews"], list)

    def test_consolidate_result_format_auto_apply(self, temp_storage):
        """Test result format for auto-detect apply mode."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="apply")

        # Verify all expected keys
        assert "success" in result
        assert "mode" in result
        assert "consolidated_clusters" in result
        assert "total_memories_saved" in result
        assert "results" in result
        assert "message" in result

        assert result["success"] is True
        assert result["mode"] == "auto_detect_apply"
        assert isinstance(result["consolidated_clusters"], int)
        assert isinstance(result["total_memories_saved"], int)
        assert isinstance(result["results"], list)

    # Error case tests
    def test_consolidate_missing_cluster_id(self, temp_storage):
        """Test that cluster_id is required when auto_detect is False."""
        result = consolidate_memories(auto_detect=False, mode="preview")

        assert result["success"] is False
        assert "error" in result
        assert "cluster_id is required" in result["error"]
        assert "hint" in result

    def test_consolidate_cluster_not_found(self, temp_storage):
        """Test error when specific cluster is not found."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        nonexistent_cluster_id = make_test_uuid("nonexistent-cluster")

        result = consolidate_memories(
            cluster_id=nonexistent_cluster_id, mode="preview", auto_detect=False
        )

        assert result["success"] is False
        assert "error" in result
        assert nonexistent_cluster_id in result["error"]
        assert "hint" in result

    # Validation tests
    def test_consolidate_invalid_cluster_id_uuid(self, temp_storage):
        """Test that invalid cluster_id UUID fails validation."""
        with pytest.raises(ValueError, match="cluster_id"):
            consolidate_memories(cluster_id="not-a-uuid", mode="preview")

    def test_consolidate_invalid_cohesion_negative(self, temp_storage):
        """Test that negative cohesion_threshold fails validation."""
        with pytest.raises(ValueError, match="cohesion_threshold"):
            consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=-0.1)

    def test_consolidate_invalid_cohesion_too_high(self, temp_storage):
        """Test that cohesion_threshold > 1.0 fails validation."""
        with pytest.raises(ValueError, match="cohesion_threshold"):
            consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=1.5)

    def test_consolidate_invalid_mode(self, temp_storage):
        """Test that invalid mode fails validation."""
        with pytest.raises(ValueError, match="mode"):
            consolidate_memories(auto_detect=True, mode="invalid_mode")

    def test_consolidate_mode_not_preview_or_apply(self, temp_storage):
        """Test various invalid mode values."""
        with pytest.raises(ValueError, match="mode"):
            consolidate_memories(auto_detect=True, mode="")

        with pytest.raises(ValueError, match="mode"):
            consolidate_memories(auto_detect=True, mode="Preview")  # Case-sensitive

        with pytest.raises(ValueError, match="mode"):
            consolidate_memories(auto_detect=True, mode="execute")

    # Edge cases
    def test_consolidate_default_parameters(self, temp_storage):
        """Test consolidate with default parameters (should fail - needs cluster_id or auto_detect)."""
        result = consolidate_memories()

        # Default is auto_detect=False, mode="preview", no cluster_id
        assert result["success"] is False
        assert "cluster_id is required" in result["error"]

    def test_consolidate_preview_shows_max_5(self, temp_storage):
        """Test that auto-detect preview shows max 5 candidates."""
        # Create many similar memories to potentially trigger multiple clusters
        for i in range(20):
            mem = Memory(
                id=make_test_uuid(f"mem-{i}"),
                content=f"Test memory {i}",
                use_count=1,
            )
            temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=0.5)

        assert result["success"] is True
        # Should show at most 5 previews
        assert result["showing"] <= 5
        assert len(result["previews"]) <= 5

    def test_consolidate_none_cluster_id(self, temp_storage):
        """Test that None cluster_id is handled properly."""
        result = consolidate_memories(cluster_id=None, auto_detect=False, mode="preview")

        assert result["success"] is False
        assert "cluster_id is required" in result["error"]

    def test_consolidate_message_content(self, temp_storage):
        """Test that messages are informative."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="preview")

        assert result["success"] is True
        assert "message" in result
        # Message should mention number of candidates
        assert str(result["candidates_found"]) in result["message"]

    def test_consolidate_apply_message_content(self, temp_storage):
        """Test that apply mode messages include results."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = consolidate_memories(auto_detect=True, mode="apply")

        assert result["success"] is True
        assert "message" in result
        # Message should mention consolidation count
        assert str(result["consolidated_clusters"]) in result["message"]
        assert str(result["total_memories_saved"]) in result["message"]
