# -*- coding: utf-8 -*-
"""ZBC Phase 6 — 舆情/风险判断审计测试。

覆盖红线：
1. unknown 不等于 0 或 negative
2. critical 不被降级为 high
3. zero denominator 保护（返回 None，不伪装 0）
4. 主体过滤在风险判断中的应用
5. 风险等级判断逻辑（assess_risk critical 阈值）
6. alert_engine neg_ratio None 处理
7. daily_report calculate_risk_index critical 贡献
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import canonical_metrics as cm  # noqa: E402
from subject_rules import subject_hit, subject_hit_note, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS  # noqa: E402


# ============================================================
# 1. unknown 不等于 0 或 negative
# ============================================================

class TestUnknownNotZeroOrNegative:
    """unknown 情感必须独立计数，不得被当作 0 或 negative。"""

    def test_sentiment_unknown_not_counted_as_negative(self):
        notes = [{"sentiment": "unknown"}, {"sentiment": None}, {"sentiment": ""}, {"sentiment": "weird"}]
        r = cm.sentiment_count(notes)
        assert r["negative"] == 0
        assert r["unknown"] == 4
        assert r["known"] == 0

    def test_sentiment_unknown_not_zero_in_total(self):
        notes = [{"sentiment": "positive"}, {"sentiment": "unknown"}]
        r = cm.sentiment_count(notes)
        assert r["total"] == 2
        assert r["known"] == 1
        assert r["unknown"] == 1

    def test_neg_ratio_excludes_unknown_from_denominator(self):
        """neg_ratio 分母 = known (pos+neu+neg)，不含 unknown。"""
        notes = [{"sentiment": "negative"}, {"sentiment": "unknown"}, {"sentiment": "unknown"}]
        sent = cm.sentiment_count(notes)
        # 1 negative / 1 known = 1.0（unknown 不稀释）
        assert cm.neg_ratio(sent) == 1.0

    def test_neg_ratio_all_unknown_returns_none_not_zero(self):
        """全部 unknown 时分母=0，neg_ratio 返回 None（不可算），绝不返回 0。"""
        notes = [{"sentiment": "unknown"}, {"sentiment": None}]
        sent = cm.sentiment_count(notes)
        assert cm.neg_ratio(sent) is None

    def test_risk_missing_not_counted_as_low(self):
        """risk_level=None/空串 → missing，不得被当作 low。"""
        notes = [{"risk_level": None}, {"risk_level": ""}, {"risk_level": "low"}]
        r = cm.risk_count(notes)
        assert r["low"] == 1
        assert r["missing"] == 2

    def test_risk_other_not_counted_as_known(self):
        """非空未识别 risk_level → other，不得并入 high/medium/low/critical。"""
        notes = [{"risk_level": "extreme"}, {"risk_level": "high"}]
        r = cm.risk_count(notes)
        assert r["high"] == 1
        assert r["other"] == 1
        assert r["critical"] == 0


# ============================================================
# 2. critical 不被降级为 high
# ============================================================

class TestCriticalNotDowngraded:
    """critical 必须独立于 high，不得被合并、忽略或降级。"""

    def test_risk_count_critical_separate_from_high(self):
        notes = [{"risk_level": "critical"}] * 3 + [{"risk_level": "high"}] * 2
        r = cm.risk_count(notes)
        assert r["critical"] == 3
        assert r["high"] == 2
        assert r["high"] != r["high"] + r["critical"]

    def test_critical_not_in_high_bucket(self):
        """high 桶精确匹配 risk_level=='high'，critical 不混入。"""
        notes = [{"risk_level": "critical"}]
        r = cm.risk_count(notes)
        assert r["high"] == 0
        assert r["critical"] == 1

    def test_assess_risk_produces_critical_for_extreme_risk(self):
        """ai_analyzer.assess_risk 对极端风险必须能产出 critical（Phase 6 补齐生产者）。"""
        from ai_analyzer import assess_risk
        level, score = assess_risk(
            "广州太古汇保安打人 顾客受伤 报警 投诉",
            "保安态度恶劣动手打人，顾客受伤已报警，现场多人目击",
            likes=500, comments=200,
        )
        assert level == "critical"
        assert score >= 80

    def test_assess_risk_high_not_critical_for_moderate_risk(self):
        """中等偏高风险应为 high，不得误判 critical。"""
        from ai_analyzer import assess_risk
        level, score = assess_risk(
            "太古汇服务态度差",
            "店员态度不太好，体验一般",
            likes=10, comments=5,
        )
        assert level in ("high", "medium", "low")
        assert level != "critical" or score < 80

    def test_daily_report_risk_index_includes_critical(self):
        """calculate_risk_index 必须将 critical 纳入高风险得分（Phase 6 修复前 critical 贡献为 0）。"""
        from lumenis.shared.reporting.daily import calculate_risk_index
        critical_notes = [
            {"sentiment": "negative", "risk_level": "critical", "likes": 100, "comments": 50,
             "title": "test", "content": "test"},
        ]
        high_notes = [
            {"sentiment": "negative", "risk_level": "high", "likes": 100, "comments": 50,
             "title": "test", "content": "test"},
        ]
        idx_critical = calculate_risk_index(critical_notes, [])
        idx_high = calculate_risk_index(high_notes, [])
        # critical 权重为 high 的 2 倍，因此 critical 笔记的风险指数应高于 high 笔记
        assert idx_critical > idx_high, (
            f"critical 应贡献更高风险指数: critical={idx_critical}, high={idx_high}"
        )


# ============================================================
# 3. zero denominator 保护
# ============================================================

class TestZeroDenominatorProtection:
    """分母为 0 时必须返回 None（不可算），不得返回 0 伪装。"""

    def test_safe_ratio_zero_denominator_returns_none(self):
        assert cm.safe_ratio(1, 0) is None
        assert cm.safe_ratio(0, 0) is None
        assert cm.safe_ratio(5, None) is None

    def test_safe_ratio_normal_division(self):
        assert cm.safe_ratio(1, 4) == 0.25
        assert cm.safe_ratio(3, 3) == 1.0

    def test_neg_ratio_zero_known_returns_none(self):
        sent = {"positive": 0, "neutral": 0, "negative": 0}
        assert cm.neg_ratio(sent) is None

    def test_pos_ratio_zero_known_returns_none(self):
        sent = {"positive": 0, "neutral": 0, "negative": 0}
        assert cm.pos_ratio(sent) is None

    def test_engagement_avg_empty_returns_none(self):
        """空集互动 avg=None，不伪装 0。"""
        r = cm.engagement_stats([])
        assert r["avg"] is None
        assert r["sum"] == 0
        assert r["quality"]["empty"] is True

    def test_alert_engine_neg_ratio_none_no_typeerror(self):
        """alert_engine 在 neg_ratio=None 时不得抛 TypeError，且不得触发负面占比告警。"""
        import alert_engine
        # 全部 unknown 情感 → neg_ratio=None
        notes = [{"sentiment": "unknown"}, {"sentiment": None}]
        # 使用临时 DB 避免污染生产
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tmp_db = tf.name
        old_env = os.environ.get("ZBC_DB_PATH")
        os.environ["ZBC_DB_PATH"] = tmp_db
        try:
            alert_engine.init_alert_tables()
            result = alert_engine.evaluate_alerts(
                notes, risk_index=10.0, brand_health=80.0,
                event_high_count=0, mention_baseline=None,
            )
            # 不应有 neg_ratio 类型的告警（因为不可算）
            neg_alerts = [a for a in result["alerts"] if "neg" in a.get("type", "") or "negative" in a.get("type", "")]
            assert len(neg_alerts) == 0, f"不可算的 neg_ratio 不应触发告警: {neg_alerts}"
        finally:
            if old_env:
                os.environ["ZBC_DB_PATH"] = old_env
            else:
                os.environ.pop("ZBC_DB_PATH", None)
            if os.path.exists(tmp_db):
                os.unlink(tmp_db)


# ============================================================
# 4. 主体过滤在风险判断中的应用
# ============================================================

class TestSubjectFilterInRisk:
    """风险判断必须在主体过滤后执行，非主体内容不得进入风险统计。"""

    def test_subject_hit_guangzhou_taikoo(self):
        assert subject_hit(title="广州太古汇探店", body="今天去太古汇了") is True

    def test_subject_hit_exclude_shanghai(self):
        """上海太古汇必须被排除词一票否决。"""
        assert subject_hit(title="上海太古汇", body="兴业太古汇探店") is False

    def test_subject_hit_exclude_beijing(self):
        assert subject_hit(title="北京三里屯太古汇", body="") is False

    def test_subject_hit_note_dict(self):
        note = {"title": "广州太古汇活动", "body": "", "content": "", "source_keyword": "", "matched_keywords": ""}
        assert subject_hit_note(note) is True

    def test_non_subject_note_excluded_from_risk_count(self):
        """非主体笔记在风险统计前应被过滤，不进入 risk_count。"""
        all_notes = [
            {"title": "广州太古汇投诉", "risk_level": "high", "sentiment": "negative"},
            {"title": "上海太古汇", "risk_level": "high", "sentiment": "negative"},  # 应被排除
            {"title": " unrelated", "risk_level": "low", "sentiment": "neutral"},
        ]
        # 模拟主体过滤后再统计
        subject_notes = [n for n in all_notes if subject_hit(n.get("title", ""), n.get("body", ""))]
        assert len(subject_notes) == 1
        r = cm.risk_count(subject_notes)
        assert r["high"] == 1
        assert r["total"] == 1

    def test_risk_engine_compatibility_layer_delegates_subject_filter(self):
        """根目录 risk_engine.py 的 _subject_sql_and_values 必须委托给 subject_rules。"""
        import risk_engine
        sql, values = risk_engine._subject_sql_and_values()
        assert sql is not None
        assert len(values) > 0
        # 必须包含正向主体词参数（广州太古汇等）
        assert any("太古汇" in v for v in values)


# ============================================================
# 5. 风险等级判断逻辑
# ============================================================

class TestRiskLevelJudgment:
    """ai_analyzer.assess_risk 风险等级判断逻辑验证。"""

    def test_low_risk_for_positive_experience(self):
        from ai_analyzer import assess_risk
        level, score = assess_risk("太古汇探店分享", "环境很好，品牌齐全，推荐大家来", likes=5, comments=1)
        assert level == "low"
        assert score < 15

    def test_medium_risk_for_mild_complaint(self):
        from ai_analyzer import assess_risk
        level, score = assess_risk("太古汇停车不太方便", "停车场入口有点绕，找位花了点时间", likes=10, comments=3)
        assert level in ("low", "medium")

    def test_high_risk_for_security_incident(self):
        from ai_analyzer import assess_risk
        level, score = assess_risk(
            "广州太古汇保安冲突",
            "保安与顾客发生激烈冲突，现场混乱，已有多人拍摄",
            likes=200, comments=80,
        )
        assert level in ("high", "critical")
        assert score >= 40

    def test_critical_requires_high_risk_signals(self):
        """critical 必须同时满足高分和高风险信号，纯互动量不能触发 critical。"""
        from ai_analyzer import assess_risk
        level, score = assess_risk(
            "太古汇网红打卡点",
            "这里拍照很好看，大家快来",
            likes=10000, comments=5000,  # 极高互动但无风险信号
        )
        assert level != "critical", "纯互动量无风险信号不应判 critical"

    def test_unverified_location_capped_at_medium(self):
        """未通过地点验证的笔记 risk_score 被 cap 在 39（中风险上限），不得判 high/critical。"""
        from ai_analyzer import assess_risk
        # 不含广州太古汇地点词的高风险文本
        level, score = assess_risk(
            "保安打人顾客受伤",
            "保安动手打人，顾客受伤报警",
            likes=500, comments=200,
        )
        assert score <= 39, f"未验证地点风险分应被 cap 在 39，实际 {score}"
        assert level in ("low", "medium")


# ============================================================
# 6. canonical_metrics 注册表完整性
# ============================================================

class TestCanonicalRegistry:
    """canonical_metrics 函数注册表必须包含核心指标。"""

    def test_registry_contains_core_functions(self):
        reg = cm.registry_snapshot()
        assert "FN-SENTIMENT-COUNT" in reg
        assert "FN-RISK-COUNT" in reg
        assert "FN-ENGAGEMENT" in reg
        assert "MET-NEG-RATIO" in reg

    def test_risk_count_error_policy_documents_critical_independence(self):
        reg = cm.registry_snapshot()
        policy = reg["FN-RISK-COUNT"]["error_policy"]
        assert "critical" in policy.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
