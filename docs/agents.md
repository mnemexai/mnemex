# CortexGraph Multi-Agent Consolidation System

This document describes the multi-agent memory consolidation architecture, which enables automated memory maintenance through specialized agents coordinated via beads issue tracking.

## Overview

CortexGraph uses a pipeline of five specialized agents that work together to maintain memory health:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Consolidation Pipeline                            │
│                                                                       │
│   decay → cluster → merge → promote → relations                      │
│     │        │        │        │          │                          │
│     ▼        ▼        ▼        ▼          ▼                          │
│  Find at- Find   Combine  Promote  Discover                         │
│  risk    similar similar  to LTM   cross-                           │
│  memories groups  groups           domain                            │
│                                    links                             │
└─────────────────────────────────────────────────────────────────────┘
```

Each agent has a specific responsibility and can be run independently or as part of the full pipeline via the Scheduler.

## Agent Architecture

### Storage Utilities (v1.2.0+)

Agents access storage through a shared utility function:

```python
from cortexgraph.agents import get_storage

# Get the current storage instance
storage = get_storage()
```

This utility is exported from `cortexgraph.agents` and provides consistent storage access across all agents. The function retrieves the storage instance from the context, enabling:

- **Testability**: Easy to mock for unit tests
- **Consistency**: All agents use the same storage instance
- **Decoupling**: Agents don't need to know about context management

The utility is defined in `cortexgraph.agents.storage_utils` and re-exported from `cortexgraph.agents.__init__`.

### Base Agent Contract

All agents extend `ConsolidationAgent[T]`, which provides:

- **`dry_run` mode**: Preview changes without modifying data
- **Rate limiting**: Configurable operations per minute (default: 60)
- **Scan → Process pattern**: Identify work, then execute
- **Beads integration**: Create issues for discovered work

```python
from cortexgraph.agents.base import ConsolidationAgent

class MyAgent(ConsolidationAgent[MyResultType]):
    def scan(self) -> list[str]:
        """Identify items needing attention. Returns list of item IDs."""
        ...

    def process(self, item_id: str) -> MyResultType:
        """Process a single item. Returns result object."""
        ...
```

### Agent Results

Each agent returns structured result objects:

| Agent | Result Type | Key Fields |
|-------|-------------|------------|
| Decay | `DecayResult` | `memory_id`, `score`, `urgency`, `action` |
| Cluster | `ClusterResult` | `cluster_id`, `memory_ids`, `cohesion`, `action` |
| Merge | `MergeResult` | `new_memory_id`, `source_ids`, `relation_ids` |
| Promote | `PromotionResult` | `memory_id`, `vault_path`, `criteria_met` |
| Relations | `RelationResult` | `from_id`, `to_id`, `relation_type`, `created` |

## The Five Agents

### 1. DecayAnalyzer

**Purpose**: Identify memories at risk of being forgotten.

**Scan**: Queries all active memories and calculates decay scores.

**Process**: For each memory with score in the "danger zone" (0.15-0.35), determines urgency:
- **HIGH** (score < 0.15): Immediate attention needed
- **MEDIUM** (0.15 ≤ score < 0.25): Standard priority
- **LOW** (0.25 ≤ score < 0.35): Can wait

**Actions recommended**:
- `reinforce`: Memory is valuable, should be reviewed
- `gc_candidate`: Memory is low-value, consider deletion
- `needs_review`: Uncertain, requires human judgment

```python
from cortexgraph.agents import DecayAnalyzer

analyzer = DecayAnalyzer(dry_run=True)
results = analyzer.run()  # Returns list[DecayResult]

for result in results:
    print(f"{result.memory_id}: {result.urgency} - {result.action}")
```

### 2. ClusterDetector

**Purpose**: Find groups of similar memories for potential consolidation.

**Scan**: Uses embedding similarity to find memory clusters.

**Process**: For each cluster meeting threshold:
- **High cohesion** (≥ 0.85): Auto-merge candidate
- **Medium cohesion** (0.65-0.85): LLM review recommended
- **Low cohesion** (< 0.65): Keep separate

**Integration with beads**: Creates issues with `consolidation:cluster` label for tracking.

```python
from cortexgraph.agents import ClusterDetector

detector = ClusterDetector(
    dry_run=True,
    similarity_threshold=0.83,
    min_cluster_size=2
)
results = detector.run()  # Returns list[ClusterResult]
```

### 3. SemanticMerge

**Purpose**: Intelligently combine clustered memories.

**Scan**: Reads merge issues from beads (created by ClusterDetector).

**Process**: For each merge request:
1. Fetch source memories
2. Merge content (preserving unique information)
3. Union tags and entities
4. Calculate combined strength
5. Create new memory
6. Create `consolidated_from` relations
7. Archive original memories

**Dry run**: Returns preview of what would be merged.

```python
from cortexgraph.agents import SemanticMerge

merger = SemanticMerge(dry_run=True)
results = merger.run()  # Returns list[MergeResult]
```

### 4. LTMPromoter

**Purpose**: Move high-value memories to long-term storage (Obsidian vault).

**Scan**: Identifies promotion candidates based on:
- Score threshold (default: ≥ 0.65)
- Usage threshold (default: ≥ 5 uses in 14 days)
- Or forced promotion

**Process**: For each candidate:
1. Verify criteria still met
2. Generate Markdown content with YAML frontmatter
3. Write to vault directory
4. Update memory status to `PROMOTED`
5. Store vault path reference

```python
from cortexgraph.agents import LTMPromoter

promoter = LTMPromoter(dry_run=True)
results = promoter.run()  # Returns list[PromotionResult]
```

### 5. RelationshipDiscovery

**Purpose**: Find and create cross-domain connections between memories.

**Scan**: Identifies memories sharing entities that aren't already linked.

**Process**: For each relationship opportunity:
1. Check if relation already exists
2. Verify both memories exist
3. Create bidirectional `related` relation
4. Track in beads if enabled

**Entity-based linking**: Memories sharing entities (like "Python", "API", "Project X") are automatically connected.

```python
from cortexgraph.agents import RelationshipDiscovery

discovery = RelationshipDiscovery(dry_run=True)
results = discovery.run()  # Returns list[RelationResult]
```

## The Scheduler

The `Scheduler` orchestrates all agents:

```python
from cortexgraph.agents import Scheduler

# Run full pipeline (dry run)
scheduler = Scheduler(dry_run=True)
results = scheduler.run_pipeline()
# Returns: {"decay": [...], "cluster": [...], "merge": [...], "promote": [...], "relations": [...]}

# Run single agent
decay_results = scheduler.run_agent("decay")

# Run on schedule (checks interval)
result = scheduler.run_scheduled(force=False)
```

### Scheduled Execution

The scheduler tracks last run time and respects minimum intervals:

```python
scheduler = Scheduler(
    dry_run=False,
    interval_hours=1.0  # Run at most once per hour
)

# Called by cron/launchd
result = scheduler.run_scheduled()
if result["skipped"]:
    print(f"Skipped: {result['reason']}")
else:
    print(f"Processed: {result['results']}")
```

### Event-Driven Hook

The `post_save_hook` provides event-driven detection of urgent decay:

```python
from cortexgraph.agents.scheduler import post_save_hook

# Called after save_memory
result = post_save_hook("memory-123")
if result:
    print(f"Urgent: {result['action']}")  # Memory needs attention
```

## Beads Integration

Agents coordinate through [beads](https://github.com/steveyegge/beads) issue tracking.

### Label Convention

Each agent uses specific labels:

| Agent | Label |
|-------|-------|
| Decay | `consolidation:decay` |
| Cluster | `consolidation:cluster` |
| Merge | `consolidation:merge` |
| Promote | `consolidation:promote` |
| Relations | `consolidation:relations` |

Urgency labels: `urgency:high`, `urgency:medium`, `urgency:low`

### Issue Flow

```
1. DecayAnalyzer scans → Creates issue with memory_ids needing attention
2. ClusterDetector scans → Creates issue with cluster for merging
3. SemanticMerge reads beads → Processes merge issues
4. Issues closed on completion
```

### Creating Issues Programmatically

```python
from cortexgraph.agents.beads_integration import (
    create_consolidation_issue,
    query_consolidation_issues,
    claim_issue,
    close_issue,
)

# Create issue
issue_id = create_consolidation_issue(
    agent="decay",
    memory_ids=["mem-123", "mem-456"],
    action="reinforce",
    urgency="high",
)

# Query issues
open_issues = query_consolidation_issues(
    agent="cluster",
    status="open",
)

# Claim and process
if claim_issue(issue_id):
    # ... do work ...
    close_issue(issue_id, "Processed successfully")
```

## Configuration

### Environment Variables

```bash
# Scheduler
CORTEXGRAPH_CONSOLIDATION_INTERVAL=3600  # Seconds between runs

# Thresholds (already in main config)
CORTEXGRAPH_FORGET_THRESHOLD=0.05        # Decay below this → delete
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65       # Score above this → promote
CORTEXGRAPH_PROMOTE_USE_COUNT=5          # Uses within window → promote
```

### Agent-Specific Configuration

Agents accept configuration in their constructors:

```python
ClusterDetector(
    dry_run=True,
    similarity_threshold=0.83,  # Minimum similarity to cluster
    min_cluster_size=2,         # Minimum memories per cluster
    rate_limit=60,              # Max operations per minute
)
```

## Running the Pipeline

### Via CLI

```bash
# Run full pipeline (dry run)
cortexgraph-consolidate --dry-run

# Run full pipeline (live)
cortexgraph-consolidate

# Run single agent
cortexgraph-consolidate --agent decay --dry-run

# Run on schedule
cortexgraph-consolidate --scheduled --interval-hours 1
```

### Via Python

```python
from cortexgraph.agents import Scheduler

# One-time run
scheduler = Scheduler(dry_run=False)
results = scheduler.run_pipeline()

# Check what would change
scheduler = Scheduler(dry_run=True)
preview = scheduler.run_pipeline()
for agent, items in preview.items():
    print(f"{agent}: {len(items)} items")
```

### Via Cron/Launchd

```bash
# crontab -e
0 * * * * /path/to/cortexgraph-consolidate --scheduled 2>&1 >> /var/log/cortexgraph.log
```

## Best Practices

### 1. Always Start with Dry Run

```python
scheduler = Scheduler(dry_run=True)
preview = scheduler.run_pipeline()
# Review preview before running live
```

### 2. Run Agents Individually When Debugging

```python
scheduler = Scheduler(dry_run=True)

# Test just decay analysis
decay_results = scheduler.run_agent("decay")
for r in decay_results:
    print(f"{r.memory_id}: {r.score:.3f} → {r.action}")
```

### 3. Monitor with Beads

```bash
# See what's being processed
bd list --status open --labels consolidation

# See what's completed
bd list --status closed --labels consolidation --limit 20
```

### 4. Check Logs

```python
import logging
logging.basicConfig(level=logging.INFO)

# Agents log their operations
scheduler = Scheduler(dry_run=False)
scheduler.run_pipeline()  # Check logs for details
```

## Architecture Decisions

### Why Five Agents?

Each agent has a **single responsibility**:
- Decay: Find problems
- Cluster: Group similar items
- Merge: Combine groups
- Promote: Move to long-term
- Relations: Build connections

This separation allows:
- Independent testing
- Parallel execution (future)
- Easy debugging
- Selective running

### Why Beads Integration?

Beads provides:
- **Audit trail**: Every decision is tracked
- **Human override**: Humans can review/reject
- **State persistence**: Survives restarts
- **Parallelization**: Multiple agents can work simultaneously

### Why Pipeline Order?

The order `decay → cluster → merge → promote → relations` is deliberate:

1. **Decay first**: Identify at-risk memories before clustering
2. **Cluster second**: Group identified memories
3. **Merge third**: Consolidate clusters
4. **Promote fourth**: Move valuable memories to LTM
5. **Relations last**: Build connections after structure is stable

## Troubleshooting

### Agent Returns Empty Results

Check:
1. Are there memories in storage? (`cortexgraph-maintenance stats`)
2. Are thresholds appropriate for your data?
3. Is the storage path correct?

### Beads Issues Piling Up

The agents create issues but aren't closing them:
1. Check if `bd` CLI is installed and working
2. Run `bd list --status open` to see pending work
3. Manually close stale issues: `bd close <id> --reason "stale"`

### Merge Not Working

Common issues:
1. Cluster cohesion too low (try lowering threshold)
2. Memories already archived
3. Storage permissions

### Pipeline Takes Too Long

Solutions:
1. Increase `rate_limit` (default: 60/min)
2. Run agents individually
3. Reduce scope with filters
