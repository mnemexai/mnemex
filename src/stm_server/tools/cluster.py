"""Cluster memory tool - find similar memories for consolidation."""

from typing import Any, Optional

from ..config import get_config
from ..context import db, mcp
from ..core.clustering import cluster_memories_simple, find_duplicate_candidates
from ..storage.models import ClusterConfig, MemoryStatus


@mcp.tool()
def cluster_memories(
    strategy: str = "similarity",
    threshold: Optional[float] = None,
    max_cluster_size: Optional[int] = None,
    find_duplicates: bool = False,
    duplicate_threshold: Optional[float] = None,
) -> dict[str, Any]:
    """
    Cluster similar memories for potential consolidation or find duplicates.

    Groups similar memories based on semantic similarity (if embeddings are
    enabled) or other strategies. Useful for identifying redundant memories.

    Args:
        strategy: Clustering strategy (default: "similarity").
        threshold: Similarity threshold for linking (uses config default).
        max_cluster_size: Maximum memories per cluster (uses config default).
        find_duplicates: Find likely duplicate pairs instead of clustering.
        duplicate_threshold: Similarity threshold for duplicates (uses config default).

    Returns:
        List of clusters or duplicate pairs with scores and suggested actions.
    """
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
