"""
Configuration models for natural language activation.

This module defines the configuration structures for pattern matching and
decision boundaries. These models are loaded from YAML config and environment
variables to control activation behavior.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class ConfidenceThreshold(BaseModel):
    """Configuration for activation decision boundaries.

    Defines the confidence thresholds that determine whether to automatically
    save/recall, ask the user for clarification, or skip the operation.

    Attributes:
        auto_save_min: Confidence >= this triggers automatic save_memory
        auto_recall_min: Confidence >= this triggers automatic search_memory
        clarification_min: Lower bound for asking user (clarification range start)
        clarification_max: Upper bound for asking user (clarification range end)

    Decision Logic:
        - confidence >= auto_save_min → AUTO (execute immediately)
        - clarification_min <= confidence < clarification_max → ASK (user confirmation)
        - confidence < clarification_min → SKIP (too low confidence)
    """

    auto_save_min: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Auto-save if confidence >= this value",
    )

    auto_recall_min: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Auto-search if confidence >= this value",
    )

    clarification_min: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Ask user if confidence >= this (lower bound of clarification range)",
    )

    clarification_max: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Ask user if confidence < this (upper bound of clarification range)",
    )

    @property
    def skip_threshold(self) -> float:
        """Threshold below which to skip action."""
        return self.clarification_min

    def get_decision(self, confidence: float) -> Literal["auto", "ask", "skip"]:
        """Determine decision based on confidence.

        Args:
            confidence: Confidence score (0.0-1.0)

        Returns:
            "auto" - Execute immediately
            "ask" - Request user confirmation
            "skip" - Too low confidence, don't act
        """
        if confidence >= self.auto_save_min:
            return "auto"
        elif confidence >= self.clarification_min:
            return "ask"
        else:
            return "skip"

    @model_validator(mode="after")
    def validate_thresholds(self) -> "ConfidenceThreshold":
        """Ensure threshold ordering is correct.

        Validates:
            - clarification_min < clarification_max (valid range)
            - auto_save_min >= clarification_max (no gap between ranges)
            - auto_recall_min >= clarification_max (consistent with save)

        Raises:
            ValueError: If threshold ordering is invalid
        """
        if self.clarification_min >= self.clarification_max:
            raise ValueError(
                f"clarification_min ({self.clarification_min}) must be < "
                f"clarification_max ({self.clarification_max})"
            )

        if self.auto_save_min < self.clarification_max:
            raise ValueError(
                f"auto_save_min ({self.auto_save_min}) must be >= "
                f"clarification_max ({self.clarification_max})"
            )

        if self.auto_recall_min < self.clarification_max:
            raise ValueError(
                f"auto_recall_min ({self.auto_recall_min}) must be >= "
                f"clarification_max ({self.clarification_max})"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "auto_save_min": 0.7,
                "auto_recall_min": 0.7,
                "clarification_min": 0.4,
                "clarification_max": 0.7,
            }
        }
    }


class PatternLibrary(BaseModel):
    """Collection of trigger phrases and markers.

    Loaded from YAML configuration file (activation.yaml), this library
    contains all the pattern lists used for natural language detection.

    Attributes:
        explicit_save_triggers: Phrases indicating save intent ("remember this")
        explicit_recall_triggers: Phrases indicating recall intent ("what did I say")
        importance_markers: Words indicating high importance ("critical", "must")
        exclusion_patterns: Patterns to skip ("what is", "how do")
        uncertainty_markers: Words indicating low confidence ("maybe", "might")
        case_sensitive: Whether pattern matching is case-sensitive
        partial_match: Allow patterns as substrings (not just exact match)
    """

    explicit_save_triggers: list[str] = Field(
        default_factory=list,
        description="Phrases like 'remember this', 'don't forget'",
    )

    explicit_recall_triggers: list[str] = Field(
        default_factory=list,
        description="Phrases like 'what did I say', 'remind me'",
    )

    importance_markers: list[str] = Field(
        default_factory=list,
        description="Words indicating high importance: 'critical', 'must'",
    )

    exclusion_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to skip: 'what is', 'how do' (general questions)",
    )

    uncertainty_markers: list[str] = Field(
        default_factory=list,
        description="Words indicating low confidence: 'maybe', 'might'",
    )

    case_sensitive: bool = Field(
        default=False, description="Whether pattern matching is case-sensitive"
    )

    partial_match: bool = Field(
        default=True,
        description="Allow patterns as substrings (not just exact match)",
    )

    @property
    def total_patterns(self) -> int:
        """Total number of patterns across all categories."""
        return (
            len(self.explicit_save_triggers)
            + len(self.explicit_recall_triggers)
            + len(self.importance_markers)
            + len(self.exclusion_patterns)
            + len(self.uncertainty_markers)
        )

    def validate_patterns(self) -> list[str]:
        """Validate all patterns are non-empty strings.

        Returns:
            List of validation issues (empty if all patterns valid)

        Issues detected:
            - Empty or whitespace-only patterns
            - Patterns shorter than 2 characters
        """
        issues = []

        for category, patterns in [
            ("explicit_save_triggers", self.explicit_save_triggers),
            ("explicit_recall_triggers", self.explicit_recall_triggers),
            ("importance_markers", self.importance_markers),
            ("exclusion_patterns", self.exclusion_patterns),
            ("uncertainty_markers", self.uncertainty_markers),
        ]:
            for pattern in patterns:
                if not pattern or not pattern.strip():
                    issues.append(f"Empty pattern in {category}")
                elif len(pattern) < 2:
                    issues.append(f"Pattern too short in {category}: '{pattern}'")

        return issues

    model_config = {
        "json_schema_extra": {
            "example": {
                "explicit_save_triggers": [
                    "remember this",
                    "don't forget",
                    "save this",
                ],
                "explicit_recall_triggers": ["what did I say", "remind me"],
                "importance_markers": ["critical", "must", "important"],
                "exclusion_patterns": ["what is", "how do"],
                "uncertainty_markers": ["maybe", "might", "not sure"],
                "case_sensitive": False,
                "partial_match": True,
            }
        }
    }


class ActivationConfig(BaseModel):
    """Complete activation configuration.

    Combines pattern library, confidence thresholds, signal weights,
    and query expansions from YAML configuration file.

    Attributes:
        patterns: Pattern library for trigger detection
        thresholds: Confidence decision boundaries
        weights: Signal weights for confidence scoring
        bias: Bias term for sigmoid formula
        query_expansions: Tech term expansion mappings
    """

    patterns: PatternLibrary = Field(
        default_factory=PatternLibrary,
        description="Pattern library for trigger detection",
    )

    thresholds: ConfidenceThreshold = Field(
        default_factory=ConfidenceThreshold,
        description="Confidence decision boundaries",
    )

    weights: dict[str, float] = Field(
        default_factory=dict,
        description="Signal weights for confidence scoring",
    )

    bias: float = Field(default=-2.0, description="Bias term for sigmoid formula")

    query_expansions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Tech term expansion mappings (abbreviation -> full terms)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "patterns": {
                    "explicit_save_triggers": ["remember this"],
                    "case_sensitive": False,
                },
                "thresholds": {"auto_save_min": 0.7, "clarification_min": 0.4},
                "weights": {"explicit_save_request": 5.0, "entity_count": 0.8},
                "bias": -2.0,
                "query_expansions": {"auth": ["authentication", "authorization"]},
            }
        }
    }


def get_default_config_path() -> Path:
    """Get the default configuration file path.

    Search order:
        1. ~/.config/cortexgraph/activation.yaml
        2. src/cortexgraph/activation/activation.yaml.example (package default)

    Returns:
        Path to configuration file

    Raises:
        FileNotFoundError: If no config file found
    """
    # User config directory
    user_config = Path.home() / ".config" / "cortexgraph" / "activation.yaml"
    if user_config.exists():
        return user_config

    # Package default (example file)
    package_example = Path(__file__).parent / "activation.yaml.example"
    if package_example.exists():
        return package_example

    raise FileNotFoundError(
        "No activation.yaml found. Copy activation.yaml.example to "
        "~/.config/cortexgraph/activation.yaml"
    )


def load_activation_config(config_path: Path | str | None = None) -> ActivationConfig:
    """Load activation configuration from YAML file.

    Args:
        config_path: Path to YAML config file (default: auto-detect)

    Returns:
        Loaded and validated ActivationConfig

    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file malformed
        ValidationError: If config fails Pydantic validation

    Example:
        >>> config = load_activation_config()
        >>> config.patterns.explicit_save_triggers
        ['remember this', 'don't forget', ...]
        >>> config.thresholds.auto_save_min
        0.7
    """
    # Resolve config path
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load YAML
    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    # Extract pattern library
    patterns = PatternLibrary(
        explicit_save_triggers=raw_config.get("explicit_save_triggers", []),
        explicit_recall_triggers=raw_config.get("explicit_recall_triggers", []),
        importance_markers=raw_config.get("importance_markers", []),
        exclusion_patterns=raw_config.get("exclusion_patterns", []),
        uncertainty_markers=raw_config.get("uncertainty_markers", []),
        case_sensitive=raw_config.get("config", {}).get("case_sensitive", False),
        partial_match=raw_config.get("config", {}).get("partial_match", True),
    )

    # Extract confidence thresholds
    config_section = raw_config.get("config", {})
    thresholds = ConfidenceThreshold(
        auto_save_min=config_section.get("auto_save_min", 0.7),
        auto_recall_min=config_section.get("auto_recall_min", 0.7),
        clarification_min=config_section.get("clarification_min", 0.4),
        clarification_max=config_section.get("clarification_max", 0.7),
    )

    # Extract signal weights
    weights = config_section.get("weights", {})

    # Extract bias
    bias = config_section.get("bias", -2.0)

    # Extract query expansions
    query_expansions = raw_config.get("query_expansions", {})

    return ActivationConfig(
        patterns=patterns,
        thresholds=thresholds,
        weights=weights,
        bias=bias,
        query_expansions=query_expansions,
    )


def get_signal_weight(config: ActivationConfig, signal_name: str) -> float:
    """Get weight for a specific signal.

    Args:
        config: Activation configuration
        signal_name: Signal name (e.g., "explicit_save_request")

    Returns:
        Signal weight (default: 0.0 if not found)
    """
    return config.weights.get(signal_name, 0.0)


def expand_query(config: ActivationConfig, query: str) -> list[str]:
    """Expand query terms using query_expansions mapping.

    Args:
        config: Activation configuration
        query: Original query string

    Returns:
        List of expanded query terms (includes original)

    Example:
        >>> expand_query(config, "jwt authentication")
        ['jwt authentication', 'json web token authentication',
         'bearer token authentication']
    """
    terms = []
    words = query.lower().split()

    for word in words:
        if word in config.query_expansions:
            # Add expanded terms
            for expansion in config.query_expansions[word]:
                terms.append(expansion)

    # Always include original query
    return [query] + terms if terms else [query]
