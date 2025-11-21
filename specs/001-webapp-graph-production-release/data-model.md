# Data Model: Web-App Graph Visualization and Production Hardening

**Feature**: 001-webapp-graph-production-release
**Date**: 2025-11-20
**Status**: Complete

## Overview

This document defines the data models for graph visualization and production hardening features. All models use Pydantic for validation, aligning with the constitution's type safety requirements.

## Core Entities

### Memory (Existing - Extended)

The existing `Memory` model in `src/cortexgraph/storage/models.py` contains all fields needed for metadata display (P3). No structural changes required.

```python
class Memory(BaseModel):
    """A memory unit with temporal decay properties."""

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))

    # Content
    content: str
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)

    # Metadata
    source: str | None = None
    context: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    # Temporal decay
    created_at: int = Field(default_factory=lambda: int(time.time()))
    last_used: int = Field(default_factory=lambda: int(time.time()))
    use_count: int = 1
    strength: float = Field(default=1.0, ge=0, le=2.0)

    # Spaced repetition (v0.5.1+)
    review_priority: float = Field(default=0.0, ge=0, le=1)
    last_review_at: int | None = None
    review_count: int = 0
    cross_domain_count: int = 0

    # Status
    status: MemoryStatus = MemoryStatus.ACTIVE
    embedding: list[float] | None = None
```

**Display in Web-App** (P3 - Full Metadata):
- All fields rendered in detail panel
- Null/empty fields shown as "Not set"
- Timestamps formatted as human-readable dates
- Decay score calculated and displayed (not stored)

---

### Relation (Existing - No Changes)

The existing `Relation` model handles all relationship types.

```python
class Relation(BaseModel):
    """A directed relationship between two memories."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    from_memory_id: str
    to_memory_id: str
    relation_type: RelationType  # related, causes, supports, contradicts, has_decision, consolidated_from
    strength: float = Field(default=1.0, ge=0, le=2.0)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    metadata: dict[str, Any] = Field(default_factory=dict)
```

---

### GraphNode (New - Visualization)

Represents a memory as a visual node in the graph.

```python
class GraphNode(BaseModel):
    """Visual representation of a memory in graph visualization."""

    # Identity (from Memory)
    id: str

    # Display properties
    label: str  # Truncated content for display
    tags: list[str]
    entities: list[str]

    # Visual encoding
    status: MemoryStatus  # Determines color
    decay_score: float  # Determines opacity (0.05-1.0)
    use_count: int  # Determines size

    # Layout (optional, user-saved)
    x: float | None = None
    y: float | None = None
    fx: float | None = None  # Fixed x (user pinned)
    fy: float | None = None  # Fixed y (user pinned)

    # Timestamps for tooltips
    created_at: int
    last_used: int


def memory_to_graph_node(memory: Memory, decay_score: float) -> GraphNode:
    """Convert a Memory to a GraphNode for visualization."""
    return GraphNode(
        id=memory.id,
        label=memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
        tags=memory.tags,
        entities=memory.entities,
        status=memory.status,
        decay_score=decay_score,
        use_count=memory.use_count,
        created_at=memory.created_at,
        last_used=memory.last_used,
    )
```

**Visual Encoding**:
| Property | Visual Attribute | Mapping |
|----------|-----------------|---------|
| status | Color | active=#4CAF50, promoted=#2196F3, archived=#9E9E9E |
| decay_score | Opacity | 0.05 → 0.3, 1.0 → 1.0 (linear) |
| use_count | Size | 1 → 8px, 10+ → 20px (log scale) |
| relation_count | Border | 0 → none, 5+ → thick |

---

### GraphEdge (New - Visualization)

Represents a relation as a visual edge in the graph.

```python
class GraphEdge(BaseModel):
    """Visual representation of a relation in graph visualization."""

    # Identity (from Relation)
    id: str
    source: str  # from_memory_id
    target: str  # to_memory_id

    # Display properties
    relation_type: RelationType
    strength: float  # Determines thickness

    # Computed for rendering
    directed: bool = True  # All CortexGraph relations are directed


def relation_to_graph_edge(relation: Relation) -> GraphEdge:
    """Convert a Relation to a GraphEdge for visualization."""
    return GraphEdge(
        id=relation.id,
        source=relation.from_memory_id,
        target=relation.to_memory_id,
        relation_type=relation.relation_type,
        strength=relation.strength,
    )
```

**Visual Encoding**:
| Property | Visual Attribute | Mapping |
|----------|-----------------|---------|
| relation_type | Color | related=#666, causes=#FF9800, supports=#4CAF50, contradicts=#F44336 |
| strength | Thickness | 0.0 → 1px, 2.0 → 4px |
| directed | Arrow | Yes → arrowhead |

---

### GraphData (New - API Response)

Container for full graph visualization data.

```python
class GraphData(BaseModel):
    """Complete graph structure for visualization."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]

    # Statistics
    total_memories: int
    total_relations: int
    filtered_count: int | None = None  # If filters applied

    # Performance
    query_time_ms: float


class GraphResponse(BaseModel):
    """API response wrapper for graph data."""

    success: bool = True
    data: GraphData
```

---

### GraphFilter (New - Query Parameters)

Filtering parameters for graph queries.

```python
class GraphFilter(BaseModel):
    """Filters for graph visualization queries."""

    # Content filters
    tags: list[str] | None = None
    entities: list[str] | None = None
    search_query: str | None = None

    # Score filters
    min_decay_score: float = Field(default=0.0, ge=0, le=1)

    # Time filters
    created_after: int | None = None
    created_before: int | None = None
    used_after: int | None = None

    # Status filter
    statuses: list[MemoryStatus] | None = None  # Default: [ACTIVE]

    # Pagination (for large graphs)
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)
```

---

## Error Handling Models

### ErrorResponse (New - Production Hardening)

Standardized error response format (FR-008).

```python
class ErrorContext(BaseModel):
    """Additional context for error diagnosis."""

    file: str | None = None
    line: int | None = None
    memory_id: str | None = None
    parameter: str | None = None
    value: Any | None = None


class ErrorDetail(BaseModel):
    """Detailed error information with remediation."""

    code: str  # Machine-readable error code
    message: str  # Human-readable description
    remediation: str  # How to fix it
    context: ErrorContext | None = None


class ErrorResponse(BaseModel):
    """API response wrapper for errors."""

    success: bool = False
    error: ErrorDetail
```

**Error Code Enumeration**:
```python
class ErrorCode(str, Enum):
    """Standardized error codes for CortexGraph."""

    # Storage errors
    STORAGE_NOT_FOUND = "STORAGE_NOT_FOUND"
    STORAGE_CORRUPTION = "STORAGE_CORRUPTION"
    STORAGE_PERMISSION = "STORAGE_PERMISSION"

    # Validation errors
    INVALID_MEMORY_ID = "INVALID_MEMORY_ID"
    INVALID_RELATION_TYPE = "INVALID_RELATION_TYPE"
    VALIDATION_FAILED = "VALIDATION_FAILED"

    # Operation errors
    MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
    RELATION_NOT_FOUND = "RELATION_NOT_FOUND"
    DUPLICATE_RELATION = "DUPLICATE_RELATION"

    # Security errors
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_INPUT = "INVALID_INPUT"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
```

---

### ValidationResult (New - Storage Validation)

Result of storage file validation (FR-010).

```python
class CorruptionDetail(BaseModel):
    """Details about a specific corruption issue."""

    line: int
    error: str
    raw_content: str | None = None  # Truncated for safety


class ValidationResult(BaseModel):
    """Result of storage file validation."""

    valid: bool
    file_path: str
    total_lines: int
    valid_lines: int
    errors: list[CorruptionDetail] = Field(default_factory=list)

    @property
    def error_rate(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return len(self.errors) / self.total_lines


class StorageHealthReport(BaseModel):
    """Complete health report for storage system."""

    memories_validation: ValidationResult
    relations_validation: ValidationResult
    index_status: str  # "healthy", "stale", "missing"
    last_backup: int | None = None
    recommendations: list[str] = Field(default_factory=list)
```

---

## Security Models

### RateLimitInfo (New - Rate Limiting)

Information about rate limiting state.

```python
class RateLimitInfo(BaseModel):
    """Rate limiting information for API responses."""

    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: int | None = None  # Seconds until reset (if limited)
```

---

### SecurityEvent (New - Audit Logging)

Security-relevant events for logging (FR-013).

```python
class SecurityEventType(str, Enum):
    """Types of security-relevant events."""

    RATE_LIMITED = "rate_limited"
    INVALID_INPUT = "invalid_input"
    STORAGE_ACCESS = "storage_access"
    VALIDATION_FAILURE = "validation_failure"
    RECOVERY_ATTEMPT = "recovery_attempt"


class SecurityEvent(BaseModel):
    """A security-relevant event for audit logging."""

    timestamp: int = Field(default_factory=lambda: int(time.time()))
    event_type: SecurityEventType
    source_ip: str | None = None
    endpoint: str
    details: dict[str, Any] = Field(default_factory=dict)

    # Never log sensitive data
    # No memory content, no full paths, no credentials
```

---

## Relationships Between Models

```
┌─────────────┐     1:N     ┌──────────────┐
│   Memory    │◄───────────►│   Relation   │
│             │             │              │
│  (storage)  │             │   (storage)  │
└──────┬──────┘             └──────┬───────┘
       │                           │
       │ transform                 │ transform
       ▼                           ▼
┌─────────────┐             ┌──────────────┐
│  GraphNode  │             │  GraphEdge   │
│             │◄───────────►│              │
│   (view)    │   source/   │    (view)    │
└─────────────┘   target    └──────────────┘
       │                           │
       │                           │
       ▼                           ▼
┌─────────────────────────────────────────┐
│              GraphData                   │
│                                          │
│  nodes: list[GraphNode]                  │
│  edges: list[GraphEdge]                  │
│  stats: ...                              │
└─────────────────────────────────────────┘
```

---

## Model Location

All new models will be added to `src/cortexgraph/storage/models.py` to maintain single source of truth for data structures. This follows the existing pattern and ensures:

1. Type hints available throughout codebase
2. Pydantic validation on all data
3. Easy import: `from cortexgraph.storage.models import GraphNode, GraphEdge`

---

## Backward Compatibility

**No breaking changes**:
- Existing Memory and Relation models unchanged
- New models are additive
- API responses wrapped in new structures (success/error pattern)
- Old clients can ignore new fields

**Migration path**:
- v0.7.x → v1.0.0: No data migration required
- API consumers should update to expect new response format
- Old response format deprecated but available via header `Accept: application/json; version=0.7`
