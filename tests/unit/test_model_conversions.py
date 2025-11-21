from cortexgraph.storage.models import (
    Memory,
    MemoryStatus,
    Relation,
    memory_to_graph_node,
    relation_to_graph_edge,
)


def test_memory_to_graph_node():
    memory = Memory(
        id="mem-1",
        content="This is a test memory content that is long enough to be truncated if we set the limit low enough but here we check 100 chars limit.",
        status=MemoryStatus.ACTIVE,
    )
    decay_score = 0.75

    node = memory_to_graph_node(memory, decay_score)

    assert node.id == memory.id
    assert node.status == memory.status
    assert node.decay_score == decay_score
    assert node.use_count == memory.use_count
    assert node.created_at == memory.created_at
    assert node.last_used == memory.last_used
    # Check label truncation logic if applicable, or just existence
    assert len(node.label) > 0


def test_relation_to_graph_edge():
    relation = Relation(
        id="rel-1",
        from_memory_id="mem-1",
        to_memory_id="mem-2",
        relation_type="supports",
        strength=1.0,
    )

    edge = relation_to_graph_edge(relation)

    assert edge.id == relation.id
    assert edge.source == relation.from_memory_id
    assert edge.target == relation.to_memory_id
    assert edge.relation_type == relation.relation_type
    assert edge.strength == relation.strength
