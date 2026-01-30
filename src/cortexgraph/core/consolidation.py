"""Consolidation logic for merging similar memories."""

import time
import uuid
from typing import Any

from ..storage.models import Cluster, Memory, MemoryMetadata, MemoryStatus, Relation


def merge_content_smart(memories: list[Memory]) -> str:
    """
    Intelligently merge content from multiple memories.

    Strategy:
    - If very similar (duplicates), keep the longest/most detailed version
    - If related but distinct, combine with clear separation
    - Preserve unique information from each memory

    Args:
        memories: List of memories to merge

    Returns:
        Merged content string
    """
    if not memories:
        return ""

    if len(memories) == 1:
        return memories[0].content

    # Sort by content length descending (longest first)
    sorted_mems = sorted(memories, key=lambda m: len(m.content), reverse=True)

    # Check if they're near-duplicates (longest contains others)
    base_content = sorted_mems[0].content.lower()
    is_duplicate_set = all(
        mem.content.lower() in base_content or base_content in mem.content.lower()
        for mem in sorted_mems[1:]
    )

    if is_duplicate_set:
        # Near duplicates - keep the longest
        return sorted_mems[0].content

    # Related but distinct - combine with clear separation
    merged_parts = []
    seen_content = set()

    for mem in sorted_mems:
        content_lower = mem.content.lower().strip()
        if content_lower not in seen_content:
            merged_parts.append(mem.content.strip())
            seen_content.add(content_lower)

    # Join with double newline for readability
    return "\n\n".join(merged_parts)


def merge_tags(memories: list[Memory]) -> list[str]:
    """
    Merge tags from multiple memories (union).

    Args:
        memories: List of memories

    Returns:
        Combined unique tags
    """
    all_tags = set()
    for mem in memories:
        all_tags.update(mem.meta.tags)

    return sorted(all_tags)


def merge_entities(memories: list[Memory]) -> list[str]:
    """
    Merge entities from multiple memories (union).

    Args:
        memories: List of memories

    Returns:
        Combined unique entities
    """
    all_entities = set()
    for mem in memories:
        all_entities.update(mem.entities)

    return sorted(all_entities)


def merge_metadata(memories: list[Memory]) -> MemoryMetadata:
    """
    Merge metadata from multiple memories.

    Args:
        memories: List of memories

    Returns:
        Merged metadata
    """
    # Merge tags
    tags = merge_tags(memories)

    # Combine sources (if different)
    sources = {mem.meta.source for mem in memories if mem.meta.source}
    source = "; ".join(sorted(sources)) if sources else None

    # Combine contexts (if different)
    contexts = {mem.meta.context for mem in memories if mem.meta.context}
    context = "; ".join(sorted(contexts)) if contexts else None

    # Merge extra metadata
    extra: dict[str, Any] = {}
    for mem in memories:
        extra.update(mem.meta.extra)

    return MemoryMetadata(
        tags=tags,
        source=source,
        context=context,
        extra=extra,
    )


def calculate_merged_strength(memories: list[Memory], cohesion: float) -> float:
    """
    Calculate strength for merged memory.

    Uses max strength with a bonus based on cohesion and number of memories.

    Args:
        memories: List of memories being merged
        cohesion: Cluster cohesion score (0-1)

    Returns:
        Merged strength value
    """
    if not memories:
        return 1.0

    max_strength = max(m.strength for m in memories)

    # Bonus: cohesion * num_memories * 0.1 (capped at 0.5)
    bonus = min(cohesion * len(memories) * 0.1, 0.5)

    # Result: max_strength + bonus, capped at 2.0
    return min(max_strength + bonus, 2.0)


def generate_consolidation_preview(cluster: Cluster) -> dict[str, Any]:
    """
    Generate a preview of what the consolidated memory would look like.

    Args:
        cluster: Cluster of memories to consolidate

    Returns:
        Preview dictionary with merged memory details
    """
    memories = cluster.memories

    if not memories:
        return {
            "error": "Empty cluster",
            "can_consolidate": False,
        }

    if len(memories) == 1:
        return {
            "error": "Single memory in cluster - nothing to consolidate",
            "can_consolidate": False,
        }

    # Create merged memory
    merged_content = merge_content_smart(memories)
    merged_meta = merge_metadata(memories)
    merged_entities = merge_entities(memories)
    merged_strength = calculate_merged_strength(memories, cluster.cohesion)

    # Timing: use earliest created_at, most recent last_used
    earliest_created = min(m.created_at for m in memories)
    latest_used = max(m.last_used for m in memories)
    total_use_count = sum(m.use_count for m in memories)

    preview = {
        "can_consolidate": True,
        "cluster_id": cluster.id,
        "num_memories": len(memories),
        "cohesion": cluster.cohesion,
        "suggested_action": cluster.suggested_action,
        "merged_memory": {
            "content": merged_content,
            "tags": merged_meta.tags,
            "entities": merged_entities,
            "source": merged_meta.source,
            "context": merged_meta.context,
            "created_at": earliest_created,
            "last_used": latest_used,
            "use_count": total_use_count,
            "strength": merged_strength,
        },
        "original_memories": [
            {
                "id": m.id,
                "content_preview": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                "tags": m.meta.tags,
                "use_count": m.use_count,
                "strength": m.strength,
            }
            for m in memories
        ],
        "space_saved": len(memories) - 1,  # N memories -> 1 memory = N-1 savings
    }

    return preview


def execute_consolidation(
    cluster: Cluster,
    storage: Any,  # JSONLStorage instance
    centroid_embedding: list[float] | None = None,
) -> dict[str, Any]:
    """
    Execute the consolidation - create merged memory and archive originals.

    Args:
        cluster: Cluster to consolidate
        storage: Storage instance (JSONLStorage)
        centroid_embedding: Optional centroid embedding for the merged memory

    Returns:
        Result dictionary with success status and details
    """
    memories = cluster.memories

    if len(memories) < 2:
        return {
            "success": False,
            "error": "Need at least 2 memories to consolidate",
        }

    # Generate merged memory
    merged_content = merge_content_smart(memories)
    merged_meta = merge_metadata(memories)
    merged_entities = merge_entities(memories)
    merged_strength = calculate_merged_strength(memories, cluster.cohesion)

    earliest_created = min(m.created_at for m in memories)
    latest_used = max(m.last_used for m in memories)
    total_use_count = sum(m.use_count for m in memories)

    # Create new consolidated memory
    consolidated_memory = Memory(
        id=str(uuid.uuid4()),
        content=merged_content,
        meta=merged_meta,
        entities=merged_entities,
        created_at=earliest_created,
        last_used=latest_used,
        use_count=total_use_count,
        strength=merged_strength,
        status=MemoryStatus.ACTIVE,
        embed=centroid_embedding,
    )

    # Save consolidated memory
    storage.save_memory(consolidated_memory)

    # Collect original IDs before deletion
    original_ids = [mem.id for mem in memories]

    # Create relations from new memory to originals BEFORE deleting them
    # (storage enforces foreign key constraints)
    from ..storage.models import Relation

    # Batch create relations for better performance
    relations = [
        Relation(
            id=str(uuid.uuid4()),
            from_memory_id=consolidated_memory.id,
            to_memory_id=orig_id,
            relation_type="consolidated_from",
            strength=1.0,
            created_at=int(time.time()),
            metadata={
                "cluster_id": cluster.id,
                "cluster_cohesion": cluster.cohesion,
            },
        )
        for orig_id in original_ids
    ]
    storage.create_relations_batch(relations)

    # Mark original memories as consolidated (batch delete for better performance)
    storage.delete_memories_batch(original_ids)

    return {
        "success": True,
        "new_memory_id": consolidated_memory.id,
        "consolidated_ids": original_ids,
        "space_saved": len(original_ids) - 1,
        "merged_content_length": len(merged_content),
        "merged_tags": len(merged_meta.tags),
        "merged_entities": len(merged_entities),
        "merged_strength": merged_strength,
    }


def link_cluster_memories(
    cluster: Cluster,
    storage: Any,  # JSONLStorage instance
) -> dict[str, Any]:
    """
    Create 'related' relations between all memories in a cluster without merging.

    This is useful for medium-cohesion clusters (0.40-0.75) where memories are
    related but distinct enough to keep separate. Creates bidirectional relations
    so the knowledge graph shows them as connected.

    Args:
        cluster: Cluster whose memories should be linked
        storage: Storage instance (JSONLStorage)

    Returns:
        Result dictionary with success status and relation details
    """
    memories = cluster.memories

    if len(memories) < 2:
        return {
            "success": False,
            "error": "Need at least 2 memories to link",
        }

    # Track created relations
    created_relations = []
    skipped_existing = 0

    # Create relations between all pairs in the cluster
    for i in range(len(memories)):
        for j in range(i + 1, len(memories)):
            mem_a = memories[i]
            mem_b = memories[j]

            # Check if relation already exists (either direction)
            existing_ab = storage.get_relations(
                from_memory_id=mem_a.id,
                to_memory_id=mem_b.id,
                relation_type="related",
            )
            existing_ba = storage.get_relations(
                from_memory_id=mem_b.id,
                to_memory_id=mem_a.id,
                relation_type="related",
            )

            if existing_ab or existing_ba:
                skipped_existing += 1
                continue

            # Create bidirectional relations
            relation_ab = Relation(
                id=str(uuid.uuid4()),
                from_memory_id=mem_a.id,
                to_memory_id=mem_b.id,
                relation_type="related",
                strength=cluster.cohesion,  # Use cluster cohesion as relation strength
                created_at=int(time.time()),
                metadata={
                    "cluster_id": cluster.id,
                    "cluster_cohesion": cluster.cohesion,
                    "cluster_size": len(memories),
                    "link_reason": "cluster_linking",
                },
            )

            relation_ba = Relation(
                id=str(uuid.uuid4()),
                from_memory_id=mem_b.id,
                to_memory_id=mem_a.id,
                relation_type="related",
                strength=cluster.cohesion,
                created_at=int(time.time()),
                metadata={
                    "cluster_id": cluster.id,
                    "cluster_cohesion": cluster.cohesion,
                    "cluster_size": len(memories),
                    "link_reason": "cluster_linking",
                },
            )

            storage.create_relation(relation_ab)
            storage.create_relation(relation_ba)

            created_relations.append((mem_a.id, mem_b.id))

    return {
        "success": True,
        "cluster_id": cluster.id,
        "cluster_size": len(memories),
        "cohesion": cluster.cohesion,
        "relations_created": len(created_relations) * 2,  # Bidirectional
        "pairs_linked": len(created_relations),
        "skipped_existing": skipped_existing,
        "memory_ids": [m.id for m in memories],
        "message": f"Created {len(created_relations) * 2} relations linking {len(memories)} memories",
    }
