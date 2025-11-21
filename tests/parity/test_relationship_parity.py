from cortexgraph.storage.models import Memory, MemoryStatus, Relation


def test_relationship_creation_and_retrieval(storage):
    # Create two memories
    mem1 = Memory(id="mem-1", content="Memory 1", status=MemoryStatus.ACTIVE)
    mem2 = Memory(id="mem-2", content="Memory 2", status=MemoryStatus.ACTIVE)
    storage.save_memory(mem1)
    storage.save_memory(mem2)

    # Create a relation
    relation = Relation(
        id="rel-1",
        from_memory_id="mem-1",
        to_memory_id="mem-2",
        relation_type="related_to",
        strength=1.0,
    )
    storage.create_relation(relation)

    # Verify retrieval
    relations = storage.get_relations(from_memory_id="mem-1")
    assert len(relations) == 1
    assert relations[0].id == "rel-1"
    assert relations[0].to_memory_id == "mem-2"

    # Verify reverse retrieval if supported or applicable
    # Note: CortexGraph relations are directed, but we might want to check if we can find incoming
    # storage.get_relations usually filters by from_memory_id.
    # If we want incoming, we'd need to check if the API supports it.
    # Assuming get_relations has to_memory_id filter?
    # Let's check the signature in a separate step or assume basic for now.
