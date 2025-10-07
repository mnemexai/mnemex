# STM Server - Short-Term Memory with Temporal Decay

A Model Context Protocol (MCP) server that provides ephemeral memory with temporal decay, reinforcement learning, and automatic promotion to long-term storage. Designed to give AI assistants human-like memory dynamics where memories fade if not used but strengthen with repeated access.

## Features

- **Temporal Decay**: Memories naturally fade over time using exponential decay
- **Reinforcement**: Frequently accessed memories persist longer
- **Automatic Promotion**: High-value memories are promoted to long-term storage (Obsidian vault)
- **Knowledge Graph**: Complete graph structure with memories, entities, and relations
- **Graph Navigation**: Read entire graph, open specific memories, create explicit links
- **Semantic Search**: Optional embedding-based similarity search
- **Clustering**: Find and consolidate similar memories
- **MCP Integration**: Full Model Context Protocol support for AI assistants

## Quick Start

### Installation

```bash
cd stm-server

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .

# Optional: Install with embeddings support
pip install -e ".[embeddings]"
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `STM_DB_PATH`: Database location (default: `~/.stm/memories.db`)
- `STM_DECAY_LAMBDA`: Decay rate (default: 3-day half-life)
- `BASIC_MEMORY_PATH`: Path to Obsidian vault for long-term storage

### MCP Configuration

Add to your MCP settings file (e.g., Claude Desktop config):

```json
{
  "mcpServers": {
    "stm": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/stm-server",
        "run",
        "stm-server"
      ],
      "env": {
        "STM_DB_PATH": "~/.stm/memories.db",
        "BASIC_MEMORY_PATH": "~/Documents/Obsidian/Vault"
      }
    }
  }
}
```

### Running

```bash
# Run directly
python -m stm_server.server

# Or use the installed command
stm-server
```

## MCP Tools

### Core Tools

#### `save_memory`
Save a new memory to short-term storage.

```json
{
  "content": "Important information to remember",
  "tags": ["project", "idea"],
  "entities": ["project-x", "john-smith"],
  "source": "meeting notes",
  "context": "Discussion about Q4 planning"
}
```

#### `search_memory`
Search for memories with filtering and scoring.

```json
{
  "query": "project ideas",
  "tags": ["project"],
  "top_k": 10,
  "window_days": 7,
  "min_score": 0.1,
  "use_embeddings": false
}
```

#### `touch_memory`
Reinforce a memory by updating its access time and use count.

```json
{
  "memory_id": "abc-123",
  "boost_strength": true
}
```

### Graph Tools

#### `read_graph`
Get the entire knowledge graph of memories and relations.

```json
{
  "status": "active",
  "include_scores": true,
  "limit": 100
}
```

#### `open_memories`
Retrieve specific memories by ID with their relations.

```json
{
  "memory_ids": ["abc-123", "def-456"],
  "include_relations": true
}
```

#### `create_relation`
Create an explicit link between two memories.

```json
{
  "from_memory_id": "abc-123",
  "to_memory_id": "def-456",
  "relation_type": "references",
  "strength": 0.9
}
```

### Management Tools

#### `gc`
Garbage collect low-scoring memories.

```json
{
  "dry_run": true,
  "archive_instead": false,
  "limit": 100
}
```

#### `promote_memory`
Promote high-value memories to long-term storage.

```json
{
  "auto_detect": true,
  "dry_run": false,
  "target": "obsidian"
}
```

#### `cluster_memories`
Find similar memories for consolidation.

```json
{
  "strategy": "similarity",
  "threshold": 0.83,
  "find_duplicates": true
}
```

## Architecture

### Memory Lifecycle

1. **Create**: Memory saved with `use_count=0`, `strength=1.0`
2. **Access**: Each access increments `use_count`, updates `last_used`
3. **Decay**: Score decays exponentially: `score = (use_count^β) * exp(-λ * time_delta) * strength`
4. **Promotion**: High-scoring memories promoted to Obsidian vault
5. **Garbage Collection**: Low-scoring memories are forgotten

### Decay Formula

```
score = (use_count ^ beta) * exp(-lambda * (now - last_used)) * strength
```

Where:
- `lambda`: Decay constant (default: ln(2)/(3*86400) for 3-day half-life)
- `beta`: Use count weight (default: 0.6)
- `strength`: Base multiplier (default: 1.0, max: 2.0)

### Thresholds

- **Forget**: `score < 0.05` → memory is deleted
- **Promote**: `score >= 0.65` OR `use_count >= 5` within 14 days → promoted to long-term

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=stm_server --cov-report=html
```

### Type Checking

```bash
mypy src/stm_server
```

### Linting

```bash
ruff check src/stm_server
ruff format src/stm_server
```

## Project Structure

```
stm-server/
├── src/stm_server/
│   ├── core/           # Decay, scoring, clustering logic
│   ├── storage/        # Database and data models
│   ├── tools/          # MCP tool implementations
│   ├── integration/    # External integrations (Basic Memory)
│   ├── config.py       # Configuration management
│   └── server.py       # MCP server entry point
├── tests/              # Test suite
├── docs/               # Additional documentation
├── pyproject.toml      # Project configuration
└── .env.example        # Configuration template
```

## Integration with Basic Memory

STM Server is designed to work alongside [Basic Memory](https://github.com/coleam00/basic-memory) for a complete memory system:

- **STM**: Ephemeral, working memory with temporal decay
- **Basic Memory**: Permanent knowledge graph in Obsidian

High-value memories are automatically promoted from STM to Basic Memory's vault.

## License

MIT

## Related Projects

- [Model Context Protocol](https://github.com/modelcontextprotocol)
- [Basic Memory MCP](https://github.com/coleam00/basic-memory)
- [MCP Servers](https://github.com/modelcontextprotocol/servers)
