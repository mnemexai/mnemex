"""Unit tests for LTMPromoter (T059-T060).

These tests verify the isolated logic of LTMPromoter including:
- T059: Promotion criteria matching
- T060: Markdown generation
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.storage.models import MemoryStatus

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_memory():
    """Create a mock memory with typical attributes."""
    now = int(time.time())
    memory = MagicMock()
    memory.id = "test-mem-123"
    memory.content = "PostgreSQL database configuration for production deployment"
    memory.entities = ["PostgreSQL", "Database", "Production"]
    memory.tags = ["database", "config", "production"]
    memory.strength = 1.2
    memory.use_count = 8
    memory.created_at = now - 86400 * 5  # 5 days ago
    memory.last_used = now - 3600  # 1 hour ago
    memory.status = MemoryStatus.ACTIVE
    return memory


@pytest.fixture
def mock_storage():
    """Create mock storage with test data."""
    storage = MagicMock()
    storage.memories = {}
    return storage


# =============================================================================
# T059: Unit Tests - Promotion Criteria Matching
# =============================================================================


class TestPromotionCriteriaMatching:
    """Unit tests for promotion criteria matching (T059)."""

    def test_parse_criteria_score_threshold(self) -> None:
        """_parse_criteria extracts score_threshold from reason."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            # Test score-based reason
            reason = "High score (0.85 >= 0.65)"
            criteria = promoter._parse_criteria(reason)

            assert "score_threshold" in criteria

    def test_parse_criteria_use_count_threshold(self) -> None:
        """_parse_criteria extracts use_count_threshold from reason."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            # Test use count-based reason
            reason = "High use count (8 >= 5) within 14 days"
            criteria = promoter._parse_criteria(reason)

            assert "use_count_threshold" in criteria

    def test_parse_criteria_review_count_threshold(self) -> None:
        """_parse_criteria extracts review_count_threshold from reason."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            # Test review count-based reason
            reason = "Review count threshold (5 >= 3)"
            criteria = promoter._parse_criteria(reason)

            assert "review_count_threshold" in criteria

    def test_parse_criteria_default_to_score(self) -> None:
        """_parse_criteria defaults to score_threshold when unknown reason."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            # Test unknown reason format
            reason = "Some other reason"
            criteria = promoter._parse_criteria(reason)

            # Should default to score_threshold
            assert "score_threshold" in criteria
            assert len(criteria) >= 1

    def test_parse_criteria_always_returns_list(self) -> None:
        """_parse_criteria always returns a non-empty list."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            # Even empty reason should return list
            criteria = promoter._parse_criteria("")

            assert isinstance(criteria, list)
            assert len(criteria) >= 1

    def test_scan_uses_should_promote(self, mock_memory: MagicMock) -> None:
        """scan() uses should_promote() to check promotion criteria."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        mock_storage = MagicMock()
        mock_storage.memories = {"mem-1": mock_memory}

        with (
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=mock_storage),
            patch("cortexgraph.agents.ltm_promoter.should_promote") as mock_should_promote,
        ):
            mock_should_promote.return_value = (True, "High score", 0.85)

            promoter = LTMPromoter(dry_run=True)
            promoter._storage = mock_storage
            promoter.scan()

            # should_promote should be called with the memory
            mock_should_promote.assert_called_once()

    def test_scan_excludes_non_active_memories(self) -> None:
        """scan() excludes memories that are not ACTIVE status."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        now = int(time.time())
        mock_storage = MagicMock()

        # Create memory with PROMOTED status
        promoted_mem = MagicMock()
        promoted_mem.id = "promoted-mem"
        promoted_mem.status = MemoryStatus.PROMOTED
        promoted_mem.use_count = 10
        promoted_mem.last_used = now
        promoted_mem.created_at = now - 86400
        promoted_mem.strength = 1.5

        mock_storage.memories = {"promoted-mem": promoted_mem}

        with patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=mock_storage):
            promoter = LTMPromoter(dry_run=True)
            promoter._storage = mock_storage

            candidates = promoter.scan()

            # Promoted memory should be excluded
            assert "promoted-mem" not in candidates


# =============================================================================
# T060: Unit Tests - Markdown Generation
# =============================================================================


class TestMarkdownGeneration:
    """Unit tests for markdown generation (T060)."""

    def test_generate_title_with_entities(self, mock_memory: MagicMock) -> None:
        """_generate_title creates title from entities and content."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            title = promoter._generate_title(mock_memory)

            # Title should contain first entity
            assert "PostgreSQL" in title
            # Title should contain content snippet
            assert "database" in title.lower() or "config" in title.lower()

    def test_generate_title_without_entities(self) -> None:
        """_generate_title handles memory without entities."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        memory = MagicMock()
        memory.id = "test-123-abc"
        memory.content = "Some content"
        memory.entities = []

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            title = promoter._generate_title(memory)

            # Should fallback to memory ID
            assert "test-123" in title or "Memory" in title

    def test_generate_title_truncates_long_content(self) -> None:
        """_generate_title truncates long content in title."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        memory = MagicMock()
        memory.id = "test-123-abc"
        memory.content = "A" * 100  # Very long content
        memory.entities = ["Entity"]

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            title = promoter._generate_title(memory)

            # Title should be reasonably short
            assert len(title) < 100
            # Should contain truncation indicator
            assert "..." in title

    def test_generate_content_includes_main_content(self, mock_memory: MagicMock) -> None:
        """_generate_content includes the main memory content."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            content = promoter._generate_content(mock_memory)

            # Should include the memory content
            assert "PostgreSQL database configuration" in content

    def test_generate_content_includes_entities_section(self, mock_memory: MagicMock) -> None:
        """_generate_content includes entities section with wikilinks."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            content = promoter._generate_content(mock_memory)

            # Should include entities section
            assert "## Entities" in content
            # Should have wikilinks
            assert "[[PostgreSQL]]" in content
            assert "[[Database]]" in content

    def test_generate_content_handles_empty_entities(self) -> None:
        """_generate_content handles memory with no entities."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        memory = MagicMock()
        memory.id = "test-123"
        memory.content = "Some content without entities"
        memory.entities = []

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            content = promoter._generate_content(memory)

            # Should still include content section
            assert "## Content" in content
            assert "Some content without entities" in content
            # Should not crash even without entities
            assert content is not None

    def test_generate_content_formats_as_markdown(self, mock_memory: MagicMock) -> None:
        """_generate_content produces valid markdown structure."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            content = promoter._generate_content(mock_memory)

            # Should have markdown headers
            assert content.startswith("## Content") or "## Content" in content
            # Should have proper line breaks
            assert "\n" in content


# =============================================================================
# Additional Unit Tests
# =============================================================================


class TestLTMPromoterUnit:
    """Additional unit tests for LTMPromoter."""

    def test_init_accepts_vault_path(self) -> None:
        """LTMPromoter accepts custom vault_path."""
        from pathlib import Path

        from cortexgraph.agents.ltm_promoter import LTMPromoter

        custom_path = Path("/custom/vault")

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True, vault_path=custom_path)

            assert promoter._vault_path == custom_path

    def test_init_uses_default_rate_limit(self) -> None:
        """LTMPromoter uses default rate limit of 100."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter = LTMPromoter(dry_run=True)

            assert promoter.rate_limit == 100

    def test_dry_run_mode_set(self) -> None:
        """LTMPromoter respects dry_run setting."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        with patch("cortexgraph.agents.ltm_promoter.get_storage"):
            promoter_dry = LTMPromoter(dry_run=True)
            promoter_live = LTMPromoter(dry_run=False)

            assert promoter_dry.dry_run is True
            assert promoter_live.dry_run is False

    def test_promotion_candidates_cached(self, mock_memory: MagicMock) -> None:
        """scan() caches promotion candidates for process_item()."""
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        mock_storage = MagicMock()
        mock_storage.memories = {"mem-1": mock_memory}

        with (
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=mock_storage),
            patch(
                "cortexgraph.agents.ltm_promoter.should_promote",
                return_value=(True, "High score", 0.85),
            ),
        ):
            promoter = LTMPromoter(dry_run=True)
            promoter._storage = mock_storage

            promoter.scan()

            # Should cache promotion info
            assert "mem-1" in promoter._promotion_candidates
            assert promoter._promotion_candidates["mem-1"] == (True, "High score", 0.85)
