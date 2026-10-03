"""Durable managed TaskEngine state for the owned-training phase seam."""
from __future__ import annotations

import copy
import json
import os
import sqlite3
import subprocess
import sys
import time

import pytest

from ai_task_engine import TaskEngine, _TASK_ENGINE_SCHEMA, init_task_engine_db
from lumenis.shared.database import get_repository


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OWNER = "owned_training_phase_receipts:v1"


def _binding(actor_id=41):
    if actor_id is None:
        identity = {
            "actor_id": None,
            "caller": "workspace:local",
            "principal_kind": "local_workspace",
            "principal_ref": "workspace:local",
        }
    else:
        identity = {
            "actor_id": actor_id,
            "caller": f"actor:{actor_id}",
            "principal_kind": None,
            "principal_ref": None,
        }
    return {
        "resource": "owned_training:v1:" + "a" * 64,
        "identity": identity,
        "scope_descriptors": {
            "SUBJECT-41": {
                "domain_id": "cth",
                "product_id": "CTH",
                "global_scope": False,
                "subject_id": "SUBJECT-41",
                "brand_focus_id": None,
            },
        },
    }


def _fingerprints():
    return {
        "request_sha256": "1" * 64,
        "model_identity_sha256": "2" * 64,
        "manifest_sha256": "3" * 64,
        "train_sha256": "4" * 64,
        "heldout_sha256": "5" * 64,
        "recipe_sha256": "6" * 64,
        "scope_sha256": "7" * 64,
    }


@pytest.fixture
def task_state_db(tmp_path, monkeypatch):
    db_path = tmp_path / "task-state.sqlite3"
    seed_path = tmp_path / "process-seed.sqlite3"
    seed_connection = sqlite3.connect(seed_path)
    seed_connection.close()
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("LUMENIS_TEST_SEED_DB", str(seed_path))
    init_task_engine_db()
    return db_path


def _create(engine, *, binding=None, fingerprints=None):
    return engine.create_training_receipt_task(
        binding=binding or _binding(),
        fingerprints=fingerprints or _fingerprints(),
    )


def _challenge(state, *, nonce=None, issued_at=None, expires_at=None, **changes):
    now = int(time.time())
    value = {
        "schema_version": 1,
        "run_digest": state["run_digest"],
        "task_digest": state["task_digest"],
        **state["fingerprints"],
        "nonce": nonce or "8" * 64,
        "phase": "before_train",
        "sequence": state["next_sequence"],
        "issued_at": now if issued_at is None else issued_at,
        "expires_at": now + 30 if expires_at is None else expires_at,
    }
    value.update(changes)
    return value


def _consume(engine, state, challenge, *, binding=None, decision="allow", receipt_sha256="9" * 64,
             connection=None):
    repository = get_repository()
    owns_connection = connection is None
    connection = connection or repository.connect(timeout=30)
    try:
        if owns_connection:
            connection.execute("BEGIN IMMEDIATE")
        result = engine.consume_training_phase_challenge(
            state["task_id"],
            expected_binding=binding or _binding(),
            challenge=challenge,
            receipt_sha256=receipt_sha256,
            decision=decision,
            connection=connection,
        )
        if owns_connection:
            connection.commit()
        return result
    finally:
        if owns_connection:
            connection.close()


def test_private_binding_persists_and_state_reopens_in_another_process(task_state_db):
    engine = TaskEngine()
    binding = _binding()
    state = _create(engine, binding=binding)

    assert state["task_id"].startswith("trainrelay_")
    assert state["status"] == "ready" and state["next_sequence"] == 1
    assert set(state) == {
        "task_id", "run_digest", "task_digest", "next_sequence", "fingerprints", "status",
    }
    assert state["task_digest"] == __import__("hashlib").sha256(
        state["task_id"].encode("utf-8")
    ).hexdigest()
    assert state["fingerprints"] == _fingerprints()
    assert TaskEngine().get_training_receipt_task(
        state["task_id"], expected_binding=binding,
    ) == state

    repository = get_repository()
    with repository.connection() as connection:
        row = connection.execute(
            "SELECT user_input, status, created_by, context_json, approval_token, approved_by "
            "FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()
        tables = {
            item[0] for item in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    stored = json.loads(row["context_json"])
    assert row["user_input"] == "Owned training phase receipt state"
    assert row["status"] == "ready" and row["created_by"] == _OWNER
    assert row["approval_token"] is None and row["approved_by"] is None
    assert stored["managed_owner"] == _OWNER and stored["binding"] == binding
    assert "training_phase" not in " ".join(tables)

    script = (
        "import json,sys; from ai_task_engine import TaskEngine; "
        "binding={'resource':'owned_training:v1:'+'a'*64,'identity':"
        "{'actor_id':41,'caller':'actor:41','principal_kind':None,'principal_ref':None},"
        "'scope_descriptors':{'SUBJECT-41':{'domain_id':'cth','product_id':'CTH',"
        "'global_scope':False,'subject_id':'SUBJECT-41','brand_focus_id':None}}}; "
        "print(json.dumps(TaskEngine().get_training_receipt_task(sys.argv[1],"
        "expected_binding=binding),sort_keys=True))"
    )
    child = subprocess.run(
        [sys.executable, "-c", script, state["task_id"]],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == state


@pytest.mark.parametrize("invalid_binding", [
    {**_binding(), "extra": "field"},
    {**_binding(), "identity": {"actor_id": True, "caller": "actor:True",
                                 "principal_kind": None, "principal_ref": None}},
    {**_binding(), "identity": {"actor_id": 41, "caller": "actor:42",
                                 "principal_kind": None, "principal_ref": None}},
    {**_binding(), "scope_descriptors": {}},
])
def test_creation_rejects_noncanonical_binding(invalid_binding, task_state_db):
    with pytest.raises(ValueError):
        _create(TaskEngine(), binding=invalid_binding)


def test_workspace_identity_and_fingerprint_contract_are_exact(task_state_db):
    state = _create(TaskEngine(), binding=_binding(actor_id=None))
    assert TaskEngine().get_training_receipt_task(
        state["task_id"], expected_binding=_binding(actor_id=None),
    ) == state
    invalid = _fingerprints()
    invalid["scope_sha256"] = "A" * 64
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        _create(TaskEngine(), fingerprints=invalid)


@pytest.mark.parametrize("name", [
    "run_digest", "task_digest", "request_sha256", "model_identity_sha256",
    "manifest_sha256", "train_sha256", "heldout_sha256", "recipe_sha256",
    "scope_sha256", "sequence",
])
def test_challenge_must_match_current_task_epoch_and_all_hashes(name, task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    altered = 2 if name == "sequence" else "0" * 64
    challenge = _challenge(state, **{name: altered})
    with pytest.raises(PermissionError, match="does not match"):
        _consume(engine, state, challenge)
    assert engine.get_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )["next_sequence"] == 1


def test_expired_or_extra_field_challenges_fail_before_any_step(task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    now = int(time.time())
    expired = _challenge(state, issued_at=now - 90, expires_at=now - 30)
    with pytest.raises(ValueError, match="TIME_INVALID"):
        _consume(engine, state, expired)
    with pytest.raises(ValueError, match="SCHEMA_INVALID"):
        _consume(engine, state, {**_challenge(state), "binding": _binding()})
    with get_repository().connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0] == 0


def test_consumption_is_co_transactional_and_rollback_restores_nonce(task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    challenge = _challenge(state)
    connection = get_repository().connect(timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = _consume(engine, state, challenge, connection=connection)
        assert result["next_sequence"] == 2 and result["status"] == "running"
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0] == 1
        connection.rollback()
    finally:
        connection.close()

    reopened = TaskEngine().get_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )
    assert reopened["next_sequence"] == 1 and reopened["status"] == "ready"
    with get_repository().connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0] == 0


def test_committed_nonce_cannot_replay_or_be_reused_at_a_new_sequence(task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    first = _challenge(state, nonce="b" * 64)
    _consume(engine, state, first)
    current = engine.get_training_receipt_task(state["task_id"], expected_binding=_binding())
    assert current["next_sequence"] == 2 and current["status"] == "running"

    with pytest.raises(PermissionError, match="does not match"):
        _consume(engine, current, first)
    reused_nonce = _challenge(current, nonce=first["nonce"])
    with pytest.raises(sqlite3.IntegrityError):
        _consume(engine, current, reused_nonce)
    after_replay = engine.get_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )
    assert after_replay["next_sequence"] == 2 and after_replay["status"] == "running"
    with get_repository().connection() as connection:
        rows = connection.execute(
            "SELECT step_id, phase, status, detail FROM ai_task_step WHERE task_id=?",
            (state["task_id"],),
        ).fetchall()
    assert len(rows) == 1 and rows[0]["phase"] == "before_train" and rows[0]["status"] == "allow"
    detail = json.loads(rows[0]["detail"])
    assert detail["receipt_sha256"] == "9" * 64 and detail["decision"] == "allow"
    assert set(detail["challenge"]) == set(first)
    assert "binding" not in detail and "identity" not in detail


def test_maximum_sequence_rejects_before_step_or_context_mutation(task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    with get_repository().transaction(timeout=30) as connection:
        row = connection.execute(
            "SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()
        context = json.loads(row[0])
        context["next_sequence"] = 1_000_000_000
        connection.execute(
            "UPDATE ai_task SET context_json=? WHERE task_id=?",
            (json.dumps(context, ensure_ascii=False, sort_keys=True), state["task_id"]),
        )

    boundary = engine.get_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )
    assert boundary["next_sequence"] == 1_000_000_000
    challenge = _challenge(boundary, nonce="a" * 64)
    connection = get_repository().connect(timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        before = connection.execute(
            "SELECT context_json, status FROM ai_task WHERE task_id=?",
            (state["task_id"],),
        ).fetchone()
        steps_before = connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0]
        with pytest.raises(RuntimeError, match="sequence space is exhausted"):
            engine.consume_training_phase_challenge(
                state["task_id"], expected_binding=_binding(), challenge=challenge,
                receipt_sha256="b" * 64, decision="allow", connection=connection,
            )
        after = connection.execute(
            "SELECT context_json, status FROM ai_task WHERE task_id=?",
            (state["task_id"],),
        ).fetchone()
        steps_after = connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0]
        assert tuple(after) == tuple(before)
        assert steps_after == steps_before == 0
        connection.rollback()
    finally:
        connection.close()

    readable = engine.get_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )
    assert readable["next_sequence"] == 1_000_000_000
    assert readable["status"] == "ready"


def test_wrong_binding_wrong_connection_and_missing_transaction_are_rejected(task_state_db, tmp_path):
    engine = TaskEngine()
    state = _create(engine)
    other_binding = _binding(actor_id=42)
    with pytest.raises(PermissionError, match="binding"):
        engine.get_training_receipt_task(state["task_id"], expected_binding=other_binding)

    no_transaction = get_repository().connect(timeout=30)
    try:
        with pytest.raises(RuntimeError, match="active SQLite transaction"):
            _consume(engine, state, _challenge(state), connection=no_transaction)
    finally:
        no_transaction.close()

    wrong_path = tmp_path / "wrong.sqlite3"
    wrong = sqlite3.connect(wrong_path)
    wrong.executescript(_TASK_ENGINE_SCHEMA)
    wrong.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(RuntimeError, match="canonical TaskEngine database"):
            _consume(engine, state, _challenge(state), connection=wrong)
    finally:
        wrong.rollback()
        wrong.close()


def test_deny_records_a_denial_and_never_claims_training_success(task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    result = _consume(engine, state, _challenge(state), decision="deny", receipt_sha256="c" * 64)
    assert result["status"] == "failed" and result["next_sequence"] == 2
    assert result["status"] not in {"succeeded", "trained", "promoted"}
    with get_repository().connection() as connection:
        row = connection.execute(
            "SELECT status, finished_at, result_json, approval_token FROM ai_task WHERE task_id=?",
            (state["task_id"],),
        ).fetchone()
        step = connection.execute(
            "SELECT status, detail FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()
    assert row["status"] == "failed" and row["finished_at"] is not None
    assert row["result_json"] is None and row["approval_token"] is None
    assert step["status"] == "deny"
    assert json.loads(step["detail"])["decision"] == "deny"


def test_interrupt_and_resume_rotate_run_epoch_without_rewinding_sequence(task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    first = _challenge(state, nonce="d" * 64)
    accepted = _consume(engine, state, first)
    interrupted = engine.interrupt_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )
    assert interrupted["status"] == "unknown" and interrupted["next_sequence"] == 2
    with pytest.raises(PermissionError, match="not available"):
        _consume(engine, interrupted, _challenge(interrupted))

    resumed = engine.resume_training_receipt_task(
        state["task_id"], expected_binding=_binding(),
    )
    assert resumed["status"] == "ready" and resumed["next_sequence"] == accepted["next_sequence"]
    assert resumed["run_digest"] != accepted["run_digest"]
    old_epoch = _challenge(accepted, nonce="e" * 64, sequence=2)
    with pytest.raises(PermissionError, match="does not match"):
        _consume(engine, resumed, old_epoch)
    fresh = _challenge(resumed, nonce="f" * 64)
    assert _consume(engine, resumed, fresh)["next_sequence"] == 3
    with pytest.raises(PermissionError, match="unknown"):
        engine.resume_training_receipt_task(state["task_id"], expected_binding=_binding())


@pytest.mark.parametrize("method,args", [
    ("get_task", {}), ("get_steps", {}), ("get_evidence", {}),
    ("parse_task", {}), ("select_agent_and_skill", {}), ("check_permission", {}),
    ("execute_task", {}), ("approve_task", {}), ("cancel_task", {}), ("run_task", {}),
    ("get_trace", {}),
])
def test_generic_task_api_cannot_access_managed_training_state(method, args, task_state_db):
    engine = TaskEngine()
    state = _create(engine)
    with pytest.raises(PermissionError, match="training receipt tasks"):
        getattr(engine, method)(state["task_id"], **args)
    assert all(item["task_id"] != state["task_id"] for item in engine.list_tasks())


def test_generic_creation_cannot_claim_the_reserved_training_owner(task_state_db):
    engine = TaskEngine()
    with pytest.raises(PermissionError, match="training receipt tasks"):
        engine.create_task("user content", created_by=_OWNER)
    with pytest.raises(PermissionError, match="training receipt tasks"):
        engine.create_task("user content", context={"managed_owner": _OWNER})
    assert engine.list_tasks() == []
