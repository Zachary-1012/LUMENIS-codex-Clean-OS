"""Isolated lifecycle candidate/history checks; no install or execution occurs."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import sqlite3
import uuid

import pytest

from lumenis.shared.agents.skills import lifecycle as lc
from lumenis.shared.evidence import store


@pytest.fixture
def canonical_gate(monkeypatch):
    from lumenis.system.security import permission as p
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(p, "_default_gate", None)
    gate = p.get_permission_gate()
    gate.grant_permission(p.PermissionLevel.COMMIT)
    return gate


def _workspace_app():
    from flask import Flask
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    return app


def _workspace_admission(candidate, gate, *, domain="cth", grant=True):
    from lumenis.system.security import permission as p
    principal = p.resolve_local_workspace_principal(module="skills", action="write")
    resource = p.skill_metadata_approval_resource(candidate, principal=principal,
                                                 domain_id=domain, global_scope=True)
    token = gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource,
                               granted_by="isolated-test-human") if grant else None
    return dict(gate=gate, principal=principal, domain_id=domain, global_scope=True), resource, token


def _history_count(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id=?",
                                  (lc.HISTORY_FEATURE,)).fetchone()[0]


@pytest.fixture
def registry(tmp_path, monkeypatch):
    from account.models import SKILLS_TABLES_SQL, _SKILL_RUNTIME_COLUMNS
    path = tmp_path / "skill-registry.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"skill-test": "ephemeral-skill-history-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "skill-test")
    package = tmp_path / "owned-skill"
    package.mkdir()
    (package / "main.py").write_text("raise RuntimeError('must never execute during preview')\n", encoding="utf-8")
    with sqlite3.connect(path) as connection:
        connection.executescript(SKILLS_TABLES_SQL)
        for name, kind in _SKILL_RUNTIME_COLUMNS:
            connection.execute(f"ALTER TABLE skills_registry ADD COLUMN {name} {kind}")
        connection.execute("""INSERT INTO skills_registry (
            skill_id,name,product,domain,status,version,config_json,source,source_type,runtime,
            entrypoint,permissions_granted_json,trust_level,health_state,install_state,
            lifecycle_state,install_path,active_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("owned.read", "Owned reader", "SYSTEM", "global", "enabled", "1.0.0",
             json.dumps({"secret": "private-config-kept-only-in-registry"}), str(package), "local", "python",
             "main:run", '["filesystem.read"]', "verified", "healthy", "installed", "available", str(package), "1.0.0"))
        store.ensure_evidence_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table
    ensure_skill_executions_table()
    return path, package


def _row(path):
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM skills_registry WHERE skill_id='owned.read'").fetchone())


def _manifest(package, **changes):
    value = {"skill_id": "owned.read", "name": "Owned reader", "version": "2.0.0",
             "runtime": "python", "entrypoint": "main:run", "permissions": ["filesystem.read"],
             "license": "Apache-2.0"}
    value.update(changes)
    (package / "skill.json").write_text(json.dumps(value), encoding="utf-8")


def _prepare(action="uninstall", **kwargs):
    return lc.prepare_skill_metadata_change("owned.read", action, operation_id=str(uuid.uuid4()), **kwargs)


def _history(path, candidate, *, input_changes=None):
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        value = candidate.to_dict()
        inputs = {key: value[key] for key in ("schema_version", "skill_id", "action", "operation_id",
                  "before_sha256", "after_sha256", "candidate_sha256", "config_sha256", "restore_evidence_ref")}
        inputs.update(input_changes or {})
        record_id = store.record_evidence(
            connection=connection, source=lc.HISTORY_SOURCE, product="SYSTEM", feature_id=lc.HISTORY_FEATURE,
            asset_id=candidate.skill_id, test_name=candidate.operation_id,
            version=lc.SCHEMA_VERSION + ":" + candidate.candidate_sha256,
            result="PASS", status="derived", capture_mode="isolated-test-contract",
            inputs=inputs,
            outputs={"before_metadata": value["before_metadata"], "after_metadata": value["after_metadata"]})
    return f"app_evidence_records:{record_id}"


def test_uninstall_preparation_keeps_registry_config_files_and_execution_history(registry):
    path, package = registry
    before = _row(path)
    bytes_before = (package / "main.py").read_bytes()
    candidate = _prepare()
    value = candidate.to_dict()
    assert _row(path) == before
    assert (package / "main.py").read_bytes() == bytes_before
    assert "private-config-kept-only-in-registry" not in json.dumps(value)
    assert value["after_metadata"]["status"] == "disabled"
    assert value["after_metadata"]["permissions_granted_json"] == "[]"
    assert value["after_metadata"]["entrypoint"] is None
    assert value["state"] == "PREPARED_NOT_APPROVED"
    assert value["files_deleted"] is False


def test_update_uses_fresh_manifest_without_enabling_installing_or_granting(registry):
    path, package = registry
    _manifest(package)
    manifest_hash = hashlib.sha256((package / "skill.json").read_bytes()).hexdigest()
    before = _row(path)
    candidate = _prepare("update", source=str(package))
    after = candidate.to_dict()["after_metadata"]
    assert after["version"] == "2.0.0" and after["previous_version"] == "1.0.0"
    assert after["install_state"] == "not_installed" and after["status"] == "disabled"
    assert after["permissions_granted_json"] == "[]" and after["active_version"] is None
    assert json.loads(after["compatibility_json"])["license_review"]["commercial_use"] == "UNKNOWN"
    assert _row(path) == before
    assert hashlib.sha256((package / "skill.json").read_bytes()).hexdigest() == manifest_hash


def test_candidate_cannot_be_submitted_as_json_or_modified_after_review(registry):
    candidate = _prepare()
    with pytest.raises(FrozenInstanceError):
        candidate.action = "restore"
    with pytest.raises(ValueError, match="NOT_SERVER_PREPARED"):
        lc._validate_candidate(candidate.to_dict())
    with pytest.raises(ValueError, match="CANDIDATE_CHANGED"):
        replace(candidate, action="restore").to_dict()


@pytest.mark.parametrize("changes, code", [
    ({"skill_id": "another.read"}, "ID_MISMATCH"),
    ({"entrypoint": '{"command":"python","env":{"API_KEY":"private-value"}}'}, "CONTAINS_CREDENTIAL"),
    ({"entrypoint": "https://user:password@example.invalid/run"}, "CONTAINS_CREDENTIAL"),
    ({"entrypoint": "https://example.invalid/run?token=private-value"}, "CONTAINS_CREDENTIAL"),
])
def test_wrong_package_or_embedded_credentials_do_not_reach_candidate_history(registry, changes, code):
    path, package = registry
    before = _row(path)
    _manifest(package, **changes)
    with pytest.raises(ValueError, match=code):
        _prepare("update", source=str(package))
    assert _row(path) == before


def test_restore_requires_signed_history_and_resets_old_enablement_and_grants(registry):
    path, _package = registry
    ref = _history(path, _prepare())
    before = _row(path)
    candidate = _prepare("restore", restore_evidence_ref=ref)
    after = candidate.to_dict()["after_metadata"]
    assert after["version"] == "1.0.0"
    assert after["status"] == "disabled" and after["permissions_granted_json"] == "[]"
    assert after["install_state"] == "not_installed" and after["trust_level"] == "unverified"
    assert after["install_path"] is None and after["active_version"] is None
    assert _row(path) == before
    history = lc.read_skill_version_history("owned.read")
    assert history[0]["evidence_ref"] == ref and history[0]["signature_verified"] is True
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (int(ref.split(":")[1]),))
    with pytest.raises(RuntimeError, match="SIGNATURE_INVALID"):
        _prepare("restore", restore_evidence_ref=ref)
    with pytest.raises(RuntimeError, match="SIGNATURE_INVALID"):
        lc.read_skill_version_history("owned.read")


def test_existing_builtin_cannot_be_uninstalled_as_a_package(registry):
    path, _package = registry
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE skills_registry SET source_type='builtin'")
    with pytest.raises(ValueError, match="BUILTIN_SKILL"):
        _prepare()


@pytest.mark.parametrize("changes", [{"candidate_sha256": "a" * 64}, {"before_sha256": "b" * 64}])
def test_signed_but_misbound_history_cannot_authorize_restore(registry, changes):
    path, _package = registry
    ref = _history(path, _prepare(), input_changes=changes)
    with pytest.raises(ValueError, match="CANDIDATE_MISMATCH"):
        _prepare("restore", restore_evidence_ref=ref)


def test_preparation_does_not_migrate_missing_registry_schema(tmp_path, monkeypatch):
    path = tmp_path / "old-schema.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE skills_registry(skill_id TEXT)")
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with pytest.raises(RuntimeError, match="SCHEMA_NOT_READY"):
        _prepare()
    with sqlite3.connect(path) as connection:
        assert [row[1] for row in connection.execute("PRAGMA table_info(skills_registry)")] == ["skill_id"]


def _runtime_info():
    from account.skills import get_skill_info
    from lumenis.shared.agents.skills.execution import SkillRuntimeInfo
    info = get_skill_info("owned.read")
    config = dict(info["config"])
    fields = ("runtime", "source", "source_type", "entrypoint", "install_path", "active_version", "version",
              "tools_json", "permissions_granted_json", "install_state", "lifecycle_state", "health_state",
              "input_schema_json", "output_schema_json", "compatibility_json")
    config.update({name: info[name] for name in fields if info[name] is not None})
    config["registry_sha256"] = info["registry_sha256"]
    return SkillRuntimeInfo(skill_id="owned.read", name=info["name"], product="SYSTEM", enabled=True,
                            version=info["version"], config=config, source=info["source"])


def test_package_start_persists_running_and_finish_preserves_execution_identity(registry):
    from lumenis.shared.agents.skills import execution as ex
    path, _package = registry
    ctx = ex.SkillExecutionContext(skill_id="owned.read", task="Read approved material")
    assert ex._reserve_package_execution(ctx, _runtime_info()) == "reserved"
    with sqlite3.connect(path) as connection:
        running = connection.execute("SELECT id,created_at,status FROM skill_executions WHERE execution_id=?", (ctx.execution_id,)).fetchone()
    assert running[2] == "running"
    ctx.status = ex.ExecutionStatus.COMPLETED
    ctx.execute_result = {"success": True, "result": {"observed": "actual returned material"}}
    assert ex.write_trace(ctx, 5)
    with sqlite3.connect(path) as connection:
        completed = connection.execute("SELECT id,created_at,status,output_json FROM skill_executions WHERE execution_id=?", (ctx.execution_id,)).fetchone()
    assert completed[:2] == running[:2]
    assert completed[2] == "completed"
    assert json.loads(completed[3])["result"]["observed"] == "actual returned material"


@pytest.mark.parametrize("change", ["disabled", "digest", "config"])
def test_cached_runtime_cannot_start_after_metadata_or_configuration_changes(registry, change):
    from lumenis.shared.agents.skills import execution as ex
    path, _package = registry
    runtime = _runtime_info()
    with sqlite3.connect(path) as connection:
        if change == "disabled":
            connection.execute("UPDATE skills_registry SET status='disabled'")
        elif change == "digest":
            connection.execute("UPDATE skills_registry SET digest=?", ("a" * 64,))
        else:
            connection.execute("UPDATE skills_registry SET config_json='{}'")
    ctx = ex.SkillExecutionContext(skill_id="owned.read")
    assert ex._reserve_package_execution(ctx, runtime) in {"SKILL_RUNTIME_NOT_READY", "SKILL_RUNTIME_METADATA_CHANGED"}
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM skill_executions").fetchone()[0] == 0


def test_package_start_fails_closed_if_execution_tracking_schema_is_missing(registry):
    from lumenis.shared.agents.skills import execution as ex
    path, _package = registry
    runtime = _runtime_info()
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE skill_executions")
    assert ex._reserve_package_execution(ex.SkillExecutionContext(skill_id="owned.read"), runtime) == "SKILL_EXECUTION_RESERVATION_UNAVAILABLE"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='skill_executions'").fetchone()[0] == 0


def test_trace_keeps_valid_long_json_and_excludes_raw_approval_credentials(registry):
    from lumenis.shared.agents.skills import execution as ex
    path, _package = registry
    ctx = ex.SkillExecutionContext(skill_id="owned.read", input_payload={"content": "material " * 900})
    ctx.permission_result = {"allowed": True, "approval_token": "private-approval-token"}
    assert ex.write_trace(ctx)
    with sqlite3.connect(path) as connection:
        stored = connection.execute("SELECT input_json,permission_json FROM skill_executions WHERE execution_id=?", (ctx.execution_id,)).fetchone()
    assert json.loads(stored[0])["content"] == ctx.input_payload["content"]
    assert "private-approval-token" not in stored[1] and "approval_token" not in json.loads(stored[1])


@pytest.mark.parametrize("action", ["uninstall", "update"])
def test_actual_metadata_apply_commits_signed_history_and_preserves_config_files(registry, canonical_gate, action):
    path, package = registry
    if action == "update":
        _manifest(package)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE skills_registry SET last_error=?,last_health_at=? WHERE skill_id='owned.read'",
                           ("Retained diagnostic from the previous execution", "2026-10-01 12:34:56"))
    before = _row(path)
    package_before = {file.name: file.read_bytes() for file in package.iterdir()}
    candidate = _prepare(action, **({"source": str(package)} if action == "update" else {}))
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, resource, _token = _workspace_admission(candidate, canonical_gate)
        result = lc.apply_skill_metadata_change(candidate, **args)
    after = _row(path)
    assert result["state"] == "applied" and result["resource"] == resource
    assert after["config_json"] == before["config_json"]
    assert (after["last_error"], after["last_health_at"]) == (before["last_error"], before["last_health_at"])
    assert {file.name: file.read_bytes() for file in package.iterdir()} == package_before
    assert after["status"] == "disabled" and after["permissions_granted_json"] == "[]"
    assert after["install_state"] == "not_installed" and after["active_version"] is None
    assert result["configuration_changed"] is False and result["files_deleted"] is False
    assert _history_count(path) == 1
    assert lc.read_skill_version_history("owned.read")[0]["signature_verified"] is True
    with sqlite3.connect(path) as connection:
        inputs = json.loads(connection.execute("SELECT inputs_json FROM app_evidence_records").fetchone()[0])
        assert connection.execute("SELECT COUNT(*) FROM skill_executions").fetchone()[0] == 0
    assert inputs["identity"]["principal_ref"] == "workspace:local"
    assert inputs["resource"] == resource and inputs["scope"]["global_scope"] is True
    assert len(inputs["commit_verification"]["approval_token_sha256"]) == 64
    assert "private-config-kept-only-in-registry" not in json.dumps(inputs)


@pytest.mark.parametrize("approval", ["missing", "revoked", "wrong_scope"])
def test_actual_apply_requires_current_exact_approval_without_registry_or_history_write(registry, canonical_gate, approval):
    path, _package = registry
    before, candidate = _row(path), _prepare()
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, _resource, token = _workspace_admission(candidate, canonical_gate, grant=approval != "missing")
        if approval == "revoked":
            assert canonical_gate.revoke_approval(token)
        elif approval == "wrong_scope":
            args["domain_id"] = "bmp"
        with pytest.raises(PermissionError):
            lc.apply_skill_metadata_change(candidate, **args)
    assert _row(path) == before and _history_count(path) == 0


def test_actual_restore_uses_applied_signed_version_and_remains_disabled(registry, canonical_gate):
    path, package = registry
    _manifest(package)
    diagnostics = ("Historical execution diagnostic; not metadata approval input", "2026-10-01 09:10:11")
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE skills_registry SET last_error=?,last_health_at=? WHERE skill_id='owned.read'", diagnostics)
    config_before = _row(path)["config_json"]
    file_before = (package / "main.py").read_bytes()
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        update = _prepare("update", source=str(package))
        args, _resource, _token = _workspace_admission(update, canonical_gate)
        first = lc.apply_skill_metadata_change(update, **args)
        assert _row(path)["version"] == "2.0.0"
        assert (_row(path)["last_error"], _row(path)["last_health_at"]) == diagnostics
        replayed_update = lc.apply_skill_metadata_change(update, **args)
        assert replayed_update["state"] == "already_applied"
        assert (_row(path)["last_error"], _row(path)["last_health_at"]) == diagnostics
        restore = _prepare("restore", restore_evidence_ref=first["evidence_ref"])
        restore_args, restore_resource, _restore_token = _workspace_admission(restore, canonical_gate)
        restored = lc.apply_skill_metadata_change(restore, **restore_args)
        replayed_restore = lc.apply_skill_metadata_change(restore, **restore_args)
        assert replayed_restore["state"] == "already_applied"
    after = _row(path)
    assert restored["state"] == "applied" and restored["resource"] == restore_resource
    assert after["version"] == "1.0.0" and after["status"] == "disabled"
    assert after["permissions_granted_json"] == "[]" and after["install_state"] == "not_installed"
    assert after["active_version"] is None and after["install_path"] is None
    assert after["config_json"] == config_before and (package / "main.py").read_bytes() == file_before
    assert (after["last_error"], after["last_health_at"]) == diagnostics
    history = lc.read_skill_version_history("owned.read")
    assert [row["action"] for row in history] == ["restore", "update"]
    assert all(row["signature_verified"] for row in history) and _history_count(path) == 2


def test_revoke_after_signed_history_rolls_back_registry_and_evidence(registry, canonical_gate, monkeypatch):
    path, _package = registry
    before, candidate = _row(path), _prepare()
    actual_record = store.record_evidence
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, _resource, token = _workspace_admission(candidate, canonical_gate)
        def record_then_revoke(**kwargs):
            record_id = actual_record(**kwargs)
            assert canonical_gate.revoke_approval(token)
            return record_id
        monkeypatch.setattr(store, "record_evidence", record_then_revoke)
        with pytest.raises(PermissionError):
            lc.apply_skill_metadata_change(candidate, **args)
    assert _row(path) == before and _history_count(path) == 0


def test_revoke_before_commit_lease_rolls_back_both_writes(registry, canonical_gate, monkeypatch):
    path, _package = registry
    before, candidate = _row(path), _prepare()
    actual_lease = canonical_gate.skill_metadata_commit_lease
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, _resource, token = _workspace_admission(candidate, canonical_gate)
        def revoke_then_lease(*values, **kwargs):
            assert canonical_gate.revoke_approval(token)
            return actual_lease(*values, **kwargs)
        monkeypatch.setattr(canonical_gate, "skill_metadata_commit_lease", revoke_then_lease)
        with pytest.raises(PermissionError, match="COMMIT_LEASE_APPROVAL_REQUIRED"):
            lc.apply_skill_metadata_change(candidate, **args)
    assert _row(path) == before and _history_count(path) == 0


def test_signed_evidence_write_failure_rolls_back_registry(registry, canonical_gate, monkeypatch):
    path, _package = registry
    before, candidate = _row(path), _prepare()
    def reject_history(**kwargs):
        raise RuntimeError("isolated signed-history transport unavailable")
    monkeypatch.setattr(store, "record_evidence", reject_history)
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, _resource, _token = _workspace_admission(candidate, canonical_gate)
        with pytest.raises(RuntimeError, match="signed-history transport unavailable"):
            lc.apply_skill_metadata_change(candidate, **args)
    assert _row(path) == before and _history_count(path) == 0


@pytest.mark.parametrize("field,value", [("caller", "workspace:other"), ("domain_id", "bmp"),
                                        ("resource", "skill_metadata:wrong"), ("scope_audit_id", "")])
def test_caller_rejects_a_typed_fence_result_with_wrong_binding(registry, canonical_gate, monkeypatch, field, value):
    from lumenis.system.security import effect_fence as ef
    path, _package = registry
    before, candidate = _row(path), _prepare()
    fence = ef.get_effect_fence()
    actual_check = fence.check_skill_metadata_change
    def wrong_binding(*args, **kwargs):
        return replace(actual_check(*args, **kwargs), **{field: value})
    monkeypatch.setattr(fence, "check_skill_metadata_change", wrong_binding)
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, _resource, _token = _workspace_admission(candidate, canonical_gate)
        with pytest.raises(PermissionError, match="FENCE_BINDING_MISMATCH"):
            lc.apply_skill_metadata_change(candidate, **args)
    assert _row(path) == before and _history_count(path) == 0


def test_running_package_prevents_metadata_apply_and_keeps_execution_record(registry, canonical_gate):
    from lumenis.shared.agents.skills import execution as ex
    path, _package = registry
    before, candidate = _row(path), _prepare()
    context = ex.SkillExecutionContext(skill_id="owned.read")
    assert ex._reserve_package_execution(context, _runtime_info()) == "reserved"
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, _resource, _token = _workspace_admission(candidate, canonical_gate)
        with pytest.raises(RuntimeError, match="EXECUTION_IN_PROGRESS"):
            lc.apply_skill_metadata_change(candidate, **args)
    assert _row(path) == before and _history_count(path) == 0
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT status FROM skill_executions WHERE execution_id=?",
                                  (context.execution_id,)).fetchone()[0] == "running"


def test_new_process_recovery_requires_fresh_approval_and_replays_without_duplicate_write(registry, canonical_gate, tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    path, _package = registry
    candidate = _prepare()
    with _workspace_app().test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args, resource, token = _workspace_admission(candidate, canonical_gate)
        first = lc.apply_skill_metadata_change(candidate, **args)
        assert canonical_gate.revoke_approval(token)
    before = _row(path)
    child = tmp_path / "isolated_skill_recovery.py"
    child.write_text('''import json,sys
from flask import Flask
from lumenis.shared.agents.skills import lifecycle as lc
from lumenis.system.security import permission as p
app=Flask(__name__)
app.config["LUMENIS_OPEN_WORKSPACE"]=True
p.set_testing_bypass(False)
gate=p.get_permission_gate()
gate.grant_permission(p.PermissionLevel.COMMIT)
candidate=lc.recover_skill_metadata_candidate("owned.read",sys.argv[1])
with app.test_request_context("/",environ_overrides={"REMOTE_ADDR":"127.0.0.1"}):
    principal=p.resolve_local_workspace_principal(module="skills",action="write")
    args=dict(gate=gate,principal=principal,domain_id="cth",global_scope=True)
    try:
        lc.apply_skill_metadata_change(candidate,**args)
    except PermissionError:
        denied=True
    else:
        raise AssertionError("restart replay accepted without fresh approval")
    resource=p.skill_metadata_approval_resource(candidate,principal=principal,domain_id="cth",global_scope=True)
    gate.grant_approval(p.OperationType.CONFIG_MODIFY.value,resource=resource,granted_by="isolated-test-human-after-restart")
    result=lc.apply_skill_metadata_change(candidate,**args)
print(json.dumps(dict(denied_before_approval=denied,state=result["state"],evidence_ref=result["evidence_ref"],resource=resource)))
''', encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("PERMISSION_GATE_TESTING", None)
    env["PYTHONPATH"] = str(root)
    output = subprocess.run([sys.executable, str(child), first["evidence_ref"]], cwd=root,
                            env=env, capture_output=True, text=True, timeout=30, check=True)
    result = json.loads(output.stdout.strip().splitlines()[-1])
    assert result == {"denied_before_approval": True, "state": "already_applied",
                      "evidence_ref": first["evidence_ref"], "resource": resource}
    assert _row(path) == before and _history_count(path) == 1
