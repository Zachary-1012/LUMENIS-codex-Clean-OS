"""User-provided campaign calculations preserve missingness and provenance."""

import math
import pytest
from kos_metrics import koc_campaign_review


def test_campaign_incomplete_metrics_are_unknown_with_explicit_partial_coverage():
    result = koc_campaign_review(
        "Private review",
        [
            {"author_id": "a", "engagement": 0},
            {"author_id": "b", "viewership": 10, "engagement": 2},
        ],
    )
    assert result["engagement"] == 2
    assert result["viewership"] is None
    assert result["coverage"]["viewership"] == {
        "known": 1,
        "provided_rows": 2,
        "known_subtotal": 10,
    }
    assert result["tiers"] == {"UNKNOWN": 2}
    assert result["external_campaign_results"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("value", [True, -1, math.inf, math.nan, "10"])
def test_campaign_rejects_invalid_metrics(value):
    with pytest.raises(ValueError, match="NUMBER_INVALID"):
        koc_campaign_review("Review", [{"viewership": value}])


def test_empty_campaign_is_not_zero_population_measurement():
    result = koc_campaign_review("Review", [])
    assert result["viewership"] is None
    assert result["population_coverage"] == "UNKNOWN"
