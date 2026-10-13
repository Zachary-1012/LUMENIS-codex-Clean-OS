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
        lambda: {
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
        lambda: (_ for _ in ()).throw(RuntimeError("private diagnostic")),
    )

    body = _client().get("/api/intelligence/models").get_json()

    assert body["runtime_available"] is False
    assert body["gateway"]["state"] == "UNKNOWN"
    assert body["gateway"]["service_binding"] == "NOT_VERIFIED"
    assert body["gateway"]["reason"] == "OWNED_RUNTIME_STATUS_UNAVAILABLE"
    assert "private diagnostic" not in str(body)
