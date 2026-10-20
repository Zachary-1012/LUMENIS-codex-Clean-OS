from __future__ import annotations

from flask import Flask
import pytest


class _EmptyCursor:
    def fetchall(self):
        return []


class _EmptyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _sql, _params=()):
        return _EmptyCursor()


class _RowsCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _RowsConnection(_EmptyConnection):
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _sql, _params=()):
        return _RowsCursor(self.rows)


def _client():
    from ic_routes import ic_bp

    app = Flask(__name__)
    app.register_blueprint(ic_bp)
    return app.test_client()


@pytest.mark.parametrize("raw", ["not-a-number", "", "-1", "NaN", "Infinity", "1e309"])
def test_emv_route_rejects_explicit_invalid_cpm_before_reading_database(monkeypatch, raw):
    import database
    import emv

    def unexpected_db_access():
        raise AssertionError("invalid CPM must be rejected before database access")

    def unexpected_aggregate(*_args, **_kwargs):
        raise AssertionError("invalid CPM must be rejected before aggregation")

    monkeypatch.setattr(database, "get_db", unexpected_db_access)
    monkeypatch.setattr(emv, "aggregate_emv", unexpected_aggregate)

    response = _client().get("/api/ic/emv", query_string={"cpm": raw})

    assert response.status_code == 400
    assert response.get_json() == {
        "ok": False,
        "error": "cpm must be a finite non-negative number",
    }


@pytest.mark.parametrize(("query", "expected_cpm"), [({}, None), ({"cpm": "5.5"}, 5.5), ({"cpm": "0"}, 0.0)])
def test_emv_route_preserves_default_and_valid_custom_cpm(monkeypatch, query, expected_cpm):
    import database
    import emv

    aggregate_calls = []

    monkeypatch.setattr(database, "get_db", _EmptyConnection)

    def capture_aggregate(notes, *, cpm):
        aggregate_calls.append((notes, cpm))
        return {"status": "NOT_AVAILABLE", "emv_total_yuan": None}

    monkeypatch.setattr(emv, "aggregate_emv", capture_aggregate)

    response = _client().get("/api/ic/emv", query_string=query)

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert aggregate_calls == [([], expected_cpm)]


def test_emv_route_does_not_report_overflowed_estimate_as_success(monkeypatch):
    import database

    monkeypatch.setattr(database, "get_db", lambda: _RowsConnection([{
        "note_id": "synthetic-overflow", "title": "",
        "author_nickname": "", "likes": 100, "comments": 0,
        "collects": 0, "shares": 0, "sentiment": "neutral",
    }]))

    response = _client().get("/api/ic/emv", query_string={"cpm": "1e308"})

    assert response.status_code == 422
    assert response.get_json()["ok"] is False
    assert response.get_json()["status"] == "INVALID_INPUT"
    assert response.get_json()["emv_total_yuan"] is None
