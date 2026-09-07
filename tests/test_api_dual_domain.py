# -*- coding: utf-8 -*-
"""Test API Dual-Domain Namespace — /api/zbmp/*, /api/cth/*, /api/system/* endpoints.

Verifies:
1. All 9 dual-domain endpoints return 200 with real data
2. ZBMP and CTH endpoints return different domain_id in response
3. Domain isolation: CTH endpoint forces subject=guangzhou_taikoo_hui
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
    """Create Flask test client once for all tests (with auth for ZBMP/system endpoints).

    P1-1: ZBMP/system endpoints now require auth; CTH readonly GET remains no-auth.
    Auth headers are sent for all requests (harmless for no-auth endpoints).
    """
    import base64
    from app import app
    c = app.test_client()
    _env = {}
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        for _line in open(_env_path, encoding="utf-8"):
            _line = _line.strip()
            if "=" in _line and not _line.startswith("#"):
                _k, _v = _line.split("=", 1)
                _env[_k.strip()] = _v.strip().strip('"')
    except Exception:
        pass
    _u = _env.get("TAIKOO_AUTH_USER", os.environ.get("TAIKOO_AUTH_USER", "zachary"))
    _p = _env.get("TAIKOO_AUTH_PASSWORD", os.environ.get("TAIKOO_AUTH_PASSWORD", "Zachary01"))
    if _u and _p:
        _tok = base64.b64encode(("%s:%s" % (_u, _p)).encode()).decode()
        c.environ_base["HTTP_AUTHORIZATION"] = "Basic " + _tok
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

    def test_cth_overview_returns_200(self, client):
        resp = client.get("/api/cth/overview", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "cth"
        assert data["product_id"] == "CTH"

    def test_cth_overview_forces_subject(self, client):
        """CTH overview must have subject=guangzhou_taikoo_hui."""
        resp = client.get("/api/cth/overview", headers={"X-Domain-Id": "cth"})
        data = resp.get_json()
        assert data["data"]["subject"] == "guangzhou_taikoo_hui"

    def test_cth_events_returns_200(self, client):
        resp = client.get("/api/cth/events", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["domain_id"] == "cth"
        assert "events" in data["data"]

    def test_cth_xiaohongshu_returns_200(self, client):
        resp = client.get("/api/cth/xiaohongshu", headers={"X-Domain-Id": "cth"})
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

    def test_zbmp_and_cth_return_different_domain_ids(self, client):
        zbmp_resp = client.get("/api/zbmp/overview", headers={"X-Domain-Id": "zbmp"})
        cth_resp = client.get("/api/cth/overview", headers={"X-Domain-Id": "cth"})
        assert zbmp_resp.get_json()["domain_id"] == "zbmp"
        assert cth_resp.get_json()["domain_id"] == "cth"

    def test_unified_response_format(self, client):
        """All endpoints must return {success, data, error, domain_id, product_id}."""
        for path in ["/api/zbmp/overview", "/api/cth/overview", "/api/system/status"]:
            resp = client.get(path)
            data = resp.get_json()
            assert "success" in data, f"{path} missing 'success'"
            assert "data" in data, f"{path} missing 'data'"
            assert "error" in data, f"{path} missing 'error'"
            assert "domain_id" in data, f"{path} missing 'domain_id'"
            assert "product_id" in data, f"{path} missing 'product_id'"


class TestRiskCompatibilityRoute:
    """/api/risks/active compatibility route (P0 broken link fix)."""

    def test_risks_active_returns_200(self, client):
        resp = client.get("/api/risks/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "risks" in data
        assert "total" in data
        assert "by_level" in data

    def test_risk_active_singular_returns_200(self, client):
        resp = client.get("/api/risk/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
