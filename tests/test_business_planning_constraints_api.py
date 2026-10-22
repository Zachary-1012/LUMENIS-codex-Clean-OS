"""Existing CTH/BMP HTTP owner accepts user planning constraints safely."""
import pytest

pytest_plugins = (
    "tests.test_business_result_continuity",
    "tests.test_saved_document_workflow",
)


@pytest.fixture
def business_route_client(business, monkeypatch):
    import lumenis_app_api

    ws = business
    ws["app"].register_blueprint(lumenis_app_api.domain_api_bp)
    monkeypatch.setattr(
        lumenis_app_api,
        "_business_work_binding",
        lambda _operation: (ws["service"], ws["actor_ref"], ws["domain_scope"], ws["authorize"]),
    )
    return ws, ws["app"].test_client()


def test_prepare_http_supports_source_bound_analysis_and_explicit_constraints(business_route_client):
    ws, client = business_route_client
    payload = {
        "submission_id": "http-derived-planning-001",
        "source_job_id": ws["current"]["source_report"]["job_id"],
        "kind": ws["current"]["kind"],
        "question": "Review this source and check the activity dates.",
        "planning_constraints": {
            "time_range": {
                "start": "2026-10-01T00:00:00+08:00",
                "end": "2026-10-31T23:59:59+08:00",
            },
            "resource_constraints": {
                "budget_amount": "100",
                "estimated_cost_amount": "50",
                "currency": "CNY",
                "as_of": "2026-10-08T08:00:00+08:00",
                "limits": ["Estimate only; no purchasing."],
            },
        },
    }

    response = client.post("/api/experience/business-works", json=payload)
    assert response.status_code == 200, response.get_json()
    result = response.get_json()["result"]
    assert result["domain_analysis"]["question_result"]["planning_constraints"]["time_range"] == payload["planning_constraints"]["time_range"]
    assert result["options"]
    assert all(option["cost_estimate"] is None for option in result["options"])
    assert all(option["budget_fit"] == "UNKNOWN" for option in result["options"])


@pytest.mark.parametrize("extra", [
    {"unrecognized": True},
    {"case_id": "case-not-a-source-job"},
])
def test_prepare_http_rejects_unrecognized_or_mixed_case_source_fields(business_route_client, extra):
    ws, client = business_route_client
    payload = {
        "submission_id": "http-invalid-planning-001",
        "source_job_id": ws["current"]["source_report"]["job_id"],
        "kind": ws["current"]["kind"],
        "question": "Review this source.",
        **extra,
    }
    response = client.post("/api/experience/business-works", json=payload)
    assert response.status_code == 400
    assert response.get_json()["code"] == "BUSINESS_WORK_REQUEST_INVALID"


def test_prepare_http_preserves_explicit_operator_options(business_route_client):
    from tests.test_business_result_continuity import make_options

    ws, client = business_route_client
    source_id = ws["current"]["options"][0]["source_ids"][0]
    options = make_options(source_id)
    payload = {
        "submission_id": "http-manual-options-001",
        "source_job_id": ws["current"]["source_report"]["job_id"],
        "kind": ws["current"]["kind"],
        "question": "Keep these operator proposals.",
        "options": options,
    }
    response = client.post("/api/experience/business-works", json=payload)
    assert response.status_code == 200, response.get_json()
    result = response.get_json()["result"]
    assert [item["proposal"] for item in result["options"]] == [item["proposal"] for item in options]
    assert all(item["claim_type"] == "OPERATOR_PROPOSAL" for item in result["options"])
    assert "domain_analysis" not in result
