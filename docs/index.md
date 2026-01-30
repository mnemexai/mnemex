# CortexGraph

**Memory persistence for AI assistants with temporal decay**

[![Tests](https://github.com/prefrontal-systems/cortexgraph/actions/workflows/tests.yml/badge.svg)](https://github.com/prefrontal-systems/cortexgraph/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/prefrontal-systems/cortexgraph/branch/main/graph/badge.svg)](https://codecov.io/gh/prefrontal-systems/cortexgraph)
[![Security](https://github.com/prefrontal-systems/cortexgraph/actions/workflows/security.yml/badge.svg)](https://github.com/prefrontal-systems/cortexgraph/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What is CortexGraph?

CortexGraph is a **Model Context Protocol (MCP)** server that gives AI assistants like Claude a memory system with:

- **Short-term memory (STM)** with temporal decay (like human working memory)
- **Long-term memory (LTM)** for permanent storage in Obsidian-compatible Markdown
- **Knowledge graph** with entities, relations, and context tracking
- **Natural language activation** (v0.6.0+) - Conversational memory without explicit commands
- **Smart consolidation** to merge related memories
- **13 MCP tools** and **7 CLI commands**

### Why CortexGraph?

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
uv tool install git+https://github.com/prefrontal-systems/cortexgraph.git
```

### Configuration

Create `~/.config/cortexgraph/.env`:

```bash
# Storage
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl

# Decay model (power_law | exponential | two_component)
CORTEXGRAPH_DECAY_MODEL=power_law
CORTEXGRAPH_PL_HALFLIFE_DAYS=3.0

# Long-term memory
LTM_VAULT_PATH=~/Documents/Obsidian/Vault
```

### Claude Desktop Setup

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "/Users/yourusername/.local/bin/cortexgraph"
    }
  }
}
```

**Find your path:**
```bash
which cortexgraph
```

Use the full path from that command. GUI apps don't see shell PATH, so absolute paths work best.

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

### 🧩 Modular Architecture (v1.2.0+)

Clean separation of concerns:

- **cortexgraph.core**: Similarity, clustering, decay, search validation
- **cortexgraph.agents**: Consolidation pipeline with storage utilities
- **cortexgraph.storage**: JSONL/SQLite backends with batch operations
- **cortexgraph.tools**: MCP tool implementations

### 💬 Natural Language Activation (v0.6.0+)

Conversational memory without explicit commands:

- **Auto-enrichment**: Automatic entity extraction and importance scoring
- **Phrase detection**: "remember this", "what did I say about"
- **Decision support**: Tools help Claude decide when to save/recall
- **70-80% reliability**: Realistic MCP architecture ceiling

## Documentation

- [Architecture](architecture.md) - System design and components
- [API Reference](api.md) - All 13 MCP tools documented (v0.6.0+)
- [Knowledge Graph](graph_features.md) - Entity and relation system
- [Scoring Algorithm](scoring_algorithm.md) - How temporal decay works
- [Natural Language Activation](conversational-activation-plan.md) - Phase 1 implementation guide
- [Deployment Guide](deployment.md) - Production setup

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE.md) for details.

## Status

✅ **v1.2.0 Released** (2026-01-30)

See [ROADMAP.md](ROADMAP.md) for upcoming features.
