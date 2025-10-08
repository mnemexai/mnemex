"""Shared context for the STM server."""

from mcp.server.fastmcp import FastMCP
from .storage.jsonl_storage import JSONLStorage

# Create the FastMCP server instance
mcp = FastMCP(
    name="stm-server",
)

# Create the database instance
db = JSONLStorage()
