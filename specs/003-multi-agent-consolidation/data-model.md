# Data Model: Multi-Agent Memory Consolidation

**Phase**: 1 (Design) | **Date**: 2025-11-24

## Entity Relationship Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONSOLIDATION AGENTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐        ┌──────────────────┐                           │
│  │ ConsolidationAgent│◄──────│ DecayAnalyzer    │                           │
│  │ (Abstract Base)   │        └──────────────────┘                           │
│  │                   │        ┌──────────────────┐                           │
│  │ + dry_run: bool   │◄──────│ ClusterDetector  │                           │
│  │ + rate_limit: int │        └──────────────────┘                           │
│  │ + scan()          │        ┌──────────────────┐                           │
│  │ + process_item()  │◄──────│ SemanticMerge    │                           │
│  │ + run()           │        └──────────────────┘                           │
│  └──────────────────┘        ┌──────────────────┐                           │
│           │                  │ LTMPromoter      │                           │
│           │                  └──────────────────┘                           │
│           │                  ┌──────────────────┐                           │
│           │                  │RelationshipDisc. │                           │
│           │                  └──────────────────┘                           │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ BeadsIntegration │─────────────────────────────────────────────┐         │
│  │                   │                                             │         │
│  │ + create_issue()  │                                             ▼         │
│  │ + update_issue()  │                               ┌──────────────────┐   │
│  │ + query_issues()  │                               │ ConsolidationTask│   │
│  │ + close_issue()   │                               │ (Beads Issue)    │   │
│  └──────────────────┘                               │                   │   │
│                                                      │ + title: str     │   │
│                                                      │ + notes: JSON    │   │
│                                                      │ + labels: list   │   │
│                                                      │ + status: enum   │   │
│                                                      └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESULT MODELS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │ DecayResult      │    │ ClusterResult    │    │ MergeResult      │      │
│  │                   │    │                   │    │                   │      │
│  │ + memory_id: str  │    │ + cluster_id: str│    │ + new_id: str    │      │
│  │ + score: float    │    │ + memory_ids: [] │    │ + source_ids: [] │      │
│  │ + urgency: enum   │    │ + cohesion: float│    │ + relations: []  │      │
│  │ + action: enum    │    │ + action: enum   │    │ + content_diff   │      │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘      │
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                               │
│  │ PromotionResult  │    │ RelationResult   │                               │
│  │                   │    │                   │                               │
│  │ + memory_id: str  │    │ + from_id: str   │                               │
│  │ + vault_path: str │    │ + to_id: str     │                               │
│  │ + criteria_met: []│    │ + strength: float│                               │
│  │ + success: bool   │    │ + reasoning: str │                               │
│  └──────────────────┘    └──────────────────┘                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Entities

### ConsolidationAgent (Abstract Base Class)

Base class for all consolidation agents.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `dry_run` | `bool` | Preview mode without changes | Default: `False` |
| `rate_limit` | `int` | Max operations per minute | Default: `100`, Min: `1` |
| `confidence_thresholds` | `ConfidenceConfig` | Auto/log/wait thresholds | See ConfidenceConfig |

**Methods**:
- `scan() -> list[str]`: Abstract - find items needing processing
- `process_item(memory_id: str) -> T`: Abstract - process single item
- `run() -> list[T]`: Execute agent on all scanned items
- `_log_to_beads(item_id: str, result: T) -> str`: Create audit beads issue

---

### ConfidenceConfig

Configuration for confidence-based processing decisions.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `auto_threshold` | `float` | Auto-process above this | Default: `0.9`, Range: `[0,1]` |
| `log_threshold` | `float` | Log-only above this | Default: `0.7`, Range: `[0,1]` |
| `wait_below` | `float` | Wait for human below this | Derived: `log_threshold` |

---

### ConsolidationTask (Beads Issue Schema)

Schema for beads issues used in agent coordination.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `title` | `str` | Human-readable description | `"Decay: Memory abc-123 at 0.08"` |
| `notes` | `JSON` | Structured data for processing | `{"memory_ids": ["abc-123"], "scores": [0.08]}` |
| `labels` | `list[str]` | Agent type + priority | `["consolidation:decay", "urgency:high"]` |
| `status` | `str` | Beads status | `open`, `in_progress`, `blocked`, `closed` |
| `priority` | `int` | 1-3 urgency | `1` = high, `2` = medium, `3` = low |

**Label Conventions**:
- `consolidation:decay` - Decay Analyzer created
- `consolidation:cluster` - Cluster Detector created
- `consolidation:merge` - Semantic Merge created
- `consolidation:promote` - LTM Promoter created
- `consolidation:relations` - Relationship Discovery created
- `urgency:high` - Score < 0.10
- `urgency:medium` - Score in danger zone (0.10-0.35)
- `urgency:low` - Routine processing

---

### DecayResult

Output from Decay Analyzer agent.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `memory_id` | `str` | Memory UUID | Required |
| `score` | `float` | Current decay score | Range: `[0,1]` |
| `urgency` | `Urgency` | Processing urgency | Enum: `high`, `medium`, `low` |
| `action` | `DecayAction` | Recommended action | Enum: `reinforce`, `consolidate`, `promote`, `gc` |
| `beads_issue_id` | `str \| None` | Created beads issue | Optional |

---

### ClusterResult

Output from Cluster Detector agent.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `cluster_id` | `str` | Generated cluster UUID | Required |
| `memory_ids` | `list[str]` | Memories in cluster | Min length: `2` |
| `cohesion` | `float` | Cluster cohesion score | Range: `[0,1]` |
| `action` | `ClusterAction` | Recommended action | Enum: `merge`, `link`, `ignore` |
| `confidence` | `float` | Confidence in recommendation | Range: `[0,1]` |
| `beads_issue_id` | `str \| None` | Created beads issue | Optional |

---

### MergeResult

Output from Semantic Merge agent.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `new_memory_id` | `str` | Merged memory UUID | Required |
| `source_ids` | `list[str]` | Original memory IDs | Min length: `2` |
| `relation_ids` | `list[str]` | Created `consolidated_from` relations | Min length: `len(source_ids)` |
| `content_diff` | `str` | Summary of merge changes | Required |
| `entities_preserved` | `int` | Count of unique entities kept | Min: `0` |
| `success` | `bool` | Merge completed successfully | Required |
| `beads_issue_id` | `str \| None` | Closed beads issue | Optional |

---

### PromotionResult

Output from LTM Promoter agent.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `memory_id` | `str` | Promoted memory UUID | Required |
| `vault_path` | `str` | Path to markdown file | Required if success |
| `criteria_met` | `list[str]` | Which promotion criteria matched | Min length: `1` |
| `success` | `bool` | Promotion completed successfully | Required |
| `beads_issue_id` | `str \| None` | Closed beads issue | Optional |

**Promotion Criteria**:
- `score_threshold` - decay score > 0.65
- `use_count_threshold` - use_count >= 5 within 14 days
- `review_count_threshold` - review_count >= 3

---

### RelationResult

Output from Relationship Discovery agent.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `from_memory_id` | `str` | Source memory UUID | Required |
| `to_memory_id` | `str` | Target memory UUID | Required |
| `relation_id` | `str` | Created relation UUID | Required |
| `strength` | `float` | Relation strength | Range: `[0,1]` |
| `reasoning` | `str` | Why relation was created | Required |
| `shared_entities` | `list[str]` | Entities in common | May be empty |
| `confidence` | `float` | Confidence in relation | Range: `[0,1]` |
| `beads_issue_id` | `str \| None` | Created beads issue | Optional |

---

## Enums

### Urgency

```python
class Urgency(str, Enum):
    HIGH = "high"      # score < 0.10 - immediate attention
    MEDIUM = "medium"  # score 0.10-0.35 (danger zone)
    LOW = "low"        # routine processing
```

### DecayAction

```python
class DecayAction(str, Enum):
    REINFORCE = "reinforce"    # Touch memory to reset decay
    CONSOLIDATE = "consolidate" # Merge with similar memories
    PROMOTE = "promote"         # Move to LTM
    GC = "gc"                   # Allow garbage collection
```

### ClusterAction

```python
class ClusterAction(str, Enum):
    MERGE = "merge"   # Cohesion >= 0.75 - merge into one
    LINK = "link"     # Cohesion 0.4-0.75 - create relations
    IGNORE = "ignore" # Cohesion < 0.4 - no action
```

### ProcessingDecision

```python
class ProcessingDecision(str, Enum):
    AUTO = "auto"          # confidence >= 0.9
    LOG_ONLY = "log"       # 0.7 <= confidence < 0.9
    WAIT_HUMAN = "wait"    # confidence < 0.7
```

---

## State Transitions

### Memory Lifecycle with Agents

```text
                    ┌──────────────────────────────────────────────┐
                    │            MEMORY LIFECYCLE                   │
                    └──────────────────────────────────────────────┘

    ┌─────────┐     Decay Analyzer      ┌─────────────┐
    │ CREATED │────────────────────────▶│ IN_DANGER   │
    │ (new)   │     score < 0.35        │ (0.15-0.35) │
    └─────────┘                         └──────┬──────┘
         │                                     │
         │                    ┌────────────────┼────────────────┐
         │                    ▼                ▼                ▼
         │            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │            │ REINFORCED  │  │ CLUSTERED   │  │ CRITICAL    │
         │            │ (touched)   │  │ (detected)  │  │ (< 0.10)    │
         │            └─────────────┘  └──────┬──────┘  └──────┬──────┘
         │                    │               │                │
         │                    │               ▼                │
         │                    │        ┌─────────────┐         │
         │                    │        │ MERGED      │         │
         │                    │        │ (new memory)│         │
         │                    │        └──────┬──────┘         │
         │                    │               │                │
         ▼                    ▼               ▼                ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      PROMOTED (to LTM)                       │
    │                   status=promoted, ltm_path set              │
    └─────────────────────────────────────────────────────────────┘
                                    │
                                    │ (originals after merge)
                                    ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      ARCHIVED                                │
    │              status=archived, recoverable 30 days            │
    └─────────────────────────────────────────────────────────────┘
                                    │
                                    │ (after 30 days or GC)
                                    ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      DELETED                                 │
    │                   (garbage collected)                        │
    └─────────────────────────────────────────────────────────────┘
```

### Beads Issue Lifecycle

```text
    ┌─────────┐  agent creates   ┌─────────────┐
    │  OPEN   │◄────────────────│ Agent Scan  │
    └────┬────┘                  └─────────────┘
         │
         │ agent claims (bd update --status=in_progress)
         ▼
    ┌─────────────┐
    │ IN_PROGRESS │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│ BLOCKED │ │ CLOSED  │
│ (error) │ │(success)│
└────┬────┘ └─────────┘
     │
     │ retry (max 3x)
     ▼
┌─────────┐
│  OPEN   │ (re-queue)
└─────────┘
```

---

## Data Validation Rules

### Memory ID Format
- UUID v4 format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- Validated via regex or UUID library

### Beads Notes JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "memory_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"},
      "minItems": 1
    },
    "scores": {
      "type": "array",
      "items": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "cohesion": {"type": "number", "minimum": 0, "maximum": 1},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "action": {"type": "string"},
    "agent": {"type": "string"}
  },
  "required": ["memory_ids", "agent"]
}
```

### Thresholds (Configurable)
| Threshold | Default | Environment Variable |
|-----------|---------|---------------------|
| Danger zone min | 0.15 | `CORTEXGRAPH_DANGER_ZONE_MIN` |
| Danger zone max | 0.35 | `CORTEXGRAPH_DANGER_ZONE_MAX` |
| Forget threshold | 0.10 | `CORTEXGRAPH_FORGET_THRESHOLD` |
| Promote threshold | 0.65 | `CORTEXGRAPH_PROMOTE_THRESHOLD` |
| Merge cohesion | 0.75 | `CORTEXGRAPH_MERGE_COHESION` |
| Link cohesion | 0.40 | `CORTEXGRAPH_LINK_COHESION` |
| Auto confidence | 0.90 | `CORTEXGRAPH_AUTO_CONFIDENCE` |
| Log confidence | 0.70 | `CORTEXGRAPH_LOG_CONFIDENCE` |
