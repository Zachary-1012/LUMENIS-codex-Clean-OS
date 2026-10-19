"""Reload-safe fatal handling and periodic stack diagnostics.

Native dump_traceback_later can race changing frames on affected CPython
runtimes (cpython#116008). A Python worker calls dump_traceback with the GIL.
Periodic snapshots cannot run during a permanently GIL-held native deadlock;
fatal signal handling remains installed. No claim is made about all versions.
"""
from __future__ import annotations

import atexit
import faulthandler
import os
import threading

_handler_lock = threading.RLock()
_handler_owner = None
_CLOSE_TIMEOUT = 0.5


class FaultDiagnostics:
    def __init__(self, path: str, interval: float = 120.0):
        global _handler_owner
        if interval <= 0:
            raise ValueError("diagnostic interval must be positive")
        self.path = os.path.abspath(path)
        self.interval = interval
        self.stop = threading.Event()
        self.file = open(self.path, "a", encoding="utf-8")
        self.thread = threading.Thread(
            target=self._run, name="lumenis-fault-diagnostics", daemon=True
        )
        with _handler_lock:
            previous = _handler_owner
            try:
                faulthandler.enable(file=self.file, all_threads=True)
                _handler_owner = self
                self.thread.start()
            except BaseException:
                _handler_owner = previous
                if previous is not None and not previous.file.closed:
                    faulthandler.enable(file=previous.file, all_threads=True)
                else:
                    faulthandler.disable()
                self.file.close()
                raise

    def _retire(self):
        global _handler_owner
        with _handler_lock:
            if _handler_owner is self:
                faulthandler.disable()
                _handler_owner = None
            if not self.file.closed:
                self.file.close()

    def _run(self):
        try:
            while not self.stop.wait(self.interval):
                try:
                    self.file.write("\n[PeriodicDiagnostics] all-thread stack snapshot\n")
                    self.file.flush()
                    faulthandler.dump_traceback(file=self.file, all_threads=True)
                except (OSError, ValueError):
                    pass
        finally:
            self._retire()

    def close(self):
        self.stop.set()
        if self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=_CLOSE_TIMEOUT)
        # A blocked sink retains its live file until its worker returns. Never
        # close a descriptor underneath an in-progress dump or block shutdown.
        if not self.thread.is_alive():
            self._retire()


_lock = threading.RLock()
_current = None


def install_fault_diagnostics(path: str):
    """Reuse the live sink; a failed replacement preserves the current owner."""
    global _current, _handler_owner
    path = os.path.abspath(path)
    with _lock:
        if (_current is not None and _current.path == path
                and not _current.file.closed and _current.thread.is_alive()
                and not _current.stop.is_set()):
            with _handler_lock:
                faulthandler.enable(file=_current.file, all_threads=True)
                _handler_owner = _current
            return _current.file
        replacement = FaultDiagnostics(path)
        previous, _current = _current, replacement
        if previous is not None:
            previous.close()
        return replacement.file


def shutdown_fault_diagnostics():
    global _current
    with _lock:
        if _current is not None:
            _current.close()
            _current = None


atexit.register(shutdown_fault_diagnostics)
