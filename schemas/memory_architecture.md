# CortexGraph Memory Architecture: PostgreSQL + pgvector

## Overview

This document describes the migration from JSONL/SQLite storage to **PostgreSQL + pgvector** for CortexGraph's temporal memory system. The goal is to:

1. Preserve all existing decay logic and scoring behavior
2. Add native vector similarity search via pgvector
3. Provide true graph traversal capabilities via relationships
4. Maintain local-first operation (no cloud dependencies)
5. Enable efficient scaling to millions of memories

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         CortexGraph Application Logic            │
│    (decay.py, scoring.py, consolidation.py)    │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│    PostgreSQL Storage Abstraction Layer         │
│    (replaces JSONLStorage / SQLiteStorage)      │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│   PostgreSQL Database (local-first)             │
│   ├─ memories table (with vector embeddings)    │
│   ├─ relationships table (graph edges)          │
│   ├─ Decay scoring functions                    │
│   └─ Full-text search + vector similarity      │
└─────────────────────────────────────────────────┘
```

## Core Design Decisions

### 1. Why PostgreSQL + pgvector?

**Advantages:**
- **True local-first**: Single file database, no external services
- **ACID compliance**: Transactional integrity for multi-agent systems
- **Rich query capabilities**: SQL, full-text search, vector similarity, graph traversal
- **Mature ecosystem**: Battle-tested, performant, extensible
- **Zero cost**: Open source, no vendor lock-in
- **Apple Silicon native**: Compiles natively via Homebrew

**Trade-offs:**
- Slightly more operational overhead than SQLite (but still minimal)
- Not embedded in Python (requires separate server process)
- Full-text search is less sophisticated than Elasticsearch (but sufficient)

### 2. Memory Model Mapping

The `memories` table directly maps cortexgraph's `Memory` model:

| CortexGraph Field | PostgreSQL Column | Type | Notes |
|---|---|---|---|
| `id` | `id` | TEXT (UUID) | Primary key |
| `content` | `content` | TEXT | Memory text (max 50KB) |
| `meta` | `meta` | JSONB | Flexible tags, source, context |
| `entities` | `entities` | TEXT[] | Extracted named entities |
| `created_at` | `created_at` | BIGINT | Unix timestamp (seconds) |
| `last_used` | `last_used` | BIGINT | Last access timestamp |
| `use_count` | `use_count` | INTEGER | Access count |
| `strength` | `strength` | FLOAT | Importance multiplier (0-2) |
| `status` | `status` | TEXT | active / promoted / archived |
| `promoted_at` | `promoted_at` | BIGINT | Promotion timestamp |
| `promoted_to` | `promoted_to` | TEXT | Vault path (LTM reference) |
| `embed` | `embed` | vector(384) | 384-dim embeddings (pgvector) |
| `review_priority` | `review_priority` | FLOAT | Spaced repetition urgency |
| `last_review_at` | `last_review_at` | BIGINT | Last reinforcement |
| `review_count` | `review_count` | INTEGER | Reinforcement count |
| `cross_domain_count` | `cross_domain_count` | INTEGER | Cross-context usage |

### 3. Relationships as Graph Edges

The `relationships` table models the knowledge graph:

```sql
from_memory_id → [relation_type] → to_memory_id
```

**Allowed Relation Types** (from cortexgraph validation):
- `related` — General semantic association
- `causes` — Causal relationship (A → B)
- `supports` — Supporting evidence (Evidence → Claim)
- `contradicts` — Conflicting information (A ↔ B)
- `has_decision` — Links project to decision
- `consolidated_from` — Consolidation result (Merged → Source₁, Source₂)

Each relationship stores:
- `strength` (0-1): How confident is the relationship?
- `metadata` (JSONB): Custom fields (confidence, context, etc.)
- `created_at`: When relationship was established

### 4. Temporal Decay in SQL

The decay formula is **computed in SQL** at query time, not stored:

```sql
score = (use_count + 1)^β × e^(-λ·Δt) × strength
```

**PostgreSQL Implementation:**
```sql
(use_count + 1)^0.6 * EXP(-2.673e-6 * (now - last_used)) * strength
```

Where:
- `β = 0.6` (sub-linear use count exponent)
- `λ = 2.673e-6` (exponential decay constant for 3-day half-life)
- `Δt = current_time - last_used` (seconds)

**Why Compute at Query Time?**
- Scores change continuously as time passes
- No need to update millions of rows every second
- Can use different decay models per query if needed
- Same behavior as existing cortexgraph implementation

**Decision Thresholds:**
- Score ≥ 0.65 → **PROMOTE** to LTM
- Score < 0.05 → **FORGET** (delete)
- 0.15 < Score < 0.35 → **REVIEW** (danger zone, needs reinforcement)
- Score ≥ 5 uses in 14 days → **PROMOTE** (secondary criterion)

### 5. Vector Search via pgvector

**Embedding Generation:**
- Model: `all-MiniLM-L6-v2` (384-dimensional)
- Similarity: Cosine distance
- Index: HNSW (Hierarchical Navigable Small World) for fast ANN

**Search Patterns:**
```sql
-- Semantic similarity search
SELECT * FROM memories
ORDER BY embed <=> query_vector
LIMIT 10;

-- Hybrid: vector + metadata filter
SELECT * FROM memories
WHERE status = 'active'
  AND meta->>'source' = 'conversation'
ORDER BY embed <=> query_vector
LIMIT 10;

-- Full-text search as fallback
SELECT * FROM memories
WHERE to_tsvector('english', content) @@ plainto_tsquery('english', 'python')
ORDER BY ts_rank(...) DESC
LIMIT 10;
```

### 6. Graph Traversal

**Single-hop relationships:**
```sql
SELECT * FROM relationships
WHERE from_memory_id = 'mem-123'
  AND relation_type = 'causes';
```

**Multi-hop traversal (CTE):**
```sql
WITH RECURSIVE related AS (
  -- Find direct relationships
  SELECT to_memory_id, relation_type, 1 AS depth
  FROM relationships WHERE from_memory_id = 'mem-123'

  UNION ALL

  -- Follow relationships recursively
  SELECT r.to_memory_id, r.relation_type, rel.depth + 1
  FROM related rel
  JOIN relationships r ON r.from_memory_id = rel.memory_id
  WHERE rel.depth < 3  -- Max depth 3
)
SELECT * FROM related;
```

This enables:
- **Context expansion**: Find related memories via traversal
- **Reasoning chains**: Follow causal relationships (A causes B causes C)
- **Conflict detection**: Find contradictory information
- **Consolidation detection**: Trace back to original memories

## Migration Path from JSONL/SQLite

### Phase 1: Setup (One-time)
1. Install PostgreSQL + pgvector
2. Create schema via `pgvector_schema.sql`
3. Create storage abstraction layer (`PostgresMemoryStorage`)

### Phase 2: Data Import (Batch)
1. Read from `~/.config/cortexgraph/jsonl/memories.jsonl`
2. Parse JSON, validate, generate embeddings
3. Insert into PostgreSQL in batches
4. Verify integrity

### Phase 3: Relationship Import
1. Read from `~/.config/cortexgraph/jsonl/relationships.jsonl`
2. Insert into relationships table with foreign key validation
3. Create indexes

### Phase 4: Deployment
1. Update config to use PostgreSQL backend
2. Fall back to JSONL on errors (for safety)
3. Monitor performance, tune indexes
4. Eventually deprecate JSONL backend

## Query Patterns: JSONL vs PostgreSQL

### Example 1: Decay Scoring

**JSONL (current):**
```python
for memory in all_memories:
    score = (memory.use_count + 1)**0.6 * exp(-lambda * (now - memory.last_used)) * memory.strength
    if score >= 0.65:
        promote(memory)
```
Performance: O(n) scan, slow for large datasets

**PostgreSQL:**
```sql
SELECT * FROM find_memories_to_promote()
WHERE current_score >= 0.65;
```
Performance: O(log n) indexed query

### Example 2: Semantic Search

**JSONL (current):**
```python
query_embed = embed_model.encode(query_text)
for memory in all_memories:
    if memory.embed:
        sim = cosine_similarity(query_embed, memory.embed)
        if sim > 0.8:
            results.append(memory)
```
Performance: O(n) brute-force

**PostgreSQL:**
```sql
SELECT * FROM memories
ORDER BY embed <=> query_vector
LIMIT 10;
```
Performance: O(log n) HNSW index

### Example 3: Graph Traversal

**JSONL (current):**
```python
related = [r for r in all_relations if r.from_memory_id == memory.id]
# Manual recursion needed for multi-hop
```
Performance: O(n) per hop, difficult to implement correctly

**PostgreSQL:**
```sql
SELECT * FROM traverse_relationships('mem-123', depth=2);
```
Performance: O(k) where k = edges to traverse, clear and maintainable

## Performance Characteristics

### Memory Capacity

| Approach | Capacity | Notes |
|---|---|---|
| JSONL | 10-50K | Limited by RAM (full load) |
| SQLite | 100K-500K | Good for single-user |
| **PostgreSQL** | **1M+** | Scales with disk space |

### Query Latency

| Query Type | JSONL | SQLite | PostgreSQL |
|---|---|---|---|
| Decay score (all) | 500ms | 50ms | **5ms** |
| Vector search (10K) | 100ms | 20ms | **2ms** |
| Relationship traversal | N/A | 50ms | **5ms** |
| Full-text search | N/A | 100ms | **10ms** |

(Approximate for single-user, non-concurrent)

## Configuration for Cortexgraph

### Environment Variables

```bash
# Backend selection
CORTEXGRAPH_STORAGE_BACKEND=postgres  # or jsonl, sqlite

# PostgreSQL connection
CORTEXGRAPH_POSTGRES_HOST=localhost
CORTEXGRAPH_POSTGRES_PORT=5432
CORTEXGRAPH_POSTGRES_DB=cortexgraph
CORTEXGRAPH_POSTGRES_USER=cortexgraph
CORTEXGRAPH_POSTGRES_PASSWORD=<secure>

# Embeddings
CORTEXGRAPH_ENABLE_EMBEDDINGS=true
CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2

# Decay model (unchanged from existing)
CORTEXGRAPH_DECAY_MODEL=exponential
CORTEXGRAPH_DECAY_LAMBDA=2.673e-6  # 3-day half-life
CORTEXGRAPH_DECAY_BETA=0.6
```

## Implementation Roadmap

### Phase 1: Storage Layer Abstraction
- [ ] Create `PostgresMemoryStorage` class
- [ ] Implement CRUD operations
- [ ] Preserve exact API compatibility with existing storage backends
- [ ] Add transaction support for multi-operation atomicity

### Phase 2: Decay & Scoring Functions
- [ ] Migrate decay logic to PostgreSQL stored procedures
- [ ] Verify scores match JSONL/SQLite computations
- [ ] Add promotion/forgetting jobs

### Phase 3: Vector Integration
- [ ] Add embedding generation to save path
- [ ] Implement vector search endpoint
- [ ] Add similarity-based duplicate detection
- [ ] Implement consolidation via clustering

### Phase 4: Graph Traversal
- [ ] Implement multi-hop traversal
- [ ] Add relationship strength weighting
- [ ] Context expansion via traversal
- [ ] Cycle detection (to prevent infinite loops)

### Phase 5: Testing & Optimization
- [ ] Verify migration preserves all memories
- [ ] Performance testing and index tuning
- [ ] Concurrent user testing
- [ ] Backup/recovery procedures

## Remaining Open Questions

1. **Markdown LTM Reindexing**: Currently promoted Markdown files aren't "seen" by cortexgraph. Should PostgreSQL store full LTM text, or reference vault files?
   - **Option A**: Store full text in promoted_to column, re-embed periodically
   - **Option B**: Index vault directory on startup, sync with database
   - **Option C**: Hybrid - store metadata, lazy-load content on demand

2. **Multi-user Concurrency**: PostgreSQL enables multi-user, but cortexgraph was single-user. Should we add:
   - User/tenant ID to memories table?
   - Access control lists for shared memories?
   - Conflict resolution for concurrent edits?

3. **Embeddings Generation**: Should embeddings be:
   - Generated eagerly on save (slower write, fast read)
   - Generated lazily on first search (fast write, slow first read)
   - Pre-computed in batch jobs (complex but optimal)

## References

- CortexGraph Main Docs: `/Users/sc/cortexgraph/docs/`
- Decay Algorithm: `/Users/sc/cortexgraph/docs/scoring_algorithm.md`
- Existing Storage Code: `/Users/sc/cortexgraph/src/cortexgraph/storage/`
- PostgreSQL pgvector Docs: https://github.com/pgvector/pgvector
- Spaced Repetition Research: `/Users/sc/cortexgraph/docs/` (architecture notes)
