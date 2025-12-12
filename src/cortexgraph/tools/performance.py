"""Performance monitoring tool for Mnemex."""

from typing import Any

from ..context import mcp
from ..performance import get_performance_stats, reset_metrics


@mcp.tool()
def get_performance_metrics() -> dict[str, Any]:
    """Get current performance metrics.

    Returns:
        Dict with: operation stats, counts, timings.
    """
    return get_performance_stats()


@mcp.tool()
def reset_performance_metrics() -> dict[str, Any]:
    """Reset all performance metrics.

    Returns:
        Dict with: success, message.
    """
    reset_metrics()
    return {"success": True, "message": "Performance metrics have been reset"}
