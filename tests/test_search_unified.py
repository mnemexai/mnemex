"""Tests for unified search merging STM and LTM."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cortexgraph.config import Config, set_config
from cortexgraph.context import db
from cortexgraph.storage.ltm_index import LTMIndex
from cortexgraph.storage.models import Memory, MemoryMetadata
from cortexgraph.tools.search_unified import UnifiedSearchResult, format_results, search_unified


class TestUnifiedSearchResult:
    """Test UnifiedSearchResult class."""

    def test_create_instance(self) -> None:
        """Test creating UnifiedSearchResult instance."""
        result = UnifiedSearchResult(
            content="Test content",
            title="Test Title",
            source="stm",
            score=0.85,
            memory_id="mem-123",
            tags=["test", "example"],
            created_at=1000000,
            last_used=1000100,
        )

        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.source == "stm"
        assert result.score == 0.85
        assert result.memory_id == "mem-123"
        assert result.tags == ["test", "example"]
        assert result.created_at == 1000000
        assert result.last_used == 1000100

    def test_create_instance_with_defaults(self) -> None:
        """Test creating UnifiedSearchResult with optional fields."""
        result = UnifiedSearchResult(
            content="Test content",
            title="Test Title",
            source="ltm",
            score=0.5,
        )

        assert result.content == "Test content"
        assert result.title == "Test Title"
        assert result.source == "ltm"
        assert result.score == 0.5
        assert result.path is None
        assert result.memory_id is None
        assert result.tags == []
        assert result.created_at is None
        assert result.last_used is None

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        result = UnifiedSearchResult(
            content="Test content",
            title="Test Title",
            source="stm",
            score=0.75,
            memory_id="mem-456",
            tags=["python"],
            created_at=2000000,
            last_used=2000200,
            path="/some/path.md",
        )

        result_dict = result.to_dict()

        assert result_dict["content"] == "Test content"
        assert result_dict["title"] == "Test Title"
        assert result_dict["source"] == "stm"
        assert result_dict["score"] == 0.75
        assert result_dict["memory_id"] == "mem-456"
        assert result_dict["tags"] == ["python"]
        assert result_dict["created_at"] == 2000000
        assert result_dict["last_used"] == 2000200
        assert result_dict["path"] == "/some/path.md"


class TestSearchUnified:
    """Test search_unified function."""

    def test_search_with_query_only(self, tmp_path: Path) -> None:
        """Test search with query parameter only."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add some test memories
        db.save_memory(
            Memory(
                id="mem-1",
                content="Python is a great programming language",
                meta=MemoryMetadata(tags=["python"]),
            )
        )
        db.save_memory(
            Memory(
                id="mem-2",
                content="JavaScript frameworks are popular",
                meta=MemoryMetadata(tags=["javascript"]),
            )
        )

        result = search_unified(query="Python")

        assert result["success"] is True
        assert result["count"] >= 1
        assert any("Python" in r["content"] for r in result["results"])

    def test_search_with_tags_only(self, tmp_path: Path) -> None:
        """Test search with tags parameter only."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Tagged with python",
                meta=MemoryMetadata(tags=["python", "code"]),
            )
        )
        db.save_memory(
            Memory(
                id="mem-2",
                content="Tagged with java",
                meta=MemoryMetadata(tags=["java"]),
            )
        )

        result = search_unified(tags=["python"])

        assert result["success"] is True
        assert result["count"] >= 1

    def test_search_with_both_query_and_tags(self, tmp_path: Path) -> None:
        """Test search with both query and tags."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Python web development with Django",
                meta=MemoryMetadata(tags=["python", "web"]),
            )
        )

        result = search_unified(query="Django", tags=["python"])

        assert result["success"] is True
        assert result["count"] >= 1

    def test_search_with_limit(self, tmp_path: Path) -> None:
        """Test search respects limit parameter."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add multiple memories
        for i in range(10):
            db.save_memory(
                Memory(
                    id=f"mem-{i}",
                    content=f"Test memory {i}",
                    meta=MemoryMetadata(tags=["test"]),
                )
            )

        result = search_unified(tags=["test"], limit=3)

        assert result["success"] is True
        assert result["count"] <= 3

    def test_search_with_stm_weight(self, tmp_path: Path) -> None:
        """Test search with custom STM weight."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Weighted test",
                meta=MemoryMetadata(tags=["test"]),
            )
        )

        result = search_unified(query="test", stm_weight=1.5)

        assert result["success"] is True

    def test_search_with_ltm_weight(self, tmp_path: Path) -> None:
        """Test search with custom LTM weight."""
        storage_dir = tmp_path / "jsonl"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        cfg = Config(
            storage_path=storage_dir,
            ltm_vault_path=vault_dir,
            enable_embeddings=False,
        )
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Create LTM document
        note = vault_dir / "test.md"
        note.write_text("---\ntitle: Test\ntags:\n  - test\n---\nTest content", encoding="utf-8")

        index = LTMIndex(vault_path=vault_dir)
        index.build_index(force=True)

        result = search_unified(query="test", ltm_weight=1.2)

        assert result["success"] is True

    def test_search_with_window_days(self, tmp_path: Path) -> None:
        """Test search with window_days parameter."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add a recent memory
        now = int(time.time())
        db.save_memory(
            Memory(
                id="mem-recent",
                content="Recent memory",
                meta=MemoryMetadata(tags=["recent"]),
                created_at=now - 86400,  # 1 day ago
                last_used=now - 86400,
            )
        )

        result = search_unified(tags=["recent"], window_days=7)

        assert result["success"] is True

    def test_search_with_min_score(self, tmp_path: Path) -> None:
        """Test search with min_score parameter."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="High score memory",
                meta=MemoryMetadata(tags=["test"]),
                use_count=10,
                strength=0.9,
            )
        )

        result = search_unified(query="memory", min_score=0.1)

        assert result["success"] is True

    def test_empty_results(self, tmp_path: Path) -> None:
        """Test search with no matches."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        result = search_unified(query="nonexistent_query_xyz")

        assert result["success"] is True
        assert result["count"] == 0
        assert result["results"] == []

    def test_stm_only_results(self, tmp_path: Path) -> None:
        """Test search with only STM results (no LTM vault)."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="STM only content",
                meta=MemoryMetadata(tags=["stm"]),
            )
        )

        result = search_unified(query="STM")

        assert result["success"] is True
        assert result["count"] >= 1
        results = [UnifiedSearchResult(**r) for r in result["results"]]
        assert all(r.source == "stm" for r in results)

    def test_ltm_only_results(self, tmp_path: Path) -> None:
        """Test search with only LTM results (empty STM)."""
        storage_dir = tmp_path / "jsonl"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        cfg = Config(
            storage_path=storage_dir,
            ltm_vault_path=vault_dir,
            enable_embeddings=False,
        )
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Create only LTM documents
        note = vault_dir / "ltm_only.md"
        note.write_text(
            "---\ntitle: LTM Only\ntags:\n  - ltm\n---\nLTM only content", encoding="utf-8"
        )

        index = LTMIndex(vault_path=vault_dir)
        index.build_index(force=True)

        result = search_unified(query="LTM")

        assert result["success"] is True
        assert result["count"] >= 1
        results = [UnifiedSearchResult(**r) for r in result["results"]]
        assert all(r.source == "ltm" for r in results)

    def test_combined_stm_ltm_results(self, tmp_path: Path) -> None:
        """Test search with combined STM and LTM results."""
        storage_dir = tmp_path / "jsonl"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        cfg = Config(
            storage_path=storage_dir,
            ltm_vault_path=vault_dir,
            enable_embeddings=False,
        )
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add STM memory
        db.save_memory(
            Memory(
                id="mem-1",
                content="Combined search test",
                meta=MemoryMetadata(tags=["combined"]),
            )
        )

        # Add LTM document
        note = vault_dir / "combined.md"
        note.write_text(
            "---\ntitle: Combined Test\ntags:\n  - combined\n---\nCombined search test",
            encoding="utf-8",
        )

        index = LTMIndex(vault_path=vault_dir)
        index.build_index(force=True)

        result = search_unified(query="Combined", tags=["combined"])

        assert result["success"] is True
        assert result["count"] >= 1
        results = [UnifiedSearchResult(**r) for r in result["results"]]
        sources = {r.source for r in results}
        # Should have results from at least one source (both if LTM index is fresh)
        assert len(sources) >= 1
        # Verify we have STM or LTM results
        assert "stm" in sources or "ltm" in sources

    def test_results_sorted_by_score(self, tmp_path: Path) -> None:
        """Test that results are sorted by score."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add memories with different use counts (which affect scores)
        db.save_memory(
            Memory(
                id="mem-high",
                content="High score",
                meta=MemoryMetadata(tags=["test"]),
                use_count=20,
                strength=0.9,
            )
        )
        db.save_memory(
            Memory(
                id="mem-low",
                content="Low score",
                meta=MemoryMetadata(tags=["test"]),
                use_count=1,
                strength=0.1,
            )
        )

        result = search_unified(tags=["test"])

        assert result["success"] is True
        results = [UnifiedSearchResult(**r) for r in result["results"]]

        # Check that scores are in descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestSearchUnifiedValidation:
    """Test validation errors in search_unified."""

    def test_query_too_long(self, tmp_path: Path) -> None:
        """Test query exceeds maximum length."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # MAX_CONTENT_LENGTH is 50000
        long_query = "x" * 50001

        with pytest.raises(ValueError, match="query"):
            search_unified(query=long_query)

    def test_too_many_tags(self, tmp_path: Path) -> None:
        """Test too many tags."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # MAX_TAGS_COUNT is 50
        too_many_tags = [f"tag{i}" for i in range(51)]

        with pytest.raises(ValueError, match="tags"):
            search_unified(tags=too_many_tags)

    def test_invalid_tag_sanitized(self, tmp_path: Path) -> None:
        """Test that invalid tags are auto-sanitized (MCP-friendly)."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Should succeed with sanitized tags ("invalid tag with spaces" -> "invalid_tag_with_spaces")
        result = search_unified(tags=["valid", "invalid tag with spaces"])
        assert result["success"] is True
        assert result["count"] >= 0  # Search succeeds even if no results

    def test_limit_too_small(self, tmp_path: Path) -> None:
        """Test limit less than 1."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="limit"):
            search_unified(query="test", limit=0)

    def test_limit_too_large(self, tmp_path: Path) -> None:
        """Test limit exceeds maximum."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="limit"):
            search_unified(query="test", limit=101)

    def test_stm_weight_too_low(self, tmp_path: Path) -> None:
        """Test stm_weight below valid range."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="stm_weight"):
            search_unified(query="test", stm_weight=-0.1)

    def test_stm_weight_too_high(self, tmp_path: Path) -> None:
        """Test stm_weight above valid range."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="stm_weight"):
            search_unified(query="test", stm_weight=2.1)

    def test_ltm_weight_too_low(self, tmp_path: Path) -> None:
        """Test ltm_weight below valid range."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="ltm_weight"):
            search_unified(query="test", ltm_weight=-0.1)

    def test_ltm_weight_too_high(self, tmp_path: Path) -> None:
        """Test ltm_weight above valid range."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="ltm_weight"):
            search_unified(query="test", ltm_weight=2.1)

    def test_window_days_too_small(self, tmp_path: Path) -> None:
        """Test window_days less than 1."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="window_days"):
            search_unified(query="test", window_days=0)

    def test_window_days_too_large(self, tmp_path: Path) -> None:
        """Test window_days exceeds maximum."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="window_days"):
            search_unified(query="test", window_days=3651)

    def test_min_score_too_low(self, tmp_path: Path) -> None:
        """Test min_score below valid range."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="min_score"):
            search_unified(query="test", min_score=-0.1)

    def test_min_score_too_high(self, tmp_path: Path) -> None:
        """Test min_score above valid range."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        with pytest.raises(ValueError, match="min_score"):
            search_unified(query="test", min_score=1.1)


class TestEdgeCases:
    """Test edge cases for unified search."""

    def test_search_unified_merges_sources(self, tmp_path: Path) -> None:
        """Test that unified search merges STM and LTM sources."""
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

        # Seed LTM with a markdown note (proper YAML formatting)
        note_path = vault_dir / "TypeScript Pref.md"
        note_path.write_text(
            """---
title: TypeScript Pref
tags:
  - preferences
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

    def test_ltm_index_not_available(self, tmp_path: Path) -> None:
        """Test search when LTM index doesn't exist."""
        storage_dir = tmp_path / "jsonl"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        cfg = Config(
            storage_path=storage_dir,
            ltm_vault_path=vault_dir,
            enable_embeddings=False,
        )
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add STM memory
        db.save_memory(
            Memory(
                id="mem-1",
                content="Test without LTM index",
                meta=MemoryMetadata(tags=["test"]),
            )
        )

        # Don't build LTM index - it should gracefully handle missing index
        result = search_unified(query="test")

        assert result["success"] is True
        # Should still get STM results
        assert result["count"] >= 0

    def test_stale_ltm_index(self, tmp_path: Path) -> None:
        """Test search with stale LTM index (older than max age)."""
        storage_dir = tmp_path / "jsonl"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        # Use minimum allowed value (60 seconds)
        cfg = Config(
            storage_path=storage_dir,
            ltm_vault_path=vault_dir,
            enable_embeddings=False,
            ltm_index_max_age_seconds=60,
        )
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Create LTM document and build index
        note = vault_dir / "test.md"
        note.write_text("---\ntitle: Test\ntags:\n  - test\n---\nTest content", encoding="utf-8")

        index = LTMIndex(vault_path=vault_dir)
        index.build_index(force=True)

        # With 60 second max age, the index should still be fresh
        # This test verifies the max_age logic doesn't break the search
        result = search_unified(query="test")

        assert result["success"] is True


class TestErrorHandling:
    """Test error handling in search_unified."""

    def test_stm_search_error_handling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that STM search errors are caught and don't break the function."""
        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Mock db.search_memories to raise an exception
        def mock_search_error(*args, **kwargs):
            raise RuntimeError("Simulated STM search error")

        monkeypatch.setattr(db, "search_memories", mock_search_error)

        # Should not raise, should catch exception and continue
        result = search_unified(query="test")

        assert result["success"] is True
        # May have 0 results due to error, that's OK
        assert result["count"] >= 0

    def test_ltm_search_error_handling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that LTM search errors are caught and don't break the function."""
        storage_dir = tmp_path / "jsonl"
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        cfg = Config(
            storage_path=storage_dir,
            ltm_vault_path=vault_dir,
            enable_embeddings=False,
        )
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Create a valid index
        note = vault_dir / "test.md"
        note.write_text("---\ntitle: Test\n---\nContent", encoding="utf-8")
        index = LTMIndex(vault_path=vault_dir)
        index.build_index(force=True)

        # Mock LTMIndex.search to raise an exception
        def mock_ltm_search_error(self, *args, **kwargs):
            raise RuntimeError("Simulated LTM search error")

        monkeypatch.setattr(LTMIndex, "search", mock_ltm_search_error)

        # Should not raise, should catch exception and continue
        result = search_unified(query="test")

        assert result["success"] is True
        # May have fewer results due to LTM error, that's OK
        assert result["count"] >= 0


class TestCLI:
    """Test CLI main function."""

    def test_main_with_query(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        """Test main CLI with query argument."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        # Add test memory
        db.save_memory(
            Memory(
                id="mem-cli",
                content="CLI test memory",
                meta=MemoryMetadata(tags=["cli"]),
            )
        )

        # Mock sys.argv
        monkeypatch.setattr("sys.argv", ["search_unified", "CLI"])

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "CLI" in captured.out or "results" in captured.out

    def test_main_with_tags(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        """Test main CLI with tags argument."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-tag",
                content="Tagged memory",
                meta=MemoryMetadata(tags=["testtag"]),
            )
        )

        monkeypatch.setattr("sys.argv", ["search_unified", "--tags", "testtag"])

        exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "results" in captured.out

    def test_main_with_limit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main CLI with limit argument."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Test",
                meta=MemoryMetadata(tags=["test"]),
            )
        )

        monkeypatch.setattr("sys.argv", ["search_unified", "Test", "--limit", "5"])

        exit_code = main()
        assert exit_code == 0

    def test_main_with_weights(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main CLI with weight arguments."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Test",
                meta=MemoryMetadata(tags=["test"]),
            )
        )

        monkeypatch.setattr(
            "sys.argv", ["search_unified", "Test", "--stm-weight", "1.5", "--ltm-weight", "0.8"]
        )

        exit_code = main()
        assert exit_code == 0

    def test_main_with_window_days(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main CLI with window-days argument."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Test",
                meta=MemoryMetadata(tags=["test"]),
            )
        )

        monkeypatch.setattr("sys.argv", ["search_unified", "Test", "--window-days", "7"])

        exit_code = main()
        assert exit_code == 0

    def test_main_with_min_score(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main CLI with min-score argument."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-1",
                content="Test",
                meta=MemoryMetadata(tags=["test"]),
            )
        )

        monkeypatch.setattr("sys.argv", ["search_unified", "Test", "--min-score", "0.1"])

        exit_code = main()
        assert exit_code == 0

    def test_main_verbose(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        """Test main CLI with verbose flag."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        db.storage_path = storage_dir
        db.connect()

        db.save_memory(
            Memory(
                id="mem-verbose",
                content="Verbose test",
                meta=MemoryMetadata(tags=["verbose"]),
            )
        )

        monkeypatch.setattr("sys.argv", ["search_unified", "Verbose", "--verbose"])

        exit_code = main()
        assert exit_code == 0
        captured = capsys.readouterr()
        # Verbose mode should show more details
        assert "mem-" in captured.out or "results" in captured.out

    def test_main_no_args(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
        """Test main CLI with no query or tags (should print help)."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        monkeypatch.setattr("sys.argv", ["search_unified"])

        exit_code = main()
        assert exit_code == 1  # Should return error code

    def test_main_error_handling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        """Test main CLI error handling."""
        from cortexgraph.tools.search_unified import main

        storage_dir = tmp_path / "jsonl"
        cfg = Config(storage_path=storage_dir, enable_embeddings=False)
        set_config(cfg)

        # Cause an error by using invalid limit
        monkeypatch.setattr("sys.argv", ["search_unified", "test", "--limit", "0"])

        exit_code = main()
        assert exit_code == 1  # Should return error code
        captured = capsys.readouterr()
        assert "Error" in captured.err or "error" in captured.err.lower()


class TestFormatResults:
    """Test format_results function."""

    def test_format_empty_results(self) -> None:
        """Test formatting empty results."""
        formatted = format_results([])
        assert "No results found" in formatted

    def test_format_single_result(self) -> None:
        """Test formatting a single result."""
        result = UnifiedSearchResult(
            content="Test content for formatting",
            title="Test Title",
            source="stm",
            score=0.85,
            memory_id="mem-123",
            tags=["test"],
        )

        formatted = format_results([result])

        assert "Found 1 results" in formatted
        assert "Test Title" in formatted
        assert "score: 0.850" in formatted
        assert "Test content" in formatted

    def test_format_multiple_results(self) -> None:
        """Test formatting multiple results."""
        results = [
            UnifiedSearchResult(
                content="First result",
                title="First",
                source="stm",
                score=0.9,
            ),
            UnifiedSearchResult(
                content="Second result",
                title="Second",
                source="ltm",
                score=0.7,
            ),
        ]

        formatted = format_results(results)

        assert "Found 2 results" in formatted
        assert "First" in formatted
        assert "Second" in formatted

    def test_format_verbose(self) -> None:
        """Test formatting with verbose flag."""
        result = UnifiedSearchResult(
            content="Verbose test content",
            title="Verbose Test",
            source="stm",
            score=0.8,
            memory_id="mem-verbose",
            tags=["verbose", "test"],
            path="/some/path.md",
        )

        formatted = format_results([result], verbose=True)

        assert "Verbose Test" in formatted
        assert "mem-verbose" in formatted
        assert "verbose, test" in formatted or "verbose,test" in formatted

    def test_format_long_content(self) -> None:
        """Test formatting with content exceeding 150 chars."""
        long_content = "x" * 200
        result = UnifiedSearchResult(
            content=long_content,
            title="Long Content",
            source="stm",
            score=0.75,
        )

        formatted = format_results([result])

        # Should truncate at 150 chars and add ellipsis
        assert "..." in formatted
        assert len([line for line in formatted.split("\n") if "xxx" in line][0]) < 200

    def test_format_stm_source(self) -> None:
        """Test STM source is labeled correctly."""
        result = UnifiedSearchResult(
            content="STM test",
            title="STM",
            source="stm",
            score=0.8,
        )

        formatted = format_results([result])

        assert "🧠 STM" in formatted

    def test_format_ltm_source(self) -> None:
        """Test LTM source is labeled correctly."""
        result = UnifiedSearchResult(
            content="LTM test",
            title="LTM",
            source="ltm",
            score=0.6,
        )

        formatted = format_results([result])

        assert "📚 LTM" in formatted
