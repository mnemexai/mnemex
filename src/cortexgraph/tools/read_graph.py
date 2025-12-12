"""Read graph tool - return entire knowledge graph."""

import time
from typing import Any

from ..context import db, mcp
from ..core.decay import calculate_score
from ..core.pagination import paginate_list, validate_pagination_params
from ..security.validators import validate_positive_int
from ..storage.models import MemoryStatus


@mcp.tool()
def read_graph(
    status: str = "active",
    include_scores: bool = True,
    limit: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """Return entire knowledge graph with memories and relations.

    Args:
        status: "active", "promoted", "archived", or "all".
        include_scores: Include decay scores and age.
        limit: Max memories (1-10,000).
        page: Page number (1-indexed).
        page_size: Memories per page (max 100).

    Returns:
        Dict with memories, relations, stats, and pagination metadata.

    Raises:
        ValueError: If status invalid or limit out of range.
    """
    # Input validation
    valid_statuses = {"active", "promoted", "archived", "all"}
    if status not in valid_statuses:
        raise ValueError(f"status must be one of {valid_statuses}, got: {status}")

    if limit is not None:
        limit = validate_positive_int(limit, "limit", min_value=1, max_value=10000)

    # Only validate pagination if explicitly requested
    pagination_requested = page is not None or page_size is not None

    status_filter = None if status == "all" else MemoryStatus(status)
    graph = db.get_knowledge_graph(status=status_filter)

    if limit and limit > 0:
        graph.memories = graph.memories[:limit]
        graph.stats["limited_to"] = limit

    now = int(time.time())
    memories_data = []
    for memory in graph.memories:
        mem_data = {
            "id": memory.id,
            "content": memory.content,
            "entities": memory.entities,
            "tags": memory.meta.tags,
            "created_at": memory.created_at,
            "last_used": memory.last_used,
            "use_count": memory.use_count,
            "strength": memory.strength,
            "status": memory.status.value,
        }
        if include_scores:
            score = calculate_score(
                use_count=memory.use_count,
                last_used=memory.last_used,
                strength=memory.strength,
                now=now,
            )
            mem_data["score"] = round(score, 4)
            mem_data["age_days"] = round((now - memory.created_at) / 86400, 1)
        memories_data.append(mem_data)

    relations_data = [
        {
            "id": rel.id,
            "from": rel.from_memory_id,
            "to": rel.to_memory_id,
            "type": rel.relation_type,
            "strength": round(rel.strength, 4),
            "created_at": rel.created_at,
        }
        for rel in graph.relations
    ]

    # Apply pagination only if requested
    if pagination_requested:
        # Validate and get non-None values
        valid_page, valid_page_size = validate_pagination_params(page, page_size)
        paginated_memories = paginate_list(
            memories_data, page=valid_page, page_size=valid_page_size
        )
        return {
            "success": True,
            "memories": paginated_memories.items,
            "relations": relations_data,
            "stats": {
                "total_memories": graph.stats["total_memories"],
                "total_relations": graph.stats["total_relations"],
                "avg_score": round(graph.stats["avg_score"], 4),
                "avg_use_count": round(graph.stats["avg_use_count"], 2),
                "status_filter": graph.stats["status_filter"],
            },
            "pagination": paginated_memories.to_dict(),
        }
    else:
        # No pagination - return all memories
        return {
            "success": True,
            "memories": memories_data,
            "relations": relations_data,
            "stats": {
                "total_memories": graph.stats["total_memories"],
                "total_relations": graph.stats["total_relations"],
                "avg_score": round(graph.stats["avg_score"], 4),
                "avg_use_count": round(graph.stats["avg_use_count"], 2),
                "status_filter": graph.stats["status_filter"],
            },
        }
