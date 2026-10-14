from __future__ import annotations

from datetime import datetime

import pytest


class _Cursor:
    def __init__(self):
        self._row = None

    def execute(self, sql, _params=()):
        lowered = sql.lower()
        assert "from notes" not in lowered
        assert "join notes" not in lowered
        if "sqlite_master" in lowered:
            self._row = None
            return self
        raise AssertionError(f"unexpected dashboard SQL: {sql}")

    def fetchone(self):
        return self._row

    def fetchall(self):
        return []


class _Connection:
    row_factory = None

    def __init__(self):
        self._cursor = _Cursor()

    def cursor(self):
        return self._cursor

    def close(self):
        pass


class _Repository:
    def connect(self, **_kwargs):
        return _Connection()


def _note(note_id, *, sentiment, risk_level, risk_score, category="service"):
    today = datetime.now().astimezone().date().isoformat()
    return {
        "note_id": note_id,
        "sentiment": sentiment,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "category": category,
        "likes": 1,
        "comments": 2,
        "collects": 3,
        "shares": 4,
        "collected_at": f"{today} 10:00:00",
        "publish_date": today,
        "negative_confirmed": 0,
        "is_official": 1,
        "title": note_id,
        "url": f"https://example.invalid/{note_id}",
    }


@pytest.fixture
def app_module(app):
    import app as module

    return module


def _mock_dashboard_dependencies(monkeypatch, module, scope, reader):
    seen_scope = []

    def scoped_read(received_scope, *, limit, source_types, date_start=None, date_end=None):
        assert limit == 5000
        assert source_types == ("note",)
        assert (date_start is None) == (date_end is None)
        seen_scope.append(received_scope)
        assert received_scope == scope
        return reader(date_start=date_start, date_end=date_end)

    monkeypatch.setattr(
        module, "_resolve_web_scope",
        lambda action, *, module="reports": ({"actor_id": "actor-1"}, scope, [], None),
    )
    monkeypatch.setattr(module.db, "get_scoped_event_source_rows", scoped_read)
    monkeypatch.setattr(
        module.db, "get_events_curated",
        lambda _limit, *, scope: {"featured": [], "generic_count": 0, "noise_count": 0},
    )
    monkeypatch.setattr(module.db, "get_stats", lambda: pytest.fail("unscoped get_stats was called"))
    monkeypatch.setattr(
        module.db, "get_category_distribution",
        lambda: pytest.fail("unscoped category query was called"),
    )
    monkeypatch.setattr(module, "get_repository", lambda: _Repository())
    return seen_scope


def test_dashboard_aggregates_only_current_scope_canonical_notes(app_module, monkeypatch):
    scope = {
        "domain_id": "cth", "product_id": "CTH", "subject_id": "subject-7",
        "brand_focus_id": None, "global_scope": False,
    }
    rows = [
        _note("n-negative", sentiment="negative", risk_level="high", risk_score=70),
        _note("n-positive", sentiment="positive", risk_level="medium", risk_score=30),
    ]
    seen_scope = _mock_dashboard_dependencies(
        monkeypatch, app_module, scope,
        lambda **_kwargs: {
            "sources": rows, "candidate_count": 2, "rejected_count": 0,
            "truncated": False, "state": "AVAILABLE",
        },
    )

    with app_module.app.test_request_context("/api/dashboard/all"):
        response = app_module.api_dashboard_all()

    payload = response.get_json()
    assert response.status_code == 200
    assert len(seen_scope) == 1  # all business summaries share the same scoped read
    assert payload["notes_coverage"]["state"] == "COMPLETE"
    assert payload["overview"]["total_notes"] == 2
    assert payload["overview"]["verified_notes"] == 2
    assert payload["overview"]["negative_notes"] == 1
    assert payload["stats"]["total"] == 2
    assert payload["stats"]["negative"] == 1
    assert payload["stats"]["categories"] == [{"category": "service", "count": 2}]
    assert payload["risk_alerts"][0]["note_id"] == "n-negative"
    assert payload["pending_negative"] == 1
    assert payload["changes"]["stats"]["total"] == 2
    assert payload["changes"]["scope"] == scope


def test_dashboard_incomplete_canonical_read_does_not_publish_partial_totals(app_module, monkeypatch):
    scope = {
        "domain_id": "cth", "product_id": "CTH", "subject_id": "subject-7",
        "brand_focus_id": None, "global_scope": False,
    }
    row = _note("n-partial", sentiment="negative", risk_level="high", risk_score=90)
    _mock_dashboard_dependencies(
        monkeypatch, app_module, scope,
        lambda **_kwargs: {
            "sources": [row], "candidate_count": 6000, "rejected_count": 0,
            "truncated": True, "state": "TRUNCATED",
        },
    )

    with app_module.app.test_request_context("/api/dashboard/all"):
        response = app_module.api_dashboard_all()

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["notes_coverage"]["state"] == "INCOMPLETE"
    assert payload["overview"]["total_notes"] is None
    assert payload["overview"]["today_notes"] is None
    assert payload["stats"]["negative"] is None
    assert payload["pending_negative"] is None
    assert payload["pending_negative_state"] == "INCOMPLETE"
    assert payload["changes"]["stats"]["total"] is None
    assert payload["hot_topics_state"] == "INCOMPLETE"


def test_dashboard_does_not_turn_unknown_publication_time_into_daily_zero(app_module, monkeypatch):
    scope = {
        "domain_id": "cth", "product_id": "CTH", "subject_id": "subject-7",
        "brand_focus_id": None, "global_scope": False,
    }
    row = _note("n-time-unknown", sentiment="negative", risk_level="high", risk_score=90)
    row["publish_date"] = None
    _mock_dashboard_dependencies(
        monkeypatch, app_module, scope,
        lambda **_kwargs: {
            "sources": [row], "candidate_count": 1, "rejected_count": 0,
            "truncated": False, "state": "AVAILABLE",
        },
    )

    with app_module.app.test_request_context("/api/dashboard/all"):
        response = app_module.api_dashboard_all()

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["overview"]["total_notes"] == 1
    assert payload["overview"]["trend_state"] == "UNKNOWN_PUBLICATION_TIME"
    assert all(point["total"] is None for point in payload["overview"]["trend"])


def test_linked_event_notes_sort_known_highest_risk_before_unknown(app_module, monkeypatch):
    scope = {
        "domain_id": "cth", "product_id": "CTH", "subject_id": "subject-7",
        "brand_focus_id": None, "global_scope": False,
    }
    notes = [
        {"source_type": "note", "note_id": "unknown", "sentiment": "negative",
         "risk_level": "high", "risk_score": None},
        {"source_type": "note", "note_id": "known-15", "sentiment": "negative",
         "risk_level": "high", "risk_score": 15},
        {"source_type": "note", "note_id": "known-80", "sentiment": "negative",
         "risk_level": "critical", "risk_score": 80},
        {"source_type": "note", "note_id": "positive-99", "sentiment": "positive",
         "risk_level": "high", "risk_score": 99},
        {"source_type": "note", "note_id": "negative-low", "sentiment": "negative",
         "risk_level": "low", "risk_score": 5},
    ]
    monkeypatch.setattr(
        app_module, "_resolve_web_scope",
        lambda action, *, module="reports": ({"actor_id": "actor-1"}, scope, [], None),
    )
    monkeypatch.setattr(
        app_module.db, "get_scoped_event",
        lambda _event_id, _scope, include_sources: {"sources": notes} if include_sources else {},
    )

    with app_module.app.test_request_context("/api/events/event-1/notes"):
        response = app_module.api_event_notes("event-1")

    payload = response.get_json()
    assert response.status_code == 200
    assert [item["note_id"] for item in payload["notes"]] == [
        "known-80", "known-15", "unknown", "negative-low", "positive-99",
    ]
