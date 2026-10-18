"""Baseline-aware breakout classification.

This is intentionally model-free. Platform-specific collectors provide
normalized observations; this layer only compares current values to a known
baseline and labels the state.
"""
from __future__ import annotations

from enum import StrEnum
import math


class BreakoutState(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    NORMAL = "normal"
    ACCELERATING = "accelerating"
    BREAKOUT = "breakout"
    VIRAL = "viral"
    UNDERPERFORMING = "underperforming"
    DECAYING = "decaying"


def classify_breakout(current: float | None, baseline: float | None, *, breakout_ratio: float = 1.8, viral_ratio: float = 3.0) -> BreakoutState:
    for value in (current, baseline):
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value < 0):
            raise ValueError("PODCAST_BREAKOUT_OBSERVATION_INVALID")
    if (any(type(value) not in (int,float) or not math.isfinite(value) for value in (breakout_ratio,viral_ratio))
            or not 1 < breakout_ratio < viral_ratio):
        raise ValueError("PODCAST_BREAKOUT_THRESHOLDS_INVALID")
    if current is None or baseline is None or baseline == 0:
        return BreakoutState.INSUFFICIENT_DATA
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
