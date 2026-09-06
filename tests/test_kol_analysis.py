# -*- coding: utf-8 -*-
"""P1-C KOL/KOC/UGC 分层测试：分类边界 + 聚合（隔离临时库）。"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import kol_analysis as ka  # noqa: E402


def test_classify_kol():
    assert ka.classify_author(20000, 5) == "KOL"
    assert ka.classify_author(10000, 3) == "KOL"


def test_classify_koc():
    assert ka.classify_author(5000, 2) == "KOC"
    assert ka.classify_author(1000, 1) == "KOC"


def test_classify_ugc():
    assert ka.classify_author(500, 1) == "UGC"
    assert ka.classify_author(0, 0) == "UGC"
    # 高互动但笔记不足 -> 降级 KOC
    assert ka.classify_author(20000, 1) == "KOC"


def test_analyze_authors_pure():
    rows = [
        ("a1", "kol_user", 5, 20000),
        ("a2", "koc_user", 2, 5000),
        ("a3", "ugc_user", 1, 100),
    ]
    r = ka.analyze_authors(rows)
    assert r["summary"] == {"KOL": 1, "KOC": 1, "UGC": 1}
    layers = {x["author_id"]: x["layer"] for x in r["authors"]}
    assert layers == {"a1": "KOL", "a2": "KOC", "a3": "UGC"}


@pytest.fixture
def db(tmp_path, monkeypatch):
    import database
    p = tmp_path / "k.db"
    monkeypatch.setattr(database, "DB_PATH", str(p))
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE notes (note_id TEXT PRIMARY KEY, title TEXT, content TEXT, "
                "author_id TEXT DEFAULT '', author_nickname TEXT DEFAULT '', "
                "likes INT DEFAULT 0, comments INT DEFAULT 0, collects INT DEFAULT 0, "
                "shares INT DEFAULT 0, publish_date TEXT DEFAULT '', url TEXT DEFAULT '')")
    rows = [
        ("n1", "a1", "kol1", 8000, 100, 50, 20),
        ("n2", "a1", "kol1", 7000, 80, 40, 10),
        ("n3", "a1", "kol1", 6000, 60, 30, 5),
        ("n4", "a2", "koc2", 1000, 50, 20, 5),
        ("n5", "a2", "koc2", 900, 40, 15, 3),
        ("n6", "a3", "ugc3", 100, 5, 2, 1),
    ]
    for nid, aid, nick, lk, cm, co, sh in rows:
        con.execute("INSERT INTO notes (note_id,author_id,author_nickname,likes,comments,collects,shares) "
                    "VALUES (?,?,?,?,?,?,?)", (nid, aid, nick, lk, cm, co, sh))
    con.commit()
    con.close()
    return p


def test_top_authors_from_db(db, monkeypatch):
    import database
    import sqlite3 as _s
    # monkeypatch get_db 返回临时库连接
    real_get_db = database.get_db

    def fake_get_db():
        c = _s.connect(str(db))
        return c
    monkeypatch.setattr(database, "get_db", fake_get_db)
    r = ka.top_authors(limit=10)
    by_id = {x["author_id"]: x["layer"] for x in r["authors"]}
    # a1: 8150+7140+6095=21385 -> KOL；a2: 1075+958=2033 -> KOC；a3: 108 -> UGC
    assert by_id.get("a1") == "KOL"
    assert by_id.get("a2") == "KOC"
    assert by_id.get("a3") == "UGC"
    assert r["authors"][0]["author_id"] == "a1"  # 按互动降序


def test_chain_structure():
    c = ka.chain()
    for k in ("account", "note", "interaction", "event", "evidence"):
        assert k in c
