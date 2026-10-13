"""Isolated unit coverage for the existing owned-training final-byte path.

These tests use real temporary files and an in-process fake authorized transport.
They do not start a model, SSH session, database-backed training operation, or GPU run.
"""
from __future__ import annotations

import hashlib
import io
import json
import threading
from pathlib import Path, PurePosixPath

import pytest

from lumenis.system.ai_gateway import owned_training_runtime as runtime
from lumenis.system.ai_gateway.owned_training import (
    TrainingApprovalRequest,
    TrainingBlocked,
)

_REMOTE_ROOT = PurePosixPath("/approved/storage/output-12345678-1234-4234-8234-123456789abc")
_REMOTE_STORAGE = _REMOTE_ROOT.parent
_REMOTE_PEER = {"pid": 987, "created_at": 123.0, "source_root": "/approved/source"}


def _result(adapter: bytes, config: bytes) -> dict:
    return {
        "execution_state": "TRAINED_NOT_EVALUATED",
        "candidate_status": "NOT_EVALUATED",
        "adapter_sha256": hashlib.sha256(adapter).hexdigest(),
        "adapter_config_sha256": hashlib.sha256(config).hexdigest(),
        "status": "TRAINING_FINISHED_EVALUATION_REQUIRED",
    }


def _write_candidate(root: Path, result: dict, *, adapter=b"real-adapter-bytes", config=b'{"rank":8}\n'):
    root.mkdir(parents=True, exist_ok=True)
    (root / "training_status.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "adapter_model.safetensors").write_bytes(adapter)
    (root / "adapter_config.json").write_bytes(config)
    return runtime._describe_final_candidate(root, result)


class _FakeAuthorizedTransport:
    def __init__(self, source_root: Path, peer: dict, *, corrupt_path=None,
                 change_peer_after_first_file=False):
        self.source_root = source_root
        self.peer = dict(peer)
        self.corrupt_path = corrupt_path
        self.change_peer_after_first_file = change_peer_after_first_file
        self.fetch_calls = 0
        self.authorization_calls = 0
        self.after_file = None

    def require_live(self):
        return dict(self.peer)

    def fetch_checkpoint_bytes(self, *, remote_root, local_root, files, max_bytes, authorize):
        assert remote_root == str(_REMOTE_ROOT)
        assert max_bytes >= sum(item["size_bytes"] for item in files)
        self.fetch_calls += 1
        total = sum(item["size_bytes"] for item in files)
        authorize()
        self.authorization_calls += 1
        local_root.mkdir(parents=True, exist_ok=False)
        copied = []
        for item in files:
            authorize()
            self.authorization_calls += 1
            raw = (self.source_root / item["path"]).read_bytes()
            if item["path"] == self.corrupt_path:
                raw = b"different-bytes"
            target = local_root / item["path"]
            with target.open("xb") as stream:
                stream.write(raw)
            copied.append(dict(item))
            if len(copied) == 1 and self.change_peer_after_first_file:
                self.peer["pid"] += 1
            if self.after_file is not None:
                self.after_file(item, target)
        authorize()
        self.authorization_calls += 1
        return {
            "state": "PHYSICAL_CHECKPOINT_BYTES_VERIFIED",
            "source_root": str(local_root),
            "files": copied,
            "total_bytes": total,
            "remote_peer": dict(self.peer),
        }


def _invoke_fixture(tmp_path, monkeypatch, *, remote=True, corrupt_path=None,
                    revoke_authorization=False, revoke_after_authorizations=None,
                    change_peer_after_first_file=False, descriptor_case=None):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    train_path = tmp_path / "train.jsonl"
    heldout_path = tmp_path / "heldout.jsonl"
    manifest_path = tmp_path / "manifest.json"
    train_path.write_bytes(b'{"case":"train"}\n')
    heldout_path.write_bytes(b'{"case":"heldout"}\n')
    manifest_path.write_bytes(b'{"manifest":true}\n')
    output_dir = tmp_path / "final-output"
    request = TrainingApprovalRequest(
        model_id="test-model", model_revision="test-revision",
        train_sha256=hashlib.sha256(train_path.read_bytes()).hexdigest(),
        heldout_sha256=hashlib.sha256(heldout_path.read_bytes()).hexdigest(),
        scopes=("unit-test-only",), manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        domain_id="cth")
    invocation = {
        "model_snapshot_dir": str(model_dir),
        "train_jsonl_path": str(train_path),
        "heldout_jsonl_path": str(heldout_path),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path),
        "resume_request": None,
        "stop_after_checkpoint_step": None,
    }
    adapter, config = b"real-adapter-bytes", b'{"rank":8}\n'
    result = _result(adapter, config)
    if remote:
        source_root = tmp_path / "remote-worker-output"
        descriptor = _write_candidate(source_root, result, adapter=adapter, config=config)
        descriptor["output_root"] = str(_REMOTE_ROOT)
        fake_transport = _FakeAuthorizedTransport(source_root, _REMOTE_PEER,
            corrupt_path=corrupt_path, change_peer_after_first_file=change_peer_after_first_file)
        remote_paths = {
            "model_snapshot_dir": "/approved/source/model",
            "train_jsonl_path": "/approved/source/train.jsonl",
            "heldout_jsonl_path": "/approved/source/heldout.jsonl",
            "manifest_path": "/approved/source/config/ai-owned-foundation.json",
            "output_dir": str(_REMOTE_ROOT),
        }
        remote_storage_root = _REMOTE_STORAGE
        peer = dict(_REMOTE_PEER)
    else:
        source_root = output_dir
        descriptor = None
        fake_transport = None
        remote_paths = None
        remote_storage_root = None
        peer = {"pid": 987, "created_at": 123.0}

    if descriptor_case == "wrong_root":
        descriptor["output_root"] = str(_REMOTE_STORAGE / "output-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    elif descriptor_case == "wrong_path":
        descriptor["files"][1]["path"] = "other.safetensors"
    elif descriptor_case == "wrong_role":
        descriptor["files"][1]["role"] = "checkpoint"
    elif descriptor_case == "wrong_hash":
        descriptor["files"][1]["sha256"] = "0" * 64
    elif descriptor_case == "oversized_metadata":
        descriptor["files"][2]["size_bytes"] = 1024 * 1024 + 1
    elif descriptor_case == "wrong_total":
        descriptor["total_bytes"] += 1
    elif descriptor_case == "over_client_limit":
        descriptor["files"][1]["size_bytes"] = 1024 * 1024
        descriptor["total_bytes"] = sum(item["size_bytes"] for item in descriptor["files"])
    elif descriptor_case == "missing":
        descriptor = None

    client = object.__new__(runtime.OwnedTrainingCheckpointClient)
    client.request = request
    client.context = {"test_context": True}
    client.task_id = "task-test"
    client.worker = None
    client._manifest_path = manifest_path
    client._max_bytes = 1024 * 1024
    client._remote_storage_root = remote_storage_root
    client._fingerprints = {}
    client._pin = {"test": "pin"}
    authorization_state = {"calls": 0}
    def authorize_storage(**kwargs):
        authorization_state["calls"] += 1
        if (revoke_authorization or revoke_after_authorizations is not None
                and authorization_state["calls"] >= revoke_after_authorizations):
            raise TrainingBlocked("CHECKPOINT_PERMISSION_REVOKED")
    client._authorize_storage = authorize_storage
    client._fresh = lambda: None
    client.initial_phase_context = lambda: {"prepared": True}

    fence = object.__new__(runtime.TrainingProcessFence)
    fence._mutex = threading.RLock()
    fence._source_root = tmp_path
    fence._source_pins = {"source": "pinned"}
    fence._remote_transport = fake_transport
    fence._remote_peer = peer if remote else None
    fence._peer = {"pid": 986, "created_at": 122.0}
    fence._channel = (io.BytesIO(), io.BytesIO())
    fence._load_observation = None
    fence._observing_load = False
    fence.stop_calls = 0
    fence._worker = None
    fence._invocation_active = False
    fence._managed_invoked = False
    fence.require_live = lambda expected_binding=None: None
    fence.stop_and_reap = lambda: setattr(fence, "stop_calls", fence.stop_calls + 1)
    fence._receive_managed = lambda deadline: {
        "kind": "result", "sequence": 1,
        "value": ({**result, **({runtime._FINAL_CANDIDATE_INTERNAL_FIELD: descriptor}
            if descriptor is not None else {})}),
    }
    fence._verify_remote_training_inputs = lambda *args, **kwargs: remote_paths
    if remote:
        # The inventory root is checked against the exact owner-created output
        # path; all other SSH behavior remains behind this fake transport.
        monkeypatch.setattr(runtime, "_write_pipe", lambda stream, body: None)
    else:
        def write_and_materialize(stream, body):
            monkeypatch.setattr(runtime, "_write_pipe", lambda _stream, _body: None)
            _write_candidate(output_dir, result, adapter=adapter, config=config)
            nonlocal descriptor
            descriptor = runtime._describe_final_candidate(output_dir, result)
            fence._receive_managed = lambda deadline: {
                "kind": "result", "sequence": 1,
                "value": {**result, runtime._FINAL_CANDIDATE_INTERNAL_FIELD: descriptor},
            }
        monkeypatch.setattr(runtime, "_write_pipe", write_and_materialize)

    monkeypatch.setattr(runtime, "training_worker_source_pins", lambda root: {"source": "pinned"})
    from lumenis.system.ai_gateway import owned_training_phases
    monkeypatch.setattr(owned_training_phases, "TrainingPublicContext", lambda *args, **kwargs: None)
    monkeypatch.setattr(fence, "_source_test_only", True, raising=False)
    client.worker = fence
    if remote:
        fence._verify_remote_training_inputs = lambda *args, **kwargs: remote_paths
    return fence, client, invocation, remote_paths, fake_transport, descriptor


def _call(fence, client, invocation, remote_paths):
    return fence._invoke_training_bound(client=client, phase_transport=lambda *args: {},
        invocation=invocation, timeout_seconds=10, remote_input_paths=(
            {key: value for key, value in remote_paths.items() if key != "manifest_path" and key != "output_dir"}
            if remote_paths is not None else None))


def test_remote_final_candidate_copies_real_bytes_and_returns_exact_unpromoted_receipt(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(tmp_path, monkeypatch)

    result = _call(fence, client, invocation, remote_paths)

    receipt = result["final_candidate_materialization"]
    assert receipt["state"] == "PHYSICAL_FINAL_CANDIDATE_BYTES_VERIFIED"
    assert receipt["promotion_state"] == "NOT_PROMOTED"
    assert receipt["evaluation_state"] == "NOT_EVALUATED"
    assert receipt["local_directory"] == str(invocation["output_dir"])
    assert [item["path"] for item in receipt["files"]] == [name for name, _ in runtime._FINAL_CANDIDATE_FILES]
    assert all((Path(receipt["local_directory"]) / item["path"]).read_bytes()
        == (transport.source_root / item["path"]).read_bytes() for item in receipt["files"])
    assert all(hashlib.sha256((Path(receipt["local_directory"]) / item["path"]).read_bytes()).hexdigest()
        == item["sha256"] for item in receipt["files"])
    assert transport.fetch_calls == 1
    assert transport.authorization_calls >= 2
    assert runtime._FINAL_CANDIDATE_INTERNAL_FIELD not in result
    assert fence.stop_calls == 1


def test_local_final_candidate_is_independently_verified_without_refetch(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, _, _ = _invoke_fixture(
        tmp_path, monkeypatch, remote=False)

    result = _call(fence, client, invocation, remote_paths)

    assert result["final_candidate_materialization"]["state"] == "PHYSICAL_FINAL_CANDIDATE_BYTES_VERIFIED"
    assert result["execution_state"] == "TRAINED_NOT_EVALUATED"
    assert fence.stop_calls == 1


@pytest.mark.parametrize("case", [
    "wrong_root", "wrong_path", "wrong_role", "wrong_hash", "oversized_metadata", "wrong_total",
    "over_client_limit", "missing",
])
def test_invalid_inventory_is_rejected_before_any_remote_transfer(tmp_path, monkeypatch, case):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch, descriptor_case=case)

    with pytest.raises(TrainingBlocked):
        _call(fence, client, invocation, remote_paths)

    assert transport.fetch_calls == 0
    assert fence.stop_calls == 1


def test_revoked_storage_authorization_prevents_transfer_and_reaps_worker(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch, revoke_authorization=True)

    with pytest.raises(TrainingBlocked, match="CHECKPOINT_PERMISSION_REVOKED"):
        _call(fence, client, invocation, remote_paths)

    assert transport.fetch_calls == 0
    assert fence.stop_calls == 1


def test_storage_authorization_revoked_mid_transfer_keeps_partial_directory(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch, revoke_after_authorizations=4)

    with pytest.raises(TrainingBlocked, match="CHECKPOINT_PERMISSION_REVOKED"):
        _call(fence, client, invocation, remote_paths)

    partial = Path(invocation["output_dir"])
    assert transport.fetch_calls == 1
    assert (partial / "training_status.json").is_file()
    assert not (partial / "adapter_model.safetensors").exists()
    assert fence.stop_calls == 1


def test_remote_peer_revocation_mid_transfer_keeps_partial_directory(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch, change_peer_after_first_file=True)

    with pytest.raises(TrainingBlocked, match="CHECKPOINT_WORKER_FENCE_LOST"):
        _call(fence, client, invocation, remote_paths)

    partial = Path(invocation["output_dir"])
    assert transport.fetch_calls == 1
    assert (partial / "training_status.json").is_file()
    assert not (partial / "adapter_model.safetensors").exists()
    assert fence.stop_calls == 1


def test_source_pin_change_mid_transfer_keeps_partial_directory(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch)
    changed = {"value": False}
    transport.after_file = lambda item, target: changed.__setitem__("value", True)
    monkeypatch.setattr(runtime, "training_worker_source_pins",
        lambda root: {"source": "changed" if changed["value"] else "pinned"})

    with pytest.raises(TrainingBlocked, match="TRAINING_WORKER_SOURCE_MISMATCH"):
        _call(fence, client, invocation, remote_paths)

    partial = Path(invocation["output_dir"])
    assert transport.fetch_calls == 1
    assert (partial / "training_status.json").is_file()
    assert not (partial / "adapter_model.safetensors").exists()
    assert fence.stop_calls == 1


def test_copied_status_mismatch_fails_closed_and_leaves_partial_bytes_in_place(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch, corrupt_path="training_status.json")

    with pytest.raises(TrainingBlocked):
        _call(fence, client, invocation, remote_paths)

    assert transport.fetch_calls == 1
    assert (Path(invocation["output_dir"]) / "training_status.json").is_file()
    assert fence.stop_calls == 1


def test_worker_side_inventory_requires_status_and_adapter_hashes_to_match_result(tmp_path):
    adapter, config = b"adapter", b'{"rank":4}\n'
    result = _result(adapter, config)
    root = tmp_path / "bad-status"
    root.mkdir()
    (root / "training_status.json").write_text("{}", encoding="utf-8")
    (root / "adapter_model.safetensors").write_bytes(adapter)
    (root / "adapter_config.json").write_bytes(config)

    with pytest.raises(TrainingBlocked, match="FINAL_CANDIDATE_STATUS_MISMATCH"):
        runtime._describe_final_candidate(root, result)


def test_output_destination_guard_rejects_protected_path_before_transfer(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(tmp_path, monkeypatch)
    invocation["output_dir"] = str(Path(invocation["model_snapshot_dir"]) / "candidate")

    with pytest.raises(TrainingBlocked, match="FINAL_CANDIDATE_OUTPUT_PATH_INVALID"):
        _call(fence, client, invocation, remote_paths)

    assert transport.fetch_calls == 0
    assert fence.stop_calls == 1


def test_managed_invocation_reaps_worker_in_its_finally_on_missing_descriptor(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(
        tmp_path, monkeypatch, descriptor_case="missing")
    fence._worker = {"pid": 100, "created_at": 1.0}

    with pytest.raises(TrainingBlocked):
        fence.invoke_owned_training(client=client, phase_transport=lambda *args: {},
            invocation=invocation, timeout_seconds=10,
            remote_input_paths={key: value for key, value in remote_paths.items()
                if key not in {"manifest_path", "output_dir"}})

    assert transport.fetch_calls == 0
    assert fence.stop_calls >= 1


@pytest.mark.parametrize("replacement", [True, 1.0])
def test_status_cannot_replace_an_integer_step_with_a_different_json_type(tmp_path, replacement):
    adapter, config = b"adapter", b'{"rank":4}\n'
    result = {**_result(adapter, config), "trained_steps": 1}
    root = tmp_path / "typed-status"
    _write_candidate(root, result, adapter=adapter, config=config)
    (root / "training_status.json").write_text(
        json.dumps({**result, "trained_steps": replacement}), encoding="utf-8")

    with pytest.raises(TrainingBlocked, match="FINAL_CANDIDATE_STATUS_MISMATCH"):
        runtime._describe_final_candidate(root, result)


def test_status_reader_rejects_replaced_opened_identity_before_read(tmp_path, monkeypatch):
    path = tmp_path / "training_status.json"
    other = tmp_path / "same-content-other-file.json"
    raw = b'{"execution_state":"TRAINED_NOT_EVALUATED"}'
    path.write_bytes(raw)
    other.write_bytes(raw)
    original_open = Path.open
    opens = {"count": 0}

    def replace_second_open(self, *args, **kwargs):
        if self == path:
            opens["count"] += 1
            if opens["count"] == 2:
                return original_open(other, *args, **kwargs)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_second_open)
    with pytest.raises(TrainingBlocked, match="FINAL_CANDIDATE_BYTES_NOT_VERIFIED"):
        runtime._read_final_candidate_status(path, len(raw), hashlib.sha256(raw).hexdigest())
    assert opens["count"] == 2


@pytest.mark.parametrize("result", [None, [], {},
    {"execution_state": [], "candidate_status": "NOT_EVALUATED"},
    {"execution_state": {}, "candidate_status": "NOT_EVALUATED"},
    {"execution_state": "PASS", "candidate_status": "NOT_EVALUATED"},
    {"execution_state": "TRAINED_NOT_EVALUATED", "candidate_status": "PROMOTED"},
    {"execution_state": "CHECKPOINT_SAVED_TRAINING_INTERRUPTED"},
])
def test_untyped_or_unexpected_worker_result_is_rejected_and_worker_reaped(tmp_path, monkeypatch, result):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(tmp_path, monkeypatch)
    fence._receive_managed = lambda deadline: {"kind": "result", "sequence": 1, "value": result}

    with pytest.raises(TrainingBlocked, match="TRAINING_RESULT_INVALID"):
        _call(fence, client, invocation, remote_paths)

    assert transport.fetch_calls == 0
    assert fence.stop_calls == 1


@pytest.mark.parametrize("field", [runtime._FINAL_CANDIDATE_INTERNAL_FIELD, "final_candidate_materialization"])
def test_interrupt_cannot_carry_a_final_candidate_inventory_or_receipt(tmp_path, monkeypatch, field):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(tmp_path, monkeypatch)
    result = {"execution_state": "CHECKPOINT_SAVED_TRAINING_INTERRUPTED",
        "candidate_status": "NOT_EVALUATED", field: {}}
    fence._receive_managed = lambda deadline: {"kind": "result", "sequence": 1, "value": result}

    with pytest.raises(TrainingBlocked, match="FINAL_CANDIDATE_INVENTORY_INVALID"):
        _call(fence, client, invocation, remote_paths)

    assert transport.fetch_calls == 0
    assert fence.stop_calls == 1


def test_real_checkpoint_interrupt_result_is_retained_without_final_transfer(tmp_path, monkeypatch):
    fence, client, invocation, remote_paths, transport, _ = _invoke_fixture(tmp_path, monkeypatch)
    result = {"execution_state": "CHECKPOINT_SAVED_TRAINING_INTERRUPTED",
        "candidate_status": "NOT_EVALUATED", "worker_stop_state": "OWNER_STOP_AND_REAP_REQUIRED"}
    fence._receive_managed = lambda deadline: {"kind": "result", "sequence": 1, "value": result}

    assert _call(fence, client, invocation, remote_paths) == result
    assert transport.fetch_calls == 0
    assert fence.stop_calls == 1
