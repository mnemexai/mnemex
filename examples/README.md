# Mnemex Examples

## Installation

**Recommended: UV Tool Install**
```bash
uv tool install git+https://github.com/simplemindedbot/cortexgraph.git
```

This installs `cortexgraph` and all CLI commands. Configuration goes in `~/.config/cortexgraph/.env`.

## Configuration Files

### `claude_desktop_config.json`

This shows the **minimal** Claude Desktop configuration needed after installing via `uv tool install`. Copy this to:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

That's it! Just `{"command": "cortexgraph"}` - no paths, no environment variables.

**For development (editable install)**, use:
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

### All Other Configuration

**All configuration goes in `~/.config/cortexgraph/.env`**, not in the Claude config:

```bash
# Storage paths
MNEMEX_STORAGE_PATH=~/.config/cortexgraph/jsonl
LTM_VAULT_PATH=~/Documents/Obsidian/Vault

# Decay model and parameters
MNEMEX_DECAY_MODEL=power_law
MNEMEX_PL_ALPHA=1.1
MNEMEX_PL_HALFLIFE_DAYS=3.0
MNEMEX_DECAY_BETA=0.6

# Thresholds
MNEMEX_FORGET_THRESHOLD=0.05
MNEMEX_PROMOTE_THRESHOLD=0.65

# Optional
MNEMEX_ENABLE_EMBEDDINGS=false
LOG_LEVEL=INFO
```

See `.env.example` at the repository root for a complete configuration template.

## Why This Split?

- **Claude Desktop config**: Minimal - just tells Claude how to run the server
- **`.env` file**: All the server settings - decay rates, paths, thresholds, etc.

This keeps your Claude config clean and makes it easy to tune the server behavior without editing Claude's config file.

## Usage Examples

See `usage_example.md` for detailed examples of using the MCP tools to save, search, and manage memories.
