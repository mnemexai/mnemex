"""Unit tests for rate limiter (T022).

Tests the token bucket rate limiting implementation.
"""

from __future__ import annotations

import time

import pytest

from cortexgraph.agents.rate_limiter import AgentRateLimiters, RateLimiter

# =============================================================================
# RateLimiter Tests
# =============================================================================


class TestRateLimiterInitialization:
    """Tests for RateLimiter initialization."""

    def test_default_values(self) -> None:
        """Test default initialization values."""
        limiter = RateLimiter()
        assert limiter.max_ops == 100
        assert limiter.window == 60

    def test_custom_values(self) -> None:
        """Test custom initialization values."""
        limiter = RateLimiter(max_ops=50, window_seconds=30)
        assert limiter.max_ops == 50
        assert limiter.window == 30

    def test_invalid_max_ops(self) -> None:
        """Test invalid max_ops raises ValueError."""
        with pytest.raises(ValueError, match="max_ops must be >= 1"):
            RateLimiter(max_ops=0)

        with pytest.raises(ValueError, match="max_ops must be >= 1"):
            RateLimiter(max_ops=-1)

    def test_invalid_window(self) -> None:
        """Test invalid window raises ValueError."""
        with pytest.raises(ValueError, match="window_seconds must be >= 1"):
            RateLimiter(window_seconds=0)


class TestRateLimiterAcquire:
    """Tests for RateLimiter.acquire method."""

    def test_acquire_success(self) -> None:
        """Test successful token acquisition."""
        limiter = RateLimiter(max_ops=5, window_seconds=60)

        # Should be able to acquire 5 tokens
        for _ in range(5):
            assert limiter.acquire() is True

        # 6th should fail
        assert limiter.acquire() is False

    def test_remaining_property(self) -> None:
        """Test remaining tokens property."""
        limiter = RateLimiter(max_ops=5, window_seconds=60)

        assert limiter.remaining == 5
        limiter.acquire()
        assert limiter.remaining == 4
        limiter.acquire()
        assert limiter.remaining == 3

    def test_tokens_expire(self) -> None:
        """Test tokens expire after window."""
        limiter = RateLimiter(max_ops=2, window_seconds=1)

        # Use both tokens
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire() is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be able to acquire again
        assert limiter.acquire() is True


class TestRateLimiterWaitAndAcquire:
    """Tests for RateLimiter.wait_and_acquire method."""

    def test_immediate_acquire(self) -> None:
        """Test immediate acquire when tokens available."""
        limiter = RateLimiter(max_ops=5, window_seconds=60)

        start = time.time()
        result = limiter.wait_and_acquire(timeout=1.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.2  # Should be immediate

    def test_wait_for_token(self) -> None:
        """Test waiting for token when limit exceeded."""
        limiter = RateLimiter(max_ops=1, window_seconds=1)

        # Use the one token
        limiter.acquire()

        # Should wait and then acquire
        start = time.time()
        result = limiter.wait_and_acquire(timeout=2.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.9  # Should have waited ~1 second

    def test_timeout(self) -> None:
        """Test timeout when cannot acquire."""
        limiter = RateLimiter(max_ops=1, window_seconds=10)
        limiter.acquire()

        start = time.time()
        result = limiter.wait_and_acquire(timeout=0.5)
        elapsed = time.time() - start

        assert result is False
        assert elapsed >= 0.4  # Should have waited ~0.5 seconds


class TestRateLimiterUtilities:
    """Tests for RateLimiter utility methods."""

    def test_reset(self) -> None:
        """Test reset clears all timestamps."""
        limiter = RateLimiter(max_ops=5, window_seconds=60)

        # Use some tokens
        limiter.acquire()
        limiter.acquire()
        assert limiter.remaining == 3

        # Reset
        limiter.reset()
        assert limiter.remaining == 5

    def test_time_until_available(self) -> None:
        """Test time_until_available calculation."""
        limiter = RateLimiter(max_ops=1, window_seconds=60)

        # When tokens available
        assert limiter.time_until_available() == 0.0

        # When limit exceeded
        limiter.acquire()
        wait_time = limiter.time_until_available()
        assert 59.0 <= wait_time <= 60.0

    def test_repr(self) -> None:
        """Test string representation."""
        limiter = RateLimiter(max_ops=100, window_seconds=60)
        repr_str = repr(limiter)

        assert "RateLimiter" in repr_str
        assert "max_ops=100" in repr_str
        assert "window=60s" in repr_str


class TestRateLimiterThreadSafety:
    """Tests for thread safety of RateLimiter."""

    def test_concurrent_acquire(self) -> None:
        """Test concurrent acquire is thread-safe."""
        import threading

        limiter = RateLimiter(max_ops=100, window_seconds=60)
        acquired_count = 0
        lock = threading.Lock()

        def acquire_tokens(n: int) -> None:
            nonlocal acquired_count
            for _ in range(n):
                if limiter.acquire():
                    with lock:
                        acquired_count += 1

        # Start 10 threads each trying to acquire 20 tokens
        threads = [threading.Thread(target=acquire_tokens, args=(20,)) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have acquired exactly 100 tokens
        assert acquired_count == 100


# =============================================================================
# AgentRateLimiters Tests
# =============================================================================


class TestAgentRateLimiters:
    """Tests for AgentRateLimiters manager."""

    def test_get_creates_limiter(self) -> None:
        """Test get creates limiter on first access."""
        manager = AgentRateLimiters(default_ops=50)

        limiter = manager.get("decay")

        assert limiter is not None
        assert limiter.max_ops == 50

    def test_get_returns_same_limiter(self) -> None:
        """Test get returns same limiter instance."""
        manager = AgentRateLimiters()

        limiter1 = manager.get("decay")
        limiter2 = manager.get("decay")

        assert limiter1 is limiter2

    def test_per_agent_limits(self) -> None:
        """Test per-agent custom limits."""
        manager = AgentRateLimiters(
            default_ops=100,
            per_agent_limits={"decay": 50, "cluster": 200},
        )

        assert manager.get("decay").max_ops == 50
        assert manager.get("cluster").max_ops == 200
        assert manager.get("merge").max_ops == 100  # Uses default

    def test_status(self) -> None:
        """Test status returns all active limiters."""
        manager = AgentRateLimiters(default_ops=10)

        manager.get("decay").acquire()
        manager.get("cluster")

        status = manager.status()

        assert "decay" in status
        assert "cluster" in status
        assert status["decay"]["remaining"] == 9
        assert status["cluster"]["remaining"] == 10

    def test_reset_all(self) -> None:
        """Test reset_all clears all limiters."""
        manager = AgentRateLimiters(default_ops=5)

        # Use some tokens
        for _ in range(3):
            manager.get("decay").acquire()
            manager.get("cluster").acquire()

        # Reset all
        manager.reset_all()

        assert manager.get("decay").remaining == 5
        assert manager.get("cluster").remaining == 5
