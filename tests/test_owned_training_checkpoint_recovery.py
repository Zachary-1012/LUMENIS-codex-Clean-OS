"""Disposable trainer-side recovery checks; no model or permission is issued."""
import copy
import hashlib
import json
import os
from pathlib import Path
import time
from collections import OrderedDict
from types import SimpleNamespace

import numpy as np
import pytest

from lumenis.system.ai_gateway import owned_training as training
from lumenis.system.ai_gateway import owned_training_checkpoints as checkpoints
from lumenis.system.ai_gateway.owned_training_phases import TrainingPhaseClient
from lumenis.system.security import training_receipts


def digest(value):
    return hashlib.sha256(checkpoints.canonical_bytes(value)).hexdigest()


@pytest.fixture
def policy_material():
    versions = {name: "test-runtime" for name in checkpoints._FRAMEWORK_PACKAGES}
    config = {"batch_size": 1, "gradient_accumulation_steps": 4, "single_device": True}
    order = {"case_ids": ["synthetic-a", "synthetic-b"], "partition": "unit-only"}
    roles = {
        "adapter_or_model": ["adapter_model.safetensors"],
        "model_config": ["adapter_config.json"],
        "tokenizer": ["tokenizer.json", "tokenizer_config.json"],
        "optimizer": ["optimizer.pt"], "scheduler": ["scheduler.pt"],
        "rng_cpu": ["rng_state.pth"], "rng_cuda": ["lumenis_cuda_rng.safetensors"],
        "trainer_state": ["trainer_state.json"],
        "data_position": ["lumenis_data_position.json"],
        "callback_state": ["lumenis_callback_state.json"],
    }
    document = {
        "schema_version": 1, "base_recipe": training.T4_RECIPE,
        "checkpoint_interval_steps": 2, "max_replay_optimizer_steps": 2,
        "retain_committed": True, "save_only_at_completed_optimizer_step": True,
        "save_only_model": False, "automatic_rotation": False,
        "restore_dataset_position": True, "restore_callback_state": True,
        "rng_devices": ["cpu", "cuda:0"], "required_roles": roles,
        "framework_lock_sha256": digest(versions), "trainer_config_sha256": digest(config),
        "data_order_sha256": digest(order), "numerical_tolerance": {"rtol": 0, "atol": 0},
    }
    return document, versions, config, order


@pytest.fixture
def checkpoint_tree(tmp_path, policy_material):
    document, _, _, _ = policy_material
    policy = checkpoints.CheckpointPolicy.validate(document)
    staging = tmp_path / "reserved-output"
    directory = staging / "checkpoint-2"
    directory.mkdir(parents=True)
    for names in document["required_roles"].values():
        for name in names:
            (directory / name).write_bytes(b"Synthetic inventory bytes; never loaded as a model.")
    # TRL writes this outside the checkpoint directory but within the reservation.
    (staging / "README.md").write_text("Synthetic model card", encoding="utf-8")
    return staging, directory, policy


def test_policy_is_immutable_and_changes_recipe_identity(policy_material):
    document, _, _, _ = policy_material
    policy = checkpoints.CheckpointPolicy.validate(document)
    document["max_replay_optimizer_steps"] = 1
    assert policy.document["max_replay_optimizer_steps"] == 2
    assert checkpoints.CheckpointPolicy.validate(document).recipe != policy.recipe
    copy_out = policy.document
    copy_out["required_roles"].clear()
    assert policy.document["required_roles"]


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("checkpoint_interval_steps", True),
    ("max_replay_optimizer_steps", -1), ("retain_committed", False),
    ("save_only_at_completed_optimizer_step", False), ("save_only_model", True),
    ("automatic_rotation", True), ("restore_dataset_position", False),
    ("restore_callback_state", False), ("rng_devices", ["cpu"]),
    ("base_recipe", training.H100_RECIPE),
    ("numerical_tolerance", {"rtol": float("nan"), "atol": 0}),
    ("numerical_tolerance", {"rtol": True, "atol": 0}),
])
def test_policy_rejects_missing_recovery_guarantees(policy_material, field, value):
    document = copy.deepcopy(policy_material[0])
    document[field] = value
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        checkpoints.CheckpointPolicy.validate(document)


@pytest.mark.parametrize("role", sorted(checkpoints._REQUIRED_ROLES))
def test_policy_cannot_omit_a_required_state_role(policy_material, role):
    document = copy.deepcopy(policy_material[0])
    del document["required_roles"][role]
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        checkpoints.CheckpointPolicy.validate(document)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "\\\\server\\share",
                                  "x/../optimizer.pt", "optimizer.pt:stream", "NUL", "x.", "x//state"])
def test_role_paths_cannot_escape_or_alias_reserved_files(policy_material, name):
    document = copy.deepcopy(policy_material[0])
    document["required_roles"]["optimizer"] = [name]
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_INVENTORY_INVALID"):
        checkpoints.CheckpointPolicy.validate(document)


@pytest.mark.parametrize("raw", [b'{"schema_version":1,"schema_version":2}', b'{"x":NaN}', b'"\xff"'])
def test_strict_metadata_rejects_duplicate_nonfinite_and_invalid_utf8(raw):
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        checkpoints.strict_json(raw)


def test_runtime_lock_and_scaler_are_exact(policy_material):
    document, versions, config, order = policy_material
    policy = checkpoints.CheckpointPolicy.validate(document)
    policy.validate_runtime(framework_versions=versions, trainer_config=config,
                            data_order=order, scaler_present=False)
    for changed in ["versions", "config", "order"]:
        v, c, o = copy.deepcopy((versions, config, order))
        if changed == "versions": v["peft"] = "different-version"
        elif changed == "config": c["gradient_accumulation_steps"] = 2
        else: o["case_ids"].reverse()
        with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_HASH_MISMATCH"):
            policy.validate_runtime(framework_versions=v, trainer_config=c, data_order=o, scaler_present=False)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        policy.validate_runtime(framework_versions=versions, trainer_config=config,
                                data_order=order, scaler_present=True)


def test_registered_policy_is_required_and_hash_cannot_be_relabelled(tmp_path, monkeypatch, policy_material):
    document = policy_material[0]
    policy = checkpoints.CheckpointPolicy.validate(document)
    manifest = tmp_path / "foundation.json"
    monkeypatch.setattr(training, "APPROVED_MANIFEST_PATH", manifest)
    registry = {"schema_version": 1, "policies": {}}
    manifest.write_text(json.dumps({"checkpoint_recovery_policies": registry}), encoding="utf-8")
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_RECIPE_NOT_AUTHORIZED"):
        checkpoints.load_recovery_policy(policy.recipe, manifest)
    registry["policies"][policy.sha256] = document
    manifest.write_text(json.dumps({"checkpoint_recovery_policies": registry}), encoding="utf-8")
    assert checkpoints.load_recovery_policy(policy.recipe, manifest) == policy
    document["max_replay_optimizer_steps"] = 1
    manifest.write_text(json.dumps({"checkpoint_recovery_policies": registry}), encoding="utf-8")
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_HASH_MISMATCH"):
        checkpoints.load_recovery_policy(policy.recipe, manifest)


def test_inventory_covers_full_trl_output_root(checkpoint_tree):
    staging, directory, policy = checkpoint_tree
    inventory = checkpoints.inspect_checkpoint_files(staging, "checkpoint-2", policy)
    assert [item["path"] for item in inventory] == sorted(item["path"] for item in inventory)
    assert {item["path"] for item in inventory} == {
        p.relative_to(staging).as_posix() for p in staging.rglob("*") if p.is_file()
    }
    card = next(item for item in inventory if item["path"] == "README.md")
    assert card["role"] == "auxiliary"
    for item in inventory:
        raw = (staging / item["path"]).read_bytes()
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
        assert item["size_bytes"] == len(raw)


def test_completed_rewrite_before_inventory_is_not_concurrent_mutation(checkpoint_tree):
    staging, _, policy = checkpoint_tree
    card = staging / "README.md"
    time.sleep(0.02)
    card.write_bytes(b"A completed metadata rewrite before inspection")
    inventory = checkpoints.inspect_checkpoint_files(staging, "checkpoint-2", policy)
    record = next(item for item in inventory if item["path"] == "README.md")
    assert record["sha256"] == hashlib.sha256(card.read_bytes()).hexdigest()


@pytest.mark.parametrize("role", sorted(checkpoints._REQUIRED_ROLES))
def test_partial_save_cannot_be_a_complete_inventory(checkpoint_tree, role):
    staging, directory, policy = checkpoint_tree
    (directory / policy.document["required_roles"][role][0]).unlink()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        checkpoints.inspect_checkpoint_files(staging, "checkpoint-2", policy)


def test_required_empty_file_is_not_state(checkpoint_tree):
    staging, directory, policy = checkpoint_tree
    (directory / "optimizer.pt").write_bytes(b"")
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        checkpoints.inspect_checkpoint_files(staging, "checkpoint-2", policy)


def test_external_hardlink_cannot_be_admitted(checkpoint_tree, tmp_path):
    staging, directory, policy = checkpoint_tree
    external = tmp_path / "outside-reservation"
    external.write_bytes(b"External bytes are not checkpoint-owned")
    path = directory / "optimizer.pt"
    path.unlink()
    os.link(external, path)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_INVENTORY_INVALID"):
        checkpoints.inspect_checkpoint_files(staging, "checkpoint-2", policy)
    assert external.read_bytes() == b"External bytes are not checkpoint-owned"


def test_inventory_detects_mutation_during_read(checkpoint_tree, monkeypatch):
    staging, directory, policy = checkpoint_tree
    victim = directory / "optimizer.pt"
    original_open = Path.open

    class MutatingReader:
        def __init__(self, stream): self.stream, self.changed = stream, False
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def fileno(self): return self.stream.fileno()
        def read(self, count):
            value = self.stream.read(count)
            if value and not self.changed:
                self.changed = True
                with original_open(victim, "wb") as target:
                    target.write(b"Changed while reading")
            return value

    def opened(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return MutatingReader(stream) if path == victim and args == ("rb",) else stream

    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_HASH_MISMATCH"):
        checkpoints.inspect_checkpoint_files(staging, "checkpoint-2", policy)


def test_resume_without_authority_owner_never_calls_transport(monkeypatch):
    monkeypatch.delattr(training_receipts, "VerifiedTrainingRecoveryHandoff", raising=False)
    calls = []
    request = training.TrainingApprovalRequest("unit-only", "unit-only", "a" * 64,
                                               "b" * 64, ("unit-scope",))
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_CONTRACT_NOT_BOUND"):
        TrainingPhaseClient.from_recovery_handoff(
            request, {}, handoff={"verified": True}, pinned_public_key={},
            transport=lambda *args: calls.append(args),
        )
    assert calls == []


def data_cursor(count=10):
    rows = [digest({"synthetic_row": i}) for i in range(count)]
    cursor = checkpoints.TrainingDataCursor(dataset_sha256="d" * 64,
                                           row_sha256=rows, gradient_accumulation_steps=4)
    return cursor, rows


def consume_update(cursor, rows, start, end, step):
    for index in range(start, end):
        cursor.begin_batch(index, rows[index])
        cursor.complete_batch()
    cursor.complete_optimizer_step(step, sync_gradients=True, optimizer_step_was_skipped=False)


def test_data_position_survives_interruption_without_skipping_rows():
    reference, rows = data_cursor()
    interrupted, _ = data_cursor()
    consume_update(reference, rows, 0, 4, 1)
    consume_update(interrupted, rows, 0, 4, 1)
    committed = json.loads(json.dumps(interrupted.snapshot()))
    # A later partial backward pass is not another committed position.
    interrupted.begin_batch(4, rows[4])
    interrupted.complete_batch()
    interrupted.fail_batch()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        interrupted.snapshot()
    resumed, _ = data_cursor()
    resumed.restore(committed)
    assert resumed.snapshot() == reference.snapshot()
    for cursor in (reference, resumed):
        consume_update(cursor, rows, 4, 8, 2)
        consume_update(cursor, rows, 8, 10, 3)
    assert resumed.snapshot() == reference.snapshot()
    assert resumed.snapshot()["sampler_state"]["consumed_row_sha256"] == rows
    assert resumed.snapshot()["data_position"]["completed_step"] == 3


@pytest.mark.parametrize("boundary", ["before_any_batch", "pending_batch", "partial_accumulation",
                                      "before_optimizer_update", "failed_batch"])
def test_prefetch_or_partial_gradients_cannot_commit_data_position(boundary):
    cursor, rows = data_cursor()
    if boundary in {"pending_batch", "failed_batch"}:
        cursor.begin_batch(0, rows[0])
    if boundary == "failed_batch":
        cursor.fail_batch()
    if boundary in {"partial_accumulation", "before_optimizer_update"}:
        for index in range(1 if boundary == "partial_accumulation" else 4):
            cursor.begin_batch(index, rows[index])
            cursor.complete_batch()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        cursor.snapshot()


def unbound_load_adapter(tmp_path):
    # Guard-only fixture: it cannot issue a signed admission, commit a load,
    # produce a handoff, or certify any actual model recovery.
    adapter = object.__new__(checkpoints.TrainingCheckpointAdapter)
    adapter._failed = False
    adapter._load_started = False
    adapter._load_committed = False
    adapter._load_components = set()
    adapter._resume_reservation = None
    adapter._approval_verifier = lambda request: False
    adapter._request = object()
    adapter._bind_trainer = lambda trainer: None
    return adapter


@pytest.mark.parametrize("method", ["train", "_load_from_checkpoint",
    "_load_optimizer_and_scheduler", "_load_scaler", "_load_rng_state"])
@pytest.mark.parametrize("selection", [True, False, "latest", "checkpoint-2"])
def test_framework_resume_selector_without_owner_reservation_never_calls_loader(tmp_path, method, selection):
    calls = []
    class Loader:
        def __init__(self): pass
        def train(self, checkpoint=None): calls.append(checkpoint)
        def _load_from_checkpoint(self, checkpoint, model=None): calls.append(checkpoint)
        def _load_optimizer_and_scheduler(self, checkpoint): calls.append(checkpoint)
        def _load_scaler(self, checkpoint): calls.append(checkpoint)
        def _load_rng_state(self, checkpoint): calls.append(checkpoint)

    adapter = unbound_load_adapter(tmp_path)
    trainer = adapter.trainer_type(Loader)()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_NOT_COMMITTED"):
        getattr(trainer, method)(selection)
    assert calls == []


@pytest.mark.parametrize("method", ["_load_optimizer_and_scheduler", "_load_scaler", "_load_rng_state"])
def test_resumed_component_cannot_silently_skip_checkpoint_by_passing_none(tmp_path, method):
    calls = []
    class Loader:
        def __init__(self): pass
        def _load_optimizer_and_scheduler(self, checkpoint): calls.append(checkpoint)
        def _load_scaler(self, checkpoint): calls.append(checkpoint)
        def _load_rng_state(self, checkpoint): calls.append(checkpoint)
    adapter = unbound_load_adapter(tmp_path)
    adapter._resume_reservation = {"load_root": tmp_path, "checkpoint_relative_path": "checkpoint-2"}
    trainer = adapter.trainer_type(Loader)()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_SCOPE_MISMATCH"):
        getattr(trainer, method)(None)
    assert calls == []


def test_revoked_permission_denies_before_current_admission_or_checkpoint_io(tmp_path):
    calls = []
    adapter = unbound_load_adapter(tmp_path)
    adapter._resume_reservation = {"load_root": tmp_path, "checkpoint_relative_path": "checkpoint-2"}
    adapter._client = SimpleNamespace(require_current_admission=lambda *a, **k: calls.append("admission"))
    adapter._prepare_load_metadata = lambda: calls.append("read-state")
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        adapter._load_component("model", tmp_path / "checkpoint-2", lambda: calls.append("load"))
    assert calls == []
    assert adapter._failed is True
    assert adapter._load_started is False


def test_uncommitted_loaded_attempt_cannot_execute_forward_backward(tmp_path):
    calls = []
    class Trainer:
        def __init__(self): pass
        def training_step(self, *args): calls.append("forward-backward")
    adapter = unbound_load_adapter(tmp_path)
    adapter._resume_reservation = {"load_root": tmp_path, "checkpoint_relative_path": "checkpoint-2"}
    trainer = adapter.trainer_type(Trainer)()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_NOT_COMMITTED"):
        trainer.training_step(None, {})
    assert calls == []


@pytest.mark.parametrize("failed,admitted", [(False, False), (True, True)])
def test_loaded_attempt_requires_current_recovery_phase_before_backward(tmp_path, failed, admitted):
    calls = []
    class Trainer:
        def __init__(self): pass
        def training_step(self, *args): calls.append("forward-backward")
    adapter = unbound_load_adapter(tmp_path)
    adapter._resume_reservation = {"unit_only": True}
    adapter._load_committed = True
    adapter._failed = failed
    adapter._recovery_phase_admitted = admitted
    trainer = adapter.trainer_type(Trainer)()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_NOT_COMMITTED"):
        trainer.training_step(None, {})
    assert calls == []


def post_load_guard_fixture(tmp_path):
    """Synthetic observations only; never loads weights or issues authority."""
    adapter = unbound_load_adapter(tmp_path)
    cursor, rows = data_cursor()
    consume_update(cursor, rows, 0, 4, 1)
    adapter._cursor = cursor
    checkpoint = tmp_path / "checkpoint-1"
    checkpoint.mkdir()
    (checkpoint / "lumenis_callback_state.json").write_text("{}", encoding="utf-8")
    adapter._resume_reservation = {"load_root": tmp_path,
        "checkpoint_relative_path": "checkpoint-1", "completed_step": 1}
    adapter._load_started = True
    adapter._load_components = {"model", "optimizer_scheduler", "scaler", "callback", "rng"}
    adapter._approval_verifier = lambda request: True
    adapter._trainer = SimpleNamespace(state=SimpleNamespace(global_step=1, stateful_callbacks={}))
    adapter._validate_runtime = lambda trainer: ({}, {})
    observed = {"completed_step": 1, "data_position": cursor.snapshot()["data_position"],
        "optimizer_state_sha256": "1" * 64, "scheduler_state_sha256": "2" * 64,
        "rng_state_sha256": "3" * 64, "adapter_or_model_state_sha256": "4" * 64,
        "framework_lock_sha256": "5" * 64}
    adapter._expected_restored_state = copy.deepcopy(observed)
    adapter._observe_state = lambda *args: copy.deepcopy(observed)
    adapter._operation_id = "unit-load-operation"
    calls = []
    adapter._client = SimpleNamespace(complete_load=lambda **kwargs: calls.append(kwargs))
    return adapter, observed, calls


@pytest.mark.parametrize("component", ["model", "optimizer_scheduler", "scaler", "callback", "rng"])
def test_incomplete_actual_load_never_commits(tmp_path, component):
    adapter, _, calls = post_load_guard_fixture(tmp_path)
    adapter._load_components.remove(component)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        adapter._finish_load(adapter._trainer)
    assert calls == [] and adapter._failed and not adapter._load_committed


@pytest.mark.parametrize("change", ["bool_step", "wrong_step", "callback", "optimizer", "scheduler",
    "rng", "model", "framework", "data_position", "permission"])
def test_actual_state_or_live_permission_mismatch_cannot_commit_load(tmp_path, change):
    adapter, observed, calls = post_load_guard_fixture(tmp_path)
    expected_error = "CHECKPOINT_RESTORED_STATE_MISMATCH"
    if change == "bool_step": adapter._trainer.state.global_step = True
    elif change == "wrong_step": adapter._trainer.state.global_step = 2
    elif change == "callback": adapter._trainer.state.stateful_callbacks = {"Missing": {}}
    elif change == "permission":
        adapter._approval_verifier = lambda request: False
        expected_error = "TRAINING_APPROVAL_REQUIRED"
    elif change == "data_position": observed["data_position"]["next_batch_index"] = 5
    else:
        field = {"optimizer": "optimizer_state_sha256", "scheduler": "scheduler_state_sha256",
            "rng": "rng_state_sha256", "model": "adapter_or_model_state_sha256",
            "framework": "framework_lock_sha256"}[change]
        observed[field] = "0" * 64
    with pytest.raises(training.TrainingBlocked, match=expected_error):
        adapter._finish_load(adapter._trainer)
    assert calls == [] and adapter._failed and not adapter._load_committed


def test_revocation_after_measurement_denies_before_owner_commit(tmp_path):
    adapter, observed, calls = post_load_guard_fixture(tmp_path)
    def measure(*args):
        adapter._approval_verifier = lambda request: False
        return copy.deepcopy(observed)
    adapter._observe_state = measure
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        adapter._finish_load(adapter._trainer)
    assert calls == [] and adapter._failed


def test_lost_complete_load_ack_is_terminal_and_never_reloads(tmp_path):
    adapter, _, calls = post_load_guard_fixture(tmp_path)
    def lose_ack(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("synthetic acknowledgement loss")
    adapter._client.complete_load = lose_ack
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_COMMIT_UNKNOWN"):
        adapter._finish_load(adapter._trainer)
    assert adapter._failed and not adapter._load_committed
    assert calls[0]["operation_id"] == adapter._operation_id
    with pytest.raises(training.TrainingBlocked):
        adapter._finish_load(adapter._trainer)
    assert len(calls) == 1


@pytest.mark.parametrize("failure,error", [(OSError, "CHECKPOINT_STORAGE_UNAVAILABLE"),
                                          (ValueError, "CHECKPOINT_LOAD_FAILED")])
def test_measurement_failure_terminates_attempt_without_owner_commit(tmp_path, failure, error):
    adapter, _, calls = post_load_guard_fixture(tmp_path)
    def unavailable(*args): raise failure("synthetic measurement failure")
    adapter._observe_state = unavailable
    with pytest.raises(training.TrainingBlocked, match=error):
        adapter._finish_load(adapter._trainer)
    assert calls == [] and adapter._failed


@pytest.mark.parametrize("change,error", [("missing", "CHECKPOINT_STATE_INCOMPLETE"),
    ("duplicate", "CHECKPOINT_STATE_INCOMPLETE"), ("value", "CHECKPOINT_RESTORED_STATE_MISMATCH")])
def test_warning_only_callback_restore_is_rejected(tmp_path, change, error):
    adapter, _, _ = post_load_guard_fixture(tmp_path)
    class Stateful:
        def state(self): return {"args": {}, "attributes": {"position": 1}}
    material = {"Stateful": Stateful().state()}
    (adapter._selected_checkpoint() / "lumenis_callback_state.json").write_bytes(
        checkpoints.canonical_bytes(material))
    adapter._trainer.state.stateful_callbacks = material
    adapter._trainer.control = object()
    objects = [] if change == "missing" else [Stateful()]
    if change == "duplicate": objects.append(Stateful())
    if change == "value": objects[0].state = lambda: {"args": {}, "attributes": {"position": 2}}
    adapter._trainer.callback_handler = SimpleNamespace(callbacks=objects)
    with pytest.raises(training.TrainingBlocked, match=error):
        adapter._validate_loaded_callbacks(adapter._trainer)
    assert adapter._failed


def resume_receipt_guard_fixture(tmp_path):
    """Unsigned unit material: no production verifier can accept these bytes."""
    adapter, observed, _ = post_load_guard_fixture(tmp_path)
    task_id = "trainrelay_5b9cbe28-d8e2-4d3c-a9a6-f7a5c9145a90"
    reservation = adapter._resume_reservation
    reservation.update({"schema_version": 1,
        "operation_id": "5b9cbe28-d8e2-4d3c-a9a6-f7a5c9145a90",
        "task_digest": hashlib.sha256(task_id.encode()).hexdigest(), "run_digest": "6" * 64,
        "checkpoint_ref": "ART-0123456789abcdef", "checkpoint_sha256": "7" * 64,
        "attempt_id": "6b9cbe28-d8e2-4d3c-a9a6-f7a5c9145a90", "worker_epoch": 2})
    adapter._fingerprints = {"unit": "8" * 64}
    adapter._pin = {"unit-only": True}
    receipt = {key: reservation[key] for key in ("schema_version", "operation_id", "task_digest",
        "run_digest", "checkpoint_ref", "checkpoint_sha256")}
    receipt.update({"restored_state": copy.deepcopy(observed), "task_step_ref": "unit-step",
                    "committed_at_utc": "2026-10-03T00:00:00Z", "receipt": {"unit": True}})
    payload = {key: reservation[key] for key in ("task_digest", "run_digest", "attempt_id",
        "worker_epoch", "checkpoint_ref", "checkpoint_sha256")}
    payload.update({"schema_version": 1, "task_id": task_id, "fingerprints": adapter._fingerprints,
        "load_operation_id": reservation["operation_id"],
        "resume_receipt_sha256": digest({k: v for k, v in receipt.items() if k != "receipt"}),
        "next_sequence": 8, "next_phase": "before_train", "admission_version": 3,
        "worker_binding_sha256": "9" * 64})
    receipt["phase_handoff"] = {"payload": payload, "unit-unsigned": True}
    return adapter, observed, receipt


@pytest.mark.parametrize("field,value", [("run_digest", "0" * 64), ("attempt_id", "wrong"),
    ("worker_epoch", True), ("fingerprints", {}), ("checkpoint_ref", "ART-fedcba9876543210"),
    ("checkpoint_sha256", "0" * 64), ("load_operation_id", "wrong"),
    ("resume_receipt_sha256", "0" * 64), ("next_sequence", True), ("next_sequence", 0),
    ("next_phase", "initial"), ("admission_version", 2), ("worker_binding_sha256", "unknown"),
    ("task_id", "trainrelay_6b9cbe28-d8e2-4d3c-a9a6-f7a5c9145a90")])
def test_resume_handoff_cannot_change_loaded_identity_or_replay_sequence(tmp_path, field, value):
    adapter, observed, receipt = resume_receipt_guard_fixture(tmp_path)
    receipt["phase_handoff"]["payload"][field] = value
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_SCOPE_MISMATCH"):
        adapter._accept_resume_receipt(receipt, observed)


@pytest.mark.parametrize("change", ["extra_receipt", "extra_handoff", "bool_schema", "state", "local_time"])
def test_resume_receipt_rejects_ambiguous_or_changed_metadata(tmp_path, change):
    adapter, observed, receipt = resume_receipt_guard_fixture(tmp_path)
    if change == "extra_receipt": receipt["permission"] = True
    elif change == "extra_handoff": receipt["phase_handoff"]["payload"]["permission"] = True
    elif change == "bool_schema": receipt["schema_version"] = True
    elif change == "state": receipt["restored_state"]["completed_step"] = True
    else: receipt["committed_at_utc"] = "2026-10-03T00:00:00"
    with pytest.raises(training.TrainingBlocked):
        adapter._accept_resume_receipt(receipt, observed)


def test_unsealed_verifier_result_cannot_authorize_resumed_training(tmp_path, monkeypatch):
    adapter, observed, receipt = resume_receipt_guard_fixture(tmp_path)
    monkeypatch.setattr(training_receipts, "VerifiedTrainingResumeReceipt", type("UnitSealed", (), {}), raising=False)
    calls = []
    def unsealed(envelope, *, expected_payload, pinned_public_key):
        calls.append((envelope, expected_payload, pinned_public_key))
        return {"verified": True}
    monkeypatch.setattr(training_receipts, "verify_training_resume_receipt", unsealed, raising=False)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_HASH_MISMATCH"):
        adapter._accept_resume_receipt(receipt, observed)
    assert calls[0][2] == adapter._pin
    assert calls[0][1] == {k: v for k, v in receipt.items() if k != "receipt"}


def test_recovery_phase_requires_live_permission_before_transport(tmp_path):
    adapter = unbound_load_adapter(tmp_path)
    adapter._load_committed = True
    adapter._loaded_handoff = object()
    adapter._recovery_phase_client = None
    calls = []
    with pytest.raises(training.TrainingBlocked, match="TRAINING_APPROVAL_REQUIRED"):
        adapter.recovered_phase_client(transport=lambda *args: calls.append(args))
    assert calls == [] and adapter._failed


@pytest.mark.parametrize("index,changed_row", [(1, False), (True, False), (-1, False), (0, True)])
def test_actual_batch_order_must_match_pinned_data(index, changed_row):
    cursor, rows = data_cursor()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_RESTORED_STATE_MISMATCH"):
        cursor.begin_batch(index, "f" * 64 if changed_row else rows[0])
    with pytest.raises(training.TrainingBlocked):
        cursor.begin_batch(0, rows[0])


@pytest.mark.parametrize("step,sync,skipped", [(True, True, False), (2, True, False),
                                            (1, False, False), (1, True, True)])
def test_unobserved_or_skipped_optimizer_update_is_not_a_checkpoint(step, sync, skipped):
    cursor, rows = data_cursor()
    for index in range(4):
        cursor.begin_batch(index, rows[index])
        cursor.complete_batch()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        cursor.complete_optimizer_step(step, sync_gradients=sync, optimizer_step_was_skipped=skipped)
    with pytest.raises(training.TrainingBlocked):
        cursor.snapshot()


@pytest.mark.parametrize("change", ["dataset", "order", "prefix", "step", "offset", "extra", "bool_epoch"])
def test_global_step_or_sampler_hash_alone_cannot_restore_position(change):
    cursor, rows = data_cursor()
    consume_update(cursor, rows, 0, 4, 1)
    state = cursor.snapshot()
    if change == "dataset": state["data_position"]["dataset_sha256"] = "e" * 64
    elif change == "order": state["sampler_state"]["data_order_sha256"] = "e" * 64
    elif change == "prefix":
        state["sampler_state"]["consumed_row_sha256"].reverse()
        state["data_position"]["sampler_state_sha256"] = digest(state["sampler_state"])
    elif change == "step": state["data_position"]["completed_step"] = 2
    elif change == "offset": state["data_position"]["gradient_accumulation_offset"] = 1
    elif change == "extra": state["permission"] = True
    elif change == "bool_epoch": state["data_position"]["epoch_index"] = False
    resumed, _ = data_cursor()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_RESTORED_STATE_MISMATCH"):
        resumed.restore(state)


def test_restored_position_cannot_be_reapplied_or_rewind_a_running_cursor():
    cursor, rows = data_cursor()
    consume_update(cursor, rows, 0, 4, 1)
    state = cursor.snapshot()
    restored, _ = data_cursor()
    restored.restore(state)
    state["sampler_state"]["consumed_row_sha256"].clear()
    assert restored.snapshot() == cursor.snapshot()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_OPERATION_CONFLICT"):
        restored.restore(cursor.snapshot())


def test_state_hash_preserves_values_types_shapes_and_mapping_identity():
    state = {"optimizer": {0: {"step": 2, "moment": np.array([1.0, 2.0], dtype=np.float32)}},
             "scheduler": {"last_epoch": 2, "learning_rate": 0.0002},
             "rng": ("MT19937", np.array([1, 3, 8], dtype=np.uint32), 3, 0, 0.0)}
    original = checkpoints.training_state_sha256(state)
    reordered = OrderedDict(reversed(list(state.items())))
    assert checkpoints.training_state_sha256(reordered) == original
    restored = copy.deepcopy(state)
    assert checkpoints.training_state_sha256(restored) == original
    restored["optimizer"][0]["moment"][0] = 1.5
    assert checkpoints.training_state_sha256(restored) != original
    for left, right in [(0, False), (1, 1.0), ([1], (1,)), ({1: 0}, {"1": 0}),
                        (np.array([1], dtype=np.float32), np.array([1], dtype=np.float64)),
                        (np.array([1, 2]), np.array([[1, 2]]))]:
        assert checkpoints.training_state_sha256(left) != checkpoints.training_state_sha256(right)


def test_state_hash_normalizes_numpy_strides_and_byte_order():
    array = np.arange(12, dtype=np.int32).reshape(3, 4).T
    expected = checkpoints.training_state_sha256(array)
    assert checkpoints.training_state_sha256(array.copy(order="C")) == expected
    assert checkpoints.training_state_sha256(array.astype(array.dtype.newbyteorder(">"))) == expected


@pytest.mark.parametrize("state", [float("nan"), float("inf"), {True: 1}, object(),
                                  np.array([float("nan")]), np.array([object()], dtype=object)])
def test_state_hash_rejects_unknown_or_nonfinite_state(state):
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        checkpoints.training_state_sha256(state)


def test_state_hash_rejects_cycles_without_serializing_arbitrary_objects():
    cycle = []
    cycle.append(cycle)
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        checkpoints.training_state_sha256(cycle)


def registered_checkpoint_inputs(tmp_path, monkeypatch, policy_material):
    from tests.test_owned_ai_training import _t4_inputs

    paths = _t4_inputs(tmp_path, monkeypatch)
    policy = checkpoints.CheckpointPolicy.validate(policy_material[0])
    manifest = json.loads(paths[1].read_text())
    manifest["checkpoint_recovery_policies"] = {
        "schema_version": 1, "policies": {policy.sha256: policy.document},
    }
    paths[1].write_text(json.dumps(manifest), encoding="utf-8")
    return paths, policy


def test_recovery_preflight_keeps_exact_extended_recipe_and_derivative(tmp_path, monkeypatch, policy_material):
    paths, policy = registered_checkpoint_inputs(tmp_path, monkeypatch, policy_material)
    model, manifest, train, heldout, output = paths
    result = training.run_owned_lora_training(model, train, heldout, output,
                                              manifest_path=manifest, recipe=policy.recipe)
    assert result["training_recipe"] == policy.recipe
    assert result["model_id"] == training.T4_MODEL_ID
    assert result["checkpoint_policy_sha256"] == policy.sha256
    assert result["execution_state"] == "PREFLIGHT_ONLY"
    assert not output.exists()
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_CONTRACT_NOT_BOUND"):
        training.run_owned_lora_training(model, train, heldout, output,
            manifest_path=manifest, recipe=policy.recipe, execute=True,
            approval_verifier=lambda request: True, checkpoint_adapter={"authorized": True})
    assert not output.exists()


def test_extended_recipe_must_be_registered_before_any_training_boundary(tmp_path, monkeypatch, policy_material):
    paths, policy = registered_checkpoint_inputs(tmp_path, monkeypatch, policy_material)
    model, manifest, train, heldout, output = paths
    material = json.loads(manifest.read_text())
    material["checkpoint_recovery_policies"]["policies"].clear()
    manifest.write_text(json.dumps(material), encoding="utf-8")
    calls = []
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_RECIPE_NOT_AUTHORIZED"):
        training.run_owned_lora_training(model, train, heldout, output,
            manifest_path=manifest, recipe=policy.recipe, execute=True,
            approval_verifier=lambda request: calls.append(request))
    assert not calls and not output.exists()


def test_save_adapter_without_typed_owner_performs_no_client_calls(tmp_path, monkeypatch, policy_material):
    paths, policy = registered_checkpoint_inputs(tmp_path, monkeypatch, policy_material)
    monkeypatch.delattr(training_receipts, "VerifiedTrainingCheckpointAdmission", raising=False)
    request = training.TrainingApprovalRequest(training.T4_MODEL_ID, training.T4_MODEL_REVISION,
        "a" * 64, "b" * 64, ("GLOBAL / ALL",), policy.recipe, "c" * 64, "cth")

    class NoClientAccess:
        def __getattr__(self, name):
            raise AssertionError("missing authority must fail before accessing the client")

    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_CONTRACT_NOT_BOUND"):
        checkpoints.TrainingCheckpointAdapter(request, {}, manifest_path=paths[1],
            client=NoClientAccess(), pinned_public_key={})
    assert not paths[-1].exists()


def config_fixture():
    config = {
        "per_device_train_batch_size": 1, "gradient_accumulation_steps": 4,
        "num_train_epochs": 1.0, "dataloader_num_workers": 0,
        "dataloader_drop_last": False, "remove_unused_columns": False,
        "save_only_model": False, "save_total_limit": None,
        "restore_callback_states_from_checkpoint": True, "ignore_data_skip": False,
        "push_to_hub": False, "hub_model_id": None, "hub_token": "<HUB_TOKEN>",
        "packing": False, "fp16": False, "bf16": False,
        "save_strategy": "steps", "eval_strategy": "no", "report_to": [],
        "output_dir": "/unit/attempt-a", "logging_dir": "/unit/logs-a", "save_steps": 2,
    }
    args = SimpleNamespace(to_dict=lambda: copy.deepcopy(config), hub_token=None, world_size=1, n_gpu=1)
    trainer = SimpleNamespace(args=args, is_deepspeed_enabled=False, is_fsdp_enabled=False, hp_search_backend=None)
    return trainer, config


def test_effective_trainer_config_normalizes_only_owner_paths_and_verified_absent_token():
    trainer, config = config_fixture()
    original = checkpoints.trainer_checkpoint_config(trainer)
    config["output_dir"], config["logging_dir"] = "/unit/attempt-b", "/unit/logs-b"
    assert checkpoints.trainer_checkpoint_config(trainer) == original
    config["learning_rate"] = 0.0003
    assert checkpoints.trainer_checkpoint_config(trainer) != original
    assert original["hub_token"] is None
    trainer.args.hub_token = "unit-token-never-transmitted"
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        checkpoints.trainer_checkpoint_config(trainer)


@pytest.mark.parametrize("key,value", [("dataloader_num_workers", 1), ("packing", True),
    ("save_only_model", True), ("remove_unused_columns", True), ("ignore_data_skip", True),
    ("save_total_limit", 1), ("per_device_train_batch_size", True), ("report_to", ["wandb"]),
    ("eval_strategy", "steps"), ("push_to_hub", True), ("fp16", True)])
def test_unsupported_effective_trainer_config_cannot_save(key, value):
    trainer, config = config_fixture()
    config[key] = value
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
        checkpoints.trainer_checkpoint_config(trainer)


@pytest.mark.parametrize("fails", [False, True])
def test_trainer_wrapper_counts_only_completed_forward_backward_calls(fails):
    cursor, rows = data_cursor()
    calls = []

    class SyntheticTrainer:
        def __init__(self): pass
        def training_step(self, model, inputs, num_items_in_batch=None):
            assert checkpoints._ROW_MARKER not in inputs
            calls.append(inputs)
            if fails:
                raise RuntimeError("synthetic backward interruption")
            return "synthetic-loss-marker"

    # This fixture validates wrapper call order only; it has no owner client,
    # model, permission or save capability and cannot certify training.
    adapter = SimpleNamespace(_cursor=cursor, _bind_trainer=lambda trainer: None)
    trainer_type = checkpoints.TrainingCheckpointAdapter.trainer_type(adapter, SyntheticTrainer)
    trainer = trainer_type()
    inputs = {checkpoints._ROW_MARKER: (0, rows[0]), "input_ids": [[1, 2, 3]]}
    if fails:
        with pytest.raises(RuntimeError, match="synthetic backward interruption"):
            trainer.training_step(None, inputs)
        with pytest.raises(training.TrainingBlocked):
            cursor.begin_batch(0, rows[0])
    else:
        assert trainer.training_step(None, inputs) == "synthetic-loss-marker"
        cursor.begin_batch(1, rows[1])
    assert len(calls) == 1
    assert checkpoints._ROW_MARKER in inputs
    with pytest.raises(training.TrainingBlocked, match="CHECKPOINT_STATE_INCOMPLETE"):
        cursor.snapshot()
