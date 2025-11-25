"""
Pattern matching engine for natural language activation.

This module implements efficient pattern matching for trigger phrase detection.
Uses compiled regex patterns for performance (<20ms target).
"""

import re
from dataclasses import dataclass

from cortexgraph.activation.config import PatternLibrary


@dataclass
class PatternMatch:
    """Result of pattern matching.

    Attributes:
        matched: Whether any patterns matched
        matched_patterns: List of patterns that matched (empty if no match)
        pattern_type: Type of patterns matched (e.g., "explicit_save", "recall")
        match_count: Number of patterns matched
    """

    matched: bool
    matched_patterns: list[str]
    pattern_type: str = ""
    match_count: int = 0

    def __post_init__(self) -> None:
        """Calculate match_count from matched_patterns."""
        if not self.match_count:
            self.match_count = len(self.matched_patterns)


class PatternMatcher:
    """Efficient pattern matching engine.

    Compiles pattern lists into regex for fast matching. Supports
    case-insensitive and partial matching based on PatternLibrary config.

    Performance: <20ms for typical message analysis
    """

    def __init__(self, patterns: PatternLibrary) -> None:
        """Initialize pattern matcher with compiled regex.

        Args:
            patterns: Pattern library from configuration
        """
        self.patterns = patterns
        self.case_sensitive = patterns.case_sensitive
        self.partial_match = patterns.partial_match

        # Compile regex for each pattern category
        regex_flags = 0 if patterns.case_sensitive else re.IGNORECASE

        self.save_triggers_regex = self._compile_patterns(
            patterns.explicit_save_triggers, regex_flags
        )
        self.recall_triggers_regex = self._compile_patterns(
            patterns.explicit_recall_triggers, regex_flags
        )
        self.importance_regex = self._compile_patterns(patterns.importance_markers, regex_flags)
        self.exclusion_regex = self._compile_patterns(patterns.exclusion_patterns, regex_flags)
        self.uncertainty_regex = self._compile_patterns(patterns.uncertainty_markers, regex_flags)

    def _compile_patterns(self, pattern_list: list[str], flags: int) -> re.Pattern[str] | None:
        """Compile list of patterns into single regex.

        Args:
            pattern_list: List of literal string patterns
            flags: Regex flags (re.IGNORECASE, etc.)

        Returns:
            Compiled regex pattern or None if empty list
        """
        if not pattern_list:
            return None

        # Escape special regex characters in patterns
        escaped = [re.escape(p) for p in pattern_list]

        # Build regex:
        # - Partial match: pattern can appear anywhere
        # - Exact match: pattern must be whole word(s)
        if self.partial_match:
            # Just OR together the patterns
            regex_str = "|".join(escaped)
        else:
            # Require word boundaries around each pattern
            regex_str = "|".join(rf"\b{p}\b" for p in escaped)

        return re.compile(regex_str, flags)

    def match_save_triggers(self, text: str) -> PatternMatch:
        """Match explicit save trigger phrases.

        Args:
            text: User message to analyze

        Returns:
            PatternMatch with matched save triggers

        Example:
            >>> matcher = PatternMatcher(patterns)
            >>> result = matcher.match_save_triggers("Remember this: I prefer PostgreSQL")
            >>> result.matched
            True
            >>> "remember this" in result.matched_patterns
            True
        """
        return self._match_category(
            text, self.save_triggers_regex, self.patterns.explicit_save_triggers, "save"
        )

    def match_recall_triggers(self, text: str) -> PatternMatch:
        """Match explicit recall trigger phrases.

        Args:
            text: User query to analyze

        Returns:
            PatternMatch with matched recall triggers
        """
        return self._match_category(
            text,
            self.recall_triggers_regex,
            self.patterns.explicit_recall_triggers,
            "recall",
        )

    def match_importance_markers(self, text: str) -> PatternMatch:
        """Match importance marker words.

        Args:
            text: Text to analyze

        Returns:
            PatternMatch with matched importance markers
        """
        return self._match_category(
            text, self.importance_regex, self.patterns.importance_markers, "importance"
        )

    def match_exclusion_patterns(self, text: str) -> PatternMatch:
        """Match exclusion patterns (general questions).

        Args:
            text: Text to analyze

        Returns:
            PatternMatch with matched exclusion patterns
        """
        return self._match_category(
            text, self.exclusion_regex, self.patterns.exclusion_patterns, "exclusion"
        )

    def match_uncertainty_markers(self, text: str) -> PatternMatch:
        """Match uncertainty marker words.

        Args:
            text: Text to analyze

        Returns:
            PatternMatch with matched uncertainty markers
        """
        return self._match_category(
            text,
            self.uncertainty_regex,
            self.patterns.uncertainty_markers,
            "uncertainty",
        )

    def _match_category(
        self,
        text: str,
        regex: re.Pattern[str] | None,
        original_patterns: list[str],
        category: str,
    ) -> PatternMatch:
        """Match text against a pattern category.

        Args:
            text: Text to search
            regex: Compiled regex (or None if no patterns)
            original_patterns: Original pattern strings
            category: Pattern category name

        Returns:
            PatternMatch with results
        """
        if regex is None or not text:
            return PatternMatch(matched=False, matched_patterns=[], pattern_type=category)

        # Find all matches
        matches = regex.findall(text)

        if not matches:
            return PatternMatch(matched=False, matched_patterns=[], pattern_type=category)

        # Normalize matches to lowercase for comparison
        normalized_matches = [m.lower() for m in matches]

        # Map back to original pattern strings
        matched_patterns = []
        for pattern in original_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in normalized_matches or any(
                pattern_lower in match for match in normalized_matches
            ):
                matched_patterns.append(pattern)

        return PatternMatch(
            matched=len(matched_patterns) > 0,
            matched_patterns=matched_patterns,
            pattern_type=category,
        )

    def detect_all_signals(self, text: str) -> dict[str, PatternMatch]:
        """Detect all signal types in text.

        Convenience method that runs all pattern matchers and returns
        results in a dictionary.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping signal type to PatternMatch:
            {
                "save": PatternMatch(...),
                "recall": PatternMatch(...),
                "importance": PatternMatch(...),
                "exclusion": PatternMatch(...),
                "uncertainty": PatternMatch(...)
            }
        """
        return {
            "save": self.match_save_triggers(text),
            "recall": self.match_recall_triggers(text),
            "importance": self.match_importance_markers(text),
            "exclusion": self.match_exclusion_patterns(text),
            "uncertainty": self.match_uncertainty_markers(text),
        }
