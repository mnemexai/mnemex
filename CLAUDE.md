# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Status

This repository contains:
1. **Research documentation** (`stm-server-research.md`) - Original research and design
2. **Working implementation** (`stm-server/`) - Functional MCP server with 10 tools

**Current Phase:** Phase 1 Complete → Phase 2 Planning
**Next Milestone:** Storage refactor (SQLite → JSONL), LTM index, Git integration

## Current Implementation (v0.1 - Phase 1 Complete)

The `stm-server/` directory contains a fully functional MCP server with:

### 10 MCP Tools Implemented

1. **save_memory** - Save memory with entities, tags, optional embeddings
2. **search_memory** - Search with temporal filtering and semantic similarity
3. **touch_memory** - Reinforce memory (update last_used, use_count, strength)
4. **gc** - Garbage collect low-scoring memories
5. **promote_memory** - Promote high-value memories to long-term storage
6. **cluster_memories** - Find similar memories for consolidation
7. **consolidate_memories** - LLM-driven merge/dedupe (stub)
8. **read_graph** - Return entire knowledge graph with memories and relations
9. **open_memories** - Retrieve specific memories by ID with relations
10. **create_relation** - Create explicit links between memories

### Core Features

- **Temporal Decay**: Exponential decay with 3-day default half-life
- **Reinforcement**: Memories strengthen with repeated access
- **Knowledge Graph**: Entities, relations, and memory nodes
- **SQLite Storage**: v2 schema with migrations (memories + relations tables)
- **Type-Safe Models**: Pydantic models for Memory, Relation, KnowledgeGraph
- **FastMCP Framework**: Modern MCP server implementation

### Storage Schema (Current - SQLite)

```sql
-- V1 Schema
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  meta TEXT,                -- JSON: {tags, source, context}
  created_at INTEGER NOT NULL,
  last_used INTEGER NOT NULL,
  use_count INTEGER NOT NULL DEFAULT 0,
  strength REAL NOT NULL DEFAULT 1.0,
  status TEXT NOT NULL DEFAULT 'active',
  entities TEXT,            -- Added in v2: JSON array
  embed BLOB                -- Optional: float32 array
);

-- V2 Schema Addition
CREATE TABLE relations (
  id TEXT PRIMARY KEY,
  from_memory_id TEXT NOT NULL,
  to_memory_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  strength REAL NOT NULL DEFAULT 1.0,
  created_at INTEGER NOT NULL,
  metadata TEXT,
  FOREIGN KEY (from_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
  FOREIGN KEY (to_memory_id) REFERENCES memories(id) ON DELETE CASCADE
);
```

## Upcoming Refactor (v0.2 - Planned & Approved)

**Goal:** Human-readable storage + LTM index + Git backups + Remove Basic Memory dependency

### Key Changes

1. **Storage: SQLite → JSONL**
   - Human-readable, git-friendly format
   - One memory per line: `{"id": "...", "content": "...", ...}\n`
   - In-memory indexes for fast queries
   - Periodic compaction to remove deleted entries

2. **LTM Index for Vault Search**
   - Index 1500+ existing Obsidian vault markdown files
   - Parse YAML frontmatter and extract metadata
   - Track file mtimes for incremental updates
   - Lightweight JSONL index file

3. **Git Integration**
   - Use GitPython library for automated backups
   - Auto-commit on schedule or significant events
   - Snapshot and restore functionality

4. **Remove Basic Memory Dependency**
   - Write markdown files directly to vault
   - Clean-room wikilink implementation
   - YAML frontmatter with relations metadata
   - Avoid AGPL v3 license contamination

5. **Document Core IP**
   - Smart prompting system (when to auto-save/recall/reinforce)
   - Scoring algorithm mathematical details
   - Tuning guidelines and visualizations

### Libraries to Use (Don't Reinvent Wheels)

- **python-frontmatter** - Parse/write YAML frontmatter in markdown
- **markdown** - Markdown parsing with wikilinks extension
- **GitPython** - Git operations
- **json** (stdlib) - JSONL reading/writing

### Migration Plan

1. Create `jsonl_storage.py` with same API as `database.py`
2. Implement migration tool: SQLite → JSONL
3. Update server.py to use new storage
4. Add LTM index builder
5. Add Git backup module
6. Create unified search tool (STM + LTM)
7. Update all documentation

## Key Technical Innovations

### 1. Temporal Decay Scoring Algorithm

**Formula:**
```
score = (use_count ^ β) * exp(-λ * time_delta) * strength
```

**Parameters:**
- `λ` (lambda): Decay constant - default: `ln(2) / (3 * 86400)` for 3-day half-life
- `β` (beta): Use count weight - default: 0.6
- `time_delta`: Seconds since last access
- `strength`: Base multiplier (1.0-2.0)

**Thresholds:**
- `τ_forget`: 0.05 - memories below this are deleted
- `τ_promote`: 0.65 - memories above this are promoted to LTM
- **OR** use_count ≥ 5 within 14 days → promote

**Implementation:** `src/stm_server/core/decay.py:calculate_score()`

### 2. Smart Prompting System

**Concept:** Teach LLMs to naturally interact with memory without explicit commands.

**Auto-Detection Patterns:**
- **Auto-save**: User shares important information, decisions, preferences
- **Auto-recall**: User asks about past topics, references previous context
- **Auto-reinforce**: User revisits or builds upon previous memories
- **Auto-consolidate**: Similar memories detected, prompt for merge

**System Prompt Template:**
```
When the user shares important information (decisions, preferences, facts about
themselves or their projects), automatically save it to short-term memory using
save_memory. When they reference past topics, search and recall relevant memories.
When they revisit information, reinforce those memories with touch_memory.

Be natural - don't announce every memory operation. Just remember things like
a human would.
```

**Documentation:** To be created in `docs/prompts/memory_system_prompt.md`

## Architecture

### Two-Layer Memory System

```
┌─────────────────────────────────────┐
│   STM (Short-Term Memory)           │
│   - JSONL storage                   │
│   - Temporal decay                  │
│   - Fast in-memory indexes          │
│   - Hours to weeks retention        │
│   - Knowledge graph with relations  │
└──────────────┬──────────────────────┘
               │
               │ Promotion (high value)
               ↓
┌─────────────────────────────────────┐
│   LTM (Long-Term Memory)            │
│   - Markdown files in Obsidian      │
│   - Permanent storage               │
│   - Wikilinks and frontmatter       │
│   - Git version control             │
│   - Indexed for search              │
└─────────────────────────────────────┘
```

### Search Strategy

**Unified Search:**
1. Query STM (in-memory, fast)
2. Query LTM index (lightweight JSONL)
3. Merge results with temporal ranking
4. Apply decay scores to STM results
5. Deduplicate and return top-k

**When to search where:**
- Recent context (< 7 days): STM primarily
- Older context (> 7 days): LTM primarily
- Semantic queries: Both with embedding similarity
- Entity queries: Both with entity matching

### File Organization

```
stm-server/
├── src/stm_server/
│   ├── core/              # Decay, scoring, clustering
│   │   ├── decay.py       # Temporal decay algorithm (CORE IP)
│   │   ├── scoring.py     # Forget/promote decisions
│   │   └── cluster.py     # Similarity detection
│   ├── storage/           # Data persistence
│   │   ├── models.py      # Pydantic models
│   │   ├── database.py    # SQLite (current, v0.1)
│   │   ├── jsonl_storage.py  # JSONL (planned, v0.2)
│   │   ├── ltm_index.py   # Vault index (planned, v0.2)
│   │   └── migrations.py  # Schema versioning
│   ├── tools/             # MCP tool implementations (10 tools)
│   ├── vault/             # Markdown writing (planned, v0.2)
│   ├── backup/            # Git integration (planned, v0.2)
│   ├── config.py          # Configuration management
│   └── server.py          # MCP server entry point
├── tests/                 # Test suite
├── docs/                  # Documentation
│   ├── architecture.md    # Deep dive
│   ├── api.md            # Tool reference
│   ├── graph_features.md # Knowledge graph guide
│   └── prompts/          # Smart prompting (planned, v0.2)
├── pyproject.toml         # Project config
├── .env.example           # Config template
└── README.md              # Quick start
```

## Configuration

**Key Settings (.env):**
```bash
# Storage
STM_DB_PATH=~/.stm/memories.db          # Current: SQLite
STM_STORAGE_PATH=~/.stm/memories.jsonl  # Planned: JSONL

# Decay parameters
STM_DECAY_LAMBDA=2.673e-6  # 3-day half-life: ln(2)/(3*86400)
STM_DECAY_BETA=0.6         # Use count exponent

# Thresholds
STM_FORGET_THRESHOLD=0.05  # Delete if score < this
STM_PROMOTE_THRESHOLD=0.65 # Promote if score >= this

# Long-term storage
LTM_VAULT_PATH=~/Documents/Obsidian/Vault
LTM_INDEX_PATH=~/.stm/ltm_index.jsonl

# Git backups
GIT_AUTO_COMMIT=true
GIT_COMMIT_INTERVAL=3600   # Seconds

# Embeddings (optional)
USE_EMBEDDINGS=false
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Development Commands

```bash
# Installation
cd stm-server
uv pip install -e ".[dev]"

# Run server
python -m stm_server.server
# Or: stm-server

# Tests
pytest
pytest --cov=stm_server --cov-report=html

# Type checking
mypy src/stm_server

# Linting
ruff check src/stm_server
ruff format src/stm_server
```

## MCP Integration

**Claude Desktop Config:**
```json
{
  "mcpServers": {
    "stm": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/stm-research/stm-server",
        "run",
        "stm-server"
      ],
      "env": {
        "STM_STORAGE_PATH": "~/.stm/memories.jsonl",
        "LTM_VAULT_PATH": "~/Documents/Obsidian/Vault"
      }
    }
  }
}
```

## License and Attribution

**License:** MIT (for this implementation)

**Attribution:**
- Research inspired by Memoripy, Titan MCP, MemoryBank
- MCP protocol by Anthropic
- Clean-room implementation (no AGPL code copied)

**What NOT to copy:**
- Basic Memory MCP server code (AGPL v3)
- Use libraries (python-frontmatter, markdown, GitPython) instead
- Can reference for inspiration but reimplement from scratch

## Related Systems

- **Model Context Protocol**: https://github.com/modelcontextprotocol
- **MCP Memory Server**: https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- **Basic Memory MCP**: https://github.com/coleam00/basic-memory (AGPL - don't copy code)

## Working with This Codebase

When implementing new features:

1. **Read existing code first** - Understand patterns in models.py, tools/, core/
2. **Maintain API compatibility** - Don't break existing tool interfaces
3. **Add tests** - Every tool and core function needs tests
4. **Type hints everywhere** - Use Pydantic models, mypy compliance
5. **Update docs** - Keep README, architecture.md, api.md in sync
6. **Use existing libraries** - Don't reinvent (frontmatter, markdown, GitPython)
7. **Preserve core IP** - Decay algorithm and smart prompting are unique value

When refactoring:

1. **Create new modules alongside old** - Don't break working code
2. **Add migration tools** - Help users transition (SQLite → JSONL)
3. **Test backwards compatibility** - Existing clients shouldn't break
4. **Update config gradually** - Support both old and new formats during transition

## Next Implementation Phase

**Priority Order:**
1. Create `jsonl_storage.py` with in-memory indexing
2. Build migration tool from SQLite
3. Implement LTM index for vault search
4. Add Git integration with auto-commits
5. Create unified search tool (STM + LTM)
6. Document smart prompting patterns
7. Document scoring algorithm details
8. Update all examples and documentation

**Testing Strategy:**
- Unit tests for each storage method
- Integration tests for migration
- Performance tests with 1K, 10K, 100K memories
- LTM index tests with 1500+ markdown files
