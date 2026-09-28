"""Topic input truth: unobserved signals are not zero or negative judgments."""
import math

import pytest
from flask import Flask

import podcast_routes
import topic_scoring


FIELDS = tuple(topic_scoring.TopicSignals.__dataclass_fields__)


@pytest.fixture
def topic_client(monkeypatch):
    def unexpected_store():
        pytest.fail("stateless topic evaluation must not open the entity store")

    monkeypatch.setattr(podcast_routes, "_store", unexpected_store)
    app = Flask(__name__)
    app.register_blueprint(podcast_routes.podcast_bp)
    return app.test_client()


def test_empty_signals_are_unknown_not_zero():
    signals = topic_scoring.TopicSignals()
    assert topic_scoring.score_topic(signals) is None
    assert topic_scoring.classify_topic(None, None) is None
    assert all(getattr(signals, field) is None for field in FIELDS)


@pytest.mark.parametrize("payload", [{}, {"signals": {}}, {"signals": {"demand": None}}])
def test_empty_request_has_input_required_result(topic_client, payload):
    response = topic_client.post("/api/podcast/topic-score", json=payload)
    assert response.status_code == 200, response.json
    assert response.json["state"] == "input_required"
    assert response.json["score"] is None and response.json["stage"] is None
    assert response.json["signals"] == dict.fromkeys(FIELDS)
    assert response.json["missing_signals"] == list(FIELDS)


@pytest.mark.parametrize("missing", FIELDS)
@pytest.mark.parametrize("form", ["absent", "null"])
def test_each_missing_signal_prevents_complete_score(topic_client, missing, form):
    values = dict.fromkeys(FIELDS, 0.5)
    if form == "absent":
        del values[missing]
    else:
        values[missing] = None
    response = topic_client.post("/api/podcast/topic-score", json={"signals": values})
    assert response.status_code == 200
    assert response.json["state"] == "input_required"
    assert response.json["missing_signals"] == [missing]
    assert response.json["signals"][missing] is None
    assert response.json["score"] is None and response.json["stage"] is None


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [True, False, math.nan, math.inf, -math.inf, "0.5", "", [], {}, -0.1, 1.1])
def test_invalid_signal_never_becomes_a_score(topic_client, field, value):
    values = dict.fromkeys(FIELDS, 0.5)
    values[field] = value
    with pytest.raises(ValueError):
        topic_scoring.TopicSignals(**values)
    response = topic_client.post("/api/podcast/topic-score", json={"signals": values})
    assert response.status_code == 400, response.json
    assert response.json["code"] == "PODCAST_TOPIC_SIGNALS_INVALID"
    assert response.json["state"] == "invalid_input"
    assert response.json["score"] is None and response.json["stage"] is None


@pytest.mark.parametrize("body", [[], True, 1, "signals", {"signals": []}, {"signals": None}, {"demand_typo": 1}])
def test_invalid_body_does_not_fall_back_to_empty_or_zero(topic_client, body):
    response = topic_client.post("/api/podcast/topic-score", json=body)
    assert response.status_code == 400, response.json
    assert response.json["state"] == "invalid_input"
    assert response.json["score"] is None


def test_json_null_and_malformed_json_are_explicit_client_errors(topic_client):
    for body in ("null", "{not-json", ""):
        response = topic_client.post("/api/podcast/topic-score", data=body, content_type="application/json")
        assert response.status_code == 400, response.json
        assert response.json["score"] is None


@pytest.mark.parametrize("positive, risk, cost, expected", [(0, 0, 0, 0), (1, 0, 0, 90), (1, 1, 1, 80), (0.5, 0.5, 0.5, 40)])
def test_complete_inputs_preserve_existing_weights_and_explicit_zero(topic_client, positive, risk, cost, expected):
    values = {**dict.fromkeys(FIELDS, positive), "risk": risk, "cost": cost}
    response = topic_client.post("/api/podcast/topic-score", json={"signals": values})
    assert response.status_code == 200, response.json
    assert response.json["state"] == "scored"
    assert response.json["score"] == expected
    assert response.json["missing_signals"] == []
    assert response.json["stage"] == topic_scoring.classify_topic(expected, positive)
    assert response.json["signals"] == values


def test_partial_zero_remains_observed_zero_without_imputing_other_fields(topic_client):
    response = topic_client.post("/api/podcast/topic-score", json={"demand": 0})
    assert response.status_code == 200
    assert response.json["signals"]["demand"] == 0
    assert response.json["score"] is None
    assert response.json["missing_signals"] == [field for field in FIELDS if field != "demand"]


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/podcast/overview"),
    ("GET", "/api/podcast/entities"),
    ("GET", "/api/podcast/entity?entity_id=another-scope"),
    ("POST", "/api/podcast/entity"),
])
def test_unrelated_scoped_entity_routes_stay_blocked(topic_client, method, path):
    response = topic_client.open(path, method=method, json={"entity_type": "episode"})
    assert response.status_code == 503
    assert response.json["code"] == "PODCAST_ENTITY_SCOPE_UNAVAILABLE"


def test_blueprint_registration_does_not_initialize_unscoped_store(monkeypatch):
    import sys
    from types import SimpleNamespace

    def forbidden_init():
        pytest.fail("Blueprint registration must not initialize production tables")

    monkeypatch.setitem(sys.modules, "podcast_store", SimpleNamespace(init_db=forbidden_init))
    app = Flask(__name__)
    podcast_routes.register_podcast_api(app)
    assert "/api/podcast/topic-score" in {rule.rule for rule in app.url_map.iter_rules()}


@pytest.mark.parametrize("value", [True, False, math.nan, math.inf, -math.inf, "0", -1])
def test_invalid_classification_does_not_fabricate_a_stage(value):
    with pytest.raises(ValueError):
        topic_scoring.classify_topic(value, 0.5)
    with pytest.raises(ValueError):
        topic_scoring.classify_topic(50, value)


def test_scoring_dependency_error_is_unavailable_without_internal_details(topic_client, monkeypatch):
    def failed(_signals):
        raise RuntimeError("private/internal/location")

    monkeypatch.setattr(topic_scoring, "score_topic", failed)
    response = topic_client.post("/api/podcast/topic-score", json=dict.fromkeys(FIELDS, 0.5))
    assert response.status_code == 503
    assert response.json["state"] == "unavailable"
    assert response.json["score"] is None and response.json["stage"] is None
    assert "private" not in response.get_data(as_text=True)
