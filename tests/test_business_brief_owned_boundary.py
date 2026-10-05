"""Unbound owned Gateway never invokes a retired route or signs a fake draft."""
import pytest

from tests.test_source_brief_job_routes import client, GLOBAL, URL
from tests.test_source_brief_job import job_db
from lumenis.shared.reporting import business_brief as brief
from lumenis.system.ai_gateway import core as gateway


@pytest.mark.parametrize("status", [
    {"service_binding": "NOT_BOUND", "state": "UNAVAILABLE", "available": False},
    {"service_binding": "NOT_BOUND", "state": "LOADED_EVALUATION_CANDIDATE", "candidate_loaded": True},
    {"service_binding": "claimed", "available": True},
])
def test_status_or_offline_candidate_cannot_be_promoted_to_structured_service(client, monkeypatch, status):
    api, _, db, _, _ = client
    monkeypatch.setattr(brief.owned_inference, "owned_inference_status", lambda: status)
    monkeypatch.setattr(gateway, "local_structured_chat", lambda *a, **k: pytest.fail("retired route invoked"))
    response = api.post(URL + "/generate", headers=GLOBAL,
                        json={"business_question": "Which information is missing from these sources?"})
    assert response.status_code == 200
    job = response.get_json()["result"]
    analysis = job["business_analysis"]
    assert analysis["state"] == "unavailable" and analysis["real_input_bound"] is False
    assert analysis["provider"] == "owned" and "analysis" not in analysis and "evidence_ref" not in analysis
    assert analysis["provider_status"]["generation_probe_performed"] is False
    assert analysis["provider_status"]["fallback_allowed"] is False
    assert api.get(URL + "/jobs/" + job["job_id"], headers=GLOBAL).get_json()["result"] == job
    from lumenis.shared.database import DatabaseRepository
    with DatabaseRepository(db).connection(read_only=True, wal=False) as connection:
        assert connection.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0


def test_status_read_failure_is_explicit_without_generation(monkeypatch):
    def failed():
        raise RuntimeError("private runtime detail")
    monkeypatch.setattr(brief.owned_inference, "owned_inference_status", failed)
    raw, provider, meta = brief._request_business_inference("question", "source")
    assert raw is None and provider == "owned" and meta["reason"] == "OWNED_STATUS_UNAVAILABLE"
    assert "private" not in str(meta)
