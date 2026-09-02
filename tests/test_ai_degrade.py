# -*- coding: utf-8 -*-
"""P1-G AI 分层核验：无 key 全链降级不阻塞系统 + 云端发送脱敏（合规 AI-01）。"""
import sys

sys.path.insert(0, r"D:\Taikoo-monitor-new")

import intelligence


def test_no_key_ai_status_degrades(monkeypatch):
    monkeypatch.setattr(intelligence, "_provider_config", lambda: None)
    s = intelligence.ai_status()
    assert s["enabled"] is False
    assert s["runtime"] == "rule"  # 降级到内置规则引擎，系统不依赖付费 API


def test_no_key_ai_enabled_false(monkeypatch):
    monkeypatch.setattr(intelligence, "_provider_config", lambda: None)
    assert intelligence.ai_enabled() is False


def test_no_key_chat_fallback_no_throw(monkeypatch):
    monkeypatch.setattr(intelligence, "_provider_config", lambda: None)
    text, tag = intelligence._chat("sys", "user")
    assert text is None
    assert tag in ("rule", "no_key")  # 优雅降级，不抛异常


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
