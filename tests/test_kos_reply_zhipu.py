# -*- coding: utf-8 -*-
"""Historical KOS regression node names, migrated to the current Gateway contract.

Synthetic helper-consumption units do not establish model inference, SourceUse
admission, provider availability or real KOS AI integration. No provider runs.
Keep default deterministic behavior, risk refusal, drafts and failure recovery.
"""
import kos_engine as ke
from lumenis.system.ai_gateway import core as gateway


def _fake_intelligence(monkeypatch, ai_enabled=True,
                       chat_result=("Synthetic AI回复建议", "synthetic-fixture"), error=None):
    """Patch the canonical compatibility seam, with observable synthetic calls."""
    calls = []
    monkeypatch.setattr(gateway, "ai_enabled", lambda: ai_enabled)
    monkeypatch.setattr(gateway, "_strong_model", lambda: None)

    def chat(system, user, **kwargs):
        calls.append({"system": system, "user": user, "kwargs": kwargs})
        if error is not None:
            raise error
        return chat_result[0], chat_result[1], {"synthetic_fixture": True}

    monkeypatch.setattr(gateway, "chat", chat)
    return calls


def _must_not_enhance(*args, **kwargs):
    raise AssertionError("Risk/default/input checks must precede enhancement")


class TestReplyRuleLayer:
    def test_high_risk_always_no_reply(self, monkeypatch):
        monkeypatch.setattr(ke, "_ai_generate_reply", _must_not_enhance)
        r = ke.generate_reply("我要投诉你们卖假货，我要曝光维权！",
                              brand_name="Synthetic Brand", risk_level="high", ai_enhance=True)
        assert r["action"] == "NO_REPLY"
        assert r.get("auto_reply", False) is not True
        assert "suggested_reply" not in r
        assert r.get("suggested_action")

    def test_high_risk_keyword_no_reply(self, monkeypatch):
        monkeypatch.setattr(ke, "_ai_generate_reply", _must_not_enhance)
        r = ke.generate_reply("律师函已经寄出，12315见", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["action"] == "NO_REPLY"
        assert "suggested_reply" not in r
        assert r.get("auto_reply", False) is not True
        assert r.get("suggested_action")

    def test_empty_comment_error(self, monkeypatch):
        monkeypatch.setattr(ke, "_ai_generate_reply", _must_not_enhance)
        r = ke.generate_reply("", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["ok"] is False
        assert r["error"] == "empty comment"
        assert "suggested_reply" not in r

    def test_category_classification(self):
        r = ke.generate_reply("请问多少钱？哪里可以买？", brand_name="Synthetic Brand")
        assert r["category"] in ("purchase_intent", "general_interaction")

    def test_auto_reply_never_true(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch)
        for text in ["这个店很好", "怎么买", "你们在哪个位置"]:
            r = ke.generate_reply(text, brand_name="Synthetic Brand", ai_enhance=True)
            assert r["auto_reply"] is False
        assert len(calls) == 3


class TestReplyZhipuIntegration:
    """Retained historical class name; tests the synthetic generic Gateway seam."""
    def test_ai_hit_returns_suggestion(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch)
        r = ke.generate_reply("这个店服务真的很好，推荐大家来逛逛", brand_name="Synthetic Brand",
                              reply_style="friendly", ai_enhance=True)
        assert r["action"] == "SUGGEST_REPLY"
        assert r["ai_source"] is True
        assert "AI回复建议" in r["suggested_reply"]
        assert r["auto_reply"] is False
        assert len(calls) == 1
        assert "Synthetic Brand" in calls[0]["system"]

    def test_default_does_not_call_gateway(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch, error=AssertionError("No default AI call"))
        r = ke.generate_reply("这个店服务很好", brand_name="Synthetic Brand")
        assert calls == []
        assert r["ai_source"] is False
        assert r["suggested_reply"]
        assert r["auto_reply"] is False

    def test_ai_disabled_falls_back_to_rule(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch, ai_enabled=False)
        r = ke.generate_reply("这个店服务真的很好", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["ai_source"] is False
        assert r["suggested_reply"]
        assert calls == []

    def test_ai_failure_falls_back_to_rule(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch, chat_result=(None, "rule"))
        r = ke.generate_reply("这个店服务真的很好", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["ok"] is True
        assert r["ai_source"] is False
        assert r["suggested_reply"]
        assert len(calls) == 1

    def test_ai_exception_falls_back(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch, error=RuntimeError("synthetic transport failure"))
        r = ke.generate_reply("这个店服务真的很好", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["ok"] is True
        assert r["ai_source"] is False
        assert r["suggested_reply"]
        assert len(calls) == 1

    def test_negative_feedback_requires_approval(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch)
        r = ke.generate_reply("这次体验太差了，很失望", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["requires_approval"] is True or r["action"] == "NO_REPLY"
        assert len(calls) == 1
        assert r["auto_reply"] is False

    def test_real_generic_gateway_stays_unavailable_without_typed_source_request(self, monkeypatch):
        """Real compatibility owner remains fail-closed; no mock-success acceptance."""
        from lumenis.system.ai_gateway import user_api_adapter
        monkeypatch.setattr(gateway, "ai_enabled", lambda: True)
        monkeypatch.setattr(user_api_adapter, "chat", _must_not_enhance)
        monkeypatch.setattr(gateway, "run_owned_request", _must_not_enhance)
        content, provider, metadata = gateway.chat("synthetic system", "synthetic source text")
        assert content is None and provider == "provider_disabled"
        r = ke.generate_reply("这个店服务很好", brand_name="Synthetic Brand", ai_enhance=True)
        assert r["ai_source"] is False
        assert r["suggested_reply"] and r["auto_reply"] is False


class TestOutreachZhipu:
    """Retained node names; admitted-profile draft behavior, never sending."""
    def test_kos_missing_returns_error(self):
        r = ke.generate_outreach("NO_SUCH_AUTHOR_XYZ", brand_name="Synthetic Brand", profile=None)
        assert r["ok"] is False
        assert r["error"] == "KOS 不存在"

    def test_mismatched_profile_is_rejected(self):
        r = ke.generate_outreach("requested-author", brand_name="Synthetic Brand",
                                 profile={"author_id": "different-author"})
        assert r["ok"] is False and r["error"] == "KOS 不存在"

    def test_matching_profile_remains_deterministic_draft(self, monkeypatch):
        monkeypatch.setattr(ke, "_ai_generate_outreach", _must_not_enhance)
        r = ke.generate_outreach("same", brand_name="Synthetic Brand",
                                 profile={"author_id": "same", "author_nickname": "Fixture", "notes": []})
        assert r["ok"] is True and r["status"] == "DRAFT"
        assert r["ai_source"] is False and r["content_source"] == "deterministic_rule"
        assert r["content"] and r["author_id"] == "same"
        assert r.get("sent", False) is False

    def test_ai_outreach_draft(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch)
        out = ke._ai_generate_outreach("Fixture", "S", "Synthetic topic", "Synthetic Brand", "Synthetic campaign")
        assert isinstance(out, str) and len(out) > 0
        assert len(calls) == 1

    def test_ai_outreach_disabled_returns_empty(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch, ai_enabled=False)
        out = ke._ai_generate_outreach("Fixture", "S", "Synthetic topic", "Synthetic Brand", "Synthetic campaign")
        assert out == "" and calls == []

    def test_ai_outreach_failure_returns_empty(self, monkeypatch):
        calls = _fake_intelligence(monkeypatch, chat_result=(None, "rule"))
        out = ke._ai_generate_outreach("Fixture", "S", "Synthetic topic", "Synthetic Brand", "Synthetic campaign")
        assert out == "" and len(calls) == 1
