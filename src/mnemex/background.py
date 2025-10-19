"""Background task management for expensive operations."""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for expensive operations."""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks: dict[str, Any] = {}
        self.task_results: dict[str, Any] = {}
        self.task_errors: dict[str, Exception] = {}

    def submit_task(
        self, task_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """Submit a background task."""
        if task_id in self.running_tasks:
            logger.warning(f"Task {task_id} is already running")
            return

        future = self.executor.submit(self._run_task, task_id, func, *args, **kwargs)
        self.running_tasks[task_id] = future
        logger.info(f"Submitted background task: {task_id}")

    def _run_task(self, task_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Run a task and store results."""
        try:
            logger.info(f"Starting background task: {task_id}")
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            self.task_results[task_id] = {
                "result": result,
                "duration": duration,
                "completed_at": time.time(),
            }
            logger.info(f"Completed background task: {task_id} in {duration:.2f}s")

        except Exception as e:
            self.task_errors[task_id] = e
            logger.error(f"Background task {task_id} failed: {e}")
        finally:
            self.running_tasks.pop(task_id, None)

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get status of a background task."""
        if task_id in self.running_tasks:
            return {"status": "running", "task_id": task_id}
        elif task_id in self.task_results:
            return {"status": "completed", "task_id": task_id, **self.task_results[task_id]}
        elif task_id in self.task_errors:
            return {"status": "failed", "task_id": task_id, "error": str(self.task_errors[task_id])}
        else:
            return {"status": "not_found", "task_id": task_id}

    def get_task_result(self, task_id: str) -> Any:
        """Get result of a completed task."""
        if task_id in self.task_results:
            return self.task_results[task_id]["result"]
        return None

    def cleanup_old_results(self, max_age_hours: int = 24) -> int:
        """Clean up old task results."""
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned = 0

        for task_id in list(self.task_results.keys()):
            if self.task_results[task_id]["completed_at"] < cutoff_time:
                del self.task_results[task_id]
                cleaned += 1

        for task_id in list(self.task_errors.keys()):
            # Keep errors for shorter time
            if time.time() - 3600 > cutoff_time:  # 1 hour for errors
                del self.task_errors[task_id]
                cleaned += 1

        return cleaned

    def shutdown(self) -> None:
        """Shutdown the task manager."""
        self.executor.shutdown(wait=True)
        logger.info("Background task manager shutdown")


# Global task manager instance
_task_manager: BackgroundTaskManager | None = None


def get_task_manager() -> BackgroundTaskManager:
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager


def submit_background_task(
    task_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> None:
    """Submit a background task."""
    get_task_manager().submit_task(task_id, func, *args, **kwargs)


def get_task_status(task_id: str) -> dict[str, Any]:
    """Get status of a background task."""
    return get_task_manager().get_task_status(task_id)


def get_task_result(task_id: str) -> Any:
    """Get result of a completed task."""
    return get_task_manager().get_task_result(task_id)
