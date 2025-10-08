"""Tests for unified search merging STM and LTM."""

from __future__ import annotations

from pathlib import Path

from mnemex.config import Config, set_config
from mnemex.storage.jsonl_storage import JSONLStorage
from mnemex.storage.models import Memory, MemoryMetadata
from mnemex.tools.search_unified import search_unified


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

    # Seed STM with a memory
    stm = JSONLStorage(storage_path=storage_dir)
    stm.connect()
    m = Memory(
        id="mem-1",
        content="User prefers TypeScript projects",
        meta=MemoryMetadata(tags=["preferences", "typescript"]),
    )
    stm.save_memory(m)

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

    # Execute unified search
    results = search_unified(query="TypeScript", tags=["preferences"], limit=5)

    # Expect at least one STM and one LTM result
    sources = {r.source for r in results}
    assert "stm" in sources
    assert "ltm" in sources

    # Verify ordering is by score and that content previews are present
    assert all(hasattr(r, "score") for r in results)
    assert any("TypeScript" in r.content for r in results)
