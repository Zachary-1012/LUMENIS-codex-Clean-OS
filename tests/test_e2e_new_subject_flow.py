"""E2E: a user-added Subject runs the product flow.

add_subject (sanctioned registry write) -> DB row -> official name with source
-> registry-wide acquisition plan targets it -> collected note verified for
that subject (not Taikoo-only) -> persisted -> visible to product readers.
Brand: Swire Properties / 太古地产, official site https://www.swireproperties.com/zh-cn/ .
"""
from __future__ import annotations

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
