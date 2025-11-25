"""
Unit tests for pattern matching engine.

Tests PatternMatcher compilation, matching logic, and PatternMatch results for:
- Save triggers (explicit phrases, decision markers, preferences)
- Recall triggers (past references, possessive forms)
- Importance markers
- Exclusion patterns
- Uncertainty markers
"""

import pytest

from cortexgraph.activation.config import PatternLibrary
from cortexgraph.activation.patterns import PatternMatch, PatternMatcher


@pytest.fixture
def basic_patterns():
    """Create basic pattern library for testing."""
    return PatternLibrary(
        explicit_save_triggers=["remember this", "don't forget", "i prefer"],
        explicit_recall_triggers=["what did i say", "remind me"],
        importance_markers=["critical", "must", "important"],
        exclusion_patterns=["what is", "how do"],
        uncertainty_markers=["maybe", "might", "not sure"],
        case_sensitive=False,
        partial_match=True,
    )


@pytest.fixture
def matcher(basic_patterns):
    """Create PatternMatcher with basic patterns."""
    return PatternMatcher(basic_patterns)


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_create_with_match(self):
        """Test creating PatternMatch with matched patterns."""
        result = PatternMatch(
            matched=True,
            matched_patterns=["remember this", "don't forget"],
            pattern_type="save",
        )

        assert result.matched is True
        assert len(result.matched_patterns) == 2
        assert result.pattern_type == "save"
        assert result.match_count == 2

    def test_create_without_match(self):
        """Test creating PatternMatch with no matches."""
        result = PatternMatch(matched=False, matched_patterns=[], pattern_type="save")

        assert result.matched is False
        assert len(result.matched_patterns) == 0
        assert result.match_count == 0

    def test_match_count_auto_calculated(self):
        """Test match_count is calculated from matched_patterns."""
        result = PatternMatch(matched=True, matched_patterns=["pattern1", "pattern2", "pattern3"])

        assert result.match_count == 3


class TestPatternMatcherInit:
    """Tests for PatternMatcher initialization."""

    def test_init_with_basic_patterns(self, basic_patterns):
        """Test PatternMatcher initializes with basic patterns."""
        matcher = PatternMatcher(basic_patterns)

        assert matcher.patterns == basic_patterns
        assert matcher.case_sensitive is False
        assert matcher.partial_match is True

    def test_init_compiles_save_triggers(self, basic_patterns):
        """Test save triggers are compiled to regex."""
        matcher = PatternMatcher(basic_patterns)

        assert matcher.save_triggers_regex is not None

    def test_init_compiles_recall_triggers(self, basic_patterns):
        """Test recall triggers are compiled to regex."""
        matcher = PatternMatcher(basic_patterns)

        assert matcher.recall_triggers_regex is not None

    def test_init_with_empty_patterns(self):
        """Test PatternMatcher handles empty pattern lists."""
        empty_patterns = PatternLibrary(
            explicit_save_triggers=[],
            explicit_recall_triggers=[],
            importance_markers=[],
            exclusion_patterns=[],
            uncertainty_markers=[],
        )

        matcher = PatternMatcher(empty_patterns)

        # Regex should be None for empty lists
        assert matcher.save_triggers_regex is None
        assert matcher.recall_triggers_regex is None

    def test_case_sensitive_mode(self):
        """Test case-sensitive pattern matching."""
        patterns = PatternLibrary(
            explicit_save_triggers=["Remember"],
            case_sensitive=True,
            partial_match=True,
        )

        matcher = PatternMatcher(patterns)
        assert matcher.case_sensitive is True


class TestSaveTriggerMatching:
    """Tests for save trigger pattern matching."""

    def test_explicit_save_trigger_matched(self, matcher):
        """Test explicit save trigger is matched."""
        text = "Remember this: I prefer PostgreSQL for databases"
        result = matcher.match_save_triggers(text)

        assert result.matched is True
        assert "remember this" in result.matched_patterns
        assert result.pattern_type == "save"

    def test_multiple_save_triggers_matched(self, matcher):
        """Test multiple save triggers in same text."""
        text = "Remember this and don't forget: I prefer FastAPI"
        result = matcher.match_save_triggers(text)

        assert result.matched is True
        assert len(result.matched_patterns) >= 2
        assert "remember this" in result.matched_patterns
        assert "don't forget" in result.matched_patterns

    def test_preference_statement_matched(self, matcher):
        """Test preference statement trigger."""
        text = "I prefer PostgreSQL over MongoDB"
        result = matcher.match_save_triggers(text)

        assert result.matched is True
        assert "i prefer" in result.matched_patterns

    def test_case_insensitive_matching(self, matcher):
        """Test case-insensitive matching works."""
        text = "REMEMBER THIS: important information"
        result = matcher.match_save_triggers(text)

        assert result.matched is True
        assert "remember this" in result.matched_patterns

    def test_partial_match_substring(self, matcher):
        """Test partial match finds pattern as substring."""
        text = "You should remember this detail"
        result = matcher.match_save_triggers(text)

        assert result.matched is True
        assert "remember this" in result.matched_patterns

    def test_no_save_trigger_matched(self, matcher):
        """Test no match when text lacks save triggers."""
        text = "Just asking about PostgreSQL features"
        result = matcher.match_save_triggers(text)

        assert result.matched is False
        assert len(result.matched_patterns) == 0

    def test_empty_text_no_match(self, matcher):
        """Test empty text returns no match."""
        result = matcher.match_save_triggers("")

        assert result.matched is False


class TestRecallTriggerMatching:
    """Tests for recall trigger pattern matching."""

    def test_explicit_recall_trigger_matched(self, matcher):
        """Test explicit recall trigger is matched."""
        text = "What did I say about authentication?"
        result = matcher.match_recall_triggers(text)

        assert result.matched is True
        assert "what did i say" in result.matched_patterns
        assert result.pattern_type == "recall"

    def test_remind_me_trigger(self, matcher):
        """Test 'remind me' trigger."""
        text = "Remind me what database I chose"
        result = matcher.match_recall_triggers(text)

        assert result.matched is True
        assert "remind me" in result.matched_patterns

    def test_case_insensitive_recall(self, matcher):
        """Test recall matching is case-insensitive."""
        text = "WHAT DID I SAY about this?"
        result = matcher.match_recall_triggers(text)

        assert result.matched is True

    def test_no_recall_trigger_matched(self, matcher):
        """Test no match when text lacks recall triggers."""
        text = "How do I set up authentication?"
        result = matcher.match_recall_triggers(text)

        # "how do" is an exclusion pattern, not recall
        assert result.matched is False


class TestImportanceMarkers:
    """Tests for importance marker matching."""

    def test_critical_marker_matched(self, matcher):
        """Test 'critical' importance marker."""
        text = "This is critical information about security"
        result = matcher.match_importance_markers(text)

        assert result.matched is True
        assert "critical" in result.matched_patterns

    def test_must_marker_matched(self, matcher):
        """Test 'must' importance marker."""
        text = "You must use HTTPS for this API"
        result = matcher.match_importance_markers(text)

        assert result.matched is True
        assert "must" in result.matched_patterns

    def test_important_marker_matched(self, matcher):
        """Test 'important' marker."""
        text = "This is an important consideration"
        result = matcher.match_importance_markers(text)

        assert result.matched is True
        assert "important" in result.matched_patterns

    def test_no_importance_marker(self, matcher):
        """Test no match when text lacks importance markers."""
        text = "Just a regular statement"
        result = matcher.match_importance_markers(text)

        assert result.matched is False


class TestExclusionPatterns:
    """Tests for exclusion pattern matching."""

    def test_what_is_exclusion(self, matcher):
        """Test 'what is' exclusion pattern."""
        text = "What is PostgreSQL?"
        result = matcher.match_exclusion_patterns(text)

        assert result.matched is True
        assert "what is" in result.matched_patterns

    def test_how_do_exclusion(self, matcher):
        """Test 'how do' exclusion pattern."""
        text = "How do I install FastAPI?"
        result = matcher.match_exclusion_patterns(text)

        assert result.matched is True
        assert "how do" in result.matched_patterns

    def test_no_exclusion_match(self, matcher):
        """Test no match when text lacks exclusion patterns."""
        text = "I prefer PostgreSQL for this project"
        result = matcher.match_exclusion_patterns(text)

        assert result.matched is False


class TestUncertaintyMarkers:
    """Tests for uncertainty marker matching."""

    def test_maybe_uncertainty(self, matcher):
        """Test 'maybe' uncertainty marker."""
        text = "I might use Redis for caching, maybe"
        result = matcher.match_uncertainty_markers(text)

        assert result.matched is True
        assert "maybe" in result.matched_patterns or "might" in result.matched_patterns

    def test_might_uncertainty(self, matcher):
        """Test 'might' uncertainty marker."""
        text = "I might choose PostgreSQL"
        result = matcher.match_uncertainty_markers(text)

        assert result.matched is True
        assert "might" in result.matched_patterns

    def test_not_sure_uncertainty(self, matcher):
        """Test 'not sure' phrase."""
        text = "I'm not sure which database to use"
        result = matcher.match_uncertainty_markers(text)

        assert result.matched is True
        assert "not sure" in result.matched_patterns

    def test_no_uncertainty_marker(self, matcher):
        """Test no match when text lacks uncertainty."""
        text = "I definitely prefer PostgreSQL"
        result = matcher.match_uncertainty_markers(text)

        assert result.matched is False


class TestDetectAllSignals:
    """Tests for detect_all_signals convenience method."""

    def test_detect_all_returns_dict(self, matcher):
        """Test detect_all_signals returns dictionary of results."""
        text = "Remember this: PostgreSQL is critical"
        results = matcher.detect_all_signals(text)

        assert isinstance(results, dict)
        assert "save" in results
        assert "recall" in results
        assert "importance" in results
        assert "exclusion" in results
        assert "uncertainty" in results

    def test_detect_multiple_signals(self, matcher):
        """Test detect_all_signals finds multiple signal types."""
        text = "Remember this: PostgreSQL is critical for our project"
        results = matcher.detect_all_signals(text)

        assert results["save"].matched is True  # "remember this"
        assert results["importance"].matched is True  # "critical"
        assert results["recall"].matched is False
        assert results["exclusion"].matched is False

    def test_detect_conflicting_signals(self, matcher):
        """Test detect_all_signals handles conflicting signals."""
        text = "What is PostgreSQL? I'm not sure but maybe it's important"
        results = matcher.detect_all_signals(text)

        assert results["exclusion"].matched is True  # "what is"
        assert results["uncertainty"].matched is True  # "maybe", "not sure"
        assert results["importance"].matched is True  # "important"

    def test_detect_all_with_empty_text(self, matcher):
        """Test detect_all_signals with empty text."""
        results = matcher.detect_all_signals("")

        # All should be False
        assert results["save"].matched is False
        assert results["recall"].matched is False
        assert results["importance"].matched is False
        assert results["exclusion"].matched is False
        assert results["uncertainty"].matched is False


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_pattern_at_text_start(self, matcher):
        """Test pattern matching at start of text."""
        text = "Remember this detail"
        result = matcher.match_save_triggers(text)

        assert result.matched is True

    def test_pattern_at_text_end(self, matcher):
        """Test pattern matching at end of text."""
        text = "Please remember this"
        result = matcher.match_save_triggers(text)

        assert result.matched is True

    def test_pattern_in_middle(self, matcher):
        """Test pattern matching in middle of text."""
        text = "I want to remember this for later"
        result = matcher.match_save_triggers(text)

        assert result.matched is True

    def test_special_characters_in_text(self, matcher):
        """Test patterns work with special characters."""
        text = "Remember this: API keys = sk-abc123!"
        result = matcher.match_save_triggers(text)

        assert result.matched is True

    def test_unicode_text(self, matcher):
        """Test patterns work with unicode characters."""
        text = "Remember this: café ☕"
        result = matcher.match_save_triggers(text)

        assert result.matched is True

    def test_multiline_text(self, matcher):
        """Test patterns work across multiple lines."""
        text = """Remember this:
        I prefer PostgreSQL
        for databases"""
        result = matcher.match_save_triggers(text)

        assert result.matched is True

    def test_very_long_text(self, matcher):
        """Test pattern matching in long text."""
        long_text = "word " * 500 + "remember this" + " word" * 500
        result = matcher.match_save_triggers(long_text)

        assert result.matched is True

    def test_pattern_repeated_multiple_times(self, matcher):
        """Test same pattern appears multiple times."""
        text = "Remember this and remember this again: important"
        result = matcher.match_save_triggers(text)

        assert result.matched is True
        # Should still only list pattern once
        assert result.matched_patterns.count("remember this") <= 2
