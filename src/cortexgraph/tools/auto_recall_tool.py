"""MCP tool for automatic memory recall and reinforcement.

This tool enables conversational memory by automatically searching for
and reinforcing related memories based on discussion topics.

Phase 1 (MVP): Silent reinforcement - no surfacing, just prevent decay
"""

from __future__ import annotations

from typing import Any

from cortexgraph.config import get_config
from cortexgraph.context import db, mcp
from cortexgraph.core.auto_recall import AutoRecallEngine, RecallMode


@mcp.tool()
def auto_recall_process_message(
    message: str,
) -> dict[str, Any]:
    """Process a message and automatically recall/reinforce related memories.

    This tool implements Phase 1 of auto-recall: silent reinforcement.
    When the user discusses topics, this tool:
    1. Analyzes the message for topics/entities
    2. Searches for related memories
    3. Automatically reinforces found memories (updates last_used, use_count)
    4. Returns statistics (no memory surfacing in Phase 1)

    **Usage**: Call this periodically during conversations to keep important
    memories from decaying. The LLM should call this when the user discusses
    substantive topics (not on simple commands/queries).

    **Phase 1 Behavior**: Silent mode - memories are reinforced but not
    surfaced to the conversation. This prevents decay while we tune
    surfacing strategies in later phases.

    Args:
        message: User message to analyze for recall opportunities

    Returns:
        Dictionary with:
        - success: bool
        - enabled: bool (is auto-recall enabled in config?)
        - topics_found: list[str] (topics extracted from message)
        - memories_found: int (count of related memories)
        - memories_reinforced: list[str] (IDs of reinforced memories)
        - mode: str (current mode: silent/subtle/interactive)
        - message: str (human-readable summary)

    Example:
        >>> result = auto_recall_process_message(
        ...     "I'm working on the STOPPER protocol implementation"
        ... )
        >>> result["memories_reinforced"]
        ["abc-123", "def-456"]  # IDs of STOPPER-related memories

    Raises:
        ValueError: If message is empty or invalid
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
