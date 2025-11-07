# CortexGraph to Memory MCP Converter

This script converts CortexGraph's JSONL memory format to Anthropic's Memory MCP `memory.json` format, enabling interoperability between the two memory systems.

> **Note:** CortexGraph was formerly known as "mnemex". Some field references below still use "Mnemex" when referring to the JSONL format structure.

## Overview

**Script:** `convert_to_memory_mcp.py`
**Tests:** `test_convert_to_memory_mcp.py`

### What It Does

Converts cortexgraph memories and relations into the entity-observation format used by Anthropic's Memory MCP server:

- **Mnemex memories** → **Memory MCP entities** (with observations)
- **Mnemex relations** → **Memory MCP relations** (from/to/relationType)

## Usage

### Basic Usage

Convert using default cortexgraph storage paths:

```bash
python scripts/convert_to_memory_mcp.py
```

This reads from:
- `~/.config/cortexgraph/jsonl/memories.jsonl`
- `~/.config/cortexgraph/jsonl/relations.jsonl`

And writes to:
- `memory.json` (in current directory)

### Custom Paths

Specify input and output files:

```bash
python scripts/convert_to_memory_mcp.py \
    --memories-input data/memories.jsonl \
    --relations-input data/relations.jsonl \
    --output memory.json
```

### Dry Run

Preview conversion without writing files:

```bash
python scripts/convert_to_memory_mcp.py --dry-run --verbose
```

### Verbose Output

See detailed conversion information:

```bash
python scripts/convert_to_memory_mcp.py --verbose
```

## Input Format (Mnemex)

### memories.jsonl

One JSON object per line:

```json
{
  "id": "mem-123",
  "content": "User prefers TypeScript over JavaScript",
  "meta": {
    "tags": ["preferences", "typescript"],
    "source": "conversation",
    "context": "Discussing project setup"
  },
  "entities": ["TypeScript", "JavaScript"],
  "created_at": 1704067200,
  "last_used": 1730678400,
  "use_count": 5,
  "strength": 1.2,
  "status": "active"
}
```

### relations.jsonl

One JSON object per line:

```json
{
  "id": "rel-456",
  "from_memory_id": "mem-123",
  "to_memory_id": "mem-789",
  "relation_type": "related",
  "strength": 0.8,
  "created_at": 1704153600
}
```

## Output Format (Memory MCP)

### memory.json

Single JSON file with entities and relations:

```json
{
  "entities": [
    {
      "name": "mem-123",
      "entityType": "memory",
      "observations": [
        "Content: User prefers TypeScript over JavaScript",
        "Tags: preferences, typescript",
        "Entities: TypeScript, JavaScript",
        "Created: 2023-12-31 19:00:00",
        "Use count: 5",
        "Strength: 1.20",
        "Source: conversation",
        "Context: Discussing project setup"
      ]
    }
  ],
  "relations": [
    {
      "from": "mem-123",
      "to": "mem-789",
      "relationType": "related"
    }
  ]
}
```

## Conversion Logic

### Memory → Entity

Each cortexgraph memory becomes a Memory MCP entity with:

- **name**: Memory ID (e.g., `mem-123`)
- **entityType**: Always set to `"memory"`
- **observations**: Array of formatted strings containing:
  - Content (primary memory text)
  - Tags (comma-separated)
  - Entities (comma-separated)
  - Created timestamp (human-readable)
  - Use count (if > 0)
  - Strength (if ≠ 1.0)
  - Source (if present)
  - Context (if present)

### Relation → Relation

Each cortexgraph relation becomes a Memory MCP relation with:

- **from**: Source memory ID
- **to**: Target memory ID
- **relationType**: Relation type (preserved from cortexgraph)

**Note:** Mnemex relation `strength` is NOT preserved in Memory MCP format.

## Field Mapping Reference

| Mnemex Field | Memory MCP Field | Notes |
|-------------|------------------|-------|
| `memory.id` | `entity.name` | Unique identifier |
| `memory.content` | `entity.observations[0]` | Primary content |
| `memory.meta.tags` | `entity.observations[]` | Formatted as "Tags: a, b, c" |
| `memory.entities` | `entity.observations[]` | Formatted as "Entities: X, Y, Z" |
| `memory.created_at` | `entity.observations[]` | Formatted as "Created: YYYY-MM-DD HH:MM:SS" |
| `memory.use_count` | `entity.observations[]` | Formatted as "Use count: N" |
| `memory.strength` | `entity.observations[]` | Formatted as "Strength: N.NN" |
| `memory.meta.source` | `entity.observations[]` | Formatted as "Source: X" |
| `memory.meta.context` | `entity.observations[]` | Formatted as "Context: X" |
| `relation.from_memory_id` | `relation.from` | Direct mapping |
| `relation.to_memory_id` | `relation.to` | Direct mapping |
| `relation.relation_type` | `relation.relationType` | Direct mapping |

### Fields NOT Converted

These cortexgraph fields are not included in Memory MCP output:

- `memory.last_used`
- `memory.status`
- `memory.promoted_at`
- `memory.promoted_to`
- `memory.embed`
- `memory.review_priority`
- `memory.last_review_at`
- `memory.review_count`
- `memory.cross_domain_count`
- `relation.id`
- `relation.strength`
- `relation.created_at`
- `relation.metadata`

## Examples

### Example 1: Basic Conversion

```bash
# Convert default cortexgraph storage
$ python scripts/convert_to_memory_mcp.py
Converted 42 memories and 17 relations to memory.json
```

### Example 2: Dry Run with Preview

```bash
# Preview conversion
$ python scripts/convert_to_memory_mcp.py --dry-run --verbose
Loading memories from /Users/sc/.config/cortexgraph/jsonl/memories.jsonl
Loading relations from /Users/sc/.config/cortexgraph/jsonl/relations.jsonl
Converting 42 memories to entities...
Converting 17 relations...

[DRY RUN] Would write to: memory.json
Entities: 42
Relations: 17

Sample entity:
{
  "name": "mem-123",
  "entityType": "memory",
  "observations": [
    "Content: User prefers TypeScript over JavaScript",
    "Tags: preferences, typescript",
    ...
  ]
}

Sample relation:
{
  "from": "mem-123",
  "to": "mem-456",
  "relationType": "related"
}
```

### Example 3: Custom Paths

```bash
# Convert specific files
$ python scripts/convert_to_memory_mcp.py \
    --memories-input backups/memories_2024-11-04.jsonl \
    --relations-input backups/relations_2024-11-04.jsonl \
    --output exports/memory_export.json
Converted 35 memories and 12 relations to exports/memory_export.json
```

## Testing

Run the test suite:

```bash
python scripts/test_convert_to_memory_mcp.py
```

Tests cover:
- Memory to entity conversion
- Relation conversion
- Output validation
- Full pipeline
- Edge cases (empty files, minimal fields, JSON string meta)

All tests should pass:

```
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

## Error Handling

The script validates both input and output:

### Input Validation
- Checks file existence
- Handles malformed JSON (skips invalid lines with warnings)
- Supports empty files (produces valid empty output)

### Output Validation
- Ensures all required fields are present
- Validates data types (arrays, strings)
- Reports specific validation errors

### Example Error Output

```bash
$ python scripts/convert_to_memory_mcp.py --memories-input missing.jsonl
Error: Input file not found: missing.jsonl

$ python scripts/convert_to_memory_mcp.py # with invalid data
Validation error: Output validation failed:
  - Entity 0: missing required field 'observations'
  - Relation 2: missing required field 'relationType'
```

## Integration with Memory MCP

After conversion, use the output file with Anthropic's Memory MCP server:

1. **Convert cortexgraph data:**
   ```bash
   python scripts/convert_to_memory_mcp.py --output memory.json
   ```

2. **Configure Memory MCP** to use the generated file:
   ```json
   {
     "mcpServers": {
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

3. **Use both systems** (if desired):
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

## Use Cases

### 1. Migration from Mnemex to Memory MCP

If switching from cortexgraph to Memory MCP:

```bash
# Export current cortexgraph data
python scripts/convert_to_memory_mcp.py --output memory_export.json

# Update MCP config to use Memory MCP with exported data
# (see Integration section above)
```

### 2. Data Analysis

Export cortexgraph data to analyze with tools that understand the Memory MCP format:

```bash
# Convert for analysis
python scripts/convert_to_memory_mcp.py --output analysis/memory_snapshot.json

# Use with visualization tools that support Memory MCP format
```

### 3. Interoperability

Run both systems side-by-side, periodically syncing cortexgraph → Memory MCP:

```bash
# Daily export from cortexgraph to Memory MCP
0 0 * * * python /path/to/convert_to_memory_mcp.py --output /path/to/memory.json
```

### 4. Backup and Export

Create periodic snapshots in Memory MCP format:

```bash
# Export with timestamp
python scripts/convert_to_memory_mcp.py \
    --output "backups/memory_$(date +%Y%m%d).json"
```

## Limitations

### Information Loss

Some cortexgraph-specific features are not preserved:

1. **Temporal decay metadata**: `last_used`, `review_priority`, etc.
2. **Relation strength**: Memory MCP relations don't have strength values
3. **Status tracking**: `promoted_at`, `promoted_to`, `status`
4. **Embeddings**: `embed` vectors are not included

These fields are captured in observations as text but not as structured data.

### One-Way Conversion

This converter only works **cortexgraph → Memory MCP**. There is no reverse converter (Memory MCP → cortexgraph).

### Entity Type Limitation

All converted entities have `entityType: "memory"`. Memory MCP supports multiple entity types (person, organization, etc.), but this converter treats all memories uniformly.

## Requirements

- **Python:** 3.10+
- **Dependencies:** None (uses stdlib only)
- **Input:** Valid cortexgraph JSONL files
- **Output:** Compatible with Memory MCP format

## Development

### Code Structure

```python
# Main conversion functions
convert_memory_to_entity(memory: dict) -> dict
convert_relation(relation: dict) -> dict

# Pipeline
convert(memories_path, relations_path, output_path) -> dict

# Validation
validate_output(output: dict) -> list[str]

# CLI
main()
```

### Adding New Observation Types

To include additional memory fields as observations:

1. Edit `convert_memory_to_entity()` function
2. Add new observation format
3. Update tests in `test_convert_to_memory_mcp.py`
4. Update documentation (this README)

Example:

```python
# Add review count to observations
review_count = memory.get("review_count", 0)
if review_count > 0:
    observations.append(f"Review count: {review_count}")
```

## Troubleshooting

### Issue: "Input file not found"

**Cause:** Specified JSONL files don't exist

**Solution:** Check paths, ensure cortexgraph has created storage files:

```bash
# Check default storage path
ls -la ~/.config/cortexgraph/jsonl/

# Or check custom path from .env
echo $MNEMEX_STORAGE_PATH
```

### Issue: "Validation error: missing required field"

**Cause:** Malformed cortexgraph data or converter bug

**Solution:** Run with `--verbose` to see which entities/relations are problematic:

```bash
python scripts/convert_to_memory_mcp.py --verbose 2>&1 | less
```

### Issue: "Warning: Skipping invalid JSON on line X"

**Cause:** Corrupted JSONL file

**Solution:** This is non-fatal. Valid records are still converted. To fix:

```bash
# Use cortexgraph maintenance tool to compact storage
cortexgraph-maintenance compact
```

### Issue: Empty output file

**Cause:** Input files are empty or contain no valid records

**Solution:** Verify cortexgraph has saved memories:

```bash
# Check record count
wc -l ~/.config/cortexgraph/jsonl/memories.jsonl
wc -l ~/.config/cortexgraph/jsonl/relations.jsonl
```

## License

MIT License (same as cortexgraph)

## Related Documentation

- [Mnemex README](../README.md) - Main cortexgraph documentation
- [Mnemex Storage](../src/cortexgraph/storage/) - JSONL storage implementation
- [Memory MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) - Anthropic's Memory MCP
- [Model Context Protocol](https://github.com/modelcontextprotocol) - MCP specification

## Questions?

File issues on GitHub: https://github.com/simplemindedbot/cortexgraph/issues
