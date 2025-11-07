"""Consolidate memory tool - algorithmic memory merging with preview."""

from typing import Any

from ..context import db, mcp
from ..core.clustering import cluster_memories_simple
from ..core.consolidation import execute_consolidation, generate_consolidation_preview
from ..security.validators import validate_score, validate_uuid
from ..storage.models import ClusterConfig, MemoryStatus


@mcp.tool()
def consolidate_memories(
    cluster_id: str | None = None,
    mode: str = "preview",
    auto_detect: bool = False,
    cohesion_threshold: float = 0.75,
) -> dict[str, Any]:
    """
    Consolidate similar memories using algorithmic merging.

    This tool intelligently merges similar memories by:
    1. Combining content (preserving unique information)
    2. Merging tags and entities (union)
    3. Calculating appropriate strength based on cohesion
    4. Preserving earliest created_at and latest last_used timestamps

    Modes:
    - "preview": Generate merge preview without making changes
    - "apply": Execute the consolidation (requires cluster_id)

    Args:
        cluster_id: Specific cluster ID to consolidate (valid UUID, required for apply mode).
        mode: Operation mode - "preview" or "apply".
        auto_detect: If True, automatically find high-cohesion clusters.
        cohesion_threshold: Minimum cohesion for auto-detection (0.0-1.0, default: 0.75).

    Returns:
        Consolidation preview or execution results.

    Raises:
        ValueError: If cluster_id is invalid or cohesion_threshold is out of range.
    """
    # Input validation
    if cluster_id is not None:
        cluster_id = validate_uuid(cluster_id, "cluster_id")

    cohesion_threshold = validate_score(cohesion_threshold, "cohesion_threshold")

    if mode not in ("preview", "apply"):
        raise ValueError(f"mode must be 'preview' or 'apply', got: {mode}")

    # Auto-detect mode: find clusters worth consolidating
    if auto_detect:
        memories = db.list_memories(status=MemoryStatus.ACTIVE)

        # Create cluster config
        cluster_config = ClusterConfig(
            strategy="similarity",
            threshold=cohesion_threshold,
            max_cluster_size=12,
            min_cluster_size=2,
            use_embeddings=True,
        )

        clusters = cluster_memories_simple(memories, cluster_config)

        # Filter to high-cohesion clusters worth consolidating
        candidates = [c for c in clusters if c.cohesion >= cohesion_threshold]

        if mode == "preview":
            # Show top candidates
            previews = []
            for cluster in candidates[:5]:  # Top 5 candidates
                preview = generate_consolidation_preview(cluster)
                previews.append(preview)

            return {
                "success": True,
                "mode": "auto_detect_preview",
                "candidates_found": len(candidates),
                "showing": len(previews),
                "previews": previews,
                "message": f"Found {len(candidates)} clusters ready for consolidation",
            }
        else:
            # Apply consolidation to all candidates
            results = []
            for cluster in candidates:
                result = execute_consolidation(cluster, db, centroid_embedding=cluster.centroid)
                results.append(result)

            total_saved = sum(r.get("space_saved", 0) for r in results)

            return {
                "success": True,
                "mode": "auto_detect_apply",
                "consolidated_clusters": len(results),
                "total_memories_saved": total_saved,
                "results": results,
                "message": f"Consolidated {len(results)} clusters, saved {total_saved} memory slots",
            }

    # Specific cluster mode
    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required when auto_detect is False",
            "hint": "Use auto_detect=True to find clusters automatically",
        }

    # Find the cluster (need to re-cluster to get the cluster object)
    memories = db.list_memories(status=MemoryStatus.ACTIVE)
    cluster_config = ClusterConfig(
        strategy="similarity",
        threshold=0.75,
        max_cluster_size=12,
        min_cluster_size=2,
        use_embeddings=True,
    )

    clusters = cluster_memories_simple(memories, cluster_config)
    target_cluster = next((c for c in clusters if c.id == cluster_id), None)

    if not target_cluster:
        return {
            "success": False,
            "error": f"Cluster {cluster_id} not found",
            "hint": "Cluster IDs change on each run. Use auto_detect or get fresh cluster IDs from cluster_memories tool",
        }

    if mode == "preview":
        preview = generate_consolidation_preview(target_cluster)
        return {
            "success": True,
            "mode": "preview",
            **preview,
        }

    elif mode == "apply":
        result = execute_consolidation(
            target_cluster, db, centroid_embedding=target_cluster.centroid
        )
        return {
            "success": True,
            "mode": "apply",
            **result,
        }

    else:
        return {
            "success": False,
            "error": f"Unknown mode: {mode}",
            "valid_modes": ["preview", "apply"],
        }
