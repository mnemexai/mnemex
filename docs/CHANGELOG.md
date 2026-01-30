# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-01-30

### Changed

- **Code Consolidation & Optimization** - Major internal refactoring for better maintainability
  - Extracted similarity functions into dedicated `cortexgraph.core.similarity` module
  - Consolidated search validation into `cortexgraph.core.search_common` module
  - Created `cortexgraph.core.text_utils` for shared text utilities
  - Created `cortexgraph.agents.storage_utils` for agent storage access
  - Refactored `search_unified.py` into smaller, testable functions (`_search_stm()`, `_search_ltm()`, `_deduplicate_results()`)
  - Reduced `clustering.py` from ~290 to ~110 lines

### Added

- **Batch Storage Operations** - Performance improvements for bulk operations
  - `JSONLStorage.create_relations_batch()` - Create multiple relations atomically
  - `JSONLStorage.delete_memories_batch()` - Delete multiple memories atomically
  - Consolidation now uses batch operations for faster execution

### Notes

- No breaking API changes - all existing imports continue to work
- New module exports available via `cortexgraph.core` and `cortexgraph.agents`

## [1.0.0] - 2025-10-09

🎉 **Production Release: CortexGraph v1.0.0**

This is the first production-ready release of CortexGraph (formerly CortexGraph), a temporal memory management system for AI assistants with human-like memory dynamics.

### 🚀 Major Features

#### Complete Rebranding
- **Renamed from CortexGraph to CortexGraph**
  - Updated all references, paths, and documentation
  - Changed storage paths from `~/.stm/` to `~/.config/cortexgraph/` (XDG-compliant)
  - Updated command names from `stm-*` to `cortexgraph-*`
  - Updated environment variables from CORTEXGRAPH_* to CORTEXGRAPH_*
  - Repository moved to https://github.com/prefrontal-systems/cortexgraph

#### Simplified Installation
- **UV Tool Install Support**
  - One-command installation: `uv tool install git+https://github.com/simplemindedbot/cortexgraph.git`
  - Simplified MCP configuration: `{"command": "cortexgraph"}` (no more complex paths)
  - All configuration moved to `~/.config/cortexgraph/.env` (not MCP config)
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

- Migration tool (`cortexgraph-migrate`) to upgrade from old STM Server installations
- Comprehensive contributing guide with platform-specific instructions
- Windows/Linux tester recruitment documentation
- Future roadmap documentation
- Privacy and local storage documentation sections
- ELI5 guide updates with simplified installation steps
- All AI assistant instruction files (CLAUDE.md, AGENTS.md, GEMINI.md)

### 🔄 Changed

- **Storage paths**: Migrated to XDG-compliant `~/.config/cortexgraph/`
- **Command names**: All CLI tools renamed from `stm-*` to `cortexgraph-*`
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
- `cortexgraph` - MCP server
- `cortexgraph-migrate` - Migration from old installations
- `cortexgraph-search` - Unified search across STM and LTM
- `cortexgraph-maintenance` - Storage stats and compaction
- `cortexgraph-index-ltm` - Index Obsidian vault
- `cortexgraph-backup` - Git backup operations
- `cortexgraph-vault` - Markdown file operations

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
- Unified search surfaced as an MCP tool (`search_unified`) alongside the CLI (`cortexgraph-search`).
- Maintenance CLI (`cortexgraph-maintenance`) to show JSONL storage stats and compact files.
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
