"""Unit tests for cron-like scheduled execution (T089).

Tests for the scheduler's ability to:
1. Accept schedule interval configuration
2. Check if enough time has passed since last run
3. Track last run time
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


class TestSchedulerInterval:
    """Tests for schedule interval configuration."""

    def test_scheduler_default_interval(self) -> None:
        """Scheduler has default interval of 1 hour."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()
        assert scheduler.interval_seconds == 3600  # 1 hour

    def test_scheduler_custom_interval(self) -> None:
        """Scheduler accepts custom interval in seconds."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(interval_seconds=1800)  # 30 minutes
        assert scheduler.interval_seconds == 1800

    def test_scheduler_interval_from_hours(self) -> None:
        """Scheduler can be configured with hours."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(interval_hours=2)
        assert scheduler.interval_seconds == 7200  # 2 hours


class TestSchedulerShouldRun:
    """Tests for determining if scheduled run should execute."""

    def test_should_run_no_last_run(self) -> None:
        """should_run returns True if never run before."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()

        with patch.object(scheduler, "_get_last_run_time", return_value=None):
            assert scheduler.should_run() is True

    def test_should_run_interval_elapsed(self) -> None:
        """should_run returns True if interval has elapsed."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(interval_seconds=3600)  # 1 hour
        last_run = int(time.time()) - 4000  # ~1.1 hours ago

        with patch.object(scheduler, "_get_last_run_time", return_value=last_run):
            assert scheduler.should_run() is True

    def test_should_run_interval_not_elapsed(self) -> None:
        """should_run returns False if interval has not elapsed."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(interval_seconds=3600)  # 1 hour
        last_run = int(time.time()) - 1800  # 30 minutes ago

        with patch.object(scheduler, "_get_last_run_time", return_value=last_run):
            assert scheduler.should_run() is False

    def test_should_run_force_override(self) -> None:
        """should_run returns True with force=True even if interval not elapsed."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(interval_seconds=3600)
        last_run = int(time.time()) - 1800  # 30 minutes ago

        with patch.object(scheduler, "_get_last_run_time", return_value=last_run):
            assert scheduler.should_run(force=True) is True


class TestSchedulerLastRunTracking:
    """Tests for tracking last run time."""

    def test_record_run_updates_timestamp(self) -> None:
        """record_run stores current timestamp."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()
        before = int(time.time())

        with patch.object(scheduler, "_save_last_run_time") as mock_save:
            scheduler.record_run()
            mock_save.assert_called_once()
            saved_time = mock_save.call_args[0][0]
            assert before <= saved_time <= int(time.time()) + 1

    def test_get_last_run_time_returns_stored_value(self) -> None:
        """_get_last_run_time retrieves stored timestamp."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()

        with patch("cortexgraph.config.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.storage_path = "/tmp/test"
            mock_config.return_value = mock_cfg

            # When file doesn't exist, should return None
            with patch("pathlib.Path.exists", return_value=False):
                result = scheduler._get_last_run_time()
                assert result is None


class TestSchedulerRunScheduled:
    """Tests for scheduled pipeline execution."""

    def test_run_scheduled_skips_if_not_due(self) -> None:
        """run_scheduled skips execution if interval not elapsed."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler()

        with (
            patch.object(scheduler, "should_run", return_value=False),
            patch.object(scheduler, "run_pipeline") as mock_run,
        ):
            result = scheduler.run_scheduled()

            mock_run.assert_not_called()
            assert result["skipped"] is True
            assert "not due" in result["reason"].lower()

    def test_run_scheduled_executes_if_due(self) -> None:
        """run_scheduled executes pipeline if interval elapsed."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with (
            patch.object(scheduler, "should_run", return_value=True),
            patch.object(scheduler, "run_pipeline", return_value={"decay": []}) as mock_run,
            patch.object(scheduler, "record_run") as mock_record,
        ):
            result = scheduler.run_scheduled()

            mock_run.assert_called_once()
            mock_record.assert_called_once()
            assert result["skipped"] is False
            assert "decay" in result["results"]

    def test_run_scheduled_force_ignores_interval(self) -> None:
        """run_scheduled with force=True ignores interval check."""
        from cortexgraph.agents.scheduler import Scheduler

        scheduler = Scheduler(dry_run=True)

        with (
            patch.object(scheduler, "should_run", return_value=False),
            patch.object(scheduler, "run_pipeline", return_value={"decay": []}) as mock_run,
            patch.object(scheduler, "record_run"),
        ):
            result = scheduler.run_scheduled(force=True)

            mock_run.assert_called_once()
            assert result["skipped"] is False


class TestSchedulerConstants:
    """Tests for scheduler constants."""

    def test_default_interval_constant(self) -> None:
        """DEFAULT_INTERVAL_SECONDS is 1 hour."""
        from cortexgraph.agents.scheduler import DEFAULT_INTERVAL_SECONDS

        assert DEFAULT_INTERVAL_SECONDS == 3600
