from pathlib import Path

import pytest

from cortexgraph.config import Config, set_config
from cortexgraph.context import db
from cortexgraph.storage.models import Memory, MemoryStatus
from cortexgraph.tools.search import search_memory
from cortexgraph.tools.search_unified import search_unified


@pytest.fixture(autouse=True)
def setup_db(tmp_path: Path):
    storage_dir = tmp_path / "jsonl"
    cfg = Config(storage_path=storage_dir, enable_embeddings=False)
    set_config(cfg)

    # Force disconnect and clear state
    db.close()
    db.storage_path = storage_dir
    db.connect()

    # Manual clear of in-memory state for JSONLStorage
    if hasattr(db, "_memories"):
        db._memories = {}
    if hasattr(db, "_relations"):
        db._relations = {}
    if hasattr(db, "_tag_index"):
        db._tag_index = {}

    yield
    db.close()


def test_search_memory_includes_promoted():
    """Test that search_memory tool includes promoted memories by default."""
    # Create an ACTIVE memory
    db.save_memory(
        Memory(id="active-1", content="Active memory content", status=MemoryStatus.ACTIVE)
    )

    # Create a PROMOTED memory
    db.save_memory(
        Memory(id="promoted-1", content="Promoted memory content", status=MemoryStatus.PROMOTED)
    )

    # Search without specifying status - should find both
    results = search_memory(query="memory")
    found_ids = [r["id"] for r in results["results"]]

    assert "active-1" in found_ids
    assert "promoted-1" in found_ids


def test_search_memory_custom_status():
    """Test that search_memory tool respects custom status parameter."""
    db.save_memory(Memory(id="m1", content="Active", status=MemoryStatus.ACTIVE))
    db.save_memory(Memory(id="m2", content="Promoted", status=MemoryStatus.PROMOTED))
    db.save_memory(Memory(id="m3", content="Archived", status=MemoryStatus.ARCHIVED))

    # Test single status
    results = search_memory(status="archived")
    found_ids = [r["id"] for r in results["results"]]
    assert found_ids == ["m3"]

    # Test list of statuses
    results = search_memory(status=["active", "archived"])
    found_ids = [r["id"] for r in results["results"]]
    assert "m1" in found_ids
    assert "m3" in found_ids
    assert "m2" not in found_ids


def test_search_unified_includes_promoted():
    """Test that search_unified tool includes promoted memories in STM results."""
    # Create an ACTIVE memory
    db.save_memory(
        Memory(id="active-1-unified", content="Active stm content", status=MemoryStatus.ACTIVE)
    )

    # Create a PROMOTED memory
    db.save_memory(
        Memory(
            id="promoted-1-unified", content="Promoted stm content", status=MemoryStatus.PROMOTED
        )
    )

    # Search without specifying status
    results = search_unified(query="stm")
    found_ids = [r["memory_id"] for r in results["results"] if r["source"] == "stm"]

    assert "active-1-unified" in found_ids
    assert "promoted-1-unified" in found_ids


def test_search_unified_custom_status():
    """Test that search_unified tool respects custom status parameter for STM."""
    db.save_memory(Memory(id="u1", content="Active", status=MemoryStatus.ACTIVE))
    db.save_memory(Memory(id="u2", content="Promoted", status=MemoryStatus.PROMOTED))

    # Only active
    results = search_unified(status="active")
    found_ids = [r["memory_id"] for r in results["results"] if r["source"] == "stm"]

    assert "u1" in found_ids
    assert "u2" not in found_ids
