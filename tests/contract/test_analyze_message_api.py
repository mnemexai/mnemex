"""
Contract tests for analyze_message MCP tool.

These tests validate the API contract (JSON schema) of the analyze_message tool,
ensuring consistent response structure regardless of internal implementation.

Contract guarantees:
- Response contains required fields: should_save, confidence, suggested_entities,
  suggested_tags, suggested_strength, reasoning
- Field types are correct (bool, float, list, str)
- Confidence is bounded [0.0, 1.0]
- Strength is bounded [1.0, 2.0]
- Explicit save triggers yield high confidence (>=0.7)
"""

from cortexgraph.tools.analyze_message import analyze_message


class TestAnalyzeMessageContract:
    """Contract tests for analyze_message API schema."""

    def test_response_contains_required_fields(self):
        """Contract: Response must contain all required fields."""
        result = analyze_message("Test message")

        # Required fields
        assert "should_save" in result
        assert "confidence" in result
        assert "suggested_entities" in result
        assert "suggested_tags" in result
        assert "suggested_strength" in result
        assert "reasoning" in result

    def test_field_types_are_correct(self):
        """Contract: Field types must match specification."""
        result = analyze_message("I prefer PostgreSQL for databases")

        assert isinstance(result["should_save"], bool)
        assert isinstance(result["confidence"], float)
        assert isinstance(result["suggested_entities"], list)
        assert isinstance(result["suggested_tags"], list)
        assert isinstance(result["suggested_strength"], (int, float))
        assert isinstance(result["reasoning"], str)

    def test_confidence_bounded_zero_to_one(self):
        """Contract: Confidence must be in range [0.0, 1.0]."""
        # Test with various inputs
        messages = [
            "Hello",
            "Remember this: important info",
            "What is Python?",
            "I prefer PostgreSQL for databases",
            "This is critical security information",
        ]

        for message in messages:
            result = analyze_message(message)
            assert 0.0 <= result["confidence"] <= 1.0, (
                f"Confidence {result['confidence']} out of bounds for: {message}"
            )

    def test_strength_bounded_one_to_two(self):
        """Contract: Strength must be in range [1.0, 2.0]."""
        messages = [
            "Hello",
            "Remember this: important info",
            "I prefer PostgreSQL for databases",
        ]

        for message in messages:
            result = analyze_message(message)
            assert 1.0 <= result["suggested_strength"] <= 2.0, (
                f"Strength {result['suggested_strength']} out of bounds for: {message}"
            )

    def test_entities_are_strings(self):
        """Contract: Entities list must contain only strings."""
        result = analyze_message("I use PostgreSQL and MongoDB for my projects")

        for entity in result["suggested_entities"]:
            assert isinstance(entity, str)

    def test_tags_are_strings(self):
        """Contract: Tags list must contain only strings."""
        result = analyze_message("Remember this: database preferences")

        for tag in result["suggested_tags"]:
            assert isinstance(tag, str)


class TestExplicitSaveRequestContract:
    """Contract tests for explicit save request detection."""

    def test_remember_this_triggers_high_confidence(self):
        """Contract: 'Remember this' yields should_save=True with confidence >= 0.7."""
        result = analyze_message("Remember this: I prefer PostgreSQL for databases")

        assert result["should_save"] is True
        assert result["confidence"] >= 0.7

    def test_dont_forget_triggers_high_confidence(self):
        """Contract: 'Don't forget' yields should_save=True with confidence >= 0.7."""
        result = analyze_message("Don't forget: my API key format is sk-xxx")

        assert result["should_save"] is True
        assert result["confidence"] >= 0.7

    def test_i_prefer_with_entity_triggers_save_detection(self):
        """Contract: 'I prefer [entity]' yields should_save=True (preference detection).

        Note: Preferences require recognizable entities to trigger save.
        Per acceptance criteria: "I prefer PostgreSQL for databases" → should_save=True

        Implemented in v0.7.5 via activation module integration with 'i prefer'
        pattern in explicit_save_triggers and preference_statement signal weight.
        """
        result = analyze_message("I prefer PostgreSQL for my databases")

        assert result["should_save"] is True
        # Preferences with entities have medium-high confidence
        assert result["confidence"] >= 0.5
        # Entity should be extracted
        assert any("postgresql" in e.lower() for e in result["suggested_entities"])

    def test_explicit_trigger_includes_phrase_signals(self):
        """Contract: Response includes phrase_signals for transparency."""
        result = analyze_message("Remember this: important configuration")

        # phrase_signals may be optional but if present, should have structure
        if "phrase_signals" in result:
            assert isinstance(result["phrase_signals"], dict)
            # Common signals to check
            if "save_request" in result["phrase_signals"]:
                assert isinstance(result["phrase_signals"]["save_request"], bool)


class TestEntityExtractionContract:
    """Contract tests for entity extraction in analyze_message."""

    def test_technology_names_extracted(self):
        """Contract: Technology names should be extracted as entities."""
        result = analyze_message("I use PostgreSQL and FastAPI for my backend")

        entities_lower = [e.lower() for e in result["suggested_entities"]]
        # At least one tech name should be extracted
        assert any(tech in entities_lower for tech in ["postgresql", "fastapi"])

    def test_multiple_entities_detected(self):
        """Contract: Multiple entities in message are all extracted."""
        result = analyze_message("Remember: Python, TypeScript, and Rust are my favorites")

        # Should extract multiple entities
        assert len(result["suggested_entities"]) >= 2

    def test_empty_message_returns_empty_entities(self):
        """Contract: Empty message returns empty entity list."""
        result = analyze_message("")

        assert result["suggested_entities"] == []
        assert result["should_save"] is False


class TestReasoningContract:
    """Contract tests for reasoning explanation."""

    def test_reasoning_is_non_empty_string(self):
        """Contract: Reasoning must be non-empty explanatory string."""
        result = analyze_message("I prefer PostgreSQL")

        assert len(result["reasoning"]) > 0
        # Reasoning should explain the decision
        assert any(
            word in result["reasoning"].lower()
            for word in [
                "detect",
                "signal",
                "entity",
                "importance",
                "request",
                "marker",
                "preference",
            ]
        )

    def test_reasoning_mentions_entities_when_present(self):
        """Contract: Reasoning mentions entities when they affect decision."""
        result = analyze_message("Remember: PostgreSQL and Redis are my database choices")

        if result["suggested_entities"]:
            # Reasoning should reference entities (may say "Entities:" or list them)
            assert "entit" in result["reasoning"].lower() or any(
                e.lower() in result["reasoning"].lower() for e in result["suggested_entities"][:3]
            )


class TestEdgeCasesContract:
    """Contract tests for edge cases and error handling."""

    def test_empty_string_handled(self):
        """Contract: Empty string returns valid response without error."""
        result = analyze_message("")

        assert "should_save" in result
        assert result["should_save"] is False
        assert result["confidence"] >= 0.0

    def test_very_long_message_handled(self):
        """Contract: Very long messages are handled without error."""
        long_message = "Remember this: " + "PostgreSQL " * 500

        result = analyze_message(long_message)

        assert "should_save" in result
        assert isinstance(result["confidence"], float)

    def test_unicode_message_handled(self):
        """Contract: Unicode characters are handled correctly."""
        result = analyze_message("I prefer PostgreSQL for my café database ☕")

        assert "should_save" in result
        assert isinstance(result["confidence"], float)

    def test_special_characters_handled(self):
        """Contract: Special characters don't break analysis."""
        result = analyze_message("Remember: API key = sk-abc123!@#$%^&*()")

        assert "should_save" in result
        assert isinstance(result["confidence"], float)

    def test_multiline_message_handled(self):
        """Contract: Multiline messages are handled correctly."""
        multiline = """Remember this:
        I prefer PostgreSQL
        for all databases"""

        result = analyze_message(multiline)

        assert "should_save" in result
        assert result["should_save"] is True
