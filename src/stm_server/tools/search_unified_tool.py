"""MCP tool wrapper for unified STM+LTM search."""

from typing import Any

from mcp.server import Server
from mcp.types import Tool

from ..storage.jsonl_storage import JSONLStorage
from .search_unified import format_results, search_unified


def register(server: Server, db: JSONLStorage) -> None:
    """Register the unified search tool with the MCP server."""

    @server.call_tool()
    async def search_unified_tool(arguments: dict[str, Any]) -> list[Any]:
        """
        Search across STM (JSONL) and LTM (Obsidian vault index) with unified ranking.

        Args:
            query: Text query (optional if tags provided)
            tags: List of tags to filter by (optional)
            limit: Maximum number of results (default: 10)
            stm_weight: Weight multiplier for STM results (default: 1.0)
            ltm_weight: Weight multiplier for LTM results (default: 0.7)
            window_days: Only include STM memories from last N days (optional)
            min_score: Minimum STM score threshold (optional)
            verbose: Include metadata fields in output (optional)

        Returns:
            Formatted result list as a single text block.
        """
        results = search_unified(
            query=arguments.get("query"),
            tags=arguments.get("tags"),
            limit=arguments.get("limit", 10),
            stm_weight=arguments.get("stm_weight", 1.0),
            ltm_weight=arguments.get("ltm_weight", 0.7),
            window_days=arguments.get("window_days"),
            min_score=arguments.get("min_score"),
        )

        text = format_results(results, verbose=bool(arguments.get("verbose", False)))
        return [{"type": "text", "text": text}]

    # Add tool metadata
    tools = getattr(server, "list_tools", lambda: [])()
    tools.append(
        Tool(
            name="search_unified",
            description="Search across STM and LTM with unified ranking and deduplication.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags",
                    },
                    "limit": {"type": "integer", "default": 10},
                    "stm_weight": {"type": "number", "default": 1.0},
                    "ltm_weight": {"type": "number", "default": 0.7},
                    "window_days": {"type": "integer"},
                    "min_score": {"type": "number"},
                    "verbose": {"type": "boolean", "default": False},
                },
            },
        )
    )
    server.list_tools = lambda: tools
