"""
Unit tests for activation Pydantic models.

Tests validation rules, field constraints, and serialization for:
- ActivationSignal
- MessageAnalysis
- RecallAnalysis
"""

import time

import pytest
from pydantic import ValidationError

from cortexgraph.activation.models import (
    ActivationSignal,
    MessageAnalysis,
    RecallAnalysis,
)


class TestActivationSignal:
    """Tests for ActivationSignal model."""

    def test_valid_save_signal(self):
        """Test creating valid save signal."""
        signal = ActivationSignal(
            type="save",
            confidence=0.92,
            matched_patterns=["remember this", "explicit_save"],
            context="Remember this: I prefer PostgreSQL for databases",
            timestamp=int(time.time()),
        )

        assert signal.type == "save"
        assert signal.confidence == 0.92
        assert len(signal.matched_patterns) == 2
        assert "remember this" in signal.matched_patterns
        assert len(signal.context) > 0

    def test_valid_recall_signal(self):
        """Test creating valid recall signal."""
        signal = ActivationSignal(
            type="recall",
            confidence=0.88,
            matched_patterns=["what did i say"],
            context="What did I say about authentication?",
            timestamp=int(time.time()),
        )

        assert signal.type == "recall"
        assert signal.confidence == 0.88

    def test_valid_reinforce_signal(self):
        """Test creating valid reinforce signal."""
        signal = ActivationSignal(
            type="reinforce",
            confidence=0.75,
            matched_patterns=["like i told you"],
            context="Like I told you before, I use JWT",
            timestamp=int(time.time()),
        )

        assert signal.type == "reinforce"
        assert signal.confidence == 0.75

    def test_confidence_valid_range(self):
        """Test confidence accepts valid 0.0-1.0 range."""
        # Boundary values
        signal_low = ActivationSignal(
            type="save", confidence=0.0, context="test", timestamp=int(time.time())
        )
        assert signal_low.confidence == 0.0

        signal_high = ActivationSignal(
            type="save", confidence=1.0, context="test", timestamp=int(time.time())
        )
        assert signal_high.confidence == 1.0

        # Mid-range
        signal_mid = ActivationSignal(
            type="save", confidence=0.5, context="test", timestamp=int(time.time())
        )
        assert signal_mid.confidence == 0.5

    def test_confidence_below_zero_fails(self):
        """Test confidence < 0.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActivationSignal(
                type="save",
                confidence=-0.1,
                context="test",
                timestamp=int(time.time()),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_confidence_above_one_fails(self):
        """Test confidence > 1.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActivationSignal(
                type="save",
                confidence=1.5,
                context="test",
                timestamp=int(time.time()),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_invalid_type_fails(self):
        """Test invalid type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActivationSignal(
                type="invalid",  # type: ignore[arg-type]
                confidence=0.8,
                context="test",
                timestamp=int(time.time()),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) for e in errors)

    def test_context_max_length(self):
        """Test context enforces max 1000 chars."""
        long_context = "x" * 1500  # 1500 chars

        # Should raise ValidationError for exceeding max_length
        with pytest.raises(ValidationError) as exc_info:
            ActivationSignal(
                type="save",
                confidence=0.8,
                context=long_context,
                timestamp=int(time.time()),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("context",) for e in errors)
        assert any(e["type"] == "string_too_long" for e in errors)

    def test_matched_patterns_default_empty(self):
        """Test matched_patterns defaults to empty list."""
        signal = ActivationSignal(
            type="save", confidence=0.8, context="test", timestamp=int(time.time())
        )

        assert signal.matched_patterns == []

    def test_serialization(self):
        """Test model can be serialized to JSON."""
        signal = ActivationSignal(
            type="save",
            confidence=0.92,
            matched_patterns=["remember this"],
            context="Test context",
            timestamp=1706140800,
        )

        json_data = signal.model_dump_json()
        assert '"type":"save"' in json_data
        assert '"confidence":0.92' in json_data


class TestMessageAnalysis:
    """Tests for MessageAnalysis model."""

    def test_valid_high_confidence_save(self):
        """Test valid high-confidence save analysis."""
        analysis = MessageAnalysis(
            should_save=True,
            confidence=0.92,
            suggested_entities=["postgresql", "fastapi"],
            suggested_tags=["database", "framework"],
            suggested_strength=1.5,
            reasoning="Explicit save request (+5.0), 2 entities (+1.6) | Raw score: 4.6 → Confidence: 0.920",
            phrase_signals={"save_request": True, "importance_marker": False},
        )

        assert analysis.should_save is True
        assert analysis.confidence == 0.92
        assert len(analysis.suggested_entities) == 2
        assert len(analysis.suggested_tags) == 2
        assert analysis.suggested_strength == 1.5
        assert "Explicit save request" in analysis.reasoning
        assert analysis.phrase_signals["save_request"] is True

    def test_valid_low_confidence_skip(self):
        """Test valid low-confidence skip analysis."""
        analysis = MessageAnalysis(
            should_save=False,
            confidence=0.12,
            suggested_entities=[],
            suggested_tags=[],
            suggested_strength=1.0,
            reasoning="Signals: exclusion (-5.0) | Raw score: -7.0 → Confidence: 0.120",
            phrase_signals={"exclusion_pattern": True},
        )

        assert analysis.should_save is False
        assert analysis.confidence == 0.12
        assert len(analysis.suggested_entities) == 0
        assert analysis.suggested_strength == 1.0

    def test_confidence_valid_range(self):
        """Test confidence accepts 0.0-1.0 range."""
        # Boundary values
        analysis_low = MessageAnalysis(should_save=False, confidence=0.0, reasoning="test")
        assert analysis_low.confidence == 0.0

        analysis_high = MessageAnalysis(should_save=True, confidence=1.0, reasoning="test")
        assert analysis_high.confidence == 1.0

    def test_confidence_out_of_range_fails(self):
        """Test confidence outside [0, 1] raises ValidationError."""
        with pytest.raises(ValidationError):
            MessageAnalysis(should_save=True, confidence=1.5, reasoning="test")

        with pytest.raises(ValidationError):
            MessageAnalysis(should_save=False, confidence=-0.1, reasoning="test")

    def test_strength_valid_range(self):
        """Test suggested_strength accepts 1.0-2.0 range."""
        # Boundary values
        analysis_low = MessageAnalysis(
            should_save=True, confidence=0.7, suggested_strength=1.0, reasoning="test"
        )
        assert analysis_low.suggested_strength == 1.0

        analysis_high = MessageAnalysis(
            should_save=True, confidence=0.9, suggested_strength=2.0, reasoning="test"
        )
        assert analysis_high.suggested_strength == 2.0

    def test_strength_out_of_range_fails(self):
        """Test suggested_strength outside [1, 2] raises ValidationError."""
        with pytest.raises(ValidationError):
            MessageAnalysis(
                should_save=True, confidence=0.8, suggested_strength=0.5, reasoning="test"
            )

        with pytest.raises(ValidationError):
            MessageAnalysis(
                should_save=True, confidence=0.8, suggested_strength=2.5, reasoning="test"
            )

    def test_strength_default_value(self):
        """Test suggested_strength defaults to 1.0."""
        analysis = MessageAnalysis(should_save=True, confidence=0.8, reasoning="test")
        assert analysis.suggested_strength == 1.0

    def test_entities_max_length(self):
        """Test suggested_entities enforces max 100 items."""
        # 100 should work
        entities = [f"entity{i}" for i in range(100)]
        analysis = MessageAnalysis(
            should_save=True,
            confidence=0.8,
            suggested_entities=entities,
            reasoning="test",
        )
        assert len(analysis.suggested_entities) == 100

        # 101 should fail
        entities_too_many = [f"entity{i}" for i in range(101)]
        with pytest.raises(ValidationError):
            MessageAnalysis(
                should_save=True,
                confidence=0.8,
                suggested_entities=entities_too_many,
                reasoning="test",
            )

    def test_tags_max_length(self):
        """Test suggested_tags enforces max 50 items."""
        # 50 should work
        tags = [f"tag{i}" for i in range(50)]
        analysis = MessageAnalysis(
            should_save=True, confidence=0.8, suggested_tags=tags, reasoning="test"
        )
        assert len(analysis.suggested_tags) == 50

        # 51 should fail
        tags_too_many = [f"tag{i}" for i in range(51)]
        with pytest.raises(ValidationError):
            MessageAnalysis(
                should_save=True,
                confidence=0.8,
                suggested_tags=tags_too_many,
                reasoning="test",
            )

    def test_reasoning_required(self):
        """Test reasoning field is required."""
        with pytest.raises(ValidationError) as exc_info:
            MessageAnalysis(should_save=True, confidence=0.8)  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("reasoning",) for e in errors)

    def test_reasoning_min_length(self):
        """Test reasoning requires min 1 character."""
        with pytest.raises(ValidationError):
            MessageAnalysis(should_save=True, confidence=0.8, reasoning="")

    def test_reasoning_max_length(self):
        """Test reasoning enforces max 1000 chars."""
        long_reasoning = "x" * 1500

        with pytest.raises(ValidationError):
            MessageAnalysis(should_save=True, confidence=0.8, reasoning=long_reasoning)

    def test_phrase_signals_optional(self):
        """Test phrase_signals is optional and defaults to empty dict."""
        analysis = MessageAnalysis(should_save=True, confidence=0.8, reasoning="test")
        assert analysis.phrase_signals == {}

    def test_serialization(self):
        """Test model serialization to JSON."""
        analysis = MessageAnalysis(
            should_save=True,
            confidence=0.92,
            suggested_entities=["postgresql"],
            suggested_tags=["database"],
            suggested_strength=1.5,
            reasoning="Test reasoning",
            phrase_signals={"save_request": True},
        )

        json_data = analysis.model_dump_json()
        assert '"should_save":true' in json_data
        assert '"confidence":0.92' in json_data
        assert '"suggested_strength":1.5' in json_data


class TestRecallAnalysis:
    """Tests for RecallAnalysis model."""

    def test_valid_high_confidence_recall(self):
        """Test valid high-confidence recall analysis."""
        analysis = RecallAnalysis(
            should_search=True,
            confidence=0.88,
            suggested_query="authentication methods",
            suggested_tags=["auth", "security"],
            suggested_entities=["jwt", "oauth"],
            reasoning="Signals: recall request (+4.0), 2 entities (+1.6) | Raw score: 3.6 → Confidence: 0.880",
            phrase_signals={"recall_request": True, "past_reference": True},
        )

        assert analysis.should_search is True
        assert analysis.confidence == 0.88
        assert analysis.suggested_query == "authentication methods"
        assert len(analysis.suggested_tags) == 2
        assert len(analysis.suggested_entities) == 2
        assert analysis.phrase_signals["recall_request"] is True

    def test_valid_low_confidence_skip(self):
        """Test valid low-confidence skip analysis."""
        analysis = RecallAnalysis(
            should_search=False,
            confidence=0.18,
            suggested_query="",
            suggested_tags=[],
            suggested_entities=[],
            reasoning="Signals: exclusion (-4.0) | Raw score: -6.0 → Confidence: 0.180",
            phrase_signals={"exclusion_pattern": True},
        )

        assert analysis.should_search is False
        assert analysis.confidence == 0.18
        assert analysis.suggested_query == ""

    def test_confidence_valid_range(self):
        """Test confidence accepts 0.0-1.0 range."""
        analysis_low = RecallAnalysis(should_search=False, confidence=0.0, reasoning="test")
        assert analysis_low.confidence == 0.0

        analysis_high = RecallAnalysis(should_search=True, confidence=1.0, reasoning="test")
        assert analysis_high.confidence == 1.0

    def test_confidence_out_of_range_fails(self):
        """Test confidence outside [0, 1] raises ValidationError."""
        with pytest.raises(ValidationError):
            RecallAnalysis(should_search=True, confidence=1.5, reasoning="test")

        with pytest.raises(ValidationError):
            RecallAnalysis(should_search=False, confidence=-0.1, reasoning="test")

    def test_suggested_query_optional(self):
        """Test suggested_query is optional and defaults to empty."""
        analysis = RecallAnalysis(should_search=False, confidence=0.3, reasoning="test")
        assert analysis.suggested_query == ""

    def test_suggested_query_max_length(self):
        """Test suggested_query enforces max 1000 chars."""
        long_query = "x" * 1500

        with pytest.raises(ValidationError):
            RecallAnalysis(
                should_search=True, confidence=0.8, suggested_query=long_query, reasoning="test"
            )

    def test_tags_max_length(self):
        """Test suggested_tags enforces max 50 items."""
        tags = [f"tag{i}" for i in range(50)]
        analysis = RecallAnalysis(
            should_search=True, confidence=0.8, suggested_tags=tags, reasoning="test"
        )
        assert len(analysis.suggested_tags) == 50

        tags_too_many = [f"tag{i}" for i in range(51)]
        with pytest.raises(ValidationError):
            RecallAnalysis(
                should_search=True,
                confidence=0.8,
                suggested_tags=tags_too_many,
                reasoning="test",
            )

    def test_entities_max_length(self):
        """Test suggested_entities enforces max 100 items."""
        entities = [f"entity{i}" for i in range(100)]
        analysis = RecallAnalysis(
            should_search=True, confidence=0.8, suggested_entities=entities, reasoning="test"
        )
        assert len(analysis.suggested_entities) == 100

        entities_too_many = [f"entity{i}" for i in range(101)]
        with pytest.raises(ValidationError):
            RecallAnalysis(
                should_search=True,
                confidence=0.8,
                suggested_entities=entities_too_many,
                reasoning="test",
            )

    def test_reasoning_required(self):
        """Test reasoning field is required."""
        with pytest.raises(ValidationError) as exc_info:
            RecallAnalysis(should_search=True, confidence=0.8)  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("reasoning",) for e in errors)

    def test_reasoning_constraints(self):
        """Test reasoning min/max length constraints."""
        # Empty reasoning
        with pytest.raises(ValidationError):
            RecallAnalysis(should_search=True, confidence=0.8, reasoning="")

        # Too long reasoning
        long_reasoning = "x" * 1500
        with pytest.raises(ValidationError):
            RecallAnalysis(should_search=True, confidence=0.8, reasoning=long_reasoning)

    def test_phrase_signals_optional(self):
        """Test phrase_signals is optional and defaults to empty dict."""
        analysis = RecallAnalysis(should_search=True, confidence=0.8, reasoning="test")
        assert analysis.phrase_signals == {}

    def test_serialization(self):
        """Test model serialization to JSON."""
        analysis = RecallAnalysis(
            should_search=True,
            confidence=0.88,
            suggested_query="authentication",
            suggested_tags=["auth"],
            suggested_entities=["jwt"],
            reasoning="Test reasoning",
            phrase_signals={"recall_request": True},
        )

        json_data = analysis.model_dump_json()
        assert '"should_search":true' in json_data
        assert '"confidence":0.88' in json_data
        assert '"suggested_query":"authentication"' in json_data


class TestModelExamples:
    """Test that model examples from json_schema_extra work correctly."""

    def test_activation_signal_example(self):
        """Test ActivationSignal example from model config."""
        example = {
            "type": "save",
            "confidence": 0.95,
            "matched_patterns": ["remember this", "explicit_save_trigger"],
            "context": "Remember this: I prefer PostgreSQL for databases",
            "timestamp": 1706140800,
        }

        signal = ActivationSignal(**example)
        assert signal.type == "save"
        assert signal.confidence == 0.95

    def test_message_analysis_example(self):
        """Test MessageAnalysis example from model config."""
        example = {
            "should_save": True,
            "confidence": 0.92,
            "suggested_entities": ["postgresql", "api"],
            "suggested_tags": ["database", "preference"],
            "suggested_strength": 1.5,
            "reasoning": "Signals: explicit save request (+5.0), 2 entities (+1.6) | Raw score: 4.6 → Confidence: 0.920",
            "phrase_signals": {
                "save_request": True,
                "importance_marker": False,
                "uncertainty_marker": False,
            },
        }

        analysis = MessageAnalysis(**example)
        assert analysis.should_save is True
        assert analysis.confidence == 0.92

    def test_recall_analysis_example(self):
        """Test RecallAnalysis example from model config."""
        example = {
            "should_search": True,
            "confidence": 0.88,
            "suggested_query": "authentication methods",
            "suggested_tags": ["auth", "security"],
            "suggested_entities": ["jwt", "oauth"],
            "reasoning": "Signals: recall request (+4.0), 2 entities (+1.6) | Raw score: 3.6 → Confidence: 0.880",
            "phrase_signals": {"recall_request": True, "past_reference": True},
        }

        analysis = RecallAnalysis(**example)
        assert analysis.should_search is True
        assert analysis.confidence == 0.88
