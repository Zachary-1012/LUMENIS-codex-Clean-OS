# -*- coding: utf-8 -*-
"""IC-039 跨文化本地化守卫 单元测试

验证：
1. 多语言内容检测（中/英/韩）
2. 文化敏感词识别（禁忌库命中）
3. 本地化适配建议框架
4. 品牌名/文化符号跨文化敏感度评分
5. 与 canonical_data.CanonicalRecord 集成（localization_score 字段）
6. 禁止自动改写后直接发布（契约红线）
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


class TestLocalizationCheck:
    """基础检查功能测试。"""

    def test_clean_content_passes(self):
        from localization_guard import check
        result = check("这是一篇正常的产品体验分享，内容真实可信。", lang="zh")
        assert result["hold"] is False
        assert result["blocked"] is False
        assert result["requires_human"] is False
        assert result["label"] == "通过"

    def test_absolute_terms_trigger_hold_zh(self):
        from localization_guard import check
        result = check("这是最好的产品，全国第一，行业领先。", lang="zh")
        assert result["hold"] is True
        assert result["requires_human"] is True
        assert len(result["hits"]) > 0

    def test_absolute_terms_trigger_hold_en(self):
        from localization_guard import check
        result = check("This is the best product, number 1 in the industry.", lang="en")
        assert result["hold"] is True
        assert len(result["hits"]) > 0

    def test_religious_symbol_triggers_block(self):
        from localization_guard import check
        result = check("本产品符合清真认证标准。", lang="zh")
        assert result["blocked"] is True
        assert result["hold"] is True
        assert any(h["level"] == "BLOCK" for h in result["hits"])

    def test_empty_text_returns_clean(self):
        from localization_guard import check
        result = check("", lang="zh")
        assert result["hold"] is False
        assert result["blocked"] is False

    def test_platform_advice_included(self):
        from localization_guard import check
        result = check("测试内容", lang="zh", platform="xiaohongshu")
        assert len(result["platform_advice"]) > 0


class TestMultiLangCheck:
    """多语言检查测试。"""

    def test_check_multi_all_languages(self):
        from localization_guard import check_multi
        result = check_multi("这是最好的产品 the best 최고의 제품")
        assert "zh" in result["results"]
        assert "en" in result["results"]
        assert "ko" in result["results"]
        assert result["hold"] is True

    def test_check_multi_clean_content(self):
        from localization_guard import check_multi
        result = check_multi("正常内容 normal content")
        assert result["hold"] is False
        assert result["blocked"] is False


class TestLocalizationScore:
    """本地化评分功能测试（IC-039 核心）。"""

    def test_clean_content_scores_high(self):
        from localization_guard import score_content
        score = score_content("这是一篇真实的产品体验分享，用户反馈良好。", lang="zh")
        assert score == 1.0

    def test_hold_content_scores_lower(self):
        from localization_guard import score_content
        score = score_content("这是最好的产品，全国第一。", lang="zh")
        assert score is not None
        assert 0.3 <= score < 1.0

    def test_blocked_content_scores_low(self):
        from localization_guard import score_content
        score = score_content("本产品符合清真认证，Allah 保佑。", lang="zh")
        assert score is not None
        assert score < 0.3

    def test_empty_text_returns_none(self):
        from localization_guard import score_content
        score = score_content("", lang="zh")
        assert score is None

    def test_score_multi(self):
        from localization_guard import score_multi
        result = score_multi("这是最好的产品 the best")
        assert "scores" in result
        assert "min_score" in result
        assert "max_score" in result
        assert result["min_score"] is not None
        assert result["min_score"] <= result["max_score"]


class TestCanonicalRecordIntegration:
    """与 canonical_data.CanonicalRecord 集成测试。"""

    def test_record_has_localization_score_field(self):
        from canonical_data import CanonicalRecord
        record = CanonicalRecord()
        assert hasattr(record, "localization_score")
        assert record.localization_score is None  # 默认未评估

    def test_apply_to_record_sets_score(self):
        from localization_guard import apply_to_record
        from canonical_data import CanonicalRecord
        record = CanonicalRecord(title="正常标题", content="正常内容")
        score = apply_to_record(record, lang="zh")
        assert score == 1.0
        assert record.localization_score == 1.0

    def test_apply_to_record_with_hold_content(self):
        from localization_guard import apply_to_record
        from canonical_data import CanonicalRecord
        record = CanonicalRecord(title="最好的产品", content="全国第一")
        score = apply_to_record(record, lang="zh")
        assert score is not None
        assert score < 1.0
        assert record.localization_score == score

    def test_apply_to_record_uses_record_text_when_none(self):
        from localization_guard import apply_to_record
        from canonical_data import CanonicalRecord
        record = CanonicalRecord(title="最好的产品", content="全国第一，行业领先")
        score = apply_to_record(record)  # text=None，自动使用 title+content
        assert score is not None
        assert score < 1.0

    def test_record_to_dict_includes_score(self):
        from canonical_data import CanonicalRecord
        record = CanonicalRecord()
        record.localization_score = 0.85
        d = record.to_dict()
        assert "localization_score" in d
        assert d["localization_score"] == 0.85


class TestLocalizationAdvice:
    """本地化适配建议测试。"""

    def test_get_advice_for_clean_content(self):
        from localization_guard import get_localization_advice
        result = get_localization_advice("正常内容", lang="zh")
        assert result["score"] == 1.0
        assert result["hold"] is False
        assert len(result["suggestions"]) == 0

    def test_get_advice_for_hold_content(self):
        from localization_guard import get_localization_advice
        result = get_localization_advice("最好的产品，全国第一", lang="zh")
        assert result["score"] < 1.0
        assert result["hold"] is True
        assert len(result["suggestions"]) > 0
        assert any("[复核]" in s for s in result["suggestions"])

    def test_get_advice_for_blocked_content(self):
        from localization_guard import get_localization_advice
        result = get_localization_advice("清真认证产品", lang="zh")
        assert result["blocked"] is True
        assert any("[禁止]" in s for s in result["suggestions"])


class TestContractRedLines:
    """契约红线测试（IC-039 PCCC §4）。"""

    def test_hit_requires_human_confirmation(self):
        """命中规则必须要求人工确认，禁止自动发布。"""
        from localization_guard import check
        result = check("最好的产品", lang="zh")
        assert result["requires_human"] is True

    def test_blocked_never_auto_publish(self):
        """BLOCK 级命中永远不能自动发布。"""
        from localization_guard import check
        result = check("清真认证", lang="zh")
        assert result["blocked"] is True
        assert result["requires_human"] is True

    def test_guard_can_be_disabled(self):
        """guard 可整体关闭（回滚机制）。"""
        import localization_guard as lg
        old_enabled = lg.ENABLED
        try:
            lg.ENABLED = False
            from localization_guard import check, score_content
            result = check("最好的产品，清真认证", lang="zh")
            assert result["disabled"] is True
            assert result["hold"] is False
            score = score_content("最好的产品", lang="zh")
            assert score == 1.0  # 关闭时不扣分
        finally:
            lg.ENABLED = old_enabled
