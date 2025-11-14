# Knowledge Graph Features

CortexGraph now includes comprehensive knowledge graph capabilities inspired by the reference MCP memory server, adapted for temporal memory management.

## Overview

The knowledge graph provides:

1. **Entity Tracking**: Tag memories with named entities
2. **Explicit Relations**: Create directed links between memories
3. **Graph Navigation**: Read the entire graph or access specific nodes
4. **Temporal Scoring**: All graph operations respect memory decay

## Core Concepts

### Memories as Nodes

Each memory is a node in the graph with:
- **Content**: The actual information stored
- **Entities**: Named entities mentioned (e.g., people, projects, concepts)
- **Metadata**: Tags, source, context
- **Temporal Properties**: Score, use_count, last_used
- **Status**: Active, promoted, or archived

### Relations as Edges

Relations connect memories with:
- **Type**: The nature of the relationship (e.g., "references", "similar_to", "follows_from")
- **Direction**: From one memory to another
- **Strength**: Weight of the relationship (0.0-1.0)
- **Metadata**: Additional context about the relation

### Knowledge Graph Structure

```
{
  "memories": [
    {
      "id": "mem-123",
      "content": "Project X deadline is Friday",
      "entities": ["project-x"],
      "tags": ["deadline", "work"],
      "score": 0.82,
      ...
    }
  ],
  "relations": [
    {
      "from": "mem-123",
      "to": "mem-456",
      "type": "references",
      "strength": 0.9
    }
  ],
  "stats": {
    "total_memories": 150,
    "total_relations": 45,
    "avg_score": 0.42
  }
}
```

## New Tools

### read_graph

Get the complete knowledge graph.

**Use Cases:**
- Visualize the entire memory network
- Export memories for analysis
- Understand memory structure
- Feed full context to LLM

**Example:**

```json
{
  "status": "active",        // Filter: "active", "promoted", "archived", "all"
  "include_scores": true,    // Include temporal decay scores
  "limit": 100               // Optional: limit number of memories
}
```

**Response:**

```json
{
  "success": true,
  "memories": [
    {
      "id": "mem-123",
      "content": "...",
      "entities": ["project-x", "john"],
      "tags": ["work"],
      "score": 0.82,
      "use_count": 5,
      "age_days": 2.5
    }
  ],
  "relations": [
    {
      "from": "mem-123",
      "to": "mem-456",
      "type": "references",
      "strength": 0.9
    }
  ],
  "stats": {
    "total_memories": 150,
    "total_relations": 45,
    "avg_score": 0.42,
    "avg_use_count": 3.2,
    "status_filter": "active"
  }
}
```

---

### open_memories

Retrieve specific memories with their relations.

**Use Cases:**
- Get detailed info about specific memories
- Navigate the graph by following relations
- Context assembly for LLM
- Debugging and inspection

**Example:**

```json
{
  "memory_ids": ["mem-123", "mem-456"],  // Single ID or array
  "include_relations": true,              // Include incoming/outgoing relations
  "include_scores": true                  // Include temporal scores
}
```

**Response:**

```json
{
  "success": true,
  "count": 2,
  "memories": [
    {
      "id": "mem-123",
      "content": "...",
      "entities": ["project-x"],
      "tags": ["work"],
      "score": 0.82,
      "relations": {
        "outgoing": [
          {
            "to": "mem-456",
            "type": "references",
            "strength": 0.9
          }
        ],
        "incoming": [
          {
            "from": "mem-789",
            "type": "similar_to",
            "strength": 0.85
          }
        ]
      }
    }
  ],
  "not_found": []
}
```

---

### create_relation

Create an explicit directed link between two memories.

**Use Cases:**
- Manual linking of related information
- Building knowledge graphs explicitly
- Documenting dependencies
- Creating semantic networks

**Relation Types:**

Common relation types:
- `references`: One memory mentions/cites another
- `follows_from`: Temporal sequence (this came after that)
- `similar_to`: Semantic similarity
- `contradicts`: Conflicting information
- `elaborates_on`: Provides detail about another memory
- `part_of`: Hierarchical relationship

**Example:**

```json
{
  "from_memory_id": "mem-123",
  "to_memory_id": "mem-456",
  "relation_type": "references",
  "strength": 0.9,
  "metadata": {
    "context": "same project",
    "created_by": "manual"
  }
}
```

**Response:**

```json
{
  "success": true,
  "relation_id": "rel-789",
  "from": "mem-123",
  "to": "mem-456",
  "type": "references",
  "strength": 0.9,
  "message": "Relation created: mem-123 --[references]--> mem-456"
}
```

## Usage Patterns

### 1. Entity-Based Navigation

Tag memories with entities for easier retrieval:

```python
# Save with entities
save_memory({
  "content": "John Smith joined Project X as lead engineer",
  "entities": ["john-smith", "project-x"],
  "tags": ["team", "project"]
})

# Later: Find all memories about john-smith
search_memory({
  "query": "john-smith",  # Searches entities too
  "tags": ["team"]
})

# Or read full graph and filter client-side by entity
read_graph({"status": "active"})
```

### 2. Explicit Knowledge Chains

Build chains of related information:

```python
# Memory 1: Initial decision
save_memory({
  "content": "Decided to use PostgreSQL for analytics",
  "entities": ["postgresql", "analytics-project"]
})
# -> Returns mem-123

# Memory 2: Follow-up
save_memory({
  "content": "Set up PostgreSQL cluster with streaming replication",
  "entities": ["postgresql", "infrastructure"]
})
# -> Returns mem-456

# Link them
create_relation({
  "from_memory_id": "mem-456",
  "to_memory_id": "mem-123",
  "relation_type": "implements_decision"
})

# Later: Navigate the chain
open_memories({
  "memory_ids": ["mem-123"],
  "include_relations": true
})
# See that mem-456 implements this decision
```

### 3. Context Assembly

Build rich context by following graph:

```python
# Start with a memory
memories = open_memories({
  "memory_ids": ["mem-123"],
  "include_relations": true
})

# Get related memories
related_ids = [r["to"] for r in memories["memories"][0]["relations"]["outgoing"]]

# Fetch them
related = open_memories({
  "memory_ids": related_ids,
  "include_relations": false
})

# Assemble full context for LLM
context = memories + related
```

### 4. Graph Visualization

Export graph for visualization:

```python
graph = read_graph({
  "status": "active",
  "include_scores": true
})

# Convert to format for visualization tools:
# - Graphviz: dot format
# - D3.js: nodes/links arrays
# - Neo4j: Cypher import
# - Obsidian Canvas: .canvas format
```

## Automatic vs Manual Relations

### Automatic Relations

The clustering tool can auto-detect relations based on similarity:

```python
# Find similar memories
clusters = cluster_memories({
  "strategy": "similarity",
  "threshold": 0.85
})

# STM can suggest relations:
# High similarity (>0.9) -> "similar_to"
# Moderate (>0.8) -> "related_to"
```

### Manual Relations

Explicit relations you create:

```python
create_relation({
  "from_memory_id": "mem-123",
  "to_memory_id": "mem-456",
  "relation_type": "references"
})
```

Both types coexist. Manual relations have higher fidelity but require effort. Automatic relations provide coverage but may be noisy.

## Integration with Temporal Decay

Graph features respect temporal properties:

### 1. Relations Survive Forgetting

If a memory is forgotten (GC'd), its relations are deleted (CASCADE).

But: if one memory is promoted and another forgotten, the relation is preserved in the promoted memory's metadata.

### 2. Scoring Affects Graph Traversal

When following relations, low-scoring memories are less prominent:

```python
# Open memories with scores
open_memories({
  "memory_ids": [...],
  "include_scores": true
})

# Client can filter by score
memories_above_threshold = [m for m in result if m["score"] > 0.3]
```

### 3. Promotion Preserves Relations

When promoting a memory to Obsidian:
- Relations are recorded in note frontmatter
- Links to other memories (if also promoted) become wiki-links
- Un-promoted relation targets are noted as STM references

## Advanced: Graph Queries

While not yet built-in, you can build graph queries client-side:

```python
graph = read_graph({"status": "active"})

# Find all memories that reference project-x
project_x_memories = [
  m for m in graph["memories"]
  if "project-x" in m["entities"]
]

# Find all 2-hop neighbors of a memory
def get_neighbors(memory_id, graph, hops=2):
    neighbors = set()
    current = {memory_id}

    for _ in range(hops):
        next_hop = set()
        for mid in current:
            rels = [r for r in graph["relations"] if r["from"] == mid]
            next_hop.update(r["to"] for r in rels)
        neighbors.update(next_hop)
        current = next_hop

    return neighbors

# Strongly connected components
# Topological sort
# Path finding
# etc.
```

## Comparison to Reference Memory Server

| Feature | Reference Memory | CortexGraph |
|---------|-----------------|------------|
| **Primary Unit** | Entity (person, org) | Memory (time-bound info) |
| **Observations** | Attached to entities | N/A (content is primary) |
| **Relations** | Between entities | Between memories |
| **Temporal** | No decay | Exponential decay + promotion |
| **read_graph** | ✅ | ✅ |
| **search_nodes** | ✅ | ✅ (as search_memory) |
| **open_nodes** | ✅ | ✅ (as open_memories) |
| **create_entities** | ✅ | Via save_memory with entities |
| **create_relations** | ✅ | ✅ |
| **Persistence** | Permanent | Temporal → Optional promotion |

## Best Practices

1. **Use Entities Consistently**: Pick a naming scheme and stick to it
   - Good: `"project-x"`, `"john-smith"`
   - Avoid: `"Project X"`, `"John"`, `"john"`

2. **Relation Types**: Define a small set of relation types
   - Too many types → hard to query
   - Too few → lack of semantics
   - Recommended: 5-10 core types

3. **Bidirectional Relations**: Create both directions if needed
   ```python
   create_relation({"from": "A", "to": "B", "type": "references"})
   create_relation({"from": "B", "to": "A", "type": "referenced_by"})
   ```

4. **Metadata**: Use relation metadata for context
   ```python
   {
     "metadata": {
       "confidence": 0.8,
       "source": "auto-detected",
       "created_by": "clustering"
     }
   }
   ```

5. **Graph Size**: Monitor graph growth
   - Use `read_graph().stats` to track size
   - Run GC regularly to prune low-scoring memories
   - Consider archiving old but important memories

## Future Enhancements

Planned features:

1. **Graph Queries**: Built-in query language for graph traversal
2. **Automatic Relation Detection**: NER + coreference resolution
3. **Relation Types Ontology**: Predefined semantic types
4. **Graph Embeddings**: Node2Vec for memory embeddings based on structure
5. **Community Detection**: Find clusters of related memories
6. **Temporal Graph Analysis**: How relationships change over time
