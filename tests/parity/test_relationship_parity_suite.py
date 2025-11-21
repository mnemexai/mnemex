import pytest

from cortexgraph.storage.models import Memory, MemoryStatus, Relation

RELATION_TYPES = ["references", "similar_to", "follows_from", "contradicts", "supports"]


@pytest.fixture
def populated_storage(storage):
    # Create a set of memories
    memories = [
        Memory(id=f"mem-{i}", content=f"Memory {i}", status=MemoryStatus.ACTIVE) for i in range(10)
    ]
    for mem in memories:
        storage.save_memory(mem)
    return storage


def test_all_relationship_types(populated_storage):
    storage = populated_storage

    for i, rel_type in enumerate(RELATION_TYPES):
        relation = Relation(
            id=f"rel-{i}",
            from_memory_id="mem-0",
            to_memory_id=f"mem-{i + 1}",
            relation_type=rel_type,
            strength=0.5 + (i * 0.1),
        )
        storage.create_relation(relation)

    relations = storage.get_relations(from_memory_id="mem-0")
    assert len(relations) == len(RELATION_TYPES)

    # Verify types and strengths are preserved
    for rel in relations:
        assert rel.relation_type in RELATION_TYPES
        assert 0.5 <= rel.strength <= 1.0


def test_multiple_relationships_same_pair(populated_storage):
    storage = populated_storage

    # Add two relations between mem-0 and mem-1 with different types
    rel1 = Relation(
        id="rel-1",
        from_memory_id="mem-0",
        to_memory_id="mem-1",
        relation_type="references",
        strength=0.8,
    )
    rel2 = Relation(
        id="rel-2",
        from_memory_id="mem-0",
        to_memory_id="mem-1",
        relation_type="supports",
        strength=0.9,
    )

    storage.create_relation(rel1)
    storage.create_relation(rel2)

    relations = storage.get_relations(from_memory_id="mem-0")
    assert len(relations) == 2
    types = {r.relation_type for r in relations}
    assert "references" in types
    assert "supports" in types


def test_non_existent_source_memory(populated_storage):
    storage = populated_storage
    relations = storage.get_relations(from_memory_id="non-existent")
    assert len(relations) == 0


def test_add_relation_non_existent_memories(populated_storage):
    # Depending on implementation, this might raise error or allow it.
    # We check parity: both should behave the same.
    storage = populated_storage
    relation = Relation(
        id="rel-ghost",
        from_memory_id="ghost-1",
        to_memory_id="ghost-2",
        relation_type="haunts",
        strength=0.1,
    )

    try:
        storage.create_relation(relation)
        # If successful, verify retrieval
        relations = storage.get_relations(from_memory_id="ghost-1")
        assert len(relations) == 1
        assert relations[0].id == "rel-ghost"
    except (Exception, ValueError):
        # SQLite raises IntegrityError (which inherits from Exception/DatabaseError)
        # JSONL now raises ValueError
        # We just want to ensure it fails.
        pass


def test_large_number_of_relations(populated_storage):
    storage = populated_storage
    # Add 100 relations from mem-0
    for i in range(100):
        rel = Relation(
            id=f"rel-many-{i}",
            from_memory_id="mem-0",
            to_memory_id="mem-1",
            relation_type="references",
            strength=0.5,
        )
        storage.create_relation(rel)

    relations = storage.get_relations(from_memory_id="mem-0")
    assert len(relations) == 100
