# Quick Start

Get up and running with Mnemex in 5 minutes.

## Prerequisites

- ✅ Mnemex installed ([Installation Guide](installation.md))
- ✅ Configuration file created ([Configuration Guide](configuration.md))
- ✅ Claude Desktop configured with MCP server

## Step 1: Verify Installation

Check that Mnemex is ready:

```bash
# Check MCP server
mnemex --version

# Check CLI tools
mnemex-search --help
mnemex-maintenance --help
```

## Step 2: Start Claude Desktop

Restart Claude Desktop to load the Mnemex MCP server.

Verify Mnemex is available:
1. Start a new conversation
2. Look for the 🔌 icon (MCP tools available)
3. Mnemex should appear in the available servers

## Step 3: Save Your First Memory

In Claude, try:

> "I prefer TypeScript over JavaScript for new projects. Remember this preference."

Claude will automatically use `save_memory` to store this information.

## Step 4: Recall a Memory

Later, ask:

> "What are my language preferences?"

Claude will use `search_memory` to find and recall your preference.

## Step 5: View Your Memories

Check what's stored:

```bash
# Search all memories
mnemex-search "TypeScript"

# View storage statistics
mnemex-maintenance stats

# See raw JSONL storage
cat ~/.config/mnemex/jsonl/memories.jsonl
```

## Common Patterns

### Auto-Save Important Information

Claude automatically saves when you share:
- Personal preferences
- Project decisions
- Important facts
- Context about your work

### Auto-Recall Context

Claude automatically searches memory when you:
- Reference past topics
- Ask about previous decisions
- Continue earlier conversations

### Reinforce Memories

When you revisit information, Claude uses `touch_memory` to strengthen it, preventing decay.

### Consolidate Similar Memories

When similar memories accumulate:

```bash
# Find clusters
mnemex-consolidate --preview

# Apply consolidation
mnemex-consolidate --apply
```

Or let Claude do it automatically when detecting related memories.

## Example Workflow

### 1. Project Setup

> "I'm starting a new project called 'task-tracker'. It's a Python web app using FastAPI and PostgreSQL."

Claude saves this as a memory with entities: `task-tracker`, `FastAPI`, `PostgreSQL`

### 2. Make Decisions

> "For task-tracker, I've decided to use SQLAlchemy for the ORM and Alembic for migrations."

Claude saves this decision and links it to the project entity.

### 3. Days Later...

> "What decisions did I make for task-tracker?"

Claude searches memories for `task-tracker` entity and recalls all related decisions.

### 4. Review Memory Status

```bash
# See all memories related to project
mnemex-search "task-tracker"

# Check decay scores
mnemex-maintenance stats
```

### 5. Promote to Long-Term

Important memories automatically promote to LTM when:
- Score >= 0.65 (high value)
- Used 5+ times in 14 days

Or manually promote:

```bash
# Find high-value memories
mnemex-promote --dry-run

# Promote to Obsidian vault
mnemex-promote
```

## CLI Tools

### Search Across STM + LTM

```bash
# Basic search
mnemex-search "Python"

# Filter by tags
mnemex-search "Python" --tags coding,projects

# Limit results
mnemex-search "Python" --limit 10
```

### Maintenance

```bash
# View statistics
mnemex-maintenance stats

# Compact storage (remove deleted entries)
mnemex-maintenance compact

# Full report
mnemex-maintenance report
```

### Garbage Collection

```bash
# Preview what will be deleted
mnemex-gc --dry-run

# Delete low-scoring memories
mnemex-gc
```

### Memory Consolidation

```bash
# Find similar memory clusters
mnemex-consolidate --preview --cohesion-threshold 0.75

# Apply consolidation
mnemex-consolidate --apply --cohesion-threshold 0.80
```

## Advanced Usage

### Custom Decay Parameters

Edit `~/.config/mnemex/.env`:

```bash
# Slower decay (memories last longer)
MNEMEX_PL_HALFLIFE_DAYS=7.0

# Faster decay (more aggressive forgetting)
MNEMEX_PL_HALFLIFE_DAYS=1.0
```

Restart Claude Desktop to apply changes.

### Knowledge Graph

Build a graph of connected concepts:

```python
# Create explicit relations
create_relation(
    from_id="mem_project_xyz",
    to_id="mem_decision_sqlalchemy",
    relation_type="has_decision"
)

# Query the graph
read_graph()  # Get entire graph
open_memories(["mem_project_xyz"])  # Get memory with relations
```

### Embeddings for Semantic Search

Enable in `.env`:

```bash
MNEMEX_ENABLE_EMBEDDINGS=true
MNEMEX_EMBED_MODEL=all-MiniLM-L6-v2
```

Install dependencies:
```bash
uv pip install sentence-transformers
```

## Troubleshooting

### No Memories Being Saved

1. Check Claude Desktop logs for MCP errors
2. Verify `.env` file exists: `cat ~/.config/mnemex/.env`
3. Check storage directory: `ls ~/.config/mnemex/jsonl/`

### Can't Find Memories

1. Check search: `mnemex-search "keyword"`
2. View all: `cat ~/.config/mnemex/jsonl/memories.jsonl`
3. Check decay scores: `mnemex-maintenance stats`

### Memory Decay Too Fast

Increase half-life in `.env`:
```bash
MNEMEX_PL_HALFLIFE_DAYS=7.0  # Increase from 3.0
```

## Next Steps

- [API Reference](api.md) - Learn all 11 MCP tools
- [Architecture](architecture.md) - Understand how Mnemex works
- [Knowledge Graph](graph_features.md) - Build connected concepts
- [Scoring Algorithm](scoring_algorithm.md) - Deep dive into decay
