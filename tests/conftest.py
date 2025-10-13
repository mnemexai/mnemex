"""Pytest configuration and shared fixtures."""

import tempfile
import uuid
from pathlib import Path

import pytest

from mnemex.config import Config, set_config
from mnemex.storage.jsonl_storage import JSONLStorage


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
        import mnemex.context
        import mnemex.tools.gc
        import mnemex.tools.promote
        import mnemex.tools.save
        import mnemex.tools.search
        import mnemex.tools.touch

        modules_to_patch = [
            mnemex.context,
            mnemex.tools.save,
            mnemex.tools.search,
            mnemex.tools.touch,
            mnemex.tools.gc,
            mnemex.tools.promote,
        ]
        for module in modules_to_patch:
            monkeypatch.setattr(module, "db", storage)

        yield storage
        storage.close()
