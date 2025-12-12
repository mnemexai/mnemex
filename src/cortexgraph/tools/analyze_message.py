"""Analyze message tool for conversational memory activation.

Helper tool that analyzes user messages to determine if they contain memory-worthy
content and provides suggested parameters for save_memory.

This is Track 2 of the two-track MCP approach for conversational activation.

Updated in v0.7.5 to use the new activation module with configurable patterns
and weighted sigmoid confidence calculation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..config import get_config
from ..context import mcp
from ..performance import time_operation

if TYPE_CHECKING:
    from ..activation.config import ActivationConfig
    from ..activation.patterns import PatternMatcher

logger = logging.getLogger(__name__)

# Module-level cache for config and matcher (lazy initialization)
_activation_config: ActivationConfig | None = None
_pattern_matcher: PatternMatcher | None = None


def _get_default_activation_config() -> ActivationConfig:
    """Create default activation config with sensible defaults.

    Used when YAML config file is not available. These defaults match
    the activation.yaml.example file for consistency.

    Returns:
        ActivationConfig with production-ready defaults
    """
    from ..activation.config import (
        ActivationConfig,
        ConfidenceThreshold,
        PatternLibrary,
    )

    patterns = PatternLibrary(
        explicit_save_triggers=[
            "remember this",
            "remember that",
            "don't forget",
            "do not forget",
            "save this",
            "keep in mind",
            "make a note",
            "note that",
            # User preferences (key patterns for "I prefer" support)
            "my preference is",
            "i prefer",
            "i always",
            "i never",
            "i like to",
            "i tend to",
            # Decisions
            "i've decided",
            "i decided to",
            "my decision is",
            "my choice is",
        ],
        explicit_recall_triggers=[
            "what did i say",
            "what did we discuss",
            "do you remember",
            "remind me",
            "recall",
            "my preference",
            "my choice",
            "what's my",
            "what is my",
        ],
        importance_markers=[
            "critical",
            "crucial",
            "essential",
            "must",
            "important",
            "vital",
            "urgent",
            "key",
            "always",
            "never",
        ],
        exclusion_patterns=[
            "what is",
            "who is",
            "how do",
            "how to",
            "tell me about",
            "explain",
            "can you explain",
        ],
        uncertainty_markers=[
            "maybe",
            "might",
            "not sure",
            "perhaps",
            "possibly",
            "probably",
            "i think",
        ],
        case_sensitive=False,
        partial_match=True,
    )

    thresholds = ConfidenceThreshold(
        auto_save_min=0.7,
        auto_recall_min=0.7,
        clarification_min=0.4,
        clarification_max=0.7,
    )

    weights = {
        "explicit_save_request": 5.0,
        "explicit_recall_request": 4.0,
        "preference_statement": 4.0,
        "critical_marker": 3.0,
        "important_marker": 2.0,
        "uncertainty_marker": -3.0,
        "entity_count": 0.8,
    }

    return ActivationConfig(
        patterns=patterns,
        thresholds=thresholds,
        weights=weights,
        bias=-2.0,
    )


def _get_activation_config() -> ActivationConfig:
    """Get or create activation config (cached).

    Tries to load from YAML config file first, falls back to defaults.
    Config is cached at module level for performance.

    Returns:
        ActivationConfig instance
    """
    global _activation_config

    if _activation_config is not None:
        return _activation_config

    from ..activation.config import load_activation_config

    try:
        _activation_config = load_activation_config()
        logger.info("Loaded activation config from YAML file")
    except FileNotFoundError:
        logger.info("No activation.yaml found, using default config")
        _activation_config = _get_default_activation_config()

    return _activation_config


def _get_pattern_matcher() -> PatternMatcher:
    """Get or create pattern matcher (cached).

    Creates PatternMatcher from current activation config.
    Matcher is cached at module level for performance.

    Returns:
        PatternMatcher instance
    """
    global _pattern_matcher

    if _pattern_matcher is not None:
        return _pattern_matcher

    from ..activation.patterns import PatternMatcher

    config = _get_activation_config()
    _pattern_matcher = PatternMatcher(config.patterns)
    return _pattern_matcher


def _make_error_response(reason: str) -> dict[str, Any]:
    """Create a minimal error response with consistent structure.

    Args:
        reason: Human-readable explanation of why analysis failed/skipped

    Returns:
        Dictionary with all expected fields set to safe defaults
    """
    return {
        "should_save": False,
        "confidence": 0.0,
        "suggested_entities": [],
        "suggested_tags": [],
        "suggested_strength": 1.0,
        "reasoning": reason,
        "phrase_signals": {},
    }


@mcp.tool()
@time_operation("analyze_message")
def analyze_message(message: str) -> dict[str, Any]:
    """Analyze message for memory-worthy content.

    Args:
        message: User message text.

    Returns:
        Dict with: should_save, confidence, suggested_entities, suggested_tags,
        suggested_strength, reasoning, phrase_signals.

    Raises:
        ValueError: Invalid input.
    """
    # Input validation
    if message is None:
        logger.warning("analyze_message called with None message")
        return _make_error_response("Invalid input: message is None")

    if not isinstance(message, str):
        logger.warning(f"analyze_message called with non-string: {type(message)}")
        return _make_error_response(f"Invalid input: expected string, got {type(message).__name__}")

    # Log analysis request (truncate long messages)
    msg_preview = message[:100] + "..." if len(message) > 100 else message
    logger.debug(f"Analyzing message: {msg_preview!r}")

    config = get_config()

    if not config.enable_preprocessing:
        logger.debug("Preprocessing disabled, returning minimal response")
        return _make_error_response("Preprocessing disabled in configuration")

    try:
        # Use new activation module
        from ..activation.detectors import detect_save_intent

        activation_config = _get_activation_config()
        matcher = _get_pattern_matcher()

        # Run detection
        analysis = detect_save_intent(message, activation_config, matcher)

        # Log decision for debugging
        if analysis.should_save:
            logger.debug(
                f"Save recommended: confidence={analysis.confidence:.3f}, "
                f"entities={analysis.suggested_entities}"
            )
        else:
            logger.debug(f"No save: confidence={analysis.confidence:.3f}")

        # Convert MessageAnalysis to dict response
        return {
            "should_save": analysis.should_save,
            "confidence": analysis.confidence,
            "suggested_entities": analysis.suggested_entities,
            "suggested_tags": analysis.suggested_tags,
            "suggested_strength": analysis.suggested_strength,
            "reasoning": analysis.reasoning,
            "phrase_signals": analysis.phrase_signals,
        }

    except Exception as e:
        # Log unexpected errors but don't crash
        logger.error(f"Error in analyze_message: {e}", exc_info=True)
        return _make_error_response(f"Analysis error: {type(e).__name__}")
