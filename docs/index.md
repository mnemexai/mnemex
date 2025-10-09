# Mnemex

**Memory persistence for AI assistants with temporal decay**

[![Tests](https://github.com/simplemindedbot/mnemex/actions/workflows/tests.yml/badge.svg)](https://github.com/simplemindedbot/mnemex/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/simplemindedbot/mnemex/branch/main/graph/badge.svg)](https://codecov.io/gh/simplemindedbot/mnemex)
[![Security](https://github.com/simplemindedbot/mnemex/actions/workflows/security.yml/badge.svg)](https://github.com/simplemindedbot/mnemex/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What is Mnemex?

Mnemex is a **Model Context Protocol (MCP)** server that gives AI assistants like Claude a memory system with:

- **Short-term memory (STM)** with temporal decay (like human working memory)
- **Long-term memory (LTM)** for permanent storage in Obsidian-compatible Markdown
- **Knowledge graph** with entities, relations, and context tracking
- **Smart consolidation** to merge related memories
- **11 MCP tools** and **7 CLI commands**

### Why Mnemex?

🔒 **Privacy First**: All data stored locally on your machine - no cloud, no tracking, no data sharing

📁 **Human-Readable**:
- Short-term memory in JSONL format (one JSON object per line)
- Long-term memory in Markdown with YAML frontmatter
- Both formats are easy to inspect, edit, and version control

🎯 **Full Control**: Your memories, your files, your rules

## Quick Start

### Installation

```bash
# Recommended: UV tool install
uv tool install git+https://github.com/simplemindedbot/mnemex.git
```

### Configuration

Create `~/.config/mnemex/.env`:

```bash
# Storage
MNEMEX_STORAGE_PATH=~/.config/mnemex/jsonl

# Decay model (power_law | exponential | two_component)
MNEMEX_DECAY_MODEL=power_law
MNEMEX_PL_HALFLIFE_DAYS=3.0

# Long-term memory
LTM_VAULT_PATH=~/Documents/Obsidian/Vault
```

### Claude Desktop Setup

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mnemex": {
      "command": "mnemex"
    }
  }
}
```

Restart Claude Desktop and you're ready!

## Features

### 🧠 Temporal Decay

Memories fade over time unless reinforced through repeated access:

- **Power-law decay** (default): Realistic forgetting curve matching human memory
- **Exponential decay**: Traditional time-based forgetting
- **Two-component decay**: Fast + slow decay for short/long term

### 🔗 Knowledge Graph

Build a graph of connected concepts:

- **Entities**: People, projects, concepts
- **Relations**: Explicit links between memories
- **Context tracking**: Understand relationships over time

### 🤝 Smart Consolidation

Automatically detect and merge similar memories:

- **Duplicate detection**: Near-duplicates → keep longest
- **Content merging**: Related but distinct → combine with separation
- **Metadata preservation**: Tags, entities, timestamps all preserved
- **Audit trail**: Track consolidation history

### 📊 Unified Search

Search across both STM and LTM:

- **Temporal ranking**: Recent memories weighted higher
- **Semantic similarity**: Optional embedding-based search
- **Entity matching**: Find related concepts
- **Tag filtering**: Narrow results by category

## Documentation

- [Architecture](architecture.md) - System design and components
- [API Reference](api.md) - All 11 MCP tools documented
- [Knowledge Graph](graph_features.md) - Entity and relation system
- [Scoring Algorithm](scoring_algorithm.md) - How temporal decay works
- [Deployment Guide](deployment.md) - Production setup

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE.md) for details.

## Status

✅ **v1.0.0 Released** (2025-10-09)

See [ROADMAP.md](ROADMAP.md) for upcoming features.
