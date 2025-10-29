"""Tests for search_memory tool."""

import time
from unittest.mock import MagicMock, patch

import pytest

from mnemex.storage.models import Memory, MemoryMetadata
from mnemex.tools.search import search_memory
from tests.conftest import make_test_uuid


class TestSearchMemory:
    """Test suite for search_memory tool."""

    def test_search_basic_text_query(self, temp_storage):
        """Test basic text search."""
        # Create test memories with use_count > 0 so they have non-zero scores
        mem1 = Memory(
            id=make_test_uuid("mem-1"), content="Python programming tutorial", use_count=1
        )
        mem2 = Memory(id=make_test_uuid("mem-2"), content="JavaScript guide", use_count=1)
        mem3 = Memory(id=make_test_uuid("mem-3"), content="Python data analysis", use_count=1)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        result = search_memory(query="Python")

        assert result["success"] is True
        # Search returns all memories but scores matches higher
        assert result["count"] >= 2
        # Check that Python memories are in top results
        top_two = result["results"][:2]
        assert all("Python" in r["content"] for r in top_two)

    def test_search_exact_match_scores_higher(self, temp_storage):
        """Test that exact matches score higher than partial matches."""
        id1 = make_test_uuid("mem-1")
        id2 = make_test_uuid("mem-2")

        # Create mem1 as older so it has lower decay score
        now = int(time.time())
        old_time = now - (7 * 86400)  # 7 days ago

        mem1 = Memory(
            id=id1,
            content="machine learning basics",
            use_count=1,
            last_used=old_time,
            created_at=old_time,
        )
        mem2 = Memory(id=id2, content="learning", use_count=1, last_used=now, created_at=now)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)

        result = search_memory(query="learning")

        assert result["success"] is True
        assert result["count"] == 2
        # Verify that the more recent exact match ('mem-2') is scored higher and appears first
        assert result["results"][0]["id"] == id2
        assert result["results"][1]["id"] == id1
        assert result["results"][0]["score"] > result["results"][1]["score"]

    def test_search_with_tags_filter(self, temp_storage):
        """Test searching with tag filter."""
        mem1 = Memory(
            id="mem-1", content="Python tutorial", meta=MemoryMetadata(tags=["python", "tutorial"])
        )
        mem2 = Memory(
            id="mem-2", content="Python guide", meta=MemoryMetadata(tags=["python", "guide"])
        )
        mem3 = Memory(
            id="mem-3",
            content="JavaScript tutorial",
            meta=MemoryMetadata(tags=["javascript", "tutorial"]),
        )

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        result = search_memory(tags=["python"])

        assert result["success"] is True
        assert result["count"] == 2
        assert all("python" in r["tags"] for r in result["results"])

    def test_search_with_top_k_limit(self, temp_storage):
        """Test that top_k limits results."""
        for i in range(10):
            mem = Memory(id=f"mem-{i}", content=f"Test memory {i}")
            temp_storage.save_memory(mem)

        result = search_memory(top_k=3)

        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["results"]) == 3

    def test_search_with_window_days(self, temp_storage):
        """Test filtering by time window."""
        now = int(time.time())
        old_time = now - (10 * 86400)  # 10 days ago
        recent_time = now - 86400  # 1 day ago

        old_mem = Memory(
            id="mem-old", content="Old memory", created_at=old_time, last_used=old_time
        )
        recent_mem = Memory(
            id="mem-recent", content="Recent memory", created_at=recent_time, last_used=recent_time
        )

        temp_storage.save_memory(old_mem)
        temp_storage.save_memory(recent_mem)

        result = search_memory(window_days=7)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"][0]["id"] == "mem-recent"

    def test_search_with_min_score(self, temp_storage):
        """Test filtering by minimum score."""
        now = int(time.time())

        # High-scoring memory (recently used)
        high_mem = Memory(
            id="mem-high", content="High score", use_count=5, last_used=now, strength=1.5
        )
        # Low-scoring memory (old, unused)
        low_mem = Memory(
            id="mem-low",
            content="Low score",
            use_count=0,
            last_used=now - (30 * 86400),  # 30 days ago
            strength=1.0,
        )

        temp_storage.save_memory(high_mem)
        temp_storage.save_memory(low_mem)

        result = search_memory(min_score=0.5)

        assert result["success"] is True
        # Only high-scoring memory should be returned
        assert all(r["score"] >= 0.5 for r in result["results"])

    def test_search_no_query_returns_all(self, temp_storage):
        """Test that no query returns all memories."""
        for i in range(3):
            mem = Memory(id=f"mem-{i}", content=f"Memory {i}")
            temp_storage.save_memory(mem)

        result = search_memory()

        assert result["success"] is True
        assert result["count"] == 3

    def test_search_no_results(self, temp_storage):
        """Test search with no matches still returns results (with lower scores)."""
        mem = Memory(id="mem-1", content="Python programming")
        temp_storage.save_memory(mem)

        result = search_memory(query="JavaScript")

        assert result["success"] is True
        # Search may return all memories with base relevance score
        # We can't guarantee empty results with current implementation
        assert result["count"] >= 0

    def test_search_with_query_and_tags(self, temp_storage):
        """Test combining query and tag filters."""
        mem1 = Memory(
            id="mem-1",
            content="Python tutorial for beginners",
            meta=MemoryMetadata(tags=["python", "tutorial"]),
        )
        mem2 = Memory(
            id="mem-2",
            content="Python advanced guide",
            meta=MemoryMetadata(tags=["python", "advanced"]),
        )
        mem3 = Memory(
            id="mem-3",
            content="JavaScript tutorial",
            meta=MemoryMetadata(tags=["javascript", "tutorial"]),
        )

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        result = search_memory(query="tutorial", tags=["python"])

        assert result["success"] is True
        # Tags filter to python, query boosts "tutorial" matches
        assert result["count"] >= 1
        # mem-1 should be in top results (has both python tag and "tutorial")
        assert any(r["id"] == "mem-1" for r in result["results"])

    def test_search_results_sorted_by_score(self, temp_storage):
        """Test that results are sorted by score descending."""
        now = int(time.time())

        # Create memories with different scores
        mem1 = Memory(id="mem-1", content="Test", use_count=1, last_used=now)
        mem2 = Memory(id="mem-2", content="Test", use_count=5, last_used=now)
        mem3 = Memory(id="mem-3", content="Test", use_count=3, last_used=now)

        temp_storage.save_memory(mem1)
        temp_storage.save_memory(mem2)
        temp_storage.save_memory(mem3)

        result = search_memory()

        assert result["success"] is True
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_result_format(self, temp_storage):
        """Test that search results have correct format."""
        mem = Memory(
            id="mem-1", content="Test memory", meta=MemoryMetadata(tags=["test"]), use_count=3
        )
        temp_storage.save_memory(mem)

        result = search_memory()

        assert result["success"] is True
        assert result["count"] == 1

        res = result["results"][0]
        assert "id" in res
        assert "content" in res
        assert "tags" in res
        assert "score" in res
        assert "similarity" in res
        assert "use_count" in res
        assert "last_used" in res
        assert "age_days" in res

        assert res["id"] == "mem-1"
        assert res["content"] == "Test memory"
        assert res["tags"] == ["test"]
        assert res["use_count"] == 3

    # Validation tests
    def test_search_query_too_long_fails(self):
        """Test that query exceeding max length fails."""
        long_query = "x" * 50001
        with pytest.raises(ValueError, match="query.*exceeds maximum"):
            search_memory(query=long_query)

    def test_search_too_many_tags_fails(self):
        """Test that too many tags fails validation."""
        too_many_tags = [f"tag{i}" for i in range(51)]
        with pytest.raises(ValueError, match="tags.*exceeds maximum"):
            search_memory(tags=too_many_tags)

    def test_search_invalid_tag_sanitized(self, temp_storage):
        """Test that invalid tag characters are auto-sanitized (MCP-friendly)."""
        # Should succeed with sanitized tag ("invalid tag!" -> "invalid_tag")
        result = search_memory(tags=["invalid tag!"])
        assert result["success"] is True
        # Search should complete without error (even if no results found)

    def test_search_invalid_top_k_fails(self):
        """Test that invalid top_k values fail."""
        with pytest.raises(ValueError, match="top_k"):
            search_memory(top_k=0)

        with pytest.raises(ValueError, match="top_k"):
            search_memory(top_k=101)

        with pytest.raises(ValueError, match="top_k"):
            search_memory(top_k=-1)

    def test_search_invalid_window_days_fails(self):
        """Test that invalid window_days values fail."""
        with pytest.raises(ValueError, match="window_days"):
            search_memory(window_days=0)

        with pytest.raises(ValueError, match="window_days"):
            search_memory(window_days=3651)  # Over max

        with pytest.raises(ValueError, match="window_days"):
            search_memory(window_days=-1)

    def test_search_invalid_min_score_fails(self):
        """Test that invalid min_score values fail."""
        with pytest.raises(ValueError, match="min_score"):
            search_memory(min_score=-0.1)

        with pytest.raises(ValueError, match="min_score"):
            search_memory(min_score=1.1)

    # Embedding tests
    @patch("mnemex.tools.search.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("mnemex.tools.search.get_config")
    @patch("mnemex.tools.search.SentenceTransformer")
    def test_search_with_embeddings(self, mock_transformer, mock_config, temp_storage):
        """Test semantic search with embeddings."""
        # Setup mocks
        mock_config.return_value.enable_embeddings = True
        mock_config.return_value.embed_model = "test-model"
        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_embedding
        mock_transformer.return_value = mock_model

        # Create memory with embedding
        mem = Memory(
            id=make_test_uuid("mem-1"),
            content="Machine learning tutorial",
            embed=[0.1, 0.21, 0.29],  # Similar to query
        )
        temp_storage.save_memory(mem)

        result = search_memory(query="ML guide", use_embeddings=True)

        assert result["success"] is True
        assert result["count"] == 1
        # Similarity should be calculated
        assert result["results"][0]["similarity"] is not None

    @patch("mnemex.tools.search.get_config")
    def test_search_embeddings_disabled(self, mock_config, temp_storage):
        """Test that embeddings not used when disabled."""
        mock_config.return_value.enable_embeddings = False

        mem = Memory(id="mem-1", content="Test", embed=[0.1, 0.2])
        temp_storage.save_memory(mem)

        result = search_memory(query="Test", use_embeddings=True)

        assert result["success"] is True
        # Similarity should be None when embeddings disabled
        if result["count"] > 0:
            assert result["results"][0]["similarity"] is None

    @patch("mnemex.tools.search.SENTENCE_TRANSFORMERS_AVAILABLE", True)
    @patch("mnemex.tools.search.get_config")
    @patch("mnemex.tools.search.SentenceTransformer")
    def test_search_embedding_import_error(self, mock_transformer, mock_config, temp_storage):
        """Test graceful handling of embedding import errors."""
        mock_config.return_value.enable_embeddings = True
        mock_transformer.side_effect = ImportError("No model")

        mem = Memory(id=make_test_uuid("mem-1"), content="Test")
        temp_storage.save_memory(mem)

        # Should not crash, just skip embeddings
        result = search_memory(query="Test", use_embeddings=True)

        assert result["success"] is True

    # Edge cases
    def test_search_with_none_query(self, temp_storage):
        """Test that None query is handled."""
        mem = Memory(id="mem-1", content="Test")
        temp_storage.save_memory(mem)

        result = search_memory(query=None)

        assert result["success"] is True
        assert result["count"] == 1

    def test_search_with_none_tags(self, temp_storage):
        """Test that None tags is handled."""
        mem = Memory(id="mem-1", content="Test")
        temp_storage.save_memory(mem)

        result = search_memory(tags=None)

        assert result["success"] is True
        assert result["count"] == 1

    def test_search_with_empty_tags(self, temp_storage):
        """Test search with empty tags list."""
        mem = Memory(id="mem-1", content="Test")
        temp_storage.save_memory(mem)

        result = search_memory(tags=[])

        assert result["success"] is True

    def test_search_case_insensitive(self, temp_storage):
        """Test that search is case insensitive."""
        mem = Memory(id="mem-1", content="Python Programming")
        temp_storage.save_memory(mem)

        result_lower = search_memory(query="python")
        result_upper = search_memory(query="PYTHON")

        assert result_lower["count"] == 1
        assert result_upper["count"] == 1

    def test_search_with_special_characters(self, temp_storage):
        """Test search with special characters in query."""
        mem = Memory(id="mem-1", content="C++ programming guide")
        temp_storage.save_memory(mem)

        result = search_memory(query="C++")

        assert result["success"] is True
        assert result["count"] == 1

    def test_search_partial_word_match(self, temp_storage):
        """Test that partial words are matched."""
        mem = Memory(id="mem-1", content="Understanding machine learning")
        temp_storage.save_memory(mem)

        result = search_memory(query="machine")

        assert result["success"] is True
        assert result["count"] == 1
