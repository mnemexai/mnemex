"""Tests for cluster_memories tool."""

import pytest

from mnemex.storage.models import Memory
from mnemex.tools.cluster import cluster_memories
from tests.conftest import make_test_uuid


class TestClusterMemories:
    """Test suite for cluster_memories tool."""

    def test_cluster_basic_clustering(self, temp_storage):
        """Test basic clustering functionality."""
        # Create similar memories
        mem1 = Memory(
            id=make_test_uuid("mem-1"), content="Python programming tutorial", use_count=1
        )
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Python coding guide", use_count=1)
        mem3 = Memory(id=make_test_uuid("mem-3"), content="JavaScript basics", use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        result = cluster_memories()

        assert result["success"] is True
        assert result["mode"] == "clustering"
        assert "clusters_found" in result
        assert "strategy" in result
        assert "threshold" in result
        assert "clusters" in result
        assert isinstance(result["clusters"], list)

    def test_cluster_find_duplicates_mode(self, temp_storage):
        """Test duplicate detection mode."""
        # Create potential duplicates
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test memory content", use_count=1)
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Test memory content", use_count=1)
        mem3 = Memory(id=make_test_uuid("mem-3"), content="Different content here", use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        result = cluster_memories(find_duplicates=True)

        assert result["success"] is True
        assert result["mode"] == "duplicate_detection"
        assert "duplicates_found" in result
        assert "duplicates" in result
        assert isinstance(result["duplicates"], list)

    def test_cluster_duplicate_result_format(self, temp_storage):
        """Test duplicate detection result structure."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Duplicate content", use_count=1)
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Duplicate content", use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = cluster_memories(find_duplicates=True)

        assert result["success"] is True
        if result["duplicates_found"] > 0:
            dup = result["duplicates"][0]
            assert "id1" in dup
            assert "id2" in dup
            assert "content1_preview" in dup
            assert "content2_preview" in dup
            assert "similarity" in dup
            assert isinstance(dup["similarity"], float)

    def test_cluster_with_threshold(self, temp_storage):
        """Test clustering with custom threshold."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem1)

        result = cluster_memories(threshold=0.8)

        assert result["success"] is True
        assert result["threshold"] == 0.8

    def test_cluster_with_max_cluster_size(self, temp_storage):
        """Test clustering with max_cluster_size parameter."""
        for i in range(10):
            mem = Memory(id=make_test_uuid(f"mem-{i}"), content=f"Memory {i}", use_count=1)
            temp_storage.save_memory(mem)

        result = cluster_memories(max_cluster_size=5)

        assert result["success"] is True
        # Verify no cluster exceeds max size
        for cluster in result["clusters"]:
            assert cluster["size"] <= 5

    def test_cluster_with_duplicate_threshold(self, temp_storage):
        """Test duplicate detection with custom threshold."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem1)

        result = cluster_memories(find_duplicates=True, duplicate_threshold=0.9)

        assert result["success"] is True
        assert result["mode"] == "duplicate_detection"

    def test_cluster_result_format(self, temp_storage):
        """Test cluster result structure."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test memory", use_count=1)
        temp_storage.save_memory(mem1)

        result = cluster_memories()

        assert result["success"] is True
        assert "mode" in result
        assert "clusters_found" in result
        assert "strategy" in result
        assert "threshold" in result
        assert "clusters" in result
        assert "message" in result

        # Test cluster structure if any clusters found
        if result["clusters_found"] > 0:
            cluster = result["clusters"][0]
            assert "id" in cluster
            assert "size" in cluster
            assert "cohesion" in cluster
            assert "suggested_action" in cluster
            assert "memory_ids" in cluster
            assert "content_previews" in cluster

    def test_cluster_with_strategy_parameter(self, temp_storage):
        """Test clustering with strategy parameter."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem1)

        result = cluster_memories(strategy="similarity")

        assert result["success"] is True
        assert result["strategy"] == "similarity"

    def test_cluster_empty_database(self, temp_storage):
        """Test clustering on empty database."""
        result = cluster_memories()

        assert result["success"] is True
        assert result["clusters_found"] == 0
        assert result["clusters"] == []

    def test_cluster_duplicates_empty_database(self, temp_storage):
        """Test duplicate detection on empty database."""
        result = cluster_memories(find_duplicates=True)

        assert result["success"] is True
        assert result["duplicates_found"] == 0
        assert result["duplicates"] == []

    def test_cluster_single_memory(self, temp_storage):
        """Test clustering with only one memory."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Single memory", use_count=1)
        temp_storage.save_memory(mem)

        result = cluster_memories()

        assert result["success"] is True
        # Should have 0 or 1 cluster
        assert result["clusters_found"] in (0, 1)

    def test_cluster_many_memories(self, temp_storage):
        """Test clustering with many memories."""
        for i in range(25):
            mem = Memory(id=make_test_uuid(f"mem-{i}"), content=f"Memory {i}", use_count=1)
            temp_storage.save_memory(mem)

        result = cluster_memories()

        assert result["success"] is True
        # Should limit to 20 clusters in result
        assert len(result["clusters"]) <= 20

    def test_cluster_duplicates_limited_to_20(self, temp_storage):
        """Test that duplicate results are limited to 20."""
        # Create many potential duplicates
        for i in range(30):
            mem = Memory(id=make_test_uuid(f"mem-{i}"), content="Duplicate content", use_count=1)
            temp_storage.save_memory(mem)

        result = cluster_memories(find_duplicates=True)

        assert result["success"] is True
        # Should limit to 20 duplicates in result
        assert len(result["duplicates"]) <= 20

    # Validation tests
    def test_cluster_invalid_threshold_fails(self):
        """Test that invalid threshold values fail."""
        with pytest.raises(ValueError, match="threshold"):
            cluster_memories(threshold=1.5)

        with pytest.raises(ValueError, match="threshold"):
            cluster_memories(threshold=-0.1)

    def test_cluster_invalid_max_cluster_size_fails(self):
        """Test that invalid max_cluster_size values fail."""
        with pytest.raises(ValueError, match="max_cluster_size"):
            cluster_memories(max_cluster_size=0)

        with pytest.raises(ValueError, match="max_cluster_size"):
            cluster_memories(max_cluster_size=101)

        with pytest.raises(ValueError, match="max_cluster_size"):
            cluster_memories(max_cluster_size=-1)

    def test_cluster_invalid_duplicate_threshold_fails(self):
        """Test that invalid duplicate_threshold values fail."""
        with pytest.raises(ValueError, match="duplicate_threshold"):
            cluster_memories(find_duplicates=True, duplicate_threshold=1.5)

        with pytest.raises(ValueError, match="duplicate_threshold"):
            cluster_memories(find_duplicates=True, duplicate_threshold=-0.1)

    # Edge cases
    def test_cluster_content_preview_truncated(self, temp_storage):
        """Test that content previews are truncated to 80 characters."""
        long_content = "A" * 200
        mem = Memory(id=make_test_uuid("mem-1"), content=long_content, use_count=1)
        temp_storage.save_memory(mem)

        result = cluster_memories()

        assert result["success"] is True
        if result["clusters_found"] > 0 and result["clusters"][0]["content_previews"]:
            preview = result["clusters"][0]["content_previews"][0]
            assert len(preview) <= 80

    def test_cluster_duplicate_content_preview_truncated(self, temp_storage):
        """Test that duplicate content previews are truncated to 100 characters."""
        long_content = "B" * 200
        mem1 = Memory(id=make_test_uuid("mem-1"), content=long_content, use_count=1)
        mem2 = Memory(id=make_test_uuid("mem-2"), content=long_content, use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = cluster_memories(find_duplicates=True)

        assert result["success"] is True
        if result["duplicates_found"] > 0:
            dup = result["duplicates"][0]
            assert len(dup["content1_preview"]) <= 100
            assert len(dup["content2_preview"]) <= 100

    def test_cluster_message_includes_count(self, temp_storage):
        """Test that message includes cluster count."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = cluster_memories()

        assert result["success"] is True
        assert str(result["clusters_found"]) in result["message"]

    def test_cluster_duplicate_message_includes_count(self, temp_storage):
        """Test that duplicate message includes count."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Test", use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = cluster_memories(find_duplicates=True)

        assert result["success"] is True
        assert str(result["duplicates_found"]) in result["message"]
