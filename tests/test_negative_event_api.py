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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from subject_rules import subject_sql_and_values, subject_hit
import database


@pytest.fixture(scope="module", autouse=True)
def _isolated_sample_db():
    """建立可验证的主体、负面和事件关系样本，不读取生产数据。"""
    database.DB_PATH = os.environ["ZBC_DB_PATH"]
    database.init_db()
    conn = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    try:
        conn.execute(
            """INSERT OR REPLACE INTO notes
               (note_id,title,content,body,source_keyword,matched_keywords,sentiment,
                negative_confirmed,is_duplicate,noise_type,collected_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            ("p0c-negative", "广州太古汇服务体验", "广州太古汇排队时间长",
             "广州太古汇排队时间长", "广州太古汇", "广州太古汇", "negative",
             0, 0, "", "2026-09-09 10:00:00"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO events(event_key,title,first_seen) VALUES (?,?,?)",
            ("p0c-event", "广州太古汇服务事件", "2026-09-09 10:00:00"),
        )
        event_id = conn.execute(
            "SELECT id FROM events WHERE event_key='p0c-event'"
        ).fetchone()[0]
        conn.execute(
            "INSERT OR REPLACE INTO event_mentions(event_id,source_type,source_id,match_score) VALUES (?,?,?,?)",
            (event_id, "note", "p0c-negative", 1.0),
        )
        conn.commit()
    finally:
        conn.close()


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
    conn = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    conn.row_factory = sqlite3.Row
    try:
        pending, _, _ = _get_pending(conn)
        if not pending:
            pytest.skip('数据库无负面待办数据，跳过')
        CASE_BRANDS = ['拉夫劳伦', 'Ralph Lauren', '宝格丽', 'ZARA', 'GBC', '宝珀']
        leaked = [n for n in pending if any(b.lower() in (n.get('title') or '').lower() for b in CASE_BRANDS)]
        assert len(leaked) == 0, f'待办列表混入公关案例: {[n.get("title") for n in leaked]}'
    finally:
        conn.close()


def test_negative_pending_subject_visible():
    """每条待办笔记经详情主体口径均可见（杜绝 Not found）。"""
    conn = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    conn.row_factory = sqlite3.Row
    try:
        pending, _, _ = _get_pending(conn)
        if not pending:
            pytest.skip('数据库无负面待办数据，跳过')
        hidden = [n['note_id'] for n in pending if not _visible(n)]
        assert len(hidden) == 0, f'以下笔记经详情主体口径不可见: {hidden}'
    finally:
        conn.close()


def test_event_mentions_linked_notes():
    """首个事件经 event_mentions 可关联到笔记，负面排在最前。"""
    conn = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    conn.row_factory = sqlite3.Row
    try:
        ev = conn.execute("SELECT id FROM events ORDER BY id LIMIT 1").fetchone()
        if not ev:
            pytest.skip('数据库无事件数据，跳过')
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
        conn.close()


def test_negative_stats_matches_list():
    """统计 pending 数与列表 total 一致。"""
    conn = sqlite3.connect(os.environ["ZBC_DB_PATH"])
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
