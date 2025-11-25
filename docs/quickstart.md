# Quick Start

Get up and running with CortexGraph in 5 minutes.

## Prerequisites

- ✅ CortexGraph installed ([Installation Guide](installation.md))
- ✅ Configuration file created ([Configuration Guide](configuration.md))
- ✅ Claude Desktop configured with MCP server

## Step 1: Verify Installation

Check that CortexGraph is ready:

```bash
# Check MCP server
cortexgraph --version

# Check CLI tools
cortexgraph-search --help
cortexgraph-maintenance --help
```

## Step 2: Start Claude Desktop

Restart Claude Desktop to load the CortexGraph MCP server.

Verify CortexGraph is available:
1. Start a new conversation
2. Look for the 🔌 icon (MCP tools available)
3. CortexGraph should appear in the available servers

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
cortexgraph-search "TypeScript"

# View storage statistics
cortexgraph-maintenance stats

# See raw JSONL storage
cat ~/.config/cortexgraph/jsonl/memories.jsonl
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
# Find clusters (dry run)
cortexgraph-consolidate run --all --dry-run

# Apply consolidation
cortexgraph-consolidate run --all

# Check queue status
cortexgraph-consolidate status
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
cortexgraph-search "task-tracker"

# Check decay scores
cortexgraph-maintenance stats
```

### 5. Promote to Long-Term

Important memories automatically promote to LTM when:
- Score >= 0.65 (high value)
- Used 5+ times in 14 days

Or manually promote via CLI:

```bash
# Find promotion candidates (dry run)
cortexgraph-consolidate run promote --dry-run

# Execute promotion to Obsidian vault
cortexgraph-consolidate run promote
```

Or ask Claude to promote specific memories via the `promote_memory` MCP tool.

## CLI Tools

### Search Across STM + LTM

```bash
# Basic search
cortexgraph-search "Python"

# Filter by tags
cortexgraph-search "Python" --tags coding,projects

# Limit results
cortexgraph-search "Python" --limit 10
```

### Maintenance

```bash
# View statistics
cortexgraph-maintenance stats

# Compact storage (remove deleted entries)
cortexgraph-maintenance compact

# Full report
cortexgraph-maintenance report
```

### Garbage Collection

Low-scoring memories can be cleaned up via MCP (ask Claude to use the `gc` tool) or via the decay analyzer:

```bash
# Find memories at risk of deletion (dry run)
cortexgraph-consolidate run decay --dry-run

# Process decay analysis
cortexgraph-consolidate run decay
```

### Memory Consolidation

```bash
# Run full consolidation pipeline (dry run)
cortexgraph-consolidate run --all --dry-run

# Apply consolidation (all agents)
cortexgraph-consolidate run --all

# Run individual agents
cortexgraph-consolidate run cluster --dry-run
cortexgraph-consolidate run merge --dry-run
```

## Advanced Usage

### Custom Decay Parameters

Edit `~/.config/cortexgraph/.env`:

```bash
# Slower decay (memories last longer)
CORTEXGRAPH_PL_HALFLIFE_DAYS=7.0

# Faster decay (more aggressive forgetting)
CORTEXGRAPH_PL_HALFLIFE_DAYS=1.0
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
CORTEXGRAPH_ENABLE_EMBEDDINGS=true
CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2
```

Install dependencies:
```bash
uv pip install sentence-transformers
```

## Troubleshooting

### No Memories Being Saved

1. Check Claude Desktop logs for MCP errors
2. Verify `.env` file exists: `cat ~/.config/cortexgraph/.env`
3. Check storage directory: `ls ~/.config/cortexgraph/jsonl/`

### Can't Find Memories

1. Check search: `cortexgraph-search "keyword"`
2. View all: `cat ~/.config/cortexgraph/jsonl/memories.jsonl`
3. Check decay scores: `cortexgraph-maintenance stats`

### Memory Decay Too Fast

Increase half-life in `.env`:
```bash
CORTEXGRAPH_PL_HALFLIFE_DAYS=7.0  # Increase from 3.0
```

## Next Steps

- [API Reference](api.md) - Learn all 15 MCP tools
- [Architecture](architecture.md) - Understand how CortexGraph works
- [Knowledge Graph](graph_features.md) - Build connected concepts
- [Scoring Algorithm](scoring_algorithm.md) - Deep dive into decay
