"""Tests for JSONL storage layer."""

import tempfile
import time
from pathlib import Path

import pytest

from mnemex.storage.jsonl_storage import JSONLStorage
from mnemex.storage.models import Memory, MemoryMetadata, MemoryStatus


@pytest.fixture
def temp_storage():
    """Create a temporary JSONL storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()
        yield storage
        storage.close()


def test_storage_init(temp_storage):
    """Test storage initialization."""
    count = temp_storage.count_memories()
    assert count == 0


def test_save_and_get_memory(temp_storage):
    """Test saving and retrieving a memory."""
    memory = Memory(
        id="test-123",
        content="Test memory content",
        meta=MemoryMetadata(tags=["test"]),
    )

    temp_storage.save_memory(memory)

    retrieved = temp_storage.get_memory("test-123")
    assert retrieved is not None
    assert retrieved.id == "test-123"
    assert retrieved.content == "Test memory content"
    assert "test" in retrieved.meta.tags


def test_update_memory(temp_storage):
    """Test updating memory fields."""
    memory = Memory(
        id="test-456",
        content="Test content",
        use_count=0,
    )

    temp_storage.save_memory(memory)

    # Update use count and last_used
    now = int(time.time())
    success = temp_storage.update_memory(
        memory_id="test-456",
        last_used=now,
        use_count=5,
    )

    assert success

    updated = temp_storage.get_memory("test-456")
    assert updated is not None
    assert updated.use_count == 5
    assert updated.last_used == now


def test_delete_memory(temp_storage):
    """Test deleting a memory."""
    memory = Memory(id="test-789", content="To be deleted")

    temp_storage.save_memory(memory)
    assert temp_storage.get_memory("test-789") is not None

    success = temp_storage.delete_memory("test-789")
    assert success
    assert temp_storage.get_memory("test-789") is None


def test_list_memories(temp_storage):
    """Test listing memories with filters."""
    # Create some test memories
    for i in range(5):
        memory = Memory(
            id=f"mem-{i}",
            content=f"Memory {i}",
            status=MemoryStatus.ACTIVE if i < 3 else MemoryStatus.PROMOTED,
        )
        temp_storage.save_memory(memory)

    # List all active memories
    active = temp_storage.list_memories(status=MemoryStatus.ACTIVE)
    assert len(active) == 3

    # List all memories
    all_mems = temp_storage.list_memories()
    assert len(all_mems) == 5


def test_search_memories_by_tags(temp_storage):
    """Test searching memories by tags."""
    mem1 = Memory(
        id="mem-1",
        content="Python tutorial",
        meta=MemoryMetadata(tags=["python", "tutorial"]),
    )
    mem2 = Memory(
        id="mem-2",
        content="JavaScript guide",
        meta=MemoryMetadata(tags=["javascript", "guide"]),
    )
    mem3 = Memory(
        id="mem-3",
        content="Python guide",
        meta=MemoryMetadata(tags=["python", "guide"]),
    )

    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)
    temp_storage.save_memory(mem3)

    # Search for python tag
    results = temp_storage.search_memories(tags=["python"])
    assert len(results) == 2
    assert all("python" in m.meta.tags for m in results)


def test_count_memories(temp_storage):
    """Test counting memories."""
    for i in range(3):
        memory = Memory(id=f"mem-{i}", content=f"Memory {i}")
        temp_storage.save_memory(memory)

    count = temp_storage.count_memories()
    assert count == 3

    count_active = temp_storage.count_memories(status=MemoryStatus.ACTIVE)
    assert count_active == 3
