"""Tool for observing and reinforcing memory usage in conversation."""

from typing import Any

from ..config import get_config
from ..context import db, mcp
from ..core.review import detect_cross_domain_usage, reinforce_memory


@mcp.tool()
def observe_memory_usage(
    memory_ids: list[str],
    context_tags: list[str] | None = None,
) -> dict[str, Any]:
    """Record that memories were actively used in conversation.

    This tool should be called when memories are actually incorporated into
    responses, not just retrieved. It enables natural spaced repetition by
    reinforcing memories through usage.

    The system automatically:
    - Updates last_used timestamp and use_count
    - Increments review_count
    - Detects cross-domain usage (valuable for retention)
    - Potentially boosts strength for cross-domain usage

    Args:
        memory_ids: IDs of memories that were used
        context_tags: Optional tags representing current conversation context
                     (used to detect cross-domain usage)

    Returns:
        Dictionary with reinforcement results

    Example:
        User asks about "authentication in the API"
        System retrieves memories about JWT preferences and API structure
        System uses those memories to answer
        System calls: observe_memory_usage(
            memory_ids=["jwt_pref_123", "api_struct_456"],
            context_tags=["api", "authentication", "backend"]
        )
    """
    config = get_config()

    if not config.auto_reinforce:
        return {
            "reinforced": False,
            "reason": "auto_reinforce is disabled in config",
            "count": 0,
        }

    if not memory_ids:
        return {
            "reinforced": False,
            "reason": "no memory_ids provided",
            "count": 0,
        }

    context_tags = context_tags or []

    reinforced_count = 0
    cross_domain_count = 0
    results: list[dict[str, Any]] = []

    for mem_id in memory_ids:
        # Get memory
        memory = db.get_memory(mem_id)
        if not memory:
            results.append(
                {
                    "id": mem_id,
                    "status": "not_found",
                }
            )
            continue

        # Detect cross-domain usage
        is_cross_domain = detect_cross_domain_usage(memory, context_tags)

        # Reinforce
        updated = reinforce_memory(memory, cross_domain=is_cross_domain)

        # Save
        db.update_memory(
            memory_id=mem_id,
            last_used=updated.last_used,
            use_count=updated.use_count,
            strength=updated.strength,
            last_review_at=updated.last_review_at,
            review_count=updated.review_count,
            cross_domain_count=updated.cross_domain_count,
        )

        reinforced_count += 1
        if is_cross_domain:
            cross_domain_count += 1

        results.append(
            {
                "id": mem_id,
                "status": "reinforced",
                "cross_domain": is_cross_domain,
                "new_use_count": updated.use_count,
                "new_review_count": updated.review_count,
                "strength": updated.strength,
            }
        )

    return {
        "reinforced": True,
        "count": reinforced_count,
        "cross_domain_count": cross_domain_count,
        "results": results,
    }
