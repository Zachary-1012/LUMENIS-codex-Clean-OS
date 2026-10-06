"""AI Hub must share the owned Gateway and never replace unavailable analysis with rules."""

import pytest

from lumenis.ai_hub import service


def _unavailable(**_kwargs):
    return {
        "ok": False,
        "status": "UNAVAILABLE",
        "code": "OWNED_RUNTIME_NOT_BOUND",
        "provider": "owned",
        "analysis": None,
    }


def test_ai_hub_status_reports_owned_runtime_without_provider_discovery(monkeypatch):
    monkeypatch.setattr(
        service.intelligence,
        "owned_inference_status",
        lambda: {
            "provider": "owned", "available": False,
            "service_binding": "NOT_BOUND", "state": "UNAVAILABLE",
            "reason": "OWNED_RUNTIME_NOT_BOUND",
        },
    )
    monkeypatch.setattr(
        service.intelligence, "ai_status",
        lambda: pytest.fail("legacy provider status or discovery called"),
    )

    result = service.status()

    assert result["provider"] == "owned"
    assert result["enabled"] is False
    assert result["fallback_allowed"] is False
    assert result["rule_fallback"] is False
    assert result["service_binding"] == "NOT_BOUND"


def test_ai_hub_chat_returns_unavailable_instead_of_rule_success(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "retrieve", lambda *_args, **_kwargs: {
        "functions": [], "brands": [], "websites": [], "cases": [],
        "notes": [], "events": [], "meta": {},
    })
    monkeypatch.setattr(service, "_context_text", lambda *_args: "verified context")
    monkeypatch.setattr(service, "record_learning", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.intelligence, "run_owned_analysis", lambda **kwargs: (calls.append(kwargs) or _unavailable()))
    monkeypatch.setattr(
        service.intelligence, "_chat",
        lambda *_args, **_kwargs: pytest.fail("legacy provider route called"),
    )

    result = service.chat("What changed?", scope="all")

    assert result["ok"] is False
    assert result["status"] == "UNAVAILABLE"
    assert result["provider"] == "owned"
    assert result["reply"] is None
    assert result["used_rule_fallback"] is False
    assert result["context"] == "verified context"
    assert calls and calls[0]["analysis_type"] == "conversation"


def test_ai_hub_module_analysis_does_not_invent_neutral_or_low_risk(monkeypatch):
    monkeypatch.setattr(service, "record_learning", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.intelligence, "run_owned_analysis", lambda **_kwargs: _unavailable())
    monkeypatch.setattr(
        service.intelligence, "_chat",
        lambda *_args, **_kwargs: pytest.fail("legacy provider route called"),
    )

    result = service.analyze_module("notes", "real source text")

    assert result["ok"] is False
    assert result["status"] == "UNAVAILABLE"
    assert result["provider"] == "owned"
    assert result["analysis"] is None
    assert "sentiment" not in result
    assert "risk_level" not in result
