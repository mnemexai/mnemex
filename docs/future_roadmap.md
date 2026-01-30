# Future Roadmap for CortexGraph

This document outlines potential future improvements and implementation approaches for CortexGraph.

## 1. Spaced Repetition

**What it is:** A learning technique where review intervals increase exponentially (e.g., SuperMemo, Anki algorithms).

**Current State in CortexGraph:**
- You have `touch_memory()` which reinforces memories
- Decay algorithm reduces scores over time
- But there's no **proactive suggestion** of when to review

**Potential Implementation:**

```python
# Calculate optimal review time based on current strength
next_review = calculate_next_review(memory)
  = current_time + (strength * base_interval * (use_count ^ β))

# SM-2 inspired spacing
intervals = [1 day, 3 days, 7 days, 14 days, 30 days, ...]
```

**Features to add:**
1. **Review scheduling** - Track `next_review_at` timestamp
2. **Review queue tool** - `get_review_queue()` returns memories due for review
3. **Review outcome tracking** - Easy/medium/hard adjusts next interval
4. **Adaptive intervals** - Learn from user's actual recall patterns

**Benefit:** Memories you want to keep get reinforced just before they'd decay too much. More efficient than random touching.

---

## 2. Adaptive Decay Parameters

**The Problem:** Current λ (decay rate) and β (use weight) are fixed. But different memory types should decay differently:
- Preferences: slow decay
- Project context: medium decay
- Random facts: fast decay

**Approaches:**

### A. Category-Based Adaptation

```python
DECAY_PROFILES = {
    "preference": {"lambda": 5.7e-7, "beta": 0.3},  # 14-day half-life
    "decision": {"lambda": 1.15e-6, "beta": 0.5},   # 7-day half-life
    "context": {"lambda": 2.67e-6, "beta": 0.6},    # 3-day half-life (default)
    "fact": {"lambda": 8.02e-6, "beta": 0.8},       # 1-day half-life
}
```

Auto-detect category from tags or content analysis.

### B. Usage-Pattern Learning

Track actual usage patterns and adjust:

```python
if memory.use_count > 10 and time_since_last_use < 1_day:
    # Frequently accessed → slow decay
    memory.custom_lambda = memory.custom_lambda * 0.8
elif memory.use_count < 3 and time_since_last_use > 7_days:
    # Rarely accessed → fast decay
    memory.custom_lambda = memory.custom_lambda * 1.2
```

### C. Reinforcement Learning

- Track which memories get promoted vs forgotten
- Learn optimal parameters per memory type
- Requires more data but most powerful

**Recommendation:** Start with **Category-Based** (simple, immediate benefit), then add **Usage-Pattern Learning** (moderate complexity).

---

## 3. Clustering & Consolidation: LLM vs Algorithmic?

**Current clustering (algorithmic):**
- ✅ Embeddings-based similarity (cosine distance)
- ✅ Duplicate detection (high threshold like 0.88+)
- ✅ Cluster formation (medium threshold like 0.78-0.83)

**Consolidation Options:**

### Option A: Pure Algorithmic (No LLM)

```python
def consolidate_algorithmic(cluster):
    if similarity > 0.95:
        # Near-duplicates: keep newer, delete older
        return keep_newest(cluster)

    if similarity > 0.85:
        # High overlap: merge tags, combine entities
        return merge_metadata(cluster)

    if similarity > 0.75:
        # Related: just create relations, don't merge
        return link_memories(cluster)
```

**Pros:** Fast, deterministic, no external dependencies
**Cons:** Can't understand semantic nuance, might lose information

### Option B: LLM-Assisted (Hybrid)

```python
def consolidate_with_llm(cluster):
    # 1. Algorithmic pre-filter
    if similarity < 0.75:
        return "no_action"

    # 2. LLM decides merge strategy
    prompt = f"""
    These memories are similar. Should they be:
    1. Merged (duplicates/redundant)
    2. Linked (related but distinct)
    3. Kept separate

    Memory 1: {mem1.content}
    Memory 2: {mem2.content}
    """

    decision = llm_call(prompt)

    # 3. If merge, LLM writes consolidated version
    if decision == "merge":
        merged_content = llm_call(f"Merge these: {memories}")
        return create_consolidated_memory(merged_content)
```

**Pros:** Smart decisions, preserves semantic meaning
**Cons:** Slower, requires MCP client support, not deterministic

### Option C: Algorithmic with Human Review

```python
def consolidate_interactive(cluster):
    # Show side-by-side comparison
    preview = generate_merge_preview(cluster)

    # User approves/rejects/edits
    return {
        "action": "preview",
        "original_memories": cluster,
        "suggested_merge": algorithmic_merge(cluster),
        "user_can_edit": True
    }
```

**Pros:** User control, no LLM needed, no data loss
**Cons:** Manual work required

### **Recommendation:**

Start with **Option C (Algorithmic + Human Review)** because:
1. **Safe** - No automatic deletions, user confirms
2. **Fast** - No LLM calls needed
3. **Flexible** - User can edit merged content
4. **MCP-friendly** - Returns preview, client handles approval

Later, add **Option B (LLM-assisted)** as an opt-in feature for power users.

**Implementation:**

```python
@mcp.tool()
def consolidate_memories(cluster_id: str, mode: str = "preview"):
    cluster = get_cluster(cluster_id)

    if mode == "preview":
        # Algorithmic merge
        merged = {
            "content": merge_content_smart(cluster),
            "tags": union(tags),
            "entities": union(entities),
            "strength": max(strengths) * 1.1,
            "original_ids": [m.id for m in cluster]
        }
        return {"preview": merged, "action": "awaiting_approval"}

    if mode == "apply":
        # User approved, do the merge
        new_mem = create_memory(merged)
        for old_mem in cluster:
            mark_as_consolidated(old_mem, new_mem.id)
        return {"success": True, "new_id": new_mem.id}
```

---

## 4. Performance Improvements

**Current Bottlenecks:**

### A. In-Memory Search (JSONL files)

- Every search reads entire file
- O(n) for every query
- Gets slow at 10K+ memories

**Solution:**

```python
# Option 1: Index by tags/entities
tag_index = {"typescript": [mem_id1, mem_id2, ...]}
entity_index = {"Claude": [mem_id3, mem_id4, ...]}

# Option 2: Bloom filter for quick "not found"
if not bloom_filter.might_contain(query):
    return []  # Fast path

# Option 3: Incremental compaction
compact_if(num_tombstones > 1000 or file_size > 10MB)
```

### B. Embedding Generation

- Slow for large batches
- Re-computes for duplicates

**Solution:**

```python
# Cache embeddings by content hash
embedding_cache[hash(content)] = embedding
```

### C. Decay Calculation

- Calculates score for every memory on every search

**Solution:**

```python
# Pre-compute scores periodically
background_task:
    update_all_scores_cached()
    sleep(60)  # Refresh every minute

# Search uses cached scores
def search(query):
    candidates = filter_by_tags(query)
    # Use pre-computed scores, don't recalc
    return sort_by(candidates, key=lambda m: m.cached_score)
```

**Benchmarking Plan:**

```python
# tests/performance/test_benchmarks.py
def benchmark_search():
    for n in [100, 1000, 10000, 100000]:
        memories = generate_test_memories(n)
        start = time()
        search(query)
        print(f"n={n}: {time() - start}s")

def benchmark_decay():
    # Measure score calculation speed

def benchmark_compaction():
    # Measure JSONL rewrite performance
```

---

## 5. Other Improvements

### A. Testing Coverage

Current gaps (likely):
- Edge cases in decay models
- LTM index updates
- Git backup failures
- Concurrent access

**Plan:**

```bash
# Generate coverage report
pytest --cov=cortexgraph --cov-report=html
open htmlcov/index.html

# Focus on <80% coverage modules
# Add integration tests for CLI tools
```

### B. Production Hardening

- Error handling for corrupted JSONL
- Graceful degradation if embeddings fail
- File locking for concurrent access
- Backup before destructive operations

### C. GitHub Release (v1.0.0)

- Tag the current commit
- Generate changelog
- Build wheel
- Publish to PyPI (optional)

### D. More Examples

- Claude prompt templates for auto-save
- Different use cases (personal assistant, dev env, research)
- Integration with other tools (Raycast, Alfred, etc.)

---

## Completed: UV Tool Install Migration ✅

### Changes Made

**Installation Simplified:**

Before:
```bash
git clone https://github.com/simplemindedbot/cortexgraph.git
cd cortexgraph
uv pip install -e .
# Complex MCP config with paths and PYTHONPATH
```

After:
```bash
uv tool install git+https://github.com/simplemindedbot/cortexgraph.git
# Simple MCP config: {"command": "cortexgraph"}
```

### MCP Config Updates

**Before:**
```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "uv",
      "args": ["--directory", "/path/to/cortexgraph", "run", "cortexgraph"],
      "env": {"PYTHONPATH": "/path/to/cortexgraph/src"}
    }
  }
}
```

**After:**
```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "cortexgraph"
    }
  }
}
```

### Migration Guide for Users

For existing users switching from editable install:

```bash
# 1. Uninstall editable version
uv pip uninstall cortexgraph

# 2. Install as tool
uv tool install git+https://github.com/simplemindedbot/cortexgraph.git

# 3. Update Claude config to just: {"command": "cortexgraph"}
#    Remove the --directory, run, and PYTHONPATH settings
```

**Your data is safe!** This only changes how the command is installed. Your memories in `~/.config/cortexgraph/` are untouched.

---

## Completed: Consolidation Tool ✅

### Implementation Summary

**Completed:** Algorithmic consolidation with preview/apply modes

**Files Added:**
- `src/cortexgraph/core/consolidation.py` - Core merging logic (uses batch operations in v1.2.0+)
- `src/cortexgraph/core/similarity.py` - Similarity calculation functions (extracted in v1.2.0)
- `tests/test_consolidation.py` - Comprehensive test suite (15 tests, 100% coverage)

**Features:**
- Smart content merging (preserves unique information, detects duplicates)
- Tag and entity merging (union of all values)
- Strength calculation based on cluster cohesion
- Timestamp preservation (earliest created_at, latest last_used)
- Relation tracking (consolidated_from relations)
- Auto-detect mode (finds high-cohesion clusters automatically)
- Preview mode (dry-run to inspect before applying)

**Usage:**
```python
# Auto-detect and preview
consolidate_memories(auto_detect=True, mode="preview", cohesion_threshold=0.75)

# Apply consolidation
consolidate_memories(auto_detect=True, mode="apply", cohesion_threshold=0.80)
```

**Test Results:**
All 15 tests passing:
- `test_merge_tags`, `test_merge_entities`, `test_merge_metadata`
- `test_merge_content_duplicates`, `test_merge_content_distinct`
- `test_calculate_merged_strength`
- `test_generate_consolidation_preview`
- `test_execute_consolidation`
- `test_consolidation_preserves_timestamps`

---

## Priority Order

1. ~~**Consolidation Tool** (1-2 days) - Implement algorithmic merge with preview~~ ✅ **DONE**
2. **Spaced Repetition** (2-3 days) - Add review queue and scheduling
3. **Adaptive Decay** (3-4 days) - Category-based decay profiles
4. **Performance** (1-2 days) - Benchmarking and optimization
5. **Production Hardening** (ongoing) - Testing and error handling
