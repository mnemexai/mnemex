"""Tests for open_memories tool."""

import time

import pytest

from mnemex.storage.models import Memory, MemoryStatus, Relation
from mnemex.tools.open_memories import open_memories
from tests.conftest import make_test_uuid


class TestOpenMemories:
    """Test suite for open_memories tool."""

    def test_open_single_memory(self, temp_storage):
        """Test retrieving a single memory by ID."""
        mem_id = make_test_uuid("test-123")
        mem = Memory(id=mem_id, content="Test memory", use_count=5, entities=["python"])
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id)

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["memories"]) == 1
        assert result["memories"][0]["id"] == mem_id
        assert result["memories"][0]["content"] == "Test memory"
        assert result["not_found"] == []

    def test_open_multiple_memories(self, temp_storage):
        """Test retrieving multiple memories at once."""
        ids = [make_test_uuid(f"mem-{i}") for i in range(3)]
        for i, mem_id in enumerate(ids):
            mem = Memory(id=mem_id, content=f"Memory {i}", use_count=1)
            temp_storage.save_memory(mem)

        result = open_memories(memory_ids=ids)

        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["memories"]) == 3
        assert result["not_found"] == []

    def test_open_memory_includes_all_fields(self, temp_storage):
        """Test that result includes all expected memory fields."""
        now = int(time.time())
        mem_id = make_test_uuid("full-mem")
        mem = Memory(
            id=mem_id,
            content="Full memory",
            entities=["entity1", "entity2"],
            use_count=10,
            strength=1.5,
            created_at=now,
            last_used=now,
        )
        mem.meta.tags = ["tag1", "tag2"]
        mem.meta.source = "test"
        mem.meta.context = "test context"
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id)

        assert result["success"] is True
        memory = result["memories"][0]
        assert memory["id"] == mem_id
        assert memory["content"] == "Full memory"
        assert memory["entities"] == ["entity1", "entity2"]
        assert memory["tags"] == ["tag1", "tag2"]
        assert memory["source"] == "test"
        assert memory["context"] == "test context"
        assert memory["created_at"] == now
        assert memory["last_used"] == now
        assert memory["use_count"] == 10
        assert memory["strength"] == 1.5
        assert memory["status"] == "active"

    def test_open_memory_with_scores(self, temp_storage):
        """Test including decay scores in results."""
        mem_id = make_test_uuid("scored-mem")
        mem = Memory(id=mem_id, content="Test", use_count=5)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id, include_scores=True)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "score" in memory
        assert "age_days" in memory
        assert isinstance(memory["score"], float)
        assert isinstance(memory["age_days"], float)
        assert memory["score"] >= 0

    def test_open_memory_without_scores(self, temp_storage):
        """Test excluding scores from results."""
        mem_id = make_test_uuid("no-score")
        mem = Memory(id=mem_id, content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id, include_scores=False)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "score" not in memory
        assert "age_days" not in memory

    def test_open_memory_with_relations(self, temp_storage):
        """Test including relations in results."""
        mem1_id = make_test_uuid("mem-1")
        mem2_id = make_test_uuid("mem-2")
        mem3_id = make_test_uuid("mem-3")

        mem1 = Memory(id=mem1_id, content="Memory 1", use_count=1)
        mem2 = Memory(id=mem2_id, content="Memory 2", use_count=1)
        mem3 = Memory(id=mem3_id, content="Memory 3", use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        # Create relations
        rel1 = Relation(
            id=make_test_uuid("rel-1"),
            from_memory_id=mem1_id,
            to_memory_id=mem2_id,
            relation_type="related",
            strength=0.8,
            created_at=int(time.time()),
        )
        rel2 = Relation(
            id=make_test_uuid("rel-2"),
            from_memory_id=mem3_id,
            to_memory_id=mem1_id,
            relation_type="causes",
            strength=0.6,
            created_at=int(time.time()),
        )

        temp_storage.create_relation(rel1)
        temp_storage.create_relation(rel2)

        result = open_memories(memory_ids=mem1_id, include_relations=True)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "relations" in memory
        assert "outgoing" in memory["relations"]
        assert "incoming" in memory["relations"]
        assert len(memory["relations"]["outgoing"]) == 1
        assert len(memory["relations"]["incoming"]) == 1
        assert memory["relations"]["outgoing"][0]["to"] == mem2_id
        assert memory["relations"]["incoming"][0]["from"] == mem3_id

    def test_open_memory_without_relations(self, temp_storage):
        """Test excluding relations from results."""
        mem_id = make_test_uuid("no-rel")
        mem = Memory(id=mem_id, content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id, include_relations=False)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "relations" not in memory

    def test_open_memory_not_found(self, temp_storage):
        """Test retrieving non-existent memory."""
        nonexistent_id = make_test_uuid("nonexistent")

        result = open_memories(memory_ids=nonexistent_id)

        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["memories"]) == 0
        assert nonexistent_id in result["not_found"]

    def test_open_memories_partial_not_found(self, temp_storage):
        """Test retrieving mix of existing and non-existent memories."""
        existing_id = make_test_uuid("exists")
        nonexistent_id = make_test_uuid("missing")

        mem = Memory(id=existing_id, content="Exists", use_count=1)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=[existing_id, nonexistent_id])

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["memories"]) == 1
        assert result["memories"][0]["id"] == existing_id
        assert nonexistent_id in result["not_found"]
        assert existing_id not in result["not_found"]

    def test_open_memories_promoted_memory(self, temp_storage):
        """Test retrieving promoted memory."""
        mem_id = make_test_uuid("promoted")
        mem = Memory(
            id=mem_id,
            content="Promoted memory",
            use_count=1,
            status=MemoryStatus.PROMOTED,
            promoted_at=int(time.time()),
            promoted_to="/vault/promoted.md",
        )
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id)

        assert result["success"] is True
        memory = result["memories"][0]
        assert memory["status"] == "promoted"
        assert memory["promoted_at"] is not None
        assert memory["promoted_to"] == "/vault/promoted.md"

    # Validation tests
    def test_open_invalid_uuid_fails(self):
        """Test that invalid UUID fails validation."""
        with pytest.raises(ValueError, match="memory_ids"):
            open_memories(memory_ids="not-a-uuid")

    def test_open_invalid_uuid_in_list_fails(self):
        """Test that invalid UUID in list fails validation."""
        valid_id = make_test_uuid("valid")
        with pytest.raises(ValueError, match="memory_ids"):
            open_memories(memory_ids=[valid_id, "not-a-uuid"])

    def test_open_too_many_ids_fails(self):
        """Test that exceeding max list length fails."""
        # Generate 101 IDs (max is 100)
        too_many_ids = [make_test_uuid(f"mem-{i}") for i in range(101)]

        with pytest.raises(ValueError, match="memory_ids"):
            open_memories(memory_ids=too_many_ids)

    def test_open_invalid_type_fails(self):
        """Test that invalid memory_ids type fails."""
        with pytest.raises(ValueError, match="memory_ids must be a string or list"):
            open_memories(memory_ids=123)  # type: ignore

    # Edge cases
    def test_open_empty_list(self, temp_storage):
        """Test with empty list of IDs."""
        result = open_memories(memory_ids=[])

        assert result["success"] is True
        assert result["count"] == 0
        assert result["memories"] == []
        assert result["not_found"] == []

    def test_open_memory_no_relations(self, temp_storage):
        """Test memory with no relations when include_relations=True."""
        mem_id = make_test_uuid("isolated")
        mem = Memory(id=mem_id, content="Isolated memory", use_count=1)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id, include_relations=True)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "relations" in memory
        assert memory["relations"]["outgoing"] == []
        assert memory["relations"]["incoming"] == []

    def test_open_memory_age_calculation(self, temp_storage):
        """Test age_days calculation."""
        now = int(time.time())
        three_days_ago = now - (3 * 86400)

        mem_id = make_test_uuid("old")
        mem = Memory(id=mem_id, content="Old memory", use_count=1, created_at=three_days_ago)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id, include_scores=True)

        assert result["success"] is True
        memory = result["memories"][0]
        assert "age_days" in memory
        # Should be approximately 3 days old
        assert 2.9 <= memory["age_days"] <= 3.1

    def test_open_memory_score_rounded(self, temp_storage):
        """Test that scores are rounded to 4 decimal places."""
        mem_id = make_test_uuid("rounded")
        mem = Memory(id=mem_id, content="Test", use_count=1)
        temp_storage.save_memory(mem)

        result = open_memories(memory_ids=mem_id, include_scores=True)

        assert result["success"] is True
        memory = result["memories"][0]
        # Score should have at most 4 decimal places
        score_str = str(memory["score"])
        if "." in score_str:
            decimals = len(score_str.split(".")[1])
            assert decimals <= 4

    def test_open_memory_relation_strength_rounded(self, temp_storage):
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
            strength=0.123456789,  # Many decimal places
            created_at=int(time.time()),
        )
        temp_storage.create_relation(rel)

        result = open_memories(memory_ids=mem1_id, include_relations=True)

        assert result["success"] is True
        memory = result["memories"][0]
        strength = memory["relations"]["outgoing"][0]["strength"]
        # Strength should have at most 4 decimal places
        strength_str = str(strength)
        if "." in strength_str:
            decimals = len(strength_str.split(".")[1])
            assert decimals <= 4
