from fastapi.testclient import TestClient

from cortexgraph.storage.models import GraphData, Memory, MemoryStatus, Relation
from cortexgraph.web.app import app

client = TestClient(app)


def test_get_graph_data_structure(temp_storage):
    """Verify GET /api/graph returns correct GraphData structure."""
    # Ensure we have some data
    with temp_storage as storage:
        mem1 = Memory(id="mem-a", content="Node A", status=MemoryStatus.ACTIVE)
        mem2 = Memory(id="mem-b", content="Node B", status=MemoryStatus.ACTIVE)
        storage.save_memory(mem1)
        storage.save_memory(mem2)

    response = client.get("/api/graph")
    assert response.status_code == 200

    data = response.json()
    # Validate against Pydantic model
    graph_data = GraphData(**data)

    assert isinstance(graph_data.nodes, list)
    assert isinstance(graph_data.edges, list)
    assert isinstance(graph_data.total_memories, int)
    assert isinstance(graph_data.total_relations, int)
    assert isinstance(graph_data.query_time_ms, float)


def test_get_graph_data_content(temp_storage):
    """Verify GET /api/graph returns expected content."""
    with temp_storage as storage:
        mem1 = Memory(id="mem-1", content="Memory 1", status=MemoryStatus.ACTIVE)
        mem2 = Memory(id="mem-2", content="Memory 2", status=MemoryStatus.ACTIVE)
        storage.save_memory(mem1)
        storage.save_memory(mem2)

        relation = Relation(
            id="rel-1",
            from_memory_id="mem-1",
            to_memory_id="mem-2",
            relation_type="related_to",
            strength=0.5,
        )
        storage.create_relation(relation)

    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()

    assert len(data["nodes"]) >= 2
    assert len(data["edges"]) >= 1

    # Check node properties
    node_ids = [n["id"] for n in data["nodes"]]
    assert mem1.id in node_ids
    assert mem2.id in node_ids

    # Check edge properties
    edge = data["edges"][0]
    assert edge["source"] == mem1.id
    assert edge["target"] == mem2.id
    assert edge["relation_type"] == "related_to"


def test_get_filtered_graph_data(temp_storage):
    """Verify POST /api/graph/filtered returns filtered content."""
    with temp_storage as storage:
        mem1 = Memory(id="mem-1", content="Memory 1", status=MemoryStatus.ACTIVE)
        mem2 = Memory(id="mem-2", content="Memory 2", status=MemoryStatus.ARCHIVED)
        storage.save_memory(mem1)
        storage.save_memory(mem2)

    # Filter for ACTIVE only
    response = client.post("/api/graph/filtered", json={"statuses": ["active"]})
    assert response.status_code == 200
    data = response.json()

    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["id"] == "mem-1"
