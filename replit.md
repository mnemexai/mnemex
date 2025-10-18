# Mnemex - Temporal Memory for AI

## Project Overview

Mnemex is a Model Context Protocol (MCP) server providing human-like memory dynamics for AI assistants. It implements temporal decay algorithms based on cognitive science, allowing memories to naturally fade over time unless reinforced through use.

### Key Features

- **Temporal decay algorithm** with reinforcement learning
- **Two-layer architecture** (short-term + long-term memory)
- **Knowledge graph** with entities and relations
- **Smart prompting patterns** for natural LLM integration
- **Git-friendly JSONL storage** for human-readable data
- **10 MCP tools** for memory management

## Project Structure

- `src/mnemex/` - Main Python package
  - `server.py` - MCP server entry point
  - `core/` - Decay, scoring, and clustering algorithms
  - `storage/` - JSONL and LTM index management
  - `tools/` - 10 MCP tools for memory operations
  - `backup/` - Git integration
  - `vault/` - Obsidian integration
- `tests/` - Test suite
- `docs/` - Documentation (algorithm details, API reference, guides)
- `examples/` - Usage examples

## Technology Stack

- **Language**: Python 3.10+
- **Framework**: Model Context Protocol (MCP)
- **Storage**: JSONL files (short-term), Markdown (long-term)
- **Dependencies**: pydantic, python-dotenv, GitPython, markdown, python-frontmatter

## Replit Setup

### Installed Components

1. **Python Dependencies** (via pip):
   - mcp >= 1.2.0
   - pydantic >= 2.0.0
   - python-dotenv >= 1.0.0
   - python-frontmatter >= 1.1.0
   - markdown >= 3.5.0
   - GitPython >= 3.1.40

2. **Workflow**: MCP Server
   - Command: `PYTHONPATH=/home/runner/workspace/src python -m mnemex.server`
   - Output: Console (this is a server/CLI tool, not a web app)

### Running the Server

The MCP server runs automatically via the configured workflow. It starts on project load and provides:

- 10 MCP tools for AI assistants
- JSONL storage at `~/.config/mnemex/jsonl/`
- Temporal decay with power-law model (3-day half-life)
- Memory scoring and automatic garbage collection

### Configuration

Configuration is managed through environment variables (see `.env.example`):

- **Decay Model**: `power_law` (default), `exponential`, or `two_component`
- **Storage Path**: `~/.config/mnemex/jsonl/` (default)
- **Embeddings**: Optional (disabled by default)
- **LTM Integration**: Obsidian vault path (optional)

### CLI Commands

The package provides 7 CLI commands:

- `mnemex` - Run MCP server
- `mnemex-migrate` - Migrate from old STM setup
- `mnemex-index-ltm` - Index Obsidian vault
- `mnemex-backup` - Git backup operations
- `mnemex-vault` - Vault markdown operations
- `mnemex-search` - Unified STM+LTM search
- `mnemex-maintenance` - JSONL storage stats and compaction

## Development Notes

### Code Fixes Applied

1. Fixed missing imports in `src/mnemex/performance.py`:
   - Added `Callable`, `ParamSpec`, `TypeVar` from typing module
   - Required for the `time_operation` decorator

2. Fixed Python 3.10 compatibility in MCP tools:
   - Added `from __future__ import annotations` to `save.py` and `search.py`
   - Enables modern type hint syntax (`X | None`)

### Testing

The server initializes successfully with:
- 0 initial memories (fresh install)
- Power-law decay model (α=1.1, half-life=3.0 days)
- 13 MCP tools registered
- Secured storage directory

## Usage

This is an MCP server designed to be used with AI assistants like Claude Desktop. To use:

1. Configure your MCP client to connect to the server
2. The server provides 10 tools for memory management
3. Memories are stored locally in JSONL format
4. Automatic temporal decay and promotion to long-term storage

See the main [README.md](README.md) for detailed documentation.

## Recent Changes

**2024-10-18**: Initial Replit setup
- Installed Python dependencies via pip
- Fixed compatibility issues for Python 3.10
- Configured MCP Server workflow
- Server running successfully

## License

MIT License - See [LICENSE](LICENSE) for details.
