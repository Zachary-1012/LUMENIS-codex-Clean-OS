# -*- coding: utf-8 -*-
"""Test Flask Request-Level Domain Context.

Verifies:
1. subject_context.init_app(app) registers before_request/after_request hooks
2. X-Domain-Id header sets thread DomainContext
3. X-Product-Id header is parsed and mapped
4. Domain selection preserves explicit focus without an implicit reference
5. after_request clears thread context (no leakage between requests)
6. DomainContext is accessible via flask.g during request
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from flask import Flask, jsonify, g


@pytest.fixture
def app():
    """Create a minimal Flask app with subject_context.init_app."""
    app = Flask(__name__)
    app.secret_key = "test_secret_key"

    from subject_context import init_app
    init_app(app)

    @app.route("/test/domain-context")
    def test_domain_context():
        """Endpoint that returns the current domain/subject context."""
        result = {}
        # SubjectContext
        from subject_context import get_thread_context
        sc = get_thread_context()
        if sc:
            result["subject_context"] = {
                "brand_key": sc.brand_key,
                "product_id": sc.product_id,
                "subject_id": sc.subject_id,
            }
        # DomainContext (from flask.g)
        dc = getattr(g, "domain_context", None)
        if dc:
            result["domain_context"] = {
                "domain_id": dc.domain_id,
                "product_id": dc.product_id,
                "brand_key": dc.brand_key,
            }
        return jsonify(result)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestRequestDomainContext:
    """Request-level domain context parsing."""

    def test_x_domain_id_cth_header(self, client):
        """X-Domain-Id: cth header should set CTH domain context."""
        resp = client.get("/test/domain-context", headers={"X-Domain-Id": "cth"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "domain_context" in data
        assert data["domain_context"]["domain_id"] == "cth"
        assert data["domain_context"]["product_id"] == "CTH"

    def test_x_domain_id_zbmp_header(self, client):
        """X-Domain-Id: zbmp header should set ZBMP domain context."""
        resp = client.get("/test/domain-context", headers={"X-Domain-Id": "zbmp"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_context"]["domain_id"] == "zbmp"
        assert data["domain_context"]["product_id"] == "ZBMP"

    def test_x_product_id_header(self, client):
        """X-Product-Id: ZBMP header should map to domain_id=zbmp."""
        resp = client.get("/test/domain-context", headers={"X-Product-Id": "ZBMP"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_context"]["domain_id"] == "zbmp"

    def test_cth_preserves_explicit_brand(self, client):
        """Selecting a domain must not replace the requested subject."""
        resp = client.get("/test/domain-context",
                          headers={"X-Domain-Id": "cth", "X-Brand-Key": "other_venue"})
        data = resp.get_json()
        assert data["subject_context"]["brand_key"] == "other_venue"
        assert data["domain_context"]["brand_key"] == "other_venue"

    def test_default_is_unfocused_global(self, client):
        """No headers means GLOBAL, irrespective of machine defaults."""
        resp = client.get("/test/domain-context")
        data = resp.get_json()
        # Neither domain nor subject is inferred.
        assert data["subject_context"]["product_id"] == ""
        assert data["subject_context"]["subject_id"] == ""

    def test_context_cleared_after_request(self, client):
        """Thread context must be cleared after request (no leakage)."""
        # First request sets CTH context
        client.get("/test/domain-context", headers={"X-Domain-Id": "cth"})
        # After request, thread context should be cleared
        from subject_context import get_thread_context
        from domain_isolation import get_domain_context as get_dc
        sc = get_thread_context()
        assert sc is None, "SubjectContext leaked after request"


class TestSubjectContextIntegration:
    """SubjectContext is set alongside DomainContext."""

    def test_subject_context_set_with_domain(self, client):
        resp = client.get("/test/domain-context", headers={"X-Domain-Id": "zbmp"})
        data = resp.get_json()
        assert "subject_context" in data
        assert data["subject_context"]["product_id"] == "ZBMP"

    def test_cth_without_focus_is_not_reference_subject(self, client):
        resp = client.get("/test/domain-context", headers={"X-Domain-Id": "cth"})
        data = resp.get_json()
        assert data["subject_context"]["brand_key"] == ""
        assert data["subject_context"]["product_id"] == "CTH"
