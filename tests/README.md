# CortexGraph Test Suite

Comprehensive test suite for the CortexGraph temporal memory system with natural spaced repetition.

## Overview

- **869 tests** across 28 files
- **99%+ code coverage**
- **Organized by component**: tools, core logic, security, storage
- **Shared fixtures** in `conftest.py` for consistency

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_tools_memory_management.py

# Single test
pytest tests/test_tools_memory_management.py::TestSaveMemory::test_save_basic_memory

# With coverage report
pytest --cov=cortexgraph --cov-report=html
# Open htmlcov/index.html to view

# Watch mode (run tests on file changes)
pytest-watch

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## Test Organization

### Consolidated Test Files (v0.7.0+)

Tests are organized into logical groups:

- **`test_tools_memory_management.py`** - Memory lifecycle (save, touch, gc, promote, open)
- **`test_tools_graph_operations.py`** - Graph operations (relations, read_graph)
- **`test_tools_analysis.py`** - Analysis tools (cluster, consolidate)
- **`test_security_*.py`** - Security validators and permissions
- **`test_storage.py`** - JSONL storage layer
- **`test_review.py`** - Natural spaced repetition
- **`test_auto_recall.py`** - Natural language activation
- **`test_search_unified.py`** - Unified STM+LTM search

### Legacy Organization (pre-v0.7.0)

Older branches may have individual test files per tool (`test_tools_save.py`, `test_tools_search.py`, etc.).

## Shared Fixtures

All fixtures are defined in `conftest.py` and available to all tests.

### Core Fixtures

#### `test_config` (autouse)

Automatically applied to all tests. Sets consistent decay parameters and disables embeddings by default.

```python
# No need to request this fixture - it's automatic
def test_something():
    # test_config is already active
    pass
```

#### `temp_storage`

Creates isolated temporary JSONL storage for each test. Automatically patches global `db` instances across 11 tool modules.

```python
def test_save_memory(temp_storage):
    mem = Memory(id="test-123", content="Test")
    temp_storage.save_memory(mem)

    result = temp_storage.get_memory("test-123")
    assert result.content == "Test"
```

### Config Mock Fixtures

#### `mock_config_preprocessor`

Config with `enable_preprocessing=False` for testing legacy behavior without auto-enrichment.

```python
def test_basic_save(mock_config_preprocessor, temp_storage):
    # Preprocessing disabled - entities won't be auto-extracted
    result = save_memory(content="Test about Claude")
    memory = temp_storage.get_memory(result["memory_id"])
    assert memory.entities == []  # Not auto-extracted
```

#### `mock_config_embeddings`

Config with `enable_embeddings=True` and test model configured.

```python
def test_semantic_search(mock_config_embeddings, temp_storage):
    result = search_memory(query="AI", use_embeddings=True)
    # Will use semantic similarity with embeddings
```

### Embedding Mock Fixtures

#### `mock_embeddings_save`

Mocks `SentenceTransformer` for the save module. Use with `mock_config_embeddings`.

```python
def test_save_with_embeddings(
    mock_config_embeddings,
    mock_embeddings_save,
    temp_storage
):
    result = save_memory(content="Test")
    assert result["has_embedding"] is True

    memory = temp_storage.get_memory(result["memory_id"])
    assert memory.embed == [0.1, 0.2, 0.3]  # Predictable test embeddings
```

#### `mock_embeddings_search`

Mocks `SentenceTransformer` for the search module. Use with `mock_config_embeddings`.

```python
def test_search_with_embeddings(
    mock_config_embeddings,
    mock_embeddings_search,
    temp_storage
):
    result = search_memory(query="test", use_embeddings=True)
    # Similarity scoring uses mocked embeddings
```

### Utility Functions

#### `make_test_uuid(name: str) -> str`

Generates deterministic UUIDs for reproducible tests.

```python
from tests.conftest import make_test_uuid

id1 = make_test_uuid("test-memory-1")
# Always returns same UUID for "test-memory-1"
```

## Writing New Tests

### Tool Tests

Test MCP tool endpoints by calling them directly with the shared `temp_storage` fixture.

```python
class TestMyTool:
    """Test suite for my_tool."""

    def test_basic_functionality(self, temp_storage):
        """Test basic operation."""
        result = my_tool(param="value")

        assert result["success"] is True
        assert "data" in result

        # Verify side effects
        memory = temp_storage.get_memory(result["memory_id"])
        assert memory.content == "expected"
```

### Validation Tests

Test input validation with `pytest.raises`.

```python
def test_invalid_param_fails(self):
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError, match="param.*invalid"):
        my_tool(param="bad value")
```

### Config-Dependent Tests

Use shared config fixtures instead of module-specific patches.

```python
# ❌ DON'T: Module-specific patch (brittle)
@patch("cortexgraph.tools.save.get_config")
def test_foo(self, mock_config, temp_storage):
    config = get_config()
    config.enable_preprocessing = False
    mock_config.return_value = config
    ...

# ✅ DO: Use shared fixture (resilient)
def test_foo(self, mock_config_preprocessor, temp_storage):
    # Fixture handles everything
    result = save_memory(content="Test")
    ...
```

### Embedding Tests

Use shared embedding fixtures instead of manual mock setup.

```python
# ❌ DON'T: Manual mock setup (duplicated)
@patch("cortexgraph.tools.save.SENTENCE_TRANSFORMERS_AVAILABLE", True)
@patch("cortexgraph.tools.save._SentenceTransformer")
def test_foo(self, mock_transformer, ...):
    mock_model = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
    # ... 7 more lines of setup

# ✅ DO: Use shared fixtures (clean)
def test_foo(self, mock_config_embeddings, mock_embeddings_save, temp_storage):
    # Fixtures handle everything
    result = save_memory(content="Test")
    assert result["has_embedding"] is True
```

## Common Pitfalls

### ❌ Module-Specific Config Patches

**DON'T** use module-specific `@patch` decorators for config:

```python
# BRITTLE - breaks when imports move
@patch("cortexgraph.tools.save.get_config")
@patch("cortexgraph.tools.search.get_config")
```

**DO** use shared global config fixtures:

```python
# RESILIENT - immune to refactoring
def test_foo(self, mock_config_preprocessor, temp_storage):
    ...
```

**Why?** Module-specific patches couple tests to import structure. When you move imports or add new config fields, these tests break. Global fixtures patch at the config module level, making tests immune to refactoring.

### ❌ Local Fixture Definitions

**DON'T** redefine shared fixtures locally:

```python
# SHADOWS conftest.py fixture!
@pytest.fixture
def temp_storage():
    # Different behavior than conftest version
    ...
```

**DO** use the shared fixture from conftest.py:

```python
def test_foo(temp_storage):  # Uses conftest version
    ...
```

**Why?** Local fixture definitions shadow the canonical ones, causing inconsistent behavior and hard-to-debug issues.

### ❌ Hardcoded Test Data

**DON'T** use hardcoded UUIDs or timestamps:

```python
mem = Memory(
    id="abc-123",  # Not a valid UUID format
    created_at=1234567890,  # Hardcoded timestamp
)
```

**DO** use utilities for reproducible test data:

```python
from tests.conftest import make_test_uuid
import time

mem = Memory(
    id=make_test_uuid("test-memory-1"),  # Deterministic UUID
    created_at=int(time.time()),  # Current time
)
```

### ❌ Testing Implementation Details

**DON'T** test internal implementation details:

```python
# Tests know too much about internals
def test_foo():
    assert memory._internal_cache == {}
    assert memory._update_timestamp()
```

**DO** test observable behavior:

```python
# Tests verify behavior, not implementation
def test_foo():
    result = save_memory(content="Test")
    assert result["success"] is True

    memory = temp_storage.get_memory(result["memory_id"])
    assert memory.content == "Test"
```

**Why?** Testing implementation details makes tests brittle. When you refactor internals, tests break even though behavior is unchanged.

## Test Patterns

### Validation Tests

Use descriptive test names and clear error matching:

```python
def test_save_empty_content_fails(self):
    """Test that empty content raises ValueError."""
    with pytest.raises(ValueError, match="content.*empty"):
        save_memory(content="")

def test_save_content_too_long_fails(self):
    """Test that content exceeding max length fails."""
    long_content = "x" * 50001
    with pytest.raises(ValueError, match="content.*exceeds maximum"):
        save_memory(content=long_content)
```

### State Verification Tests

Create memory, perform operation, verify state change:

```python
def test_touch_memory_updates_timestamp(self, temp_storage):
    """Test that touching a memory updates last_used."""
    # Setup
    mem = Memory(id="test-123", content="Test", last_used=0)
    temp_storage.save_memory(mem)

    # Action
    result = touch_memory(memory_id="test-123")

    # Verification
    assert result["success"] is True
    updated = temp_storage.get_memory("test-123")
    assert updated.last_used > 0
```

### Decay/Scoring Tests

Use time manipulation for reproducible temporal behavior:

```python
def test_memory_decays_over_time(self, temp_storage):
    """Test that memory score decreases over time."""
    now = int(time.time())
    old_time = now - (7 * 86400)  # 7 days ago

    mem = Memory(
        id="test-123",
        content="Test",
        use_count=1,
        last_used=old_time,
        created_at=old_time,
    )
    temp_storage.save_memory(mem)

    # Calculate score
    from cortexgraph.core.decay import calculate_score
    score = calculate_score(
        use_count=mem.use_count,
        last_used=mem.last_used,
        strength=mem.strength,
        now=now,
    )

    # Should have decayed significantly
    assert score < 0.5
```

## Test Coverage

Current coverage: **99%+**

To generate coverage report:

```bash
pytest --cov=cortexgraph --cov-report=html
open htmlcov/index.html
```

### Coverage Goals

- **Core modules**: 100% (decay.py, scoring.py, storage)
- **Tools**: 95%+ (MCP endpoints)
- **Security**: 100% (validators, permissions)
- **Utilities**: 90%+ (helpers, formatters)

## Debugging Tests

### Run Single Test with Output

```bash
pytest tests/test_tools_memory_management.py::TestSaveMemory::test_save_basic_memory -v -s
```

### Debug with pdb

```python
def test_something(temp_storage):
    import pdb; pdb.set_trace()  # Add breakpoint
    result = save_memory(content="Test")
```

### Print Fixture Values

```python
def test_something(temp_storage, mock_config_preprocessor):
    print(f"Storage path: {temp_storage.storage_path}")
    print(f"Config: {mock_config_preprocessor}")
    ...
```

## Contributing

When adding new tests:

1. **Use shared fixtures** - Don't duplicate config/embedding setup
2. **Test behavior, not implementation** - Focus on observable effects
3. **Write descriptive test names** - `test_save_empty_content_fails` not `test_error_1`
4. **Include docstrings** - Explain what behavior is being verified
5. **Follow existing patterns** - Match the style of similar tests
6. **Run full suite** - Ensure your changes don't break other tests

## Getting Help

- **Fixture questions**: See `conftest.py` docstrings
- **Pattern questions**: Search for similar tests in the same file
- **Brittleness issues**: Review "Common Pitfalls" section above
- **New patterns**: Discuss in PR review before adding

---

**Last Updated**: November 18, 2025 (v0.7.0 - Test suite consolidation and brittleness fixes)
