"""Tests for Markdown export utility."""

import tempfile
from pathlib import Path

import pytest
import yaml

from cortexgraph.storage.models import Memory, MemoryMetadata
from cortexgraph.tools.export import MarkdownExport


@pytest.fixture
def temp_export_dir():
    """Create a temporary directory for export."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_export_single_memory(temp_export_dir):
    """Test exporting a single memory."""
    exporter = MarkdownExport(output_dir=temp_export_dir)

    memory = Memory(
        id="test-123",
        content="This is a test memory content.\nIt has multiple lines.",
        meta=MemoryMetadata(tags=["test", "export"]),
    )

    success = exporter.export_memory(memory)
    assert success

    # Check file exists
    files = list(temp_export_dir.glob("*.md"))
    assert len(files) == 1

    # Check content
    with open(files[0]) as f:
        content = f.read()

    # Verify frontmatter
    assert content.startswith("---\n")
    parts = content.split("---\n")
    assert len(parts) >= 3

    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["id"] == "test-123"
    assert "test" in frontmatter["tags"]
    assert frontmatter["status"] == "active"

    # Verify body
    assert "This is a test memory content." in parts[2]


def test_export_batch(temp_export_dir):
    """Test exporting a batch of memories."""
    exporter = MarkdownExport(output_dir=temp_export_dir)

    memories = [Memory(id=f"mem-{i}", content=f"Memory content {i}") for i in range(5)]

    stats = exporter.export_batch(memories)

    assert stats.total == 5
    assert stats.success == 5
    assert stats.failed == 0

    files = list(temp_export_dir.glob("*.md"))
    assert len(files) == 5


def test_filename_sanitization(temp_export_dir):
    """Test that filenames are sanitized."""
    exporter = MarkdownExport(output_dir=temp_export_dir)

    # Content with invalid chars
    memory = Memory(
        id="bad-chars",
        content='Invalid: / \\ : * ? " < > | chars',
    )

    exporter.export_memory(memory)

    files = list(temp_export_dir.glob("*.md"))
    assert len(files) == 1
    filename = files[0].name

    # Should not contain invalid chars
    assert "/" not in filename
    assert ":" not in filename
    assert "?" not in filename


def test_export_with_complex_metadata(temp_export_dir):
    """Test exporting memory with complex metadata."""
    exporter = MarkdownExport(output_dir=temp_export_dir)

    memory = Memory(
        id="complex",
        content="Content",
        meta=MemoryMetadata(
            tags=["a", "b"], source="web", extra={"url": "http://example.com", "score": 0.9}
        ),
        entities=["Entity1", "Entity2"],
    )

    exporter.export_memory(memory)

    files = list(temp_export_dir.glob("*.md"))
    with open(files[0]) as f:
        content = f.read()

    parts = content.split("---\n")
    frontmatter = yaml.safe_load(parts[1])

    assert frontmatter["source"] == "web"
    assert frontmatter["extra"]["url"] == "http://example.com"
    assert "Entity1" in frontmatter["entities"]
