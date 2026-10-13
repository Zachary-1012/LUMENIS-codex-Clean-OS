import pytest

from flask import Flask

import lumenis_agg_api
from lumenis.system.ai_gateway import core as ai_gateway_core


def _client():
    app = Flask("owned-gateway-status")
    lumenis_agg_api.register_agg_api(app)
    return app.test_client()


def test_intelligence_models_reports_only_owned_gateway_runtime(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-only-secret-never-returned")
    monkeypatch.setenv("ZHIPU_MODEL", "retired-model")
    monkeypatch.setenv("OLLAMA_MODEL", "retired-local-model")
    monkeypatch.setattr(
        ai_gateway_core,
        "owned_inference_status",
        lambda domain_id=None: {
            "provider": "owned",
            "available": False,
            "service_binding": "NOT_BOUND",
            "state": "UNAVAILABLE",
            "reason": "OWNED_RUNTIME_NOT_BOUND",
            "model_id": "unbound-candidate-model",
            "fallback_allowed": False,
        },
    )

    response = _client().get("/api/intelligence/models")

    assert response.status_code == 200
    body = response.get_json()
    assert body["active_provider"] == "owned"
    assert body["runtime_available"] is False
    assert body["fallback_chain"] == []
    assert body["gateway"] == {
        "provider": "owned",
        "state": "UNAVAILABLE",
        "service_binding": "NOT_BOUND",
        "available": False,
        "reason": "OWNED_RUNTIME_NOT_BOUND",
        "fallback_allowed": False,
    }
    assert body["providers"] == [
        {
            "provider": "owned",
            "kind": "owned",
            "model": None,
            "configured": False,
            "credential_present": None,
            "active": False,
            "available": False,
            "state": "UNAVAILABLE",
            "service_binding": "NOT_BOUND",
            "fallback_allowed": False,
        }
    ]
    serialized = response.get_data(as_text=True)
    assert "zhipu" not in serialized.lower()
    assert "ollama" not in serialized.lower()
    assert "retired-model" not in serialized
    assert "test-only-secret-never-returned" not in serialized


def test_intelligence_models_does_not_claim_runtime_ready_when_status_read_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        ai_gateway_core,
        "owned_inference_status",
        lambda domain_id=None: (_ for _ in ()).throw(RuntimeError("private diagnostic")),
    )

    body = _client().get("/api/intelligence/models").get_json()

    assert body["runtime_available"] is False
    assert body["gateway"]["state"] == "UNKNOWN"
    assert body["gateway"]["service_binding"] == "NOT_VERIFIED"
    assert body["gateway"]["reason"] == "OWNED_RUNTIME_STATUS_UNAVAILABLE"
    assert "private diagnostic" not in str(body)


@pytest.mark.parametrize("configured", [True, False])
def test_explicit_user_api_is_not_replaced_or_probed(monkeypatch, configured):
    from lumenis.system.ai_gateway import user_api_adapter

    monkeypatch.setattr(user_api_adapter, "is_selected", lambda: True)
    monkeypatch.setattr(user_api_adapter, "is_configured", lambda: configured)
    monkeypatch.setattr(user_api_adapter, "config", lambda domain_id=None: {
        "model": "user-chosen-model", "api_key": "test-only-secret", "base_url": "https://private.invalid",
    })
    monkeypatch.setattr(user_api_adapter, "chat", lambda *_a, **_k: pytest.fail("external model call"))
    monkeypatch.setattr(ai_gateway_core, "owned_inference_status", lambda domain_id=None: {
        "available": True, "service_binding": "BOUND", "state": "READY", "model_id": "owned-model",
    })
    body = _client().get("/api/intelligence/models").get_json()
    assert body["active_provider"] == "user_api"
    assert body["runtime_available"] is None
    assert body["gateway"]["state"] == ("CONFIGURED_NOT_VERIFIED" if configured else "NOT_CONFIGURED")
    assert body["fallback_chain"] == []
    assert body["providers"][0]["active"] is False
    assert body["providers"][1]["configured"] is configured
    assert "test-only-secret" not in str(body)
    assert "private.invalid" not in str(body)


def test_scoped_service_binding_is_not_replaced_by_candidate_status(monkeypatch):
    from lumenis.system.ai_gateway import owned_inference, owned_service, user_api_adapter

    monkeypatch.setattr(user_api_adapter, "is_selected", lambda: False)
    monkeypatch.setattr(owned_inference, "owned_inference_status", lambda: pytest.fail("candidate read"))
    observed = []

    def status(domain):
        observed.append(domain)
        bound = domain == "cth"
        return {"available": bound, "service_binding": "BOUND" if bound else "NOT_BOUND",
                "state": "SERVICE_BOUND" if bound else "UNAVAILABLE", "model_id": "owned-model"}

    monkeypatch.setattr(owned_service, "owned_service_status", status)
    body = _client().get("/api/intelligence/models?domain_id=cth").get_json()
    assert body["runtime_available"] is True
    assert observed == ["cth"]
    observed.clear()
    aggregate = _client().get("/api/intelligence/models").get_json()
    assert observed == ["cth", "bmp"]
    assert aggregate["runtime_available"] is False
    assert aggregate["domain_statuses"]["cth"]["available"] is True
    assert aggregate["domain_statuses"]["bmp"]["available"] is False
    assert aggregate["gateway"]["state"] == "PARTIAL"
    invalid = _client().get("/api/intelligence/models?domain_id=unknown").get_json()
    assert invalid["gateway"]["reason"] == "OWNED_SERVICE_DOMAIN_INVALID"
