import builtins
import errno
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

import run_supervised


class FakeProcess:
    def __init__(self, pid, returncode=1, poll_error=None, launch_id=None,
                 boot_id=None, entry_sha256=None):
        self.pid = pid
        self.returncode = returncode
        self.poll_error = poll_error
        self.wait_calls = []
        self.launch_id = launch_id or uuid.uuid4().hex
        self.boot_id = boot_id or uuid.uuid4().hex
        self.entry_sha256 = entry_sha256 or "a" * 64

    def poll(self):
        if self.poll_error is not None:
            raise self.poll_error
        return self.returncode

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake-child", timeout)
        return self.returncode


class FakeLock:
    def __init__(self, events=None):
        self.closed = False
        self.events = events if events is not None else []

    def close(self):
        self.closed = True
        self.events.append(("lock_closed", None))


class FakeSocket:
    def settimeout(self, _timeout):
        pass

    def bind(self, _address):
        pass

    def close(self):
        pass


class FakeHTTPResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, size):
        return json.dumps(self.payload).encode("utf-8")[:size]


class FakeEvent:
    def __init__(self, on_wait=None):
        self.wait_calls = []
        self.on_wait = on_wait

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if self.on_wait:
            self.on_wait(len(self.wait_calls), timeout)
        return False


@pytest.fixture
def isolated_runtime_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(run_supervised, "ROOT", tmp_path)
    monkeypatch.setattr(run_supervised, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(run_supervised, "LOG_FILE", tmp_path / "logs" / "supervisor.log")
    monkeypatch.setattr(run_supervised, "STATE_FILE", tmp_path / "data" / "supervisor_state.json")
    monkeypatch.setattr(run_supervised, "APP_OUT", tmp_path / "logs" / "supervised_app.out")
    return tmp_path


def _configure_main(monkeypatch, event, *, health_result=False, fake_clock=None,
                    process_returncodes=1, launch_id=None, health_calls=None,
                    stop_after_health=False):
    states = []
    spawned = []
    events = []
    handlers = {}
    lock = FakeLock(events)

    monkeypatch.setattr(run_supervised, "acquire_instance_lock", lambda _path, _port: lock)
    monkeypatch.setattr(run_supervised.signal, "signal", lambda sig, handler: handlers.setdefault(sig, handler))
    monkeypatch.setattr(run_supervised.threading, "Event", lambda: event)
    monkeypatch.setattr(run_supervised.socket, "socket", lambda *_args, **_kwargs: FakeSocket())
    monkeypatch.setattr(run_supervised, "write_state", lambda **state: (states.append(dict(state)) or True))
    monkeypatch.setattr(run_supervised, "log", lambda _message: None)
    def record_health(_port, **expected_identity):
        if health_calls is not None:
            health_calls.append(dict(expected_identity))
        if stop_after_health:
            handlers[run_supervised.signal.SIGTERM](run_supervised.signal.SIGTERM, None)
        return health_result

    monkeypatch.setattr(run_supervised, "http_health", record_health)
    argv = ["run_supervised.py", "--port", "0"]
    if launch_id is not None:
        argv.extend(["--launch-id", launch_id])
    monkeypatch.setattr(run_supervised.sys, "argv", argv)
    if fake_clock is not None:
        monkeypatch.setattr(run_supervised, "time", SimpleNamespace(time=fake_clock))

    def record_spawn(app, host, port, *, launch_id=None):
        index = len(spawned)
        if isinstance(process_returncodes, (list, tuple)):
            returncode = process_returncodes[index]
        else:
            returncode = process_returncodes
        process = FakeProcess(
            pid=1000 + index,
            returncode=returncode,
            launch_id=launch_id,
        )
        spawned.append((app, host, port, process))
        events.append(("spawn", process.pid))
        return process

    monkeypatch.setattr(run_supervised, "spawn", record_spawn)
    return states, spawned, events, handlers, lock


def test_spawn_closes_parent_output_handle_on_success_and_failure(monkeypatch, isolated_runtime_paths):
    (isolated_runtime_paths / "app.py").write_bytes(b"core entry")
    handles = []

    def successful_popen(_args, **kwargs):
        handles.append(kwargs["stdout"])
        return FakeProcess(pid=456, returncode=None)

    monkeypatch.setattr(run_supervised.subprocess, "Popen", successful_popen)
    process = run_supervised.spawn("app.py", "127.0.0.1", "8201")
    assert uuid.UUID(process.launch_id).hex == process.launch_id
    assert handles[-1].closed

    def failed_popen(_args, **kwargs):
        handles.append(kwargs["stdout"])
        raise OSError("simulated process creation failure")

    monkeypatch.setattr(run_supervised.subprocess, "Popen", failed_popen)
    with pytest.raises(OSError, match="simulated process creation failure"):
        run_supervised.spawn("app.py", "127.0.0.1", "8201")
    assert handles[-1].closed


def test_spawn_passes_loaded_entry_identity_and_uses_a_fresh_boot_id(
    monkeypatch, isolated_runtime_paths
):
    entry_bytes = b"the exact Product Core entry bytes\n"
    entry = isolated_runtime_paths / "app.py"
    entry.write_bytes(entry_bytes)
    calls = []

    def record_popen(args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess(pid=500 + len(calls), returncode=None)

    monkeypatch.setattr(run_supervised.subprocess, "Popen", record_popen)
    launch_id = uuid.uuid4().hex
    first = run_supervised.spawn("app.py", "127.0.0.1", "8201", launch_id=launch_id)
    second = run_supervised.spawn(str(entry), "127.0.0.1", "8201", launch_id=launch_id)
    expected_hash = hashlib.sha256(entry_bytes).hexdigest()

    assert calls[0][0][4] == str(entry.resolve())
    assert first.launch_id == second.launch_id == launch_id
    assert first.entry_sha256 == second.entry_sha256 == expected_hash
    assert first.boot_id != second.boot_id
    assert uuid.UUID(first.boot_id).hex == first.boot_id
    assert uuid.UUID(second.boot_id).hex == second.boot_id
    for process, (_args, kwargs) in zip((first, second), calls):
        child_env = kwargs["env"]
        assert child_env["LUMENIS_CORE_LAUNCH_ID"] == process.launch_id
        assert child_env["LUMENIS_CORE_BOOT_ID"] == process.boot_id
        assert child_env["LUMENIS_CORE_ENTRY_SHA256"] == process.entry_sha256


def test_spawn_rejects_missing_or_outside_root_core_entry(
    monkeypatch, isolated_runtime_paths
):
    runtime_root = isolated_runtime_paths / "runtime"
    runtime_root.mkdir()
    monkeypatch.setattr(run_supervised, "ROOT", runtime_root)
    outside_entry = isolated_runtime_paths / "outside.py"
    outside_entry.write_bytes(b"outside")
    monkeypatch.setattr(
        run_supervised.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("Popen must not run for an invalid entry"),
    )

    with pytest.raises(ValueError, match="within the runtime root"):
        run_supervised.spawn(str(outside_entry), "127.0.0.1", "8201")
    with pytest.raises(ValueError, match="must exist within the runtime root"):
        run_supervised.spawn("missing.py", "127.0.0.1", "8201")


def test_http_health_requires_each_supplied_core_instance_identity(monkeypatch):
    expected = {
        "launch_id": uuid.uuid4().hex,
        "boot_id": uuid.uuid4().hex,
        "entry_sha256": "b" * 64,
    }
    payload = {
        "ok": True,
        "status": "healthy",
        "dependencies": {"database": "ok"},
        "core_instance": dict(expected),
    }

    def use_payload(value):
        monkeypatch.setattr(
            run_supervised.urllib.request,
            "urlopen",
            lambda *_args, **_kwargs: FakeHTTPResponse(value),
        )

    use_payload(payload)
    assert run_supervised.http_health(
        8201,
        expected_launch_id=expected["launch_id"],
        expected_boot_id=expected["boot_id"],
        expected_entry_sha256=expected["entry_sha256"],
    )

    for field, value in expected.items():
        missing = dict(expected)
        missing.pop(field)
        payload["core_instance"] = missing
        use_payload(payload)
        assert not run_supervised.http_health(
            8201,
            expected_launch_id=expected["launch_id"],
            expected_boot_id=expected["boot_id"],
            expected_entry_sha256=expected["entry_sha256"],
        )

        mismatched = dict(expected)
        mismatched[field] = value + "-other"
        payload["core_instance"] = mismatched
        use_payload(payload)
        assert not run_supervised.http_health(
            8201,
            expected_launch_id=expected["launch_id"],
            expected_boot_id=expected["boot_id"],
            expected_entry_sha256=expected["entry_sha256"],
        )

    payload.pop("core_instance")
    use_payload(payload)
    assert run_supervised.http_health(8201)


def test_lock_contention_is_duplicate_but_unexpected_lock_error_closes_handle(monkeypatch, tmp_path):
    lock_path = tmp_path / "data" / "supervisor_8201.lock"
    real_open = builtins.open
    handles = []

    def tracked_open(file, *args, **kwargs):
        handle = real_open(file, *args, **kwargs)
        if Path(file) == lock_path:
            handles.append(handle)
        return handle

    class ContendedMsvcrt:
        LK_NBLCK = 1

        @staticmethod
        def locking(_fd, _mode, _length):
            raise OSError(errno.EACCES, "lock is held")

    monkeypatch.setattr(builtins, "open", tracked_open)
    monkeypatch.setitem(sys.modules, "msvcrt", ContendedMsvcrt)
    assert run_supervised.acquire_instance_lock(lock_path, "8201") is None
    assert handles[-1].closed

    class BrokenMsvcrt:
        LK_NBLCK = 1

        @staticmethod
        def locking(_fd, _mode, _length):
            raise OSError(errno.EBADF, "invalid lock handle")

    monkeypatch.setitem(sys.modules, "msvcrt", BrokenMsvcrt)
    with pytest.raises(OSError, match="invalid lock handle"):
        run_supervised.acquire_instance_lock(lock_path, "8201")
    assert handles[-1].closed


def test_main_fails_closed_when_lock_setup_fails(monkeypatch):
    monkeypatch.setattr(run_supervised.sys, "argv", ["run_supervised.py", "--port", "0"])
    monkeypatch.setattr(
        run_supervised, "acquire_instance_lock",
        lambda *_args: (_ for _ in ()).throw(OSError("lock setup failed")),
    )
    monkeypatch.setattr(run_supervised, "log", lambda _message: None)
    monkeypatch.setattr(
        run_supervised, "spawn",
        lambda *_args: pytest.fail("supervisor spawned without owning its lock"),
    )
    with pytest.raises(SystemExit) as exc:
        run_supervised.main()
    assert exc.value.code == 1


def test_main_exits_cleanly_when_another_supervisor_holds_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(run_supervised, "ROOT", tmp_path)
    monkeypatch.setattr(run_supervised.sys, "argv", ["run_supervised.py", "--port", "0"])
    monkeypatch.setattr(run_supervised, "acquire_instance_lock", lambda *_args: None)
    monkeypatch.setattr(run_supervised, "log", lambda _message: None)
    monkeypatch.setattr(
        run_supervised, "spawn",
        lambda *_args: pytest.fail("duplicate supervisor must exit without spawning"),
    )
    with pytest.raises(SystemExit) as exc:
        run_supervised.main()
    assert exc.value.code == 0


def test_kill_tree_requires_successful_taskkill_and_reaps_child(monkeypatch, isolated_runtime_paths):
    monkeypatch.setattr(run_supervised, "sys", SimpleNamespace(platform="win32"))
    calls = []
    process = FakeProcess(pid=2468, returncode=None)

    def taskkill(args, **kwargs):
        calls.append((args, kwargs))
        process.returncode = 0
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(run_supervised.subprocess, "run", taskkill)
    assert run_supervised.kill_tree(process, timeout=4)
    assert calls[0][0] == ["taskkill", "/PID", "2468", "/T", "/F"]
    assert calls[0][1]["timeout"] == 4
    assert process.wait_calls == [4]

    still_running = FakeProcess(pid=2469, returncode=None)
    monkeypatch.setattr(run_supervised.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1))
    assert not run_supervised.kill_tree(still_running, timeout=2)
    assert still_running.wait_calls == [2]


def test_actual_disposable_child_is_terminated_and_reaped(isolated_runtime_paths):
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert process.poll() is None
        assert run_supervised.kill_tree(process, timeout=5)
        assert process.wait(timeout=0) == process.returncode
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_shutdown_interrupts_escalated_crash_backoff_and_releases_after_cleanup(
    monkeypatch, isolated_runtime_paths
):
    handler_ref = [None]

    def request_stop_on_long_backoff(call_count, _timeout):
        # Four ordinary 3-second restart waits use 12 slices. Stop on the first
        # slice of the fifth crash's 63-second cooldown.
        if call_count == 13:
            handler_ref[0][run_supervised.signal.SIGTERM](run_supervised.signal.SIGTERM, None)

    event = FakeEvent(request_stop_on_long_backoff)
    states, spawned, events, main_handlers, lock = _configure_main(monkeypatch, event)
    handler_ref[0] = main_handlers
    monkeypatch.setattr(run_supervised, "kill_tree", lambda process: events.append(("kill", process.pid)) or True)

    run_supervised.main()

    assert len(spawned) == run_supervised.FAST_CRASH_LIMIT
    child_processes = [spawn[3] for spawn in spawned]
    launch_ids = {process.launch_id for process in child_processes}
    assert len(launch_ids) == 1
    assert uuid.UUID(next(iter(launch_ids))).hex == next(iter(launch_ids))
    assert len({process.boot_id for process in child_processes}) == len(child_processes)
    assert 1.0 in event.wait_calls
    assert states[-1]["status"] == "stopped"
    assert states[-1]["child_cleanup"] == "confirmed"
    assert lock.closed
    assert events.index(("kill", spawned[-1][3].pid)) < events.index(("lock_closed", None))


def test_main_binds_health_and_state_to_restarted_child_identity(
    monkeypatch, isolated_runtime_paths
):
    clock = [0.0]
    health_calls = []
    launch_id = uuid.uuid4().hex

    def advance_clock(timeout):
        clock[0] += timeout

    event = FakeEvent(lambda _count, timeout: advance_clock(timeout))
    states, spawned, events, _handlers, lock = _configure_main(
        monkeypatch,
        event,
        health_result=True,
        fake_clock=lambda: clock[0],
        process_returncodes=[1, None],
        launch_id=launch_id,
        health_calls=health_calls,
        stop_after_health=True,
    )
    monkeypatch.setattr(run_supervised, "HEALTH_INTERVAL", 1)
    monkeypatch.setattr(run_supervised, "kill_tree", lambda process: events.append(("kill", process.pid)) or True)

    run_supervised.main()

    assert len(spawned) == 2
    first_child = spawned[0][3]
    current_child = spawned[1][3]
    assert first_child.launch_id == current_child.launch_id == launch_id
    assert first_child.boot_id != current_child.boot_id
    assert health_calls == [{
        "expected_launch_id": current_child.launch_id,
        "expected_boot_id": current_child.boot_id,
        "expected_entry_sha256": current_child.entry_sha256,
    }]

    starting_states = [state for state in states if state.get("status") == "starting"]
    assert [state["pid"] for state in starting_states] == [first_child.pid, current_child.pid]
    assert starting_states[1]["launch_id"] == current_child.launch_id
    assert starting_states[1]["boot_id"] == current_child.boot_id
    assert starting_states[1]["entry_sha256"] == current_child.entry_sha256
    running_state = next(state for state in states if state.get("status") == "running")
    assert running_state["pid"] == current_child.pid
    assert running_state["launch_id"] == current_child.launch_id
    assert running_state["boot_id"] == current_child.boot_id
    assert running_state["entry_sha256"] == current_child.entry_sha256
    assert states[-1]["status"] == "stopped"
    assert states[-1]["child_cleanup"] == "confirmed"
    assert events.index(("kill", current_child.pid)) < events.index(("lock_closed", None))
    assert lock.closed


def test_zombie_kill_failure_does_not_spawn_replacement_and_keeps_failure_state(
    monkeypatch, isolated_runtime_paths
):
    clock = [0.0]

    def advance_clock(timeout):
        clock[0] += timeout

    event = FakeEvent(lambda _count, timeout: advance_clock(timeout))
    states, spawned, events, _handlers, lock = _configure_main(
        monkeypatch, event, health_result=False, fake_clock=lambda: clock[0]
    )
    zombie = FakeProcess(pid=7777, returncode=None)
    monkeypatch.setattr(
        run_supervised, "spawn",
        lambda *_args, **_kwargs: spawned.append(zombie) or zombie,
    )
    monkeypatch.setattr(run_supervised, "POLL_INTERVAL", 2)
    monkeypatch.setattr(run_supervised, "HEALTH_INTERVAL", 1)
    kill_results = iter([False, True])

    def fail_then_cleanup(process):
        events.append(("kill", process.pid))
        return next(kill_results)

    monkeypatch.setattr(run_supervised, "kill_tree", fail_then_cleanup)
    monkeypatch.setattr(run_supervised, "FAST_CRASH_LIMIT", 3)

    with pytest.raises(SystemExit) as exc:
        run_supervised.main()

    assert exc.value.code == 1
    assert len(spawned) == 1
    assert len([event for event in events if event[0] == "kill"]) == 2
    assert states[-1]["status"] == "restart_failed"
    assert states[-1]["child_cleanup"] == "confirmed"
    assert lock.closed


def test_loop_exception_cleans_child_before_terminal_state_and_lock_release(
    monkeypatch, isolated_runtime_paths
):
    error = RuntimeError("simulated supervisor loop failure")
    event = FakeEvent()
    states, spawned, events, _handlers, lock = _configure_main(monkeypatch, event)
    process = FakeProcess(pid=9876, returncode=None, poll_error=error)
    monkeypatch.setattr(
        run_supervised, "spawn",
        lambda *_args, **_kwargs: spawned.append(process) or process,
    )

    def record_cleanup(child):
        events.append(("kill", child.pid))
        return True

    monkeypatch.setattr(run_supervised, "kill_tree", record_cleanup)
    monkeypatch.setattr(run_supervised, "write_state", lambda **state: (states.append(dict(state)) or events.append(("state", state.get("status"))) or True))

    with pytest.raises(RuntimeError, match="simulated supervisor loop failure"):
        run_supervised.main()

    assert states[-1]["status"] == "stopped"
    assert events.index(("kill", process.pid)) < events.index(("state", "stopped"))
    assert events.index(("state", "stopped")) < events.index(("lock_closed", None))
    assert lock.closed


def test_failed_final_cleanup_never_marks_stopped_or_explicitly_releases_lock(
    monkeypatch, isolated_runtime_paths
):
    error = RuntimeError("simulated supervisor loop failure")
    event = FakeEvent()
    states, spawned, _events, _handlers, lock = _configure_main(monkeypatch, event)
    process = FakeProcess(pid=9877, returncode=None, poll_error=error)
    monkeypatch.setattr(
        run_supervised, "spawn",
        lambda *_args, **_kwargs: spawned.append(process) or process,
    )
    monkeypatch.setattr(run_supervised, "kill_tree", lambda _child: False)
    monkeypatch.setattr(run_supervised, "write_state", lambda **state: (states.append(dict(state)) or True))

    with pytest.raises(RuntimeError, match="simulated supervisor loop failure"):
        run_supervised.main()

    assert states[-1]["status"] == "stop_failed"
    assert states[-1]["child_cleanup"] == "failed"
    assert lock.closed is False
