"""Shared context for CortexGraph."""

from mcp.server.fastmcp import FastMCP

from .storage.jsonl_storage import JSONLStorage

# Create the FastMCP server instance
mcp = FastMCP(
    name="cortexgraph",
)

# Create the database instance
db = JSONLStorage()
