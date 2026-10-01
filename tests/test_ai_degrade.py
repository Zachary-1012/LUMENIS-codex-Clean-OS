# -*- coding: utf-8 -*-
"""P1-G AI checks: retired routes fail closed and redaction remains stable."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.system.ai_gateway import core as intelligence
from lumenis.system.ai_gateway import channel as ai_channel


def test_no_key_ai_status_degrades(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setitem(intelligence._CACHE, "ts", 10**12)
    monkeypatch.setitem(intelligence._CACHE, "provider", "zhipu")
    monkeypatch.setitem(intelligence._CACHE, "model", "glm-stale")
    monkeypatch.setitem(intelligence._CACHE, "base", "https://stale.invalid")
    probes = []
    monkeypatch.setattr(intelligence, "_get_json", lambda *a, **k: probes.append(a))
    monkeypatch.setattr(intelligence, "_detect_local", lambda: probes.append("local-detect"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", lambda *a, **k: probes.append("urlopen"))
    s = intelligence.ai_status()
    assert s["enabled"] is False
    assert s["provider"] == "provider_disabled"
    assert s["runtime"] == "unavailable"
    assert s["hints"] == []
    assert probes == []
    assert intelligence._CACHE["provider"] is None


def test_no_key_ai_enabled_false(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    assert intelligence.ai_enabled() is False


def test_no_key_chat_fallback_no_throw(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    calls = []

    def _all_providers_fail(func, providers=None):
        calls.append("route")
        raise AssertionError("retired provider must not enter fallback")

    monkeypatch.setattr(intelligence, "_provider_config", lambda: calls.append("config"))
    monkeypatch.setattr(intelligence, "_detect_local", lambda: calls.append("local-detect"))
    monkeypatch.setattr(intelligence.urllib.request, "urlopen", lambda *a, **k: calls.append("urlopen"))
    monkeypatch.setattr(ai_channel, "route_with_fallback", _all_providers_fail)
    text, tag = intelligence._chat("sys", "user")
    assert text is None
    assert tag == "provider_disabled"
    assert calls == []


def test_redact_api_key():
    out = intelligence.redact_for_cloud("Authorization: Bearer abcdef123456")
    assert "[REDACTED]" in out
    assert "abcdef123456" not in out
    # 纯 Bearer token 场景
    out2 = intelligence.redact_for_cloud("Bearer abcdef123456")
    assert "[REDACTED]" in out2
    assert "abcdef123456" not in out2


def test_redact_phone_email_idcard():
    out = intelligence.redact_for_cloud(
        "手机13800138000 邮箱 a@b.com 身份证110101199001011234")
    assert "[手机号]" in out and "[邮箱]" in out and "[身份证]" in out
    assert "13800138000" not in out


def test_redact_internal_host():
    out = intelligence.redact_for_cloud("内网 http://192.168.1.5:8321/x")
    assert "[内网主机]" in out
    assert "192.168.1.5" not in out
