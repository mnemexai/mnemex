"""Tests for memory consolidation logic."""

import tempfile
import time
from pathlib import Path

import pytest

from cortexgraph.core.consolidation import (
    calculate_merged_strength,
    execute_consolidation,
    generate_consolidation_preview,
    merge_content_smart,
    merge_entities,
    merge_metadata,
    merge_tags,
)
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Cluster, Memory, MemoryMetadata


@pytest.fixture
def temp_storage():
    """Create a temporary JSONL storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()
        yield storage
        storage.close()


@pytest.fixture
def sample_memories():
    """Create sample memories for testing."""
    return [
        Memory(
            id="mem-1",
            content="Python is a great programming language for beginners",
            meta=MemoryMetadata(tags=["python", "programming"]),
            entities=["Python"],
            use_count=3,
            strength=1.0,
            created_at=int(time.time()) - 86400,  # 1 day ago
            last_used=int(time.time()) - 3600,  # 1 hour ago
        ),
        Memory(
            id="mem-2",
            content="Python is excellent for data science and machine learning",
            meta=MemoryMetadata(tags=["python", "data-science"]),
            entities=["Python"],
            use_count=5,
            strength=1.2,
            created_at=int(time.time()) - 172800,  # 2 days ago
            last_used=int(time.time()) - 1800,  # 30 min ago
        ),
        Memory(
            id="mem-3",
            content="Python has a simple and readable syntax",
            meta=MemoryMetadata(tags=["python", "syntax"]),
            entities=["Python"],
            use_count=2,
            strength=0.9,
            created_at=int(time.time()) - 259200,  # 3 days ago
            last_used=int(time.time()) - 7200,  # 2 hours ago
        ),
    ]


def test_merge_tags():
    """Test merging tags from multiple memories."""
    memories = [
        Memory(id="1", content="test", meta=MemoryMetadata(tags=["a", "b"])),
        Memory(id="2", content="test", meta=MemoryMetadata(tags=["b", "c"])),
        Memory(id="3", content="test", meta=MemoryMetadata(tags=["c", "d"])),
    ]

    merged = merge_tags(memories)
    assert sorted(merged) == ["a", "b", "c", "d"]
    assert len(merged) == 4  # No duplicates


def test_merge_entities():
    """Test merging entities from multiple memories."""
    memories = [
        Memory(id="1", content="test", entities=["Python", "Django"]),
        Memory(id="2", content="test", entities=["Python", "Flask"]),
        Memory(id="3", content="test", entities=["JavaScript"]),
    ]

    merged = merge_entities(memories)
    assert sorted(merged) == ["Django", "Flask", "JavaScript", "Python"]
    assert len(merged) == 4


def test_merge_metadata():
    """Test merging metadata from multiple memories."""
    memories = [
        Memory(
            id="1",
            content="test",
            meta=MemoryMetadata(tags=["a"], source="source1", context="ctx1"),
        ),
        Memory(
            id="2",
            content="test",
            meta=MemoryMetadata(tags=["b"], source="source2", context="ctx2"),
        ),
    ]

    merged = merge_metadata(memories)
    assert "a" in merged.tags
    assert "b" in merged.tags
    assert "source1" in merged.source
    assert "source2" in merged.source
    assert "ctx1" in merged.context
    assert "ctx2" in merged.context


def test_merge_content_duplicates():
    """Test merging near-duplicate content."""
    memories = [
        Memory(id="1", content="Python is great"),
        Memory(id="2", content="Python is great for programming"),
        Memory(id="3", content="Python is great"),
    ]

    merged = merge_content_smart(memories)
    # Should keep the longest/most detailed version
    assert merged == "Python is great for programming"


def test_merge_content_distinct():
    """Test merging distinct but related content."""
    memories = [
        Memory(id="1", content="Python is easy to learn"),
        Memory(id="2", content="Python has great libraries"),
        Memory(id="3", content="Python is widely used"),
    ]

    merged = merge_content_smart(memories)
    # Should combine all distinct pieces
    assert "easy to learn" in merged
    assert "great libraries" in merged
    assert "widely used" in merged


def test_merge_content_single():
    """Test merging single memory."""
    memories = [Memory(id="1", content="Single memory")]

    merged = merge_content_smart(memories)
    assert merged == "Single memory"


def test_merge_content_empty():
    """Test merging empty list."""
    merged = merge_content_smart([])
    assert merged == ""


def test_calculate_merged_strength():
    """Test calculating strength for merged memory."""
    memories = [
        Memory(id="1", content="test", strength=1.0),
        Memory(id="2", content="test", strength=1.5),
        Memory(id="3", content="test", strength=0.8),
    ]

    # High cohesion should give bonus
    strength = calculate_merged_strength(memories, cohesion=0.9)
    assert strength > 1.5  # Max + bonus
    assert strength <= 2.0  # Capped at 2.0

    # Low cohesion gives smaller bonus
    strength_low = calculate_merged_strength(memories, cohesion=0.5)
    assert strength_low < strength


def test_calculate_merged_strength_empty():
    """Test calculating strength for empty list."""
    strength = calculate_merged_strength([], cohesion=0.9)
    assert strength == 1.0


def test_generate_consolidation_preview(sample_memories):
    """Test generating consolidation preview."""
    cluster = Cluster(
        id="cluster-1",
        memories=sample_memories,
        centroid=None,
        cohesion=0.85,
        suggested_action="llm-review",
    )

    preview = generate_consolidation_preview(cluster)

    assert preview["can_consolidate"] is True
    assert preview["num_memories"] == 3
    assert preview["cohesion"] == 0.85
    assert preview["space_saved"] == 2  # 3 memories -> 1 memory = 2 saved

    merged = preview["merged_memory"]
    assert "Python" in merged["content"]
    assert "python" in merged["tags"]
    assert "Python" in merged["entities"]
    assert merged["use_count"] == 10  # 3 + 5 + 2
    assert merged["strength"] > 1.2  # Max + bonus


def test_generate_consolidation_preview_empty():
    """Test preview with empty cluster."""
    cluster = Cluster(
        id="cluster-1",
        memories=[],
        centroid=None,
        cohesion=0.0,
        suggested_action="keep-separate",
    )

    preview = generate_consolidation_preview(cluster)
    assert preview["can_consolidate"] is False
    assert "error" in preview


def test_generate_consolidation_preview_single():
    """Test preview with single memory."""
    memory = Memory(id="mem-1", content="Single memory")
    cluster = Cluster(
        id="cluster-1",
        memories=[memory],
        centroid=None,
        cohesion=1.0,
        suggested_action="keep-separate",
    )

    preview = generate_consolidation_preview(cluster)
    assert preview["can_consolidate"] is False
    assert "error" in preview


def test_execute_consolidation(temp_storage, sample_memories):
    """Test executing consolidation."""
    # Save original memories
    for mem in sample_memories:
        temp_storage.save_memory(mem)

    cluster = Cluster(
        id="cluster-1",
        memories=sample_memories,
        centroid=None,
        cohesion=0.85,
        suggested_action="llm-review",
    )

    result = execute_consolidation(cluster, temp_storage)

    assert result["success"] is True
    assert "new_memory_id" in result
    assert len(result["consolidated_ids"]) == 3
    assert result["space_saved"] == 2

    # Verify new memory exists
    new_mem = temp_storage.get_memory(result["new_memory_id"])
    assert new_mem is not None
    assert "Python" in new_mem.content
    assert new_mem.use_count == 10  # Sum of use counts

    # Verify originals are deleted
    for orig_id in result["consolidated_ids"]:
        assert temp_storage.get_memory(orig_id) is None

    # Verify relations were created
    relations = temp_storage.get_relations(from_memory_id=result["new_memory_id"])
    assert len(relations) == 3
    assert all(r.relation_type == "consolidated_from" for r in relations)


def test_execute_consolidation_insufficient_memories(temp_storage):
    """Test consolidation with too few memories."""
    memory = Memory(id="mem-1", content="Single memory")
    cluster = Cluster(
        id="cluster-1",
        memories=[memory],
        centroid=None,
        cohesion=1.0,
        suggested_action="keep-separate",
    )

    result = execute_consolidation(cluster, temp_storage)
    assert result["success"] is False
    assert "error" in result


def test_consolidation_preserves_timestamps(temp_storage):
    """Test that consolidation preserves earliest created_at and latest last_used."""
    now = int(time.time())

    memories = [
        Memory(
            id="mem-1",
            content="Memory 1",
            created_at=now - 3600,  # 1 hour ago
            last_used=now - 1800,  # 30 min ago
        ),
        Memory(
            id="mem-2",
            content="Memory 2",
            created_at=now - 7200,  # 2 hours ago (earliest)
            last_used=now - 3600,  # 1 hour ago
        ),
        Memory(
            id="mem-3",
            content="Memory 3",
            created_at=now - 1800,  # 30 min ago
            last_used=now - 600,  # 10 min ago (most recent)
        ),
    ]

    for mem in memories:
        temp_storage.save_memory(mem)

    cluster = Cluster(
        id="cluster-1",
        memories=memories,
        centroid=None,
        cohesion=0.8,
        suggested_action="auto-merge",
    )

    result = execute_consolidation(cluster, temp_storage)
    new_mem = temp_storage.get_memory(result["new_memory_id"])

    # Should have earliest created_at
    assert new_mem.created_at == now - 7200

    # Should have latest last_used
    assert new_mem.last_used == now - 600
