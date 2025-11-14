"""Performance monitoring and metrics for CortexGraph."""

import time
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class PerformanceMetrics:
    """Collects and tracks performance metrics."""

    def __init__(self) -> None:
        self.metrics: dict[str, list[float]] = defaultdict(list)
        self.counters: dict[str, int] = defaultdict(int)
        self.timers: dict[str, float] = {}

    def record_timing(self, operation: str, duration: float) -> None:
        """Record timing for an operation."""
        self.metrics[operation].append(duration)
        # Keep only last 1000 measurements to prevent memory growth
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]

    def increment_counter(self, operation: str) -> None:
        """Increment counter for an operation."""
        self.counters[operation] += 1

    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        self.timers[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation not in self.timers:
            return 0.0

        duration = time.time() - self.timers[operation]
        self.record_timing(operation, duration)
        del self.timers[operation]
        return duration

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        stats: dict[str, Any] = {}

        for operation, timings in self.metrics.items():
            if timings:
                stats[operation] = {
                    "count": len(timings),
                    "avg_ms": sum(timings) * 1000 / len(timings),
                    "min_ms": min(timings) * 1000,
                    "max_ms": max(timings) * 1000,
                    "total_ms": sum(timings) * 1000,
                }

        for operation, count in self.counters.items():
            stats[f"{operation}_count"] = int(count)

        return stats

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.counters.clear()
        self.timers.clear()


# Global metrics instance
_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Get the global metrics instance."""
    return _metrics


def time_operation(operation_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to time function execution."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            metrics = get_metrics()
            metrics.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                metrics.end_timer(operation_name)
                metrics.increment_counter(operation_name)

        return wrapper

    return decorator


def record_timing(operation: str, duration: float) -> None:
    """Record timing for an operation."""
    get_metrics().record_timing(operation, duration)


def increment_counter(operation: str) -> None:
    """Increment counter for an operation."""
    get_metrics().increment_counter(operation)


def get_performance_stats() -> dict[str, Any]:
    """Get current performance statistics."""
    return get_metrics().get_stats()


def reset_metrics() -> None:
    """Reset all performance metrics."""
    get_metrics().reset()
