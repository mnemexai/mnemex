"""
Tests for tools related to graph structure operations.

This test suite covers the following tools:
- `create_relation`
- `read_graph`
"""

import time

import pytest

from cortexgraph.storage.models import Memory, MemoryStatus, Relation
from cortexgraph.tools.create_relation import create_relation
from cortexgraph.tools.read_graph import read_graph
from tests.conftest import make_test_uuid


class TestCreateRelation:
    """Test suite for create_relation tool."""

    def test_create_basic_relation(self, temp_storage):
        """Test creating a basic relation between two memories."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related"
        )

        assert result["success"] is True
        assert "relation_id" in result
        assert result["from"] == mem1_id
        assert result["to"] == mem2_id
        assert result["type"] == "related"
        assert result["strength"] == 1.0
        assert "message" in result

    def test_create_relation_all_types(self, temp_storage):
        """Test creating relations with all valid types."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        valid_types = [
            "related",
            "causes",
            "supports",
            "contradicts",
            "has_decision",
            "consolidated_from",
        ]

        for rel_type in valid_types:
            # Use different target for each type to avoid duplicates
            target_id = make_test_uuid(f"target-{rel_type}")
            target = Memory(id=target_id, content=f"Target {rel_type}", use_count=1)
            temp_storage.save_memory(target)

            result = create_relation(
                from_memory_id=mem1_id, to_memory_id=target_id, relation_type=rel_type
            )

            assert result["success"] is True
            assert result["type"] == rel_type

    def test_create_relation_custom_strength(self, temp_storage):
        """Test creating relation with custom strength value."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related", strength=0.75
        )

        assert result["success"] is True
        assert result["strength"] == 0.75

    def test_create_relation_with_metadata(self, temp_storage):
        """Test creating relation with metadata."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        metadata = {"reason": "testing", "confidence": 0.9}
        result = create_relation(
            from_memory_id=mem1_id,
            to_memory_id=mem2_id,
            relation_type="related",
            metadata=metadata,
        )

        assert result["success"] is True
        # Verify metadata is stored
        relations = temp_storage.get_relations(from_memory_id=mem1_id)
        assert len(relations) == 1
        assert relations[0].metadata == metadata

    def test_create_relation_strength_boundaries(self, temp_storage):
        """Test strength values at boundaries."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")
        mem3_id = make_test_uuid("mem-3")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        mem3 = Memory(id=mem3_id, content="Memory 3", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        # Test minimum strength (0.0)
        result_min = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related", strength=0.0
        )
        assert result_min["success"] is True
        assert result_min["strength"] == 0.0

        # Test maximum strength (1.0)
        result_max = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem3_id, relation_type="related", strength=1.0
        )
        assert result_max["success"] is True
        assert result_max["strength"] == 1.0

    def test_create_self_relation(self, temp_storage):
        """Test creating a relation from memory to itself."""
        mem_id = make_test_uuid("mem-1")
        mem = Memory(id=mem_id, content="Self-referential memory", use_count=1)
        temp_storage.save_memory(mem)

        result = create_relation(
            from_memory_id=mem_id, to_memory_id=mem_id, relation_type="related"
        )

        # Self-relations should be allowed
        assert result["success"] is True
        assert result["from"] == mem_id
        assert result["to"] == mem_id

    def test_create_relation_is_stored(self, temp_storage):
        """Test that created relation is actually stored in database."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="causes", strength=0.8
        )

        assert result["success"] is True
        relation_id = result["relation_id"]

        # Verify relation is in database
        relations = temp_storage.get_relations(from_memory_id=mem1_id)
        assert len(relations) == 1
        assert relations[0].id == relation_id
        assert relations[0].from_memory_id == mem1_id
        assert relations[0].to_memory_id == mem2_id
        assert relations[0].relation_type == "causes"
        assert relations[0].strength == 0.8

    def test_create_multiple_relations_same_memories(self, temp_storage):
        """Test creating multiple relations between same memories with different types."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        # Create different relation types between same memories
        result1 = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related"
        )
        result2 = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="causes"
        )

        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["relation_id"] != result2["relation_id"]

        # Verify both relations exist
        relations = temp_storage.get_relations(from_memory_id=mem1_id, to_memory_id=mem2_id)
        assert len(relations) == 2

    # Error case tests
    def test_create_relation_source_not_found(self, temp_storage):
        """Test creating relation when source memory doesn't exist."""
        nonexistent_id = make_test_uuid("nonexistent")
        existing_id = make_test_uuid("exists")

        mem = Memory(id=existing_id, content="Exists", use_count=1)
        temp_storage.save_memory(mem)

        result = create_relation(
            from_memory_id=nonexistent_id, to_memory_id=existing_id, relation_type="related"
        )

        assert result["success"] is False
        assert "not found" in result["message"].lower()
        assert nonexistent_id in result["message"]

    def test_create_relation_target_not_found(self, temp_storage):
        """Test creating relation when target memory doesn't exist."""
        existing_id = make_test_uuid("exists")
        nonexistent_id = make_test_uuid("nonexistent")

        mem = Memory(id=existing_id, content="Exists", use_count=1)
        temp_storage.save_memory(mem)

        result = create_relation(
            from_memory_id=existing_id, to_memory_id=nonexistent_id, relation_type="related"
        )

        assert result["success"] is False
        assert "not found" in result["message"].lower()
        assert nonexistent_id in result["message"]

    def test_create_relation_duplicate_fails(self, temp_storage):
        """Test that creating duplicate relation fails."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        # Create first relation
        result1 = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related"
        )
        assert result1["success"] is True
        relation_id = result1["relation_id"]

        # Try to create duplicate
        result2 = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related"
        )

        assert result2["success"] is False
        assert "already exists" in result2["message"].lower()
        assert "existing_relation_id" in result2
        assert result2["existing_relation_id"] == relation_id

    # Validation tests
    def test_create_relation_invalid_from_uuid(self, temp_storage):
        """Test that invalid from_memory_id UUID fails validation."""
        mem_id = make_test_uuid("mem-1")
        mem = Memory(id=mem_id, content="Memory", use_count=1)
        temp_storage.save_memory(mem)

        with pytest.raises(ValueError, match="from_memory_id"):
            create_relation(
                from_memory_id="not-a-uuid", to_memory_id=mem_id, relation_type="related"
            )

    def test_create_relation_invalid_to_uuid(self, temp_storage):
        """Test that invalid to_memory_id UUID fails validation."""
        mem_id = make_test_uuid("mem-1")
        mem = Memory(id=mem_id, content="Memory", use_count=1)
        temp_storage.save_memory(mem)

        with pytest.raises(ValueError, match="to_memory_id"):
            create_relation(
                from_memory_id=mem_id, to_memory_id="not-a-uuid", relation_type="related"
            )

    def test_create_relation_invalid_type(self, temp_storage):
        """Test that invalid relation_type fails validation."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        with pytest.raises(ValueError, match="relation_type"):
            create_relation(
                from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="invalid_type"
            )

    def test_create_relation_invalid_strength_negative(self, temp_storage):
        """Test that negative strength fails validation."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        with pytest.raises(ValueError, match="strength"):
            create_relation(
                from_memory_id=mem1_id,
                to_memory_id=mem2_id,
                relation_type="related",
                strength=-0.1,
            )

    def test_create_relation_invalid_strength_too_high(self, temp_storage):
        """Test that strength > 1.0 fails validation."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        with pytest.raises(ValueError, match="strength"):
            create_relation(
                from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related", strength=1.5
            )

    # Edge cases
    def test_create_relation_empty_metadata(self, temp_storage):
        """Test creating relation with empty metadata dict."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related", metadata={}
        )

        assert result["success"] is True
        # Verify empty metadata is stored
        relations = temp_storage.get_relations(from_memory_id=mem1_id)
        assert relations[0].metadata == {}

    def test_create_relation_none_metadata(self, temp_storage):
        """Test creating relation with None metadata (should use empty dict)."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related", metadata=None
        )

        assert result["success"] is True
        # Verify None becomes empty dict
        relations = temp_storage.get_relations(from_memory_id=mem1_id)
        assert relations[0].metadata == {}

    def test_create_relation_result_format(self, temp_storage):
        """Test that result has all expected keys and correct format."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = create_relation(
            from_memory_id=mem1_id,
            to_memory_id=mem2_id,
            relation_type="causes",
            strength=0.85,
        )

        # Verify all expected keys
        assert "success" in result
        assert "relation_id" in result
        assert "from" in result
        assert "to" in result
        assert "type" in result
        assert "strength" in result
        assert "message" in result

        # Verify values
        assert result["success"] is True
        assert isinstance(result["relation_id"], str)
        assert result["from"] == mem1_id
        assert result["to"] == mem2_id
        assert result["type"] == "causes"
        assert result["strength"] == 0.85
        assert "causes" in result["message"]

    def test_create_relation_timestamp(self, temp_storage):
        """Test that created relation has proper timestamp."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        before = int(time.time())
        result = create_relation(
            from_memory_id=mem1_id, to_memory_id=mem2_id, relation_type="related"
        )
        after = int(time.time())

        assert result["success"] is True

        # Verify timestamp is within reasonable range
        relations = temp_storage.get_relations(from_memory_id=mem1_id)
        assert len(relations) == 1
        assert before <= relations[0].created_at <= after


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
