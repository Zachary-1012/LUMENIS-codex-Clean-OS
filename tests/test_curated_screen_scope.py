import pytest
from flask import Flask

import database
import experience_runtime as runtime
import experience_screens as screens


def binding(domain):
    return {"contract": "lumenis.scope-read-binding.v1", "scope_verified": True,
            "read_allowed": True, "domain_id": domain, "canonical_scope": "FOCUS",
            "subject_id": "SUBJECT-A", "brand_focus_id": "BRAND-A" if domain == "BMP" else None}


@pytest.mark.parametrize("sid,domain", [("CTH-04", "CTH"), ("CTH-08", "CTH"), ("BMP-10", "BMP")])
def test_curated_screen_route_preserves_verified_scope(monkeypatch, sid, domain):
    selected = binding(domain)
    monkeypatch.setattr(runtime, "_cth03_read_scope", lambda: (selected, None))
    monkeypatch.setattr(runtime, "_bmp01_read_scope", lambda: (selected, None))
    monkeypatch.setattr(runtime, "_all_builders", lambda: screens.SCREEN_BUILDERS)
    seen = []

    def read_events(limit, *, scope):
        seen.append(scope)
        return {"featured": [{"event_id": "E-A", "title": "Scoped event", "mention_count": 2}],
                "rejected_count": 0}

    def read_sources(scope, **kwargs):
        seen.append(scope)
        return {"sources": [{"note_id": "N-A", "risk_level": "high"}],
                "truncated": False, "rejected_count": 0}

    monkeypatch.setattr(database, "get_events_curated", read_events)
    monkeypatch.setattr(database, "get_scoped_event_source_rows", read_sources)
    monkeypatch.setattr(database, "get_high_risk_notes", lambda *a, **k: pytest.fail("unscoped risk read"))
    app = Flask(__name__)
    app.register_blueprint(runtime.experience_bp)
    response = app.test_client().get("/api/experience/screen/" + sid)
    assert response.status_code == 200, response.get_json()
    assert seen
    for scope in seen:
        assert scope["global_scope"] is False
        assert scope["domain_id"] == ("cth" if domain == "CTH" else "zbmp")
        assert scope["subject_id"] == ("SUBJECT-A" if domain == "CTH" else None)
        assert scope["brand_focus_id"] == ("BRAND-A" if domain == "BMP" else None)
    assert any(section.get("items") for section in response.get_json()["sections"] if section["type"] == "events")


@pytest.mark.parametrize("builder,domain", [(screens._build_cth04, "CTH"), (screens._build_cth08, "CTH"), (screens._build_bmp10, "BMP")])
def test_curated_screen_read_failure_is_not_empty_success(monkeypatch, builder, domain):
    def fail(*args, **kwargs):
        raise OSError("isolated read failure")
    monkeypatch.setattr(database, "get_events_curated", fail)
    with pytest.raises(OSError):
        builder(binding=binding(domain))
    with pytest.raises(ValueError, match="EVENT_SCOPE_BINDING_REQUIRED"):
        builder(binding=binding("BMP" if domain == "CTH" else "CTH"))


def test_act_advice_uses_exact_scope_without_provider_or_completed_action():
    from lumenis.shared.reporting.routes import generate_act_strategies
    scope = {"domain_id": "cth", "subject_id": "SUBJECT-A", "brand_focus_id": None, "global_scope": False}
    result = generate_act_strategies("User supplied event description", scope=scope)
    assert result["scope"]["subject_id"] == "SUBJECT-A"
    assert result["claim_type"] == "ADVISORY"
    assert result["provider"] == "deterministic"
    assert result["ai_status"] == "UNAVAILABLE"
    assert result["strategies"]
    assert not any("已成立" in item or "已第一时间" in item for item in result["strategies"])
    with pytest.raises(ValueError):
        generate_act_strategies("description")


@pytest.mark.parametrize("payload", [["event"], {"event_info": 7},
                                   {"event_info": "   "},
                                   {"event_info": "event", "trigger_reasons": [None]}])
def test_act_route_rejects_invalid_user_input_before_case_lookup(monkeypatch, payload):
    from lumenis.shared.reporting import routes
    monkeypatch.setattr(routes, "_authorized_report_scope", lambda: (None, {}, [], None))
    app = Flask(__name__)
    app.register_blueprint(routes.report_bp)
    response = app.test_client().post('/api/report/special/generate-strategies', json=payload)
    assert response.status_code == 400
    assert response.get_json()['ok'] is False
