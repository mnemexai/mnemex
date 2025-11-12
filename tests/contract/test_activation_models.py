"""Contract tests for activation Pydantic models."""

import pytest
from pydantic import ValidationError

from cortexgraph.storage.models import (
    ActivationContext,
    ActivationResult,
    ActivationScore,
    ActivationSource,
    Memory,
    MemoryMetadata,
)


class TestActivationContextContract:
    """Test ActivationContext model contract."""

    def test_activation_context_required_fields(self) -> None:
        """Test that message is required."""
        with pytest.raises(ValidationError):
            ActivationContext()  # type: ignore

        # Minimum valid context
        ctx = ActivationContext(message="test query")
        assert ctx.message == "test query"
        assert ctx.keywords == []
        assert ctx.session_id is None
        assert ctx.already_activated == set()

    def test_activation_context_defaults(self) -> None:
        """Test default values for optional fields."""
        ctx = ActivationContext(message="test")
        assert ctx.max_memories == 10
        assert ctx.activation_threshold == 0.5
        assert ctx.enable_spreading is True

    def test_activation_context_validation_max_memories(self) -> None:
        """Test max_memories validation (1-100 range)."""
        # Valid ranges
        ctx1 = ActivationContext(message="test", max_memories=1)
        assert ctx1.max_memories == 1

        ctx2 = ActivationContext(message="test", max_memories=100)
        assert ctx2.max_memories == 100

        # Invalid ranges
        with pytest.raises(ValidationError):
            ActivationContext(message="test", max_memories=0)

        with pytest.raises(ValidationError):
            ActivationContext(message="test", max_memories=101)

    def test_activation_context_validation_threshold(self) -> None:
        """Test activation_threshold validation (0.0-1.0 range)."""
        # Valid ranges
        ctx1 = ActivationContext(message="test", activation_threshold=0.0)
        assert ctx1.activation_threshold == 0.0

        ctx2 = ActivationContext(message="test", activation_threshold=1.0)
        assert ctx2.activation_threshold == 1.0

        # Invalid ranges
        with pytest.raises(ValidationError):
            ActivationContext(message="test", activation_threshold=-0.1)

        with pytest.raises(ValidationError):
            ActivationContext(message="test", activation_threshold=1.1)

    def test_activation_context_keywords_max_length(self) -> None:
        """Test keywords max_length constraint."""
        # Valid: 20 keywords
        keywords = [f"keyword{i}" for i in range(20)]
        ctx = ActivationContext(message="test", keywords=keywords)
        assert len(ctx.keywords) == 20

        # Invalid: 21 keywords (exceeds max_length=20)
        with pytest.raises(ValidationError):
            keywords_too_many = [f"keyword{i}" for i in range(21)]
            ActivationContext(message="test", keywords=keywords_too_many)

    def test_activation_context_mutable(self) -> None:
        """Test that context is mutable (frozen=False)."""
        ctx = ActivationContext(message="test")

        # Should be able to modify
        ctx.keywords = ["new", "keywords"]
        ctx.already_activated.add("mem1")

        assert ctx.keywords == ["new", "keywords"]
        assert "mem1" in ctx.already_activated


class TestActivationScoreContract:
    """Test ActivationScore model contract."""

    def test_activation_score_required_fields(self) -> None:
        """Test required fields for ActivationScore."""
        with pytest.raises(ValidationError):
            ActivationScore()  # type: ignore

        # Minimum valid score
        score = ActivationScore(
            memory_id="mem1",
            base_relevance=0.8,
            temporal_score=0.6,
            final_score=0.7,
            source=ActivationSource.DIRECT,
        )
        assert score.memory_id == "mem1"
        assert score.spreading_score == 0.0  # Default

    def test_activation_score_validation_ranges(self) -> None:
        """Test score validation (all 0.0-1.0)."""
        # Valid ranges
        score = ActivationScore(
            memory_id="mem1",
            base_relevance=1.0,
            temporal_score=1.0,
            spreading_score=1.0,
            final_score=1.0,
            source=ActivationSource.DIRECT,
        )
        assert score.base_relevance == 1.0

        # Invalid ranges
        with pytest.raises(ValidationError):
            ActivationScore(
                memory_id="mem1",
                base_relevance=-0.1,  # Invalid
                temporal_score=0.5,
                final_score=0.5,
                source=ActivationSource.DIRECT,
            )

        with pytest.raises(ValidationError):
            ActivationScore(
                memory_id="mem1",
                base_relevance=0.5,
                temporal_score=1.1,  # Invalid
                final_score=0.5,
                source=ActivationSource.DIRECT,
            )

    def test_activation_score_calculate_method(self) -> None:
        """Test ActivationScore.calculate() class method."""
        score = ActivationScore.calculate(
            memory_id="mem1",
            base_relevance=0.8,
            temporal_score=0.6,
            spreading_score=0.4,
            source=ActivationSource.SPREAD_1HOP,
            matched_keywords=["python", "testing"],
        )

        # Verify formula: 0.5*base + 0.3*temporal + 0.2*spreading
        expected = 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4
        assert score.final_score == pytest.approx(expected)
        assert score.source == ActivationSource.SPREAD_1HOP
        assert score.matched_keywords == ["python", "testing"]

    def test_activation_score_calculate_caps_at_1_0(self) -> None:
        """Test that calculate() caps final_score at 1.0."""
        # All max values would exceed 1.0 without capping
        score = ActivationScore.calculate(
            memory_id="mem1",
            base_relevance=1.0,
            temporal_score=1.0,
            spreading_score=1.0,
        )

        assert score.final_score == 1.0  # Capped, not 1.0 (0.5+0.3+0.2)

    def test_activation_score_immutable(self) -> None:
        """Test that score is immutable (frozen=True)."""
        score = ActivationScore.calculate(memory_id="mem1", base_relevance=0.8, temporal_score=0.6)

        # Should not be able to modify
        with pytest.raises(ValidationError):
            score.final_score = 0.9  # type: ignore


class TestActivationResultContract:
    """Test ActivationResult model contract."""

    def test_activation_result_defaults(self) -> None:
        """Test default values for ActivationResult."""
        result = ActivationResult()

        assert result.activated_memories == []
        assert result.activation_scores == {}
        assert result.direct_matches == []
        assert result.spread_matches == []
        assert result.total_candidates == 0
        assert result.activation_latency_ms == 0.0
        assert result.timing_breakdown == {}
        assert result.fallback_tier == "full"

    def test_activation_result_validation(self) -> None:
        """Test validation constraints."""
        # Valid result
        result = ActivationResult(
            activated_memories=["mem1", "mem2"],
            total_candidates=10,
            activation_latency_ms=25.5,
        )
        assert len(result.activated_memories) == 2

        # Invalid: negative values
        with pytest.raises(ValidationError):
            ActivationResult(total_candidates=-1)

        with pytest.raises(ValidationError):
            ActivationResult(activation_latency_ms=-5.0)

    def test_activation_result_format_for_context(self) -> None:
        """Test format_for_context() method."""
        memories = [
            Memory(
                id="mem1",
                content="Python is great for machine learning and data science applications",
                meta=MemoryMetadata(tags=["python", "ml"]),
            ),
            Memory(
                id="mem2",
                content="TypeScript provides type safety",
                meta=MemoryMetadata(tags=["typescript"]),
            ),
        ]

        score1 = ActivationScore.calculate(memory_id="mem1", base_relevance=0.8, temporal_score=0.7)
        score2 = ActivationScore.calculate(memory_id="mem2", base_relevance=0.6, temporal_score=0.5)

        result = ActivationResult(
            activated_memories=["mem1", "mem2"],
            activation_scores={"mem1": score1, "mem2": score2},
        )

        formatted = result.format_for_context(memories)

        # Should contain memory content (truncated)
        assert "Python is great for machine learning" in formatted
        assert "TypeScript provides type safety" in formatted

        # Should contain relevance scores
        assert "relevance:" in formatted

        # Should contain tags
        assert "python" in formatted or "ml" in formatted

    def test_activation_result_format_empty(self) -> None:
        """Test format_for_context() with no activated memories."""
        result = ActivationResult(activated_memories=[])
        formatted = result.format_for_context([])

        assert formatted == ""

    def test_activation_result_format_truncates_long_content(self) -> None:
        """Test that format_for_context() truncates long memory content."""
        long_content = "A" * 300  # 300 characters
        memories = [
            Memory(
                id="mem1",
                content=long_content,
                meta=MemoryMetadata(),
            )
        ]

        score = ActivationScore.calculate(memory_id="mem1", base_relevance=0.8, temporal_score=0.7)

        result = ActivationResult(
            activated_memories=["mem1"],
            activation_scores={"mem1": score},
        )

        formatted = result.format_for_context(memories)

        # Content should be truncated to 200 chars + "..."
        assert len(long_content) == 300
        assert "A" * 200 in formatted
        assert "..." in formatted
        assert "A" * 300 not in formatted  # Full content not present

    def test_activation_result_format_limits_to_top_5(self) -> None:
        """Test that format_for_context() only shows top 5 memories."""
        memories = [Memory(id=f"mem{i}", content=f"Content {i}") for i in range(10)]

        scores = {
            f"mem{i}": ActivationScore.calculate(
                memory_id=f"mem{i}", base_relevance=0.5, temporal_score=0.5
            )
            for i in range(10)
        }

        result = ActivationResult(
            activated_memories=[f"mem{i}" for i in range(10)],
            activation_scores=scores,
        )

        formatted = result.format_for_context(memories)

        # Should only contain first 5
        assert "Content 0" in formatted
        assert "Content 4" in formatted
        assert "Content 5" not in formatted
        assert "Content 9" not in formatted

    def test_activation_result_immutable(self) -> None:
        """Test that result is immutable (frozen=True)."""
        result = ActivationResult()

        # Should not be able to modify
        with pytest.raises(ValidationError):
            result.activated_memories = ["mem1"]  # type: ignore


class TestActivationSourceEnum:
    """Test ActivationSource enum."""

    def test_activation_source_values(self) -> None:
        """Test all enum values are accessible."""
        assert ActivationSource.DIRECT == "direct"
        assert ActivationSource.SPREAD_1HOP == "spread_1hop"
        assert ActivationSource.SPREAD_2HOP == "spread_2hop"
        assert ActivationSource.SPREAD_3HOP == "spread_3hop"

    def test_activation_source_in_score(self) -> None:
        """Test using enum in ActivationScore."""
        for source in ActivationSource:
            score = ActivationScore.calculate(
                memory_id="mem1", base_relevance=0.5, temporal_score=0.5, source=source
            )
            assert score.source == source
