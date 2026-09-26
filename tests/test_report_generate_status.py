"""The report generation API must not present absent artifacts as complete."""

from flask import Flask

from lumenis.shared.reporting import routes


def _client():
    app = Flask(__name__)
    app.register_blueprint(routes.report_bp)
    return app.test_client()


def _bundles():
    return {
        report_type: {
            "report": {
                "report_type": report_type,
                "report_date": "2026-09-26",
                "report_id": f"report-{report_type}",
                "_db_row_id": index,
                "_artifact_verified": True,
                "total_notes": 0,
            },
            "digest": None,
        }
        for index, report_type in enumerate(routes.report_engine.REPORT_TYPES, start=1)
    }


def test_generate_accepts_explicit_measured_zero(monkeypatch):
    monkeypatch.setattr(routes.report_engine, "generate_all", _bundles)

    response = _client().post("/api/report/generate")

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert set(body["verified"]) == set(routes.report_engine.REPORT_TYPES)
    assert all(item["total_notes"] == 0 and item["report_valid"] for item in body["verified"].values())


def test_generate_rejects_missing_count_without_inventing_zero(monkeypatch):
    bundles = _bundles()
    del bundles["daily"]["report"]["total_notes"]
    monkeypatch.setattr(routes.report_engine, "generate_all", lambda: bundles)

    response = _client().post("/api/report/generate")

    assert response.status_code == 500
    body = response.get_json()
    assert body["ok"] is False
    assert body["verified"]["daily"]["total_notes"] is None
    assert body["verified"]["daily"]["report_valid"] is False


def test_generate_rejects_empty_or_partial_batch(monkeypatch):
    client = _client()
    monkeypatch.setattr(routes.report_engine, "generate_all", lambda: {})
    empty = client.post("/api/report/generate")
    assert empty.status_code == 500
    assert empty.get_json()["ok"] is False

    bundles = _bundles()
    del bundles["special"]
    monkeypatch.setattr(routes.report_engine, "generate_all", lambda: bundles)
    partial = client.post("/api/report/generate")
    assert partial.status_code == 500
    assert partial.get_json()["ok"] is False
