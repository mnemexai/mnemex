"""Phrase detection for conversational memory activation.

Detects explicit save/recall requests and importance markers in natural language.

Phase 1 Implementation (v0.6.0):
- Regex-based pattern matching
- Three signal types: save_request, recall_request, importance_marker
- Confidence scoring based on phrase specificity
"""

import re
from typing import TypedDict


class PhraseSignals(TypedDict):
    """Detection signals from phrase analysis."""

    save_request: bool  # Explicit request to save/remember
    recall_request: bool  # Explicit request to recall/retrieve
    importance_marker: bool  # Importance indicator detected
    matched_phrases: list[str]  # Phrases that matched
    confidence: float  # 0.0-1.0 confidence in detection


class PhraseDetector:
    """Detect memory-related phrases in natural language.

    Examples of detected patterns:
    - Save requests: "remember this", "don't forget", "keep in mind"
    - Recall requests: "what did I say about", "recall when", "remind me"
    - Importance: "this is important", "critical that", "key point"
    """

    def __init__(self) -> None:
        """Initialize phrase patterns."""
        # Explicit save requests (high confidence)
        self.save_patterns = [
            r"\bremember this\b",
            r"\bdon't forget\b",
            r"\bkeep in mind\b",
            r"\bmake a note\b",
            r"\bsave this\b",
            r"\bstore this\b",
            r"\brecord that\b",
            r"\bI should remember\b",
            r"\blet's remember\b",
        ]

        # Explicit recall requests (high confidence)
        self.recall_patterns = [
            r"\bwhat did I say about\b",
            r"\bwhat do you remember about\b",
            r"\brecall when\b",
            r"\bremind me\b",
            r"\bdo you remember\b",
            r"\bhave I mentioned\b",
            r"\bdid I tell you about\b",
            r"\bwhat have I said about\b",
        ]

        # Importance markers (medium confidence)
        self.importance_patterns = [
            r"\bthis is important\b",
            r"\bthis is critical\b",
            r"\bkey point\b",
            r"\bcrucial that\b",
            r"\bvital that\b",
            r"\bessential that\b",
            r"\bmust remember\b",
            r"\bdon't want to forget\b",
        ]

        # Compile for performance
        self.save_regex = re.compile("|".join(self.save_patterns), re.IGNORECASE)
        self.recall_regex = re.compile("|".join(self.recall_patterns), re.IGNORECASE)
        self.importance_regex = re.compile("|".join(self.importance_patterns), re.IGNORECASE)

    def detect(self, text: str) -> PhraseSignals:
        """Detect memory-related phrases in text.

        Args:
            text: Natural language text to analyze

        Returns:
            PhraseSignals with detection results and confidence

        Example:
            >>> detector = PhraseDetector()
            >>> signals = detector.detect("Remember this API key: sk-123")
            >>> signals["save_request"]
            True
            >>> signals["confidence"]
            0.9
        """
        save_matches = self.save_regex.findall(text)
        recall_matches = self.recall_regex.findall(text)
        importance_matches = self.importance_regex.findall(text)

        all_matches = save_matches + recall_matches + importance_matches

        # Calculate confidence based on pattern specificity
        confidence = 0.0
        if save_matches or recall_matches:
            # Explicit requests are high confidence
            confidence = 0.9
        elif importance_matches:
            # Importance markers are medium confidence
            confidence = 0.6

        return PhraseSignals(
            save_request=len(save_matches) > 0,
            recall_request=len(recall_matches) > 0,
            importance_marker=len(importance_matches) > 0,
            matched_phrases=all_matches,
            confidence=confidence,
        )

    def add_pattern(self, pattern: str, pattern_type: str = "save") -> None:
        """Add custom pattern at runtime.

        Args:
            pattern: Regex pattern to add
            pattern_type: "save", "recall", or "importance"

        Example:
            >>> detector = PhraseDetector()
            >>> detector.add_pattern(r"\\bstore in memory\\b", "save")
        """
        if pattern_type == "save":
            self.save_patterns.append(pattern)
            self.save_regex = re.compile("|".join(self.save_patterns), re.IGNORECASE)
        elif pattern_type == "recall":
            self.recall_patterns.append(pattern)
            self.recall_regex = re.compile("|".join(self.recall_patterns), re.IGNORECASE)
        elif pattern_type == "importance":
            self.importance_patterns.append(pattern)
            self.importance_regex = re.compile("|".join(self.importance_patterns), re.IGNORECASE)
        else:
            raise ValueError(
                f"Unknown pattern_type: {pattern_type}. Must be 'save', 'recall', or 'importance'"
            )
