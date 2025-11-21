<!--
SYNC IMPACT REPORT
==================
Version change: N/A → 1.0.0 (initial ratification)
Modified principles: N/A (initial creation)
Added sections:
  - Core Principles (4): Code Quality, Testing Standards, UX Consistency, Performance Requirements
  - Quality Gates
  - Development Workflow
  - Governance

Templates requiring updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section compatible
  ✅ .specify/templates/spec-template.md - Success Criteria aligns with performance/UX principles
  ✅ .specify/templates/tasks-template.md - Test-first workflow compatible
  ✅ .specify/templates/checklist-template.md - No conflicts

Follow-up TODOs: None
-->

# CortexGraph Constitution

## Core Principles

### I. Code Quality Standards

All code in CortexGraph MUST meet these non-negotiable quality standards:

- **Type Safety**: All public functions and methods MUST have type hints. Pydantic models MUST be used for data structures crossing module boundaries. mypy MUST pass without errors on `src/cortexgraph/`.
- **Linting Compliance**: All code MUST pass ruff checks with zero errors. Formatting MUST use ruff format (line-length 100, target Python 3.10).
- **Import-Time Safety**: Modules MUST NOT create live resources (files, network connections, database handles) at import time. Global singletons MUST be behind getters or factories for testability.
- **Documentation**: Public APIs MUST have docstrings describing purpose, parameters, return values, and exceptions. Complex algorithms MUST include inline comments explaining non-obvious logic.

**Rationale**: CortexGraph is an MCP server handling user memories—a trust-critical application. Type safety and clean code prevent subtle bugs that could corrupt or lose user data.

### II. Testing Standards (NON-NEGOTIABLE)

Testing is mandatory and MUST follow these requirements:

- **Coverage Threshold**: Test coverage MUST remain at or above 90% for `src/cortexgraph/`. New features MUST have tests before merging. PRs that decrease coverage below 90% MUST be blocked.
- **Test Organization**: Tests MUST be organized by category:
  - `tests/unit/` - Isolated function/class tests (no I/O)
  - `tests/integration/` - Tests requiring storage, MCP protocol, or external systems
  - `tests/contract/` - API contract validation
- **Test Isolation**: Each test MUST be independent—no shared state between tests. Storage paths MUST be overridable for isolated test environments. Tests MUST clean up any resources they create.
- **Async Testing**: Async functions MUST be tested with `pytest-asyncio`. Use `asyncio_mode = "auto"` configuration.

**Rationale**: CortexGraph's temporal decay and memory consolidation algorithms are mathematically precise. Comprehensive tests are the only way to verify correctness across edge cases and decay models.

### III. User Experience Consistency

All user-facing interfaces MUST provide consistent, predictable experiences:

- **MCP Tool Interface**: All MCP tools MUST return structured responses with consistent field names. Error responses MUST include `error` field with human-readable message. Success responses MUST include `success: true` and relevant data.
- **CLI Interface**: All CLI commands MUST follow the pattern: `cortexgraph-<function>`. Commands MUST support `--help` with clear descriptions. Output MUST support both human-readable and JSON formats (where applicable).
- **Error Messages**: Errors MUST be actionable—tell users what went wrong AND how to fix it. Include relevant context (file paths, memory IDs, parameter values). Never expose raw stack traces to end users.
- **Backward Compatibility**: Existing tool interfaces MUST NOT break without major version bump. Deprecation MUST include migration guidance and minimum one minor version warning period.

**Rationale**: Users interact with CortexGraph through MCP tools and CLI commands. Inconsistent interfaces create friction and confusion, especially when memories are involved—users must trust the system.

### IV. Performance Requirements

Performance standards ensure CortexGraph remains responsive with growing memory stores:

- **Response Time Targets**:
  - `save_memory`: < 100ms p95
  - `search_memory` (without embeddings): < 200ms p95 for stores up to 10,000 memories
  - `search_memory` (with embeddings): < 500ms p95 for stores up to 10,000 memories
  - `read_graph`: < 1000ms p95 for stores up to 10,000 memories
- **Memory Efficiency**: JSONL storage MUST use in-memory indexes, not full file scans. Compaction MUST run without blocking read operations. Embedding generation MAY be deferred to background tasks.
- **Scalability Design**: Core operations MUST scale linearly (O(n)) or better with memory count. Quadratic operations (O(n²)) MUST be justified and documented. No unbounded memory growth during normal operations.
- **Benchmarking**: Performance-critical changes MUST include benchmark results in PR description. Regressions exceeding 20% MUST be justified or blocked.

**Rationale**: CortexGraph is a memory system—performance directly impacts user experience. Slow searches or saves disrupt conversation flow and erode trust in the system.

## Quality Gates

All PRs MUST pass these gates before merge:

| Gate | Tool | Threshold | Blocking |
|------|------|-----------|----------|
| Tests Pass | pytest | 100% pass | Yes |
| Coverage | pytest-cov | ≥ 90% | Yes |
| Type Check | mypy | 0 errors | Yes |
| Lint | ruff check | 0 errors | Yes |
| Format | ruff format | No changes | Yes |
| Security | bandit | No high/critical | No (warnings only) |

**CI Configuration**: GitHub Actions workflow MUST enforce all blocking gates. Non-blocking gates MUST be reported but not fail the build.

## Development Workflow

### Branch Strategy

- **main**: Protected, requires PR review, must pass all quality gates
- **feature/***: Feature development branches
- **fix/***: Bug fix branches
- **release/***: Release preparation branches

### PR Requirements

1. **Description**: Clear explanation of changes and motivation
2. **Tests**: New/modified tests for all functional changes
3. **Documentation**: Updated docstrings and README if public API changes
4. **Breaking Changes**: Explicitly called out with migration guidance
5. **Performance**: Benchmark results for performance-sensitive changes

### Commit Messages

Follow conventional commits format:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation only
- `test:` Test additions/modifications
- `refactor:` Code changes that neither fix bugs nor add features
- `perf:` Performance improvements
- `chore:` Maintenance tasks

## Governance

This constitution establishes the fundamental quality and development standards for CortexGraph. All contributors, PRs, and code reviews MUST verify compliance with these principles.

### Amendment Process

1. **Proposal**: Open an issue describing the proposed change and rationale
2. **Discussion**: Minimum 3-day comment period for substantive changes
3. **Implementation**: Update constitution.md with new version
4. **Propagation**: Update all dependent templates (plan, spec, tasks)
5. **Documentation**: Record change in CHANGELOG

### Versioning Policy

Constitution versions follow semantic versioning:

- **MAJOR**: Principle removals, backward-incompatible governance changes
- **MINOR**: New principles, material expansions, new gates
- **PATCH**: Clarifications, threshold adjustments, typo fixes

### Compliance Review

- **PR Review**: Reviewers MUST check principle compliance
- **Automated Gates**: CI MUST enforce quality gates (see table above)
- **Periodic Audit**: Quarterly review of coverage trends and gate effectiveness

### Guidance Reference

For day-to-day development guidance, see `CLAUDE.md` which contains:

- Development commands (pytest, mypy, ruff)
- MCP configuration examples
- Storage architecture details
- Tool implementation patterns

**Version**: 1.0.0 | **Ratified**: 2025-11-20 | **Last Amended**: 2025-11-20
