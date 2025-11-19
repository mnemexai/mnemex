# Configuration

CortexGraph is configured via environment variables, typically stored in `~/.config/cortexgraph/.env`.

## Configuration File

Create `~/.config/cortexgraph/.env`:

```bash
# ============================================
# Storage Configuration
# ============================================

# Where short-term memories are stored (JSONL format)
# Where short-term memories are stored (JSONL format)
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl

# Storage Backend (jsonl | sqlite)
CORTEXGRAPH_STORAGE_BACKEND=jsonl

# SQLite Database Path (optional, defaults to storage_path/cortexgraph.db)
# CORTEXGRAPH_SQLITE_PATH=~/.config/cortexgraph/cortexgraph.db

# ============================================
# Decay Model Configuration
# ============================================

# Decay model: power_law | exponential | two_component
CORTEXGRAPH_DECAY_MODEL=power_law

# Power-law model parameters
CORTEXGRAPH_PL_ALPHA=1.1                # Power exponent (higher = faster decay)
CORTEXGRAPH_PL_HALFLIFE_DAYS=3.0       # Half-life in days

# Exponential model parameters (if CORTEXGRAPH_DECAY_MODEL=exponential)
# CORTEXGRAPH_DECAY_LAMBDA=2.673e-6     # Decay constant

# Two-component model parameters (if CORTEXGRAPH_DECAY_MODEL=two_component)
# CORTEXGRAPH_TC_LAMBDA_FAST=1.603e-5   # Fast decay constant
# CORTEXGRAPH_TC_LAMBDA_SLOW=1.147e-6   # Slow decay constant
# CORTEXGRAPH_TC_WEIGHT_FAST=0.7        # Weight for fast component

# Use count exponent (affects reinforcement)
CORTEXGRAPH_DECAY_BETA=0.6

# ============================================
# Thresholds
# ============================================

# Forget threshold: delete memories with score < this
CORTEXGRAPH_FORGET_THRESHOLD=0.05

# Promote threshold: move to LTM if score >= this
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65

# ============================================
# Long-Term Memory (LTM)
# ============================================

# Obsidian vault path (for permanent storage)
LTM_VAULT_PATH=~/Documents/Obsidian/Vault

# LTM index path (for fast search)
LTM_INDEX_PATH=~/.config/cortexgraph/ltm_index.jsonl

# ============================================
# Git Backups
# ============================================

# Auto-commit changes to git
GIT_AUTO_COMMIT=true

# Commit interval in seconds (3600 = 1 hour)
GIT_COMMIT_INTERVAL=3600

# ============================================
# Embeddings (Optional)
# ============================================

# Enable semantic search with embeddings
CORTEXGRAPH_ENABLE_EMBEDDINGS=false

# Embedding model (if enabled)
CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2
```

## Configuration Options

### Decay Models

#### Power-Law (Recommended)

Most realistic model matching human memory:

```bash
CORTEXGRAPH_DECAY_MODEL=power_law
CORTEXGRAPH_PL_ALPHA=1.1
CORTEXGRAPH_PL_HALFLIFE_DAYS=3.0
```

- `CORTEXGRAPH_PL_ALPHA`: Power exponent (1.0-2.0, higher = faster decay)
- `CORTEXGRAPH_PL_HALFLIFE_DAYS`: Half-life in days

#### Exponential

Traditional time-based decay:

```bash
CORTEXGRAPH_DECAY_MODEL=exponential
CORTEXGRAPH_DECAY_LAMBDA=2.673e-6  # ln(2) / (3 days in seconds)
```

#### Two-Component

Combines fast and slow decay:

```bash
CORTEXGRAPH_DECAY_MODEL=two_component
CORTEXGRAPH_TC_LAMBDA_FAST=1.603e-5
CORTEXGRAPH_TC_LAMBDA_SLOW=1.147e-6
CORTEXGRAPH_TC_WEIGHT_FAST=0.7
```

### Thresholds

Control memory lifecycle:

- **Forget Threshold** (`CORTEXGRAPH_FORGET_THRESHOLD`): Delete if score < this
- **Promote Threshold** (`CORTEXGRAPH_PROMOTE_THRESHOLD`): Move to LTM if score >= this

Default values (0.05, 0.65) work well for most use cases.

### Storage Paths

- **STM**: `CORTEXGRAPH_STORAGE_PATH` - Directory for storage
- **LTM**: `LTM_VAULT_PATH` - Markdown files in Obsidian vault
- **Index**: `LTM_INDEX_PATH` - Fast search index for LTM

### Storage Backend

Choose between:
- **JSONL** (default): Human-readable, git-friendly text files. Best for transparency and small-to-medium datasets.
- **SQLite**: Binary database file. Best for performance with large datasets.

```bash
CORTEXGRAPH_STORAGE_BACKEND=sqlite
```

### Embeddings

Enable semantic similarity search:

```bash
CORTEXGRAPH_ENABLE_EMBEDDINGS=true
CORTEXGRAPH_EMBED_MODEL=all-MiniLM-L6-v2
```

Requires additional dependencies:
```bash
uv pip install sentence-transformers
```

## MCP Server Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "cortexgraph"
    }
  }
}
```

On Windows: `%APPDATA%\Claude\claude_desktop_config.json`

On Linux: `~/.config/Claude/claude_desktop_config.json`

### Development Mode

For development/testing:

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/cortexgraph", "run", "cortexgraph"],
      "env": {"PYTHONPATH": "/absolute/path/to/cortexgraph/src"}
    }
  }
}
```

## Verification

Check configuration:

```bash
# View current config
cat ~/.config/cortexgraph/.env

# Test MCP server
cortexgraph

# Check storage
ls -la ~/.config/cortexgraph/jsonl/
```

## Next Steps

- [Quick Start](quickstart.md) - Start using CortexGraph with Claude
- [API Reference](api.md) - Learn about available tools
