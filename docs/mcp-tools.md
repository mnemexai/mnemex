# CortexGraph MCP Tools Reference

**Comprehensive documentation for all CortexGraph MCP server tools.**

This document contains the full technical reference for all 18 MCP tools provided by CortexGraph. For minimal tool schemas in the MCP server itself, see the source files in `src/cortexgraph/tools/`.

---

## Table of Contents

1. [Memory Management](#memory-management)
   - save_memory
   - search_memory
   - search_unified
   - touch_memory
   - open_memories
   - read_graph

2. [Analysis Tools](#analysis-tools)
   - analyze_message
   - analyze_for_recall
   - auto_recall_process_message

3. [Graph Operations](#graph-operations)
   - cluster_memories
   - consolidate_memories
   - create_relation

4. [Maintenance](#maintenance)
   - gc
   - promote_memory
   - backfill_embeddings

5. [Performance](#performance)
   - get_performance_metrics
   - reset_performance_metrics

---

## Memory Management

### save_memory

Save a new memory to short-term storage with automatic preprocessing.

The memory will have temporal decay applied and will be forgotten if not used regularly. Frequently accessed memories may be promoted to long-term storage automatically.

**Auto-enrichment (v0.6.0)**: If entities or strength are not provided, they will be automatically extracted/calculated from the content using natural language preprocessing. This makes save_memory "just work" for conversational use.

**Parameters:**

- `content` (str): The content to remember (max 50,000 chars).
- `tags` (list[str] | None): Tags for categorization (max 50 tags, each max 100 chars).
- `entities` (list[str] | None): Named entities in this memory (max 100 entities). If None, automatically extracted from content.
- `source` (str | None): Source of the memory (max 500 chars).
- `context` (str | None): Context when memory was created (max 1,000 chars).
- `meta` (dict[str, Any] | None): Additional custom metadata.
- `strength` (float | None): Base strength multiplier (1.0-2.0). If None, automatically calculated based on content importance.

**Returns:**

Dictionary with:
- `success` (bool): Whether operation succeeded
- `memory_id` (str): UUID of saved memory
- `message` (str): Human-readable confirmation
- `has_embedding` (bool): Whether embedding was generated
- `enrichment_applied` (bool): Whether auto-enrichment was used
- `auto_entities` (int): Number of entities auto-extracted
- `calculated_strength` (float): Final strength value

**Raises:**

- `ValueError`: If any input fails validation.

---

### search_memory

Search for memories with optional filters and scoring.

This tool implements natural spaced repetition by blending memories due for review into results when they're relevant. This creates the "Maslow effect" - natural reinforcement through conversation.

**Content Preview (v0.7.0):** By default, returns first 300 characters of each memory to reduce context usage. Pass `preview_length=0` for full content, or set a custom length (1-5000 characters).

**Pagination:** Results are paginated to help you find specific memories across large result sets. Use `page` and `page_size` to navigate through results. If a search term isn't found on the first page, increment `page` to see more results.

**Parameters:**

- `query` (str | None): Text query to search for (max 50,000 chars).
- `tags` (list[str] | None): Filter by tags (max 50 tags).
- `top_k` (int): Maximum number of results before pagination (1-100).
- `window_days` (int | None): Only search memories from last N days (1-3650).
- `min_score` (float | None): Minimum decay score threshold (0.0-1.0).
- `use_embeddings` (bool): Use semantic search with embeddings.
- `include_review_candidates` (bool): Blend in memories due for review (default True).
- `page` (int | None): Page number to retrieve (1-indexed, default: 1).
- `page_size` (int | None): Number of memories per page (default: 10, max: 100).
- `preview_length` (int | None): Content preview length in chars (default: 300, 0 = full content).

**Returns:**

Dictionary with paginated results including:
- `results` (list): List of matching memories with scores for current page
- `pagination` (dict): Metadata (page, page_size, total_count, total_pages, has_more)

Some results may be review candidates that benefit from reinforcement.

**Examples:**

```python
# Get first page with previews (default 300 chars)
search_memory(query="authentication", page=1, page_size=10)

# Get full content
search_memory(query="authentication", preview_length=0)

# Custom preview length
search_memory(query="authentication", preview_length=500)
```

**Raises:**

- `ValueError`: If any input fails validation.

---

### search_unified

Search across both STM and LTM with unified ranking.

**Content Preview (v0.7.0):** By default, returns first 300 characters of each memory to reduce context usage. Pass `preview_length=0` for full content, or set a custom length (1-5000 characters).

**Pagination:** Results are paginated to help you find specific memories across large result sets from both short-term and long-term memory. Use `page` and `page_size` to navigate through results. If a search term isn't found on the first page, increment `page` to see more results.

**Parameters:**

- `query` (str | None): Text query to search for (max 50,000 chars).
- `tags` (list[str] | None): Filter by tags (max 50 tags).
- `limit` (int): Maximum total results before pagination (1-100).
- `stm_weight` (float): Weight multiplier for STM results (0.0-2.0).
- `ltm_weight` (float): Weight multiplier for LTM results (0.0-2.0).
- `window_days` (int | None): Only include STM memories from last N days (1-3650).
- `min_score` (float | None): Minimum score threshold for STM memories (0.0-1.0).
- `page` (int | None): Page number to retrieve (1-indexed, default: 1).
- `page_size` (int | None): Number of memories per page (default: 10, max: 100).
- `preview_length` (int | None): Content preview length in chars (default: 300, 0 = full content).

**Returns:**

Dictionary with paginated results including:
- `results` (list): List of matching memories from STM and LTM for current page
- `pagination` (dict): Metadata (page, page_size, total_count, total_pages, has_more)

**Examples:**

```python
# Get first page with previews (default 300 chars)
search_unified(query="architecture", page=1, page_size=10)

# Get full content
search_unified(query="architecture", preview_length=0)
```

**Raises:**

- `ValueError`: If any input fails validation.

---

### touch_memory

Reinforce a memory by updating its last accessed time and use count.

This resets the temporal decay and increases the memory's resistance to being forgotten. Optionally can boost the memory's base strength.

**Parameters:**

- `memory_id` (str): ID of the memory to reinforce (valid UUID).
- `boost_strength` (bool): Whether to boost the base strength.

**Returns:**

Updated memory statistics including old and new scores.

Dictionary with:
- `success` (bool): Whether operation succeeded
- `memory_id` (str): UUID of reinforced memory
- `old_score` (float): Score before reinforcement
- `new_score` (float): Score after reinforcement
- `use_count` (int): Updated use count
- `strength` (float): Updated strength value
- `message` (str): Human-readable summary

**Raises:**

- `ValueError`: If memory_id is invalid.

---

### open_memories

Retrieve specific memories by their IDs.

Similar to the reference MCP memory server's open_nodes functionality. Returns detailed information about the requested memories including their relations to other memories.

**Pagination:** When retrieving many memories by ID, results are paginated. Use `page` and `page_size` to navigate through the list of requested memories.

**Parameters:**

- `memory_ids` (str | list[str]): Single memory ID or list of memory IDs to retrieve (max 100 IDs).
- `include_relations` (bool): Include relations from/to these memories.
- `include_scores` (bool): Include decay scores and age.
- `page` (int | None): Page number to retrieve (1-indexed, default: 1).
- `page_size` (int | None): Number of memories per page (default: 10, max: 100).

**Returns:**

Dictionary with paginated results including:
- `memories` (list): Detailed memory information for current page
- `not_found` (list): List of IDs that weren't found
- `pagination` (dict): Metadata (page, page_size, total_count, total_pages, has_more)

**Examples:**

```python
# Get first page of memories
open_memories(["id1", "id2", "id3", ...], page=1, page_size=10)

# Get next page
open_memories(["id1", "id2", "id3", ...], page=2, page_size=10)
```

**Raises:**

- `ValueError`: If any memory ID is invalid or list exceeds maximum length.

---

### read_graph

Read the entire knowledge graph of memories and relations.

Returns the complete graph structure including all memories (with decay scores), all relations between memories, and statistics about the graph.

**Pagination:** Results are paginated to help you navigate large knowledge graphs. Use `page` and `page_size` to retrieve specific portions of the graph. If searching for specific memories or patterns, increment `page` to see more results.

**Parameters:**

- `status` (str): Filter memories by status - "active", "promoted", "archived", or "all".
- `include_scores` (bool): Include decay scores and age in results.
- `limit` (int | None): Maximum number of memories to return (1-10,000).
- `page` (int | None): Page number to retrieve (1-indexed, default: 1).
- `page_size` (int | None): Number of memories per page (default: 10, max: 100).

**Returns:**

Dictionary with paginated graph including:
- `memories` (list): List of memories for current page
- `relations` (list): All relations (not paginated, for graph structure)
- `stats` (dict): Graph statistics
- `pagination` (dict): Metadata (page, page_size, total_count, total_pages, has_more)

**Examples:**

```python
# Get first page of active memories
read_graph(status="active", page=1, page_size=10)

# Get next page
read_graph(status="active", page=2, page_size=10)

# Larger page for overview
read_graph(status="active", page=1, page_size=50)
```

**Raises:**

- `ValueError`: If status is invalid or limit is out of range.

---

## Analysis Tools

### analyze_message

Analyze a message to determine if it contains memory-worthy content.

Returns activation signals and suggested parameters for save_memory. This tool helps the LLM decide whether to save information without explicit "remember this" commands.

**Decision Support (v0.6.0)**: Provides confidence scores and reasoning to help Claude determine if save_memory should be called. High confidence (>0.7) suggests automatic save; medium confidence (0.4-0.7) suggests asking user first.

**Activation Module (v0.7.5)**: Now uses the configurable activation module with weighted sigmoid confidence calculation. Supports "I prefer" and other preference patterns from activation.yaml configuration.

**Parameters:**

- `message` (str): User message to analyze

**Returns:**

Dictionary containing:
- `should_save` (bool): Recommendation to save
- `confidence` (float): 0.0-1.0 confidence in recommendation
- `suggested_entities` (list[str]): Detected entities
- `suggested_tags` (list[str]): Suggested tags
- `suggested_strength` (float): Calculated importance (1.0-2.0)
- `reasoning` (str): Explanation of decision
- `phrase_signals` (dict): Detected signals for transparency

**Example:**

```python
>>> result = analyze_message("I prefer PostgreSQL for databases")
>>> result["should_save"]
True
>>> result["confidence"]
0.73
>>> "preference" in result["reasoning"].lower()
True
```

**Raises:**

- `ValueError`: If message is invalid or None.

---

### analyze_for_recall

Analyze a message to detect recall/search intent.

Returns detection signals and suggested parameters for search_memory. This tool helps the LLM decide whether to search memories based on natural language patterns like "what did I say about", "do you remember", etc.

**Decision Support (v0.6.0)**: Provides confidence scores and reasoning to help Claude determine if search_memory should be called. High confidence (>0.7) suggests automatic search; medium confidence (0.4-0.7) suggests asking user first.

**Parameters:**

- `message` (str): User message to analyze for recall patterns

**Returns:**

Dictionary containing:
- `should_search` (bool): Recommendation to search
- `confidence` (float): 0.0-1.0 confidence in recommendation
- `suggested_query` (str): Extracted query terms
- `suggested_tags` (list[str]): Tags to filter by (empty in Phase 1)
- `suggested_entities` (list[str]): Entities to filter by
- `reasoning` (str): Explanation of decision

**Example:**

```python
>>> result = analyze_for_recall("What did I say about my API preferences?")
>>> result["should_search"]
True
>>> result["confidence"]
0.9
>>> result["suggested_query"]
"API preferences"
```

**Raises:**

- `ValueError`: If message is invalid.

---

### auto_recall_process_message

Process a message and automatically recall/reinforce related memories.

This tool implements Phase 1 of auto-recall: silent reinforcement. When the user discusses topics, this tool:
1. Analyzes the message for topics/entities
2. Searches for related memories
3. Automatically reinforces found memories (updates last_used, use_count)
4. Returns statistics (no memory surfacing in Phase 1)

**Usage**: Call this periodically during conversations to keep important memories from decaying. The LLM should call this when the user discusses substantive topics (not on simple commands/queries).

**Phase 1 Behavior**: Silent mode - memories are reinforced but not surfaced to the conversation. This prevents decay while we tune surfacing strategies in later phases.

**Parameters:**

- `message` (str): User message to analyze for recall opportunities

**Returns:**

Dictionary with:
- `success` (bool): Whether operation succeeded
- `enabled` (bool): Is auto-recall enabled in config?
- `topics_found` (list[str]): Topics extracted from message
- `memories_found` (int): Count of related memories
- `memories_reinforced` (list[str]): IDs of reinforced memories
- `mode` (str): Current mode: silent/subtle/interactive
- `message` (str): Human-readable summary

**Example:**

```python
>>> result = auto_recall_process_message(
...     "I'm working on the STOPPER protocol implementation"
... )
>>> result["memories_reinforced"]
["abc-123", "def-456"]  # IDs of STOPPER-related memories
```

**Raises:**

- `ValueError`: If message is empty or invalid.

---

## Graph Operations

### cluster_memories

Cluster similar memories for potential consolidation or find duplicates.

Groups similar memories based on semantic similarity (if embeddings are enabled) or other strategies. Useful for identifying redundant memories.

**Parameters:**

- `strategy` (str): Clustering strategy (default: "similarity").
- `threshold` (float | None): Similarity threshold for linking (0.0-1.0, uses config default if not specified).
- `max_cluster_size` (int | None): Maximum memories per cluster (1-100, uses config default if not specified).
- `find_duplicates` (bool): Find likely duplicate pairs instead of clustering.
- `duplicate_threshold` (float | None): Similarity threshold for duplicates (0.0-1.0, uses config default).

**Returns:**

List of clusters or duplicate pairs with scores and suggested actions.

Dictionary with either:
- Clustering mode: `clusters` (list), `clusters_found` (int), `strategy` (str), `threshold` (float)
- Duplicate mode: `duplicates` (list), `duplicates_found` (int), `message` (str)

**Raises:**

- `ValueError`: If any input fails validation.

---

### consolidate_memories

Consolidate similar memories using algorithmic merging or linking.

This tool handles clusters in three ways:
1. MERGE (mode="apply"): Combine memories into one (high cohesion ≥0.75)
2. LINK (mode="link"): Create 'related' relations without merging (medium cohesion 0.40-0.75)
3. PREVIEW (mode="preview"): Show what would happen without making changes

**Merging intelligently:**
- Combines content (preserving unique information)
- Merges tags and entities (union)
- Calculates appropriate strength based on cohesion
- Preserves earliest created_at and latest last_used timestamps

Linking creates bidirectional 'related' relations to form knowledge graph connections.

**Modes:**
- "preview": Generate merge preview without making changes
- "apply": Execute the consolidation/merge (requires cluster_id or auto_detect)
- "link": Create relations between cluster members without merging

**Parameters:**

- `cluster_id` (str | None): Specific cluster ID to act on (valid UUID, required unless auto_detect=True).
- `mode` (str): Operation mode - "preview", "apply", or "link".
- `auto_detect` (bool): If True, automatically find high-cohesion clusters.
- `cohesion_threshold` (float): Minimum cohesion for auto-detection (0.0-1.0, default: 0.75).

**Returns:**

Consolidation/linking preview or execution results.

Dictionary with:
- `success` (bool): Whether operation succeeded
- `mode` (str): Operation mode used
- `candidates_found` (int): Number of candidates (preview mode)
- `consolidated_clusters` (int): Number of clusters merged (apply mode)
- `linked_clusters` (int): Number of clusters linked (link mode)
- `results` (list): Detailed results for each operation

**Raises:**

- `ValueError`: If cluster_id is invalid or cohesion_threshold is out of range.

---

### create_relation

Create an explicit relation between two memories.

Links two memories with a typed relationship.

**Parameters:**

- `from_memory_id` (str): Source memory ID (valid UUID).
- `to_memory_id` (str): Target memory ID (valid UUID).
- `relation_type` (str): Type of relation (must be one of: related, causes, supports, contradicts, has_decision, consolidated_from).
- `strength` (float): Strength of the relation (0.0-1.0).
- `metadata` (dict[str, Any] | None): Additional metadata about the relation.

**Returns:**

Created relation ID and confirmation.

Dictionary with:
- `success` (bool): Whether operation succeeded
- `relation_id` (str): UUID of created relation
- `from` (str): Source memory ID
- `to` (str): Target memory ID
- `type` (str): Relation type
- `strength` (float): Relation strength
- `message` (str): Human-readable confirmation

**Raises:**

- `ValueError`: If any input fails validation.

---

## Maintenance

### gc

Perform garbage collection on low-scoring memories.

Removes or archives memories whose decay score has fallen below the forget threshold. This prevents the database from growing indefinitely with unused memories.

**Parameters:**

- `dry_run` (bool): Preview what would be removed without actually removing.
- `archive_instead` (bool): Archive memories instead of deleting.
- `limit` (int | None): Maximum number of memories to process (1-10,000).

**Returns:**

Statistics about removed/archived memories.

Dictionary with:
- `success` (bool): Whether operation succeeded
- `dry_run` (bool): Whether this was a preview
- `removed_count` (int): Number of memories deleted
- `archived_count` (int): Number of memories archived
- `freed_score_sum` (float): Total score of affected memories
- `memory_ids` (list): Sample of affected memory IDs (first 10)
- `total_affected` (int): Total count of affected memories
- `message` (str): Human-readable summary

**Raises:**

- `ValueError`: If limit is out of valid range.

---

### promote_memory

Promote high-value memories to long-term storage.

Memories with high scores or frequent usage are promoted to the Obsidian vault (or other long-term storage) where they become permanent.

**Parameters:**

- `memory_id` (str | None): Specific memory ID to promote (valid UUID).
- `auto_detect` (bool): Automatically detect promotion candidates.
- `dry_run` (bool): Preview what would be promoted without promoting.
- `target` (str): Storage backend for promotion. Default: "obsidian" (Obsidian-compatible markdown). Note: This is a storage format, not a file path. Path configured via LTM_VAULT_PATH.
- `force` (bool): Force promotion even if criteria not met.

**Returns:**

List of promoted memories and promotion statistics.

Dictionary with:
- `success` (bool): Whether operation succeeded
- `dry_run` (bool): Whether this was a preview
- `candidates_found` (int): Number of promotion candidates
- `promoted_count` (int): Number of memories promoted
- `promoted_ids` (list): UUIDs of promoted memories
- `candidates` (list): Details about top candidates
- `message` (str): Human-readable summary

**Raises:**

- `ValueError`: If memory_id is invalid or target is not supported.

---

### backfill_embeddings

Generate embeddings for memories that don't have them.

This tool backfills embedding vectors for existing memories, enabling semantic search and improved clustering. Embeddings are generated using sentence-transformers models (default: all-MiniLM-L6-v2).

**When to use:**
- After importing memories without embeddings
- When switching from text-only to semantic search
- Before running consolidation with embedding-based clustering
- To enable similarity-based features

**Safety features:**
- dry_run: Preview what would be processed without making changes
- limit: Process only N memories (useful for testing or incremental backfill)
- force: Regenerate embeddings even if they exist (for model upgrades)

**Parameters:**

- `model` (str): Sentence-transformers model name (default: "all-MiniLM-L6-v2"). Common alternatives: "all-mpnet-base-v2" (higher quality, slower), "paraphrase-MiniLM-L6-v2" (good for paraphrase detection).
- `limit` (int | None): Maximum number of memories to process (1-10,000). If None, processes all.
- `force` (bool): If True, regenerate embeddings even if they exist (for model upgrades).
- `dry_run` (bool): If True, show what would be done without actually doing it.

**Returns:**

Result dictionary with:
- `success` (bool): Whether operation completed successfully
- `dry_run` (bool): Whether this was a dry run
- `processed` (int): Number of memories processed (0 if dry_run)
- `errors` (int): Number of errors encountered
- `model` (str): Model name used
- `total_memories` (int): Total memories in database
- `memories_without_embeddings` (int): Count of memories lacking embeddings
- `would_process` (int): Number of memories that would be processed (dry_run only)
- `message` (str): Human-readable summary

**Examples:**

```python
# Preview what would be backfilled
backfill_embeddings(dry_run=True)

# Backfill 10 memories for testing
backfill_embeddings(limit=10)

# Backfill all memories without embeddings
backfill_embeddings()

# Force regenerate with better model
backfill_embeddings(model="all-mpnet-base-v2", force=True)
```

**Raises:**

- `ValueError`: If limit is out of valid range.
- `ImportError`: If sentence-transformers is not installed.

---

## Performance

### get_performance_metrics

Get current performance metrics and statistics.

**Parameters:** None

**Returns:**

Dictionary containing performance statistics for various operations.

Includes timing information, operation counts, and performance metrics for:
- Memory operations (save, search, retrieve)
- Graph operations (clustering, consolidation)
- Storage operations (read, write, compaction)

---

### reset_performance_metrics

Reset all performance metrics and return confirmation.

**Parameters:** None

**Returns:**

Dictionary confirming metrics have been reset.

Dictionary with:
- `success` (bool): Always True
- `message` (str): Confirmation message

---

## Version History

- **v0.7.5**: Added activation module with configurable patterns, web visualization
- **v0.7.0**: Added content preview and pagination features
- **v0.6.0**: Added natural language activation (analyze_message, analyze_for_recall, auto_recall_process_message)
- **v0.5.1**: Added natural spaced repetition system
- **v0.5.0**: Initial release with 13 core tools

---

## See Also

- [Architecture Documentation](architecture.md) - System design and components
- [API Quick Reference](api.md) - Minimal tool signatures
- [Configuration Guide](../README.md#configuration) - Environment variables and settings
- [GitHub Repository](https://github.com/simplemindedbot/cortexgraph) - Source code and issues
