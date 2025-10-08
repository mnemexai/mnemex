"""Tests for temporal decay functions."""

import time

import pytest

from mnemex.core.decay import (
    calculate_decay_lambda,
    calculate_halflife,
    calculate_score,
    project_score_at_time,
    time_until_threshold,
)


def test_calculate_score_basic():
    """Test basic score calculation."""
    now = int(time.time())

    # Fresh memory with use_count=1 should have non-zero score
    score = calculate_score(
        use_count=1,
        last_used=now,
        strength=1.0,
        now=now,
        lambda_=2.673e-6,
        beta=0.6,
    )
    assert score > 0
    assert score == pytest.approx(1.0, rel=0.01)  # Should be close to 1 when just accessed


def test_calculate_score_decay():
    """Test that score decays over time."""
    now = int(time.time())
    one_day_ago = now - 86400

    score_fresh = calculate_score(
        use_count=1,
        last_used=now,
        strength=1.0,
        now=now,
        lambda_=2.673e-6,
        beta=0.6,
    )

    score_old = calculate_score(
        use_count=1,
        last_used=one_day_ago,
        strength=1.0,
        now=now,
        lambda_=2.673e-6,
        beta=0.6,
    )

    assert score_old < score_fresh  # Older memory has lower score


def test_calculate_score_use_count():
    """Test that higher use count increases score."""
    now = int(time.time())

    score_low = calculate_score(
        use_count=1,
        last_used=now,
        strength=1.0,
        now=now,
        lambda_=2.673e-6,
        beta=0.6,
    )

    score_high = calculate_score(
        use_count=10,
        last_used=now,
        strength=1.0,
        now=now,
        lambda_=2.673e-6,
        beta=0.6,
    )

    assert score_high > score_low  # Higher use count = higher score


def test_calculate_decay_lambda():
    """Test decay lambda calculation from half-life."""
    # 3-day half-life
    lambda_3d = calculate_decay_lambda(3.0)
    assert lambda_3d == pytest.approx(2.673e-6, rel=0.01)

    # 7-day half-life
    lambda_7d = calculate_decay_lambda(7.0)
    assert lambda_7d < lambda_3d  # Longer half-life = slower decay


def test_calculate_halflife():
    """Test half-life calculation from lambda."""
    lambda_val = 2.673e-6
    halflife = calculate_halflife(lambda_val)
    assert halflife == pytest.approx(3.0, rel=0.01)  # Should be 3 days


def test_time_until_threshold():
    """Test calculation of time until score drops below threshold."""
    now = int(time.time())

    # Memory with current score of 1.0
    remaining = time_until_threshold(
        current_score=1.0,
        threshold=0.5,  # Half the score
        last_used=now,
        lambda_=calculate_decay_lambda(3.0),  # 3-day half-life
    )

    assert remaining is not None
    # Should be approximately 3 days (259200 seconds)
    assert remaining == pytest.approx(259200, rel=0.1)


def test_time_until_threshold_already_below():
    """Test time_until_threshold when already below threshold."""
    now = int(time.time())

    remaining = time_until_threshold(
        current_score=0.3,
        threshold=0.5,
        last_used=now,
        lambda_=2.673e-6,
    )

    assert remaining is None  # Already below threshold


def test_project_score_at_time():
    """Test score projection to future time."""
    now = int(time.time())
    future = now + 86400  # 1 day from now

    projected = project_score_at_time(
        use_count=5,
        last_used=now,
        strength=1.0,
        target_time=future,
        lambda_=2.673e-6,
        beta=0.6,
    )

    current = calculate_score(
        use_count=5,
        last_used=now,
        strength=1.0,
        now=now,
        lambda_=2.673e-6,
        beta=0.6,
    )

    assert projected < current  # Future score should be lower due to decay
