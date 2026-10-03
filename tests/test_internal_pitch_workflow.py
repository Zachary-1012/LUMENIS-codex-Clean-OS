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
def workspace(tmp_path, monkeypatch):
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


def test_attachment_corruption_blocks_reopen(workspace):
    task = prepare(workspace)
    saved = run(workspace, task)
    attachment = saved["action_receipt"]["output"]["artifact_id"]
    path = workspace["root"] / "artifacts" / (attachment + ".docx")
    path.write_bytes(path.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="WORK_ATTACHMENT_INTEGRITY_FAILED"):
        pitch.read_internal_pitch(task["task_id"], actor=workspace["actor"], scope=workspace["scope"])


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
    names = {"_auth_enabled", "_is_cth_readonly_get", "_basic_auth",
             "_pg_resolve_operation_type", "_permission_gate_write_check"}
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
    assert pitch.engine().get_pitch_task(task["task_id"], owner_context=work.authorize(
        workspace["actor"], workspace["scope"], action="read"))["status"] == "failed"


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
