"""P5 regression: one production DB authority and call-time test isolation."""
import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from lumenis.shared.database import DEFAULT_DB_PATH, main_db_path

SPECIALIZED_ENV = [
    "ZBC_EVIDENCE_DB_PATH",
    "ZBC_RUNTIME_GUARDIAN_DB",
    "ZBC_TOKEN_DB_PATH",
]

@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    isolated_path = os.path.abspath(str(tmp_path / "iso_monitor.db"))
    monkeypatch.setenv("ZBC_DB_PATH", isolated_path)
    for key in SPECIALIZED_ENV:
        monkeypatch.delenv(key, raising=False)
    return isolated_path

def _norm(path):
    return os.path.normcase(os.path.abspath(path))

def _open_file(conn):
    return conn.execute("PRAGMA database_list").fetchone()[2]

def _file_fingerprint(path):
    target = Path(path)
    if not target.exists():
        return False, None, None, None
    stat = target.stat()
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return True, stat.st_size, stat.st_mtime_ns, digest.hexdigest()

def _production_db_fingerprint():
    return {
        suffix or "main": _file_fingerprint(str(DEFAULT_DB_PATH) + suffix)
        for suffix in ("", "-wal", "-shm")
    }

def test_default_path_unchanged_when_no_env(iso_db, monkeypatch):
    expected = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monitor.db")
    with monkeypatch.context() as default_path_env:
        default_path_env.delenv("ZBC_DB_PATH", raising=False)
        assert _norm(main_db_path()) == _norm(expected)
        assert _norm(DEFAULT_DB_PATH) == _norm(expected)
    assert _norm(main_db_path()) == _norm(iso_db)

def test_single_canonical_env_redirects_every_domain(iso_db, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    assert _norm(main_db_path()) == _norm(iso_db)

def test_specialized_envs_cannot_split_production_truth(iso_db, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    import db_paths
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", iso_db.replace("iso_monitor.db", "evidence.db"))
    monkeypatch.setenv("ZBC_RUNTIME_GUARDIAN_DB", iso_db.replace("iso_monitor.db", "guardian.db"))
    monkeypatch.setenv("ZBC_TOKEN_DB_PATH", iso_db.replace("iso_monitor.db", "token.db"))
    assert _norm(db_paths.evidence_db_path()) == _norm(iso_db)
    assert _norm(db_paths.guardian_db_path()) == _norm(iso_db)
    assert _norm(db_paths.token_db_path()) == _norm(iso_db)

def test_scheduler_store_uses_single_canonical_env(iso_db, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    import lumenis.system.collector.adapters.scheduling as scheduling
    monkeypatch.setattr(scheduling, "_PLANNER", None)
    planner = scheduling.get_planner()
    assert _norm(planner.store.db_path) == _norm(iso_db)

def test_ui_polling_apis_use_single_canonical_env(iso_db, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    import badge_api
    import data_center_api
    badge_conn = badge_api._get_db()
    data_center_conn = data_center_api._get_db()
    try:
        assert _norm(_open_file(badge_conn)) == _norm(iso_db)
        assert _norm(_open_file(data_center_conn)) == _norm(iso_db)
    finally:
        badge_conn.close()
        data_center_conn.close()

def test_connect_helpers_redirect_at_call_time_even_after_import(iso_db, monkeypatch):
    production_before = _production_db_fingerprint()
    import_db = os.path.join(os.path.dirname(iso_db), "import-time.sqlite3")
    monkeypatch.setenv("ZBC_DB_PATH", import_db)

    import database
    import runtime_guardian
    import intelligence_library_api
    from lumenis.shared.evidence import chain as evidence_chain
    from lumenis.shared.evidence import manual as app_evidence

    assert _norm(import_db) != _norm(iso_db)
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    opened = {}
    conn = database._db_connect_with_retry(); opened["database"] = _open_file(conn); conn.close()
    conn = evidence_chain._get_conn(); opened["evidence_chain"] = _open_file(conn); conn.close()
    conn = runtime_guardian._get_db(); opened["runtime_guardian"] = _open_file(conn); conn.close()
    conn = app_evidence._get_db(); opened["app_evidence"] = _open_file(conn); conn.close()
    conn = intelligence_library_api._get_db(); opened["intelligence_library_api"] = _open_file(conn); conn.close()
    for name, actual in opened.items():
        assert _norm(actual) == _norm(iso_db), f"{name} opened {actual}"
    assert _production_db_fingerprint() == production_before

def test_real_default_db_untouched_under_isolation(iso_db, monkeypatch):
    production_before = _production_db_fingerprint()
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    from lumenis.shared.evidence import chain as evidence_chain
    evidence_chain.EvidenceStore()
    evidence_chain.CanonicalDataStore()
    assert os.path.exists(iso_db)
    assert _production_db_fingerprint() == production_before
