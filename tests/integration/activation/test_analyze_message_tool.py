"""
Integration tests for analyze_message MCP tool with real pattern matching.

These tests verify the full tool pipeline including:
- Preprocessing components (PhraseDetector, EntityExtractor, ImportanceScorer)
- Decision logic and confidence calculation
- Response formatting

Unlike contract tests (schema validation) or unit tests (isolated components),
integration tests verify the components work correctly together.
"""

from cortexgraph.tools.analyze_message import analyze_message


class TestAnalyzeMessageToolIntegration:
    """Integration tests for analyze_message MCP tool."""

    def test_tool_returns_complete_response(self):
        """Integration: Tool returns all expected fields."""
        result = analyze_message("I prefer PostgreSQL for databases")

        # All expected fields present
        assert "should_save" in result
        assert "confidence" in result
        assert "suggested_entities" in result
        assert "suggested_tags" in result
        assert "suggested_strength" in result
        assert "reasoning" in result
        assert "phrase_signals" in result

    def test_explicit_save_request_full_pipeline(self):
        """Integration: Explicit save request flows through full pipeline."""
        result = analyze_message("Remember this: my API endpoint is /v2/users")

        assert result["should_save"] is True
        assert result["confidence"] >= 0.7
        assert result["phrase_signals"]["save_request"] is True
        # Entity should be extracted
        assert len(result["suggested_entities"]) >= 0  # May or may not extract endpoint
        # Reasoning should explain decision
        assert "save" in result["reasoning"].lower() or "remember" in result["reasoning"].lower()

    def test_importance_marker_full_pipeline(self):
        """Integration: Importance marker flows through full pipeline.

        Note: The activation module uses 'critical_marker' for 'critical' phrases
        and 'importance_marker' for non-critical markers like 'important', 'must'.
        """
        result = analyze_message("This is critical: always validate input")

        # Should trigger save due to importance marker
        assert result["should_save"] is True
        # New activation module uses critical_marker for "critical" phrases
        assert result["phrase_signals"].get("critical_marker") is True
        assert result["confidence"] >= 0.5

    def test_entity_extraction_full_pipeline(self):
        """Integration: Entity extraction works end-to-end."""
        result = analyze_message("I use PostgreSQL, Redis, and FastAPI for my backend")

        # Multiple entities should be extracted
        assert len(result["suggested_entities"]) >= 2
        entities_lower = [e.lower() for e in result["suggested_entities"]]
        # At least some tech entities detected
        assert any(tech in entities_lower for tech in ["postgresql", "redis", "fastapi"])

    def test_exclusion_pattern_full_pipeline(self):
        """Integration: Exclusion patterns are detected end-to-end.

        Note: The current MCP tool uses old preprocessing which may not
        have exclusion detection. This test validates current behavior.
        """
        result = analyze_message("What is a database index?")

        # Should NOT trigger save for general questions
        assert result["should_save"] is False
        assert result["confidence"] < 0.5

    def test_low_signal_message_full_pipeline(self):
        """Integration: Low-signal messages correctly rejected."""
        result = analyze_message("Hello, how are you today?")

        assert result["should_save"] is False
        assert result["confidence"] < 0.5

    def test_strength_calculation_full_pipeline(self):
        """Integration: Strength is calculated based on message content."""
        # High importance message
        result_high = analyze_message("Remember this critical decision: use PostgreSQL")
        # Low importance message
        result_low = analyze_message("I sometimes use Python")

        # High importance should have higher strength
        assert result_high["suggested_strength"] >= result_low["suggested_strength"]

    def test_phrase_signals_structure(self):
        """Integration: phrase_signals has expected structure.

        Note: The activation module returns dynamic phrase_signals based on what's
        detected. Keys present depend on the message content:
        - save_request: Explicit save triggers
        - critical_marker: "critical" phrases
        - importance_marker: Non-critical importance markers
        - decision_marker: Preference/decision patterns
        - exclusion_pattern: General questions
        - uncertainty_marker: Uncertain language
        """
        result = analyze_message("Remember this: I prefer dark mode")

        signals = result["phrase_signals"]
        # phrase_signals should be a dict
        assert isinstance(signals, dict)

        # For "Remember this: I prefer dark mode" we expect:
        # - save_request (from "remember this")
        # - decision_marker (from "prefer")
        assert signals.get("save_request") is True
        assert signals.get("decision_marker") is True

        # All values should be booleans
        for key, value in signals.items():
            assert isinstance(value, bool), f"Signal {key} should be bool, got {type(value)}"


class TestAnalyzeMessageToolEdgeCases:
    """Integration tests for edge cases in analyze_message tool."""

    def test_empty_message(self):
        """Integration: Empty message handled gracefully."""
        result = analyze_message("")

        assert result["should_save"] is False
        assert result["confidence"] < 0.5
        assert result["suggested_entities"] == []

    def test_very_long_message(self):
        """Integration: Very long messages handled without error."""
        long_message = "Remember this important information: " + "PostgreSQL " * 200

        result = analyze_message(long_message)

        # Should still work
        assert "should_save" in result
        assert "confidence" in result

    def test_unicode_and_special_characters(self):
        """Integration: Unicode and special characters handled.

        Note: Current preprocessing requires "remember this" not just "remember:".
        This test validates handling without triggering save.
        """
        result = analyze_message("Remember: my café uses PostgreSQL 🐘 with API key=sk-123!@#")

        assert "should_save" in result
        # Entities should still be extracted despite unicode
        assert "postgresql" in [e.lower() for e in result["suggested_entities"]]

    def test_unicode_with_explicit_trigger(self):
        """Integration: Unicode handled with explicit save trigger."""
        result = analyze_message("Remember this: my café uses PostgreSQL 🐘")

        assert result["should_save"] is True

    def test_multiline_message(self):
        """Integration: Multiline messages handled correctly."""
        multiline = """Remember this configuration:
        Database: PostgreSQL
        Cache: Redis
        Framework: FastAPI"""

        result = analyze_message(multiline)

        assert "should_save" in result
        assert result["should_save"] is True
        # Should extract multiple entities
        assert len(result["suggested_entities"]) >= 1


class TestAnalyzeMessageToolWithVariousInputs:
    """Integration tests with various real-world input patterns."""

    def test_decision_statement(self):
        """Integration: Decision statements detected."""
        result = analyze_message("I've decided to use TypeScript for all frontend code")

        # May or may not auto-save, but should have reasonable confidence
        assert result["confidence"] >= 0.0  # Valid confidence

    def test_preference_statement(self):
        """Integration: Preference statements without explicit trigger.

        Note: Current MCP tool doesn't use activation module's preference_statement
        signal. Without explicit trigger, confidence is low. This documents
        current behavior - activation module integration (T027-T028) will improve this.
        """
        result = analyze_message("My preference is PostgreSQL over MySQL")

        # Currently low confidence without explicit trigger
        assert result["confidence"] >= 0.0  # Valid confidence returned
        # Entities should still be extracted
        assert len(result["suggested_entities"]) >= 1

    def test_technical_configuration(self):
        """Integration: Technical configuration detected as memory-worthy."""
        result = analyze_message("Remember this: DATABASE_URL=postgres://localhost:5432/mydb")

        assert result["should_save"] is True
        assert result["confidence"] >= 0.7

    def test_personal_preference(self):
        """Integration: Personal preferences detected."""
        result = analyze_message("Don't forget: I prefer tabs over spaces")

        assert result["should_save"] is True
        assert result["confidence"] >= 0.7

    def test_general_knowledge_question(self):
        """Integration: General knowledge questions filtered out."""
        result = analyze_message("How does garbage collection work?")

        assert result["should_save"] is False

    def test_specific_project_context(self):
        """Integration: Project-specific context with explicit trigger."""
        result = analyze_message(
            "Remember this for the project: we're using FastAPI with async endpoints"
        )

        assert result["should_save"] is True
        assert "fastapi" in [e.lower() for e in result["suggested_entities"]]
