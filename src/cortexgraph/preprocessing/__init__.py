"""Natural language preprocessing for conversational memory activation.

This module provides automatic detection and enrichment for memory operations:
- Phrase detection for explicit save/recall requests
- Entity extraction from natural language
- Importance scoring for memory strength calculation

Designed to work within MCP constraints (no pre-LLM interception).
"""

from .entity_extractor import EntityExtractor
from .importance_scorer import ImportanceScorer
from .phrase_detector import PhraseDetector

__all__ = [
    "PhraseDetector",
    "EntityExtractor",
    "ImportanceScorer",
]
