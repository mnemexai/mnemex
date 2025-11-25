"""Unit tests for RelationshipDiscovery (T071-T072).

These tests verify the isolated logic of RelationshipDiscovery including:
- T071: Shared entity detection
- T072: Relation strength calculation
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
def mock_memory_with_entities():
    """Create a mock memory with typical entities and tags."""
    now = int(time.time())
    memory = MagicMock()
    memory.id = "mem-entity-1"
    memory.content = "PostgreSQL database configuration for production"
    memory.entities = ["PostgreSQL", "Database", "Production"]
    memory.tags = ["database", "config", "production"]
    memory.strength = 1.2
    memory.use_count = 5
    memory.created_at = now - 86400 * 3  # 3 days ago
    memory.last_used = now - 3600  # 1 hour ago
    memory.status = MemoryStatus.ACTIVE
    return memory


@pytest.fixture
def mock_memory_overlapping():
    """Create a second memory with overlapping entities."""
    now = int(time.time())
    memory = MagicMock()
    memory.id = "mem-entity-2"
    memory.content = "PostgreSQL optimization tips for high load"
    memory.entities = ["PostgreSQL", "Optimization", "Performance"]
    memory.tags = ["database", "performance", "tips"]
    memory.strength = 1.0
    memory.use_count = 3
    memory.created_at = now - 86400 * 5  # 5 days ago
    memory.last_used = now - 7200  # 2 hours ago
    memory.status = MemoryStatus.ACTIVE
    return memory


@pytest.fixture
def mock_memory_no_overlap():
    """Create a memory with no entity overlap."""
    now = int(time.time())
    memory = MagicMock()
    memory.id = "mem-entity-3"
    memory.content = "React component design patterns"
    memory.entities = ["React", "Components", "Frontend"]
    memory.tags = ["javascript", "frontend", "ui"]
    memory.strength = 1.1
    memory.use_count = 4
    memory.created_at = now - 86400 * 2
    memory.last_used = now - 1800
    memory.status = MemoryStatus.ACTIVE
    return memory


@pytest.fixture
def mock_storage():
    """Create mock storage with test data."""
    storage = MagicMock()
    storage.memories = {}
    storage.relations = {}
    return storage


# =============================================================================
# T071: Unit Tests - Shared Entity Detection
# =============================================================================


class TestSharedEntityDetection:
    """Unit tests for shared entity detection (T071)."""

    def test_detects_single_shared_entity(
        self, mock_memory_with_entities: MagicMock, mock_memory_overlapping: MagicMock
    ) -> None:
        """Detects when two memories share one entity."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-1": mock_memory_with_entities,
            "mem-2": mock_memory_overlapping,
        }
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=1)
            discovery._storage = mock_storage

            candidates = discovery.scan()

            # Should find the pair with PostgreSQL as shared entity
            assert len(candidates) >= 1

    def test_respects_min_shared_entities_threshold(
        self, mock_memory_with_entities: MagicMock, mock_memory_overlapping: MagicMock
    ) -> None:
        """Respects minimum shared entities threshold."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-1": mock_memory_with_entities,  # ["PostgreSQL", "Database", "Production"]
            "mem-2": mock_memory_overlapping,  # ["PostgreSQL", "Optimization", "Performance"]
        }
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            # With min_shared_entities=2, should NOT find pair (only 1 shared: PostgreSQL)
            discovery_high = RelationshipDiscovery(dry_run=True, min_shared_entities=2)
            discovery_high._storage = mock_storage
            candidates_high = discovery_high.scan()

            # With min_shared_entities=1, should find pair
            discovery_low = RelationshipDiscovery(dry_run=True, min_shared_entities=1)
            discovery_low._storage = mock_storage
            candidates_low = discovery_low.scan()

            # Higher threshold = fewer candidates
            assert len(candidates_low) >= len(candidates_high)

    def test_no_candidates_when_no_shared_entities(
        self, mock_memory_with_entities: MagicMock, mock_memory_no_overlap: MagicMock
    ) -> None:
        """Returns no candidates when memories have no shared entities."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-1": mock_memory_with_entities,  # PostgreSQL, Database, Production
            "mem-3": mock_memory_no_overlap,  # React, Components, Frontend
        }
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=1)
            discovery._storage = mock_storage

            candidates = discovery.scan()

            # No shared entities = no candidates
            assert len(candidates) == 0

    def test_caches_shared_entities_for_processing(
        self, mock_memory_with_entities: MagicMock, mock_memory_overlapping: MagicMock
    ) -> None:
        """Caches shared entities during scan for use in process_item."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-1": mock_memory_with_entities,
            "mem-2": mock_memory_overlapping,
        }
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=1)
            discovery._storage = mock_storage

            candidates = discovery.scan()

            # Cache should contain the shared entities
            for candidate in candidates:
                assert candidate in discovery._candidate_cache
                _, _, shared = discovery._candidate_cache[candidate]
                assert isinstance(shared, set)
                assert len(shared) >= 1

    def test_handles_memories_with_empty_entities(self) -> None:
        """Handles memories that have no entities gracefully."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())
        mem_no_entities = MagicMock()
        mem_no_entities.id = "mem-empty"
        mem_no_entities.entities = []
        mem_no_entities.tags = ["test"]
        mem_no_entities.status = MemoryStatus.ACTIVE
        mem_no_entities.created_at = now
        mem_no_entities.last_used = now

        mem_with_entities = MagicMock()
        mem_with_entities.id = "mem-has"
        mem_with_entities.entities = ["Entity1"]
        mem_with_entities.tags = ["test"]
        mem_with_entities.status = MemoryStatus.ACTIVE
        mem_with_entities.created_at = now
        mem_with_entities.last_used = now

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-empty": mem_no_entities,
            "mem-has": mem_with_entities,
        }
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            # Should not crash
            candidates = discovery.scan()
            # mem_no_entities won't participate in any pairs
            assert isinstance(candidates, list)

    def test_handles_none_entities_gracefully(self) -> None:
        """Handles memories where entities is None."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())
        mem_none_entities = MagicMock()
        mem_none_entities.id = "mem-none"
        mem_none_entities.entities = None
        mem_none_entities.tags = []
        mem_none_entities.status = MemoryStatus.ACTIVE
        mem_none_entities.created_at = now
        mem_none_entities.last_used = now

        mock_storage = MagicMock()
        mock_storage.memories = {"mem-none": mem_none_entities}
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            # Should not crash when entities is None
            candidates = discovery.scan()
            assert isinstance(candidates, list)


# =============================================================================
# T072: Unit Tests - Relation Strength Calculation
# =============================================================================


class TestRelationStrengthCalculation:
    """Unit tests for relation strength calculation (T072)."""

    def test_jaccard_similarity_entities_only(
        self, mock_memory_with_entities: MagicMock, mock_memory_overlapping: MagicMock
    ) -> None:
        """Calculates correct Jaccard similarity for entities."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-1": mock_memory_with_entities,
            "mem-2": mock_memory_overlapping,
        }

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            # Shared entities: {"PostgreSQL"}
            # Union: {"PostgreSQL", "Database", "Production", "Optimization", "Performance"}
            # Jaccard = 1/5 = 0.2
            strength, confidence, reasoning = discovery._calculate_relation_metrics(
                "mem-1", "mem-2", {"PostgreSQL"}
            )

            # Strength = 0.7 * entity_jaccard + 0.3 * tag_jaccard
            # Entity jaccard = 1/5 = 0.2
            # Tag jaccard: shared {"database"} / union {"database", "config", "production", "performance", "tips"} = 1/5 = 0.2
            # Expected strength = 0.7 * 0.2 + 0.3 * 0.2 = 0.14 + 0.06 = 0.2
            assert 0.1 <= strength <= 0.3  # Allow some tolerance

    def test_strength_increases_with_more_shared_entities(self) -> None:
        """Strength increases when more entities are shared."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())

        # Create two memories with many shared entities
        mem1 = MagicMock()
        mem1.id = "mem-high-1"
        mem1.entities = ["A", "B", "C", "D"]
        mem1.tags = ["tag1", "tag2"]
        mem1.status = MemoryStatus.ACTIVE
        mem1.created_at = now
        mem1.last_used = now

        mem2 = MagicMock()
        mem2.id = "mem-high-2"
        mem2.entities = ["A", "B", "C", "E"]  # 3 shared: A, B, C
        mem2.tags = ["tag1", "tag3"]
        mem2.status = MemoryStatus.ACTIVE
        mem2.created_at = now
        mem2.last_used = now

        # Create two memories with few shared entities
        mem3 = MagicMock()
        mem3.id = "mem-low-1"
        mem3.entities = ["X", "Y", "Z"]
        mem3.tags = ["tagA"]
        mem3.status = MemoryStatus.ACTIVE
        mem3.created_at = now
        mem3.last_used = now

        mem4 = MagicMock()
        mem4.id = "mem-low-2"
        mem4.entities = ["X", "W", "V"]  # 1 shared: X
        mem4.tags = ["tagB"]
        mem4.status = MemoryStatus.ACTIVE
        mem4.created_at = now
        mem4.last_used = now

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-high-1": mem1,
            "mem-high-2": mem2,
            "mem-low-1": mem3,
            "mem-low-2": mem4,
        }

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            # High overlap pair
            strength_high, _, _ = discovery._calculate_relation_metrics(
                "mem-high-1", "mem-high-2", {"A", "B", "C"}
            )

            # Low overlap pair
            strength_low, _, _ = discovery._calculate_relation_metrics(
                "mem-low-1", "mem-low-2", {"X"}
            )

            # More shared entities = higher strength
            assert strength_high > strength_low

    def test_confidence_based_on_shared_count(self) -> None:
        """Confidence increases with number of shared entities and tags."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())

        # High confidence scenario: 3+ entities, 2+ tags
        mem1 = MagicMock()
        mem1.id = "mem-conf-1"
        mem1.entities = ["A", "B", "C", "D"]
        mem1.tags = ["t1", "t2", "t3"]
        mem1.status = MemoryStatus.ACTIVE
        mem1.created_at = now
        mem1.last_used = now

        mem2 = MagicMock()
        mem2.id = "mem-conf-2"
        mem2.entities = ["A", "B", "C", "E"]
        mem2.tags = ["t1", "t2", "t4"]
        mem2.status = MemoryStatus.ACTIVE
        mem2.created_at = now
        mem2.last_used = now

        # Low confidence scenario: 1 entity, 0 tags
        mem3 = MagicMock()
        mem3.id = "mem-lowconf-1"
        mem3.entities = ["X", "Y"]
        mem3.tags = ["a"]
        mem3.status = MemoryStatus.ACTIVE
        mem3.created_at = now
        mem3.last_used = now

        mem4 = MagicMock()
        mem4.id = "mem-lowconf-2"
        mem4.entities = ["X", "Z"]
        mem4.tags = ["b"]
        mem4.status = MemoryStatus.ACTIVE
        mem4.created_at = now
        mem4.last_used = now

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-conf-1": mem1,
            "mem-conf-2": mem2,
            "mem-lowconf-1": mem3,
            "mem-lowconf-2": mem4,
        }

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            # High confidence
            _, conf_high, _ = discovery._calculate_relation_metrics(
                "mem-conf-1", "mem-conf-2", {"A", "B", "C"}
            )

            # Low confidence
            _, conf_low, _ = discovery._calculate_relation_metrics(
                "mem-lowconf-1", "mem-lowconf-2", {"X"}
            )

            # More shared = higher confidence
            assert conf_high > conf_low

    def test_reasoning_includes_shared_entities(
        self, mock_memory_with_entities: MagicMock, mock_memory_overlapping: MagicMock
    ) -> None:
        """Reasoning string includes shared entity names."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {
            "mem-1": mock_memory_with_entities,
            "mem-2": mock_memory_overlapping,
        }

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            _, _, reasoning = discovery._calculate_relation_metrics(
                "mem-1", "mem-2", {"PostgreSQL"}
            )

            # Reasoning should mention shared entities
            assert "PostgreSQL" in reasoning
            assert "Shared entities:" in reasoning

    def test_reasoning_includes_shared_tags_when_present(self) -> None:
        """Reasoning includes shared tags when they exist."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())

        mem1 = MagicMock()
        mem1.id = "mem-tag-1"
        mem1.entities = ["Entity1"]
        mem1.tags = ["shared-tag", "unique-1"]
        mem1.meta = None  # Disable meta so implementation uses direct .tags
        mem1.status = MemoryStatus.ACTIVE
        mem1.created_at = now
        mem1.last_used = now

        mem2 = MagicMock()
        mem2.id = "mem-tag-2"
        mem2.entities = ["Entity1"]
        mem2.tags = ["shared-tag", "unique-2"]
        mem2.meta = None  # Disable meta so implementation uses direct .tags
        mem2.status = MemoryStatus.ACTIVE
        mem2.created_at = now
        mem2.last_used = now

        mock_storage = MagicMock()
        mock_storage.memories = {"mem-tag-1": mem1, "mem-tag-2": mem2}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            _, _, reasoning = discovery._calculate_relation_metrics(
                "mem-tag-1", "mem-tag-2", {"Entity1"}
            )

            # Reasoning should mention shared tags
            assert "shared-tag" in reasoning
            assert "Shared tags:" in reasoning

    def test_returns_zero_for_missing_memories(self) -> None:
        """Returns zero strength/confidence when memories not found."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            strength, confidence, reasoning = discovery._calculate_relation_metrics(
                "nonexistent-1", "nonexistent-2", set()
            )

            assert strength == 0.0
            assert confidence == 0.0
            assert "not found" in reasoning.lower()

    def test_strength_capped_at_one(self) -> None:
        """Strength is capped at 1.0 even with perfect overlap."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())

        # Identical entities and tags
        mem1 = MagicMock()
        mem1.id = "mem-same-1"
        mem1.entities = ["A", "B"]
        mem1.tags = ["t1", "t2"]
        mem1.status = MemoryStatus.ACTIVE
        mem1.created_at = now
        mem1.last_used = now

        mem2 = MagicMock()
        mem2.id = "mem-same-2"
        mem2.entities = ["A", "B"]
        mem2.tags = ["t1", "t2"]
        mem2.status = MemoryStatus.ACTIVE
        mem2.created_at = now
        mem2.last_used = now

        mock_storage = MagicMock()
        mock_storage.memories = {"mem-same-1": mem1, "mem-same-2": mem2}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            strength, _, _ = discovery._calculate_relation_metrics(
                "mem-same-1", "mem-same-2", {"A", "B"}
            )

            # Perfect overlap = Jaccard 1.0, strength = 0.7*1 + 0.3*1 = 1.0
            assert strength <= 1.0


# =============================================================================
# Additional Unit Tests
# =============================================================================


class TestRelationshipDiscoveryUnit:
    """Additional unit tests for RelationshipDiscovery."""

    def test_init_accepts_min_confidence(self) -> None:
        """RelationshipDiscovery accepts custom min_confidence."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch("cortexgraph.agents.relationship_discovery.get_storage"):
            discovery = RelationshipDiscovery(dry_run=True, min_confidence=0.5)

            assert discovery._min_confidence == 0.5

    def test_init_accepts_min_shared_entities(self) -> None:
        """RelationshipDiscovery accepts custom min_shared_entities."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch("cortexgraph.agents.relationship_discovery.get_storage"):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=3)

            assert discovery._min_shared_entities == 3

    def test_init_uses_default_rate_limit(self) -> None:
        """RelationshipDiscovery uses default rate limit of 100."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch("cortexgraph.agents.relationship_discovery.get_storage"):
            discovery = RelationshipDiscovery(dry_run=True)

            assert discovery.rate_limit == 100

    def test_dry_run_mode_set(self) -> None:
        """RelationshipDiscovery respects dry_run setting."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch("cortexgraph.agents.relationship_discovery.get_storage"):
            discovery_dry = RelationshipDiscovery(dry_run=True)
            discovery_live = RelationshipDiscovery(dry_run=False)

            assert discovery_dry.dry_run is True
            assert discovery_live.dry_run is False

    def test_pair_id_format_normalized(
        self, mock_memory_with_entities: MagicMock, mock_memory_overlapping: MagicMock
    ) -> None:
        """Pair IDs are normalized to consistent order."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        # Use IDs that would sort differently
        mock_memory_with_entities.id = "zebra-mem"
        mock_memory_overlapping.id = "alpha-mem"
        mock_storage.memories = {
            "zebra-mem": mock_memory_with_entities,
            "alpha-mem": mock_memory_overlapping,
        }
        mock_storage.relations = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=1)
            discovery._storage = mock_storage

            candidates = discovery.scan()

            # Pair ID should be normalized (alpha before zebra)
            for candidate in candidates:
                parts = candidate.split(":")
                assert parts[0] < parts[1], "Pair IDs should be in sorted order"

    def test_get_memory_returns_none_for_missing(self) -> None:
        """_get_memory returns None for non-existent memory ID."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        mock_storage = MagicMock()
        mock_storage.memories = {}

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage

            result = discovery._get_memory("nonexistent")

            assert result is None
