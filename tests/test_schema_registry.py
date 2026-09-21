# -*- coding: utf-8 -*-
"""P1-5 单一权威 Schema 源测试：反射只读、声明来源、无主表锁定、红线时间列。"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import schema_registry as sr  # noqa: E402


def test_reflect_readonly_and_structure(tmp_path):
    db = tmp_path / "t.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, publish_datetime TEXT, captured_at TEXT)")
    con.execute("CREATE INDEX idx_note_time ON notes(publish_datetime)")
    con.execute("INSERT INTO notes VALUES (1,'2026-09-01','2026-09-02')")
    con.commit(); con.close()

    refl = sr.reflect(str(db))
    assert set(refl) == {"notes"}
    names = [c["name"] for c in refl["notes"]["columns"]]
    assert names == ["id", "publish_datetime", "captured_at"]
    assert refl["notes"]["row_count"] == 1 and len(refl["notes"]["indexes"]) == 1


def test_reflect_opens_readonly(tmp_path):
    db = tmp_path / "ro.db"
    con = sqlite3.connect(db); con.execute("CREATE TABLE a (id INT)"); con.commit(); con.close()
    refl = sr.reflect(str(db))  # 能 ro 读
    assert "a" in refl


def test_declared_sources_finds_core_tables():
    srcs = sr.declared_sources(ROOT)
    assert "notes" in srcs
    assert "lumenis/shared/database/business_schema.py" in srcs["notes"]
    assert "database.py" not in srcs["notes"]


def test_classify_states():
    srcs = {"notes": ["database.py"]}
    assert sr.classify("notes", srcs)[0] == "DECLARED"
    assert sr.classify("industry_stats", srcs)[0] == "LEGACY_NO_DECL"
    assert sr.classify("bi_brand_entity", srcs)[0] == "MIGRATION_ISOLATED"
    assert sr.classify("mystery_table", srcs)[0] == "MISSING_SOURCE"


def test_generated_registry_has_no_missing_source_and_redline_cols():
    reg = os.path.join(ROOT, "docs", "DATABASE-SCHEMA-REGISTRY.md")
    assert os.path.exists(reg)
    txt = open(reg, encoding="utf-8").read()
    assert "无主未登记：**0**" in txt
    assert "`notes`" in txt
    assert "`notes.publish_datetime`: 存在" in txt
    assert "`notes.captured_at`: 存在" in txt
    # 表格行里不允许出现 MISSING_SOURCE 状态
    for line in txt.splitlines():
        if line.startswith("| ") and "MISSING_SOURCE" in line:
            raise AssertionError(f"存在无主表未登记: {line}")
    # industry_stats 必须被明确标注为遗留
    assert "industry_stats" in txt and "LEGACY_NO_DECL" in txt
