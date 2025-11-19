"""Mathematical utility functions for CortexGraph."""

import math


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
