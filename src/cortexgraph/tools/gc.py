"""Garbage collection tool - remove or archive low-scoring memories."""

import time
from typing import Any

from ..config import get_config
from ..context import db, mcp
from ..core.scoring import should_forget
from ..security.validators import validate_positive_int
from ..storage.models import GarbageCollectionResult, MemoryStatus


@mcp.tool()
def gc(
    dry_run: bool = True,
    archive_instead: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Remove or archive low-scoring memories.

    Args:
        dry_run: Preview without removing.
        archive_instead: Archive instead of deleting.
        limit: Max memories to process (1-10,000).

    Returns:
        Dict with removed_count, archived_count, freed_score_sum, memory_ids.

    Raises:
        ValueError: Invalid limit range.
    """
    # Input validation
    if limit is not None:
        limit = validate_positive_int(limit, "limit", min_value=1, max_value=10000)

    config = get_config()
    now = int(time.time())

    memories = db.list_memories(status=MemoryStatus.ACTIVE)

    to_remove = []
    total_score_removed = 0.0
    for memory in memories:
        should_delete, score = should_forget(memory, now)
        if should_delete:
            to_remove.append((memory, score))
            total_score_removed += score

    to_remove.sort(key=lambda x: x[1])

    if limit and len(to_remove) > limit:
        to_remove = to_remove[:limit]
        total_score_removed = sum(score for _, score in to_remove)

    removed_count = 0
    archived_count = 0
    memory_ids = []

    if not dry_run:
        for memory, _score in to_remove:
            memory_ids.append(memory.id)
            if archive_instead:
                db.update_memory(memory_id=memory.id, status=MemoryStatus.ARCHIVED)
                archived_count += 1
            else:
                db.delete_memory(memory.id)
                removed_count += 1
    else:
        memory_ids = [memory.id for memory, _ in to_remove]
        if archive_instead:
            archived_count = len(to_remove)
        else:
            removed_count = len(to_remove)

    result = GarbageCollectionResult(
        removed_count=removed_count,
        archived_count=archived_count,
        freed_score_sum=total_score_removed,
        memory_ids=memory_ids,
    )

    return {
        "success": True,
        "dry_run": dry_run,
        "removed_count": result.removed_count,
        "archived_count": result.archived_count,
        "freed_score_sum": round(result.freed_score_sum, 4),
        "memory_ids": result.memory_ids[:10],
        "total_affected": len(result.memory_ids),
        "message": (
            f"{'Would remove' if dry_run else 'Removed'} {len(result.memory_ids)} "
            f"low-scoring memories (threshold: {config.forget_threshold})"
        ),
    }
