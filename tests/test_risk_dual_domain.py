# -*- coding: utf-8 -*-
"""
Risk 双域策略测试（ZBC V2.0）
==============================
覆盖：
  1. ZBMP/CTH 阈值独立配置
  2. 同一条数据在两域可能风险等级不同
  3. 风险结果包含 domain_id/product_id
  4. unknown 保持 unknown（不伪造）
  5. critical 独立于 high
  6. 0/0 安全处理
  7. 关键词权重独立
  8. 升级规则独立
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_engine import (
    CTH_RISK_POLICY, ZBMP_RISK_POLICY, DOMAIN_RISK_POLICIES,
    get_risk_policy, compute_domain_risk_score, compare_domain_risk,
    get_risk_policy_summary, evaluate_risk,
)


@pytest.fixture
def isolated_domain_context():
    """Keep policy-selection tests independent of stale request/job context."""
    from domain_isolation import (
        clear_domain_context, get_domain_context, set_domain_context,
    )
    from subject_context import (
        clear_thread_context, get_thread_context, set_thread_context,
    )

    prior_domain = get_domain_context()
    prior_thread = get_thread_context()
    clear_domain_context()
    clear_thread_context()
    yield
    clear_domain_context()
    clear_thread_context()
    if prior_domain is not None:
        set_domain_context(prior_domain)
    if prior_thread is not None:
        set_thread_context(prior_thread)


class TestRiskPolicyDefinitions:
    """验证双域风险策略定义独立。"""

    def test_cth_policy_exists(self):
        assert CTH_RISK_POLICY.domain_id == "cth"
        assert CTH_RISK_POLICY.product_id == "CTH"

    def test_zbmp_policy_exists(self):
        assert ZBMP_RISK_POLICY.domain_id == "zbmp"
        assert ZBMP_RISK_POLICY.product_id == "ZBMP"

    def test_thresholds_are_independent(self):
        """两域的 risk_level 阈值必须不同（不得混成一套）。"""
        assert CTH_RISK_POLICY.risk_thresholds != ZBMP_RISK_POLICY.risk_thresholds

    def test_cth_thresholds_values(self):
        t = CTH_RISK_POLICY.risk_thresholds
        assert t["low"] < t["medium"] < t["high"] < t["critical"]

    def test_zbmp_thresholds_values(self):
        t = ZBMP_RISK_POLICY.risk_thresholds
        assert t["low"] < t["medium"] < t["high"] < t["critical"]

    def test_keyword_weights_independent(self):
        """两域的关键词权重必须不同。"""
        assert CTH_RISK_POLICY.keyword_weights != ZBMP_RISK_POLICY.keyword_weights

    def test_cth_has_specific_keywords(self):
        """CTH 必须有太古汇专项关键词（歧视/KOC集中/舆情扩散等）。"""
        kws = CTH_RISK_POLICY.keyword_weights
        assert "歧视" in kws or "KOC集中" in kws or "舆情扩散" in kws

    def test_zbmp_has_specific_keywords(self):
        """ZBMP 必须有多品牌专项关键词（品牌危机/竞品冲击/传播异常等）。"""
        kws = ZBMP_RISK_POLICY.keyword_weights
        assert "品牌危机" in kws or "竞品冲击" in kws or "传播异常" in kws

    def test_escalation_rules_independent(self):
        """两域的升级规则必须不同。"""
        cth_rules = [r["condition"] for r in CTH_RISK_POLICY.escalation_rules]
        zbmp_rules = [r["condition"] for r in ZBMP_RISK_POLICY.escalation_rules]
        assert cth_rules != zbmp_rules

    def test_risk_dimensions_independent(self):
        assert CTH_RISK_POLICY.risk_dimensions != ZBMP_RISK_POLICY.risk_dimensions


class TestGetRiskPolicy:
    def test_get_cth_policy(self):
        assert get_risk_policy("cth").domain_id == "cth"

    def test_get_zbmp_policy(self):
        assert get_risk_policy("zbmp").domain_id == "zbmp"

    def test_unknown_explicit_domain_is_rejected_without_context_fallback(
        self, isolated_domain_context,
    ):
        from domain_isolation import DomainContext, set_domain_context

        set_domain_context(DomainContext.from_domain("cth"))
        with pytest.raises(ValueError, match="INVALID_DOMAIN_ID"):
            get_risk_policy("nonexistent")
        assert get_risk_policy(None).domain_id == "cth"

    def test_bmp_alias_keeps_canonical_zbmp_policy(self):
        policy = get_risk_policy("BMP")
        assert policy.domain_id == "zbmp"
        assert policy.product_id == "ZBMP"

    def test_system_domain_has_no_business_risk_policy(self):
        with pytest.raises(ValueError, match="RISK_POLICY_UNAVAILABLE_FOR_DOMAIN:system"):
            get_risk_policy("system")

    @pytest.mark.parametrize("domain_id", ["cth", "zbmp"])
    def test_default_uses_bound_domain_context(self, isolated_domain_context, domain_id):
        from domain_isolation import DomainContext, set_domain_context

        set_domain_context(DomainContext.from_domain(domain_id))
        policy = get_risk_policy(None)
        assert policy.domain_id == domain_id

    def test_default_without_context_is_unselected_and_does_not_leak(
        self, isolated_domain_context,
    ):
        from domain_isolation import DomainContext, clear_domain_context, set_domain_context

        with pytest.raises(ValueError, match="DOMAIN_NOT_SELECTED"):
            get_risk_policy(None)

        set_domain_context(DomainContext.from_domain("zbmp"))
        assert get_risk_policy(None).domain_id == "zbmp"
        clear_domain_context()
        with pytest.raises(ValueError, match="DOMAIN_NOT_SELECTED"):
            get_risk_policy(None)


class TestComputeDomainRiskScore:
    """验证域专属风险计算。"""

    def test_cth_discrimination_critical(self):
        """CTH 域中歧视类内容应直接升级到 critical。"""
        result = compute_domain_risk_score(
            text="这家店存在歧视行为，态度恶劣",
            sentiment="negative",
            domain_id="cth",
        )
        assert result["domain_id"] == "cth"
        assert result["product_id"] == "CTH"
        assert result["risk_level"] == "critical"

    def test_zbmp_brand_crisis_critical(self):
        """ZBMP 域中品牌危机应直接升级到 critical。"""
        result = compute_domain_risk_score(
            text="品牌危机爆发，高管丑闻曝光",
            sentiment="negative",
            domain_id="zbmp",
        )
        assert result["domain_id"] == "zbmp"
        assert result["risk_level"] == "critical"

    def test_no_data_returns_unknown(self):
        """无数据时返回 unknown，不伪造为 low。"""
        result = compute_domain_risk_score(text="", sentiment="unknown", domain_id="cth")
        assert result["risk_level"] == "unknown"
        assert result["data_available"] is False
        assert result["risk_score"] is None

    def test_measured_zero_score_is_preserved(self):
        result = compute_domain_risk_score(text="ordinary content", sentiment="neutral", engagement=0, domain_id="cth")
        assert result["data_available"] is True
        assert result["risk_score"] == 0.0

    def test_zero_engagement_safe(self):
        """0 互动量安全处理，不崩溃。"""
        result = compute_domain_risk_score(
            text="普通内容", sentiment="neutral", engagement=0, domain_id="cth"
        )
        assert result["data_available"] is True
        assert result["risk_level"] in ("low", "medium")

    def test_result_contains_domain_identity(self):
        result = compute_domain_risk_score(text="test", domain_id="zbmp")
        assert "domain_id" in result
        assert "product_id" in result
        assert "policy_version" in result
        assert result["domain_id"] == "zbmp"
        assert result["product_id"] == "ZBMP"

    def test_critical_independent_from_high(self):
        """critical 和 high 是独立等级，critical 不被合并为 high。"""
        result = compute_domain_risk_score(
            text="歧视事件曝光，集体维权", sentiment="negative",
            engagement=5000, negative_count=10, domain_id="cth",
        )
        assert result["risk_level"] == "critical"
        assert result["risk_level"] != "high"

    def test_matched_keywords_recorded(self):
        result = compute_domain_risk_score(
            text="投诉维权曝光", domain_id="cth"
        )
        assert len(result["matched_keywords"]) > 0

    def test_escalation_triggered_recorded(self):
        result = compute_domain_risk_score(
            text="歧视行为", sentiment="negative", domain_id="cth"
        )
        assert len(result["escalation_triggered"]) > 0


class TestCompareDomainRisk:
    """验证同一条数据在两域可能风险等级不同。"""

    def test_same_input_different_policies(self):
        """同一条输入使用两域独立策略计算。"""
        comparison = compare_domain_risk(
            text="品牌危机和歧视同时出现",
            sentiment="negative",
            engagement=100,
        )
        assert "cth" in comparison
        assert "zbmp" in comparison
        assert comparison["cth"]["domain_id"] == "cth"
        assert comparison["zbmp"]["domain_id"] == "zbmp"

    def test_thresholds_independent_in_comparison(self):
        comparison = compare_domain_risk(text="test", sentiment="neutral")
        assert comparison["thresholds_independent"] is True

    def test_discrimination_harsher_in_cth(self):
        """歧视类内容在 CTH 域应比 ZBMP 域更严重（CTH 有歧视直接critical规则）。"""
        comparison = compare_domain_risk(
            text="存在歧视行为，消费者投诉",
            sentiment="negative",
        )
        # CTH 有 contains_discrimination -> critical 规则
        assert comparison["cth"]["risk_level"] == "critical"
        # ZBMP 没有歧视直接critical规则（但有品牌危机等），分数可能不同
        assert comparison["cth"]["risk_score"] >= comparison["zbmp"]["risk_score"]

    def test_brand_crisis_harsher_in_zbmp(self):
        """品牌危机在 ZBMP 域应触发 critical。"""
        comparison = compare_domain_risk(
            text="品牌危机，财务造假曝光",
            sentiment="negative",
        )
        assert comparison["zbmp"]["risk_level"] == "critical"


class TestRiskHardConstraints:
    """验证风险硬约束在双域下仍生效。"""

    def test_evaluate_risk_unknown_preserved(self):
        result = evaluate_risk(sentiment=None, risk_level=None)
        assert result["final_risk"] == "unknown"
        assert result["risk_score"] is None

    def test_safe_division_keeps_undefined_ratio_unknown(self):
        from risk_engine import _safe_div
        assert _safe_div(0, 0) is None
        assert _safe_div(0, 5) == 0

    def test_evaluate_risk_critical_independent(self):
        result = evaluate_risk(risk_level="critical")
        assert result["final_risk"] == "critical"
        assert result["risk_level"] == "critical"

    def test_evaluate_risk_safe_div(self):
        result = evaluate_risk(engagement=0)
        assert result["data_available"] is False or result["engagement_available"] is True

    def test_no_critical_equals_high(self):
        """critical 永远不等于 high。"""
        from risk_engine import RISK_LEVELS
        assert "critical" in RISK_LEVELS
        assert "high" in RISK_LEVELS
        assert RISK_LEVELS.index("critical") != RISK_LEVELS.index("high")


class TestRiskPolicySummary:
    def test_summary_structure(self):
        summary = get_risk_policy_summary()
        assert "cth" in summary
        assert "zbmp" in summary
        assert summary["thresholds_independent"] is True
        assert summary["keywords_independent"] is True
        assert len(summary["hard_constraints"]) >= 3
