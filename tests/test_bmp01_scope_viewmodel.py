"""BMP-01 exact BrandFocus route/projection acceptance."""
import sqlite3

import pytest
from flask import Flask


def _record(brand_focus="BRAND-NIKE"):
    return {
        "canonical_id": "can-nike-1", "brand_focus_id": brand_focus,
        "title": "Nike signal", "content": "Observed source",
        "publish_datetime": "2026-09-29T00:00:00Z",
        "captured_at": "2026-09-29 12:00:00", "source_platform": "x",
        "canonical_url": "https://example.com/nike", "url": "",
        "quality_status": "ok", "sentiment": "neutral", "risk_level": "low",
        "engagement_likes": 4, "engagement_comments": 2,
        "engagement_collects": 1, "engagement_shares": 1,
        "scope_evidence": {
            "id": 9, "source_id": "raw-nike-1",
            "stored_scope": {
                "product_id": "ZBMP", "domain_id": "zbmp",
                "subject_id": "", "brand_focus_id": brand_focus,
            },
            "integrity": {
                "integrity_version": 2, "verified": True, "lineage_verified": True,
                "algorithm": "hmac-sha256", "assurance": "writer-authenticated",
                "digest": "b" * 64,
            },
        },
    }
@pytest.fixture
def bmp_client(tmp_path, monkeypatch):
    path = tmp_path / "bmp.sqlite3"
    sqlite3.connect(path).close()
    monkeypatch.setenv("ZBC_DB_PATH", str(path))

    import canonical_data
    import experience_runtime as runtime
    import experience_screens as screens
    import lumenis.auth.service as auth
    import subject_registry

    state = {"reads": [], "records": [_record()]}

    def read_rows(con, *, product_id, brand_focus_id, limit):
        state["reads"].append((product_id, brand_focus_id, limit))
        rows = [r for r in state["records"] if r["brand_focus_id"] == brand_focus_id]
        return {
            "records": rows, "returned_count": len(rows), "scanned_count": len(rows),
            "candidate_count": len(rows), "limit": limit,
            "rejected_count": 0, "truncated": False,
        }

    monkeypatch.setattr(canonical_data, "list_scoped_canonical", read_rows)
    monkeypatch.setattr(runtime, "_all_builders", lambda: {"BMP-01": screens._build_bmp01})
    monkeypatch.setattr(auth, "get_current_user", lambda **_kwargs: None)
    def subject(domain, subject_id):
        if domain == "BMP" and subject_id == "SUBJ-NIKE":
            return {
                "subject_id": subject_id, "brand_focus_id": "BRAND-NIKE",
                "subject_type": "brand", "name_en": "Nike", "name_zh": "耐克",
            }
        return None

    monkeypatch.setattr(subject_registry, "get_subject_by_id", subject)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(runtime.experience_bp)
    return app.test_client(), state


def test_focus_reads_only_exact_verified_brand_scope(bmp_client):
    client, state = bmp_client
    headers = {
        "X-Lumenis-Context-Mode": "FOCUS",
        "X-Domain-Id": "BMP",
        "X-Subject-ID": "SUBJ-NIKE",
    }
    response = client.get("/api/experience/screen/BMP-01", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert state["reads"] == [("ZBMP", "BRAND-NIKE", 100)]
    binding = body["focus_binding"]
    assert binding["contract"] == "lumenis.scope-read-binding.v1"
    assert binding["module"] == "brand_market_overview"
    assert binding["subject_id"] == "SUBJ-NIKE"
    assert binding["brand_focus_id"] == "BRAND-NIKE"
    assert binding["read_allowed"] is True
    assert binding["scope_verified"] is True
    assert body["focus_context"]["display_name"]["en"] == "Nike"
    assert body["truth"]["canonical_count"] == 1
    assert body["truth"]["data_state"] == "READY"

    kpis = next(section for section in body["sections"] if section["type"] == "kpis")
    values = {item["id"]: item["value"] for item in kpis["items"]}
    assert values["bmp01.total"] == 1
    assert values["bmp01.neg"] == 0
    assert values["bmp01.high"] == 0
    assert values["bmp01.eng"] == 8


def test_wrong_or_missing_focus_never_reads_canonical(bmp_client):
    client, state = bmp_client
    response = client.get("/api/experience/screen/BMP-01", headers={
        "X-Lumenis-Context-Mode": "FOCUS",
        "X-Domain-Id": "BMP",
        "X-Subject-ID": "SUBJ-MISSING",
    })
    assert response.status_code == 404
    assert state["reads"] == []


def test_truncated_rows_do_not_claim_global_total_or_partial_engagement(bmp_client, monkeypatch):
    client, state = bmp_client
    state["records"][0]["engagement_comments"] = None
    original = state["records"]

    import canonical_data

    def truncated_rows(con, *, product_id, brand_focus_id, limit):
        return {
            "records": original, "returned_count": 1, "scanned_count": 2,
            "candidate_count": 2, "limit": limit, "rejected_count": 0,
            "truncated": True,
        }

    # Replace only the read boundary for this assertion; the permission and
    # exact BrandFocus resolution remain the same as the prior real-scope test.
    monkeypatch.setattr(canonical_data, "list_scoped_canonical", truncated_rows)
    response = client.get("/api/experience/screen/BMP-01", headers={
        "X-Lumenis-Context-Mode": "FOCUS", "X-Domain-Id": "BMP",
        "X-Subject-ID": "SUBJ-NIKE",
    })
    body = response.get_json()
    kpis = next(section for section in body["sections"] if section["type"] == "kpis")
    values = {item["id"]: item for item in kpis["items"]}
    assert values["bmp01.total"]["value"] is None
    assert values["bmp01.total"]["label"] == "已返回记录"
    assert values["bmp01.eng"]["value"] is None
    assert body["truth"]["truncated"] is True
    assert body["truth"]["engagement_complete"] is False


def test_global_uses_signed_canonical_reader(bmp_client, monkeypatch):
    client, state = bmp_client
    import canonical_data
    import api_dual_domain
    monkeypatch.setattr(api_dual_domain, "get_zbmp_product_snapshot", lambda: pytest.fail("legacy unsigned global reader"))
    def read_rows(con, *, product_id, brand_focus_id, limit):
        assert product_id == "ZBMP" and brand_focus_id is None
        return {"records": state["records"], "truncated": False}
    monkeypatch.setattr(canonical_data, "list_scoped_canonical", read_rows)
    response = client.get("/api/experience/screen/BMP-01")
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result["global_binding"]["canonical_scope"] == "GLOBAL_ALL"
    assert result["truth"]["canonical_count"] == 1
