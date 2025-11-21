from cortexgraph.storage.models import (
    GraphData,
    GraphEdge,
    GraphFilter,
    GraphNode,
    MemoryStatus,
)


def test_graph_node_creation():
    node = GraphNode(
        id="mem-1",
        label="Test Memory",
        tags=["test"],
        entities=["Entity1"],
        status=MemoryStatus.ACTIVE,
        decay_score=0.8,
        use_count=5,
        created_at=1000,
        last_used=2000,
    )
    assert node.id == "mem-1"
    assert node.label == "Test Memory"
    assert node.status == MemoryStatus.ACTIVE
    assert node.decay_score == 0.8


def test_graph_edge_creation():
    edge = GraphEdge(
        id="rel-1",
        source="mem-1",
        target="mem-2",
        relation_type="causes",
        strength=1.5,
    )
    assert edge.id == "rel-1"
    assert edge.source == "mem-1"
    assert edge.target == "mem-2"
    assert edge.relation_type == "causes"
    assert edge.strength == 1.5
    assert edge.directed is True


def test_graph_data_creation():
    node = GraphNode(
        id="mem-1",
        label="Test",
        tags=[],
        entities=[],
        status=MemoryStatus.ACTIVE,
        decay_score=1.0,
        use_count=1,
        created_at=1000,
        last_used=1000,
    )
    edge = GraphEdge(
        id="rel-1",
        source="mem-1",
        target="mem-2",
        relation_type="related",
        strength=1.0,
    )
    data = GraphData(
        nodes=[node],
        edges=[edge],
        total_memories=1,
        total_relations=1,
        query_time_ms=10.5,
    )
    assert len(data.nodes) == 1
    assert len(data.edges) == 1
    assert data.total_memories == 1
    assert data.query_time_ms == 10.5


def test_graph_filter_defaults():
    filters = GraphFilter()
    assert filters.min_decay_score == 0.0
    assert filters.limit == 1000
    assert filters.offset == 0
    assert filters.tags is None
