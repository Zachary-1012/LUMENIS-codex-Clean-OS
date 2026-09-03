# -*- coding: utf-8 -*-
"""数据驱动原创创意生成器测试。"""
from scripts.idea_generator import CIRCLE_SYMBOLS, EMOTION_STYLES, generate_ideas, signals_from_db


def test_generate_ideas_structure():
    s = {"topics": ["太古汇", "消费"], "sentiment": "neutral", "negative_rate": 0.1,
         "risk_events": 0, "circle": "Z世代潮人", "hotspot": "世界杯", "volume_notes": 100}
    r = generate_ideas("测试品牌", "美妆", s, n=3)
    assert len(r["ideas"]) == 3
    for idea in r["ideas"]:
        assert idea["big_idea"]
        assert idea["concept"] and idea["why"]
        assert idea["circle"] and idea["circle_symbols"]
        assert idea["timeliness"] and "世界杯" in idea["timeliness"]
        assert idea["virality"]


def test_signals_from_db_real(tmp_path):
    import sqlite3
    db = str(tmp_path / "m.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT, content TEXT, "
              "sentiment TEXT, risk_level TEXT)")
    c.execute("CREATE TABLE events (event_id TEXT PRIMARY KEY, title TEXT, summary TEXT, "
              "risk_level TEXT)")
    c.executemany("INSERT INTO notes (title,content,sentiment,risk_level) VALUES (?,?,?,?)",
                  [("太古汇新店","太古汇新店火爆", "positive", "low"),
                   ("太古汇投诉","消费者投诉服务", "negative", "high"),
                   ("太古汇活动","周年庆活动", "neutral", "low")])
    c.commit(); c.close()
    s = signals_from_db(db, "太古汇", "Z世代潮人", "618")
    assert s["topics"] and s["circle"] == "Z世代潮人"
    assert s["hotspot"] == "618" and s["volume_notes"] == 3
    assert s["sentiment"] in EMOTION_STYLES


def test_sentiment_changes_style():
    s_pos = {"topics": ["新品"], "sentiment": "positive", "negative_rate": 0.0, "risk_events": 0,
             "circle": "Z世代潮人", "hotspot": "", "volume_notes": 5}
    s_neg = {"topics": ["新品"], "sentiment": "negative", "negative_rate": 0.5, "risk_events": 2,
             "circle": "Z世代潮人", "hotspot": "", "volume_notes": 5}
    a = generate_ideas("X", "快消", s_pos, 1)["ideas"][0]
    b = generate_ideas("X", "快消", s_neg, 1)["ideas"][0]
    assert a["mechanism"] != b["mechanism"]
    assert "危机共情" in b["why"] or "负面" in b["why"]


def test_all_circles_symbols():
    for c in CIRCLE_SYMBOLS:
        s = {"topics": ["话题"], "sentiment": "neutral", "negative_rate": 0.0, "risk_events": 0,
             "circle": c, "hotspot": "", "volume_notes": 3}
        r = generate_ideas("X", "通用", s, 1)
        assert r["ideas"][0]["circle_symbols"]
