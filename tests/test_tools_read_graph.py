"""Tests for read_graph tool."""

import time

import pytest

from mnemex.storage.models import Memory, MemoryStatus, Relation
from mnemex.tools.read_graph import read_graph
from tests.conftest import make_test_uuid


class TestReadGraph:
    """Test suite for read_graph tool."""

    def test_read_graph_basic(self, temp_storage):
        """Test basic graph reading."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test 1", use_count=1)
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Test 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = read_graph()

        assert result["success"] is True
        assert "memories" in result
        assert "relations" in result
        assert "stats" in result
        assert len(result["memories"]) == 2

    def test_read_graph_includes_scores(self, temp_storage):
        """Test that scores are included by default."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=5)
        temp_storage.save_memory(mem)

        result = read_graph(include_scores=True)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "score" in memory
        assert "age_days" in memory
        assert isinstance(memory["score"], float)
        assert isinstance(memory["age_days"], float)

    def test_read_graph_without_scores(self, temp_storage):
        """Test excluding scores from results."""
        mem = Memory(id=make_test_uuid("mem-1"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = read_graph(include_scores=False)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "score" not in memory
        assert "age_days" not in memory

    def test_read_graph_filter_active_status(self, temp_storage):
        """Test filtering by active status."""
        active_mem = Memory(id=make_test_uuid("active"), content="Active", use_count=1)
        promoted_mem = Memory(
            id=make_test_uuid("promoted"),
            content="Promoted",
            use_count=1,
            status=MemoryStatus.PROMOTED,
        )
        archived_mem = Memory(
            id=make_test_uuid("archived"),
            content="Archived",
            use_count=1,
            status=MemoryStatus.ARCHIVED,
        )

        temp_storage.save_memory(active_mem)
        temp_storage.save_memory(promoted_mem)
        temp_storage.save_memory(archived_mem)

        result = read_graph(status="active")

        assert result["success"] is True
        assert len(result["memories"]) == 1
        assert result["memories"][0]["status"] == "active"

    def test_read_graph_filter_promoted_status(self, temp_storage):
        """Test filtering by promoted status."""
        active_mem = Memory(id=make_test_uuid("active"), content="Active", use_count=1)
        promoted_mem = Memory(
            id=make_test_uuid("promoted"),
            content="Promoted",
            use_count=1,
            status=MemoryStatus.PROMOTED,
        )

        temp_storage.save_memory(active_mem)
        temp_storage.save_memory(promoted_mem)

        result = read_graph(status="promoted")

        assert result["success"] is True
        assert len(result["memories"]) == 1
        assert result["memories"][0]["status"] == "promoted"

    def test_read_graph_filter_archived_status(self, temp_storage):
        """Test filtering by archived status."""
        active_mem = Memory(id=make_test_uuid("active"), content="Active", use_count=1)
        archived_mem = Memory(
            id=make_test_uuid("archived"),
            content="Archived",
            use_count=1,
            status=MemoryStatus.ARCHIVED,
        )

        temp_storage.save_memory(active_mem)
        temp_storage.save_memory(archived_mem)

        result = read_graph(status="archived")

        assert result["success"] is True
        assert len(result["memories"]) == 1
        assert result["memories"][0]["status"] == "archived"

    def test_read_graph_filter_all_status(self, temp_storage):
        """Test getting all memories regardless of status."""
        active_mem = Memory(id=make_test_uuid("active"), content="Active", use_count=1)
        promoted_mem = Memory(
            id=make_test_uuid("promoted"),
            content="Promoted",
            use_count=1,
            status=MemoryStatus.PROMOTED,
        )
        archived_mem = Memory(
            id=make_test_uuid("archived"),
            content="Archived",
            use_count=1,
            status=MemoryStatus.ARCHIVED,
        )

        temp_storage.save_memory(active_mem)
        temp_storage.save_memory(promoted_mem)
        temp_storage.save_memory(archived_mem)

        result = read_graph(status="all")

        assert result["success"] is True
        assert len(result["memories"]) == 3

    def test_read_graph_with_limit(self, temp_storage):
        """Test limiting number of memories returned."""
        for i in range(10):
            mem = Memory(id=make_test_uuid(f"mem-{i}"), content=f"Memory {i}", use_count=1)
            temp_storage.save_memory(mem)

        result = read_graph(limit=5)

        assert result["success"] is True
        assert len(result["memories"]) == 5

    def test_read_graph_limit_none_returns_all(self, temp_storage):
        """Test that limit=None returns all memories."""
        for i in range(15):
            mem = Memory(id=make_test_uuid(f"mem-{i}"), content=f"Memory {i}", use_count=1)
            temp_storage.save_memory(mem)

        result = read_graph(limit=None)

        assert result["success"] is True
        assert len(result["memories"]) == 15
        assert "limited_to" not in result["stats"]

    def test_read_graph_includes_relations(self, temp_storage):
        """Test that relations are included in graph."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        rel = Relation(
            id=make_test_uuid("rel-1"),
            from_memory_id=mem1_id,
            to_memory_id=mem2_id,
            relation_type="related",
            strength=0.8,
            created_at=int(time.time()),
        )
        temp_storage.create_relation(rel)

        result = read_graph()

        assert result["success"] is True
        assert len(result["relations"]) == 1
        relation = result["relations"][0]
        assert relation["from"] == mem1_id
        assert relation["to"] == mem2_id
        assert relation["type"] == "related"
        assert relation["strength"] == 0.8

    def test_read_graph_stats(self, temp_storage):
        """Test that stats are calculated correctly."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test 1", use_count=5)
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Test 2", use_count=3)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        rel = Relation(
            id=make_test_uuid("rel"),
            from_memory_id=mem1.id,
            to_memory_id=mem2.id,
            relation_type="related",
            strength=0.5,
            created_at=int(time.time()),
        )
        temp_storage.create_relation(rel)

        result = read_graph()

        assert result["success"] is True
        stats = result["stats"]
        assert stats["total_memories"] == 2
        assert stats["total_relations"] == 1
        assert "avg_score" in stats
        assert "avg_use_count" in stats
        assert "status_filter" in stats

    def test_read_graph_memory_fields(self, temp_storage):
        """Test that memory objects include all expected fields."""
        mem_id = make_test_uuid("full")
        mem = Memory(
            id=mem_id,
            content="Full memory",
            entities=["entity1"],
            use_count=10,
            strength=1.5,
        )
        mem.meta.tags = ["tag1"]
        temp_storage.save_memory(mem)

        result = read_graph()

        assert result["success"] is True
        memory = result["memories"][0]
        assert memory["id"] == mem_id
        assert memory["content"] == "Full memory"
        assert memory["entities"] == ["entity1"]
        assert memory["tags"] == ["tag1"]
        assert memory["created_at"] is not None
        assert memory["last_used"] is not None
        assert memory["use_count"] == 10
        assert memory["strength"] == 1.5
        assert memory["status"] == "active"

    def test_read_graph_relation_fields(self, temp_storage):
        """Test that relation objects include all expected fields."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="M1", use_count=1)
        mem2 = Memory(id=mem2_id, content="M2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        rel_id = make_test_uuid("rel")
        now = int(time.time())
        rel = Relation(
            id=rel_id,
            from_memory_id=mem1_id,
            to_memory_id=mem2_id,
            relation_type="causes",
            strength=0.75,
            created_at=now,
        )
        temp_storage.create_relation(rel)

        result = read_graph()

        assert result["success"] is True
        relation = result["relations"][0]
        assert relation["id"] == rel_id
        assert relation["from"] == mem1_id
        assert relation["to"] == mem2_id
        assert relation["type"] == "causes"
        assert relation["strength"] == 0.75
        assert relation["created_at"] == now

    # Validation tests
    def test_read_graph_invalid_status_fails(self):
        """Test that invalid status values fail."""
        with pytest.raises(ValueError, match="status must be one of"):
            read_graph(status="invalid")

    def test_read_graph_invalid_limit_fails(self):
        """Test that invalid limit values fail."""
        with pytest.raises(ValueError, match="limit"):
            read_graph(limit=0)

        with pytest.raises(ValueError, match="limit"):
            read_graph(limit=10001)

        with pytest.raises(ValueError, match="limit"):
            read_graph(limit=-1)

    # Edge cases
    def test_read_graph_empty_database(self, temp_storage):
        """Test reading graph from empty database."""
        result = read_graph()

        assert result["success"] is True
        assert len(result["memories"]) == 0
        assert len(result["relations"]) == 0
        assert result["stats"]["total_memories"] == 0
        assert result["stats"]["total_relations"] == 0

    def test_read_graph_no_relations(self, temp_storage):
        """Test graph with memories but no relations."""
        mem1 = Memory(id=make_test_uuid("mem-1"), content="Test 1", use_count=1)
        mem2 = Memory(id=make_test_uuid("mem-2"), content="Test 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = read_graph()

        assert result["success"] is True
        assert len(result["memories"]) == 2
        assert len(result["relations"]) == 0
        assert result["stats"]["total_relations"] == 0

    def test_read_graph_score_rounded(self, temp_storage):
        """Test that scores are rounded to 4 decimal places."""
        mem = Memory(id=make_test_uuid("mem"), content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = read_graph(include_scores=True)

        assert result["success"] is True
        memory = result["memories"][0]
        score_str = str(memory["score"])
        if "." in score_str:
            decimals = len(score_str.split(".")[1])
            assert decimals <= 4

    def test_read_graph_relation_strength_rounded(self, temp_storage):
        """Test that relation strengths are rounded to 4 decimal places."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="M1", use_count=1)
        mem2 = Memory(id=mem2_id, content="M2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        rel = Relation(
            id=make_test_uuid("rel"),
            from_memory_id=mem1_id,
            to_memory_id=mem2_id,
            relation_type="related",
            strength=0.123456789,
            created_at=int(time.time()),
        )
        temp_storage.create_relation(rel)

        result = read_graph()

        assert result["success"] is True
        relation = result["relations"][0]
        strength_str = str(relation["strength"])
        if "." in strength_str:
            decimals = len(strength_str.split(".")[1])
            assert decimals <= 4

    def test_read_graph_stats_rounded(self, temp_storage):
        """Test that stats values are properly rounded."""
        for i in range(3):
            mem = Memory(id=make_test_uuid(f"mem-{i}"), content=f"Test {i}", use_count=i + 1)
            temp_storage.save_memory(mem)

        result = read_graph()

        assert result["success"] is True
        stats = result["stats"]
        # avg_score should be rounded to 4 decimals
        score_str = str(stats["avg_score"])
        if "." in score_str:
            decimals = len(score_str.split(".")[1])
            assert decimals <= 4
        # avg_use_count should be rounded to 2 decimals
        use_count_str = str(stats["avg_use_count"])
        if "." in use_count_str:
            decimals = len(use_count_str.split(".")[1])
            assert decimals <= 2
