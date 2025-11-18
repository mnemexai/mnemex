"""Pytest configuration and shared fixtures."""

import tempfile
import uuid
from pathlib import Path

import pytest

import cortexgraph.context
import cortexgraph.tools.auto_recall_tool
import cortexgraph.tools.cluster
import cortexgraph.tools.consolidate
import cortexgraph.tools.create_relation
import cortexgraph.tools.gc
import cortexgraph.tools.open_memories
import cortexgraph.tools.promote
import cortexgraph.tools.read_graph
import cortexgraph.tools.save
import cortexgraph.tools.search
import cortexgraph.tools.touch
from cortexgraph.config import Config, set_config
from cortexgraph.storage.jsonl_storage import JSONLStorage


def make_test_uuid(name: str) -> str:
    """Generate a deterministic UUID for testing based on a name.

    Args:
        name: A short descriptive name (e.g., 'test-123', 'mem-promoted')

    Returns:
        A valid UUID string generated deterministically from the name

    Examples:
        >>> make_test_uuid("test-123")
        'a1b2c3d4-...'  # Always returns the same UUID for "test-123"
    """
    # Use UUID5 with a fixed namespace to generate deterministic UUIDs
    namespace = uuid.UUID("12345678-1234-5678-1234-567812345678")
    return str(uuid.uuid5(namespace, name))


@pytest.fixture(autouse=True)
def test_config():
    """Set up a test configuration for all tests."""
    config = Config(
        decay_lambda=2.673e-6,
        decay_beta=0.6,
        forget_threshold=0.05,
        promote_threshold=0.65,
        enable_embeddings=False,  # Disable embeddings in tests
    )
    set_config(config)
    yield config


@pytest.fixture
def temp_storage(monkeypatch):
    """Create a temporary JSONL storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir)
        storage = JSONLStorage(storage_path=storage_dir)
        storage.connect()

        # Monkey-patch the global db instance in context and all tool modules

        modules_to_patch = [
            cortexgraph.context,
            cortexgraph.tools.save,
            cortexgraph.tools.search,
            cortexgraph.tools.touch,
            cortexgraph.tools.gc,
            cortexgraph.tools.promote,
            cortexgraph.tools.cluster,
            cortexgraph.tools.consolidate,
            cortexgraph.tools.create_relation,
            cortexgraph.tools.open_memories,
            cortexgraph.tools.read_graph,
            cortexgraph.tools.auto_recall_tool,
        ]
        for module in modules_to_patch:
            monkeypatch.setattr(module, "db", storage)

        yield storage
        storage.close()


@pytest.fixture
def mock_config_preprocessor(monkeypatch):
    """Mock config with preprocessing disabled.

    Use this fixture for tests that need legacy behavior without auto-enrichment
    of entities and strength. This is useful for testing basic memory operations
    without the natural language preprocessing layer.

    Example:
        def test_basic_save(mock_config_preprocessor, temp_storage):
            result = save_memory(content="Test")
            # Entities will be empty (not auto-extracted)
    """
    from cortexgraph.config import get_config

    config = get_config()
    config.enable_preprocessing = False
    # Patch at global level to avoid module-specific coupling
    import cortexgraph.config

    monkeypatch.setattr(cortexgraph.config, "_global_config", config)
    return config


@pytest.fixture
def mock_config_embeddings(monkeypatch):
    """Mock config with embeddings enabled.

    Use this fixture for tests that need semantic search with embeddings.
    Configures a test model and ensures all embedding-related config fields
    are set appropriately.

    Example:
        def test_semantic_search(mock_config_embeddings, temp_storage):
            result = search_memory(query="AI", use_embeddings=True)
            # Will use mocked embeddings for similarity scoring
    """
    from cortexgraph.config import get_config

    config = get_config()
    config.enable_embeddings = True
    config.embed_model = "test-model"
    config.search_default_preview_length = 300
    # Patch at global level to avoid module-specific coupling
    import cortexgraph.config

    monkeypatch.setattr(cortexgraph.config, "_global_config", config)
    return config
