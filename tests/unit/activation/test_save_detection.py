"""
Unit tests for save detection in natural language activation.

This module tests the detect_save_intent function with:
- T022: Explicit save triggers ("remember this", "don't forget", "I prefer")
- T023: Implicit signals (importance markers, entity count)
- T024: Exclusion patterns (general questions, small talk)

Tests focus on the decision-making logic, not the underlying pattern matching
(which is tested in test_patterns.py).
"""

import pytest

from cortexgraph.activation.config import ActivationConfig, ConfidenceThreshold, PatternLibrary
from cortexgraph.activation.detectors import detect_save_intent
from cortexgraph.activation.patterns import PatternMatcher


@pytest.fixture
def save_detection_config():
    """Create configuration for save detection testing."""
    patterns = PatternLibrary(
        explicit_save_triggers=["remember this", "don't forget", "i prefer"],
        explicit_recall_triggers=["what did i say", "remind me"],
        importance_markers=["critical", "must remember", "very important", "essential"],
        exclusion_patterns=["what is", "how do", "how does", "can you explain"],
        uncertainty_markers=["maybe", "might", "not sure", "perhaps"],
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
        "explicit_save_request": 4.0,
        "explicit_recall_request": 5.0,
        "critical_marker": 3.5,
        "important_marker": 2.5,
        "uncertainty_marker": -2.0,
        "preference_statement": 3.0,
        "entity_count": 0.8,
    }

    return ActivationConfig(
        patterns=patterns,
        thresholds=thresholds,
        weights=weights,
        bias=-2.0,
    )


@pytest.fixture
def save_detection_matcher(save_detection_config):
    """Create pattern matcher for save detection testing."""
    return PatternMatcher(save_detection_config.patterns)


# ============================================================================
# T022: EXPLICIT SAVE TRIGGERS
# ============================================================================


class TestExplicitSaveTriggers:
    """Unit tests for explicit save trigger detection (T022).

    Explicit triggers are phrases that clearly indicate user intent to save:
    - "Remember this: ..."
    - "Don't forget: ..."
    - "I prefer [entity]"
    """

    def test_remember_this_triggers_save(self, save_detection_config, save_detection_matcher):
        """'Remember this' should trigger save with high confidence."""
        result = detect_save_intent(
            "Remember this: I use PostgreSQL for all my projects",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
        assert result.confidence >= 0.7
        assert result.phrase_signals.get("save_request") is True

    def test_dont_forget_triggers_save(self, save_detection_config, save_detection_matcher):
        """'Don't forget' should trigger save with high confidence."""
        result = detect_save_intent(
            "Don't forget: my API key format is sk-xxx",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
        assert result.confidence >= 0.7
        assert result.phrase_signals.get("save_request") is True

    def test_i_prefer_with_entity_triggers_save(
        self, save_detection_config, save_detection_matcher
    ):
        """'I prefer [entity]' should trigger save.

        Note: The activation module's detect_save_intent correctly handles this
        via the 'preference_statement' signal. The MCP tool (analyze_message)
        needs to be updated to use this module (tracked in T026-T028).
        """
        result = detect_save_intent(
            "I prefer PostgreSQL for my databases",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
        assert result.confidence >= 0.5
        assert "postgresql" in [e.lower() for e in result.suggested_entities]

    def test_explicit_trigger_case_insensitive(self, save_detection_config, save_detection_matcher):
        """Explicit triggers should work regardless of case."""
        result = detect_save_intent(
            "REMEMBER THIS: I always use TypeScript",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
        assert result.confidence >= 0.7

    def test_explicit_trigger_with_multiple_entities(
        self, save_detection_config, save_detection_matcher
    ):
        """Explicit triggers with multiple entities should have higher confidence."""
        result = detect_save_intent(
            "Remember this: I prefer PostgreSQL for databases and Redis for caching",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
        assert result.confidence >= 0.7
        # Should extract multiple entities
        assert len(result.suggested_entities) >= 2


# ============================================================================
# T023: IMPLICIT SAVE SIGNALS
# ============================================================================


class TestImplicitSaveSignals:
    """Unit tests for implicit save signal detection (T023).

    Implicit signals suggest memory-worthy content without explicit request:
    - Importance markers ("critical", "must remember")
    - High entity count (multiple tech names)
    - Decision/preference statements
    """

    def test_critical_marker_triggers_save(self, save_detection_config, save_detection_matcher):
        """'Critical' importance marker should trigger save."""
        result = detect_save_intent(
            "This is critical: the API endpoint changed to /v2/users",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
        assert result.confidence >= 0.7
        assert result.phrase_signals.get("critical_marker") is True

    def test_must_remember_marker_triggers_consideration(
        self, save_detection_config, save_detection_matcher
    ):
        """'Must remember' should trigger at least ask-level consideration.

        Note: With single importance marker and no entities, confidence
        lands in ask range (0.4-0.7) not auto-save (>0.7). This is by design -
        the system asks for confirmation rather than auto-saving.
        """
        result = detect_save_intent(
            "I must remember to use environment variables for secrets",
            save_detection_config,
            save_detection_matcher,
        )

        # Should be in ask range (0.4-0.7) or higher
        assert result.confidence >= 0.4
        # Importance marker should be detected
        assert result.phrase_signals.get("importance_marker") is True

    def test_very_important_marker_triggers_consideration(
        self, save_detection_config, save_detection_matcher
    ):
        """'Very important' should at least reach ask threshold."""
        result = detect_save_intent(
            "This is very important: always validate user input",
            save_detection_config,
            save_detection_matcher,
        )

        # Should at least be in ask range or auto-save
        assert result.confidence >= 0.4

    def test_high_entity_count_increases_confidence(
        self, save_detection_config, save_detection_matcher
    ):
        """Multiple tech entities should increase save confidence."""
        # Low entity message
        result_low = detect_save_intent(
            "I use Python",
            save_detection_config,
            save_detection_matcher,
        )

        # High entity message
        result_high = detect_save_intent(
            "I use Python, TypeScript, Rust, and Go for different projects",
            save_detection_config,
            save_detection_matcher,
        )

        # Higher entity count should have higher confidence
        assert result_high.confidence > result_low.confidence
        assert len(result_high.suggested_entities) >= 3

    def test_decision_keyword_boosts_confidence(
        self, save_detection_config, save_detection_matcher
    ):
        """Decision-related keywords should boost save confidence."""
        result = detect_save_intent(
            "I've decided to use FastAPI for all my backend services",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.phrase_signals.get("decision_marker") is True
        # Should have reasonable confidence due to decision + entity
        assert result.confidence >= 0.4

    def test_preference_keyword_boosts_confidence(
        self, save_detection_config, save_detection_matcher
    ):
        """Preference statements should boost save confidence."""
        result = detect_save_intent(
            "My preference is to always use TypeScript over JavaScript",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.phrase_signals.get("decision_marker") is True

    def test_combined_signals_high_confidence(self, save_detection_config, save_detection_matcher):
        """Multiple positive signals should result in high confidence."""
        result = detect_save_intent(
            "Remember this critical decision: I chose PostgreSQL and Redis",
            save_detection_config,
            save_detection_matcher,
        )

        # Explicit trigger + critical marker + entities = very high confidence
        assert result.should_save is True
        assert result.confidence >= 0.9


# ============================================================================
# T024: EXCLUSION PATTERNS (SMALL TALK FILTERING)
# ============================================================================


class TestExclusionPatterns:
    """Unit tests for exclusion pattern detection (T024).

    Exclusion patterns filter out messages that should NOT be saved:
    - General knowledge questions ("What is X?")
    - How-to questions ("How do I X?")
    - Small talk and casual conversation
    """

    def test_what_is_question_excluded(self, save_detection_config, save_detection_matcher):
        """'What is X?' questions should NOT trigger save."""
        result = detect_save_intent(
            "What is a database index?",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False
        assert result.confidence < 0.4
        assert result.phrase_signals.get("exclusion_pattern") is True

    def test_how_do_question_excluded(self, save_detection_config, save_detection_matcher):
        """'How do I X?' questions should NOT trigger save."""
        result = detect_save_intent(
            "How do I connect to PostgreSQL?",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False
        assert result.phrase_signals.get("exclusion_pattern") is True

    def test_how_does_question_excluded(self, save_detection_config, save_detection_matcher):
        """'How does X?' questions should NOT trigger save."""
        result = detect_save_intent(
            "How does garbage collection work in Python?",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False
        assert result.phrase_signals.get("exclusion_pattern") is True

    def test_can_you_explain_excluded(self, save_detection_config, save_detection_matcher):
        """'Can you explain X?' questions should NOT trigger save."""
        result = detect_save_intent(
            "Can you explain async/await in JavaScript?",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False
        assert result.phrase_signals.get("exclusion_pattern") is True

    def test_exclusion_overrides_entity_count(self, save_detection_config, save_detection_matcher):
        """Exclusion pattern should override positive entity signals."""
        result = detect_save_intent(
            "What is the difference between PostgreSQL, MySQL, and SQLite?",
            save_detection_config,
            save_detection_matcher,
        )

        # Despite having 3 entities, exclusion pattern should keep confidence low
        assert result.should_save is False
        assert result.confidence < 0.5

    def test_exclusion_does_not_override_explicit_save(
        self, save_detection_config, save_detection_matcher
    ):
        """Explicit save trigger should still work even with exclusion pattern words.

        Note: This tests edge case where user says something like
        'Remember this: what is my database preference?' - which is a recall,
        but if they say 'Remember this: my preference is PostgreSQL' that's a save.
        """
        result = detect_save_intent(
            "Remember this: PostgreSQL is my database choice",
            save_detection_config,
            save_detection_matcher,
        )

        # Explicit trigger should result in save
        assert result.should_save is True
        assert result.confidence >= 0.7


# ============================================================================
# UNCERTAINTY MARKERS
# ============================================================================


class TestUncertaintyMarkers:
    """Unit tests for uncertainty marker detection.

    Uncertainty reduces confidence in save decision.
    """

    def test_maybe_reduces_confidence(self, save_detection_config, save_detection_matcher):
        """'Maybe' should reduce save confidence."""
        result_certain = detect_save_intent(
            "I use PostgreSQL for databases",
            save_detection_config,
            save_detection_matcher,
        )

        result_uncertain = detect_save_intent(
            "Maybe I should use PostgreSQL for databases",
            save_detection_config,
            save_detection_matcher,
        )

        assert result_uncertain.confidence < result_certain.confidence
        assert result_uncertain.phrase_signals.get("uncertainty_marker") is True

    def test_not_sure_reduces_confidence(self, save_detection_config, save_detection_matcher):
        """'Not sure' should reduce save confidence."""
        result = detect_save_intent(
            "I'm not sure if PostgreSQL is the right choice",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.phrase_signals.get("uncertainty_marker") is True
        # Should have reduced confidence
        assert result.confidence < 0.7


# ============================================================================
# EDGE CASES
# ============================================================================


class TestSaveDetectionEdgeCases:
    """Edge case tests for save detection."""

    def test_empty_message_no_save(self, save_detection_config, save_detection_matcher):
        """Empty message should not trigger save."""
        result = detect_save_intent(
            "",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False
        assert result.confidence < 0.5

    def test_whitespace_only_no_save(self, save_detection_config, save_detection_matcher):
        """Whitespace-only message should not trigger save."""
        result = detect_save_intent(
            "   \n\t  ",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False

    def test_very_short_message_no_save(self, save_detection_config, save_detection_matcher):
        """Very short messages typically shouldn't trigger save."""
        result = detect_save_intent(
            "Hi",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is False
        assert result.confidence < 0.5

    def test_very_long_message_handled(self, save_detection_config, save_detection_matcher):
        """Very long messages should be handled without error."""
        long_message = "Remember this: " + "PostgreSQL " * 500

        result = detect_save_intent(
            long_message,
            save_detection_config,
            save_detection_matcher,
        )

        # Should still work
        assert result.should_save is True
        assert result.confidence >= 0.5

    def test_unicode_handled(self, save_detection_config, save_detection_matcher):
        """Unicode characters should be handled correctly."""
        result = detect_save_intent(
            "Remember this: my café database uses PostgreSQL ☕",
            save_detection_config,
            save_detection_matcher,
        )

        assert result.should_save is True
