# Storage Backends

CortexGraph supports multiple storage backends for short-term memory (STM).

## Choosing a Backend

**Use JSONL when:**
- Dataset size < 10,000 memories
- You want human-readable, git-friendly files
- You need easy inspection and manual editing
- Memory usage is not a concern

**Use SQLite when:**
- Dataset size > 10,000 memories
- Memory efficiency is important (low RAM usage)
- You need fast queries and filtering on large datasets
- You want ACID transaction guarantees

**Performance Characteristics:**

| Backend | Memory Count | RAM Usage | Search Speed | Git-Friendly |
|---------|--------------|-----------|--------------|--------------|
| JSONL   | < 10k        | High      | Fast        | ✅ Yes       |
| JSONL   | 10k - 50k    | Very High | Medium      | ✅ Yes       |
| JSONL   | > 50k        | Excessive | Slow        | ⚠️ Large diffs |
| SQLite  | Any size     | Low       | Fast        | ❌ Binary    |

## JSONL (Default)

The default backend uses human-readable JSONL (JSON Lines) files.

- **Path**: `~/.config/cortexgraph/jsonl/` (configurable)
- **Format**: One JSON object per line
- **Pros**:
  - Human-readable
  - Git-friendly (easy to diff and version control)
  - Easy to backup and inspect
  - No external dependencies
- **Cons**:
  - Loads entire dataset into memory (RAM)
  - Slower for very large datasets (>100k memories)

### Configuration

```bash
CORTEXGRAPH_STORAGE_BACKEND=jsonl
CORTEXGRAPH_STORAGE_PATH=~/.config/cortexgraph/jsonl
```

## SQLite

The SQLite backend uses a binary database file.

- **Path**: `~/.config/cortexgraph/cortexgraph.db` (configurable)
- **Format**: SQLite database
- **Pros**:
  - Efficient for large datasets
  - Low memory usage (doesn't load everything into RAM)
  - Fast queries and filtering
  - ACID transactions
- **Cons**:
  - Not human-readable
  - Binary file (not git-friendly for diffs)

### Configuration

```bash
CORTEXGRAPH_STORAGE_BACKEND=sqlite
# Optional: Custom path
# CORTEXGRAPH_SQLITE_PATH=~/.config/cortexgraph/my_db.sqlite
```

## Batch Operations (v1.2.0+)

For performance-critical operations, JSONL storage supports batch methods that are significantly faster than individual calls:

```python
from cortexgraph.storage.jsonl_storage import JSONLStorage

storage = JSONLStorage()
storage.connect()

# Batch delete memories (more efficient than loop)
memory_ids = ["id1", "id2", "id3"]
deleted_count = storage.delete_memories_batch(memory_ids)
print(f"Deleted {deleted_count} memories")

# Batch create relations
from cortexgraph.storage.models import Relation
relations = [
    Relation(from_id="mem-1", to_id="mem-2", type="related"),
    Relation(from_id="mem-2", to_id="mem-3", type="supports"),
]
storage.create_relations_batch(relations)
```

### Method Reference

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `delete_memories_batch` | `memory_ids: list[str]` | `int` (count deleted) | Delete multiple memories atomically |
| `create_relations_batch` | `relations: list[Relation]` | `int` (count created) | Create multiple relations atomically |

### Performance Benefits

These batch operations are used internally by consolidation agents for better performance:

- **Single I/O operation**: Writes all changes in one file operation instead of N operations
- **Index updates**: Updates in-memory indexes once instead of N times
- **Atomic**: All-or-nothing semantics for consistency

**When to use batch operations:**
- Consolidating multiple memories (SemanticMerge agent)
- Bulk cleanup during garbage collection
- Creating multiple relations from a cluster

## Markdown Export

CortexGraph includes a utility to export memories to Markdown files, useful for:
- Migrating data
- Backing up to a readable format
- Importing into other tools (Obsidian, Notion, etc.)

### Usage (Python)

```python
from pathlib import Path
from cortexgraph.tools.export import MarkdownExport
from cortexgraph.storage.sqlite_storage import SQLiteStorage

# Connect to storage
storage = SQLiteStorage()
storage.connect()

# Get all active memories
memories = storage.list_memories()

# Export
exporter = MarkdownExport(output_dir=Path("./exported_memories"))
stats = exporter.export_batch(memories)

print(f"Exported {stats.success} memories")
```

### Output Format

Each memory is saved as a `.md` file with YAML frontmatter:

```markdown
---
id: mem-123
created_at: 2023-10-27T10:00:00
status: active
tags:
  - python
  - coding
strength: 1.5
---

Memory content goes here...
```

## Migration Guide

### Migrating from JSONL to SQLite

If your dataset has grown large (>10k memories) and you want to switch to SQLite for better performance:

**Step 1: Backup your data**

```bash
# Backup current JSONL files
cp -r ~/.config/cortexgraph/jsonl ~/.config/cortexgraph/jsonl.backup
```

**Step 2: Export to Markdown (optional but recommended)**

```python
from pathlib import Path
from cortexgraph.tools.export import MarkdownExport
from cortexgraph.storage.jsonl_storage import JSONLStorage

# Read from JSONL
storage = JSONLStorage()
storage.connect()
memories = storage.list_memories()

# Export to Markdown as backup
exporter = MarkdownExport(output_dir=Path("./backup_export"))
stats = exporter.export_batch(memories)
print(f"Backed up {stats.success} memories")
```

**Step 3: Copy data from JSONL to SQLite**

```python
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.sqlite_storage import SQLiteStorage

# Read all data from JSONL
jsonl = JSONLStorage()
jsonl.connect()

memories = jsonl.list_memories()
relations = jsonl.list_relations()

# Write to SQLite
sqlite = SQLiteStorage()
sqlite.connect()

# Copy memories
for memory in memories:
    sqlite.save_memory(memory)

# Copy relations
for relation in relations:
    sqlite.create_relation(relation)

print(f"Migrated {len(memories)} memories and {len(relations)} relations")

jsonl.close()
sqlite.close()
```

**Step 4: Update configuration**

Update `~/.config/cortexgraph/.env`:

```bash
# Change from jsonl to sqlite
CORTEXGRAPH_STORAGE_BACKEND=sqlite
```

**Step 5: Test**

Restart your MCP server or application and verify memories are accessible:

```python
from cortexgraph.storage.sqlite_storage import SQLiteStorage

storage = SQLiteStorage()
storage.connect()
memories = storage.list_memories()
print(f"Found {len(memories)} memories in SQLite")
storage.close()
```

### Migrating from SQLite to JSONL

If you want to switch back to JSONL (e.g., for better git integration):

**Step 1: Backup SQLite database**

```bash
cp ~/.config/cortexgraph/cortexgraph.db ~/.config/cortexgraph/cortexgraph.db.backup
```

**Step 2: Copy data from SQLite to JSONL**

```python
from cortexgraph.storage.jsonl_storage import JSONLStorage
from cortexgraph.storage.sqlite_storage import SQLiteStorage

# Read all data from SQLite
sqlite = SQLiteStorage()
sqlite.connect()

memories = sqlite.list_memories()
relations = sqlite.list_relations()

# Write to JSONL
jsonl = JSONLStorage()
jsonl.connect()

# Copy memories
for memory in memories:
    jsonl.save_memory(memory)

# Copy relations
for relation in relations:
    jsonl.create_relation(relation)

print(f"Migrated {len(memories)} memories and {len(relations)} relations")

sqlite.close()
jsonl.close()
```

**Step 3: Update configuration**

Update `~/.config/cortexgraph/.env`:

```bash
# Change from sqlite to jsonl
CORTEXGRAPH_STORAGE_BACKEND=jsonl
```

**Step 4: Test**

Verify the migration:

```python
from cortexgraph.storage.jsonl_storage import JSONLStorage

storage = JSONLStorage()
storage.connect()
memories = storage.list_memories()
print(f"Found {len(memories)} memories in JSONL")
storage.close()
```

### Migration Safety Tips

1. **Always backup before migrating** - Keep your original data until you've verified the migration
2. **Test with small subset first** - If you have many memories, test the migration script on a subset
3. **Verify data integrity** - Check memory counts and spot-check a few memories after migration
4. **Keep Markdown exports** - Export to Markdown as a human-readable backup format
5. **No data loss** - Both backends support the same data model, so no information is lost in migration
