# CortexGraph Architecture

## Overview

CortexGraph implements a biologically-inspired memory system with temporal decay and reinforcement, designed to give AI assistants human-like memory dynamics.

## Core Concepts

### Temporal Decay

Memories naturally fade over time using exponential decay:

```
score(t) = (use_count^β) * exp(-λ * Δt) * strength
```

Where:
- `Δt = now - last_used` (time since last access)
- `λ` (lambda): Decay constant controlling decay rate
- `β` (beta): Exponent weighting the importance of use_count
- `strength`: Base multiplier (1.0-2.0)

### Half-Life

The decay constant λ is typically defined by a half-life period:

```
λ = ln(2) / halflife_seconds
```

Default: 3-day half-life → `λ ≈ 2.673e-6`

This means a memory's score will drop to 50% of its current value after 3 days without access.

### Reinforcement

Each time a memory is accessed:
1. `last_used` is updated to current time (resets decay)
2. `use_count` is incremented (increases base score)
3. Optionally, `strength` can be boosted (max 2.0)

This implements a "use it or lose it" principle: frequently accessed information persists.

### Promotion Criteria

A memory is promoted to long-term storage if:

**Score-based**: `score >= promote_threshold` (default: 0.65)

OR

**Usage-based**: `use_count >= N` (default: 5) within time window (default: 14 days)

Once promoted, the memory is:
1. Written to Obsidian vault as a Markdown note
2. Marked as `PROMOTED` in the database
3. Retained with a redirect pointer to the vault location

### Garbage Collection

Memories are forgotten (deleted) if:

`score < forget_threshold` (default: 0.05)

This prevents indefinite accumulation of unused memories.

## Natural Spaced Repetition

CortexGraph implements a natural spaced repetition system inspired by how humans remember concepts better when they appear across different contexts - the "Maslow effect" (remembering Maslow's hierarchy better when it appears in history, economics, and sociology classes).

**Key principle:** No flashcards, no explicit review sessions. Reinforcement happens naturally through conversation.

### Review Priority Calculation

Memories are prioritized for review based on their position in the "danger zone" - the decay score range where memories are most at risk of being forgotten:

```python
def calculate_review_priority(memory: Memory) -> float:
    """Calculate review priority using inverted parabola curve.
    
    Priority peaks at the midpoint of the danger zone (0.25 by default).
    Returns 0.0-1.0 priority score.
    """
    score = calculate_score(memory)
    
    if score < danger_zone_min or score > danger_zone_max:
        return 0.0  # Outside danger zone
    
    # Inverted parabola: peaks at midpoint
    midpoint = (danger_zone_min + danger_zone_max) / 2
    range_width = danger_zone_max - danger_zone_min
    
    # Normalize to 0-1 range
    normalized = (score - danger_zone_min) / range_width
    
    # Inverted parabola: 1 - 4*(x - 0.5)^2
    priority = 1.0 - 4.0 * (normalized - 0.5) ** 2
    
    return max(0.0, min(1.0, priority))
```

**Danger zone defaults:**
- Lower bound: 0.15 (memories decaying rapidly)
- Upper bound: 0.35 (memories still reasonably strong)
- Peak priority: 0.25 (midpoint - maximum urgency)

### Cross-Domain Usage Detection

The system detects when memories are used in different contexts by comparing the memory's original tags with the current conversation context tags:

```python
def detect_cross_domain_usage(memory: Memory, context_tags: list[str]) -> bool:
    """Detect if memory is being used in a different domain.
    
    Uses Jaccard similarity: intersection / union
    If similarity < 30%, tags are sufficiently different to indicate cross-domain usage.
    """
    if not memory.tags or not context_tags:
        return False
    
    memory_tags = set(memory.tags)
    context_tags_set = set(context_tags)
    
    intersection = memory_tags & context_tags_set
    union = memory_tags | context_tags_set
    
    jaccard_similarity = len(intersection) / len(union)
    
    return jaccard_similarity < 0.3  # <30% overlap = cross-domain
```

**Example:**
- Memory tags: `[security, jwt, preferences]`
- Context tags: `[api, auth, backend]`
- Jaccard similarity: 0.0 (no overlap) → **Cross-domain detected**
- Result: Memory gets strength boost (1.0 → 1.1-1.2)

### Automatic Reinforcement

When a memory is used in conversation, the `observe_memory_usage` tool:

1. **Updates usage statistics**: Increments `use_count`, updates `last_used`
2. **Increments review count**: Tracks how many times memory has been reinforced
3. **Detects cross-domain usage**: Compares memory tags with context tags
4. **Applies strength boost**: If cross-domain, increases strength (capped at 2.0)
5. **Recalculates priority**: Updates review priority for next search

```python
def reinforce_memory(memory: Memory, cross_domain: bool = False) -> Memory:
    """Reinforce a memory through usage.
    
    Args:
        memory: Memory to reinforce
        cross_domain: Whether this is cross-domain usage (gets extra boost)
    
    Returns:
        Updated memory with reinforced values
    """
    now = int(time.time())
    
    # Standard reinforcement
    memory.last_used = now
    memory.use_count += 1
    memory.review_count += 1
    memory.last_review_at = now
    
    # Cross-domain bonus
    if cross_domain:
        memory.cross_domain_count += 1
        # Boost strength (capped at 2.0)
        boost = 0.1
        memory.strength = min(2.0, memory.strength + boost)
    
    # Recalculate priority
    memory.review_priority = calculate_review_priority(memory)
    
    return memory
```

### Blended Search Results

The `search_memory` tool automatically blends review candidates into search results:

1. **Query primary index**: Get relevant memories matching search criteria
2. **Get review queue**: Retrieve memories with highest review priority
3. **Filter for relevance**: Remove review candidates not relevant to query
4. **Blend results**: Interleave primary results with review candidates
   - Default: 70% primary results, 30% review candidates
   - Configurable via `CORTEXGRAPH_REVIEW_BLEND_RATIO`

**Example flow:**
```
User searches for "typescript preferences"
→ Primary results: 7 matches (sorted by relevance × decay score)
→ Review queue: 10 memories in danger zone
→ Filter review queue: Keep only typescript-related (3 matches)
→ Blend: [primary[0], primary[1], review[0], primary[2], primary[3], review[1], ...]
→ Return top 5 blended results
```

This ensures memories needing reinforcement naturally surface during relevant searches, without disrupting the user experience.

### Configuration

```bash
# Natural Spaced Repetition
CORTEXGRAPH_REVIEW_BLEND_RATIO=0.3           # 30% review candidates in search
CORTEXGRAPH_REVIEW_DANGER_ZONE_MIN=0.15      # Lower bound of danger zone
CORTEXGRAPH_REVIEW_DANGER_ZONE_MAX=0.35      # Upper bound of danger zone
CORTEXGRAPH_AUTO_REINFORCE=true              # Auto-reinforce on observe
```

### Memory Model Extensions

Natural spaced repetition adds four fields to the `Memory` model:

```python
class Memory(BaseModel):
    # ... existing fields ...
    
    # Review tracking (v0.5.1+)
    review_priority: float = Field(default=0.0, ge=0, le=1)  # 0.0-1.0 urgency
    last_review_at: int | None = Field(default=None)         # Last reinforcement timestamp
    review_count: int = Field(default=0)                     # Total reinforcements
    cross_domain_count: int = Field(default=0)               # Cross-domain usages
```

These fields are backward-compatible - existing memories default to 0/None.

### Usage Pattern (Conversational)

The natural spaced repetition system works entirely through conversation:

1. **User asks question** with implicit context (tags, topics)
2. **System searches** (automatically includes review candidates in results)
3. **System uses memories** to form intelligent response
4. **System observes** memory usage with `observe_memory_usage(memory_ids, context_tags)`
5. **Cross-domain detection** triggers if tags differ significantly
6. **Automatic reinforcement** updates memory statistics and priority
7. **Next search** naturally surfaces memories in danger zone

**No explicit review commands. No interruptions. Just natural strengthening through use.**

## Core Module Organization (v1.2.0+)

The `cortexgraph.core` package contains foundational algorithms organized into focused modules:

| Module | Purpose |
|--------|---------|
| `decay.py` | Temporal decay calculations (power-law, exponential, two-component) |
| `similarity.py` | Similarity metrics (`cosine_similarity`, `jaccard_similarity`, `tfidf_similarity`, `text_similarity`) |
| `clustering.py` | Memory clustering logic using similarity functions |
| `consolidation.py` | Memory merging algorithms with batch operations |
| `search_common.py` | Shared search validation (`SearchParams`, `validate_search_params`) |
| `text_utils.py` | Text processing utilities (`truncate_content`) |
| `pagination.py` | Pagination helpers |
| `scoring.py` | Score-based decision functions |

### Agent Utilities

The `cortexgraph.agents` package includes:

| Module | Purpose |
|--------|---------|
| `storage_utils.py` | Shared storage access (`get_storage()`) |
| `base.py` | Base agent class for consolidation pipeline |
| Individual agents | `decay_analyzer.py`, `cluster_detector.py`, `semantic_merge.py`, etc. |

All core functions are re-exported from `cortexgraph.core` for convenient imports:

```python
from cortexgraph.core import (
    cosine_similarity,
    jaccard_similarity,
    text_similarity,
    truncate_content,
    SearchParams,
    validate_search_params,
)

from cortexgraph.agents import get_storage
```

## System Architecture

### Layers

```
┌─────────────────────────────────────┐
│       MCP Tools (API Layer)         │
│  save, search, touch, gc, promote   │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Core Logic Layer            │
│   decay, scoring, clustering        │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│      Storage Layer (JSONL)          │
│  human-readable files + models      │
└─────────────────────────────────────┘
```

### Storage Format (JSONL)

Each memory is stored as a JSON object, one per line, in `memories.jsonl`. Relations in `relations.jsonl`.

Example line:
```
{"id":"...","content":"...","meta":{"tags":["..."]},"created_at":1736275200,"last_used":1736275200,"use_count":0,"strength":1.0,"status":"active"}
```

In-memory indexes are built at startup for fast queries; periodic compaction rewrites files to remove tombstones and duplicates.

### Memory States

```
ACTIVE → [high score/usage] → PROMOTED
   ↓
[low score]
   ↓
ARCHIVED or DELETED
```

- **ACTIVE**: Normal short-term memory undergoing decay
- **PROMOTED**: Moved to long-term storage (Obsidian)
- **ARCHIVED**: Low-scoring but preserved (optional)

## Data Flow

### Saving a Memory

```
User/AI → save_memory(content, tags)
    ↓
Generate embedding (optional)
    ↓
Create Memory object
    ↓
Append to JSONL storage
    ↓
Return memory_id
```

### Searching Memories

```
User/AI → search_memory(query, filters)
    ↓
Database query (tags, window, status)
    ↓
Calculate decay scores for each
    ↓
[Optional] Calculate semantic similarity
    ↓
Rank by combined score
    ↓
Return top_k results
```

### Touching a Memory

```
User/AI → touch_memory(id)
    ↓
Get existing memory
    ↓
Update: last_used=now, use_count+=1, strength+=boost
    ↓
Calculate new score
    ↓
Save updated memory
    ↓
Return old/new scores
```

### Promotion Flow

```
[Automatic or Manual Trigger]
    ↓
Identify candidates (score/usage criteria)
    ↓
[Optional: Dry-run preview]
    ↓
For each candidate:
    ├─ Generate Markdown note
    ├─ Write to Obsidian vault
    ├─ Update status=PROMOTED
    └─ Store vault path
```

### Garbage Collection

```
gc(dry_run, archive_instead)
    ↓
Get all ACTIVE memories
    ↓
Calculate scores
    ↓
Filter: score < forget_threshold
    ↓
[Optional: Dry-run preview]
    ↓
Delete or Archive
    ↓
Return statistics
```

## Clustering for Consolidation

### Similarity-Based Clustering

Uses functions from `cortexgraph.core.similarity`:

1. **Embedding Generation**: Use sentence-transformers to create vectors
2. **Pairwise Similarity**: Calculate `cosine_similarity()` between memory embeddings
3. **Fallback**: Use `text_similarity()` (Jaccard-based) when embeddings unavailable
4. **Linking**: Connect memories with similarity > threshold (default: 0.83)
5. **Cluster Formation**: Single-linkage clustering
6. **Cohesion Calculation**: Average intra-cluster similarity via `calculate_centroid()`

### Cluster Actions

- **Auto-merge** (cohesion ≥ 0.9): Clear duplicates
- **LLM-review** (0.75 ≤ cohesion < 0.9): Require human/LLM review
- **Keep-separate** (cohesion < 0.75): Different enough to keep apart

## Integration Points

### Basic Memory (Obsidian)

When promoting to long-term:

1. Create note in `vault/STM/` directory
2. Add YAML frontmatter with metadata
3. Format content with sections
4. Include backlinks to related notes (future feature)
5. Tag appropriately for graph view

### Sentence Transformers (Optional)

For semantic search and clustering:

1. Load model (default: `all-MiniLM-L6-v2`)
2. Encode content → 384-dim vector
3. Store as BLOB in database
4. Use for similarity search and clustering

## Performance Considerations

### Database

- JSONL is simple and git-friendly for single-machine use
- Indexes on frequently queried fields
- BLOB storage for embeddings (efficient)
- Typical operations: < 10ms

### Embeddings

- Optional feature (disabled by default)
- Model loads on first use (~50MB memory)
- Encoding: ~10-50ms per text
- Consider batch encoding for bulk operations

### Scaling

Current design targets:
- 1,000-10,000 active memories
- Single user, single machine
- Local-first architecture

For larger scales, consider:
- External databases (e.g., PostgreSQL) are out of scope for this project
- Vector database (e.g., Qdrant, Weaviate)
- Distributed MCP architecture

## Configuration Tuning

### Decay Rate (λ)

- **Fast decay** (1-day half-life): `λ = 8.02e-6`
- **Default** (3-day half-life): `λ = 2.673e-6`
- **Slow decay** (7-day half-life): `λ = 1.145e-6`

### Thresholds

Adjust based on usage patterns:

- `forget_threshold`: Lower → keep more memories
- `promote_threshold`: Lower → promote more aggressively
- `promote_use_count`: Higher → require more reinforcement

### Use Count Weight (β)

- **Low** (β = 0.3): Linear-ish, less emphasis on repetition
- **Default** (β = 0.6): Balanced
- **High** (β = 1.0): Linear, heavy emphasis on use count

## Future Enhancements

1. **LLM Consolidation**: Automatic memory merging with LLM review
2. **Relationship Tracking**: Link related memories explicitly
3. **Context Windows**: Group memories by temporal/semantic context
4. **Adaptive Decay**: Learn optimal decay rates per memory type
5. **Multi-user Support**: Shared memory spaces with access control
6. **Incremental Promotion**: Partial content promotion before full commit
