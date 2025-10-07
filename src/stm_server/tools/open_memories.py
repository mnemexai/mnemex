"""Open memories tool - retrieve specific memories by ID."""

import time
from typing import Any

from mcp.server import Server

from ..core.decay import calculate_score
from ..storage.jsonl_storage import JSONLStorage


async def open_memories_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle open memories requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary with requested memories
    """
    memory_ids = arguments["memory_ids"]
    include_relations = arguments.get("include_relations", True)
    include_scores = arguments.get("include_scores", True)

    # Ensure memory_ids is a list
    if isinstance(memory_ids, str):
        memory_ids = [memory_ids]

    # Retrieve memories
    memories = []
    not_found = []
    now = int(time.time())

    for memory_id in memory_ids:
        memory = db.get_memory(memory_id)

        if memory is None:
            not_found.append(memory_id)
            continue

        mem_data = {
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
            # Get relations from and to this memory
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

    return {
        "success": True,
        "count": len(memories),
        "memories": memories,
        "not_found": not_found,
    }


def register(server: Server, db: JSONLStorage) -> None:
    """Register the open memories tool with the MCP server."""

    @server.call_tool()
    async def open_memories(arguments: dict[str, Any]) -> list[Any]:
        """
        Retrieve specific memories by their IDs.

        Similar to the reference MCP memory server's open_nodes functionality.
        Returns detailed information about the requested memories including
        their relations to other memories.

        Args:
            memory_ids: Single memory ID (string) or list of memory IDs to retrieve (required)
            include_relations: Include relations from/to these memories (default: true)
            include_scores: Include decay scores and age (default: true)

        Returns:
            Detailed information about the requested memories with relations
        """
        result = await open_memories_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
