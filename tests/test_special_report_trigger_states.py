"""Tri-state contract for the five existing special-report trigger rules."""

import risk_engine


CONDITION_NAMES = (
    "negative_engagement",
    "negative_cluster_24h",
    "safety_discrimination_or_illegal",
    "local_koc_forward",
    "group_or_media_inquiry",
)


def _known_false_event():
    return {
        "engagement": 0,
        "sentiment": "negative",
        "negative_count_24h": "0",
        "title": "",
        "content": "",
        "subject_hit": {"is_high_risk": False},
        "is_koc_forwarded": False,
        "is_media_inquiry": False,
    }


def test_real_zero_and_complete_known_inputs_are_not_triggered():
    decision = risk_engine.special_report_trigger_decision(_known_false_event())

    assert decision["recipe"] == "SPECIAL_REPORT_TRIGGER_V2"
    assert decision["triggered"] is False
    assert decision["state"] == "NOT_TRIGGERED"
    assert decision["unknown_conditions"] == []
    assert decision["reasons"] == []
    assert all(item["value"] is False and item["reason"] is None
               for item in decision["conditions"].values())
    assert decision["metadata"] == {
        "basis": "RULE_DERIVED",
        "business_outcome_measured": False,
    }


def test_negative_engagement_threshold_is_inclusive():
    below = _known_false_event()
    below.update(sentiment="negative", engagement=499)
    at = {**below, "engagement": 500}

    below_decision = risk_engine.special_report_trigger_decision(below)
    at_decision = risk_engine.special_report_trigger_decision(at)

    assert below_decision["conditions"]["negative_engagement"]["value"] is False
    assert below_decision["triggered"] is False
    assert at_decision["conditions"]["negative_engagement"]["value"] is True
    assert at_decision["triggered"] is True
    assert at_decision["reasons"] == ["单条负面互动≥500（当前500）"]


def test_negative_cluster_threshold_is_inclusive():
    below = {**_known_false_event(), "negative_count_24h": 2}
    at = {**below, "negative_count_24h": 3}

    below_decision = risk_engine.special_report_trigger_decision(below)
    at_decision = risk_engine.special_report_trigger_decision(at)

    assert below_decision["conditions"]["negative_cluster_24h"]["value"] is False
    assert at_decision["conditions"]["negative_cluster_24h"]["value"] is True
    assert at_decision["reasons"] == ["24h内负面帖≥3条集中爆发（当前3条）"]


def test_all_missing_inputs_return_unknown_without_fabricated_reasons():
    decision = risk_engine.special_report_trigger_decision({})

    assert decision["triggered"] is None
    assert decision["state"] == "UNKNOWN"
    assert decision["unknown_conditions"] == list(CONDITION_NAMES)
    assert decision["reasons"] == []
    assert all(item["value"] is None and item["reason"]
               for item in decision["conditions"].values())


def test_unknown_conditions_name_missing_and_invalid_inputs():
    missing = risk_engine.special_report_trigger_decision({})
    invalid_event = risk_engine.special_report_trigger_decision(None)
    invalid_values = _known_false_event()
    invalid_values.update(engagement=500.5, is_koc_forwarded="false")
    invalid = risk_engine.special_report_trigger_decision(invalid_values)

    assert missing["conditions"]["negative_engagement"]["reason"] == (
        "MISSING:sentiment;MISSING:engagement"
    )
    assert missing["conditions"]["negative_cluster_24h"]["reason"] == (
        "MISSING:negative_count_24h"
    )
    assert invalid_event["conditions"]["negative_engagement"]["reason"] == (
        "INVALID:event"
    )
    assert invalid["conditions"]["negative_engagement"]["reason"] == (
        "INVALID:engagement"
    )
    assert invalid["conditions"]["local_koc_forward"]["reason"] == (
        "INVALID:is_koc_forwarded"
    )


def test_known_positive_trigger_wins_over_other_unknown_conditions():
    decision = risk_engine.special_report_trigger_decision({"is_koc_forwarded": True})

    assert decision["triggered"] is True
    assert decision["state"] == "TRIGGERED"
    assert decision["conditions"]["local_koc_forward"] == {
        "value": True,
        "reason": None,
    }
    assert decision["unknown_conditions"] == [
        "negative_engagement",
        "negative_cluster_24h",
        "safety_discrimination_or_illegal",
        "group_or_media_inquiry",
    ]
    assert decision["reasons"] == ["本地KOC转发（kos_profiles联动）"]


def test_keyword_hit_is_rule_derived_even_when_other_text_is_missing():
    decision = risk_engine.special_report_trigger_decision({"title": "现场安全事故"})

    condition = decision["conditions"]["safety_discrimination_or_illegal"]
    assert condition["value"] is True
    assert condition["reason"] is None
    assert decision["triggered"] is True
    assert decision["reasons"] == ["涉及安全/歧视/违法关键词（命中: safety）"]
    assert decision["metadata"]["basis"] == "RULE_DERIVED"
    assert decision["metadata"]["business_outcome_measured"] is False


def test_empty_text_is_known_but_missing_text_or_subject_rule_stays_unknown():
    known = _known_false_event()
    known_decision = risk_engine.special_report_trigger_decision(known)
    missing_text = {**known, "title": None}
    missing_subject_flag = {**known, "subject_hit": {}}

    assert known_decision["conditions"]["safety_discrimination_or_illegal"]["value"] is False
    assert risk_engine.special_report_trigger_decision(missing_text)["conditions"][
        "safety_discrimination_or_illegal"
    ]["value"] is None
    assert risk_engine.special_report_trigger_decision(missing_subject_flag)["conditions"][
        "safety_discrimination_or_illegal"
    ]["value"] is None


def test_exact_subject_risk_true_can_trigger_without_text():
    decision = risk_engine.special_report_trigger_decision(
        {"subject_hit": {"is_high_risk": True}}
    )

    assert decision["conditions"]["safety_discrimination_or_illegal"]["value"] is True
    assert decision["reasons"] == [
        "涉及安全/歧视/违法关键词（命中: subject_rules_high_risk）"
    ]


def test_sentiment_requires_an_exact_canonical_value():
    for sentiment in ("unknown", "NEGATIVE", " negative ", "other", None, []):
        event = {**_known_false_event(), "sentiment": sentiment, "engagement": 500}
        decision = risk_engine.special_report_trigger_decision(event)
        assert decision["conditions"]["negative_engagement"]["value"] is None
        assert decision["triggered"] is None

    nonnegative = {**_known_false_event(), "sentiment": "positive", "engagement": None}
    assert risk_engine.special_report_trigger_decision(nonnegative)["conditions"][
        "negative_engagement"
    ]["value"] is False


def test_numeric_strings_use_the_existing_exact_count_parser():
    event = {
        **_known_false_event(),
        "sentiment": "negative",
        "engagement": "1,000",
        "negative_count_24h": "3",
    }
    decision = risk_engine.special_report_trigger_decision(event)

    assert decision["conditions"]["negative_engagement"]["value"] is True
    assert decision["conditions"]["negative_cluster_24h"]["value"] is True
    assert decision["reasons"] == [
        "单条负面互动≥500（当前1000）",
        "24h内负面帖≥3条集中爆发（当前3条）",
    ]


def test_invalid_engagement_is_unknown_instead_of_zero_or_rounded():
    invalid_counts = (None, True, float("nan"), float("inf"), -1, "1万", 500.5)
    for value in invalid_counts:
        event = {**_known_false_event(), "sentiment": "negative", "engagement": value}
        decision = risk_engine.special_report_trigger_decision(event)
        condition = decision["conditions"]["negative_engagement"]
        assert condition["value"] is None, value
        assert condition["reason"], value
        assert decision["triggered"] is None, value


def test_invalid_negative_cluster_count_is_unknown():
    for value in (None, False, float("nan"), float("inf"), -1, "1万", 2.5):
        event = {**_known_false_event(), "negative_count_24h": value}
        decision = risk_engine.special_report_trigger_decision(event)
        condition = decision["conditions"]["negative_cluster_24h"]
        assert condition["value"] is None, value
        assert condition["reason"], value
        assert decision["triggered"] is None, value


def test_manual_flags_require_exact_booleans():
    for value in ("false", "0", 0, 1, [], "true"):
        event = {**_known_false_event(), "is_koc_forwarded": value}
        decision = risk_engine.special_report_trigger_decision(event)
        condition = decision["conditions"]["local_koc_forward"]
        assert condition["value"] is None, value
        assert condition["reason"], value
        assert decision["triggered"] is None, value

    assert risk_engine.special_report_trigger_decision(
        {**_known_false_event(), "is_media_inquiry": True}
    )["conditions"]["group_or_media_inquiry"]["value"] is True


def test_non_mapping_event_is_explicitly_unknown_and_does_not_crash():
    decision = risk_engine.special_report_trigger_decision(None)

    assert decision["triggered"] is None
    assert decision["state"] == "UNKNOWN"
    assert decision["unknown_conditions"] == list(CONDITION_NAMES)
    assert decision["reasons"] == []


def test_legacy_tuple_preserves_tri_state_and_reason_list():
    event = {"is_media_inquiry": True}
    decision = risk_engine.special_report_trigger_decision(event)

    assert risk_engine.check_special_report_trigger(event) == (
        decision["triggered"], decision["reasons"]
    )
    assert risk_engine.check_special_report_trigger({}) == (None, [])


def test_existing_config_keeps_the_approved_thresholds():
    conditions = risk_engine.get_special_report_trigger_config()["trigger_conditions"]

    assert conditions[0]["threshold"] == 500
    assert conditions[1]["threshold"] == 3
