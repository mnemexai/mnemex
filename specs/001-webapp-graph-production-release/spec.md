# Feature Specification: Web-App Graph Visualization and Production Hardening for 1.0.0 Release

**Feature Branch**: `001-webapp-graph-production-release`
**Created**: 2025-11-20
**Status**: Draft
**Input**: User description: "Progress from basic web-app to include relationships and full metadata, add graph visualization similar to Obsidian/Logseq, then production hardening for error handling, resilience, security and supply chain for 1.0.0 release."

## User Scenarios & Testing *(mandatory)*

### User Story 0 - Storage Backend Relationship Parity Verification (Priority: P0 - Spike)

As a developer implementing the graph visualization, I need to verify that JSONL and SQLite backends store and retrieve relationships identically so that the visualization works consistently regardless of which backend users choose.

**Why this priority**: This is a blocking prerequisite (spike) before any visualization work. If the backends have different relationship schemas or behaviors, we must resolve the differences first—otherwise the visualization will break for SQLite users.

**Independent Test**: Can be fully tested by creating identical relationship data in both backends and verifying that queries return identical results through the storage abstraction layer.

**Acceptance Scenarios**:

1. **Given** a set of memories with relationships in JSONL storage, **When** I migrate to SQLite, **Then** all relationship data (type, direction, strength, metadata) is preserved identically
2. **Given** both backends contain identical relationship data, **When** I query relationships through the storage abstraction, **Then** I receive identical results from both backends
3. **Given** both backends are tested, **When** any difference is found, **Then** the difference is documented and a fix is implemented before proceeding to P1

**Spike Output**: Verification report documenting relationship schema parity, any differences found, and remediation completed.

---

### User Story 1 - View Memory Relationships in Web-App (Priority: P1)

As a user reviewing my memory graph, I want to see the relationships between memories (not just isolated memories) so that I can understand how my knowledge connects and identify patterns across my stored information.

**Why this priority**: The current web-app shows memories in isolation. Relationships are the core differentiator of a knowledge graph—without them, users only see a list, not a graph. This is the most critical missing piece for demonstrating CortexGraph's value proposition.

**Independent Test**: Can be fully tested by viewing any memory in the web-app and seeing its connected memories with relationship types. Delivers the "aha moment" of seeing knowledge as a connected graph rather than isolated notes.

**Acceptance Scenarios**:

1. **Given** a memory with related memories exists, **When** I view that memory in the web-app, **Then** I see a list of related memories with their relationship types (e.g., "causes", "supports", "contradicts", "consolidated_from")
2. **Given** I am viewing memory relationships, **When** I click on a related memory, **Then** I navigate to that memory's detail view
3. **Given** a memory has no relationships, **When** I view that memory, **Then** I see an appropriate message indicating no connections exist

---

### User Story 2 - Interactive Graph Visualization (Priority: P2)

As a user exploring my knowledge base, I want to see an interactive visual graph of my memories (similar to Obsidian/Logseq graph view) so that I can visually navigate connections, identify clusters, and discover unexpected relationships.

**Why this priority**: Visual graph exploration is what makes knowledge graphs intuitive and powerful. This transforms CortexGraph from a memory storage system into a true knowledge exploration tool. Depends on relationships being visible (P1) but adds significant user value.

**Independent Test**: Can be fully tested by opening the graph visualization and visually navigating between memory nodes by clicking/dragging. Delivers visual discovery of knowledge patterns that text lists cannot provide.

**Acceptance Scenarios**:

1. **Given** my memory store contains memories with relationships, **When** I open the graph visualization, **Then** I see memories as nodes and relationships as edges in an interactive canvas
2. **Given** the graph is displayed, **When** I click on a memory node, **Then** I see that memory's details (content preview, metadata, decay score)
3. **Given** the graph is displayed, **When** I drag nodes, **Then** the graph layout updates smoothly and maintains visual clarity
4. **Given** my memory store is large (1000+ memories), **When** I open the graph, **Then** the visualization loads within 3 seconds and remains responsive
5. **Given** a memory has a low decay score (near forget threshold), **When** I view the graph, **Then** that memory node is visually distinguished (e.g., faded opacity, different color)

---

### User Story 3 - Full Metadata Display (Priority: P3)

As a user reviewing my memories, I want to see complete metadata for each memory (tags, entities, decay score, use count, created/updated timestamps, source, context) so that I can understand memory importance and make informed decisions about promotion or deletion.

**Why this priority**: Metadata visibility enables informed decision-making about memory management. Users need this information to understand why certain memories persist and others decay. Lower priority than relationships and visualization because the current web-app already shows basic memory content.

**Independent Test**: Can be fully tested by viewing any memory and seeing all its metadata fields rendered in a clear, organized layout. Delivers transparency into the memory system's decision-making.

**Acceptance Scenarios**:

1. **Given** I am viewing a memory detail, **When** the view loads, **Then** I see: content, tags, entities, decay score, use count, review count, strength, created_at, last_used, source, context, and status
2. **Given** I am viewing memory metadata, **When** the memory has been promoted to LTM, **Then** I see the promotion status and vault file path
3. **Given** I am viewing memory metadata, **When** any field is empty/null, **Then** that field shows a clear "Not set" indicator rather than being hidden

---

### User Story 4 - Error Resilience (Priority: P4)

As a user of CortexGraph in production, I want the system to handle errors gracefully (corrupted storage, network issues, malformed data) so that I never lose my memories and always receive helpful error messages.

**Why this priority**: Production hardening is essential for 1.0.0 release. Users must trust that their memories are safe. This is a non-negotiable gate for production readiness but is lower priority than the user-facing features that define 1.0.0 value.

**Independent Test**: Can be fully tested by simulating various failure modes (corrupt JSONL, missing files, invalid data) and verifying the system recovers or fails gracefully with actionable messages.

**Acceptance Scenarios**:

1. **Given** the JSONL storage file is corrupted, **When** CortexGraph starts, **Then** it detects the corruption, attempts recovery, and reports a clear error with recovery instructions
2. **Given** a memory operation fails, **When** the error occurs, **Then** the user receives an actionable error message (not a stack trace) with specific remediation steps
3. **Given** the web-app loses connection to the backend, **When** network is restored, **Then** the app automatically reconnects without requiring a page refresh
4. **Given** a memory contains malformed data, **When** I attempt to load it, **Then** the system loads what it can and clearly indicates which fields failed validation

---

### User Story 5 - Security Hardening (Priority: P5)

As a user storing personal memories locally, I want CortexGraph to follow security best practices (input validation, safe defaults, dependency verification) so that my memory data remains private and the system cannot be exploited.

**Why this priority**: Security is essential for production release and user trust. Local-first architecture already provides privacy, but hardening prevents exploitation through malicious inputs or compromised dependencies.

**Independent Test**: Can be fully tested by running security scans (bandit, safety), attempting injection attacks, and verifying all inputs are validated. Delivers confidence that the system is production-safe.

**Acceptance Scenarios**:

1. **Given** user input is provided to any MCP tool or API endpoint, **When** the input contains potentially malicious content (injection attempts, path traversal), **Then** the system validates and sanitizes the input before processing
2. **Given** I am building CortexGraph from source, **When** dependencies are installed, **Then** all dependencies are pinned and verified against known vulnerability databases
3. **Given** CortexGraph is running, **When** security scanning tools are executed, **Then** no high or critical vulnerabilities are reported in CortexGraph code

---

### User Story 6 - Supply Chain Hardening (Priority: P6)

As a user or contributor installing CortexGraph, I want verifiable builds, SBOMs (Software Bill of Materials), and signed releases so that I can trust the software I'm running hasn't been tampered with.

**Why this priority**: Supply chain security is increasingly important for production software. This completes the production hardening story but is the lowest priority as it affects distribution rather than core functionality.

**Independent Test**: Can be fully tested by verifying release signatures, reviewing SBOMs, and confirming reproducible builds from tagged releases. Delivers trust in the distribution pipeline.

**Acceptance Scenarios**:

1. **Given** a new release is published, **When** I download it, **Then** I can verify the release signature against the published public key
2. **Given** a release is available, **When** I request the SBOM, **Then** I receive a complete inventory of all dependencies with their versions and licenses
3. **Given** I have the source code at a release tag, **When** I build the package, **Then** I can reproduce the same artifact as the published release (reproducible builds)

---

### Edge Cases

- What happens when the graph visualization has thousands of nodes? System must implement level-of-detail or filtering to remain responsive.
- How does the system handle circular relationships (A→B→C→A)? Graph visualization must handle cycles without infinite loops.
- What happens when promoting a memory with broken relationship references? System must validate referential integrity before promotion.
- How does error recovery work when both JSONL and backup are corrupted? System must provide manual recovery documentation.
- What happens when a user attempts to inject malicious content through the web-app search field? All inputs must be validated and sanitized.

## Requirements *(mandatory)*

### Functional Requirements

**Web-App Enhancement**:

- **FR-001**: Web-app MUST display all relationships for a memory, including relationship type, direction, and strength
- **FR-002**: Web-app MUST provide interactive graph visualization with pan, zoom, drag, and click interactions
- **FR-003**: Graph visualization MUST distinguish memory nodes by status (active, promoted, archived) and decay score
- **FR-004**: Web-app MUST display complete metadata for each memory including all fields from the Memory model
- **FR-005**: Graph visualization MUST support filtering by tags, entities, date range, and decay score threshold
- **FR-006**: Web-app MUST provide memory search that queries both content and metadata fields

**Production Hardening - Error Handling**:

- **FR-007**: System MUST validate all user inputs against defined schemas before processing
- **FR-008**: System MUST provide actionable error messages that include: what went wrong, why it happened, and how to fix it
- **FR-009**: System MUST implement automatic retry with exponential backoff for transient failures
- **FR-010**: System MUST detect and report storage corruption with recovery instructions

**Production Hardening - Security**:

- **FR-011**: System MUST sanitize all inputs to prevent injection attacks (path traversal, command injection)
- **FR-012**: System MUST implement rate limiting on web-app API endpoints
- **FR-013**: System MUST log all errors and security-relevant events with appropriate detail (without exposing sensitive data)
- **FR-014**: System MUST run with minimum required permissions (principle of least privilege)

**Production Hardening - Supply Chain**:

- **FR-015**: Releases MUST include cryptographic signatures verifiable with published keys
- **FR-016**: Releases MUST include SBOM in CycloneDX or SPDX format
- **FR-017**: CI/CD pipeline MUST scan dependencies for known vulnerabilities before release
- **FR-018**: System MUST pin all dependency versions in lockfiles

### Key Entities

- **Memory**: Core data unit with content, metadata (tags, entities, strength, timestamps), decay score, and relationships to other memories
- **Relation**: Connection between two memories with type (related, causes, supports, contradicts, has_decision, consolidated_from), strength, and optional metadata
- **GraphNode**: Visual representation of a memory in the graph visualization with position, size, color based on memory properties
- **GraphEdge**: Visual representation of a relation with direction, weight, and style based on relation type

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify all relationships for any memory within 2 seconds of opening its detail view
- **SC-002**: Graph visualization loads and becomes interactive within 3 seconds for stores up to 10,000 memories
- **SC-003**: Users can navigate from any memory to any connected memory within 2 clicks (detail view → relationship → target memory)
- **SC-004**: 100% of user-facing errors include actionable remediation steps (no raw stack traces)
- **SC-005**: System passes security scanning with zero high/critical vulnerabilities in CortexGraph code
- **SC-006**: All releases include verifiable signatures and complete SBOMs
- **SC-007**: Web-app remains responsive (< 100ms interaction latency) during graph exploration with 1000+ visible nodes
- **SC-008**: System recovers from storage corruption in 95% of cases without data loss (validated through fault injection testing)

## Clarifications

### Session 2025-11-20

- Q: Should relationship display work identically regardless of storage backend (JSONL, SQLite)? → A: Storage-agnostic via existing abstraction (web-app reads through storage layer, backend transparent)
- Q: Should we verify backend parity before visualization? → A: Yes, add P0 spike to verify JSONL and SQLite store relationships identically (work-alike backends)

## Assumptions

- Relationships already exist in JSONL storage (via `relations.jsonl`) and the web-app exposes these existing relationships through the storage abstraction layer
- Storage backend is transparent to the web-app—relationship display works identically on JSONL, SQLite, or future backends
- Graph visualization will use a force-directed layout algorithm (standard for knowledge graph visualization)
- Security scanning uses Bandit for Python code analysis (already configured in CI)
- SBOM generation uses CycloneDX format (already generating in CI workflow)
- Rate limiting applies to web-app API only (MCP tools are local and don't need rate limiting)
- Reproducible builds target PyPI wheel format
- Error recovery prioritizes data preservation over automatic correction
