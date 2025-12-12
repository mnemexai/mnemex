"""Analyze message for recall activation.

Helper tool that analyzes user messages to detect recall requests and provide
suggested parameters for search_memory.

This is the recall counterpart to analyze_message (save activation).
Phase 1b Implementation (v0.6.0).
"""

import logging
from typing import Any

from ..config import get_config
from ..context import mcp
from ..performance import time_operation

logger = logging.getLogger(__name__)


@mcp.tool()
@time_operation("analyze_for_recall")
def analyze_for_recall(message: str) -> dict[str, Any]:
    """Analyze message for recall/search intent.

    Args:
        message: User message text.

    Returns:
        Dict with: should_search, confidence, suggested_query, suggested_tags,
        suggested_entities, reasoning, phrase_signals.

    Raises:
        ValueError: Invalid input.
    """
    config = get_config()

    if not config.enable_preprocessing:
        # Preprocessing disabled - return minimal response
        return {
            "should_search": False,
            "confidence": 0.0,
            "suggested_query": "",
            "suggested_tags": [],
            "suggested_entities": [],
            "reasoning": "Preprocessing disabled in configuration",
        }

    # Import preprocessing components
    from ..preprocessing import EntityExtractor, PhraseDetector

    # Initialize components
    phrase_detector = PhraseDetector()
    entity_extractor = EntityExtractor()

    # Analyze message
    phrase_signals = phrase_detector.detect(message)
    entities = entity_extractor.extract(message)

    # Determine if search is recommended
    should_search = False
    reasoning_parts = []
    suggested_query = ""

    if phrase_signals["recall_request"]:
        should_search = True
        confidence = 0.9
        reasoning_parts.append(f"Explicit recall request: {phrase_signals['matched_phrases']}")

        # Extract query from message by removing recall phrases
        query_text = message
        for phrase in phrase_signals["matched_phrases"]:
            query_text = query_text.replace(phrase, "")

        # Clean up query (remove extra spaces, question marks)
        suggested_query = " ".join(query_text.split()).strip("? ")

    elif len(entities) >= 2:
        # Multiple entities without explicit recall phrase might be implicit search
        should_search = True
        confidence = 0.5
        reasoning_parts.append(f"Multiple entities ({len(entities)}) suggest potential recall need")
        # Use entities as query
        suggested_query = " ".join(entities[:3])

    else:
        # No recall signals detected
        should_search = False
        confidence = 0.2
        reasoning_parts.append("No recall signals detected")
        suggested_query = message[:50]  # Fallback to first 50 chars

    # Build reasoning string
    reasoning = "; ".join(reasoning_parts)
    if entities:
        reasoning += f" | Entities: {', '.join(entities[:5])}"

    return {
        "should_search": should_search,
        "confidence": confidence,
        "suggested_query": suggested_query,
        "suggested_tags": [],  # Phase 2: Intent classifier will populate this
        "suggested_entities": entities,
        "reasoning": reasoning,
        "phrase_signals": {
            "save_request": phrase_signals["save_request"],
            "recall_request": phrase_signals["recall_request"],
            "importance_marker": phrase_signals["importance_marker"],
            "matched_phrases": phrase_signals["matched_phrases"],
        },
    }
