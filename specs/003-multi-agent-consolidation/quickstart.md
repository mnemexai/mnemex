# Quickstart: Multi-Agent Memory Consolidation

**Phase**: 1 (Design) | **Date**: 2025-11-24

## Overview

Five specialized agents work together to maintain memory health:

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Decay Analyzer  │────▶│ Cluster Detector│────▶│ Semantic Merge  │
│ (identifies)    │     │ (groups)        │     │ (combines)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌─────────────────┐             │
                        │ LTM Promoter    │◀────────────┘
                        │ (preserves)     │
                        └─────────────────┘
                                │
                        ┌─────────────────┐
                        │ Relationship    │
                        │ Discovery       │
                        │ (connects)      │
                        └─────────────────┘
```

## Installation

```bash
# Install cortexgraph with consolidation agents
uv pip install -e ".[dev]"

# Verify CLI is available
cortexgraph-consolidate --help
```

## Basic Usage

### Run All Agents (Pipeline)

```bash
# Preview what agents would do (safe)
cortexgraph-consolidate --dry-run run --all

# Execute full consolidation pipeline
cortexgraph-consolidate run --all
```

### Run Individual Agents

```bash
# Check for decaying memories
cortexgraph-consolidate run decay

# Find similar memories for merge
cortexgraph-consolidate run cluster

# Merge high-cohesion clusters
cortexgraph-consolidate run merge

# Promote valuable memories to LTM
cortexgraph-consolidate run promote

# Discover implicit relationships
cortexgraph-consolidate run relations
```

### Check Status

```bash
# Human-readable status
cortexgraph-consolidate status

# JSON output for scripting
cortexgraph-consolidate status --json
```

## Agent Behaviors

### Decay Analyzer

**Purpose**: Identifies memories approaching the forget threshold (0.10).

**Triggers**: Scheduled (hourly) + Event-driven (on save if score < 0.10)

**Actions**:
- Score < 0.10: Creates urgent beads issue
- Score 0.10-0.35: Creates medium-priority issue
- Score > 0.35: No action (healthy)

**Example Output**:
```
Found 3 memories in danger zone:
  - abc-123: score=0.08 (URGENT)
  - def-456: score=0.22 (WARNING)
  - ghi-789: score=0.31 (WARNING)

Created beads issue: cortexgraph-001
```

### Cluster Detector

**Purpose**: Groups similar memories for potential consolidation.

**Triggers**: Scheduled only (not urgent)

**Actions**:
- Cohesion ≥ 0.75: Recommends merge
- Cohesion 0.40-0.75: Recommends linking
- Cohesion < 0.40: No action

**Example Output**:
```
Found cluster of 3 memories (cohesion: 0.82):
  - "I prefer PostgreSQL for databases"
  - "PostgreSQL is my database choice"
  - "My projects use PostgreSQL"

Action: MERGE (cohesion >= 0.75)
Created beads issue: cortexgraph-002
```

### Semantic Merge

**Purpose**: Combines clustered memories intelligently.

**Triggers**: Processes from beads issues only (not free scanning)

**Guarantees**:
- 100% entity preservation (union of all entities)
- 100% unique content preservation
- Creates `consolidated_from` relations
- Archives originals (30-day recovery)

**Example Output**:
```
Processing cluster cortexgraph-002...
  Merged 3 memories → new memory xyz-789
  Preserved 5 unique entities
  Created 3 consolidated_from relations
  Archived originals (recoverable 30 days)
Closed beads issue: cortexgraph-002
```

### LTM Promoter

**Purpose**: Moves high-value memories to permanent Obsidian vault storage.

**Promotion Criteria** (any one):
- Decay score > 0.65
- Use count ≥ 5 within 14 days
- Review count ≥ 3

**Output**: Markdown file with YAML frontmatter in vault.

**Example Output**:
```
Promoting memory abc-123...
  Criteria met: score_threshold (0.72)
  Written to: ~/Documents/Obsidian/Vault/memories/abc-123.md
  Status updated: promoted
Created beads issue: cortexgraph-003
```

### Relationship Discovery

**Purpose**: Finds implicit connections between memories.

**Detection Methods**:
- Shared entities (partial overlap)
- Semantic similarity (embedding-based)
- Contextual proximity (same session/tags)

**Example Output**:
```
Discovered relation:
  From: "I use FastAPI for my backends"
  To: "My API connects to PostgreSQL"
  Strength: 0.73
  Reasoning: Shared context (backend development)
Created relation: rel-456
Created beads issue: cortexgraph-004
```

## Confidence-Based Processing

Agents use confidence thresholds to decide actions:

| Confidence | Action | Description |
|------------|--------|-------------|
| ≥ 0.90 | Auto-process | Execute immediately |
| 0.70-0.90 | Log and process | Execute with detailed logging |
| < 0.70 | Wait for human | Create beads issue, don't execute |

```bash
# Override thresholds for testing
CORTEXGRAPH_AUTO_CONFIDENCE=0.95 cortexgraph-consolidate run merge
```

## Scheduling

### Cron Setup (Recommended)

```bash
# Run all agents hourly
0 * * * * cortexgraph-consolidate run --all >> ~/.config/cortexgraph/consolidate.log 2>&1
```

### Manual Trigger

```bash
# One-time execution
cortexgraph-consolidate run --all
```

## Beads Coordination

Agents coordinate through beads issues:

```bash
# View consolidation issues
bd list --labels consolidation

# View by agent type
bd list --labels consolidation:decay
bd list --labels consolidation:cluster
bd list --labels consolidation:merge

# View by urgency
bd list --labels urgency:high
```

### Issue Schema

```json
{
  "title": "Decay: Memory abc-123 at 0.08",
  "notes": "{\"memory_ids\": [\"abc-123\"], \"scores\": [0.08], \"agent\": \"decay\"}",
  "labels": ["consolidation:decay", "urgency:high"],
  "priority": 1
}
```

## Configuration

```bash
# ~/.config/cortexgraph/.env

# Thresholds
CORTEXGRAPH_FORGET_THRESHOLD=0.10
CORTEXGRAPH_DANGER_ZONE_MIN=0.15
CORTEXGRAPH_DANGER_ZONE_MAX=0.35
CORTEXGRAPH_PROMOTE_THRESHOLD=0.65
CORTEXGRAPH_MERGE_COHESION=0.75
CORTEXGRAPH_LINK_COHESION=0.40

# Confidence
CORTEXGRAPH_AUTO_CONFIDENCE=0.90
CORTEXGRAPH_LOG_CONFIDENCE=0.70

# Rate limiting
CORTEXGRAPH_AGENT_RATE_LIMIT=100  # ops/minute
```

## Dry Run Mode

Always preview before making changes:

```bash
# Preview all agents
cortexgraph-consolidate --dry-run run --all

# Preview specific agent
cortexgraph-consolidate --dry-run run merge

# JSON output for scripting
cortexgraph-consolidate --dry-run --json run decay
```

## Troubleshooting

### "No memories found in danger zone"

This is good! Your memories are healthy.

### "Rate limit exceeded"

Wait or adjust `CORTEXGRAPH_AGENT_RATE_LIMIT`:

```bash
CORTEXGRAPH_AGENT_RATE_LIMIT=50 cortexgraph-consolidate run --all
```

### "Beads issue already exists"

Agents won't duplicate issues. Check existing:

```bash
bd list --labels consolidation --json
```

### "Merge failed: low cohesion"

Cluster cohesion dropped below threshold. Use linking instead:

```bash
cortexgraph-consolidate run cluster  # Re-analyze clusters
```

## Next Steps

1. **Test with dry-run**: `cortexgraph-consolidate --dry-run run --all`
2. **Review beads issues**: `bd list --labels consolidation`
3. **Set up cron job**: Schedule hourly consolidation
4. **Monitor logs**: Check `~/.config/cortexgraph/consolidate.log`
