"""File-lock regressions; simulated Windows tests do not certify native Windows."""
from __future__ import annotations

import builtins
import errno
import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from lumenis.shared.learning import content_assets
from lumenis.shared.learning.content_assets import (
    ContentPatternRegistry,
    create_pattern_candidate,
)
from lumenis.shared.learning.persistence import LearningPersistence


def _registry(directory):
    persistence = LearningPersistence()
    persistence.init(data_dir=directory)
    return ContentPatternRegistry(persistence)


def _candidate():
    return create_pattern_candidate(
        asset_type="narrative",
        title="Portable locking regression",
        source_kind="research",
        source_refs=("regression-source",),
        extracted_principle="Keep each concurrent candidate.",
        reusable_pattern={"progression": ["action", "meaning"]},
        evidence_requirements=("review source",),
        originality_boundary="Do not copy creator identity.",
        legal_or_compliance_boundary="Use permitted source material.",
        counterexamples=("Do not infer permission from a candidate.",),
        format_scope=("text",),
    )


def _save_many(directory, start, count):
    registry = _registry(directory)
    original_load = registry._persistence.load_collection

    def slow_load(name):
        result = original_load(name)
        time.sleep(0.005)
        return result

    registry._persistence.load_collection = slow_load
    assert start.wait(15)
    for _ in range(count):
        registry.save_candidate(_candidate())


def _enter_guard(directory, ready, acquired):
    registry = _registry(directory)
    ready.set()
    with registry.mutation_guard():
        acquired.set()


def _hold_guard_until_terminated(directory, acquired):
    registry = _registry(directory)
    with registry.mutation_guard():
        acquired.set()
        time.sleep(30)


def _stop_processes(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
        process.join(5)


def test_import_does_not_require_posix_fcntl():
    source_root = str(Path(__file__).resolve().parents[1])
    script = """
import builtins
original_import = builtins.__import__
def without_fcntl(name, *args, **kwargs):
    if name == 'fcntl':
        raise ModuleNotFoundError('fcntl is unavailable on native Windows')
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_fcntl
from lumenis.shared.learning.content_assets import ContentPatternRegistry
assert ContentPatternRegistry is not None
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=source_root,
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_process_writers_preserve_every_candidate(tmp_path):
    registry = _registry(tmp_path)
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    processes = [context.Process(target=_save_many, args=(str(tmp_path), start, 12)) for _ in range(4)]
    try:
        for process in processes:
            process.start()
        start.set()
        for process in processes:
            process.join(20)
            assert process.exitcode == 0
        records = registry.snapshot()
        assert len(records) == 48
        assert all(record["decision"] == "EXPERIMENT" for record in records.values())
        assert not (tmp_path / "patterns.json.tmp").exists()
    finally:
        _stop_processes(processes)


def test_nested_guard_excludes_process_and_releases_after_exception(tmp_path):
    registry = _registry(tmp_path)
    context = multiprocessing.get_context("spawn")
    ready, acquired = context.Event(), context.Event()
    process = context.Process(target=_enter_guard, args=(str(tmp_path), ready, acquired))
    try:
        with pytest.raises(RuntimeError, match="injected mutation failure"):
            with registry.mutation_guard():
                with _registry(tmp_path).mutation_guard():
                    process.start()
                    assert ready.wait(10)
                    assert not acquired.wait(0.2)
                assert not acquired.wait(0.2)
                raise RuntimeError("injected mutation failure")
        assert acquired.wait(10)
        process.join(10)
        assert process.exitcode == 0
        assert not getattr(content_assets._PATTERN_LOCK_STATE, "held", set())
    finally:
        if process.pid is not None:
            _stop_processes([process])


def test_failed_atomic_replace_can_restore_and_next_writer_succeeds(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    original = registry.save_candidate(_candidate())
    saved_replace = os.replace
    failed = False

    def fail_one_replace(source, destination):
        nonlocal failed
        if Path(source).name == "patterns.json.tmp" and not failed:
            failed = True
            raise OSError(errno.EIO, "injected atomic replace failure")
        return saved_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_one_replace)
    with pytest.raises(OSError, match="injected atomic replace failure"):
        with registry.mutation_guard():
            snapshot = registry.snapshot()
            try:
                registry.save_candidate(_candidate())
            except OSError:
                registry.restore_snapshot(snapshot)
                raise
    assert set(registry.snapshot()) == {original.asset_id}
    reopened = _registry(tmp_path)
    later = reopened.save_candidate(_candidate())
    assert set(reopened.snapshot()) == {original.asset_id, later.asset_id}
    assert not (tmp_path / "patterns.json.tmp").exists()


def test_process_crash_releases_os_lock(tmp_path):
    _registry(tmp_path)
    context = multiprocessing.get_context("spawn")
    holding, ready, entered = context.Event(), context.Event(), context.Event()
    holder = context.Process(target=_hold_guard_until_terminated, args=(str(tmp_path), holding))
    waiter = context.Process(target=_enter_guard, args=(str(tmp_path), ready, entered))
    started = []
    try:
        holder.start()
        started.append(holder)
        assert holding.wait(10)
        waiter.start()
        started.append(waiter)
        assert ready.wait(10)
        assert not entered.wait(0.2)
        holder.terminate()
        holder.join(10)
        assert holder.exitcode is not None
        assert entered.wait(10)
        waiter.join(10)
        assert waiter.exitcode == 0
    finally:
        _stop_processes(started)


def _windows_lock(monkeypatch, locking):
    monkeypatch.setattr(content_assets, "os", SimpleNamespace(name="nt"))
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=locking))


def test_synthetic_windows_contention_retries_fixed_byte_and_unlocks(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    calls, sleeps = [], []

    def locking(fd, mode, length):
        calls.append((mode, length, os.lseek(fd, 0, os.SEEK_CUR)))
        if mode == 2 and len(calls) < 3:
            raise OSError(errno.EACCES, "lock held by another process")

    _windows_lock(monkeypatch, locking)
    monkeypatch.setattr(content_assets, "time", SimpleNamespace(sleep=sleeps.append))
    with pytest.raises(RuntimeError, match="mutation failed"):
        with registry.mutation_guard():
            with registry.mutation_guard():
                assert len(calls) == 3
            assert len(calls) == 3
            raise RuntimeError("mutation failed")
    assert calls == [(2, 1, 0), (2, 1, 0), (2, 1, 0), (0, 1, 0)]
    assert sleeps == [0.05, 0.05]
    assert not getattr(content_assets._PATTERN_LOCK_STATE, "held", set())
    # Locking beyond EOF is supported by msvcrt. Avoid racing pre-lock writes.
    assert (tmp_path / "patterns.json.lock").read_bytes() == b""


@pytest.mark.parametrize("error", [errno.EBADF, errno.EINVAL, errno.EIO])
def test_synthetic_windows_noncontention_errors_fail_closed_and_close_file(tmp_path, monkeypatch, error):
    registry = _registry(tmp_path)
    handles, calls = [], []
    original_open = builtins.open

    def tracked_open(*args, **kwargs):
        handle = original_open(*args, **kwargs)
        handles.append(handle)
        return handle

    def locking(fd, mode, length):
        calls.append(mode)
        raise OSError(error, "invalid lock operation")

    monkeypatch.setattr(content_assets, "open", tracked_open, raising=False)
    _windows_lock(monkeypatch, locking)
    with pytest.raises(OSError, match="invalid lock operation"):
        with registry.mutation_guard():
            pytest.fail("mutation entered without an OS lock")
    assert calls == [2]
    assert handles[-1].closed
    assert not getattr(content_assets._PATTERN_LOCK_STATE, "held", set())


def test_synthetic_windows_interrupted_wait_closes_file_and_can_retry(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    original_open = builtins.open
    handles = []

    def tracked_open(*args, **kwargs):
        handle = original_open(*args, **kwargs)
        handles.append(handle)
        return handle

    def locked(fd, mode, length):
        raise OSError(errno.EACCES, "lock held")

    def interrupt_wait(_seconds):
        raise KeyboardInterrupt()

    monkeypatch.setattr(content_assets, "open", tracked_open, raising=False)
    _windows_lock(monkeypatch, locked)
    monkeypatch.setattr(content_assets, "time", SimpleNamespace(sleep=interrupt_wait))
    with pytest.raises(KeyboardInterrupt):
        with registry.mutation_guard():
            pytest.fail("mutation entered without an OS lock")
    assert handles[-1].closed
    assert not getattr(content_assets._PATTERN_LOCK_STATE, "held", set())
    _windows_lock(monkeypatch, lambda *args: None)
    with registry.mutation_guard():
        pass
    assert handles[-1].closed


def test_synthetic_windows_unlock_error_closes_file_and_clears_reentrancy(tmp_path, monkeypatch):
    registry = _registry(tmp_path)
    original_open = builtins.open
    handles, calls = [], []

    def tracked_open(*args, **kwargs):
        handle = original_open(*args, **kwargs)
        handles.append(handle)
        return handle

    def locking(fd, mode, length):
        calls.append(mode)
        if mode == 0:
            raise OSError(errno.EIO, "unlock failed")

    monkeypatch.setattr(content_assets, "open", tracked_open, raising=False)
    _windows_lock(monkeypatch, locking)
    with pytest.raises(OSError, match="unlock failed"):
        with registry.mutation_guard():
            pass
    assert calls == [2, 0]
    assert handles[-1].closed
    assert not getattr(content_assets._PATTERN_LOCK_STATE, "held", set())
