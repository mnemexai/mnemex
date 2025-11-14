#!/usr/bin/env python3
"""Convert cortexgraph JSONL format to Anthropic Memory MCP format.

This script converts cortexgraph memories and relations to the memory.json format
used by Anthropic's Memory MCP server.

Conversion Logic:
-----------------
1. Each cortexgraph memory becomes a Memory MCP entity:
   - name: memory.id (unique identifier)
   - entityType: "memory"
   - observations: [content, tags as formatted strings, entities as formatted strings]

2. Each cortexgraph relation becomes a Memory MCP relation:
   - from: relation.from_memory_id
   - to: relation.to_memory_id
   - relationType: relation.relation_type

Input Format (cortexgraph):
---------------------
memories.jsonl:
{
  "id": "mem-123",
  "content": "User prefers TypeScript over JavaScript",
  "meta": {"tags": ["preferences", "typescript"], "source": "conversation", ...},
  "entities": ["TypeScript", "JavaScript"],
  "created_at": 1234567890,
  "last_used": 1234567890,
  "use_count": 5,
  "strength": 1.2,
  ...
}

relations.jsonl:
{
  "id": "rel-456",
  "from_memory_id": "mem-123",
  "to_memory_id": "mem-789",
  "relation_type": "related",
  "strength": 0.8,
  ...
}

Output Format (Memory MCP):
--------------------------
memory.json:
{
  "entities": [
    {
      "name": "mem-123",
      "entityType": "memory",
      "observations": [
        "Content: User prefers TypeScript over JavaScript",
        "Tags: preferences, typescript",
        "Entities: TypeScript, JavaScript",
        "Created: 2009-02-13 23:31:30",
        "Use count: 5",
        "Strength: 1.2"
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

Usage:
------
    # Basic usage with default paths
    python convert_to_memory_mcp.py

    # Specify custom input/output paths
    python convert_to_memory_mcp.py \\
        --memories-input ~/.config/cortexgraph/jsonl/memories.jsonl \\
        --relations-input ~/.config/cortexgraph/jsonl/relations.jsonl \\
        --output memory.json

    # Dry run to preview conversion
    python convert_to_memory_mcp.py --dry-run

    # Verbose output
    python convert_to_memory_mcp.py --verbose

Examples:
---------
    # Convert default cortexgraph storage to memory.json
    $ python convert_to_memory_mcp.py
    Converted 42 memories and 17 relations to memory.json

    # Preview conversion without writing file
    $ python convert_to_memory_mcp.py --dry-run --verbose
    Would convert 42 memories:
      - mem-123: User prefers TypeScript...
      - mem-456: API authentication uses JWT...
    Would convert 17 relations:
      - mem-123 -> mem-789 (related)
      - mem-456 -> mem-123 (references)

Requirements:
------------
    - Python 3.10+
    - No external dependencies (uses stdlib only)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def convert_memory_to_entity(memory: dict[str, Any]) -> dict[str, Any]:
    """Convert a cortexgraph memory to a Memory MCP entity.

    Args:
        memory: Dictionary containing cortexgraph memory data

    Returns:
        Dictionary in Memory MCP entity format with name, entityType, and observations
    """
    # Extract metadata
    meta = memory.get("meta", {})
    if isinstance(meta, str):
        meta = json.loads(meta)

    tags = meta.get("tags", [])
    entities = memory.get("entities", [])
    created_at = memory.get("created_at")
    use_count = memory.get("use_count", 0)
    strength = memory.get("strength", 1.0)
    source = meta.get("source")
    context = meta.get("context")

    # Build observations list
    observations = []

    # Primary content
    content = memory.get("content", "")
    if content:
        observations.append(f"Content: {content}")

    # Tags
    if tags:
        observations.append(f"Tags: {', '.join(tags)}")

    # Entities
    if entities:
        observations.append(f"Entities: {', '.join(entities)}")

    # Created timestamp (human-readable)
    if created_at:
        try:
            dt = datetime.fromtimestamp(created_at)
            observations.append(f"Created: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except (ValueError, OSError):
            observations.append(f"Created: {created_at}")

    # Use count
    if use_count > 0:
        observations.append(f"Use count: {use_count}")

    # Strength (if not default)
    if strength != 1.0:
        observations.append(f"Strength: {strength:.2f}")

    # Source
    if source:
        observations.append(f"Source: {source}")

    # Context
    if context:
        observations.append(f"Context: {context}")

    # Return entity
    return {
        "name": memory["id"],
        "entityType": "memory",
        "observations": observations,
    }


def convert_relation(relation: dict[str, Any]) -> dict[str, Any]:
    """Convert a cortexgraph relation to a Memory MCP relation.

    Args:
        relation: Dictionary containing cortexgraph relation data

    Returns:
        Dictionary in Memory MCP relation format with from, to, and relationType
    """
    return {
        "from": relation["from_memory_id"],
        "to": relation["to_memory_id"],
        "relationType": relation["relation_type"],
    }


def load_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """Load JSONL file into list of dictionaries.

    Args:
        file_path: Path to JSONL file

    Returns:
        List of dictionaries parsed from JSONL

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    records = []
    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(
                    f"Warning: Skipping invalid JSON on line {line_num}: {e}",
                    file=sys.stderr,
                )
    return records


def validate_output(output: dict[str, Any]) -> list[str]:
    """Validate the output format matches Memory MCP schema.

    Args:
        output: Dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check top-level structure
    if "entities" not in output:
        errors.append("Missing required field: entities")
    if "relations" not in output:
        errors.append("Missing required field: relations")

    # Validate entities
    if "entities" in output:
        if not isinstance(output["entities"], list):
            errors.append("entities must be a list")
        else:
            for i, entity in enumerate(output["entities"]):
                if "name" not in entity:
                    errors.append(f"Entity {i}: missing required field 'name'")
                if "entityType" not in entity:
                    errors.append(f"Entity {i}: missing required field 'entityType'")
                if "observations" not in entity:
                    errors.append(f"Entity {i}: missing required field 'observations'")
                elif not isinstance(entity["observations"], list):
                    errors.append(f"Entity {i}: observations must be a list")

    # Validate relations
    if "relations" in output:
        if not isinstance(output["relations"], list):
            errors.append("relations must be a list")
        else:
            for i, relation in enumerate(output["relations"]):
                if "from" not in relation:
                    errors.append(f"Relation {i}: missing required field 'from'")
                if "to" not in relation:
                    errors.append(f"Relation {i}: missing required field 'to'")
                if "relationType" not in relation:
                    errors.append(f"Relation {i}: missing required field 'relationType'")

    return errors


def convert(
    memories_path: Path,
    relations_path: Path,
    output_path: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Convert cortexgraph JSONL files to Memory MCP format.

    Args:
        memories_path: Path to memories.jsonl
        relations_path: Path to relations.jsonl
        output_path: Path to output memory.json
        dry_run: If True, don't write output file
        verbose: If True, print detailed conversion info

    Returns:
        Dictionary containing converted data

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If conversion produces invalid output
    """
    # Load input files
    if verbose:
        print(f"Loading memories from {memories_path}")
    memories = load_jsonl(memories_path)

    if verbose:
        print(f"Loading relations from {relations_path}")
    relations = load_jsonl(relations_path)

    # Convert
    if verbose:
        print(f"Converting {len(memories)} memories to entities...")
    entities = [convert_memory_to_entity(m) for m in memories]

    if verbose:
        print(f"Converting {len(relations)} relations...")
    converted_relations = [convert_relation(r) for r in relations]

    # Build output
    output = {"entities": entities, "relations": converted_relations}

    # Validate
    validation_errors = validate_output(output)
    if validation_errors:
        raise ValueError(
            "Output validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
        )

    # Write output (unless dry run)
    if dry_run:
        if verbose:
            print("\n[DRY RUN] Would write to:", output_path)
            print(f"Entities: {len(entities)}")
            print(f"Relations: {len(converted_relations)}")
            if entities:
                print("\nSample entity:")
                print(json.dumps(entities[0], indent=2))
            if converted_relations:
                print("\nSample relation:")
                print(json.dumps(converted_relations[0], indent=2))
    else:
        if verbose:
            print(f"Writing to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        if verbose:
            print(
                f"Successfully wrote {len(entities)} entities and {len(converted_relations)} relations"
            )

    return output


def get_default_paths() -> tuple[Path, Path]:
    """Get default paths for cortexgraph storage.

    Returns:
        Tuple of (memories_path, relations_path)
    """
    # Try to read from environment or use default
    import os

    storage_path = os.getenv("CORTEXGRAPH_STORAGE_PATH", "~/.config/cortexgraph/jsonl")
    storage_path = Path(storage_path).expanduser()

    return (
        storage_path / "memories.jsonl",
        storage_path / "relations.jsonl",
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert cortexgraph JSONL format to Anthropic Memory MCP format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --dry-run --verbose
  %(prog)s --memories-input data/memories.jsonl --output memory.json
        """,
    )

    # Input arguments
    memories_default, relations_default = get_default_paths()
    parser.add_argument(
        "--memories-input",
        type=Path,
        default=memories_default,
        help=f"Path to memories.jsonl (default: {memories_default})",
    )
    parser.add_argument(
        "--relations-input",
        type=Path,
        default=relations_default,
        help=f"Path to relations.jsonl (default: {relations_default})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("memory.json"),
        help="Path to output memory.json (default: memory.json)",
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview conversion without writing output file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed conversion information",
    )

    args = parser.parse_args()

    # Convert
    try:
        output = convert(
            memories_path=args.memories_input,
            relations_path=args.relations_input,
            output_path=args.output,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        # Print summary
        if not args.verbose:
            if args.dry_run:
                print(
                    f"[DRY RUN] Would convert {len(output['entities'])} memories "
                    f"and {len(output['relations'])} relations to {args.output}"
                )
            else:
                print(
                    f"Converted {len(output['entities'])} memories "
                    f"and {len(output['relations'])} relations to {args.output}"
                )

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
