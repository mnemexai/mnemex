import pytest
from fastapi.testclient import TestClient

from cortexgraph.storage.models import Memory, MemoryMetadata, MemoryStatus
from cortexgraph.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_full_metadata_api(client, temp_storage):
    """Test that the API returns all metadata fields."""
    # Create a memory with full metadata
    memory = Memory(
        id="meta-test-1",
        content="Test content with full metadata",
        meta=MemoryMetadata(
            tags=["test", "metadata"],
            source="integration-test",
            context="testing context",
        ),
        status=MemoryStatus.PROMOTED,
        strength=0.85,
        entities=["Entity1", "Entity2"],
        promoted_at=1700000000,
        promoted_to="Vault/Test/Path.md",
        review_count=5,
        last_review_at=1700000100,
        review_priority=0.75,
    )

    # Add to storage
    temp_storage.save_memory(memory)

    # Fetch via API
    response = client.get(f"/api/memories/{memory.id}")
    assert response.status_code == 200
    data = response.json()

    # Verify all fields
    assert data["id"] == memory.id
    assert data["content"] == memory.content
    assert data["status"] == "promoted"
    assert data["tags"] == ["test", "metadata"]
    assert data["strength"] == 0.85
    assert data["entities"] == ["Entity1", "Entity2"]
    assert data["source"] == "integration-test"
    assert data["context"] == "testing context"
    assert data["promoted_at"] == 1700000000
    assert data["promoted_to"] == "Vault/Test/Path.md"
    assert data["review_count"] == 5
    assert data["last_review_at"] == 1700000100
    assert data["review_priority"] == 0.75
