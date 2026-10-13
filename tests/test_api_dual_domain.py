# -*- coding: utf-8 -*-
"""Test API Dual-Domain Namespace — /api/zbmp/*, /api/cth/*, /api/system/* endpoints.

Verifies:
1. All 9 dual-domain endpoints return 200 with real data
2. ZBMP and CTH endpoints return different domain_id in response
3. Domain isolation: CTH reads preserve GLOBAL scope unless an explicit focus is selected
4. Unified JSON format: {success, data, error, domain_id, product_id}
5. /api/system/runtime (existing lumenis endpoint) now includes runtime_by_domain
6. /api/risks/active compatibility route returns 200
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(scope="module")
def client():
    """Authenticated test client for ZBMP and SYSTEM endpoints."""
    import base64
    from app import app
    c = app.test_client()
    username = os.environ.get("TAIKOO_AUTH_USER")
    password = os.environ.get("TAIKOO_AUTH_PASSWORD")
    assert username and password, "tests/conftest.py must provide isolated test credentials"
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    c.environ_base["HTTP_AUTHORIZATION"] = f"Basic {token}"
    return c


@pytest.fixture
def cth_client(monkeypatch):
    """Server-opened local workspace; CTH routes still perform real scope Permission."""
    from app import app
    monkeypatch.setitem(app.config, "LUMENIS_OPEN_WORKSPACE", True)
    c = app.test_client()
    assert "HTTP_AUTHORIZATION" not in c.environ_base
    return c


class TestZBMPEndpoints:
    """ZBMP domain endpoints: /api/zbmp/*."""

    def test_zbmp_overview_returns_200(self, client):
        resp = client.get("/api/zbmp/overview", headers={"X-Domain-Id": "zbmp"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "zbmp"
        assert data["product_id"] == "ZBMP"
        assert "data" in data

    def test_zbmp_brands_returns_200(self, client):
        resp = client.get("/api/zbmp/brands", headers={"X-Domain-Id": "zbmp"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "zbmp"
        assert "brands" in data["data"]

    def test_zbmp_metrics_returns_200(self, client):
        resp = client.get("/api/zbmp/metrics", headers={"X-Domain-Id": "zbmp"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "zbmp"
        assert "total_notes" in data["data"]


class TestCTHEndpoints:
    """CTH domain endpoints: /api/cth/*."""

    def test_cth_overview_returns_200(self, cth_client):
        resp = cth_client.get("/api/cth/overview", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "cth"
        assert data["product_id"] == "CTH"

    def test_cth_overview_defaults_to_global_without_focus(self, cth_client):
        """An unselected CTH request remains GLOBAL / ALL, not an implicit Subject focus."""
        resp = cth_client.get("/api/cth/overview", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["scope"]["mode"] == "GLOBAL_ALL"
        assert data["data"]["scope"]["subject_id"] is None
        assert data["data"]["subject_id"] is None

    def test_cth_events_returns_200(self, cth_client):
        resp = cth_client.get("/api/cth/events", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "cth"
        assert "events" in data["data"]

    def test_cth_xiaohongshu_returns_200(self, cth_client):
        resp = cth_client.get("/api/cth/xiaohongshu", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "cth"
        assert "records" in data["data"]


class TestSystemEndpoints:
    """System domain endpoints: /api/system/*."""

    def test_system_status_returns_200(self, client):
        resp = client.get("/api/system/status", headers={"X-Domain-Id": "system"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "system"

    def test_system_runtime_workers_returns_200(self, client):
        resp = client.get("/api/system/runtime-workers", headers={"X-Domain-Id": "system"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "by_domain" in data["data"]

    def test_system_domains_returns_200(self, client):
        resp = client.get("/api/system/domains", headers={"X-Domain-Id": "system"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "domains" in data["data"]
        assert "cth" in data["data"]["domains"]
        assert "zbmp" in data["data"]["domains"]
        assert "system" in data["data"]["domains"]

    def test_existing_system_runtime_has_domain_data(self, client):
        """Existing /api/system/runtime (lumenis) must now include runtime_by_domain."""
        resp = client.get("/api/system/runtime")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "runtime_by_domain" in data
        assert "cth" in data["runtime_by_domain"]
        assert "zbmp" in data["runtime_by_domain"]
        assert "system" in data["runtime_by_domain"]


class TestDomainIsolation:
    """Cross-domain isolation verification."""

    def test_zbmp_and_cth_return_different_domain_ids(self, client, cth_client):
        zbmp_resp = client.get("/api/zbmp/overview", headers={"X-Domain-Id": "zbmp"})
        cth_resp = cth_client.get("/api/cth/overview", headers={"X-Domain-Id": "cth"})
        assert zbmp_resp.get_json()["domain_id"] == "zbmp"
        assert cth_resp.get_json()["domain_id"] == "cth"

    def test_unified_response_format(self, client, cth_client):
        """All endpoints must return {success, data, error, domain_id, product_id}."""
        for path in ["/api/zbmp/overview", "/api/cth/overview", "/api/system/status"]:
            active_client = cth_client if path.startswith("/api/cth/") else client
            resp = active_client.get(path)
            data = resp.get_json()
            assert "success" in data, f"{path} missing 'success'"
            assert "data" in data, f"{path} missing 'data'"
            assert "error" in data, f"{path} missing 'error'"
            assert "domain_id" in data, f"{path} missing 'domain_id'"
            assert "product_id" in data, f"{path} missing 'product_id'"


class TestRiskCompatibilityRoute:
    """/api/risks/active compatibility route (P0 broken link fix)."""

    @pytest.mark.parametrize("path", ["/api/risks/active", "/api/risk/active"])
    def test_unselected_risk_route_requires_domain_without_reading_legacy_notes(
        self, cth_client, monkeypatch, path
    ):
        import database

        def unexpected_legacy_read(*_args, **_kwargs):
            pytest.fail("risk compatibility routes must not read unscoped legacy notes")

        monkeypatch.setattr(database, "get_high_risk_notes", unexpected_legacy_read)
        resp = cth_client.get(path)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False
        assert data["code"] == "DOMAIN_SELECTION_REQUIRED"
        assert data["selection_required"] is True
        assert data["risks"] is None
        assert data["total"] is None

    @pytest.mark.parametrize("path", ["/api/risks/active", "/api/risk/active"])
    def test_selected_cth_risk_route_uses_authorized_canonical(
        self, cth_client, monkeypatch, path
    ):
        import database

        def unexpected_legacy_read(*_args, **_kwargs):
            pytest.fail("selected risk reads must use scoped Canonical, not legacy notes")

        monkeypatch.setattr(database, "get_high_risk_notes", unexpected_legacy_read)
        resp = cth_client.get(path, headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["domain_id"] == "cth"
        assert data["product_id"] == "CTH"
        assert data["scope"]["mode"] == "GLOBAL_ALL"
        assert "risks" in data
        assert "total" in data
        assert "by_level" in data
        assert data["source"] == "permission-checked canonical_data.list_scoped_canonical"
        assert data["risk_policy_version"] == "cth-risk-v2.1"
        assert data["dismissal_state"] == "APPLIED_FOR_CANONICAL_NOTE_SOURCE_IDS"
        assert data["total"] == len(data["risks"])

    def test_active_risk_projection_excludes_low_and_unknown_levels(
        self, cth_client, monkeypatch
    ):
        import database
        import lumenis_app_api

        scope = {
            "mode": "GLOBAL_ALL", "domain_id": "cth", "product_id": "CTH",
            "subject_id": None, "global": True,
        }
        canonical = {
            "records": [
                {"canonical_id": "critical-1", "risk_level": "critical",
                 "source_type": "note", "source_table": "notes", "source_id": "critical-1",
                 "external_id": "critical-1",
                 "raw_ref": '{"table":"notes","note_id":"critical-1"}'},
                {"canonical_id": "high-1", "risk_level": "high",
                 "source_type": "note", "source_table": "notes", "source_id": "high-1",
                 "external_id": "high-1",
                 "raw_ref": '{"table":"notes","note_id":"high-1"}'},
                {"canonical_id": "medium-1", "risk_level": "medium",
                 "source_type": "note", "source_table": "notes", "source_id": "medium-1",
                 "external_id": "medium-1",
                 "raw_ref": '{"table":"notes","note_id":"medium-1"}'},
                {"canonical_id": "low-1", "risk_level": "low"},
                {"canonical_id": "unknown-1", "risk_level": "unknown"},
            ],
            "candidate_count": 5, "returned_count": 5, "truncated": False,
        }
        monkeypatch.setattr(
            lumenis_app_api, "_domain_api_canonical",
            lambda domain, module: (scope, canonical),
        )
        monkeypatch.setattr(
            database, "get_high_risk_note_dismissal_states",
            lambda note_ids: {note_id: 0 for note_id in note_ids},
        )
        resp = cth_client.get("/api/risks/active", headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH",
        })

        assert resp.status_code == 200
        data = resp.get_json()
        assert [row["canonical_id"] for row in data["risks"]] == [
            "critical-1", "high-1", "medium-1",
        ]
        assert data["by_level"] == {"critical": 1, "high": 1, "medium": 1}
        assert data["total"] == 3

    def test_dismissed_note_is_not_returned_as_an_active_risk(
        self, cth_client, monkeypatch
    ):
        import json
        import database
        import lumenis_app_api
        import uuid

        active_id = f"active-{uuid.uuid4().hex}"
        dismissed_id = f"dismissed-{uuid.uuid4().hex}"
        with database.get_db() as connection:
            connection.executemany(
                "INSERT INTO notes (note_id, risk_level, negative_confirmed) VALUES (?, 'high', ?)",
                [(active_id, 0), (dismissed_id, 2)],
            )

        scope = {
            "mode": "GLOBAL_ALL", "domain_id": "cth", "product_id": "CTH",
            "subject_id": None, "global": True,
        }
        canonical = {
            "records": [
                {"canonical_id": f"canonical-{active_id}", "risk_level": "high",
                 "source_type": "note", "source_table": "notes", "source_id": active_id,
                 "external_id": active_id,
                 "raw_ref": json.dumps({"table": "notes", "note_id": active_id})},
                {"canonical_id": f"canonical-{dismissed_id}", "risk_level": "critical",
                 "source_type": "note", "source_table": "notes", "source_id": dismissed_id,
                 "external_id": dismissed_id,
                 "raw_ref": json.dumps({"table": "notes", "note_id": dismissed_id})},
            ],
            "candidate_count": 2, "returned_count": 2, "truncated": False,
        }
        monkeypatch.setattr(
            lumenis_app_api, "_domain_api_canonical",
            lambda domain, module: (scope, canonical),
        )

        response = cth_client.get("/api/risks/active", headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH",
        })

        assert response.status_code == 200
        data = response.get_json()
        assert [row["source_id"] for row in data["risks"]] == [active_id]
        assert data["dismissal_state"] == "APPLIED_FOR_CANONICAL_NOTE_SOURCE_IDS"

    def test_unknown_risk_domain_is_rejected_without_cth_fallback(self, cth_client):
        resp = cth_client.get("/api/risks/active", headers={
            "X-Domain-Id": "unregistered-domain",
        })

        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False
