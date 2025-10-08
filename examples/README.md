# STM Server Examples

## Configuration Files

### `claude_desktop_config.json`

This shows the **minimal** Claude Desktop configuration needed. Copy this to:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Important**: Replace `/Users/your-username/path/to/stm-research` with your actual repository path.

The only required environment variable in the Claude config is:
- `PYTHONPATH`: Points to the `src/` directory for module imports

### All Other Configuration

**All STM configuration goes in `.env` at the root of the repository**, not in the Claude config:

```bash
# Storage paths
STM_STORAGE_PATH=~/.stm/jsonl
LTM_VAULT_PATH=~/Documents/Obsidian/Vault

# Decay model and parameters
STM_DECAY_MODEL=power_law
STM_PL_ALPHA=1.1
STM_PL_HALFLIFE_DAYS=3.0
STM_DECAY_BETA=0.6

# Thresholds
STM_FORGET_THRESHOLD=0.05
STM_PROMOTE_THRESHOLD=0.65

# Optional
STM_ENABLE_EMBEDDINGS=false
LOG_LEVEL=INFO
```

See `.env.example` at the repository root for a complete configuration template.

## Why This Split?

- **Claude Desktop config**: Minimal - just tells Claude how to run the server
- **`.env` file**: All the server settings - decay rates, paths, thresholds, etc.

This keeps your Claude config clean and makes it easy to tune the server behavior without editing Claude's config file.

## Usage Examples

See `usage_example.md` for detailed examples of using the MCP tools to save, search, and manage memories.
