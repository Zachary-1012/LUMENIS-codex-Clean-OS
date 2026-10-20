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


def test_emv_route_rejects_nonfinite_total_from_calculation(monkeypatch):
    import database
    import emv

    monkeypatch.setattr(database, "get_db", _EmptyConnection)
    monkeypatch.setattr(emv, "aggregate_emv", lambda _notes, *, cpm: {
        "status": "SUCCESS", "emv_total_yuan": float("inf"),
    })

    response = _client().get("/api/ic/emv")

    assert response.status_code == 422
    assert response.get_json() == {
        "ok": False,
        "status": "INVALID_INPUT",
        "error": "EMV total must be finite",
        "emv_total_yuan": None,
    }


def test_all_zero_note_without_observation_provenance_is_not_a_zero_amount():
    import emv

    unobserved = emv.aggregate_emv([{"note_id": "a", "likes": 0, "comments": 0, "collects": 0, "shares": 0}])
    assert unobserved["status"] == "NOT_AVAILABLE"
    assert unobserved["emv_total_yuan"] is None
    assert unobserved["complete_coverage"] == 0.0

    observed = emv.aggregate_emv([{
        "note_id": "b", "likes": 0, "comments": 0, "collects": 0, "shares": 0,
        "metrics_observed": True,
    }])
    assert observed["status"] == "OK"
    assert observed["emv_total_yuan"] == 0.0

    detail = emv.aggregate_emv([{
        "note_id": "c", "likes": 0, "comments": 0, "collects": 0, "shares": 0,
        "detail_fetched_at": "2026-10-20 10:00:00",
    }])
    # A generic detail timestamp is not metric-completeness provenance.
    assert detail["status"] == "NOT_AVAILABLE"

    marked = emv.aggregate_emv([{
        "note_id": "d", "likes": 0, "comments": 0, "collects": 0, "shares": 0,
        "metrics_observed_at": "2026-10-20 10:00:00",
    }])
    assert marked["status"] == "OK"


def test_emv_route_reads_observation_provenance_from_real_schema(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    path = tmp_path / "emv.db"
    conn = sqlite3.connect(path)
    apply_business_schema(conn)
    conn.execute("INSERT INTO notes (note_id, likes, comments, collects, shares) VALUES ('z', 0, 0, 0, 0)")
    conn.commit()
    conn.close()

    @contextmanager
    def fixture_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    monkeypatch.setattr(database, "get_db", fixture_db)
    body = _client().get("/api/ic/emv").get_json()
    assert body["status"] == "NOT_AVAILABLE"
    assert body["emv_total_yuan"] is None


def test_emv_route_without_metric_snapshots_table_is_not_an_error(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager
    import database

    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE notes (note_id TEXT, title TEXT, author_nickname TEXT, likes INT, comments INT,"
                 " collects INT, shares INT, sentiment TEXT, publish_date TEXT, captured_at TEXT)")
    conn.execute("INSERT INTO notes VALUES ('l', 't', 'a', 5, 1, 0, 0, 'neutral', '2026-10-01', '2026-10-01')")
    conn.commit()
    conn.close()

    @contextmanager
    def fixture_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    monkeypatch.setattr(database, "get_db", fixture_db)
    response = _client().get("/api/ic/emv")
    assert response.status_code == 200
    # Legacy rows carry no observation provenance: positive counters are PARTIAL.
    assert response.get_json()["status"] == "PARTIAL"


def test_initial_import_of_observed_zero_metrics_keeps_zero_amount(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    path = tmp_path / "import.db"
    conn = sqlite3.connect(path)
    apply_business_schema(conn)
    conn.commit()
    conn.close()

    @contextmanager
    def fixture_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    monkeypatch.setattr(database, "get_db", fixture_db)
    monkeypatch.setenv("ZBC_METRIC_SNAPSHOT", "1")
    database.insert_note({"note_id": "obs0", "title": "t", "likes": 0, "comments": 0,
                          "collects": 0, "shares": 0, "_lumenis_metric_observation_complete": True})
    database.insert_note({"note_id": "synth", "title": "t", "likes": 0, "comments": 0,
                          "collects": 0, "shares": 0})
    database.insert_note({"note_id": "absent", "title": "t"})
    body = _client().get("/api/ic/emv").get_json()
    by_id = {item["note_id"]: item for item in body["items"]}
    assert by_id["obs0"]["status"] == "OK"
    assert by_id["obs0"]["emv_yuan"] == 0
    assert by_id["absent"]["status"] != "OK"
    # Counters materialized without an explicit completeness signal stay unavailable.
    assert by_id["synth"]["status"] == "NOT_AVAILABLE"


def test_initial_import_does_not_create_trend_snapshot(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    path = tmp_path / "snap.db"
    conn = sqlite3.connect(path)
    apply_business_schema(conn)
    conn.commit()
    conn.close()

    @contextmanager
    def fixture_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    monkeypatch.setattr(database, "get_db", fixture_db)
    database.insert_note({"note_id": "n1", "title": "t", "likes": 0, "comments": 0,
                          "collects": 0, "shares": 0, "_lumenis_metric_observation_complete": True})
    c = sqlite3.connect(path)
    assert c.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0] == 0
    assert c.execute("SELECT metrics_observed_at FROM notes WHERE note_id='n1'").fetchone()[0]
    c.close()


def test_platform_aggregate_overflow_is_reported_separately():
    import emv
    notes = [{"note_id": str(i), "likes": 10 ** 306, "comments": 0, "collects": 0, "shares": 0,
              "source_platform": "xhs", "metrics_observed": True} for i in range(1000)]
    r = emv.aggregate_emv_by_platform(notes)
    assert all(item["status"] == "OK" for item in r["items"])
    assert r["status"] == "INVALID_INPUT"
    assert r["invalid_count"] == 0
    assert r["emv_total_yuan"] is None
    assert "platform_calculation" in r["invalid_inputs"] or "calculation" in r["invalid_inputs"]


def test_partial_metric_patch_does_not_certify_stored_zeros(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    path = tmp_path / "partial.db"
    conn = sqlite3.connect(path)
    apply_business_schema(conn)
    conn.execute("INSERT INTO notes (note_id, title, likes, comments, collects, shares) VALUES ('p', 't', 0, 0, 0, 0)")
    conn.commit()
    conn.close()

    @contextmanager
    def fixture_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    monkeypatch.setattr(database, "get_db", fixture_db)
    database.insert_note({"note_id": "p", "title": "t", "likes": 0,
                          "_lumenis_metric_observation_complete": True})
    c = sqlite3.connect(path)
    assert not c.execute("SELECT metrics_observed_at FROM notes WHERE note_id='p'").fetchone()[0]
    c.close()
    item = _client().get("/api/ic/emv").get_json()["items"][0]
    assert item["status"] == "NOT_AVAILABLE"


def _schema_db(monkeypatch, tmp_path, name):
    import sqlite3
    from contextlib import contextmanager
    import database
    from lumenis.shared.database.business_schema import apply_business_schema

    path = tmp_path / name
    conn = sqlite3.connect(path)
    apply_business_schema(conn)
    conn.commit()
    conn.close()

    @contextmanager
    def fixture_db():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    monkeypatch.setattr(database, "get_db", fixture_db)
    return path


def test_uncertified_overwrite_clears_previous_certification(monkeypatch, tmp_path):
    import sqlite3
    import database
    path = _schema_db(monkeypatch, tmp_path, "clear.db")
    database.insert_note({"note_id": "c", "title": "t", "likes": 5, "comments": 1, "collects": 1,
                          "shares": 1, "_lumenis_metric_observation_complete": True})
    database.insert_note({"note_id": "c", "title": "t", "likes": 0, "comments": 0, "collects": 0,
                          "shares": 0})
    c = sqlite3.connect(path)
    assert not c.execute("SELECT metrics_observed_at FROM notes WHERE note_id='c'").fetchone()[0]
    c.close()
    assert _client().get("/api/ic/emv").get_json()["items"][0]["status"] == "NOT_AVAILABLE"


def test_historical_snapshot_alone_is_not_current_provenance(monkeypatch, tmp_path):
    import sqlite3
    path = _schema_db(monkeypatch, tmp_path, "snaphist.db")
    c = sqlite3.connect(path)
    c.execute("INSERT INTO notes (note_id, title, likes, comments, collects, shares) VALUES ('h','t',0,0,0,0)")
    c.execute("INSERT INTO metric_snapshots(entity_type,entity_key,likes,comments,collects,shares,source)"
              " VALUES('note','h',3,0,0,0,'live')")
    c.commit()
    c.close()
    assert _client().get("/api/ic/emv").get_json()["items"][0]["status"] == "NOT_AVAILABLE"


def test_live_collector_completeness_uses_source_fields():
    from lumenis.system.collector.runtime.xhs.live_engine import _source_counters_observed
    assert _source_counters_observed({"likes": 0, "comments": "0", "collects": 0, "shares": 0}) is True
    assert _source_counters_observed({"likes": 0, "comments": 0, "collects": 0}) is False
    assert _source_counters_observed({"likes": "", "comments": 0, "collects": 0, "shares": 0}) is False
    assert _source_counters_observed({"likes": "N/A", "comments": "-", "collects": "0", "shares": "0"}) is False
    assert _source_counters_observed({"likes": float("nan"), "comments": 0, "collects": 0, "shares": 0}) is False
    assert _source_counters_observed({"likes": "1.2万", "comments": "3.5k", "collects": "10w+", "shares": 2}) is True


@pytest.mark.parametrize("query", [
    {"limit": "abc"}, {"limit": "0"}, {"limit": "501"}, {"limit": "-3"},
    {"start": "2026-10-01"}, {"end": "2026-10-01"},
    {"start": "2026-13-01", "end": "2026-10-02"}, {"start": "2026-10-05", "end": "2026-10-01"},
])
def test_emv_route_rejects_invalid_query_before_reading_database(monkeypatch, query):
    import database

    def unexpected_db_access():
        raise AssertionError("invalid query must be rejected before database access")

    monkeypatch.setattr(database, "get_db", unexpected_db_access)
    response = _client().get("/api/ic/emv", query_string=query)
    assert response.status_code == 400
    assert response.get_json()["status"] == "INVALID_INPUT"


def test_emv_route_database_failure_is_unavailable_not_client_error(monkeypatch):
    import database

    def broken_db():
        raise RuntimeError("disk I/O error at /secret/path")

    monkeypatch.setattr(database, "get_db", broken_db)
    response = _client().get("/api/ic/emv")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "SOURCE_UNAVAILABLE"
    assert body["emv_total_yuan"] is None
    assert "secret" not in str(body)


def test_emv_route_capped_read_is_not_reported_complete(monkeypatch, tmp_path):
    import sqlite3
    import database
    path = _schema_db(monkeypatch, tmp_path, "cap.db")
    c = sqlite3.connect(path)
    for i in range(3):
        c.execute("INSERT INTO notes (note_id, title, likes, comments, collects, shares, metrics_observed_at)"
                  " VALUES (?,?,5,1,1,1,'2026-10-20')", (f"n{i}", "t"))
    c.commit()
    c.close()
    body = _client().get("/api/ic/emv", query_string={"limit": "2"}).get_json()
    assert body["note_count"] == 2
    assert body["truncated"] is True and body["source_read_complete"] is False
    assert body["status"] == "PARTIAL"
    full = _client().get("/api/ic/emv", query_string={"limit": "5"}).get_json()
    assert full["truncated"] is False and full["status"] == "OK"


def test_uncertified_positive_counters_are_partial_not_complete():
    import emv
    r = emv.aggregate_emv([{"note_id": "u", "likes": 5, "comments": 0, "collects": 0, "shares": 0}])
    assert r["status"] == "PARTIAL"
    assert r["complete_count"] == 0
    assert "metric_observation_provenance" in r["items"][0]["missing_inputs"]
    certified = emv.aggregate_emv([{"note_id": "c", "likes": 5, "comments": 0, "collects": 0,
                                    "shares": 0, "metrics_observed_at": "2026-10-20"}])
    assert certified["status"] == "OK"
    by_platform = emv.aggregate_emv_by_platform([{"note_id": "u", "likes": 5, "comments": 0,
                                                  "collects": 0, "shares": 0}])
    assert by_platform["complete_count"] == 0


def test_direct_metric_writer_invalidates_provenance(monkeypatch, tmp_path):
    import sqlite3
    path = _schema_db(monkeypatch, tmp_path, "trigger.db")
    c = sqlite3.connect(path)
    c.execute("INSERT INTO notes (note_id, title, likes, comments, collects, shares, metrics_observed_at)"
              " VALUES ('d','t',5,1,1,1,'2026-10-20')")
    c.execute("UPDATE notes SET likes=0, comments=0, collects=0, shares=0 WHERE note_id='d'")
    assert c.execute("SELECT metrics_observed_at FROM notes WHERE note_id='d'").fetchone()[0] == ""
    c.execute("UPDATE notes SET likes=2, metrics_observed_at='2026-10-21' WHERE note_id='d'")
    assert c.execute("SELECT metrics_observed_at FROM notes WHERE note_id='d'").fetchone()[0] == "2026-10-21"
    c.execute("UPDATE notes SET title='x' WHERE note_id='d'")
    assert c.execute("SELECT metrics_observed_at FROM notes WHERE note_id='d'").fetchone()[0] == "2026-10-21"
    c.close()


@pytest.mark.parametrize("bounds", [("2026-10-01garbagexx", "2026-10-02"), ("2026-10-01", "2026-10-02 25:00:00")])
def test_emv_route_rejects_malformed_full_date_value(monkeypatch, bounds):
    import database

    def unexpected_db_access():
        raise AssertionError("malformed dates must be rejected before database access")

    monkeypatch.setattr(database, "get_db", unexpected_db_access)
    response = _client().get("/api/ic/emv", query_string={"start": bounds[0], "end": bounds[1]})
    assert response.status_code == 400


def test_import_boolean_counters_do_not_certify():
    from lumenis.system.collector.adapters.multi_platform_import import _is_observed_counter
    assert _is_observed_counter(0) and _is_observed_counter(3.0)
    assert not _is_observed_counter(False) and not _is_observed_counter(True)
    assert not _is_observed_counter(float("nan")) and not _is_observed_counter(-1)
    assert not _is_observed_counter("5")
