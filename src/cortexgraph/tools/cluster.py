"""Cluster memory tool - find similar memories for consolidation."""

from typing import Any

from ..config import get_config
from ..context import db, mcp
from ..core.clustering import cluster_memories_simple, find_duplicate_candidates
from ..security.validators import validate_positive_int, validate_score
from ..storage.models import ClusterConfig, MemoryStatus


@mcp.tool()
def cluster_memories(
    strategy: str = "similarity",
    threshold: float | None = None,
    max_cluster_size: int | None = None,
    find_duplicates: bool = False,
    duplicate_threshold: float | None = None,
) -> dict[str, Any]:
    """Cluster similar memories or find duplicates.

    Args:
        strategy: Clustering strategy (default "similarity").
        threshold: Similarity threshold (0.0-1.0, uses config default if None).
        max_cluster_size: Max cluster size (1-100, uses config default if None).
        find_duplicates: Find duplicate pairs instead of clustering.
        duplicate_threshold: Duplicate threshold (0.0-1.0, uses config default if None).

    Returns:
        Dict with clusters or duplicates list, scores, suggested_action.

    Raises:
        ValueError: Invalid threshold or max_cluster_size.
    """
    # Input validation
    if threshold is not None:
        threshold = validate_score(threshold, "threshold")

    if max_cluster_size is not None:
        max_cluster_size = validate_positive_int(
            max_cluster_size, "max_cluster_size", min_value=1, max_value=100
        )

    if duplicate_threshold is not None:
        duplicate_threshold = validate_score(duplicate_threshold, "duplicate_threshold")

    config = get_config()

    cluster_config = ClusterConfig(
        strategy=strategy,
        threshold=threshold or config.cluster_link_threshold,
        max_cluster_size=max_cluster_size or config.cluster_max_size,
        use_embeddings=config.enable_embeddings,
    )

    memories = db.list_memories(status=MemoryStatus.ACTIVE)

    if find_duplicates:
        dup_threshold = duplicate_threshold or config.semantic_hi
        duplicates = find_duplicate_candidates(memories, dup_threshold)
        return {
            "success": True,
            "mode": "duplicate_detection",
            "duplicates_found": len(duplicates),
            "duplicates": [
                {
                    "id1": d[0].id,
                    "id2": d[1].id,
                    "content1_preview": d[0].content[:100],
                    "content2_preview": d[1].content[:100],
                    "similarity": round(d[2], 4),
                }
                for d in duplicates[:20]
            ],
            "message": f"Found {len(duplicates)} potential duplicate pairs",
        }

    clusters = cluster_memories_simple(memories, cluster_config)

    return {
        "success": True,
        "mode": "clustering",
        "clusters_found": len(clusters),
        "strategy": strategy,
        "threshold": cluster_config.threshold,
        "clusters": [
            {
                "id": cluster.id,
                "size": len(cluster.memories),
                "cohesion": round(cluster.cohesion, 4),
                "suggested_action": cluster.suggested_action,
                "memory_ids": [m.id for m in cluster.memories],
                "content_previews": [m.content[:80] for m in cluster.memories[:3]],
            }
            for cluster in clusters[:20]
        ],
        "message": f"Found {len(clusters)} clusters using {strategy} strategy",
    }
