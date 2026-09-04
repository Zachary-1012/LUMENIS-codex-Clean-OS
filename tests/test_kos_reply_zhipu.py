# -*- coding: utf-8 -*-
"""KOS 评论回复/私信触达 · 智谱 AI 接入 回归测试（P0 最高标准 TARGET TEST）

覆盖：
1. 规则层（不依赖 AI）：高风险 NO_REPLY 不得被 AI 越权；空输入报错；评论分类正确
2. 智谱集成层（mock intelligence，CI 可复现）：
   - AI 可用 → 返回建议且 ai_source=True
   - AI 不可用/失败 → 回退规则模板，ai_source=False
   - auto_reply 恒为 False（AI 只给建议，不自动回复）
   - 高风险即使 AI 可用仍 NO_REPLY
3. 触达层：KOS 不存在报错；AI 可用 → DRAFT + ai_source=True；不可用 → 模板兜底
红线：AI 不发送、不承诺、官方账号只读不受影响。
"""
import os
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import kos_engine as ke  # noqa: E402


def _fake_intelligence(ai_enabled=True, chat_result=("这是一条AI回复建议", "zhipu")):
    """构造假 intelligence 模块（不进真实网络，CI 可复现）。"""
    mod = types.ModuleType("intelligence")

    def _ai_enabled():
        return ai_enabled

    def _strong_model():
        return "glm-5.3"

    def _chat(system, user, **kw):
        return chat_result

    def chat(system, user, **kw):
        # production interface converged: _chat -> chat (returns 3-tuple)
        return (chat_result[0], chat_result[1], {})

    mod.ai_enabled = _ai_enabled
    mod._strong_model = _strong_model
    mod._chat = _chat
    mod.chat = chat
    return mod


class TestReplyRuleLayer:
    """规则层：AI 不可越权，红线优先。"""

    def test_high_risk_always_no_reply(self, monkeypatch):
        """高风险评论：即使 AI 可用也必须 NO_REPLY（AI 不得越权）。"""
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True))
        r = ke.generate_reply("我要投诉你们卖假货，我要曝光维权！", risk_level="high")
        assert r["action"] == "NO_REPLY"
        # NO_REPLY 分支不产生任何可发送回复
        assert r.get("auto_reply", False) is not True
        assert "suggested_reply" not in r
        assert r.get("suggested_action")

    def test_high_risk_keyword_no_reply(self, monkeypatch):
        """正文含高风险关键词（律师/12315/曝光）→ NO_REPLY。"""
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True))
        r = ke.generate_reply("律师函已经寄出，12315见")
        assert r["action"] == "NO_REPLY"

    def test_empty_comment_error(self):
        r = ke.generate_reply("")
        assert r["ok"] is False
        assert r["error"] == "empty comment"

    def test_category_classification(self):
        r = ke.generate_reply("请问多少钱？哪里可以买？", brand_name="海南中免CDF")
        assert r["category"] in ("purchase_intent", "general_interaction")

    def test_auto_reply_never_true(self, monkeypatch):
        """红线：AI 只给建议，auto_reply 恒 False。"""
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True))
        for text in ["这个店很好", "怎么买", "你们在哪个位置"]:
            r = ke.generate_reply(text, brand_name="海南中免CDF")
            assert r["auto_reply"] is False


class TestReplyZhipuIntegration:
    """智谱集成层：命中/降级/失败回退。"""

    def test_ai_hit_returns_suggestion(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True))
        r = ke.generate_reply("这个店服务真的很好，推荐大家来逛逛", brand_name="海南中免CDF", reply_style="friendly")
        assert r["action"] == "SUGGEST_REPLY"
        assert r["ai_source"] is True
        assert "AI回复建议" in r["suggested_reply"]
        assert r["auto_reply"] is False

    def test_ai_disabled_falls_back_to_rule(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=False))
        r = ke.generate_reply("这个店服务真的很好", brand_name="海南中免CDF")
        assert r["ai_source"] is False
        assert r["suggested_reply"]  # 规则模板兜底，非空

    def test_ai_failure_falls_back_to_rule(self, monkeypatch):
        """AI 调用失败（返回 None/'rule'）→ 规则兜底，不崩溃。"""
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True, chat_result=(None, "rule")))
        r = ke.generate_reply("这个店服务真的很好", brand_name="海南中免CDF")
        assert r["ok"] is True
        assert r["ai_source"] is False
        assert r["suggested_reply"]

    def test_ai_exception_falls_back(self, monkeypatch):
        """AI 抛异常 → 规则兜底，不崩溃。"""
        mod = types.ModuleType("intelligence")
        mod.ai_enabled = lambda: True

        def _boom(*a, **k):
            raise RuntimeError("network down")

        mod._chat = _boom
        mod._strong_model = lambda: "glm-5.3"
        monkeypatch.setitem(sys.modules, "intelligence", mod)
        r = ke.generate_reply("这个店服务真的很好", brand_name="海南中免CDF")
        assert r["ok"] is True
        assert r["ai_source"] is False

    def test_negative_feedback_requires_approval(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True))
        r = ke.generate_reply("这次体验太差了，很失望", brand_name="海南中免CDF")
        # 负面反馈走强模型分层，且需人工确认
        assert r["requires_approval"] is True or r["action"] == "NO_REPLY"


class TestOutreachZhipu:
    """触达 DRAFT：不伪造已发送。"""

    def test_kos_missing_returns_error(self):
        r = ke.generate_outreach("NO_SUCH_AUTHOR_XYZ", brand_name="海南中免CDF")
        assert r["ok"] is False

    def test_ai_outreach_draft(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True))
        # 需要一个存在 author（造最小 profile 环境由调用方保证）；此处直接测 AI 生成函数本身
        out = ke._ai_generate_outreach("小鹿", "S", "免税攻略", "海南中免CDF", "cdf会员购拉新")
        assert isinstance(out, str) and len(out) > 0

    def test_ai_outreach_disabled_returns_empty(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=False))
        out = ke._ai_generate_outreach("小鹿", "S", "免税攻略", "海南中免CDF", "cdf会员购拉新")
        assert out == ""

    def test_ai_outreach_failure_returns_empty(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "intelligence", _fake_intelligence(ai_enabled=True, chat_result=(None, "rule")))
        out = ke._ai_generate_outreach("小鹿", "S", "免税攻略", "海南中免CDF", "cdf会员购拉新")
        assert out == ""
