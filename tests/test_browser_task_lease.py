"""Isolated SYSTEM/browser task lease tests; no browser action or live E2E."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from flask import Flask

import account.authorization as account_authorization
import account.service as account_service
import ai_task_engine as task_engine_module
from ai_task_engine import BrowserTaskLease, TaskEngine

_ACTOR_ID = 741
_ACCOUNT_SESSION_ID = 852
_BROWSER_SESSION_ID = "bs_0123456789ab"
_TARGET = "https://example.invalid/work?auth=do-not-store"


class _Session:
    def __init__(self, *, actor_id=_ACTOR_ID, account_session_id=_ACCOUNT_SESSION_ID,
                 principal_ref=None, session_id=_BROWSER_SESSION_ID, status="running"):
        self.session_id = session_id
        self.owner_actor_id = actor_id
        self.owner_account_session_id = account_session_id
        self.owner_principal_ref = principal_ref
        self.status = SimpleNamespace(value=status)

    def is_alive(self):
        return self.status.value in {"created", "running"}


class _SessionManager:
    def __init__(self, *sessions):
        self.sessions = {item.session_id: item for item in sessions}

    def get_session(self, session_id):
        session = self.sessions.get(session_id)
        return session if session and session.is_alive() else None


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "browser-task.sqlite3"))
    monkeypatch.setattr(task_engine_module, "_LIFECYCLE_AVAILABLE", False)
    session = _Session()
    manager = _SessionManager(session)
    monkeypatch.setattr(
        "ai_browser_runtime.get_session_manager", lambda: manager,
    )
    current = {"id": _ACTOR_ID, "session_id": _ACCOUNT_SESSION_ID}
    permission = {"allowed": True, "calls": []}

    def get_current_user():
        return dict(current)

    def check_dual_domain_permission(actor_id, product_id, *, module, action):
        permission["calls"].append((actor_id, product_id, module, action))
        return permission["allowed"]

    monkeypatch.setattr(account_service, "get_current_user", get_current_user)
    monkeypatch.setattr(
        account_authorization, "check_dual_domain_permission",
        check_dual_domain_permission,
    )
    engine = TaskEngine(auto_init_db=True)
    return SimpleNamespace(
        engine=engine, session=session, manager=manager,
        current=current, permission=permission,
    )


def _account_kwargs(**overrides):
    result = {
        "actor_id": _ACTOR_ID,
        "account_session_id": _ACCOUNT_SESSION_ID,
    }
    result.update(overrides)
    return result


def _create(setup, *, target_url=_TARGET, browser_session_id=_BROWSER_SESSION_ID,
            **identity):
    return setup.engine.create_browser_task(
        target_url, browser_session_id=browser_session_id,
        **(_account_kwargs() if not identity else identity),
    )


def _task_call(setup, method, task_id, *, target_url=_TARGET,
               browser_session_id=_BROWSER_SESSION_ID, **kwargs):
    return getattr(setup.engine, method)(
        task_id, target_url=target_url, browser_session_id=browser_session_id,
        **(_account_kwargs() if not kwargs else kwargs),
    )


def _raw_row(setup, task_id):
    with sqlite3.connect(os.environ["ZBC_DB_PATH"]) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute(
            "SELECT * FROM ai_task WHERE task_id=?", (task_id,),
        ).fetchone())


def _claim(setup, task_id, *, target_url=_TARGET, **overrides):
    values = _account_kwargs()
    values.update(overrides)
    return setup.engine.claim_browser_task(
        task_id, target_url=target_url, browser_session_id=_BROWSER_SESSION_ID,
        **values,
    )


def _require(setup, task_id, lease, **overrides):
    values = _account_kwargs()
    values.update(overrides)
    return setup.engine.require_current_browser_task(
        task_id, lease=lease, target_url=_TARGET,
        browser_session_id=_BROWSER_SESSION_ID, **values,
    )


def _finish(setup, task_id, lease, *, target_url=_TARGET, **result_or_error):
    return setup.engine.finish_browser_task(
        task_id, lease=lease, target_url=target_url,
        browser_session_id=_BROWSER_SESSION_ID, **_account_kwargs(),
        **result_or_error,
    )


def test_create_read_and_receipt_keep_only_safe_target_display(setup):
    created = _create(setup)
    task_id = created["task_id"]

    assert task_id.startswith("task-browser-")
    assert created["status"] == "pending"
    assert created["scope"] == {
        "product_id": "SYSTEM", "module": "browser", "origin": "NOT_BOUND",
        "model": "NOT_BOUND", "source": "NOT_BOUND",
    }
    assert created["target_display"] == "https://example.invalid/work"
    assert created["authority"] == "NONE" and created["grants"] == []
    assert "owner_key" not in created and "browser_session_id" not in created

    row = _raw_row(setup, task_id)
    context = json.loads(row["context_json"])
    assert row["created_by"] == "system_browser_task"
    assert context["managed_owner"] == context["created_by"] == "system_browser_task"
    assert context["intent"] == "system_browser_task"
    assert context["owner_key"] == f"account:{_ACTOR_ID}:{_ACCOUNT_SESSION_ID}"
    assert context["browser_session_id"] == _BROWSER_SESSION_ID
    assert context["target_sha256"] == __import__("hashlib").sha256(_TARGET.encode()).hexdigest()
    assert "auth=do-not-store" not in row["context_json"]
    assert row["user_input"] == "Internal browser task"
    assert setup.permission["calls"]
    assert set(setup.permission["calls"]) == {
        (_ACTOR_ID, "SYSTEM", "browser", "write"),
        (_ACTOR_ID, "SYSTEM", "browser", "read"),
    }


@pytest.mark.parametrize("target", [
    "file:///etc/passwd", "javascript:alert(1)",
    "https://user:password@example.invalid/path", "https://example.invalid/a\r\nX: y",
    " https://example.invalid/path", "https://example.invalid/has space",
])
def test_invalid_target_is_rejected_before_persistence(setup, target):
    with pytest.raises(ValueError, match="BROWSER_TASK_TARGET_INVALID"):
        _create(setup, target_url=target)
    assert setup.engine.list_tasks() == []


def test_actual_manager_session_owner_and_closed_status_are_required(setup):
    setup.session.owner_actor_id = _ACTOR_ID + 1
    with pytest.raises(PermissionError, match="BROWSER_TASK_SESSION_OWNER_DENIED"):
        _create(setup)
    setup.session.owner_actor_id = _ACTOR_ID
    setup.session.status.value = "closed"
    with pytest.raises(PermissionError, match="BROWSER_TASK_SESSION_UNAVAILABLE"):
        _create(setup)
    assert setup.engine.list_tasks() == []


@pytest.mark.parametrize("identity", [
    {"actor_id": _ACTOR_ID + 1, "account_session_id": _ACCOUNT_SESSION_ID},
    {"actor_id": _ACTOR_ID, "account_session_id": _ACCOUNT_SESSION_ID + 1},
])
def test_account_identity_must_match_fresh_authenticated_user(setup, identity):
    with pytest.raises(PermissionError, match="BROWSER_TASK_IDENTITY_DENIED"):
        _create(setup, **identity)
    assert setup.engine.list_tasks() == []


def test_every_read_binds_current_owner_browser_session_and_exact_raw_target(setup):
    task = _create(setup)
    task_id = task["task_id"]

    setup.current["id"] = _ACTOR_ID + 1
    with pytest.raises(PermissionError, match="BROWSER_TASK_IDENTITY_DENIED"):
        _task_call(setup, "get_browser_task", task_id)
    setup.current["id"] = _ACTOR_ID

    with pytest.raises(PermissionError, match="BROWSER_TASK_SCOPE_DENIED"):
        setup.engine.get_browser_task(
            task_id, target_url=_TARGET, browser_session_id="bs_ffffffffffff",
            **_account_kwargs(),
        )
    with pytest.raises(PermissionError, match="BROWSER_TASK_SCOPE_DENIED"):
        _task_call(setup, "get_browser_task", task_id,
                   target_url="https://example.invalid/work?auth=other")


def test_json_shaped_principal_and_public_receipt_cannot_authorize(setup):
    task = _create(setup)
    with pytest.raises(PermissionError, match="BROWSER_TASK_IDENTITY_DENIED"):
        setup.engine.get_browser_task(
            task["task_id"], target_url=_TARGET,
            browser_session_id=_BROWSER_SESSION_ID,
            principal={"principal_kind": "local_workspace", "principal_ref": "workspace:local"},
        )
    with pytest.raises(TypeError, match="issued only by TaskEngine"):
        BrowserTaskLease(_issuer=object())

    lease = _claim(setup, task["task_id"])
    receipt = lease.to_public_receipt()
    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_INVALID"):
        _require(setup, task["task_id"], receipt)
    assert receipt["authority"] == "NONE"
    assert receipt["grants"] == []
    assert receipt["model_analyze"] == "NOT_GRANTED"
    assert receipt["source_use"] == "NOT_GRANTED"
    assert receipt["browser_action"] == "NOT_GRANTED"


def test_claim_is_single_transactional_cas_and_receipt_is_not_a_grant(setup):
    task = _create(setup)
    task_id = task["task_id"]
    barrier = threading.Barrier(3)

    def claim():
        barrier.wait(timeout=5)
        try:
            return _claim(setup, task_id)
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim) for _ in range(2)]
        barrier.wait(timeout=5)
        claims = [future.result(timeout=15) for future in futures]

    leases = [item for item in claims if type(item) is BrowserTaskLease]
    assert len(leases) == 1
    assert claims.count("BROWSER_TASK_NOT_RUNNABLE") == 1
    lease = leases[0]
    assert lease.attempt == 1 and len(lease.run_id) == 32
    assert lease.worker_pid > 0 and lease.worker_create_time > 0
    assert 30 <= lease.lease_seconds <= 300
    assert _require(setup, task_id, lease)["status"] == "running"
    public = setup.engine.get_browser_task(
        task_id, target_url=_TARGET, browser_session_id=_BROWSER_SESSION_ID,
        **_account_kwargs(),
    )
    assert public["lease_receipt"]["authority"] == "NONE"
    assert public["lease_receipt"]["grants"] == []


def test_heartbeat_supersedes_old_lease_and_rejects_expired_or_forged_lease(setup):
    task = _create(setup)
    task_id = task["task_id"]
    old = _claim(setup, task_id)
    renewed = setup.engine.heartbeat_browser_task(
        task_id, lease=old, target_url=_TARGET,
        browser_session_id=_BROWSER_SESSION_ID, **_account_kwargs(),
    )
    assert renewed.run_id == old.run_id and renewed.attempt == old.attempt
    assert renewed.heartbeat_at >= old.heartbeat_at
    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_STALE"):
        _require(setup, task_id, old)

    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_INVALID"):
        setup.engine.heartbeat_browser_task(
            task_id, lease={"task_id": task_id, "run_id": renewed.run_id},
            target_url=_TARGET, browser_session_id=_BROWSER_SESSION_ID,
            **_account_kwargs(),
        )


def test_expired_live_worker_cannot_be_reclaimed_by_timeout(setup):
    task = _create(setup)
    task_id = task["task_id"]
    _claim(setup, task_id)
    row = _raw_row(setup, task_id)
    parameters = json.loads(row["parameters_json"])
    parameters["heartbeat_at"] = time.time() - 60
    parameters["lease_seconds"] = 30
    parameters["lease_expires_at"] = parameters["heartbeat_at"] + 30
    with sqlite3.connect(os.environ["ZBC_DB_PATH"]) as connection:
        connection.execute(
            "UPDATE ai_task SET parameters_json=? WHERE task_id=?",
            (json.dumps(parameters, sort_keys=True, separators=(",", ":")), task_id),
        )

    with pytest.raises(RuntimeError, match="BROWSER_TASK_WORKER_STILL_ACTIVE"):
        _task_call(setup, "reconcile_browser_task", task_id)
    with pytest.raises(ValueError, match="BROWSER_TASK_NOT_RUNNABLE"):
        _claim(setup, task_id)


def test_dead_worker_recovery_increments_attempt_and_invalidates_old_run(setup, monkeypatch):
    import psutil

    task = _create(setup)
    task_id = task["task_id"]
    old = _claim(setup, task_id)

    def gone_process(_pid):
        raise psutil.NoSuchProcess(_pid)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(psutil, "Process", gone_process)
        recovered = _task_call(setup, "reconcile_browser_task", task_id)
    assert recovered["status"] == "interrupted"

    new = _claim(setup, task_id)
    assert new.attempt == old.attempt + 1
    assert new.run_id != old.run_id
    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_STALE"):
        _require(setup, task_id, old)
    assert _require(setup, task_id, new)["status"] == "running"


def test_cancel_invalidates_running_lease_and_preserves_terminal_result(setup):
    task = _create(setup)
    task_id = task["task_id"]
    lease = _claim(setup, task_id)
    cancelled = _task_call(setup, "cancel_browser_task", task_id)
    assert cancelled["status"] == "cancel_requested"
    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_STALE"):
        _require(setup, task_id, lease)
    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_STALE"):
        _finish(setup, task_id, lease, result={"answer": "late"})

    import psutil
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(psutil, "Process", lambda _pid: (_ for _ in ()).throw(psutil.NoSuchProcess(_pid)))
        reconciled = _task_call(setup, "reconcile_browser_task", task_id)
    assert reconciled["status"] == "cancelled" and reconciled["result"] is None

    other_task = _create(setup, target_url="https://example.invalid/final")
    other_id = other_task["task_id"]
    final_url = "https://example.invalid/final"
    current = _claim(setup, other_id, target_url=final_url)
    assert _finish(
        setup, other_id, current,
        target_url=final_url,
        result={"summary": "stored", "access_token": "never-persist-this"},
    ) is True
    finished = _task_call(setup, "get_browser_task", other_id,
                          target_url=final_url)
    assert finished["status"] == "finished"
    assert finished["result"]["business_outcome"] == "NOT_OBSERVED"
    assert finished["result"]["evaluation"] == "NOT_EVALUATED"
    assert finished["result"]["promotion"] == "NOT_PROMOTED"
    assert finished["result"]["payload"]["access_token"] == "[redacted]"

    cancelled_terminal = _task_call(
        setup, "cancel_browser_task", other_id, target_url=final_url,
    )
    assert cancelled_terminal["status"] == "finished"
    assert cancelled_terminal["result"] == finished["result"]

    # Finished results are history and remain readable after their Browser/Core
    # session disappears; the read still checks current identity, permission and
    # exact persisted owner/session/target binding.
    setup.manager.sessions.clear()
    reopened = TaskEngine(auto_init_db=False)
    reopened_state = reopened.get_browser_task(
        other_id, target_url=final_url,
        browser_session_id=_BROWSER_SESSION_ID, **_account_kwargs(),
    )
    assert reopened_state["result"] == finished["result"]
    setup.current["id"] = _ACTOR_ID + 1
    with pytest.raises(PermissionError, match="BROWSER_TASK_IDENTITY_DENIED"):
        reopened.get_browser_task(
            other_id, target_url=final_url,
            browser_session_id=_BROWSER_SESSION_ID, **_account_kwargs(),
        )


def test_permission_revocation_before_claim_write_leaves_row_unchanged(setup, monkeypatch):
    task = _create(setup)
    task_id = task["task_id"]
    before = _raw_row(setup, task_id)
    calls = []

    def revoke_between_admission_and_cas(actor_id, product_id, *, module, action):
        calls.append(action)
        return len(calls) == 1

    monkeypatch.setattr(
        account_authorization, "check_dual_domain_permission",
        revoke_between_admission_and_cas,
    )
    with pytest.raises(PermissionError, match="BROWSER_TASK_PERMISSION_DENIED"):
        _claim(setup, task_id)
    after = _raw_row(setup, task_id)
    assert calls == ["write", "write"]
    assert before["status"] == after["status"] == "pending"
    assert before["parameters_json"] == after["parameters_json"] == "{}"


@pytest.mark.parametrize("operation", ["heartbeat", "finish"])
def test_expiry_during_final_fresh_auth_prevents_lease_write(setup, monkeypatch, operation):
    task = _create(setup)
    task_id = task["task_id"]
    lease = _claim(setup, task_id)
    before = _raw_row(setup, task_id)
    original_request = TaskEngine._browser_task_request
    calls = []

    def expire_during_final_auth(**kwargs):
        result = original_request(**kwargs)
        calls.append(kwargs["action"])
        if len(calls) == 2:
            # Model permission/session resolution consuming the remaining TTL.
            monkeypatch.setattr(
                task_engine_module.time, "time",
                lambda: lease.lease_expires_at + 1.0,
            )
        return result

    monkeypatch.setattr(
        TaskEngine, "_browser_task_request", staticmethod(expire_during_final_auth),
    )
    with pytest.raises(PermissionError, match="BROWSER_TASK_LEASE_EXPIRED"):
        if operation == "heartbeat":
            setup.engine.heartbeat_browser_task(
                task_id, lease=lease, target_url=_TARGET,
                browser_session_id=_BROWSER_SESSION_ID, **_account_kwargs(),
            )
        else:
            setup.engine.finish_browser_task(
                task_id, lease=lease, target_url=_TARGET,
                browser_session_id=_BROWSER_SESSION_ID,
                result={"answer": "must not persist"}, **_account_kwargs(),
            )
    after = _raw_row(setup, task_id)
    assert calls == ["write", "write"]
    assert after["status"] == before["status"] == "running"
    assert after["parameters_json"] == before["parameters_json"]
    assert after["result_json"] == before["result_json"] is None


def test_worker_timing_metadata_must_be_positive_and_self_consistent(setup):
    task = _create(setup)
    task_id = task["task_id"]
    _claim(setup, task_id)
    row = _raw_row(setup, task_id)
    parameters = json.loads(row["parameters_json"])
    parameters["lease_expires_at"] += 0.25
    with sqlite3.connect(os.environ["ZBC_DB_PATH"]) as connection:
        connection.execute(
            "UPDATE ai_task SET parameters_json=? WHERE task_id=?",
            (json.dumps(parameters, sort_keys=True, separators=(",", ":")), task_id),
        )
    with pytest.raises(ValueError, match="BROWSER_TASK_WORKER_INTEGRITY_INVALID"):
        _task_call(setup, "get_browser_task", task_id)


def test_real_local_workspace_principal_requires_fresh_browser_resolution(setup):
    from lumenis.system.security import permission

    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    local_session = _Session(
        actor_id=None, account_session_id=None, principal_ref="workspace:local",
        session_id="bs_abcdef012345",
    )
    setup.manager.sessions = {local_session.session_id: local_session}
    headers = {"Host": "localhost"}

    with app.test_request_context(
        "/", headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = permission.resolve_local_workspace_principal(
            module="browser", action="write",
        )
        assert type(principal) is permission.LocalWorkspacePrincipal
        task = setup.engine.create_browser_task(
            _TARGET, browser_session_id=local_session.session_id, principal=principal,
        )
        got = setup.engine.get_browser_task(
            task["task_id"], target_url=_TARGET,
            browser_session_id=local_session.session_id, principal=principal,
        )
        assert got["status"] == "pending"

    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    with app.test_request_context(
        "/", headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ), pytest.raises(PermissionError, match="BROWSER_TASK_PERMISSION_DENIED"):
        setup.engine.get_browser_task(
            task["task_id"], target_url=_TARGET,
            browser_session_id=local_session.session_id, principal=principal,
        )


def test_generic_task_paths_and_forged_managed_owner_are_denied(setup):
    with pytest.raises(PermissionError, match="browser tasks"):
        setup.engine.create_task("forged", created_by="system_browser_task")
    with pytest.raises(PermissionError, match="browser tasks"):
        setup.engine.create_task(
            "forged", context={"managed_owner": "system_browser_task"},
        )
    with pytest.raises(PermissionError, match="browser tasks"):
        setup.engine.create_mathematical_task(
            "forged", {"openai_math_request_id": "a" * 32,
                        "managed_owner": "system_browser_task"},
            created_by="unit-test",
        )
    forged_id = "task-browser-00000000-0000-4000-8000-000000000000"
    for call in (
        lambda: setup.engine.get_task(forged_id),
        lambda: setup.engine.get_steps(forged_id),
        lambda: setup.engine.get_evidence(forged_id),
        lambda: setup.engine.get_trace(forged_id),
        lambda: setup.engine.run_task(forged_id),
        lambda: setup.engine.cancel_task(forged_id),
    ):
        with pytest.raises(PermissionError):
            call()


def test_generic_lists_do_not_disclose_managed_browser_task_rows(setup):
    task = _create(setup)
    task_id = task["task_id"]
    assert all(row["task_id"] != task_id for row in setup.engine.list_tasks())
    assert all(row["task_id"] != task_id for row in setup.engine.get_trace())


def test_context_tampering_fails_closed_without_exposing_private_fields(setup):
    task = _create(setup)
    task_id = task["task_id"]
    raw = _raw_row(setup, task_id)
    context = json.loads(raw["context_json"])
    context["browser_session_id"] = "bs_ffffffffffff"
    with sqlite3.connect(os.environ["ZBC_DB_PATH"]) as connection:
        connection.execute(
            "UPDATE ai_task SET context_json=? WHERE task_id=?",
            (json.dumps(context, sort_keys=True, separators=(",", ":")), task_id),
        )
    with pytest.raises(PermissionError, match="BROWSER_TASK_SCOPE_DENIED"):
        _task_call(setup, "get_browser_task", task_id)
