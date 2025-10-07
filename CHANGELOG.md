# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-10-07

### Added
- Decay models: power-law (default), exponential, and two-component with configurable parameters.
- Unified search surfaced as an MCP tool (`search_unified`) alongside the CLI (`stm-search`).
- Maintenance CLI (`stm-maintenance`) to show JSONL storage stats and compact files.
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

