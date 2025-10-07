"""Temporal decay functions for memory scoring."""

import math
import time


def calculate_score(
    use_count: int,
    last_used: int,
    strength: float,
    now: int | None = None,
    lambda_: float | None = None,
    beta: float | None = None,
) -> float:
    """
    Calculate the current score of a memory using exponential decay.

    The formula is:
        score = (use_count ^ beta) * exp(-lambda * time_delta) * strength

    Where:
        - use_count: Number of times the memory has been accessed
        - beta: Exponent that weights the importance of use_count
        - lambda: Decay constant (higher = faster decay)
        - time_delta: Time since last use (in seconds)
        - strength: Base strength of the memory

    Args:
        use_count: Number of times memory has been accessed
        last_used: Unix timestamp when memory was last used
        strength: Base strength multiplier
        now: Current timestamp (defaults to current time)
        lambda_: Decay constant (defaults to config value)
        beta: Use count exponent (defaults to config value)

    Returns:
        Current score of the memory (0 to ~infinity, typically 0-100)
    """
    from ..config import get_config

    if now is None:
        now = int(time.time())

    config = get_config()
    if lambda_ is None:
        lambda_ = config.decay_lambda
    if beta is None:
        beta = config.decay_beta

    time_delta = max(0, now - last_used)

    # Calculate components
    use_component = math.pow(use_count, beta) if use_count > 0 else 0
    decay_component = math.exp(-lambda_ * time_delta)

    return use_component * decay_component * strength


def calculate_decay_lambda(halflife_days: float) -> float:
    """
    Calculate decay constant from half-life in days.

    Half-life is the time it takes for the score to decay to 50% of its original value.

    Args:
        halflife_days: Half-life period in days

    Returns:
        Decay constant (lambda) for exponential decay
    """
    halflife_seconds = halflife_days * 86400
    return math.log(2) / halflife_seconds


def calculate_halflife(lambda_: float) -> float:
    """
    Calculate half-life in days from decay constant.

    Args:
        lambda_: Decay constant

    Returns:
        Half-life in days
    """
    halflife_seconds = math.log(2) / lambda_
    return halflife_seconds / 86400


def time_until_threshold(
    current_score: float,
    threshold: float,
    last_used: int,
    lambda_: float | None = None,
) -> float | None:
    """
    Calculate how many seconds until the memory score drops below a threshold.

    Args:
        current_score: Current memory score
        threshold: Threshold score
        last_used: Unix timestamp when memory was last used
        lambda_: Decay constant (defaults to config value)

    Returns:
        Seconds until threshold, or None if already below threshold
    """
    from ..config import get_config

    if current_score <= threshold:
        return None

    if lambda_ is None:
        lambda_ = get_config().decay_lambda

    # From: threshold = current_score * exp(-lambda * t)
    # Solve for t: t = -ln(threshold / current_score) / lambda
    time_delta = -math.log(threshold / current_score) / lambda_

    now = int(time.time())
    elapsed = now - last_used
    remaining = time_delta - elapsed

    return max(0, remaining)


def project_score_at_time(
    use_count: int,
    last_used: int,
    strength: float,
    target_time: int,
    lambda_: float | None = None,
    beta: float | None = None,
) -> float:
    """
    Project what the memory score will be at a future time.

    Args:
        use_count: Number of times memory has been accessed
        last_used: Unix timestamp when memory was last used
        strength: Base strength multiplier
        target_time: Unix timestamp to project to
        lambda_: Decay constant (defaults to config value)
        beta: Use count exponent (defaults to config value)

    Returns:
        Projected score at target_time
    """
    return calculate_score(
        use_count=use_count,
        last_used=last_used,
        strength=strength,
        now=target_time,
        lambda_=lambda_,
        beta=beta,
    )
