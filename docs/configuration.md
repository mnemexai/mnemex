# Configuration

Mnemex is configured via environment variables, typically stored in `~/.config/mnemex/.env`.

## Configuration File

Create `~/.config/mnemex/.env`:

```bash
# ============================================
# Storage Configuration
# ============================================

# Where short-term memories are stored (JSONL format)
MNEMEX_STORAGE_PATH=~/.config/mnemex/jsonl

# ============================================
# Decay Model Configuration
# ============================================

# Decay model: power_law | exponential | two_component
MNEMEX_DECAY_MODEL=power_law

# Power-law model parameters
MNEMEX_PL_ALPHA=1.1                # Power exponent (higher = faster decay)
MNEMEX_PL_HALFLIFE_DAYS=3.0       # Half-life in days

# Exponential model parameters (if MNEMEX_DECAY_MODEL=exponential)
# MNEMEX_DECAY_LAMBDA=2.673e-6     # Decay constant

# Two-component model parameters (if MNEMEX_DECAY_MODEL=two_component)
# MNEMEX_TC_LAMBDA_FAST=1.603e-5   # Fast decay constant
# MNEMEX_TC_LAMBDA_SLOW=1.147e-6   # Slow decay constant
# MNEMEX_TC_WEIGHT_FAST=0.7        # Weight for fast component

# Use count exponent (affects reinforcement)
MNEMEX_DECAY_BETA=0.6

# ============================================
# Thresholds
# ============================================

# Forget threshold: delete memories with score < this
MNEMEX_FORGET_THRESHOLD=0.05

# Promote threshold: move to LTM if score >= this
MNEMEX_PROMOTE_THRESHOLD=0.65

# ============================================
# Long-Term Memory (LTM)
# ============================================

# Obsidian vault path (for permanent storage)
LTM_VAULT_PATH=~/Documents/Obsidian/Vault

# LTM index path (for fast search)
LTM_INDEX_PATH=~/.config/mnemex/ltm_index.jsonl

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
MNEMEX_ENABLE_EMBEDDINGS=false

# Embedding model (if enabled)
MNEMEX_EMBED_MODEL=all-MiniLM-L6-v2
```

## Configuration Options

### Decay Models

#### Power-Law (Recommended)

Most realistic model matching human memory:

```bash
MNEMEX_DECAY_MODEL=power_law
MNEMEX_PL_ALPHA=1.1
MNEMEX_PL_HALFLIFE_DAYS=3.0
```

- `MNEMEX_PL_ALPHA`: Power exponent (1.0-2.0, higher = faster decay)
- `MNEMEX_PL_HALFLIFE_DAYS`: Half-life in days

#### Exponential

Traditional time-based decay:

```bash
MNEMEX_DECAY_MODEL=exponential
MNEMEX_DECAY_LAMBDA=2.673e-6  # ln(2) / (3 days in seconds)
```

#### Two-Component

Combines fast and slow decay:

```bash
MNEMEX_DECAY_MODEL=two_component
MNEMEX_TC_LAMBDA_FAST=1.603e-5
MNEMEX_TC_LAMBDA_SLOW=1.147e-6
MNEMEX_TC_WEIGHT_FAST=0.7
```

### Thresholds

Control memory lifecycle:

- **Forget Threshold** (`MNEMEX_FORGET_THRESHOLD`): Delete if score < this
- **Promote Threshold** (`MNEMEX_PROMOTE_THRESHOLD`): Move to LTM if score >= this

Default values (0.05, 0.65) work well for most use cases.

### Storage Paths

- **STM**: `MNEMEX_STORAGE_PATH` - JSONL files for short-term memory
- **LTM**: `LTM_VAULT_PATH` - Markdown files in Obsidian vault
- **Index**: `LTM_INDEX_PATH` - Fast search index for LTM

### Embeddings

Enable semantic similarity search:

```bash
MNEMEX_ENABLE_EMBEDDINGS=true
MNEMEX_EMBED_MODEL=all-MiniLM-L6-v2
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
    "mnemex": {
      "command": "mnemex"
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
    "mnemex": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/mnemex", "run", "mnemex"],
      "env": {"PYTHONPATH": "/absolute/path/to/mnemex/src"}
    }
  }
}
```

## Verification

Check configuration:

```bash
# View current config
cat ~/.config/mnemex/.env

# Test MCP server
mnemex

# Check storage
ls -la ~/.config/mnemex/jsonl/
```

## Next Steps

- [Quick Start](quickstart.md) - Start using Mnemex with Claude
- [API Reference](api.md) - Learn about available tools
