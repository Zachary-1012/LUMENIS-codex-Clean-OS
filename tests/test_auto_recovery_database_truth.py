"""Isolated regressions for the database invariant used by recovery status."""

import sqlite3

import auto_recovery as recovery


def _engine(monkeypatch):
    engine = object.__new__(recovery.AutoRecoveryEngine)
    engine.max_retries = 2
    engine.stats = {
        "total_checks": 0,
        "total_fixes": 0,
        "successful_fixes": 0,
        "failed_fixes": 0,
        "manual_interventions": 0,
        "last_check": None,
        "last_fix": None,
    }
    engine.manual_intervention_modules = []
    engine.log = lambda *_args, **_kwargs: None
    engine.add_alert = lambda *_args, **_kwargs: None
    engine.check_port = lambda **_kwargs: True
    engine.check_cdp = lambda: True
    engine.get_active_alerts = lambda: []
    monkeypatch.setattr(recovery.time, "sleep", lambda _seconds: None)
    return engine


def _create_database(path, *, with_notes=False, broken_notes_view=False):
    conn = sqlite3.connect(path)
    if with_notes:
        conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY)")
        conn.executemany("INSERT INTO notes DEFAULT VALUES", [(), ()])
    elif broken_notes_view:
        conn.execute("CREATE VIEW notes AS SELECT * FROM missing_notes_source")
    conn.commit()
    conn.close()


def test_database_recovery_reports_fixed_only_when_notes_query_passes(tmp_path, monkeypatch):
    db_path = tmp_path / "healthy.sqlite"
    _create_database(db_path, with_notes=True)
    monkeypatch.setattr(recovery, "main_db_path", lambda: str(db_path))
    engine = _engine(monkeypatch)

    assert engine.check_database() == (True, "数据库正常，笔记数: 2")
    status, message = engine.auto_repair({
        "module": "database", "issue": "数据库连接异常", "fixable": True,
    })

    assert status is recovery.FixStatus.FIXED
    assert message == "数据库重连成功"
    assert engine.stats["successful_fixes"] == 1


def test_missing_notes_table_stays_failed_and_cycle_reports_partial(tmp_path, monkeypatch):
    db_path = tmp_path / "missing-notes.sqlite"
    _create_database(db_path)
    monkeypatch.setattr(recovery, "main_db_path", lambda: str(db_path))
    engine = _engine(monkeypatch)

    assert engine.check_database()[0] is False
    result = engine.run_recovery_cycle()

    assert result["status"] == "partial"
    assert result["repair_results"] == [{
        "issue": {"module": "database", "issue": "数据库连接异常", "fixable": True},
        "status": recovery.FixStatus.FAILED.value,
        "message": "数据库重连失败，已重试2次",
    }]
    assert result["final_health"]["needs_fix"] is True
    assert result["final_health"]["issues"][0]["module"] == "database"
    assert engine.stats["successful_fixes"] == 0
    assert engine.stats["failed_fixes"] == 1


def test_notes_query_failure_is_not_mistaken_for_database_connectivity(tmp_path, monkeypatch):
    db_path = tmp_path / "broken-notes-view.sqlite"
    _create_database(db_path, broken_notes_view=True)
    monkeypatch.setattr(recovery, "main_db_path", lambda: str(db_path))
    engine = _engine(monkeypatch)

    healthy, reason = engine.check_database()
    status, message = engine.auto_repair({
        "module": "database", "issue": "数据库连接异常", "fixable": True,
    })

    assert healthy is False
    assert "missing_notes_source" in reason
    assert status is recovery.FixStatus.FAILED
    assert message == "数据库重连失败，已重试2次"
