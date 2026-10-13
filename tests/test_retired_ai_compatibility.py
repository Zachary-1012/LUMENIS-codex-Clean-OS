"""Retired provider URLs remain honest and cannot create an external effect."""

from flask import Flask

import ai_governance
import ai_resource_packs
import system_features_api


def _system_features_client():
    app = Flask(__name__)
    app.register_blueprint(system_features_api.system_features_bp)
    return app.test_client()


def test_local_ai_routes_fail_closed_without_calling_compatibility_client(monkeypatch):
    assert not hasattr(system_features_api, "local_ai")
    client = _system_features_client()
    for method, path, payload in (
        (client.get, "/api/local-ai/status", None),
        (client.post, "/api/local-ai/analyze", {"text": "request"}),
        (client.post, "/api/local-ai/chat", {"messages": [{"role": "user", "content": "request"}]}),
    ):
        response = method(path, json=payload) if payload is not None else method(path)
        assert response.status_code == 503
        assert response.get_json() == {
            "compatibility_adapter": True,
            "ok": False,
            "reason": "RETIRED_LOCAL_AI_COMPATIBILITY_ONLY",
            "status": "provider_disabled",
        }


def test_retired_per_call_does_not_check_quota_record_usage_or_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(ai_resource_packs, "check_quota", lambda *_args, **_kwargs: calls.append("quota"))
    monkeypatch.setattr(ai_resource_packs, "record_usage", lambda *_args, **_kwargs: calls.append("usage"))

    result = ai_resource_packs.execute_per_call_request("real work request")

    assert result == {
        "ok": False,
        "provider": "zhipu",
        "reason": "RETIRED_PROVIDER_COMPATIBILITY_ONLY",
        "resource_consumed": False,
        "status": "provider_disabled",
    }
    assert calls == []


def test_governance_status_does_not_relabel_a_retired_provider_as_primary(monkeypatch):
    monkeypatch.setattr(
        "lumenis.system.ai_gateway.core.ai_status",
        lambda: {"enabled": False, "provider": "provider_disabled", "detail": "UNAVAILABLE"},
    )

    status = ai_governance.get_governance_status()

    assert status["active_providers"] == []
    assert status["primary_provider"] == "provider_disabled"


def test_retired_pack_cannot_resume_or_dispatch_if_registry_metadata_changes(monkeypatch):
    calls = []
    monkeypatch.setattr("lumenis.system.ai_gateway.providers.is_provider_retired", lambda _name: False)
    monkeypatch.setattr(ai_resource_packs, "_save_stats", lambda *_args: calls.append("write"))
    monkeypatch.setattr("lumenis.system.ai_gateway.core._chat", lambda *args, **kwargs: calls.append("model"))
    assert ai_resource_packs.resume_connection()["paused"] is True
    assert ai_resource_packs.execute_per_call_request("request", model="requested")["resource_consumed"] is False
    assert calls == []
