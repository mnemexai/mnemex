# CortexGraph Usage Examples

## Basic Workflow

### 1. Save a Memory

```json
// Tool: save_memory
{
  "content": "The new API endpoint will be deployed on Friday at 3 PM",
  "tags": ["deployment", "api"],
  "source": "team slack",
  "context": "Discussion about Q4 release schedule"
}

// Response:
{
  "success": true,
  "memory_id": "abc-123-def-456",
  "message": "Memory saved with ID: abc-123-def-456",
  "has_embedding": false
}
```

### 2. Search for Memories

```json
// Tool: search_memory
{
  "query": "deployment",
  "tags": ["api"],
  "top_k": 5,
  "window_days": 7
}

// Response:
{
  "success": true,
  "count": 2,
  "results": [
    {
      "id": "abc-123-def-456",
      "content": "The new API endpoint will be deployed on Friday at 3 PM",
      "tags": ["deployment", "api"],
      "score": 0.8234,
      "use_count": 1,
      "last_used": 1699012345,
      "age_days": 0.2
    },
    {
      "id": "xyz-789",
      "content": "Deployment checklist: backup DB, update docs, notify users",
      "tags": ["deployment", "checklist"],
      "score": 0.6123,
      "use_count": 3,
      "age_days": 2.5
    }
  ]
}
```

### 3. Reinforce Important Memory

```json
// Tool: touch_memory
{
  "memory_id": "abc-123-def-456",
  "boost_strength": true
}

// Response:
{
  "success": true,
  "memory_id": "abc-123-def-456",
  "old_score": 0.8234,
  "new_score": 1.2456,
  "use_count": 2,
  "strength": 1.1,
  "message": "Memory reinforced. Score: 0.82 -> 1.25"
}
```

## Maintenance Workflows

### Weekly Garbage Collection

```json
// Step 1: Preview what would be removed
{
  "dry_run": true,
  "archive_instead": true
}

// Review the response...

// Step 2: Execute if looks good
{
  "dry_run": false,
  "archive_instead": true,
  "limit": 100
}
```

### Automatic Promotion

```json
// Step 1: Find promotion candidates
{
  "auto_detect": true,
  "dry_run": true
}

// Response shows candidates:
{
  "success": true,
  "candidates_found": 5,
  "candidates": [
    {
      "id": "mem-1",
      "content_preview": "Project requirements: must support...",
      "reason": "High use count (8 >= 5) within 14 days",
      "score": 0.7234,
      "use_count": 8,
      "age_days": 10.5
    }
  ]
}

// Step 2: Promote if candidates look good
{
  "auto_detect": true,
  "dry_run": false
}
```

### Finding Duplicates

```json
// Tool: cluster_memories
{
  "find_duplicates": true,
  "duplicate_threshold": 0.90
}

// Response:
{
  "success": true,
  "mode": "duplicate_detection",
  "duplicates_found": 2,
  "duplicates": [
    {
      "id1": "mem-1",
      "id2": "mem-2",
      "content1_preview": "Meeting on Tuesday at 2 PM",
      "content2_preview": "Tuesday 2pm meeting confirmed",
      "similarity": 0.94
    }
  ]
}
```

## Advanced Patterns

### Topic Tracking

Track related memories over time:

```python
# Day 1: Initial information
save_memory({
  "content": "Started working on user authentication feature",
  "tags": ["auth", "feature"]
})

# Day 2: Progress update
save_memory({
  "content": "Implemented JWT token generation and validation",
  "tags": ["auth", "jwt"]
})
touch_memory("previous-auth-memory-id")  # Link to previous

# Day 5: Completion
save_memory({
  "content": "Auth feature complete, ready for testing",
  "tags": ["auth", "testing"]
})
touch_memory("initial-auth-memory-id")
touch_memory("jwt-memory-id")

# Week later: Search all auth memories
search_memory({
  "tags": ["auth"],
  "window_days": 14
})
```

### Decision Documentation

Document decisions that might need review:

```python
# Save decision
save_memory({
  "content": "Decided to use PostgreSQL for analytics data due to better JSON query support",
  "tags": ["decision", "database", "analytics"],
  "source": "architecture review",
  "context": "Compared PostgreSQL vs MongoDB for analytics workload"
})

# Later: Review decision
search_memory({
  "query": "database decision",
  "tags": ["decision", "database"]
})

# If still relevant after multiple accesses: promote
promote_memory({
  "memory_id": "decision-memory-id",
  "force": true  # Even if doesn't meet auto-criteria
})
```

### Project Context

Maintain project context that naturally fades when project ends:

```python
# Active project
save_memory({
  "content": "Project X deadlines: MVP Feb 1, Beta March 1, Launch April 1",
  "tags": ["project-x", "deadline"]
})

# As you work, keep touching relevant memories
touch_memory("project-x-deadline-id")

# After project ends, memories naturally decay
# Search later will return low scores unless touched
```

## Integration Patterns

### With Basic Memory

1. **Work Memory → Knowledge Base**:
   - Save working notes to STM
   - Touch frequently used ones
   - Auto-promote becomes permanent knowledge

2. **Dual Search**:
   - Search STM for recent context
   - Search Basic Memory for established knowledge
   - Combine results

3. **Consolidation Flow**:
   - Cluster similar STM memories
   - Review clusters
   - Promote consolidated version to Basic Memory
   - Archive individual STM entries

### With Task Management

```python
# Save task context
save_memory({
  "content": "Bug #123: Users can't login on mobile - related to JWT expiry",
  "tags": ["bug", "mobile", "auth"],
  "meta": {"ticket_id": "123", "priority": "high"}
})

# As you work on it, touch it
touch_memory("bug-123-memory")

# When resolved, add resolution
save_memory({
  "content": "Bug #123 resolved: Extended JWT expiry to 24h for mobile clients",
  "tags": ["bug", "resolution", "auth"],
  "meta": {"ticket_id": "123", "resolved": true}
})

# Promote important bug fixes
promote_memory({
  "memory_id": "bug-123-resolution"
})
```

## Tuning for Your Workflow

### Fast-paced Development

Quick iteration, short-lived context:

```bash
STM_DECAY_LAMBDA=8.02e-6      # 1-day half-life
STM_FORGET_THRESHOLD=0.03
STM_PROMOTE_USE_COUNT=3
```

### Research/Long-term Projects

Slower decay, more preservation:

```bash
STM_DECAY_LAMBDA=1.145e-6     # 7-day half-life
STM_FORGET_THRESHOLD=0.08
STM_PROMOTE_USE_COUNT=7
```

### High Volume

Aggressive cleanup:

```bash
STM_FORGET_THRESHOLD=0.10
STM_PROMOTE_THRESHOLD=0.70    # Higher bar for promotion
```

Run GC more frequently:
```json
// Daily GC
{
  "dry_run": false,
  "archive_instead": false,  // Delete instead of archive
  "limit": 200
}
```
