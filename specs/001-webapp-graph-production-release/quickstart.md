# Quickstart: Web-App Graph Visualization

**Feature**: 001-webapp-graph-production-release
**Date**: 2025-11-20

## Overview

This quickstart demonstrates how to use the new graph visualization and relationship display features in CortexGraph 1.0.0.

## Prerequisites

- CortexGraph 1.0.0 installed (`uv tool install cortexgraph`)
- Some memories with relationships (see "Creating Test Data" below)
- Web browser for visualization

## Starting the Web-App

```bash
# Start CortexGraph with web-app enabled
cortexgraph --web

# Or specify a custom port
cortexgraph --web --port 8765

# The web-app will be available at http://localhost:8765
```

## Viewing Memory Relationships (P1)

### In the Web-App

1. Navigate to `http://localhost:8765`
2. Click on any memory in the list
3. The detail panel shows:
   - Memory content and metadata
   - **Relationships section** with incoming/outgoing connections
   - Click any related memory to navigate to it

### Via API

```bash
# Get relationships for a specific memory
curl http://localhost:8765/api/memories/{memory-id}/relationships

# Response:
{
  "success": true,
  "data": {
    "memory_id": "abc-123",
    "incoming": [
      {
        "relation_id": "rel-1",
        "related_memory_id": "def-456",
        "relation_type": "causes",
        "strength": 0.8,
        "memory_preview": "When the database crashes..."
      }
    ],
    "outgoing": [
      {
        "relation_id": "rel-2",
        "related_memory_id": "ghi-789",
        "relation_type": "supports",
        "strength": 0.7,
        "memory_preview": "Error handling strategy..."
      }
    ]
  }
}
```

## Interactive Graph Visualization (P2)

### Opening the Graph View

1. Click the **Graph** tab in the web-app navigation
2. The graph loads with all active memories as nodes
3. Relationships appear as directed edges between nodes

### Graph Interactions

| Action | Result |
|--------|--------|
| **Click node** | Show memory details in side panel |
| **Drag node** | Reposition node (holds position) |
| **Scroll** | Zoom in/out |
| **Drag background** | Pan the view |
| **Double-click node** | Pin node position |
| **Right-click node** | Context menu (view, edit, delete) |

### Visual Encoding

**Node Colors** (by status):
- 🟢 Green: Active memories
- 🔵 Blue: Promoted to LTM
- ⚪ Gray: Archived

**Node Opacity** (by decay score):
- Bright: High score (recently used)
- Faded: Low score (approaching forget threshold)

**Edge Colors** (by relation type):
- Gray: `related`
- Orange: `causes`
- Green: `supports`
- Red: `contradicts`
- Purple: `has_decision`
- Blue: `consolidated_from`

### Filtering the Graph

Use the filter panel to focus on specific memories:

```javascript
// Filter by tags
{
  "tags": ["project-x", "architecture"]
}

// Filter by minimum decay score
{
  "min_decay_score": 0.3
}

// Combined filters
{
  "tags": ["security"],
  "min_decay_score": 0.2,
  "created_after": 1699228800,  // Nov 6, 2024
  "limit": 500
}
```

## Full Metadata Display (P3)

Click any memory to see complete metadata:

```yaml
Content: "The API should use JWT tokens with 15-minute expiry..."

Metadata:
  ID: abc-123-def-456
  Status: active
  Tags: [authentication, jwt, security]
  Entities: [JWT, API, OAuth]
  Source: conversation with Claude
  Context: API design discussion

Temporal:
  Created: Nov 15, 2024 at 3:42 PM
  Last Used: Nov 20, 2024 at 9:15 AM
  Use Count: 7
  Decay Score: 0.72
  Strength: 1.2

Spaced Repetition:
  Review Priority: 0.15
  Review Count: 3
  Cross-Domain Uses: 2

Promotion:
  Status: Not promoted
  Vault Path: N/A
```

## Creating Test Data

If you need memories with relationships for testing:

```python
# Using the MCP tools or Python API
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.models import Memory, Relation

storage = JSONLStorage()

# Create memories
mem1 = Memory(content="Database connection pooling improves performance", tags=["database", "performance"])
mem2 = Memory(content="Connection pool size should match CPU cores", tags=["database", "config"])
mem3 = Memory(content="Too many connections cause resource exhaustion", tags=["database", "errors"])

storage.save_memory(mem1)
storage.save_memory(mem2)
storage.save_memory(mem3)

# Create relationships
storage.create_relation(Relation(
    from_memory_id=mem1.id,
    to_memory_id=mem2.id,
    relation_type="supports",
    strength=0.9
))

storage.create_relation(Relation(
    from_memory_id=mem3.id,
    to_memory_id=mem1.id,
    relation_type="contradicts",
    strength=0.7
))
```

Or use the CLI:

```bash
# Create a relation between two existing memories
cortexgraph-maintenance create-relation \
  --from abc-123 \
  --to def-456 \
  --type supports \
  --strength 0.8
```

## API Examples

### Get Full Graph

```bash
curl "http://localhost:8765/api/graph?limit=1000&min_score=0.1"
```

### Get Filtered Graph

```bash
curl -X POST http://localhost:8765/api/graph/filtered \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["security"],
    "min_decay_score": 0.2,
    "statuses": ["active", "promoted"],
    "limit": 500
  }'
```

### Save Custom Layout

```bash
curl -X POST http://localhost:8765/api/graph/layout \
  -H "Content-Type: application/json" \
  -d '{
    "positions": {
      "abc-123": {"x": 100, "y": 200, "fx": 100, "fy": 200},
      "def-456": {"x": 300, "y": 150}
    },
    "zoom": 1.5,
    "pan": {"x": -50, "y": 0}
  }'
```

### Check Storage Health

```bash
curl http://localhost:8765/api/health
```

## Performance Tips

### For Large Graphs (1000+ nodes)

1. **Use filters** - Don't load all memories at once
2. **Increase min_score** - Filter out low-value memories
3. **Limit results** - Start with 500, increase as needed

### For Slow Rendering

1. Check console for JavaScript errors
2. Reduce animation frames (Settings → Performance)
3. Use Canvas mode for >1000 nodes (automatic)

## Troubleshooting

### Graph Won't Load

```bash
# Check storage health
curl http://localhost:8765/api/health

# Validate storage files
cortexgraph-maintenance validate

# Repair if needed
cortexgraph-maintenance repair
```

### Missing Relationships

1. Verify relationships exist:
   ```bash
   cortexgraph-maintenance stats
   ```

2. Check relation types are valid:
   - related, causes, supports, contradicts, has_decision, consolidated_from

### Rate Limited

The API limits requests to prevent overload:
- Graph endpoints: 30/minute
- Other endpoints: 100/minute

Wait for the reset time shown in the error response.

## Next Steps

- [Full API Reference](contracts/graph-api.yaml)
- [Data Model Documentation](data-model.md)
- [Research & Architecture Decisions](research.md)
- [Feature Specification](spec.md)
