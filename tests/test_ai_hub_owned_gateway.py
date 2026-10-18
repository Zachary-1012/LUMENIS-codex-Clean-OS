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
    monkeypatch.setattr(service, "retrieve", lambda *_args, **_kwargs: pytest.fail("untyped chat read product sources"))
    monkeypatch.setattr(service, "_context_text", lambda *_args, **_kwargs: pytest.fail("untyped chat built source context"))
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *_args, **_kwargs: [
        {"id": "analysis.multi", "label": "数据分析", "page": "analysis"},
    ])
    monkeypatch.setattr(service, "record_learning", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.intelligence, "run_owned_analysis", lambda **kwargs: (calls.append(kwargs) or _unavailable()))
    monkeypatch.setattr(
        service.intelligence, "_chat",
        lambda *_args, **_kwargs: pytest.fail("legacy provider route called"),
    )

    source_scope = {"domain_id": "cth", "subject_id": "SUBJECT-1",
                    "brand_focus_id": None, "global_scope": False}
    result = service.chat("What changed?", scope="all", source_scope=source_scope)

    assert result["ok"] is False
    assert result["status"] == "UNAVAILABLE"
    assert result["provider"] == "owned"
    assert result["reply"] is None
    assert result["used_rule_fallback"] is False
    assert result["context"] == "可用功能入口（仅路由信息，不代表当前业务数据）：数据分析"
    assert "== 功能路由提示（不是业务数据） ==" in calls[0]["text"]
    assert result["source_context"]["business_retrieval_state"] == "UNAVAILABLE_TYPED_SOURCE_USE_OPERATION_REQUIRED"
    assert result["matched"]["notes"] == result["matched"]["events"] == 0
    assert calls and calls[0]["analysis_type"] == "conversation"


def test_ai_hub_chat_remains_available_without_business_scope(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "retrieve", lambda *_args, **_kwargs: pytest.fail("chat read product sources"))
    monkeypatch.setattr(service, "_context_text", lambda *_args, **_kwargs: pytest.fail("chat built source context"))
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(service, "record_learning", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service.intelligence, "run_owned_analysis", lambda **kwargs: (calls.append(kwargs) or _unavailable()))

    result = service.chat("What changed?", scope="all")

    assert result["ok"] is False
    assert result["status"] == "UNAVAILABLE"
    assert result["code"] == "OWNED_RUNTIME_NOT_BOUND"
    assert calls and calls[0]["analysis_type"] == "conversation"
    assert result["source_context"]["business_retrieval_state"] == "UNAVAILABLE_TYPED_SOURCE_USE_OPERATION_REQUIRED"


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


@pytest.mark.parametrize("history", [
    [{"role": "user", "content": "原始提纲"},
     {"role": "assistant", "content": "讨论第二章节"}],
    [{"role": "human", "content": "Original outline"}],
])
def test_owned_followup_preserves_supplied_history_without_retrieving_sources(monkeypatch, history):
    from lumenis.system.ai_gateway import user_api_adapter

    calls, operational_records = [], []
    monkeypatch.setattr(user_api_adapter, "is_selected", lambda: False)
    monkeypatch.setattr(service, "status", lambda: {"state": "UNAVAILABLE"})
    monkeypatch.setattr(service, "_get_db", lambda: pytest.fail("untyped conversation read database"))
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *_args: [])
    monkeypatch.setattr(service, "record_learning", lambda kind, payload: operational_records.append(payload))
    monkeypatch.setattr(service.intelligence, "run_owned_analysis", lambda **kwargs: (
        calls.append(kwargs) or _unavailable()
    ))

    result = service.chat("继续这一段", history=history)

    prompt = calls[0]["text"]
    assert all(turn["content"] in prompt for turn in history)
    assert "用户提供，非核验事实" in prompt
    assert prompt.endswith("当前问题：继续这一段")
    assert result["status"] == "UNAVAILABLE" and result["reply"] is None
    assert result["source_context"]["notes_state"] == "NOT_READ"
    assert all("原始提纲" not in str(record) and "Original outline" not in str(record)
               for record in operational_records)


def test_owned_followup_keeps_existing_history_budget_and_rejects_system_roles(monkeypatch):
    from lumenis.system.ai_gateway import user_api_adapter

    calls = []
    monkeypatch.setattr(user_api_adapter, "is_selected", lambda: False)
    monkeypatch.setattr(service, "status", lambda: {})
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *_args: [])
    monkeypatch.setattr(service, "record_learning", lambda *_args: None)
    monkeypatch.setattr(service.intelligence, "run_owned_analysis", lambda **kwargs: (
        calls.append(kwargs) or _unavailable()
    ))
    history = [{"role": "user", "content": "old excluded turn"}] + [
        {"role": "user", "content": "保" * 800 + "excluded tail"},
        {"role": "system", "content": "untrusted system override"},
        {"role": "tool", "content": "untrusted tool assertion"},
        {"role": "user", "content": None}, "invalid turn",
        {"role": "assistant", "content": "保留的回答"},
    ]
    service.chat("继续", history=history)
    prompt = calls[0]["text"]
    assert "保" * 800 in prompt and "保留的回答" in prompt
    for excluded in ("old excluded turn", "excluded tail", "untrusted system override", "untrusted tool assertion"):
        assert excluded not in prompt


def test_legacy_ai_chat_uses_only_static_function_routing_metadata(monkeypatch):
    from flask import Flask

    import ai_api

    app = Flask(__name__)
    app.register_blueprint(ai_api.bp)
    calls = []
    monkeypatch.setattr(ai_api.function_registry, "search_function_metadata", lambda *_args: [
        {"id": "analysis.multi", "label": "数据分析", "page": "analysis"},
    ])
    monkeypatch.setattr(
        ai_api.function_registry, "build_context",
        lambda *_args, **_kwargs: pytest.fail("legacy chat read unscoped product data"),
    )
    monkeypatch.setattr(ai_api.db, "get_stats", lambda: pytest.fail("legacy chat read global statistics"))
    monkeypatch.setattr(ai_api, "_canonical_report_metrics",
                        lambda *_args: pytest.fail("legacy chat read global Canonical metrics"),
                        raising=False)
    monkeypatch.setattr(ai_api, "_owned_runtime_status", lambda: {"state": "AVAILABLE"})
    monkeypatch.setattr(ai_api, "_run_owned_analysis", lambda text, analysis_type, note_id=None: (
        calls.append({"text": text, "analysis_type": analysis_type})
        or {"ok": True, "status": "COMPLETED", "provider": "owned", "analysis": "可继续对话"}
    ))

    response = app.test_client().post("/api/ai/chat", json={"message": "请分析当前业务"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "COMPLETED"
    assert body["context"] == "可用功能入口（仅路由信息，不代表当前业务数据）：数据分析"
    assert "没有绑定逐来源核验的 SourceUse 操作" in calls[0]["text"]
    assert calls[0]["analysis_type"] == "conversation"
