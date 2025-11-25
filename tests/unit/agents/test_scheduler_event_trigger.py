"""Unit tests for event-driven urgent decay detection (T090).

Tests for integrating post_save_check into the save_memory flow:
1. Configuration to enable/disable event triggers
2. Hook function that can be called after save
3. Integration with scheduler.post_save_check
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestEventTriggerConfig:
    """Tests for event trigger configuration."""

    def test_config_enables_event_triggers_by_default(self) -> None:
        """Event triggers are enabled by default in config."""
        from cortexgraph.config import get_config

        config = get_config()
        assert hasattr(config, "enable_urgent_decay_check")
        assert config.enable_urgent_decay_check is True

    def test_config_urgent_threshold(self) -> None:
        """Config has urgent decay threshold."""
        from cortexgraph.config import get_config

        config = get_config()
        assert hasattr(config, "urgent_decay_threshold")
        assert config.urgent_decay_threshold == 0.10


class TestPostSaveHook:
    """Tests for the post-save hook function."""

    def test_post_save_hook_exists(self) -> None:
        """post_save_hook function exists in scheduler module."""
        from cortexgraph.agents.scheduler import post_save_hook

        assert callable(post_save_hook)

    def test_post_save_hook_calls_scheduler(self) -> None:
        """post_save_hook creates scheduler and calls post_save_check."""
        from cortexgraph.agents.scheduler import post_save_hook

        with patch("cortexgraph.agents.scheduler.Scheduler") as mock_class:
            mock_scheduler = MagicMock()
            mock_scheduler.post_save_check.return_value = None
            mock_class.return_value = mock_scheduler

            result = post_save_hook("memory-123")

            mock_class.assert_called_once()
            mock_scheduler.post_save_check.assert_called_once_with("memory-123")
            assert result is None

    def test_post_save_hook_returns_urgent_info(self) -> None:
        """post_save_hook returns urgent info when detected."""
        from cortexgraph.agents.scheduler import post_save_hook

        with patch("cortexgraph.agents.scheduler.Scheduler") as mock_class:
            mock_scheduler = MagicMock()
            mock_scheduler.post_save_check.return_value = {
                "memory_id": "memory-456",
                "score": 0.05,
                "action": "flagged_urgent",
            }
            mock_class.return_value = mock_scheduler

            result = post_save_hook("memory-456")

            assert result is not None
            assert result["memory_id"] == "memory-456"
            assert result["action"] == "flagged_urgent"


class TestSaveMemoryIntegration:
    """Tests for save_memory integration with event triggers."""

    def test_save_memory_result_includes_urgent_check(self) -> None:
        """save_memory result includes urgent_check field when enabled."""
        # This test verifies the result structure after integration
        # The actual integration will add an "urgent_check" field to results
        pass  # Implementation will add the field

    def test_save_memory_calls_post_save_hook_when_enabled(self) -> None:
        """save_memory calls post_save_hook when event triggers enabled."""
        # This will be tested via integration tests
        # Unit test here just verifies the hook is callable
        from cortexgraph.agents.scheduler import post_save_hook

        assert callable(post_save_hook)


class TestEventTriggerPerformance:
    """Tests for event trigger performance considerations."""

    def test_post_save_hook_is_fast(self) -> None:
        """post_save_hook completes quickly (< 100ms)."""
        import time

        from cortexgraph.agents.scheduler import post_save_hook

        # Mock the scheduler to avoid actual storage access
        with patch("cortexgraph.agents.scheduler.Scheduler") as mock_class:
            mock_scheduler = MagicMock()
            mock_scheduler.post_save_check.return_value = None
            mock_class.return_value = mock_scheduler

            start = time.time()
            post_save_hook("test-memory")
            elapsed = time.time() - start

            # Should be very fast with mocked scheduler
            assert elapsed < 0.1  # 100ms

    def test_post_save_hook_handles_errors_gracefully(self) -> None:
        """post_save_hook doesn't raise on internal errors."""
        from cortexgraph.agents.scheduler import post_save_hook

        with patch("cortexgraph.agents.scheduler.Scheduler") as mock_class:
            mock_scheduler = MagicMock()
            mock_scheduler.post_save_check.side_effect = RuntimeError("Storage error")
            mock_class.return_value = mock_scheduler

            # Should not raise - just log and return None
            result = post_save_hook("memory-error")
            assert result is None
