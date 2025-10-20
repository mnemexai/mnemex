# Mnemex: Temporal Memory for AI

A Model Context Protocol (MCP) server providing **human-like memory dynamics** for AI assistants. Memories naturally fade over time unless reinforced through use, mimicking the [Ebbinghaus forgetting curve](https://en.wikipedia.org/wiki/Forgetting_curve).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/simplemindedbot/mnemex/actions/workflows/tests.yml/badge.svg)](https://github.com/simplemindedbot/mnemex/actions/workflows/tests.yml)
[![Security Scanning](https://github.com/simplemindedbot/mnemex/actions/workflows/security.yml/badge.svg)](https://github.com/simplemindedbot/mnemex/actions/workflows/security.yml)
[![codecov](https://codecov.io/gh/simplemindedbot/mnemex/branch/main/graph/badge.svg)](https://codecov.io/gh/simplemindedbot/mnemex)
[![SBOM: CycloneDX](https://img.shields.io/badge/SBOM-CycloneDX-blue)](https://github.com/simplemindedbot/mnemex/actions/workflows/security.yml)

> [!WARNING]
> **🚧 ACTIVE DEVELOPMENT - EXPECT BUGS 🚧**
>
> This project is under active development and should be considered **experimental**. You will likely encounter bugs, breaking changes, and incomplete features. Use at your own risk. Please report issues on GitHub, but understand that this is research code, not production-ready software.
>
> **Known issues:**
> - API may change without notice between versions
> - Test coverage is incomplete

> **📖 New to this project?** Start with the [ELI5 Guide](ELI5.md) for a simple explanation of what this does and how to use it.

## Overview

This repository contains research, design, and a complete implementation of a short-term memory system that combines:

- **Novel temporal decay algorithm** based on cognitive science
- **Reinforcement learning** through usage patterns
- **Two-layer architecture** (STM + LTM) for working and permanent memory
- **Smart prompting patterns** for natural LLM integration
- **Git-friendly storage** with human-readable JSONL
- **Knowledge graph** with entities and relations

## Why Mnemex?

### 🔒 Privacy & Transparency

**All data stored locally on your machine** - no cloud services, no tracking, no data sharing.

- **Short-term memory**: Human-readable JSONL files (`~/.config/mnemex/jsonl/`)
  - One JSON object per line
  - Easy to inspect, version control, and backup
  - Git-friendly format for tracking changes

- **Long-term memory**: Markdown files optimized for Obsidian
  - YAML frontmatter with metadata
  - Wikilinks for connections
  - Permanent storage you control

You own your data. You can read it, edit it, delete it, or version control it - all without any special tools.

## Core Algorithm

The temporal decay scoring function:

$$
\Large \text{score}(t) = (n_{\text{use}})^\beta \cdot e^{-\lambda \cdot \Delta t} \cdot s
$$

Where:

- $\large n_{\text{use}}$ - Use count (number of accesses)
- $\large \beta$ (beta) - Sub-linear use count weighting (default: 0.6)
- $\large \lambda = \frac{\ln(2)}{t_{1/2}}$ (lambda) - Decay constant; set via half-life (default: 3-day)
- $\large \Delta t$ - Time since last access (seconds)
- $\large s$ - Strength parameter $\in [0, 2]$ (importance multiplier)

Thresholds:

- $\large \tau_{\text{forget}}$ (default 0.05) — if score < this, forget
- $\large \tau_{\text{promote}}$ (default 0.65) — if score ≥ this, promote (or if $\large n_{\text{use}}\ge5$ in 14 days)

Decay Models:

- Power‑Law (default): heavier tail; most human‑like retention
- Exponential: lighter tail; forgets sooner
- Two‑Component: fast early forgetting + heavier tail

See detailed parameter reference, model selection, and worked examples in docs/scoring_algorithm.md.

## Tuning Cheat Sheet

- Balanced (default)
  - Half-life: 3 days (λ ≈ 2.67e-6)
  - β = 0.6, τ_forget = 0.05, τ_promote = 0.65, use_count≥5 in 14d
  - Strength: 1.0 (bump to 1.3–2.0 for critical)
- High‑velocity context (ephemeral notes, rapid switching)
  - Half-life: 12–24 hours (λ ≈ 1.60e-5 to 8.02e-6)
  - β = 0.8–0.9, τ_forget = 0.10–0.15, τ_promote = 0.70–0.75
- Long retention (research/archival)
  - Half-life: 7–14 days (λ ≈ 1.15e-6 to 5.73e-7)
  - β = 0.3–0.5, τ_forget = 0.02–0.05, τ_promote = 0.50–0.60
- Preference/decision heavy assistants
  - Half-life: 3–7 days; β = 0.6–0.8
  - Strength defaults: 1.3–1.5 for preferences; 1.8–2.0 for decisions
- Aggressive space control
  - Raise τ_forget to 0.08–0.12 and/or shorten half-life; schedule weekly GC
- Environment template
  - MNEMEX_DECAY_LAMBDA=2.673e-6, MNEMEX_DECAY_BETA=0.6
  - MNEMEX_FORGET_THRESHOLD=0.05, MNEMEX_PROMOTE_THRESHOLD=0.65
  - MNEMEX_PROMOTE_USE_COUNT=5, MNEMEX_PROMOTE_TIME_WINDOW=14

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

### 3. Natural Spaced Repetition

Inspired by how concepts naturally reinforce across different contexts (the "Maslow effect" - remembering Maslow's hierarchy better when it appears in history, economics, and sociology classes).

**No flashcards. No explicit review sessions. Just natural conversation.**

**How it works:**

1. **Review Priority Calculation** - Memories in the "danger zone" (0.15-0.35 decay score) get highest priority
2. **Cross-Domain Detection** - Detects when memories are used in different contexts (tag Jaccard similarity <30%)
3. **Automatic Reinforcement** - Memories strengthen naturally when used, especially across domains
4. **Blended Search** - Review candidates appear in 30% of search results (configurable)

**Usage pattern:**

```
User: "Can you help with authentication in my API?"
→ System searches, retrieves JWT preference memory
→ System uses memory to answer question
→ System calls observe_memory_usage with context tags [api, auth, backend]
→ Cross-domain usage detected (original tags: [security, jwt, preferences])
→ Memory automatically reinforced, strength boosted
→ Next search naturally surfaces memories needing review
```

**Configuration:**

```bash
MNEMEX_REVIEW_BLEND_RATIO=0.3           # 30% review candidates in search
MNEMEX_REVIEW_DANGER_ZONE_MIN=0.15      # Lower bound of danger zone
MNEMEX_REVIEW_DANGER_ZONE_MAX=0.35      # Upper bound of danger zone
MNEMEX_AUTO_REINFORCE=true              # Auto-reinforce on observe
```

See `docs/prompts/` for LLM system prompt templates that enable natural memory usage.

### 4. Two-Layer Architecture

```
┌─────────────────────────────────────┐
│   Short-term memory                 │
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
mnemex/
├── README.md                          # This file
├── CLAUDE.md                          # Guide for AI assistants
├── src/mnemex/
│   ├── core/                          # Decay, scoring, clustering
│   ├── storage/                       # JSONL and LTM index
│   ├── tools/                         # 11 MCP tools
│   ├── backup/                        # Git integration
│   └── vault/                         # Obsidian integration
├── docs/
│   ├── scoring_algorithm.md           # Mathematical details
│   ├── prompts/                       # Smart prompting patterns
│   ├── architecture.md                # System design
│   └── api.md                         # Tool reference
├── tests/                             # Test suite
├── examples/                          # Usage examples
└── pyproject.toml                     # Project configuration
```

## Quick Start

### Installation

**Recommended: UV Tool Install**

```bash
# Install from GitHub (recommended)
uv tool install git+https://github.com/simplemindedbot/mnemex.git

# Or install from local directory (for development)
uv tool install .
```

This installs `mnemex` and all 7 CLI commands as isolated tools.

**Alternative: Editable Install (for development)**

```bash
# Clone and install in editable mode
git clone https://github.com/simplemindedbot/mnemex.git
cd mnemex
uv pip install -e ".[dev]"
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Storage
MNEMEX_STORAGE_PATH=~/.config/mnemex/jsonl

# Decay model (power_law | exponential | two_component)
MNEMEX_DECAY_MODEL=power_law

# Power-law parameters (default model)
MNEMEX_PL_ALPHA=1.1
MNEMEX_PL_HALFLIFE_DAYS=3.0

# Exponential (if selected)
# MNEMEX_DECAY_LAMBDA=2.673e-6  # 3-day half-life

# Two-component (if selected)
# MNEMEX_TC_LAMBDA_FAST=1.603e-5  # ~12h
# MNEMEX_TC_LAMBDA_SLOW=1.147e-6  # ~7d
# MNEMEX_TC_WEIGHT_FAST=0.7

# Common parameters
MNEMEX_DECAY_LAMBDA=2.673e-6
MNEMEX_DECAY_BETA=0.6

# Thresholds
MNEMEX_FORGET_THRESHOLD=0.05
MNEMEX_PROMOTE_THRESHOLD=0.65

# Long-term memory (optional)
LTM_VAULT_PATH=~/Documents/Obsidian/Vault
```

### MCP Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mnemex": {
      "command": "mnemex"
    }
  }
}
```

That's it! No paths, no environment variables needed.

**For development (editable install):**

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

**Configuration:**
- Storage paths are configured in `~/.config/mnemex/.env` or project `.env`
- See `.env.example` for all available settings

### Maintenance

Use the maintenance CLI to inspect and compact JSONL storage:

```bash
# Show storage stats (active counts, file sizes, compaction hints)
mnemex-maintenance stats

# Compact JSONL (rewrite without tombstones/duplicates)
mnemex-maintenance compact
```

### Migrating to UV Tool Install

If you're currently using an editable install (`uv pip install -e .`), you can switch to the simpler UV tool install:

```bash
# 1. Uninstall editable version
uv pip uninstall mnemex

# 2. Install as UV tool
uv tool install git+https://github.com/simplemindedbot/mnemex.git

# 3. Update Claude Desktop config to just:
#    {"command": "mnemex"}
#    Remove the --directory, run, and PYTHONPATH settings
```

**Your data is safe!** This only changes how the command is installed. Your memories in `~/.config/mnemex/` are untouched.

### Migrating from STM Server

If you previously used this project as "STM Server", use the migration tool:

```bash
# Preview what will be migrated
mnemex-migrate --dry-run

# Migrate data files from ~/.stm/ to ~/.config/mnemex/
mnemex-migrate --data-only

# Also migrate .env file (rename STM_* variables to MNEMEX_*)
mnemex-migrate --migrate-env --env-path ./.env
```

The migration tool will:
- Copy JSONL files from `~/.stm/jsonl/` to `~/.config/mnemex/jsonl/`
- Optionally rename environment variables (STM_* → MNEMEX_*)
- Create backups before making changes
- Provide clear next-step instructions

After migration, update your Claude Desktop config to use `mnemex` instead of `stm`.

## CLI Commands

The server includes 7 command-line tools:

```bash
mnemex                  # Run MCP server
mnemex-migrate          # Migrate from old STM setup
mnemex-index-ltm        # Index Obsidian vault
mnemex-backup           # Git backup operations
mnemex-vault            # Vault markdown operations
mnemex-search           # Unified STM+LTM search
mnemex-maintenance      # JSONL storage stats and compaction
```

## MCP Tools

11 tools for AI assistants to manage memories:

| Tool | Purpose |
|------|---------|
| `save_memory` | Save new memory with tags, entities |
| `search_memory` | Search with filters and scoring (includes review candidates) |
| `search_unified` | Unified search across STM + LTM |
| `touch_memory` | Reinforce memory (boost strength) |
| `observe_memory_usage` | Record memory usage for natural spaced repetition |
| `gc` | Garbage collect low-scoring memories |
| `promote_memory` | Move to long-term storage |
| `cluster_memories` | Find similar memories |
| `consolidate_memories` | Merge similar memories (algorithmic) |
| `read_graph` | Get entire knowledge graph |
| `open_memories` | Retrieve specific memories |
| `create_relation` | Link memories explicitly |

### Example: Unified Search

Search across STM and LTM with the CLI:

```bash
mnemex-search "typescript preferences" --tags preferences --limit 5 --verbose
```

### Example: Reinforce (Touch) Memory

Boost a memory's recency/use count to slow decay:

```json
{
  "memory_id": "mem-123",
  "boost_strength": true
}
```

Sample response:

```json
{
  "success": true,
  "memory_id": "mem-123",
  "old_score": 0.41,
  "new_score": 0.78,
  "use_count": 5,
  "strength": 1.1
}
```

### Example: Promote Memory

Suggest and promote high-value memories to the Obsidian vault.

Auto-detect (dry run):

```json
{
  "auto_detect": true,
  "dry_run": true
}
```

Promote a specific memory:

```json
{
  "memory_id": "mem-123",
  "dry_run": false,
  "target": "obsidian"
}
```

As an MCP tool (request body):

```json
{
  "query": "typescript preferences",
  "tags": ["preferences"],
  "limit": 5,
  "verbose": true
}
```

### Example: Consolidate Similar Memories

Find and merge duplicate or highly similar memories to reduce clutter:

Auto-detect candidates (preview):

```json
{
  "auto_detect": true,
  "mode": "preview",
  "cohesion_threshold": 0.75
}
```

Apply consolidation to detected clusters:

```json
{
  "auto_detect": true,
  "mode": "apply",
  "cohesion_threshold": 0.80
}
```

The tool will:
- Merge content intelligently (preserving unique information)
- Combine tags and entities (union)
- Calculate strength based on cluster cohesion
- Preserve earliest `created_at` and latest `last_used` timestamps
- Create tracking relations showing consolidation history

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

- **[Scoring Algorithm](docs/scoring_algorithm.md)** - Complete mathematical model with LaTeX formulas
- **[Smart Prompting](docs/prompts/memory_system_prompt.md)** - Patterns for natural LLM integration
- **[Architecture](docs/architecture.md)** - System design and implementation
- **[API Reference](docs/api.md)** - MCP tool documentation
- **[Bear Integration](docs/bear-integration.md)** - Guide to using Bear app as an LTM store
- **[Graph Features](docs/graph_features.md)** - Knowledge graph usage

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

### Knowledge & Memory
*   [mem0ai/mem0-mcp](https://github.com/mem0ai/mem0-mcp) (Python) - A MCP server that provides a smart memory for AI to manage and reference past conversations, user preferences, and key details.
*   [mnemex](https://github.com/simplemindedbot/mnemex) (Python) - A Python-based MCP server that provides a human-like short-term working memory (JSONL) and long-term memory (Markdown) system for AI assistants. The core of the project is a temporal decay algorithm that causes memories to fade over time unless they are reinforced through use.
*   [modelcontextprotocol/server-memory](https://github.com/modelcontextprotocol/server-memory) (TypeScript) - A knowledge graph-based persistent memory system for AI.

## Related Work

- [Model Context Protocol](https://github.com/modelcontextprotocol) - MCP specification
- [Ebbinghaus Forgetting Curve](https://en.wikipedia.org/wiki/Forgetting_curve) - Cognitive science foundation
- Research inspired by: Memoripy, Titan MCP, MemoryBank

## Citation

If you use this work in research, please cite:

```bibtex
@software{mnemex_2025,
  title = {Mnemex: Temporal Memory for AI},
  author = {simplemindedbot},
  year = {2025},
  url = {https://github.com/simplemindedbot/mnemex},
  version = {1.0.0}
}
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions.

### 🚨 **Help Needed: Windows & Linux Testers!**

I develop on macOS and need help testing on Windows and Linux. If you have access to these platforms, please:

- Try the installation instructions
- Run the test suite
- Report what works and what doesn't

See the [**Help Needed section**](CONTRIBUTING.md#-help-needed-windows--linux-testers) in CONTRIBUTING.md for details.

### General Contributions

For all contributors, see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Platform-specific setup (Windows, Linux, macOS)
- Development workflow
- Testing guidelines
- Code style requirements
- Pull request process

Quick start:

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for platform-specific setup
2. Understand the [Architecture docs](docs/architecture.md)
3. Review the [Scoring Algorithm](docs/scoring_algorithm.md)
4. Follow existing code patterns
5. Add tests for new features
6. Update documentation

## Status

**Version:** 1.0.0
**Status:** Research implementation - functional but evolving

### Phase 1 (Complete) ✅

- 10 MCP tools
- Temporal decay algorithm

- Knowledge graph

### Phase 2 (Complete) ✅

- JSONL storage
- LTM index
- Git integration
- Smart prompting documentation
- Maintenance CLI
- Memory consolidation (algorithmic merging)

### Future Work

- Spaced repetition optimization
- Adaptive decay parameters
- Performance benchmarks
- LLM-assisted consolidation (optional enhancement)

---

**Built with** [Claude Code](https://claude.com/claude-code) 🤖
