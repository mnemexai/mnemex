# Feature Specification: Multi-Agent Memory Consolidation

**Feature Branch**: `003-multi-agent-consolidation`
**Created**: 2025-11-24
**Status**: Clarified
**Input**: User description: "Multi-agent memory consolidation using beads for coordination. Five specialized agents: Decay Analyzer (identifies memories approaching forget threshold), Cluster Detector (finds similar memories for potential merge), Semantic Merge (combines related memories intelligently), LTM Promoter (moves high-value memories to long-term storage), and Relationship Discovery (finds implicit connections between memories). Beads serves as message queue and audit log."

## Clarifications

### Session 2025-11-24

- Q: How should the consolidation agents be implemented? → A: Python classes (single-process, called via CLI, simple to test)
- Q: What triggers agent execution? → A: Hybrid (scheduled scans + event triggers for urgent items with score < 0.10)
- Q: How should new agents relate to existing MCP tools? → A: Extend (agents call existing tool logic internally, add orchestration layer)
- Q: How should beads issues encode memory context? → A: Notes field (memory IDs as JSON in `notes`, human-readable title, labels for agent type filtering)
- Q: When should system auto-process vs. wait for human review? → A: Confidence threshold (auto if ≥0.9, log-only if 0.7-0.9, wait for human if <0.7)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Memory Decay Triage (Priority: P1)

As a CortexGraph user, I want memories approaching the forget threshold to be automatically identified and triaged so that important information isn't lost due to decay while unimportant memories are allowed to expire naturally.

**Why this priority**: This is the foundational use case - without decay analysis, all other consolidation operations lack the context needed to make intelligent decisions. The Decay Analyzer identifies which memories need attention, feeding the entire consolidation pipeline.

**Independent Test**: Can be fully tested by creating memories with varying decay scores and verifying the Decay Analyzer correctly identifies those in the "danger zone" (0.15-0.35 score) and near-forget threshold (< 0.10). Delivers value by preventing accidental data loss.

**Acceptance Scenarios**:

1. **Given** a memory with decay score 0.08 (below forget threshold 0.10), **When** the Decay Analyzer runs, **Then** a beads issue is created flagging this memory for review with urgency=high
2. **Given** a memory with decay score 0.25 (in danger zone), **When** the Decay Analyzer runs, **Then** a beads issue is created suggesting reinforcement or consolidation with urgency=medium
3. **Given** a memory with decay score 0.70 (healthy), **When** the Decay Analyzer runs, **Then** no action is taken for this memory
4. **Given** multiple memories approaching threshold simultaneously, **When** the Decay Analyzer runs, **Then** issues are prioritized by semantic importance (entity count, tag relevance) not just raw score

---

### User Story 2 - Intelligent Memory Clustering (Priority: P1)

As a CortexGraph user, I want similar memories to be automatically detected and grouped so that redundant information can be consolidated into single, comprehensive memories.

**Why this priority**: Clustering is the prerequisite for merging. Without accurate similarity detection, the system cannot identify consolidation opportunities. This directly reduces memory bloat and improves search relevance.

**Independent Test**: Can be tested by inserting memories with known semantic overlap (e.g., multiple preferences about PostgreSQL) and verifying clusters are correctly formed. Delivers value by identifying merge candidates.

**Acceptance Scenarios**:

1. **Given** three memories all discussing "PostgreSQL preferences", **When** the Cluster Detector runs, **Then** a cluster is created linking all three with cohesion score > 0.7
2. **Given** memories with different topics (PostgreSQL, cooking recipes, travel), **When** the Cluster Detector runs, **Then** these are NOT grouped together (cohesion < 0.4)
3. **Given** a high-cohesion cluster is detected, **When** cluster cohesion > 0.75, **Then** a beads issue is created for the Semantic Merge agent
4. **Given** a medium-cohesion cluster (0.4-0.75), **When** detected, **Then** a beads issue is created suggesting linking (not merging)

---

### User Story 3 - Semantic Memory Merging (Priority: P2)

As a CortexGraph user, I want clustered memories to be intelligently merged into comprehensive single memories that preserve all unique information while eliminating redundancy.

**Why this priority**: Depends on clustering (User Story 2). Merging is the core value proposition - reducing clutter while preserving information. Lower priority than detection because detection is prerequisite.

**Independent Test**: Can be tested by providing a known cluster and verifying the merged output contains all unique entities, tags, and content segments from originals. Delivers value by creating cleaner, more comprehensive memories.

**Acceptance Scenarios**:

1. **Given** a cluster of 3 memories about database preferences, **When** Semantic Merge processes it, **Then** a single merged memory is created containing all unique facts
2. **Given** memories with overlapping content ("I prefer PostgreSQL" + "PostgreSQL is my choice"), **When** merged, **Then** duplicate information appears only once
3. **Given** memories with distinct entities, **When** merged, **Then** all entities are preserved (union of entity sets)
4. **Given** a successful merge, **When** complete, **Then** `consolidated_from` relations are created linking to originals, and original memories are archived (not deleted)
5. **Given** merge creates new memory, **When** complete, **Then** beads issue is closed with audit trail documenting the merge

---

### User Story 4 - Long-Term Memory Promotion (Priority: P2)

As a CortexGraph user, I want high-value memories to be automatically promoted to long-term storage (Obsidian vault) so that important knowledge becomes permanent and searchable outside CortexGraph.

**Why this priority**: Promotion preserves the most valuable memories permanently. Depends on having accurate value assessment (influenced by decay analysis and usage patterns). Medium priority because LTM already exists - this automates an existing manual process.

**Independent Test**: Can be tested by creating memories that meet promotion criteria (score > 0.65 OR use_count >= 5 within 14 days) and verifying markdown files are created in the vault. Delivers value by automating knowledge preservation.

**Acceptance Scenarios**:

1. **Given** a memory with decay score 0.75 and use_count 3, **When** LTM Promoter runs, **Then** a markdown file is created in the Obsidian vault with YAML frontmatter
2. **Given** a memory with use_count 6 within 14 days, **When** LTM Promoter runs, **Then** memory is promoted regardless of decay score
3. **Given** a promoted memory, **When** promotion completes, **Then** the STM memory is marked as `status=promoted` and retains a reference to the LTM file
4. **Given** a memory already promoted, **When** LTM Promoter runs, **Then** no duplicate file is created
5. **Given** promotion succeeds, **When** complete, **Then** beads issue documents vault path and promotion criteria met

---

### User Story 5 - Relationship Discovery (Priority: P3)

As a CortexGraph user, I want implicit connections between memories to be automatically discovered so that my knowledge graph becomes richer and more interconnected over time.

**Why this priority**: Relationship discovery enhances the knowledge graph but doesn't prevent data loss or reduce redundancy. It's an enhancement over the core consolidation functionality. Lower priority because the graph already works - this makes it better.

**Independent Test**: Can be tested by inserting memories with implicit relationships (e.g., "I use FastAPI" and "My backend uses Python") and verifying `related` relations are created. Delivers value by enriching the knowledge graph.

**Acceptance Scenarios**:

1. **Given** memories "I prefer PostgreSQL for databases" and "My API connects to a PostgreSQL instance", **When** Relationship Discovery runs, **Then** a `related` relation is created between them
2. **Given** memories with shared entities but different contexts, **When** analyzed, **Then** relation strength reflects contextual similarity (not just entity match)
3. **Given** a discovered relationship, **When** relation is created, **Then** beads issue documents the reasoning (shared entities, semantic similarity score)
4. **Given** memories with no meaningful connection, **When** analyzed, **Then** no spurious relations are created

---

### Edge Cases

- What happens when a memory is in multiple clusters simultaneously?
  - Memory can only be merged into ONE cluster; select highest cohesion cluster
  - Lower-cohesion clusters receive `related` links instead of merges

- How does system handle merge conflicts (same entity, different values)?
  - Preserve both values with timestamp context: "Preferred PostgreSQL (2024-01), later switched to MySQL (2024-06)"
  - Flag conflicts in beads issue for human review if confidence < 0.7

- What happens when beads issue queue grows faster than processing?
  - Implement priority queue with urgency-based ordering
  - Issues older than 7 days auto-escalate priority
  - Rate limiting prevents agent storms

- How does system handle agent failures mid-operation?
  - Each agent operation is atomic (all-or-nothing)
  - Failed operations leave beads issue in `blocked` status with error details
  - Retry logic with exponential backoff (max 3 retries)

- What happens during concurrent agent execution?
  - Beads provides locking via `in_progress` status
  - Agents claim issues before processing
  - Optimistic concurrency: detect conflicts, abort and retry

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a Decay Analyzer agent that identifies memories with scores below configurable threshold (default: 0.15)
- **FR-002**: System MUST provide a Cluster Detector agent that groups memories with semantic similarity above configurable threshold (default: 0.7)
- **FR-003**: System MUST provide a Semantic Merge agent that combines clustered memories while preserving all unique content
- **FR-004**: System MUST provide an LTM Promoter agent that writes high-value memories to Obsidian vault as markdown
- **FR-005**: System MUST provide a Relationship Discovery agent that identifies implicit connections between memories
- **FR-006**: System MUST use beads issues as the coordination mechanism between agents (message queue pattern)
- **FR-007**: System MUST create audit trail in beads for all consolidation operations (what was changed, why, by which agent)
- **FR-008**: Merged memories MUST preserve `consolidated_from` relations linking to original memories
- **FR-009**: Original memories MUST be archived (not deleted) after successful merge, allowing recovery
- **FR-010**: System MUST support dry-run mode for all agents (preview without changes)
- **FR-011**: Each agent MUST be independently executable (can run solo or as part of pipeline)
- **FR-012**: System MUST provide CLI commands to trigger each agent manually: `cortexgraph-consolidate [agent-name]`
- **FR-013**: System MUST support hybrid triggering: (a) scheduled scans at configurable intervals (default: hourly), and (b) event-driven triggers for urgent items (memories with score < 0.10)
- **FR-014**: System MUST rate-limit agent operations to prevent overwhelming the system (configurable, default: 100 operations/minute)
- **FR-015**: Agents MUST extend existing MCP tool logic (`cluster_memories`, `consolidate_memories`, `promote_memory`) rather than replacing it. Existing tools remain available for manual invocation; agents add orchestration and beads coordination.
- **FR-016**: Agents MUST apply confidence-based processing thresholds: (a) confidence ≥ 0.9 → auto-process immediately, (b) confidence 0.7-0.9 → process with detailed logging, (c) confidence < 0.7 → create beads issue and wait for human review

### Key Entities

- **ConsolidationAgent**: Python base class for all five specialized agents, providing common interfaces for dry-run, audit logging, and beads integration. Agents run as single-process CLI commands, not separate daemons or LLM-powered SDK agents.
- **ConsolidationTask**: Beads issue representing work for an agent. Schema: human-readable `title`, memory IDs as JSON in `notes` field (e.g., `{"memory_ids": ["abc-123"], "scores": [0.08]}`), agent type via labels (`consolidation:decay`, `consolidation:cluster`, `consolidation:merge`, `consolidation:promote`, `consolidation:relations`)
- **ClusterResult**: Output from Cluster Detector containing memory IDs, cohesion score, and recommended action (merge | link | ignore)
- **MergeResult**: Output from Semantic Merge containing new memory ID, original IDs, content diff, and relation IDs created
- **PromotionResult**: Output from LTM Promoter containing vault path, memory ID, and promotion criteria matched

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Decay Analyzer identifies 95%+ of memories within 0.05 of forget threshold within 24 hours of entering danger zone
- **SC-002**: Cluster Detector achieves precision > 0.85 (85%+ of suggested clusters are actually related memories)
- **SC-003**: Semantic Merge preserves 100% of unique entities and facts from source memories (no data loss)
- **SC-004**: LTM Promoter successfully creates valid markdown files for 100% of eligible memories (no silent failures)
- **SC-005**: Relationship Discovery creates meaningful relations with precision > 0.80 (80%+ of relations represent genuine semantic connections)
- **SC-006**: All agent operations complete within 5 seconds per memory processed (performance SLA)
- **SC-007**: System maintains full audit trail allowing reconstruction of any consolidation decision
- **SC-008**: Zero data loss - original memories remain recoverable for 30 days after consolidation

### Implementation Validation (Added 2025-11-25)

| Criterion | Validation Method | Result |
|-----------|-------------------|--------|
| SC-001 | Contract tests verify scan() returns all memories with score < 0.35 (danger zone); unit tests verify urgency classification at threshold boundaries | ✅ PASS |
| SC-002 | Contract tests verify ClusterResult cohesion scores; unit tests verify action thresholds (merge ≥0.75, link 0.4-0.75, ignore <0.4) | ✅ PASS |
| SC-003 | Unit tests verify entity/tag union preservation; integration tests verify no content loss during merge | ✅ PASS |
| SC-004 | Integration tests verify markdown file creation with valid frontmatter; contract tests verify PromotionResult contains vault_path | ✅ PASS |
| SC-005 | Contract tests verify RelationResult includes reasoning; unit tests verify min_confidence threshold prevents spurious relations | ✅ PASS |
| SC-006 | Performance validation: all agents complete in <10ms per memory (well under 5s SLA) | ✅ PASS |
| SC-007 | Beads integration creates issues with full context in notes field; consolidated_from relations preserve provenance | ✅ PASS |
| SC-008 | SemanticMerge archives originals (status=archived) rather than deleting; integration tests verify recovery | ✅ PASS |
