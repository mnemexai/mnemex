# STM Server Architecture

## Overview

STM Server implements a biologically-inspired memory system with temporal decay and reinforcement, designed to give AI assistants human-like memory dynamics.

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
│        Storage Layer (SQLite)       │
│  database, migrations, models       │
└─────────────────────────────────────┘
```

### Database Schema

```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    meta TEXT NOT NULL,             -- JSON metadata
    created_at INTEGER NOT NULL,
    last_used INTEGER NOT NULL,
    use_count INTEGER NOT NULL DEFAULT 0,
    strength REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'active',
    promoted_at INTEGER,
    promoted_to TEXT,
    embed BLOB                      -- Optional embeddings
);
```

Indexes on: `last_used`, `use_count`, `status`, `created_at`

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
Store in SQLite
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

1. **Embedding Generation**: Use sentence-transformers to create vectors
2. **Pairwise Similarity**: Calculate cosine similarity between memories
3. **Linking**: Connect memories with similarity > threshold (default: 0.83)
4. **Cluster Formation**: Single-linkage clustering
5. **Cohesion Calculation**: Average intra-cluster similarity

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

- SQLite is fast for single-machine use
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
- PostgreSQL instead of SQLite
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
