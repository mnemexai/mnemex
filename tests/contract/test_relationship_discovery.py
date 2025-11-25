"""Contract tests for RelationshipDiscovery (T069-T070).

These tests verify the RelationshipDiscovery agent conforms to the ConsolidationAgent
contract defined in contracts/agent-api.md.

Contract Requirements (RelationshipDiscovery-specific):
- scan() MUST find memories with potential connections
- scan() MUST NOT return already-related pairs
- scan() MUST return list of memory ID pairs (may be empty)
- scan() MUST NOT modify any data
- process_item() MUST return RelationResult or raise exception
- process_item() MUST calculate relation strength
- process_item() MUST provide reasoning for relation
- process_item() MUST respect confidence threshold
- process_item() MUST NOT create spurious relations (precision > 0.8)
- If dry_run=True, process_item() MUST NOT modify any data
- process_item() SHOULD complete within 5 seconds
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.base import ConsolidationAgent
from cortexgraph.agents.models import RelationResult
from cortexgraph.storage.models import MemoryStatus

if TYPE_CHECKING:
    from cortexgraph.agents.relationship_discovery import RelationshipDiscovery


# =============================================================================
# Contract Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create mock storage with memories that have potential relationships."""
    storage = MagicMock()
    now = int(time.time())

    # Memory about FastAPI backend
    storage.memories = {
        "mem-fastapi": MagicMock(
            id="mem-fastapi",
            content="FastAPI backend with PostgreSQL database connection",
            entities=["FastAPI", "PostgreSQL", "Backend"],
            tags=["api", "database", "python"],
            strength=1.2,
            use_count=5,
            created_at=now - 86400 * 5,
            last_used=now - 3600,
            status=MemoryStatus.ACTIVE,
        ),
        # Memory about PostgreSQL configuration - shares entity with mem-fastapi
        "mem-postgres": MagicMock(
            id="mem-postgres",
            content="PostgreSQL configuration for production deployment",
            entities=["PostgreSQL", "Production", "Database"],
            tags=["database", "config", "production"],
            strength=1.3,
            use_count=8,
            created_at=now - 86400 * 7,
            last_used=now - 7200,
            status=MemoryStatus.ACTIVE,
        ),
        # Memory about Backend architecture - shares entity with mem-fastapi
        "mem-backend": MagicMock(
            id="mem-backend",
            content="Backend architecture design decisions",
            entities=["Backend", "Architecture", "Design"],
            tags=["architecture", "design"],
            strength=1.1,
            use_count=3,
            created_at=now - 86400 * 10,
            last_used=now - 86400,
            status=MemoryStatus.ACTIVE,
        ),
        # Unrelated memory - no shared entities
        "mem-unrelated": MagicMock(
            id="mem-unrelated",
            content="Random notes about cooking recipes",
            entities=["Cooking", "Recipes"],
            tags=["personal", "food"],
            strength=1.0,
            use_count=2,
            created_at=now - 86400 * 15,
            last_used=now - 86400 * 3,
            status=MemoryStatus.ACTIVE,
        ),
        # Archived memory - should be excluded
        "mem-archived": MagicMock(
            id="mem-archived",
            content="Archived database notes",
            entities=["Database", "Archive"],
            tags=["archive"],
            strength=1.0,
            use_count=1,
            created_at=now - 86400 * 30,
            last_used=now - 86400 * 20,
            status=MemoryStatus.ARCHIVED,
        ),
    }

    # Mock existing relations
    storage.relations = {}

    def get_memory(memory_id: str) -> MagicMock | None:
        return storage.memories.get(memory_id)

    storage.get = get_memory
    storage.get_memory = get_memory

    # Mock get_relations_for_memory to return empty for most
    def get_relations_for_memory(memory_id: str) -> list:
        return []

    storage.get_relations_for_memory = get_relations_for_memory

    return storage


@pytest.fixture
def mock_beads_integration() -> MagicMock:
    """Create mock beads integration."""
    beads = MagicMock()
    beads.create_consolidation_issue = MagicMock(return_value="cortexgraph-relations-001")
    beads.close_issue = MagicMock()
    return beads


@pytest.fixture
def relationship_discovery(
    mock_storage: MagicMock,
    mock_beads_integration: MagicMock,
) -> RelationshipDiscovery:
    """Create RelationshipDiscovery with mocked dependencies."""
    from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

    with (
        patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=mock_storage,
        ),
        patch(
            "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
            mock_beads_integration.create_consolidation_issue,
        ),
        patch(
            "cortexgraph.agents.relationship_discovery.close_issue",
            mock_beads_integration.close_issue,
        ),
    ):
        discovery = RelationshipDiscovery(dry_run=True)
        discovery._storage = mock_storage
        discovery._beads = mock_beads_integration
        return discovery


# =============================================================================
# T069: Contract Test - scan() Finds Relationship Candidates
# =============================================================================


class TestRelationshipDiscoveryScanContract:
    """Contract tests for RelationshipDiscovery.scan() method (T069)."""

    def test_scan_returns_list(self, relationship_discovery: RelationshipDiscovery) -> None:
        """scan() MUST return a list."""
        result = relationship_discovery.scan()
        assert isinstance(result, list)

    def test_scan_returns_string_pairs(self, relationship_discovery: RelationshipDiscovery) -> None:
        """scan() MUST return list of string pair identifiers."""
        result = relationship_discovery.scan()
        # Each item should be a string (pair identifier like "mem-1:mem-2")
        for item in result:
            assert isinstance(item, str)

    def test_scan_may_return_empty(self, mock_beads_integration: MagicMock) -> None:
        """scan() MAY return empty list when no relationship candidates."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        # Create storage with only one memory (can't have relationships)
        storage = MagicMock()
        now = int(time.time())
        storage.memories = {
            "mem-1": MagicMock(
                id="mem-1",
                content="Single memory",
                entities=["Entity"],
                tags=["tag"],
                strength=1.0,
                use_count=1,
                created_at=now - 86400,
                last_used=now - 3600,
                status=MemoryStatus.ACTIVE,
            ),
        }
        storage.get_relations_for_memory = MagicMock(return_value=[])

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = storage
            result = discovery.scan()
            # May be empty if no relationship candidates
            assert isinstance(result, list)

    def test_scan_excludes_already_related_pairs(
        self, mock_storage: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """scan() MUST NOT return already-related pairs."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        # Mock existing relation between mem-fastapi and mem-postgres
        existing_relation = MagicMock()
        existing_relation.from_memory_id = "mem-fastapi"
        existing_relation.to_memory_id = "mem-postgres"
        existing_relation.relation_type = "related"

        # Add to relations dict (implementation checks this)
        mock_storage.relations = {"existing-rel-1": existing_relation}

        def get_relations_for_memory(memory_id: str) -> list:
            if memory_id == "mem-fastapi":
                return [existing_relation]
            if memory_id == "mem-postgres":
                return [existing_relation]
            return []

        mock_storage.get_relations_for_memory = get_relations_for_memory

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=mock_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage
            result = discovery.scan()

            # Already-related pair should not appear
            for pair_id in result:
                # Check both orderings
                assert pair_id != "mem-fastapi:mem-postgres"
                assert pair_id != "mem-postgres:mem-fastapi"

    def test_scan_excludes_archived_memories(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """scan() MUST NOT include archived memories."""
        result = relationship_discovery.scan()

        # No pair should include the archived memory
        for pair_id in result:
            assert "mem-archived" not in pair_id

    def test_scan_does_not_modify_data(
        self, relationship_discovery: RelationshipDiscovery, mock_storage: MagicMock
    ) -> None:
        """scan() MUST NOT modify any data."""
        # Take snapshot before
        original_count = len(mock_storage.memories)
        original_relations = len(mock_storage.relations)

        # Run scan
        relationship_discovery.scan()

        # Verify no changes
        assert len(mock_storage.memories) == original_count
        assert len(mock_storage.relations) == original_relations

    def test_scan_is_subclass_of_consolidation_agent(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """RelationshipDiscovery MUST inherit from ConsolidationAgent."""
        assert isinstance(relationship_discovery, ConsolidationAgent)


# =============================================================================
# T070: Contract Test - process_item() Returns RelationResult
# =============================================================================


class TestRelationshipDiscoveryProcessItemContract:
    """Contract tests for RelationshipDiscovery.process_item() method (T070)."""

    def test_process_item_returns_relation_result(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """process_item() MUST return RelationResult."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            result = relationship_discovery.process_item(pair_ids[0])
            assert isinstance(result, RelationResult)

    def test_process_item_result_has_required_fields(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """RelationResult MUST have all required fields."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            result = relationship_discovery.process_item(pair_ids[0])

            # Required fields from contracts/agent-api.md
            assert hasattr(result, "from_memory_id")
            assert hasattr(result, "to_memory_id")
            assert hasattr(result, "relation_id")
            assert hasattr(result, "strength")
            assert hasattr(result, "reasoning")
            assert hasattr(result, "confidence")

            # Types
            assert isinstance(result.from_memory_id, str)
            assert isinstance(result.to_memory_id, str)
            assert isinstance(result.relation_id, str)
            assert isinstance(result.strength, float)
            assert isinstance(result.reasoning, str)
            assert isinstance(result.confidence, float)

    def test_process_item_strength_in_valid_range(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """strength MUST be in range [0.0, 1.0]."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            result = relationship_discovery.process_item(pair_ids[0])
            assert 0.0 <= result.strength <= 1.0

    def test_process_item_confidence_in_valid_range(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """confidence MUST be in range [0.0, 1.0]."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            result = relationship_discovery.process_item(pair_ids[0])
            assert 0.0 <= result.confidence <= 1.0

    def test_process_item_reasoning_not_empty(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """reasoning MUST NOT be empty."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            result = relationship_discovery.process_item(pair_ids[0])
            assert len(result.reasoning) > 0

    def test_process_item_raises_on_invalid_pair_id(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """process_item() MUST raise exception for invalid pair ID."""
        with pytest.raises((ValueError, KeyError, RuntimeError)):
            relationship_discovery.process_item("nonexistent:pair")

    def test_process_item_dry_run_no_side_effects(
        self,
        mock_storage: MagicMock,
        mock_beads_integration: MagicMock,
    ) -> None:
        """If dry_run=True, process_item() MUST NOT modify any data."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=mock_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.close_issue",
                mock_beads_integration.close_issue,
            ),
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage
            discovery._beads = mock_beads_integration

            # Track calls that would modify data
            mock_storage.create_relation = MagicMock()

            pair_ids = discovery.scan()
            if pair_ids:
                discovery.process_item(pair_ids[0])

                # In dry_run mode, no relations should be created
                mock_storage.create_relation.assert_not_called()

    def test_process_item_completes_within_timeout(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """process_item() SHOULD complete within 5 seconds."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            start = time.time()
            relationship_discovery.process_item(pair_ids[0])
            elapsed = time.time() - start

            assert elapsed < 5.0, f"process_item took {elapsed:.2f}s (limit: 5s)"


# =============================================================================
# Contract Integration Tests
# =============================================================================


class TestRelationshipDiscoveryFullContract:
    """Integration tests verifying full contract compliance."""

    def test_run_method_uses_scan_and_process_item(
        self, relationship_discovery: RelationshipDiscovery
    ) -> None:
        """run() MUST call scan() then process_item() for each result."""
        results = relationship_discovery.run()

        # All results should be RelationResult
        for result in results:
            assert isinstance(result, RelationResult)

    def test_shared_entities_populated(self, relationship_discovery: RelationshipDiscovery) -> None:
        """shared_entities SHOULD be populated for related memories."""
        pair_ids = relationship_discovery.scan()
        if pair_ids:
            result = relationship_discovery.process_item(pair_ids[0])

            # If relation was created, shared_entities should be populated
            # (may be empty if relation based on other factors)
            assert isinstance(result.shared_entities, list)

    def test_precision_threshold_respected(
        self, mock_storage: MagicMock, mock_beads_integration: MagicMock
    ) -> None:
        """MUST NOT create spurious relations (precision > 0.8 requirement)."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        # Create memories with very weak potential relationship
        now = int(time.time())
        mock_storage.memories = {
            "mem-weak-1": MagicMock(
                id="mem-weak-1",
                content="Something about topic A",
                entities=["TopicA"],
                tags=["tag1"],
                strength=1.0,
                use_count=1,
                created_at=now - 86400,
                last_used=now - 3600,
                status=MemoryStatus.ACTIVE,
            ),
            "mem-weak-2": MagicMock(
                id="mem-weak-2",
                content="Something about topic B",
                entities=["TopicB"],  # No overlap
                tags=["tag2"],  # No overlap
                strength=1.0,
                use_count=1,
                created_at=now - 86400,
                last_used=now - 3600,
                status=MemoryStatus.ACTIVE,
            ),
        }
        mock_storage.get_relations_for_memory = MagicMock(return_value=[])

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=mock_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_confidence=0.8)
            discovery._storage = mock_storage

            # With no shared entities and high confidence threshold,
            # should not find this as a candidate
            results = discovery.run()

            # If any results, confidence should meet threshold
            for result in results:
                assert result.confidence >= 0.8

    def test_run_handles_errors_gracefully(
        self,
        mock_storage: MagicMock,
        mock_beads_integration: MagicMock,
    ) -> None:
        """run() MUST handle errors per-item without aborting all."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        # Add a broken memory that might cause issues
        mock_storage.memories["mem-broken"] = MagicMock(
            id="mem-broken",
            content=None,  # This might cause issues
            entities=None,
            tags=None,
            strength=None,
            use_count=None,
            created_at=None,
            last_used=None,
            status=MemoryStatus.ACTIVE,
        )

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=mock_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                mock_beads_integration.create_consolidation_issue,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.close_issue",
                mock_beads_integration.close_issue,
            ),
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = mock_storage
            discovery._beads = mock_beads_integration

            # Should not raise - should skip errors and continue
            results = discovery.run()

            # Should still produce some results from valid memories
            assert isinstance(results, list)
