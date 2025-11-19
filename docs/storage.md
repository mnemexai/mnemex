# Storage Backends

CortexGraph supports multiple storage backends for short-term memory (STM).

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
