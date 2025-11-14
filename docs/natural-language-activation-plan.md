# Natural Language Activation Implementation Plan
## Spreading Activation for CortexGraph Memory Recall

**Document Type**: Implementation Plan
**Created**: 2025-11-14
**Status**: Research Complete, Ready for Implementation
**Feature Branch**: `feat/natural-language-activation`
**Target Version**: v0.6.0

---

## Executive Summary

This document outlines the implementation of **natural language activation** for cortexgraph, enabling conversational memory recall through spreading activation and multi-dimensional search. Unlike the existing explicit tool-based retrieval (`search_memory`), this system will automatically activate related memories based on conversational context, creating a more natural and human-like memory experience.

**Core Innovation**: Hybrid spreading activation + temporal decay, combining graph-based memory traversal with cortexgraph's unique temporal properties.

**Expected Impact**: 3-4x improvement in context-relevant memory retrieval during conversations

**Timeline**: 8-10 weeks to production-ready system

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Research Findings](#research-findings)
3. [Solution Architecture](#solution-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Integration Points](#integration-points)
6. [Success Metrics](#success-metrics)
7. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### Current State

CortexGraph v0.5.1 provides excellent memory foundations:
- ✅ Temporal decay with natural spaced repetition
- ✅ Knowledge graph with entities and relations
- ✅ Multi-message context (via `observe_memory_usage`)
- ✅ Review priority system (danger zone detection)
- ✅ Cross-domain usage detection (Jaccard similarity <30%)

However, memory retrieval requires **explicit search queries**:
```python
# Current: Explicit search required
search_memory(query="TypeScript preferences", tags=["backend"])
```

### The Gap: Natural Conversational Activation

When humans converse, related memories activate **automatically** without explicit recall commands:

**Example Conversation:**
```
User: "I'm starting a new backend API project"
→ Should auto-activate:
  - Previous preference for TypeScript
  - Recent discussion about PostgreSQL for analytics
  - Decision to use JWT for authentication
  - Related project X architecture notes
```

**Current behavior:** LLM must explicitly decide to search for each relevant memory

**Desired behavior:** Related memories surface automatically through spreading activation

### Why This Matters

**From User Perspective:**
- AI remembers context without being prompted
- Feels more natural and attentive
- Reduces cognitive load (user doesn't need to remind AI)

**From System Perspective:**
- Leverages existing knowledge graph structure
- Complements (doesn't replace) explicit search
- Aligns with cortexgraph's temporal memory philosophy

---

## Research Findings

### State-of-the-Art (2024-2025)

#### 1. IMDMR: Multi-Dimensional Memory Retrieval (Nov 2025)

**Paper**: arxiv:2511.05495v1
**Key Finding**: 3.8x improvement using 6-dimensional search

**Six Dimensions:**
1. **Semantic** - meaning similarity (embeddings)
2. **Entity** - shared named entities
3. **Category** - topical classification
4. **Intent** - user goals/preferences
5. **Context** - conversational state
6. **Temporal** - time-based relevance

**Relevance to CortexGraph:**
- ✅ Already have: Semantic (optional embeddings), Entity (graph), Temporal (decay)
- ❌ Need: Category, Intent, Context dimensions

**Performance**: Individual dimensions vs. full system = 23.3% improvement

---

#### 2. SpreadPy: Spreading Activation Library (July 2025)

**Paper**: arxiv:2507.09628
**GitHub**: Python library for cognitive network activation

**Core Algorithm:**
```python
# Spreading activation pseudocode
def spread_activation(source_nodes, network, decay_rate, threshold):
    """
    Args:
        source_nodes: Initial activation points (e.g., entities in user message)
        network: Graph structure (nodes = memories, edges = relations)
        decay_rate: Activation strength decay per hop
        threshold: Minimum activation to consider node "activated"

    Returns:
        activated_nodes: Memories that received sufficient activation
    """
    activation = {node: 0.0 for node in network.nodes}

    # Initialize source nodes
    for source in source_nodes:
        activation[source] = 1.0

    # Spread activation iteratively
    for iteration in range(max_hops):
        new_activation = activation.copy()

        for node, strength in activation.items():
            if strength < threshold:
                continue

            # Spread to neighbors
            for neighbor in network.neighbors(node):
                edge_weight = network[node][neighbor]['weight']
                transferred = strength * edge_weight * (decay_rate ** iteration)
                new_activation[neighbor] += transferred

        activation = new_activation

    # Return nodes above threshold
    return {n: a for n, a in activation.items() if a >= threshold}
```

**Relevance to CortexGraph:**
- Direct application to existing knowledge graph (entities + relations)
- Compatible with temporal decay (combine activation strength with decay score)
- Can use existing relation weights (strength field)

---

#### 3. Mem0: Scalable Production Memory (Apr 2025)

**Paper**: arxiv:2504.19413
**Key Finding**: 26% improvement over OpenAI, 91% lower latency

**Architecture:**
```
User Message
    ↓
Extract Facts (LLM)
    ↓
Update Memory Graph (deduplicate, consolidate)
    ↓
Retrieve Relevant Context (RAG + Graph)
```

**Mem0ᵍ Enhancement**: Graph-based store for multi-session relationships

**Relevance to CortexGraph:**
- Validates graph-enhanced memory approach
- Two-phase pipeline: Extract → Update (aligns with conversational-activation-plan.md)
- Confirms value of deduplication (already in cortexgraph roadmap)

---

#### 4. A-MEM: Agentic Memory with Zettelkasten (Feb 2025)

**Paper**: arxiv:2502.12110
**Key Concept**: Dynamic indexing with interconnected notes

**Memory Structure:**
```python
{
    "content": "User prefers TypeScript for backend",
    "keywords": ["typescript", "backend", "preference"],
    "tags": ["programming", "languages"],
    "links": [
        {"to": "mem-456", "relation": "related_to", "context": "same project"},
        {"to": "mem-789", "relation": "elaborates_on", "context": "tech stack"}
    ],
    "context": "Discussion about new API project"
}
```

**Relevance to CortexGraph:**
- ✅ Already have: content, tags, entities
- ✅ Already have: relations (via `create_relation` tool)
- ❌ Need: Automatic keyword extraction
- ❌ Need: Contextual link creation

---

#### 5. Context Window Paradox (Industry Research 2025)

**Finding**: Beyond 128K tokens, LLM performance degrades ("context rot")

**Implication**: Active memory retrieval > dumping entire context

**Solution**: Intelligent activation that surfaces only relevant memories

**Relevance to CortexGraph:**
- Validates selective memory retrieval approach
- Spreading activation naturally limits context to relevant memories
- Temporal decay filters out stale information

---

### Synthesis: What CortexGraph Needs

Combining all research findings:

| Feature | IMDMR | SpreadPy | Mem0 | A-MEM | CortexGraph Status |
|---------|-------|----------|------|-------|-------------------|
| **Semantic Search** | ✅ | | ✅ | | ✅ (optional embeddings) |
| **Entity Tracking** | ✅ | | ✅ | ✅ | ✅ (graph entities) |
| **Temporal Relevance** | ✅ | | | | ✅ (decay + review priority) |
| **Spreading Activation** | | ✅ | | | ❌ **NEED** |
| **Category/Intent** | ✅ | | | | ❌ **NEED** |
| **Context Dimension** | ✅ | | | ✅ | ⚠️ Partial (tags only) |
| **Automatic Activation** | ✅ | ✅ | ✅ | | ❌ **NEED** |
| **Dynamic Relations** | | | ✅ | ✅ | ⚠️ Manual only |

**Priority Gaps:**
1. **Spreading activation engine** - Core algorithm for graph traversal
2. **Automatic activation triggers** - Detect when to activate vs. explicit search
3. **Context extraction** - Pull entities/intents from conversation
4. **Category inference** - Classify memory topical areas

---

## Solution Architecture

### Three-Layer Activation System

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Trigger Detection                             │
│  - Extract entities from user message                   │
│  - Detect intent (question, statement, command)         │
│  - Determine activation vs. explicit search             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Layer 2: Spreading Activation Engine                   │
│  - Initialize activation from source entities           │
│  - Propagate through relation graph                     │
│  - Combine with temporal decay scores                   │
│  - Apply cross-domain detection                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Layer 3: Memory Integration                            │
│  - Blend activated memories with review candidates      │
│  - Rank by combined score (activation × decay × review) │
│  - Return top-k for LLM context                         │
│  - Call observe_memory_usage for reinforcement          │
└─────────────────────────────────────────────────────────┘
```

### Core Components

#### Component 1: Activation Trigger Detector

**Purpose**: Determine when to activate memories automatically vs. wait for explicit search

**Implementation**:
```python
# src/cortexgraph/activation/trigger_detector.py

from typing import List, Dict, Literal
import spacy

class ActivationTrigger:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.question_patterns = ["what", "when", "where", "who", "how", "why", "do you remember"]

    def detect(self, message: str) -> Dict:
        """
        Determine if message should trigger automatic activation.

        Returns:
            {
                "should_activate": bool,
                "activation_type": "question" | "statement" | "command",
                "source_entities": List[str],  # Entities to start spreading from
                "intent": "recall" | "store" | "update" | "general"
            }
        """
        doc = self.nlp(message)

        # Extract entities
        entities = [ent.text.lower() for ent in doc.ents]

        # Detect question (triggers recall activation)
        is_question = any(token.text.lower() in self.question_patterns for token in doc)

        # Detect explicit memory command
        memory_keywords = ["remember", "recall", "what did i say", "previously"]
        is_memory_command = any(kw in message.lower() for kw in memory_keywords)

        # Intent classification
        if is_question or is_memory_command:
            intent = "recall"
            should_activate = len(entities) > 0  # Activate if entities present
        elif any(token.pos_ == "VERB" and token.lemma_ in ["prefer", "like", "decide", "choose"] for token in doc):
            intent = "store"  # Preference/decision statement
            should_activate = False  # Don't activate on save
        else:
            intent = "general"
            should_activate = len(entities) >= 2  # Activate if multiple entities (likely building on prior context)

        return {
            "should_activate": should_activate,
            "activation_type": "question" if is_question else "statement",
            "source_entities": entities,
            "intent": intent
        }
```

**Test Coverage**:
- Detect questions correctly (95%+ accuracy)
- Extract entities from messages (spaCy NER)
- Intent classification (recall vs. store vs. general)

---

#### Component 2: Spreading Activation Engine

**Purpose**: Traverse knowledge graph from source entities, activating related memories

**Algorithm**: Multi-hop activation with temporal decay integration

**Implementation**:
```python
# src/cortexgraph/activation/spreading.py

from typing import List, Dict, Set
from collections import defaultdict
import networkx as nx

class SpreadingActivation:
    def __init__(self, storage, config):
        self.storage = storage
        self.decay_rate = config.ACTIVATION_DECAY_RATE  # 0.7 default
        self.threshold = config.ACTIVATION_THRESHOLD  # 0.15 default
        self.max_hops = config.MAX_ACTIVATION_HOPS  # 3 default

    def activate(self, source_entities: List[str]) -> Dict[str, float]:
        """
        Spread activation from source entities through knowledge graph.

        Args:
            source_entities: List of entity names to start activation

        Returns:
            activated_memories: {memory_id: activation_score}
        """
        # Build activation graph from memory relations
        graph = self._build_activation_graph()

        # Initialize activation
        activation = defaultdict(float)
        for entity in source_entities:
            # Find memories containing this entity
            memory_ids = self._find_memories_by_entity(entity)
            for mid in memory_ids:
                activation[mid] = 1.0

        if not activation:
            return {}

        # Spread activation iteratively
        for hop in range(self.max_hops):
            new_activation = activation.copy()
            current_decay = self.decay_rate ** (hop + 1)

            for memory_id, strength in activation.items():
                if strength < self.threshold:
                    continue

                # Get outgoing relations
                relations = self.storage.get_relations_from(memory_id)

                for relation in relations:
                    target_id = relation.to_memory_id
                    edge_weight = relation.strength  # Use relation strength as edge weight

                    # Transfer activation with decay
                    transferred = strength * edge_weight * current_decay
                    new_activation[target_id] += transferred

            activation = new_activation

        # Filter by threshold
        return {mid: score for mid, score in activation.items() if score >= self.threshold}

    def _build_activation_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from memory relations."""
        G = nx.DiGraph()
        relations = self.storage.get_all_relations()

        for rel in relations:
            G.add_edge(
                rel.from_memory_id,
                rel.to_memory_id,
                weight=rel.strength,
                type=rel.relation_type
            )

        return G

    def _find_memories_by_entity(self, entity: str) -> List[str]:
        """Find all memory IDs containing given entity."""
        all_memories = self.storage.get_all_memories(status="active")
        return [m.id for m in all_memories if entity.lower() in [e.lower() for e in m.entities]]
```

**Configuration**:
```bash
# Spreading Activation
ACTIVATION_DECAY_RATE=0.7        # Activation strength per hop (70% retained)
ACTIVATION_THRESHOLD=0.15        # Minimum activation to consider
MAX_ACTIVATION_HOPS=3            # Maximum graph traversal depth
```

---

#### Component 3: Hybrid Scoring System

**Purpose**: Combine spreading activation with existing temporal decay and review priority

**Formula**:
```
final_score = activation_score × decay_score × (1 + review_priority)

Where:
- activation_score: From spreading activation (0.0-1.0)
- decay_score: Existing temporal decay (0.0-∞)
- review_priority: Danger zone urgency (0.0-1.0)
```

**Implementation**:
```python
# src/cortexgraph/activation/hybrid_scoring.py

from typing import List, Dict
from ..core.decay import calculate_score
from ..core.review import calculate_review_priority

class HybridScorer:
    def __init__(self, config):
        self.activation_weight = config.ACTIVATION_WEIGHT  # 0.4 default
        self.decay_weight = config.DECAY_WEIGHT  # 0.4 default
        self.review_weight = config.REVIEW_WEIGHT  # 0.2 default

    def score(self, memory, activation_score: float) -> float:
        """
        Calculate hybrid score combining activation, decay, and review.

        Args:
            memory: Memory object
            activation_score: Score from spreading activation

        Returns:
            Combined score (0.0-∞)
        """
        # Existing temporal decay score
        decay_score = calculate_score(memory)

        # Existing review priority
        review_priority = calculate_review_priority(memory)

        # Weighted combination
        combined = (
            self.activation_weight * activation_score +
            self.decay_weight * decay_score +
            self.review_weight * review_priority
        )

        return combined
```

---

#### Component 4: Natural Activation API

**Purpose**: New MCP tool for conversational activation (complements existing `search_memory`)

**Tool Signature**:
```python
@mcp.tool()
async def activate_memories(
    message: str,
    max_results: int = 5,
    include_review: bool = True
) -> Dict:
    """
    Automatically activate relevant memories based on conversational message.

    This tool uses spreading activation from entities in the message to
    surface contextually relevant memories without explicit search queries.

    Args:
        message: User's conversational message
        max_results: Maximum memories to return (default: 5)
        include_review: Blend in review candidates (default: True)

    Returns:
        {
            "activated_memories": [
                {
                    "id": "mem-123",
                    "content": "...",
                    "activation_score": 0.85,
                    "decay_score": 0.62,
                    "hybrid_score": 0.73,
                    "source": "spreading_activation" | "review_candidate",
                    "activation_path": ["entity:typescript", "relation:prefers", "mem-123"]
                },
                ...
            ],
            "trigger_info": {
                "should_activate": True,
                "activation_type": "question",
                "source_entities": ["typescript", "backend"],
                "intent": "recall"
            },
            "stats": {
                "total_activated": 12,
                "returned_count": 5,
                "activation_hops": 3
            }
        }
    """
    # Implementation in tools/activate.py
    ...
```

**Usage Example**:
```python
# User: "What did I decide about TypeScript for backend projects?"

result = activate_memories(
    message="What did I decide about TypeScript for backend projects?",
    max_results=5
)

# Returns:
# - Memory about TypeScript preference (direct entity match)
# - Memory about backend architecture choice (1-hop relation)
# - Memory about related project X (2-hop relation via shared entity)
# - Review candidate about JWT authentication (danger zone, tag overlap)
```

---

## Implementation Phases

### Phase 1: Core Spreading Activation (3 weeks)

**Goal**: Implement basic spreading activation on existing knowledge graph

**Deliverables**:
- ✅ `src/cortexgraph/activation/spreading.py` - Core activation algorithm
- ✅ `src/cortexgraph/activation/trigger_detector.py` - Entity extraction + intent detection
- ✅ `src/cortexgraph/activation/hybrid_scoring.py` - Combine activation + decay + review
- ✅ `tests/activation/test_spreading.py` - Unit tests (90%+ coverage)
- ✅ Configuration options in `config.py`

**Success Criteria**:
- ✅ Activate memories through 1-3 hops in knowledge graph
- ✅ Combine activation scores with temporal decay correctly
- ✅ Entity extraction works on 80%+ of test messages

**Dependencies**:
- Existing knowledge graph (entities + relations) ✅
- spaCy for NER (`en_core_web_sm`) - new

---

### Phase 2: MCP Tool Integration (2 weeks)

**Goal**: Expose spreading activation via MCP tool

**Deliverables**:
- ✅ `src/cortexgraph/tools/activate.py` - New `activate_memories` tool
- ✅ Integration with MCP server (`server.py`)
- ✅ Documentation in `docs/api.md`
- ✅ Integration tests (end-to-end flow)

**Success Criteria**:
- ✅ LLM can call `activate_memories` from conversation
- ✅ Returns relevant memories without explicit search query
- ✅ Activation explanations (path tracing) included in response

---

### Phase 3: Advanced Features (3 weeks)

**Goal**: Category inference, automatic relation creation, multi-dimensional search

**Component 3.1: Category Inference**

```python
# src/cortexgraph/activation/categorizer.py

from transformers import pipeline

class CategoryInference:
    def __init__(self):
        # Zero-shot classification for predefined categories
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

        self.categories = [
            "programming", "project-management", "preferences",
            "decisions", "facts", "relationships", "goals"
        ]

    def infer_categories(self, content: str) -> List[str]:
        """
        Classify memory content into predefined categories.

        Returns categories with confidence > 0.5
        """
        result = self.classifier(content, self.categories, multi_label=True)
        return [label for label, score in zip(result["labels"], result["scores"]) if score > 0.5]
```

**Component 3.2: Automatic Relation Creation**

```python
# src/cortexgraph/activation/auto_relations.py

class AutoRelationCreator:
    def __init__(self, storage, similarity_threshold=0.85):
        self.storage = storage
        self.threshold = similarity_threshold

    async def create_relations_for_new_memory(self, memory_id: str):
        """
        Automatically create relations to similar/related existing memories.

        Uses:
        - Entity overlap (shared entities → "related_to")
        - Semantic similarity (embeddings → "similar_to")
        - Temporal proximity (created within 24h → "follows_from")
        """
        new_memory = self.storage.get_memory(memory_id)
        candidates = self.storage.get_all_memories(status="active")

        for candidate in candidates:
            if candidate.id == memory_id:
                continue

            # Check entity overlap
            shared_entities = set(new_memory.entities) & set(candidate.entities)
            if len(shared_entities) >= 2:
                await self.storage.create_relation(
                    from_id=memory_id,
                    to_id=candidate.id,
                    relation_type="related_to",
                    strength=0.7,
                    metadata={"shared_entities": list(shared_entities), "auto_created": True}
                )

            # Check semantic similarity (if embeddings enabled)
            if new_memory.embedding and candidate.embedding:
                similarity = cosine_similarity(new_memory.embedding, candidate.embedding)
                if similarity > self.threshold:
                    await self.storage.create_relation(
                        from_id=memory_id,
                        to_id=candidate.id,
                        relation_type="similar_to",
                        strength=similarity,
                        metadata={"similarity_score": similarity, "auto_created": True}
                    )
```

**Component 3.3: Multi-Dimensional Search**

Extend existing `search_memory` with IMDMR-inspired dimensions:

```python
# Enhance search_memory to support multi-dimensional ranking

def search_memory_multidim(
    query: str,
    tags: List[str] = None,
    entities: List[str] = None,
    categories: List[str] = None,
    intent: str = None,
    top_k: int = 10
) -> List[Memory]:
    """
    Multi-dimensional memory search combining:
    - Semantic: embedding similarity
    - Entity: entity overlap
    - Category: category match
    - Intent: intent alignment
    - Temporal: decay score
    - Context: tag overlap
    """
    # Score each dimension separately
    semantic_scores = _score_semantic(query, candidates)
    entity_scores = _score_entity_overlap(entities, candidates)
    category_scores = _score_category_match(categories, candidates)
    temporal_scores = _score_temporal_decay(candidates)
    context_scores = _score_tag_overlap(tags, candidates)

    # Weighted combination
    final_scores = (
        0.3 * semantic_scores +
        0.2 * entity_scores +
        0.15 * category_scores +
        0.2 * temporal_scores +
        0.15 * context_scores
    )

    # Rank and return top-k
    return sorted(candidates, key=lambda m: final_scores[m.id], reverse=True)[:top_k]
```

**Deliverables**:
- ✅ Category inference (zero-shot classification)
- ✅ Automatic relation creation on `save_memory`
- ✅ Multi-dimensional search enhancement
- ✅ Tests for each component

**Success Criteria**:
- ✅ Categories automatically inferred with 70%+ accuracy
- ✅ Auto-relations reduce manual linking effort by 60%+
- ✅ Multi-dimensional search outperforms single-dimension by 20%+

---

### Phase 4: Production Tuning (2 weeks)

**Goal**: Performance optimization, configuration tuning, user testing

**Optimization Targets**:
- Activation latency < 100ms (in-memory graph traversal)
- Category inference < 50ms (lightweight model)
- Auto-relation creation async (doesn't block save_memory)

**Configuration Tuning**:
```bash
# Spreading Activation
ACTIVATION_DECAY_RATE=0.7        # Test 0.6, 0.7, 0.8
ACTIVATION_THRESHOLD=0.15        # Test 0.10, 0.15, 0.20
MAX_ACTIVATION_HOPS=3            # Test 2, 3, 4

# Hybrid Scoring Weights
ACTIVATION_WEIGHT=0.4            # Test 0.3-0.5
DECAY_WEIGHT=0.4                 # Test 0.3-0.5
REVIEW_WEIGHT=0.2                # Test 0.1-0.3

# Auto Relations
AUTO_RELATION_ENABLED=true
AUTO_RELATION_MIN_ENTITY_OVERLAP=2
AUTO_RELATION_SIMILARITY_THRESHOLD=0.85
```

**User Testing**:
- A/B test: Activation ON vs. OFF
- Metrics: Conversation quality, memory recall accuracy, user satisfaction
- Target: 3-4x improvement in relevant memory retrieval

**Deliverables**:
- ✅ Performance benchmarks
- ✅ Configuration recommendations
- ✅ User testing report
- ✅ Documentation updates

---

## Integration Points

### 1. MCP Server Entry Point

**File**: `src/cortexgraph/server.py`

```python
from .activation import ActivationTrigger, SpreadingActivation, HybridScorer

# Initialize activation components (lazy loading)
_activation_components = None

def get_activation_components():
    global _activation_components
    if _activation_components is None and config.ENABLE_ACTIVATION:
        _activation_components = {
            "trigger": ActivationTrigger(),
            "spreader": SpreadingActivation(storage, config),
            "scorer": HybridScorer(config),
        }
    return _activation_components

@mcp.tool()
async def activate_memories(message: str, max_results: int = 5, include_review: bool = True):
    """Natural language memory activation."""
    # Implementation calls components above
    ...
```

### 2. Integration with Existing Tools

**Relationship to `search_memory`**:
- `activate_memories`: Automatic, conversational, graph-based
- `search_memory`: Explicit, query-driven, text/tag-based
- Both can coexist and complement each other

**Enhancement to `save_memory`**:
```python
@mcp.tool()
async def save_memory(content, tags, entities, ...):
    # Existing save logic
    memory_id = storage.save(...)

    # NEW: Automatic relation creation
    if config.AUTO_RELATION_ENABLED:
        await auto_relation_creator.create_relations_for_new_memory(memory_id)

    # NEW: Category inference
    if config.ENABLE_CATEGORY_INFERENCE:
        categories = categorizer.infer_categories(content)
        storage.update_categories(memory_id, categories)

    return memory_id
```

### 3. Conversational Activation Integration

This feature **complements** the approved conversational-activation-plan.md:

**conversational-activation-plan.md**: Preprocessing layer for **detecting when to save**
- Intent classification (SAVE_PREFERENCE, SAVE_DECISION, etc.)
- Entity extraction for populating `entities` field
- Tag suggestion
- Importance scoring

**natural-language-activation (this plan)**: Graph traversal for **retrieving related memories**
- Spreading activation from entities
- Multi-dimensional search
- Automatic relation creation

**Together**: Complete conversational memory system
```
User Message
    ↓
Preprocessing (conversational-activation-plan)
    ├─ Intent: SAVE_PREFERENCE → save_memory
    └─ Intent: RECALL_INFO → activate_memories (this plan)
    ↓
Memory Operations
```

---

## Success Metrics

### Quantitative Metrics

**1. Activation Quality** (Primary Metric):
- **Baseline**: Explicit search (`search_memory`) retrieves 2-3 relevant memories per query
- **Target**: Spreading activation retrieves 4-8 relevant memories per conversation turn
- **Measurement**: Manual annotation of relevance (human judgment)

**2. Precision/Recall**:
- **Precision**: % of activated memories that are relevant
  - Target: 70%+ (vs. 85%+ for explicit search - acceptable tradeoff for breadth)
- **Recall**: % of relevant memories that are activated
  - Target: 80%+ (vs. 60% for explicit search - improvement through graph traversal)

**3. Latency**:
- **Activation time**: < 100ms (in-memory graph traversal)
- **Total retrieval time**: < 200ms (activation + scoring + ranking)

**4. Graph Density**:
- **Auto-relations created**: 60%+ reduction in manual relation effort
- **Average relations per memory**: Increase from ~0.5 to ~2.5

### Qualitative Metrics

**User Experience**:
- Survey: "Does the AI remember context naturally?" (8/10 target)
- Survey: "How often does the AI miss relevant information?" (Rarely/Never target)

**Developer Experience**:
- Ease of configuration (tuning activation parameters)
- Debuggability (activation path tracing)

---

## Configuration

```bash
# ============================================================================
# Natural Language Activation Configuration
# ============================================================================

# Enable/Disable Activation
ENABLE_ACTIVATION=true

# Spreading Activation
ACTIVATION_DECAY_RATE=0.7        # Activation strength decay per hop (0.0-1.0)
ACTIVATION_THRESHOLD=0.15        # Minimum activation to consider memory
MAX_ACTIVATION_HOPS=3            # Maximum graph traversal depth (1-5)

# Hybrid Scoring Weights
ACTIVATION_WEIGHT=0.4            # Weight for activation score (0.0-1.0)
DECAY_WEIGHT=0.4                 # Weight for temporal decay (0.0-1.0)
REVIEW_WEIGHT=0.2                # Weight for review priority (0.0-1.0)

# Automatic Relation Creation
AUTO_RELATION_ENABLED=true
AUTO_RELATION_MIN_ENTITY_OVERLAP=2       # Min shared entities for "related_to"
AUTO_RELATION_SIMILARITY_THRESHOLD=0.85  # Min similarity for "similar_to"

# Category Inference
ENABLE_CATEGORY_INFERENCE=true
CATEGORY_MODEL=facebook/bart-large-mnli  # Zero-shot classification model
CATEGORY_CONFIDENCE_THRESHOLD=0.5        # Min confidence to assign category

# Multi-Dimensional Search
ENABLE_MULTIDIM_SEARCH=true
MULTIDIM_SEMANTIC_WEIGHT=0.3
MULTIDIM_ENTITY_WEIGHT=0.2
MULTIDIM_CATEGORY_WEIGHT=0.15
MULTIDIM_TEMPORAL_WEIGHT=0.2
MULTIDIM_CONTEXT_WEIGHT=0.15
```

---

## Dependencies

### Python Packages

```toml
# pyproject.toml additions

[project.dependencies]
# Phase 1
spacy = "^3.7.0"
networkx = "^3.2"

# Phase 3
transformers = "^4.35.0"  # For zero-shot classification
torch = "^2.1.0"          # Or tensorflow
scikit-learn = "^1.3.0"   # For similarity calculations

[project.optional-dependencies]
activation = [
    "spacy>=3.7.0",
    "networkx>=3.2",
    "transformers>=4.35.0",
    "torch>=2.1.0",
]
```

**Model Downloads**:
```bash
# Phase 1
python -m spacy download en_core_web_sm  # 17MB

# Phase 3
# facebook/bart-large-mnli automatically downloaded by transformers (~1.6GB)
```

---

## Future Enhancements

### Short-Term (Next 6 Months)

**1. Activation Visualization**
- Export activation graph to Graphviz/D3.js
- Show activation paths in UI
- Debug activation patterns

**2. Personalized Activation Parameters**
- Learn optimal decay rates per user
- Adaptive hop count based on graph density
- User-specific category taxonomies

**3. Temporal Activation Patterns**
- Time-of-day aware activation
- Seasonal/periodic memory patterns
- Event-based activation triggers

### Medium-Term (6-12 Months)

**4. Multi-Agent Spreading Activation**
- Shared memory graphs across agents
- Collaborative activation (multiple agents activating same memory)
- Agent-specific activation weights

**5. Explanation Generation**
- Natural language explanations for why memories activated
- "I remember this because you mentioned X and it relates to Y"
- Transparency for user trust

**6. Active Learning for Relations**
- User feedback on relation quality
- Automatic relation type inference (beyond "related_to", "similar_to")
- Reinforcement learning for optimal graph structure

### Long-Term (12+ Months)

**7. Neuromorphic Activation**
- Spiking neural network-inspired activation
- Continuous activation (not just on-demand)
- Background memory consolidation

**8. Cross-Modal Activation**
- Activate memories from images, audio, video
- Multi-modal embeddings
- Sensory-triggered recall

**9. Metacognitive Activation**
- LLM self-reflection on activated memories
- "Why did I remember this? Is it relevant?"
- Confidence scores for activations

---

## Risks & Mitigations

### Risk 1: Over-Activation (Too Many Memories)

**Impact**: Medium - Context overload, slower LLM processing

**Mitigation**:
- Conservative threshold (0.15 default)
- Limit max_results (5-10 default)
- Decay activation strength with hops
- User feedback: "Was this relevant?"

### Risk 2: Under-Activation (Missing Relevant Memories)

**Impact**: High - Defeats purpose of natural activation

**Mitigation**:
- Lower threshold for testing (0.10)
- Increase max hops (4-5)
- Fallback to explicit search if activation returns <3 memories
- Blend with review candidates (danger zone memories)

### Risk 3: Graph Sparsity (Insufficient Relations)

**Impact**: Medium - Activation can't spread if no relations exist

**Mitigation**:
- Automatic relation creation (Phase 3)
- Seed graph with common relations
- Entity-based activation (doesn't require relations)
- Encourage manual relation creation through UI

### Risk 4: Latency from Graph Traversal

**Impact**: Low - Could slow conversation if >200ms

**Mitigation**:
- In-memory graph (NetworkX) for fast traversal
- Limit max hops (3 default)
- Async processing (don't block LLM response)
- Cache activation results for similar queries

### Risk 5: Category Inference Accuracy

**Impact**: Low - Wrong categories reduce multi-dimensional search quality

**Mitigation**:
- Zero-shot classification (no training required)
- Conservative confidence threshold (0.5)
- User feedback loop: Accept/reject category suggestions
- Manual category override option

---

## Timeline Summary

| Phase | Duration | Components | Expected Impact |
|-------|----------|------------|-----------------|
| **Phase 1** | 3 weeks | Spreading activation, trigger detection, hybrid scoring | 2-3x improvement in relevant memory retrieval |
| **Phase 2** | 2 weeks | MCP tool integration, API exposure | Usable natural activation in conversations |
| **Phase 3** | 3 weeks | Category inference, auto-relations, multi-dimensional search | 3-4x improvement, graph density increase |
| **Phase 4** | 2 weeks | Performance tuning, user testing, documentation | Production-ready system |
| **Total** | **10 weeks** | Complete natural language activation system | **3-4x overall improvement** |

---

## Conclusion

This implementation plan transforms cortexgraph from **explicit memory retrieval** to **natural conversational activation**, leveraging cutting-edge research from 2024-2025 while building on cortexgraph's unique temporal memory foundations.

**Key Innovations**:
1. **Hybrid spreading activation + temporal decay** - Unique combination not seen in existing systems
2. **Multi-dimensional search** - Inspired by IMDMR, adapted for temporal memory
3. **Automatic relation creation** - Graph density improvement without manual effort
4. **Integration with natural spaced repetition** - Activated memories automatically reinforce

**Expected Outcome**: Conversational AI that remembers context naturally, achieving 3-4x improvement in relevant memory retrieval compared to explicit search baseline.

---

## References

### Academic Papers (2024-2025)

1. **IMDMR** (arxiv:2511.05495v1) - Multi-dimensional memory retrieval
2. **SpreadPy** (arxiv:2507.09628) - Spreading activation library
3. **Mem0** (arxiv:2504.19413) - Production-ready scalable memory
4. **A-MEM** (arxiv:2502.12110) - Agentic memory with Zettelkasten
5. **MIRIX** (arxiv:2507.07957v1) - Multi-agent memory system
6. **SynapticRAG** (arxiv:2410.13553) - Temporal memory retrieval
7. **Semantic Network Model** (arxiv:2301.11709v1) - Spreading activation for comprehension

### Industry Systems

- Mem0: github.com/mem0ai/mem0
- Memori: github.com/GibsonAI/Memori
- spaCy: spacy.io
- NetworkX: networkx.org
- Transformers (Hugging Face): huggingface.co/transformers

### CortexGraph Documentation

- **conversational-activation-plan.md** - Preprocessing for save detection
- **architecture.md** - Temporal decay and natural spaced repetition
- **graph_features.md** - Knowledge graph structure
- **api.md** - Existing MCP tools

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
**Author**: Claude (Sonnet 4.5)
**Branch**: `feat/natural-language-activation`
**Next Review**: After Phase 1 completion
