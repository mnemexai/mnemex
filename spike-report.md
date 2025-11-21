# Storage Backend Parity Spike Report

## Objective
Verify that JSONL and SQLite storage backends behave identically regarding relationship management to ensure consistent graph visualization.

## Findings

### 1. Foreign Key Enforcement
**Issue**: SQLite enforces foreign key constraints on `Relation` creation (ensuring `from_memory_id` and `to_memory_id` exist), while JSONL storage does not.
**Impact**: Data integrity issues in JSONL storage; potential for "ghost" edges in graph visualization.
**Resolution**: Implement validation in `JSONLStorage.create_relation` to check for existence of source and target memories.

### 2. Method Naming
**Issue**: Initial assumption of `add_memory`/`add_relation` was incorrect.
**Resolution**: Verified correct methods are `save_memory` and `create_relation`.

## Verification Suite
A comprehensive test suite `tests/parity/test_relationship_parity_suite.py` has been created covering:
- All relationship types
- Multiple relationships between same nodes
- Non-existent source/target handling (Parity fix required)
- Large number of relationships

## Conclusion
With the fix for Foreign Key enforcement in JSONL, the backends will have sufficient parity for the graph visualization feature.
