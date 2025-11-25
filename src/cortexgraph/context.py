"""Shared context for CortexGraph."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .storage.jsonl_storage import JSONLStorage

# Create the FastMCP server instance
mcp = FastMCP(
    name="cortexgraph",
)

# Create the database instance (lazy initialization available via get_db())
_db: JSONLStorage | None = None


def get_db() -> JSONLStorage:
    """Get the storage instance (lazy initialization).

    Returns:
        Configured JSONLStorage instance

    Note:
        This getter pattern allows agents to be imported without
        immediately initializing storage, improving testability.
    """
    global _db
    if _db is None:
        _db = JSONLStorage()
    return _db


# Legacy: keep `db` for backwards compatibility with existing code
# that imports `from cortexgraph.context import db`
db = JSONLStorage()
