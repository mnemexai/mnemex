"""
Natural Language Activation Module for CortexGraph.

This module provides automatic detection of memory operations (save, recall, reinforce)
from natural language without requiring explicit commands. It analyzes user messages
and queries using pattern matching and heuristics to provide decision support for
memory operations.

Main Components:
- models: Pydantic models for activation signals and analysis results
- config: Configuration management and pattern libraries
- patterns: Pattern matching engine for trigger phrase detection
- detectors: Detection logic and confidence scoring
- entity_extraction: Entity extraction from text

Public API:
- analyze_message: Analyze message for memory-worthy content
- analyze_for_recall: Analyze query for recall intent
- MessageAnalysis: Result model for save detection
- RecallAnalysis: Result model for recall detection
"""

from cortexgraph.activation.models import (
    ActivationSignal,
    MessageAnalysis,
    RecallAnalysis,
)

__all__ = [
    "ActivationSignal",
    "MessageAnalysis",
    "RecallAnalysis",
]

__version__ = "0.7.0"
