"""Focused contract tests for the single Shared Content & Creation surface."""
from __future__ import annotations

import importlib

import pytest

from lumenis_shared_skills import (
    SHARED_SKILL_CATALOG,
    list_shared_skills,
    run_shared_skill,
)
from skill_registry import SkillMetadata, get_skill_registry


EXPECTED_TOOLS = {
    "union-search-skill",
    "video-shotcraft",
    "cangjie-skill",
    "huashu-skills",
    "quizang-social-card-skill",
    "last30days-skill",
}


@pytest.fixture()
def shared_client(tmp_path, monkeypatch):
    """Mount only the experience blueprint against an OS-temporary database."""
    db_file = tmp_path / "shared_skill_runtime.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_file))
    monkeypatch.setenv("ZBC_TEST_OFFLINE", "1")

    import database

    importlib.reload(database)
    database.DB_PATH = str(db_file)
    database.init_db()

    import evidence_store

    evidence_store.DB_PATH = str(db_file)

    from flask import Flask
    import experience_runtime

    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    return app.test_client()


def test_six_tools_are_one_shared_capability_surface():
    records = list_shared_skills()
    assert {record["tool_name"] for record in records} == EXPECTED_TOOLS
    assert {record["product"] for record in records} == {"SHARED"}
    assert {tuple(record["consumers"]) for record in records} == {("CTH", "BMP")}
    assert all(record["domain"] == "content" for record in records)


def test_shared_metadata_passes_skill_registry_contract():
    registry = get_skill_registry()
    for item in SHARED_SKILL_CATALOG:
        metadata = SkillMetadata.from_dict(item["metadata"])
        result = registry.validate(metadata)
        assert result["valid"], (metadata.skill_id, result)
        assert registry.get(metadata.skill_id) is not None


def test_local_draft_adapters_do_not_need_external_sites():
    card = run_shared_skill(
        "shared.social_card", "序境的事实入口", {"title": "序境的事实入口"}
    )
    assert card["status"] == "completed"
    assert card["artifact_type"] == "svg_draft"
    assert "external" not in card["svg"].lower()
    assert card["approval_required"] is True

    storyboard = run_shared_skill(
        "shared.video_shotcraft", "开场展示问题，随后给出证据和行动", {}
    )
    assert storyboard["status"] == "completed"
    assert storyboard["external_media_fetch"] is False
    assert storyboard["approval_required"] is True

    structure = run_shared_skill(
        "shared.cangjie", "", {"text": "# 事实\n\n证据段落。\n\n## 结论\n\n行动段落。"}
    )
    assert structure["status"] == "completed"
    assert structure["structure"]["section_count"] == 2


def test_shared_route_contract_is_read_and_plan_only():
    from pathlib import Path

    source = Path("experience_runtime.py").read_text(encoding="utf-8")
    assert "/api/experience/shared-skills" in source
    assert '"READ", "ANALYZE", "SUGGEST"' in source
    assert "SHARED_ACTION_NOT_ALLOWED" in source
    assert "写入、发布和推送必须走人工审批链" in source


def test_shared_route_runs_on_bmp_through_evidence_chain(shared_client):
    response = shared_client.post(
        "/api/experience/shared-skills/shared.social_card/run",
        json={
            "action_type": "SUGGEST",
            "task": "为序境生成一个事实入口草稿",
            "input": {"title": "序境 · Evidence First"},
            "domain": "BMP",
        },
    )
    payload = response.get_json()
    assert response.status_code == 200, payload
    assert payload["status"] == "completed", payload
    assert payload["evidence_recorded"] is True, payload
    assert payload["external_fetch"] is False
    assert payload["ai_is_derivative"] is True
    assert payload["result"]["artifact_type"] == "svg_draft"


def test_shared_route_rejects_write_and_unknown_domain(shared_client):
    write = shared_client.post(
        "/api/experience/shared-skills/shared.social_card/run",
        json={"action_type": "WRITE", "task": "publish", "input": {"title": "x"}},
    )
    assert write.status_code == 403
    assert write.get_json()["code"] == "SHARED_ACTION_NOT_ALLOWED"

    unknown = shared_client.post(
        "/api/experience/shared-skills/shared.social_card/run",
        json={"action_type": "SUGGEST", "task": "x", "domain": "NEW_PRODUCT"},
    )
    assert unknown.status_code == 400
    assert unknown.get_json()["code"] == "DOMAIN_NOT_ALLOWED"
