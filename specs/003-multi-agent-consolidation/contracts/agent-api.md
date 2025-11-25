# Agent API Contracts

**Phase**: 1 (Design) | **Date**: 2025-11-24

## CLI Interface Contract

### Entry Point: `cortexgraph-consolidate`

**Pattern**: `cortexgraph-consolidate [OPTIONS] COMMAND [ARGS]`

#### Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | flag | `false` | Preview without making changes |
| `--json` | flag | `false` | Output JSON instead of human-readable |
| `--rate-limit` | int | `100` | Max operations per minute |
| `--verbose` / `-v` | flag | `false` | Verbose logging |
| `--help` | flag | - | Show help message |

#### Commands

##### `run`

Run one or more agents.

```bash
# Run all agents in pipeline order
cortexgraph-consolidate run --all

# Run specific agent
cortexgraph-consolidate run decay
cortexgraph-consolidate run cluster
cortexgraph-consolidate run merge
cortexgraph-consolidate run promote
cortexgraph-consolidate run relations

# Dry run with JSON output
cortexgraph-consolidate --dry-run --json run decay
```

**Exit Codes**:
- `0`: Success
- `1`: Error (see stderr for details)
- `2`: Invalid arguments

##### `status`

Check agent and queue status.

```bash
# Show pending issues per agent
cortexgraph-consolidate status

# Show specific agent queue
cortexgraph-consolidate status decay --json
```

**Output Schema** (JSON mode):
```json
{
  "agents": {
    "decay": {"pending": 5, "in_progress": 1, "blocked": 0},
    "cluster": {"pending": 2, "in_progress": 0, "blocked": 0},
    "merge": {"pending": 1, "in_progress": 0, "blocked": 0},
    "promote": {"pending": 0, "in_progress": 0, "blocked": 0},
    "relations": {"pending": 3, "in_progress": 0, "blocked": 0}
  },
  "total_pending": 11,
  "rate_limit_remaining": 89
}
```

##### `process`

Process a specific beads issue.

```bash
# Process by issue ID
cortexgraph-consolidate process cortexgraph-abc123

# Process with dry-run
cortexgraph-consolidate --dry-run process cortexgraph-abc123
```

---

## Python API Contract

### ConsolidationAgent (Abstract Base)

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class ConsolidationAgent(ABC, Generic[T]):
    """Abstract base class for consolidation agents.

    All agents MUST inherit from this class and implement:
    - scan(): Find items needing processing
    - process_item(): Process a single item
    """

    def __init__(
        self,
        dry_run: bool = False,
        rate_limit: int = 100,
        confidence_config: ConfidenceConfig | None = None,
    ) -> None:
        """Initialize agent.

        Args:
            dry_run: If True, preview without making changes
            rate_limit: Max operations per minute
            confidence_config: Thresholds for auto/log/wait decisions
        """
        ...

    @abstractmethod
    def scan(self) -> list[str]:
        """Scan for items needing processing.

        Returns:
            List of memory IDs to process

        Contract:
            - MUST return list (may be empty)
            - MUST NOT modify any data
            - SHOULD complete within 5 seconds
        """
        ...

    @abstractmethod
    def process_item(self, memory_id: str) -> T:
        """Process a single memory.

        Args:
            memory_id: UUID of memory to process

        Returns:
            Result model (agent-specific)

        Contract:
            - MUST return result model or raise exception
            - If dry_run=True, MUST NOT modify any data
            - MUST create beads issue for audit trail
            - SHOULD complete within 5 seconds
        """
        ...

    def run(self) -> list[T]:
        """Execute agent on all scanned items.

        Returns:
            List of results from process_item calls

        Contract:
            - MUST respect rate_limit
            - MUST call scan() then process_item() for each
            - MUST handle exceptions per-item (don't abort all)
        """
        ...
```

### Agent-Specific Contracts

#### DecayAnalyzer

```python
class DecayAnalyzer(ConsolidationAgent[DecayResult]):
    """Identifies memories approaching forget threshold.

    Scan Contract:
        - MUST find memories with score < DANGER_ZONE_MAX (0.35)
        - MUST prioritize by urgency (score < 0.10 first)
        - MUST NOT return memories already being processed

    Process Contract:
        - MUST calculate current decay score
        - MUST determine urgency level
        - MUST recommend action (reinforce/consolidate/promote/gc)
        - MUST create beads issue for urgent items (< 0.10)
    """
```

#### ClusterDetector

```python
class ClusterDetector(ConsolidationAgent[ClusterResult]):
    """Finds similar memories for potential merge.

    Scan Contract:
        - MUST find memories with potential clusters
        - MUST NOT return already-clustered memories
        - MAY use embeddings if enabled

    Process Contract:
        - MUST calculate cohesion score
        - MUST determine action (merge/link/ignore)
        - MUST create beads issue if cohesion >= 0.4
        - MUST NOT create duplicate clusters
    """
```

#### SemanticMerge

```python
class SemanticMerge(ConsolidationAgent[MergeResult]):
    """Combines clustered memories intelligently.

    Scan Contract:
        - MUST only process from beads issues (not free scan)
        - MUST filter for consolidation:merge label

    Process Contract:
        - MUST preserve all unique entities
        - MUST preserve all unique content
        - MUST create consolidated_from relations
        - MUST archive (not delete) originals
        - MUST close beads issue on success
    """
```

#### LTMPromoter

```python
class LTMPromoter(ConsolidationAgent[PromotionResult]):
    """Moves high-value memories to long-term storage.

    Scan Contract:
        - MUST find memories meeting promotion criteria
        - MUST NOT return already-promoted memories

    Process Contract:
        - MUST write valid markdown to vault
        - MUST set memory status to 'promoted'
        - MUST store vault_path reference
        - MUST NOT create duplicate vault files
    """
```

#### RelationshipDiscovery

```python
class RelationshipDiscovery(ConsolidationAgent[RelationResult]):
    """Finds implicit connections between memories.

    Scan Contract:
        - MUST find memories with potential connections
        - MUST NOT return already-related pairs

    Process Contract:
        - MUST calculate relation strength
        - MUST provide reasoning for relation
        - MUST respect confidence threshold
        - MUST NOT create spurious relations (precision > 0.8)
    """
```

---

## Beads Integration Contract

### Issue Creation

```python
def create_consolidation_issue(
    agent: str,
    memory_ids: list[str],
    action: str,
    urgency: str = "medium",
    extra_data: dict | None = None,
) -> str:
    """Create a beads issue for consolidation work.

    Args:
        agent: Agent type (decay/cluster/merge/promote/relations)
        memory_ids: Memory UUIDs involved
        action: Recommended action
        urgency: high/medium/low
        extra_data: Additional JSON data for notes

    Returns:
        Beads issue ID

    Contract:
        - MUST set title as human-readable description
        - MUST set notes as JSON with memory_ids and agent
        - MUST add labels: consolidation:{agent}, urgency:{urgency}
        - MUST NOT create duplicate issues for same memory_ids
    """
```

### Issue Query

```python
def query_consolidation_issues(
    agent: str | None = None,
    status: str = "open",
    urgency: str | None = None,
) -> list[dict]:
    """Query beads issues for consolidation work.

    Args:
        agent: Filter by agent type (None = all)
        status: Filter by status (open/in_progress/blocked/closed)
        urgency: Filter by urgency (None = all)

    Returns:
        List of issue dicts with id, title, notes, labels, status

    Contract:
        - MUST return empty list if no matches (not error)
        - MUST parse notes JSON for structured data
        - MUST respect all filters (AND logic)
    """
```

### Issue Update

```python
def claim_issue(issue_id: str) -> bool:
    """Claim an issue for processing.

    Args:
        issue_id: Beads issue ID

    Returns:
        True if successfully claimed, False if already claimed

    Contract:
        - MUST set status to in_progress
        - MUST fail gracefully if already in_progress
        - MUST NOT claim blocked issues
    """

def close_issue(issue_id: str, reason: str) -> None:
    """Close an issue after processing.

    Args:
        issue_id: Beads issue ID
        reason: Completion reason for audit trail

    Contract:
        - MUST set status to closed
        - MUST add reason to close message
    """

def block_issue(issue_id: str, error: str) -> None:
    """Block an issue due to error.

    Args:
        issue_id: Beads issue ID
        error: Error message for debugging

    Contract:
        - MUST set status to blocked
        - MUST add error to issue notes
    """
```

---

## Result Model Schemas

### DecayResult

```json
{
  "type": "object",
  "properties": {
    "memory_id": {"type": "string", "format": "uuid"},
    "score": {"type": "number", "minimum": 0, "maximum": 1},
    "urgency": {"enum": ["high", "medium", "low"]},
    "action": {"enum": ["reinforce", "consolidate", "promote", "gc"]},
    "beads_issue_id": {"type": ["string", "null"]}
  },
  "required": ["memory_id", "score", "urgency", "action"]
}
```

### ClusterResult

```json
{
  "type": "object",
  "properties": {
    "cluster_id": {"type": "string", "format": "uuid"},
    "memory_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"},
      "minItems": 2
    },
    "cohesion": {"type": "number", "minimum": 0, "maximum": 1},
    "action": {"enum": ["merge", "link", "ignore"]},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "beads_issue_id": {"type": ["string", "null"]}
  },
  "required": ["cluster_id", "memory_ids", "cohesion", "action", "confidence"]
}
```

### MergeResult

```json
{
  "type": "object",
  "properties": {
    "new_memory_id": {"type": "string", "format": "uuid"},
    "source_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"},
      "minItems": 2
    },
    "relation_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"}
    },
    "content_diff": {"type": "string"},
    "entities_preserved": {"type": "integer", "minimum": 0},
    "success": {"type": "boolean"},
    "beads_issue_id": {"type": ["string", "null"]}
  },
  "required": ["new_memory_id", "source_ids", "relation_ids", "content_diff", "entities_preserved", "success"]
}
```

### PromotionResult

```json
{
  "type": "object",
  "properties": {
    "memory_id": {"type": "string", "format": "uuid"},
    "vault_path": {"type": "string"},
    "criteria_met": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1
    },
    "success": {"type": "boolean"},
    "beads_issue_id": {"type": ["string", "null"]}
  },
  "required": ["memory_id", "criteria_met", "success"]
}
```

### RelationResult

```json
{
  "type": "object",
  "properties": {
    "from_memory_id": {"type": "string", "format": "uuid"},
    "to_memory_id": {"type": "string", "format": "uuid"},
    "relation_id": {"type": "string", "format": "uuid"},
    "strength": {"type": "number", "minimum": 0, "maximum": 1},
    "reasoning": {"type": "string"},
    "shared_entities": {
      "type": "array",
      "items": {"type": "string"}
    },
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "beads_issue_id": {"type": ["string", "null"]}
  },
  "required": ["from_memory_id", "to_memory_id", "relation_id", "strength", "reasoning", "confidence"]
}
```
