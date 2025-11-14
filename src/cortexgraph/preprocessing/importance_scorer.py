"""Importance scoring for automatic memory strength calculation.

Calculates memory strength (1.0-2.0) based on content characteristics.

Phase 1 Implementation (v0.6.0):
- Heuristic-based scoring
- Multiple signal types (length, entities, markers, questions)
- Configurable weights and thresholds
"""

from typing import TypedDict


class ImportanceSignals(TypedDict):
    """Component signals for importance calculation."""

    length_score: float  # Based on content length
    entity_score: float  # Based on entity density
    marker_score: float  # Based on importance markers
    question_score: float  # Based on question presence
    final_strength: float  # Combined score (1.0-2.0)


class ImportanceScorer:
    """Calculate memory importance/strength from content characteristics.

    Strength scale:
    - 1.0: Default (no special markers)
    - 1.2-1.4: Moderate importance (entities, length)
    - 1.5-1.7: High importance (markers, questions)
    - 1.8-2.0: Critical importance (explicit markers)
    """

    def __init__(
        self,
        min_strength: float = 1.0,
        max_strength: float = 2.0,
        length_weight: float = 0.2,
        entity_weight: float = 0.3,
        marker_weight: float = 0.4,
        question_weight: float = 0.1,
    ) -> None:
        """Initialize importance scorer.

        Args:
            min_strength: Minimum strength value (default: 1.0)
            max_strength: Maximum strength value (default: 2.0)
            length_weight: Weight for length signal (default: 0.2)
            entity_weight: Weight for entity signal (default: 0.3)
            marker_weight: Weight for marker signal (default: 0.4)
            question_weight: Weight for question signal (default: 0.1)
        """
        self.min_strength = min_strength
        self.max_strength = max_strength
        self.length_weight = length_weight
        self.entity_weight = entity_weight
        self.marker_weight = marker_weight
        self.question_weight = question_weight

        # Normalize weights to sum to 1.0
        total_weight = length_weight + entity_weight + marker_weight + question_weight
        self.length_weight /= total_weight
        self.entity_weight /= total_weight
        self.marker_weight /= total_weight
        self.question_weight /= total_weight

    def score(
        self,
        content: str,
        entities: list[str] | None = None,
        importance_marker: bool = False,
    ) -> float:
        """Calculate memory strength from content.

        Args:
            content: Memory content text
            entities: Extracted entities (optional)
            importance_marker: Whether importance phrase detected

        Returns:
            Strength value between min_strength and max_strength

        Example:
            >>> scorer = ImportanceScorer()
            >>> strength = scorer.score(
            ...     "This is critical: remember API key sk-123",
            ...     entities=["api"],
            ...     importance_marker=True
            ... )
            >>> strength > 1.5
            True
        """
        # Length signal (0.0-1.0)
        # Longer content suggests more detail/importance
        length_score = min(1.0, len(content) / 500)

        # Entity signal (0.0-1.0)
        # More entities = more concrete/specific
        entity_count = len(entities) if entities else 0
        entity_score = min(1.0, entity_count / 5)

        # Marker signal (0.0-1.0)
        # Explicit importance markers trump other signals
        marker_score = 1.0 if importance_marker else 0.0

        # Question signal (0.0-1.0)
        # Questions suggest decision points or uncertainties
        has_question = "?" in content
        question_score = 0.5 if has_question else 0.0

        # Weighted combination
        combined_score = (
            self.length_weight * length_score
            + self.entity_weight * entity_score
            + self.marker_weight * marker_score
            + self.question_weight * question_score
        )

        # Map to strength range
        strength_range = self.max_strength - self.min_strength
        final_strength = self.min_strength + (combined_score * strength_range)

        # Clamp to valid range
        final_strength = max(self.min_strength, min(self.max_strength, final_strength))

        return final_strength

    def get_signals(
        self,
        content: str,
        entities: list[str] | None = None,
        importance_marker: bool = False,
    ) -> ImportanceSignals:
        """Get detailed breakdown of importance signals.

        Args:
            content: Memory content text
            entities: Extracted entities (optional)
            importance_marker: Whether importance phrase detected

        Returns:
            ImportanceSignals with component scores and final strength

        Example:
            >>> scorer = ImportanceScorer()
            >>> signals = scorer.get_signals("Short note")
            >>> signals["length_score"] < 0.1
            True
            >>> signals["final_strength"]
            1.0
        """
        # Calculate individual signals
        length_score = min(1.0, len(content) / 500)
        entity_count = len(entities) if entities else 0
        entity_score = min(1.0, entity_count / 5)
        marker_score = 1.0 if importance_marker else 0.0
        has_question = "?" in content
        question_score = 0.5 if has_question else 0.0

        # Calculate final strength
        combined_score = (
            self.length_weight * length_score
            + self.entity_weight * entity_score
            + self.marker_weight * marker_score
            + self.question_weight * question_score
        )

        strength_range = self.max_strength - self.min_strength
        final_strength = self.min_strength + (combined_score * strength_range)
        final_strength = max(self.min_strength, min(self.max_strength, final_strength))

        return ImportanceSignals(
            length_score=length_score,
            entity_score=entity_score,
            marker_score=marker_score,
            question_score=question_score,
            final_strength=final_strength,
        )
