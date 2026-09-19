# -*- coding: utf-8 -*-
"""P1-8 ZBC→OSAI 证据导出器测试：只读、只导核准、脱敏、剔除凭证、增量幂等。"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.system.collector.adapters import evidence_exporter as EE  # noqa: E402


def _make_db(path):
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE notes(id INTEGER PRIMARY KEY, note_id TEXT, title TEXT,
        content TEXT, url TEXT, author_id TEXT, author_nickname TEXT, xsec_token TEXT,
        publish_datetime TEXT, captured_at TEXT, sentiment TEXT, risk_level TEXT,
        source_platform TEXT, matched_keywords TEXT, subject_type TEXT,
        is_taikoo_verified INTEGER, negative_confirmed INTEGER)""")
    c.execute("""CREATE TABLE events(id INTEGER PRIMARY KEY, event_key TEXT, title TEXT,
        summary TEXT, fact_status TEXT, risk_level TEXT, mention_count INTEGER,
        source_count INTEGER, first_seen TEXT, last_seen TEXT, status TEXT,
        event_date TEXT, negative_confirmed INTEGER)""")
    c.execute("""CREATE TABLE daily_reports(id INTEGER PRIMARY KEY, report_type TEXT,
        report_date TEXT, period_start TEXT, period_end TEXT, total_notes INTEGER,
        positive_count INTEGER, neutral_count INTEGER, negative_count INTEGER,
        high_risk_count INTEGER, medium_risk_count INTEGER, low_risk_count INTEGER,
        total_engagements INTEGER, summary TEXT, executive_summary TEXT, generated_at TEXT)""")
    # 已核准笔记：正文含手机号/邮箱，url 带 xsec_token，带作者身份字段
    c.execute("""INSERT INTO notes(id,note_id,title,content,url,author_id,author_nickname,
        xsec_token,publish_datetime,captured_at,is_taikoo_verified,source_platform)
        VALUES(1,'n1','方所闭店','联系 13800138000 或 a@b.com 了解',
        'https://x.com/note?xsec_token=SECRET&xsec_source=pc','uid9','昵称','SECRET',
        '2026-08-30','2026-08-31',1,'xhs')""")
    # 未过主体口径：不得导出
    c.execute("INSERT INTO notes(id,note_id,title,content,is_taikoo_verified) VALUES(2,'n2','其他城市同名','无关',0)")
    c.execute("INSERT INTO events(id,event_key,title,summary,fact_status,risk_level,mention_count,source_count) VALUES(1,'e1','闭店事件','s','confirmed','high',5,2)")
    c.execute("INSERT INTO events(id,event_key,title,fact_status) VALUES(2,'e2','未核实','unconfirmed')")
    c.execute("INSERT INTO daily_reports(id,report_type,report_date,total_notes,summary) VALUES(1,'daily','2026-08-30',10,'日报含 13900139000')")
    c.commit()
    c.close()


def test_only_approved_exported_and_redacted(tmp_path):
    db = tmp_path / "t.db"; _make_db(str(db))
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True); conn.row_factory = sqlite3.Row
    recs, wm, redacted = EE.build_export(conn, None)
    conn.close()
    assert [n["id"] for n in recs["notes"]] == [1]          # 未核准的 n2 被排除
    assert [e["id"] for e in recs["events"]] == [1]         # unconfirmed 事件被排除
    assert len(recs["daily_reports"]) == 1
    note = recs["notes"][0]
    assert "author_id" not in note and "author_nickname" not in note and "xsec_token" not in note
    assert note["url"] == "https://x.com/note"              # 凭证 query 被剥离
    assert "13800138000" not in note["content"] and "[REDACTED:phone]" in note["content"]
    assert "[REDACTED:email]" in note["content"]
    assert redacted >= 2


def test_incremental_watermark(tmp_path):
    db = tmp_path / "t.db"; _make_db(str(db))
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True); conn.row_factory = sqlite3.Row
    first, wm1, _ = EE.build_export(conn, None)
    assert wm1["notes"] == 1 and wm1["events"] == 1 and wm1["daily_reports"] == 1
    # 新增一条已核准
    conn.close()
    w = sqlite3.connect(str(db)); w.execute("INSERT INTO notes(id,note_id,title,is_taikoo_verified) VALUES(3,'n3','新',1)"); w.commit(); w.close()
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True); conn.row_factory = sqlite3.Row
    second, wm2, _ = EE.build_export(conn, wm1)
    conn.close()
    assert [n["id"] for n in second["notes"]] == [3]        # 只取增量
    assert wm2["notes"] == 3


def test_export_end_to_end_manifest_and_readonly(tmp_path):
    db = tmp_path / "t.db"; _make_db(str(db))
    before = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    outbox = tmp_path / "outbox"
    man = EE.export_evidence(str(db), str(outbox), version="5.9.9")
    after = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    assert before == after                                 # 源库未被写
    assert man["schema"] == EE.EXPORT_SCHEMA
    assert man["production_unchanged"] is True             # V-06
    assert man["counts"] == {"notes": 1, "events": 1, "daily_reports": 1}
    assert man["total"] == 3
    jsonl = outbox / man["jsonl"]
    assert jsonl.exists()
    import hashlib
    assert man["sha256"] == hashlib.sha256(jsonl.read_bytes()).hexdigest()
    lines = [json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines()]
    assert all("xsec_token" not in ln and "author_id" not in ln for ln in lines)
    # 水位已落盘，二次导出为空增量
    man2 = EE.export_evidence(str(db), str(outbox), version="5.9.9")
    assert man2["total"] == 0
    assert (outbox / "_watermark.json").exists()


def test_safe_identifier():
    """验证 _safe_identifier 拒绝非法SQL标识符。"""
    from lumenis.system.collector.adapters import evidence_exporter as ee
    assert ee._safe_identifier("notes") == "notes"
    assert ee._safe_identifier("daily_reports") == "daily_reports"
    import pytest
    with pytest.raises(ValueError):
        ee._safe_identifier("notes; DROP TABLE x;--")
    with pytest.raises(ValueError):
        ee._safe_identifier("a b")
    with pytest.raises(ValueError):
        ee._safe_identifier("")