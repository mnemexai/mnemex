"""Tests for SQLite storage layer."""

import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from cortexgraph.storage.models import Memory, MemoryMetadata, MemoryStatus, Relation
from cortexgraph.storage.sqlite_storage import SQLiteStorage


@pytest.fixture
def temp_sqlite_storage():
    """Create a temporary SQLite storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        storage = SQLiteStorage(storage_path=storage_dir)
        storage.connect()
        yield storage
        storage.close()


def test_storage_init(temp_sqlite_storage):
    """Test storage initialization."""
    count = temp_sqlite_storage.count_memories()
    assert count == 0
    assert temp_sqlite_storage.db_path.exists()


def test_save_and_get_memory(temp_sqlite_storage):
    """Test saving and retrieving a memory."""
    memory = Memory(
        id="test-123",
        content="Test memory content",
        meta=MemoryMetadata(tags=["test"]),
        embed=[0.1, 0.2, 0.3],
    )

    temp_sqlite_storage.save_memory(memory)

    retrieved = temp_sqlite_storage.get_memory("test-123")
    assert retrieved is not None
    assert retrieved.id == "test-123"
    assert retrieved.content == "Test memory content"
    assert "test" in retrieved.meta.tags
    assert retrieved.embed == [0.1, 0.2, 0.3]


def test_update_memory(temp_sqlite_storage):
    """Test updating memory fields."""
    memory = Memory(
        id="test-456",
        content="Test content",
        use_count=0,
    )

    temp_sqlite_storage.save_memory(memory)

    # Update use count and last_used
    now = int(time.time())
    success = temp_sqlite_storage.update_memory(
        memory_id="test-456",
        last_used=now,
        use_count=5,
    )

    assert success

    updated = temp_sqlite_storage.get_memory("test-456")
    assert updated is not None
    assert updated.use_count == 5
    assert updated.last_used == now


def test_delete_memory(temp_sqlite_storage):
    """Test deleting a memory."""
    memory = Memory(id="test-789", content="To be deleted")

    temp_sqlite_storage.save_memory(memory)
    assert temp_sqlite_storage.get_memory("test-789") is not None

    success = temp_sqlite_storage.delete_memory("test-789")
    assert success
    assert temp_sqlite_storage.get_memory("test-789") is None


def test_list_memories(temp_sqlite_storage):
    """Test listing memories with filters."""
    # Create some test memories
    for i in range(5):
        memory = Memory(
            id=f"mem-{i}",
            content=f"Memory {i}",
            status=MemoryStatus.ACTIVE if i < 3 else MemoryStatus.PROMOTED,
        )
        temp_sqlite_storage.save_memory(memory)

    # List all active memories
    active = temp_sqlite_storage.list_memories(status=MemoryStatus.ACTIVE)
    assert len(active) == 3

    # List all memories
    all_mems = temp_sqlite_storage.list_memories(status=None)
    assert len(all_mems) == 5


def test_search_memories_by_tags(temp_sqlite_storage):
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

    temp_sqlite_storage.save_memory(mem1)
    temp_sqlite_storage.save_memory(mem2)
    temp_sqlite_storage.save_memory(mem3)

    # Search for python tag
    results = temp_sqlite_storage.search_memories(tags=["python"])
    assert len(results) == 2
    assert all("python" in m.meta.tags for m in results)


def test_relation_operations(temp_sqlite_storage):
    """Test relation operations."""
    # Create memories
    mem1 = Memory(id="mem-1", content="Memory 1")
    mem2 = Memory(id="mem-2", content="Memory 2")
    temp_sqlite_storage.save_memory(mem1)
    temp_sqlite_storage.save_memory(mem2)

    # Create relation
    relation = Relation(
        id="rel-1", from_memory_id="mem-1", to_memory_id="mem-2", relation_type="references"
    )
    temp_sqlite_storage.create_relation(relation)

    # Get relations
    relations = temp_sqlite_storage.get_relations(from_memory_id="mem-1")
    assert len(relations) == 1
    assert relations[0].to_memory_id == "mem-2"

    # Delete relation
    success = temp_sqlite_storage.delete_relation("rel-1")
    assert success
    assert len(temp_sqlite_storage.get_all_relations()) == 0


def test_batch_save_memories(temp_sqlite_storage):
    """Test batch saving memories."""
    memories = [Memory(id=f"batch-{i}", content=f"Batch {i}") for i in range(10)]

    temp_sqlite_storage.save_memories_batch(memories)

    assert temp_sqlite_storage.count_memories() == 10
    assert temp_sqlite_storage.get_memory("batch-0") is not None
    assert temp_sqlite_storage.get_memory("batch-9") is not None


def test_get_knowledge_graph(temp_sqlite_storage):
    """Test getting knowledge graph."""
    mem1 = Memory(id="m1", content="M1", status=MemoryStatus.ACTIVE)
    mem2 = Memory(id="m2", content="M2", status=MemoryStatus.ACTIVE)
    temp_sqlite_storage.save_memory(mem1)
    temp_sqlite_storage.save_memory(mem2)

    rel = Relation(id="r1", from_memory_id="m1", to_memory_id="m2", relation_type="test")
    temp_sqlite_storage.create_relation(rel)

    graph = temp_sqlite_storage.get_knowledge_graph()

    assert len(graph.memories) == 2
    assert len(graph.relations) == 1
    assert graph.stats["total_memories"] == 2


def test_integrity_error_handling(temp_sqlite_storage):
    """Test that foreign key constraints work (if enabled)."""
    # Try to create relation for non-existent memories
    # Note: We enabled foreign keys in connect(), so this should fail
    rel = Relation(
        id="bad-rel", from_memory_id="missing-1", to_memory_id="missing-2", relation_type="test"
    )

    with pytest.raises(sqlite3.IntegrityError):
        temp_sqlite_storage.create_relation(rel)
