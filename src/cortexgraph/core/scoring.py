"""Scoring and decision logic for memory management."""

import time

from ..config import get_config
from ..storage.models import Memory
from .decay import calculate_score


def should_forget(memory: Memory, now: int | None = None) -> tuple[bool, float]:
    """
    Determine if a memory should be forgotten (deleted).

    Args:
        memory: Memory to evaluate
        now: Current timestamp (defaults to current time)

    Returns:
        Tuple of (should_forget, current_score)
    """
    config = get_config()

    if now is None:
        now = int(time.time())

    score = calculate_score(
        use_count=memory.use_count,
        last_used=memory.last_used,
        strength=memory.strength,
        now=now,
    )

    return score < config.forget_threshold, score


def should_promote(memory: Memory, now: int | None = None) -> tuple[bool, str, float]:
    """
    Determine if a memory should be promoted to long-term storage.

    A memory should be promoted if:
    1. Score is above promotion threshold, OR
    2. Use count is above threshold and memory has existed for minimum time

    Args:
        memory: Memory to evaluate
        now: Current timestamp (defaults to current time)

    Returns:
        Tuple of (should_promote, reason, current_score)
    """
    config = get_config()

    if now is None:
        now = int(time.time())

    score = calculate_score(
        use_count=memory.use_count,
        last_used=memory.last_used,
        strength=memory.strength,
        now=now,
    )

    # Check score-based promotion
    if score >= config.promote_threshold:
        return True, f"High score ({score:.2f} >= {config.promote_threshold})", score

    # Check use count-based promotion
    age_days = (now - memory.created_at) / 86400
    if memory.use_count >= config.promote_use_count and age_days <= config.promote_time_window:
        return (
            True,
            f"High use count ({memory.use_count} >= {config.promote_use_count}) "
            f"within {config.promote_time_window} days",
            score,
        )

    return False, "Does not meet promotion criteria", score


def rank_memories_by_score(
    memories: list[Memory], now: int | None = None
) -> list[tuple[Memory, float]]:
    """
    Rank memories by their current decay score.

    Args:
        memories: List of memories to rank
        now: Current timestamp (defaults to current time)

    Returns:
        List of (memory, score) tuples, sorted by score descending
    """
    if now is None:
        now = int(time.time())

    scored = []
    for memory in memories:
        score = calculate_score(
            use_count=memory.use_count,
            last_used=memory.last_used,
            strength=memory.strength,
            now=now,
        )
        scored.append((memory, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored


def filter_by_score(
    memories: list[Memory], min_score: float, now: int | None = None
) -> list[tuple[Memory, float]]:
    """
    Filter memories by minimum score threshold.

    Args:
        memories: List of memories to filter
        min_score: Minimum score threshold
        now: Current timestamp (defaults to current time)

    Returns:
        List of (memory, score) tuples that meet the threshold
    """
    if now is None:
        now = int(time.time())

    filtered = []
    for memory in memories:
        score = calculate_score(
            use_count=memory.use_count,
            last_used=memory.last_used,
            strength=memory.strength,
            now=now,
        )
        if score >= min_score:
            filtered.append((memory, score))

    return filtered


def calculate_memory_age(memory: Memory, now: int | None = None) -> float:
    """
    Calculate the age of a memory in days.

    Args:
        memory: Memory to evaluate
        now: Current timestamp (defaults to current time)

    Returns:
        Age in days
    """
    if now is None:
        now = int(time.time())

    age_seconds = now - memory.created_at
    return age_seconds / 86400


def calculate_recency(memory: Memory, now: int | None = None) -> float:
    """
    Calculate recency score (time since last use, in days).

    Args:
        memory: Memory to evaluate
        now: Current timestamp (defaults to current time)

    Returns:
        Days since last use
    """
    if now is None:
        now = int(time.time())

    recency_seconds = now - memory.last_used
    return recency_seconds / 86400
