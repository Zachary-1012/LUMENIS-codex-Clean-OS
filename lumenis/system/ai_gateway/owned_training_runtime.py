"""Training-specific supervised process and current checkpoint composition.

The existing Task, Permission and Shared Artifact owners retain authority. This
module provides process handles and adapters, never a queue, store or provider.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import queue
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid
from urllib.parse import urlsplit

import psutil

from .owned_training import TrainingBlocked
from .owned_training_checkpoints import canonical_bytes, _regular_stat


_MANAGED_SOURCE_PATHS = (
    "lumenis/system/ai_gateway/owned_training.py",
    "lumenis/system/ai_gateway/owned_training_phases.py",
    "lumenis/system/ai_gateway/owned_training_checkpoints.py",
    "lumenis/system/ai_gateway/owned_training_runtime.py",
    "lumenis/system/security/training_receipts.py",
)
_CHECKPOINT_METHODS = frozenset({"reserve_save", "commit_save", "read_save", "prepare_resume",
    "complete_load", "read_resume", "require_current_admission"})
_PIPE_LIMIT = 2 * 1024 * 1024


def training_worker_source_pins(root: Path):
    """Measure the named trainer/observer files; never infer whole-repo proof."""
    if type(root) is not type(Path()) or not root.is_absolute():
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    result = {}
    for name in _MANAGED_SOURCE_PATHS:
        path = root / name
        _regular_stat(path, directory=False)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _pipe_encode(value):
    """Only detached JSON, Paths and reverified public receipts cross the pipe."""
    from lumenis.system.security import training_receipts as r
    receipt_types = {r.VerifiedTrainingCheckpointAdmission: "owned_training_checkpoint_admission",
        r.VerifiedTrainingCheckpointReceipt: "owned_training_checkpoint_committed",
        r.VerifiedTrainingResumeReceipt: "owned_training_resume_loaded",
        r.VerifiedTrainingRecoveryHandoff: "owned_training_recovery_handoff"}
    if type(value) in receipt_types:
        return {"__owned_training_wire__": "receipt", "kind": receipt_types[type(value)], "envelope": value.envelope}
    if type(value) in {type(Path()), PurePosixPath}:
        return {"__owned_training_wire__": "path", "value": str(value)}
    if type(value) is dict:
        if any(type(k) is not str for k in value) or "__owned_training_wire__" in value:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        return {k: _pipe_encode(v) for k, v in value.items()}
    if type(value) in {list, tuple}:
        return [_pipe_encode(v) for v in value]
    if value is None or type(value) in {str, int, bool} or type(value) is float and math.isfinite(value):
        return value
    raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")


def _pipe_decode(value, pin):
    from lumenis.system.security import training_receipts as r
    if type(value) is dict and "__owned_training_wire__" in value:
        if value.get("__owned_training_wire__") == "path" and set(value) == {"__owned_training_wire__", "value"}:
            if type(value["value"]) is not str:
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
            if Path(value["value"]).is_absolute():
                return Path(value["value"])
            remote = PurePosixPath(value["value"])
            if (remote.is_absolute() and "\\" not in value["value"]
                    and not value["value"].startswith("//")
                    and not any(ord(char) < 32 for char in value["value"])
                    and all(part not in {".", ".."} for part in value["value"].split("/"))):
                return remote
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        verifiers = {"owned_training_checkpoint_admission": r.verify_training_checkpoint_admission,
            "owned_training_checkpoint_committed": r.verify_training_checkpoint_receipt,
            "owned_training_resume_loaded": r.verify_training_resume_receipt,
            "owned_training_recovery_handoff": r.verify_training_recovery_handoff}
        if (set(value) != {"__owned_training_wire__", "kind", "envelope"}
                or value["__owned_training_wire__"] != "receipt" or value["kind"] not in verifiers
                or type(value["envelope"]) is not dict or type(value["envelope"].get("payload")) is not dict):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        try:
            return verifiers[value["kind"]](value["envelope"],
                expected_payload=value["envelope"]["payload"], pinned_public_key=pin)
        except r.TrainingReceiptError:
            raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH") from None
    if type(value) is dict:
        return {k: _pipe_decode(v, pin) for k, v in value.items()}
    if type(value) is list:
        return [_pipe_decode(v, pin) for v in value]
    if value is None or type(value) in {str, int, bool} or type(value) is float and math.isfinite(value):
        return value
    raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")


def _write_pipe(stream, value):
    raw = canonical_bytes(value)
    if len(raw) > _PIPE_LIMIT:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    stream.write(raw + b"\n")
    stream.flush()


def _read_pipe(stream):
    if type(stream) is _RemoteTrainingInput:
        return stream.receive()
    from .owned_training_checkpoints import strict_json
    raw = stream.readline(_PIPE_LIMIT + 2)
    if not raw or len(raw) > _PIPE_LIMIT + 1 or not raw.endswith(b"\n"):
        raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
    return strict_json(raw[:-1])


class _RemoteTrainingInput:
    """One reader owns SSH stdin; actual EOF kills this isolated Linux tree.

    No admission or successful training is inferred from connection identity.
    The controller independently checks /proc and source bytes over its SSH
    connection. Dedicated process-group/session ownership is mandatory.
    """

    def __init__(self, stream):
        pid = os.getpid()
        if (sys.platform != "linux" or os.getsid(pid) != pid or os.getpgid(pid) != pid):
            raise TrainingBlocked("REMOTE_TRAINING_ISOLATED_SESSION_REQUIRED")
        self._pid = pid
        self._messages = queue.Queue(maxsize=4)
        self._closed = threading.Event()
        def receive():
            try:
                while True:
                    value = _read_pipe(stream)
                    self._messages.put(value)
            except BaseException:
                # The actual owner-launched session contains only this worker
                # and its descendants. Do not let a disconnected optimizer
                # continue or certify a checkpoint through an expired channel.
                self._closed.set()
                os.killpg(self._pid, signal.SIGKILL)
        self._reader = threading.Thread(target=receive, daemon=True)
        self._reader.start()

    def receive(self):
        if self._closed.is_set():
            raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
        return self._messages.get()

    def wait_closed(self):
        self._closed.wait()


class OwnedTrainingPhaseHTTPTransport:
    """Use W6's exact Core address and already authenticated private Session.

    The original public pin is separate from server authentication. No default
    host, credential discovery, redirects, retries or checkpoint endpoint exists.
    This object stays on the owner side of the supervised worker's private pipe.
    """

    def __init__(self, *, core_origin, session, pinned_public_key):
        import requests
        from lumenis.system.security import training_receipts as r
        if type(core_origin) is not str or core_origin != core_origin.strip():
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        address = urlsplit(core_origin)
        if (address.scheme not in {"https", "http"} or not address.hostname
                or address.username is not None or address.password is not None
                or address.path not in {"", "/"} or address.query or address.fragment
                or address.scheme == "http" and address.hostname not in {"127.0.0.1", "localhost", "::1"}
                or type(session) is not requests.Session or session.trust_env is not False
                or session.verify is not True):
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        self._origin = core_origin.rstrip("/")
        self._session = session
        r._validate_pinned_public_key(pinned_public_key)
        self._pin = copy.deepcopy(pinned_public_key)

    def __call__(self, method, path, body=None):
        import requests
        from .owned_training_checkpoints import strict_json
        root = "/api/experience/owned-training/phase-tasks"
        task = r"trainrelay_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
        post = path == root or type(path) is str and re.fullmatch(root + "/" + task + r"/(challenges|challenge-decisions)", path) is not None
        get = type(path) is str and re.fullmatch(root + "/" + task + r"/receipts/[0-9a-f]{64}", path) is not None
        if not ((method == "POST" and post and type(body) is dict)
                or (method == "GET" and get and body is None)):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        url = self._origin + path
        adapter = self._session.get_adapter(url)
        if (self._session.trust_env is not False or self._session.verify is not True
                or getattr(adapter.max_retries, "total", None) not in {0, False}):
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        raw = None if body is None else canonical_bytes(body)
        if raw is not None and len(raw) > _PIPE_LIMIT:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        request = requests.Request(method, url, data=raw, headers={"Content-Type": "application/json"})
        prepared = self._session.prepare_request(request)
        if prepared.url != url:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        try:
            with self._session.send(prepared, stream=True, allow_redirects=False,
                    timeout=(3, 10), verify=True, proxies={}) as response:
                if not 200 <= response.status_code < 300:
                    raise TrainingBlocked("TRAINING_PHASE_RESPONSE_DENIED")
                chunks, size = [], 0
                for chunk in response.iter_content(16384):
                    size += len(chunk)
                    if size > _PIPE_LIMIT:
                        raise TrainingBlocked("TRAINING_PHASE_RESPONSE_INVALID")
                    chunks.append(chunk)
                reply = strict_json(b"".join(chunks))
        except requests.RequestException:
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_FAILED") from None
        if (type(reply) is not dict or reply.get("ok") is not True
                or "pinned_public_key" in reply and reply["pinned_public_key"] != self._pin):
            raise TrainingBlocked("TRAINING_PHASE_RESPONSE_DENIED")
        # The existing decision response has no echoed public pin. Its sealed
        # receipt is verified by TrainingPhaseClient against the original pin.
        return reply


class TrainingProcessFence:
    """Retain an OS exclusion handle and the actual spawned worker identity.

    The caller creates one owner-only lock directory. No attach-to-arbitrary-PID
    operation exists. A missing handle or ambiguous descendant never permits
    replacement. The supervisor must retain this object for the whole attempt.
    """

    def __init__(self, lock_path: Path):
        if type(lock_path) is not type(Path()) or not lock_path.is_absolute():
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        for parent in [*reversed(lock_path.parent.parents), lock_path.parent]:
            _regular_stat(parent, directory=True)
        self._mutex = threading.RLock()
        self._lock_path = lock_path
        self._file = None
        self._process = None
        self._worker = None
        self._descendants = {}
        self._stopped = None
        self._last_stop = None
        self._channel = None
        self._channel_queue = None
        self._source_root = None
        self._source_pins = None
        self._remote_transport = None
        self._remote_peer = None
        self._peer = None
        self._load_observation = None
        self._observing_load = False
        self._invocation_active = False
        self._managed_invoked = False
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(lock_path, flags, 0o600)
            self._file = os.fdopen(descriptor, "r+b", buffering=0)
            info = os.fstat(self._file.fileno())
            path_info = lock_path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or stat.S_ISLNK(path_info.st_mode)
                    or getattr(path_info, "st_file_attributes", 0) & 0x400
                    or (info.st_dev, info.st_ino) != (path_info.st_dev, path_info.st_ino)):
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            if info.st_size == 0:
                self._file.write(b"\0")
                os.fsync(self._file.fileno())
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._file_identity = (info.st_dev, info.st_ino)
            self._lock_sha256 = hashlib.sha256(canonical_bytes({
                "path": str(lock_path), "device": info.st_dev, "inode": info.st_ino})).hexdigest()
        except (OSError, TrainingBlocked):
            if self._file is not None:
                self._file.close()
            self._file = None

            raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST") from None

    def _require_handle(self):
        if self._file is None or self._file.closed:
            raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
        try:
            info = self._lock_path.lstat()
            current = os.fstat(self._file.fileno())
        except OSError:
            raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST") from None
        if (stat.S_ISLNK(info.st_mode) or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 0x400
                or (info.st_dev, info.st_ino) != self._file_identity
                or (current.st_dev, current.st_ino) != self._file_identity):
            raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")

    @property
    def worker_binding(self):
        with self._mutex:
            self._require_handle()
            if self._worker is None:
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
            return dict(self._worker)

    def start(self, argv: list[str], *, cwd: Path, log_path: Path, _managed=False):
        """Launch the owner-selected executable, with no shell or secret env."""
        with self._mutex:
            self._require_handle()
            if self._process is not None or self._worker is not None:
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
            if (type(argv) is not list or not argv or any(type(x) is not str or not x or "\0" in x for x in argv)
                    or type(cwd) is not type(Path()) or not cwd.is_absolute()
                    or type(log_path) is not type(Path()) or not log_path.is_absolute()):
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
            _regular_stat(cwd, directory=True)
            _regular_stat(log_path.parent, directory=True)
            environment = {name: os.environ[name] for name in (
                "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "LANG", "LC_ALL")
                if name in os.environ}
            environment.update(PYTHONUNBUFFERED="1", PYTHONNOUSERSITE="1")
            try:
                with log_path.open("xb", buffering=0) as log:
                    self._process = subprocess.Popen(argv, cwd=cwd, env=environment,
                        stdin=subprocess.PIPE if _managed else subprocess.DEVNULL,
                        stdout=subprocess.PIPE if _managed else log,
                        stderr=log if _managed else subprocess.STDOUT,
                        shell=False, close_fds=True, start_new_session=os.name != "nt")
                process = psutil.Process(self._process.pid)
                self._worker = {"pid": process.pid, "created_at": process.create_time(),
                                "lock_sha256": self._lock_sha256}
                if _managed:
                    self._channel = (self._process.stdin, self._process.stdout)
                    self._channel_queue = queue.Queue(maxsize=4)
                    incoming, messages = self._process.stdout, self._channel_queue
                    def receive():
                        try:
                            while True:
                                messages.put(_read_pipe(incoming))
                        except BaseException:
                            messages.put(TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST"))
                    threading.Thread(target=receive, daemon=True).start()
                return dict(self._worker)
            except Exception:
                if self._process is not None:
                    self._process.kill()
                    self._process.wait(timeout=5)
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None

    def require_live(self, expected_binding=None):
        with self._mutex:
            self._require_handle()
            if self._worker is None or self._stopped is not None or self._process.poll() is not None:
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            if expected_binding is not None and expected_binding != self._worker:
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            if self._remote_transport is not None:
                try:
                    observed = self._remote_transport.require_live()
                    if observed != self._remote_peer or observed.get("pid") != self._worker["pid"] or observed.get("created_at") != self._worker["created_at"]:
                        raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
                    return None
                except TrainingBlocked:
                    raise
                except Exception:
                    raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST") from None
            try:
                process = psutil.Process(self._worker["pid"])
                if not process.is_running() or process.create_time() != self._worker["created_at"]:
                    raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
                children = process.children(recursive=True)
                for child in children:
                    self._descendants[child.pid] = child.create_time()
                return process
            except (psutil.Error, OSError):
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None

    @contextmanager
    def exclude_writer(self, expected_binding):
        """Pause the exact live tree while the Artifact owner copies closed bytes.

        A successful metadata flag is never treated as OS exclusion. Ambiguous
        pause/reaping returns an error, and the caller must stop/reconcile.
        """
        with self._mutex:
            root = self.require_live(expected_binding)
            if self._remote_transport is not None:
                paused = False
                try:
                    result = self._remote_transport.signal_writer_group(paused=True)
                    if (type(result) is not dict or set(result) != {"state", "peer"}
                            or result.get("state") != "REMOTE_WRITERS_PAUSED"
                            or result.get("peer") != self._remote_peer):
                        raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                    paused = True
                    self._require_handle()
                    yield
                    self._require_handle()
                    self.require_live(expected_binding)
                except TrainingBlocked:
                    raise
                except Exception:
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None
                finally:
                    if paused:
                        try:
                            result = self._remote_transport.signal_writer_group(paused=False)
                            if (type(result) is not dict or set(result) != {"state", "peer"}
                                    or result.get("state") != "REMOTE_WRITERS_RESUMED"
                                    or result.get("peer") != self._remote_peer):
                                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                            self.require_live(expected_binding)
                        except Exception:
                            raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None
                return
            paused = []
            try:
                root.suspend()
                paused.append(root)
                children = root.children(recursive=True)
                for child in children:
                    self._descendants[child.pid] = child.create_time()
                    child.suspend()
                    paused.append(child)
                # Enumerate again after stopping parents; newly observed children
                # must also be stopped before any immutable copy.
                for child in root.children(recursive=True):
                    if child.pid not in {p.pid for p in paused}:
                        self._descendants[child.pid] = child.create_time()
                        child.suspend()
                        paused.append(child)
                if os.name != "nt" and any(p.status() != psutil.STATUS_STOPPED for p in paused):
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                self._require_handle()
                yield
                self._require_handle()
            except psutil.Error:
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None
            finally:
                resume_failed = False
                for process in reversed(paused):
                    try:
                        if process.is_running():
                            process.resume()
                    except psutil.Error:
                        resume_failed = True
                if resume_failed:
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")

    def stop_and_reap(self, *, timeout_seconds=5.0):
        """Terminate only this retained child/tree; keep the OS lock afterward."""
        with self._mutex:
            self._require_handle()
            if type(timeout_seconds) not in {int, float} or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30:
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
            if self._stopped is not None:
                return copy.deepcopy(self._stopped)
            if self._worker is None:
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
            if self._remote_transport is not None:
                try:
                    result = self._remote_transport.stop_remote_and_reap()
                    if (type(result) is not dict or set(result) != {"state", "pid", "process_group", "live_members"}
                            or result.get("state") != "REMOTE_GROUP_STOPPED"
                            or result.get("live_members") != 0 or result.get("pid") != self._worker["pid"]
                            or result.get("process_group") != self._worker["pid"]):
                        raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                    self._process.stdin.close()
                    self._process.wait(timeout=float(timeout_seconds))
                    self._require_handle()
                    self._stopped = {"worker_binding": dict(self._worker), "descendants": [],
                        "stopped_at_ns": time.time_ns(), "returncode": self._process.returncode,
                        "remote_stop": copy.deepcopy(result)}
                    return copy.deepcopy(self._stopped)
                except (TrainingBlocked, psutil.Error):
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None
                except Exception:
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None
            processes = []
            try:
                try:
                    root = psutil.Process(self._worker["pid"])
                    if root.create_time() != self._worker["created_at"]:
                        raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                    for child in root.children(recursive=True):
                        self._descendants[child.pid] = child.create_time()
                    identities = {**self._descendants, root.pid: root.create_time()}
                except psutil.NoSuchProcess:
                    identities = dict(self._descendants)
                for pid, created in identities.items():
                    try:
                        process = psutil.Process(pid)
                        if process.create_time() == created:
                            processes.append(process)
                    except psutil.NoSuchProcess:
                        continue
                for process in processes:
                    process.kill()
                _, alive = psutil.wait_procs(processes, timeout=float(timeout_seconds))
                if alive:
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                self._process.wait(timeout=float(timeout_seconds))
                for pid, created in identities.items():
                    try:
                        process = psutil.Process(pid)
                        if process.create_time() == created and process.is_running():
                            raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                    except psutil.NoSuchProcess:
                        continue
                self._require_handle()
                self._stopped = {"worker_binding": dict(self._worker),
                    "descendants": [{"pid": pid, "created_at": created} for pid, created in sorted(self._descendants.items())],
                    "stopped_at_ns": time.time_ns(), "returncode": self._process.returncode}
                return copy.deepcopy(self._stopped)
            except (psutil.Error, OSError, subprocess.TimeoutExpired):
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED") from None

    def close(self):
        with self._mutex:
            if self._file is None:
                return
            if self._remote_transport is not None and self._process is not None and self._worker is None:
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
            if self._worker is not None:
                self.stop_and_reap()
            if self._channel is not None:
                for stream in self._channel:
                    stream.close()
                self._channel = None
            self._file.close()
            self._file = None

    def replace_stopped_worker(self, argv, *, cwd, log_path, _managed=False):
        with self._mutex:
            self._require_handle()
            if self._stopped is None:
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
            self._last_stop = copy.deepcopy(self._stopped)
            if self._remote_transport is None:
                rows = [self._last_stop["worker_binding"], *self._last_stop["descendants"]]
            else:
                stop = self._last_stop.get("remote_stop")
                if (type(stop) is not dict or stop.get("state") != "REMOTE_GROUP_STOPPED"
                        or stop.get("live_members") != 0):
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                rows = []
            for row in rows:
                try:
                    process = psutil.Process(row["pid"])
                    created = row.get("created_at")
                    if process.is_running() and process.create_time() == created:
                        raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                except psutil.NoSuchProcess:
                    continue
            self._process, self._worker, self._stopped = None, None, None
            self._descendants = {}
            if self._channel is not None:
                for stream in self._channel:
                    try:
                        stream.close()
                    except OSError:
                        pass
            self._channel = self._channel_queue = self._peer = self._load_observation = None
            self._observing_load = False
            self._managed_invoked = False
            self._remote_peer = None
            if self._remote_transport is not None:
                return None
            return self.start(argv, cwd=cwd, log_path=log_path, _managed=_managed)

    def _receive_managed(self, deadline):
        if self._channel_queue is None:
            raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TrainingBlocked("TRAINING_WORKER_DEADLINE_REACHED")
        try:
            value = self._channel_queue.get(timeout=remaining)
        except queue.Empty:
            raise TrainingBlocked("TRAINING_WORKER_DEADLINE_REACHED") from None
        if isinstance(value, BaseException):
            raise value
        return value

    def _launch_remote_managed_training(self):
        transport = self._remote_transport
        if transport is None:
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        required = ("start_stdio", "admit_peer", "require_live", "signal_writer_group",
                    "fetch_checkpoint_bytes", "stop_remote_and_reap")
        if any(not callable(getattr(transport, name, None)) for name in required):
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        try:
            channel = transport.start_stdio()
            if (not isinstance(channel, subprocess.Popen) or channel.poll() is not None
                    or channel.stdin is None or channel.stdout is None):
                raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
            self._process = channel
            self._channel = (channel.stdin, channel.stdout)
            self._channel_queue = queue.Queue(maxsize=4)
            incoming, messages = channel.stdout, self._channel_queue
            def receive():
                try:
                    while True:
                        messages.put(_read_pipe(incoming))
                except BaseException:
                    messages.put(TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST"))
            threading.Thread(target=receive, daemon=True).start()
            hello = self._receive_managed(time.monotonic() + 30)
            if (type(hello) is not dict or set(hello) != {"kind", "pid", "created_at", "source_pins",
                    "process_group_id", "session_id", "proc_start_ticks"}
                    or hello.get("kind") != "owned_training_remote_worker_ready"
                    or hello.get("source_pins") != self._source_pins):
                raise TrainingBlocked("TRAINING_WORKER_SOURCE_MISMATCH")
            observed = transport.admit_peer(hello)
            if (type(observed) is not dict or set(observed) != {"pid", "created_at", "parent_pid",
                    "process_group", "session_id", "proc_start_ticks", "boot_id", "source_root",
                    "source_pins", "state"} or observed.get("pid") != hello.get("pid")
                    or observed.get("created_at") != hello.get("created_at")
                    or observed.get("process_group") != observed.get("pid")
                    or observed.get("session_id") != observed.get("pid")
                    or observed.get("source_pins") != self._source_pins
                    or observed.get("state") != "LIVE"):
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            self._remote_peer = copy.deepcopy(observed)
            self._worker = {"pid": observed["pid"], "created_at": observed["created_at"],
                "lock_sha256": self._lock_sha256}
            self._peer = {"pid": observed["pid"], "created_at": observed["created_at"]}
            self.require_live(self._worker)
            return {"worker_binding": self.worker_binding, "framework_worker": dict(self._peer),
                "source_pins": dict(self._source_pins), "model_loaded": False,
                "remote_peer": copy.deepcopy(observed)}
        except BaseException:
            if self._worker is not None:
                self.stop_and_reap()
            else:
                try:
                    if self._process is not None and self._process.poll() is None:
                        self._process.terminate()
                        self._process.wait(timeout=5)
                except Exception:
                    pass
            raise

    def start_managed_training(self, *, python_executable: Path, cwd: Path,
                               log_path: Path, source_pins: dict, replace=False,
                               remote_transport=None):
        """Start only this source-pinned trainer, holding its private OS pipes.

        The child waits for the existing owner's actual binding before loading
        anything. It receives public material and receipts; no signer or session.
        """
        if (type(python_executable) is not type(Path()) or not python_executable.is_absolute()
                or type(source_pins) is not dict or source_pins != training_worker_source_pins(cwd)
                or type(replace) is not bool
                or remote_transport is not None and any(not callable(getattr(remote_transport, name, None))
                    for name in ("start_stdio", "admit_peer", "require_live", "signal_writer_group",
                        "fetch_checkpoint_bytes", "stop_remote_and_reap"))):
            raise TrainingBlocked("TRAINING_WORKER_SOURCE_MISMATCH")
        _regular_stat(python_executable, directory=False)
        self._source_root, self._source_pins = cwd, dict(source_pins)
        if remote_transport is not None:
            if self._remote_transport is not None and self._remote_transport is not remote_transport:
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            self._remote_transport = remote_transport
        argv = [str(python_executable), "-X", "utf8", "-u", "-m",
            "lumenis.system.ai_gateway.owned_training_runtime", "--managed-training-worker"]
        if self._remote_transport is not None:
            try:
                if replace:
                    self.replace_stopped_worker(argv, cwd=cwd, log_path=log_path, _managed=True)
                elif self._worker is not None or self._process is not None:
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                return self._launch_remote_managed_training()
            except BaseException:
                if self._worker is not None:
                    self.stop_and_reap()
                raise
        try:
            if replace:
                self.replace_stopped_worker(argv, cwd=cwd, log_path=log_path, _managed=True)
            else:
                self.start(argv, cwd=cwd, log_path=log_path, _managed=True)
            hello = self._receive_managed(time.monotonic() + 30)
            if (type(hello) is not dict or set(hello) != {"kind", "pid", "created_at", "source_pins"}
                    or hello["kind"] != "owned_training_worker_ready" or hello["source_pins"] != self._source_pins
                    or type(hello["pid"]) is not int or type(hello["created_at"]) not in {int, float}):
                raise TrainingBlocked("TRAINING_WORKER_SOURCE_MISMATCH")
            root = self.require_live()
            peer = psutil.Process(hello["pid"])
            if (peer.create_time() != hello["created_at"]
                    or peer.pid not in {root.pid, *(p.pid for p in root.children(recursive=True))}):
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            self._peer = {"pid": peer.pid, "created_at": peer.create_time()}
            return {"worker_binding": self.worker_binding, "framework_worker": dict(self._peer),
                    "source_pins": dict(self._source_pins), "model_loaded": False}
        except BaseException:
            if self._worker is not None:
                self.stop_and_reap()
            raise

    def require_completed_training_load(self, *, operation_id, restored_state):
        """Accept only the load currently observed on this retained child pipe."""
        with self._mutex:
            self.require_live()
            observed = self._load_observation
            if (not self._observing_load or observed is None or self._peer is None
                    or observed["operation_id"] != operation_id
                    or canonical_bytes(observed["restored_state"]) != canonical_bytes(restored_state)
                    or observed["worker_binding"] != self.worker_binding
                    or observed["framework_worker"] != self._peer
                    or self._source_pins != training_worker_source_pins(self._source_root)):
                raise TrainingBlocked("CHECKPOINT_ACTUAL_LOAD_NOT_OBSERVED")
            if self._remote_transport is not None:
                if self._remote_peer is None or self._remote_transport.require_live() != self._remote_peer:
                    raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
                return None
            try:
                process = psutil.Process(self._peer["pid"])
                if process.create_time() != self._peer["created_at"] or not process.is_running():
                    raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
            except psutil.Error:
                raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST") from None
            return None

    def invoke_owned_training(self, *, client, phase_transport, invocation, timeout_seconds,
                              remote_input_paths=None):
        with self._mutex:
            if self._invocation_active or self._managed_invoked:
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
            self._invocation_active, self._managed_invoked = True, True
        try:
            return self._invoke_training_bound(client=client, phase_transport=phase_transport,
                invocation=invocation, timeout_seconds=timeout_seconds,
                remote_input_paths=remote_input_paths)
        finally:
            self._invocation_active = False
            if self._worker is not None:
                self.stop_and_reap()

    def _verify_remote_training_inputs(self, client, invocation, remote_input_paths, remote_storage_root):
        transport = self._remote_transport
        verifier = getattr(transport, "verify_training_inputs", None)
        if not callable(verifier):
            raise TrainingBlocked("REMOTE_TRAINING_INPUT_MAPPING_REQUIRED")
        if (type(remote_input_paths) is not dict or set(remote_input_paths) != {
                    "model_snapshot_dir", "train_jsonl_path", "heldout_jsonl_path"}
                or type(client._manifest_path) is not type(Path())):
            raise TrainingBlocked("REMOTE_TRAINING_INPUT_MAPPING_REQUIRED")
        endpoint = getattr(transport, "endpoint", None)
        source_root = getattr(endpoint, "source_root", None)
        if type(source_root) is not str:
            raise TrainingBlocked("REMOTE_TRAINING_INPUT_MAPPING_REQUIRED")
        try:
            admitted_root = PurePosixPath(source_root)
            if not admitted_root.is_absolute() or str(admitted_root) != source_root:
                raise ValueError
            paths = {}
            for key, value in remote_input_paths.items():
                if (type(value) is not str or value.startswith("//") or "\\" in value
                        or any(ord(char) < 32 for char in value)
                        or any(part in {".", ".."} for part in value.split("/"))):
                    raise ValueError
                remote = PurePosixPath(value)
                if not remote.is_absolute() or str(remote) != value or not remote.is_relative_to(admitted_root):
                    raise ValueError
                paths[key] = value
            manifest_remote = admitted_root / "config" / "ai-owned-foundation.json"
            if (len({paths["train_jsonl_path"], paths["heldout_jsonl_path"], str(manifest_remote)}) != 3
                    or any(PurePosixPath(paths[key]).is_relative_to(PurePosixPath(paths["model_snapshot_dir"]))
                        for key in ("train_jsonl_path", "heldout_jsonl_path"))):
                raise ValueError
            if paths["train_jsonl_path"].rsplit("/", 1)[-1] != Path(invocation["train_jsonl_path"]).name:
                raise ValueError
            if paths["heldout_jsonl_path"].rsplit("/", 1)[-1] != Path(invocation["heldout_jsonl_path"]).name:
                raise ValueError
        except (TypeError, ValueError):
            raise TrainingBlocked("REMOTE_TRAINING_INPUT_MAPPING_REQUIRED") from None
        manifest_document = json.loads(client._manifest_path.read_bytes())
        from .owned_training_checkpoints import _file_snapshot
        from .owned_training import NF4_RECIPES, T4_RECIPE
        base_recipe = client.policy.document["base_recipe"]
        model_contract = manifest_document
        variants = manifest_document.get("training_variants")
        if base_recipe in NF4_RECIPES:
            if type(variants) is not dict or type(variants.get(T4_RECIPE)) is not dict:
                raise TrainingBlocked("APPROVED_T4_DERIVATIVE_MANIFEST_INVALID")
            model_contract = variants[T4_RECIPE]
        model_files = model_contract.get("files")
        if (type(model_files) is not dict or len(model_files) != 11
                or model_contract.get("model_id") != client.request.model_id
                or model_contract.get("revision") != client.request.model_revision):
            raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_INVALID")
        model_dir = Path(invocation["model_snapshot_dir"])
        _regular_stat(model_dir, directory=True)
        local_model_files = {entry.name for entry in model_dir.iterdir()}
        if local_model_files != set(model_files):
            raise TrainingBlocked("LOCAL_MODEL_SNAPSHOT_FILE_SET_MISMATCH")
        expected_files = {"model_snapshot_dir": [], "train_jsonl_path": [],
            "heldout_jsonl_path": [], "manifest_path": []}
        for name, pin in sorted(model_files.items()):
            if (type(name) is not str or Path(name).name != name or type(pin) is not dict
                    or set(pin) != {"size_bytes", "sha256"} or type(pin["size_bytes"]) is not int
                    or pin["size_bytes"] <= 0
                    or type(pin["sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) is None):
                raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_INVALID")
            path = model_dir / name
            _regular_stat(path, directory=False)
            size, digest = _file_snapshot(path)
            if size != pin["size_bytes"] or digest != pin["sha256"]:
                raise TrainingBlocked("MODEL_SNAPSHOT_HASH_MISMATCH")
            expected_files["model_snapshot_dir"].append({"path": name, "role": "model",
                "size_bytes": size, "sha256": digest})
        for logical, local, digest in (
                ("train_jsonl_path", Path(invocation["train_jsonl_path"]), client.request.train_sha256),
                ("heldout_jsonl_path", Path(invocation["heldout_jsonl_path"]), client.request.heldout_sha256),
                ("manifest_path", client._manifest_path, client.request.manifest_sha256)):
            _regular_stat(local, directory=False)
            size, actual = _file_snapshot(local)
            if size <= 0 or actual != digest:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
            role = {"train_jsonl_path": "train", "heldout_jsonl_path": "heldout",
                "manifest_path": "manifest"}[logical]
            expected_files[logical] = [{"path": local.name, "role": role,
                "size_bytes": size, "sha256": digest}]
        paths["manifest_path"] = str(manifest_remote)
        paths["output_dir"] = str(remote_storage_root / ("output-" + str(uuid.uuid4())))
        if (manifest_remote.name != Path(invocation["manifest_path"]).name
                or not paths["output_dir"].startswith(str(remote_storage_root).rstrip("/") + "/")):
            raise TrainingBlocked("REMOTE_TRAINING_INPUT_MAPPING_REQUIRED")
        self._fresh_remote_observation()
        try:
            observed = verifier(paths, expected_files)
        except Exception:
            raise TrainingBlocked("REMOTE_TRAINING_INPUTS_UNAVAILABLE") from None
        if (type(observed) is not dict or set(observed) != {"state", "paths", "files", "remote_peer"}
                or observed.get("state") != "PHYSICAL_TRAINING_INPUTS_VERIFIED"
                or observed.get("paths") != paths or observed.get("files") != expected_files
                or observed.get("remote_peer") != self._remote_peer):
            raise TrainingBlocked("REMOTE_TRAINING_INPUTS_UNVERIFIED")
        self._fresh_remote_observation()
        return paths

    def _fresh_remote_observation(self):
        if (self._remote_transport is None or self._remote_peer is None
                or self._remote_transport.require_live() != self._remote_peer):
            raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")

    def _invoke_training_bound(self, *, client, phase_transport, invocation, timeout_seconds,
                               remote_input_paths=None):
        """Run the existing trainer through canonical, fresh owner callables.

        Remote paths are accepted only after the authenticated transport
        independently observes their exact bytes against owner-derived pins.
        All exceptions stop/reap the retained worker; a result is not promotion.
        """
        from dataclasses import asdict
        from .owned_training_phases import TrainingPublicContext
        if (type(client) is not OwnedTrainingCheckpointClient or client.worker is not self
                or not callable(phase_transport) or self._peer is None or type(invocation) is not dict
                or type(timeout_seconds) not in {int, float} or not math.isfinite(timeout_seconds)
                or not 0 < timeout_seconds <= 21600):
            raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        fields = {"model_snapshot_dir", "train_jsonl_path", "heldout_jsonl_path", "output_dir",
            "manifest_path", "resume_request", "stop_after_checkpoint_step"}
        if set(invocation) != fields:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        if invocation["manifest_path"] != str(client._manifest_path):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        for name in ("model_snapshot_dir", "train_jsonl_path", "heldout_jsonl_path", "output_dir", "manifest_path"):
            value = invocation[name]
            if type(value) is not str or not Path(value).is_absolute():
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        for name, expected in (("train_jsonl_path", client.request.train_sha256),
                ("heldout_jsonl_path", client.request.heldout_sha256), ("manifest_path", client.request.manifest_sha256)):
            path = Path(invocation[name])
            _regular_stat(path, directory=False)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
        remote_paths = None
        if self._remote_transport is not None:
            remote_paths = self._verify_remote_training_inputs(client, invocation, remote_input_paths,
                client._remote_storage_root)
        elif remote_input_paths is not None:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        TrainingPublicContext(client.request, client.context, client._fingerprints)
        client._fresh()
        self.require_live()
        if self._source_pins != training_worker_source_pins(self._source_root):
            raise TrainingBlocked("TRAINING_WORKER_SOURCE_MISMATCH")
        public_request = asdict(client.request)
        public_request["scopes"] = list(client.request.scopes)
        worker_invocation = copy.deepcopy(invocation)
        if remote_paths is not None:
            worker_invocation.update(remote_paths)
        body = {"kind": "owned_training_invocation", "invocation": worker_invocation,
            "training_request": public_request, "context": copy.deepcopy(client.context),
            "fingerprints": dict(client._fingerprints), "pinned_public_key": copy.deepcopy(client._pin),
            "source_pins": dict(self._source_pins),
            "prepared_phase_task": None if invocation["resume_request"] is not None else client.initial_phase_context()}
        deadline, sequence = time.monotonic() + timeout_seconds, 1
        try:
            _write_pipe(self._channel[0], body)
            while True:
                message = self._receive_managed(deadline)
                self.require_live()
                if type(message) is not dict or message.get("sequence") != sequence or type(message.get("sequence")) is not int:
                    raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
                if message.get("kind") in {"result", "blocked"}:
                    if set(message) != {"kind", "sequence", "value"}:
                        raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
                    if message["kind"] == "blocked":
                        raise TrainingBlocked(message["value"] if type(message["value"]) is str else "TRAINING_FAILED")
                    return _pipe_decode(message["value"], client._pin)
                if set(message) != {"kind", "sequence", "method", "arguments", "load_observation"} or message["kind"] != "call":
                    raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
                arguments = _pipe_decode(message["arguments"], client._pin)
                method = message["method"]
                if type(arguments) is not dict or type(method) is not str:
                    raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
                if method != "complete_load" and message["load_observation"] is not None:
                    raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
                if method == "approval":
                    if arguments != {"training_request": public_request}:
                        raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
                    client._fresh()
                    result = True
                elif method == "phase":
                    if set(arguments) != {"method", "path", "body"}:
                        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
                    prefix = "/api/experience/owned-training/phase-tasks/" + client.task_id + "/"
                    if type(arguments["path"]) is not str or not arguments["path"].startswith(prefix):
                        raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
                    transport = phase_transport
                    if invocation["resume_request"] is not None:
                        transport = client.recovery_phase_transport(operation_id=invocation["resume_request"]["operation_id"])
                    result = transport(arguments["method"], arguments["path"], arguments["body"])
                elif method in _CHECKPOINT_METHODS:
                    if method == "require_current_admission":
                        if arguments.get("request") != public_request:
                            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
                        arguments["request"] = client.request
                    if method == "complete_load":
                        observation = message["load_observation"]
                        if (type(observation) is not dict
                                or set(observation) != {"components", "framework_worker", "source_pins", "operation_id", "restored_state"}
                                or observation["components"] != ["callback", "model", "optimizer_scheduler", "rng", "scaler"]
                                or observation["framework_worker"] != self._peer or observation["source_pins"] != self._source_pins
                                or observation["operation_id"] != arguments.get("operation_id")
                                or observation["restored_state"] != arguments.get("restored_state")):
                            raise TrainingBlocked("CHECKPOINT_ACTUAL_LOAD_NOT_OBSERVED")
                        self._load_observation = {"operation_id": observation["operation_id"],
                            "restored_state": copy.deepcopy(observation["restored_state"]),
                            "worker_binding": self.worker_binding, "framework_worker": dict(self._peer)}
                        self._observing_load = True
                    try:
                        result = getattr(client, method)(**arguments)
                    finally:
                        self._observing_load = False
                else:
                    raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
                _write_pipe(self._channel[0], {"kind": "reply", "sequence": sequence, "value": _pipe_encode(result)})
                sequence += 1
        finally:
            self._observing_load = False
            self.stop_and_reap()

    def require_previous_worker_stopped(self, binding):
        with self._mutex:
            self._require_handle()
            if self._last_stop is None or self._last_stop["worker_binding"] != binding:
                raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
            if self._remote_transport is not None:
                stop = self._last_stop.get("remote_stop")
                if (type(stop) is not dict or stop.get("state") != "REMOTE_GROUP_STOPPED"
                        or stop.get("pid") != binding.get("pid")
                        or stop.get("process_group") != binding.get("pid")
                        or stop.get("live_members") != 0 or self._remote_peer is None
                        or self._remote_peer.get("pid") == binding.get("pid")):
                    raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                return copy.deepcopy(self._last_stop)
            for row in [binding, *self._last_stop["descendants"]]:
                try:
                    process = psutil.Process(row["pid"])
                    if process.is_running() and process.create_time() == row["created_at"]:
                        raise TrainingBlocked("CHECKPOINT_WORKER_STOP_NOT_CONFIRMED")
                except psutil.NoSuchProcess:
                    continue
            return copy.deepcopy(self._last_stop)


class _TrainingWorkerProxy:
    """Private inherited-pipe client; no public observer registration exists."""

    def __init__(self, incoming, outgoing, *, request, pin, source_pins, source_root):
        self._incoming, self._outgoing = incoming, outgoing
        self._request, self._pin = request, pin
        self._source_pins, self._source_root = source_pins, source_root
        self._sequence = 1
        self._adapter = None

    def _call(self, method, arguments, observation=None):
        _write_pipe(self._outgoing, {"kind": "call", "sequence": self._sequence,
            "method": method, "arguments": _pipe_encode(arguments), "load_observation": observation})
        reply = _read_pipe(self._incoming)
        if (type(reply) is not dict or set(reply) != {"kind", "sequence", "value"}
                or reply["kind"] != "reply" or type(reply["sequence"]) is not int
                or reply["sequence"] != self._sequence):
            raise TrainingBlocked("TRAINING_WORKER_CHANNEL_LOST")
        self._sequence += 1
        return _pipe_decode(reply["value"], self._pin)

    def approval(self, request):
        from dataclasses import asdict
        from .owned_training import TrainingApprovalRequest
        if type(request) is not TrainingApprovalRequest or request != self._request:
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        body = asdict(request)
        body["scopes"] = list(request.scopes)
        return self._call("approval", {"training_request": body}) is True

    def phase(self, method, path, body):
        return self._call("phase", {"method": method, "path": path, "body": body})

    def reserve_save(self, **arguments):
        return self._call("reserve_save", arguments)

    def commit_save(self, **arguments):
        return self._call("commit_save", arguments)

    def read_save(self, **arguments):
        return self._call("read_save", arguments)

    def prepare_resume(self, **arguments):
        return self._call("prepare_resume", arguments)

    def read_resume(self, **arguments):
        return self._call("read_resume", arguments)

    def require_current_admission(self, admission, *, request, operation):
        from dataclasses import asdict
        if request != self._request:
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        body = asdict(request)
        body["scopes"] = list(request.scopes)
        return self._call("require_current_admission", {"admission": admission, "request": body, "operation": operation})

    def complete_load(self, *, operation_id, restored_state):
        """Remeasure real loaded framework objects inside the pinned worker.

        The existing adapter has already checked each actual load hook, callback
        restoration and saved tensors. The supervisor retains this observation
        only for this synchronous completion on its private OS channel.
        """
        from .owned_training_checkpoints import TrainingCheckpointAdapter, strict_json
        adapter = self._adapter
        if (type(adapter) is not TrainingCheckpointAdapter or adapter._trainer is None
                or adapter._operation_id != operation_id or not adapter._load_started
                or adapter._failed or adapter._load_committed
                or adapter._load_components != {"model", "optimizer_scheduler", "scaler", "callback", "rng"}
                or adapter._resume_reservation is None
                or self._source_pins != training_worker_source_pins(self._source_root)):
            raise TrainingBlocked("CHECKPOINT_ACTUAL_LOAD_NOT_OBSERVED")
        trainer = adapter._trainer
        packages, _ = adapter._validate_runtime(trainer)
        position = adapter._cursor.snapshot()
        if (type(trainer.state.global_step) is not int
                or trainer.state.global_step != adapter._resume_reservation["completed_step"]
                or trainer.state.global_step != position["data_position"]["completed_step"]):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        callbacks = strict_json((adapter._selected_checkpoint() / "lumenis_callback_state.json").read_bytes())
        if canonical_bytes(callbacks) != canonical_bytes(trainer.state.stateful_callbacks):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        measured = adapter._observe_state(trainer, position, packages)
        if (canonical_bytes(measured) != canonical_bytes(restored_state)
                or canonical_bytes(measured) != canonical_bytes(adapter._expected_restored_state)):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        process = psutil.Process(os.getpid())
        observation = {"components": sorted(adapter._load_components),
            "framework_worker": {"pid": process.pid, "created_at": process.create_time()},
            "source_pins": self._source_pins, "operation_id": operation_id, "restored_state": measured}
        return self._call("complete_load", {"operation_id": operation_id, "restored_state": measured}, observation)


def _managed_training_worker(*, remote=False):
    """The sole managed entry invokes the existing trainer, never a new model."""
    from .owned_training import TrainingApprovalRequest, TrainingResumeRequest, run_owned_lora_training
    from .owned_training_checkpoints import TrainingCheckpointAdapter
    from .owned_training_phases import TrainingPhaseClient, TrainingPublicContext
    from lumenis.system.security import training_receipts
    # Keep one private protocol fd; library/CUDA writes on stdout go to the
    # owner-selected log, not the protocol. No log is used as an observation.
    outgoing = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
    incoming = sys.stdin.buffer
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    root = Path(__file__).resolve().parents[3]
    process = psutil.Process(os.getpid())
    source_pins = training_worker_source_pins(root)
    hello = {"kind": "owned_training_worker_ready", "pid": process.pid,
        "created_at": process.create_time(), "source_pins": source_pins}
    if remote:
        incoming = _RemoteTrainingInput(incoming)
        # Field22 of /proc/stat follows the parenthesized comm field. Keep
        # the monotonic kernel creation identity independent of wall time.
        fields = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()
        hello.update(kind="owned_training_remote_worker_ready", process_group_id=os.getpgid(0),
            session_id=os.getsid(0), proc_start_ticks=int(fields[19]))
    _write_pipe(outgoing, hello)
    proxy = None
    try:
        body = _read_pipe(incoming)
        if (type(body) is not dict
                or set(body) != {"kind", "invocation", "training_request", "context", "fingerprints", "pinned_public_key", "source_pins", "prepared_phase_task"}
                or body["kind"] != "owned_training_invocation" or body["source_pins"] != source_pins):
            raise TrainingBlocked("TRAINING_WORKER_SOURCE_MISMATCH")
        request_body = dict(body["training_request"])
        if type(request_body.get("scopes")) is not list:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        request_body["scopes"] = tuple(request_body["scopes"])
        request = TrainingApprovalRequest(**request_body)
        public_context = TrainingPublicContext(request, body["context"], body["fingerprints"])
        training_receipts._validate_pinned_public_key(body["pinned_public_key"])
        invocation = body["invocation"]
        fields = {"model_snapshot_dir", "train_jsonl_path", "heldout_jsonl_path", "output_dir",
            "manifest_path", "resume_request", "stop_after_checkpoint_step"}
        if type(invocation) is not dict or set(invocation) != fields:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        proxy = _TrainingWorkerProxy(incoming, outgoing, request=request, pin=body["pinned_public_key"],
            source_pins=source_pins, source_root=root)
        if proxy.approval(request) is not True:
            raise TrainingBlocked("TRAINING_APPROVAL_REQUIRED")
        adapter = TrainingCheckpointAdapter(request, body["context"], manifest_path=Path(invocation["manifest_path"]),
            client=proxy, pinned_public_key=body["pinned_public_key"], public_context=public_context)
        proxy._adapter = adapter
        resume = None if invocation["resume_request"] is None else TrainingResumeRequest(**invocation["resume_request"])
        phase = None if resume is not None else TrainingPhaseClient.from_prepared_task(request, body["context"],
            prepared_task=body["prepared_phase_task"], pinned_public_key=body["pinned_public_key"],
            transport=proxy.phase, public_context=public_context)
        result = run_owned_lora_training(invocation["model_snapshot_dir"], invocation["train_jsonl_path"],
            invocation["heldout_jsonl_path"], invocation["output_dir"], manifest_path=invocation["manifest_path"],
            execute=True, approval_verifier=proxy.approval, recipe=request.recipe, phase_client=phase,
            checkpoint_adapter=adapter, resume_request=resume,
            recovery_phase_transport=None if resume is None else proxy.phase,
            stop_after_checkpoint_step=invocation["stop_after_checkpoint_step"])
        _write_pipe(outgoing, {"kind": "result", "sequence": proxy._sequence, "value": _pipe_encode(result)})
    except BaseException as exc:
        code = str(exc) if isinstance(exc, TrainingBlocked) else "TRAINING_FAILED"
        _write_pipe(outgoing, {"kind": "blocked", "sequence": 1 if proxy is None else proxy._sequence, "value": code})
    # Retain the actual child until the owner observes and reaps it. Successful
    # return/exit is never a substitute for its framework/Artifact receipts.
    try:
        if remote:
            incoming.wait_closed()
        else:
            incoming.read(1)
    finally:
        outgoing.close()


class OwnedTrainingCheckpointClient:
    """Bound server composition for the frozen seven-method trainer interface.

    Construction checks the real canonical owners. Missing Shared/Permission/
    Effect Fence bindings stop before filesystem IO; dependency injection of an
    arbitrary signer or a truthy approval callback is not supported.
    """

    def __init__(self, request, context, *, task_id, worker, manifest_path,
                 staging_root, max_bytes, actor_id=None, principal=None,
                 remote_storage_root: PurePosixPath | None = None):
        import shared_artifacts
        from ai_task_engine import get_task_engine
        from lumenis.system.security import permission as p, effect_fence as f, training_receipts as r
        from .owned_training import TrainingApprovalRequest
        from .owned_training_checkpoints import load_recovery_policy
        if type(request) is not TrainingApprovalRequest or type(worker) is not TrainingProcessFence:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        gate, fence = p.get_permission_gate(), f.get_effect_fence()
        if (type(gate) is not p.PermissionGate or not gate.fail_closed or p.is_testing_bypass_enabled()
                or type(fence) is not f.EffectFence):
            raise TrainingBlocked("CHECKPOINT_PERMISSION_REVOKED")
        required = ("stage_training_checkpoint_artifact", "register_training_checkpoint_artifact",
                    "read_training_checkpoint_artifact")
        if (any(not callable(getattr(shared_artifacts, name, None)) for name in required)
                or not callable(getattr(gate, "require_current_training_checkpoint_admission", None))
                or not callable(getattr(fence, "authorize_training_checkpoint_metadata", None))):
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        if (type(staging_root) is not type(Path()) or not staging_root.is_absolute()
                or type(max_bytes) is not int or not 1 <= max_bytes <= 1024**4):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        for parent in [*reversed(staging_root.parents), staging_root]:
            _regular_stat(parent, directory=True)
        self.request, self.context = request, copy.deepcopy(context)
        self.task_id, self.worker = task_id, worker
        self._manifest_path = Path(manifest_path).resolve(strict=True)
        self.policy = load_recovery_policy(request.recipe, manifest_path)
        self._identity_args = {"actor_id": actor_id} if actor_id is not None else {"principal": principal}
        self._gate, self._fence, self._engine, self._artifact = gate, fence, get_task_engine(), shared_artifacts
        try:
            staging_root.relative_to(shared_artifacts.artifact_root())
        except ValueError as exc:
            raise TrainingBlocked("CHECKPOINT_STORAGE_OUTSIDE_OWNER_ROOT") from exc
        self._staging_root, self._max_bytes = staging_root, max_bytes
        self._remote_storage_root = None
        if worker._remote_transport is not None:
            endpoint = getattr(worker._remote_transport, "endpoint", None)
            source_root = getattr(endpoint, "source_root", None)
            if (type(remote_storage_root) is not PurePosixPath or type(source_root) is not str
                    or not remote_storage_root.is_absolute()
                    or str(remote_storage_root).startswith("//")
                    or any(part in {".", ".."} for part in str(remote_storage_root).split("/"))
                    or "\\" in str(remote_storage_root)
                    or any(ord(char) < 32 for char in str(remote_storage_root))):
                raise TrainingBlocked("REMOTE_CHECKPOINT_STORAGE_ROOT_REQUIRED")
            admitted_root = PurePosixPath(source_root)
            if (not admitted_root.is_absolute() or str(admitted_root) != source_root
                    or admitted_root.parent == PurePosixPath("/")
                    or not remote_storage_root.is_relative_to(admitted_root.parent)
                    or remote_storage_root == admitted_root.parent
                    or remote_storage_root.is_relative_to(admitted_root)
                    or admitted_root.is_relative_to(remote_storage_root)
                    or worker._remote_peer is None
                    or worker._remote_peer.get("source_root") != source_root):
                raise TrainingBlocked("REMOTE_CHECKPOINT_STORAGE_ROOT_INVALID")
            worker.require_live(worker.worker_binding)
            self._remote_storage_root = remote_storage_root
        elif remote_storage_root is not None:
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        self._remote_local_stage_roots = {}
        self._mutex = threading.RLock()
        self._pin = r.get_training_receipt_public_key()
        self._fingerprints = p.owned_training_phase_fingerprints(request, context=context,
            domain_id=request.domain_id, **self._identity_args)
        identity = p.owned_training_identity(**self._identity_args)
        self._binding = {"resource": p.owned_training_approval_resource(request, context=context,
            domain_id=request.domain_id, **self._identity_args),
            "identity": {key: identity[key] for key in ("actor_id", "caller", "principal_kind", "principal_ref")},
            "scope_descriptors": copy.deepcopy(context["scope_descriptors"])}
        self._verifier = p.make_owned_training_approval_verifier(gate, context=context,
            domain_id=request.domain_id, **self._identity_args)
        _, self._reference = self._fresh()

    def _fresh(self):
        from lumenis.system.security import permission as p
        if self._verifier(self.request) is not True:
            raise TrainingBlocked("CHECKPOINT_PERMISSION_REVOKED")
        identity = p.owned_training_identity(**self._identity_args)
        if {key: identity[key] for key in self._binding["identity"]} != self._binding["identity"]:
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        approval = self._gate.check(p.OperationType.MODEL_TRAIN, resource=self._binding["resource"],
            caller=identity["caller"], domain_id=self.request.domain_id, exact_approval_required=True)
        if type(approval) is not p.PermissionResult or approval.allowed is not True or approval.requires_approval is not True:
            raise TrainingBlocked("CHECKPOINT_PERMISSION_REVOKED")
        reference = self._gate.owned_training_approval_reference(training_request=self.request,
            context=self.context, domain_id=self.request.domain_id, approval=approval, **self._identity_args)
        if hasattr(self, "_reference") and reference != self._reference:
            raise TrainingBlocked("CHECKPOINT_PERMISSION_REVOKED")
        return approval, reference

    def _args(self, connection):
        return dict(expected_binding=self._binding, expected_approval_reference=self._reference,
                    pinned_public_key=self._pin, connection=connection)

    def _mutate(self, mutation, action, *, operation_id=None):
        from lumenis.shared.database import get_repository
        with self._mutex:
            self._fresh()
            self.worker.require_live()
            with get_repository().connection(timeout=30) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    result = action(conn)
                    execution = self._engine.training_execution_read(self.task_id, **self._args(conn))
                    operation = None if operation_id is None else self._engine.training_operation_read(
                        self.task_id, operation_id=operation_id, **self._args(conn))
                    expected_state = {"execution": execution, "operation": operation}
                    approval, reference = self._fresh()
                    self.worker.require_live(execution["worker_binding"])
                    decision = self._fence.authorize_training_checkpoint_metadata(connection=conn,
                        task_id=self.task_id, mutation=mutation, training_request=self.request,
                        context=self.context, domain_id=self.request.domain_id, gate=self._gate,
                        approval=approval, approval_reference=reference, expected_state=expected_state,
                        capture_mode="owned_training_checkpoint_metadata", **self._identity_args)
                    from lumenis.system.security.effect_fence import TrainingPhaseMetadataFenceDecision
                    if (type(decision) is not TrainingPhaseMetadataFenceDecision
                            or decision.allowed is not True
                            or getattr(decision, "effect_mode", None) != "owned_training_checkpoint_metadata"
                            or getattr(decision, "task_id", None) != self.task_id
                            or getattr(decision, "mutation", None) != mutation
                            or getattr(decision, "model_execution_allowed", None) is not False
                            or getattr(decision, "resource", None) != self._binding["resource"]
                            or not getattr(decision, "fence_audit_id", None)):
                        raise TrainingBlocked("CHECKPOINT_PERMISSION_REVOKED")
                    with self._gate.owned_training_phase_commit_lease(training_request=self.request,
                        context=self.context, domain_id=self.request.domain_id, approval=approval,
                        connection=conn, expected_approval_reference=reference, **self._identity_args):
                        self.worker.require_live(execution["worker_binding"])
                        conn.commit()
                    return result
                except BaseException:
                    conn.rollback()
                    raise

    def _authorize_storage(self, *, connection=None, operation_id=None, expected_state=None):
        """Fresh exact Task/Permission/worker check; None is storage admission."""
        from lumenis.shared.database import get_repository
        if connection is None:
            with get_repository().connection(timeout=30) as conn:
                conn.execute("BEGIN")
                try:
                    self._authorize_storage(connection=conn, operation_id=operation_id,
                        expected_state=expected_state)
                finally:
                    conn.rollback()
            return None
        self._fresh()
        self.worker.require_live()
        material = self._engine.get_training_receipt_history_material(self.task_id,
            expected_identity=self._binding["identity"], connection=connection)
        if (material["binding"] != self._binding or material["approval_reference"] != self._reference
                or material["fingerprints"] != self._fingerprints):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        if operation_id is not None:
            current = self._engine.training_operation_read(self.task_id,
                operation_id=operation_id, **self._args(connection))
            if current is None or current["state"] != expected_state:
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        return None

    def initialize(self):
        return self._mutate("reserve", lambda conn: self._engine.training_execution_initialize(
            self.task_id, worker_binding=self.worker.worker_binding, policy_sha256=self.policy.sha256,
            byte_limit=self._max_bytes, **self._args(conn)))

    def initial_phase_context(self):
        """Read the one actual sealed Task before its first physical invocation."""
        from lumenis.shared.database import get_repository
        self._fresh()
        self.worker.require_live()
        with get_repository().connection(timeout=30) as conn:
            conn.execute("BEGIN")
            try:
                state = self._engine.require_training_receipt_admission(self.task_id,
                    self._binding, self._reference, self._pin, conn)
                execution = self._engine.training_execution_read(self.task_id, **self._args(conn))
                if (execution is None or execution["worker_binding"] != self.worker.worker_binding
                        or execution["worker_epoch"] != 1 or execution["run_digest"] != state["run_digest"]
                        or execution["state"] != "RUNNABLE" or state["next_sequence"] != 1
                        or state["last_phase"] is not None or state["terminal"] is not False
                        or state["status"] != "ready"):
                    raise TrainingBlocked("TRAINING_PHYSICAL_RECOVERY_REQUIRED")
                self._fresh()
                self.worker.require_live(execution["worker_binding"])
                return {"ok": True, "state": "PHASE_TASK_PREPARED", "task_id": self.task_id,
                    "public_challenge_context": {key: value for key, value in state.items() if key != "task_id"},
                    "pinned_public_key": copy.deepcopy(self._pin), "training_started": False, "approval_issued": False}
            finally:
                conn.rollback()

    def _read(self, operation_id):
        from lumenis.shared.database import get_repository
        self._fresh()
        self.worker.require_live()
        with get_repository().connection(timeout=30) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                result = self._engine.training_operation_read(self.task_id, operation_id=operation_id, **self._args(conn))
                self._fresh()
                return result
            finally:
                conn.rollback()

    @staticmethod
    def _admission_value(reservation, *, operation, reservation_digest):
        return {"operation_id": reservation["operation_id"], "task_digest": reservation["task_digest"],
            "run_digest": reservation["origin_run_digest" if operation == "save" else "run_digest"],
            "attempt_id": reservation["attempt_id"], "worker_epoch": reservation["worker_epoch"],
            "operation": operation, "completed_step": reservation["completed_step"],
            "checkpoint_ref": None if operation == "save" else reservation["checkpoint_ref"],
            "checkpoint_sha256": None if operation == "save" else reservation["checkpoint_sha256"],
            "policy_sha256": reservation["policy_sha256"], "fingerprints": reservation["fingerprints"],
            "reservation_digest": reservation_digest}

    def _allocate_remote_checkpoint_root(self, operation_id, remote_root, *, expected_state):
        transport = self.worker._remote_transport
        allocate = getattr(transport, "allocate_empty_checkpoint_root", None)
        if not callable(allocate):
            raise TrainingBlocked("REMOTE_CHECKPOINT_ROOT_ALLOCATION_REQUIRED")
        authorize = lambda: self._authorize_storage(operation_id=operation_id, expected_state=expected_state)
        try:
            observed = allocate(remote_root=str(remote_root), authorize=authorize)
        except Exception:
            raise TrainingBlocked("REMOTE_CHECKPOINT_ROOT_ALLOCATION_FAILED") from None
        if (type(observed) is not dict
                or set(observed) != {"state", "remote_root", "remote_peer"}
                or observed.get("state") != "REMOTE_CHECKPOINT_ROOT_ALLOCATED"
                or observed.get("remote_root") != str(remote_root)
                or observed.get("remote_peer") != self.worker._remote_peer):
            raise TrainingBlocked("REMOTE_CHECKPOINT_ROOT_UNVERIFIED")
        self.worker.require_live()

    def reserve_save(self, *, operation_id, completed_step, parent_ref):
        from lumenis.system.security import training_receipts as r
        r._checkpoint_uuid(operation_id)
        r._checkpoint_integer(completed_step, 1)
        r._checkpoint_ref(parent_ref, nullable=True)
        normalized = {"completed_step": completed_step, "parent_ref": parent_ref}

        def prepare(conn):
            state = self._engine.training_execution_read(self.task_id, **self._args(conn))
            if state["state"] != "RUNNABLE" or completed_step % self.policy.document["checkpoint_interval_steps"]:
                raise TrainingBlocked("CHECKPOINT_REPLAY_NOT_AUTHORIZED")
            latest = self._engine.training_checkpoint_latest_receipt(self.task_id, **self._args(conn))
            if parent_ref != (None if latest is None else latest["artifact_ref"]):
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
            if latest is not None and completed_step <= latest["completed_step"]:
                raise TrainingBlocked("CHECKPOINT_REPLAY_NOT_AUTHORIZED")
            prior = self._engine.training_operation_read(self.task_id, operation_id=operation_id, **self._args(conn))
            if prior is not None:
                if prior["input"] != normalized:
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                if prior["state"] != "RESERVED":
                    raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
                return prior["result"]
            local_root = self._staging_root / operation_id
            if self._remote_storage_root is None:
                local_root.mkdir(mode=0o700)
                staging_root = str(local_root)
            else:
                if local_root.exists():
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                staging_root = str(self._remote_storage_root / operation_id)
            deadline = datetime.now(timezone.utc) + timedelta(seconds=300)
            reservation = {"schema_version": 1, "operation_id": operation_id,
                "task_digest": state["task_digest"], "origin_run_digest": state["run_digest"],
                "attempt_id": state["attempt_id"], "worker_epoch": state["worker_epoch"],
                "completed_step": completed_step, "parent_ref": parent_ref, "policy_sha256": self.policy.sha256,
                "fingerprints": self._fingerprints, "staging_root": staging_root,
                "checkpoint_relative_path": f"checkpoint-{completed_step}", "write_deadline_utc": deadline.isoformat()}
            binding = {"task_id": self.task_id, "domain_id": self.request.domain_id,
                "task_digest": state["task_digest"], "operation_id": operation_id,
                "attempt_id": state["attempt_id"], "worker_epoch": state["worker_epoch"],
                "actor_identity": self._binding["identity"], "scope_descriptors": self._binding["scope_descriptors"],
                "artifact_version": 1 if latest is None else latest["artifact_version"] + 1,
                "parent_ref": parent_ref}
            private_binding = {"reservation": reservation, "artifact_binding": binding,
                "max_bytes": self._max_bytes, "worker_binding": state["worker_binding"]}
            envelope = r.sign_training_checkpoint_payload(self._admission_value(reservation,
                operation="save", reservation_digest=hashlib.sha256(canonical_bytes(private_binding)).hexdigest()),
                receipt_kind="owned_training_checkpoint_admission")
            result = {"reservation": reservation, "admission": envelope, "binding": binding}
            self._engine.training_operation_prepare(self.task_id, operation_id=operation_id, kind="save",
                normalized_input=normalized, result=result, **self._args(conn))
            return result
        result = self._mutate("reserve", prepare, operation_id=operation_id)
        reservation = copy.deepcopy(result["reservation"])
        if self._remote_storage_root is None:
            reservation["staging_root"] = Path(reservation["staging_root"])
        else:
            remote_root = PurePosixPath(reservation["staging_root"])
            expected_remote_root = self._remote_storage_root / operation_id
            local_root = self._staging_root / operation_id
            if remote_root != expected_remote_root or local_root.exists():
                raise TrainingBlocked("REMOTE_CHECKPOINT_ROOT_UNVERIFIED")
            self._remote_local_stage_roots[operation_id] = local_root
            self._allocate_remote_checkpoint_root(operation_id, remote_root, expected_state="RESERVED")
            reservation["staging_root"] = remote_root
        reservation["admission_receipt"] = r.verify_training_checkpoint_admission(result["admission"],
            expected_payload=result["admission"]["payload"], pinned_public_key=self._pin)
        return reservation

    def require_current_admission(self, admission, *, request, operation):
        if request != self.request or type(request) is not type(self.request):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")

        def begin(conn):
            approval, _ = self._fresh()
            record = self._engine.training_require_current_checkpoint_admission(self.task_id, admission=admission,
                operation=operation, expected_fingerprints=self._fingerprints,
                worker_binding=self.worker.worker_binding, **self._args(conn))
            self._gate.require_current_training_checkpoint_admission(training_request=self.request,
                context=self.context, domain_id=self.request.domain_id, approval=approval,
                approval_reference=self._reference, engine=self._engine, task_id=self.task_id,
                admission=admission, operation=operation, worker=self.worker, connection=conn,
                pinned_public_key=self._pin, **self._identity_args)
            result = copy.deepcopy(record["result"])
            result["started_at_utc"] = datetime.now(timezone.utc).isoformat()
            self._engine.training_operation_transition(self.task_id, operation_id=record["operation_id"],
                before_state=record["state"], state="WRITING" if operation == "save" else "LOADING",
                result=result, **self._args(conn))
        self._mutate("start", begin, operation_id=admission.envelope["payload"]["operation_id"])

    def read_save(self, *, operation_id):
        record = self._read(operation_id)
        if record is None:
            return {"state": "NOT_FOUND"}
        if record["kind"] != "save":
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        if record["state"] == "COMMITTED":
            return {"state": "COMMITTED", "receipt": copy.deepcopy(record["result"])}
        return {"state": "FAILED" if record["state"] in {"FAILED", "INTERRUPTED"} else "PENDING"}

    def commit_save(self, *, operation_id, inventory):
        from lumenis.system.security import training_receipts as r
        from .owned_training_checkpoints import inspect_checkpoint_files, _utc_time
        record = self._read(operation_id)
        if record is None or record["kind"] != "save":
            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
        if record["state"] == "COMMITTED":
            if record["result"]["inventory_sha256"] != hashlib.sha256(canonical_bytes(inventory)).hexdigest():
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
            return copy.deepcopy(record["result"])
        if record["state"] != "WRITING":
            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
        reservation = record["result"]["reservation"]
        if _utc_time(reservation["write_deadline_utc"]) <= datetime.now(timezone.utc):
            self.worker.stop_and_reap()
            raise TrainingBlocked("CHECKPOINT_WRITE_EXPIRED")
        expected = {"schema_version": 1, "operation_id": operation_id,
            "completed_step": reservation["completed_step"],
            "checkpoint_relative_path": reservation["checkpoint_relative_path"],
            "policy_sha256": self.policy.sha256, "fingerprints": self._fingerprints,
            "trainer_config_sha256": self.policy.document["trainer_config_sha256"],
            "data_order_sha256": self.policy.document["data_order_sha256"]}
        if (type(inventory) is not dict or set(inventory) != {*expected, "framework_versions", "data_position", "files"}
                or any(type(inventory.get(k)) is not type(v) or inventory[k] != v for k, v in expected.items())
                or hashlib.sha256(canonical_bytes(inventory["framework_versions"])).hexdigest()
                    != self.policy.document["framework_lock_sha256"]):
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        r._checkpoint_position(inventory["data_position"])
        if (inventory["data_position"]["completed_step"] != reservation["completed_step"]
                or inventory["data_position"]["dataset_sha256"] != self.request.train_sha256):
            raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
        remote_root = None
        if self._remote_storage_root is None:
            root = Path(reservation["staging_root"])
        else:
            remote_root = PurePosixPath(reservation["staging_root"])
            if remote_root != self._remote_storage_root / operation_id:
                raise TrainingBlocked("REMOTE_CHECKPOINT_ROOT_UNVERIFIED")
            root = self._remote_local_stage_roots.get(operation_id, self._staging_root / operation_id)
        with self.worker.exclude_writer(self.worker.worker_binding):
            self._fresh()
            if remote_root is not None:
                if root.exists():
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                fetch = getattr(self.worker._remote_transport, "fetch_checkpoint_bytes", None)
                if not callable(fetch):
                    raise TrainingBlocked("REMOTE_CHECKPOINT_FETCH_NOT_BOUND")
                try:
                    copied = fetch(remote_root=str(remote_root), local_root=root,
                        files=inventory["files"], max_bytes=self._max_bytes,
                        authorize=lambda: self._authorize_storage(operation_id=operation_id,
                            expected_state="WRITING"))
                except Exception:
                    raise TrainingBlocked("CHECKPOINT_BYTES_NOT_VERIFIED") from None
                expected_size = sum(item["size_bytes"] for item in inventory["files"])
                if (type(copied) is not dict
                        or set(copied) != {"state", "source_root", "files", "total_bytes", "remote_peer"}
                        or copied.get("state") != "PHYSICAL_CHECKPOINT_BYTES_VERIFIED"
                        or copied.get("source_root") != str(root)
                        or copied.get("files") != inventory["files"]
                        or copied.get("total_bytes") != expected_size
                        or copied.get("remote_peer") != self.worker._remote_peer):
                    raise TrainingBlocked("CHECKPOINT_BYTES_NOT_VERIFIED")
                self.worker.require_live()
            if inventory["files"] != inspect_checkpoint_files(root, reservation["checkpoint_relative_path"], self.policy):
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
            staged = self._artifact.stage_training_checkpoint_artifact(source_root=root, inventory=inventory,
                binding=record["result"]["binding"], max_bytes=self._max_bytes,
                authorize=lambda: self._authorize_storage(operation_id=operation_id, expected_state="WRITING"))

            def commit(conn):
                current = self._engine.training_operation_read(self.task_id, operation_id=operation_id, **self._args(conn))
                if current != record:
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                artifact = self._artifact.register_training_checkpoint_artifact(connection=conn, staged=staged,
                                                                              authorize=lambda: self._authorize_storage(connection=conn, operation_id=operation_id, expected_state="WRITING"))
                receipt = {key: reservation[key] for key in ("schema_version", "operation_id", "task_digest",
                    "origin_run_digest", "attempt_id", "worker_epoch", "fingerprints", "policy_sha256",
                    "completed_step", "parent_ref")}
                latest = self._engine.training_checkpoint_latest_receipt(self.task_id, **self._args(conn))
                if reservation["parent_ref"] != (None if latest is None else latest["artifact_ref"]):
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                receipt.update(artifact_ref=artifact["artifact_ref"], artifact_version=1 if latest is None else latest["artifact_version"] + 1,
                    inventory_sha256=hashlib.sha256(canonical_bytes(inventory)).hexdigest(),
                    artifact_sha256=artifact["sha256"], storage_identity=artifact["storage_identity"],
                    committed_at_utc=datetime.now(timezone.utc).isoformat(),
                    task_step_ref="trainop_" + hashlib.sha256((self.task_id + operation_id).encode()).hexdigest())
                envelope = r.sign_training_checkpoint_payload(receipt, receipt_kind="owned_training_checkpoint_committed")
                r.verify_training_checkpoint_receipt(envelope, expected_payload=receipt, pinned_public_key=self._pin)
                receipt["receipt"] = envelope
                self._engine.training_operation_transition(self.task_id, operation_id=operation_id,
                    before_state="WRITING", state="COMMITTED", result=receipt, **self._args(conn))
                return receipt
            return self._mutate("commit", commit, operation_id=operation_id)

    def prepare_resume(self, *, operation_id, checkpoint_ref, expected_checkpoint_sha256, replay_through_step):
        from lumenis.system.security import training_receipts as r
        from .owned_training_checkpoints import inspect_checkpoint_files, strict_json, _file_snapshot
        r._checkpoint_uuid(operation_id)
        r._checkpoint_ref(checkpoint_ref)
        r._checkpoint_hash(expected_checkpoint_sha256)
        r._checkpoint_integer(replay_through_step)
        normalized = {"checkpoint_ref": checkpoint_ref, "expected_checkpoint_sha256": expected_checkpoint_sha256,
                      "replay_through_step": replay_through_step}
        transfer_spec = {}

        def prepare(conn):
            prior = self._engine.training_operation_read(self.task_id, operation_id=operation_id, **self._args(conn))
            if prior is not None and (prior["kind"] != "load" or prior["input"] != normalized):
                raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
            if prior is not None and prior["state"] != "LOAD_ADMITTED":
                raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
            saved = self._engine.training_checkpoint_receipt_for_artifact(self.task_id,
                artifact_ref=checkpoint_ref, **self._args(conn))
            if saved is None or saved["artifact_sha256"] != expected_checkpoint_sha256:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
            if not saved["completed_step"] <= replay_through_step <= saved["completed_step"] + self.policy.document["max_replay_optimizer_steps"]:
                raise TrainingBlocked("CHECKPOINT_REPLAY_NOT_AUTHORIZED")
            artifact = self._artifact.read_training_checkpoint_artifact(connection=conn, artifact_ref=checkpoint_ref,
                expected_sha256=expected_checkpoint_sha256, authorize=lambda: self._authorize_storage(connection=conn))
            root, manifest = artifact["load_root"], artifact["manifest"]
            inventory = manifest["inventory"]
            binding = manifest["binding"]
            checkpoint_relative_path = inventory["checkpoint_relative_path"]
            if (type(root) is not type(Path()) or inventory["policy_sha256"] != self.policy.sha256
                    or inventory["fingerprints"] != self._fingerprints
                    or binding["task_id"] != self.task_id or binding["domain_id"] != self.request.domain_id
                    or binding["task_digest"] != saved["task_digest"]
                    or binding["actor_identity"] != self._binding["identity"]
                    or binding["scope_descriptors"] != self._binding["scope_descriptors"]
                    or binding["operation_id"] != saved["operation_id"]
                    or binding["artifact_version"] != saved["artifact_version"]
                    or inventory["files"] != [item for item in inspect_checkpoint_files(root, checkpoint_relative_path, self.policy)
                        if item["path"] != "checkpoint.manifest.json"]):
                raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
            observed_path = root / checkpoint_relative_path / "lumenis_observed_state.json"
            measured_size, measured_hash = _file_snapshot(observed_path)
            observed_raw = observed_path.read_bytes()
            if len(observed_raw) != measured_size or hashlib.sha256(observed_raw).hexdigest() != measured_hash:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
            observed_state = strict_json(observed_raw)
            state = self._engine.training_execution_read(self.task_id, **self._args(conn))
            if prior is None:
                stopped = self.worker.require_previous_worker_stopped(state["worker_binding"])
                stop_ref = "trainstop_" + hashlib.sha256(canonical_bytes(stopped)).hexdigest()
                state = self._engine.training_execution_register_resume(self.task_id,
                    previous_worker_binding=state["worker_binding"], worker_binding=self.worker.worker_binding,
                    worker_stop_receipt_ref=stop_ref, **self._args(conn))
                load_root = (self._remote_storage_root / operation_id if self._remote_storage_root is not None else root)
                reservation = {"schema_version": 1, "operation_id": operation_id, "task_digest": state["task_digest"],
                    "checkpoint_ref": checkpoint_ref, "checkpoint_sha256": expected_checkpoint_sha256,
                    "source_run_digest": saved["origin_run_digest"], "run_digest": state["run_digest"],
                    "attempt_id": state["attempt_id"], "worker_epoch": state["worker_epoch"],
                    "completed_step": saved["completed_step"], "replay_through_step": replay_through_step,
                    "policy_sha256": self.policy.sha256, "fingerprints": self._fingerprints,
                    "load_root": str(load_root), "checkpoint_relative_path": checkpoint_relative_path,
                    "worker_stop_receipt_ref": stop_ref}
                reservation_hash = hashlib.sha256(canonical_bytes({"reservation": reservation,
                    "worker_binding": state["worker_binding"], "max_bytes": self._max_bytes})).hexdigest()
            else:
                if state["state"] != "LOAD_ADMITTED" or state["worker_binding"] != self.worker.worker_binding:
                    raise TrainingBlocked("CHECKPOINT_WORKER_FENCE_LOST")
                reservation = prior["result"]["reservation"]
                expected_load_root = (str(self._remote_storage_root / operation_id)
                    if self._remote_storage_root is not None else str(root))
                if reservation["load_root"] != expected_load_root:
                    raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
                reservation_hash = prior["result"]["admission"]["payload"]["reservation_digest"]
            transfer_spec.update(local_root=root, files=copy.deepcopy(inventory["files"]))
            envelope = r.sign_training_checkpoint_payload(self._admission_value(reservation,
                operation="load", reservation_digest=reservation_hash), receipt_kind="owned_training_checkpoint_admission")
            result = {"reservation": reservation, "admission": envelope,
                      "expected_observed_state": observed_state}
            if prior is None:
                self._engine.training_operation_prepare(self.task_id, operation_id=operation_id, kind="load",
                    normalized_input=normalized, result=result, **self._args(conn))
            else:
                self._engine.training_operation_transition(self.task_id, operation_id=operation_id,
                    before_state="LOAD_ADMITTED", state="LOAD_ADMITTED", result=result, **self._args(conn))
            return result
        result = self._mutate("reserve", prepare, operation_id=operation_id)
        reservation = copy.deepcopy(result["reservation"])
        if self._remote_storage_root is None:
            reservation["load_root"] = Path(reservation["load_root"])
        else:
            remote_root = PurePosixPath(reservation["load_root"])
            if remote_root != self._remote_storage_root / operation_id:
                raise TrainingBlocked("CHECKPOINT_HASH_MISMATCH")
            files = transfer_spec.get("files")
            if type(files) is not list or sum(item["size_bytes"] for item in files) > self._max_bytes:
                raise TrainingBlocked("CHECKPOINT_SIZE_LIMIT")
            put = getattr(self.worker._remote_transport, "put_checkpoint_bytes", None)
            if not callable(put):
                raise TrainingBlocked("REMOTE_CHECKPOINT_LOAD_NOT_BOUND")
            try:
                copied = put(local_root=transfer_spec["local_root"], remote_root=str(remote_root),
                    files=files, authorize=lambda: self._authorize_storage(operation_id=operation_id,
                        expected_state="LOAD_ADMITTED"))
            except Exception:
                raise TrainingBlocked("CHECKPOINT_LOAD_BYTES_NOT_VERIFIED") from None
            expected_copied = [{key: item[key] for key in ("path", "size_bytes", "sha256")} for item in files]
            if (type(copied) is not dict or set(copied) != {"state", "files", "remote_root"}
                    or copied.get("state") != "PHYSICAL_REMOTE_LOAD_BYTES_VERIFIED"
                    or copied.get("remote_root") != str(remote_root) or copied.get("files") != expected_copied):
                raise TrainingBlocked("CHECKPOINT_LOAD_BYTES_NOT_VERIFIED")
            self.worker.require_live()
            reservation["load_root"] = remote_root
        reservation["admission_receipt"] = r.verify_training_checkpoint_admission(result["admission"],
            expected_payload=result["admission"]["payload"], pinned_public_key=self._pin)
        return reservation

    def complete_load(self, *, operation_id, restored_state):
        from lumenis.system.security import training_receipts as r
        # Completion is called only by the existing trusted supervised execution
        # adapter. Its recorded actual load observation is a retained runtime
        # input, not a dict supplied over an external/public checkpoint API.
        observer = getattr(self.worker, "require_completed_training_load", None)
        if not callable(observer):
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        observer(operation_id=operation_id, restored_state=restored_state)

        def commit(conn):
            record = self._engine.training_operation_read(self.task_id, operation_id=operation_id, **self._args(conn))
            if record is None or record["kind"] != "load":
                raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
            if record["state"] in {"LOADED", "RUNNABLE"}:
                if record["result"]["restored_state"] != restored_state:
                    raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                return record["result"]
            if record["state"] != "LOADING":
                raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
            reservation = record["result"]["reservation"]
            r._checkpoint_position(restored_state.get("data_position"))
            if (restored_state["completed_step"] != reservation["completed_step"]
                    or record["result"]["expected_observed_state"] != restored_state
                    or restored_state["framework_lock_sha256"] != self.policy.document["framework_lock_sha256"]):
                raise TrainingBlocked("CHECKPOINT_RESTORED_STATE_MISMATCH")
            state = self._engine.training_execution_read(self.task_id, **self._args(conn))
            receipt = {"schema_version": 1, "operation_id": operation_id, "task_digest": state["task_digest"],
                "run_digest": state["run_digest"], "checkpoint_ref": reservation["checkpoint_ref"],
                "checkpoint_sha256": reservation["checkpoint_sha256"], "restored_state": copy.deepcopy(restored_state),
                "task_step_ref": "trainop_" + hashlib.sha256((self.task_id + operation_id).encode()).hexdigest(),
                "committed_at_utc": datetime.now(timezone.utc).isoformat()}
            handoff = {"schema_version": 1, "task_id": self.task_id, "task_digest": state["task_digest"],
                "run_digest": state["run_digest"], "attempt_id": state["attempt_id"], "worker_epoch": state["worker_epoch"],
                "fingerprints": self._fingerprints, "checkpoint_ref": reservation["checkpoint_ref"],
                "checkpoint_sha256": reservation["checkpoint_sha256"], "load_operation_id": operation_id,
                "resume_receipt_sha256": hashlib.sha256(canonical_bytes(receipt)).hexdigest(),
                "next_sequence": state["next_sequence"], "next_phase": "before_train", "admission_version": 3,
                "worker_binding_sha256": hashlib.sha256(canonical_bytes(state["worker_binding"])).hexdigest()}
            receipt["phase_handoff"] = r.sign_training_checkpoint_payload(handoff,
                receipt_kind="owned_training_recovery_handoff")
            receipt["receipt"] = r.sign_training_checkpoint_payload(receipt, receipt_kind="owned_training_resume_loaded")
            self._engine.training_operation_transition(self.task_id, operation_id=operation_id,
                before_state="LOADING", state="LOADED", result=receipt, **self._args(conn))
            self._engine.training_execution_commit_loaded(self.task_id, phase_handoff=receipt["phase_handoff"], **self._args(conn))
            return receipt
        return self._mutate("load", commit, operation_id=operation_id)

    def read_resume(self, *, operation_id):
        record = self._read(operation_id)
        if record is None:
            return {"state": "NOT_FOUND"}
        if record["kind"] != "load":
            raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
        if record["state"] in {"LOADED", "RUNNABLE"}:
            return {"state": "COMMITTED", "receipt": copy.deepcopy(record["result"])}
        return {"state": "FAILED" if record["state"] in {"FAILED", "INTERRUPTED"} else "PENDING"}


    def recovery_phase_transport(self, *, operation_id):
        """Bind the existing phase callable to one actually committed load.

        This is private Core composition, not a new HTTP service. A remote
        transport still needs the actual authenticated connection owned by W6.
        Every mutation traverses the current Gate/Fence/short commit lease.
        """
        from dataclasses import asdict
        from lumenis.system.security import training_receipts as r
        r._checkpoint_uuid(operation_id)
        request_body = asdict(self.request)
        request_body["scopes"] = list(self.request.scopes)
        common = {"training_request": request_body,
                  "scope_descriptors": copy.deepcopy(self.context["scope_descriptors"])}
        prefix = "/api/experience/owned-training/phase-tasks/" + self.task_id

        def current_load(conn):
            record = self._engine.training_operation_read(self.task_id,
                operation_id=operation_id, **self._args(conn))
            execution = self._engine.training_execution_read(self.task_id, **self._args(conn))
            if (record is None or record["kind"] != "load" or record["state"] not in {"LOADED", "RUNNABLE"}
                    or execution["state"] not in {"LOADED", "RUNNABLE", "COMPLETED"}
                    or record["result"]["run_digest"] != execution["run_digest"]
                    or record["result"]["task_digest"] != execution["task_digest"]):
                raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
            r.verify_training_resume_receipt(record["result"]["receipt"],
                expected_payload={k:v for k,v in record["result"].items() if k != "receipt"},
                pinned_public_key=self._pin)
            self.worker.require_live(execution["worker_binding"])
            return record

        def call(method, relative_path, body):
            if type(method) is not str or type(relative_path) is not str:
                raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
            if method == "POST" and relative_path in {prefix + "/challenges", prefix + "/challenge-decisions"}:
                field = "phase" if relative_path.endswith("/challenges") else "challenge"
                if (type(body) is not dict or set(body) != {*common, field}
                        or any(type(body[k]) is not type(value) or body[k] != value for k,value in common.items())):
                    raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
                if field == "phase":
                    def prepare(conn):
                        current_load(conn)
                        return self._engine.training_prepare_recovery_phase_challenge(
                            self.task_id, phase=body["phase"], **self._args(conn))
                    challenge = self._mutate("recovery-phase", prepare, operation_id=operation_id)
                    return {"ok": True, "state": "PHASE_CHALLENGE_PREPARED", "challenge": challenge,
                            "pinned_public_key": copy.deepcopy(self._pin), "model_execution_claimed": False}

                def issue(conn):
                    load = current_load(conn)
                    execution = self._engine.training_execution_read(self.task_id, **self._args(conn))
                    challenge = r.validate_training_phase_challenge(body["challenge"])
                    if execution["pending_challenge"] != challenge:
                        raise TrainingBlocked("CHECKPOINT_OPERATION_CONFLICT")
                    self._fresh()
                    signed = r.sign_training_phase_decision(challenge, "allow")
                    r.verify_training_phase_decision(signed, expected_challenge=challenge,
                                                    pinned_public_key=self._pin)
                    state = self._engine.training_commit_recovery_phase_receipt(
                        self.task_id, challenge=challenge, receipt=signed, **self._args(conn))
                    if load["state"] == "LOADED":
                        self._engine.training_operation_transition(self.task_id, operation_id=operation_id,
                            before_state="LOADED", state="RUNNABLE", result=load["result"], **self._args(conn))
                    return signed, state["next_sequence"]
                receipt, next_sequence = self._mutate("recovery-phase", issue, operation_id=operation_id)
                return {"ok": True, "state": "PHASE_RECEIPT_COMMITTED", "receipt": receipt,
                    "next_sequence": next_sequence, "pinned_public_key": copy.deepcopy(self._pin),
                    "historical": False, "authorization_usable": True, "model_execution_claimed": False}
            if method == "GET" and relative_path.startswith(prefix + "/receipts/") and body is None:
                from lumenis.shared.database import get_repository
                nonce = relative_path[len(prefix + "/receipts/"):]
                self._fresh()
                with get_repository().connection(timeout=30) as conn:
                    conn.execute("BEGIN")
                    try:
                        current_load(conn)
                        history = self._engine.training_recovery_phase_history(
                            self.task_id, nonce=nonce, **self._args(conn))
                        self._fresh()
                    finally:
                        conn.rollback()
                return {"ok": True, "state": "PHASE_RECEIPT_NOT_COMMITTED" if history is None else "PHASE_RECEIPT_HISTORY",
                    "receipt": None if history is None else history["receipt"],
                    "challenge": None if history is None else history["challenge"],
                    "pinned_public_key": copy.deepcopy(self._pin), "historical": True,
                    "authorization_usable": False, "model_execution_claimed": False}
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
        return call


if __name__ == "__main__":
    if sys.argv[1:] not in (["--managed-training-worker"], ["--remote-managed-training-worker"]):
        raise SystemExit("Only the owner-supervised training entry is available")
    _managed_training_worker(remote=sys.argv[1:] == ["--remote-managed-training-worker"])
