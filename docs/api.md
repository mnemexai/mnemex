# Mnemex API Reference

Complete reference for all MCP tools provided by Mnemex.

## Core Memory Tools

### save_memory

Save a new memory to short-term storage.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `content` | string | Yes | The content to remember |
| `tags` | array[string] | No | Tags for categorization |
| `source` | string | No | Source of the memory |
| `context` | string | No | Context when memory was created |
| `meta` | object | No | Additional custom metadata |

**Returns:**

```json
{
  "success": true,
  "memory_id": "abc-123-def-456",
  "message": "Memory saved with ID: abc-123-def-456",
  "has_embedding": false
}
```

**Example:**

```json
{
  "content": "The project deadline is December 15th",
  "tags": ["project", "deadline"],
  "source": "team meeting",
  "context": "Q4 planning discussion"
}
```

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
MNEMEX_AUTO_REINFORCE=true

# If disabled, returns:
{
  "reinforced": false,
  "reason": "auto_reinforce is disabled in config",
  "count": 0
}
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

Consolidate similar memories using LLM-driven merging (NOT YET IMPLEMENTED).

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `cluster_id` | string | Yes | - | Cluster ID to consolidate |
| `mode` | string | No | "dry_run" | "dry_run" or "apply" |

**Returns:**

```json
{
  "success": false,
  "message": "Consolidation tool is not yet implemented...",
  "status": "not_implemented",
  "cluster_id": "cluster-abc",
  "mode": "dry_run"
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
| `MNEMEX_STORAGE_PATH` | `~/.config/mnemex/jsonl` | JSONL storage directory |
| `MNEMEX_DECAY_MODEL` | `power_law` | Decay model (power_law\|exponential\|two_component) |
| `MNEMEX_PL_HALFLIFE_DAYS` | `3.0` | Power-law half-life in days |
| `MNEMEX_DECAY_LAMBDA` | `2.673e-6` | Exponential decay constant |
| `MNEMEX_DECAY_BETA` | `0.6` | Use count exponent |
| `MNEMEX_FORGET_THRESHOLD` | `0.05` | Forgetting threshold |
| `MNEMEX_PROMOTE_THRESHOLD` | `0.65` | Promotion threshold |
| `MNEMEX_PROMOTE_USE_COUNT` | `5` | Use count for promotion |
| `MNEMEX_ENABLE_EMBEDDINGS` | `false` | Enable semantic search |
| `LTM_VAULT_PATH` | - | Obsidian vault path |

### Tuning Recommendations

**Fast Decay** (1-day half-life):
```bash
MNEMEX_PL_HALFLIFE_DAYS=1.0
# Or exponential: MNEMEX_DECAY_LAMBDA=8.02e-6
```

**Slow Decay** (7-day half-life):
```bash
MNEMEX_PL_HALFLIFE_DAYS=7.0
# Or exponential: MNEMEX_DECAY_LAMBDA=1.145e-6
```

**Aggressive Promotion**:
```bash
MNEMEX_PROMOTE_THRESHOLD=0.5
MNEMEX_PROMOTE_USE_COUNT=3
```

**Conservative Forgetting**:
```bash
MNEMEX_FORGET_THRESHOLD=0.01
```

---

## Maintenance

Use the CLI to manage JSONL storage:

- `mnemex-maintenance stats` — prints `get_storage_stats()` including active counts and compaction hints
- `mnemex-maintenance compact` — compacts JSONL files to remove tombstones and duplicates

Optionally specify a path: `mnemex-maintenance --storage-path ~/.config/mnemex/jsonl stats`
