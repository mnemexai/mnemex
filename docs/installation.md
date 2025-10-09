# Installation

## Requirements

- **Python**: 3.10 or higher
- **UV**: Modern Python package installer (recommended)
- **Git**: For cloning the repository

## Recommended: UV Tool Install

The simplest installation method uses UV's tool install feature:

```bash
uv tool install git+https://github.com/simplemindedbot/mnemex.git
```

This installs all 7 CLI commands:
- `mnemex` - MCP server
- `mnemex-search` - Unified search across STM + LTM
- `mnemex-maintenance` - Stats and compaction
- `mnemex-migrate` - Migration from old STM Server
- `mnemex-consolidate` - Memory consolidation tool
- `mnemex-gc` - Garbage collection
- `mnemex-promote` - Promote memories to LTM

## Alternative: Development Install

For contributors who want to modify the code:

```bash
# Clone repository
git clone https://github.com/simplemindedbot/mnemex.git
cd mnemex

# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Development Install with MCP

For development, configure Claude Desktop with:

```json
{
  "mcpServers": {
    "mnemex": {
      "command": "uv",
      "args": ["--directory", "/path/to/mnemex", "run", "mnemex"],
      "env": {"PYTHONPATH": "/path/to/mnemex/src"}
    }
  }
}
```

## Verify Installation

Check that all commands are available:

```bash
mnemex --version
mnemex-search --help
mnemex-maintenance --help
```

## Next Steps

- [Configuration](configuration.md) - Set up your memory system
- [Quick Start](quickstart.md) - Get started with Claude
