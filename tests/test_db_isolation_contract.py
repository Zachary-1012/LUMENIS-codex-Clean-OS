"""P0-DBISO-01 回归：单一 ZBC_DB_PATH 必须重定向所有写连接。

核心保证：
1. 不设置任何环境变量时，默认路径仍是 <repo>/data/monitor.db（向后兼容，不静默改路径）。
2. 只设置统一的 ZBC_DB_PATH（不设 evidence/guardian/token 专用变量）时，所有模块的
   连接 helper 在**调用时**都解析到隔离库——即使模块在设置环境变量之前就已 import。
3. 各域专用变量（ZBC_EVIDENCE_DB_PATH 等）优先级高于 ZBC_DB_PATH。
4. 隔离运行不会在真实默认库 data/monitor.db 上建表/写入（mtime 不变 / 不被创建）。

本测试只用系统临时目录，不接触任何生产或 Staging 数据库。
"""
import os
import sys
import sqlite3

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

ALL_ENV = [
    "ZBC_DB_PATH",
    "ZBC_EVIDENCE_DB_PATH",
    "ZBC_RUNTIME_GUARDIAN_DB",
    "ZBC_TOKEN_DB_PATH",
]


@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    """清空全部 DB 隔离环境变量，返回临时隔离库路径。"""
    for key in ALL_ENV:
        monkeypatch.delenv(key, raising=False)
    return os.path.abspath(str(tmp_path / "iso_monitor.db"))


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


def _open_file(conn):
    """返回某条 sqlite 连接真正打开的主库文件路径。"""
    return conn.execute("PRAGMA database_list").fetchone()[2]


def test_default_path_unchanged_when_no_env(iso_db):
    import db_paths

    expected = os.path.join(REPO, "data", "monitor.db")
    assert _norm(db_paths.main_db_path()) == _norm(expected)
    assert _norm(db_paths.evidence_db_path()) == _norm(expected)
    assert _norm(db_paths.guardian_db_path()) == _norm(expected)
    assert _norm(db_paths.token_db_path()) == _norm(expected)


def test_single_canonical_env_redirects_every_domain(iso_db, monkeypatch):
    import db_paths

    monkeypatch.setenv("ZBC_DB_PATH", iso_db)  # 只设统一变量，其余故意不设
    assert _norm(db_paths.main_db_path()) == _norm(iso_db)
    assert _norm(db_paths.evidence_db_path()) == _norm(iso_db)
    assert _norm(db_paths.guardian_db_path()) == _norm(iso_db)
    assert _norm(db_paths.token_db_path()) == _norm(iso_db)


def test_scheduler_store_uses_single_canonical_env(iso_db, monkeypatch):
    import platform_adapters.scheduling as scheduling

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


def test_legacy_guardian_helpers_use_single_canonical_env(iso_db, monkeypatch):
    import auto_recovery
    import data_feedback_loop

    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    conn = sqlite3.connect(iso_db)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    feedback = data_feedback_loop.DataFeedbackLoop()
    assert _norm(feedback.db_path) == _norm(iso_db)
    ok, _message = auto_recovery.AutoRecoveryEngine().check_database()
    assert ok is True


def test_domain_specific_env_takes_precedence(iso_db, monkeypatch):
    import db_paths

    evidence_db = iso_db.replace("iso_monitor.db", "evidence_only.db")
    guardian_db = iso_db.replace("iso_monitor.db", "guardian_only.db")
    monkeypatch.setenv("ZBC_DB_PATH", iso_db)
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", evidence_db)
    monkeypatch.setenv("ZBC_RUNTIME_GUARDIAN_DB", guardian_db)

    assert _norm(db_paths.main_db_path()) == _norm(iso_db)
    assert _norm(db_paths.evidence_db_path()) == _norm(evidence_db)
    assert _norm(db_paths.guardian_db_path()) == _norm(guardian_db)


def test_blank_env_value_is_ignored(iso_db, monkeypatch):
    import db_paths

    monkeypatch.setenv("ZBC_DB_PATH", "   ")  # 纯空白视为未设置
    expected = os.path.join(REPO, "data", "monitor.db")
    assert _norm(db_paths.main_db_path()) == _norm(expected)


def test_connect_helpers_redirect_at_call_time_even_after_import(iso_db, monkeypatch):
    # 关键：先在“无环境变量”状态下 import，再设置 ZBC_DB_PATH。
    # call-time 解析必须让随后的每次连接都落到隔离库（这正是本次修复点）。
    import database
    import evidence_chain
    import runtime_guardian
    import app_evidence
    import intelligence_library_api

    monkeypatch.setenv("ZBC_DB_PATH", iso_db)

    opened = {}
    conn = database._db_connect_with_retry()
    opened["database"] = _open_file(conn); conn.close()

    conn = evidence_chain._get_conn()
    opened["evidence_chain"] = _open_file(conn); conn.close()

    conn = runtime_guardian._get_db()
    opened["runtime_guardian"] = _open_file(conn); conn.close()

    conn = app_evidence._get_db()
    opened["app_evidence"] = _open_file(conn); conn.close()

    conn = intelligence_library_api._get_db()
    opened["intelligence_library_api"] = _open_file(conn); conn.close()

    for name, actual in opened.items():
        assert _norm(actual) == _norm(iso_db), f"{name} 未被 ZBC_DB_PATH 重定向: {actual}"


def test_real_default_db_untouched_under_isolation(iso_db, monkeypatch):
    import db_paths
    import evidence_chain

    default_path = db_paths.DEFAULT_DB_PATH
    existed_before = os.path.exists(default_path)
    mtime_before = os.path.getmtime(default_path) if existed_before else None

    monkeypatch.setenv("ZBC_DB_PATH", iso_db)

    # 在隔离库上初始化证据/规范数据存储（会建表）。
    evidence_chain.EvidenceStore()
    evidence_chain.CanonicalDataStore()

    assert os.path.exists(iso_db), "隔离库应当被创建"
    if existed_before:
        assert os.path.getmtime(default_path) == mtime_before, "隔离运行改动了真实默认库"
    else:
        assert not os.path.exists(default_path), "隔离运行不应凭空创建真实默认库"
