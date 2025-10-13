"""Tests for create_relation tool."""

import time

import pytest

from mnemex.storage.models import Memory
from mnemex.tools.create_relation import create_relation
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
