# -*- coding: utf-8 -*-
"""AI Gateway retirement compatibility checks; all provider transports are mocked."""
import os
import shutil
import sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import intelligence
from lumenis.system.ai_gateway import channel as ai_channel

# Retired local provider names remain accepted by compatibility interfaces.
LOCAL_PROVIDERS = ("ollama", "lmstudio", "llama_cpp")

def use(p, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", p)
    monkeypatch.setitem(intelligence._CACHE, "ts", 0)
    return intelligence.ai_status()

def _cache_key(system, user):
    params = intelligence._level_params("medium")
    return intelligence._cache_key(
        system, user, params["temperature"], params["max_tokens"], params["model"]
    )

def _unexpected_call(calls, label):
    def fail(*args, **kwargs):
        calls.append(label)
        raise AssertionError(f"retired provider path must not call {label}")
    return fail

def test_openai_failure_falls_back(monkeypatch):
    """Explicitly disabled selections do not enter the provider fallback chain."""
    calls = []
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setattr(intelligence, "_provider_config", _unexpected_call(calls, "config"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(ai_channel, "route_with_fallback", _unexpected_call(calls, "fallback"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    raw, provider = intelligence._chat("Only answer OK", "test", 0, 20)
    assert (raw, provider) == (None, "provider_disabled")
    assert calls == []

def test_zhipu_wired_and_safe(monkeypatch):
    """Stale configuration/cache cannot reactivate Zhipu or return cached output."""
    calls = []
    monkeypatch.setitem(intelligence._CACHE, "provider", "zhipu")
    monkeypatch.setitem(intelligence._CACHE, "model", "stale-glm")
    monkeypatch.setitem(intelligence._CACHE, "base", "https://stale.invalid")
    monkeypatch.setattr(intelligence, "_get_json", _unexpected_call(calls, "discovery"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    monkeypatch.setattr(intelligence, "_chat", _unexpected_call(calls, "inference"))
    monkeypatch.setattr(ai_channel, "route_with_fallback", _unexpected_call(calls, "fallback"))
    st = use("zhipu", monkeypatch)
    assert st["enabled"] is False
    assert st["provider"] == "provider_disabled"
    assert st["runtime"] == "unavailable"
    assert st["hints"] == []
    # Status is read-only; retained historical metadata grants no execution.
    assert intelligence._CACHE["provider"] == "zhipu"
    monkeypatch.setattr(intelligence, "_provider_config", _unexpected_call(calls, "config"))

    system, user = "Only JSON", '{"ok":true}'
    monkeypatch.setitem(intelligence._CHAT_CACHE, _cache_key(system, user), ("stale answer", "zhipu"))
    cache_reads = []
    get_cached = intelligence._chat_cache_get
    monkeypatch.setattr(
        intelligence, "_chat_cache_get",
        lambda key: cache_reads.append(key) or get_cached(key),
    )
    budget_calls = []
    monkeypatch.setattr(intelligence, "_budget_check", _unexpected_call(budget_calls, "budget check"))
    raw, provider, meta = intelligence.chat(system, user, use_cache=True)
    assert (raw, provider) == (None, "provider_disabled")
    assert meta["cache"] is False
    assert cache_reads == []
    assert budget_calls == []
    assert calls == []

def test_auto_priority(monkeypatch):
    """Auto selection remains unavailable and performs no local discovery."""
    calls = []
    for k in ("ARK_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(intelligence, "_get_json", _unexpected_call(calls, "discovery"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    st = use("auto", monkeypatch)
    assert st["enabled"] is False
    assert st["provider"] == "provider_disabled"
    assert st["runtime"] == "unavailable"
    assert st["hints"] == []
    assert calls == []


def test_daily_capability_reports_owned_gateway_unavailable_without_fallback():
    selected = intelligence.select_model_by_capability("daily")
    assert selected["provider"] == "owned"
    assert selected["model"] is None
    assert selected["primary_available"] is False
    assert selected["primary_status"] == "OWNED_RUNTIME_NOT_BOUND"
    assert selected["fallback_chain"] == []


def test_strong_reasoning_reports_owned_gateway_unavailable_without_fallback():
    selected = intelligence.select_model_by_capability("strong_reasoning")
    assert selected["provider"] == "owned"
    assert selected["model"] is None
    assert selected["primary_available"] is False
    assert selected["primary_status"] == "OWNED_RUNTIME_NOT_BOUND"
    assert selected["fallback_chain"] == []


def test_local_chat_does_not_consume_cloud_pack(monkeypatch):
    """Retired Ollama does not probe, read cache, consume budget, or infer."""
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    calls = []
    monkeypatch.setattr(intelligence, "_provider_config", _unexpected_call(calls, "config"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(intelligence, "_chat", _unexpected_call(calls, "inference"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    monkeypatch.setattr(intelligence, "_budget_check", _unexpected_call(calls, "budget check"))
    monkeypatch.setattr(intelligence, "_budget_record", _unexpected_call(calls, "budget record"))
    system, user = "Only reply with result", "local test"
    monkeypatch.setitem(intelligence._CHAT_CACHE, _cache_key(system, user), ("stale local result", "ollama"))
    cache_reads = []
    get_cached = intelligence._chat_cache_get
    monkeypatch.setattr(
        intelligence, "_chat_cache_get",
        lambda key: cache_reads.append(key) or get_cached(key),
    )
    raw, provider, meta = intelligence.chat(
        system, user, level="medium", pack_id="glm_4_5_air", use_cache=True
    )
    assert (raw, provider) == (None, "provider_disabled")
    assert meta["cache"] is False
    assert cache_reads == []
    assert calls == []


def test_explicit_local_failure_falls_back_to_rule_only(monkeypatch):
    """Explicit Ollama selection fails closed before local or cloud transport."""
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    calls = []
    monkeypatch.setattr(intelligence, "_provider_config", _unexpected_call(calls, "config"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(ai_channel, "route_with_fallback", _unexpected_call(calls, "fallback"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    raw, provider = intelligence._chat("只回复结果", "本地测试", 0.0, 8)
    assert (raw, provider) == (None, "provider_disabled")
    assert calls == []


def test_cloud_failure_falls_back_to_ollama_with_thinking_disabled(monkeypatch):
    """Retired Zhipu selection cannot probe or fall back to local inference."""
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(intelligence, "_provider_config", _unexpected_call(calls, "config"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(ai_channel, "route_with_fallback", _unexpected_call(calls, "fallback"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    raw, provider = intelligence._chat("system-local", "user-local", 0.0, 16)
    assert (raw, provider) == (None, "provider_disabled")
    assert calls == []


def test_cloud_and_ollama_failure_falls_back_to_rule(monkeypatch):
    """Retired provider selections do not silently report rule inference success."""
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    calls = []
    monkeypatch.setattr(intelligence, "_provider_config", _unexpected_call(calls, "config"))
    monkeypatch.setattr(intelligence, "_detect_local", _unexpected_call(calls, "local discovery"))
    monkeypatch.setattr(ai_channel, "route_with_fallback", _unexpected_call(calls, "fallback"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call(calls, "HTTP"))
    raw, provider = intelligence._chat("system", "user", 0.0, 16)
    assert (raw, provider) == (None, "provider_disabled")
    assert calls == []


def test_ollama_hint_reflects_reachable_models(monkeypatch):
    """Retired Ollama health hints do not probe /api/tags or inspect PATH."""
    calls = []
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(intelligence, "_get_json", _unexpected_call(calls, "discovery HTTP"))
    monkeypatch.setattr(shutil, "which", _unexpected_call(calls, "PATH probe"))
    assert intelligence._installed_hints() == []
    assert calls == []

def test_review_note_structure(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "auto")
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", _unexpected_call([], "HTTP"))
    note = {"title": "太古汇停车排队久", "content": "品牌很全环境好，就是停车场排队太久、引导不清"}
    rule = {"verified": True, "summary": "提及太古汇停车", "topics": ["停车"], "verify_reason": ""}
    res = intelligence.review_note(note, rule)
    assert res["verification"] in ("verified", "review", "suspicious_fake", "rejected")
    assert res.get("summary")
    assert res.get("provider") == "rule"


def test_review_note_uses_verified_scope_without_reference_subject(monkeypatch):
    calls = []

    def capture(system, user, **kwargs):
        calls.append((system, user))
        return None, "provider_disabled", {}

    monkeypatch.setattr(intelligence, "chat", capture)
    note = {"title": "测试广场停车", "content": "停车场出口排队"}
    rule = {"verified": True, "summary": "测试广场停车反馈", "topics": ["停车"],
            "verified_scope": {"domain_id": "cth", "product_id": "CTH",
                               "subject_id": "MALL_SCOPE_1", "brand_focus_id": None,
                               "global_scope": False, "display_name": "测试广场",
                               "aliases": ["测试商场"]}}
    result = intelligence.review_note(note, rule)
    assert len(calls) == 1
    system, user = calls[0]
    assert "广州太古汇" not in system
    assert "当前已核验业务范围" in system
    assert "不得自行假定或替换主体" in system
    assert note["title"] in user and rule["summary"] in user
    assert "MALL_SCOPE_1" in user and "测试商场" in user
    assert result["summary"] == rule["summary"]
    assert result["provider"] == "rule"
    assert result["verification"] == "review"
    rejected = intelligence.review_note(note, {"verified": False, "verify_reason": "scope rejected"})
    assert rejected["verification"] == "rejected"
    assert len(calls) == 1


@pytest.mark.parametrize("scope", [None, {},
    {"domain_id": "cth", "product_id": "ZBMP", "subject_id": "MALL_SCOPE_1",
     "brand_focus_id": None, "global_scope": False, "display_name": "测试广场"},
    {"domain_id": "cth", "product_id": "CTH", "subject_id": "MALL_SCOPE_1",
     "brand_focus_id": None, "global_scope": False},
    {"domain_id": "cth", "product_id": "CTH", "subject_id": None,
     "brand_focus_id": None, "global_scope": True, "display_name": "全部"},
])
def test_review_note_missing_or_ambiguous_scope_keeps_rules_without_ai(monkeypatch, scope):
    monkeypatch.setattr(intelligence, "chat", _unexpected_call([], "unscoped inference"))
    result = intelligence.review_note({"title": "甲乙两家商场对比"}, {
        "verified": True, "summary": "已取得文本，主体审阅待核验", "verified_scope": scope,
    })
    assert result["provider"] == "rule"
    assert result["verification"] == "review"
    assert result["summary"] == "已取得文本，主体审阅待核验"
    assert result["enhancement_state"] == "VERIFIED_SCOPE_REQUIRED"
