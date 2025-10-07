"""Tests for storage layer."""

import tempfile
import time
from pathlib import Path

import pytest

from stm_server.storage.database import Database
from stm_server.storage.models import Memory, MemoryMetadata, MemoryStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.connect()
        yield db
        db.close()


def test_database_init(temp_db):
    """Test database initialization."""
    assert temp_db.conn is not None
    count = temp_db.count_memories()
    assert count == 0


def test_save_and_get_memory(temp_db):
    """Test saving and retrieving a memory."""
    memory = Memory(
        id="test-123",
        content="Test memory content",
        meta=MemoryMetadata(tags=["test"]),
    )

    temp_db.save_memory(memory)

    retrieved = temp_db.get_memory("test-123")
    assert retrieved is not None
    assert retrieved.id == "test-123"
    assert retrieved.content == "Test memory content"
    assert "test" in retrieved.meta.tags


def test_update_memory(temp_db):
    """Test updating memory fields."""
    memory = Memory(
        id="test-456",
        content="Test content",
        use_count=0,
    )

    temp_db.save_memory(memory)

    # Update use count and last_used
    now = int(time.time())
    success = temp_db.update_memory(
        memory_id="test-456",
        last_used=now,
        use_count=5,
    )

    assert success

    updated = temp_db.get_memory("test-456")
    assert updated is not None
    assert updated.use_count == 5
    assert updated.last_used == now


def test_delete_memory(temp_db):
    """Test deleting a memory."""
    memory = Memory(id="test-789", content="To be deleted")

    temp_db.save_memory(memory)
    assert temp_db.get_memory("test-789") is not None

    success = temp_db.delete_memory("test-789")
    assert success
    assert temp_db.get_memory("test-789") is None


def test_list_memories(temp_db):
    """Test listing memories with filters."""
    # Create some test memories
    for i in range(5):
        memory = Memory(
            id=f"mem-{i}",
            content=f"Memory {i}",
            status=MemoryStatus.ACTIVE if i < 3 else MemoryStatus.PROMOTED,
        )
        temp_db.save_memory(memory)

    # List all active memories
    active = temp_db.list_memories(status=MemoryStatus.ACTIVE)
    assert len(active) == 3

    # List all memories
    all_mems = temp_db.list_memories()
    assert len(all_mems) == 5


def test_search_memories_by_tags(temp_db):
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

    temp_db.save_memory(mem1)
    temp_db.save_memory(mem2)
    temp_db.save_memory(mem3)

    # Search for python tag
    results = temp_db.search_memories(tags=["python"])
    assert len(results) == 2
    assert all("python" in m.meta.tags for m in results)


def test_count_memories(temp_db):
    """Test counting memories."""
    for i in range(3):
        memory = Memory(id=f"mem-{i}", content=f"Memory {i}")
        temp_db.save_memory(memory)

    count = temp_db.count_memories()
    assert count == 3

    count_active = temp_db.count_memories(status=MemoryStatus.ACTIVE)
    assert count_active == 3
