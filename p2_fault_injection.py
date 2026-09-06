# -*- coding: utf-8 -*-
"""P2 基础框架 — 故障注入（只建模拟函数+测试，不做完整演练平台）。
固定模拟：OSAI 不可用 / AI 超时 / Cookie 失效 / DB 锁 / 网络抖动
"""
from __future__ import annotations
import time, random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class FaultType(str, Enum):
    OSAI_UNAVAILABLE = "osai_unavailable"
    AI_TIMEOUT = "ai_timeout"
    COOKIE_EXPIRED = "cookie_expired"
    DB_LOCKED = "db_locked"
    NETWORK_JITTER = "network_jitter"
    NONE = "none"


@dataclass
class FaultInjectionResult:
    fault_type: str
    injected: bool
    simulated: bool = True
    response: Dict[str, Any] = field(default_factory=dict)
    delay_ms: int = 0
    error: Optional[str] = None
    def to_dict(self):
        return {"fault_type": self.fault_type, "injected": self.injected,
                "simulated": self.simulated, "response": self.response,
                "delay_ms": self.delay_ms, "error": self.error}


class FaultInjector:
    def __init__(self):
        self._active_faults: Dict[str, bool] = {}
        self._injection_log: List[FaultInjectionResult] = []

    def enable(self, ft): self._active_faults[ft.value] = True
    def disable(self, ft): self._active_faults.pop(ft.value, None)
    def disable_all(self): self._active_faults.clear()
    def is_active(self, ft): return self._active_faults.get(ft.value, False)
    def list_active(self): return list(self._active_faults.keys())
    def _log(self, r):
        self._injection_log.append(r)
        if len(self._injection_log) > 1000: self._injection_log = self._injection_log[-500:]

    def simulate_osai_unavailable(self):
        r = FaultInjectionResult(fault_type=FaultType.OSAI_UNAVAILABLE.value,
            injected=self.is_active(FaultType.OSAI_UNAVAILABLE),
            response={"connected": False, "status": "UNAVAILABLE", "source": "FALLBACK_NONE",
                      "data": None, "error": "OSAI_REPO_NOT_FOUND (simulated)", "skills": [], "total": 0},
            error="OSAI unavailable (simulated)")
        self._log(r); return r

    def simulate_ai_timeout(self, timeout_ms=30000):
        delay = 0
        if self.is_active(FaultType.AI_TIMEOUT):
            delay = min(timeout_ms, 50); time.sleep(delay / 1000)
        r = FaultInjectionResult(fault_type=FaultType.AI_TIMEOUT.value,
            injected=self.is_active(FaultType.AI_TIMEOUT),
            response={"success": False, "status": "TIMEOUT",
                      "error": f"AI request timed out after {timeout_ms}ms (simulated)", "provider": "simulated"},
            delay_ms=delay, error="AI timeout (simulated)")
        self._log(r); return r

    def simulate_cookie_expired(self):
        r = FaultInjectionResult(fault_type=FaultType.COOKIE_EXPIRED.value,
            injected=self.is_active(FaultType.COOKIE_EXPIRED),
            response={"success": False, "status": "SESSION_EXPIRED",
                      "error": "Cookie/session expired, requires re-login (simulated)",
                      "platform": "xiaohongshu", "need_verify": True},
            error="Cookie expired (simulated)")
        self._log(r); return r

    def simulate_db_locked(self):
        r = FaultInjectionResult(fault_type=FaultType.DB_LOCKED.value,
            injected=self.is_active(FaultType.DB_LOCKED),
            response={"success": False, "status": "DB_LOCKED",
                      "error": "database is locked (simulated)", "retry_after_ms": 1000},
            error="DB locked (simulated)")
        self._log(r); return r

    def simulate_network_jitter(self, base_delay_ms=100, jitter_ms=500):
        delay = 0
        if self.is_active(FaultType.NETWORK_JITTER):
            delay = base_delay_ms + random.randint(0, jitter_ms)
            time.sleep(min(delay, 50) / 1000)
        r = FaultInjectionResult(fault_type=FaultType.NETWORK_JITTER.value,
            injected=self.is_active(FaultType.NETWORK_JITTER),
            response={"success": True, "status": "OK_WITH_JITTER", "delay_ms": delay,
                      "jitter_applied": self.is_active(FaultType.NETWORK_JITTER)},
            delay_ms=delay)
        self._log(r); return r

    def run_with_fault(self, fn, ft, *args, **kwargs):
        fr = None
        if ft == FaultType.OSAI_UNAVAILABLE: fr = self.simulate_osai_unavailable()
        elif ft == FaultType.AI_TIMEOUT: fr = self.simulate_ai_timeout()
        elif ft == FaultType.COOKIE_EXPIRED: fr = self.simulate_cookie_expired()
        elif ft == FaultType.DB_LOCKED: fr = self.simulate_db_locked()
        elif ft == FaultType.NETWORK_JITTER: fr = self.simulate_network_jitter()
        if fr and fr.injected:
            return {"original_result": None, "fault_injected": True, "fault_type": ft.value, "fault_response": fr.to_dict()}
        try:
            return {"original_result": fn(*args, **kwargs), "fault_injected": False, "fault_type": ft.value, "fault_response": None}
        except Exception as e:
            return {"original_result": None, "fault_injected": False, "fault_type": ft.value, "fault_response": None, "error": str(e)}

    def get_log(self): return [r.to_dict() for r in self._injection_log]
    def stats(self):
        by_type = {}
        for r in self._injection_log: by_type[r.fault_type] = by_type.get(r.fault_type, 0) + 1
        return {"total_injections": len(self._injection_log), "active_faults": self.list_active(), "by_type": by_type}


_injector = None
def get_fault_injector():
    global _injector
    if _injector is None: _injector = FaultInjector()
    return _injector
