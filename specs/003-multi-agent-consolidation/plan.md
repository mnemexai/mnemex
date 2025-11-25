# Implementation Plan: Multi-Agent Memory Consolidation

**Branch**: `003-multi-agent-consolidation` | **Date**: 2025-11-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-multi-agent-consolidation/spec.md`

## Summary

Implement five specialized Python agent classes (Decay Analyzer, Cluster Detector, Semantic Merge, LTM Promoter, Relationship Discovery) that extend existing CortexGraph MCP tool logic and coordinate via beads issues. Agents run as single-process CLI commands with hybrid triggering (scheduled + event-driven for urgent items).

## Technical Context

**Language/Version**: Python 3.10+ (matches existing codebase)
**Primary Dependencies**: FastMCP (MCP framework), Pydantic (models), beads/bd CLI (coordination)
**Storage**: JSONL (`~/.config/cortexgraph/jsonl/`) for memories, beads SQLite (`.beads/beads.db`) for coordination
**Testing**: pytest, pytest-cov (90%+ coverage required), mypy, ruff
**Target Platform**: Local CLI (macOS/Linux)
**Project Type**: Single project (extending existing cortexgraph package)
**Performance Goals**: < 5 seconds per memory processed (SC-006)
**Constraints**: Rate limit 100 ops/minute, confidence thresholds for auto-processing
**Scale/Scope**: 10,000 memories typical workload

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality Standards | ✅ PASS | Type hints on all agents, Pydantic models for results |
| II. Testing Standards | ✅ PASS | Unit tests per agent, integration tests for pipeline, 90%+ coverage |
| III. UX Consistency | ✅ PASS | CLI follows `cortexgraph-consolidate [agent]` pattern |
| IV. Performance Requirements | ✅ PASS | 5s/memory aligns with existing targets |

**Quality Gates**:
- Tests Pass: Will include unit + integration tests
- Coverage: Target 90%+ for new `agents/` module
- Type Check: mypy strict on new code
- Lint: ruff check/format compliance
- Security: No credentials in code, beads handles local data only

**No violations requiring justification.** Design extends existing patterns.

## Project Structure

### Documentation (this feature)

```text
specs/003-multi-agent-consolidation/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── agent-api.md     # Agent interface contracts
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/cortexgraph/
├── agents/                    # NEW: Consolidation agents
│   ├── __init__.py
│   ├── base.py                # ConsolidationAgent base class
│   ├── decay_analyzer.py      # Decay Analyzer agent
│   ├── cluster_detector.py    # Cluster Detector agent
│   ├── semantic_merge.py      # Semantic Merge agent
│   ├── ltm_promoter.py        # LTM Promoter agent
│   ├── relationship_discovery.py  # Relationship Discovery agent
│   ├── scheduler.py           # Hybrid trigger scheduler
│   └── beads_integration.py   # Beads issue creation/query helpers
├── cli/
│   └── consolidate.py         # NEW: cortexgraph-consolidate CLI entry point
├── core/                      # EXISTING: Will be called by agents
│   ├── consolidation.py       # Existing merge logic (extend, not replace)
│   ├── clustering.py          # Existing similarity logic
│   ├── decay.py               # Existing decay scoring
│   ├── review.py              # Existing danger zone logic
│   └── scoring.py             # Existing score calculations
├── tools/                     # EXISTING: MCP tools remain unchanged
│   ├── cluster.py             # cluster_memories tool
│   ├── consolidate.py         # consolidate_memories tool
│   └── promote.py             # promote_memory tool
└── vault/                     # EXISTING: LTM markdown writing

tests/
├── unit/
│   └── agents/                # NEW: Agent unit tests
│       ├── test_base_agent.py
│       ├── test_decay_analyzer.py
│       ├── test_cluster_detector.py
│       ├── test_semantic_merge.py
│       ├── test_ltm_promoter.py
│       └── test_relationship_discovery.py
├── integration/
│   └── agents/                # NEW: Agent integration tests
│       ├── test_agent_pipeline.py
│       └── test_beads_coordination.py
└── contract/
    └── test_agent_api.py      # NEW: Agent API contracts
```

**Structure Decision**: Agents live in new `src/cortexgraph/agents/` module, following existing package organization. Agents import from `core/` to reuse tested logic. New CLI entry point `cortexgraph-consolidate` added alongside existing `cortexgraph`, `cortexgraph-search`, etc.

## Complexity Tracking

> **No violations requiring justification** - design follows existing patterns.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Agent model | Python classes | Simplest approach, matches clarification decision |
| Coordination | beads issues | Already in use for project tracking, proven stable |
| Scheduling | Hybrid | Balances responsiveness with simplicity |
| Tool reuse | Extend via imports | Reuses 100%-coverage tested code |
