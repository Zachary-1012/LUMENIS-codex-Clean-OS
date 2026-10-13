"""Actual disposable OS child/lock checks; never a model training receipt."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil
import pytest

from lumenis.system.ai_gateway.owned_training import TrainingBlocked
from lumenis.system.ai_gateway.owned_training_runtime import TrainingProcessFence


def test_real_os_lock_prevents_competing_owner_and_survives_child_stop(tmp_path):
    lock = (tmp_path / "owner.lock").resolve()
    first = TrainingProcessFence(lock)
    try:
        with pytest.raises(TrainingBlocked, match="CHECKPOINT_WORKER_FENCE_LOST"):
            TrainingProcessFence(lock)
        worker = first.start([sys.executable, "-c", "import time; time.sleep(60)"],
                             cwd=tmp_path.resolve(), log_path=(tmp_path / "worker.log").resolve())
        assert worker["pid"] != os.getpid()
        assert first.require_live(worker).create_time() == worker["created_at"]
        stopped = first.stop_and_reap()
        assert stopped["returncode"] is not None
        assert not psutil.pid_exists(worker["pid"])
        altered = first.stop_and_reap()
        altered["worker_binding"]["pid"] = 0
        assert first.stop_and_reap()["worker_binding"] == worker
        with pytest.raises(TrainingBlocked):
            first.require_live(worker)
        with pytest.raises(TrainingBlocked):
            TrainingProcessFence(lock)
    finally:
        first.close()
    second = TrainingProcessFence(lock)
    second.close()


def test_actual_descendant_exit_is_confirmed_before_lock_release(tmp_path):
    marker = tmp_path / "child.json"
    script = ("import subprocess,sys,time,json,pathlib; "
              "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
              "pathlib.Path(sys.argv[1]).write_text(json.dumps({'pid':p.pid})); time.sleep(60)")
    fence = TrainingProcessFence((tmp_path / "tree.lock").resolve())
    try:
        worker = fence.start([sys.executable, "-c", script, str(marker)], cwd=tmp_path.resolve(),
                             log_path=(tmp_path / "tree.log").resolve())
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        child_pid = json.loads(marker.read_text())["pid"]
        fence.require_live(worker)
        # Windows venv python.exe is a redirector and adds an actual intermediate
        # process. Require retained ancestry, not an invented direct parent.
        assert worker["pid"] in {process.pid for process in psutil.Process(child_pid).parents()}
        stopped = fence.stop_and_reap()
        assert child_pid in {row["pid"] for row in stopped["descendants"]}
        assert not psutil.pid_exists(worker["pid"]) and not psutil.pid_exists(child_pid)
    finally:
        fence.close()


def test_current_worker_binding_is_required_and_no_arbitrary_pid_attach(tmp_path):
    fence = TrainingProcessFence((tmp_path / "binding.lock").resolve())
    try:
        worker = fence.start([sys.executable, "-c", "import time; time.sleep(60)"],
                             cwd=tmp_path.resolve(), log_path=(tmp_path / "binding.log").resolve())
        with pytest.raises(TrainingBlocked):
            fence.require_live({**worker, "created_at": worker["created_at"] + 1})
        with pytest.raises(TrainingBlocked):
            fence.start([sys.executable, "-c", "pass"], cwd=tmp_path.resolve(),
                        log_path=(tmp_path / "second.log").resolve())
    finally:
        fence.close()


def test_physical_writer_is_paused_during_owner_copy_then_resumed(tmp_path):
    heartbeat = tmp_path / "heartbeat.txt"
    script = ("import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
              "exec('while True:\\n p.write_text(str(time.time_ns()))\\n time.sleep(0.01)')")
    fence = TrainingProcessFence((tmp_path / "pause.lock").resolve())
    try:
        worker = fence.start([sys.executable, "-c", script, str(heartbeat)], cwd=tmp_path.resolve(),
                             log_path=(tmp_path / "pause.log").resolve())
        deadline = time.monotonic() + 5
        while not heartbeat.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert heartbeat.exists()
        with fence.exclude_writer(worker):
            before = heartbeat.read_text()
            time.sleep(0.12)
            assert heartbeat.read_text() == before
        deadline = time.monotonic() + 3
        while heartbeat.read_text() == before and time.monotonic() < deadline:
            time.sleep(0.02)
        assert heartbeat.read_text() != before
    finally:
        fence.close()


def test_source_pinned_managed_worker_has_actual_private_peer_and_stop_replacement(tmp_path):
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins
    root = Path(__file__).resolve().parents[1]
    pins = training_worker_source_pins(root)
    worker = TrainingProcessFence((tmp_path / "managed.lock").resolve())
    try:
        started = worker.start_managed_training(python_executable=Path(sys.executable), cwd=root,
            log_path=(tmp_path / "managed.log").resolve(), source_pins=pins)
        assert started["model_loaded"] is False
        assert started["source_pins"] == pins
        peer = psutil.Process(started["framework_worker"]["pid"])
        assert peer.create_time() == started["framework_worker"]["created_at"]
        assert started["worker_binding"]["pid"] in {peer.pid, *(p.pid for p in peer.parents())}
        with pytest.raises(TrainingBlocked, match="CHECKPOINT_ACTUAL_LOAD_NOT_OBSERVED"):
            worker.require_completed_training_load(operation_id="caller", restored_state={})
        with pytest.raises(TrainingBlocked, match="TRAINING_WORKER_DEADLINE_REACHED"):
            worker._receive_managed(time.monotonic() + 0.02)
        stopped = worker.stop_and_reap()
        assert not psutil.pid_exists(peer.pid)
        replaced = worker.start_managed_training(python_executable=Path(sys.executable), cwd=root,
            log_path=(tmp_path / "managed-replaced.log").resolve(), source_pins=pins, replace=True)
        assert replaced["framework_worker"] != started["framework_worker"]
        assert worker.require_previous_worker_stopped(started["worker_binding"]) == stopped
        assert replaced["model_loaded"] is False
    finally:
        worker.close()


def test_changed_managed_source_pin_cannot_spawn_worker(tmp_path):
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins
    root = Path(__file__).resolve().parents[1]
    pins = training_worker_source_pins(root)
    pins[next(iter(pins))] = "0" * 64
    worker = TrainingProcessFence((tmp_path / "wrong-pin.lock").resolve())
    try:
        with pytest.raises(TrainingBlocked, match="TRAINING_WORKER_SOURCE_MISMATCH"):
            worker.start_managed_training(python_executable=Path(sys.executable), cwd=root,
                log_path=(tmp_path / "not-created.log").resolve(), source_pins=pins)
        assert worker._process is None and not (tmp_path / "not-created.log").exists()
    finally:
        worker.close()


def test_authenticated_remote_transport_binds_remote_peer_and_replaces_under_retained_lock(tmp_path):
    """Protocol mechanics only; synthetic peer IDs are not remote OS evidence."""
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins

    class Transport:
        def __init__(self):
            from types import SimpleNamespace
            self.generation = 0
            self.channel = None
            self.peer = None
            self.pause_states = []
            self.endpoint = SimpleNamespace(source_root="/remote/source")

        def start_stdio(self):
            self.generation += 1
            pid = 900000 + self.generation
            self.created = 1000.0 + self.generation
            # The synthetic channel emits a remote-ready frame; its fabricated
            # peer identity deliberately differs from this local subprocess.
            hello = {"kind": "owned_training_remote_worker_ready", "pid": pid,
                "created_at": self.created, "source_pins": self.source_pins,
                "process_group_id": pid, "session_id": pid, "proc_start_ticks": 42 + self.generation}
            self.channel = subprocess.Popen([sys.executable, "-u", "-c",
                "import sys; print(sys.argv[1], flush=True); sys.stdin.buffer.read()",
                json.dumps(hello)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=0)
            self.pending_hello = hello
            return self.channel

        def admit_peer(self, hello):
            assert hello == self.pending_hello
            self.peer = {"pid": hello["pid"], "created_at": hello["created_at"],
                "parent_pid": 1, "process_group": hello["pid"], "session_id": hello["pid"],
                "proc_start_ticks": hello["proc_start_ticks"], "boot_id": "test-only",
                "source_root": "/remote/source", "source_pins": self.source_pins, "state": "LIVE"}
            return dict(self.peer)

        def require_live(self):
            assert self.channel.poll() is None
            return dict(self.peer)

        def signal_writer_group(self, *, paused):
            self.pause_states.append(paused)
            return {"state": "REMOTE_WRITERS_PAUSED" if paused else "REMOTE_WRITERS_RESUMED",
                "peer": dict(self.peer)}

        def fetch_checkpoint_bytes(self, **_kwargs):
            raise AssertionError("This protocol test does not transfer checkpoint bytes")

        def verify_training_inputs(self, paths, expected_files):
            return {"state": "PHYSICAL_TRAINING_INPUTS_VERIFIED", "paths": paths,
                "files": expected_files, "remote_peer": dict(self.peer)}

        def stop_remote_and_reap(self):
            return {"state": "REMOTE_GROUP_STOPPED", "pid": self.peer["pid"],
                "process_group": self.peer["pid"], "live_members": 0}

    root = Path(__file__).resolve().parents[1]
    transport = Transport()
    transport.source_pins = training_worker_source_pins(root)
    fence = TrainingProcessFence((tmp_path / "remote.lock").resolve())
    try:
        first = fence.start_managed_training(python_executable=Path(sys.executable), cwd=root,
            log_path=(tmp_path / "remote.log").resolve(), source_pins=transport.source_pins,
            remote_transport=transport)
        assert first["worker_binding"] == {"pid": 900001, "created_at": 1001.0,
            "lock_sha256": fence._lock_sha256}
        assert first["remote_peer"]["process_group"] == first["worker_binding"]["pid"]
        assert fence.require_live(first["worker_binding"]) is None
        with fence.exclude_writer(first["worker_binding"]):
            assert transport.pause_states == [True]
        assert transport.pause_states == [True, False]
        stopped = fence.stop_and_reap()
        second = fence.start_managed_training(python_executable=Path(sys.executable), cwd=root,
            log_path=(tmp_path / "remote-replaced.log").resolve(), source_pins=transport.source_pins,
            replace=True)
        assert second["worker_binding"]["pid"] == 900002
        assert second["worker_binding"]["lock_sha256"] == first["worker_binding"]["lock_sha256"]
        assert fence.require_previous_worker_stopped(first["worker_binding"]) == stopped

        import hashlib
        from types import SimpleNamespace
        from pathlib import PurePosixPath
        model = tmp_path / "model"
        model.mkdir()
        pins = {}
        for index in range(11):
            name = f"model-{index:02d}.bin"
            payload = f"approved-model-file-{index}".encode()
            (model / name).write_bytes(payload)
            pins[name] = {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        train = tmp_path / "train.jsonl"
        heldout = tmp_path / "heldout.jsonl"
        train.write_bytes(b"approved train bytes\n")
        heldout.write_bytes(b"approved heldout bytes\n")
        manifest = tmp_path / "ai-owned-foundation.json"
        from lumenis.system.ai_gateway.owned_training import BLACKWELL_RECIPE, T4_RECIPE
        manifest_data = {"training_variants": {T4_RECIPE: {"model_id": "approved-model",
            "revision": "approved-revision", "files": pins}}}
        manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
        manifest_bytes = manifest.read_bytes()
        public = SimpleNamespace(model_id="approved-model", model_revision="approved-revision",
            train_sha256=hashlib.sha256(train.read_bytes()).hexdigest(),
            heldout_sha256=hashlib.sha256(heldout.read_bytes()).hexdigest(),
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
        client = SimpleNamespace(_manifest_path=manifest,
            policy=SimpleNamespace(document={"base_recipe": BLACKWELL_RECIPE}), request=public)
        invocation = {"model_snapshot_dir": str(model), "train_jsonl_path": str(train),
            "heldout_jsonl_path": str(heldout), "manifest_path": str(manifest),
            "output_dir": str(tmp_path / "unused-output"), "resume_request": None,
            "stop_after_checkpoint_step": 1}
        remote_paths = fence._verify_remote_training_inputs(client, invocation, {
            "model_snapshot_dir": "/remote/source/cache/model",
            "train_jsonl_path": "/remote/source/data/train.jsonl",
            "heldout_jsonl_path": "/remote/source/data/heldout.jsonl"}, PurePosixPath("/remote/storage"))
        assert remote_paths["manifest_path"] == "/remote/source/config/ai-owned-foundation.json"
        assert remote_paths["output_dir"].startswith("/remote/storage/output-")
        assert len(transport.peer["source_pins"]) == 5
        with pytest.raises(TrainingBlocked, match="REMOTE_TRAINING_INPUT_MAPPING_REQUIRED"):
            fence._verify_remote_training_inputs(client, invocation, {
                "model_snapshot_dir": "/remote/source/cache/model",
                "train_jsonl_path": "/remote/source/data/../train.jsonl",
                "heldout_jsonl_path": "/remote/source/data/heldout.jsonl"}, PurePosixPath("/remote/storage"))
    finally:
        fence.close()


def test_remote_pure_posix_root_uses_existing_bounded_path_wire_tag():
    from pathlib import Path, PurePosixPath
    from lumenis.system.ai_gateway.owned_training_runtime import _pipe_encode, _pipe_decode
    encoded = _pipe_encode(PurePosixPath("/srv/lumenis/checkpoints/op-1"))
    assert encoded == {"__owned_training_wire__": "path", "value": "/srv/lumenis/checkpoints/op-1"}
    decoded = _pipe_decode(encoded, None)
    expected_type = type(Path()) if Path("/").is_absolute() else PurePosixPath
    assert type(decoded) is expected_type and str(decoded) == "/srv/lumenis/checkpoints/op-1"


def test_unbound_invocation_reaps_real_managed_worker_without_waiting(tmp_path):
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins
    root = Path(__file__).resolve().parents[1]
    worker = TrainingProcessFence((tmp_path / "no-binding.lock").resolve())
    try:
        ready = worker.start_managed_training(python_executable=Path(sys.executable), cwd=root,
            log_path=(tmp_path / "no-binding.log").resolve(), source_pins=training_worker_source_pins(root))
        with pytest.raises(TrainingBlocked, match="TRAINING_PHASE_TRANSPORT_NOT_BOUND"):
            worker.invoke_owned_training(client=object(), phase_transport=None, invocation={}, timeout_seconds=1)
        assert not psutil.pid_exists(ready["framework_worker"]["pid"])
        assert worker._process.returncode is not None
        with pytest.raises(TrainingBlocked, match="CHECKPOINT_OPERATION_CONFLICT"):
            worker.invoke_owned_training(client=object(), phase_transport=None, invocation={}, timeout_seconds=1)
    finally:
        worker.close()


@pytest.mark.parametrize("domain,scope,product", [("cth", "SUB-1", "CTH"), ("bmp", "BRAND-1", "ZBMP"), ("cth", "GLOBAL / ALL", "CTH")])
def test_public_worker_context_matches_canonical_hashes_without_manufacturing_identity(domain, scope, product):
    from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
    from lumenis.system.ai_gateway.owned_training_phases import TrainingPublicContext, TrainingPhaseClient
    from lumenis.system.security.permission import owned_training_phase_fingerprints
    request = TrainingApprovalRequest("model", "revision", "a" * 64, "b" * 64, (scope,),
        recipe="recipe", manifest_sha256="c" * 64, domain_id=domain)
    descriptor = {"domain_id": domain, "product_id": product, "global_scope": scope == "GLOBAL / ALL",
        "subject_id": scope if domain == "cth" and scope != "GLOBAL / ALL" else None,
        "brand_focus_id": scope if domain == "bmp" else None}
    context = {"scope_descriptors": {scope: descriptor}}
    fingerprints = owned_training_phase_fingerprints(request, context=context, domain_id=domain, actor_id=1)
    public = TrainingPublicContext(request, context, fingerprints)
    assert public.fingerprints_for(request, context) == fingerprints
    fingerprints["scope_sha256"] = "d" * 64
    with pytest.raises(TrainingBlocked, match="TRAINING_PHASE_REQUEST_CHANGED"):
        TrainingPublicContext(request, context, fingerprints)
    # This public value supplies no authenticated transport or MODEL_TRAIN grant.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    import base64
    key = Ed25519PrivateKey.generate()
    pin = {"schema_version": 1, "algorithm": "Ed25519", "key_id": "test-key",
        "public_key": base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")}
    client = TrainingPhaseClient(request, context, pinned_public_key=pin, public_context=public)
    with pytest.raises(TrainingBlocked, match="TRAINING_PHASE_TRANSPORT_NOT_BOUND"):
        client.authorize(request, "initial")


# The real owner implementations run against an explicitly disposable Canonical
# DB. These tests grant only synthetic technical material; they are not admission
# or acceptance for a real training job.
from tests.test_owned_training_checkpoint_recovery import policy_material
from tests.test_owned_training_phase_http_v2 import (
    _prepare_task,
    _request_object,
    phase_http,
    strict_permission_mode,
)

__all__ = ["phase_http", "policy_material", "strict_permission_mode"]


def test_actual_authenticated_phase_http_preserves_original_task_pin_and_fresh_revocation(checkpoint_owner):
    import threading
    import requests
    from werkzeug.serving import make_server
    from lumenis.system.ai_gateway.owned_training_runtime import OwnedTrainingPhaseHTTPTransport
    from lumenis.system.ai_gateway.owned_training_phases import TrainingPhaseClient, TrainingPublicContext
    from lumenis.system.security.permission import owned_training_phase_fingerprints
    from tests.test_owned_training_phase_http_v2 import _headers_for, _task_rows
    owner, worker, case, grant = checkpoint_owner
    owner.initialize()
    prepared = owner.initial_phase_context()
    task_count = len(_task_rows(case["db"])[0])
    server = make_server("127.0.0.1", 0, case["app"])
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    session = requests.Session()
    session.trust_env = False
    session.headers.update(_headers_for(grant["identity"]))
    try:
        transport = OwnedTrainingPhaseHTTPTransport(core_origin=f"http://127.0.0.1:{server.server_port}",
            session=session, pinned_public_key=case["initial_public_key"])
        request = _request_object(case["request_data"])
        context = {"scope_descriptors": case["body"]["scope_descriptors"]}
        fingerprints = owned_training_phase_fingerprints(request, context=context, domain_id="cth", actor_id=1)
        client = TrainingPhaseClient.from_prepared_task(request, context, prepared_task=prepared,
            pinned_public_key=case["initial_public_key"], transport=transport,
            public_context=TrainingPublicContext(request, context, fingerprints))
        client.authorize(request, "initial")
        client.require_current_receipt()
        history = client.read_last_history()
        assert history["historical"] is True and history["authorization_usable"] is False
        assert client._task_id == owner.task_id and len(_task_rows(case["db"])[0]) == task_count
        with pytest.raises(TrainingBlocked, match="TRAINING_PHYSICAL_RECOVERY_REQUIRED"):
            owner.initial_phase_context()
        with pytest.raises(TrainingBlocked, match="CHECKPOINT_REQUEST_INVALID"):
            transport("POST", "https://other-host.invalid/", {})
        assert case["gate"].revoke_approval(grant["approval_token"]) is True
        with pytest.raises(TrainingBlocked):
            client.authorize(request, "before_output_dir")
    finally:
        session.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


@pytest.fixture
def checkpoint_owner(phase_http, policy_material, tmp_path, monkeypatch, request):
    import copy
    import hashlib
    import shared_artifacts
    from lumenis.system.ai_gateway import owned_training as training
    from lumenis.system.ai_gateway.owned_training_checkpoints import CheckpointPolicy
    from lumenis.system.ai_gateway.owned_training_runtime import OwnedTrainingCheckpointClient
    document = copy.deepcopy(policy_material[0])
    document["base_recipe"] = training.ADA_RECIPE
    policy = CheckpointPolicy.validate(document)
    material = json.loads(training.APPROVED_MANIFEST_PATH.read_bytes())
    material["checkpoint_recovery_policies"] = {"schema_version": 1, "policies": {policy.sha256: document}}
    manifest = (tmp_path / "approved-technical-manifest.json").resolve()
    manifest.write_text(json.dumps(material), encoding="utf-8")
    monkeypatch.setattr(training, "APPROVED_MANIFEST_PATH", manifest)
    case = phase_http
    case["request_data"]["recipe"] = policy.recipe
    case["request_data"]["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if getattr(request, "param", None) == "managed":
        # Non-model technical bytes, solely to exercise the authenticated pipe.
        for split in ("train", "heldout"):
            path = (tmp_path / (split + ".jsonl")).resolve()
            path.write_bytes(("{\"technical_split\":\"" + split + "\"}\n").encode())
            case["request_data"][split + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        case["managed_inputs"] = {"train": tmp_path / "train.jsonl", "heldout": tmp_path / "heldout.jsonl"}
    grant = case["grant"]("account", 1)
    task_id = _prepare_task(case, grant)
    owner_root = (tmp_path / "artifact-owner").resolve()
    staging = owner_root / "worker-output"
    staging.mkdir(parents=True)
    monkeypatch.setattr(shared_artifacts, "artifact_root", lambda: owner_root)
    worker = TrainingProcessFence((tmp_path / "client-owner.lock").resolve())
    try:
        worker.start([sys.executable, "-c", "import time; time.sleep(60)"],
            cwd=tmp_path.resolve(), log_path=(tmp_path / "client-owner.log").resolve())
        client = OwnedTrainingCheckpointClient(request=_request_object(case["request_data"]),
            context={"scope_descriptors": case["body"]["scope_descriptors"]},
            task_id=task_id, worker=worker, staging_root=staging, max_bytes=1024**2,
            manifest_path=manifest, actor_id=1)
        from tests.test_owned_training_phase_http_v2 import _headers_for
        with case["app"].test_request_context("/", headers=_headers_for(grant["identity"]),
                environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
            yield client, worker, case, grant
    finally:
        worker.close()


@pytest.mark.parametrize("checkpoint_owner", ["managed"], indirect=True)
def test_actual_private_worker_calls_current_owner_and_reaps_on_test_only_policy(checkpoint_owner):
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins
    client, worker, case, grant = checkpoint_owner
    root = Path(__file__).resolve().parents[1]
    stopped = worker.stop_and_reap()
    worker.start_managed_training(python_executable=Path(sys.executable), cwd=root,
        log_path=(client._staging_root / "managed-owner.log").resolve(),
        source_pins=training_worker_source_pins(root), replace=True)
    state = client.initialize()
    assert state["worker_binding"] == worker.worker_binding
    # The child rechecks actual Permission over its private pipe, then rejects
    # a test-only recipe that is not admitted in its canonical config.
    invocation = {"model_snapshot_dir": str(client._staging_root / "no-model"),
        "train_jsonl_path": str(case["managed_inputs"]["train"]),
        "heldout_jsonl_path": str(case["managed_inputs"]["heldout"]),
        "output_dir": str(client._staging_root / "not-created"),
        "manifest_path": str(client._manifest_path), "resume_request": None, "stop_after_checkpoint_step": 2}
    with pytest.raises(TrainingBlocked, match="CHECKPOINT_RECIPE_NOT_AUTHORIZED"):
        worker.invoke_owned_training(client=client, phase_transport=lambda *args: pytest.fail("No phase/model may run"),
            invocation=invocation, timeout_seconds=30)
    assert worker._process.returncode is not None
    assert not (client._staging_root / "not-created").exists()
    assert stopped["worker_binding"] != worker.worker_binding


def test_actual_gate_fence_task_binding_and_single_use_start(checkpoint_owner):
    import uuid
    client, worker, case, grant = checkpoint_owner
    state = client.initialize()
    assert state["worker_binding"] == worker.worker_binding
    operation_id = str(uuid.uuid4())
    reservation = client.reserve_save(operation_id=operation_id, completed_step=2, parent_ref=None)
    record = client._read(operation_id)
    assert set(record["result"]["binding"]) == {"task_id", "domain_id", "task_digest", "operation_id",
        "attempt_id", "worker_epoch", "actor_identity", "scope_descriptors", "artifact_version", "parent_ref"}
    assert record["state"] == "RESERVED"
    assert reservation["staging_root"].is_dir()
    client.require_current_admission(reservation["admission_receipt"], request=client.request, operation="save")
    assert client._read(operation_id)["state"] == "WRITING"
    with pytest.raises((TrainingBlocked, PermissionError, ValueError)):
        client.require_current_admission(reservation["admission_receipt"], request=client.request, operation="save")
    assert client._read(operation_id)["state"] == "WRITING"


def test_revoked_actual_approval_prevents_reserved_start(checkpoint_owner):
    import uuid
    from tests.test_owned_training_phase_http_v2 import _db_snapshot
    client, worker, case, grant = checkpoint_owner
    client.initialize()
    reservation = client.reserve_save(operation_id=str(uuid.uuid4()), completed_step=2, parent_ref=None)
    before = _db_snapshot(case["db"])
    assert case["gate"].revoke_approval(grant["approval_token"]) is True
    with pytest.raises((TrainingBlocked, PermissionError)):
        client.require_current_admission(reservation["admission_receipt"], request=client.request, operation="save")
    assert _db_snapshot(case["db"]) == before



def test_actual_task_artifact_commit_and_load_start_renewal(checkpoint_owner, tmp_path):
    """Synthetic checkpoint bytes test storage/state only; no trainer is loaded."""
    import hashlib
    import uuid
    import shared_artifacts
    from lumenis.shared.database import get_repository
    from lumenis.system.ai_gateway.owned_training_checkpoints import canonical_bytes, inspect_checkpoint_files, _FRAMEWORK_PACKAGES
    client, worker, case, grant = checkpoint_owner
    shared_artifacts.ensure_artifact_table()
    client.initialize()
    operation_id = str(uuid.uuid4())
    reservation = client.reserve_save(operation_id=operation_id, completed_step=2, parent_ref=None)
    client.require_current_admission(reservation["admission_receipt"], request=client.request, operation="save")
    directory = reservation["staging_root"] / reservation["checkpoint_relative_path"]
    directory.mkdir()
    for names in client.policy.document["required_roles"].values():
        for name in names:
            (directory / name).write_bytes(b"synthetic technical checkpoint inventory, never a model")
    position = {"dataset_sha256": client.request.train_sha256, "sampler_state_sha256": "f"*64,
        "epoch_index": 0, "next_batch_index": 2, "completed_step": 2, "gradient_accumulation_offset": 0}
    observed = {"completed_step": 2, "data_position": position,
        **{k:"a"*64 for k in ("optimizer_state_sha256", "scheduler_state_sha256", "rng_state_sha256", "adapter_or_model_state_sha256")},
        "framework_lock_sha256": client.policy.document["framework_lock_sha256"]}
    (directory / "lumenis_observed_state.json").write_bytes(canonical_bytes(observed))
    inventory = {"schema_version": 1, "operation_id": operation_id, "completed_step": 2,
        "checkpoint_relative_path": reservation["checkpoint_relative_path"], "policy_sha256": client.policy.sha256,
        "fingerprints": client._fingerprints, "framework_versions": {name:"test-runtime" for name in _FRAMEWORK_PACKAGES},
        "trainer_config_sha256": client.policy.document["trainer_config_sha256"],
        "data_order_sha256": client.policy.document["data_order_sha256"], "data_position": position,
        "files": inspect_checkpoint_files(reservation["staging_root"], reservation["checkpoint_relative_path"], client.policy)}
    receipt = client.commit_save(operation_id=operation_id, inventory=inventory)
    assert receipt["artifact_version"] == 1 and client.read_save(operation_id=operation_id)["state"] == "COMMITTED"
    assert client.commit_save(operation_id=operation_id, inventory=inventory) == receipt
    with get_repository().connection(read_only=True, wal=False) as con:
        assert con.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts").fetchone()[0] == 1
    _ = worker.worker_binding
    worker.stop_and_reap()
    worker.replace_stopped_worker([sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path.resolve(), log_path=(tmp_path / "resume-worker.log").resolve())
    load_id = str(uuid.uuid4())
    args = {"operation_id": load_id, "checkpoint_ref": receipt["artifact_ref"],
        "expected_checkpoint_sha256": receipt["artifact_sha256"], "replay_through_step": 4}
    first = client.prepare_resume(**args)
    assert first["worker_epoch"] == 2 and first["source_run_digest"] != first["run_digest"]
    renewed = client.prepare_resume(**args)
    assert renewed["attempt_id"] == first["attempt_id"] and renewed["run_digest"] == first["run_digest"]
    assert renewed["admission_receipt"].envelope["payload"]["reservation_digest"] == first["admission_receipt"].envelope["payload"]["reservation_digest"]
    client.require_current_admission(renewed["admission_receipt"], request=client.request, operation="load")
    assert client._read(load_id)["state"] == "LOADING"
    with pytest.raises((TrainingBlocked, PermissionError, ValueError)):
        client.prepare_resume(**args)
    # A storage inventory and caller dict cannot certify physical optimizer/RNG
    # restore. Managed execution observation still has to be bound by the owner.
    with pytest.raises(TrainingBlocked, match="CHECKPOINT_ACTUAL_LOAD_NOT_OBSERVED"):
        client.complete_load(operation_id=load_id, restored_state=observed)


    # Seed only an explicitly synthetic signed loaded-state fixture to exercise
    # the real resumed phase protocol. complete_load above still rejects caller
    # dicts. This fixture certifies no physical framework or GPU restore.
    from datetime import datetime, timezone
    from lumenis.system.security import training_receipts as r
    from lumenis.system.ai_gateway.owned_training_phases import TrainingPhaseClient, TrainingPhaseBlocked

    def fixture_loaded(conn):
        execution = client._engine.training_execution_read(client.task_id, **client._args(conn))
        loaded = {"schema_version": 1, "operation_id": load_id, "task_digest": execution["task_digest"],
            "run_digest": execution["run_digest"], "checkpoint_ref": receipt["artifact_ref"],
            "checkpoint_sha256": receipt["artifact_sha256"], "restored_state": observed,
            "task_step_ref": "trainop_" + hashlib.sha256((client.task_id+load_id).encode()).hexdigest(),
            "committed_at_utc": datetime.now(timezone.utc).isoformat()}
        handoff = {"schema_version": 1, "task_id": client.task_id, "task_digest": execution["task_digest"],
            "run_digest": execution["run_digest"], "attempt_id": execution["attempt_id"], "worker_epoch": execution["worker_epoch"],
            "fingerprints": client._fingerprints, "checkpoint_ref": receipt["artifact_ref"],
            "checkpoint_sha256": receipt["artifact_sha256"], "load_operation_id": load_id,
            "resume_receipt_sha256": hashlib.sha256(canonical_bytes(loaded)).hexdigest(),
            "next_sequence": execution["next_sequence"], "next_phase": "before_train", "admission_version": 3,
            "worker_binding_sha256": hashlib.sha256(canonical_bytes(execution["worker_binding"])).hexdigest()}
        loaded["phase_handoff"] = r.sign_training_checkpoint_payload(handoff, receipt_kind="owned_training_recovery_handoff")
        loaded["receipt"] = r.sign_training_checkpoint_payload(loaded, receipt_kind="owned_training_resume_loaded")
        client._engine.training_operation_transition(client.task_id, operation_id=load_id,
            before_state="LOADING", state="LOADED", result=loaded, **client._args(conn))
        client._engine.training_execution_commit_loaded(client.task_id,
            phase_handoff=loaded["phase_handoff"], **client._args(conn))
        return loaded
    fixture_load = client._mutate("load", fixture_loaded, operation_id=load_id)
    transport = client.recovery_phase_transport(operation_id=load_id)
    verified = r.verify_training_recovery_handoff(fixture_load["phase_handoff"],
        expected_payload=fixture_load["phase_handoff"]["payload"], pinned_public_key=client._pin)
    phase = TrainingPhaseClient.from_recovery_handoff(client.request, client.context,
        handoff=verified, pinned_public_key=client._pin, transport=transport, actor_id=1)
    before_recovery = client._read(load_id)
    with pytest.raises(TrainingPhaseBlocked):
        phase.authorize(client.request, "initial")
    assert client._read(load_id) == before_recovery
    phase.authorize(client.request, "before_train")
    phase.require_current_receipt()
    assert client._read(load_id)["state"] == "RUNNABLE"
    history = phase.read_last_history()
    assert history["historical"] is True and history["authorization_usable"] is False
    prefix = "/api/experience/owned-training/phase-tasks/" + client.task_id
    from dataclasses import asdict
    request_body = asdict(client.request);request_body["scopes"] = list(client.request.scopes)
    common = {"training_request": request_body, "scope_descriptors": client.context["scope_descriptors"]}
    with pytest.raises((TrainingBlocked, PermissionError, ValueError)):
        transport("POST", prefix+"/challenge-decisions", {**common,"challenge":history["challenge"]})
    with pytest.raises(TrainingBlocked, match="CHECKPOINT_SCOPE_MISMATCH"):
        transport("POST",prefix+"/challenges",{**common,"phase":"step_begin","caller_grant":True})
    phase.authorize(client.request, "step_begin")
    phase.require_current_receipt()
    # Actual current Permission revocation prevents any resumed optimizer permit.
    assert case["gate"].revoke_approval(grant["approval_token"]) is True
    with pytest.raises(TrainingPhaseBlocked):
        phase.authorize(client.request, "pre_optimizer_step")
