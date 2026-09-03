# -*- coding: utf-8 -*-
"""品牌诊断工具测试（定位框架×舆情数据，只读）。"""
import sqlite3

from scripts.brand_insight import diagnose, fetch_related


def _mkdb(tmp_path):
    db = str(tmp_path / "b.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT, content TEXT, "
              "sentiment TEXT, risk_level TEXT, publish_date TEXT)")
    c.execute("CREATE TABLE events (event_id TEXT PRIMARY KEY, title TEXT, summary TEXT, "
              "risk_level TEXT, first_seen TEXT, last_seen TEXT)")
    c.executemany(
        "INSERT INTO notes (title, content, sentiment, risk_level, publish_date) VALUES (?,?,?,?,?)",
        [
            ("太古汇新店开业", "太古汇新店开业人气火爆", "positive", "low", "2026-09-01"),
            ("太古汇某品牌投诉", "消费者投诉太古汇某品牌服务", "negative", "high", "2026-09-02"),
            ("太古汇周年庆", "太古汇周年庆活动反馈", "neutral", "low", "2026-09-02"),
        ])
    c.execute("INSERT INTO events VALUES ('e1','太古汇投诉事件','太古汇相关投诉集中','high','2026-09-01','2026-09-02')")
    c.commit()
    c.close()
    return db


def test_fetch_related(tmp_path):
    db = _mkdb(tmp_path)
    r = fetch_related(db, "太古汇")
    assert len(r["notes"]) == 3
    assert len(r["events"]) == 1


def test_diagnose_structure(tmp_path):
    db = _mkdb(tmp_path)
    r = diagnose(db, "太古汇")
    assert r["keyword"] == "太古汇"
    assert r["volume"]["notes"] == 3 and r["volume"]["events"] == 1
    assert r["sentiment"]["positive"] == 1 and r["sentiment"]["negative"] == 1
    assert r["negative_rate"] > 0
    assert len(r["topics"]) > 0
    assert len(r["risk_events"]) == 1
    assert len(r["advice"]) >= 1


def test_diagnose_empty(tmp_path):
    db = _mkdb(tmp_path)
    r = diagnose(db, "不存在的品牌XYZ")
    assert r["volume"]["notes"] == 0 and r["volume"]["events"] == 0
    assert any("无该关键词相关记录" in a for a in r["advice"])
