# Tasks: Natural Language Memory Activation

**Feature**: 002-natural-language-activation
**Input**: Design documents from `/specs/002-natural-language-activation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Unit and integration tests are included as this is a core feature requiring ≥90% coverage per constitution.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and module structure

- [X] T001 Create `src/cortexgraph/activation/` module directory structure
- [X] T002 Create `src/cortexgraph/activation/__init__.py` with public API exports
- [X] T003 [P] Create `tests/unit/activation/` directory for unit tests
- [X] T004 [P] Create `tests/integration/activation/` directory for integration tests
- [X] T005 [P] Create `tests/contract/` directory for API contract tests
- [X] T006 Create default configuration file template at `src/cortexgraph/activation/activation.yaml.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement `ActivationSignal` Pydantic model in `src/cortexgraph/activation/models.py`
- [X] T008 [P] Implement `MessageAnalysis` Pydantic model in `src/cortexgraph/activation/models.py`
- [X] T009 [P] Implement `RecallAnalysis` Pydantic model in `src/cortexgraph/activation/models.py`
- [X] T010 [P] Implement `ConfidenceThreshold` config model in `src/cortexgraph/activation/config.py`
- [X] T011 [P] Implement `PatternLibrary` config model in `src/cortexgraph/activation/config.py`
- [X] T012 Create configuration loader with YAML parsing in `src/cortexgraph/activation/config.py`
- [X] T013 Implement entity extraction using hybrid spaCy+regex in `src/cortexgraph/activation/entity_extraction.py`
- [X] T014 Implement pattern matching engine with regex compilation in `src/cortexgraph/activation/patterns.py`
- [X] T015 Implement confidence scoring with weighted sigmoid formula in `src/cortexgraph/activation/detectors.py`
- [X] T016 Add activation configuration settings to `src/cortexgraph/config.py`
- [X] T017 [P] Write unit tests for Pydantic model validation in `tests/unit/activation/test_models.py`
- [X] T018 [P] Write unit tests for pattern matching logic in `tests/unit/activation/test_patterns.py`
- [X] T019 [P] Write unit tests for entity extraction in `tests/unit/activation/test_entity_extraction.py`
- [X] T020 [P] Write unit tests for confidence scoring in `tests/unit/activation/test_detectors.py`

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Memory Capture (Priority: P1) 🎯 MVP

**Goal**: Users share important information and the system automatically detects memory-worthy content without explicit commands

**Independent Test**: Share a preference like "I prefer PostgreSQL for databases" and verify it's detected with high confidence (>0.7) and suggested parameters (entities, tags, strength)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
> **CHECKPOINT (2025-11-24): All 5 test tasks complete - 68 tests pass, 1 xfail**

- [X] T021 [P] [US1] Contract test for `analyze_message` tool validating JSON schema in `tests/contract/test_analyze_message_api.py` (20 tests)
- [X] T022 [P] [US1] Unit test for save detection with explicit triggers in `tests/unit/activation/test_save_detection.py` (5 tests)
- [X] T023 [P] [US1] Unit test for save detection with implicit signals in `tests/unit/activation/test_save_detection.py` (7 tests)
- [X] T024 [P] [US1] Unit test for exclusion patterns (small talk filtering) in `tests/unit/activation/test_save_detection.py` (6 tests + 7 edge/uncertainty tests)
- [X] T025 [US1] Integration test for analyze_message tool with real pattern matching in `tests/integration/activation/test_analyze_message_tool.py` (19 tests)

**KEY FINDING**: Unit tests show `detect_save_intent` in activation module correctly handles "I prefer" via preference_statement signal. MCP tool needs updating to use this module (T027-T028).

### Implementation for User Story 1

- [ ] T026 [US1] Implement save detection logic in `src/cortexgraph/activation/detectors.py` (detect_save_intent function)
- [ ] T027 [US1] Implement message analysis logic in `src/cortexgraph/activation/detectors.py` (analyze_message function)
- [ ] T028 [US1] Create `analyze_message` MCP tool in `src/cortexgraph/tools/analyze_message.py`
- [ ] T029 [US1] Register `analyze_message` tool with FastMCP server in `src/cortexgraph/server.py`
- [ ] T030 [US1] Add validation and error handling for analyze_message tool
- [ ] T031 [US1] Add logging for save detection decisions with confidence scores
- [ ] T032 [US1] Create default save trigger patterns in `activation.yaml.example`

**Checkpoint**: At this point, analyze_message tool should detect memory-worthy content and provide suggested parameters

**Acceptance Verification**:
1. "I prefer PostgreSQL for databases" → should_save=True, confidence ≥0.7, entities=["postgresql"]
2. "Remember this: I use VSCode" → should_save=True, confidence ≥0.9, explicit trigger detected
3. "Nice weather today" → should_save=False, confidence <0.4, excluded as small talk
4. "I decided to use React" → should_save=True, confidence ≥0.7, decision marker detected
5. "My API endpoint is api.example.com" → should_save=True, entities=["api.example.com"]

---

## Phase 4: User Story 2 - Contextual Memory Recall (Priority: P1)

**Goal**: Users ask questions referencing past conversations and the system automatically detects recall intent without explicit "search memory" commands

**Independent Test**: First save a preference using US1 or manually, then ask "what did I say about authentication?" and verify the system detects recall intent (should_search=True, confidence ≥0.7) with extracted query

### Tests for User Story 2

- [ ] T033 [P] [US2] Contract test for `analyze_for_recall` tool validating JSON schema in `tests/contract/test_analyze_for_recall_api.py`
- [ ] T034 [P] [US2] Unit test for recall detection with explicit triggers in `tests/unit/activation/test_recall_detection.py`
- [ ] T035 [P] [US2] Unit test for recall detection with implicit signals in `tests/unit/activation/test_recall_detection.py`
- [ ] T036 [P] [US2] Unit test for query extraction from natural language in `tests/unit/activation/test_recall_detection.py`
- [ ] T037 [P] [US2] Unit test for exclusion patterns (general knowledge questions) in `tests/unit/activation/test_recall_detection.py`
- [ ] T038 [US2] Integration test for analyze_for_recall tool with real pattern matching in `tests/integration/activation/test_analyze_for_recall_tool.py`

### Implementation for User Story 2

- [ ] T039 [US2] Implement recall detection logic in `src/cortexgraph/activation/detectors.py` (detect_recall_intent function)
- [ ] T040 [US2] Implement query extraction from user messages in `src/cortexgraph/activation/detectors.py`
- [ ] T041 [US2] Implement semantic query expansion with tech term mappings in `src/cortexgraph/activation/patterns.py`
- [ ] T042 [US2] Implement recall analysis logic in `src/cortexgraph/activation/detectors.py` (analyze_for_recall function)
- [ ] T043 [US2] Create `analyze_for_recall` MCP tool in `src/cortexgraph/tools/analyze_for_recall.py`
- [ ] T044 [US2] Register `analyze_for_recall` tool with FastMCP server in `src/cortexgraph/server.py`
- [ ] T045 [US2] Add validation and error handling for analyze_for_recall tool
- [ ] T046 [US2] Add logging for recall detection decisions with confidence scores
- [ ] T047 [US2] Create default recall trigger patterns in `activation.yaml.example`
- [ ] T048 [US2] Add 50+ tech term mappings (JWT→"json web token", etc.) to `activation.yaml.example`

**Checkpoint**: At this point, analyze_for_recall tool should detect recall intent and extract search queries

**Acceptance Verification**:
1. "What did I say about auth methods?" → should_search=True, confidence ≥0.7, query="auth methods"
2. "Remind me of my database choice" → should_search=True, confidence ≥0.7, query="database choice"
3. "What's my API endpoint again?" → should_search=True, confidence ≥0.7, possessive marker detected
4. "What did I say about GraphQL?" → should_search=True (even if no memories exist - graceful empty result)
5. "What's the best authentication method?" → should_search=False, confidence <0.4, general knowledge pattern

---

## Phase 5: User Story 3 - Automatic Memory Reinforcement (Priority: P2)

**Goal**: When users revisit previously discussed topics, the system automatically reinforces those memories through integration with existing touch_memory tool

**Independent Test**: Save a memory manually, then reference it in conversation, and verify that the system detects the reference and can trigger reinforcement (this is integration with existing touch_memory - the detection is the new part)

### Tests for User Story 3

- [ ] T049 [P] [US3] Unit test for topic/entity detection in messages in `tests/unit/activation/test_reinforcement_detection.py`
- [ ] T050 [P] [US3] Unit test for cross-domain usage detection via tag similarity in `tests/unit/activation/test_reinforcement_detection.py`
- [ ] T051 [US3] Integration test for reinforcement workflow (detect → recommend touch_memory) in `tests/integration/activation/test_reinforcement_workflow.py`

### Implementation for User Story 3

- [ ] T052 [US3] Implement topic extraction from messages in `src/cortexgraph/activation/detectors.py`
- [ ] T053 [US3] Implement cross-domain usage detection with tag Jaccard similarity in `src/cortexgraph/activation/detectors.py`
- [ ] T054 [US3] Add reinforcement logic to detect when recalled memories should be touched in `src/cortexgraph/activation/detectors.py`
- [ ] T055 [US3] Add reinforcement detection to analyze_message output (new field: should_reinforce with memory_ids)
- [ ] T056 [US3] Add logging for reinforcement detection with cross-domain signals
- [ ] T057 [US3] Update integration tests to verify touch_memory is called after recall in `tests/integration/activation/test_reinforcement_workflow.py`

**Checkpoint**: At this point, the system should detect when memories are referenced and provide signals for reinforcement

**Acceptance Verification**:
1. Previously saved "JWT preference", then reference JWT in new context → reinforcement signal detected
2. Discussed "PostgreSQL" 7 days ago, ask database question today → memory retrieved AND reinforcement recommended
3. Multiple auth memories exist, discuss OAuth → OAuth-specific memory reinforcement (not all auth memories)
4. Memory in danger zone (0.15-0.35 score) → prioritized for surfacing and reinforcement
5. "Based on my React choice, I'll use Next.js" → React memory reinforcement + new Next.js memory

---

## Phase 6: User Story 4 - Decision Support for Ambiguous Cases (Priority: P3)

**Goal**: For borderline cases where confidence is in clarification range (0.4-0.7), provide reasoning and support LLM decision-making

**Independent Test**: Submit an ambiguous statement like "I might use Redis for caching" and verify confidence falls in clarification range with clear reasoning

### Tests for User Story 4

- [ ] T058 [P] [US4] Unit test for uncertainty marker detection in `tests/unit/activation/test_ambiguous_detection.py`
- [ ] T059 [P] [US4] Unit test for confidence threshold decision logic in `tests/unit/activation/test_confidence_thresholds.py`
- [ ] T060 [P] [US4] Unit test for reasoning string generation in `tests/unit/activation/test_reasoning.py`
- [ ] T061 [US4] Integration test for ambiguous cases with clarification flow in `tests/integration/activation/test_ambiguous_workflow.py`

### Implementation for User Story 4

- [ ] T062 [US4] Implement uncertainty marker detection in `src/cortexgraph/activation/detectors.py`
- [ ] T063 [US4] Implement conditional language detection ("if", "maybe", "considering") in `src/cortexgraph/activation/detectors.py`
- [ ] T064 [US4] Enhance reasoning string generation with signal breakdown in `src/cortexgraph/activation/detectors.py`
- [ ] T065 [US4] Implement phrase_signals dictionary population for transparency in `src/cortexgraph/activation/detectors.py`
- [ ] T066 [US4] Add strict_mode parameter support to analyze_message and analyze_for_recall tools
- [ ] T067 [US4] Add context_tags parameter support to analyze_message for context-aware analysis
- [ ] T068 [US4] Add available_tags parameter support to analyze_for_recall for better tag suggestions
- [ ] T069 [US4] Update logging to include phrase_signals for debugging
- [ ] T070 [US4] Create uncertainty marker patterns in `activation.yaml.example`

**Checkpoint**: At this point, ambiguous cases should provide clear reasoning and fall in appropriate confidence ranges

**Acceptance Verification**:
1. "I might use Redis for caching" → confidence 0.4-0.6, uncertainty markers detected, reasoning explains low confidence
2. "What's the best authentication method?" → should_search=False or confidence 0.4-0.6, ambiguous (memory vs general knowledge)
3. Strict mode with "I prefer PostgreSQL" → should_save=False (no explicit trigger in strict mode)
4. Context-aware: "That's my choice" with context_tags=["database"] → better confidence through context
5. Feedback integration: "Don't remember that" → explicit negative command handled

---

## Phase 7: CLI Tools & Documentation

**Purpose**: Developer tools and user-facing documentation

- [ ] T071 [P] Create `cortexgraph-activation` CLI entry point in `src/cortexgraph/cli/activation.py`
- [ ] T072 [P] Implement `analyze` subcommand for testing pattern detection in `src/cortexgraph/cli/activation.py`
- [ ] T073 [P] Implement `test` subcommand for pattern validation in `src/cortexgraph/cli/activation.py`
- [ ] T074 [P] Add CLI command registration to `pyproject.toml` console_scripts
- [ ] T075 [P] Update `README.md` with natural language activation overview and links to quickstart
- [ ] T076 [P] Update `docs/api.md` with analyze_message and analyze_for_recall tool documentation
- [ ] T077 [P] Create `docs/activation.md` with detailed activation system documentation
- [ ] T078 [P] Validate all examples in `quickstart.md` work with implementation

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Quality improvements and final validation

- [ ] T079 [P] Add hot-reload support using watchdog library for `activation.yaml` in `src/cortexgraph/activation/config.py`
- [ ] T080 [P] Performance benchmarking: verify analyze_message <50ms p95 in `tests/performance/test_activation_performance.py`
- [ ] T081 [P] Performance benchmarking: verify analyze_for_recall <50ms p95 in `tests/performance/test_activation_performance.py`
- [ ] T082 [P] Performance benchmarking: verify combined workflow <300ms p95 in `tests/performance/test_activation_performance.py`
- [ ] T083 [P] Security review: ensure no sensitive data leaks in reasoning strings
- [ ] T084 [P] Security review: validate pattern injection prevention
- [ ] T085 Code cleanup: remove any debug logging, finalize error messages
- [ ] T086 Run mypy type checking with zero errors on activation module
- [ ] T087 Run ruff linting with zero errors on activation module
- [ ] T088 Run pytest with ≥90% coverage target on activation module
- [ ] T089 Update `CHANGELOG.md` with v0.7.0 natural language activation feature
- [ ] T090 Run all quickstart.md examples as final validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase - Can start once Phase 2 complete
- **User Story 2 (Phase 4)**: Depends on Foundational phase - Can start in parallel with US1 (different files)
- **User Story 3 (Phase 5)**: Depends on Foundational phase AND US2 (needs recall detection for reinforcement signals)
- **User Story 4 (Phase 6)**: Depends on Foundational phase AND US1/US2 (enhances existing detection logic)
- **CLI Tools (Phase 7)**: Depends on US1 and US2 being complete (needs both tools to work)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundation (Phase 2)
    ├── User Story 1 (US1) - Automatic Memory Capture [P1] ✓ Independent
    ├── User Story 2 (US2) - Contextual Memory Recall [P1] ✓ Independent
    │   └── User Story 3 (US3) - Automatic Memory Reinforcement [P2] (needs US2 for recall detection)
    └── User Story 4 (US4) - Decision Support for Ambiguous Cases [P3] (enhances US1/US2)
```

**Key insight**: US1 and US2 are fully independent and can be developed in parallel. US3 builds on US2 (needs recall to trigger reinforcement). US4 enhances all previous stories.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models (in Foundational) before detectors
- Detectors before MCP tools
- MCP tools before tool registration
- Core implementation before integration tests

### Parallel Opportunities

**Setup Phase (Phase 1)**: Tasks T003, T004, T005, T006 all [P] - different directories

**Foundational Phase (Phase 2)**:
- T008, T009, T010, T011 all [P] - different models in same file (can be written simultaneously)
- T017, T018, T019, T020 all [P] - different test files

**User Story 1 (Phase 3)**:
- T021, T022, T023, T024 all [P] - different test files/functions

**User Story 2 (Phase 4)**:
- T033, T034, T035, T036, T037 all [P] - different test files/functions
- Can run ENTIRE US2 in parallel with US1 (different files, no dependencies)

**User Story 4 (Phase 6)**:
- T058, T059, T060 all [P] - different test files

**CLI Phase (Phase 7)**:
- T071, T072, T073, T074, T075, T076, T077, T078 all [P] - different files

**Polish Phase (Phase 8)**:
- T079, T080, T081, T082, T083, T084 all [P] - different concerns

---

## Parallel Example: User Story 1 + User Story 2

```bash
# These two user stories can be developed completely in parallel:

# Developer A: User Story 1 (Automatic Memory Capture)
Tasks T021-T032: analyze_message tool + save detection
Files: tests/contract/test_analyze_message_api.py
       tests/unit/activation/test_save_detection.py
       tests/integration/activation/test_analyze_message_tool.py
       src/cortexgraph/activation/detectors.py (detect_save_intent, analyze_message)
       src/cortexgraph/tools/analyze_message.py

# Developer B: User Story 2 (Contextual Memory Recall)
Tasks T033-T048: analyze_for_recall tool + recall detection
Files: tests/contract/test_analyze_for_recall_api.py
       tests/unit/activation/test_recall_detection.py
       tests/integration/activation/test_analyze_for_recall_tool.py
       src/cortexgraph/activation/detectors.py (detect_recall_intent, analyze_for_recall)
       src/cortexgraph/activation/patterns.py (query expansion)
       src/cortexgraph/tools/analyze_for_recall.py

# NO file conflicts - completely parallel development!
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (6 tasks)
2. Complete Phase 2: Foundational (14 tasks) - CRITICAL foundation
3. Complete Phase 3: User Story 1 (12 tasks)
4. **STOP and VALIDATE**: Test analyze_message tool independently
   - "I prefer PostgreSQL" → should_save=True, confidence ≥0.7
   - "Nice weather today" → should_save=False
5. Deploy/demo if ready - **system can now detect memory-worthy content!**

**MVP Delivered**: Users can have natural conversations and the system detects when information should be saved, providing confidence scores and suggested parameters. This is immediately useful even without auto-recall.

### Incremental Delivery

1. **Foundation** (Phase 1+2): 20 tasks → All models, patterns, config ready
2. **MVP** (+ Phase 3): 12 tasks → Automatic memory capture working (analyze_message tool)
3. **Enhanced** (+ Phase 4): 16 tasks → Add automatic recall (analyze_for_recall tool)
4. **Intelligent** (+ Phase 5): 9 tasks → Add automatic reinforcement
5. **Polished** (+ Phase 6): 12 tasks → Handle ambiguous cases with reasoning
6. **Production-Ready** (+ Phase 7+8): 20 tasks → CLI tools, docs, performance validation

**Total**: 89 tasks across 8 phases

### Parallel Team Strategy

With 2-3 developers:

1. **Day 1-2**: Everyone completes Setup + Foundational together (20 tasks, foundation MUST be complete)
2. **Day 3-5**: Once Foundational done:
   - Developer A: User Story 1 (12 tasks) - analyze_message tool
   - Developer B: User Story 2 (16 tasks) - analyze_for_recall tool
   - No conflicts! Different files, parallel work
3. **Day 6**: Integration - verify US1 and US2 both work
4. **Day 7-8**: Developer C adds User Story 3 (9 tasks) while A+B do User Story 4 (12 tasks)
5. **Day 9-10**: Everyone works on CLI, docs, polish (20 tasks in parallel)

**Timeline**: ~10 days with 2-3 developers working efficiently

---

## Task Count Summary

| Phase | Task Count | Can Parallelize |
|-------|-----------|----------------|
| Phase 1: Setup | 6 tasks | 4 tasks (67%) |
| Phase 2: Foundational | 14 tasks | 7 tasks (50%) |
| Phase 3: User Story 1 (P1) | 12 tasks | 5 tasks (42%) |
| Phase 4: User Story 2 (P1) | 16 tasks | 7 tasks (44%) |
| Phase 5: User Story 3 (P2) | 9 tasks | 3 tasks (33%) |
| Phase 6: User Story 4 (P3) | 12 tasks | 4 tasks (33%) |
| Phase 7: CLI & Docs | 8 tasks | 8 tasks (100%) |
| Phase 8: Polish | 12 tasks | 6 tasks (50%) |
| **Total** | **89 tasks** | **44 tasks (49%)** |

**MVP Scope** (US1 only): 32 tasks (Setup + Foundational + US1)
**Core Features** (US1 + US2): 48 tasks (add US2)
**Full Feature** (All User Stories): 81 tasks (add US3 + US4 + CLI + Polish)

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group of related tasks
- Stop at any checkpoint to validate story independently
- Foundation phase is CRITICAL - no shortcuts, this blocks everything
- US1 and US2 have no dependencies on each other - true parallel development
- Pattern matching is deterministic - confidence thresholds may need tuning during testing
- All file paths assume single project structure (`src/cortexgraph/`, `tests/`)

---

**Generated**: 2025-01-24
**Feature**: 002-natural-language-activation
**Total Tasks**: 89 tasks across 8 phases
**MVP Tasks**: 32 tasks (Setup + Foundation + US1)
**Parallel Opportunities**: 44 tasks (49% can run in parallel)
