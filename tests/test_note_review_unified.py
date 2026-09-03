# -*- coding: utf-8 -*-
"""
GAP-09 笔记负面评审统一写路径回归测试。
验证 _note_set_review 是唯一写路径：
  1. 4 个 API 入口（/api/negative/* + /api/negative-review/*）共用同一函数；
  2. state=1 确认负面 → notes.negative_confirmed=1；
  3. state=2 驳回 → notes.negative_confirmed=2；
  4. 空 note_id → 返回 400 且 ok=False；
  5. 不存在的 note_id → affected=0（不报错）。
用独立临时库（monkeypatch 注入，pytest 自动恢复），不接触生产/Staging 库。
运行：.venv\\Scripts\\python.exe -m pytest tests/test_note_review_unified.py -q
"""
import os
import sys
import sqlite3
import tempfile

import pytest

# 让项目根可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_mod  # noqa: E402


@pytest.fixture()
def tmp_db(monkeypatch):
    """临时 sqlite 库 + monkeypatch db.DB_PATH，pytest 自动恢复"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE notes (
            note_id TEXT PRIMARY KEY,
            title TEXT,
            sentiment TEXT,
            negative_confirmed INTEGER DEFAULT 0,
            negative_confirmed_at TEXT,
            negative_confirmed_by TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO notes (note_id, title, sentiment, negative_confirmed) VALUES (?,?,?,?)",
        ("N1", "负面测试", "negative", 0),
    )
    conn.execute(
        "INSERT INTO notes (note_id, title, sentiment, negative_confirmed) VALUES (?,?,?,?)",
        ("N2", "负面测试2", "negative", 0),
    )
    conn.commit()
    conn.close()
    # 让 app.db.DB_PATH 指向临时库（_note_set_review 用 db.DB_PATH）
    monkeypatch.setattr(app_mod.db, "DB_PATH", path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def _get_state(path, note_id):
    conn = sqlite3.connect(path)
    row = conn.execute("SELECT negative_confirmed, negative_confirmed_by FROM notes WHERE note_id=?", (note_id,)).fetchone()
    conn.close()
    return row


def test_confirm_sets_state_1(tmp_db):
    resp, status, _ = app_mod._note_set_review("N1", 1)
    assert status == 200
    assert resp["ok"] is True
    assert resp["affected"] == 1
    state, by = _get_state(tmp_db, "N1")
    assert state == 1
    assert by == "admin"
    assert resp["note_id"] == "N1"


def test_reject_sets_state_2(tmp_db):
    resp, status, _ = app_mod._note_set_review("N2", 2)
    assert status == 200
    assert resp["ok"] is True
    assert resp["affected"] == 1
    state, _ = _get_state(tmp_db, "N2")
    assert state == 2


def test_empty_note_id_returns_400(tmp_db):
    resp, status, _ = app_mod._note_set_review("", 1)
    assert status == 400
    assert resp["ok"] is False


def test_missing_note_affected_zero(tmp_db):
    resp, status, _ = app_mod._note_set_review("NOT_EXIST", 1)
    assert status == 200
    assert resp["ok"] is True
    assert resp["affected"] == 0


def test_four_endpoints_share_same_function():
    """4 个 API 入口函数都调用 _note_set_review（唯一写路径），防止回归出分叉实现"""
    assert app_mod.api_negative_confirm.__code__.co_names.__contains__("_note_set_review")
    assert app_mod.api_negative_reject.__code__.co_names.__contains__("_note_set_review")
    assert app_mod.api_negative_review_confirm.__code__.co_names.__contains__("_note_set_review")
    assert app_mod.api_negative_review_reject.__code__.co_names.__contains__("_note_set_review")
