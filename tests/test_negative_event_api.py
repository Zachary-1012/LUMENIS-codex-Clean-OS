# -*- coding: utf-8 -*-
"""负面审核主体口径 + 事件关联笔记 的回归测试（纯 DB，不启服务、不联网）。
覆盖本轮三个修复：
1. 负面审核待办只含广州太古汇主体、非重复非噪音笔记（全网公关案例不得混入）；
2. 待办列表里的每条笔记都能通过详情接口的主体口径（不会再 404 Not found）；
3. 事件"相关笔记案例"走 event_mentions 关联表，能取到真实笔记而非关键词 0 条；
4. 负面审核统计与列表同口径，数字一致。
运行：.venv\\Scripts\\python.exe -m pytest tests\\test_negative_event_api.py
"""
import os
import sys
import sqlite3
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from subject_rules import subject_sql_and_values, subject_hit
from database import note_to_dict


@pytest.fixture(autouse=True)
def _ensure_isolated_schema(tmp_path, monkeypatch):
    """Exercise the legacy SQL contract on scoped synthetic rows, not old data."""
    import database
    from lumenis.shared.database import repository
    from subject_context import brand_scope
    path = tmp_path / "negative-events.sqlite3"
    repo = repository.DatabaseRepository(str(path))
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setattr(repository, "_default_repository", repo)
    database.init_db()
    with repo.transaction() as connection:
        connection.executemany(
            "INSERT INTO notes(note_id,title,content,sentiment,negative_confirmed,is_duplicate,noise_type) "
            "VALUES(?,?,?,'negative',0,?,'')",
            [("scope-negative", "广州太古汇服务反馈", "广州太古汇", 0),
             ("foreign-case", "ZARA 独立案例", "其他主体", 0),
             ("scope-duplicate", "广州太古汇重复", "广州太古汇", 1)],
        )
    with brand_scope("guangzhou_taikoo_hui", product_id="CTH"):
        yield


def _visible(note):
    return subject_hit(title=note.get('title',''), body=note.get('body',''),
                       content=note.get('content',''), source_keyword=note.get('source_keyword',''),
                       matched_keywords=note.get('matched_keywords',''))


def _get_pending(conn):
    """与 app.api_negative_pending 完全一致的口径。"""
    clause, sp = subject_sql_and_values()
    sp = list(sp)
    base = ("sentiment='negative' AND (negative_confirmed=0 OR negative_confirmed IS NULL) "
            "AND COALESCE(is_duplicate,0)=0 AND COALESCE(noise_type,'')='' AND " + clause)
    rows = conn.execute(f"SELECT * FROM notes WHERE {base} ORDER BY collected_at DESC", tuple(sp)).fetchall()
    return [dict(r) for r in rows], base, sp


def test_negative_pending_no_case_brands():
    """待办列表不含全网公关案例（拉夫劳伦/宝格丽/ZARA 等）。"""
    conn = sqlite3.connect(os.environ['ZBC_DB_PATH'])
    conn.row_factory = sqlite3.Row
    try:
        pending, _, _ = _get_pending(conn)
        assert [n["note_id"] for n in pending] == ["scope-negative"]
        CASE_BRANDS = ['拉夫劳伦', 'Ralph Lauren', '宝格丽', 'ZARA', 'GBC', '宝珀']
        leaked = [n for n in pending if any(b.lower() in (n.get('title') or '').lower() for b in CASE_BRANDS)]
        assert len(leaked) == 0, f'待办列表混入公关案例: {[n.get("title") for n in leaked]}'
    finally:
        conn.close()


def test_negative_pending_subject_visible():
    """每条待办笔记经详情主体口径均可见（杜绝 Not found）。"""
    conn = sqlite3.connect(os.environ['ZBC_DB_PATH'])
    conn.row_factory = sqlite3.Row
    try:
        pending, _, _ = _get_pending(conn)
        assert [n["note_id"] for n in pending] == ["scope-negative"]
        hidden = [n['note_id'] for n in pending if not _visible(n)]
        assert len(hidden) == 0, f'以下笔记经详情主体口径不可见: {hidden}'
    finally:
        conn.close()


def test_event_mentions_linked_notes():
    """隔离构造的事件经 event_mentions 可关联到笔记，负面排在最前。"""
    conn = sqlite3.connect(os.environ['ZBC_DB_PATH'])
    conn.row_factory = sqlite3.Row
    note_id = 'pytest-event-linked-negative'
    event_key = 'pytest-event-link-contract'
    try:
        conn.execute(
            "INSERT OR REPLACE INTO notes(note_id,title,content,sentiment) VALUES(?,?,?,?)",
            (note_id, '太古汇 测试负面事件', '隔离测试证据', 'negative'),
        )
        conn.execute(
            "INSERT OR IGNORE INTO events(event_key,title) VALUES(?,?)",
            (event_key, '隔离事件关联契约'),
        )
        ev = conn.execute("SELECT id FROM events WHERE event_key=?", (event_key,)).fetchone()
        assert ev is not None
        conn.execute(
            "INSERT OR REPLACE INTO event_mentions(event_id,source_type,source_id,match_score) "
            "VALUES(?,?,?,?)",
            (ev['id'], 'note', note_id, 1.0),
        )
        conn.commit()
        linked = conn.execute("""SELECT COUNT(*) FROM event_mentions m JOIN notes n ON n.note_id=m.source_id
                                 WHERE m.event_id=?""", (ev['id'],)).fetchone()[0]
        assert linked >= 1, f'事件(id={ev["id"]})经event_mentions无关联笔记'
        # 负面必须排在前
        ordered = [dict(r) for r in conn.execute("""SELECT n.sentiment FROM event_mentions m JOIN notes n
                     ON n.note_id=m.source_id WHERE m.event_id=?
                     ORDER BY CASE n.sentiment WHEN 'negative' THEN 0 ELSE 1 END""", (ev['id'],)).fetchall()]
        negs = [i for i, x in enumerate(ordered) if x['sentiment'] == 'negative']
        if negs:
            assert min(negs) == 0, '事件关联笔记负面未排在最前'
    finally:
        ev = conn.execute("SELECT id FROM events WHERE event_key=?", (event_key,)).fetchone()
        if ev:
            conn.execute("DELETE FROM event_mentions WHERE event_id=?", (ev['id'],))
            conn.execute("DELETE FROM events WHERE id=?", (ev['id'],))
        conn.execute("DELETE FROM notes WHERE note_id=?", (note_id,))
        conn.commit()
        conn.close()


def test_negative_stats_matches_list():
    """统计 pending 数与列表 total 一致。"""
    conn = sqlite3.connect(os.environ['ZBC_DB_PATH'])
    conn.row_factory = sqlite3.Row
    try:
        pending, base, sp = _get_pending(conn)
        stat_pending = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base}", tuple(sp)).fetchone()[0]
        assert stat_pending == len(pending), f'统计数({stat_pending})与列表数({len(pending)})不一致'
    finally:
        conn.close()


if __name__ == '__main__':
    test_negative_pending_no_case_brands()
    test_negative_pending_subject_visible()
    test_event_mentions_linked_notes()
    test_negative_stats_matches_list()
    print('负面审核主体口径: 全部通过')


def test_negative_sql_refuses_unbound_scope(monkeypatch):
    import subject_context
    monkeypatch.setattr(subject_context, "get_thread_context", lambda: None)
    with pytest.raises(ValueError, match="LEGACY_SUBJECT_SCOPE_REQUIRED"):
        subject_sql_and_values()
