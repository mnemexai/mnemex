"""
Pydantic models for natural language memory activation.

This module defines the data structures used for activation signal detection,
message analysis, and recall analysis. All models include validation rules
and are used across the activation module and MCP tools.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ActivationSignal(BaseModel):
    """Detected pattern indicating memory operation intent.

    Internal result from pattern detection, used before final analysis.

    Attributes:
        type: Type of memory operation detected (save, recall, reinforce)
        confidence: Confidence score for this detection (0.0-1.0)
        matched_patterns: List of trigger patterns that matched
        context: Surrounding text providing context for the match
        timestamp: Unix timestamp when signal was detected
    """

    type: Literal["save", "recall", "reinforce"] = Field(
        ..., description="Type of memory operation detected"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this detection (0.0-1.0)",
    )

    matched_patterns: list[str] = Field(
        default_factory=list,
        description="List of trigger patterns that matched (e.g., ['remember this', 'explicit_save'])",
    )

    context: str = Field(
        ..., max_length=1000, description="Surrounding text providing context for the match"
    )

    timestamp: int = Field(..., description="Unix timestamp when signal was detected")

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "save",
                "confidence": 0.95,
                "matched_patterns": ["remember this", "explicit_save_trigger"],
                "context": "Remember this: I prefer PostgreSQL for databases",
                "timestamp": 1706140800,
            }
        }
    }


class MessageAnalysis(BaseModel):
    """Result of analyzing user message for memory-worthy content.

    Returned by analyze_message MCP tool to provide decision support
    for save_memory operations.

    Attributes:
        should_save: Recommendation - should this message be saved to memory?
        confidence: Confidence in the recommendation (0.0-1.0)
        suggested_entities: Extracted entities (names, technologies, URLs, tools)
        suggested_tags: Suggested tags for categorization
        suggested_strength: Importance multiplier (1.0-2.0) for memory strength
        reasoning: Human-readable explanation of the decision
        phrase_signals: Detected phrase signals for transparency
    """

    should_save: bool = Field(
        ..., description="Recommendation: should this message be saved to memory?"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the recommendation (0.0-1.0)",
    )

    suggested_entities: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Extracted entities (names, technologies, URLs, tools)",
    )

    suggested_tags: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Suggested tags for categorization",
    )

    suggested_strength: float = Field(
        default=1.0,
        ge=1.0,
        le=2.0,
        description="Importance multiplier (1.0-2.0) for memory strength",
    )

    reasoning: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable explanation of the decision",
    )

    phrase_signals: dict[str, bool] = Field(
        default_factory=dict,
        description="Detected phrase signals (save_request, importance_marker, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
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
        }
    }


class RecallAnalysis(BaseModel):
    """Result of analyzing user query for recall intent.

    Returned by analyze_for_recall MCP tool to provide decision support
    for search_memory operations.

    Attributes:
        should_search: Recommendation - should memory be searched?
        confidence: Confidence in the recommendation (0.0-1.0)
        suggested_query: Extracted search query from user's message
        suggested_tags: Suggested tags to filter by
        suggested_entities: Suggested entities to filter by
        reasoning: Human-readable explanation of the decision
        phrase_signals: Detected phrase signals for transparency
    """

    should_search: bool = Field(..., description="Recommendation: should memory be searched?")

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the recommendation (0.0-1.0)",
    )

    suggested_query: str = Field(
        default="",
        max_length=1000,
        description="Extracted search query from user's message",
    )

    suggested_tags: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Suggested tags to filter by",
    )

    suggested_entities: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="Suggested entities to filter by",
    )

    reasoning: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable explanation of the decision",
    )

    phrase_signals: dict[str, bool] = Field(
        default_factory=dict,
        description="Detected phrase signals (recall_request, question_marker, etc.)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "should_search": True,
                "confidence": 0.88,
                "suggested_query": "authentication methods",
                "suggested_tags": ["auth", "security"],
                "suggested_entities": ["jwt", "oauth"],
                "reasoning": "Signals: recall request (+4.0), 2 entities (+1.6) | Raw score: 3.6 → Confidence: 0.880",
                "phrase_signals": {"recall_request": True, "past_reference": True},
            }
        }
    }
