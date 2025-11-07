# Converter Quick Reference

## One-Liner Commands

```bash
# Basic conversion (default paths)
python scripts/convert_to_memory_mcp.py

# Dry run preview
python scripts/convert_to_memory_mcp.py --dry-run --verbose

# Custom paths
python scripts/convert_to_memory_mcp.py \
  --memories-input data/memories.jsonl \
  --relations-input data/relations.jsonl \
  --output memory.json

# Run tests
python scripts/test_convert_to_memory_mcp.py
```

## Input/Output Quick View

### Input (Mnemex JSONL)

**memories.jsonl** - One JSON per line:
```json
{"id": "mem-123", "content": "...", "meta": {...}, "entities": [...], ...}
```

**relations.jsonl** - One JSON per line:
```json
{"id": "rel-456", "from_memory_id": "mem-123", "to_memory_id": "mem-789", ...}
```

### Output (Memory MCP JSON)

**memory.json** - Single JSON file:
```json
{
  "entities": [
    {"name": "mem-123", "entityType": "memory", "observations": [...]}
  ],
  "relations": [
    {"from": "mem-123", "to": "mem-789", "relationType": "related"}
  ]
}
```

## Conversion Rules

| Mnemex → Memory MCP |
|---------------------|
| `memory` → `entity` with `entityType: "memory"` |
| `memory.id` → `entity.name` |
| `memory.content` → `entity.observations[]` |
| `memory.meta.tags` → `entity.observations[]` as "Tags: ..." |
| `memory.entities` → `entity.observations[]` as "Entities: ..." |
| `relation` → `relation` (simplified) |
| `relation.from_memory_id` → `relation.from` |
| `relation.to_memory_id` → `relation.to` |
| `relation.relation_type` → `relation.relationType` |

## Default Paths

- **Input memories:** `~/.config/cortexgraph/jsonl/memories.jsonl`
- **Input relations:** `~/.config/cortexgraph/jsonl/relations.jsonl`
- **Output:** `memory.json` (current directory)

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--memories-input PATH` | | Path to memories.jsonl |
| `--relations-input PATH` | | Path to relations.jsonl |
| `--output PATH` | `-o` | Output memory.json path |
| `--dry-run` | | Preview without writing |
| `--verbose` | `-v` | Detailed output |
| `--help` | `-h` | Show help |

## Common Use Cases

### Migration to Memory MCP
```bash
python scripts/convert_to_memory_mcp.py --output memory.json
# Then configure Memory MCP to use memory.json
```

### Daily Backup
```bash
python scripts/convert_to_memory_mcp.py \
  --output "backups/memory_$(date +%Y%m%d).json"
```

### Analysis Export
```bash
python scripts/convert_to_memory_mcp.py \
  --output analysis/snapshot.json --verbose
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| File not found | Check `~/.config/cortexgraph/jsonl/` exists |
| Empty output | Verify cortexgraph has saved memories |
| Invalid JSON warning | Run `cortexgraph-maintenance compact` |
| Validation error | Use `--verbose` to identify issue |

## Integration Example

```json
{
  "mcpServers": {
    "cortexgraph": {
      "command": "cortexgraph"
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE_PATH": "/path/to/memory.json"
      }
    }
  }
}
```

## Test Suite

```bash
# Run all tests
python scripts/test_convert_to_memory_mcp.py

# Expected output
Running tests...
✓ test_convert_memory_to_entity passed
✓ test_convert_memory_with_minimal_fields passed
✓ test_convert_relation passed
✓ test_validate_output_valid passed
✓ test_validate_output_invalid passed
✓ test_full_conversion passed
✓ test_empty_files passed
✓ test_meta_as_json_string passed

8/8 tests passed
All tests passed! ✓
```

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## Documentation

- Full guide: [README_CONVERTER.md](README_CONVERTER.md)
- Mnemex docs: [../README.md](../README.md)
- Memory MCP: https://github.com/modelcontextprotocol/servers/tree/main/src/memory
