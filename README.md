# STM Research: Short-Term Memory with Temporal Decay

A Model Context Protocol (MCP) server providing **human-like memory dynamics** for AI assistants. Memories naturally fade over time unless reinforced through use, mimicking the [Ebbinghaus forgetting curve](https://en.wikipedia.org/wiki/Forgetting_curve).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Overview

This repository contains research, design, and a complete implementation of a short-term memory system that combines:

- **Novel temporal decay algorithm** based on cognitive science
- **Reinforcement learning** through usage patterns
- **Two-layer architecture** (STM + LTM) for working and permanent memory
- **Smart prompting patterns** for natural LLM integration
- **Git-friendly storage** with human-readable JSONL
- **Knowledge graph** with entities and relations

## Core Algorithm

The temporal decay scoring function:

$$
\text{score}(t) = (n_{\text{use}})^\beta \cdot e^{-\lambda \cdot \Delta t} \cdot s
$$

Where:
- $n_{\text{use}}$ - Use count (number of accesses)
- $\beta = 0.6$ - Sub-linear use count weighting (diminishing returns)
- $\lambda = \frac{\ln(2)}{t_{1/2}}$ - Decay constant (default: 3-day half-life)
- $\Delta t$ - Time since last access (seconds)
- $s$ - Strength parameter $\in [0, 2]$ (importance multiplier)

**Decision thresholds:**
- Forget: $\text{score} < 0.05$ → delete memory
- Promote: $\text{score} \geq 0.65$ OR $n_{\text{use}} \geq 5$ within 14 days → move to LTM

## Key Innovations

### 1. Temporal Decay with Reinforcement

Unlike traditional caching (TTL, LRU), memories are scored continuously based on:
- **Recency** - Exponential decay over time
- **Frequency** - Use count with sub-linear weighting
- **Importance** - Adjustable strength parameter

This creates memory dynamics that closely mimic human cognition.

### 2. Smart Prompting System

Patterns for making AI assistants use memory naturally:

**Auto-Save**
```
User: "I prefer TypeScript over JavaScript"
→ Automatically saved with tags: [preferences, typescript, programming]
```

**Auto-Recall**
```
User: "Can you help with another TypeScript project?"
→ Automatically retrieves preferences and conventions
```

**Auto-Reinforce**
```
User: "Yes, still using TypeScript"
→ Memory strength increased, decay slowed
```

No explicit memory commands needed - just natural conversation.

### 3. Two-Layer Architecture

```
┌─────────────────────────────────────┐
│   STM (Short-Term Memory)           │
│   - JSONL storage                   │
│   - Temporal decay                  │
│   - Hours to weeks retention        │
└──────────────┬──────────────────────┘
               │ Automatic promotion
               ↓
┌─────────────────────────────────────┐
│   LTM (Long-Term Memory)            │
│   - Markdown files (Obsidian)       │
│   - Permanent storage               │
│   - Git version control             │
└─────────────────────────────────────┘
```

## Project Structure

```
stm-research/
├── README.md                          # This file
├── CLAUDE.md                          # Guide for AI assistants
├── stm-server-research.md            # Original research notes
└── stm-server/                        # Implementation
    ├── src/stm_server/
    │   ├── core/                      # Decay, scoring, clustering
    │   ├── storage/                   # JSONL, SQLite, LTM index
    │   ├── tools/                     # 10 MCP tools
    │   ├── backup/                    # Git integration
    │   └── vault/                     # Obsidian integration
    ├── docs/
    │   ├── scoring_algorithm.md       # Mathematical details
    │   ├── prompts/                   # Smart prompting patterns
    │   ├── architecture.md            # System design
    │   └── api.md                     # Tool reference
    └── tests/                         # Test suite
```

## Quick Start

### Installation

```bash
cd stm-server

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Storage
STM_STORAGE_PATH=~/.stm/jsonl

# Decay parameters (3-day half-life)
STM_DECAY_LAMBDA=2.673e-6
STM_DECAY_BETA=0.6

# Thresholds
STM_FORGET_THRESHOLD=0.05
STM_PROMOTE_THRESHOLD=0.65

# Long-term memory (optional)
LTM_VAULT_PATH=~/Documents/Obsidian/Vault
```

### MCP Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "stm": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/stm-research/stm-server",
        "run",
        "stm-server"
      ],
      "env": {
        "STM_STORAGE_PATH": "~/.stm/jsonl",
        "LTM_VAULT_PATH": "~/Documents/Obsidian/Vault"
      }
    }
  }
}
```

## CLI Commands

The server includes 6 command-line tools:

```bash
stm-server           # Run MCP server
stm-migrate          # Migrate SQLite → JSONL
stm-index-ltm        # Index Obsidian vault
stm-backup           # Git backup operations
stm-vault            # Vault markdown operations
stm-search           # Unified STM+LTM search
```

## MCP Tools

10 tools for AI assistants to manage memories:

| Tool | Purpose |
|------|---------|
| `save_memory` | Save new memory with tags, entities |
| `search_memory` | Search with filters and scoring |
| `touch_memory` | Reinforce memory (boost strength) |
| `gc` | Garbage collect low-scoring memories |
| `promote_memory` | Move to long-term storage |
| `cluster_memories` | Find similar memories |
| `consolidate_memories` | Merge duplicates (LLM-driven) |
| `read_graph` | Get entire knowledge graph |
| `open_memories` | Retrieve specific memories |
| `create_relation` | Link memories explicitly |

## Mathematical Details

### Decay Curves

For a memory with $n_{\text{use}}=1$, $s=1.0$, and $\lambda = 2.673 \times 10^{-6}$ (3-day half-life):

| Time | Score | Status |
|------|-------|--------|
| 0 hours | 1.000 | Fresh |
| 12 hours | 0.917 | Active |
| 1 day | 0.841 | Active |
| 3 days | 0.500 | Half-life |
| 7 days | 0.210 | Decaying |
| 14 days | 0.044 | Near forget |
| 30 days | 0.001 | **Forgotten** |

### Use Count Impact

With $\beta = 0.6$ (sub-linear weighting):

| Use Count | Boost Factor |
|-----------|--------------|
| 1 | 1.0× |
| 5 | 2.6× |
| 10 | 4.0× |
| 50 | 11.4× |

Frequent access significantly extends retention.

## Documentation

- **[Scoring Algorithm](stm-server/docs/scoring_algorithm.md)** - Complete mathematical model with LaTeX formulas
- **[Smart Prompting](stm-server/docs/prompts/memory_system_prompt.md)** - Patterns for natural LLM integration
- **[Architecture](stm-server/docs/architecture.md)** - System design and implementation
- **[API Reference](stm-server/docs/api.md)** - MCP tool documentation
- **[Graph Features](stm-server/docs/graph_features.md)** - Knowledge graph usage

## Use Cases

### Personal Assistant (Balanced)
- 3-day half-life
- Remember preferences and decisions
- Auto-promote frequently referenced information

### Development Environment (Aggressive)
- 1-day half-life
- Fast context switching
- Aggressive forgetting of old context

### Research / Archival (Conservative)
- 14-day half-life
- Long retention
- Comprehensive knowledge preservation

## License

MIT License - See [LICENSE](LICENSE) for details.

Clean-room implementation. No AGPL dependencies.

## Related Work

- [Model Context Protocol](https://github.com/modelcontextprotocol) - MCP specification
- [Ebbinghaus Forgetting Curve](https://en.wikipedia.org/wiki/Forgetting_curve) - Cognitive science foundation
- Research inspired by: Memoripy, Titan MCP, MemoryBank

## Citation

If you use this work in research, please cite:

```bibtex
@software{stm_research_2025,
  title = {STM Research: Short-Term Memory with Temporal Decay},
  author = {simplemindedbot},
  year = {2025},
  url = {https://github.com/simplemindedbot/stm-research},
  version = {0.2.0}
}
```

## Contributing

This is a research project. Contributions welcome! Please:

1. Read the [Architecture docs](stm-server/docs/architecture.md)
2. Understand the [Scoring Algorithm](stm-server/docs/scoring_algorithm.md)
3. Follow existing code patterns
4. Add tests for new features
5. Update documentation

## Status

**Version:** 0.2.0
**Status:** Research implementation - functional but evolving

### Phase 1 (Complete) ✅
- 10 MCP tools
- Temporal decay algorithm
- SQLite storage
- Knowledge graph

### Phase 2 (Complete) ✅
- JSONL storage
- LTM index
- Git integration
- Smart prompting documentation
- Migration tools

### Future Work
- Spaced repetition optimization
- Adaptive decay parameters
- Enhanced clustering algorithms
- Performance benchmarks

---

**Built with** [Claude Code](https://claude.com/claude-code) 🤖
