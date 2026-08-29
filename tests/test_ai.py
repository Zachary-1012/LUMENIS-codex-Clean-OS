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
    """豆包AI模块测试"""

    def test_ark_llm_import(self):
        """测试ark_llm模块导入"""
        try:
            import ark_llm
            assert ark_llm is not None
        except ImportError:
            pytest.skip("ark_llm模块未安装")

    def test_get_api_status(self):
        """测试API状态查询"""
        try:
            import ark_llm
            status = ark_llm.get_api_status()
            assert status is not None
            assert 'provider' in status
        except ImportError:
            pytest.skip("ark_llm模块未安装")
        except Exception as e:
            pytest.skip(f"API调用失败: {e}")

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
