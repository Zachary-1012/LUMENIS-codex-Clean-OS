"""G165 narrow offline regressions with original canonical Evidence owner."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import pytest
from tests.test_saved_document_workflow import workspace as original_workspace

@pytest.fixture
def workspace(original_workspace, monkeypatch):
    from lumenis.system import security
    monkeypatch.setattr(security, "get_permission_gate", lambda: original_workspace["gate"])
    return original_workspace
from lumenis.shared.evaluation.openai_math_papers import provenance as p
from lumenis.shared.evaluation.openai_math_papers.dispatch import execute, OPERATIONS
from lumenis.shared.evaluation.openai_math_papers.core import digest, MathInputError
from lumenis.system.security.permission import OperationType

REQUEST = {"operation": "unique_games.evaluate", "parameters": {
    "vertices": 1, "alphabet": 1, "constraints": [{"source": 0, "target": 0, "images": [0]}], "labeling": [0]}}


def review(w, identity=None, state="REVOKED", kind="withdrawal"):
    identity = identity or p.REGISTRY["102"]["manuscript_identity"]
    content = "Isolated reviewer fixture, not real upstream withdrawal: " + state
    sha = hashlib.sha256(content.encode()).hexdigest()
    material = {"schema": p.REVIEW_SCHEMA, "identity": identity, "state": state,
                "evidence_url": p.HISTORY_URL, "evidence_sha256": sha,
                "upstream_commit": p.HISTORY_COMMIT, "change_kind": kind,
                "implementation_pin": p.UPSTREAM_COMMIT}
    from lumenis.shared.reporting.saved_work import authorize
    principal = authorize(w["actor"], w["scope"], action="write")
    material.update(reviewer=principal.get("principal_ref") or f"actor:{principal['actor_id']}", review_scope=principal)
    w["gate"].grant_approval(OperationType.CONFIG_MODIFY.value,
        resource="math-source-review:" + digest(material), granted_by="isolated-test-reviewer")
    return p.record_source_review(identity=identity, state=state,
        evidence_url=p.HISTORY_URL, evidence_sha256=sha, upstream_commit=p.HISTORY_COMMIT,
        change_kind=kind, actor=w["actor"], scope=w["scope"], evidence_content=content)


def test_three_exact_unrelated_withdrawals_do_not_block_current_registry(workspace):
    for title in p.WITHDRAWN_TITLES:
        review(workspace, title)
    for family, _, _ in OPERATIONS.values():
        assert p.assert_review(family)["status"] == "REVIEWED_PINNED"
    assert execute(REQUEST)["paper"]["commit"] == p.UPSTREAM_COMMIT


def test_precise_revocation_persists_restart_and_does_not_touch_other_family(workspace):
    old = execute(REQUEST)
    review(workspace)
    with pytest.raises(MathInputError, match="PAPER_REVOKED"):
        execute(REQUEST)
    assert p.assert_review("103")["status"] == "REVIEWED_PINNED"
    assert old["paper"]["review"]["status"] == "REVIEWED_PINNED"
    result = subprocess.run([sys.executable, "-c", "from lumenis.shared.evaluation.openai_math_papers.provenance import review_snapshot; print(review_snapshot('102')['status'])"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "REVOKED"


def test_unknown_and_workflow_updates_never_rehabilitate_revocation(workspace):
    review(workspace, state="UNKNOWN", kind="fetch_unknown")
    with pytest.raises(MathInputError, match="PAPER_UNKNOWN"):
        execute(REQUEST)
    review(workspace)
    review(workspace, state="REVIEWED_PINNED", kind="workflow_only")
    assert p.review_snapshot("102")["status"] == "REVOKED"


def test_workflow_update_preserves_pin_and_invalidates_inflight_revision(workspace):
    old = p.assert_review("102")
    review(workspace, state="REVIEWED_PINNED", kind="workflow_only")
    with pytest.raises(MathInputError, match="PAPER_REVIEW_CHANGED"):
        p.assert_review("102", old)
    assert execute(REQUEST)["paper"]["commit"] == p.UPSTREAM_COMMIT


def test_revocation_during_computation_cannot_return_result(workspace, monkeypatch):
    from lumenis.shared.evaluation.openai_math_papers import unique_games_102
    real = unique_games_102.check_instance
    def withdrawing(**kwargs):
        result = real(**kwargs)
        review(workspace)
        return result
    monkeypatch.setattr(unique_games_102, "check_instance", withdrawing)
    with pytest.raises(MathInputError, match="PAPER_REVOKED"):
        execute(REQUEST)


def test_dependency_revocation_and_evidence_tamper_fail_closed(workspace):
    identity = p.REGISTRY["113"]["dependency_identities"][0]
    review(workspace, identity)
    with pytest.raises(MathInputError, match="PAPER_REVOKED"):
        p.assert_review("113")
    with workspace["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE source=?", (p.REVIEW_SOURCE,))
    with pytest.raises(MathInputError, match="PAPER_REVIEW_EVIDENCE_INTEGRITY"):
        p.assert_review("113")

# Real original API/Task/SourceBrief/SavedWork integration, generated source only.
from tests.test_source_brief_job_routes import client, GLOBAL, URL
from tests.test_source_brief_job import job_db

@pytest.fixture
def math_task(client, monkeypatch, tmp_path):
    import ai_api
    from ai_task_engine import TaskEngine
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    api, app, path, entry, gate = client
    from lumenis.system.security.permission import PermissionLevel
    gate.grant_permission(PermissionLevel.COMMIT)
    import shared_artifacts
    shared_artifacts.ensure_artifact_table()
    engine = TaskEngine()
    monkeypatch.setattr(ai_api, "_get_engine", lambda: engine)
    app.register_blueprint(ai_api.bp)
    source = api.post(URL + "/generate", headers=GLOBAL, json={})
    assert source.status_code == 200, source.get_json()
    source = source.get_json()["result"]
    created = api.post("/api/ai/tasks", headers=GLOBAL, json={"input": "Evaluate declared finite constraints", "context": {
        "analysis_operation": "openai_math", "source_brief_job_id": source["job_id"],
        "openai_math_request_id": "a" * 32, "openai_math_problem": REQUEST,
        "openai_math_declaration": {"origin": "DECLARED_MATHEMATICAL_SCENARIO", "purpose": "isolated G165 integration", "variable_map": {"labeling": "user declared assignment"}}}})
    assert created.status_code == 200, created.get_json()
    task = created.get_json()["task"]
    engine._db_update_task(task["task_id"], status="running")
    task = engine._db_get_task(task["task_id"])
    with app.test_request_context("/", headers=GLOBAL, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        actor, _ = engine._analysis_actor(task)
        yield {"api": api, "app": app, "engine": engine, "task": task, "gate": gate, "actor": actor,
               "scope": {"domain_id": "cth", "subject_id": None, "brand_focus_id": None, "global_scope": True}, "path": path}


def test_original_task_source_savedwork_preserved_after_revocation(math_task):
    from lumenis.shared.evaluation.openai_math_papers.product_outcome import execute_product_task, verify_product_outcome
    from lumenis.shared.reporting.saved_work import read_committed_work
    w = math_task
    result = execute_product_task(w["engine"], w["task"])
    assert verify_product_outcome(w["engine"], w["task"], result)
    before = read_committed_work(result["artifact_id"], actor=w["actor"], scope=w["scope"])
    review(w)
    reopened = read_committed_work(result["artifact_id"], actor=w["actor"], scope=w["scope"])
    assert reopened == before
    assert p.review_snapshot("102")["status"] == "REVOKED"
    with pytest.raises(MathInputError, match="PAPER_REVOKED"):
        execute_product_task(w["engine"], w["task"])


def test_revocation_after_compute_before_save_cannot_commit(math_task, monkeypatch):
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.evaluation.openai_math_papers.product_outcome import execute_product_task
    w = math_task
    original = saved_work.save_work
    def revoke_then_save(**kwargs):
        review(w)
        return original(**kwargs)
    monkeypatch.setattr(saved_work, "save_work", revoke_then_save)
    with pytest.raises(MathInputError, match="PAPER_REVOKED"):
        execute_product_task(w["engine"], w["task"])
    with sqlite3.connect(w["path"]) as con:
        assert con.execute("SELECT result_json FROM ai_task WHERE task_id=?", (w["task"]["task_id"],)).fetchone()[0] is None
        assert con.execute("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_work'").fetchone()[0] == 0


def test_missing_store_structured_error_explicit_cli_offline_only(tmp_path):
    import os
    request = tmp_path / "request.json"
    request.write_text(json.dumps(REQUEST))
    env = {**os.environ, "ZBC_DB_PATH": str(tmp_path / "missing.sqlite3")}
    command = [sys.executable, "-m", "lumenis.shared.evaluation.openai_math_papers.cli", str(request)]
    default = subprocess.run(command, env=env, text=True, capture_output=True)
    assert default.returncode == 2 and json.loads(default.stdout)["reason"] == "PAPER_REVIEW_UNAVAILABLE"
    offline = subprocess.run(command + ["--offline-review"], env=env, text=True, capture_output=True)
    assert offline.returncode == 0, offline.stderr
    result = json.loads(offline.stdout)
    assert result["paper"]["review"]["status"] == "OFFLINE_PIN_REVIEW_ONLY"
    # Existing Evaluation package initializes its own evaluation_records on import.
    # G165 must not create a review table/store as a dispatch side effect.
    with sqlite3.connect(tmp_path / "missing.sqlite3") as con:
        assert con.execute("SELECT name FROM sqlite_master WHERE name='app_evidence_records'").fetchone() is None


def test_product_rejects_injected_offline_result(math_task, monkeypatch):
    import agent_runtime.openai_math_paper_handler as handler
    from lumenis.shared.evaluation.openai_math_papers.product_outcome import execute_product_task
    monkeypatch.setattr(handler, "execute", lambda spec, **kw: execute(spec, offline_review=True))
    with pytest.raises(MathInputError, match="PAPER_OFFLINE_REVIEW_NOT_PUBLISHABLE"):
        execute_product_task(math_task["engine"], math_task["task"])


def test_review_requires_exact_permission_and_content(workspace):
    with pytest.raises(MathInputError, match="PAPER_REVIEW_CONTENT_HASH"):
        p.record_source_review(identity=p.REGISTRY["102"]["manuscript_identity"], state="REVOKED",
            evidence_url=p.HISTORY_URL, evidence_sha256="0"*64, upstream_commit=p.HISTORY_COMMIT,
            change_kind="withdrawal", actor=workspace["actor"], scope=workspace["scope"], evidence_content="wrong")
    with pytest.raises(PermissionError, match="PAPER_REVIEW_EXACT_APPROVAL_REQUIRED"):
        p.record_source_review(identity=p.REGISTRY["102"]["manuscript_identity"], state="REVOKED",
            evidence_url=p.HISTORY_URL, evidence_sha256=hashlib.sha256(b"correct").hexdigest(), upstream_commit=p.HISTORY_COMMIT,
            change_kind="withdrawal", actor=workspace["actor"], scope=workspace["scope"], evidence_content="correct")


def test_cross_process_revocation_serializes_after_final_commit(math_task, monkeypatch, tmp_path):
    import os
    import time
    from lumenis.shared.evaluation.openai_math_papers.product_outcome import execute_product_task
    marker = tmp_path / "writer-started"
    child = None
    real = p.assert_review
    code = '''
from pathlib import Path
from flask import Flask
from tests.test_math_revocation import review
from lumenis.system.security import permission
from lumenis.system import security
app=Flask(__name__); app.config['LUMENIS_OPEN_WORKSPACE']=True
gate=permission.PermissionGate(); gate.grant_permission(permission.PermissionLevel.COMMIT)
permission.get_permission_gate=lambda:gate
security.get_permission_gate=lambda:gate
with app.test_request_context('/', environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
 actor=permission.resolve_local_workspace_principal(module='reports', action='write')
 Path(MARKER).write_text('started')
 review({'gate':gate,'actor':actor,'scope':{'domain_id':'cth','subject_id':None,'brand_focus_id':None,'global_scope':True}})
print('review committed')
'''.replace('MARKER', repr(str(marker)))
    def checked(family, expected=None, *, connection=None):
        nonlocal child
        result = real(family, expected, connection=connection)
        if connection is not None:
            child = subprocess.Popen([sys.executable, "-c", code], env=os.environ.copy(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            assert marker.exists()
            time.sleep(.15)
            assert child.poll() is None, "review writer must wait on SavedWork writer transaction"
        return result
    monkeypatch.setattr(p, "assert_review", checked)
    result = execute_product_task(math_task["engine"], math_task["task"])
    stdout, stderr = child.communicate(timeout=10)
    assert child.returncode == 0, stderr
    assert "review committed" in stdout
    assert result["artifact_id"] and p.review_snapshot("102")["status"] == "REVOKED"


def test_http_budget_failure_is_persisted_without_success_artifact(math_task):
    from fractions import Fraction
    from tests.test_openai_math_entropy_intervals import _request
    w = math_task
    context = {**w["task"]["context"], "openai_math_request_id": "b" * 32,
               "openai_math_problem": _request(Fraction(1, 2**90 + 1))}
    created = w["api"].post("/api/ai/tasks", headers=GLOBAL,
                             json={"input": "Analyze declared matching entropy", "context": context})
    assert created.status_code == 200, created.get_json()
    task_id = created.get_json()["task"]["task_id"]
    run = w["api"].post("/api/ai/tasks/" + task_id + "/run", headers=GLOBAL, json={})
    assert run.status_code == 200, run.get_json()
    task = run.get_json()["task"]
    assert task["status"] == "failed", task
    readback = w["api"].get("/api/ai/tasks/" + task_id, headers=GLOBAL)
    assert readback.status_code == 200, readback.get_json()
    assert "EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED" in readback.get_data(as_text=True)
    with sqlite3.connect(w["path"]) as con:
        assert con.execute("SELECT count(*) FROM lumenis_shared_artifacts WHERE source_execution_id=?", ("WORK-" + digest({"task_id": task_id, "actor": "workspace:local"})[:24],)).fetchone()[0] == 0


def test_product_api_offline_flag_never_bypasses_revocation(math_task):
    w = math_task
    review(w)
    context = {**w["task"]["context"], "openai_math_request_id": "c"*32, "offline_review": True}
    created = w["api"].post("/api/ai/tasks", headers=GLOBAL,
                             json={"input": "Evaluate declared constraints", "context": context})
    assert created.status_code == 200, created.get_json()
    task_id = created.get_json()["task"]["task_id"]
    run = w["api"].post("/api/ai/tasks/" + task_id + "/run", headers=GLOBAL, json={})
    assert run.status_code == 200, run.get_json()
    assert run.get_json()["task"]["status"] == "failed", run.get_json()
    assert "PAPER_REVOKED" in run.get_data(as_text=True)


def test_source_change_stays_pending_after_workflow_update(workspace):
    review(workspace, state="REVIEW_REQUIRED", kind="source_change")
    review(workspace, state="REVIEWED_PINNED", kind="workflow_only")
    assert p.review_snapshot("102")["status"] == "REVIEW_REQUIRED"


def test_savedwork_and_review_survive_independent_process_restart(math_task):
    import os
    from lumenis.shared.evaluation.openai_math_papers.product_outcome import execute_product_task
    w = math_task
    result = execute_product_task(w["engine"], w["task"])
    review(w)
    code = '''
import json
from flask import Flask
from lumenis.system.security.permission import resolve_local_workspace_principal
from lumenis.shared.reporting.saved_work import read_committed_work
from lumenis.shared.evaluation.openai_math_papers.provenance import review_snapshot
app=Flask(__name__); app.config['LUMENIS_OPEN_WORKSPACE']=True
with app.test_request_context('/', environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
 actor=resolve_local_workspace_principal(module='reports',action='read')
 saved=read_committed_work(ARTIFACT, actor=actor,scope={'domain_id':'cth','subject_id':None,'brand_focus_id':None,'global_scope':True})
 print(json.dumps({'saved_pin':saved['document']['payload']['paper']['commit'], 'historical_review':saved['document']['payload']['paper']['review']['status'], 'current_review':review_snapshot('102')['status']}))
'''.replace('ARTIFACT', repr(result['artifact_id']))
    child = subprocess.run([sys.executable, "-c", code], env=os.environ.copy(), capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == {"saved_pin":p.UPSTREAM_COMMIT,"historical_review":"REVIEWED_PINNED","current_review":"REVOKED"}


@pytest.fixture
def account_reviewers(workspace):
    # Real account rows; authority is loaded from the original account owner.
    with workspace["repo"].transaction() as con:
        con.execute("CREATE TABLE IF NOT EXISTS v4_users (id INTEGER PRIMARY KEY,role TEXT,status TEXT)")
        con.executemany("INSERT INTO v4_users(id,role,status) VALUES(?,'owner','active')", [(99123,), (99124,)])
    return [{**workspace, "actor": {"id": identity}} for identity in (99123, 99124)]


def test_account_review_persists_stable_owner_identity(account_reviewers):
    first, _ = account_reviewers
    evidence_id = review(first)
    with first["repo"].connection() as con:
        row = con.execute("SELECT outputs_json,inputs_json FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone()
    assert json.loads(row[0])["reviewer"] == "actor:99123"
    assert json.loads(row[0])["review_scope"]["actor_id"] == 99123
    assert json.loads(row[1])["reviewer"] == "actor:99123"
    assert p.review_snapshot("102")["status"] == "REVOKED"


def test_review_approval_cannot_cross_actor_or_survive_revocation(account_reviewers, monkeypatch):
    first, second = account_reviewers
    original = p.record_source_review
    captured = {}
    def capture(**kwargs):
        captured.update(kwargs)
        return None
    monkeypatch.setattr(p, "record_source_review", capture)
    review(first)  # Builds a real exact approval for A without executing it.
    monkeypatch.setattr(p, "record_source_review", original)
    with pytest.raises(PermissionError, match="PAPER_REVIEW_EXACT_APPROVAL_REQUIRED"):
        original(**{**captured, "actor": second["actor"]})
    for token in list(first["gate"]._approvals):
        first["gate"].revoke_approval(token)
    with pytest.raises(PermissionError, match="PAPER_REVIEW_EXACT_APPROVAL_REQUIRED"):
        original(**captured)
    with first["repo"].connection() as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE source=?", (p.REVIEW_SOURCE,)).fetchone()[0] == 0


def test_inactive_account_review_permission_is_rechecked(account_reviewers, monkeypatch):
    first, _ = account_reviewers
    original = p.record_source_review
    captured = {}
    monkeypatch.setattr(p, "record_source_review", lambda **kwargs: captured.update(kwargs))
    review(first)
    monkeypatch.setattr(p, "record_source_review", original)
    with first["repo"].transaction() as con:
        con.execute("UPDATE v4_users SET status='inactive' WHERE id=99123")
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        original(**captured)


def test_bmp_alias_review_uses_authorized_canonical_domain(account_reviewers, monkeypatch):
    first, _ = account_reviewers
    first = {**first, "scope": {**first["scope"], "domain_id": "bmp"}}
    observed = []
    original = first["gate"].check
    def check(*args, **kwargs):
        if args[0] == OperationType.CONFIG_MODIFY:
            observed.append(kwargs["domain_id"])
        return original(*args, **kwargs)
    monkeypatch.setattr(first["gate"], "check", check)
    evidence_id = review(first)
    assert observed == ["bmp"]
    with first["repo"].connection() as con:
        value = json.loads(con.execute("SELECT outputs_json FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone()[0])
    assert value["review_scope"]["domain_id"] == "zbmp"


def test_review_approval_bmp_alias_matches_canonical_but_not_cth(account_reviewers, monkeypatch):
    first, _ = account_reviewers
    first = {**first, "scope": {**first["scope"], "domain_id": "bmp"}}
    original = p.record_source_review
    captured = {}
    monkeypatch.setattr(p, "record_source_review", lambda **kwargs: captured.update(kwargs))
    review(first)
    monkeypatch.setattr(p, "record_source_review", original)
    with pytest.raises(PermissionError, match="PAPER_REVIEW_EXACT_APPROVAL_REQUIRED"):
        original(**{**captured, "scope": {**captured["scope"], "domain_id": "cth"}})
    evidence_id = original(**{**captured, "scope": {**captured["scope"], "domain_id": "zbmp"}})
    assert type(evidence_id) is int
