import pytest
from fastapi.testclient import TestClient

from cortexgraph.storage.models import Memory, MemoryStatus, Relation
from cortexgraph.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def populated_storage(temp_storage):
    # Create memories
    mem1 = Memory(id="mem-1", content="Memory 1", status=MemoryStatus.ACTIVE)
    mem2 = Memory(id="mem-2", content="Memory 2", status=MemoryStatus.ACTIVE)
    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)

    # Create relation
    relation = Relation(
        id="rel-1",
        from_memory_id="mem-1",
        to_memory_id="mem-2",
        relation_type="related_to",
        strength=0.8,
    )
    temp_storage.create_relation(relation)
    return temp_storage


def test_get_memory_relationships_contract(client, populated_storage):
    # This test defines the contract for the GET /api/memories/{id}/relationships endpoint
    response = client.get("/api/memories/mem-1/relationships")

    # Verify status code
    assert response.status_code == 200

    # Verify response structure
    data = response.json()
    assert "relationships" in data
    assert isinstance(data["relationships"], list)
    assert len(data["relationships"]) == 1

    # Verify relationship item structure
    rel = data["relationships"][0]
    assert "id" in rel
    assert "target_memory_id" in rel
    assert "relation_type" in rel
    assert "strength" in rel
    assert "direction" in rel  # Should indicate if outgoing or incoming

    # Verify values
    assert rel["id"] == "rel-1"
    assert rel["target_memory_id"] == "mem-2"
    assert rel["relation_type"] == "related_to"
    assert rel["strength"] == 0.8
    assert rel["direction"] == "outgoing"


def test_get_memory_relationships_not_found(client):
    response = client.get("/api/memories/non-existent/relationships")
    assert response.status_code == 404
