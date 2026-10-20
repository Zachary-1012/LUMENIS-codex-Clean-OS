"""Pure KOS tier classification regressions; no product route or external effect."""

import pytest

import kos_engine


def test_low_finite_engagement_returns_unknown_with_readable_reason():
    result = kos_engine.classify_kol_tier(followers=500_000, engagement_rate=0.005)

    assert result["tier"] == "unknown"
    assert result["engagement_rate"] == 0.005
    assert "0.50%" in result["reason"]
    assert "未达到" in result["reason"]


def test_engagement_threshold_and_missing_value_keep_existing_behavior():
    at_threshold = kos_engine.classify_kol_tier(followers=500_000, engagement_rate=0.01)
    missing = kos_engine.classify_kol_tier(followers=500_000, engagement_rate=None)

    assert at_threshold["tier"] == "head"
    assert missing["tier"] == "head"
    assert missing["engagement_unknown"] is True
    assert "仅按粉丝量" in missing["reason"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.01, True])
def test_invalid_engagement_is_treated_as_unknown(value):
    result = kos_engine.classify_kol_tier(followers=500_000, engagement_rate=value)

    assert result["tier"] == "head"
    assert result["engagement_rate"] is None
    assert result["engagement_unknown"] is True


def test_zero_interaction_has_valid_percentage_diagnostic():
    result = kos_engine.classify_kol_tier(followers=500_000, engagement_rate=0.0)

    assert result["tier"] == "unknown"
    assert "0.00%" in result["reason"]
