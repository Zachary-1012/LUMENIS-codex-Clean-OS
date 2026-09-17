import json
import sys
from pathlib import Path

from flask import Flask


def test_system_creator_ops_is_local_truth_and_redacts(monkeypatch, tmp_path):
    monkeypatch.setenv("ZBC_DATA_DIR", str(tmp_path))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import system_creator_ops_api as ops

    monkeypatch.setattr(ops, "_system_health_payload", lambda: {
        "ok": True, "overall_status": "ok", "diagnostic_hints": [], "sub_lights": {},
    })
    app = Flask(__name__)
    app.register_blueprint(ops.system_creator_ops_bp)
    client = app.test_client()

    initial = client.get("/api/system/ops/summary")
    assert initial.status_code == 200
    payload = initial.get_json()
    assert payload["schema"] == "lumenis-system-creator-ops-v1"
    assert payload["scope"]["health_truth"] == "/api/system/health/summary"
    assert payload["costs"]["month_tracked_usd"] is None
    assert payload["costs"]["actual_provider_billing"] == "not_connected"

    assert client.post("/api/system/ops/costs", json={"amount_usd": -1}).status_code == 400
    cost = client.post("/api/system/ops/costs", json={"amount_usd": 12.5, "category": "Hosting"})
    assert cost.status_code == 201

    secret = "super-secret-credential-0123456789-abcdefghijklmnopqrstuvwxyz"
    feedback = client.post("/api/system/ops/feedback", json={
        "title": "mobile issue", "severity": "high", "detail": f"Authorization: Bearer {secret}; cookie={secret}",
    })
    assert feedback.status_code == 201
    assert secret not in json.dumps(feedback.get_json())
    assert "[REDACTED]" in json.dumps(feedback.get_json())

    events = client.get("/api/system/ops/events").get_json()
    assert len(events["costs"]) == 1 and len(events["feedback"]) == 1
    assert secret not in json.dumps(events)
    summary = client.get("/api/system/ops/summary").get_json()
    assert summary["costs"]["month_tracked_usd"] == 12.5
    assert summary["feedback"]["open_count"] == 1
    assert client.get("/api/system/ops/report").status_code == 200
    html = client.get("/system/ops").data.decode("utf-8")
    assert "SYSTEM Ops" in html and "不会自动重启" in html
