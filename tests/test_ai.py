"""
AI功能测试 - 广州太古汇舆情监测系统
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAIAnalyzer:
    """AI分析器测试"""

    def test_analyze_sentiment(self):
        """测试情感分析"""
        from ai_analyzer import analyze_sentiment
        result = analyze_sentiment("广州太古汇服务很好，环境高级")
        assert result is not None
        # analyze_sentiment 实际返回 (label, score) 元组，兼容 dict/元组两种形态
        label = result[0] if isinstance(result, (tuple, list)) else result.get('sentiment')
        assert label in ('positive', 'neutral', 'negative')

    def test_analyze_negative_sentiment(self):
        """测试负面情感分析"""
        from ai_analyzer import analyze_sentiment
        result = analyze_sentiment("太古汇停车场排队太长，服务很差")
        assert result is not None

    def test_assess_risk(self):
        """测试风险评估"""
        from ai_analyzer import assess_risk
        result = assess_risk("测试标题", "测试内容", 100, 50, "测试用户")
        assert result is not None
        # assess_risk 实际返回 (level, score) 元组，兼容 dict/元组两种形态
        level = result[0] if isinstance(result, (tuple, list)) else result.get('risk_level', result.get('level'))
        assert level in ('low', 'medium', 'high')

    def test_extract_topics(self):
        """测试话题提取"""
        from ai_analyzer import extract_topics
        result = extract_topics("广州太古汇奢侈品购物体验")
        assert result is not None

    def test_categorize(self):
        """测试内容分类"""
        from ai_analyzer import categorize
        result = categorize("广州太古汇购物体验")
        assert result is not None

    def test_generate_summary(self):
        """测试摘要生成"""
        from ai_analyzer import generate_summary
        result = generate_summary("测试标题", "测试内容", "positive", "low", ["购物"])
        assert result is not None
        assert len(result) > 0

class TestARKLLM:
    """Historical node IDs retained; retired ARK is not an installed dependency.

    Current acceptance is the unique Gateway owner and truthful disabled status,
    never a claim of successful ARK inference or a restored legacy provider.
    """

    def test_ark_llm_import(self):
        """The compatibility AI import resolves to the canonical owner."""
        import intelligence
        from lumenis.system.ai_gateway import core, providers
        assert intelligence is core
        assert intelligence.ai_status is core.ai_status
        for name in ("ark", "doubao"):
            assert providers.is_provider_retired(name)
            assert providers.provider_status(name) == providers.DISABLED
            assert providers.provider_info(name)["role"] == "retired_builtin_route"
            assert providers.provider_info(name)["env_key"] is None
            assert not providers.is_provider_available(name)
            assert not providers.is_provider_active(name)

    def test_get_api_status(self, monkeypatch):
        """Unavailable owned runtime stays unavailable despite legacy selection."""
        from lumenis.system.ai_gateway import core, channel, providers
        import socket

        def forbidden(*args, **kwargs):
            pytest.fail("retired ARK status/dispatch attempted provider discovery or network")

        monkeypatch.setattr(core, "_provider_config", forbidden)
        monkeypatch.setattr(core.urllib.request, "urlopen", forbidden)
        monkeypatch.setattr(core.urllib.request, "build_opener", forbidden)
        monkeypatch.setattr(channel, "route_with_fallback", forbidden)
        monkeypatch.setattr(socket, "create_connection", forbidden)
        unavailable = {"available": False, "service_binding": "UNBOUND",
                       "state": "UNAVAILABLE", "reason": "SYNTHETIC_RUNTIME_UNBOUND"}
        monkeypatch.setattr(core, "owned_inference_status", lambda: dict(unavailable))
        for name in ("ark", "doubao"):
            monkeypatch.setenv("AI_PROVIDER", name)
            monkeypatch.setenv("ALLOW_CLOUD_AI", "true")
            status = core.ai_status()
            assert status["provider"] == "provider_disabled"
            assert status["enabled"] is status["installed"] is status["running"] is False
            assert status["owned_status"] == unavailable
            assert status["runtime"] == "unavailable" and status["base_url"] == ""
            assert providers.provider_status(name) == providers.DISABLED
            assert core._chat("synthetic system", "synthetic user") == (None, "provider_disabled")
            assert core._get_call_meta()["provider"] == "provider_disabled"

class TestIntelligence:
    """智能层测试"""

    def test_ai_status(self):
        """测试AI状态"""
        from intelligence import ai_status
        status = ai_status()
        assert status is not None
        assert 'provider' in status

    def test_ai_enabled(self):
        """测试AI是否启用"""
        from intelligence import ai_enabled
        result = ai_enabled()
        assert isinstance(result, bool)

class TestSubjectRules:
    @pytest.fixture(autouse=True)
    def explicit_reference_focus(self):
        from subject_context import brand_scope
        with brand_scope("guangzhou_taikoo_hui", product_id="CTH"):
            yield

    """主体规则测试"""

    def test_subject_words_defined(self):
        """测试主体词定义"""
        from subject_rules import SUBJECT_WORDS
        assert len(SUBJECT_WORDS) > 0

    def test_subject_exclude_words_defined(self):
        """测试排除词定义"""
        from subject_rules import SUBJECT_EXCLUDE_WORDS
        assert SUBJECT_EXCLUDE_WORDS is not None

    def test_subject_hit(self):
        """测试主体命中"""
        from subject_rules import subject_hit
        result = subject_hit("广州太古汇购物")
        assert result is True

    def test_subject_not_hit(self):
        """测试主体未命中"""
        from subject_rules import subject_hit
        result = subject_hit("北京王府井购物")
        assert result is False
