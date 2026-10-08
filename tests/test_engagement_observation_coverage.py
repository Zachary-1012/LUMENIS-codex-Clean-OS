"""Native count/coverage semantics and the existing ViewModel consumer."""
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import sys

import pytest

from canonical_data import CanonicalRecord, note_to_canonical
from canonical_metrics import ENGAGEMENT_KEYS, engagement_count, engagement_stats
from ui_view_model import DataLayer, DataQuery, DataResult, DataStatus, MetricLayer, ViewModelBuilder


@pytest.mark.parametrize("value", [None, "", "—", "3.7", 3.7, -1, True, False, "2k", "1万",
                                    "1,2", "NaN", float("nan"), float("inf"), float(2**53)])
def test_unmeasured_or_inexact_count_is_not_a_measured_zero(value):
    assert engagement_count(value) is None
    record = note_to_canonical({"note_id": "counter", "likes": value})
    assert record.engagement_likes is None
    assert record.engagement_total() is None


@pytest.mark.parametrize("value,expected", [(0, 0), ("0", 0), (1.0, 1), ("1,234", 1234),
                                            ("9007199254740993", 9007199254740993)])
def test_exact_native_counts_keep_zero_and_integer_precision(value, expected):
    assert engagement_count(value) == expected


def test_oversized_decimal_does_not_disable_runtime_conversion_safety():
    previous_limit = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        assert engagement_count("9" * 5000) is None
        assert sys.get_int_max_str_digits() == 4300
    finally:
        sys.set_int_max_str_digits(previous_limit)


def test_unrepresentable_average_preserves_exact_sum_and_complete_coverage():
    exact = 10**400
    result = engagement_stats([{**{k: 0 for k in ENGAGEMENT_KEYS}, "likes": exact}])
    assert result["sum"] == exact and result["observed_sum"] == exact
    assert result["per_field"]["likes"] == exact
    assert result["avg"] is None
    assert result["quality"]["state"] == "COMPLETE"
    assert result["quality"]["reason"] is None
    assert result["quality"]["avg_reason"] == "ENGAGEMENT_AVERAGE_OUT_OF_RANGE"
    assert result["quality"]["known_field_count"] == result["quality"]["expected_field_count"] == 4


def test_one_unobserved_post_does_not_become_a_zero_post_in_an_average():
    result = engagement_stats([{k: 0 for k in ENGAGEMENT_KEYS}, {k: None for k in ENGAGEMENT_KEYS}])
    assert result["sum"] is None
    assert result["avg"] is None
    assert result["observed_sum"] == 0
    assert result["quality"]["state"] == "PARTIAL"
    assert result["quality"]["observed_notes"] == 1
    assert result["quality"]["complete_notes"] == 1
    assert result["quality"]["known_field_count"] == 4
    assert result["quality"]["expected_field_count"] == 8


def test_complete_real_zero_is_distinct_from_unobserved_or_partial_zero():
    complete = engagement_stats([{k: 0 for k in ENGAGEMENT_KEYS}])
    unknown = engagement_stats([{}])
    partial = engagement_stats([{"likes": 0}])
    assert (complete["sum"], complete["quality"]["state"]) == (0, "COMPLETE")
    assert (unknown["sum"], unknown["observed_sum"], unknown["quality"]["state"]) == (None, None, "UNKNOWN")
    assert (partial["sum"], partial["observed_sum"], partial["quality"]["state"]) == (None, 0, "PARTIAL")
    assert partial["observed_per_field"]["comments"] is None


def test_invalid_components_are_counted_in_coverage_without_manufacturing_values():
    result = engagement_stats([{"likes": True, "comments": "2k", "collects": -1, "shares": None}, None])
    assert result["sum"] is None and result["observed_sum"] is None
    assert result["quality"]["invalid_field_count"] == 3
    assert result["quality"]["missing_field_count"] == 8
    assert result["quality"]["missing_field_notes"] == 2


@pytest.mark.parametrize("components,expected_state,expected_value,observed", [
    ({}, "unavailable", None, None),
    ({"likes": 0}, "partial", None, 0),
    ({k: 0 for k in ENGAGEMENT_KEYS}, "ok", 0, 0),
])
def test_serialized_viewmodel_preserves_post_presence_and_metric_missingness(
    components, expected_state, expected_value, observed,
):
    record = {"title": "real source body exists", "evidence_ref": "native-ref", **components}
    def fetch(query):
        return DataResult(query=query, records=[record], total=1, status=DataStatus.OK,
                          source_timestamp=datetime.now(timezone.utc).isoformat())
    builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=fetch))
    result = builder.build("collection", "单帖互动", DataQuery(source="native-source")).to_dict()
    metric = result["metrics"]["engagement"]
    assert result["truth"]["record_count"] == 1
    assert metric["current_value"] == expected_value
    assert metric["status"] == expected_state
    assert metric["breakdown"]["observed_sum"] == observed
    assert metric["reason"] == {"ok": None, "partial": "INCOMPLETE_ENGAGEMENT_COMPONENT_COVERAGE",
                                "unavailable": "NO_MEASURED_ENGAGEMENT_COMPONENTS"}[expected_state]


def test_metric_owner_unavailable_does_not_activate_another_total():
    layer = MetricLayer()
    layer._canonical = None
    result = layer.engagement_total([{k: 1 for k in ENGAGEMENT_KEYS}])
    assert result.value is None
    assert result.status == DataStatus.UNAVAILABLE.value
    assert result.reason == "CANONICAL_METRICS_UNAVAILABLE"


def test_existing_raw_metric_consumer_remains_json_serializable():
    metric = MetricLayer().engagement_total([{"likes": 0}])
    payload = json.loads(json.dumps(metric.__dict__))
    assert payload["value"] is None
    assert payload["status"] == "partial"
    assert payload["breakdown"]["observed_sum"] == 0


def test_old_loaded_metric_contract_cannot_forge_current_zero():
    layer = MetricLayer()
    layer._canonical = SimpleNamespace(engagement_stats=lambda rows: {"sum": 0, "quality": {}})
    result = layer.engagement_total([{}])
    assert result.value is None
    assert result.reason == "ENGAGEMENT_CONTRACT_VERSION_MISMATCH"


def test_unknown_previous_period_does_not_fabricate_growth():
    builder = ViewModelBuilder()
    current = builder.metric_layer.engagement_total([{k: 1 for k in ENGAGEMENT_KEYS}])
    delta = builder._compute_delta(current, [{}], "engagement")
    assert delta.value is None and delta.percent is None
