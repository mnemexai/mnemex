"""Shared storage utilities for agents.

This module provides common utilities for agent access to the storage layer,
separated for testability and to avoid duplication across agents.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortexgraph.storage.jsonl_storage import JSONLStorage


def get_storage() -> "JSONLStorage":
    """Get storage instance. Separated for testability.

    Returns:
        JSONLStorage instance from the global context.
    """
    from cortexgraph.context import get_db

    return get_db()
