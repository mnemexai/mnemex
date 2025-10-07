"""Read graph tool - return entire knowledge graph."""

import time
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import Tool

from ..core.decay import calculate_score
from ..storage.database import Database
from ..storage.models import MemoryStatus


async def read_graph_handler(db: Database, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle read graph requests.

    Args:
        db: Database instance
        arguments: Tool arguments

    Returns:
        Response dictionary with complete knowledge graph
    """
    status_filter = arguments.get("status", "active")
    include_scores = arguments.get("include_scores", True)
    limit = arguments.get("limit")

    # Parse status filter
    if status_filter == "all":
        status = None
    else:
        status = MemoryStatus(status_filter)

    # Get knowledge graph
    graph = db.get_knowledge_graph(status=status)

    # Apply limit if specified
    if limit and limit > 0:
        graph.memories = graph.memories[:limit]
        graph.stats["limited_to"] = limit

    # Build response
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


def register(server: Server, db: Database) -> None:
    """Register the read graph tool with the MCP server."""

    @server.call_tool()
    async def read_graph(arguments: Dict[str, Any]) -> List[Any]:
        """
        Read the entire knowledge graph of memories and relations.

        Returns the complete graph structure including all memories (with decay scores),
        all relations between memories, and statistics about the graph. This is similar
        to the reference MCP memory server's read_graph functionality.

        Args:
            status: Filter memories by status - "active", "promoted", "archived", or "all" (default: "active")
            include_scores: Include decay scores and age in results (default: true)
            limit: Maximum number of memories to return (optional)

        Returns:
            Complete knowledge graph with memories, relations, and statistics
        """
        result = await read_graph_handler(db, arguments)
        return [{"type": "text", "text": str(result)}]
