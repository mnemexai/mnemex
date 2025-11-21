# Research: Web-App Graph Visualization and Production Hardening

**Feature**: 001-webapp-graph-production-release
**Date**: 2025-11-20
**Status**: Complete

## Executive Summary

This research document captures technology decisions, library selections, and architectural patterns for implementing graph visualization and production hardening in CortexGraph 1.0.0. All decisions align with the constitution's code quality, testing, UX consistency, and performance requirements.

## Technology Decisions

### 1. Graph Visualization Library

**Decision**: D3.js with d3-force for force-directed layouts

**Alternatives Considered**:
- **Cytoscape.js**: More graph-specific but heavier (280KB minified)
- **Vis.js**: Good for networks but outdated maintenance
- **Sigma.js**: WebGL-based, overkill for 10k nodes
- **Force Graph (3D)**: Too complex for initial implementation

**Rationale**:
- D3.js is already widely used, well-documented (SC-002 testability)
- Force-directed layout is industry standard for knowledge graphs (Assumption in spec)
- Lightweight (~87KB minified core + force module)
- Excellent performance for target scale (1000+ nodes with <100ms interaction)
- Vanilla JavaScript - no framework lock-in
- Canvas rendering option for large graphs

**Implementation Approach**:
```javascript
// Basic structure
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id))
  .force("charge", d3.forceManyBody().strength(-100))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide().radius(30));
```

**Performance Optimizations**:
- Use `alphaDecay` to settle quickly (default 0.0228)
- Implement level-of-detail (LOD) for >500 nodes
- Canvas rendering fallback for >1000 nodes
- Web Workers for layout calculations if needed

---

### 2. API Endpoints Architecture

**Decision**: Extend existing FastAPI routes with dedicated relationship and graph endpoints

**New Endpoints**:
```
GET  /api/memories/{id}/relationships  - Get memory's relationships
GET  /api/graph                        - Get full graph structure
GET  /api/graph/filtered               - Get filtered graph (tags, score, date)
POST /api/graph/layout                 - Save user's custom layout positions
```

**Response Format** (consistent with FR-002 UX requirements):
```json
{
  "success": true,
  "data": {
    "nodes": [...],
    "edges": [...],
    "stats": {
      "total_nodes": 1000,
      "total_edges": 2500,
      "render_time_ms": 45
    }
  }
}
```

**Error Format** (FR-008 actionable errors):
```json
{
  "success": false,
  "error": {
    "code": "STORAGE_CORRUPTION",
    "message": "Memory file contains invalid JSON at line 42",
    "remediation": "Run 'cortexgraph-maintenance repair' to attempt automatic recovery",
    "context": {
      "file": "~/.config/cortexgraph/jsonl/memories.jsonl",
      "line": 42
    }
  }
}
```

---

### 3. Storage Backend Parity Verification (P0 Spike)

**Decision**: Create comprehensive parity test suite before visualization work

**Verification Approach**:
1. Define canonical relationship test cases (all 6 types)
2. Create identical data in both backends via storage abstraction
3. Query through abstraction layer
4. Assert identical results (structure, values, ordering)

**Test Cases**:
```python
RELATIONSHIP_PARITY_TESTS = [
    # Basic relationship types
    ("related", {"strength": 1.0}),
    ("causes", {"strength": 0.8}),
    ("supports", {"strength": 0.7}),
    ("contradicts", {"strength": 0.6}),
    ("has_decision", {"strength": 0.9}),
    ("consolidated_from", {"strength": 1.0, "metadata": {"cluster_id": "xyz"}}),

    # Edge cases
    ("related", {"strength": 0.0}),  # Minimum strength
    ("related", {"strength": 2.0}),  # Maximum strength
    ("related", {"metadata": {"key": "value with unicode: 日本語"}}),
]
```

**Expected Output**:
- `specs/001-webapp-graph-production-release/spike-report.md`
- Documents any differences found
- Remediation completed before P1 work begins

---

### 4. Security Scanning Configuration

**Decision**: Bandit with custom configuration for CortexGraph patterns

**Bandit Configuration** (`.bandit`):
```yaml
skips:
  - B101  # assert_used - OK in tests
  - B404  # subprocess - we control inputs

targets:
  - src/cortexgraph

exclude_dirs:
  - tests
  - .venv
  - build

severity:
  - HIGH
  - CRITICAL  # Block on these
```

**Additional Security Tools**:
- **Safety**: Dependency vulnerability scanning (already in CI)
- **pip-audit**: Alternative dependency scanner

**Rate Limiting Implementation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/graph")
@limiter.limit("30/minute")  # Reasonable for local use
async def get_graph():
    ...
```

---

### 5. SBOM Generation

**Decision**: CycloneDX format via cyclonedx-bom tool (already in CI)

**Current CI Workflow** (`.github/workflows/security.yml`):
```yaml
- name: Generate SBOM
  run: |
    pip install cyclonedx-bom
    cyclonedx-py environment -o sbom.json --format json
```

**Enhancement for FR-016**:
- Include in GitHub Release artifacts
- Add SPDX format option for compliance
- Document how to verify components

---

### 6. Error Recovery Strategy

**Decision**: Layered recovery with user-controlled actions

**Recovery Hierarchy**:
1. **Auto-recover**: Missing indexes, stale caches
2. **Prompt user**: Corrupted single memory (skip or delete)
3. **Manual intervention**: Full storage corruption

**JSONL Corruption Detection**:
```python
def validate_jsonl_file(path: Path) -> ValidationResult:
    errors = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(CorruptionError(line=i, error=str(e)))
    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

**Recovery Commands**:
```bash
cortexgraph-maintenance validate   # Check for corruption
cortexgraph-maintenance repair     # Attempt auto-fix
cortexgraph-maintenance backup     # Create snapshot before repair
```

---

### 7. Web-App State Management

**Decision**: Vanilla JavaScript with minimal state (no framework)

**Rationale**:
- Existing web-app is vanilla JS/HTML
- Graph visualization is mostly D3-managed state
- Avoids framework churn and build complexity
- Aligns with project simplicity goals

**State Structure**:
```javascript
const appState = {
  memories: [],           // Current visible memories
  relations: [],          // Current visible relations
  selectedMemory: null,   // Detail view target
  filters: {
    tags: [],
    minScore: 0,
    dateRange: null
  },
  layout: {
    positions: {},        // User-saved node positions
    zoom: 1,
    pan: { x: 0, y: 0 }
  }
};
```

---

## Library Dependencies

### Production Dependencies (to add)

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| d3 | ^7.8.5 | Graph visualization | ISC |
| slowapi | ^0.1.9 | Rate limiting | MIT |

### Development Dependencies (existing)

Already have: pytest, pytest-cov, pytest-asyncio, mypy, ruff, bandit

### Frontend (no npm/build step)

D3.js will be loaded via CDN or vendored in `src/cortexgraph/web/static/lib/`:
```html
<script src="/static/lib/d3.v7.min.js"></script>
```

---

## Performance Benchmarks

### Target Metrics (from spec)

| Operation | Target | Measurement Point |
|-----------|--------|-------------------|
| Graph load | <3s | Time from request to interactive |
| Node interaction | <100ms | Click → detail panel render |
| Filter application | <500ms | Filter change → graph re-render |
| Drag/pan | 60fps | Continuous interaction |

### Baseline Measurements (to capture in spike)

Will benchmark existing operations:
- `read_graph` current performance
- `search_memory` with relationship expansion
- Frontend rendering with test data sets (100, 500, 1000, 5000 nodes)

---

## Risk Mitigation

### Performance Risk: Large Graphs

**Risk**: Graph with 10,000 nodes may exceed <3s load time

**Mitigations**:
1. Progressive loading (show subset, load more on demand)
2. Server-side filtering (don't send all nodes)
3. Level-of-detail rendering (simplify distant nodes)
4. Canvas rendering for >1000 nodes
5. Pagination for memory list (already exists)

### Security Risk: Input Validation

**Risk**: XSS through memory content displayed in graph

**Mitigations**:
1. All content rendered as text nodes (not innerHTML)
2. Content preview truncation with sanitization
3. CSP headers restricting inline scripts
4. Input validation on save (existing)

### Compatibility Risk: Backend Parity

**Risk**: SQLite and JSONL store relationships differently

**Mitigations**:
1. P0 spike verifies parity before implementation
2. All queries go through storage abstraction
3. Integration tests run on both backends
4. Document any unavoidable differences

---

## References

### Internal
- [Feature Specification](spec.md)
- [Implementation Plan](plan.md)
- [Constitution](../../.specify/memory/constitution.md)

### External
- [D3.js Force Documentation](https://d3js.org/d3-force)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/advanced/)
- [CycloneDX Specification](https://cyclonedx.org/specification/overview/)
- [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [Bandit Documentation](https://bandit.readthedocs.io/)
