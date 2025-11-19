"""Temporal decay functions for memory scoring.

Supports multiple decay models:
- power_law (default): (1 + dt/t0)^(-alpha)
- exponential: exp(-lambda * dt)
- two_component: w * exp(-lambda_fast*dt) + (1-w) * exp(-lambda_slow*dt)
"""

import math
import time

# Re-export math utilities for backward compatibility with existing imports
# These functions were refactored to math_utils.py but are imported here to maintain
# the public API (used by core/__init__.py and server.py)
from .math_utils import calculate_decay_lambda, calculate_halflife  # noqa: F401

# Constants
SECONDS_PER_DAY = 86400.0
SECONDS_PER_HOUR = 3600.0
BISECTION_MAX_YEARS = 10.0
BISECTION_MAX_SECONDS = 3650 * SECONDS_PER_DAY  # ~10 years
BISECTION_EXPANSION_ITERATIONS = 32
BISECTION_PRECISION_ITERATIONS = 60


def calculate_score(
    use_count: int,
    last_used: int,
    strength: float,
    now: int | None = None,
    lambda_: float | None = None,
    beta: float | None = None,
) -> float:
    """Calculate current score using the configured decay model.

    If `lambda_` is provided, uses exponential decay explicitly
    (for backward compatibility and tests). Otherwise, branches
    by `config.decay_model`.
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
    # Add 1 to use_count so new memories (use_count=0) don't get zero score
    # This gives new memories a grace period before decay dominates
    use_component = math.pow(use_count + 1, beta)
    # If lambda_ explicitly provided, force exponential path
    if lambda_ is not None and (getattr(config, "decay_model", "power_law") != "exponential"):
        decay_component = math.exp(-lambda_ * time_delta)
    else:
        model = getattr(config, "decay_model", "power_law")
        if model == "power_law":
            # Derive t0 from alpha and target half-life
            alpha = config.pl_alpha
            t_half = config.pl_halflife_days * SECONDS_PER_DAY
            # t0 = H / (2^(1/alpha) - 1)
            denom = math.pow(2.0, 1.0 / alpha) - 1.0
            t0 = t_half / denom if denom > 0 else t_half
            decay_component = math.pow(1.0 + (time_delta / t0), -alpha)
        elif model == "two_component":
            w = config.tc_weight_fast
            decay_component = w * math.exp(-config.tc_lambda_fast * time_delta) + (
                1.0 - w
            ) * math.exp(-config.tc_lambda_slow * time_delta)
        else:  # exponential
            decay_component = math.exp(-lambda_ * time_delta)

    return use_component * decay_component * strength


def time_until_threshold(
    current_score: float,
    threshold: float,
    last_used: int,
    lambda_: float | None = None,
) -> float | None:
    """Calculate seconds until score drops below threshold.

    If `lambda_` is provided, uses exponential closed-form.
    Otherwise, branches by configured decay model. For two-component
    decay, uses numeric bisection.
    """
    from ..config import get_config

    if current_score <= threshold:
        return None

    config = get_config()
    now = int(time.time())

    if lambda_ is not None or getattr(config, "decay_model", "power_law") == "exponential":
        if lambda_ is None:
            lambda_ = config.decay_lambda
        # threshold = current_score * exp(-lambda * t) -> t = -ln(threshold/current)/lambda
        time_delta = -math.log(threshold / current_score) / lambda_
        elapsed = now - last_used
        remaining = time_delta - elapsed
        return max(0, remaining)

    # Factor out K * f(dt). Let f be decay function; current_score = K * f(elapsed).
    elapsed = now - last_used

    def f(dt: float) -> float:
        model = getattr(config, "decay_model", "power_law")
        if model == "power_law":
            alpha = config.pl_alpha
            t_half = config.pl_halflife_days * SECONDS_PER_DAY
            denom = math.pow(2.0, 1.0 / alpha) - 1.0
            t0 = t_half / denom if denom > 0 else t_half
            return math.pow(1.0 + (dt / t0), -alpha)
        elif model == "two_component":
            return config.tc_weight_fast * math.exp(-config.tc_lambda_fast * dt) + (
                1.0 - config.tc_weight_fast
            ) * math.exp(-config.tc_lambda_slow * dt)
        else:
            return math.exp(-config.decay_lambda * dt)

    # We want t such that K*f(elapsed + t) = threshold; K = current_score / f(elapsed)
    # => f(elapsed + t) = threshold * f(elapsed) / current_score
    f_elapsed = f(float(elapsed))
    target = (threshold * f_elapsed) / current_score
    # If target >= f_elapsed, then threshold already reached or below (shouldn't happen due to early return)

    # Bisection search for t >= 0 with upper bound expansion
    lo = 0.0
    hi = SECONDS_PER_HOUR  # start with 1 hour
    # Expand until f(elapsed + hi) <= target or cap
    for _ in range(BISECTION_EXPANSION_ITERATIONS):
        if f(elapsed + hi) <= target:
            break
        hi *= 2.0
        if hi > BISECTION_MAX_SECONDS:  # cap ~10 years
            break

    # If even at very large hi we haven't crossed, return None (effectively never)
    if f(elapsed + hi) > target:
        return None

    for _ in range(BISECTION_PRECISION_ITERATIONS):  # high-precision bisection
        mid = (lo + hi) / 2.0
        if f(elapsed + mid) <= target:
            hi = mid
        else:
            lo = mid
    remaining = hi
    return max(0.0, remaining)


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
