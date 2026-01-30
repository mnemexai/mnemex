"""Multi-Agent Memory Consolidation System.

This module provides five specialized agents for memory management:

- DecayAnalyzer: Identifies memories approaching forget threshold
- ClusterDetector: Finds similar memories for potential merge
- SemanticMerge: Combines clustered memories intelligently
- LTMPromoter: Moves high-value memories to long-term storage
- RelationshipDiscovery: Finds implicit connections between memories

Agents coordinate via beads issues (message queue pattern) and share
a common ConsolidationAgent base class.

Example:
    >>> from cortexgraph.agents import DecayAnalyzer
    >>> analyzer = DecayAnalyzer(dry_run=True)
    >>> results = analyzer.run()
"""

from cortexgraph.agents.base import ConfidenceConfig, ConsolidationAgent
from cortexgraph.agents.cluster_detector import ClusterDetector
from cortexgraph.agents.decay_analyzer import DecayAnalyzer
from cortexgraph.agents.models import (
    ClusterAction,
    ClusterResult,
    DecayAction,
    DecayResult,
    MergeResult,
    ProcessingDecision,
    PromotionResult,
    RelationResult,
    Urgency,
)
from cortexgraph.agents.storage_utils import get_storage

__all__ = [
    # Base class
    "ConsolidationAgent",
    "ConfidenceConfig",
    # Agents
    "DecayAnalyzer",
    "ClusterDetector",
    # Result models
    "DecayResult",
    "ClusterResult",
    "MergeResult",
    "PromotionResult",
    "RelationResult",
    # Enums
    "Urgency",
    "DecayAction",
    "ClusterAction",
    "ProcessingDecision",
    # Utilities
    "get_storage",
]
