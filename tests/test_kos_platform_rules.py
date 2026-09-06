# -*- coding: utf-8 -*-
"""
KOS 平台规则化测试（P0 红线：禁止固定公式）
==============================================
验证：
1. 各平台规则独立存在且可配置
2. 计算函数从规则配置读取参数，无硬编码系数
3. 修改规则后计算结果相应变化
4. 未知平台回退到默认规则
5. config/kos_platform_rules.json 与内置默认规则结构一致

运行: .venv\\Scripts\\python.exe -m pytest tests/test_kos_platform_rules.py -v
"""
import os
import sys
import json
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from kos_metrics import (
    PLATFORM_RULES, load_platform_rules, reload_platform_rules,
    get_platform_rule, platform_engagement, platform_kos_score, platform_ad_score,
    PLATFORM_RULES_PATH, _DEFAULT_PLATFORM_RULES,
)


class TestPlatformRulesExist:
    """验证各平台规则独立存在。"""

    def test_five_platforms_exist(self):
        """五个平台（xiaohongshu/douyin/weibo/bilibili/zhihu）均有规则。"""
        for p in ("xiaohongshu", "douyin", "weibo", "bilibili", "zhihu"):
            assert p in PLATFORM_RULES, f"平台 {p} 缺少规则配置"

    def test_each_platform_has_engagement_weights(self):
        """每个平台都有 engagement_weights 且包含四个互动维度。"""
        for p, rule in PLATFORM_RULES.items():
            assert "engagement_weights" in rule, f"{p} 缺少 engagement_weights"
            w = rule["engagement_weights"]
            for key in ("likes", "comments", "collects", "shares"):
                assert key in w, f"{p} 的 engagement_weights 缺少 {key}"
                assert isinstance(w[key], (int, float)), f"{p}.{key} 不是数值"

    def test_each_platform_has_influence_config(self):
        """每个平台都有 influence 配置。"""
        for p, rule in PLATFORM_RULES.items():
            assert "influence" in rule, f"{p} 缺少 influence"
            inf = rule["influence"]
            for key in ("engagement_coeff", "engagement_max", "volume_coeff",
                        "volume_max", "brand_relevance_coeff", "quality_coeff",
                        "quality_max", "risk_penalty_coeff"):
                assert key in inf, f"{p}.influence 缺少 {key}"

    def test_each_platform_has_score_config(self):
        """每个平台都有 score 配置（min/max/round_digits）。"""
        for p, rule in PLATFORM_RULES.items():
            assert "score" in rule, f"{p} 缺少 score"
            sc = rule["score"]
            assert "min" in sc and "max" in sc and "round_digits" in sc

    def test_each_platform_has_ad_candidate_config(self):
        """每个平台都有 ad_candidate 配置。"""
        for p, rule in PLATFORM_RULES.items():
            assert "ad_candidate" in rule, f"{p} 缺少 ad_candidate"

    def test_platform_rules_independent(self):
        """各平台规则相互独立，修改一个不影响其他。"""
        original = copy.deepcopy(PLATFORM_RULES)
        # 修改 xiaohongshu 的权重
        PLATFORM_RULES["xiaohongshu"]["engagement_weights"]["comments"] = 99.0
        # 验证其他平台不受影响
        assert PLATFORM_RULES["douyin"]["engagement_weights"]["comments"] != 99.0
        assert PLATFORM_RULES["weibo"]["engagement_weights"]["comments"] != 99.0
        # 恢复
        PLATFORM_RULES["xiaohongshu"]["engagement_weights"]["comments"] = (
            original["xiaohongshu"]["engagement_weights"]["comments"]
        )


class TestPlatformEngagement:
    """验证 platform_engagement 从规则读取权重。"""

    def test_xiaohongshu_weights(self):
        """小红书：likes*1 + comments*2 + collects*1.5 + shares*2。"""
        result = platform_engagement("xiaohongshu", 10, 5, 4, 2)
        expected = 10 * 1.0 + 5 * 2.0 + 4 * 1.5 + 2 * 2.0  # 10+10+6+4=30
        assert abs(result - expected) < 0.01

    def test_douyin_weights(self):
        """抖音：shares 权重 3.0（高于小红书）。"""
        result = platform_engagement("douyin", 0, 0, 0, 10)
        assert abs(result - 30.0) < 0.01  # 10 * 3.0

    def test_zhihu_weights(self):
        """知乎：collects 权重 2.5（最高）。"""
        result = platform_engagement("zhihu", 0, 0, 10, 0)
        assert abs(result - 25.0) < 0.01  # 10 * 2.5

    def test_different_platforms_different_results(self):
        """相同输入在不同平台应得到不同结果（规则独立）。"""
        args = (100, 50, 30, 20)
        results = {p: platform_engagement(p, *args) for p in PLATFORM_RULES}
        # 至少有两个平台结果不同
        unique_values = set(round(v, 2) for v in results.values())
        assert len(unique_values) > 1, "所有平台互动量结果相同，规则未生效"

    def test_zero_input(self):
        """全零输入返回 0。"""
        assert platform_engagement("xiaohongshu", 0, 0, 0, 0) == 0.0

    def test_none_input_treated_as_zero(self):
        """None 输入按 0 处理（不崩溃）。"""
        result = platform_engagement("xiaohongshu", None, None, None, None)
        assert result == 0.0


class TestPlatformKosScore:
    """验证 platform_kos_score 从规则读取所有系数。"""

    def test_returns_dict_with_all_components(self):
        """返回完整的得分分解。"""
        result = platform_kos_score(
            "xiaohongshu", engagement=1000, note_count=10,
            subject_type="kos", content_quality=0.8,
            risk_count=0, negative_count=0,
        )
        for key in ("score", "engagement_score", "volume_score", "brand_relevance",
                     "quality_score", "risk_penalty", "platform", "rule_label"):
            assert key in result, f"缺少 {key}"

    def test_score_within_bounds(self):
        """得分在 [0, 100] 范围内。"""
        result = platform_kos_score(
            "xiaohongshu", engagement=1000000, note_count=1000,
            subject_type="kos", content_quality=1.0,
            risk_count=0, negative_count=0,
        )
        assert 0 <= result["score"] <= 100

    def test_risk_penalty_reduces_score(self):
        """风险/负面计数会降低得分。"""
        no_risk = platform_kos_score(
            "xiaohongshu", engagement=500, note_count=5,
            subject_type="kos", content_quality=0.5,
            risk_count=0, negative_count=0,
        )
        with_risk = platform_kos_score(
            "xiaohongshu", engagement=500, note_count=5,
            subject_type="kos", content_quality=0.5,
            risk_count=5, negative_count=3,
        )
        assert with_risk["score"] < no_risk["score"]

    def test_subject_type_affects_brand_relevance(self):
        """不同 subject_type 有不同品牌相关度基础分。"""
        kos_result = platform_kos_score(
            "xiaohongshu", engagement=100, note_count=1,
            subject_type="kos", content_quality=0,
        )
        normal_result = platform_kos_score(
            "xiaohongshu", engagement=100, note_count=1,
            subject_type="normal_user", content_quality=0,
        )
        assert kos_result["brand_relevance"] > normal_result["brand_relevance"]

    def test_platform_rules_affect_score(self):
        """修改平台规则后得分相应变化（证明无硬编码）。"""
        original = copy.deepcopy(PLATFORM_RULES)
        try:
            # 使用较小 engagement，确保未达到 engagement_max 上限
            base = platform_kos_score(
                "xiaohongshu", engagement=50, note_count=3,
                subject_type="kos", content_quality=0.5,
            )
            # 大幅提高 engagement_coeff
            PLATFORM_RULES["xiaohongshu"]["influence"]["engagement_coeff"] = 50.0
            modified = platform_kos_score(
                "xiaohongshu", engagement=50, note_count=3,
                subject_type="kos", content_quality=0.5,
            )
            assert modified["engagement_score"] > base["engagement_score"], \
                "修改规则后 engagement_score 未变化，可能存在硬编码"
        finally:
            PLATFORM_RULES["xiaohongshu"]["influence"]["engagement_coeff"] = (
                original["xiaohongshu"]["influence"]["engagement_coeff"]
            )


class TestPlatformAdScore:
    """验证 platform_ad_score 从规则读取系数。"""

    def test_returns_dict(self):
        result = platform_ad_score(
            "xiaohongshu", engagement=500, likes=100,
            comments=20, collects=15, quality=0.7,
        )
        for key in ("ad_score", "natural_score", "interaction_quality",
                     "quality_score", "risk_penalty", "platform"):
            assert key in result

    def test_risk_reduces_ad_score(self):
        no_risk = platform_ad_score(
            "xiaohongshu", engagement=500, likes=100,
            comments=20, collects=15, quality=0.7,
            is_risk=False, is_negative=False,
        )
        with_risk = platform_ad_score(
            "xiaohongshu", engagement=500, likes=100,
            comments=20, collects=15, quality=0.7,
            is_risk=True, is_negative=True,
        )
        assert with_risk["ad_score"] < no_risk["ad_score"]

    def test_ad_score_within_0_100(self):
        result = platform_ad_score(
            "xiaohongshu", engagement=1000000, likes=100000,
            comments=50000, collects=30000, quality=1.0,
        )
        assert 0 <= result["ad_score"] <= 100


class TestUnknownPlatformFallback:
    """验证未知平台回退到默认规则。"""

    def test_unknown_platform_returns_fallback(self):
        rule = get_platform_rule("nonexistent_platform_xyz")
        assert rule is not None
        assert "engagement_weights" in rule

    def test_unknown_platform_engagement_works(self):
        result = platform_engagement("unknown_platform", 10, 5, 4, 2)
        assert isinstance(result, float)
        assert result > 0


class TestJsonConfigConsistency:
    """验证 config/kos_platform_rules.json 与代码结构一致。"""

    def test_json_file_exists(self):
        assert PLATFORM_RULES_PATH.exists(), "config/kos_platform_rules.json 不存在"

    def test_json_loads_five_platforms(self):
        data = json.loads(PLATFORM_RULES_PATH.read_text(encoding="utf-8"))
        platforms = {k for k in data if not k.startswith("_")}
        assert {"xiaohongshu", "douyin", "weibo", "bilibili", "zhihu"}.issubset(platforms)

    def test_no_hardcoded_coefficients_in_source(self):
        """静态检查：kos_engine.py 中不再有硬编码的互动权重公式。"""
        import inspect
        import kos_engine
        source = inspect.getsource(kos_engine)
        # 检查不再有 `tc * 2` 或 `tcol * 1.5` 等硬编码模式
        # （允许出现在注释中）
        lines = source.split("\n")
        code_lines = [l for l in lines if not l.strip().startswith("#")]
        code = "\n".join(code_lines)
        # 旧的硬编码模式不应再出现在可执行代码中
        assert "tc * 2" not in code, "kos_engine.py 仍有硬编码 tc * 2"
        assert "tcol * 1.5" not in code, "kos_engine.py 仍有硬编码 tcol * 1.5"
        assert "ts * 2" not in code, "kos_engine.py 仍有硬编码 ts * 2"


class TestReloadRules:
    """验证规则热加载。"""

    def test_reload_returns_dict(self):
        result = reload_platform_rules()
        assert isinstance(result, dict)
        assert "xiaohongshu" in result
