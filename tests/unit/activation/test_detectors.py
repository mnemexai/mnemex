"""
Unit tests for detection logic and confidence scoring.

Tests sigmoid function, calculate_confidence, detect_save_intent,
detect_recall_intent, and create_activation_signal for:
- Mathematical correctness (sigmoid curve, confidence formula)
- Signal detection and weighting
- Threshold-based decisions (auto/ask thresholds)
- Edge cases (overflow, empty input, boundary values)
"""

import pytest

from cortexgraph.activation.config import ActivationConfig, ConfidenceThreshold, PatternLibrary
from cortexgraph.activation.detectors import (
    calculate_confidence,
    create_activation_signal,
    detect_recall_intent,
    detect_save_intent,
    sigmoid,
)
from cortexgraph.activation.patterns import PatternMatcher


@pytest.fixture
def test_config():
    """Create test activation configuration."""
    patterns = PatternLibrary(
        explicit_save_triggers=["remember this", "don't forget", "i prefer"],
        explicit_recall_triggers=["what did i say", "remind me"],
        importance_markers=["critical", "must", "important"],
        exclusion_patterns=["what is", "how do"],
        uncertainty_markers=["maybe", "might", "not sure"],
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
def test_matcher(test_config):
    """Create pattern matcher with test config."""
    return PatternMatcher(test_config.patterns)


class TestSigmoidFunction:
    """Tests for sigmoid activation function."""

    def test_sigmoid_zero(self):
        """Test sigmoid(0) = 0.5."""
        result = sigmoid(0.0)
        assert abs(result - 0.5) < 0.01

    def test_sigmoid_positive(self):
        """Test sigmoid of positive values."""
        result = sigmoid(2.0)
        # sigmoid(2) ≈ 0.88
        assert result > 0.5
        assert result < 1.0

    def test_sigmoid_negative(self):
        """Test sigmoid of negative values."""
        result = sigmoid(-2.0)
        # sigmoid(-2) ≈ 0.12
        assert result < 0.5
        assert result > 0.0

    def test_sigmoid_large_positive(self):
        """Test sigmoid handles large positive values."""
        result = sigmoid(100.0)
        # Should approach 1.0
        assert result > 0.99

    def test_sigmoid_large_negative(self):
        """Test sigmoid handles large negative values."""
        result = sigmoid(-100.0)
        # Should approach 0.0
        assert result < 0.01

    def test_sigmoid_overflow_protection(self):
        """Test sigmoid handles overflow gracefully."""
        # Very large negative value that would overflow exp()
        result = sigmoid(-1000.0)
        assert result == 0.0

        # Very large positive value
        result = sigmoid(1000.0)
        assert result == 1.0

    def test_sigmoid_symmetry(self):
        """Test sigmoid(x) + sigmoid(-x) = 1."""
        x = 3.5
        assert abs(sigmoid(x) + sigmoid(-x) - 1.0) < 0.01


class TestCalculateConfidence:
    """Tests for calculate_confidence function."""

    def test_empty_signals(self):
        """Test confidence with no signals."""
        signals = {}
        bias = -2.0

        confidence = calculate_confidence(signals, bias)

        # sigmoid(-2) ≈ 0.12
        assert 0.1 < confidence < 0.2

    def test_single_strong_signal(self):
        """Test confidence with single strong signal."""
        signals = {"explicit_save_request": 4.0}
        bias = -2.0

        confidence = calculate_confidence(signals, bias)

        # sigmoid(4 - 2 = 2) ≈ 0.88
        assert 0.8 < confidence < 0.9

    def test_multiple_signals(self):
        """Test confidence with multiple signals."""
        signals = {
            "explicit_save_request": 4.0,
            "entity_count": 1.6,  # 2 entities * 0.8
        }
        bias = -2.0

        confidence = calculate_confidence(signals, bias)

        # sigmoid(4 + 1.6 - 2 = 3.6) ≈ 0.97
        assert confidence > 0.9

    def test_negative_signals(self):
        """Test confidence with negative signals."""
        signals = {
            "explicit_save_request": 4.0,
            "uncertainty_marker": -2.0,
        }
        bias = -2.0

        confidence = calculate_confidence(signals, bias)

        # sigmoid(4 - 2 - 2 = 0) = 0.5
        assert 0.4 < confidence < 0.6

    def test_strong_negative_dominates(self):
        """Test strong negative signal dominates."""
        signals = {
            "exclusion": -5.0,
        }
        bias = -2.0

        confidence = calculate_confidence(signals, bias)

        # sigmoid(-5 - 2 = -7) ≈ 0.001
        assert confidence < 0.1

    def test_bias_effect(self):
        """Test bias term affects confidence."""
        signals = {"explicit_save_request": 2.0}

        # Lower bias = higher confidence
        conf_low_bias = calculate_confidence(signals, bias=-1.0)
        conf_high_bias = calculate_confidence(signals, bias=-3.0)

        assert conf_low_bias > conf_high_bias


class TestDetectSaveIntent:
    """Tests for detect_save_intent function."""

    def test_explicit_save_request(self, test_config, test_matcher):
        """Test detection of explicit save request."""
        message = "Remember this: I prefer PostgreSQL for databases"

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert analysis.should_save is True
        assert analysis.confidence >= 0.7
        assert "postgresql" in analysis.suggested_entities
        assert "save_request" in analysis.phrase_signals

    def test_importance_marker_critical(self, test_config, test_matcher):
        """Test detection of critical importance marker."""
        message = "This is critical information about security"

        analysis = detect_save_intent(message, test_config, test_matcher)

        # May or may not auto-save depending on other signals
        assert isinstance(analysis.should_save, bool)
        assert "critical_marker" in analysis.phrase_signals

    def test_importance_marker_important(self, test_config, test_matcher):
        """Test detection of important marker."""
        message = "This is important information"

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert "importance_marker" in analysis.phrase_signals

    def test_exclusion_pattern_prevents_save(self, test_config, test_matcher):
        """Test exclusion pattern blocks save."""
        message = "What is PostgreSQL?"

        analysis = detect_save_intent(message, test_config, test_matcher)

        # Exclusion should strongly reduce confidence
        assert analysis.should_save is False
        assert "exclusion_pattern" in analysis.phrase_signals

    def test_uncertainty_marker_reduces_confidence(self, test_config, test_matcher):
        """Test uncertainty marker reduces confidence."""
        message = "I might prefer PostgreSQL, maybe"

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert "uncertainty_marker" in analysis.phrase_signals
        # Uncertainty should lower confidence
        assert analysis.confidence < 0.9

    def test_entity_count_contribution(self, test_config, test_matcher):
        """Test entity count increases confidence."""
        message_few = "Remember this: PostgreSQL"
        message_many = "Remember this: PostgreSQL MongoDB Redis FastAPI Django"

        analysis_few = detect_save_intent(message_few, test_config, test_matcher)
        analysis_many = detect_save_intent(message_many, test_config, test_matcher)

        # More entities should increase confidence
        assert analysis_many.confidence >= analysis_few.confidence
        assert len(analysis_many.suggested_entities) > len(analysis_few.suggested_entities)

    def test_preference_statement(self, test_config, test_matcher):
        """Test preference detection."""
        message = "I prefer PostgreSQL over MongoDB"

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert analysis.should_save is True
        assert (
            "decision_marker" in analysis.phrase_signals
            or "save_request" in analysis.phrase_signals
        )

    def test_suggested_strength_calculation(self, test_config, test_matcher):
        """Test suggested_strength based on confidence."""
        # Very high confidence
        message_high = "Remember this: critical security information about PostgreSQL"
        analysis_high = detect_save_intent(message_high, test_config, test_matcher)

        # Lower confidence
        message_low = "Some regular information"
        analysis_low = detect_save_intent(message_low, test_config, test_matcher)

        # High confidence should suggest higher strength
        if analysis_high.confidence >= 0.9:
            assert analysis_high.suggested_strength >= 1.5
        if analysis_low.confidence < 0.7:
            assert analysis_low.suggested_strength <= 1.5

    def test_suggested_tags_generation(self, test_config, test_matcher):
        """Test automatic tag suggestion."""
        message = "I prefer PostgreSQL for my API databases"

        analysis = detect_save_intent(message, test_config, test_matcher)

        # Should suggest relevant tags
        assert any(tag in ["database", "api", "preference"] for tag in analysis.suggested_tags)

    def test_reasoning_string_format(self, test_config, test_matcher):
        """Test reasoning string is informative."""
        message = "Remember this: I prefer PostgreSQL"

        analysis = detect_save_intent(message, test_config, test_matcher)

        # Reasoning should contain signal breakdown
        assert "Signals:" in analysis.reasoning
        assert "Raw score:" in analysis.reasoning
        assert "Confidence:" in analysis.reasoning

    def test_empty_message(self, test_config, test_matcher):
        """Test detection with empty message."""
        message = ""

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert analysis.should_save is False
        assert analysis.confidence < 0.5
        assert len(analysis.suggested_entities) == 0


class TestDetectRecallIntent:
    """Tests for detect_recall_intent function."""

    def test_explicit_recall_request(self, test_config, test_matcher):
        """Test detection of explicit recall request."""
        query = "What did I say about PostgreSQL?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        assert analysis.should_search is True
        assert analysis.confidence >= 0.7
        assert "recall_request" in analysis.phrase_signals

    def test_past_reference_detection(self, test_config, test_matcher):
        """Test detection of past references."""
        query = "What did we discuss last time about databases?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        assert "past_reference" in analysis.phrase_signals
        assert analysis.confidence > 0.5

    def test_question_marker_detection(self, test_config, test_matcher):
        """Test question markers increase recall likelihood."""
        query = "What database preferences do we have?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        assert "question_marker" in analysis.phrase_signals

    def test_possessive_reference_detection(self, test_config, test_matcher):
        """Test possessive references suggest recall."""
        query = "Tell me about my database preference"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        assert "possessive_reference" in analysis.phrase_signals
        assert analysis.confidence > 0.5

    def test_exclusion_pattern_blocks_recall(self, test_config, test_matcher):
        """Test exclusion pattern blocks general questions."""
        query = "What is PostgreSQL?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        # General "what is" questions should not trigger recall
        assert analysis.should_search is False
        assert "exclusion_pattern" in analysis.phrase_signals

    def test_suggested_query_extraction(self, test_config, test_matcher):
        """Test extraction of search query."""
        query = "What did I say about PostgreSQL preferences?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        # Should strip recall triggers but keep content
        assert "postgresql" in analysis.suggested_query.lower()
        assert "preferences" in analysis.suggested_query.lower()

    def test_suggested_tags_from_entities(self, test_config, test_matcher):
        """Test tags generated from entities."""
        query = "What did I say about PostgreSQL and MongoDB?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        # Should use entities as tags (first 3)
        assert len(analysis.suggested_tags) <= 3
        if analysis.suggested_entities:
            assert analysis.suggested_tags[0] in analysis.suggested_entities

    def test_entity_count_increases_confidence(self, test_config, test_matcher):
        """Test more entities increase confidence."""
        query_few = "What did I say?"
        query_many = "What did I say about PostgreSQL MongoDB Redis FastAPI?"

        analysis_few = detect_recall_intent(query_few, test_config, test_matcher)
        analysis_many = detect_recall_intent(query_many, test_config, test_matcher)

        # More specific query should have higher confidence
        assert analysis_many.confidence >= analysis_few.confidence

    def test_reasoning_string_format(self, test_config, test_matcher):
        """Test reasoning string format."""
        query = "What did I say about PostgreSQL?"

        analysis = detect_recall_intent(query, test_config, test_matcher)

        assert "Signals:" in analysis.reasoning
        assert "Raw score:" in analysis.reasoning
        assert "Confidence:" in analysis.reasoning

    def test_empty_query(self, test_config, test_matcher):
        """Test recall detection with empty query."""
        query = ""

        analysis = detect_recall_intent(query, test_config, test_matcher)

        assert analysis.should_search is False
        assert analysis.confidence < 0.5


class TestCreateActivationSignal:
    """Tests for create_activation_signal factory function."""

    def test_create_save_signal(self):
        """Test creating save activation signal."""
        signal = create_activation_signal(
            signal_type="save",
            confidence=0.92,
            matched_patterns=["remember this", "i prefer"],
            context="Remember this: I prefer PostgreSQL for databases",
        )

        assert signal.type == "save"
        assert signal.confidence == 0.92
        assert len(signal.matched_patterns) == 2
        assert "remember this" in signal.matched_patterns
        assert signal.context == "Remember this: I prefer PostgreSQL for databases"
        assert signal.timestamp > 0

    def test_create_recall_signal(self):
        """Test creating recall activation signal."""
        signal = create_activation_signal(
            signal_type="recall",
            confidence=0.85,
            matched_patterns=["what did i say"],
            context="What did I say about databases?",
        )

        assert signal.type == "recall"
        assert signal.confidence == 0.85

    def test_create_reinforce_signal(self):
        """Test creating reinforce activation signal."""
        signal = create_activation_signal(
            signal_type="reinforce",
            confidence=0.75,
            matched_patterns=[],
            context="Using PostgreSQL knowledge again",
        )

        assert signal.type == "reinforce"
        assert signal.confidence == 0.75

    def test_context_truncation(self):
        """Test context is truncated to max length."""
        long_context = "x" * 2000

        signal = create_activation_signal(
            signal_type="save",
            confidence=0.8,
            matched_patterns=[],
            context=long_context,
        )

        # Context should be truncated to 1000 chars
        assert len(signal.context) == 1000

    def test_empty_matched_patterns(self):
        """Test creating signal with no matched patterns."""
        signal = create_activation_signal(
            signal_type="save",
            confidence=0.6,
            matched_patterns=[],
            context="Some context",
        )

        assert len(signal.matched_patterns) == 0

    def test_timestamp_is_current(self):
        """Test timestamp is set to current time."""
        import time

        before = int(time.time())
        signal = create_activation_signal(
            signal_type="save",
            confidence=0.8,
            matched_patterns=[],
            context="Test",
        )
        after = int(time.time())

        assert before <= signal.timestamp <= after


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_confidence_at_auto_threshold(self, test_config, test_matcher):
        """Test decision at exact auto threshold."""
        # Craft message to hit threshold exactly (difficult, so test near it)
        message = "Remember this: PostgreSQL"

        analysis = detect_save_intent(message, test_config, test_matcher)

        # Should make clear decision
        assert isinstance(analysis.should_save, bool)

    def test_confidence_at_ask_threshold(self, test_config, test_matcher):
        """Test decision at ask threshold."""
        # Craft message with medium confidence
        message = "Maybe PostgreSQL is important"

        analysis = detect_save_intent(message, test_config, test_matcher)

        # Between ask and auto thresholds
        if 0.4 <= analysis.confidence < 0.7:
            # Should not auto-save
            assert analysis.should_save is False

    def test_very_long_message(self, test_config, test_matcher):
        """Test detection with very long message."""
        message = "Remember this: " + "PostgreSQL " * 500

        analysis = detect_save_intent(message, test_config, test_matcher)

        # Should handle without error
        assert isinstance(analysis.confidence, float)

    def test_unicode_text(self, test_config, test_matcher):
        """Test detection with unicode characters."""
        message = "Remember this: I prefer PostgreSQL for my café ☕"

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert analysis.should_save is True

    def test_multiline_message(self, test_config, test_matcher):
        """Test detection with multiline text."""
        message = """Remember this:
        I prefer PostgreSQL
        for databases"""

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert analysis.should_save is True

    def test_special_characters(self, test_config, test_matcher):
        """Test detection with special characters."""
        message = "Remember this: API keys = sk-abc123!"

        analysis = detect_save_intent(message, test_config, test_matcher)

        assert analysis.should_save is True
