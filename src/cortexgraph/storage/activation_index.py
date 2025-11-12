"""In-memory activation index for fast keyword/entity/relation lookups.

This module provides the ActivationGraph index structure used by the
activation service for efficient memory matching during conversation.
"""

import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from cortexgraph.storage.models import Memory, Relation

if TYPE_CHECKING:
    import numpy as np  # type: ignore[import-not-found]
    import numpy.typing as npt  # type: ignore[import-not-found]
else:
    try:
        import numpy as np
        import numpy.typing as npt  # type: ignore[import-not-found]
    except ImportError:
        np = None  # type: ignore[assignment]
        npt = None  # type: ignore[assignment]


class ActivationGraph(BaseModel):
    """In-memory index for fast activation lookups.

    Built from JSONL storage on server startup, updated incrementally
    as memories are saved/modified.
    """

    # Keyword inverted index
    keyword_to_memories: dict[str, list[str]] = Field(
        default_factory=dict, description="Map: keyword -> [memory_ids]"
    )

    # Entity inverted index
    entity_to_memories: dict[str, list[str]] = Field(
        default_factory=dict, description="Map: entity -> [memory_ids]"
    )

    # Tag inverted index
    tag_to_memories: dict[str, list[str]] = Field(
        default_factory=dict, description="Map: tag -> [memory_ids]"
    )

    # Embedding vectors (optional, if MNEMEX_ENABLE_EMBEDDINGS=true)
    memory_embeddings: dict[str, np.ndarray] | None = Field(
        default=None, description="Map: memory_id -> embedding vector (768-dim)"
    )

    # Relation graph for spreading
    outgoing_relations: dict[str, list[str]] = Field(
        default_factory=dict, description="Map: from_memory_id -> [to_memory_ids]"
    )

    # Metadata
    last_updated: int = Field(..., description="Unix timestamp of last index rebuild")
    memory_count: int = Field(default=0, ge=0, description="Total memories indexed")
    relation_count: int = Field(default=0, ge=0, description="Total relations indexed")

    class Config:
        arbitrary_types_allowed = True  # Allow numpy arrays

    def find_by_keywords(self, keywords: list[str]) -> set[str]:
        """Find memory IDs matching any keyword.

        Args:
            keywords: List of keywords to search for

        Returns:
            Set of memory IDs that match any keyword
        """
        memory_ids: set[str] = set()
        for keyword in keywords:
            if keyword in self.keyword_to_memories:
                memory_ids.update(self.keyword_to_memories[keyword])
        return memory_ids

    def find_by_entities(self, entities: list[str]) -> set[str]:
        """Find memory IDs containing any entity.

        Args:
            entities: List of entities to search for

        Returns:
            Set of memory IDs that contain any entity
        """
        memory_ids: set[str] = set()
        for entity in entities:
            if entity in self.entity_to_memories:
                memory_ids.update(self.entity_to_memories[entity])
        return memory_ids

    def find_by_tags(self, tags: list[str]) -> set[str]:
        """Find memory IDs with any tag.

        Args:
            tags: List of tags to search for

        Returns:
            Set of memory IDs that have any tag
        """
        memory_ids: set[str] = set()
        for tag in tags:
            if tag in self.tag_to_memories:
                memory_ids.update(self.tag_to_memories[tag])
        return memory_ids

    def get_related_memories(self, memory_id: str) -> list[str]:
        """Get all memories directly related to this memory.

        Args:
            memory_id: ID of the source memory

        Returns:
            List of related memory IDs (via outgoing relations)
        """
        return self.outgoing_relations.get(memory_id, [])


def build_activation_graph(
    memories: list[Memory],
    relations: list[Relation],
    extract_keywords_fn: Any | None = None,
) -> ActivationGraph:
    """Build activation index from all memories and relations.

    Called on server startup and after significant changes.

    Args:
        memories: All active memories to index
        relations: All relations between memories
        extract_keywords_fn: Optional keyword extraction function
                             (defaults to None, caller should provide from nlp module)

    Returns:
        ActivationGraph with populated indexes
    """
    graph = ActivationGraph(last_updated=int(time.time()))

    # Build keyword index (if extractor provided)
    if extract_keywords_fn is not None:
        for memory in memories:
            keywords = extract_keywords_fn(memory.content)
            for keyword in keywords:
                if keyword not in graph.keyword_to_memories:
                    graph.keyword_to_memories[keyword] = []
                graph.keyword_to_memories[keyword].append(memory.id)

    # Build entity index
    for memory in memories:
        for entity in memory.entities:
            entity_lower = entity.lower()
            if entity_lower not in graph.entity_to_memories:
                graph.entity_to_memories[entity_lower] = []
            graph.entity_to_memories[entity_lower].append(memory.id)

    # Build tag index
    for memory in memories:
        for tag in memory.meta.tags:
            tag_lower = tag.lower()
            if tag_lower not in graph.tag_to_memories:
                graph.tag_to_memories[tag_lower] = []
            graph.tag_to_memories[tag_lower].append(memory.id)

    # Build relation graph (outgoing edges)
    for relation in relations:
        if relation.from_memory_id not in graph.outgoing_relations:
            graph.outgoing_relations[relation.from_memory_id] = []
        graph.outgoing_relations[relation.from_memory_id].append(relation.to_memory_id)

    # Build embeddings index (if available)
    for memory in memories:
        if memory.embed is not None:
            if graph.memory_embeddings is None:
                graph.memory_embeddings = {}
            if np is not None:
                graph.memory_embeddings[memory.id] = np.array(memory.embed)
            else:
                # Skip embeddings if numpy not available
                pass

    # Update counts
    graph.memory_count = len(memories)
    graph.relation_count = len(relations)

    return graph
