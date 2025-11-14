"""Tests for LTM index parsing and search."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from cortexgraph.storage.ltm_index import LTMDocument, LTMIndex


def write_md(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_ltm_index_parses_frontmatter_wikilinks_and_tags(tmp_path: Path) -> None:
    vault = tmp_path / "vault"

    write_md(
        vault / "Note A.md",
        """---
title: Note A
tags: [project, alpha]
---
This links to [[Note B]] and mentions #alpha.
""",
    )

    write_md(
        vault / "Note B.md",
        """---
title: Note B
tags:
  - docs
---
Backlink to [[Note A]] and #docs.
""",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    # Stats
    stats = index.get_stats()
    assert stats["total_documents"] == 2

    # Documents loaded
    doc_a = index.get_document(str((vault / "Note A.md").relative_to(vault)))
    assert doc_a is not None
    assert doc_a.title == "Note A"
    assert "project" in doc_a.tags and "alpha" in doc_a.tags
    assert "Note B" in doc_a.wikilinks

    # Hashtags extraction
    # Tags already include hashtags merged from content
    assert "alpha" in doc_a.tags

    # Search by query
    results = index.search(query="backlink", tags=None, limit=10)
    assert any(r.title == "Note B" for r in results)

    # Backlinks
    backlinks = index.get_backlinks("Note B")
    assert any(d.title == "Note A" for d in backlinks)

    # Forward links
    forward = index.get_forward_links(str((vault / "Note A.md").relative_to(vault)))
    assert any(d.title == "Note B" for d in forward)


def test_ltm_document_to_dict_and_from_dict() -> None:
    """Test LTMDocument serialization and deserialization."""
    doc = LTMDocument(
        path="test/note.md",
        title="Test Note",
        content="Test content",
        frontmatter={"author": "Test Author", "date": "2024-01-01"},
        wikilinks=["Link1", "Link2"],
        tags=["tag1", "tag2"],
        mtime=1234567890.0,
        size=1024,
    )

    # Test to_dict
    doc_dict = doc.to_dict()
    assert doc_dict["path"] == "test/note.md"
    assert doc_dict["title"] == "Test Note"
    assert doc_dict["content"] == "Test content"
    assert doc_dict["frontmatter"] == {"author": "Test Author", "date": "2024-01-01"}
    assert doc_dict["wikilinks"] == ["Link1", "Link2"]
    assert doc_dict["tags"] == ["tag1", "tag2"]
    assert doc_dict["mtime"] == 1234567890.0
    assert doc_dict["size"] == 1024

    # Test from_dict
    restored_doc = LTMDocument.from_dict(doc_dict)
    assert restored_doc.path == doc.path
    assert restored_doc.title == doc.title
    assert restored_doc.content == doc.content
    assert restored_doc.frontmatter == doc.frontmatter
    assert restored_doc.wikilinks == doc.wikilinks
    assert restored_doc.tags == doc.tags
    assert restored_doc.mtime == doc.mtime
    assert restored_doc.size == doc.size


def test_ltm_document_from_dict_with_missing_optional_fields() -> None:
    """Test LTMDocument.from_dict with missing optional fields."""
    minimal_dict = {
        "path": "test.md",
        "title": "Test",
        "content": "Content",
        "mtime": 1234567890.0,
        "size": 100,
    }

    doc = LTMDocument.from_dict(minimal_dict)
    assert doc.path == "test.md"
    assert doc.title == "Test"
    assert doc.content == "Content"
    assert doc.frontmatter == {}
    assert doc.wikilinks == []
    assert doc.tags == []
    assert doc.mtime == 1234567890.0
    assert doc.size == 100


def test_ltm_index_with_explicit_index_path(tmp_path: Path) -> None:
    """Test LTMIndex initialization with explicit index path."""
    vault = tmp_path / "vault"
    vault.mkdir()
    custom_index = tmp_path / "custom-index.jsonl"

    index = LTMIndex(vault_path=vault, index_path=custom_index)
    assert index.index_path == custom_index


def test_ltm_index_with_default_path(tmp_path: Path) -> None:
    """Test LTMIndex initialization with default path."""
    vault = tmp_path / "vault"
    vault.mkdir()

    index = LTMIndex(vault_path=vault)
    assert index.index_path == vault / ".cortexgraph-index.jsonl"


def test_ltm_index_legacy_path_fallback(tmp_path: Path) -> None:
    """Test LTMIndex falls back to legacy .stm-index.jsonl when it exists."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create legacy index file
    legacy_index = vault / ".stm-index.jsonl"
    legacy_index.write_text('{"_stats": {"total_documents": 0}}\n')

    # New path doesn't exist, so should use legacy
    index = LTMIndex(vault_path=vault)
    assert index.index_path == legacy_index


def test_ltm_index_prefers_new_path_over_legacy(tmp_path: Path) -> None:
    """Test LTMIndex prefers new path even when legacy exists."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create both index files
    new_index = vault / ".cortexgraph-index.jsonl"
    legacy_index = vault / ".stm-index.jsonl"
    new_index.write_text('{"_stats": {"total_documents": 0}}\n')
    legacy_index.write_text('{"_stats": {"total_documents": 0}}\n')

    # Should prefer new path
    index = LTMIndex(vault_path=vault)
    assert index.index_path == new_index


def test_build_index_with_files_without_frontmatter(tmp_path: Path) -> None:
    """Test building index with markdown files without frontmatter."""
    vault = tmp_path / "vault"

    write_md(
        vault / "simple.md",
        "Just some content without frontmatter.\n\nLinks to [[OtherNote]] and #simple",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    doc = index.get_document("simple.md")
    assert doc is not None
    assert doc.title == "simple"  # Should use filename as title
    assert "OtherNote" in doc.wikilinks
    assert "simple" in doc.tags


def test_build_index_with_string_tag_in_frontmatter(tmp_path: Path) -> None:
    """Test parsing frontmatter with single string tag instead of list."""
    vault = tmp_path / "vault"

    write_md(
        vault / "note.md",
        """---
title: Note with String Tag
tags: single-tag
---
Content here.
""",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    doc = index.get_document("note.md")
    assert doc is not None
    assert "single-tag" in doc.tags


def test_build_index_force_rebuild(tmp_path: Path) -> None:
    """Test force rebuild ignores existing index."""
    vault = tmp_path / "vault"

    write_md(vault / "note1.md", "First note")

    # Build initial index
    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)
    assert index.get_stats()["total_documents"] == 1

    # Add another note
    write_md(vault / "note2.md", "Second note")

    # Build with force=True should rebuild everything
    index2 = LTMIndex(vault_path=vault)
    index2.build_index(force=True, verbose=False)
    assert index2.get_stats()["total_documents"] == 2


def test_build_index_incremental_skips_unchanged(tmp_path: Path) -> None:
    """Test incremental build skips unchanged files."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Content")

    # Build initial index
    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    # Get the document's mtime
    doc = index.get_document("note.md")
    original_mtime = doc.mtime

    # Build again without force (incremental)
    # File hasn't changed, should be skipped
    index2 = LTMIndex(vault_path=vault)
    index2.build_index(force=False, verbose=False)

    doc2 = index2.get_document("note.md")
    assert doc2.mtime == original_mtime


def test_build_index_detects_deleted_files(tmp_path: Path) -> None:
    """Test index removes entries for deleted files."""
    vault = tmp_path / "vault"

    write_md(vault / "note1.md", "Note 1")
    write_md(vault / "note2.md", "Note 2")

    # Build index with both files
    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)
    assert index.get_stats()["total_documents"] == 2

    # Delete one file
    (vault / "note2.md").unlink()

    # Rebuild - should detect deletion
    index2 = LTMIndex(vault_path=vault)
    index2.build_index(force=False, verbose=False)
    assert index2.get_stats()["total_documents"] == 1
    assert index2.get_document("note1.md") is not None
    assert index2.get_document("note2.md") is None


def test_build_index_verbose_output(tmp_path: Path, capsys) -> None:
    """Test verbose output during index building."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Content")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=True)

    captured = capsys.readouterr()
    assert "Found 1 markdown files in vault" in captured.out
    assert "Index built:" in captured.out
    assert "Updated:" in captured.out
    assert "Total:" in captured.out


def test_build_index_vault_not_found(tmp_path: Path) -> None:
    """Test build_index raises error when vault doesn't exist."""
    vault = tmp_path / "nonexistent"

    index = LTMIndex(vault_path=vault)

    with pytest.raises(FileNotFoundError, match="Vault path not found"):
        index.build_index()


def test_build_index_handles_parse_errors(tmp_path: Path, capsys) -> None:
    """Test index handles files that fail to parse."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create a file that will cause parse issues (e.g., permission denied simulation)
    # We'll use a different approach - create valid markdown but test the error path
    # by creating a file with invalid encoding issues
    bad_file = vault / "bad.md"
    bad_file.write_bytes(b"\x80\x81\x82")  # Invalid UTF-8

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    # Should print warning but not crash
    captured = capsys.readouterr()
    assert "Warning: Failed to parse" in captured.out


def test_save_and_load_index(tmp_path: Path) -> None:
    """Test saving and loading index to/from JSONL."""
    vault = tmp_path / "vault"

    write_md(
        vault / "note.md",
        """---
title: Test Note
tags: [test]
---
Content with [[link]] and #hashtag
""",
    )

    # Build and save
    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    # Load in new instance
    index2 = LTMIndex(vault_path=vault)
    index2.load_index()

    # Verify loaded data
    assert index2.get_stats()["total_documents"] == 1
    doc = index2.get_document("note.md")
    assert doc is not None
    assert doc.title == "Test Note"
    assert "test" in doc.tags
    assert "link" in doc.wikilinks
    assert "hashtag" in doc.tags


def test_load_index_nonexistent_file(tmp_path: Path) -> None:
    """Test load_index handles nonexistent file gracefully."""
    vault = tmp_path / "vault"
    vault.mkdir()

    index = LTMIndex(vault_path=vault)
    index.load_index()  # Should not crash

    assert len(index._documents) == 0


def test_load_index_with_empty_lines(tmp_path: Path) -> None:
    """Test load_index handles empty lines in JSONL."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create index file with empty lines
    index_file = vault / ".cortexgraph-index.jsonl"
    index_file.write_text(
        '{"_stats": {"total_documents": 1, "total_wikilinks": 0, "last_indexed": 0, "index_time_ms": 0}}\n'
        "\n"  # Empty line
        '{"path": "test.md", "title": "Test", "content": "Content", "frontmatter": {}, "wikilinks": [], "tags": [], "mtime": 123.0, "size": 10}\n'
        "\n"  # Another empty line
    )

    index = LTMIndex(vault_path=vault)
    index.load_index()

    assert len(index._documents) == 1
    assert index.get_document("test.md") is not None


def test_search_with_query_only(tmp_path: Path) -> None:
    """Test search with query text only."""
    vault = tmp_path / "vault"

    write_md(vault / "python.md", "Python programming language")
    write_md(vault / "java.md", "Java programming language")
    write_md(vault / "cooking.md", "How to cook pasta")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    results = index.search(query="programming", limit=10)
    assert len(results) == 2
    titles = [r.title for r in results]
    assert "python" in titles
    assert "java" in titles


def test_search_with_tags_only(tmp_path: Path) -> None:
    """Test search with tags only."""
    vault = tmp_path / "vault"

    write_md(
        vault / "note1.md",
        """---
tags: [python, tutorial]
---
Content
""",
    )
    write_md(
        vault / "note2.md",
        """---
tags: [java, tutorial]
---
Content
""",
    )
    write_md(
        vault / "note3.md",
        """---
tags: [python, advanced]
---
Content
""",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    results = index.search(tags=["python"], limit=10)
    assert len(results) == 2


def test_search_with_query_and_tags(tmp_path: Path) -> None:
    """Test search with both query and tags."""
    vault = tmp_path / "vault"

    write_md(
        vault / "note1.md",
        """---
tags: [python]
---
Advanced tutorial
""",
    )
    write_md(
        vault / "note2.md",
        """---
tags: [python]
---
Basic guide
""",
    )
    write_md(
        vault / "note3.md",
        """---
tags: [java]
---
Advanced tutorial
""",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    results = index.search(query="tutorial", tags=["python"], limit=10)
    assert len(results) == 1
    assert results[0].title == "note1"


def test_search_empty_results(tmp_path: Path) -> None:
    """Test search returns empty list when no matches."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Some content")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    results = index.search(query="nonexistent", limit=10)
    assert len(results) == 0


def test_search_limit_parameter(tmp_path: Path) -> None:
    """Test search respects limit parameter."""
    vault = tmp_path / "vault"

    for i in range(10):
        write_md(vault / f"note{i}.md", "programming content")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    results = index.search(query="programming", limit=3)
    assert len(results) == 3


def test_search_prioritizes_title_matches(tmp_path: Path) -> None:
    """Test search ranks title matches higher than content matches."""
    vault = tmp_path / "vault"

    write_md(
        vault / "programming.md",
        "This is about coding",
    )
    write_md(
        vault / "cooking.md",
        "This mentions programming in the content but title doesn't match",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    results = index.search(query="programming", limit=10)
    # Title match should come first
    assert results[0].title == "programming"


def test_get_document_nonexistent(tmp_path: Path) -> None:
    """Test get_document returns None for nonexistent path."""
    vault = tmp_path / "vault"
    vault.mkdir()

    index = LTMIndex(vault_path=vault)
    doc = index.get_document("nonexistent.md")
    assert doc is None


def test_get_documents_by_tag(tmp_path: Path) -> None:
    """Test get_documents_by_tag method."""
    vault = tmp_path / "vault"

    write_md(
        vault / "note1.md",
        """---
tags: [python, tutorial]
---
Content
""",
    )
    write_md(
        vault / "note2.md",
        """---
tags: [java]
---
Content
""",
    )

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    python_docs = index.get_documents_by_tag("python")
    assert len(python_docs) == 1
    assert python_docs[0].title == "note1"


def test_get_backlinks_empty(tmp_path: Path) -> None:
    """Test get_backlinks returns empty list when no backlinks."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "No links here")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    backlinks = index.get_backlinks("nonexistent")
    assert len(backlinks) == 0


def test_get_forward_links_nonexistent_path(tmp_path: Path) -> None:
    """Test get_forward_links returns empty list for nonexistent path."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Content")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    forward_links = index.get_forward_links("nonexistent.md")
    assert len(forward_links) == 0


def test_get_forward_links_no_matches(tmp_path: Path) -> None:
    """Test get_forward_links when wikilinks don't match any documents."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Links to [[NonexistentNote]]")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    forward_links = index.get_forward_links("note.md")
    assert len(forward_links) == 0


def test_extract_wikilinks_with_aliases(tmp_path: Path) -> None:
    """Test wikilink extraction handles [[link|alias]] format."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Link with alias: [[ActualNote|Display Name]]")

    index = LTMIndex(vault_path=vault)
    doc = index.parse_markdown_file(vault / "note.md")

    assert doc is not None
    assert "ActualNote" in doc.wikilinks


def test_extract_hashtags_complex(tmp_path: Path) -> None:
    """Test hashtag extraction with complex tags."""
    vault = tmp_path / "vault"

    write_md(
        vault / "note.md",
        "Tags: #python/django #web-dev #2024 #project_alpha #nested/tag/structure",
    )

    index = LTMIndex(vault_path=vault)
    doc = index.parse_markdown_file(vault / "note.md")

    assert doc is not None
    assert "python/django" in doc.tags
    assert "web-dev" in doc.tags
    assert "2024" in doc.tags
    assert "project_alpha" in doc.tags
    assert "nested/tag/structure" in doc.tags


def test_stats_tracking(tmp_path: Path) -> None:
    """Test index statistics are tracked correctly."""
    vault = tmp_path / "vault"

    write_md(vault / "note1.md", "Links: [[Note2]] [[Note3]]")
    write_md(vault / "note2.md", "Links: [[Note1]]")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    stats = index.get_stats()
    assert stats["total_documents"] == 2
    assert stats["total_wikilinks"] == 3
    assert stats["last_indexed"] > 0
    assert stats["index_time_ms"] >= 0


def test_cli_main_basic(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test CLI main function with basic arguments."""
    vault = tmp_path / "vault"
    write_md(vault / "note.md", "Test content")

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(sys, "argv", ["ltm_index", str(vault)])
    result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "Index built:" in captured.out


def test_cli_main_with_force(tmp_path: Path, monkeypatch) -> None:
    """Test CLI main with --force flag."""
    vault = tmp_path / "vault"
    write_md(vault / "note.md", "Test content")

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(sys, "argv", ["ltm_index", str(vault), "--force"])
    result = main()

    assert result == 0


def test_cli_main_with_custom_index_path(tmp_path: Path, monkeypatch) -> None:
    """Test CLI main with --index-path argument."""
    vault = tmp_path / "vault"
    write_md(vault / "note.md", "Test content")
    custom_index = tmp_path / "custom.jsonl"

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(sys, "argv", ["ltm_index", str(vault), "--index-path", str(custom_index)])
    result = main()

    assert result == 0
    assert custom_index.exists()


def test_cli_main_with_search(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test CLI main with --search argument."""
    vault = tmp_path / "vault"
    write_md(vault / "python.md", "Python programming")
    write_md(vault / "java.md", "Java programming")

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(sys, "argv", ["ltm_index", str(vault), "--search", "python"])
    result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "Search results" in captured.out
    assert "python" in captured.out


def test_cli_main_with_tag(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test CLI main with --tag argument."""
    vault = tmp_path / "vault"
    write_md(
        vault / "note.md",
        """---
tags: [tutorial]
---
Content
""",
    )

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(sys, "argv", ["ltm_index", str(vault), "--tag", "tutorial"])
    result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "Search results" in captured.out


def test_cli_main_with_search_and_tag(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test CLI main with both --search and --tag."""
    vault = tmp_path / "vault"
    write_md(
        vault / "note.md",
        """---
tags: [python]
---
Tutorial content
""",
    )

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(
        sys, "argv", ["ltm_index", str(vault), "--search", "tutorial", "--tag", "python"]
    )
    result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "Search results" in captured.out


def test_cli_main_error_handling(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test CLI main handles errors gracefully."""
    vault = tmp_path / "nonexistent_vault"

    from cortexgraph.storage.ltm_index import main

    monkeypatch.setattr(sys, "argv", ["ltm_index", str(vault)])
    result = main()

    assert result == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_multiple_markdown_files_in_subdirectories(tmp_path: Path) -> None:
    """Test indexing multiple markdown files in subdirectories."""
    vault = tmp_path / "vault"

    write_md(vault / "root.md", "Root level note")
    write_md(vault / "folder1/note1.md", "Note in folder 1")
    write_md(vault / "folder1/subfolder/note2.md", "Note in subfolder")
    write_md(vault / "folder2/note3.md", "Note in folder 2")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=False)

    assert index.get_stats()["total_documents"] == 4
    assert index.get_document("root.md") is not None
    assert index.get_document("folder1/note1.md") is not None
    assert index.get_document("folder1/subfolder/note2.md") is not None
    assert index.get_document("folder2/note3.md") is not None


def test_index_persistence_across_instances(tmp_path: Path) -> None:
    """Test index persists correctly across different LTMIndex instances."""
    vault = tmp_path / "vault"

    write_md(vault / "note.md", "Content with [[link]] and #tag")

    # Build index in first instance
    index1 = LTMIndex(vault_path=vault)
    index1.build_index(verbose=False)
    stats1 = index1.get_stats()

    # Load in second instance
    index2 = LTMIndex(vault_path=vault)
    index2.load_index()

    # Verify data matches
    assert index2.get_stats()["total_documents"] == stats1["total_documents"]
    doc = index2.get_document("note.md")
    assert doc is not None
    assert "link" in doc.wikilinks
    assert "tag" in doc.tags


def test_verbose_output_for_large_batch(tmp_path: Path, capsys) -> None:
    """Test verbose output prints progress for large batches."""
    vault = tmp_path / "vault"

    # Create 101 files to trigger batch output (every 100 files)
    for i in range(101):
        write_md(vault / f"note{i:03d}.md", f"Content {i}")

    index = LTMIndex(vault_path=vault)
    index.build_index(verbose=True)

    captured = capsys.readouterr()
    assert "... indexed 100 files" in captured.out


def test_incremental_build_with_existing_index(tmp_path: Path, capsys) -> None:
    """Test incremental build loads and updates existing index."""
    vault = tmp_path / "vault"

    write_md(vault / "note1.md", "First note")

    # Initial build
    index1 = LTMIndex(vault_path=vault)
    index1.build_index(verbose=False)

    # Add new file
    time.sleep(0.01)  # Ensure different mtime
    write_md(vault / "note2.md", "Second note")

    # Incremental build should load existing and add new
    index2 = LTMIndex(vault_path=vault)
    index2.build_index(force=False, verbose=True)

    captured = capsys.readouterr()
    assert "Loaded existing index" in captured.out

    stats = index2.get_stats()
    assert stats["total_documents"] == 2
