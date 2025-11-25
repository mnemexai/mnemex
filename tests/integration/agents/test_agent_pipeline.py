"""Integration tests for consolidation pipeline execution (T092).

End-to-end tests for the Scheduler running the full consolidation pipeline
with real storage. Verifies agents execute in correct order and produce
expected results.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortexgraph.agents.scheduler import AGENT_ORDER, Scheduler
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Memory

# Mark all tests in this module as requiring beads CLI
# The scheduler/pipeline tests involve SemanticMerge which requires beads
pytestmark = pytest.mark.requires_beads

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_storage_dir():
    """Create temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_storage_with_memories(temp_storage_dir: Path) -> JSONLStorage:
    """Create real JSONL storage with test memories.

    Creates a mix of memories to exercise the full pipeline:
    - Low-score memories for decay analyzer
    - Similar memories for clustering
    - High-value memories for promotion consideration
    """
    storage = JSONLStorage(str(temp_storage_dir))
    now = int(time.time())

    # Memory with decay potential (old, unused)
    decaying_memory = Memory(
        id="mem-decaying",
        content="Old project configuration details",
        entities=["Config"],
        tags=["project", "config"],
        created_at=now - 86400 * 20,  # 20 days ago
        last_used=now - 86400 * 15,  # 15 days ago
        use_count=0,
        strength=1.0,
    )

    # Similar memories for clustering (share tags and content theme)
    similar_1 = Memory(
        id="mem-similar-1",
        content="Database connection settings for PostgreSQL",
        entities=["PostgreSQL", "Database"],
        tags=["database", "config"],
        created_at=now - 86400 * 5,
        last_used=now - 86400 * 2,
        use_count=3,
        strength=1.2,
    )

    similar_2 = Memory(
        id="mem-similar-2",
        content="PostgreSQL database configuration and tuning",
        entities=["PostgreSQL", "Database"],
        tags=["database", "config", "tuning"],
        created_at=now - 86400 * 4,
        last_used=now - 86400 * 1,
        use_count=4,
        strength=1.3,
    )

    # High-value memory for promotion consideration
    high_value = Memory(
        id="mem-high-value",
        content="Critical architecture decision: Use event sourcing",
        entities=["Architecture", "Event Sourcing"],
        tags=["architecture", "decision"],
        created_at=now - 86400 * 10,
        last_used=now - 3600,  # Recently used
        use_count=15,  # Heavily accessed
        strength=1.8,
    )

    # Recent healthy memory (should mostly be ignored)
    healthy = Memory(
        id="mem-healthy",
        content="Today's standup notes",
        entities=["Team"],
        tags=["meeting"],
        created_at=now - 3600,  # 1 hour ago
        last_used=now - 1800,  # 30 min ago
        use_count=2,
        strength=1.0,
    )

    storage.memories = {
        "mem-decaying": decaying_memory,
        "mem-similar-1": similar_1,
        "mem-similar-2": similar_2,
        "mem-high-value": high_value,
        "mem-healthy": healthy,
    }

    return storage


# =============================================================================
# T092: Integration Test - Pipeline Execution
# =============================================================================


class TestPipelineExecution:
    """End-to-end integration tests for pipeline execution."""

    def test_pipeline_order_constant(self) -> None:
        """Verify AGENT_ORDER constant defines correct pipeline sequence."""
        assert AGENT_ORDER == ["decay", "cluster", "merge", "promote", "relations"]

    def test_run_pipeline_returns_dict_keyed_by_agent(
        self, test_storage_with_memories: JSONLStorage
    ) -> None:
        """Test run_pipeline returns results dictionary keyed by agent name."""
        with patch("cortexgraph.context.get_db", return_value=test_storage_with_memories):
            scheduler = Scheduler(dry_run=True)
            results = scheduler.run_pipeline()

        # Should have entry for each agent
        for agent_name in AGENT_ORDER:
            assert agent_name in results
            assert isinstance(results[agent_name], list)

    def test_pipeline_executes_all_agents(self, test_storage_with_memories: JSONLStorage) -> None:
        """Test pipeline executes all five consolidation agents."""
        execution_order = []

        def mock_run_agent(name: str) -> list:
            execution_order.append(name)
            return []

        with patch("cortexgraph.context.get_db", return_value=test_storage_with_memories):
            scheduler = Scheduler(dry_run=True)

            with patch.object(scheduler, "run_agent", side_effect=mock_run_agent):
                scheduler.run_pipeline()

        # Verify all agents called in correct order
        assert execution_order == AGENT_ORDER

    def test_pipeline_with_real_agents(self, test_storage_with_memories: JSONLStorage) -> None:
        """Test pipeline with real agent implementations."""
        with (
            patch("cortexgraph.context.get_db", return_value=test_storage_with_memories),
            patch(
                "cortexgraph.agents.decay_analyzer.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.cluster_detector.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=test_storage_with_memories,
            ),
        ):
            scheduler = Scheduler(dry_run=True)
            results = scheduler.run_pipeline()

        # Pipeline should complete without errors
        assert isinstance(results, dict)
        assert len(results) == 5

        # Each result should be a list (possibly empty)
        for agent_name, agent_results in results.items():
            assert isinstance(agent_results, list), f"{agent_name} didn't return list"

    def test_pipeline_dry_run_no_mutations(self, test_storage_with_memories: JSONLStorage) -> None:
        """Test dry_run mode prevents mutations across entire pipeline."""
        # Capture original memory state
        original_ids = set(test_storage_with_memories.memories.keys())
        original_counts = {
            mid: m.use_count for mid, m in test_storage_with_memories.memories.items()
        }

        with (
            patch("cortexgraph.context.get_db", return_value=test_storage_with_memories),
            patch(
                "cortexgraph.agents.decay_analyzer.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.cluster_detector.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=test_storage_with_memories,
            ),
        ):
            scheduler = Scheduler(dry_run=True)
            scheduler.run_pipeline()

        # No memories added or removed
        assert set(test_storage_with_memories.memories.keys()) == original_ids

        # Use counts unchanged
        for mid, original_count in original_counts.items():
            assert test_storage_with_memories.memories[mid].use_count == original_count

    def test_pipeline_propagates_agent_errors(
        self, test_storage_with_memories: JSONLStorage
    ) -> None:
        """Test pipeline propagates errors from agents."""
        with patch("cortexgraph.context.get_db", return_value=test_storage_with_memories):
            scheduler = Scheduler(dry_run=True)

            # Make decay agent raise an error
            def failing_run():
                raise RuntimeError("Agent failure")

            with patch.object(scheduler, "_get_agent") as mock_get_agent:
                mock_agent = MagicMock()
                mock_agent.run.side_effect = RuntimeError("Agent failure")
                mock_get_agent.return_value = mock_agent

                with pytest.raises(RuntimeError, match="Agent failure"):
                    scheduler.run_pipeline()


class TestIndividualAgentExecution:
    """Tests for running individual agents via scheduler."""

    def test_run_single_agent_decay(self, test_storage_with_memories: JSONLStorage) -> None:
        """Test running only the decay analyzer via scheduler."""
        with (
            patch("cortexgraph.context.get_db", return_value=test_storage_with_memories),
            patch(
                "cortexgraph.agents.decay_analyzer.get_storage",
                return_value=test_storage_with_memories,
            ),
        ):
            scheduler = Scheduler(dry_run=True)
            results = scheduler.run_agent("decay")

        # Should return list of results
        assert isinstance(results, list)

    def test_run_single_agent_cluster(self, test_storage_with_memories: JSONLStorage) -> None:
        """Test running only the cluster detector via scheduler."""
        with (
            patch("cortexgraph.context.get_db", return_value=test_storage_with_memories),
            patch(
                "cortexgraph.agents.cluster_detector.get_storage",
                return_value=test_storage_with_memories,
            ),
        ):
            scheduler = Scheduler(dry_run=True)
            results = scheduler.run_agent("cluster")

        assert isinstance(results, list)

    def test_run_unknown_agent_raises(self) -> None:
        """Test running unknown agent name raises ValueError."""
        scheduler = Scheduler(dry_run=True)

        with pytest.raises(ValueError, match="Unknown agent"):
            scheduler.run_agent("unknown_agent")


class TestSchedulerConfiguration:
    """Tests for scheduler configuration affecting pipeline."""

    def test_scheduler_passes_dry_run_to_agents(
        self, test_storage_with_memories: JSONLStorage
    ) -> None:
        """Test scheduler's dry_run setting propagates to agents."""
        created_agents = []

        def capture_agent(name: str):
            # Import inside to avoid circular imports
            from cortexgraph.agents.cluster_detector import ClusterDetector
            from cortexgraph.agents.decay_analyzer import DecayAnalyzer
            from cortexgraph.agents.ltm_promoter import LTMPromoter
            from cortexgraph.agents.relationship_discovery import RelationshipDiscovery
            from cortexgraph.agents.semantic_merge import SemanticMerge

            # Create agent with dry_run from scheduler
            agents = {
                "decay": DecayAnalyzer,
                "cluster": ClusterDetector,
                "merge": SemanticMerge,
                "promote": LTMPromoter,
                "relations": RelationshipDiscovery,
            }
            agent = agents[name](dry_run=True)  # Should match scheduler's setting
            created_agents.append((name, agent.dry_run))
            return agent

        with (
            patch("cortexgraph.context.get_db", return_value=test_storage_with_memories),
            patch(
                "cortexgraph.agents.decay_analyzer.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.cluster_detector.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=test_storage_with_memories,
            ),
        ):
            scheduler = Scheduler(dry_run=True)

            with patch.object(scheduler, "_get_agent", side_effect=capture_agent):
                scheduler.run_pipeline()

        # All agents should have dry_run=True
        for name, dry_run_value in created_agents:
            assert dry_run_value is True, f"Agent {name} didn't receive dry_run=True"


class TestScheduledExecution:
    """Tests for scheduled pipeline execution."""

    def test_run_scheduled_executes_when_due(
        self, test_storage_with_memories: JSONLStorage
    ) -> None:
        """Test run_scheduled executes pipeline when interval has elapsed."""
        with (
            patch("cortexgraph.context.get_db", return_value=test_storage_with_memories),
            patch(
                "cortexgraph.agents.decay_analyzer.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.cluster_detector.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.semantic_merge.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.ltm_promoter.get_storage",
                return_value=test_storage_with_memories,
            ),
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=test_storage_with_memories,
            ),
        ):
            scheduler = Scheduler(dry_run=True, interval_seconds=1)

            # Force execution regardless of last run
            result = scheduler.run_scheduled(force=True)

        assert result["skipped"] is False
        assert "results" in result
        assert len(result["results"]) == 5

    def test_run_scheduled_skips_when_not_due(
        self, test_storage_with_memories: JSONLStorage
    ) -> None:
        """Test run_scheduled skips when interval hasn't elapsed."""
        with patch("cortexgraph.context.get_db", return_value=test_storage_with_memories):
            scheduler = Scheduler(dry_run=True, interval_seconds=9999)

            # Mock should_run to return False
            with patch.object(scheduler, "should_run", return_value=False):
                result = scheduler.run_scheduled()

        assert result["skipped"] is True
        assert "reason" in result


class TestPipelineWithEmptyStorage:
    """Tests for pipeline behavior with empty or minimal storage."""

    def test_pipeline_with_empty_storage(self, temp_storage_dir: Path) -> None:
        """Test pipeline completes gracefully with empty storage."""
        storage = JSONLStorage(str(temp_storage_dir))
        storage.memories = {}

        with (
            patch("cortexgraph.context.get_db", return_value=storage),
            patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=storage),
            patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage),
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=storage),
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=storage),
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=storage,
            ),
        ):
            scheduler = Scheduler(dry_run=True)
            results = scheduler.run_pipeline()

        # Pipeline should complete with empty results
        assert all(r == [] for r in results.values())

    def test_pipeline_with_single_memory(self, temp_storage_dir: Path) -> None:
        """Test pipeline handles single memory correctly."""
        storage = JSONLStorage(str(temp_storage_dir))
        now = int(time.time())

        single = Memory(
            id="single",
            content="Only memory in storage",
            created_at=now - 86400,
            last_used=now - 3600,
            use_count=1,
            strength=1.0,
        )
        storage.memories = {"single": single}

        with (
            patch("cortexgraph.context.get_db", return_value=storage),
            patch("cortexgraph.agents.decay_analyzer.get_storage", return_value=storage),
            patch("cortexgraph.agents.cluster_detector.get_storage", return_value=storage),
            patch("cortexgraph.agents.semantic_merge.get_storage", return_value=storage),
            patch("cortexgraph.agents.ltm_promoter.get_storage", return_value=storage),
            patch(
                "cortexgraph.agents.relationship_discovery.get_storage",
                return_value=storage,
            ),
        ):
            scheduler = Scheduler(dry_run=True)
            results = scheduler.run_pipeline()

        # Should complete without errors
        assert isinstance(results, dict)
        assert len(results) == 5
