"""Tests for JSONL storage layer."""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Memory, MemoryMetadata, MemoryStatus, Relation


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


# ============================================================================
# Initialization edge cases
# ============================================================================


def test_init_with_none_storage_path():
    """Test initialization with None storage_path uses config default."""
    storage = JSONLStorage(storage_path=None)
    # Should use config's storage_path
    assert storage.storage_dir is not None
    assert storage.storage_dir.exists()


def test_init_with_string_path():
    """Test initialization with string path converts to Path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONLStorage(storage_path=tmpdir)
        assert isinstance(storage.storage_dir, Path)
        assert str(storage.storage_dir) == tmpdir


def test_storage_path_property_getter_setter():
    """Test storage_path property getter and setter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONLStorage()

        # Test getter
        original_path = storage.storage_path
        assert isinstance(original_path, Path)

        # Test setter with Path
        new_path = Path(tmpdir) / "new_storage"
        storage.storage_path = new_path
        assert storage.storage_path == new_path
        assert storage.storage_dir == new_path
        assert new_path.exists()

        # Test setter with string
        new_path2 = Path(tmpdir) / "string_storage"
        storage.storage_path = str(new_path2)
        assert storage.storage_path == new_path2
        assert isinstance(storage.storage_path, Path)


# ============================================================================
# Connection and loading
# ============================================================================


def test_load_existing_jsonl_with_data():
    """Test loading from existing JSONL files with data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)

        # Create a JSONL file with existing data
        memories_path = storage_dir / "memories.jsonl"
        with open(memories_path, "w") as f:
            mem1 = Memory(id="existing-1", content="Existing memory 1")
            mem2 = Memory(
                id="existing-2",
                content="Existing memory 2",
                meta=MemoryMetadata(tags=["test", "existing"]),
            )
            f.write(mem1.model_dump_json() + "\n")
            f.write(mem2.model_dump_json() + "\n")

        # Load storage
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()

        # Verify data was loaded
        assert storage.count_memories() == 2
        loaded1 = storage.get_memory("existing-1")
        assert loaded1 is not None
        assert loaded1.content == "Existing memory 1"

        loaded2 = storage.get_memory("existing-2")
        assert loaded2 is not None
        assert "test" in loaded2.meta.tags
        assert "existing" in loaded2.meta.tags

        storage.close()


def test_load_with_deletion_markers():
    """Test loading with deletion markers (_deleted)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        memories_path = storage_dir / "memories.jsonl"

        # Create JSONL with memory and deletion marker
        with open(memories_path, "w") as f:
            mem1 = Memory(id="mem-1", content="Memory 1")
            mem2 = Memory(id="mem-2", content="Memory 2")
            f.write(mem1.model_dump_json() + "\n")
            f.write(mem2.model_dump_json() + "\n")
            # Add deletion marker for mem-1
            f.write('{"id": "mem-1", "_deleted": true}\n')

        # Load storage
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()

        # mem-1 should be deleted, mem-2 should exist
        assert storage.get_memory("mem-1") is None
        assert storage.get_memory("mem-2") is not None
        assert storage.count_memories() == 1
        assert "mem-1" in storage._deleted_memory_ids

        storage.close()


def test_load_handles_empty_lines():
    """Test that empty lines in JSONL are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        memories_path = storage_dir / "memories.jsonl"

        # Create JSONL with empty lines
        with open(memories_path, "w") as f:
            mem1 = Memory(id="mem-1", content="Memory 1")
            f.write(mem1.model_dump_json() + "\n")
            f.write("\n")  # Empty line
            f.write("   \n")  # Whitespace-only line
            mem2 = Memory(id="mem-2", content="Memory 2")
            f.write(mem2.model_dump_json() + "\n")

        # Load storage - should not fail
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()

        assert storage.count_memories() == 2
        assert storage.get_memory("mem-1") is not None
        assert storage.get_memory("mem-2") is not None

        storage.close()


def test_tag_index_rebuilding(temp_storage):
    """Test that tag index is rebuilt on connect."""
    # Add memories with tags
    mem1 = Memory(id="mem-1", content="Memory 1", meta=MemoryMetadata(tags=["python", "test"]))
    mem2 = Memory(id="mem-2", content="Memory 2", meta=MemoryMetadata(tags=["python", "dev"]))
    mem3 = Memory(id="mem-3", content="Memory 3", meta=MemoryMetadata(tags=["javascript"]))

    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)
    temp_storage.save_memory(mem3)

    # Verify tag index was built
    assert "python" in temp_storage._tag_index
    assert "test" in temp_storage._tag_index
    assert "javascript" in temp_storage._tag_index

    # Check index contents
    assert "mem-1" in temp_storage._tag_index["python"]
    assert "mem-2" in temp_storage._tag_index["python"]
    assert len(temp_storage._tag_index["python"]) == 2

    # Search should use tag index
    results = temp_storage.search_memories(tags=["python"])
    assert len(results) == 2


# ============================================================================
# Relations
# ============================================================================


def test_create_and_get_relation(temp_storage):
    """Test creating and retrieving relations."""
    # Create some memories
    mem1 = Memory(id="mem-1", content="Memory 1")
    mem2 = Memory(id="mem-2", content="Memory 2")
    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)

    # Create a relation
    relation = Relation(
        id="rel-1", from_memory_id="mem-1", to_memory_id="mem-2", relation_type="references"
    )
    temp_storage.create_relation(relation)

    # Get all relations
    relations = temp_storage.get_all_relations()
    assert len(relations) == 1
    assert relations[0].id == "rel-1"
    assert relations[0].from_memory_id == "mem-1"
    assert relations[0].to_memory_id == "mem-2"


def test_delete_relation(temp_storage):
    """Test deleting a relation."""
    # Create memories and relation
    mem1 = Memory(id="mem-1", content="Memory 1")
    mem2 = Memory(id="mem-2", content="Memory 2")
    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)

    relation = Relation(
        id="rel-1", from_memory_id="mem-1", to_memory_id="mem-2", relation_type="references"
    )
    temp_storage.create_relation(relation)

    # Delete relation
    success = temp_storage.delete_relation("rel-1")
    assert success
    assert len(temp_storage.get_all_relations()) == 0
    assert "rel-1" in temp_storage._deleted_relation_ids

    # Try deleting non-existent relation
    success = temp_storage.delete_relation("non-existent")
    assert not success


def test_get_relations_filtering(temp_storage):
    """Test filtering relations by source, target, and type."""
    # Create memories
    for i in range(1, 5):
        temp_storage.save_memory(Memory(id=f"mem-{i}", content=f"Memory {i}"))

    # Create various relations
    temp_storage.create_relation(
        Relation(
            id="rel-1", from_memory_id="mem-1", to_memory_id="mem-2", relation_type="references"
        )
    )
    temp_storage.create_relation(
        Relation(
            id="rel-2", from_memory_id="mem-1", to_memory_id="mem-3", relation_type="similar_to"
        )
    )
    temp_storage.create_relation(
        Relation(
            id="rel-3", from_memory_id="mem-2", to_memory_id="mem-3", relation_type="references"
        )
    )
    temp_storage.create_relation(
        Relation(
            id="rel-4", from_memory_id="mem-3", to_memory_id="mem-4", relation_type="follows_from"
        )
    )

    # Filter by source
    from_mem1 = temp_storage.get_relations(from_memory_id="mem-1")
    assert len(from_mem1) == 2
    assert all(r.from_memory_id == "mem-1" for r in from_mem1)

    # Filter by target
    to_mem3 = temp_storage.get_relations(to_memory_id="mem-3")
    assert len(to_mem3) == 2
    assert all(r.to_memory_id == "mem-3" for r in to_mem3)

    # Filter by type
    references = temp_storage.get_relations(relation_type="references")
    assert len(references) == 2
    assert all(r.relation_type == "references" for r in references)

    # Filter by multiple criteria
    specific = temp_storage.get_relations(from_memory_id="mem-1", relation_type="references")
    assert len(specific) == 1
    assert specific[0].id == "rel-1"


def test_load_relations_with_deletion_markers():
    """Test loading relations with deletion markers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        relations_path = storage_dir / "relations.jsonl"

        # Create JSONL with relations and deletion marker
        with open(relations_path, "w") as f:
            rel1 = Relation(
                id="rel-1", from_memory_id="m1", to_memory_id="m2", relation_type="references"
            )
            rel2 = Relation(
                id="rel-2", from_memory_id="m2", to_memory_id="m3", relation_type="similar_to"
            )
            f.write(rel1.model_dump_json() + "\n")
            f.write(rel2.model_dump_json() + "\n")
            # Add deletion marker for rel-1
            f.write('{"id": "rel-1", "_deleted": true}\n')

        # Load storage
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()

        # rel-1 should be deleted, rel-2 should exist
        all_relations = storage.get_all_relations()
        assert len(all_relations) == 1
        assert all_relations[0].id == "rel-2"
        assert "rel-1" in storage._deleted_relation_ids

        storage.close()


# ============================================================================
# Enhanced search functionality
# ============================================================================


def test_search_with_window_days(temp_storage):
    """Test search with window_days parameter."""
    now = int(time.time())

    # Create memories with different last_used times
    old_mem = Memory(id="old", content="Old memory", last_used=now - 10 * 86400)  # 10 days ago
    recent_mem = Memory(
        id="recent", content="Recent memory", last_used=now - 2 * 86400
    )  # 2 days ago
    new_mem = Memory(id="new", content="New memory", last_used=now)

    temp_storage.save_memory(old_mem)
    temp_storage.save_memory(recent_mem)
    temp_storage.save_memory(new_mem)

    # Search within 7 days
    results = temp_storage.search_memories(window_days=7, limit=10)
    assert len(results) == 2
    result_ids = [m.id for m in results]
    assert "new" in result_ids
    assert "recent" in result_ids
    assert "old" not in result_ids

    # Search within 1 day
    results = temp_storage.search_memories(window_days=1, limit=10)
    assert len(results) == 1
    assert results[0].id == "new"


def test_search_with_status_none(temp_storage):
    """Test search with status=None returns all statuses."""
    mem1 = Memory(id="m1", content="Active", status=MemoryStatus.ACTIVE)
    mem2 = Memory(id="m2", content="Promoted", status=MemoryStatus.PROMOTED)
    mem3 = Memory(id="m3", content="Archived", status=MemoryStatus.ARCHIVED)

    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)
    temp_storage.save_memory(mem3)

    # Search with status=None should return all
    results = temp_storage.search_memories(status=None, limit=10)
    assert len(results) == 3


def test_search_with_limit(temp_storage):
    """Test search respects limit parameter."""
    for i in range(10):
        mem = Memory(id=f"mem-{i}", content=f"Memory {i}")
        temp_storage.save_memory(mem)

    # Test default limit
    results = temp_storage.search_memories(limit=10)
    assert len(results) == 10

    # Test custom limit
    results = temp_storage.search_memories(limit=5)
    assert len(results) == 5

    # Test limit larger than available
    results = temp_storage.search_memories(limit=20)
    assert len(results) == 10


def test_search_combines_filters(temp_storage):
    """Test search with multiple filters combined."""
    now = int(time.time())

    # Create memories with various properties
    mem1 = Memory(
        id="m1",
        content="Python dev",
        meta=MemoryMetadata(tags=["python", "dev"]),
        status=MemoryStatus.ACTIVE,
        last_used=now - 1 * 86400,
    )
    mem2 = Memory(
        id="m2",
        content="Python old",
        meta=MemoryMetadata(tags=["python", "old"]),
        status=MemoryStatus.ACTIVE,
        last_used=now - 10 * 86400,
    )
    mem3 = Memory(
        id="m3",
        content="JavaScript dev",
        meta=MemoryMetadata(tags=["javascript", "dev"]),
        status=MemoryStatus.PROMOTED,
        last_used=now - 1 * 86400,
    )

    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)
    temp_storage.save_memory(mem3)

    # Search: python tag + active status + within 7 days
    results = temp_storage.search_memories(
        tags=["python"], status=MemoryStatus.ACTIVE, window_days=7, limit=10
    )
    assert len(results) == 1
    assert results[0].id == "m1"


# ============================================================================
# Knowledge graph
# ============================================================================


def test_get_knowledge_graph(temp_storage):
    """Test get_knowledge_graph method."""
    # Create memories with different statuses
    mem1 = Memory(id="m1", content="Active 1", status=MemoryStatus.ACTIVE, use_count=5)
    mem2 = Memory(id="m2", content="Active 2", status=MemoryStatus.ACTIVE, use_count=3)
    mem3 = Memory(id="m3", content="Promoted", status=MemoryStatus.PROMOTED)

    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)
    temp_storage.save_memory(mem3)

    # Create relations
    rel1 = Relation(id="r1", from_memory_id="m1", to_memory_id="m2", relation_type="references")
    rel2 = Relation(id="r2", from_memory_id="m2", to_memory_id="m3", relation_type="promotes_to")
    temp_storage.create_relation(rel1)
    temp_storage.create_relation(rel2)

    # Get knowledge graph filtered by ACTIVE status
    graph = temp_storage.get_knowledge_graph(status=MemoryStatus.ACTIVE)

    assert len(graph.memories) == 2
    assert len(graph.relations) == 2  # Relations are not filtered
    assert graph.stats["total_memories"] == 2
    assert graph.stats["total_relations"] == 2
    assert graph.stats["status_filter"] == "active"
    assert "avg_score" in graph.stats
    assert "avg_use_count" in graph.stats
    assert graph.stats["avg_use_count"] == 4.0  # (5 + 3) / 2

    # Get knowledge graph with no status filter
    graph_all = temp_storage.get_knowledge_graph(status=None)
    assert len(graph_all.memories) == 3
    assert graph_all.stats["status_filter"] == "all"


# ============================================================================
# Batch operations
# ============================================================================


def test_batch_save_memories(temp_storage):
    """Test save_memories_batch for efficient batch saving."""
    memories = [Memory(id=f"batch-{i}", content=f"Batch memory {i}") for i in range(5)]

    temp_storage.save_memories_batch(memories)

    # Verify all were saved
    assert temp_storage.count_memories() == 5
    for i in range(5):
        mem = temp_storage.get_memory(f"batch-{i}")
        assert mem is not None
        assert mem.content == f"Batch memory {i}"


def test_batch_save_empty_list(temp_storage):
    """Test save_memories_batch with empty list."""
    temp_storage.save_memories_batch([])
    assert temp_storage.count_memories() == 0


def test_batch_delete_memories(temp_storage):
    """Test deleting multiple memories."""
    # Create memories
    for i in range(5):
        temp_storage.save_memory(Memory(id=f"del-{i}", content=f"Memory {i}"))

    assert temp_storage.count_memories() == 5

    # Delete multiple
    for i in [0, 2, 4]:
        temp_storage.delete_memory(f"del-{i}")

    assert temp_storage.count_memories() == 2
    assert temp_storage.get_memory("del-1") is not None
    assert temp_storage.get_memory("del-3") is not None
    assert temp_storage.get_memory("del-0") is None


# ============================================================================
# Persistence and compaction
# ============================================================================


def test_compact_storage(temp_storage):
    """Test compact method removes deletion markers and duplicates."""
    # Create and delete some memories
    for i in range(5):
        temp_storage.save_memory(Memory(id=f"mem-{i}", content=f"Memory {i}"))

    # Update some memories (creates duplicates in JSONL)
    temp_storage.update_memory("mem-0", use_count=5)
    temp_storage.update_memory("mem-1", use_count=3)

    # Delete some memories
    temp_storage.delete_memory("mem-2")
    temp_storage.delete_memory("mem-3")

    # Count lines in JSONL before compaction
    with open(temp_storage.memories_path) as f:
        lines_before = sum(1 for line in f if line.strip())

    # Should have: 5 creates + 2 updates + 2 deletions = 9 lines
    assert lines_before == 9

    # Compact
    stats = temp_storage.compact()

    assert stats["memories_before"] == 9
    assert stats["memories_after"] == 3  # Only 3 memories remain

    # Count lines after compaction
    with open(temp_storage.memories_path) as f:
        lines_after = sum(1 for line in f if line.strip())

    assert lines_after == 3
    assert len(temp_storage._deleted_memory_ids) == 0


def test_data_persists_across_connections():
    """Test that data persists when storage is closed and reopened."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)

        # First session: create and save data
        storage1 = JSONLStorage(storage_path=storage_dir)
        storage1.connect()

        mem = Memory(
            id="persist-1",
            content="Persistent memory",
            meta=MemoryMetadata(tags=["persist", "test"]),
        )
        storage1.save_memory(mem)

        rel = Relation(
            id="rel-persist",
            from_memory_id="persist-1",
            to_memory_id="persist-1",
            relation_type="self",
        )
        storage1.create_relation(rel)

        storage1.close()

        # Second session: verify data persists
        storage2 = JSONLStorage(storage_path=storage_dir)
        storage2.connect()

        loaded_mem = storage2.get_memory("persist-1")
        assert loaded_mem is not None
        assert loaded_mem.content == "Persistent memory"
        assert "persist" in loaded_mem.meta.tags

        loaded_rels = storage2.get_all_relations()
        assert len(loaded_rels) == 1
        assert loaded_rels[0].id == "rel-persist"

        storage2.close()


def test_compact_with_relations(temp_storage):
    """Test compact also works with relations."""
    # First create memories that relations will reference
    for i in range(4):  # Need m0, m1, m2, m3
        temp_storage.save_memory(
            Memory(
                id=f"m{i}",
                content=f"Memory {i}",
            )
        )

    # Create relations
    for i in range(3):
        temp_storage.create_relation(
            Relation(
                id=f"rel-{i}",
                from_memory_id=f"m{i}",
                to_memory_id=f"m{i + 1}",
                relation_type="test",
            )
        )

    # Delete one
    temp_storage.delete_relation("rel-1")

    # Compact
    stats = temp_storage.compact()

    assert stats["relations_before"] == 4  # 3 creates + 1 delete
    assert stats["relations_after"] == 2
    assert len(temp_storage._deleted_relation_ids) == 0


# ============================================================================
# Error handling
# ============================================================================


def test_get_nonexistent_memory(temp_storage):
    """Test getting a non-existent memory returns None."""
    result = temp_storage.get_memory("does-not-exist")
    assert result is None


def test_update_nonexistent_memory(temp_storage):
    """Test updating a non-existent memory returns False."""
    result = temp_storage.update_memory("does-not-exist", use_count=5)
    assert result is False


def test_delete_nonexistent_memory(temp_storage):
    """Test deleting a non-existent memory returns False."""
    result = temp_storage.delete_memory("does-not-exist")
    assert result is False


def test_operations_without_connect():
    """Test that operations fail gracefully without connect."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONLStorage(storage_path=Path(tmpdir))
        # Don't call connect()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.save_memory(Memory(id="test", content="Test"))

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.get_memory("test")

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.list_memories()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.delete_memory("test")


# ============================================================================
# Status filtering and list operations
# ============================================================================


def test_list_memories_with_different_statuses(temp_storage):
    """Test list_memories filters correctly by different statuses."""
    # Create memories with different statuses
    temp_storage.save_memory(Memory(id="m1", content="Active 1", status=MemoryStatus.ACTIVE))
    temp_storage.save_memory(Memory(id="m2", content="Active 2", status=MemoryStatus.ACTIVE))
    temp_storage.save_memory(Memory(id="m3", content="Promoted", status=MemoryStatus.PROMOTED))
    temp_storage.save_memory(Memory(id="m4", content="Archived", status=MemoryStatus.ARCHIVED))

    # Test filtering
    active = temp_storage.list_memories(status=MemoryStatus.ACTIVE)
    assert len(active) == 2

    promoted = temp_storage.list_memories(status=MemoryStatus.PROMOTED)
    assert len(promoted) == 1
    assert promoted[0].id == "m3"

    archived = temp_storage.list_memories(status=MemoryStatus.ARCHIVED)
    assert len(archived) == 1
    assert archived[0].id == "m4"

    all_mems = temp_storage.list_memories(status=None)
    assert len(all_mems) == 4


def test_list_memories_with_limit_offset(temp_storage):
    """Test list_memories pagination with limit and offset."""
    # Create 10 memories with different last_used times
    now = int(time.time())
    for i in range(10):
        mem = Memory(
            id=f"page-{i}", content=f"Memory {i}", last_used=now - i * 100
        )  # Decreasing timestamps
        temp_storage.save_memory(mem)

    # Get first page
    page1 = temp_storage.list_memories(limit=3, offset=0)
    assert len(page1) == 3
    assert page1[0].id == "page-0"  # Most recent

    # Get second page
    page2 = temp_storage.list_memories(limit=3, offset=3)
    assert len(page2) == 3
    assert page2[0].id == "page-3"

    # Get with offset only
    rest = temp_storage.list_memories(offset=7)
    assert len(rest) == 3


def test_count_memories_by_status(temp_storage):
    """Test count_memories with status filter."""
    temp_storage.save_memory(Memory(id="m1", content="A", status=MemoryStatus.ACTIVE))
    temp_storage.save_memory(Memory(id="m2", content="B", status=MemoryStatus.ACTIVE))
    temp_storage.save_memory(Memory(id="m3", content="C", status=MemoryStatus.PROMOTED))

    assert temp_storage.count_memories(status=MemoryStatus.ACTIVE) == 2
    assert temp_storage.count_memories(status=MemoryStatus.PROMOTED) == 1
    assert temp_storage.count_memories(status=MemoryStatus.ARCHIVED) == 0
    assert temp_storage.count_memories(status=None) == 3


# ============================================================================
# Additional coverage
# ============================================================================


def test_context_manager():
    """Test using storage as a context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)

        with JSONLStorage(storage_path=storage_dir) as storage:
            assert storage._connected
            storage.save_memory(Memory(id="ctx-1", content="Context test"))
            assert storage.get_memory("ctx-1") is not None

        # After exiting context, should be closed
        assert not storage._connected


def test_get_all_embeddings(temp_storage):
    """Test get_all_embeddings returns only active memories with embeddings."""
    mem1 = Memory(
        id="m1", content="With embedding", embed=[0.1, 0.2, 0.3], status=MemoryStatus.ACTIVE
    )
    mem2 = Memory(id="m2", content="No embedding", status=MemoryStatus.ACTIVE)
    mem3 = Memory(
        id="m3",
        content="Promoted with embedding",
        embed=[0.4, 0.5, 0.6],
        status=MemoryStatus.PROMOTED,
    )

    temp_storage.save_memory(mem1)
    temp_storage.save_memory(mem2)
    temp_storage.save_memory(mem3)

    embeddings = temp_storage.get_all_embeddings()

    # Should only get active memory with embedding
    assert len(embeddings) == 1
    assert "m1" in embeddings
    assert embeddings["m1"] == [0.1, 0.2, 0.3]
    assert "m2" not in embeddings  # No embedding
    assert "m3" not in embeddings  # Not active


def test_update_memory_all_fields(temp_storage):
    """Test update_memory updates all fields correctly."""
    now = int(time.time())

    mem = Memory(id="update-all", content="Test memory")
    temp_storage.save_memory(mem)

    # Update all fields
    success = temp_storage.update_memory(
        memory_id="update-all",
        last_used=now + 100,
        use_count=10,
        strength=0.8,
        status=MemoryStatus.PROMOTED,
        promoted_at=now + 200,
        promoted_to="/vault/promoted.md",
    )

    assert success

    updated = temp_storage.get_memory("update-all")
    assert updated.last_used == now + 100
    assert updated.use_count == 10
    assert updated.strength == 0.8
    assert updated.status == MemoryStatus.PROMOTED
    assert updated.promoted_at == now + 200
    assert updated.promoted_to == "/vault/promoted.md"


def test_connect_multiple_times(temp_storage):
    """Test that calling connect multiple times is safe."""
    # temp_storage is already connected
    assert temp_storage._connected

    # Call connect again
    temp_storage.connect()

    # Should still be connected and work fine
    assert temp_storage._connected
    temp_storage.save_memory(Memory(id="test", content="Test"))
    assert temp_storage.get_memory("test") is not None


# ============================================================================
# Async operations and storage stats
# ============================================================================


def test_save_memory_async(temp_storage):
    """Test async save_memory method."""

    async def run_test():
        mem = Memory(id="async-1", content="Async memory")
        await temp_storage.save_memory_async(mem)

        # Verify it was saved
        retrieved = temp_storage.get_memory("async-1")
        assert retrieved is not None
        assert retrieved.content == "Async memory"

    asyncio.run(run_test())


def test_get_storage_stats(temp_storage):
    """Test get_storage_stats method."""
    # Create some memories and relations
    for i in range(5):
        temp_storage.save_memory(Memory(id=f"stat-{i}", content=f"Memory {i}"))

    for i in range(3):
        temp_storage.create_relation(
            Relation(
                id=f"rel-stat-{i}",
                from_memory_id=f"stat-{i}",
                to_memory_id=f"stat-{i + 1}",
                relation_type="test",
            )
        )

    # Delete one memory and one relation to create compaction potential
    temp_storage.delete_memory("stat-0")
    temp_storage.delete_relation("rel-stat-0")

    # Get stats
    stats = temp_storage.get_storage_stats()

    assert "memories" in stats
    assert "relations" in stats

    # Check memory stats
    assert stats["memories"]["active"] == 4  # 5 - 1 deleted
    assert stats["memories"]["total_lines"] >= 6  # 5 creates + 1 delete
    assert stats["memories"]["file_size_bytes"] > 0

    # Check relation stats
    assert stats["relations"]["active"] == 2  # 3 - 1 deleted
    assert stats["relations"]["total_lines"] >= 4  # 3 creates + 1 delete
    assert stats["relations"]["file_size_bytes"] > 0


def test_get_storage_stats_empty(temp_storage):
    """Test get_storage_stats on empty storage."""
    stats = temp_storage.get_storage_stats()

    assert stats["memories"]["active"] == 0
    assert stats["memories"]["total_lines"] == 0
    assert stats["memories"]["file_size_bytes"] == 0

    assert stats["relations"]["active"] == 0
    assert stats["relations"]["total_lines"] == 0
    assert stats["relations"]["file_size_bytes"] == 0


def test_operations_require_connection_all_methods():
    """Test that all major operations check for connection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONLStorage(storage_path=Path(tmpdir))
        # Don't call connect()

        # Test all methods that should raise RuntimeError
        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.update_memory("test", use_count=1)

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.search_memories()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.count_memories()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.get_all_embeddings()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.create_relation(
                Relation(id="r1", from_memory_id="m1", to_memory_id="m2", relation_type="test")
            )

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.get_relations()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.get_all_relations()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.delete_relation("test")

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.get_knowledge_graph()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.compact()

        with pytest.raises(RuntimeError, match="Storage not connected"):
            storage.get_storage_stats()


def test_save_memories_batch_updates_tag_index(temp_storage):
    """Test that batch save doesn't update tag index (as per implementation)."""
    memories = [
        Memory(id=f"batch-tag-{i}", content=f"Memory {i}", meta=MemoryMetadata(tags=[f"tag{i}"]))
        for i in range(3)
    ]

    temp_storage.save_memories_batch(memories)

    # Verify all memories were saved
    assert temp_storage.count_memories() == 3
    for i in range(3):
        mem = temp_storage.get_memory(f"batch-tag-{i}")
        assert mem is not None
