"""Unit tests for result models and enums (T020).

Tests Pydantic model validation and enum values.
"""

from __future__ import annotations

import pytest

from cortexgraph.agents.models import (
    ClusterAction,
    ClusterResult,
    DecayAction,
    DecayResult,
    MergeResult,
    ProcessingDecision,
    PromotionResult,
    RelationResult,
    Urgency,
)

# =============================================================================
# Enum Tests
# =============================================================================


class TestUrgencyEnum:
    """Tests for Urgency enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert Urgency.HIGH.value == "high"
        assert Urgency.MEDIUM.value == "medium"
        assert Urgency.LOW.value == "low"

    def test_string_conversion(self) -> None:
        """Test string conversion."""
        assert str(Urgency.HIGH) == "Urgency.HIGH"
        assert Urgency.HIGH == "high"  # str enum comparison


class TestDecayActionEnum:
    """Tests for DecayAction enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert DecayAction.REINFORCE.value == "reinforce"
        assert DecayAction.CONSOLIDATE.value == "consolidate"
        assert DecayAction.PROMOTE.value == "promote"
        assert DecayAction.GC.value == "gc"


class TestClusterActionEnum:
    """Tests for ClusterAction enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert ClusterAction.MERGE.value == "merge"
        assert ClusterAction.LINK.value == "link"
        assert ClusterAction.IGNORE.value == "ignore"


class TestProcessingDecisionEnum:
    """Tests for ProcessingDecision enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert ProcessingDecision.AUTO.value == "auto"
        assert ProcessingDecision.LOG_ONLY.value == "log"
        assert ProcessingDecision.WAIT_HUMAN.value == "wait"


# =============================================================================
# DecayResult Tests
# =============================================================================


class TestDecayResult:
    """Tests for DecayResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = DecayResult(
            memory_id="abc-123",
            score=0.08,
            urgency=Urgency.HIGH,
            action=DecayAction.REINFORCE,
        )
        assert result.memory_id == "abc-123"
        assert result.score == 0.08
        assert result.urgency == Urgency.HIGH
        assert result.action == DecayAction.REINFORCE
        assert result.beads_issue_id is None

    def test_with_beads_issue(self) -> None:
        """Test result with beads issue ID."""
        result = DecayResult(
            memory_id="abc-123",
            score=0.08,
            urgency=Urgency.HIGH,
            action=DecayAction.REINFORCE,
            beads_issue_id="cortexgraph-001",
        )
        assert result.beads_issue_id == "cortexgraph-001"

    def test_score_validation(self) -> None:
        """Test score boundary validation."""
        # Valid boundaries
        DecayResult(
            memory_id="test",
            score=0.0,
            urgency=Urgency.LOW,
            action=DecayAction.GC,
        )
        DecayResult(
            memory_id="test",
            score=1.0,
            urgency=Urgency.LOW,
            action=DecayAction.PROMOTE,
        )

        # Invalid values
        with pytest.raises(ValueError):
            DecayResult(
                memory_id="test",
                score=-0.1,
                urgency=Urgency.LOW,
                action=DecayAction.GC,
            )

        with pytest.raises(ValueError):
            DecayResult(
                memory_id="test",
                score=1.1,
                urgency=Urgency.LOW,
                action=DecayAction.GC,
            )


# =============================================================================
# ClusterResult Tests
# =============================================================================


class TestClusterResult:
    """Tests for ClusterResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = ClusterResult(
            cluster_id="cluster-456",
            memory_ids=["mem-1", "mem-2", "mem-3"],
            cohesion=0.82,
            action=ClusterAction.MERGE,
            confidence=0.95,
        )
        assert result.cluster_id == "cluster-456"
        assert len(result.memory_ids) == 3
        assert result.cohesion == 0.82
        assert result.action == ClusterAction.MERGE
        assert result.confidence == 0.95

    def test_minimum_memory_ids(self) -> None:
        """Test minimum 2 memory IDs required."""
        # Valid with 2 memories
        ClusterResult(
            cluster_id="test",
            memory_ids=["mem-1", "mem-2"],
            cohesion=0.5,
            action=ClusterAction.LINK,
            confidence=0.8,
        )

        # Invalid with 1 memory
        with pytest.raises(ValueError):
            ClusterResult(
                cluster_id="test",
                memory_ids=["mem-1"],
                cohesion=0.5,
                action=ClusterAction.LINK,
                confidence=0.8,
            )

    def test_cohesion_validation(self) -> None:
        """Test cohesion boundary validation."""
        with pytest.raises(ValueError):
            ClusterResult(
                cluster_id="test",
                memory_ids=["mem-1", "mem-2"],
                cohesion=1.5,  # Invalid
                action=ClusterAction.LINK,
                confidence=0.8,
            )


# =============================================================================
# MergeResult Tests
# =============================================================================


class TestMergeResult:
    """Tests for MergeResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = MergeResult(
            new_memory_id="merged-789",
            source_ids=["mem-1", "mem-2"],
            relation_ids=["rel-1", "rel-2"],
            content_diff="Combined PostgreSQL preferences",
            entities_preserved=5,
            success=True,
        )
        assert result.new_memory_id == "merged-789"
        assert len(result.source_ids) == 2
        assert len(result.relation_ids) == 2
        assert result.entities_preserved == 5
        assert result.success is True

    def test_default_relation_ids(self) -> None:
        """Test default empty relation_ids."""
        result = MergeResult(
            new_memory_id="merged-789",
            source_ids=["mem-1", "mem-2"],
            content_diff="Combined",
            entities_preserved=0,
            success=True,
        )
        assert result.relation_ids == []

    def test_minimum_source_ids(self) -> None:
        """Test minimum 2 source IDs required."""
        with pytest.raises(ValueError):
            MergeResult(
                new_memory_id="test",
                source_ids=["mem-1"],  # Invalid - need 2
                content_diff="test",
                entities_preserved=0,
                success=True,
            )

    def test_entities_preserved_validation(self) -> None:
        """Test entities_preserved must be >= 0."""
        with pytest.raises(ValueError):
            MergeResult(
                new_memory_id="test",
                source_ids=["mem-1", "mem-2"],
                content_diff="test",
                entities_preserved=-1,  # Invalid
                success=True,
            )


# =============================================================================
# PromotionResult Tests
# =============================================================================


class TestPromotionResult:
    """Tests for PromotionResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = PromotionResult(
            memory_id="mem-123",
            vault_path="memories/mem-123.md",
            criteria_met=["score_threshold"],
            success=True,
        )
        assert result.memory_id == "mem-123"
        assert result.vault_path == "memories/mem-123.md"
        assert "score_threshold" in result.criteria_met
        assert result.success is True

    def test_minimum_criteria_met(self) -> None:
        """Test minimum 1 criteria required."""
        with pytest.raises(ValueError):
            PromotionResult(
                memory_id="test",
                criteria_met=[],  # Invalid - need at least 1
                success=True,
            )

    def test_failed_promotion(self) -> None:
        """Test failed promotion without vault_path."""
        result = PromotionResult(
            memory_id="mem-123",
            vault_path=None,
            criteria_met=["score_threshold"],
            success=False,
        )
        assert result.success is False
        assert result.vault_path is None


# =============================================================================
# RelationResult Tests
# =============================================================================


class TestRelationResult:
    """Tests for RelationResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = RelationResult(
            from_memory_id="mem-1",
            to_memory_id="mem-2",
            relation_id="rel-123",
            strength=0.73,
            reasoning="Shared context: backend development",
            shared_entities=["FastAPI", "PostgreSQL"],
            confidence=0.85,
        )
        assert result.from_memory_id == "mem-1"
        assert result.to_memory_id == "mem-2"
        assert result.strength == 0.73
        assert len(result.shared_entities) == 2
        assert result.confidence == 0.85

    def test_default_shared_entities(self) -> None:
        """Test default empty shared_entities."""
        result = RelationResult(
            from_memory_id="mem-1",
            to_memory_id="mem-2",
            relation_id="rel-123",
            strength=0.5,
            reasoning="Semantic similarity",
            confidence=0.7,
        )
        assert result.shared_entities == []

    def test_strength_validation(self) -> None:
        """Test strength boundary validation."""
        with pytest.raises(ValueError):
            RelationResult(
                from_memory_id="mem-1",
                to_memory_id="mem-2",
                relation_id="rel-123",
                strength=1.5,  # Invalid
                reasoning="test",
                confidence=0.7,
            )
