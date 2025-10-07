"""Cluster memory tool - find similar memories for consolidation."""

from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import Tool

from ..config import get_config
from ..core.clustering import cluster_memories_simple, find_duplicate_candidates
from ..storage.database import Database
from ..storage.models import ClusterConfig, MemoryStatus


async def cluster_handler(db: Database, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle memory clustering requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    strategy = arguments.get("strategy", "similarity")
    threshold = arguments.get("threshold")
    max_cluster_size = arguments.get("max_cluster_size")
    find_duplicates = arguments.get("find_duplicates", False)

    config = get_config()

    # Build cluster configuration
    cluster_config = ClusterConfig(
        strategy=strategy,
        threshold=threshold or config.cluster_link_threshold,
        max_cluster_size=max_cluster_size or config.cluster_max_size,
        use_embeddings=config.enable_embeddings,
    )

    # Get active memories
    memories = db.list_memories(status=MemoryStatus.ACTIVE)

    if find_duplicates:
        # Find likely duplicate pairs
        duplicate_threshold = arguments.get("duplicate_threshold", config.semantic_hi)
        duplicates = find_duplicate_candidates(memories, duplicate_threshold)

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
                for d in duplicates[:20]  # Show first 20
            ],
            "message": f"Found {len(duplicates)} potential duplicate pairs",
        }

    # Perform clustering
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
            for cluster in clusters[:20]  # Show first 20
        ],
        "message": f"Found {len(clusters)} clusters using {strategy} strategy",
    }


def register(server: Server, db: Database) -> None:
    """Register the cluster memory tool with the MCP server."""

    @server.call_tool()
    async def cluster_memories(arguments: Dict[str, Any]) -> List[Any]:
        """
        Cluster similar memories for potential consolidation.

        Groups similar memories together based on semantic similarity (if embeddings
        are enabled) or other clustering strategies. Useful for identifying
        redundant or related memories that could be merged.

        Args:
            strategy: Clustering strategy (default: "similarity")
            threshold: Similarity threshold for linking (optional, uses config default)
            max_cluster_size: Maximum memories per cluster (optional, uses config default)
            find_duplicates: Find likely duplicate pairs instead of clustering (default: false)
            duplicate_threshold: Similarity threshold for duplicates (optional, uses semantic_hi)

        Returns:
            List of clusters with cohesion scores and suggested actions
        """
        result = await cluster_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
