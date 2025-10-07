"""Create relation tool - link memories explicitly."""

import time
import uuid
from typing import Any

from mcp.server import Server

from ..storage.jsonl_storage import JSONLStorage
from ..storage.models import Relation


async def create_relation_handler(db: JSONLStorage, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Handle create relation requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary
    """
    from_id = arguments["from_memory_id"]
    to_id = arguments["to_memory_id"]
    relation_type = arguments["relation_type"]
    strength = arguments.get("strength", 1.0)
    metadata = arguments.get("metadata", {})

    # Verify both memories exist
    from_memory = db.get_memory(from_id)
    to_memory = db.get_memory(to_id)

    if from_memory is None:
        return {
            "success": False,
            "message": f"Source memory not found: {from_id}",
        }

    if to_memory is None:
        return {
            "success": False,
            "message": f"Target memory not found: {to_id}",
        }

    # Check for duplicate relation
    existing = db.get_relations(
        from_memory_id=from_id,
        to_memory_id=to_id,
        relation_type=relation_type,
    )

    if existing:
        return {
            "success": False,
            "message": f"Relation already exists: {existing[0].id}",
            "existing_relation_id": existing[0].id,
        }

    # Create relation
    relation_id = str(uuid.uuid4())
    relation = Relation(
        id=relation_id,
        from_memory_id=from_id,
        to_memory_id=to_id,
        relation_type=relation_type,
        strength=strength,
        created_at=int(time.time()),
        metadata=metadata,
    )

    db.create_relation(relation)

    return {
        "success": True,
        "relation_id": relation_id,
        "from": from_id,
        "to": to_id,
        "type": relation_type,
        "strength": strength,
        "message": f"Relation created: {from_id} --[{relation_type}]--> {to_id}",
    }


def register(server: Server, db: JSONLStorage) -> None:
    """Register the create relation tool with the MCP server."""

    @server.call_tool()
    async def create_relation(arguments: dict[str, Any]) -> list[Any]:
        """
        Create an explicit relation between two memories.

        Similar to the reference MCP memory server's create_relations functionality.
        Links two memories with a typed relationship. Useful for tracking how
        memories relate to each other (references, follows_from, contradicts, etc.).

        Args:
            from_memory_id: Source memory ID (required)
            to_memory_id: Target memory ID (required)
            relation_type: Type of relation (e.g., "references", "follows_from", "similar_to") (required)
            strength: Strength of the relation (0.0-1.0, default: 1.0)
            metadata: Additional metadata about the relation (optional)

        Returns:
            Created relation ID and confirmation
        """
        result = await create_relation_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
