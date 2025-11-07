# Installation

## Requirements

- **Python**: 3.10 or higher
- **UV**: Modern Python package installer (recommended)
- **Git**: For cloning the repository

## Recommended: UV Tool Install

The simplest installation method uses UV's tool install feature:

```bash
uv tool install git+https://github.com/simplemindedbot/cortexgraph.git
```

This installs all 7 CLI commands:
- `cortexgraph` - MCP server
- `cortexgraph-search` - Unified search across STM + LTM
- `cortexgraph-maintenance` - Stats and compaction
- `cortexgraph-migrate` - Migration from old STM Server
- `cortexgraph-consolidate` - Memory consolidation tool
- `cortexgraph-gc` - Garbage collection
- `cortexgraph-promote` - Promote memories to LTM

## Alternative: Development Install

For contributors who want to modify the code:

```bash
# Clone repository
git clone https://github.com/simplemindedbot/cortexgraph.git
cd cortexgraph

# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Development Install with MCP

For development, configure Claude Desktop with:

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

## Verify Installation

Check that all commands are available:

```bash
cortexgraph --version
cortexgraph-search --help
cortexgraph-maintenance --help
```

## Next Steps

- [Configuration](configuration.md) - Set up your memory system
- [Quick Start](quickstart.md) - Get started with Claude
