"""Scoped BMP authors and comparisons never use legacy cross-domain profiles."""
import pytest
from tests.test_bmp01_scope_viewmodel import bmp_client, _record

@pytest.mark.parametrize("screen", ["BMP-03", "BMP-05", "BMP-11"])
def test_scoped_author_and_comparison_api(bmp_client, monkeypatch, screen):
    client, state = bmp_client
    import experience_runtime as runtime
    import experience_screens as screens
    state["records"] = [{**_record(), "author_id": "user-1", "author_name": "Allowed author"},
                        {**_record("BRAND-OTHER"), "title": "PRIVATE OTHER", "author_id": "other", "author_name": "PRIVATE AUTHOR"}]
    monkeypatch.setattr(runtime, "_all_builders", lambda: {"BMP-03": screens._build_bmp03, "BMP-05": screens._build_bmp05, "BMP-11": screens._build_bmp11})
    response = client.get("/api/experience/screen/" + screen, headers={
        "X-Lumenis-Context-Mode": "FOCUS", "X-Domain-Id": "BMP", "X-Subject-ID": "SUBJ-NIKE"})
    assert response.status_code == 200, response.get_json()
    assert "PRIVATE" not in response.get_data(as_text=True)
    assert response.get_json()["truth"]["source_count"] == 1


def test_profiles_unknown_metrics_are_not_zero(bmp_client):
    _, state = bmp_client
    import kos_engine
    state["records"][0].update(author_id="one", author_name="", engagement_comments=None)
    binding = {"contract": "lumenis.scope-read-binding.v1", "domain_id": "BMP", "product_id": "ZBMP",
               "read_allowed": True, "scope_verified": True, "canonical_scope": "FOCUS", "brand_focus_id": "BRAND-NIKE"}
    result = kos_engine.read_scoped_profiles(binding)
    assert result["profiles"][0]["total_engagement"] is None
    assert result["profiles"][0]["kos_score"] is None
    with pytest.raises(ValueError):
        kos_engine.read_scoped_profiles({**binding, "read_allowed": False})

@pytest.mark.parametrize("path", ["overview", "list", "detail?author_id=user-1", "content-dna?author_id=user-1", "account?author_id=user-1", "ownership", "competitor-benchmark", "kos-identity?author_id=user-1", "tier", "koc-tier", "ad-candidates"])
def test_production_kos_reads_use_same_scope(bmp_client, monkeypatch, path):
    client, state = bmp_client
    import kos_routes
    state["records"] = [{**_record(), "author_id": "user-1", "author_name": "Allowed author"},
                        {**_record("BRAND-OTHER"), "author_id": "other", "author_name": "PRIVATE OTHER"}]
    client.application.register_blueprint(kos_routes.kos_bp)
    response = client.get("/api/kos/" + path, headers={
        "X-Lumenis-Context-Mode": "FOCUS", "X-Domain-Id": "BMP", "X-Subject-ID": "SUBJ-NIKE"})
    assert response.status_code == 200, response.get_json()
    assert "PRIVATE OTHER" not in response.get_data(as_text=True)
    client.application.config["LUMENIS_OPEN_WORKSPACE"] = False
    denied = client.get("/api/kos/" + path)
    assert denied.status_code == 401


def test_propagation_scope_never_borrows_legacy_heat(bmp_client, monkeypatch):
    client, state = bmp_client
    import database
    import experience_runtime as runtime
    import experience_screens as screens
    # The classification owner now verifies the registered scope on read.
    import subject_registry
    from lumenis.shared.database import get_repository
    with get_repository().transaction() as connection:
        subject_registry.ensure_schema(connection)
        connection.execute("""INSERT INTO lumenis_subject_registry
            (subject_id,brand_focus_id,domain_id,subject_type,name_en,name_zh,
             name_en_norm,name_zh_norm,status,created_at,updated_at)
            VALUES ('SUBJ-NIKE','BRAND-NIKE','BMP','brand','Nike','耐克',
                    'nike','耐克','configured','2026-10-21','2026-10-21')""")
    observed = []
    def events(limit, *, scope):
        observed.append(scope)
        return {"featured": [], "total": 0, "read_complete": True,
                "rejected_count": 0, "scanned_count": 0, "returned_count": 0, "truncated": False}
    monkeypatch.setattr(database, 'get_events_curated', events)
    monkeypatch.setattr(runtime, '_all_builders', lambda: {'BMP-04': screens._build_bmp04})
    response = client.get('/api/experience/screen/BMP-04', headers={
        'X-Lumenis-Context-Mode':'FOCUS','X-Domain-Id':'BMP','X-Subject-ID':'SUBJ-NIKE'})
    assert response.status_code == 200, response.get_json()
    assert observed[0]['brand_focus_id'] == 'BRAND-NIKE'
    assert response.get_json()['truth']['classification_state'] == 'EMPTY'
    assert response.get_json()['truth']['heat'] is None
    assert response.get_json()['truth']['source_count'] == 1
