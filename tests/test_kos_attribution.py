# -*- coding: utf-8 -*-
"""KOS 归因模块单元测试（多触点贡献分解）

覆盖：
1. calculate_attribution：单 KOS 多触点归因（内容/互动/传播/事件/品牌/需求/商业/风险）
2. calculate_multi_touch_attribution：多触点归因（时间衰减，不全归最后一个）
3. 边界：无笔记、空 note_ids、笔记不存在
4. 红线：不把最终结果全部归因给最后一个 KOS
"""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import kos_attribution as ka  # noqa: E402


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """创建临时数据库并注入测试数据，monkeypatch DB_PATH。"""
    db_path = tmp_path / "test_monitor.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE notes (
        note_id TEXT PRIMARY KEY,
        author_id TEXT,
        author_nickname TEXT,
        title TEXT,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        collects INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        sentiment TEXT,
        risk_level TEXT,
        content_quality_score REAL,
        publish_datetime TEXT
    )""")
    conn.execute("""CREATE TABLE events (
        id INTEGER PRIMARY KEY,
        keywords TEXT
    )""")
    # KOS A：3 篇笔记，高互动
    for i, (nid, title, likes, comments, collects, shares, sentiment, risk, quality, dt) in enumerate([
        ("n1", "海南中免购物攻略", 500, 100, 200, 50, "positive", "low", 85, "2026-08-01 10:00:00"),
        ("n2", "CDF三亚免税店测评", 300, 80, 150, 30, "positive", "low", 75, "2026-08-15 14:00:00"),
        ("n3", "免税店避雷指南", 100, 50, 30, 10, "negative", "medium", 60, "2026-08-20 09:00:00"),
    ]):
        conn.execute("INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     (nid, "kos_a", "KOS_A", title, likes, comments, collects, shares, sentiment, risk, quality, dt))
    # KOS B：1 篇笔记，低互动
    conn.execute("INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 ("n4", "kos_b", "KOS_B", "随便逛逛", 10, 2, 5, 1, "neutral", "low", 50, "2026-08-10 12:00:00"))
    # 事件关键词
    conn.execute("INSERT INTO events (keywords) VALUES (?)", ("海南,中免,免税,购物节",))
    conn.commit()
    conn.close()
    monkeypatch.setattr(ka, "DB_PATH", db_path)
    return db_path


class TestCalculateAttribution:
    def test_normal_kos_attribution(self, tmp_db):
        """正常 KOS：返回 ok=True，8 维归因分均在 0-100。"""
        r = ka.calculate_attribution("kos_a", brand_name="海南中免")
        assert r["ok"] is True
        assert r["author_id"] == "kos_a"
        assert r["note_count"] == 3
        attr = r["attribution"]
        assert len(attr) == 8
        for k, v in attr.items():
            assert 0 <= v <= 100, f"{k}={v} 超出 0-100"
        assert 0 <= r["total_attribution_score"] <= 100
        # breakdown 为各维度原始分/加权总分，7 项均应 >=0（口径非贡献占比，不强制合计 100）
        assert len(r["breakdown"]) == 7
        for k, v in r["breakdown"].items():
            assert v >= 0, f"{k}={v} 不应为负"

    def test_kos_with_no_notes(self, tmp_db):
        """无笔记的 KOS：返回 ok=False，不报错。"""
        r = ka.calculate_attribution("nonexistent_kos", brand_name="海南中免")
        assert r["ok"] is False
        assert "error" in r

    def test_brand_relevance(self, tmp_db):
        """品牌相关笔记占比应正确计算（3 篇中 2 篇含中免/CDF/海南/免税）。"""
        r = ka.calculate_attribution("kos_a", brand_name="海南中免")
        # n1 含"海南中免"，n2 含"CDF"+"免税"，n3 含"免税" → 3 篇都品牌相关
        assert r["attribution"]["brand"] > 0


class TestMultiTouchAttribution:
    def test_multi_kos_not_last_touch(self, tmp_db):
        """多触点：不全归最后一个 KOS，KOS A 贡献应大于 KOS B。"""
        r = ka.calculate_multi_touch_attribution(["n1", "n2", "n3", "n4"], brand_name="海南中免")
        assert r["ok"] is True
        assert r["total_notes"] == 4
        assert r["total_kos"] == 2
        assert r["method"] == "time_decay_multi_touch (not last-touch)"
        # KOS A 有 3 篇高互动，KOS B 只有 1 篇低互动 → A 贡献应显著大于 B
        contrib = {a["author_id"]: a["attribution_pct"] for a in r["attribution"]}
        assert contrib["kos_a"] > contrib["kos_b"]
        # 最后一个笔记 n3 属于 kos_a，但 n4(kos_b) 在时间最后，不应全归 kos_b
        assert contrib["kos_b"] < 50, "最后一个 KOS 不应占据 >=50% 贡献"

    def test_empty_note_ids(self, tmp_db):
        """空 note_ids：返回 ok=False。"""
        r = ka.calculate_multi_touch_attribution([], brand_name="海南中免")
        assert r["ok"] is False

    def test_notes_not_found(self, tmp_db):
        """笔记不存在：返回 ok=False。"""
        r = ka.calculate_multi_touch_attribution(["nonexistent"], brand_name="海南中免")
        assert r["ok"] is False

    def test_attribution_pct_sum(self, tmp_db):
        """多触点归因百分比合计应约 100。"""
        r = ka.calculate_multi_touch_attribution(["n1", "n4"], brand_name="海南中免")
        total = sum(a["attribution_pct"] for a in r["attribution"])
        assert 99 <= total <= 101, f"归因百分比合计 {total} 异常"
