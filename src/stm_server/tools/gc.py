"""Garbage collection tool - remove or archive low-scoring memories."""

import time
from typing import Any

from mcp.server import Server

from ..config import get_config
from ..core.scoring import should_forget
from ..storage.jsonl_storage import JSONLStorage
from ..storage.models import GarbageCollectionResult, MemoryStatus


async def gc_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle garbage collection requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    dry_run = arguments.get("dry_run", True)
    archive_instead = arguments.get("archive_instead", False)
    limit = arguments.get("limit")

    config = get_config()
    now = int(time.time())

    # Get all active memories
    memories = db.list_memories(status=MemoryStatus.ACTIVE)

    # Find memories that should be forgotten
    to_remove = []
    total_score_removed = 0.0

    for memory in memories:
        should_delete, score = should_forget(memory, now)
        if should_delete:
            to_remove.append((memory, score))
            total_score_removed += score

    # Sort by score (remove lowest scoring first)
    to_remove.sort(key=lambda x: x[1])

    # Apply limit if specified
    if limit and len(to_remove) > limit:
        to_remove = to_remove[:limit]
        total_score_removed = sum(score for _, score in to_remove)

    removed_count = 0
    archived_count = 0
    memory_ids = []

    # Perform removal/archival if not dry run
    if not dry_run:
        for memory, _score in to_remove:
            memory_ids.append(memory.id)
            if archive_instead:
                # Archive instead of delete
                db.update_memory(
                    memory_id=memory.id,
                    status=MemoryStatus.ARCHIVED,
                )
                archived_count += 1
            else:
                # Delete permanently
                db.delete_memory(memory.id)
                removed_count += 1
    else:
        # Dry run - just collect IDs
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
        "memory_ids": result.memory_ids[:10],  # Show first 10
        "total_affected": len(result.memory_ids),
        "message": (
            f"{'Would remove' if dry_run else 'Removed'} {len(result.memory_ids)} "
            f"low-scoring memories (threshold: {config.forget_threshold})"
        ),
    }


def register(server: Server, db: JSONLStorage) -> None:
    """Register the garbage collection tool with the MCP server."""

    @server.call_tool()
    async def gc(arguments: dict[str, Any]) -> list[Any]:
        """
        Perform garbage collection on low-scoring memories.

        Removes or archives memories whose decay score has fallen below the
        forget threshold. This prevents the database from growing indefinitely
        with unused memories.

        Args:
            dry_run: Preview what would be removed without actually removing (default: true)
            archive_instead: Archive memories instead of deleting (default: false)
            limit: Maximum number of memories to process (optional)

        Returns:
            Statistics about removed/archived memories
        """
        result = await gc_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
