"""Tests for multiple decay models (power-law, exponential, two-component)."""

from __future__ import annotations

import time

import pytest

from cortexgraph.config import Config, set_config
from cortexgraph.core.decay import (
    calculate_decay_lambda,
    calculate_score,
    time_until_threshold,
)


def test_power_law_halflife_matches_config():
    now = int(time.time())
    cfg = Config(
        decay_model="power_law",
        pl_alpha=1.1,
        pl_halflife_days=3.0,
        decay_beta=0.6,
    )
    set_config(cfg)

    # With current_score = 1.0 and threshold=0.5, time_until_threshold ~= half-life
    remaining = time_until_threshold(
        current_score=1.0,
        threshold=0.5,
        last_used=now,
    )
    assert remaining is not None
    assert remaining == pytest.approx(3 * 86400, rel=0.2)


def test_power_law_heavier_tail_than_exponential():
    now = int(time.time())
    days = 21
    dt = days * 86400

    # Configure power-law 3-day half-life
    cfg = Config(decay_model="power_law", pl_alpha=1.1, pl_halflife_days=3.0, decay_beta=0.6)
    set_config(cfg)

    # Power-law score at dt
    s_pl = calculate_score(use_count=1, last_used=now - dt, strength=1.0, now=now, beta=0.6)

    # Exponential score with 3-day half-life
    lam = calculate_decay_lambda(3.0)
    s_exp = calculate_score(
        use_count=1,
        last_used=now - dt,
        strength=1.0,
        now=now,
        lambda_=lam,  # force exponential path
        beta=0.6,
    )

    assert s_pl > s_exp  # power-law should retain more at long times


def test_two_component_limits_match_single_exponential():
    now = int(time.time())
    lam_3d = calculate_decay_lambda(3.0)
    lam_7d = calculate_decay_lambda(7.0)

    # w=1.0 => effectively single exponential with fast lambda
    cfg_fast = Config(
        decay_model="two_component",
        tc_lambda_fast=lam_3d,
        tc_lambda_slow=lam_7d,
        tc_weight_fast=1.0,
        decay_beta=0.6,
    )
    set_config(cfg_fast)
    rem_fast = time_until_threshold(1.0, 0.5, now)
    assert rem_fast == pytest.approx(3 * 86400, rel=0.2)

    # w=0.0 => effectively single exponential with slow lambda
    cfg_slow = Config(
        decay_model="two_component",
        tc_lambda_fast=lam_3d,
        tc_lambda_slow=lam_7d,
        tc_weight_fast=0.0,
        decay_beta=0.6,
    )
    set_config(cfg_slow)
    rem_slow = time_until_threshold(1.0, 0.5, now)
    assert rem_slow == pytest.approx(7 * 86400, rel=0.2)
