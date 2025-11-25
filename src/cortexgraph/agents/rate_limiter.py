"""Rate limiting for consolidation agents.

Implements a token bucket algorithm to prevent agent operations from
overwhelming the system. Each agent has its own rate limiter.

Design Decision (from research.md):
    Token bucket is simple, well-understood, and allows bursting while
    maintaining overall rate limits. Per-agent limits allow parallelism
    while preventing storms.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for consolidation agents.

    Implements a sliding window rate limiter that allows up to `max_ops`
    operations within any `window_seconds` period.

    Attributes:
        max_ops: Maximum operations allowed per window
        window: Window size in seconds
        remaining: Current number of tokens available

    Example:
        >>> limiter = RateLimiter(max_ops=100, window_seconds=60)
        >>> if limiter.acquire():
        ...     # Perform operation
        ...     pass
        >>> # Or block until ready:
        >>> limiter.wait_and_acquire()
    """

    def __init__(self, max_ops: int = 100, window_seconds: int = 60) -> None:
        """Initialize rate limiter.

        Args:
            max_ops: Maximum operations per window (default: 100)
            window_seconds: Window size in seconds (default: 60)

        Raises:
            ValueError: If max_ops < 1 or window_seconds < 1
        """
        if max_ops < 1:
            raise ValueError("max_ops must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")

        self.max_ops = max_ops
        self.window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = Lock()

    @property
    def remaining(self) -> int:
        """Number of tokens remaining in current window."""
        with self._lock:
            self._cleanup()
            return self.max_ops - len(self._timestamps)

    def _cleanup(self) -> None:
        """Remove expired timestamps from the window."""
        now = time.time()
        cutoff = now - self.window
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def acquire(self) -> bool:
        """Try to acquire a token.

        Returns:
            True if token acquired, False if rate limit exceeded

        Thread-safe: Can be called from multiple threads.
        """
        with self._lock:
            self._cleanup()

            if len(self._timestamps) < self.max_ops:
                self._timestamps.append(time.time())
                logger.debug(
                    f"Rate limiter: acquired token ({self.max_ops - len(self._timestamps)} remaining)"
                )
                return True

            logger.debug(f"Rate limiter: limit exceeded ({self.max_ops} ops/{self.window}s)")
            return False

    def wait_and_acquire(self, timeout: float | None = None) -> bool:
        """Block until a token is available.

        Args:
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            True if token acquired, False if timeout reached

        Thread-safe: Can be called from multiple threads.
        """
        start_time = time.time()
        poll_interval = 0.1  # 100ms between checks

        while True:
            if self.acquire():
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.debug(f"Rate limiter: timeout after {elapsed:.2f}s")
                    return False

            time.sleep(poll_interval)

    def reset(self) -> None:
        """Reset the rate limiter, clearing all timestamps.

        Useful for testing or administrative purposes.
        """
        with self._lock:
            self._timestamps.clear()
            logger.debug("Rate limiter: reset")

    def time_until_available(self) -> float:
        """Calculate seconds until next token is available.

        Returns:
            Seconds to wait (0 if token available now)
        """
        with self._lock:
            self._cleanup()

            if len(self._timestamps) < self.max_ops:
                return 0.0

            # Oldest timestamp will expire first
            oldest = self._timestamps[0]
            wait_time = (oldest + self.window) - time.time()
            return max(0.0, wait_time)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"RateLimiter(max_ops={self.max_ops}, window={self.window}s, remaining={self.remaining})"


class AgentRateLimiters:
    """Manager for per-agent rate limiters.

    Provides centralized access to rate limiters for each agent type,
    ensuring consistent rate limiting across the consolidation system.

    Example:
        >>> limiters = AgentRateLimiters(default_ops=100)
        >>> if limiters.get("decay").acquire():
        ...     # Run decay analyzer
        ...     pass
    """

    def __init__(
        self,
        default_ops: int = 100,
        default_window: int = 60,
        per_agent_limits: dict[str, int] | None = None,
    ) -> None:
        """Initialize agent rate limiters.

        Args:
            default_ops: Default max operations per minute
            default_window: Default window in seconds
            per_agent_limits: Optional per-agent operation limits
        """
        self._default_ops = default_ops
        self._default_window = default_window
        self._per_agent_limits = per_agent_limits or {}
        self._limiters: dict[str, RateLimiter] = {}
        self._lock = Lock()

    def get(self, agent: str) -> RateLimiter:
        """Get or create rate limiter for an agent.

        Args:
            agent: Agent name (decay, cluster, merge, promote, relations)

        Returns:
            RateLimiter instance for the agent
        """
        with self._lock:
            if agent not in self._limiters:
                max_ops = self._per_agent_limits.get(agent, self._default_ops)
                self._limiters[agent] = RateLimiter(
                    max_ops=max_ops,
                    window_seconds=self._default_window,
                )
                logger.debug(
                    f"Created rate limiter for {agent}: {max_ops} ops/{self._default_window}s"
                )

            return self._limiters[agent]

    def status(self) -> dict[str, dict[str, int | float]]:
        """Get status of all active rate limiters.

        Returns:
            Dict mapping agent name to status (remaining, max_ops, wait_time)
        """
        with self._lock:
            return {
                agent: {
                    "remaining": limiter.remaining,
                    "max_ops": limiter.max_ops,
                    "wait_time": limiter.time_until_available(),
                }
                for agent, limiter in self._limiters.items()
            }

    def reset_all(self) -> None:
        """Reset all rate limiters."""
        with self._lock:
            for limiter in self._limiters.values():
                limiter.reset()
            logger.info("Reset all agent rate limiters")
