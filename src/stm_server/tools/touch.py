"""Touch memory tool - reinforce a memory by updating its access time."""

import time
from typing import Any

from mcp.server import Server

from ..core.decay import calculate_score
from ..storage.jsonl_storage import JSONLStorage


async def touch_memory_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle touch memory requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    memory_id = arguments["memory_id"]
    boost_strength = arguments.get("boost_strength", False)

    # Get existing memory
    memory = db.get_memory(memory_id)

    if memory is None:
        return {
            "success": False,
            "message": f"Memory not found: {memory_id}",
        }

    # Calculate current score
    now = int(time.time())
    old_score = calculate_score(
        use_count=memory.use_count,
        last_used=memory.last_used,
        strength=memory.strength,
        now=now,
    )

    # Update memory
    new_use_count = memory.use_count + 1
    new_strength = memory.strength
    if boost_strength:
        # Boost strength slightly (max 2.0)
        new_strength = min(2.0, memory.strength + 0.1)

    db.update_memory(
        memory_id=memory_id,
        last_used=now,
        use_count=new_use_count,
        strength=new_strength,
    )

    # Calculate new score
    new_score = calculate_score(
        use_count=new_use_count,
        last_used=now,
        strength=new_strength,
        now=now,
    )

    return {
        "success": True,
        "memory_id": memory_id,
        "old_score": round(old_score, 4),
        "new_score": round(new_score, 4),
        "use_count": new_use_count,
        "strength": new_strength,
        "message": f"Memory reinforced. Score: {old_score:.2f} -> {new_score:.2f}",
    }


def register(server: Server, db: JSONLStorage) -> None:
    """Register the touch memory tool with the MCP server."""

    @server.call_tool()
    async def touch_memory(arguments: dict[str, Any]) -> list[Any]:
        """
        Reinforce a memory by updating its last accessed time and use count.

        This resets the temporal decay and increases the memory's resistance to
        being forgotten. Optionally can boost the memory's base strength.

        Args:
            memory_id: ID of the memory to reinforce (required)
            boost_strength: Whether to boost the base strength (default: false)

        Returns:
            Updated memory statistics including old and new scores
        """
        result = await touch_memory_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
