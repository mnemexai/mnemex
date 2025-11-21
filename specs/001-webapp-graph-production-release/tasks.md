# Tasks: Web-App Graph Visualization and Production Hardening

**Input**: Design documents from `/specs/001-webapp-graph-production-release/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are included per constitution requirement (≥90% coverage for src/cortexgraph/).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US0, US1, US2...)
- Include exact file paths in descriptions

## Path Conventions

- **Single project with web component**: `src/cortexgraph/`, `src/cortexgraph/web/`, `tests/`
- Existing structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup for graph visualization

- [x] T001 Add D3.js v7 to web-app static assets in src/cortexgraph/web/static/lib/d3.v7.min.js
- [x] T002 [P] Add slowapi rate limiting dependency to pyproject.toml
- [x] T003 [P] Create graph visualization HTML template in src/cortexgraph/web/templates/graph.html
- [x] T004 Configure security scanning in .bandit configuration file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Models

- [x] T005 [P] Create GraphNode model in src/cortexgraph/storage/models.py
- [x] T006 [P] Create GraphEdge model in src/cortexgraph/storage/models.py
- [x] T007 [P] Create GraphData and GraphFilter models in src/cortexgraph/storage/models.py
- [x] T008 [P] Create ErrorResponse and ErrorDetail models in src/cortexgraph/storage/models.py
- [x] T009 [P] Create ErrorCode enumeration in src/cortexgraph/storage/models.py
- [x] T010 [P] Create ValidationResult and StorageHealthReport models in src/cortexgraph/storage/models.py
- [x] T011 Add model conversion functions (memory_to_graph_node, relation_to_graph_edge) in src/cortexgraph/storage/models.py

### API Infrastructure

- [x] T012 [P] Implement rate limiting middleware with slowapi in src/cortexgraph/web/app.py
- [x] T013 [P] Create standardized error response handler in src/cortexgraph/web/api.py
- [x] T014 [P] Add security event logging infrastructure in src/cortexgraph/security/logging.py

### Tests for Foundational Models

- [x] T015 [P] Unit tests for GraphNode/GraphEdge models in tests/unit/test_graph_models.py
- [x] T016 [P] Unit tests for ErrorResponse models in tests/unit/test_error_models.py
- [x] T017 [P] Unit tests for model conversion functions in tests/unit/test_model_conversions.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 0 - Storage Backend Parity Verification (Priority: P0 - Spike) 🔒 BLOCKING

**Goal**: Verify JSONL and SQLite backends store and retrieve relationships identically before visualization work begins

**Independent Test**: Create identical relationship data in both backends and verify queries return identical results through storage abstraction layer

### Tests for User Story 0

- [x] T018 [P] [US0] Create parity test fixtures with all 6 relationship types in tests/integration/test_backend_parity.py
- [x] T019 [P] [US0] Contract test for relationship query parity in tests/contract/test_storage_parity.py

### Implementation for User Story 0

- [x] T020 [US0] Implement relationship parity verification suite in tests/integration/test_backend_parity.py
- [x] T021 [US0] Test all relationship types (related, causes, supports, contradicts, has_decision, consolidated_from)
- [x] T022 [US0] Test edge cases (min/max strength, unicode metadata, circular references)
- [x] T023 [US0] Document any differences in specs/001-webapp-graph-production-release/spike-report.md
- [x] T024 [US0] Fix any parity issues found in storage backends (if needed)

**Checkpoint**: Spike complete - verified relationship parity. Generate spike-report.md. MUST pass before P1 work begins.

---

## Phase 4: User Story 1 - View Memory Relationships (Priority: P1) 🎯 MVP

**Goal**: Display relationships between memories in web-app detail view (list of related memories with relationship types)

**Independent Test**: View any memory in web-app and see its connected memories with relationship types (causes, supports, contradicts, etc.)

### Tests for User Story 1

- [x] T025 [P] [US1] Contract test for GET /api/memories/{id}/relationships in tests/contract/test_relationships_api.py
- [x] T026 [P] [US1] Integration test for relationship display in tests/integration/test_relationship_display.py

### Implementation for User Story 1

- [x] T027 [P] [US1] Create RelationshipItem response model in src/cortexgraph/storage/models.py
- [x] T028 [P] [US1] Create RelationshipsResponse model in src/cortexgraph/storage/models.py
- [x] T029 [US1] Implement get_memory_relationships service in src/cortexgraph/web/services/relationship_service.py
- [x] T030 [US1] Implement GET /api/memories/{id}/relationships endpoint in src/cortexgraph/web/api.py
- [x] T031 [US1] Add relationships section to memory detail template in src/cortexgraph/web/templates/memory_detail.html
- [x] T032 [US1] Add JavaScript to fetch and display relationships in src/cortexgraph/web/static/js/memory_detail.js
- [x] T033 [US1] Handle "no relationships" case with appropriate message
- [x] T034 [US1] Add click navigation from related memory to its detail view

**Checkpoint**: User Story 1 complete - users can view relationships for any memory

---

## Phase 5: User Story 2 - Interactive Graph Visualization (Priority: P2)

**Goal**: Visual graph of memories with pan, zoom, drag interactions (similar to Obsidian/Logseq)

**Independent Test**: Open graph view, see memories as nodes and relationships as edges, interact by clicking/dragging nodes

### Tests for User Story 2

- [x] T035 Create contract test for GET /api/graph `tests/contract/test_graph_api.py`
- [x] T036 Create contract test for POST /api/graph/filtered `tests/contract/test_graph_api.py`
- [x] T037 Integration test for graph loading `tests/integration/test_graph_visualization.py`

### Implementation for User Story 2

- [x] T038 Implement `get_graph_data` service `src/cortexgraph/web/services/graph_service.py`
- [x] T039 Implement GET /api/graph endpoint `src/cortexgraph/web/api.py`
- [x] T040 Implement POST /api/graph/filtered endpoint `src/cortexgraph/web/api.py`
- [x] T040 Implement POST /api/graph/filtered endpoint `src/cortexgraph/web/api.py`
- [x] T041 Create D3.js force-directed graph visualization `src/cortexgraph/web/static/js/graph.js` (REPLACED by T041b)
- [x] T041b Refactor graph visualization to use Cytoscape.js `src/cortexgraph/web/static/js/graph.js`
- [x] T042 Implement node click to show details
- [x] T043 Implement node drag behavior
- [x] T044 Implement zoom and pan
- [x] T045 Implement visual encoding for node status
- [x] T046 Implement visual encoding for edge strength
- [ ] T047 Implement layout persistence (optional for MVP)
- [x] T048 Add filter panel to graph view
- [ ] T049 Optimize graph rendering for large datasets (optional for MVP)

**Checkpoint**: User Story 2 complete - users can explore interactive graph visualization

---

## Phase 6: User Story 3 - Full Metadata Display (Priority: P3)

**Goal**: Display complete metadata for each memory (tags, entities, decay score, timestamps, etc.)

**Independent Test**: View any memory and see all metadata fields rendered in clear layout

### Tests for User Story 3

- [x] T050 [P] [US3] Integration test for full metadata display in tests/integration/test_metadata_display.py

### Implementation for User Story 3

- [x] T051 [US3] Extend memory detail template with all metadata fields in src/cortexgraph/web/templates/memory_detail.html
- [x] T052 [US3] Add timestamp formatting (human-readable) in src/cortexgraph/web/static/js/formatters.js
- [x] T053 [US3] Add decay score calculation and display
- [x] T054 [US3] Show "Not set" indicator for null/empty fields
- [x] T055 [US3] Add promotion status and vault path display for promoted memories
- [x] T056 [US3] Style metadata section for clarity and readability

**Checkpoint**: User Story 3 complete - users can see complete memory metadata

---

## Phase 7: User Story 4 - Error Resilience (Priority: P4)

**Goal**: Graceful error handling with actionable messages and storage recovery

**Independent Test**: Simulate failures (corrupt JSONL, invalid data) and verify recovery with actionable error messages

### Tests for User Story 4

- [ ] T057 [P] [US4] Integration test for storage corruption detection in tests/integration/test_error_resilience.py
- [ ] T058 [P] [US4] Integration test for error message format in tests/integration/test_error_messages.py

### Implementation for User Story 4

- [ ] T059 [US4] Implement storage validation function in src/cortexgraph/storage/validation.py
- [ ] T060 [US4] Implement corruption detection for JSONL files in src/cortexgraph/storage/jsonl_storage.py
- [ ] T061 [US4] Implement recovery attempt logic in src/cortexgraph/storage/recovery.py
- [ ] T062 [US4] Add GET /api/health endpoint in src/cortexgraph/web/api.py
- [ ] T063 [US4] Implement cortexgraph-maintenance validate command in src/cortexgraph/cli/maintenance.py
- [ ] T064 [US4] Implement cortexgraph-maintenance repair command in src/cortexgraph/cli/maintenance.py
- [ ] T065 [US4] Convert all API errors to ErrorResponse format with remediation
- [ ] T066 [US4] Add automatic reconnection logic for web-app in src/cortexgraph/web/static/js/connection.js

**Checkpoint**: User Story 4 complete - system handles errors gracefully with recovery options

---

## Phase 8: User Story 5 - Security Hardening (Priority: P5)

**Goal**: Input validation, safe defaults, rate limiting, and security scanning compliance

**Independent Test**: Run security scans (bandit), attempt injection attacks, verify all inputs validated

### Tests for User Story 5

- [ ] T067 [P] [US5] Security test for input validation in tests/security/test_input_validation.py
- [ ] T068 [P] [US5] Security test for path traversal prevention in tests/security/test_path_traversal.py

### Implementation for User Story 5

- [ ] T069 [US5] Audit and enhance input validation in all API endpoints in src/cortexgraph/web/api.py
- [ ] T070 [US5] Add path traversal prevention in storage operations in src/cortexgraph/storage/jsonl_storage.py
- [ ] T071 [US5] Implement CSP headers for web-app in src/cortexgraph/web/app.py
- [ ] T072 [US5] Add security event logging (without sensitive data) in src/cortexgraph/security/logging.py
- [ ] T073 [US5] Configure rate limiting thresholds (30/min for graph, 100/min for others)
- [ ] T074 [US5] Run bandit security scan and fix any high/critical findings
- [ ] T075 [US5] Run pip-audit/safety dependency scan and update vulnerable packages

**Checkpoint**: User Story 5 complete - system passes security scanning with zero high/critical issues

---

## Phase 9: User Story 6 - Supply Chain Hardening (Priority: P6)

**Goal**: Verifiable builds, SBOMs, signed releases for production distribution

**Independent Test**: Verify release signatures, review SBOMs, confirm reproducible builds

### Implementation for User Story 6

- [ ] T076 [P] [US6] Generate CycloneDX SBOM in CI workflow in .github/workflows/release.yml
- [ ] T077 [P] [US6] Generate SPDX SBOM as alternative format in .github/workflows/release.yml
- [ ] T078 [US6] Add release signing with GPG in .github/workflows/release.yml
- [ ] T079 [US6] Document SBOM verification process in docs/security/sbom-verification.md
- [ ] T080 [US6] Document release signature verification in docs/security/release-verification.md
- [ ] T081 [US6] Pin all dependencies with hashes in uv.lock
- [ ] T082 [US6] Configure reproducible builds for PyPI wheel

**Checkpoint**: User Story 6 complete - releases include signatures and SBOMs

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T083 [P] Update README.md with graph visualization documentation
- [ ] T084 [P] Update CLAUDE.md with new API endpoints and models
- [ ] T085 Code cleanup and refactoring across web-app
- [ ] T086 Performance optimization for graph operations
- [ ] T087 [P] Add/update docstrings for all new public APIs
- [ ] T088 Run quickstart.md validation - verify all examples work
- [ ] T089 Run full test suite and verify ≥90% coverage
- [ ] T090 Run all quality gates (mypy, ruff check, ruff format, bandit)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 0 (Phase 3)**: Depends on Foundational - BLOCKS all visualization work (P1-P3)
- **User Stories 1-3 (Phases 4-6)**: All depend on US0 completion (visualization features)
- **User Stories 4-6 (Phases 7-9)**: Depend only on Foundational (production hardening - can parallel with 1-3)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

```
┌─────────────┐
│   Setup     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Foundational│
└──────┬──────┘
       │
       ├───────────────────┬───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ US0 (Spike) │     │ US4 (Errors)│     │ US5 (Sec)   │
│   BLOCKING  │     │             │     │             │
└──────┬──────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ├───────┬───────┐   │                   │
       │       │       │   │                   │
       ▼       ▼       ▼   ▼                   ▼
┌───────┐ ┌───────┐ ┌───────┐              ┌───────┐
│  US1  │ │  US2  │ │  US3  │              │  US6  │
│ (MVP) │ │(Graph)│ │(Meta) │              │(Supply│
└───────┘ └───────┘ └───────┘              └───────┘
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**By Phase:**
- Setup: T001-T004 can all run in parallel
- Foundational: T005-T010 models can run in parallel, T012-T014 infrastructure in parallel
- US0: T018-T019 tests in parallel
- US1: T025-T026 tests in parallel, T027-T028 models in parallel
- US2: T035-T037 tests in parallel, T047 can parallel with earlier tasks
- US4: T057-T058 tests in parallel
- US5: T067-T068 tests in parallel, T076-T077 in parallel
- US6: T076-T077 SBOM generation in parallel
- Polish: T083-T084, T087 in parallel

**Cross-Story Parallel:**
- US4 (Error Resilience) can run in parallel with US1-US3
- US5 (Security) can run in parallel with US1-US4
- US6 (Supply Chain) can run in parallel with US1-US5

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for GET /api/memories/{id}/relationships in tests/contract/test_relationships_api.py"
Task: "Integration test for relationship display in tests/integration/test_relationship_display.py"

# Launch all models for User Story 1 together:
Task: "Create RelationshipItem response model in src/cortexgraph/storage/models.py"
Task: "Create RelationshipsResponse model in src/cortexgraph/storage/models.py"
```

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Contract test for GET /api/graph in tests/contract/test_graph_api.py"
Task: "Contract test for POST /api/graph/filtered in tests/contract/test_graph_filter_api.py"
Task: "Integration test for graph loading in tests/integration/test_graph_visualization.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 0 (Spike - verify backend parity)
4. Complete Phase 4: User Story 1 (Relationships display)
5. **STOP and VALIDATE**: Test User Story 1 independently
6. Deploy/demo if ready - this is a complete, valuable increment

### Incremental Delivery

1. Complete Setup + Foundational + US0 → Foundation + parity verified
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Graph viz!)
4. Add User Story 3 → Test independently → Deploy/Demo (Full metadata!)
5. Add User Stories 4-6 → Production hardening for 1.0.0 release
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. All developers complete Setup + Foundational + US0 together
2. Once US0 (Spike) is done:
   - Developer A: User Story 1 (Relationships) + User Story 3 (Metadata)
   - Developer B: User Story 2 (Graph Visualization)
   - Developer C: User Stories 4-6 (Production Hardening)
3. Stories complete and integrate independently

### Constitution Quality Gates

Before any PR merge:

- [ ] Tests Pass (100%)
- [ ] Coverage (≥90%)
- [ ] Type Check (mypy 0 errors)
- [ ] Lint (ruff check 0 errors)
- [ ] Format (ruff format no changes)
- [ ] Security (bandit no high/critical)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US0 (Spike) MUST complete before US1-US3 visualization work
- US4-US6 (hardening) can run in parallel with US1-US3
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
