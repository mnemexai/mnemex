"""Data models for Mnemex short‑term memory (STM)."""

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryStatus(str, Enum):
    """Status of a memory in the system."""

    ACTIVE = "active"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class MemoryMetadata(BaseModel):
    """Flexible metadata for memories."""

    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    source: str | None = Field(default=None, description="Source of the memory")
    context: str | None = Field(default=None, description="Context when memory was created")
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")


class Memory(BaseModel):
    """A memory record in the STM system."""

    id: str = Field(description="Unique identifier for the memory")
    content: str = Field(description="The content of the memory")
    meta: MemoryMetadata = Field(
        default_factory=MemoryMetadata, description="Metadata about the memory"
    )
    created_at: int = Field(
        default_factory=lambda: int(time.time()),
        description="Timestamp when memory was created (Unix epoch seconds)",
    )
    last_used: int = Field(
        default_factory=lambda: int(time.time()),
        description="Timestamp when memory was last accessed (Unix epoch seconds)",
    )
    use_count: int = Field(default=0, description="Number of times memory has been accessed")
    strength: float = Field(
        default=1.0, description="Strength of the memory (for decay calculations)", ge=0
    )
    status: MemoryStatus = Field(
        default=MemoryStatus.ACTIVE, description="Current status of the memory"
    )
    promoted_at: int | None = Field(
        default=None, description="Timestamp when memory was promoted (if applicable)"
    )
    promoted_to: str | None = Field(
        default=None,
        description="Location where memory was promoted (e.g., vault path)",
    )
    embed: list[float] | None = Field(
        default=None, description="Embedding vector for semantic search"
    )
    entities: list[str] = Field(
        default_factory=list, description="Named entities extracted from or tagged in this memory"
    )
    # Natural spaced repetition fields
    review_priority: float = Field(
        default=0.0,
        description="Priority score for natural review (0.0 = not needed, 1.0 = urgent)",
        ge=0,
        le=1,
    )
    last_review_at: int | None = Field(
        default=None,
        description="Timestamp when memory was last naturally reinforced in conversation",
    )
    review_count: int = Field(
        default=0, description="Number of times memory has been naturally reinforced"
    )
    cross_domain_count: int = Field(
        default=0,
        description="Number of times used across different contexts/domains",
    )

    def to_db_dict(self) -> dict[str, Any]:
        """Convert memory to dictionary for database storage."""
        import json

        return {
            "id": self.id,
            "content": self.content,
            "meta": self.meta.model_dump_json(),
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "strength": self.strength,
            "status": self.status.value,
            "promoted_at": self.promoted_at,
            "promoted_to": self.promoted_to,
            "entities": json.dumps(self.entities),
            "review_priority": self.review_priority,
            "last_review_at": self.last_review_at,
            "review_count": self.review_count,
            "cross_domain_count": self.cross_domain_count,
            # embed handled separately as BLOB
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Memory":
        """Create Memory instance from database row."""
        import json

        meta_dict = json.loads(row["meta"]) if isinstance(row["meta"], str) else row["meta"]

        # Parse entities (may be missing in older rows)
        entities_raw = row.get("entities", "[]")
        entities = json.loads(entities_raw) if isinstance(entities_raw, str) else entities_raw or []

        return cls(
            id=row["id"],
            content=row["content"],
            meta=MemoryMetadata(**meta_dict),
            created_at=row["created_at"],
            last_used=row["last_used"],
            use_count=row["use_count"],
            strength=row["strength"],
            status=MemoryStatus(row["status"]),
            promoted_at=row.get("promoted_at"),
            promoted_to=row.get("promoted_to"),
            embed=row.get("embed"),
            entities=entities,
            review_priority=row.get("review_priority", 0.0),
            last_review_at=row.get("last_review_at"),
            review_count=row.get("review_count", 0),
            cross_domain_count=row.get("cross_domain_count", 0),
        )


class SearchQuery(BaseModel):
    """Query parameters for memory search."""

    query: str | None = Field(default=None, description="Text query for search")
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    top_k: int = Field(default=10, description="Number of results to return", ge=1, le=100)
    window_days: int | None = Field(
        default=None, description="Only search memories from last N days", ge=1
    )
    min_score: float | None = Field(
        default=None, description="Minimum decay score threshold", ge=0, le=1
    )
    status: MemoryStatus | None = Field(
        default=MemoryStatus.ACTIVE, description="Filter by memory status"
    )
    use_embeddings: bool = Field(default=False, description="Use semantic search with embeddings")


class SearchResult(BaseModel):
    """Result from a memory search."""

    memory: Memory = Field(description="The memory that matched")
    score: float = Field(description="Relevance/decay score")
    similarity: float | None = Field(
        default=None, description="Semantic similarity score (if using embeddings)"
    )


class ClusterConfig(BaseModel):
    """Configuration for clustering memories."""

    strategy: str = Field(
        default="similarity", description="Clustering strategy (similarity, temporal, hybrid)"
    )
    threshold: float = Field(
        default=0.83, description="Similarity threshold for linking", ge=0, le=1
    )
    max_cluster_size: int = Field(default=12, description="Maximum memories per cluster", ge=1)
    min_cluster_size: int = Field(default=2, description="Minimum memories per cluster", ge=2)
    use_embeddings: bool = Field(default=True, description="Use embeddings for clustering")


class Cluster(BaseModel):
    """A cluster of similar memories."""

    id: str = Field(description="Cluster identifier")
    memories: list[Memory] = Field(description="Memories in this cluster")
    centroid: list[float] | None = Field(
        default=None, description="Cluster centroid (if using embeddings)"
    )
    cohesion: float = Field(description="Cluster cohesion score", ge=0, le=1)
    suggested_action: str = Field(
        description="Suggested action (auto-merge, llm-review, keep-separate)"
    )


class PromotionCandidate(BaseModel):
    """A memory that is a candidate for promotion."""

    memory: Memory = Field(description="The memory to promote")
    reason: str = Field(description="Reason for promotion")
    score: float = Field(description="Current decay score")
    use_count: int = Field(description="Number of uses")
    age_days: float = Field(description="Age in days")


class GarbageCollectionResult(BaseModel):
    """Result from garbage collection operation."""

    removed_count: int = Field(description="Number of memories removed")
    archived_count: int = Field(description="Number of memories archived")
    freed_score_sum: float = Field(description="Sum of scores of removed memories")
    memory_ids: list[str] = Field(description="IDs of affected memories")


class Relation(BaseModel):
    """A relation between two memories."""

    id: str = Field(description="Unique identifier for the relation")
    from_memory_id: str = Field(description="Source memory ID")
    to_memory_id: str = Field(description="Target memory ID")
    relation_type: str = Field(
        description="Type of relation (e.g., 'references', 'similar_to', 'follows_from')"
    )
    strength: float = Field(default=1.0, description="Strength of the relation", ge=0, le=1)
    created_at: int = Field(
        default_factory=lambda: int(time.time()),
        description="Timestamp when relation was created",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the relation"
    )

    def to_db_dict(self) -> dict[str, Any]:
        """Convert relation to dictionary for database storage."""
        import json

        return {
            "id": self.id,
            "from_memory_id": self.from_memory_id,
            "to_memory_id": self.to_memory_id,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "created_at": self.created_at,
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Relation":
        """Create Relation instance from database row."""
        import json

        metadata = (
            json.loads(row["metadata"])
            if isinstance(row["metadata"], str)
            else row.get("metadata", {})
        )

        return cls(
            id=row["id"],
            from_memory_id=row["from_memory_id"],
            to_memory_id=row["to_memory_id"],
            relation_type=row["relation_type"],
            strength=row["strength"],
            created_at=row["created_at"],
            metadata=metadata or {},
        )


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph of memories and relations."""

    memories: list[Memory] = Field(description="All memories in the graph")
    relations: list[Relation] = Field(description="All relations between memories")
    stats: dict[str, Any] = Field(default_factory=dict, description="Statistics about the graph")
