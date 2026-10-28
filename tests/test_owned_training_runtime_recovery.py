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
            self.lifecycle = []
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

        def cancel_checkpoint_transfers(self):
            self.lifecycle.append("cancel-transfer-readers")
            return {"state": "CHECKPOINT_TRANSFER_READERS_STOPPED", "count": 0}

        def verify_training_inputs(self, paths, expected_files):
            return {"state": "PHYSICAL_TRAINING_INPUTS_VERIFIED", "paths": paths,
                "files": expected_files, "remote_peer": dict(self.peer)}

        def stop_remote_and_reap(self):
            self.lifecycle.append("stop-remote-worker")
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
        assert transport.lifecycle == ["cancel-transfer-readers", "stop-remote-worker"]
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
@pytest.fixture(params=[False, True], ids=["copies", "symlinks"])
def private_worker_venv(tmp_path, request):
    """Real isolated venv with local copies of the already installed dependencies.

    No pip/network, global installation, inherited PYTHONPATH or model is used.
    The same interpreter/dependency bytes exercise both legitimate venv layouts.
    """
    import importlib.util
    import shutil
    import venv

    environment = tmp_path / ("symlinks" if request.param else "copies")
    venv.EnvBuilder(with_pip=False, symlinks=request.param).create(environment)
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site_path = json.loads(subprocess.check_output(
        [str(executable), "-I", "-c", "import json,sysconfig; print(json.dumps(sysconfig.get_path('purelib')))"],
        text=True, timeout=10))
    site_path = Path(site_path)
    for name in ("psutil", "cryptography", "cffi", "_cffi_backend", "pycparser"):
        specification = importlib.util.find_spec(name)
        assert specification is not None and specification.origin
        origin = Path(specification.origin)
        if specification.submodule_search_locations is not None:
            shutil.copytree(origin.parent, site_path / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(origin, site_path / origin.name)
    if os.name != "nt":
        assert executable.is_symlink() is request.param
    observed = json.loads(subprocess.check_output(
        [str(executable), "-I", "-c", "import json,sys,psutil; print(json.dumps({'prefix':sys.prefix,'psutil':psutil.__file__}))"],
        text=True, timeout=10))
    assert Path(observed["prefix"]) == environment
    assert Path(observed["psutil"]).is_relative_to(site_path)
    return executable, environment, site_path


def test_managed_worker_preserves_private_venv_for_start_replace_and_reap(private_worker_venv, tmp_path, monkeypatch):
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins

    executable, environment, site_path = private_worker_venv
    root = Path(__file__).resolve().parents[1]
    # These values must not be forwarded to the child to make its imports work.
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "untrusted-pythonpath"))
    monkeypatch.setenv("LUMENIS_TEST_PRIVATE_ENV_CANARY", "must-not-be-inherited")
    worker = TrainingProcessFence((tmp_path / "venv.lock").resolve())
    peers = []
    try:
        for generation in range(2):
            ready = worker.start_managed_training(python_executable=executable, cwd=root,
                log_path=(tmp_path / f"venv-{generation}.log").resolve(),
                source_pins=training_worker_source_pins(root), replace=generation > 0)
            peer = psutil.Process(ready["framework_worker"]["pid"])
            peers.append(peer.pid)
            assert os.path.normcase(peer.cmdline()[0]) == os.path.normcase(str(executable))
            identity = ready["interpreter_identity"]
            assert Path(identity["executable"]) == executable
            assert Path(identity["prefix"]) == environment
            assert identity["prefix"] != identity["base_prefix"]
            assert identity["version"] == list(sys.version_info[:3])
            assert Path(identity["psutil_origin"]).is_relative_to(site_path)
            assert ready["model_loaded"] is False
            actual_environment = peer.environ()
            assert "PYTHONPATH" not in actual_environment
            assert "LUMENIS_TEST_PRIVATE_ENV_CANARY" not in actual_environment
            assert actual_environment["PYTHONNOUSERSITE"] == "1"
            if generation == 0:
                stopped = worker.stop_and_reap()
                assert not psutil.pid_exists(peer.pid)
                first_binding = ready["worker_binding"]
            else:
                assert worker.require_previous_worker_stopped(first_binding) == stopped
                with pytest.raises(TrainingBlocked, match="TRAINING_PHASE_TRANSPORT_NOT_BOUND"):
                    worker.invoke_owned_training(client=object(), phase_transport=None, invocation={}, timeout_seconds=1)
                assert worker._process.returncode is not None
                assert not psutil.pid_exists(peer.pid)
    finally:
        worker.close()
    assert all(not psutil.pid_exists(pid) for pid in peers)


@pytest.mark.parametrize("invalid_entry", ["relative", "missing", "directory", "broken", "cycle"])
def test_managed_worker_rejects_invalid_interpreter_before_spawn(tmp_path, invalid_entry):
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins

    root = Path(__file__).resolve().parents[1]
    entry = tmp_path / "invalid-python"
    if invalid_entry == "relative":
        entry = Path("python")
    elif invalid_entry == "directory":
        entry.mkdir()
    elif invalid_entry == "broken":
        entry.symlink_to(tmp_path / "absent")
    elif invalid_entry == "cycle":
        entry.symlink_to(entry)
    fence = TrainingProcessFence((tmp_path / "invalid.lock").resolve())
    try:
        with pytest.raises(TrainingBlocked):
            fence.start_managed_training(python_executable=entry, cwd=root,
                log_path=(tmp_path / "invalid.log").resolve(), source_pins=training_worker_source_pins(root))
        assert fence._process is None
    finally:
        fence.close()


@pytest.mark.parametrize("mutation", ["malformed", "wrong-executable", "missing-entry", "changed-target"])
def test_managed_worker_rejects_identity_or_entry_change_and_reaps(tmp_path, monkeypatch, mutation):
    import shutil
    from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins

    root = Path(__file__).resolve().parents[1]
    # Keep the real launch in its original venv so its dependencies remain intact.
    executable = Path(sys.executable)
    fence = TrainingProcessFence((tmp_path / "rejected.lock").resolve())
    receive = fence._receive_managed
    actual_resolve = Path.resolve
    child_pids = []

    def altered_hello(deadline):
        hello = receive(deadline)
        child_pids.append(hello["pid"])
        if mutation == "malformed":
            hello["interpreter_identity"]["version"] = [True, 12, 0]
        elif mutation == "wrong-executable":
            hello["interpreter_identity"]["executable"] = str(tmp_path / "other-python")
        else:
            alternate = tmp_path / "alternate-python"
            if mutation == "changed-target":
                shutil.copy2(actual_resolve(executable), alternate)
            def changed_resolve(path, *args, **kwargs):
                if path == executable:
                    if mutation == "missing-entry":
                        raise FileNotFoundError("synthetic launch entry disappeared")
                    return alternate
                return actual_resolve(path, *args, **kwargs)
            monkeypatch.setattr(Path, "resolve", changed_resolve)
        return hello

    monkeypatch.setattr(fence, "_receive_managed", altered_hello)
    try:
        with pytest.raises(TrainingBlocked, match="TRAINING_WORKER_SOURCE_MISMATCH"):
            fence.start_managed_training(python_executable=executable, cwd=root,
                log_path=(tmp_path / "rejected.log").resolve(), source_pins=training_worker_source_pins(root))
        assert fence._process.returncode is not None
        assert child_pids and all(not psutil.pid_exists(pid) for pid in child_pids)
    finally:
        fence.close()
