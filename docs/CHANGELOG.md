# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-09

🎉 **Production Release: Mnemex v1.0.0**

This is the first production-ready release of Mnemex (formerly STM Research/STM Server), a temporal memory management system for AI assistants with human-like memory dynamics.

### 🚀 Major Features

#### Complete Rebranding
- **Renamed from STM Research/STM Server to Mnemex**
  - Updated all references, paths, and documentation
  - Changed storage paths from `~/.stm/` to `~/.config/mnemex/` (XDG-compliant)
  - Updated command names from `stm-*` to `mnemex-*`
  - Updated environment variables from `STM_*` to `MNEMEX_*`
  - Repository moved to https://github.com/simplemindedbot/mnemex

#### Simplified Installation
- **UV Tool Install Support**
  - One-command installation: `uv tool install git+https://github.com/simplemindedbot/mnemex.git`
  - Simplified MCP configuration: `{"command": "mnemex"}` (no more complex paths)
  - All configuration moved to `~/.config/mnemex/.env` (not MCP config)
  - Automatic installation of all 7 CLI commands

#### Memory Consolidation
- **Algorithmic Memory Consolidation** (`consolidate_memories` tool)
  - Smart content merging with duplicate detection
  - Preview mode to see proposed merges before applying
  - Apply mode to execute consolidation
  - Auto-detection of high-cohesion clusters
  - Metadata merging: tags, entities, timestamps, strength
  - Relation tracking via `consolidated_from` links
  - Strength bonuses based on cluster cohesion (capped at 2.0)
  - 100% test coverage (15 tests)

#### Privacy & Local Storage
- **Emphasized Local-First Design**
  - All data stored locally (no cloud services, no tracking)
  - Human-readable JSONL format for short-term memory
  - Markdown files (Obsidian-compatible) for long-term memory
  - Git-friendly formats for version control
  - Complete user control and transparency

### 📦 Added

- Migration tool (`mnemex-migrate`) to upgrade from old STM Server installations
- Comprehensive contributing guide with platform-specific instructions
- Windows/Linux tester recruitment documentation
- Future roadmap documentation
- Privacy and local storage documentation sections
- ELI5 guide updates with simplified installation steps
- All AI assistant instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

### 🔄 Changed

- **Storage paths**: Migrated to XDG-compliant `~/.config/mnemex/`
- **Command names**: All CLI tools renamed from `stm-*` to `mnemex-*`
- **Configuration**: Simplified MCP setup, all settings in `.env` file
- **Installation**: UV tool install as recommended method
- **Documentation**: Complete overhaul across all files

### 🐛 Fixed

- `.env.example` updated with correct decay model parameters
- LTM index path configuration
- Python path requirements in documentation
- Server initialization using `mcp.run()` instead of deprecated `mcp.run_forever()`

### 📚 Documentation

- Complete documentation suite with consistent branding
- README.md: Quick start, installation, configuration
- CLAUDE.md: AI assistant instructions
- CONTRIBUTING.md: Development guide
- ELI5.md: Beginner-friendly explanation
- docs/deployment.md: Production deployment
- docs/architecture.md: System design
- docs/api.md: Tool reference
- docs/graph_features.md: Knowledge graph guide

### 🎯 Implementation Status

**11 MCP Tools Implemented:**
1. `save_memory` - Save memory with entities, tags, optional embeddings
2. `search_memory` - Search with temporal filtering and semantic similarity
3. `search_unified` - Unified search across STM and LTM
4. `touch_memory` - Reinforce memory (update last_used, use_count, strength)
5. `gc` - Garbage collect low-scoring memories
6. `promote_memory` - Promote high-value memories to long-term storage
7. `cluster_memories` - Find similar memories for consolidation
8. `consolidate_memories` - Algorithmic merge with preview/apply modes
9. `read_graph` - Return entire knowledge graph with memories and relations
10. `open_memories` - Retrieve specific memories by ID with relations
11. `create_relation` - Create explicit links between memories

**7 CLI Commands:**
- `mnemex` - MCP server
- `mnemex-migrate` - Migration from old installations
- `mnemex-search` - Unified search across STM and LTM
- `mnemex-maintenance` - Storage stats and compaction
- `mnemex-index-ltm` - Index Obsidian vault
- `mnemex-backup` - Git backup operations
- `mnemex-vault` - Markdown file operations

### 💡 Core Innovations

- **Temporal Decay**: Power-law (default), exponential, and two-component models
- **Reinforcement Learning**: Memories strengthen with repeated access
- **Smart Prompting**: Natural memory operations without explicit commands
- **Knowledge Graph**: Entities, relations, and memory nodes
- **Two-Layer Architecture**: STM (JSONL) + LTM (Markdown/Obsidian)

### 📄 License

MIT License - Full user control and transparency

---

## [0.3.0] - 2025-10-07

### Added
- **ELI5.md** - Simple, beginner-friendly guide explaining what this project does and how to use it.
- Decay models: power-law (default), exponential, and two-component with configurable parameters.
- Unified search surfaced as an MCP tool (`search_unified`) alongside the CLI (`mnemex-search`).
- Maintenance CLI (`mnemex-maintenance`) to show JSONL storage stats and compact files.
- Tests for decay models, LTM index parsing/search, and unified search merging.
- Deployment docs for decay model configuration and tuning tips.
- Tuning cheat sheet and model selection guidance in README and scoring docs.

### Changed
- JSONL-only storage: removed SQLite and migration tooling.
- Server logs now include the active decay model and key parameters on startup.
- Standardized on Ruff for linting and formatting.

### Removed
- SQLite database implementation and migration modules.

## [0.2.0] - 2025-01-07

- JSONL storage, LTM index, Git integration, and smart prompting docs.
