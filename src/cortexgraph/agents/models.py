"""Result models and enums for consolidation agents.

This module defines the Pydantic models and enums used by all consolidation
agents. Each agent returns a specific result type that captures the outcome
of processing.

From data-model.md:
    - DecayResult: Output from Decay Analyzer
    - ClusterResult: Output from Cluster Detector
    - MergeResult: Output from Semantic Merge
    - PromotionResult: Output from LTM Promoter
    - RelationResult: Output from Relationship Discovery
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# =============================================================================
# Enums (T015)
# =============================================================================


class Urgency(str, Enum):
    """Urgency level for decay analysis.

    From data-model.md:
        - HIGH: score < 0.10 - immediate attention
        - MEDIUM: score 0.10-0.35 (danger zone)
        - LOW: routine processing
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecayAction(str, Enum):
    """Recommended action from decay analysis.

    From data-model.md:
        - REINFORCE: Touch memory to reset decay
        - CONSOLIDATE: Merge with similar memories
        - PROMOTE: Move to LTM
        - GC: Allow garbage collection
    """

    REINFORCE = "reinforce"
    CONSOLIDATE = "consolidate"
    PROMOTE = "promote"
    GC = "gc"


class ClusterAction(str, Enum):
    """Recommended action from cluster detection.

    From data-model.md:
        - MERGE: Cohesion >= 0.75 - merge into one memory
        - LINK: Cohesion 0.4-0.75 - create relations
        - IGNORE: Cohesion < 0.4 - no action
    """

    MERGE = "merge"
    LINK = "link"
    IGNORE = "ignore"


class ProcessingDecision(str, Enum):
    """Confidence-based processing decision.

    From data-model.md and spec.md FR-016:
        - AUTO: confidence >= 0.9 - auto-process immediately
        - LOG_ONLY: 0.7 <= confidence < 0.9 - process with detailed logging
        - WAIT_HUMAN: confidence < 0.7 - create beads issue, wait for human
    """

    AUTO = "auto"
    LOG_ONLY = "log"
    WAIT_HUMAN = "wait"


# =============================================================================
# Result Models (T010-T014)
# =============================================================================


class DecayResult(BaseModel):
    """Output from Decay Analyzer agent (T010).

    From contracts/agent-api.md:
        - memory_id: UUID of analyzed memory
        - score: Current decay score (0.0-1.0)
        - urgency: Processing urgency level
        - action: Recommended action
        - beads_issue_id: Created beads issue (if urgent)

    Example:
        >>> result = DecayResult(
        ...     memory_id="abc-123",
        ...     score=0.08,
        ...     urgency=Urgency.HIGH,
        ...     action=DecayAction.REINFORCE
        ... )
    """

    memory_id: str = Field(..., description="Memory UUID")
    score: float = Field(..., ge=0.0, le=1.0, description="Current decay score")
    urgency: Urgency = Field(..., description="Processing urgency")
    action: DecayAction = Field(..., description="Recommended action")
    beads_issue_id: str | None = Field(default=None, description="Created beads issue ID")


class ClusterResult(BaseModel):
    """Output from Cluster Detector agent (T011).

    From contracts/agent-api.md:
        - cluster_id: Generated cluster UUID
        - memory_ids: Memories in cluster (min 2)
        - cohesion: Cluster cohesion score (0.0-1.0)
        - action: Recommended action (merge/link/ignore)
        - confidence: Confidence in recommendation (0.0-1.0)
        - beads_issue_id: Created beads issue (if cohesion >= 0.4)

    Example:
        >>> result = ClusterResult(
        ...     cluster_id="cluster-456",
        ...     memory_ids=["mem-1", "mem-2", "mem-3"],
        ...     cohesion=0.82,
        ...     action=ClusterAction.MERGE,
        ...     confidence=0.95
        ... )
    """

    cluster_id: str = Field(..., description="Generated cluster UUID")
    memory_ids: list[str] = Field(..., min_length=2, description="Memories in cluster")
    cohesion: float = Field(..., ge=0.0, le=1.0, description="Cluster cohesion score")
    action: ClusterAction = Field(..., description="Recommended action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in recommendation")
    beads_issue_id: str | None = Field(default=None, description="Created beads issue ID")


class MergeResult(BaseModel):
    """Output from Semantic Merge agent (T012).

    From contracts/agent-api.md:
        - new_memory_id: Merged memory UUID
        - source_ids: Original memory IDs (min 2)
        - relation_ids: Created consolidated_from relations
        - content_diff: Summary of merge changes
        - entities_preserved: Count of unique entities kept
        - success: Merge completed successfully
        - beads_issue_id: Closed beads issue

    Example:
        >>> result = MergeResult(
        ...     new_memory_id="merged-789",
        ...     source_ids=["mem-1", "mem-2"],
        ...     relation_ids=["rel-1", "rel-2"],
        ...     content_diff="Combined PostgreSQL preferences",
        ...     entities_preserved=5,
        ...     success=True
        ... )
    """

    new_memory_id: str = Field(..., description="Merged memory UUID")
    source_ids: list[str] = Field(..., min_length=2, description="Original memory IDs")
    relation_ids: list[str] = Field(
        default_factory=list, description="Created consolidated_from relations"
    )
    content_diff: str = Field(..., description="Summary of merge changes")
    entities_preserved: int = Field(..., ge=0, description="Count of unique entities kept")
    success: bool = Field(..., description="Merge completed successfully")
    beads_issue_id: str | None = Field(default=None, description="Closed beads issue ID")


class PromotionResult(BaseModel):
    """Output from LTM Promoter agent (T013).

    From contracts/agent-api.md:
        - memory_id: Promoted memory UUID
        - vault_path: Path to markdown file (if success)
        - criteria_met: Which promotion criteria matched
        - success: Promotion completed successfully
        - beads_issue_id: Created beads issue

    Promotion criteria (from data-model.md):
        - score_threshold: decay score > 0.65
        - use_count_threshold: use_count >= 5 within 14 days
        - review_count_threshold: review_count >= 3

    Example:
        >>> result = PromotionResult(
        ...     memory_id="mem-123",
        ...     vault_path="memories/mem-123.md",
        ...     criteria_met=["score_threshold"],
        ...     success=True
        ... )
    """

    memory_id: str = Field(..., description="Promoted memory UUID")
    vault_path: str | None = Field(default=None, description="Path to markdown file")
    criteria_met: list[str] = Field(
        ..., min_length=1, description="Which promotion criteria matched"
    )
    success: bool = Field(..., description="Promotion completed successfully")
    beads_issue_id: str | None = Field(default=None, description="Created beads issue ID")


class RelationResult(BaseModel):
    """Output from Relationship Discovery agent (T014).

    From contracts/agent-api.md:
        - from_memory_id: Source memory UUID
        - to_memory_id: Target memory UUID
        - relation_id: Created relation UUID
        - strength: Relation strength (0.0-1.0)
        - reasoning: Why relation was created
        - shared_entities: Entities in common
        - confidence: Confidence in relation (0.0-1.0)
        - beads_issue_id: Created beads issue

    Example:
        >>> result = RelationResult(
        ...     from_memory_id="mem-1",
        ...     to_memory_id="mem-2",
        ...     relation_id="rel-123",
        ...     strength=0.73,
        ...     reasoning="Shared context: backend development",
        ...     shared_entities=["FastAPI", "PostgreSQL"],
        ...     confidence=0.85
        ... )
    """

    from_memory_id: str = Field(..., description="Source memory UUID")
    to_memory_id: str = Field(..., description="Target memory UUID")
    relation_id: str = Field(..., description="Created relation UUID")
    strength: float = Field(..., ge=0.0, le=1.0, description="Relation strength")
    reasoning: str = Field(..., description="Why relation was created")
    shared_entities: list[str] = Field(default_factory=list, description="Entities in common")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in relation")
    beads_issue_id: str | None = Field(default=None, description="Created beads issue ID")
