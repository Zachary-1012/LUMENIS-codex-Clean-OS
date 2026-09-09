from __future__ import annotations

from pathlib import Path


def test_runtime_modes_endpoint(client, auth_headers):
    response = client.get("/api/ai/runtime-modes", headers=auth_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["default"] == "LOCAL_ONLY"
    assert payload["modes"] == ["LOCAL_ONLY", "HYBRID", "CLOUD_FALLBACK"]


def test_analysis_rejects_missing_text(client, auth_headers):
    response = client.post("/api/ai/analyze", json={"type": "summary"}, headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_cth_qa_uses_canonical_local_first_contract():
    source = Path("templates/cth/qa.html").read_text(encoding="utf-8")
    assert "LUMENIS.fetch('/api/ai/analyze'" in source
    assert "runtime_mode: 'LOCAL_ONLY'" in source
    assert "data.analysis" in source


def test_ai_test_route_uses_local_first_service(monkeypatch, client, auth_headers):
    class Service:
        def analyze(self, text, task_type, mode=None):
            return {"summary": "local", "provider": "OLLAMA_LOCAL"}
    monkeypatch.setattr("local_ai_runtime.LocalFirstAIService", Service)
    response = client.post("/api/ai/test", json={"text": "test", "runtime_mode": "LOCAL_ONLY"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["analysis"]["provider"] == "OLLAMA_LOCAL"
