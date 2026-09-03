"""Baseline-aware breakout classification.

This is intentionally model-free. Platform-specific collectors provide
normalized observations; this layer only compares current values to a known
baseline and labels the state.
"""
from __future__ import annotations

from enum import StrEnum


class BreakoutState(StrEnum):
    NORMAL = "normal"
    ACCELERATING = "accelerating"
    BREAKOUT = "breakout"
    VIRAL = "viral"
    UNDERPERFORMING = "underperforming"
    DECAYING = "decaying"


def classify_breakout(current: float, baseline: float, *, breakout_ratio: float = 1.8, viral_ratio: float = 3.0) -> BreakoutState:
    if baseline <= 0:
        return BreakoutState.NORMAL
    ratio = current / baseline
    if ratio >= viral_ratio:
        return BreakoutState.VIRAL
    if ratio >= breakout_ratio:
        return BreakoutState.BREAKOUT
    if ratio >= 1.25:
        return BreakoutState.ACCELERATING
    if ratio <= 0.55:
        return BreakoutState.DECAYING
    if ratio <= 0.8:
        return BreakoutState.UNDERPERFORMING
    return BreakoutState.NORMAL
