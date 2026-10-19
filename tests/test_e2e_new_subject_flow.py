"""E2E: a user-added Subject runs the product flow.

add_subject (sanctioned registry write) -> DB row -> official name with source
-> registry-wide acquisition plan targets it -> collected note verified for
that subject (not Taikoo-only) -> persisted -> visible to product readers.
Brand: Swire Properties / 太古地产, official site https://www.swireproperties.com/zh-cn/ .
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest


@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "e2e.sqlite3"))
    import subject_registry as registry
    registry._NAMES_CACHE.update(at=0.0, names=())
    return registry


def test_new_subject_full_product_flow(reg):
    row, created = reg.add_subject({"domain_id": "CTH", "subject_type": "company",
                                    "name_en": "Swire Properties", "name_zh": "Swire Properties",
                                    "industry": "real estate", "keywords": []})
    assert created and row["subject_id"].startswith("SUBJ-")
    official = reg.record_official_name("CTH", row["subject_id"],
                                        source_url="https://www.swireproperties.com/zh-cn/",
                                        name_zh="太古地产")
    assert official["after"]["name_zh"] == "太古地产"
    assert official["after"]["subject_id"] == row["subject_id"]

    # Visible in product registry readers and in registry-derived names.
    listed = {s["subject_id"]: s for s in reg.list_subjects("CTH")}
    assert listed[row["subject_id"]]["name_zh"] == "太古地产"
    assert "太古地产" in reg.registered_subject_names()

    # Collection scope = all registered subjects: the plan targets the new subject.
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    plan = build_acquisition_plan(None, registry_loader=lambda: reg.list_subjects())
    targeted = [q for q in plan.queries if q.subject_id == row["subject_id"]]
    assert targeted, plan.to_dict()

    # Collected note is verified against its own subject, not the Taikoo-only filter.
    import xhs_cookie_bridge as bridge
    q = targeted[0]
    note = {"note_id": f"e2e-{uuid.uuid4().hex[:10]}", "title": f"{q.keyword} 新项目开幕",
            "content": f"{q.keyword} 今天发布", "source_keyword": q.keyword}
    ok, reason = bridge._verify_note_for_query(note, q)
    assert ok, reason
    bad_ok, _ = bridge._verify_note_for_query({"title": "无关", "content": "无关"}, q)
    assert not bad_ok


def test_disabled_subject_is_not_collected(reg):
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    rows = [{"domain_id": "CTH", "subject_type": "company", "subject_id": "SUBJ-x",
             "name_en": "Disabled Co", "name_zh": "停用公司", "keywords": [], "status": "disabled"}]
    plan = build_acquisition_plan(None, registry_loader=lambda: rows)
    assert not [q for q in plan.queries if q.subject_id == "SUBJ-x"]


def test_registered_subject_and_new_alias_enter_current_signed_service_plan(reg, tmp_path):
    row, created = reg.add_subject({"domain_id": "CTH", "subject_type": "company",
                                    "name_en": "Swire Properties", "name_zh": "太古地产",
                                    "industry": "real estate", "keywords": []})
    assert created and row["status"] == "configured"

    from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
        PURPOSE_POLICY,
        _canonical_config,
        load_prelaunch_baseline_config,
    )

    key = "isolated-dynamic-plan-signature"
    config = {
        "schema_version": 1, "enabled": True, "end_user_auto": False,
        "internal_auto_opt_in": True, "policy_id": PURPOSE_POLICY,
        "plan_version": "registered-entity-service-v1", "sources": [],
        "registry_expansion": {
            "schema_version": 1, "source_version": "registered-subjects-v1",
            "scope_version": "current-registry-v1",
            "authorization_ref": "isolated-approved-cth-purpose-scope",
            "cadence_seconds": 3600, "max_results": 1,
            "templates": [{
                "domain_id": "CTH", "purpose": "Review commercial venue activity",
                "dimension": "venue_operations", "platforms": ["x"],
                "acquisition_stage": "SUBJECT_INTAKE",
            }],
        },
    }
    config_path = tmp_path / "signed-registry-expansion.json"

    def save_signed():
        config["hmac"] = {
            "algorithm": "HMAC-SHA256",
            "value": hmac.new(key.encode(), _canonical_config(config), hashlib.sha256).hexdigest(),
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    save_signed()
    loaded = load_prelaunch_baseline_config(
        str(config_path), hmac_key=key, registry_loader=reg.list_subjects)
    old_plans = [plan for plan in loaded["plans"] if plan.subject_id == row["subject_id"]]
    assert old_plans
    assert all(plan.policy_id == PURPOSE_POLICY and plan.end_user_auto is False for plan in old_plans)
    old_ids = {plan.plan_id for plan in old_plans}

    update = reg.record_official_name(
        "CTH", row["subject_id"], source_url="https://www.swireproperties.com/zh-cn/",
        keywords=["太古地产商业物业"],
    )
    assert update["changed"] is True
    refreshed = load_prelaunch_baseline_config(
        str(config_path), hmac_key=key, registry_loader=reg.list_subjects)
    refreshed_plans = [plan for plan in refreshed["plans"] if plan.subject_id == row["subject_id"]]
    assert old_ids <= {plan.plan_id for plan in refreshed_plans}
    assert any("太古地产商业物业" in plan.purpose_query["keyword"] for plan in refreshed_plans)
