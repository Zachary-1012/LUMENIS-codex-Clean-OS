from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator


class ResourceLimitError(RuntimeError):
    pass


def _memory_snapshot() -> dict[str, int]:
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {"total_ram_mb": int(memory.total / 1048576), "available_ram_mb": int(memory.available / 1048576)}
    except Exception:
        return {"total_ram_mb": 0, "available_ram_mb": 0}


class ResourceGuard:
    def __init__(self, policy: dict[str, Any]):
        self.policy = dict(policy)
        self._semaphore = threading.BoundedSemaphore(int(self.policy.get("max_concurrency", 1)))
        self._queue_lock = threading.Lock()
        self._waiting = 0

    def snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = _memory_snapshot()
        result["process_id"] = os.getpid()
        result["max_runtime_seconds"] = int(self.policy.get("max_runtime_seconds", 120))
        result["max_concurrency"] = int(self.policy.get("max_concurrency", 1))
        result["max_queue"] = int(self.policy.get("max_queue", 2))
        try:
            import psutil
            result["cpu_percent"] = float(psutil.cpu_percent(interval=0.05))
        except Exception:
            result["cpu_percent"] = 0.0
        return result

    @contextmanager
    def reserve(self, required_free_ram_mb: int = 0) -> Iterator[dict[str, Any]]:
        wait = float(self.policy.get("cooldown_seconds", 15))
        with self._queue_lock:
            if self._waiting >= int(self.policy.get("max_queue", 2)):
                raise ResourceLimitError("RESOURCE_LIMIT:max_queue")
            self._waiting += 1
        try:
            acquired = self._semaphore.acquire(timeout=wait)
        finally:
            with self._queue_lock:
                self._waiting -= 1
        if not acquired:
            raise ResourceLimitError("RESOURCE_LIMIT:max_concurrency")
        try:
            state = self.snapshot()
            available = state.get("available_ram_mb", 0)
            minimum = max(int(self.policy.get("min_free_ram_mb", 2048)), int(required_free_ram_mb))
            if available and available < minimum:
                time.sleep(min(float(self.policy.get("cooldown_seconds", 15)), 3.0))
                state = self.snapshot()
                available = state.get("available_ram_mb", 0)
                if available and available < minimum:
                    raise ResourceLimitError("RESOURCE_LIMIT:min_free_ram")
            if state.get("cpu_percent", 0) > float(self.policy.get("max_cpu_percent", 90)):
                raise ResourceLimitError("RESOURCE_LIMIT:max_cpu")
            yield state
        finally:
            self._semaphore.release()
