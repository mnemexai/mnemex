"""Promote memory tool - move high-value memories to long-term storage."""

import time
from typing import Any

from mcp.server import Server

from ..core.scoring import calculate_memory_age, should_promote
from ..integration.basic_memory import BasicMemoryIntegration
from ..storage.jsonl_storage import JSONLStorage
from ..storage.models import MemoryStatus, PromotionCandidate


async def promote_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle memory promotion requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    memory_id = arguments.get("memory_id")
    auto_detect = arguments.get("auto_detect", False)
    dry_run = arguments.get("dry_run", False)
    target = arguments.get("target", "obsidian")

    # thresholds are read in should_promote; no direct config use here
    now = int(time.time())

    promoted_ids = []
    candidates = []

    if memory_id:
        # Promote specific memory
        memory = db.get_memory(memory_id)
        if memory is None:
            return {
                "success": False,
                "message": f"Memory not found: {memory_id}",
            }

        # Check if already promoted
        if memory.status == MemoryStatus.PROMOTED:
            return {
                "success": False,
                "message": f"Memory already promoted: {memory_id}",
                "promoted_to": memory.promoted_to,
            }

        promote_it, reason, score = should_promote(memory, now)

        if not promote_it and not arguments.get("force", False):
            return {
                "success": False,
                "message": f"Memory does not meet promotion criteria: {reason}",
                "score": round(score, 4),
            }

        candidates = [
            PromotionCandidate(
                memory=memory,
                reason=reason,
                score=score,
                use_count=memory.use_count,
                age_days=calculate_memory_age(memory, now),
            )
        ]

    elif auto_detect:
        # Auto-detect promotion candidates
        memories = db.list_memories(status=MemoryStatus.ACTIVE)

        for memory in memories:
            promote_it, reason, score = should_promote(memory, now)
            if promote_it:
                candidates.append(
                    PromotionCandidate(
                        memory=memory,
                        reason=reason,
                        score=score,
                        use_count=memory.use_count,
                        age_days=calculate_memory_age(memory, now),
                    )
                )

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)

    else:
        return {
            "success": False,
            "message": "Must specify memory_id or set auto_detect=true",
        }

    # Perform promotion if not dry run
    if not dry_run and candidates:
        integration = BasicMemoryIntegration()

        for candidate in candidates:
            # Promote to target
            if target == "obsidian":
                result = integration.promote_to_obsidian(candidate.memory)
            else:
                return {
                    "success": False,
                    "message": f"Unknown target: {target}",
                }

            if result["success"]:
                # Mark as promoted in database
                db.update_memory(
                    memory_id=candidate.memory.id,
                    status=MemoryStatus.PROMOTED,
                    promoted_at=now,
                    promoted_to=result.get("path"),
                )
                promoted_ids.append(candidate.memory.id)

    return {
        "success": True,
        "dry_run": dry_run,
        "candidates_found": len(candidates),
        "promoted_count": len(promoted_ids),
        "promoted_ids": promoted_ids,
        "candidates": [
            {
                "id": c.memory.id,
                "content_preview": c.memory.content[:100],
                "reason": c.reason,
                "score": round(c.score, 4),
                "use_count": c.use_count,
                "age_days": round(c.age_days, 1),
            }
            for c in candidates[:10]  # Show first 10
        ],
        "message": (
            f"{'Would promote' if dry_run else 'Promoted'} {len(promoted_ids)} memories to {target}"
        ),
    }


def register(server: Server, db: JSONLStorage) -> None:
    """Register the promote memory tool with the MCP server."""

    @server.call_tool()
    async def promote_memory(arguments: dict[str, Any]) -> list[Any]:
        """
        Promote high-value memories to long-term storage.

        Memories that have high scores or frequent usage are promoted to the
        Obsidian vault (or other long-term storage) where they become permanent.

        Args:
            memory_id: Specific memory ID to promote (optional)
            auto_detect: Automatically detect promotion candidates (default: false)
            dry_run: Preview what would be promoted without promoting (default: false)
            target: Target for promotion (default: "obsidian")
            force: Force promotion even if criteria not met (default: false)

        Returns:
            List of promoted memories and promotion statistics
        """
        result = await promote_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
