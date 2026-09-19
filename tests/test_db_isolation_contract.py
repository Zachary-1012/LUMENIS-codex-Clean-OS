"""P5 regression: one production DB authority and call-time test isolation."""
import os
import sqlite3

import pytest

from lumenis.shared.database import DEFAULT_DB_PATH, main_db_path

SPECIALIZED_ENV = [
    "ZBC_EVIDENCE_DB_PATH",
    "ZBC_RUNTIME_GUARDIAN_DB",
    "ZBC_TOKEN_DB_PATH",
]

@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    monkeypatch.delenv("ZBC_DB_PATH", raising=False)
    for key in SPECIALIZED_ENV:
        monkeypatch.delenv(key, raising=False)
    return os.path.abspath(str(tmp_path / "iso_monitor.db"))

def _norm(path):
    return os.path.normcase(os.path.abspath(path))

def _open_file(conn):
    return conn.execute("PRAGMA database_list").fetchone()[2]

def test_default_path_unchanged_when_no_env(iso_db):
    expected = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monitor.db")
    assert _norm(main_db_path()) == _norm(expected)
    assert _norm(DEFAULT_DB_PATH) == _norm(expected)

def test_single_canonical_env_redirects_every_domain(iso_db, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    assert _norm(main_db_path()) == _norm(iso_db)

def test_specialized_envs_cannot_split_production_truth(iso_db, monkeypatch):
    import db_paths
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", iso_db.replace("iso_monitor.db", "evidence.db"))
    monkeypatch.setenv("ZBC_RUNTIME_GUARDIAN_DB", iso_db.replace("iso_monitor.db", "guardian.db"))
    monkeypatch.setenv("ZBC_TOKEN_DB_PATH", iso_db.replace("iso_monitor.db", "token.db"))
    assert _norm(db_paths.evidence_db_path()) == _norm(iso_db)
    assert _norm(db_paths.guardian_db_path()) == _norm(iso_db)
    assert _norm(db_paths.token_db_path()) == _norm(iso_db)

def test_scheduler_store_uses_single_canonical_env(iso_db, monkeypatch):
    import lumenis.system.collector.adapters.scheduling as scheduling
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    monkeypatch.setattr(scheduling, "_PLANNER", None)
    planner = scheduling.get_planner()
    assert _norm(planner.store.db_path) == _norm(iso_db)

def test_ui_polling_apis_use_single_canonical_env(iso_db, monkeypatch):
    import badge_api
    import data_center_api
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    badge_conn = badge_api._get_db()
    data_center_conn = data_center_api._get_db()
    try:
        assert _norm(_open_file(badge_conn)) == _norm(iso_db)
        assert _norm(_open_file(data_center_conn)) == _norm(iso_db)
    finally:
        badge_conn.close()
        data_center_conn.close()

def test_connect_helpers_redirect_at_call_time_even_after_import(iso_db, monkeypatch):
    import database
    import runtime_guardian
    import intelligence_library_api
    from lumenis.shared.evidence import chain as evidence_chain
    from lumenis.shared.evidence import manual as app_evidence

    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    opened = {}
    conn = database._db_connect_with_retry(); opened["database"] = _open_file(conn); conn.close()
    conn = evidence_chain._get_conn(); opened["evidence_chain"] = _open_file(conn); conn.close()
    conn = runtime_guardian._get_db(); opened["runtime_guardian"] = _open_file(conn); conn.close()
    conn = app_evidence._get_db(); opened["app_evidence"] = _open_file(conn); conn.close()
    conn = intelligence_library_api._get_db(); opened["intelligence_library_api"] = _open_file(conn); conn.close()
    for name, actual in opened.items():
        assert _norm(actual) == _norm(iso_db), f"{name} opened {actual}"

def test_real_default_db_untouched_under_isolation(iso_db, monkeypatch):
    from lumenis.shared.evidence import chain as evidence_chain
    existed_before = os.path.exists(DEFAULT_DB_PATH)
    mtime_before = os.path.getmtime(DEFAULT_DB_PATH) if existed_before else None
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    evidence_chain.EvidenceStore()
    evidence_chain.CanonicalDataStore()
    assert os.path.exists(iso_db)
    if existed_before:
        assert os.path.getmtime(DEFAULT_DB_PATH) == mtime_before
    else:
        assert not os.path.exists(DEFAULT_DB_PATH)
