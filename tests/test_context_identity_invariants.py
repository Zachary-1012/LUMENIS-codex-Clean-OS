"""Frozen semantic contract: routing preserves domain and never invents focus.

Finite input enumeration is an executable invariant, not a Lean proof or a
claim that HTTP metadata authorizes access to a subject.
"""
import itertools

import pytest
from flask import Flask, jsonify, g

from domain_isolation import (
    DomainContext, clear_domain_context, cross_domain_access_allowed,
    domain_summary, domain_to_product, product_to_domain, resolve_domain_identity,
)
from subject_context import clear_thread_context, current_scope, init_app


@pytest.fixture(autouse=True)
def isolated_context():
    clear_domain_context()
    clear_thread_context()
    yield
    clear_domain_context()
    clear_thread_context()


@pytest.mark.parametrize("domain,product", itertools.product(
    ("cth", " CTH ", "bmp", "BMP", "zbmp", "system"),
    ("CTH", " cth ", "BMP", " ZBMP ", "SYSTEM"),
))
def test_identity_pair_preserves_meaning_or_rejects(domain, product):
    # Independent expected equivalence classes fixed by the product contract.
    families = {"cth": ("cth", "CTH"), "bmp": ("zbmp", "ZBMP"),
                "zbmp": ("zbmp", "ZBMP"), "system": ("system", "SYSTEM")}
    left, right = families[domain.strip().lower()], families[product.strip().lower()]
    if left == right:
        assert resolve_domain_identity(domain, product) == left
    else:
        with pytest.raises(ValueError, match="DOMAIN_PRODUCT_MISMATCH"):
            resolve_domain_identity(domain, product)


@pytest.mark.parametrize("invalid", (None, "", " ", "unknown", "GLOBAL", "ALL", 0, False, []))
def test_unknown_is_not_cth_or_a_permission(invalid):
    for mapper in (domain_to_product, product_to_domain):
        with pytest.raises(ValueError):
            mapper(invalid)
    with pytest.raises(ValueError):
        cross_domain_access_allowed(invalid, invalid, "database")


@pytest.fixture
def client(monkeypatch):
    # A running machine's reference settings must not replace the user's choice.
    monkeypatch.setenv("ZBC_PRODUCT_ID", "CTH")
    monkeypatch.setenv("ZBC_DOMAIN", "cth")
    monkeypatch.setenv("ZBC_ACTIVE_BRAND", "guangzhou_taikoo_hui")
    app = Flask(__name__)
    app.secret_key = "isolated-semantic-contract"
    init_app(app)

    @app.get("/context")
    def read_context():
        return jsonify({"domain": g.domain_context.to_dict(), "scope": current_scope(),
                        "summary": domain_summary()})

    return app.test_client()


def test_requests_do_not_leak_focus_or_inherit_machine_default(client):
    selected = client.get("/context", headers={"X-Domain-Id": "bmp", "X-Brand-Key": "nike"})
    assert selected.status_code == 200
    assert selected.json["domain"]["product_id"] == "ZBMP"
    assert selected.json["domain"]["brand_key"] == "nike"
    global_result = client.get("/context").json
    assert global_result["domain"]["domain_id"] == ""
    assert global_result["scope"]["subject"]["subject_id"] == ""
    assert global_result["scope"]["product"]["default_subject"] is None
    system = client.get("/context", headers={"X-Domain-Id": "system"}).json
    assert system["scope"]["product"]["product_id"] == "SYSTEM"
    assert system["summary"]["current_domain"] == "system"
    assert system["scope"]["subject"]["brand_key"] == ""


@pytest.mark.parametrize("headers", [
    {"X-Domain-Id": "unknown"}, {"X-Product-Id": "unknown"},
    {"X-Domain-Id": "cth", "X-Product-Id": "BMP"},
    {"X-Domain-Id": " "}, {"X-Brand-Key": "nike"},
    {"X-Domain-Id": "system", "X-Subject-Id": "GUANGZHOU_TAIKOO_HUI"},
])
def test_bad_context_is_rejected_before_handler_and_next_request_is_global(client, headers):
    response = client.get("/context", headers=headers)
    assert response.status_code == 400
    assert "scope" not in response.json
    assert client.get("/context").json["domain"]["subject_id"] == ""


def test_session_and_query_are_whole_pairs_not_mixed_with_header(client):
    with client.session_transaction() as session:
        session["domain_id"] = "cth"
        session["product_id"] = "CTH"
        session["brand_key"] = "guangzhou_taikoo_hui"
    assert client.get("/context").json["domain"]["domain_id"] == "cth"
    response = client.get("/context?domain_id=cth", headers={"X-Product-Id": "BMP"})
    assert response.status_code == 200
    assert response.json["domain"]["product_id"] == "ZBMP"
    assert response.json["domain"]["brand_key"] == ""


def test_global_legacy_filter_cannot_return_reference_rows(client):
    import subject_rules
    app = client.application
    # Evaluate the same SQL/keyword compatibility path inside its actual hook.
    with app.test_request_context("/context"):
        assert app.preprocess_request() is None
        assert subject_rules.subject_hit(title="广州太古汇") is False
        with pytest.raises(ValueError, match="LEGACY_SUBJECT_SCOPE_REQUIRED"):
            subject_rules.subject_sql_and_values()


def test_domain_only_does_not_create_subject():
    for domain in ("cth", "bmp", "system"):
        ctx = DomainContext.from_domain(domain)
        assert ctx.brand_key == ctx.subject_id == ""
        assert ctx.to_subject_context().subject_id == ""


def test_explicit_nested_scope_restores_both_identities_after_error():
    from subject_context import brand_scope, get_subject_context
    from domain_isolation import get_domain_context
    with brand_scope("other_venue", product_id="CTH"):
        with pytest.raises(RuntimeError):
            with brand_scope("nike", product_id="BMP"):
                assert get_domain_context().product_id == get_subject_context().product_id == "ZBMP"
                raise RuntimeError("interrupted")
        assert get_domain_context().domain_id == "cth"
        assert get_subject_context().brand_key == "other_venue"
    assert get_domain_context() is None
    assert get_subject_context().subject_id == ""
@pytest.mark.parametrize("subject", ["", "   ", "\t", "subject\x7f"])
def test_explicit_invalid_subject_never_reaches_reader(subject):
    from flask import Flask
    from subject_context import init_app

    app = Flask(__name__)
    app.secret_key = "isolated-subject-validation"
    init_app(app)
    calls = []

    @app.get("/probe")
    def probe():
        calls.append(True)
        return {"ok": True}

    response = app.test_client().get(
        "/probe", headers={"X-Domain-Id": "cth", "X-Subject-Id": subject})
    assert response.status_code == 400
    assert response.get_json()["error"] == "INVALID_SUBJECT_ID"
    assert calls == []
