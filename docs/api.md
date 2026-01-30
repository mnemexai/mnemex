# CortexGraph API Reference

Complete reference for all MCP tools provided by CortexGraph.

## Core Utilities (v1.2.0+)

New utility modules provide reusable functions for similarity calculations, search validation, and text processing.

### Similarity Functions

The `cortexgraph.core.similarity` module provides similarity metrics:

```python
from cortexgraph.core import (
    cosine_similarity,
    jaccard_similarity,
    tfidf_similarity,
    text_similarity,
    tokenize_text,
    calculate_centroid,
)

# Cosine similarity for embeddings
similarity = cosine_similarity(vec1, vec2)

# Jaccard similarity for token sets
similarity = jaccard_similarity(tokens1, tokens2)

# Text similarity (Jaccard on tokenized text)
similarity = text_similarity(text1, text2)

# TF-IDF weighted similarity
similarity = tfidf_similarity(text1, text2)

# Calculate centroid of embeddings
centroid = calculate_centroid(embeddings)
```

### Search Validation

The `cortexgraph.core.search_common` module provides shared search parameter validation:

```python
from cortexgraph.core import SearchParams, validate_search_params

# Validate and normalize search parameters
params = validate_search_params(
    query="example",
    tags=["tag1"],
    limit=10,
    min_score=0.1,
)
# Returns SearchParams dataclass with validated values
```

### Text Utilities

```python
from cortexgraph.core import truncate_content

# Truncate content with ellipsis
preview = truncate_content(content, max_length=300)
```

### Storage Utilities

```python
from cortexgraph.agents import get_storage

# Get the current storage instance
storage = get_storage()
```

### Batch Operations (v1.2.0+)

For better performance when processing multiple items:

```python
from cortexgraph.storage.jsonl_storage import JSONLStorage

storage = JSONLStorage()
storage.connect()

# Batch delete memories
deleted_count = storage.delete_memories_batch(["id1", "id2", "id3"])

# Batch create relations
storage.create_relations_batch([relation1, relation2, relation3])
```

These operations are significantly faster than individual calls for bulk processing (used internally by consolidation agents).

---

## Core Memory Tools

### save_memory

Save a new memory to short-term storage with optional auto-enrichment (v0.6.0+).

**Auto-Enrichment (NEW in v0.6.0):**

When `enable_preprocessing=true` (default), this tool automatically:
- Extracts entities from content if `entities=None` using spaCy NER
- Calculates importance/strength if `strength=None` based on content markers
- No manual entity specification needed - just provide natural language content

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `content` | string | Yes | The content to remember |
| `tags` | array[string] | No | Tags for categorization |
| `entities` | array[string] | No | Named entities (auto-extracted if None) **v0.6.0+** |
| `source` | string | No | Source of the memory |
| `context` | string | No | Context when memory was created |
| `meta` | object | No | Additional custom metadata |
| `strength` | float (1.0-2.0) | No | Importance multiplier (auto-calculated if None) **v0.6.0+** |

**Returns:**

```json
{
  "success": true,
  "memory_id": "abc-123-def-456",
  "message": "Memory saved with ID: abc-123-def-456",
  "has_embedding": false,
  "enrichment_applied": true
}
```

**Example (v0.6.0+ with auto-enrichment):**

```json
{
  "content": "Use JWT tokens for authentication in all new APIs"
}
```

Auto-enriched result:
- `entities`: ["jwt", "authentication", "apis"] (auto-extracted)
- `strength`: 1.0 (auto-calculated, no importance markers)

**Example (explicit parameters):**

```json
{
  "content": "The project deadline is December 15th",
  "tags": ["project", "deadline"],
  "entities": ["project", "december"],
  "source": "team meeting",
  "context": "Q4 planning discussion",
  "strength": 1.5
}
```

**Strength Parameter (v0.6.0+):**

Controls memory retention:
- `1.0` (default) - Normal importance
- `1.3-1.5` - Important information, preferences
- `1.8-2.0` - Critical decisions, never-forget facts

Auto-calculation considers:
- Content length
- Entity count
- Importance markers ("important", "critical", "remember")
- Questions (slightly lower strength)

---

### search_memory

Search for memories with optional filters and scoring.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | No | - | Text query to search for |
| `tags` | array[string] | No | - | Filter by tags |
| `top_k` | integer | No | 10 | Maximum number of results |
| `window_days` | integer | No | - | Only search last N days |
| `min_score` | float | No | - | Minimum decay score threshold |
| `use_embeddings` | boolean | No | false | Use semantic search |

**Returns:**

```json
{
  "success": true,
  "count": 3,
  "results": [
    {
      "id": "abc-123",
      "content": "Project deadline is Dec 15",
      "tags": ["project", "deadline"],
      "score": 0.8234,
      "similarity": null,
      "use_count": 3,
      "last_used": 1699012345,
      "age_days": 2.3
    }
  ]
}
```

**Example:**

```json
{
  "query": "deadline",
  "tags": ["project"],
  "top_k": 5,
  "window_days": 7,
  "min_score": 0.1
}
```

---

### search_unified

Search across STM (JSONL) and LTM (Obsidian vault index) with unified ranking and deduplication.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | No | - | Text query to search for |
| `tags` | array[string] | No | - | Filter by tags |
| `limit` | integer | No | 10 | Maximum total results |
| `stm_weight` | number | No | 1.0 | Weight for STM results |
| `ltm_weight` | number | No | 0.7 | Weight for LTM results |
| `window_days` | integer | No | - | Only include STM from last N days |
| `min_score` | number | No | - | Minimum STM decay score |
| `verbose` | boolean | No | false | Include metadata (IDs, paths) |

**Returns:** formatted text block combining STM and LTM results ordered by score.

**Example:**

```json
{
  "query": "typescript preferences",
  "tags": ["preferences"],
  "limit": 8,
  "stm_weight": 1.0,
  "ltm_weight": 0.7,
  "window_days": 14,
  "min_score": 0.1,
  "verbose": true
}
```

---

### touch_memory

Reinforce a memory by updating its access time and use count.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `memory_id` | string | Yes | - | ID of memory to reinforce |
| `boost_strength` | boolean | No | false | Boost base strength |

**Returns:**

```json
{
  "success": true,
  "memory_id": "abc-123",
  "old_score": 0.4521,
  "new_score": 0.7832,
  "use_count": 4,
  "strength": 1.1,
  "message": "Memory reinforced. Score: 0.45 -> 0.78"
}
```

**Example:**

```json
{
  "memory_id": "abc-123",
  "boost_strength": true
}
```

---

### observe_memory_usage

Record that memories were actively used in conversation for natural spaced repetition. This tool should be called when memories are actually **incorporated into responses**, not just retrieved.

Enables natural reinforcement through:
- Updates usage statistics (last_used, use_count)
- Detects cross-domain usage (via tag Jaccard similarity)
- Automatically boosts strength for cross-domain usage
- Recalculates review priority for next search

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `memory_ids` | array[string] | Yes | - | IDs of memories that were used |
| `context_tags` | array[string] | No | [] | Tags representing current conversation context |

**Returns:**

```json
{
  "reinforced": true,
  "count": 2,
  "cross_domain_count": 1,
  "results": [
    {
      "id": "mem-123",
      "status": "reinforced",
      "cross_domain": false,
      "new_use_count": 4,
      "new_review_count": 3,
      "strength": 1.0
    },
    {
      "id": "mem-456",
      "status": "reinforced",
      "cross_domain": true,
      "new_use_count": 2,
      "new_review_count": 1,
      "strength": 1.1
    }
  ]
}
```

**Example:**

```json
{
  "memory_ids": ["mem-123", "mem-456"],
  "context_tags": ["api", "authentication", "backend"]
}
```

**Use Case:**

```
User asks: "Can you help with authentication in my API?"
→ System searches and retrieves JWT preference memory (tags: [security, jwt, preferences])
→ System uses memory to answer question
→ System calls observe_memory_usage:
  {
    "memory_ids": ["jwt-pref-123"],
    "context_tags": ["api", "authentication", "backend"]
  }
→ Cross-domain usage detected (0% tag overlap)
→ Memory strength boosted: 1.0 → 1.1
→ Next search naturally surfaces this memory if in danger zone
```

**Configuration:**

```bash
# Enable/disable automatic reinforcement
CORTEXGRAPH_AUTO_REINFORCE=true

# If disabled, returns:
{
  "reinforced": false,
  "reason": "auto_reinforce is disabled in config",
  "count": 0
}
```

---

### analyze_message

**NEW in v0.6.0** - Analyze a message to determine if it contains memory-worthy content. Provides decision support for Claude to decide whether to call `save_memory`.

This tool automatically:
- Detects save-related phrases ("remember this", "don't forget", "keep in mind")
- Extracts entities using spaCy NER
- Calculates importance/strength based on content markers
- Provides confidence scores and reasoning

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `message` | string | Yes | User message to analyze for memory-worthy content |

**Returns:**

```json
{
  "should_save": true,
  "confidence": 0.9,
  "suggested_entities": ["typescript", "javascript", "preferences"],
  "suggested_tags": [],
  "suggested_strength": 1.5,
  "reasoning": "Detected: ['remember'] importance_marker: True entities_found: 3"
}
```

**Example:**

```json
{
  "message": "Remember: I prefer TypeScript over JavaScript for all new projects"
}
```

**Confidence Levels:**

| Confidence | Interpretation | Recommended Action |
|------------|----------------|-------------------|
| > 0.7 | High confidence | Automatically save memory |
| 0.4 - 0.7 | Medium confidence | Ask user first |
| < 0.4 | Low confidence | Don't save unless user explicitly requests |

**Use Case:**

```
User: "Remember: I prefer dark mode in all my apps"
→ Claude calls analyze_message
→ Response: should_save=true, confidence=0.9, strength=1.5
→ Claude automatically calls save_memory with suggested parameters
→ No explicit commands needed - natural conversation
```

---

### analyze_for_recall

**NEW in v0.6.0** - Analyze a message to detect recall/search intent. Provides decision support for Claude to decide whether to call `search_memory`.

This tool automatically:
- Detects recall-related phrases ("what did I say about", "do you remember")
- Extracts query terms from the message
- Suggests entities to filter by
- Provides confidence scores and reasoning

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `message` | string | Yes | User message to analyze for recall intent |

**Returns:**

```json
{
  "should_search": true,
  "confidence": 0.9,
  "suggested_query": "TypeScript preferences",
  "suggested_tags": [],
  "suggested_entities": ["typescript"],
  "reasoning": "Detected: ['what did i say about'] entities_found: 1"
}
```

**Example:**

```json
{
  "message": "What did I say about TypeScript?"
}
```

**Confidence Levels:**

| Confidence | Interpretation | Recommended Action |
|------------|----------------|-------------------|
| > 0.7 | High confidence | Automatically search memory |
| 0.4 - 0.7 | Medium confidence | Ask user first |
| < 0.4 | Low confidence | Don't search unless user explicitly requests |

**Use Case:**

```
User: "What did I say about my API preferences?"
→ Claude calls analyze_for_recall
→ Response: should_search=true, confidence=0.9, query="API preferences"
→ Claude automatically calls search_memory with suggested query
→ Retrieves and uses relevant memories in response
```

**Combined Workflow (v0.6.0):**

```
1. User: "Remember: I prefer JWT for authentication"
   → analyze_message: should_save=true, strength=1.5, entities=["jwt", "authentication"]
   → save_memory auto-called with auto-enrichment

2. User: "What did I say about authentication?"
   → analyze_for_recall: should_search=true, query="authentication"
   → search_memory auto-called
   → JWT preference retrieved and used in response

3. Result: Natural conversation without explicit memory commands
```

---

## Management Tools

### gc

Perform garbage collection on low-scoring memories.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `dry_run` | boolean | No | true | Preview without removing |
| `archive_instead` | boolean | No | false | Archive instead of delete |
| `limit` | integer | No | - | Max memories to process |

**Returns:**

```json
{
  "success": true,
  "dry_run": true,
  "removed_count": 0,
  "archived_count": 15,
  "freed_score_sum": 0.4523,
  "memory_ids": ["mem-1", "mem-2", "..."],
  "total_affected": 15,
  "message": "Would remove 15 low-scoring memories (threshold: 0.05)"
}
```

**Example:**

```json
{
  "dry_run": false,
  "archive_instead": true,
  "limit": 50
}
```

---

### promote_memory

Promote high-value memories to long-term storage.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `memory_id` | string | No | - | Specific memory to promote |
| `auto_detect` | boolean | No | false | Auto-detect candidates |
| `dry_run` | boolean | No | false | Preview without promoting |
| `target` | string | No | "obsidian" | Target for promotion |
| `force` | boolean | No | false | Force even if criteria not met |

**Returns:**

```json
{
  "success": true,
  "dry_run": false,
  "candidates_found": 3,
  "promoted_count": 3,
  "promoted_ids": ["mem-1", "mem-2", "mem-3"],
  "candidates": [
    {
      "id": "mem-1",
      "content_preview": "Important project information...",
      "reason": "High score (0.82 >= 0.65)",
      "score": 0.8234,
      "use_count": 7,
      "age_days": 5.2
    }
  ],
  "message": "Promoted 3 memories to obsidian"
}
```

**Example - Specific Memory:**

```json
{
  "memory_id": "abc-123",
  "dry_run": false
}
```

**Example - Auto-detect:**

```json
{
  "auto_detect": true,
  "dry_run": true
}
```

---

### cluster_memories

Cluster similar memories for potential consolidation.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `strategy` | string | No | "similarity" | Clustering strategy |
| `threshold` | float | No | 0.83 | Similarity threshold |
| `max_cluster_size` | integer | No | 12 | Max memories per cluster |
| `find_duplicates` | boolean | No | false | Find duplicates instead |
| `duplicate_threshold` | float | No | 0.88 | Threshold for duplicates |

**Returns - Clustering:**

```json
{
  "success": true,
  "mode": "clustering",
  "clusters_found": 5,
  "strategy": "similarity",
  "threshold": 0.83,
  "clusters": [
    {
      "id": "cluster-abc-123",
      "size": 4,
      "cohesion": 0.87,
      "suggested_action": "llm-review",
      "memory_ids": ["mem-1", "mem-2", "mem-3", "mem-4"],
      "content_previews": [
        "Project meeting notes...",
        "Follow-up on project...",
        "Project status update..."
      ]
    }
  ],
  "message": "Found 5 clusters using similarity strategy"
}
```

**Returns - Duplicate Detection:**

```json
{
  "success": true,
  "mode": "duplicate_detection",
  "duplicates_found": 3,
  "duplicates": [
    {
      "id1": "mem-1",
      "id2": "mem-2",
      "content1_preview": "Meeting scheduled for Tuesday...",
      "content2_preview": "Tuesday meeting confirmed...",
      "similarity": 0.92
    }
  ],
  "message": "Found 3 potential duplicate pairs"
}
```

**Example - Clustering:**

```json
{
  "strategy": "similarity",
  "threshold": 0.85,
  "max_cluster_size": 10
}
```

**Example - Find Duplicates:**

```json
{
  "find_duplicates": true,
  "duplicate_threshold": 0.90
}
```

---

### consolidate_memories

Consolidate similar memories using algorithmic merging or linking.

This tool handles clusters in three ways:
1. **MERGE** (`mode="apply"`): Combine memories into one (high cohesion ≥0.75)
2. **LINK** (`mode="link"`): Create 'related' relations without merging (medium cohesion 0.40-0.75)
3. **PREVIEW** (`mode="preview"`): Show what would happen without making changes

Merging intelligently:
- Combines content (preserving unique information)
- Merges tags and entities (union)
- Calculates appropriate strength based on cohesion
- Preserves earliest `created_at` and latest `last_used` timestamps

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `cluster_id` | string | No | - | Cluster ID to consolidate (required unless `auto_detect=true`) |
| `mode` | string | No | "preview" | "preview", "apply", or "link" |
| `auto_detect` | boolean | No | false | Auto-detect high-cohesion clusters |
| `cohesion_threshold` | float | No | 0.75 | Minimum cohesion for auto-detection (0.0-1.0) |

**Returns - Preview Mode:**

```json
{
  "success": true,
  "mode": "preview",
  "auto_detect": true,
  "candidates_found": 3,
  "previews": [
    {
      "cluster_id": "cluster-abc",
      "cohesion": 0.87,
      "memory_count": 4,
      "merged_content_preview": "Combined content from 4 memories...",
      "merged_entities": ["entity1", "entity2"],
      "merged_tags": ["tag1", "tag2"],
      "calculated_strength": 1.4
    }
  ]
}
```

**Returns - Apply Mode:**

```json
{
  "success": true,
  "mode": "apply",
  "new_memory_id": "mem-new-123",
  "source_ids": ["mem-1", "mem-2", "mem-3"],
  "relation_ids": ["rel-1", "rel-2", "rel-3"],
  "archived_count": 3,
  "message": "Merged 3 memories into mem-new-123"
}
```

**Returns - Link Mode:**

```json
{
  "success": true,
  "mode": "link",
  "relations_created": 6,
  "cluster_id": "cluster-abc",
  "message": "Created 6 bidirectional relations linking 4 memories"
}
```

**Example - Auto-detect and Preview:**

```json
{
  "auto_detect": true,
  "mode": "preview",
  "cohesion_threshold": 0.80
}
```

**Example - Apply Specific Cluster:**

```json
{
  "cluster_id": "cluster-abc-123",
  "mode": "apply"
}
```

---

### read_graph

Read the entire knowledge graph of memories and relations.

Returns the complete graph structure including all memories (with decay scores), all relations between memories, and statistics.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `status` | string | No | "active" | Filter: "active", "promoted", "archived", "all" |
| `include_scores` | boolean | No | true | Include decay scores and age |
| `limit` | integer | No | - | Maximum memories to return (1-10,000) |
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 10 | Memories per page (max: 100) |

**Returns:**

```json
{
  "success": true,
  "memories": [
    {
      "id": "mem-123",
      "content": "Important project info",
      "entities": ["Project"],
      "tags": ["work"],
      "created_at": 1699012345,
      "last_used": 1699112345,
      "use_count": 5,
      "strength": 1.2,
      "status": "active",
      "score": 0.7523,
      "age_days": 5.2
    }
  ],
  "relations": [
    {
      "id": "rel-123",
      "from": "mem-123",
      "to": "mem-456",
      "type": "related",
      "strength": 0.85,
      "created_at": 1699012345
    }
  ],
  "stats": {
    "total_memories": 150,
    "total_relations": 45,
    "avg_score": 0.4521,
    "avg_use_count": 2.3,
    "status_filter": "active"
  },
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_count": 150,
    "total_pages": 15,
    "has_more": true
  }
}
```

---

### open_memories

Retrieve specific memories by their IDs.

Similar to the reference MCP memory server's `open_nodes` functionality. Returns detailed information including relations.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `memory_ids` | string or array | Yes | - | ID(s) to retrieve (max 100) |
| `include_relations` | boolean | No | true | Include relations from/to these memories |
| `include_scores` | boolean | No | true | Include decay scores and age |
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 10 | Memories per page (max: 100) |

**Returns:**

```json
{
  "success": true,
  "count": 2,
  "memories": [
    {
      "id": "mem-123",
      "content": "Project deadline is Dec 15",
      "entities": ["Project", "December"],
      "tags": ["deadline"],
      "source": "meeting notes",
      "context": "Q4 planning",
      "created_at": 1699012345,
      "last_used": 1699112345,
      "use_count": 5,
      "strength": 1.2,
      "status": "active",
      "promoted_at": null,
      "promoted_to": null,
      "score": 0.7523,
      "age_days": 5.2,
      "relations": {
        "outgoing": [
          {"to": "mem-456", "type": "related", "strength": 0.85}
        ],
        "incoming": [
          {"from": "mem-789", "type": "supports", "strength": 0.9}
        ]
      }
    }
  ],
  "not_found": ["mem-invalid-id"]
}
```

---

### create_relation

Create an explicit relation between two memories.

Links two memories with a typed relationship for building knowledge graphs.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `from_memory_id` | string | Yes | - | Source memory ID (valid UUID) |
| `to_memory_id` | string | Yes | - | Target memory ID (valid UUID) |
| `relation_type` | string | Yes | - | Type: "related", "causes", "supports", "contradicts", "has_decision", "consolidated_from" |
| `strength` | float | No | 1.0 | Relation strength (0.0-1.0) |
| `metadata` | object | No | {} | Additional metadata |

**Returns:**

```json
{
  "success": true,
  "relation_id": "rel-abc-123",
  "from": "mem-123",
  "to": "mem-456",
  "type": "related",
  "strength": 1.0,
  "message": "Relation created: mem-123 --[related]--> mem-456"
}
```

**Example:**

```json
{
  "from_memory_id": "mem-123",
  "to_memory_id": "mem-456",
  "relation_type": "supports",
  "strength": 0.9,
  "metadata": {"reason": "Same project context"}
}
```

---

## Memory Scoring

### Decay Score Formula

```
score = (use_count ^ beta) * exp(-lambda * (now - last_used)) * strength
```

**Default Parameters:**
- `lambda` (λ): 2.673e-6 (3-day half-life)
- `beta` (β): 0.6
- `strength`: 1.0 (range: 0.0-2.0)

### Interpretation

| Score | Meaning |
|-------|---------|
| > 0.65 | High value, candidate for promotion |
| 0.10 - 0.65 | Active, decaying normally |
| 0.05 - 0.10 | Low value, approaching forgetting |
| < 0.05 | Will be garbage collected |

---

## Error Responses

All tools return errors in this format:

```json
{
  "success": false,
  "message": "Error description"
}
```

Common errors:
- Memory not found
- Invalid parameters
- Database errors
- Integration failures (e.g., vault not accessible)

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CORTEXGRAPH_STORAGE_PATH` | `~/.config/cortexgraph/jsonl` | JSONL storage directory |
| `CORTEXGRAPH_DECAY_MODEL` | `power_law` | Decay model (power_law\|exponential\|two_component) |
| `CORTEXGRAPH_PL_HALFLIFE_DAYS` | `3.0` | Power-law half-life in days |
| `CORTEXGRAPH_DECAY_LAMBDA` | `2.673e-6` | Exponential decay constant |
| `CORTEXGRAPH_DECAY_BETA` | `0.6` | Use count exponent |
| `CORTEXGRAPH_FORGET_THRESHOLD` | `0.05` | Forgetting threshold |
| `CORTEXGRAPH_PROMOTE_THRESHOLD` | `0.65` | Promotion threshold |
| `CORTEXGRAPH_PROMOTE_USE_COUNT` | `5` | Use count for promotion |
| `CORTEXGRAPH_ENABLE_EMBEDDINGS` | `false` | Enable semantic search |
| `LTM_VAULT_PATH` | - | Obsidian vault path |

### Tuning Recommendations

**Fast Decay** (1-day half-life):
```bash
CORTEXGRAPH_PL_HALFLIFE_DAYS=1.0
# Or exponential: CORTEXGRAPH_DECAY_LAMBDA=8.02e-6
```

**Slow Decay** (7-day half-life):
```bash
CORTEXGRAPH_PL_HALFLIFE_DAYS=7.0
# Or exponential: CORTEXGRAPH_DECAY_LAMBDA=1.145e-6
```

**Aggressive Promotion**:
```bash
CORTEXGRAPH_PROMOTE_THRESHOLD=0.5
CORTEXGRAPH_PROMOTE_USE_COUNT=3
```

**Conservative Forgetting**:
```bash
CORTEXGRAPH_FORGET_THRESHOLD=0.01
```

---

## Maintenance

Use the CLI to manage JSONL storage:

- `cortexgraph-maintenance stats` — prints `get_storage_stats()` including active counts and compaction hints
- `cortexgraph-maintenance compact` — compacts JSONL files to remove tombstones and duplicates

Optionally specify a path: `cortexgraph-maintenance --storage-path ~/.config/cortexgraph/jsonl stats`

---

## Multi-Agent Consolidation System

**NEW in v0.7.5** - Automated memory maintenance through five specialized agents.

For architecture details, see [docs/agents.md](agents.md).

### Pipeline Overview

```
decay → cluster → merge → promote → relations
  │        │        │        │          │
  ▼        ▼        ▼        ▼          ▼
Find at- Find    Combine  Promote  Discover
risk    similar  similar  to LTM   cross-domain
memories groups   groups           links
```

### Scheduler

The Scheduler orchestrates all agents in the pipeline.

**Python Usage:**

```python
from cortexgraph.agents import Scheduler

# Run full pipeline (dry run)
scheduler = Scheduler(dry_run=True)
results = scheduler.run_pipeline()
# Returns: {"decay": [...], "cluster": [...], "merge": [...], "promote": [...], "relations": [...]}

# Run single agent
decay_results = scheduler.run_agent("decay")

# Run on schedule (respects interval)
result = scheduler.run_scheduled(force=False)
```

**CLI Usage:**

```bash
# Run full pipeline (dry run)
cortexgraph-consolidate --dry-run

# Run full pipeline (live)
cortexgraph-consolidate

# Run single agent
cortexgraph-consolidate --agent decay --dry-run

# Run on schedule
cortexgraph-consolidate --scheduled --interval-hours 1
```

---

### DecayAnalyzer

Identifies memories at risk of being forgotten.

**Purpose:** Find memories in the "danger zone" (0.15-0.35 score) before they decay below the forget threshold.

**Urgency Levels:**

| Score | Urgency | Description |
|-------|---------|-------------|
| < 0.15 | HIGH | Immediate attention needed |
| 0.15 - 0.25 | MEDIUM | Standard priority |
| 0.25 - 0.35 | LOW | Can wait |

**Actions:**

- `reinforce` - Memory is valuable, should be reviewed
- `gc_candidate` - Memory is low-value, consider deletion
- `needs_review` - Uncertain, requires human judgment

**Python Usage:**

```python
from cortexgraph.agents import DecayAnalyzer

analyzer = DecayAnalyzer(dry_run=True)
results = analyzer.run()  # Returns list[DecayResult]

for result in results:
    print(f"{result.memory_id}: {result.urgency} - {result.action}")
```

**Result Type - DecayResult:**

| Field | Type | Description |
|-------|------|-------------|
| `memory_id` | string | ID of the at-risk memory |
| `score` | float | Current decay score |
| `urgency` | string | "high", "medium", "low" |
| `action` | string | Recommended action |

---

### ClusterDetector

Groups similar memories for potential consolidation.

**Purpose:** Find memories that share content/entities and could be merged.

**Cohesion Levels:**

| Cohesion | Action |
|----------|--------|
| ≥ 0.85 | Auto-merge candidate |
| 0.65 - 0.85 | LLM review recommended |
| < 0.65 | Keep separate |

**Python Usage:**

```python
from cortexgraph.agents import ClusterDetector

detector = ClusterDetector(
    dry_run=True,
    similarity_threshold=0.83,
    min_cluster_size=2
)
results = detector.run()  # Returns list[ClusterResult]
```

**Result Type - ClusterResult:**

| Field | Type | Description |
|-------|------|-------------|
| `cluster_id` | string | Unique cluster identifier |
| `memory_ids` | list[str] | IDs of memories in cluster |
| `cohesion` | float | Similarity score (0.0-1.0) |
| `action` | string | Recommended action |

---

### SemanticMerge

Intelligently combines clustered memories.

**Purpose:** Merge similar memories while preserving unique information.

**Merge Process:**

1. Fetch source memories from cluster
2. Merge content (preserving unique information)
3. Union tags and entities
4. Calculate combined strength (max + cohesion bonus)
5. Create new memory
6. Create `consolidated_from` relations
7. Archive original memories

**Python Usage:**

```python
from cortexgraph.agents import SemanticMerge

merger = SemanticMerge(dry_run=True)
results = merger.run()  # Returns list[MergeResult]
```

**Result Type - MergeResult:**

| Field | Type | Description |
|-------|------|-------------|
| `new_memory_id` | string | ID of merged memory |
| `source_ids` | list[str] | IDs of original memories |
| `relation_ids` | list[str] | IDs of consolidation relations |
| `success` | bool | Whether merge succeeded |

---

### LTMPromoter

Moves high-value memories to long-term Obsidian storage.

**Purpose:** Promote memories that exceed score and usage thresholds to permanent storage.

**Promotion Criteria:**

- Score ≥ 0.65 (configurable via `CORTEXGRAPH_PROMOTE_THRESHOLD`)
- OR use_count ≥ 5 within 14 days
- OR force=True

**Python Usage:**

```python
from cortexgraph.agents import LTMPromoter

promoter = LTMPromoter(dry_run=True)
results = promoter.run()  # Returns list[PromotionResult]
```

**Result Type - PromotionResult:**

| Field | Type | Description |
|-------|------|-------------|
| `memory_id` | string | ID of promoted memory |
| `vault_path` | string | Path in Obsidian vault |
| `criteria_met` | list[str] | Which criteria triggered promotion |

---

### RelationshipDiscovery

Finds cross-domain connections between memories.

**Purpose:** Discover and create relations between memories sharing entities.

**Relation Metrics:**

- **Strength**: Weighted Jaccard similarity (70% entities, 30% tags)
- **Confidence**: Based on number of shared entities/tags

**Python Usage:**

```python
from cortexgraph.agents import RelationshipDiscovery

discovery = RelationshipDiscovery(
    dry_run=True,
    min_shared_entities=2,
    min_confidence=0.5
)
results = discovery.run()  # Returns list[RelationResult]
```

**Result Type - RelationResult:**

| Field | Type | Description |
|-------|------|-------------|
| `from_id` | string | Source memory ID |
| `to_id` | string | Target memory ID |
| `relation_type` | string | Type of relation (always "related") |
| `strength` | float | Relation strength (0.0-1.0) |
| `confidence` | float | Detection confidence (0.0-1.0) |
| `shared_entities` | list[str] | Entities shared between memories |
| `reasoning` | string | Human-readable explanation |

---

### Agent Configuration

**Environment Variables:**

```bash
# Scheduler
CORTEXGRAPH_CONSOLIDATION_INTERVAL=3600  # Seconds between runs

# Thresholds (existing)
CORTEXGRAPH_FORGET_THRESHOLD=0.05        # Decay below this → delete
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65       # Score above this → promote
CORTEXGRAPH_PROMOTE_USE_COUNT=5          # Uses within window → promote

# Clustering
CORTEXGRAPH_CLUSTER_THRESHOLD=0.83       # Default similarity threshold
CORTEXGRAPH_MIN_CLUSTER_SIZE=2           # Minimum memories per cluster
```

**Agent-Specific Configuration:**

Each agent accepts configuration in their constructors:

```python
ClusterDetector(
    dry_run=True,
    similarity_threshold=0.83,  # Minimum similarity to cluster
    min_cluster_size=2,         # Minimum memories per cluster
    rate_limit=60,              # Max operations per minute
)

RelationshipDiscovery(
    dry_run=True,
    min_shared_entities=2,      # Minimum shared entities to create relation
    min_confidence=0.5,         # Minimum confidence threshold
)
```

---

### Beads Integration

Agents coordinate through [beads](https://github.com/steveyegge/beads) issue tracking.

**Label Convention:**

| Agent | Label |
|-------|-------|
| Decay | `consolidation:decay` |
| Cluster | `consolidation:cluster` |
| Merge | `consolidation:merge` |
| Promote | `consolidation:promote` |
| Relations | `consolidation:relations` |

**Issue Flow:**

1. DecayAnalyzer scans → Creates issues for at-risk memories
2. ClusterDetector scans → Creates issues with clusters for merging
3. SemanticMerge reads issues → Processes merge requests
4. Issues closed on completion

**Programmatic Integration:**

```python
from cortexgraph.agents.beads_integration import (
    create_consolidation_issue,
    query_consolidation_issues,
    claim_issue,
    close_issue,
)

# Create issue
issue_id = create_consolidation_issue(
    agent="decay",
    memory_ids=["mem-123", "mem-456"],
    action="reinforce",
    urgency="high",
)

# Query issues
open_issues = query_consolidation_issues(
    agent="cluster",
    status="open",
)

# Claim and process
if claim_issue(issue_id):
    # ... do work ...
    close_issue(issue_id, "Processed successfully")
```
