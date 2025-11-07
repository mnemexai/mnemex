"""Test for ltm_index_max_age_seconds configuration."""

from cortexgraph.config import Config


def test_ltm_index_max_age_from_env(monkeypatch):
    """Test that CORTEXGRAPH_LTM_INDEX_MAX_AGE_SECONDS can be loaded from environment."""
    # Set environment variable
    monkeypatch.setenv("CORTEXGRAPH_LTM_INDEX_MAX_AGE_SECONDS", "7200")

    # Load config from environment
    config = Config.from_env()

    # Verify it was loaded correctly
    assert config.ltm_index_max_age_seconds == 7200

    # Clean up environment variable
    monkeypatch.delenv("CORTEXGRAPH_LTM_INDEX_MAX_AGE_SECONDS", raising=False)


def test_ltm_index_max_age_default(monkeypatch):
    """Test that ltm_index_max_age_seconds has correct default value."""
    # Ensure env var is not set
    monkeypatch.delenv("CORTEXGRAPH_LTM_INDEX_MAX_AGE_SECONDS", raising=False)

    config = Config()
    assert config.ltm_index_max_age_seconds == 3600  # 1 hour default
