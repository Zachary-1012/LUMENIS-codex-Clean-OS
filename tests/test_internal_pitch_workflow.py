"""Real owner/file/transaction regressions in disposable databases."""
import copy
import hashlib
import io
import json

import pytest
from docx import Document
from flask import Flask

from lumenis.shared.database import DatabaseRepository
from lumenis.shared.content_creation import internal_pitch as pitch
from lumenis.shared.reporting import saved_work as work
from lumenis.system.security import permission


@pytest.fixture
def workspace(tmp_path, monkeypatch, request):
    path = tmp_path / "internal-pitch.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    import ai_task_engine
    import shared_artifacts
    import subject_registry
    repository = DatabaseRepository(str(path))
    for module in (ai_task_engine, shared_artifacts, work, pitch):
        monkeypatch.setattr(module, "get_repository", lambda: repository)
    with repository.connection() as con:
        con.executescript(ai_task_engine._TASK_ENGINE_SCHEMA)
        subject_registry.ensure_schema(con)
        con.execute("INSERT INTO lumenis_subject_registry (subject_id,brand_focus_id,domain_id,subject_type,name_en,name_zh,name_en_norm,name_zh_norm,status,created_at,updated_at) VALUES ('SUBJ-PITCH',NULL,'CTH','company','Pitch Center','Center','pitch center','center','configured','2026-10-03T00:00:00Z','2026-10-03T00:00:00Z')")
        con.commit()
    shared_artifacts.ensure_artifact_table()
    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    pitch.engine.cache_clear()
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", headers={"Host": "localhost"},
                                  environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        actor = permission.resolve_local_workspace_principal(module="reports", action="write")
        scope = {"domain_id": "cth", "subject_id": "SUBJ-PITCH", "brand_focus_id": None, "global_scope": False}
        if getattr(request, "param", "domain") == "shared":
            with repository.connection() as con:
                con.execute("DELETE FROM lumenis_subject_registry")
                con.commit()
            scope = {"scope_kind": "shared_workspace", "version": 1}
        yield {"repo": repository, "actor": actor, "scope": scope, "app": app, "gate": gate, "root": tmp_path}
    pitch.engine.cache_clear()


def arguments(ws, request="request-0001"):
    from lumenis.shared.content_creation.contracts import Shot, ShotPlan
    return {"manuscript": {"title": "Internal questions", "summary": "Questions for internal review.",
             "sections": [{"heading": "Original text", "body": "What changed? No change is also a valid answer."}],
             "language": "en", "authorship": "user_supplied"},
            "shot_plan": ShotPlan((Shot(shot_purpose="Review the open question", duration_sec=8),)).to_dict(),
            "request_id": request, "actor": ws["actor"], "scope": ws["scope"]}


def prepare(ws, request="request-0001", **changes):
    values = arguments(ws, request)
    values.update(changes)
    return pitch.prepare_internal_pitch(**values)


def run(ws, task):
    return pitch.run_internal_pitch(task["task_id"], actor=ws["actor"], scope=ws["scope"])


def count(ws):
    return ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]


def audiovisual_arguments(ws, request="av-plan-0001"):
    values = arguments(ws, request)
    declared = {"kind": "USER_EXPLICIT", "locator": "current_user_brief"}
    unknown = {"kind": "UNKNOWN", "locator": None}
    values["profile"] = pitch.AV_PLAN_PROFILE
    values["shot_plan"] = {
        "schema": "lumenis.audiovisual-plan/v1", "brief_text": "保留手部三个关键操作，35秒竖屏完全静音。",
        "method_source": {"reference": "dot-av-v2", "sha256": "a" * 64},
        "outputs": [{"output_id": "silent-craft", "medium": "video", "purpose": "三个关键操作清晰可读",
                     "canvas_ratio": "9:16", "duration": {"min_seconds": 35, "max_seconds": 35,
                                                              "tolerance_seconds": 0},
                     "sound": {name: "forbidden" for name in ("original", "voice", "music")},
                     "languages": ["zh"], "constraints": {"must_preserve": ["hands", "tools", "causality"]},
                     "provenance": {name: dict(declared) for name in
                                    ("purpose", "canvas_ratio", "duration", "languages", "constraints", "original", "voice", "music")},
                     "plan": None}],
        "rule_assessments": [{"rule_ref": "dot-av-v2:R10", "output_ids": ["silent-craft"],
                              "required_conditions": [{"predicate": "same_action_chain_verified", "value": None,
                                                       "provenance": unknown}], "exclusions": []}],
    }
    return values


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_audiovisual_profile_persists_reopens_revises_and_downloads_without_media_claim(workspace):
    ws = workspace
    args = audiovisual_arguments(ws)
    first = run(ws, pitch.prepare_internal_pitch(**args))
    document = first["work"]["document"]
    assert document["contract"] == pitch.AV_PLAN_CONTRACT
    plan = document["payload"]["audiovisual_plan"]
    assert plan["input"] == args["shot_plan"]
    assert plan["rule_decisions"][0]["decision"] == "NEEDS_REVIEW"
    assert plan["execution"] == "NOT_EXECUTED" and plan["rendition_binding"] is None
    assert set(plan["reviews"].values()) == {"NEEDS_REVIEW"}
    assert document["citations"] == []
    downloaded = pitch.download_internal_pitch(first["task_id"], actor=ws["actor"], scope=ws["scope"])
    assert hashlib.sha256(downloaded["content"]).hexdigest() == first["action_receipt"]["output"]["sha256"]
    assert Document(io.BytesIO(downloaded["content"])).paragraphs
    revised = audiovisual_arguments(ws, "av-plan-0002")
    revised["shot_plan"]["brief_text"] += " 允许按动作调整镜头顺序。"
    revised["shot_plan"]["outputs"][0]["constraints"]["preserve_order"] = False
    second = run(ws, pitch.prepare_internal_pitch(**revised, work_id=document["work_id"],
                previous_artifact_id=first["action_receipt"]["artifact_id"],
                expected_draft_digest=document["draft_digest"]))
    assert second["action_receipt"]["version"] == 2
    assert second["action_receipt"]["parent_sha256"] == first["action_receipt"]["sha256"]
    new_plan = second["work"]["document"]["payload"]["audiovisual_plan"]
    assert new_plan["brief_sha256"] != plan["brief_sha256"]
    reopened = pitch.read_internal_pitch(first["task_id"], actor=ws["actor"], scope=ws["scope"])
    assert reopened["work"]["document"]["payload"]["audiovisual_plan"] == plan
    assert run(ws, first)["action_receipt"] == first["action_receipt"]
    assert count(ws) == 4


def test_audiovisual_changed_brief_cannot_reuse_request_or_erase_unknowns(workspace):
    args = audiovisual_arguments(workspace)
    task = pitch.prepare_internal_pitch(**args)
    args["shot_plan"]["brief_text"] += " Changed."
    with pytest.raises(ValueError, match="INTERNAL_PITCH_REQUEST_REUSE_CONFLICT"):
        pitch.prepare_internal_pitch(**args)
    cancelled = pitch.cancel_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert cancelled["state"] == "cancelled" and count(workspace) == 0


@pytest.mark.parametrize("reference", ["brief", "plan_evidence", "shot_evidence", "podcast_evidence"])
def test_audiovisual_unbound_source_references_cannot_create_task(workspace, reference):
    from lumenis.shared.content_creation.contracts import Shot, ShotPlan
    args = audiovisual_arguments(workspace)
    plan = ShotPlan((Shot(shot_purpose="Show the permitted action", duration_sec=35),)).to_dict()
    if reference == "brief":
        plan["brief_ref"] = "unbound-brief"
    elif reference == "plan_evidence":
        plan["evidence_refs"] = ["unbound-evidence"]
    elif reference == "shot_evidence":
        plan["shots"][0]["evidence_refs"] = ["unbound-evidence"]
    output = args["shot_plan"]["outputs"][0]
    if reference == "podcast_evidence":
        from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment
        plan = PodcastPlan("Interview", "Preserve original speech", "zh", (
            PodcastSegment("segment-1", "UNRESOLVED_MEDIA", 0, 35, "原话", "原话", "Guest",
                           "Opening", ("unbound-evidence",)),
        )).to_dict()
        output.update(medium="podcast", canvas_ratio=None)
        output["provenance"]["canvas_ratio"] = {"kind": "UNKNOWN", "locator": None}
        output["sound"]["original"] = "required"
    output["plan"] = plan
    with pytest.raises(ValueError, match="INTERNAL_PITCH_SOURCE_BINDING_REQUIRED"):
        pitch.prepare_internal_pitch(**args)
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM ai_task")[0] == 0
    assert count(workspace) == 0


def test_shared_pitch_pending_read_cancel_has_no_domain_or_subject_prerequisite(workspace):
    ws = workspace
    with ws["repo"].connection() as con:
        con.execute("DELETE FROM lumenis_subject_registry")
        con.commit()
    scope = {"scope_kind": "shared_workspace", "version": 1}
    args = arguments(ws, "shared-plan-0001")
    args.update(scope=scope, profile=pitch.AUTHORING_PROFILE)
    args.pop("shot_plan")
    prepared = pitch.prepare_internal_pitch(**args)
    assert prepared["scope"] == scope and prepared["state"] == "pending"
    assert pitch.read_internal_pitch(prepared["task_id"], actor=ws["actor"], scope=scope)["scope"] == scope
    cancelled = pitch.cancel_internal_pitch(prepared["task_id"], actor=ws["actor"], scope=scope)
    assert cancelled["state"] == "cancelled" and count(ws) == 0


@pytest.mark.parametrize("extra", [{"actor_id": 1}, {"domain_id": "cth"}, {"version": True}])
def test_shared_pitch_selector_rejects_identity_domain_and_bool_without_task(workspace, extra):
    args = arguments(workspace)
    args["scope"] = {"scope_kind": "shared_workspace", "version": 1, **extra}
    with pytest.raises((ValueError, PermissionError), match="SHARED_WORKSPACE_SCOPE_INVALID"):
        pitch.prepare_internal_pitch(**args)
    assert count(workspace) == 0


def test_shared_pitch_does_not_admit_source_bound_scope_without_source_domain(workspace):
    args = arguments(workspace)
    args.pop("shot_plan")
    args.update(scope={"scope_kind": "shared_workspace", "version": 1}, profile=pitch.SOURCE_PROFILE,
                upstream_ref={"kind": "saved_work", "artifact_id": "not-a-grant"})
    with pytest.raises(ValueError, match="INTERNAL_PITCH_UPSTREAM_SOURCE_SCOPE_REQUIRED"):
        pitch.prepare_internal_pitch(**args)
    assert count(workspace) == 0


@pytest.mark.parametrize("workspace", ["shared"], indirect=True)
def test_shared_pitch_authored_document_revision_download_and_old_version(workspace):
    ws = workspace
    args = arguments(ws, "shared-author-0001")
    args.pop("shot_plan")
    args["profile"] = pitch.AUTHORING_PROFILE
    first = run(ws, pitch.prepare_internal_pitch(**args))
    parent = first["work"]["document"]
    receipt = first["action_receipt"]
    assert first["scope"] == ws["scope"]
    assert parent["contract"] == pitch.AUTHORING_CONTRACT
    assert parent["payload"]["truth_state"]["owned_model_execution"] == "NOT_RUN"
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_subject_registry")[0] == 0
    rows = ws["repo"].query_all("SELECT product_id,domain_id FROM lumenis_shared_artifacts")
    assert {tuple(row) for row in rows} == {("SHARED", "content")}
    downloaded = pitch.download_internal_pitch(first["task_id"], actor=ws["actor"], scope=ws["scope"])
    assert hashlib.sha256(downloaded["content"]).hexdigest() == receipt["output"]["sha256"]
    assert "What changed? No change is also a valid answer." in [
        paragraph.text for paragraph in Document(io.BytesIO(downloaded["content"])).paragraphs
    ]
    args["request_id"] = "shared-author-0002"
    args["manuscript"]["sections"][0]["body"] = "Preserve this manual revision."
    second = run(ws, pitch.prepare_internal_pitch(**args, work_id=parent["work_id"],
        previous_artifact_id=receipt["artifact_id"], expected_draft_digest=parent["draft_digest"]))
    assert second["action_receipt"]["version"] == 2
    assert second["action_receipt"]["parent_sha256"] == receipt["sha256"]
    assert second["work"]["document"]["payload"]["manuscript"]["sections"][0]["body"] == "Preserve this manual revision."
    assert pitch.read_internal_pitch(first["task_id"], actor=ws["actor"], scope=ws["scope"])["action_receipt"] == receipt
    assert count(ws) == 4


@pytest.mark.parametrize("workspace", ["shared"], indirect=True)
def test_shared_pitch_forged_actor_cannot_read_cancel_or_download(workspace):
    ws = workspace
    task = run(ws, prepare(ws))
    for operation in (pitch.read_internal_pitch, pitch.cancel_internal_pitch, pitch.download_internal_pitch):
        with pytest.raises(PermissionError, match="SHARED_WORKSPACE_ACCESS_DENIED"):
            operation(task["task_id"], actor={"id": "workspace:local"}, scope=ws["scope"])
    assert count(ws) == 2


def test_normal_real_word_save_revision_reopen_and_download(workspace):
    ws = workspace
    pending = prepare(ws)
    assert pending["state"] == "pending" and pending["action_receipt"] is None
    first = run(ws, pending)
    assert first["state"] == "succeeded"
    receipt = first["action_receipt"]
    assert receipt["action_kind"] == "INTERNAL_TEXT_CREATION"
    assert receipt["external_effect"] == "NOT_PERFORMED" and receipt["business_outcome"] == "NOT_OBSERVED"
    output = pitch.download_internal_pitch(pending["task_id"], actor=ws["actor"], scope=ws["scope"])
    assert hashlib.sha256(output["content"]).hexdigest() == receipt["output"]["sha256"]
    assert "What changed? No change is also a valid answer." in [p.text for p in Document(io.BytesIO(output["content"])).paragraphs]
    args = arguments(ws, "revision-0002")
    args["manuscript"]["sections"][0]["body"] = "Which information is still missing?"
    parent = first["work"]["document"]
    second = run(ws, pitch.prepare_internal_pitch(**args, work_id=parent["work_id"],
        previous_artifact_id=receipt["artifact_id"], expected_draft_digest=parent["draft_digest"]))
    assert second["action_receipt"]["version"] == 2
    assert second["action_receipt"]["action_kind"] == "INTERNAL_TEXT_REVISION"
    assert second["action_receipt"]["parent_artifact_id"] == receipt["artifact_id"]
    assert second["action_receipt"]["parent_sha256"] == receipt["sha256"]
    assert pitch.read_internal_pitch(pending["task_id"], actor=ws["actor"], scope=ws["scope"])["action_receipt"] == receipt
    assert count(ws) == 4


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_committed_retry_never_calls_word_owner_again(workspace, monkeypatch):
    task = prepare(workspace)
    first = run(workspace, task)
    import scripts.pitch_export
    monkeypatch.setattr(scripts.pitch_export, "export_pitch_docx", lambda *a, **k: pytest.fail("committed replay must not produce another Word"))
    assert run(workspace, task)["action_receipt"] == first["action_receipt"]
    assert prepare(workspace)["action_receipt"] == first["action_receipt"]
    assert count(workspace) == 2


def test_changed_input_under_same_request_is_conflict(workspace):
    prepare(workspace)
    values = arguments(workspace)
    values["manuscript"]["summary"] += " Changed."
    with pytest.raises(ValueError, match="INTERNAL_PITCH_REQUEST_REUSE_CONFLICT"):
        pitch.prepare_internal_pitch(**values)
    assert count(workspace) == 0


def test_pending_cancel_is_durable_and_not_executable(workspace):
    task = prepare(workspace)
    cancelled = pitch.cancel_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert cancelled["state"] == "cancelled" and cancelled["cancellation"] == "CANCELLED"
    assert cancelled["action_receipt"] is None
    with pytest.raises(ValueError, match="INTERNAL_PITCH_TASK_NOT_RUNNABLE"):
        run(workspace, task)
    assert count(workspace) == 0


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_actual_export_stage_cancel_rolls_back_all_outputs(workspace, monkeypatch):
    task = prepare(workspace)
    import scripts.pitch_export
    owner = scripts.pitch_export.export_pitch_docx
    observed = []
    def cancelling(*args, **kwargs):
        callback = kwargs["check_continue"]
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 3:
                reply = pitch.cancel_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])
                observed.append(reply["state"])
            callback()
        return owner(*args, **{**kwargs, "check_continue": check})
    monkeypatch.setattr(scripts.pitch_export, "export_pitch_docx", cancelling)
    with pytest.raises(ValueError, match="INTERNAL_PITCH_CANCELLED"):
        run(workspace, task)
    assert observed == ["cancel_requested"]
    assert pitch.read_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])["state"] == "cancelled"
    assert count(workspace) == 0


def test_cancel_after_commit_preserves_exact_artifact(workspace):
    task = prepare(workspace)
    first = run(workspace, task)
    after = pitch.cancel_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert after["cancellation"] == "ALREADY_COMMITTED"
    assert after["state"] == "succeeded" and after["action_receipt"] == first["action_receipt"]
    assert count(workspace) == 2


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_lost_ack_after_commit_is_reconciled_from_real_owner(workspace, monkeypatch):
    task = prepare(workspace)
    original = pitch.read_internal_pitch
    def lose(task_id, **kwargs):
        result = original(task_id, **kwargs)
        if result["state"] == "succeeded":
            raise RuntimeError("response connection lost")
        return result
    monkeypatch.setattr(pitch, "read_internal_pitch", lose)
    with pytest.raises(RuntimeError, match="connection lost"):
        run(workspace, task)
    monkeypatch.setattr(pitch, "read_internal_pitch", original)
    restored = run(workspace, task)
    assert restored["state"] == "succeeded" and count(workspace) == 2


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_attachment_corruption_blocks_reopen(workspace):
    task = prepare(workspace)
    saved = run(workspace, task)
    attachment = saved["action_receipt"]["output"]["artifact_id"]
    path = workspace["root"] / "artifacts" / (attachment + ".docx")
    path.write_bytes(path.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="WORK_ATTACHMENT_INTEGRITY_FAILED"):
        pitch.read_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_final_reopen_revocation_does_not_return_content(workspace, monkeypatch):
    task = prepare(workspace)
    run(workspace, task)
    original = work._read_attachment
    def revoke(*a, **k):
        raw = original(*a, **k)
        workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
        return raw
    monkeypatch.setattr(work, "_read_attachment", revoke)
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        pitch.read_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert count(workspace) == 2


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_stale_revision_cannot_replace_committed_result(workspace):
    first = run(workspace, prepare(workspace))
    doc = first["work"]["document"]
    args = dict(work_id=doc["work_id"], previous_artifact_id=first["action_receipt"]["artifact_id"], expected_draft_digest=doc["draft_digest"])
    run(workspace, prepare(workspace, "revision-0002", **args))
    with pytest.raises(ValueError, match="WORK_REVISION_CONFLICT"):
        run(workspace, prepare(workspace, "revision-0003", **args))
    assert count(workspace) == 4


def test_wrong_scope_or_forged_actor_cannot_read_or_cancel(workspace):
    task = prepare(workspace)
    run(workspace, task)
    wrong = {**workspace["scope"], "subject_id": "SUBJ-MISSING"}
    for operation in (pitch.read_internal_pitch, pitch.cancel_internal_pitch):
        with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
            operation(task["task_id"], actor=workspace["actor"], scope=wrong)
        with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
            operation(task["task_id"], actor={"id": "workspace:local"}, scope=workspace["scope"])


def test_generic_task_cancel_cannot_bypass_internal_owner(workspace):
    task = prepare(workspace)
    with pytest.raises(PermissionError, match="managed owner"):
        pitch.engine().cancel_task(task["task_id"])
    assert pitch.read_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])["state"] == "pending"


@pytest.fixture
def client(workspace):
    # Execute the actual global auth/effect hooks without starting collectors,
    # legacy providers, shared Core processes or any formal database.
    import ast
    import re
    import secrets
    from pathlib import Path
    from flask import request, jsonify
    from lumenis_app_api import domain_api_bp
    app = workspace["app"]
    app.register_blueprint(domain_api_bp)
    names = {"_auth_enabled", "_is_cth_readonly_get", "_owner_authorized_root_request", "_basic_auth",
             "_pg_resolve_operation_type", "_shared_workspace_owner_http_handoff", "_permission_gate_write_check"}
    constants = {"_PG_WRITE_METHODS", "_PG_BYPASS_PATHS", "_CTH_READONLY_GET_PREFIXES"}
    nodes = [node for node in ast.parse(Path("app.py").read_text(encoding="utf-8-sig")).body if
        isinstance(node, ast.FunctionDef) and node.name in names or
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets)]
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == names
    namespace = dict(app=app, request=request, jsonify=jsonify, re=re, secrets=secrets,
        AUTH_USER="isolated_basic_user", AUTH_PASSWORD="isolated_basic_password",
        _pg=workspace["gate"], OperationType=permission.OperationType)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<actual-app-hooks>", "exec"), namespace)
    return app.test_client()


PREFIX = "/api/experience/creation/internal-pitches"


def http_input(ws):
    values = arguments(ws)
    values.pop("actor")
    return values


def query(ws):
    return {k: (str(v).lower() if k == "global_scope" else v or "") for k, v in ws["scope"].items()}


def test_actual_api_normal_create_read_export_cancel(workspace, client):
    response = client.post(PREFIX, json=http_input(workspace))
    assert response.status_code == 202
    task = response.get_json()["result"]["task_id"]
    response = client.post(PREFIX + "/" + task + "/run", json={"scope": workspace["scope"]})
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    saved = response.get_json()["result"]
    reopened = client.get(PREFIX + "/" + task, query_string=query(workspace))
    assert reopened.get_json()["result"]["action_receipt"] == saved["action_receipt"]
    output = client.get(PREFIX + "/" + task + "/export", query_string=query(workspace))
    assert output.status_code == 200
    assert hashlib.sha256(output.data).hexdigest() == output.headers["X-Artifact-SHA256"]
    assert output.headers["X-Artifact-ID"] == saved["action_receipt"]["output"]["artifact_id"]
    assert len(Document(io.BytesIO(output.data)).paragraphs) > 0
    cancelled = client.post(PREFIX + "/" + task + "/cancel", json={"scope": workspace["scope"]})
    assert cancelled.get_json()["result"]["cancellation"] == "ALREADY_COMMITTED"


def test_explicit_global_internal_creation_does_not_require_entity(workspace, client):
    values = http_input(workspace)
    values["scope"] = {"domain_id": "cth", "subject_id": None, "brand_focus_id": None, "global_scope": True}
    response = client.post(PREFIX, json=values)
    assert response.status_code == 202
    task = response.get_json()["result"]["task_id"]
    response = client.post(PREFIX + "/" + task + "/run", json={"scope": values["scope"]})
    assert response.status_code == 200
    assert response.get_json()["result"]["action_receipt"]["scope"] == values["scope"]


@pytest.mark.parametrize("change", ["actor", "duplicate", "nonfinite", "global", "language", "shot", "large"])
def test_api_rejects_bad_input_without_creating_task(workspace, client, change):
    values = http_input(workspace)
    if change == "actor":
        values["actor_id"] = 1
    elif change == "global":
        values["scope"]["global_scope"] = True
    elif change == "language":
        values["manuscript"]["language"] = []
    elif change == "shot":
        values["shot_plan"]["shots"] = [None]
    body = json.dumps(values)
    if change == "duplicate":
        body = '{"scope":{},"scope":{}}'
    if change == "nonfinite":
        body = '{"scope":{},"number":NaN}'
    if change == "large":
        body = " " * (1024 * 1024 + 1)
    response = client.post(PREFIX, data=body, content_type="application/json")
    if change == "global":
        # A focus combined with GLOBAL is denied by the real Permission owner.
        assert response.status_code == 403
        assert response.get_json() == {"ok": False, "code": "WORK_PERMISSION_DENIED"}
    else:
        assert response.status_code in {400, 401}
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM ai_task")[0] == 0


def test_api_closed_workspace_and_forged_identity_do_not_bypass_auth(workspace, client):
    values = http_input(workspace)
    assert client.post(PREFIX, json=values, headers={"X-Actor-ID": "1"}).status_code == 401
    workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    assert client.post(PREFIX, json=values).status_code == 401
    assert count(workspace) == 0


def test_api_effect_gate_denial_writes_nothing(workspace, client):
    workspace["gate"].revoke_permission(permission.PermissionLevel.VERIFY)
    response = client.post(PREFIX, json=http_input(workspace))
    assert response.status_code == 403
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM ai_task")[0] == 0


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_final_export_permission_revocation_rolls_back_task_and_artifact(workspace, monkeypatch):
    task = prepare(workspace)
    original = work._stage_bytes
    def revoke(*args, **kwargs):
        result = original(*args, **kwargs)
        workspace["gate"].revoke_permission(permission.PermissionLevel.VERIFY)
        return result
    monkeypatch.setattr(work, "_stage_bytes", revoke)
    with pytest.raises(ValueError, match="WORK_EFFECT_PERMISSION_DENIED"):
        run(workspace, task)
    assert count(workspace) == 0
    assert pitch.engine().get_pitch_task(task["task_id"], owner_context=work.authorize_saved_work(
        workspace["actor"], workspace["scope"], action="read"))["status"] == "failed"


@pytest.mark.parametrize("workspace", ["domain", "shared"], indirect=True)
def test_actual_worker_process_exit_recovers_through_existing_task_owner(workspace):
    import os
    from pathlib import Path
    import subprocess
    import sys
    task = prepare(workspace)
    script = '''
import json, os, sys
from flask import Flask
from lumenis.system.security import permission
from lumenis.shared.content_creation import internal_pitch
from scripts import pitch_export
permission.set_testing_bypass(False)
app=Flask('real_worker_crash')
app.config['LUMENIS_OPEN_WORKSPACE']=True
pitch_export.export_pitch_docx=lambda *a, **k: os._exit(23)
with app.test_request_context('/', headers={'Host':'localhost'}, environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
    actor=permission.resolve_local_workspace_principal(module='reports', action='write')
    internal_pitch.run_internal_pitch(sys.argv[1], actor=actor, scope=json.loads(sys.argv[2]))
'''
    result = subprocess.run([sys.executable, "-c", script, task["task_id"], json.dumps(workspace["scope"])],
        cwd=Path.cwd(), env={**os.environ, "PYTHONPATH": str(Path.cwd())},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 23, result.stdout.decode(errors="replace")
    assert pitch.read_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])["state"] == "running"
    restored = run(workspace, task)
    assert restored["state"] == "succeeded" and restored["action_receipt"]["version"] == 1
    assert count(workspace) == 2


# New shape regressions are technical fixture evidence, never business acceptance.
def manuscript_arguments(ws, request="manuscript-request-0001"):
    args = arguments(ws, request)
    args.pop("shot_plan")
    materials = []
    for key, role, text in (("brief", "brief", "The complete fixture brief.\n"),
                            ("form", "application_form", "The separate complete fixture form.\n")):
        materials.append({"material_id": key, "role": role, "filename": key + ".docx",
            "size_bytes": 100, "sha256": "0" * 64, "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_url": "https://example.com/" + key + ".docx", "published_at": None,
            "captured_at": "2026-10-03T00:00:00Z", "source_ref": None,
            "evidence_ref": None, "source_use_ref": None})
    args.update(profile=pitch.MANUSCRIPT_PROFILE,
        input_manifest={"schema": pitch.INPUT_MANIFEST_SCHEMA, "state": "NOT_INGESTED", "materials": materials})
    return args


def test_manuscript_only_real_word_version_revision_full_manifest_and_reopen(workspace):
    ws = workspace
    args = manuscript_arguments(ws)
    first = run(ws, pitch.prepare_internal_pitch(**args))
    doc = first["work"]["document"]
    assert doc["contract"] == pitch.MANUSCRIPT_CONTRACT
    assert "shot_plan" not in doc["payload"] and "shot_timing" not in doc["payload"]["truth_state"]
    assert doc["payload"]["input_manifest"] == args["input_manifest"]
    assert doc["payload"]["truth_state"]["source_admission"] == "PENDING"
    assert doc["payload"]["truth_state"]["input_materials"] == "OPERATOR_DECLARED_NOT_INGESTED"
    assert doc["payload"]["truth_state"]["owned_model_execution"] == "NOT_RUN"
    second_args = manuscript_arguments(ws, "manuscript-revision-0002")
    second_args["manuscript"]["sections"][0]["body"] = "A revised original question."
    second_args.update(work_id=doc["work_id"], previous_artifact_id=first["action_receipt"]["artifact_id"],
                       expected_draft_digest=doc["draft_digest"])
    second = run(ws, pitch.prepare_internal_pitch(**second_args))
    assert second["action_receipt"]["version"] == 2
    assert second["action_receipt"]["parent_sha256"] == first["action_receipt"]["sha256"]
    assert second["work"]["document"]["payload"]["input_manifest"] == args["input_manifest"]
    output = pitch.download_internal_pitch(second["task_id"], actor=ws["actor"], scope=ws["scope"])
    assert "A revised original question." in [p.text for p in Document(io.BytesIO(output["content"])).paragraphs]
    assert hashlib.sha256(output["content"]).hexdigest() == second["action_receipt"]["output"]["sha256"]
    assert pitch.read_internal_pitch(first["task_id"], actor=ws["actor"], scope=ws["scope"])["work"]["document"] == doc
    assert count(ws) == 4


def test_exact_v1_task_created_with_old_owner_remains_byte_identical_under_new_owner(workspace, monkeypatch):
    import base64
    import types
    import zlib
    # Immutable pre-upgrade owner is a test-only compatibility golden, not a
    # runtime owner. Inline compressed bytes keep the test independent of W4
    # work paths, Git history depth and external source downloads.
    legacy = zlib.decompress(base64.b64decode("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"))
    assert hashlib.sha256(legacy).hexdigest() == "34eaf1dd0d6f99b394e6e39670383d9e1bb416c3694ecc47b599c17bf62cf9f8"
    old = types.ModuleType("w4_exact_legacy_pitch")
    exec(compile(legacy, "<immutable-v1-compatibility-golden>", "exec"), old.__dict__)
    monkeypatch.setattr(old, "get_repository", lambda: workspace["repo"])
    args = arguments(workspace)
    pending = old.prepare_internal_pitch(**args)
    first = old.run_internal_pitch(pending["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    row_before = dict(workspace["repo"].query_one("SELECT * FROM ai_task WHERE task_id=?", (pending["task_id"],)))
    read = pitch.read_internal_pitch(pending["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    replay = pitch.run_internal_pitch(pending["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert read == first == replay
    assert pitch.prepare_internal_pitch(**args) == first
    row_after = dict(workspace["repo"].query_one("SELECT * FROM ai_task WHERE task_id=?", (pending["task_id"],)))
    assert row_after == row_before
    assert read["work"]["document"]["contract"] == pitch.CONTRACT
    assert "input_manifest" not in read["work"]["document"]["payload"]
    assert count(workspace) == 2
    old.engine.cache_clear()


@pytest.mark.parametrize("change", ["missing", "empty", "hash", "duplicate", "bound", "state", "time", "url", "private", "role", "size", "extra"])
def test_manuscript_manifest_rejects_incomplete_forged_or_bound_claims_before_task(workspace, change):
    args = manuscript_arguments(workspace)
    manifest = args["input_manifest"]
    material = manifest["materials"][0]
    expected = "INTERNAL_PITCH_INPUT_MANIFEST_INVALID"
    if change == "missing":
        args["input_manifest"] = None
    elif change == "empty":
        manifest["materials"] = []
    elif change == "hash":
        material["text"] += "undeclared modification"
    elif change == "duplicate":
        manifest["materials"][1]["material_id"] = material["material_id"]
    elif change == "bound":
        material["source_ref"] = "DOC-invented"
        expected = "INTERNAL_PITCH_SOURCE_BINDING_REQUIRED"
    elif change == "state":
        manifest["state"] = "VERIFIED"
    elif change == "time":
        material["captured_at"] = "2026-10-03"
    elif change == "url":
        material["source_url"] = "https://user:private@example.com/source"
    elif change == "private":
        material["local_path"] = "D:/private.docx"
        expected = "WORK_PRIVATE_FIELD_FORBIDDEN"
    elif change == "role":
        material["role"] = []
    elif change == "size":
        material["size_bytes"] = True
    elif change == "extra":
        manifest["licensed"] = True
    with pytest.raises(ValueError, match=expected):
        pitch.prepare_internal_pitch(**args)
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM ai_task")[0] == 0
    assert count(workspace) == 0


def test_manuscript_profile_never_coerces_empty_shots_or_unknown_profile(workspace):
    for profile, shot in ((pitch.MANUSCRIPT_PROFILE, {"shots": []}), ("unknown/v2", None)):
        args = manuscript_arguments(workspace)
        args.update(profile=profile, shot_plan=shot)
        with pytest.raises(ValueError, match="INTERNAL_PITCH_PROFILE_INVALID"):
            pitch.prepare_internal_pitch(**args)
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM ai_task")[0] == 0


def test_manuscript_pending_cancel_and_committed_cancel_keep_history(workspace):
    args = manuscript_arguments(workspace)
    task = pitch.prepare_internal_pitch(**args)
    cancelled = pitch.cancel_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert cancelled["state"] == "cancelled" and cancelled["action_receipt"] is None
    with pytest.raises(ValueError, match="INTERNAL_PITCH_TASK_NOT_RUNNABLE"):
        run(workspace, task)
    made = run(workspace, pitch.prepare_internal_pitch(**manuscript_arguments(workspace, "manuscript-after-cancel-0002")))
    after = pitch.cancel_internal_pitch(made["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert after["action_receipt"] == made["action_receipt"] and after["cancellation"] == "ALREADY_COMMITTED"
    assert count(workspace) == 2


def test_manuscript_cannot_rewrite_legacy_contract_or_stale_parent(workspace):
    old = run(workspace, prepare(workspace))
    doc = old["work"]["document"]
    args = manuscript_arguments(workspace)
    args.update(work_id=doc["work_id"], previous_artifact_id=old["action_receipt"]["artifact_id"], expected_draft_digest=doc["draft_digest"])
    with pytest.raises(ValueError, match="WORK_CONTRACT_CHANGE_FORBIDDEN"):
        run(workspace, pitch.prepare_internal_pitch(**args))
    assert pitch.read_internal_pitch(old["task_id"], actor=workspace["actor"], scope=workspace["scope"])["work"]["document"] == doc
    assert count(workspace) == 2


def test_manuscript_changed_material_under_same_request_is_conflict(workspace):
    args = manuscript_arguments(workspace)
    pitch.prepare_internal_pitch(**args)
    args["input_manifest"]["materials"][0]["text"] += "\nNew operator input."
    args["input_manifest"]["materials"][0]["text_sha256"] = hashlib.sha256(args["input_manifest"]["materials"][0]["text"].encode()).hexdigest()
    with pytest.raises(ValueError, match="INTERNAL_PITCH_REQUEST_REUSE_CONFLICT"):
        pitch.prepare_internal_pitch(**args)
    assert count(workspace) == 0


# Bounded M review regressions; technical inputs are not source-use admission.
@pytest.mark.parametrize("display_name", ["客户原创提案.docx", "브랜드 제안서.DOCX", "Client Brief résumé.docx"])
def test_input_compatibility_unicode_upload_retains_actual_file_and_declarations(workspace, display_name):
    args = manuscript_arguments(workspace, "unicode-input-0001")
    path = workspace["root"] / display_name
    document = Document()
    document.add_paragraph("A complete local technical brief.")
    document.save(path)
    raw = path.read_bytes()
    material = args["input_manifest"]["materials"][0]
    text = "\n".join(paragraph.text for paragraph in Document(io.BytesIO(raw)).paragraphs)
    material.update(filename=display_name, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                    text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(), source_url=None,
                    source_origin={"kind": "approved-file", "ref": "TEST-UPLOAD-DECLARATION-0001"})
    expected = copy.deepcopy(args["input_manifest"])
    first = run(workspace, pitch.prepare_internal_pitch(**args))
    stored = first["work"]["document"]["payload"]
    assert stored["input_manifest"] == expected
    assert stored["truth_state"]["input_materials"] == "OPERATOR_DECLARED_NOT_INGESTED"
    assert stored["truth_state"]["source_admission"] == "PENDING"
    assert stored["input_manifest"]["materials"][0]["source_ref"] is None
    assert path.name == display_name and path.read_bytes() == raw
    read = pitch.read_internal_pitch(first["task_id"], actor=workspace["actor"], scope=workspace["scope"])
    assert read["work"]["document"]["payload"]["input_manifest"] == expected


@pytest.mark.parametrize("name", ["../提案.docx", "..\\제안.docx", "C:提案.docx", "提案/稿.docx",
    "提案\x00.docx", "提案\n.docx", "提案\u202e.docx", "", " .docx", ".docx",
    "CON.docx", "LPT1.docx", "brief .docx", "brief.docx ", "brief.txt"])
def test_input_compatibility_unsafe_basename_is_rejected(workspace, name):
    args = manuscript_arguments(workspace)
    args["input_manifest"]["materials"][0]["filename"] = name
    with pytest.raises(ValueError, match="INTERNAL_PITCH_INPUT_MANIFEST_INVALID"):
        pitch.prepare_internal_pitch(**args)
    assert count(workspace) == 0


@pytest.mark.parametrize("origin", [None, {"kind": "approved-file", "ref": ""},
    {"kind": "upload", "ref": "TEST-UPLOAD-0001"}, {"kind": "approved-file", "ref": "../private"},
    {"kind": "approved-file", "ref": "TEST-UPLOAD-0001", "approved": True}])
def test_input_compatibility_null_url_needs_existing_origin_shape(workspace, origin):
    args = manuscript_arguments(workspace)
    material = args["input_manifest"]["materials"][0]
    material["source_url"] = None
    if origin is not None:
        material["source_origin"] = origin
    with pytest.raises(ValueError, match="INTERNAL_PITCH_INPUT_MANIFEST_INVALID"):
        pitch.prepare_internal_pitch(**args)
    assert count(workspace) == 0


def test_input_compatibility_public_manifest_unchanged_and_origin_not_mixed(workspace):
    args = manuscript_arguments(workspace)
    expected = copy.deepcopy(args["input_manifest"])
    prepared = pitch.prepare_internal_pitch(**args)
    assert prepared["task_id"] and args["input_manifest"] == expected
    invalid = manuscript_arguments(workspace, "mixed-input-0002")
    invalid["input_manifest"]["materials"][0]["source_origin"] = {"kind": "approved-file", "ref": "TEST-UPLOAD-0001"}
    with pytest.raises(ValueError, match="INTERNAL_PITCH_INPUT_MANIFEST_INVALID"):
        pitch.prepare_internal_pitch(**invalid)


@pytest.mark.parametrize("language,body", [
    ("zh", "这是用户自己的创作。保留未修改的部分。"),
    ("en", "This is my own writing. Keep the unchanged section."),
    ("ko", "사용자가 직접 쓴 글입니다. 수정하지 않은 부분은 유지합니다."),
])
def test_independent_authored_manuscript_normal_revision_reopen_export(workspace, client, language, body):
    values = http_input(workspace)
    values.pop("shot_plan")
    values["profile"] = "authored-manuscript/v4"
    values["scope"] = {"domain_id": "cth", "subject_id": None, "brand_focus_id": None, "global_scope": True}
    values["manuscript"]["language"] = language
    values["manuscript"]["sections"] = [{"heading": "Draft", "body": body},
                                           {"heading": "Retained", "body": "Keep this paragraph."}]
    response = client.post(PREFIX, json=values)
    assert response.status_code == 202, response.get_json()
    task_id = response.get_json()["result"]["task_id"]
    first = client.post(PREFIX + "/" + task_id + "/run", json={"scope": values["scope"]})
    assert first.status_code == 200, first.get_json()
    original = first.get_json()["result"]
    document = original["work"]["document"]
    assert document["contract"]["version"] == "4"
    assert document["payload"]["truth_state"]["source_admission"] == "USER_AUTHORED_CONTENT"
    assert "input_manifest" not in document["payload"] and "shot_plan" not in document["payload"]
    export = client.get(PREFIX + "/" + task_id + "/export", query_string={
        "domain_id": "cth", "subject_id": "", "brand_focus_id": "", "global_scope": "true"})
    assert export.status_code == 200
    assert body in [paragraph.text for paragraph in Document(io.BytesIO(export.data)).paragraphs]
    args = copy.deepcopy(values)
    args.update(request_id="authored-revision-0002", work_id=document["work_id"],
                previous_artifact_id=original["action_receipt"]["artifact_id"],
                expected_draft_digest=document["draft_digest"])
    args["manuscript"]["sections"][0]["body"] += " Revised."
    revised = client.post(PREFIX, json=args)
    assert revised.status_code == 202, revised.get_json()
    revised_id = revised.get_json()["result"]["task_id"]
    saved = client.post(PREFIX + "/" + revised_id + "/run", json={"scope": values["scope"]})
    assert saved.status_code == 200, saved.get_json()
    child = saved.get_json()["result"]
    assert child["action_receipt"]["version"] == 2
    assert child["action_receipt"]["parent_sha256"] == original["action_receipt"]["sha256"]
    assert child["work"]["document"]["payload"]["manuscript"]["sections"][1] == values["manuscript"]["sections"][1]
    scope = values["scope"]
    reopened = pitch.read_internal_pitch(task_id, actor=workspace["actor"], scope=scope)
    assert reopened["work"]["document"] == document
    assert pitch.run_internal_pitch(revised_id, actor=workspace["actor"], scope=scope)["action_receipt"] == child["action_receipt"]


@pytest.mark.parametrize("extra", ["shot_plan", "input_manifest", "upstream_ref"])
def test_authored_profile_rejects_mixed_inputs_before_task(workspace, extra):
    values = arguments(workspace)
    values.pop("shot_plan")
    values["profile"] = "authored-manuscript/v4"
    values[extra] = {} if extra != "upstream_ref" else {"forged": True}
    with pytest.raises(ValueError, match="INTERNAL_PITCH_PROFILE_INVALID"):
        pitch.prepare_internal_pitch(**values)
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM ai_task")[0] == 0
    assert count(workspace) == 0


@pytest.fixture
def c4_source_use_environment(workspace, monkeypatch):
    """Bind real disposable Source/Evidence owners to this C4 workspace DB."""
    import canonical_data
    from lumenis.importer import documents
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evidence import store

    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"c4-test-key": "isolated-source-export-regression-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "c4-test-key")
    monkeypatch.setattr(documents, "get_repository", lambda: workspace["repo"])
    monkeypatch.setattr(store, "get_repository", lambda: workspace["repo"])
    store.init_evidence_store(str(workspace["repo"].db_path))
    with workspace["repo"].transaction() as con:
        apply_business_schema(con)
        store.ensure_evidence_schema(con)
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        evidence_columns = {row[1] for row in con.execute("PRAGMA table_info(app_evidence_records)")}
        assert {"integrity_version", "integrity_algorithm", "integrity_key_id", "integrity_digest"} <= evidence_columns
    canonical_data.ensure_canonical_table(str(workspace["repo"].db_path))
    workspace["documents"] = documents
    workspace["source_store"] = store
    return workspace


def _c4_approved_source_citation(workspace, monkeypatch, *, request_id):
    from tests.test_collected_source_citations import (
        _seed_approved_internal_source_canonical,
    )

    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    assert source["entry"]["allowed_operations"] == [
        "derive_reference", "read", "save", "revise", "reopen",
    ]
    prepared = workspace["documents"].prepare_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id=request_id,
        actor=workspace["actor"],
        scope=source["scope"],
    )
    assert prepared["prepared"] is True
    assert prepared["resource"].startswith("approved-internal-source-reference:v2:")
    pending = permission.prepare_approved_source_reference_confirmation(
        actor=workspace["actor"], scope=source["scope"], gate=workspace["gate"],
        request={"source_id": source["source_id"], "canonical_id": source["canonical_id"],
                 "expected_body_sha256": source["body_sha256"], "request_id": request_id},
    )
    assert pending["allowed"] is True
    assert pending["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING"
    assert pending["resource"] == prepared["resource"]
    confirmed = permission.confirm_approved_source_reference_confirmation(
        actor=workspace["actor"], scope=source["scope"], gate=workspace["gate"],
        confirmation_id=pending["confirmation_id"], confirmed=True,
    )
    assert confirmed["allowed"] is True
    assert confirmed["code"] == "APPROVED_SOURCE_REFERENCE_READY_FOR_RETRY"
    assert confirmed["confirmation_id"] == pending["confirmation_id"]
    assert confirmed["resource"] == prepared["resource"]
    assert "approval_token" not in confirmed
    derived = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id=request_id,
        actor=workspace["actor"],
        scope=source["scope"],
    )
    quote = "派生引用与 SavedWork"
    start = source["body"].index(quote)
    located = workspace["documents"].locate_quote(
        derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
        start=start, end=start + len(quote),
    )
    assert located["citation"]["quote"] == quote
    return source, derived, located["citation"]


def _c4_authored_request(workspace, citation, *, request_id, body):
    values = http_input(workspace)
    values.pop("shot_plan")
    values.update(profile=pitch.AUTHORING_PROFILE, citations=[citation], request_id=request_id)
    values["manuscript"]["sections"] = [{"heading": "Source-backed review", "body": body}]
    return values


def _c4_source_export_state(workspace, source):
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        tables = {
            "tasks": "SELECT * FROM ai_task ORDER BY task_id",
            "artifacts": "SELECT * FROM lumenis_shared_artifacts ORDER BY artifact_id",
            "evidence": "SELECT * FROM app_evidence_records ORDER BY id",
            "canonical": "SELECT * FROM canonical_data WHERE canonical_id=?",
            "note": "SELECT * FROM notes WHERE note_id=?",
        }
        rows = {
            "tasks": [tuple(row) for row in con.execute(tables["tasks"]).fetchall()],
            "artifacts": [tuple(row) for row in con.execute(tables["artifacts"]).fetchall()],
            "evidence": [tuple(row) for row in con.execute(tables["evidence"]).fetchall()],
            "canonical": [tuple(row) for row in con.execute(
                tables["canonical"], (source["canonical_id"],)
            ).fetchall()],
            "note": [tuple(row) for row in con.execute(
                tables["note"], (source["source_id"],)
            ).fetchall()],
        }
    artifact_root = workspace["root"] / "artifacts"
    rows["artifact_files"] = sorted(
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in artifact_root.iterdir() if path.is_file()
    )
    return rows


def test_source_use_export_rejects_internal_view_only(
    workspace, client, c4_source_use_environment, monkeypatch,
):
    from lumenis.system.security.permission import OperationType

    source, _derived, citation = _c4_approved_source_citation(
        workspace, monkeypatch, request_id="c4-source-use-export-derive-0001",
    )
    values = _c4_authored_request(
        workspace, citation, request_id="c4-source-use-export-pitch-0001",
        body=f"Review the cited source span: {citation['quote']}.",
    )
    created = client.post(PREFIX, json=values)
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()["result"]["task_id"]
    completed = client.post(PREFIX + "/" + task_id + "/run", json={"scope": source["scope"]})
    assert completed.status_code == 200, completed.get_json()
    saved = completed.get_json()["result"]
    receipt = saved["action_receipt"]
    assert receipt["task_id"] == task_id
    saved_citation = saved["work"]["document"]["citations"][0]
    assert {key: saved_citation[key] for key in ("evidence_id", "start", "end", "quote")} == citation
    assert saved_citation["source_scope"] == source["scope"]
    export_resource = "internal-pitch-export:v1:" + work._digest(receipt["output"])
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=export_resource,
        granted_by="isolated-c4-source-use-export-test",
    )

    before = _c4_source_export_state(workspace, source)
    denied = client.get(PREFIX + "/" + task_id + "/export", query_string=query(workspace))
    assert denied.status_code == 400
    assert denied.get_json() == {"ok": False, "code": "SOURCE_USE_PURPOSE_NOT_ALLOWED"}
    assert denied.mimetype == "application/json"
    assert "Content-Disposition" not in denied.headers
    assert "X-Artifact-ID" not in denied.headers
    assert "X-Artifact-SHA256" not in denied.headers
    assert not denied.data.startswith(b"PK\x03\x04")
    assert _c4_source_export_state(workspace, source) == before

    reopened = client.get(PREFIX + "/" + task_id, query_string=query(workspace))
    assert reopened.status_code == 200, reopened.get_json()
    reopened_result = reopened.get_json()["result"]
    assert reopened_result["action_receipt"] == receipt
    assert reopened_result["work"]["document"] == saved["work"]["document"]
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        note = con.execute(
            "SELECT content FROM notes WHERE note_id=?", (source["source_id"],),
        ).fetchone()
        canonical = con.execute(
            "SELECT content FROM canonical_data WHERE canonical_id=?", (source["canonical_id"],),
        ).fetchone()
    assert note[0] == canonical[0] == source["body"]
    assert _c4_source_export_state(workspace, source) == before


def _c4_import_owner_approved_text(workspace, *, filename, source_origin_ref, text):
    from lumenis.system.security.permission import OperationType

    path = workspace["root"] / filename
    raw = text.encode("utf-8")
    path.write_bytes(raw)
    provenance = {
        "source_url": None,
        "published_at": None,
        "captured_at": "2026-10-11T06:30:00Z",
        "rights": "owner-approved",
        "title": "C4 owner-approved text upload regression",
        "intended_use": "internal_draft",
        "source_origin": {"kind": "approved-file", "ref": source_origin_ref},
    }
    import_args = {"actor": workspace["actor"], "scope": workspace["scope"], "provenance": provenance}
    import_resource = workspace["documents"].document_import_resource(str(path), **import_args)
    workspace["gate"].grant_approval(
        OperationType.DATA_IMPORT.value,
        resource=import_resource,
        granted_by="isolated-c4-source-use-export-test",
    )
    imported = workspace["documents"].import_document(str(path), **import_args)
    assert imported["replayed"] is False

    source_resource = "document-source-read:v1:" + hashlib.sha256(raw).hexdigest()
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=source_resource,
        granted_by="isolated-c4-source-use-export-test",
    )
    retained = workspace["documents"].reopen_imported_source(
        imported["evidence_id"], actor=workspace["actor"], scope=workspace["scope"],
    )
    assert retained["content"] == raw
    assert retained["source_url"] is None
    assert retained["source_origin"] == provenance["source_origin"]
    path.unlink()

    quote = "The owner-approved source is retained exactly as submitted."
    start = text.index(quote)
    located = workspace["documents"].locate_quote(
        imported["evidence_id"], actor=workspace["actor"], scope=workspace["scope"],
        start=start, end=start + len(quote),
    )
    assert located["citation"]["quote"] == quote
    return imported, located["citation"], raw, retained, source_resource


def test_source_use_export_allows_owner_approved_import_with_scoped_grant(
    workspace, client, c4_source_use_environment,
):
    from lumenis.system.security.permission import OperationType

    text = (
        "Approved input for a directly authored internal proposal. "
        "The owner-approved source is retained exactly as submitted. "
        "No public URL or publication time was supplied."
    )
    source, citation, original_bytes, retained_source, source_resource = _c4_import_owner_approved_text(
        workspace, filename="owner-approved-c4-source.txt",
        source_origin_ref="c4-owner-approved-source-0001", text=text,
    )
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        evidence_row = con.execute(
            "SELECT collection_metadata FROM app_evidence_records WHERE id=?",
            (source["evidence_id"],),
        ).fetchone()
    provenance = json.loads(evidence_row[0])["provenance"]
    assert provenance["source_url"] is None and provenance["published_at"] is None
    assert provenance["captured_at"] == "2026-10-11T06:30:00Z"
    assert provenance["source_origin"] == {
        "kind": "approved-file", "ref": "c4-owner-approved-source-0001",
    }
    assert provenance["rights"] == "owner-approved"
    assert provenance["intended_use"] == "internal_draft"

    first_values = _c4_authored_request(
        workspace, citation, request_id="c4-source-use-export-owned-v1",
        body=f"Preserve the submitted source's scope: {citation['quote']}.",
    )
    first_created = client.post(PREFIX, json=first_values)
    assert first_created.status_code == 202, first_created.get_json()
    first_task = first_created.get_json()["result"]["task_id"]
    first_response = client.post(
        PREFIX + "/" + first_task + "/run", json={"scope": workspace["scope"]},
    )
    assert first_response.status_code == 200, first_response.get_json()
    first = first_response.get_json()["result"]
    first_document = first["work"]["document"]

    second_values = _c4_authored_request(
        workspace, citation, request_id="c4-source-use-export-owned-v2",
        body=f"Preserve the submitted source's scope: {citation['quote']}. Add a user revision.",
    )
    second_values.update(
        work_id=first_document["work_id"],
        previous_artifact_id=first["action_receipt"]["artifact_id"],
        expected_draft_digest=first_document["draft_digest"],
    )
    second_created = client.post(PREFIX, json=second_values)
    assert second_created.status_code == 202, second_created.get_json()
    second_task = second_created.get_json()["result"]["task_id"]
    second_response = client.post(
        PREFIX + "/" + second_task + "/run", json={"scope": workspace["scope"]},
    )
    assert second_response.status_code == 200, second_response.get_json()
    second = second_response.get_json()["result"]
    second_receipt = second["action_receipt"]
    second_document = second["work"]["document"]
    assert second_receipt["version"] == 2
    assert second_receipt["parent_artifact_id"] == first["action_receipt"]["artifact_id"]
    assert second_receipt["parent_sha256"] == first["action_receipt"]["sha256"]
    assert second_document["parent_artifact_id"] == first["action_receipt"]["artifact_id"]
    assert second_document["parent_sha256"] == first["action_receipt"]["sha256"]

    export_resource = "internal-pitch-export:v1:" + work._digest(second_receipt["output"])
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=export_resource,
        granted_by="isolated-c4-source-use-export-test",
    )
    exported = client.get(PREFIX + "/" + second_task + "/export", query_string=query(workspace))
    assert exported.status_code == 200
    assert exported.headers["X-Artifact-ID"] == second_receipt["output"]["artifact_id"]
    assert hashlib.sha256(exported.data).hexdigest() == second_receipt["output"]["sha256"]
    paragraphs = [paragraph.text for paragraph in Document(io.BytesIO(exported.data)).paragraphs]
    exported_text = "\n".join(paragraphs)
    assert citation["quote"] in exported_text
    assert "Add a user revision." in exported_text

    reopened_second = client.get(PREFIX + "/" + second_task, query_string=query(workspace))
    reopened_first = client.get(PREFIX + "/" + first_task, query_string=query(workspace))
    assert reopened_second.status_code == reopened_first.status_code == 200
    assert reopened_second.get_json()["result"]["action_receipt"] == second_receipt
    assert reopened_second.get_json()["result"]["work"]["document"] == second_document
    assert reopened_first.get_json()["result"]["action_receipt"] == first["action_receipt"]
    retained_again = workspace["documents"].reopen_imported_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"],
    )
    assert retained_again["content"] == retained_source["content"] == original_bytes
    assert retained_again["artifact_ref"] == source["source_artifact_ref"]
    assert retained_again["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert retained_again["source_origin"] == provenance["source_origin"]
    assert not (workspace["root"] / "owner-approved-c4-source.txt").exists()
    assert source_resource == "document-source-read:v1:" + retained_again["sha256"]


def test_source_use_export_rechecks_revoked_effect_after_attachment_read(
    workspace, client, c4_source_use_environment, monkeypatch,
):
    from lumenis.system.security.permission import OperationType

    text = (
        "Authorized local source for an export interruption case. "
        "The owner-approved source is retained exactly as submitted."
    )
    source, citation, _raw, _retained, _source_resource = _c4_import_owner_approved_text(
        workspace, filename="owner-approved-c4-race-source.txt",
        source_origin_ref="c4-owner-approved-race-0001", text=text,
    )
    values = _c4_authored_request(
        workspace, citation, request_id="c4-source-use-export-race-0001",
        body=f"Read the exact source before export: {citation['quote']}.",
    )
    created = client.post(PREFIX, json=values)
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()["result"]["task_id"]
    completed = client.post(PREFIX + "/" + task_id + "/run", json={"scope": workspace["scope"]})
    assert completed.status_code == 200, completed.get_json()
    saved = completed.get_json()["result"]
    receipt = saved["action_receipt"]
    export_resource = "internal-pitch-export:v1:" + work._digest(receipt["output"])
    token = workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=export_resource,
        granted_by="isolated-c4-source-use-export-race-test",
    )

    before = _c4_source_export_state(workspace, source)
    original_check = work._check_effect
    original_read_attachment = work._read_attachment
    preflight_passed = False
    revoked = False
    captured_raw = None

    def checked_effect(actor, scope, operation, resource, **options):
        nonlocal preflight_passed
        result = original_check(actor, scope, operation, resource, **options)
        if (getattr(operation, "value", operation) == OperationType.DATA_EXPORT.value
                and resource == export_resource):
            preflight_passed = True
        return result

    def read_and_revoke_after_preflight(con, binding, context, work_id, *, actor=None):
        nonlocal revoked, captured_raw
        raw = original_read_attachment(con, binding, context, work_id, actor=actor)
        if (preflight_passed and not revoked
                and binding["artifact_id"] == receipt["output"]["artifact_id"]):
            captured_raw = raw
            revoked = workspace["gate"].revoke_approval(token)
            # DATA_EXPORT is MEDIUM/auto-allowed with VERIFY permission;
            # revoking a redundant approval token alone does not revoke it.
            workspace["gate"].revoke_permission(permission.PermissionLevel.VERIFY)
            assert not workspace["gate"].has_permission(permission.PermissionLevel.VERIFY)
        return raw

    monkeypatch.setattr(work, "_check_effect", checked_effect)
    monkeypatch.setattr(work, "_read_attachment", read_and_revoke_after_preflight)
    denied = client.get(PREFIX + "/" + task_id + "/export", query_string=query(workspace))
    assert preflight_passed and revoked
    assert captured_raw is not None
    assert hashlib.sha256(captured_raw).hexdigest() == receipt["output"]["sha256"]
    assert denied.status_code == 403
    assert denied.get_json() == {"ok": False, "code": "WORK_EFFECT_PERMISSION_DENIED"}
    assert "Content-Disposition" not in denied.headers
    assert "X-Artifact-ID" not in denied.headers
    assert "X-Artifact-SHA256" not in denied.headers
    assert not denied.data.startswith(b"PK\x03\x04")
    assert _c4_source_export_state(workspace, source) == before
