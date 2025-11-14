#!/usr/bin/env python3
"""Tests for convert_to_memory_mcp.py"""

import json

# Import the converter module
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert_to_memory_mcp import (
    convert,
    convert_memory_to_entity,
    convert_relation,
    validate_output,
)


def test_convert_memory_to_entity():
    """Test memory to entity conversion."""
    # Sample cortexgraph memory
    memory = {
        "id": "mem-123",
        "content": "User prefers TypeScript over JavaScript",
        "meta": {
            "tags": ["preferences", "typescript"],
            "source": "conversation",
            "context": "Discussing project setup",
        },
        "entities": ["TypeScript", "JavaScript"],
        "created_at": 1234567890,
        "last_used": 1234567890,
        "use_count": 5,
        "strength": 1.2,
        "status": "active",
    }

    entity = convert_memory_to_entity(memory)

    # Verify structure
    assert entity["name"] == "mem-123"
    assert entity["entityType"] == "memory"
    assert isinstance(entity["observations"], list)

    # Verify observations content
    observations = entity["observations"]
    assert any("TypeScript over JavaScript" in obs for obs in observations)
    assert any("Tags: preferences, typescript" in obs for obs in observations)
    assert any("Entities: TypeScript, JavaScript" in obs for obs in observations)
    assert any("Use count: 5" in obs for obs in observations)
    assert any("Strength: 1.20" in obs for obs in observations)
    assert any("Source: conversation" in obs for obs in observations)
    assert any("Context: Discussing project setup" in obs for obs in observations)

    print("✓ test_convert_memory_to_entity passed")


def test_convert_memory_with_minimal_fields():
    """Test memory conversion with only required fields."""
    memory = {
        "id": "mem-456",
        "content": "Minimal memory example",
    }

    entity = convert_memory_to_entity(memory)

    assert entity["name"] == "mem-456"
    assert entity["entityType"] == "memory"
    assert len(entity["observations"]) == 1
    assert entity["observations"][0] == "Content: Minimal memory example"

    print("✓ test_convert_memory_with_minimal_fields passed")


def test_convert_relation():
    """Test relation conversion."""
    relation = {
        "id": "rel-789",
        "from_memory_id": "mem-123",
        "to_memory_id": "mem-456",
        "relation_type": "related",
        "strength": 0.8,
    }

    converted = convert_relation(relation)

    assert converted["from"] == "mem-123"
    assert converted["to"] == "mem-456"
    assert converted["relationType"] == "related"
    # Note: strength is NOT included in Memory MCP format
    assert "strength" not in converted

    print("✓ test_convert_relation passed")


def test_validate_output_valid():
    """Test validation with valid output."""
    output = {
        "entities": [
            {
                "name": "mem-123",
                "entityType": "memory",
                "observations": ["Test observation"],
            }
        ],
        "relations": [{"from": "mem-123", "to": "mem-456", "relationType": "related"}],
    }

    errors = validate_output(output)
    assert len(errors) == 0

    print("✓ test_validate_output_valid passed")


def test_validate_output_invalid():
    """Test validation with invalid output."""
    # Missing required fields
    output = {
        "entities": [
            {"name": "mem-123"}  # Missing entityType and observations
        ],
        "relations": [{"from": "mem-123"}],  # Missing to and relationType
    }

    errors = validate_output(output)
    assert len(errors) > 0
    assert any("entityType" in e for e in errors)
    assert any("observations" in e for e in errors)
    assert any("to" in e for e in errors)
    assert any("relationType" in e for e in errors)

    print("✓ test_validate_output_invalid passed")


def test_full_conversion():
    """Test full conversion pipeline."""
    # Create temporary input files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        memories_file = tmpdir / "memories.jsonl"
        relations_file = tmpdir / "relations.jsonl"
        output_file = tmpdir / "memory.json"

        # Write sample data
        memories = [
            {
                "id": "mem-1",
                "content": "First memory",
                "meta": {"tags": ["test"]},
                "entities": ["Entity1"],
                "created_at": 1234567890,
                "use_count": 3,
            },
            {
                "id": "mem-2",
                "content": "Second memory",
                "meta": {"tags": ["test", "example"]},
                "entities": ["Entity2"],
                "created_at": 1234567900,
                "use_count": 1,
            },
        ]

        relations = [
            {
                "id": "rel-1",
                "from_memory_id": "mem-1",
                "to_memory_id": "mem-2",
                "relation_type": "references",
                "strength": 0.9,
            }
        ]

        with open(memories_file, "w") as f:
            for mem in memories:
                f.write(json.dumps(mem) + "\n")

        with open(relations_file, "w") as f:
            for rel in relations:
                f.write(json.dumps(rel) + "\n")

        # Convert
        output = convert(
            memories_path=memories_file,
            relations_path=relations_file,
            output_path=output_file,
            dry_run=False,
            verbose=False,
        )

        # Verify output structure
        assert len(output["entities"]) == 2
        assert len(output["relations"]) == 1

        # Verify file was written
        assert output_file.exists()

        # Load and verify written file
        with open(output_file) as f:
            loaded = json.load(f)

        assert loaded["entities"][0]["name"] == "mem-1"
        assert loaded["entities"][1]["name"] == "mem-2"
        assert loaded["relations"][0]["from"] == "mem-1"
        assert loaded["relations"][0]["to"] == "mem-2"
        assert loaded["relations"][0]["relationType"] == "references"

        print("✓ test_full_conversion passed")


def test_empty_files():
    """Test conversion with empty input files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        memories_file = tmpdir / "memories.jsonl"
        relations_file = tmpdir / "relations.jsonl"
        output_file = tmpdir / "memory.json"

        # Create empty files
        memories_file.touch()
        relations_file.touch()

        # Convert
        output = convert(
            memories_path=memories_file,
            relations_path=relations_file,
            output_path=output_file,
            dry_run=False,
            verbose=False,
        )

        # Should produce valid but empty output
        assert len(output["entities"]) == 0
        assert len(output["relations"]) == 0

        # Verify file was written
        assert output_file.exists()

        print("✓ test_empty_files passed")


def test_meta_as_json_string():
    """Test memory with meta field as JSON string (from database)."""
    memory = {
        "id": "mem-789",
        "content": "Test memory",
        "meta": json.dumps({"tags": ["tag1", "tag2"], "source": "test"}),
        "entities": ["TestEntity"],
        "created_at": 1234567890,
    }

    entity = convert_memory_to_entity(memory)

    assert entity["name"] == "mem-789"
    observations = entity["observations"]
    assert any("Tags: tag1, tag2" in obs for obs in observations)
    assert any("Source: test" in obs for obs in observations)

    print("✓ test_meta_as_json_string passed")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_convert_memory_to_entity,
        test_convert_memory_with_minimal_fields,
        test_convert_relation,
        test_validate_output_valid,
        test_validate_output_invalid,
        test_full_conversion,
        test_empty_files,
        test_meta_as_json_string,
    ]

    print("Running tests...\n")
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print(f"\n{passed}/{len(tests)} tests passed")
    if failed > 0:
        print(f"{failed} tests failed")
        sys.exit(1)
    else:
        print("\nAll tests passed! ✓")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
