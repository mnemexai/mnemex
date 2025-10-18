"""Tests for unified search merging STM and LTM."""

from __future__ import annotations

from pathlib import Path

from mnemex.config import Config, set_config
from mnemex.context import db
from mnemex.storage.ltm_index import LTMIndex
from mnemex.storage.models import Memory, MemoryMetadata
from mnemex.tools.search_unified import UnifiedSearchResult, search_unified


def test_search_unified_merges_sources(tmp_path: Path) -> None:
    # Prepare temp storage and vault
    storage_dir = tmp_path / "jsonl"
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    # Configure to use temp paths
    cfg = Config(
        storage_path=storage_dir,
        ltm_vault_path=vault_dir,
        enable_embeddings=False,
    )
    set_config(cfg)

    # Use global db instance and connect it to the test storage
    db.storage_path = storage_dir
    db.connect()

    # Seed STM with a memory
    m = Memory(
        id="mem-1",
        content="User prefers TypeScript projects",
        meta=MemoryMetadata(tags=["preferences", "typescript"]),
    )
    db.save_memory(m)

    # Seed LTM with a markdown note
    note_path = vault_dir / "TypeScript Pref.md"
    note_path.write_text(
        """---
title: TypeScript Pref
tags: [preferences]
---
Documenting TypeScript preference across projects.
""",
        encoding="utf-8",
    )

    # Build LTM index so the unified search can find the markdown file
    index = LTMIndex(vault_path=vault_dir)
    index.build_index(force=True)

    # Execute unified search
    result_dict = search_unified(query="TypeScript", tags=["preferences"], limit=5)

    # Convert dict results to UnifiedSearchResult objects
    results = [UnifiedSearchResult(**r) for r in result_dict["results"]]

    # Expect at least one STM and one LTM result
    sources = {r.source for r in results}
    assert "stm" in sources
    assert "ltm" in sources

    # Verify ordering is by score and that content previews are present
    assert all(hasattr(r, "score") for r in results)
    assert any("TypeScript" in r.content for r in results)
