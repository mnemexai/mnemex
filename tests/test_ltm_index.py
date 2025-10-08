"""Tests for LTM index parsing and search."""

from __future__ import annotations

from pathlib import Path

from mnemex.storage.ltm_index import LTMIndex


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
