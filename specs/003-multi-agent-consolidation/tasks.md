# Tasks: Multi-Agent Memory Consolidation

**Input**: Design documents from `/specs/003-multi-agent-consolidation/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Tests ARE required per Constitution (90%+ coverage) and spec.md testing standards.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/cortexgraph/agents/` (new module)
- **CLI**: `src/cortexgraph/cli/consolidate.py` (new entry point)
- **Tests**: `tests/unit/agents/`, `tests/integration/agents/`, `tests/contract/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and agent module structure

- [x] T001 Create agents module directory structure at `src/cortexgraph/agents/__init__.py`
- [x] T002 [P] Create beads integration helper at `src/cortexgraph/agents/beads_integration.py`
- [x] T003 [P] Create rate limiter utility at `src/cortexgraph/agents/rate_limiter.py`
- [x] T004 Add agents dependencies to `pyproject.toml` (no new deps - uses existing)
- [x] T005 Create test directories: `tests/unit/agents/`, `tests/integration/agents/`, `tests/contract/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Base Agent Class

- [x] T006 Create ConsolidationAgent abstract base class at `src/cortexgraph/agents/base.py`
- [x] T007 Implement ConfidenceConfig model in `src/cortexgraph/agents/base.py`
- [x] T008 Implement rate limiting in base agent `run()` method
- [x] T009 Implement dry-run mode in base agent

### Result Models (Pydantic)

- [x] T010 [P] Create DecayResult model in `src/cortexgraph/agents/models.py`
- [x] T011 [P] Create ClusterResult model in `src/cortexgraph/agents/models.py`
- [x] T012 [P] Create MergeResult model in `src/cortexgraph/agents/models.py`
- [x] T013 [P] Create PromotionResult model in `src/cortexgraph/agents/models.py`
- [x] T014 [P] Create RelationResult model in `src/cortexgraph/agents/models.py`

### Enums

- [x] T015 [P] Create Urgency, DecayAction, ClusterAction, ProcessingDecision enums in `src/cortexgraph/agents/models.py`

### Beads Integration

- [x] T016 Implement `create_consolidation_issue()` in `src/cortexgraph/agents/beads_integration.py`
- [x] T017 Implement `query_consolidation_issues()` in `src/cortexgraph/agents/beads_integration.py`
- [x] T018 Implement `claim_issue()`, `close_issue()`, `block_issue()` in `src/cortexgraph/agents/beads_integration.py`

### Foundational Tests

- [x] T019 [P] Unit tests for ConsolidationAgent base class in `tests/unit/agents/test_base_agent.py`
- [x] T020 [P] Unit tests for result models in `tests/unit/agents/test_models.py`
- [x] T021 [P] Unit tests for beads integration in `tests/unit/agents/test_beads_integration.py`
- [x] T022 [P] Unit tests for rate limiter in `tests/unit/agents/test_rate_limiter.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Automatic Memory Decay Triage (Priority: P1) 🎯 MVP

**Goal**: Identify memories approaching forget threshold and create beads issues for triage

**Independent Test**: Create memories with varying decay scores, verify Decay Analyzer correctly identifies danger zone (0.15-0.35) and near-forget (<0.10) memories, creates appropriate beads issues

### Tests for User Story 1

- [x] T023 [P] [US1] Contract test: DecayAnalyzer.scan() returns memory IDs in `tests/contract/test_decay_analyzer.py`
- [x] T024 [P] [US1] Contract test: DecayAnalyzer.process_item() returns DecayResult in `tests/contract/test_decay_analyzer.py`
- [x] T025 [P] [US1] Unit test: urgency classification (high/medium/low) in `tests/unit/agents/test_decay_analyzer.py`
- [x] T026 [P] [US1] Unit test: action recommendation logic in `tests/unit/agents/test_decay_analyzer.py`
- [x] T027 [US1] Integration test: end-to-end decay triage in `tests/integration/agents/test_decay_analyzer_e2e.py`

### Implementation for User Story 1

- [x] T028 [US1] Create DecayAnalyzer class skeleton in `src/cortexgraph/agents/decay_analyzer.py`
- [x] T029 [US1] Implement `scan()` - find memories with score < 0.35 in `src/cortexgraph/agents/decay_analyzer.py`
- [x] T030 [US1] Implement `process_item()` - calculate urgency, recommend action in `src/cortexgraph/agents/decay_analyzer.py`
- [x] T031 [US1] Integrate with existing `core/decay.py` for score calculation
- [x] T032 [US1] Integrate with beads for issue creation (urgent items)
- [~] T033 [US1] Add event trigger hook for post-save decay check *(Deferred: Enhancement for future release - core decay triage works via scheduled scans)*

**Checkpoint**: ✅ Decay Analyzer fully functional and independently testable

---

## Phase 4: User Story 2 - Intelligent Memory Clustering (Priority: P1)

**Goal**: Detect and group similar memories for potential consolidation

**Independent Test**: Insert memories with known semantic overlap, verify clusters are correctly formed with appropriate cohesion scores

### Tests for User Story 2

- [x] T034 [P] [US2] Contract test: ClusterDetector.scan() returns memory IDs in `tests/contract/test_cluster_detector.py`
- [x] T035 [P] [US2] Contract test: ClusterDetector.process_item() returns ClusterResult in `tests/contract/test_cluster_detector.py`
- [x] T036 [P] [US2] Unit test: cohesion calculation in `tests/unit/agents/test_cluster_detector.py`
- [x] T037 [P] [US2] Unit test: action recommendation (merge/link/ignore) in `tests/unit/agents/test_cluster_detector.py`
- [x] T038 [US2] Integration test: cluster detection with embeddings in `tests/integration/agents/test_cluster_detector.py`

### Implementation for User Story 2

- [x] T039 [US2] Create ClusterDetector class skeleton in `src/cortexgraph/agents/cluster_detector.py`
- [x] T040 [US2] Implement `scan()` - find memories with potential clusters in `src/cortexgraph/agents/cluster_detector.py`
- [x] T041 [US2] Implement `process_item()` - calculate cohesion, determine action in `src/cortexgraph/agents/cluster_detector.py`
- [x] T042 [US2] Integrate with existing `core/clustering.py` for similarity calculation
- [x] T043 [US2] Integrate with beads for cluster issue creation (cohesion >= 0.4)
- [x] T044 [US2] Prevent duplicate cluster detection

**Checkpoint**: Cluster Detector should be fully functional and independently testable

---

## Phase 5: User Story 3 - Semantic Memory Merging (Priority: P2)

**Goal**: Combine clustered memories intelligently while preserving all unique information

**Independent Test**: Provide known cluster, verify merged output contains all unique entities, tags, and content from originals

### Tests for User Story 3

- [X] T045 [P] [US3] Contract test: SemanticMerge.scan() reads from beads issues in `tests/contract/test_semantic_merge.py`
- [X] T046 [P] [US3] Contract test: SemanticMerge.process_item() returns MergeResult in `tests/contract/test_semantic_merge.py`
- [X] T047 [P] [US3] Unit test: content deduplication in `tests/unit/agents/test_semantic_merge.py`
- [X] T048 [P] [US3] Unit test: entity/tag union preservation in `tests/unit/agents/test_semantic_merge.py`
- [X] T049 [US3] Integration test: full merge with relation creation in `tests/integration/agents/test_semantic_merge_e2e.py`

### Implementation for User Story 3

- [X] T050 [US3] Create SemanticMerge class skeleton in `src/cortexgraph/agents/semantic_merge.py`
- [X] T051 [US3] Implement `scan()` - query beads for consolidation:merge issues in `src/cortexgraph/agents/semantic_merge.py`
- [X] T052 [US3] Implement `process_item()` - merge content, preserve entities in `src/cortexgraph/agents/semantic_merge.py`
- [X] T053 [US3] Integrate with existing `core/consolidation.py` for merge logic
- [X] T054 [US3] Create `consolidated_from` relations after merge
- [X] T055 [US3] Archive original memories (status=archived, not deleted)
- [X] T056 [US3] Close beads issue on successful merge

**Checkpoint**: ✅ Semantic Merge fully functional and independently testable (41 tests)

---

## Phase 6: User Story 4 - Long-Term Memory Promotion (Priority: P2)

**Goal**: Automatically promote high-value memories to permanent Obsidian vault storage

**Independent Test**: Create memories meeting promotion criteria, verify markdown files are created in vault with correct frontmatter

### Tests for User Story 4

- [X] T057 [P] [US4] Contract test: LTMPromoter.scan() finds promotion candidates in `tests/contract/test_ltm_promoter.py`
- [X] T058 [P] [US4] Contract test: LTMPromoter.process_item() returns PromotionResult in `tests/contract/test_ltm_promoter.py`
- [X] T059 [P] [US4] Unit test: promotion criteria matching in `tests/unit/agents/test_ltm_promoter.py`
- [X] T060 [P] [US4] Unit test: markdown generation in `tests/unit/agents/test_ltm_promoter.py`
- [X] T061 [US4] Integration test: full promotion with vault write in `tests/integration/agents/test_ltm_promoter_e2e.py`

### Implementation for User Story 4

- [X] T062 [US4] Create LTMPromoter class skeleton in `src/cortexgraph/agents/ltm_promoter.py`
- [X] T063 [US4] Implement `scan()` - find memories meeting criteria in `src/cortexgraph/agents/ltm_promoter.py`
- [X] T064 [US4] Implement `process_item()` - write markdown, update status in `src/cortexgraph/agents/ltm_promoter.py`
- [X] T065 [US4] Integrate with existing `vault/writer.py` for markdown output
- [X] T066 [US4] Integrate with existing `core/scoring.py` for promotion criteria
- [X] T067 [US4] Prevent duplicate vault files
- [X] T068 [US4] Create beads issue documenting promotion

**Checkpoint**: ✅ LTM Promoter fully functional and independently testable (49 tests: 16 contract, 18 unit, 15 integration)

---

## Phase 7: User Story 5 - Relationship Discovery (Priority: P3)

**Goal**: Find implicit connections between memories to enrich the knowledge graph

**Independent Test**: Insert memories with implicit relationships, verify `related` relations are created with appropriate strength and reasoning

### Tests for User Story 5

- [X] T069 [P] [US5] Contract test: RelationshipDiscovery.scan() finds candidates in `tests/contract/test_relationship_discovery.py`
- [X] T070 [P] [US5] Contract test: RelationshipDiscovery.process_item() returns RelationResult in `tests/contract/test_relationship_discovery.py`
- [X] T071 [P] [US5] Unit test: shared entity detection in `tests/unit/agents/test_relationship_discovery.py`
- [X] T072 [P] [US5] Unit test: relation strength calculation in `tests/unit/agents/test_relationship_discovery.py`
- [X] T073 [US5] Integration test: relation creation with reasoning in `tests/integration/agents/test_relationship_discovery.py`

### Implementation for User Story 5

- [X] T074 [US5] Create RelationshipDiscovery class skeleton in `src/cortexgraph/agents/relationship_discovery.py`
- [X] T075 [US5] Implement `scan()` - find memories with potential connections in `src/cortexgraph/agents/relationship_discovery.py`
- [X] T076 [US5] Implement `process_item()` - calculate strength, provide reasoning in `src/cortexgraph/agents/relationship_discovery.py`
- [X] T077 [US5] Integrate with existing `core/clustering.py` for similarity (using Jaccard similarity directly)
- [X] T078 [US5] Create `related` relations via `create_relation` tool
- [X] T079 [US5] Prevent spurious relations (precision > 0.8) via min_confidence threshold
- [X] T080 [US5] Create beads issue documenting discovered relations via create_consolidation_issue()

**Checkpoint**: Relationship Discovery should be fully functional and independently testable

---

## Phase 8: CLI & Pipeline Integration

**Purpose**: Expose agents via CLI and enable pipeline orchestration

### CLI Entry Point

- [X] T081 Create CLI skeleton at `src/cortexgraph/cli/consolidate.py`
- [X] T082 Implement `run` command with agent selection
- [X] T083 Implement `run --all` for full pipeline
- [X] T084 Implement `status` command for queue inspection
- [X] T085 Implement `process` command for specific issue
- [X] T086 Add `--dry-run` and `--json` global options
- [X] T087 Add entry point `cortexgraph-consolidate` to `pyproject.toml`

### Scheduler

- [X] T088 Create hybrid scheduler at `src/cortexgraph/agents/scheduler.py`
- [X] T089 Implement cron-like scheduled execution
- [X] T090 Implement event trigger for urgent decay (<0.10)

### CLI Tests

- [X] T091 [P] Unit tests for CLI commands in `tests/unit/cli/test_cli_consolidate.py`
- [X] T092 Integration test for pipeline execution in `tests/integration/agents/test_agent_pipeline.py`
- [X] T093 Integration test for beads coordination in `tests/integration/agents/test_beads_coordination.py`

**Checkpoint**: CLI and pipeline should be fully functional

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T094 [P] Update `docs/api.md` with new agent tools
- [X] T095 [P] Create `docs/agents.md` architecture documentation
- [X] T096 [P] Update `README.md` with consolidation agent section
- [X] T097 Run mypy strict on `src/cortexgraph/agents/`
- [X] T098 Run ruff check/format on agents module
- [X] T099 Achieve 90%+ test coverage on agents module (90.5% achieved)
- [X] T100 Run quickstart.md validation (fixed 4 CLI command references)
- [X] T101 Performance validation: < 5 seconds per memory (all agents < 10ms)
- [X] T102 Security review: No credential exposure, rate limiting enforced

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup) ─────────────────────────────────────────┐
                                                         │
Phase 2 (Foundational) ◄─────────────────────────────────┘
         │
         │ BLOCKS ALL USER STORIES
         ▼
┌────────┴────────┬─────────────────┬─────────────────┬─────────────────┐
│                 │                 │                 │                 │
▼                 ▼                 ▼                 ▼                 ▼
Phase 3 (US1)   Phase 4 (US2)   Phase 5 (US3)   Phase 6 (US4)   Phase 7 (US5)
Decay Analyzer  Cluster Det.    Semantic Merge  LTM Promoter    Relation Disc.
P1 🎯 MVP       P1              P2              P2              P3
                                     │
                                     │ depends on US2 clusters
                                     ▼
                               (can run after US2)
         │
         ▼
Phase 8 (CLI & Pipeline) ◄───────────────────────────────┘
         │
         ▼
Phase 9 (Polish)
```

### User Story Dependencies

- **User Story 1 (Decay Analyzer)**: Independent - can start after Phase 2
- **User Story 2 (Cluster Detector)**: Independent - can start after Phase 2
- **User Story 3 (Semantic Merge)**: Depends on US2 (needs clusters to merge)
- **User Story 4 (LTM Promoter)**: Independent - can start after Phase 2
- **User Story 5 (Relationship Discovery)**: Independent - can start after Phase 2

### Within Each User Story

1. Contract tests FIRST (define expected behavior)
2. Unit tests (test isolated logic)
3. Implementation (make tests pass)
4. Integration tests (verify end-to-end)
5. Story checkpoint (validate independently)

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T010-T015 (all result models and enums) can run in parallel
- T019-T022 (all foundational tests) can run in parallel

**User Stories after Phase 2**:
- US1 and US2 can run in parallel (both P1, independent)
- US4 and US5 can run in parallel (US4 P2, US5 P3, both independent)
- US3 must wait for US2 (needs clusters)

**Within Each Story**:
- Contract tests can run in parallel
- Unit tests can run in parallel

---

## Parallel Example: Phase 2 Foundation

```bash
# Launch all result models in parallel:
Task: "T010 [P] Create DecayResult model in src/cortexgraph/agents/models.py"
Task: "T011 [P] Create ClusterResult model in src/cortexgraph/agents/models.py"
Task: "T012 [P] Create MergeResult model in src/cortexgraph/agents/models.py"
Task: "T013 [P] Create PromotionResult model in src/cortexgraph/agents/models.py"
Task: "T014 [P] Create RelationResult model in src/cortexgraph/agents/models.py"
Task: "T015 [P] Create enums in src/cortexgraph/agents/models.py"
```

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 contract/unit tests in parallel:
Task: "T023 [P] [US1] Contract test: DecayAnalyzer.scan()"
Task: "T024 [P] [US1] Contract test: DecayAnalyzer.process_item()"
Task: "T025 [P] [US1] Unit test: urgency classification"
Task: "T026 [P] [US1] Unit test: action recommendation logic"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T022)
3. Complete Phase 3: User Story 1 - Decay Analyzer (T023-T033)
4. **STOP and VALIDATE**: Test independently with real memories
5. Deploy/demo: `cortexgraph-consolidate run decay`

### Incremental Delivery

| Increment | Stories | Value Delivered |
|-----------|---------|-----------------|
| MVP | US1 (Decay) | Prevents memory loss |
| v0.8.1 | US1 + US2 | Identifies consolidation opportunities |
| v0.8.2 | US1 + US2 + US3 | Actually consolidates memories |
| v0.8.3 | US1-4 | Permanent preservation in vault |
| v0.9.0 | US1-5 + CLI | Full pipeline with relationship discovery |

### Suggested MVP Scope

**Phase 1 + Phase 2 + Phase 3 (User Story 1)**

- Total tasks: 33 (T001-T033)
- Delivers: Decay triage preventing memory loss
- Test: Create memories with various scores, run decay analyzer
- CLI: `cortexgraph-consolidate run decay`

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests follow TDD: write failing tests before implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Beads issues track execution state across chat sessions
