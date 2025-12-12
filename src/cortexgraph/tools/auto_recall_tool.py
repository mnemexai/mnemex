"""MCP tool for automatic memory recall and reinforcement.

This tool enables conversational memory by automatically searching for
and reinforcing related memories based on discussion topics.

Phase 1 (MVP): Silent reinforcement - no surfacing, just prevent decay
"""

from typing import Any

from cortexgraph.config import get_config
from cortexgraph.context import db, mcp
from cortexgraph.core.auto_recall import AutoRecallEngine, RecallMode


@mcp.tool()
def auto_recall_process_message(
    message: str,
) -> dict[str, Any]:
    """Automatically recall and reinforce memories related to message topics.

    Args:
        message: User message to analyze (non-empty string).

    Returns:
        Dict with success, enabled, topics_found, memories_found, memories_reinforced, mode, and message.

    Raises:
        ValueError: If message is empty or invalid.
    """
    config = get_config()

    # Check if auto-recall is enabled
    if not config.auto_recall_enabled:
        return {
            "success": True,
            "enabled": False,
            "topics_found": [],
            "memories_found": 0,
            "memories_reinforced": [],
            "mode": config.auto_recall_mode,
            "message": "Auto-recall is disabled in configuration",
        }

    # Validate message
    if not message or not isinstance(message, str) or not message.strip():
        raise ValueError("message cannot be empty")

    message = message.strip()

    # Initialize auto-recall engine
    mode = RecallMode(config.auto_recall_mode)
    engine = AutoRecallEngine(mode=mode)

    # Get storage
    storage = db

    # Process message
    result = engine.process_message(message, storage)

    return {
        "success": True,
        "enabled": True,
        "topics_found": result.topics_found,
        "memories_found": len(result.memories_found),
        "memories_reinforced": result.memories_reinforced,
        "mode": config.auto_recall_mode,
        "message": _generate_summary(result),
    }


def _generate_summary(result: Any) -> str:
    """Generate human-readable summary of auto-recall result.

    Args:
        result: RecallResult from engine

    Returns:
        Human-readable summary string
    """
    topics_count = len(result.topics_found)
    memories_count = len(result.memories_found)
    reinforced_count = len(result.memories_reinforced)

    if reinforced_count == 0:
        if topics_count == 0:
            return "No topics detected - message too short or simple"
        return f"Detected {topics_count} topic(s), but no related memories found"

    return (
        f"Auto-recall: Found {memories_count} related memories, "
        f"reinforced {reinforced_count} to prevent decay"
    )
