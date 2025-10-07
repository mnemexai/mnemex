"""Pytest configuration and shared fixtures."""

import pytest

from stm_server.config import Config, set_config


@pytest.fixture(autouse=True)
def test_config():
    """Set up a test configuration for all tests."""
    config = Config(
        db_path=":memory:",  # Use in-memory database for tests
        decay_lambda=2.673e-6,
        decay_beta=0.6,
        forget_threshold=0.05,
        promote_threshold=0.65,
        enable_embeddings=False,  # Disable embeddings in tests
    )
    set_config(config)
    yield config
