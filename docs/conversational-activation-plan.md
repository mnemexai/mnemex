# Conversational Activation Architecture for cortexgraph

**Document Type**: Architectural Plan
**Created**: 2025-11-04
**Status**: Approved, Ready for Implementation
**STOPPER Protocol Applied**: Yes (Full 7-step analysis completed)

---

## Executive Summary

This document outlines a comprehensive plan to add **conversational activation** to cortexgraph, transforming it from sporadic LLM-dependent memory capture to reliable, preprocessing-assisted activation. The solution adds a preprocessing layer that automatically detects save-worthy content and provides activation signals + pre-filled parameters to the LLM.

**Expected Impact**: 85-90% improvement in activation reliability (from ~40% to 85-90%)

**Timeline**: 9 weeks to production-ready system

**Core Innovation**: Hybrid architecture combining deterministic preprocessing with LLM judgment, reducing executive function load while preserving flexibility.

---

## Problem Statement

### Current State

Memory saves in cortexgraph depend entirely on the LLM explicitly calling the `save_memory` MCP tool. No automatic pattern detection, entity extraction, intent classification, or importance scoring exists.

### Root Cause Analysis

The LLM must simultaneously:
- Conduct natural conversation with the user
- Decide when to save information to memory
- Extract entities from conversation
- Infer appropriate tags
- Determine importance/strength values
- Remember to call tools consistently across long conversations

**Result**: Sporadic activation, missed memories, inconsistent parameter values, high cognitive load.

### Why This Matters

From user perspective:
- "I told you I prefer TypeScript, why did you forget?"
- "I said 'remember this' but you didn't save it"
- Inconsistent experience undermines trust

From system perspective:
- cortexgraph has excellent temporal memory foundations (decay, spaced repetition, knowledge graph)
- Activation is the bottleneck preventing production readiness
- Reliability cannot depend solely on LLM consistency

---

## Research Findings

### Current cortexgraph Architecture

**Core Components Analyzed**:
- **MCP Server** (`server.py`): FastMCP-based with 13 tools
- **Storage Layer** (`storage/jsonl_storage.py`): JSONL with in-memory indexes
- **Memory Models** (`storage/models.py`): Pydantic models with temporal fields
- **Tool Layer** (`tools/`): save, search, observe, promote, consolidate, etc.

**Existing Activation Mechanisms**:

1. **Explicit API Calls** (Primary): LLM must invoke `save_memory` tool
2. **Smart Prompting** (Documentation only): Patterns exist in `docs/prompts/memory_system_prompt.md` but no code implementation
3. **Natural Spaced Repetition** (v0.5.1): Post-retrieval reinforcement via `observe_memory_usage`
4. **Search Integration**: Review candidate blending (affects retrieval, not capture)

**Critical Finding**: All saves are explicit LLM-initiated MCP tool calls. NO automatic detection exists.

### State-of-the-Art Research (2024-2025)

**1. Mem0 Architecture (ArXiv 2504.19413v1)**
- Two-phase pipeline: Extraction → Update
- 26% accuracy boost over OpenAI's memory feature
- 91% lower latency vs. full-context approach
- Still LLM-driven but uses multi-message context

**2. Knowledge Graph Construction with LLMs**
- Hybrid LLM + structured NLP pipelines outperform pure LLM
- Dedicated entity extraction filters reduce noise
- Domain-specific pre-training enhances NER sensitivity

**3. Intent Detection with Transformers**
- BERT-based models achieve 85%+ accuracy
- Fine-tuning on small datasets (100-500 examples) is effective
- Enables automatic triggering of memory operations

**4. Entity Linking and Relationship Extraction**
- Multi-stage pipelines: NER → Linking → Relation Extraction
- spaCy provides production-ready NER with minimal setup
- Transformers models (REBEL, Relik) for relation extraction

**5. Personal Knowledge Management Trends**
- Zero-effort capture expectation (Mem.ai, MyMind)
- AI-powered automatic tagging
- Conversational interfaces over manual organization

**Key Insight**: Modern systems use **preprocessing + LLM confirmation**, not LLM-only reasoning.

### Gap Analysis

**Critical Gaps Identified**:

1. ❌ **No Automatic Pattern Detection Layer**: LLM decides when to save based on system prompt alone
2. ❌ **No Entity Extraction Pipeline**: `entities` field exists but populated manually
3. ❌ **No Tag Inference System**: `tags` field populated manually
4. ❌ **No Importance Scoring**: `strength` parameter set manually
5. ❌ **No Intent Classification**: No detection of preference vs. decision vs. fact
6. ❌ **No Phrase Trigger Detection**: No pattern matching for "remember this", "important"
7. ❌ **LLM-Dependent Activation Logic**: All decisions made by LLM reasoning

**Root Cause Summary**: cortexgraph has excellent foundations but lacks the preprocessing layer that makes activation reliable.

---

## Solution Architecture

### Hybrid Preprocessing + LLM Confirmation Model

```
User Message
     ↓
┌─────────────────────────────────────┐
│  [NEW] Preprocessing Layer          │
│  ┌────────────────────────────────┐ │
│  │ 1. Phrase Detector             │ │
│  │    (Regex for explicit trigger)│ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 2. Intent Classifier           │ │
│  │    (BERT-based, 6 intents)     │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 3. Entity Extractor (spaCy)    │ │
│  │    (NER: PERSON, ORG, TECH)    │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │ 4. Importance Scorer           │ │
│  │    (Heuristics + keywords)     │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
     ↓
Activation Signals + Pre-filled Parameters
     ↓
┌─────────────────────────────────────┐
│  [EXISTING] LLM + MCP Tools         │
│  - Receives enriched context        │
│  - Confirms/adjusts parameters      │
│  - Calls save_memory/search_memory  │
└─────────────────────────────────────┘
     ↓
[EXISTING] Storage Layer (JSONL → Markdown)
```

### Design Principles

1. **Deterministic + Flexible**: Preprocessing provides reliable signals, LLM has final say
2. **Low Latency**: Lightweight models (DistilBERT, spaCy) for real-time inference
3. **Graceful Degradation**: System works even if preprocessing fails
4. **Progressive Enhancement**: Each component adds value independently
5. **Configurable**: Enable/disable features, tune thresholds

---

## Implementation Plan

### Phase 1: Quick Wins (1 week, 40-50% improvement)

**Timeline**: Week 1
**Effort**: 3-4 days development + 2-3 days testing
**Risk**: Low (simple, deterministic components)

#### Component 1.1: Phrase Detector

**Purpose**: Detect explicit memory requests with 100% reliability

**Implementation**:
```python
# src/cortexgraph/preprocessing/phrase_detector.py

import re
from typing import List, Dict

EXPLICIT_SAVE_PHRASES = [
    r"\b(remember|don't forget|keep in mind|make a note)\b",
    r"\b(never forget|write this down|document this)\b",
    r"\b(save this|store this|record this)\b",
]

EXPLICIT_RECALL_PHRASES = [
    r"\bwhat did (i|we) (say|tell you|discuss)\b",
    r"\bdo you remember\b",
    r"\brecall\b",
]

EXPLICIT_IMPORTANCE = [
    r"\b(important|critical|crucial|essential)\b",
    r"\b(very|really|extremely)\s+(important|critical)\b",
]

class PhraseDetector:
    def __init__(self):
        self.save_patterns = [re.compile(p, re.IGNORECASE) for p in EXPLICIT_SAVE_PHRASES]
        self.recall_patterns = [re.compile(p, re.IGNORECASE) for p in EXPLICIT_RECALL_PHRASES]
        self.importance_patterns = [re.compile(p, re.IGNORECASE) for p in EXPLICIT_IMPORTANCE]

    def detect(self, text: str) -> Dict[str, any]:
        return {
            "save_request": any(p.search(text) for p in self.save_patterns),
            "recall_request": any(p.search(text) for p in self.recall_patterns),
            "importance_marker": any(p.search(text) for p in self.importance_patterns),
            "matched_phrases": self._get_matches(text),
        }

    def _get_matches(self, text: str) -> List[str]:
        matches = []
        for p in self.save_patterns + self.recall_patterns + self.importance_patterns:
            if match := p.search(text):
                matches.append(match.group())
        return matches
```

**Integration Point**: Run before LLM receives message, add signals to system context

**Test Coverage**:
- 20+ trigger patterns
- Case-insensitive matching
- False positive rate target: <1%
- False negative rate target: 0% (on explicit phrases)

#### Component 1.2: Entity Extractor

**Purpose**: Automatically populate `entities` field for better search and graph quality

**Implementation**:
```python
# src/cortexgraph/preprocessing/entity_extractor.py

import spacy
from typing import List

class EntityExtractor:
    def __init__(self, model: str = "en_core_web_sm"):
        self.nlp = spacy.load(model)

    def extract(self, text: str) -> List[str]:
        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            # Filter to relevant entity types
            if ent.label_ in ["PERSON", "ORG", "PRODUCT", "GPE", "DATE", "TIME"]:
                entities.append(ent.text)

        return list(set(entities))  # Deduplicate
```

**Dependencies**:
- `spacy >= 3.7`
- `en_core_web_sm` model (17MB download)

**Test Coverage**:
- Sample messages with known entities
- Entity type filtering validation
- Deduplication verification

#### Component 1.3: Importance Scorer

**Purpose**: Provide consistent `strength` values based on linguistic cues

**Implementation**:
```python
# src/cortexgraph/preprocessing/importance_scorer.py

import re
from typing import Dict

class ImportanceScorer:
    # Keyword → strength boost mapping
    IMPORTANCE_KEYWORDS = {
        "never forget": 0.8,
        "critical": 0.6,
        "crucial": 0.6,
        "essential": 0.5,
        "important": 0.4,
        "remember this": 0.5,
        "decided": 0.3,
        "going with": 0.3,
        "prefer": 0.2,
        "like": 0.1,
    }

    def score(self, text: str, intent: str = None) -> float:
        base_strength = self._get_base_from_intent(intent)
        boost = self._calculate_boost(text)

        # Clamp to valid range [0.0, 2.0]
        return min(2.0, max(0.0, base_strength + boost))

    def _get_base_from_intent(self, intent: str) -> float:
        base_map = {
            "SAVE_DECISION": 1.3,
            "SAVE_PREFERENCE": 1.1,
            "SAVE_FACT": 1.0,
        }
        return base_map.get(intent, 1.0)

    def _calculate_boost(self, text: str) -> float:
        text_lower = text.lower()
        max_boost = 0.0

        for keyword, boost in self.IMPORTANCE_KEYWORDS.items():
            if keyword in text_lower:
                max_boost = max(max_boost, boost)

        return max_boost
```

**Test Coverage**:
- Keyword → strength mapping validation
- Intent-based base strength verification
- Clamping to valid range [0.0, 2.0]

#### Phase 1 Deliverables

- ✅ `src/cortexgraph/preprocessing/phrase_detector.py`
- ✅ `src/cortexgraph/preprocessing/entity_extractor.py`
- ✅ `src/cortexgraph/preprocessing/importance_scorer.py`
- ✅ `tests/preprocessing/test_phrase_detector.py`
- ✅ `tests/preprocessing/test_entity_extractor.py`
- ✅ `tests/preprocessing/test_importance_scorer.py`
- ✅ Updated system prompt with activation signals
- ✅ Integration with MCP server entry point

**Success Criteria**:
- ✅ 0% missed explicit save requests ("remember this")
- ✅ Entities automatically populated in 80%+ of saves
- ✅ Consistent importance scores (no more arbitrary values)

---

### Phase 2: Intent Classification (3 weeks, 70-80% improvement)

**Timeline**: Weeks 2-4
**Effort**: 1 week data collection, 1 week training, 1 week integration
**Risk**: Medium (requires ML model training, accuracy target: 85%+)

#### Component 2.1: Intent Classifier

**Purpose**: Detect user intent to trigger appropriate memory operations

**Intents**:
- `SAVE_PREFERENCE`: "I prefer X", "I like Y", "I always use Z"
- `SAVE_DECISION`: "I decided to A", "Going with B", "I'll use C"
- `SAVE_FACT`: "My D is E", "The F is G", "H is located at I"
- `RECALL_INFO`: "What did I say about...", "Do you remember..."
- `UPDATE_INFO`: "Actually, change X to Y", "Correction: Z is W"
- `QUESTION`: General question (default, no memory action)

**Model Architecture**:
```python
# src/cortexgraph/preprocessing/intent_classifier.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Dict

class IntentClassifier:
    def __init__(self, model_path: str = "./models/intent_classifier"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

        self.label_map = {
            0: "SAVE_PREFERENCE",
            1: "SAVE_DECISION",
            2: "SAVE_FACT",
            3: "RECALL_INFO",
            4: "UPDATE_INFO",
            5: "QUESTION",
        }

    def classify(self, text: str) -> Dict[str, any]:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=128)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)

        predicted_class = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][predicted_class].item()

        return {
            "intent": self.label_map[predicted_class],
            "confidence": confidence,
            "all_probs": {self.label_map[i]: probs[0][i].item() for i in range(len(self.label_map))},
        }
```

**Model Choice**: DistilBERT (66M parameters, 6-layer distilled BERT)
- Fast inference (~20-30ms on CPU)
- Good accuracy with limited data
- Small model size (~250MB)

**Training Data Requirements**:
- 100-500 examples per intent class
- Total: 600-3000 examples
- Sources:
  - Synthetic generation via GPT-4/Claude
  - Manual curation from real conversations (anonymized)
  - Augmentation techniques (paraphrasing)

**Training Process**:
```bash
# scripts/train_intent_classifier.py

1. Load pre-trained DistilBERT
2. Add classification head (6 classes)
3. Fine-tune on intent dataset
4. Evaluate on held-out test set (target: 85%+ accuracy)
5. Save model checkpoint
```

**Hyperparameters**:
- Learning rate: 2e-5
- Batch size: 16
- Epochs: 3-5
- Warmup steps: 100
- Weight decay: 0.01

#### Component 2.2: Integration

**Purpose**: Connect intent classifier to MCP server and system prompt

**MCP Server Hook**:
```python
# src/cortexgraph/server.py

from .preprocessing import PhraseDetector, EntityExtractor, ImportanceScorer, IntentClassifier

# Initialize preprocessing components
phrase_detector = PhraseDetector()
entity_extractor = EntityExtractor()
importance_scorer = ImportanceScorer()
intent_classifier = IntentClassifier()

@mcp.before_completion()
async def preprocess_message(message: str) -> Dict:
    """
    Run preprocessing before LLM receives message.
    Returns activation signals to be injected into system context.
    """
    phrase_signals = phrase_detector.detect(message)
    intent_result = intent_classifier.classify(message)
    entities = entity_extractor.extract(message)
    importance = importance_scorer.score(message, intent_result["intent"])

    # Construct activation signals
    signals = {
        "phrase_matches": phrase_signals,
        "intent": intent_result["intent"],
        "intent_confidence": intent_result["confidence"],
        "entities": entities,
        "suggested_strength": importance,
    }

    # Generate activation recommendation
    if phrase_signals["save_request"]:
        signals["action_recommendation"] = "MUST_SAVE"
    elif intent_result["intent"] in ["SAVE_PREFERENCE", "SAVE_DECISION", "SAVE_FACT"] and intent_result["confidence"] > 0.8:
        signals["action_recommendation"] = "SHOULD_SAVE"
    elif intent_result["intent"] == "RECALL_INFO" and intent_result["confidence"] > 0.7:
        signals["action_recommendation"] = "SHOULD_SEARCH"
    else:
        signals["action_recommendation"] = "NONE"

    return signals
```

**System Prompt Enhancement**:
```markdown
# docs/prompts/memory_system_prompt.md (new section)

## Activation Signals

You will receive preprocessing signals with each user message:

**Action Recommendations**:
- `MUST_SAVE`: User explicitly requested save ("remember this") - you MUST call save_memory
- `SHOULD_SAVE`: High-confidence detection of save-worthy content (preference, decision, fact) - you SHOULD call save_memory
- `SHOULD_SEARCH`: User asking for past information - you SHOULD call search_memory
- `NONE`: No strong signal, use your judgment

**Pre-filled Parameters**:
When action is MUST_SAVE or SHOULD_SAVE, you will receive:
- `entities`: Extracted entities (you can add/remove)
- `suggested_strength`: Importance score (you can adjust)
- `intent`: Content type (PREFERENCE, DECISION, FACT)

**Your Role**:
1. Review preprocessing signals
2. Confirm or adjust parameters based on context
3. Call appropriate tool (save_memory, search_memory, etc.)
4. If uncertain, use your judgment - preprocessing is assistance, not mandate
```

**Configuration**:
```python
# src/cortexgraph/config.py (new section)

# Conversational Activation
MNEMEX_ENABLE_PREPROCESSING = os.getenv("MNEMEX_ENABLE_PREPROCESSING", "true").lower() == "true"
MNEMEX_INTENT_MODEL_PATH = os.getenv("MNEMEX_INTENT_MODEL_PATH", "./models/intent_classifier")
MNEMEX_INTENT_CONFIDENCE_THRESHOLD = float(os.getenv("MNEMEX_INTENT_CONFIDENCE_THRESHOLD", "0.7"))
MNEMEX_AUTO_SAVE_CONFIDENCE_THRESHOLD = float(os.getenv("MNEMEX_AUTO_SAVE_CONFIDENCE_THRESHOLD", "0.8"))
MNEMEX_SPACY_MODEL = os.getenv("MNEMEX_SPACY_MODEL", "en_core_web_sm")
```

#### Phase 2 Deliverables

- ✅ Intent classification training dataset (600-3000 examples)
- ✅ Training script (`scripts/train_intent_classifier.py`)
- ✅ Trained DistilBERT model checkpoint
- ✅ `src/cortexgraph/preprocessing/intent_classifier.py`
- ✅ Integration with MCP server (`before_completion` hook)
- ✅ Enhanced system prompt with activation signals
- ✅ Configuration options in `config.py`
- ✅ `tests/preprocessing/test_intent_classifier.py`
- ✅ Performance evaluation report (accuracy, precision, recall per class)

**Success Criteria**:
- ✅ 85%+ intent classification accuracy on test set
- ✅ Implicit preferences detected (e.g., "I prefer X" → auto-save suggested)
- ✅ 70-80% overall improvement in activation reliability (user testing)

---

### Phase 3: Advanced Features (4 weeks, 85-90% improvement)

**Timeline**: Weeks 5-8
**Effort**: 1 week per component
**Risk**: Medium-High (complex features, integration challenges)

#### Component 3.1: Tag Suggester

**Purpose**: Automatically suggest tags to improve search and cross-domain detection

**Approaches**:

**1. Keyword Extraction (KeyBERT)**:
```python
# src/cortexgraph/preprocessing/tag_suggester.py

from keybert import KeyBERT

class TagSuggester:
    def __init__(self):
        self.model = KeyBERT()

    def suggest_tags(self, text: str, top_k: int = 5) -> List[str]:
        keywords = self.model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=top_k,
        )
        return [kw[0] for kw in keywords]
```

**2. Zero-Shot Classification** (for predefined categories):
```python
from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def classify_into_categories(text: str, categories: List[str]) -> List[str]:
    result = classifier(text, categories, multi_label=True)
    # Return categories with confidence > 0.5
    return [label for label, score in zip(result["labels"], result["scores"]) if score > 0.5]
```

**3. Hybrid Approach**:
- Extract keywords via KeyBERT (content-specific)
- Classify into categories via zero-shot (broad themes)
- Combine and rank by relevance

**Integration**:
- Pre-fill `tags` parameter for `save_memory`
- LLM reviews and adjusts as needed
- User feedback loop: Track accepted vs. rejected suggestions

#### Component 3.2: Multi-Message Context

**Purpose**: Improve extraction of implicit preferences from conversation history

**Implementation**:
```python
# src/cortexgraph/preprocessing/context_manager.py

from collections import deque
from typing import List, Dict

class ConversationContext:
    def __init__(self, max_messages: int = 10):
        self.buffer = deque(maxlen=max_messages)

    def add_message(self, role: str, content: str):
        self.buffer.append({"role": role, "content": content})

    def get_context(self, window_size: int = 5) -> List[Dict]:
        return list(self.buffer)[-window_size:]

    def generate_summary(self) -> str:
        # TODO: Use LLM to generate rolling summary of conversation
        # Useful for detecting patterns across multiple turns
        pass
```

**Use Cases**:
- User states preference across multiple messages
- Decision emerges from discussion (not single statement)
- Fact mentioned indirectly, then clarified later

**Integration Point**: Pass context to intent classifier and tag suggester

#### Component 3.3: Automatic Deduplication

**Purpose**: Prevent redundant saves by detecting similar existing memories

**Implementation**:
```python
# src/cortexgraph/preprocessing/dedup_checker.py

from .storage import JSONLStorage
from sentence_transformers import SentenceTransformer, util

class DeduplicationChecker:
    def __init__(self, storage: JSONLStorage, similarity_threshold: float = 0.85):
        self.storage = storage
        self.threshold = similarity_threshold
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def check_before_save(self, content: str, entities: List[str]) -> Dict:
        # Search for similar memories
        candidates = self.storage.search(content, top_k=5)

        if not candidates:
            return {"is_duplicate": False}

        # Calculate semantic similarity
        new_embedding = self.embedder.encode(content, convert_to_tensor=True)
        similarities = []

        for candidate in candidates:
            candidate_embedding = self.embedder.encode(candidate["content"], convert_to_tensor=True)
            similarity = util.cos_sim(new_embedding, candidate_embedding).item()
            similarities.append((candidate, similarity))

        # Find best match
        best_match, best_score = max(similarities, key=lambda x: x[1])

        if best_score > self.threshold:
            return {
                "is_duplicate": True,
                "similar_memory": best_match,
                "similarity_score": best_score,
                "recommendation": "MERGE" if best_score > 0.9 else "REVIEW",
            }

        return {"is_duplicate": False}
```

**Integration**:
- Run before calling `save_memory`
- If duplicate detected, prompt LLM: "Similar memory exists (score: 0.92). Options: 1) Merge, 2) Save as new, 3) Skip"
- LLM decides based on context

**Relation to Existing Tools**:
- Complements existing `consolidate_memories` tool (proactive vs. reactive)
- Uses same similarity logic as `cluster_memories`

#### Phase 3 Deliverables

- ✅ `src/cortexgraph/preprocessing/tag_suggester.py`
- ✅ `src/cortexgraph/preprocessing/context_manager.py`
- ✅ `src/cortexgraph/preprocessing/dedup_checker.py`
- ✅ Integration tests for multi-message scenarios
- ✅ User acceptance testing (A/B test: old vs. new)
- ✅ Performance benchmarks (latency, accuracy)
- ✅ Documentation updates

**Success Criteria**:
- ✅ Tags automatically suggested and accepted 70%+ of time
- ✅ Multi-message context improves implicit preference detection by 20%+
- ✅ Near-duplicate detection prevents redundant saves (false positive rate <5%)
- ✅ 85-90% overall improvement in activation reliability

---

## Testing Strategy

### Unit Tests

**Phase 1 Components**:
```python
# tests/preprocessing/test_phrase_detector.py

def test_explicit_save_phrases():
    detector = PhraseDetector()

    test_cases = [
        ("Remember this for later", True),
        ("Don't forget to use TypeScript", True),
        ("This is important", True),
        ("Just a regular message", False),
    ]

    for text, expected in test_cases:
        result = detector.detect(text)
        assert result["save_request"] == expected

def test_case_insensitivity():
    detector = PhraseDetector()
    assert detector.detect("REMEMBER THIS")["save_request"]
    assert detector.detect("remember this")["save_request"]
    assert detector.detect("ReMeMbEr ThIs")["save_request"]
```

**Phase 2 Components**:
```python
# tests/preprocessing/test_intent_classifier.py

def test_intent_classification_accuracy():
    classifier = IntentClassifier()
    test_set = load_test_set()  # Held-out 20% of training data

    correct = 0
    total = len(test_set)

    for example in test_set:
        result = classifier.classify(example["text"])
        if result["intent"] == example["label"]:
            correct += 1

    accuracy = correct / total
    assert accuracy > 0.85  # 85% accuracy target
```

### Integration Tests

```python
# tests/integration/test_preprocessing_pipeline.py

async def test_end_to_end_activation():
    """Test complete flow: message → preprocessing → LLM → save"""

    # Setup
    mcp_server = setup_test_server()
    test_message = "I prefer TypeScript for backend projects"

    # Execute
    signals = await mcp_server.preprocess_message(test_message)

    # Verify preprocessing
    assert signals["intent"] == "SAVE_PREFERENCE"
    assert signals["intent_confidence"] > 0.7
    assert "TypeScript" in signals["entities"]
    assert signals["suggested_strength"] > 1.0
    assert signals["action_recommendation"] == "SHOULD_SAVE"

    # Simulate LLM calling save_memory with pre-filled params
    memory_id = await mcp_server.save_memory(
        content="User prefers TypeScript for backend projects",
        entities=signals["entities"],
        tags=["preferences", "typescript", "backend"],
        strength=signals["suggested_strength"],
    )

    # Verify save
    memory = await mcp_server.storage.get_memory(memory_id)
    assert memory is not None
    assert "TypeScript" in memory.entities
```

### User Acceptance Testing (UAT)

**A/B Test Design**:
- **Control Group**: Current cortexgraph (LLM-only activation)
- **Treatment Group**: New cortexgraph (preprocessing + LLM)
- **Sample Size**: 20-30 users, 2 weeks of usage
- **Metrics**:
  - Save rate (% of messages resulting in saves)
  - User satisfaction (survey: "Did system miss anything important?")
  - False positive rate (unnecessary saves)
  - False negative rate (missed important information)

**Success Criteria**:
- Treatment group: 85-90% save rate on save-worthy content
- Control group: ~40% save rate (baseline)
- User satisfaction: 8/10 or higher
- False positive rate: <10%
- False negative rate: <5% (excluding ambiguous cases)

---

## Integration Points

### 1. MCP Server Entry Point

**File**: `src/cortexgraph/server.py`

**Changes**:
```python
from .preprocessing import (
    PhraseDetector,
    EntityExtractor,
    ImportanceScorer,
    IntentClassifier,
    TagSuggester,
    ConversationContext,
    DeduplicationChecker,
)

# Initialize preprocessing components (lazy loading for performance)
_preprocessing_components = None

def get_preprocessing_components():
    global _preprocessing_components
    if _preprocessing_components is None:
        _preprocessing_components = {
            "phrase_detector": PhraseDetector(),
            "entity_extractor": EntityExtractor(),
            "importance_scorer": ImportanceScorer(),
            "intent_classifier": IntentClassifier() if config.MNEMEX_ENABLE_PREPROCESSING else None,
            "tag_suggester": TagSuggester() if config.MNEMEX_ENABLE_PREPROCESSING else None,
            "context_manager": ConversationContext(),
            "dedup_checker": DeduplicationChecker(storage),
        }
    return _preprocessing_components

@mcp.before_completion()
async def preprocess_message(message: str, role: str = "user") -> Dict:
    """
    Preprocessing hook called before LLM receives message.
    Returns activation signals to be injected into system context.
    """
    if not config.MNEMEX_ENABLE_PREPROCESSING:
        return {}

    components = get_preprocessing_components()

    # Add message to conversation context
    components["context_manager"].add_message(role, message)

    # Run preprocessing pipeline
    phrase_signals = components["phrase_detector"].detect(message)
    intent_result = components["intent_classifier"].classify(message)
    entities = components["entity_extractor"].extract(message)
    importance = components["importance_scorer"].score(message, intent_result["intent"])
    tags = components["tag_suggester"].suggest_tags(message) if components["tag_suggester"] else []

    # Check for duplicates if save is recommended
    dedup_result = {}
    if intent_result["intent"].startswith("SAVE_"):
        dedup_result = components["dedup_checker"].check_before_save(message, entities)

    # Construct activation signals
    return construct_activation_signals(
        phrase_signals, intent_result, entities, importance, tags, dedup_result
    )
```

### 2. System Prompt Enhancement

**File**: `docs/prompts/memory_system_prompt.md`

**New Section** (to be appended):
```markdown
---

## Activation Signals (Preprocessing)

You receive preprocessing signals with each user message to assist memory decisions.

### Signal Types

**1. Action Recommendations**
- `MUST_SAVE`: Explicit user request ("remember this") - mandatory save
- `SHOULD_SAVE`: High-confidence save-worthy content - strongly recommended
- `SHOULD_SEARCH`: User asking for past info - search recommended
- `NONE`: No strong signal, use your judgment

**2. Pre-filled Parameters**
When save is recommended, you receive:
- `entities`: Auto-extracted entities (PERSON, ORG, PRODUCT, etc.)
- `suggested_strength`: Importance score (0.0-2.0)
- `suggested_tags`: Relevant tags from content
- `intent`: Content type (PREFERENCE, DECISION, FACT, etc.)

**3. Deduplication Alerts**
If similar memory exists:
- `similar_memory`: Existing memory content
- `similarity_score`: How similar (0.0-1.0)
- `recommendation`: MERGE or REVIEW

### How to Use Signals

**When action is MUST_SAVE**:
1. Review pre-filled parameters
2. Adjust if needed (add context, refine tags)
3. Call `save_memory` with parameters

**When action is SHOULD_SAVE**:
1. Confirm content is save-worthy given full context
2. Adjust parameters as needed
3. Call `save_memory` if confirmed

**When action is SHOULD_SEARCH**:
1. Call `search_memory` with relevant query
2. Surface information to user

**When deduplication alert**:
1. Review similar memory
2. Decide: MERGE (update existing), NEW (save anyway), SKIP (don't save)
3. Explain decision to user

### Important Notes

- Preprocessing is **assistance**, not mandate
- You have final say on all memory operations
- Use your judgment for edge cases
- If uncertain, err toward saving (decay handles false positives)
- Signals improve reliability but don't replace reasoning
```

### 3. Configuration File

**File**: `src/cortexgraph/config.py`

**New Section**:
```python
# ============================================================================
# Conversational Activation Configuration
# ============================================================================

# Enable/disable preprocessing layer
MNEMEX_ENABLE_PREPROCESSING = os.getenv("MNEMEX_ENABLE_PREPROCESSING", "true").lower() == "true"

# Intent Classification
MNEMEX_INTENT_MODEL_PATH = os.getenv("MNEMEX_INTENT_MODEL_PATH", "./models/intent_classifier")
MNEMEX_INTENT_CONFIDENCE_THRESHOLD = float(os.getenv("MNEMEX_INTENT_CONFIDENCE_THRESHOLD", "0.7"))
MNEMEX_AUTO_SAVE_CONFIDENCE_THRESHOLD = float(os.getenv("MNEMEX_AUTO_SAVE_CONFIDENCE_THRESHOLD", "0.8"))

# Entity Extraction
MNEMEX_SPACY_MODEL = os.getenv("MNEMEX_SPACY_MODEL", "en_core_web_sm")

# Tag Suggestion
MNEMEX_ENABLE_TAG_SUGGESTION = os.getenv("MNEMEX_ENABLE_TAG_SUGGESTION", "true").lower() == "true"
MNEMEX_TAG_SUGGESTION_TOP_K = int(os.getenv("MNEMEX_TAG_SUGGESTION_TOP_K", "5"))

# Conversation Context
MNEMEX_CONTEXT_WINDOW_SIZE = int(os.getenv("MNEMEX_CONTEXT_WINDOW_SIZE", "10"))

# Deduplication
MNEMEX_ENABLE_DEDUP_CHECK = os.getenv("MNEMEX_ENABLE_DEDUP_CHECK", "true").lower() == "true"
MNEMEX_DEDUP_SIMILARITY_THRESHOLD = float(os.getenv("MNEMEX_DEDUP_SIMILARITY_THRESHOLD", "0.85"))
```

---

## Dependencies

### Python Packages

**Phase 1**:
```toml
# pyproject.toml additions

[project.dependencies]
# Existing dependencies...
spacy = "^3.7.0"
```

**Installation**:
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

**Phase 2**:
```toml
transformers = "^4.35.0"
torch = "^2.1.0"  # or tensorflow
scikit-learn = "^1.3.0"
```

**Phase 3**:
```toml
keybert = "^0.8.0"
sentence-transformers = "^2.2.0"
```

### Model Storage

**Models to download/train**:
- `en_core_web_sm`: 17MB (spaCy English model)
- Intent classifier: ~250MB (fine-tuned DistilBERT)
- Tag suggester: ~120MB (KeyBERT with sentence-transformers backend)
- Deduplication embedder: ~80MB (sentence-transformers/all-MiniLM-L6-v2)

**Total storage**: ~470MB

**Inference Requirements**:
- CPU: Sufficient (all models optimized for CPU inference)
- RAM: +300-500MB when all models loaded
- Latency: <100ms total preprocessing time

---

## Performance Considerations

### Latency Analysis

**Target**: <100ms total preprocessing time (avoid blocking conversation flow)

**Breakdown**:
- Phrase detection: ~1ms (regex)
- Entity extraction: ~20-30ms (spaCy)
- Intent classification: ~20-30ms (DistilBERT on CPU)
- Importance scoring: ~1ms (heuristics)
- Tag suggestion: ~30-40ms (KeyBERT, Phase 3)
- Deduplication check: ~20-30ms (embedding + similarity, Phase 3)

**Optimization Strategies**:
1. **Lazy Loading**: Load models only when first needed
2. **Caching**: Cache recent entity/intent results for similar messages
3. **Async Processing**: Run non-blocking preprocessing in background
4. **Batching**: If processing multiple messages, batch through models
5. **Model Quantization**: Use INT8 quantized models for faster inference

### Memory Management

**Model Loading**:
- Load on first use, not at startup
- Share models across requests (singleton pattern)
- Option to run preprocessing in separate process/container

**Configuration Option**:
```python
MNEMEX_PREPROCESSING_MODE = "inline"  # or "async" or "separate_process"
```

---

## Risks & Mitigations

### Risk 1: Intent Classifier Accuracy Below 85%

**Impact**: Medium - Lower accuracy reduces reliability gains

**Mitigation**:
- Start with rule-based fallback for low-confidence predictions
- Collect user feedback: "Was this save appropriate?"
- Active learning: Retrain with corrected examples
- Fallback to phrase detection + LLM judgment if confidence < threshold

### Risk 2: False Positives (Too Many Auto-Saves)

**Impact**: Medium - Clutters memory store, annoys users

**Mitigation**:
- Conservative confidence thresholds (0.8 for auto-save)
- LLM still has final say (can reject preprocessing suggestion)
- User feedback loop: "Was this save unnecessary?"
- Decay algorithm naturally handles false positives (unused memories fade)

### Risk 3: Model Inference Latency

**Impact**: Low - Could slow conversation if >200ms

**Mitigation**:
- Use lightweight models (DistilBERT, not full BERT)
- Async processing (don't block LLM response)
- Cache recent results
- Quantization for faster inference
- Option to disable preprocessing if latency critical

### Risk 4: Preprocessing Overhead Complexity

**Impact**: Low - Adds code complexity and maintenance burden

**Mitigation**:
- Clear separation of concerns (preprocessing layer is modular)
- Each component independently testable
- Configuration to disable features if not needed
- Graceful degradation (system works even if preprocessing fails)

### Risk 5: Training Data Quality

**Impact**: Medium - Poor training data → poor intent classifier

**Mitigation**:
- Use GPT-4/Claude for synthetic data generation (high quality)
- Manual review of training examples
- Balance classes (equal examples per intent)
- Augmentation techniques (paraphrasing, backtranslation)
- Held-out test set for validation

---

## Success Metrics

### Quantitative Metrics

**Activation Reliability** (Primary Metric):
- **Baseline**: ~40% (current, LLM-only)
- **Phase 1 Target**: 60-70%
- **Phase 2 Target**: 75-85%
- **Phase 3 Target**: 85-90%

**Measurement**: % of save-worthy content that results in actual saves (human-annotated test set)

**Intent Classification Accuracy**:
- **Target**: 85%+ on held-out test set
- **Per-Class Precision/Recall**: >80% for each intent

**False Positive Rate**:
- **Target**: <10% (saves that shouldn't have happened)
- **Measurement**: User feedback + manual review

**False Negative Rate**:
- **Target**: <5% (missed important information)
- **Measurement**: User reports "you forgot X"

**Latency**:
- **Target**: <100ms preprocessing time
- **Measurement**: Average time from message receipt to preprocessing complete

### Qualitative Metrics

**User Satisfaction**:
- Survey: "Does the system remember important information?" (8/10 target)
- Survey: "How often does the system miss something important?" (Rarely/Never target)
- Survey: "Are saves appropriate and relevant?" (7/10 target)

**Developer Experience**:
- Code maintainability (modular, well-tested)
- Ease of adding new intents or patterns
- Configuration flexibility

---

## Future Enhancements

### Short-Term (Next 6 Months)

**1. Custom Entity Types**
- Fine-tune spaCy for domain-specific entities
- Technology stack entities (Python → TECHNOLOGY)
- Preference entities (TypeScript → PREFERENCE:LANGUAGE)

**2. Reinforcement Learning from User Corrections**
- Track when users override preprocessing suggestions
- Retrain models with correction data
- Personalized models per user

**3. Multi-Language Support**
- Add spaCy models for other languages
- Multi-lingual intent classification
- Language detection + routing

### Medium-Term (6-12 Months)

**4. Active Learning Pipeline**
- Identify low-confidence predictions
- Request user labels for uncertain cases
- Continuously improve models with feedback

**5. Personalized Intent Models**
- Per-user fine-tuning based on usage patterns
- Adaptive confidence thresholds
- Preference learning (user prefers high/low activation rate)

**6. Cross-Turn Conversation Understanding**
- Dialog state tracking
- Coreference resolution ("it", "that", etc.)
- Multi-turn decision detection

### Long-Term (12+ Months)

**7. Automatic Relation Inference**
- Detect relationships between entities
- Populate `create_relation` automatically
- Build richer knowledge graph structure

**8. Temporal Reasoning**
- Understand time references ("last week", "in the future")
- Auto-populate temporal metadata
- Query by time periods

**9. Explainability Dashboard**
- Show why system saved/didn't save
- Visualize confidence scores and signals
- Allow users to adjust preprocessing behavior

---

## Timeline Summary

| Phase | Duration | Components | Expected Impact |
|-------|----------|------------|-----------------|
| **Phase 1** | 1 week | Phrase Detector, Entity Extractor, Importance Scorer | 40-50% improvement |
| **Phase 2** | 3 weeks | Intent Classifier, Integration, System Prompt Updates | 70-80% improvement |
| **Phase 3** | 4 weeks | Tag Suggester, Multi-Message Context, Deduplication | 85-90% improvement |
| **Testing & Deployment** | 1 week | UAT, Performance Tuning, Documentation | Production-ready |
| **Total** | **9 weeks** | All components integrated and tested | **85-90% activation reliability** |

---

## Conclusion

This architectural plan transforms cortexgraph from **sporadic, LLM-dependent activation** to **reliable, preprocessing-assisted activation**. By adding a preprocessing layer that detects patterns, extracts entities, classifies intent, and scores importance, we reduce LLM cognitive load while preserving flexibility.

**Key Principles**:
1. **Hybrid Architecture**: Deterministic preprocessing + LLM judgment
2. **Progressive Enhancement**: Each component adds independent value
3. **Research-Backed**: Built on 2024-2025 state-of-the-art approaches
4. **Production-Ready**: Optimized for latency, maintainability, configurability

**Expected Outcome**: 85-90% activation reliability, dramatically improving user experience and trust in cortexgraph as a production memory system.

---

## References

### Academic Papers
- ArXiv 2504.19413v1: "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory"
- Wiley Expert Systems (2025): "Intent detection for task-oriented conversational agents"
- MDPI Applied Sciences (2025): "Knowledge Graph Construction: Extraction, Learning, and Evaluation"
- Frontiers in Computer Science (2025): "Knowledge Graph Construction with LLMs"

### Industry Tools
- Mem0: github.com/mem0ai/mem0
- spaCy: spacy.io
- Transformers (Hugging Face): huggingface.co/transformers
- KeyBERT: github.com/MaartenGr/KeyBERT
- Sentence-Transformers: github.com/UKPLab/sentence-transformers

### cortexgraph Documentation
- Architecture: `docs/architecture.md`
- API Reference: `docs/api.md`
- Smart Prompting (current): `docs/prompts/memory_system_prompt.md`
- Scoring Algorithm: `docs/scoring_algorithm.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Author**: Claude (Sonnet 4.5) with STOPPER Protocol
**Approved By**: Scot Campbell
**Next Review**: After Phase 1 completion
