# Implementation Plan: Web-App Graph Visualization and Production Hardening

**Branch**: `001-webapp-graph-production-release` | **Date**: 2025-11-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-webapp-graph-production-release/spec.md`

## Summary

Enhance the CortexGraph web-app to display memory relationships and provide interactive graph visualization (similar to Obsidian/Logseq), then harden for production with comprehensive error handling, security measures, and supply chain verification for 1.0.0 release. A prerequisite spike will verify JSONL/SQLite backend relationship parity before visualization work begins.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastAPI (web framework), Uvicorn (ASGI server), Pydantic (models), existing CortexGraph core
**Frontend**: HTML/JavaScript (existing web-app in `src/cortexgraph/web/`)
**Storage**: JSONL (primary, `jsonl_storage.py`) and SQLite (`sqlite_storage.py`) with abstraction layer
**Testing**: pytest with pytest-asyncio, pytest-cov (≥90% coverage requirement)
**Target Platform**: Local desktop (macOS, Linux, Windows) - runs as localhost web server
**Project Type**: Single project with web component (backend + embedded frontend)
**Performance Goals**: <100ms save, <200ms search, <3s graph load for 10k memories, <100ms interaction latency
**Constraints**: <500ms p95 for graph operations with 1000+ nodes, storage-agnostic relationship queries
**Scale/Scope**: Up to 10,000 memories, local single-user deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Based on the CortexGraph constitution (v1.0.0), this feature must satisfy:

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Code Quality Standards** | Type hints on all public functions, mypy pass, ruff pass, docstrings on public APIs | ✅ Will comply |
| **II. Testing Standards** | ≥90% coverage, tests/unit + tests/integration + tests/contract structure, test isolation | ✅ Will comply |
| **III. UX Consistency** | Consistent MCP tool responses, `cortexgraph-*` CLI pattern, actionable errors, backward compatibility | ✅ Will comply |
| **IV. Performance Requirements** | <100ms save, <200ms search, <1000ms read_graph, <100ms web-app interaction | ✅ Will comply |

**Quality Gates Required**:

- [ ] Tests Pass (100%)
- [ ] Coverage (≥90%)
- [ ] Type Check (mypy 0 errors)
- [ ] Lint (ruff 0 errors)
- [ ] Format (ruff format)
- [ ] Security (bandit no high/critical)

## Project Structure

### Documentation (this feature)

```text
specs/001-webapp-graph-production-release/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API schemas)
├── checklists/          # Validation checklists
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/cortexgraph/
├── core/                # Decay, scoring, clustering algorithms
├── storage/             # JSONL and SQLite storage backends
│   ├── jsonl_storage.py
│   ├── sqlite_storage.py
│   └── models.py        # Memory, Relation Pydantic models
├── tools/               # MCP tool implementations
├── web/                 # Web application (FastAPI + frontend)
│   ├── api.py           # API endpoints (enhance for relationships)
│   ├── app.py           # FastAPI app setup
│   └── static/          # Frontend assets (add graph visualization)
├── security/            # Security utilities (enhance for hardening)
├── vault/               # Obsidian markdown writer
└── server.py            # MCP server entry point

tests/
├── unit/                # Isolated function tests
├── integration/         # Storage, web-app, MCP tests
└── contract/            # API contract validation
```

**Structure Decision**: Single project with web component. The existing `src/cortexgraph/web/` directory contains the FastAPI backend and embedded frontend. Graph visualization will be added as new frontend components, relationship display will extend existing API endpoints.

## Complexity Tracking

> No constitution violations requiring justification. Feature aligns with all principles.
