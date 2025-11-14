"""Analyze message tool for conversational memory activation.

Helper tool that analyzes user messages to determine if they contain memory-worthy
content and provides suggested parameters for save_memory.

This is Track 2 of the two-track MCP approach for conversational activation.
"""

import logging
from typing import Any

from ..config import get_config
from ..context import mcp
from ..performance import time_operation

logger = logging.getLogger(__name__)


@mcp.tool()
@time_operation("analyze_message")
def analyze_message(message: str) -> dict[str, Any]:
    """
    Analyze a message to determine if it contains memory-worthy content.

    Returns activation signals and suggested parameters for save_memory.
    This tool helps the LLM decide whether to save information without explicit
    "remember this" commands.

    **Decision Support (v0.6.0)**: Provides confidence scores and reasoning to help
    Claude determine if save_memory should be called. High confidence (>0.7) suggests
    automatic save; medium confidence (0.4-0.7) suggests asking user first.

    Args:
        message: User message to analyze

    Returns:
        Dictionary containing:
        - should_save (bool): Recommendation to save
        - confidence (float): 0.0-1.0 confidence in recommendation
        - suggested_entities (list[str]): Detected entities
        - suggested_tags (list[str]): Suggested tags (empty in Phase 1)
        - suggested_strength (float): Calculated importance (1.0-2.0)
        - reasoning (str): Explanation of decision

    Example:
        >>> result = analyze_message("Remember my API key: sk-123")
        >>> result["should_save"]
        True
        >>> result["confidence"]
        0.9
        >>> result["reasoning"]
        "Detected: ['remember']"
    """
    config = get_config()

    if not config.enable_preprocessing:
        # Preprocessing disabled - return minimal response
        return {
            "should_save": False,
            "confidence": 0.0,
            "suggested_entities": [],
            "suggested_tags": [],
            "suggested_strength": 1.0,
            "reasoning": "Preprocessing disabled in configuration",
        }

    # Import preprocessing components
    from ..preprocessing import EntityExtractor, ImportanceScorer, PhraseDetector

    # Initialize components
    phrase_detector = PhraseDetector()
    entity_extractor = EntityExtractor()
    importance_scorer = ImportanceScorer()

    # Analyze message
    phrase_signals = phrase_detector.detect(message)
    entities = entity_extractor.extract(message)
    strength = importance_scorer.score(
        message,
        entities=entities,
        importance_marker=phrase_signals["importance_marker"],
    )

    # Determine if save is recommended
    # High priority triggers:
    # - Explicit save request ("remember this")
    # - Importance marker ("this is critical")
    # - Multiple entities (>= 2) suggesting concrete information
    # - High strength score (>= 1.4)

    should_save = False
    reasoning_parts = []

    if phrase_signals["save_request"]:
        should_save = True
        confidence = 0.9
        reasoning_parts.append(f"Explicit save request: {phrase_signals['matched_phrases']}")

    elif phrase_signals["importance_marker"]:
        should_save = True
        confidence = 0.7
        reasoning_parts.append(f"Importance marker: {phrase_signals['matched_phrases']}")

    elif len(entities) >= 2 and strength >= 1.3:
        should_save = True
        confidence = 0.6
        reasoning_parts.append(f"Multiple entities ({len(entities)}) with moderate importance")

    elif strength >= 1.5:
        should_save = True
        confidence = 0.5
        reasoning_parts.append(f"High importance score ({strength:.2f})")

    else:
        # Low priority - don't recommend save
        should_save = False
        confidence = 0.2
        reasoning_parts.append("No strong memory signals detected")

    # Build reasoning string
    reasoning = "; ".join(reasoning_parts)
    if entities:
        reasoning += f" | Entities: {', '.join(entities[:5])}"

    return {
        "should_save": should_save,
        "confidence": confidence,
        "suggested_entities": entities,
        "suggested_tags": [],  # Phase 2: Intent classifier will populate this
        "suggested_strength": strength,
        "reasoning": reasoning,
        "phrase_signals": {
            "save_request": phrase_signals["save_request"],
            "recall_request": phrase_signals["recall_request"],
            "importance_marker": phrase_signals["importance_marker"],
            "matched_phrases": phrase_signals["matched_phrases"],
        },
    }
