"""Integration tests for RelationshipDiscovery end-to-end (T073).

These tests verify the full workflow of RelationshipDiscovery
with real storage and relation creation.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Memory, MemoryMetadata, MemoryStatus, Relation

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_storage(tmp_path: Path):
    """Create a temporary JSONL storage for testing."""
    storage_path = tmp_path / "test_storage"
    storage_path.mkdir(parents=True, exist_ok=True)
    storage = JSONLStorage(storage_path=str(storage_path))
    storage.connect()
    yield storage
    # JSONLStorage doesn't have disconnect(), just yield and let cleanup happen


@pytest.fixture
def populated_storage(temp_storage: JSONLStorage):
    """Create storage with memories that have shared entities."""
    now = int(time.time())

    # Memory pair with shared entities (PostgreSQL, Database)
    mem1 = Memory(
        id="mem-pg-config",
        content="PostgreSQL database configuration for production deployment",
        entities=["PostgreSQL", "Database", "Production"],
        meta=MemoryMetadata(tags=["database", "config", "devops"]),
        strength=1.2,
        use_count=5,
        created_at=now - 86400 * 3,
        last_used=now - 3600,
        status=MemoryStatus.ACTIVE,
    )

    mem2 = Memory(
        id="mem-pg-perf",
        content="PostgreSQL database performance tuning guide",
        entities=["PostgreSQL", "Database", "Performance"],
        meta=MemoryMetadata(tags=["database", "optimization", "performance"]),
        strength=1.1,
        use_count=3,
        created_at=now - 86400 * 5,
        last_used=now - 7200,
        status=MemoryStatus.ACTIVE,
    )

    # Another pair with shared entities (React, Frontend)
    mem3 = Memory(
        id="mem-react-hooks",
        content="React hooks best practices and patterns",
        entities=["React", "Hooks", "Frontend"],
        meta=MemoryMetadata(tags=["javascript", "react", "patterns"]),
        strength=1.0,
        use_count=4,
        created_at=now - 86400 * 2,
        last_used=now - 1800,
        status=MemoryStatus.ACTIVE,
    )

    mem4 = Memory(
        id="mem-react-state",
        content="React state management with hooks and context",
        entities=["React", "State", "Frontend"],
        meta=MemoryMetadata(tags=["javascript", "react", "state"]),
        strength=1.0,
        use_count=2,
        created_at=now - 86400 * 4,
        last_used=now - 5400,
        status=MemoryStatus.ACTIVE,
    )

    # Isolated memory (no shared entities with others)
    mem5 = Memory(
        id="mem-docker",
        content="Docker containerization basics",
        entities=["Docker", "Containers", "DevOps"],
        meta=MemoryMetadata(tags=["devops", "docker", "infrastructure"]),
        strength=1.0,
        use_count=1,
        created_at=now - 86400,
        last_used=now - 900,
        status=MemoryStatus.ACTIVE,
    )

    # Add all memories
    for mem in [mem1, mem2, mem3, mem4, mem5]:
        temp_storage.save_memory(mem)

    return temp_storage


# =============================================================================
# T073: Integration Tests - Relation Creation with Reasoning
# =============================================================================


class TestRelationshipDiscoveryEndToEnd:
    """End-to-end integration tests for RelationshipDiscovery."""

    def test_full_discovery_workflow_dry_run(
        self, populated_storage: JSONLStorage
    ) -> None:
        """Full workflow: scan, process, verify - in dry run mode."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=populated_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=2)
            discovery._storage = populated_storage

            # Step 1: Scan for candidates
            candidates = discovery.scan()

            # Should find pairs with 2+ shared entities
            assert len(candidates) >= 1

            # Step 2: Process each candidate
            results = []
            for pair_id in candidates:
                result = discovery.process_item(pair_id)
                results.append(result)

            # Step 3: Verify results
            for result in results:
                assert result.strength >= 0.0
                assert result.strength <= 1.0
                assert result.confidence >= 0.0
                assert result.confidence <= 1.0
                assert len(result.reasoning) > 0
                assert len(result.shared_entities) >= 2

            # Dry run should NOT create relations
            relations_after = populated_storage.get_relations()
            assert len(relations_after) == 0

    def test_full_discovery_workflow_live_mode(
        self, populated_storage: JSONLStorage
    ) -> None:
        """Full workflow with actual relation creation."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        # Patch beads integration to avoid actual beads calls
        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=populated_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                return_value="mock-issue-123",
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.close_issue",
                return_value=None,
            ),
        ):
            discovery = RelationshipDiscovery(
                dry_run=False, min_shared_entities=2, min_confidence=0.3
            )
            discovery._storage = populated_storage

            # Step 1: Scan
            candidates = discovery.scan()
            assert len(candidates) >= 1

            # Step 2: Process (creates relations)
            created_relations = []
            for pair_id in candidates:
                result = discovery.process_item(pair_id)
                if result.beads_issue_id:  # Was actually created
                    created_relations.append(result)

            # Step 3: Verify relations were created
            relations_after = populated_storage.get_relations()
            assert len(relations_after) >= len(created_relations)

            # Verify relation metadata
            for rel in relations_after:
                assert rel.relation_type == "related"
                assert "discovered_by" in rel.metadata
                assert rel.metadata["discovered_by"] == "RelationshipDiscovery"
                assert "shared_entities" in rel.metadata
                assert "confidence" in rel.metadata
                assert "reasoning" in rel.metadata

    def test_discovers_postgresql_pair(self, populated_storage: JSONLStorage) -> None:
        """Discovers relation between PostgreSQL memories."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=populated_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=2)
            discovery._storage = populated_storage

            candidates = discovery.scan()

            # Find the PostgreSQL pair
            pg_pair = None
            for pair_id in candidates:
                if "mem-pg-config" in pair_id and "mem-pg-perf" in pair_id:
                    pg_pair = pair_id
                    break

            assert pg_pair is not None, "PostgreSQL pair not found"

            # Process and verify
            result = discovery.process_item(pg_pair)

            # Should have PostgreSQL and Database as shared entities
            assert "PostgreSQL" in result.shared_entities
            assert "Database" in result.shared_entities
            assert result.reasoning  # Non-empty reasoning

    def test_discovers_react_pair(self, populated_storage: JSONLStorage) -> None:
        """Discovers relation between React memories."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=populated_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=2)
            discovery._storage = populated_storage

            candidates = discovery.scan()

            # Find the React pair
            react_pair = None
            for pair_id in candidates:
                if "mem-react-hooks" in pair_id and "mem-react-state" in pair_id:
                    react_pair = pair_id
                    break

            assert react_pair is not None, "React pair not found"

            # Process and verify
            result = discovery.process_item(react_pair)

            # Should have React and Frontend as shared entities
            assert "React" in result.shared_entities
            assert "Frontend" in result.shared_entities

    def test_excludes_isolated_memory(self, populated_storage: JSONLStorage) -> None:
        """Isolated memory with no shared entities is not paired."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=populated_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=2)
            discovery._storage = populated_storage

            candidates = discovery.scan()

            # Docker memory should not appear in any pair (no shared entities with others)
            for pair_id in candidates:
                assert "mem-docker" not in pair_id


class TestRelationshipDiscoveryEdgeCases:
    """Edge case tests for RelationshipDiscovery."""

    def test_handles_empty_storage(self, temp_storage: JSONLStorage) -> None:
        """Handles storage with no memories."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=temp_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = temp_storage

            candidates = discovery.scan()

            assert candidates == []

    def test_handles_single_memory(self, temp_storage: JSONLStorage) -> None:
        """Handles storage with only one memory."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())
        mem = Memory(
            id="mem-solo",
            content="Lonely memory",
            entities=["Entity1"],
            meta=MemoryMetadata(tags=["tag1"]),
            strength=1.0,
            use_count=1,
            created_at=now,
            last_used=now,
            status=MemoryStatus.ACTIVE,
        )
        temp_storage.save_memory(mem)

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=temp_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True)
            discovery._storage = temp_storage

            candidates = discovery.scan()

            assert candidates == []

    def test_skips_archived_memories(self, temp_storage: JSONLStorage) -> None:
        """Does not include archived memories in pairs."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        now = int(time.time())

        mem_active = Memory(
            id="mem-active",
            content="Active memory",
            entities=["SharedEntity"],
            meta=MemoryMetadata(tags=["tag1"]),
            strength=1.0,
            use_count=1,
            created_at=now,
            last_used=now,
            status=MemoryStatus.ACTIVE,
        )

        mem_archived = Memory(
            id="mem-archived",
            content="Archived memory",
            entities=["SharedEntity"],
            meta=MemoryMetadata(tags=["tag2"]),
            strength=1.0,
            use_count=1,
            created_at=now,
            last_used=now,
            status=MemoryStatus.ARCHIVED,
        )

        temp_storage.save_memory(mem_active)
        temp_storage.save_memory(mem_archived)

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=temp_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=1)
            discovery._storage = temp_storage

            candidates = discovery.scan()

            # Archived memory should not be paired
            for pair_id in candidates:
                assert "mem-archived" not in pair_id

    def test_skips_already_related_pairs(
        self, populated_storage: JSONLStorage
    ) -> None:
        """Does not suggest pairs that already have a relation."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        # Create an existing relation between PostgreSQL memories
        existing_relation = Relation(
            id="existing-rel-1",
            from_memory_id="mem-pg-config",
            to_memory_id="mem-pg-perf",
            relation_type="related",
            strength=0.8,
            metadata={"created_manually": True},
        )
        populated_storage.create_relation(existing_relation)

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=populated_storage,
        ):
            discovery = RelationshipDiscovery(dry_run=True, min_shared_entities=2)
            discovery._storage = populated_storage

            candidates = discovery.scan()

            # PostgreSQL pair should be excluded (already related)
            for pair_id in candidates:
                has_pg_config = "mem-pg-config" in pair_id
                has_pg_perf = "mem-pg-perf" in pair_id
                assert not (
                    has_pg_config and has_pg_perf
                ), "Already-related pair should be excluded"


class TestRelationshipDiscoveryLiveMode:
    """Tests for live mode relation creation."""

    def test_relation_metadata_complete(
        self, populated_storage: JSONLStorage
    ) -> None:
        """Created relations have complete metadata."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=populated_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                return_value="mock-issue-456",
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.close_issue",
                return_value=None,
            ),
        ):
            discovery = RelationshipDiscovery(
                dry_run=False, min_shared_entities=2, min_confidence=0.3
            )
            discovery._storage = populated_storage

            candidates = discovery.scan()
            assert len(candidates) >= 1

            # Process first candidate
            result = discovery.process_item(candidates[0])

            # Verify relation was created with complete metadata
            relations = populated_storage.get_relations()
            assert len(relations) >= 1

            rel = relations[0]
            assert rel.metadata["discovered_by"] == "RelationshipDiscovery"
            assert isinstance(rel.metadata["shared_entities"], list)
            assert isinstance(rel.metadata["confidence"], float)
            assert isinstance(rel.metadata["reasoning"], str)
            assert rel.metadata["beads_issue_id"] == "mock-issue-456"

    def test_skips_low_confidence_relations(
        self, populated_storage: JSONLStorage
    ) -> None:
        """Does not create relations below confidence threshold."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with patch(
            "cortexgraph.agents.relationship_discovery.get_storage",
            return_value=populated_storage,
        ):
            # Set very high confidence threshold
            discovery = RelationshipDiscovery(
                dry_run=False, min_shared_entities=1, min_confidence=0.99
            )
            discovery._storage = populated_storage

            candidates = discovery.scan()

            # Process all candidates
            for pair_id in candidates:
                result = discovery.process_item(pair_id)
                # Result should indicate skip due to confidence
                if result.confidence < 0.99:
                    assert result.beads_issue_id is None
                    assert "Skipped" in result.reasoning

    def test_result_includes_beads_issue_id(
        self, populated_storage: JSONLStorage
    ) -> None:
        """Live mode results include beads issue ID."""
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        with (
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=populated_storage,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.create_consolidation_issue",
                return_value="beads-test-789",
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.close_issue",
                return_value=None,
            ),
        ):
            discovery = RelationshipDiscovery(
                dry_run=False, min_shared_entities=2, min_confidence=0.3
            )
            discovery._storage = populated_storage

            candidates = discovery.scan()
            assert len(candidates) >= 1

            result = discovery.process_item(candidates[0])

            assert result.beads_issue_id == "beads-test-789"
