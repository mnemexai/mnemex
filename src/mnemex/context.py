"""Shared context for Mnemex."""

from mcp.server.fastmcp import FastMCP

from .storage.jsonl_storage import JSONLStorage

# Create the FastMCP server instance
mcp = FastMCP(
    name="mnemex",
)

# Create the database instance
db = JSONLStorage()
