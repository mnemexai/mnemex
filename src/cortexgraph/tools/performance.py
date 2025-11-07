"""Performance monitoring tool for Mnemex."""

from typing import Any

from ..context import mcp
from ..performance import get_performance_stats, reset_metrics


@mcp.tool()
def get_performance_metrics() -> dict[str, Any]:
    """
    Get current performance metrics and statistics.

    Returns:
        Dictionary containing performance statistics for various operations.
    """
    return get_performance_stats()


@mcp.tool()
def reset_performance_metrics() -> dict[str, Any]:
    """
    Reset all performance metrics and return confirmation.

    Returns:
        Dictionary confirming metrics have been reset.
    """
    reset_metrics()
    return {"success": True, "message": "Performance metrics have been reset"}
