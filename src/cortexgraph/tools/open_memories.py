"""Open memories tool - retrieve specific memories by ID."""

import time
from typing import Any

from ..context import db, mcp
from ..core.decay import calculate_score
from ..core.pagination import paginate_list, validate_pagination_params
from ..security.validators import MAX_LIST_LENGTH, validate_list_length, validate_uuid


@mcp.tool()
def open_memories(
    memory_ids: str | list[str],
    include_relations: bool = True,
    include_scores: bool = True,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """Retrieve specific memories by IDs with detailed information.

    Args:
        memory_ids: Single ID or list of IDs (max 100).
        include_relations: Include outgoing/incoming relations.
        include_scores: Include decay scores and age.
        page: Page number (1-indexed).
        page_size: Memories per page (max 100).

    Returns:
        Dict with memories, not_found IDs, and pagination metadata.

    Raises:
        ValueError: If memory ID invalid or list exceeds max length.
    """
    # Input validation
    ids = [memory_ids] if isinstance(memory_ids, str) else memory_ids

    if not isinstance(ids, list):
        raise ValueError(f"memory_ids must be a string or list, got {type(ids).__name__}")

    ids = validate_list_length(ids, MAX_LIST_LENGTH, "memory_ids")
    ids = [validate_uuid(mid, f"memory_ids[{i}]") for i, mid in enumerate(ids)]

    # Only validate pagination if explicitly requested
    pagination_requested = page is not None or page_size is not None

    memories = []
    not_found = []
    now = int(time.time())

    for memory_id in ids:
        memory = db.get_memory(memory_id)
        if memory is None:
            not_found.append(memory_id)
            continue

        mem_data: dict[str, Any] = {
            "id": memory.id,
            "content": memory.content,
            "entities": memory.entities,
            "tags": memory.meta.tags,
            "source": memory.meta.source,
            "context": memory.meta.context,
            "created_at": memory.created_at,
            "last_used": memory.last_used,
            "use_count": memory.use_count,
            "strength": memory.strength,
            "status": memory.status.value,
            "promoted_at": memory.promoted_at,
            "promoted_to": memory.promoted_to,
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

        if include_relations:
            relations_from = db.get_relations(from_memory_id=memory_id)
            relations_to = db.get_relations(to_memory_id=memory_id)
            mem_data["relations"] = {
                "outgoing": [
                    {
                        "to": r.to_memory_id,
                        "type": r.relation_type,
                        "strength": round(r.strength, 4),
                    }
                    for r in relations_from
                ],
                "incoming": [
                    {
                        "from": r.from_memory_id,
                        "type": r.relation_type,
                        "strength": round(r.strength, 4),
                    }
                    for r in relations_to
                ],
            }

        memories.append(mem_data)

    # Apply pagination only if requested
    if pagination_requested:
        # Validate and get non-None values
        valid_page, valid_page_size = validate_pagination_params(page, page_size)
        paginated_memories = paginate_list(memories, page=valid_page, page_size=valid_page_size)
        return {
            "success": True,
            "count": len(paginated_memories.items),
            "memories": paginated_memories.items,
            "not_found": not_found,
            "pagination": paginated_memories.to_dict(),
        }
    else:
        # No pagination - return all memories
        return {
            "success": True,
            "count": len(memories),
            "memories": memories,
            "not_found": not_found,
        }
