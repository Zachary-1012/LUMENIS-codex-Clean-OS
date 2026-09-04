# -*- coding: utf-8 -*-
"""Canonical Business Metrics 单测（FN-SENTIMENT-COUNT / FN-RISK-COUNT / FN-ENGAGEMENT）。

重点：
1) Q1 方案甲：high 桶绝不含 critical，critical 独立。
2) 五态：unknown / missing / other / 空集 / 分母0 不伪装成 0。
3) 真实库一致性：若生产 monitor.db 存在，Canonical 结果必须等于 SQL GROUP BY（迁移零变化证据）。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from canonical_metrics import (  # noqa: E402
    sentiment_count, risk_count, engagement_of, engagement_stats,
    safe_ratio, neg_ratio, pos_ratio, group_count, registry_snapshot,
    _as_int,
)


# ---------- FN-SENTIMENT-COUNT ----------
def test_sentiment_three_values_complete():
    notes = [{"sentiment": "positive"}] * 3 + [{"sentiment": "neutral"}] * 2 + [{"sentiment": "negative"}]
    r = sentiment_count(notes)
    assert r["positive"] == 3 and r["neutral"] == 2 and r["negative"] == 1
    assert r["known"] == 6 and r["total"] == 6 and r["unknown"] == 0
    assert r["quality"]["empty"] is False


def test_sentiment_unknown_isolated_not_merged():
    # None / 空串 / 异常取值 / 缺键 全部进 unknown，不并入任一已知情感
    notes = [{"sentiment": None}, {"sentiment": ""}, {"sentiment": "weird"}, {}, {"sentiment": "positive"}]
    r = sentiment_count(notes)
    assert r["positive"] == 1 and r["unknown"] == 4 and r["total"] == 5 and r["known"] == 1


def test_sentiment_empty_set_is_zero_but_flagged_empty():
    r = sentiment_count([])
    assert r["total"] == 0 and r["positive"] == 0
    assert r["quality"]["empty"] is True  # 空集与 unknown 区分


def test_sentiment_type_error():
    with pytest.raises(TypeError):
        sentiment_count("not-a-list")
    assert sentiment_count(None)["total"] == 0  # None 容错为空


# ---------- FN-RISK-COUNT（方案甲核心）----------
def test_risk_high_excludes_critical():
    notes = [{"risk_level": "high"}] * 2 + [{"risk_level": "critical"}] * 3 + [{"risk_level": "medium"}]
    r = risk_count(notes)
    assert r["high"] == 2          # high 只算 high
    assert r["critical"] == 3      # critical 独立成更高桶
    assert r["medium"] == 1
    # 关键红线：high 绝不等于 high+critical
    assert r["high"] != r["high"] + r["critical"]


def test_risk_other_vs_missing_distinguished():
    notes = [{"risk_level": "low"}, {"risk_level": None}, {"risk_level": ""}, {"risk_level": "bogus"}, {}]
    r = risk_count(notes)
    assert r["low"] == 1
    assert r["missing"] == 3   # None/空串/缺键 = 未采集
    assert r["other"] == 1     # 非空但非枚举 = 无法判定
    assert r["total"] == 5


def test_risk_empty():
    r = risk_count([])
    assert r["total"] == 0 and r["quality"]["empty"] is True


# ---------- FN-ENGAGEMENT ----------
def test_engagement_of_four_fields():
    assert engagement_of({"likes": 1, "comments": 2, "collects": 3, "shares": 4}) == 10
    # 字符串数字 / 浮点可转
    assert engagement_of({"likes": "5", "comments": 1.0, "collects": None, "shares": ""}) == 6


def test_engagement_stats_missing_tracked_not_silent():
    notes = [
        {"likes": 10, "comments": 1, "collects": 2, "shares": 3},   # 完整=16
        {"likes": 5, "comments": None, "collects": 0, "shares": 0}, # 缺1字段=5，记 missing
    ]
    r = engagement_stats(notes)
    assert r["sum"] == 21 and r["count"] == 2 and r["nonzero"] == 2
    assert r["per_field"] == {"likes": 15, "comments": 1, "collects": 2, "shares": 3}
    assert r["quality"]["missing_field_notes"] == 1  # 缺字段不静默
    assert r["avg"] == 10.5


def test_engagement_empty_avg_is_none_not_zero():
    r = engagement_stats([])
    assert r["sum"] == 0 and r["avg"] is None and r["quality"]["empty"] is True


def test_as_int_negative_clamped():
    assert _as_int(-5) == 0 and _as_int("x") == 0 and _as_int("12") == 12


# ---------- 比率 Metric ----------
def test_safe_ratio_zero_whole_returns_none():
    assert safe_ratio(1, 0) is None and safe_ratio(1, None) is None
    assert safe_ratio(1, 4) == 0.25


def test_neg_pos_ratio_exclude_unknown():
    sent = sentiment_count([{"sentiment": "negative"}] * 1 +
                           [{"sentiment": "positive"}] * 8 +
                           [{"sentiment": "neutral"}] * 1 +
                           [{"sentiment": None}] * 5)  # 5 unknown 不进分母
    assert neg_ratio(sent) == 0.1     # 1/10
    assert pos_ratio(sent) == 0.8     # 8/10


# ---------- 维度分组 ----------
def test_group_count_by_dim():
    notes = [{"cat": "A", "sentiment": "negative"},
             {"cat": "A", "sentiment": "positive"},
             {"cat": "B", "sentiment": "positive"}]
    g = group_count(notes, "cat", sentiment_count)
    assert set(g.keys()) == {"A", "B"}
    assert g["A"]["total"] == 2 and g["B"]["positive"] == 1


def test_registry_snapshot_is_copy():
    s1 = registry_snapshot()
    assert {"FN-SENTIMENT-COUNT", "FN-RISK-COUNT", "FN-ENGAGEMENT",
            "MET-NEG-RATIO", "MET-POS-RATIO"} <= set(s1.keys())
    s1["FN-RISK-COUNT"]["version"] = "999"
    assert registry_snapshot()["FN-RISK-COUNT"]["version"] == "1.0"  # 改副本不污染内部


# ---------- 真实生产库一致性（迁移零数字变化证据）----------
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monitor.db")


@pytest.mark.skipif(not os.path.exists(DB), reason="生产 monitor.db 不存在时跳过")
def test_canonical_matches_live_sql():
    import sqlite3
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT sentiment, risk_level, likes, comments, collects, shares FROM notes")]
    conn.close()
    assert rows, "生产 notes 不应为空"

    # 情感：Canonical == SQL GROUP BY
    sql_sent = {r[0]: r[1] for r in __import__("sqlite3").connect(DB).execute(
        "SELECT sentiment, COUNT(*) FROM notes GROUP BY sentiment")}
    sc = sentiment_count(rows)
    assert sc["positive"] == sql_sent.get("positive", 0)
    assert sc["neutral"] == sql_sent.get("neutral", 0)
    assert sc["negative"] == sql_sent.get("negative", 0)

    # 风险：high 只等于 SQL 里 risk_level='high'（不含任何 critical）
    sql_high = __import__("sqlite3").connect(DB).execute(
        "SELECT COUNT(*) FROM notes WHERE risk_level='high'").fetchone()[0]
    rc = risk_count(rows)
    assert rc["high"] == sql_high
    assert rc["critical"] == 0  # 现网无 critical（2026-09 基线）

    # 互动：Canonical sum == SQL 四字段求和
    sql_eng = __import__("sqlite3").connect(DB).execute(
        "SELECT COALESCE(SUM(likes+comments+collects+shares),0) FROM notes").fetchone()[0]
    es = engagement_stats(rows)
    assert es["sum"] == sql_eng
