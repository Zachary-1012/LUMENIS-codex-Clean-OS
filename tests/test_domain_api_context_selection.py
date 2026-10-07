"""The compatibility domain API must not guess CTH for GLOBAL / ALL."""
from flask import Flask
import pytest

import api_dual_domain
import lumenis_app_api
from domain_isolation import clear_domain_context
from subject_context import clear_thread_context


@pytest.fixture
def client():
    clear_domain_context()
    clear_thread_context()
    app = Flask(__name__)
    app.secret_key = "test-only"
    app.register_blueprint(lumenis_app_api.domain_api_bp)
    with app.test_client() as test_client:
        yield test_client
    clear_domain_context()
    clear_thread_context()


def test_unselected_domain_api_stays_global_selection_only(client, monkeypatch):
    def unexpected_read(*_args, **_kwargs):
        pytest.fail("unselected GLOBAL / ALL must not read CTH or BMP data")

    monkeypatch.setattr(lumenis_app_api, "_domain_api_canonical", unexpected_read)

    overview = client.get("/api/domain/overview")
    context = client.get("/api/domain/context")

    assert overview.status_code == 200
    assert overview.get_json()["mode"] == "GLOBAL_ALL"
    assert overview.get_json()["data_state"] == "DOMAIN_UNSELECTED"
    assert "stats" not in overview.get_json()
    assert context.status_code == 200
    assert context.get_json()["current_domain"] is None
    assert context.get_json()["selection"] == "GLOBAL / ALL"


def test_cth_overview_uses_the_shared_scoped_canonical_owner(client, monkeypatch):
    class Connection:
        closed = False

        def close(self):
            self.closed = True

    connection = Connection()
    calls = []
    monkeypatch.setattr(api_dual_domain, "_get_conn", lambda: connection)

    def read_scoped(actual_connection, **kwargs):
        calls.append((actual_connection, kwargs))
        return {
            "scope": {"mode": "GLOBAL_ALL", "domain_id": "cth", "product_id": "CTH",
                      "subject_id": None, "global": True},
            "permission_audit_id": "audit-test",
            "canonical": {
                "records": [{"sentiment": "positive", "risk_level": "low",
                             "source_platform": "xhs"}],
                "candidate_count": 1, "returned_count": 1, "truncated": False,
            },
        }

    monkeypatch.setattr(api_dual_domain, "read_cth_scoped_canonical", read_scoped)

    response = client.get("/api/domain/overview", headers={
        "X-Domain-Id": "cth", "X-Product-Id": "CTH",
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body["scope"]["domain_id"] == "cth"
    assert body["stats"]["returned_records"] == 1
    assert calls == [(connection, {"module": "content", "limit": 100})]
    assert connection.closed is True


def test_unknown_legacy_domain_selector_is_rejected(client):
    response = client.get("/api/domain/overview?domain=unregistered")

    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_DOMAIN_ID"
