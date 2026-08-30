# -*- coding: utf-8 -*-
"""
XHS Runtime State 统一状态机（V2.0 基线 P0-1）

六态分层：
  AUTH_STATE      — 登录认证状态
  SESSION_STATE   — 浏览器会话状态
  PLATFORM_STATE  — 平台可达/风控状态
  COLLECTOR_STATE — 采集器运行状态
  CIRCUIT_STATE   — 熔断状态
  RECOVERY_STATE  — 恢复流程状态

核心原则：Cookie 存在 ≠ XHS 健康；必须真实分层检查，绝不把验证/风控伪装成 0 条。
本模块不依赖 topic_campaign，可被 collector.py / app.py / 前端全局复用。
"""

import json
import os
import time
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# 六态枚举定义
# ──────────────────────────────────────────────

class AuthState(Enum):
    VALID = "valid"           # 登录有效，Cookie 可用
    EXPIRED = "expired"       # 登录过期
    REQUIRED = "required"     # 需要重新登录
    UNKNOWN = "unknown"       # 尚未检查


class SessionState(Enum):
    COOKIE_PRESENT = "cookie_present"        # Cookie 文件存在
    BROWSER_CONNECTED = "browser_connected"  # CDP 浏览器已连接
    REAL_SESSION_VALID = "real_session_valid"  # 真实页面探活通过
    BROWSER_DISCONNECTED = "browser_disconnected"
    NO_COOKIE = "no_cookie"


class PlatformState(Enum):
    REACHABLE = "reachable"    # 平台正常可达
    BLOCKED = "blocked"        # 被阻断
    IP_RISK = "ip_risk"        # IP 风控（300012 等）
    VERIFY = "verify"          # 安全验证/扫码
    UNREACHABLE = "unreachable"


class CollectorState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    NO_NEW_DATA = "no_new_data"
    ERROR = "error"


class CircuitState(Enum):
    CLOSED = "closed"          # 正常放行
    OPEN = "open"              # 熔断阻断
    COOLING = "cooling"        # 冷却中（IP_RISK 计时）
    HALF_OPEN = "half_open"    # 半开探测（冷却结束，待小流量验证）


class RecoveryState(Enum):
    IDLE = "idle"
    QR_DISPLAYED = "qr_displayed"
    WAITING_SCAN = "waiting_scan"
    CHECKING = "checking"
    RECOVERED = "recovered"
    FAILED = "failed"


# ──────────────────────────────────────────────
# 统一运行时状态聚合类
# ──────────────────────────────────────────────

class XhsRuntimeState:
    """聚合六态，计算 overall，提供结构化输出。

    用法：
        state = XhsRuntimeState()
        state.load_circuit('/path/to/circuit.json')
        state.set_health_probe_result(healthy=True, detail={...})
        result = state.to_dict()
    """

    def __init__(self):
        self.auth = AuthState.UNKNOWN
        self.session = SessionState.NO_COOKIE
        self.platform = PlatformState.UNREACHABLE
        self.collector = CollectorState.IDLE
        self.circuit = CircuitState.CLOSED
        self.recovery = RecoveryState.IDLE
        self.last_check = None
        self.detail = {}
        self.circuit_file = None
        self.circuit_data = None

    # ── 熔断文件加载 ──────────────────────────

    def load_circuit(self, circuit_file):
        """从熔断 JSON 文件加载 CIRCUIT_STATE / PLATFORM_STATE / AUTH_STATE。

        NEED_VERIFY → CIRCUIT=OPEN, PLATFORM=VERIFY, AUTH=REQUIRED
        IP_RISK    → 未到 resume_at → COOLING；已到 → HALF_OPEN
        无文件     → CLOSED
        """
        self.circuit_file = circuit_file
        if not circuit_file or not os.path.exists(circuit_file):
            self.circuit = CircuitState.CLOSED
            self.circuit_data = None
            return
        try:
            with open(circuit_file, 'r', encoding='utf-8') as f:
                self.circuit_data = json.load(f)
        except Exception:
            self.circuit = CircuitState.CLOSED
            self.circuit_data = None
            return

        status = (self.circuit_data.get('status') or '').upper()
        if status == 'NEED_VERIFY':
            self.circuit = CircuitState.OPEN
            self.platform = PlatformState.VERIFY
            self.auth = AuthState.REQUIRED
        elif status == 'IP_RISK':
            ra = self.circuit_data.get('resume_at')
            if ra:
                try:
                    if datetime.now() < datetime.strptime(ra, '%Y-%m-%d %H:%M:%S'):
                        self.circuit = CircuitState.COOLING
                    else:
                        self.circuit = CircuitState.HALF_OPEN
                except Exception:
                    self.circuit = CircuitState.OPEN
            else:
                self.circuit = CircuitState.OPEN
            self.platform = PlatformState.IP_RISK
        else:
            self.circuit = CircuitState.CLOSED

    # ── 健康探活结果写入 ──────────────────────

    def set_health_probe_result(self, healthy, detail=None):
        """将 CDP 健康探活结果写入六态。

        healthy=True  → AUTH=VALID, SESSION=REAL_SESSION_VALID, PLATFORM=REACHABLE
        healthy=False → 根据 detail 中的 reason 细分 AUTH/SESSION/PLATFORM
        """
        self.last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if detail:
            self.detail.update(detail)
        if healthy:
            self.auth = AuthState.VALID
            self.session = SessionState.REAL_SESSION_VALID
            self.platform = PlatformState.REACHABLE
            if self.circuit in (CircuitState.OPEN, CircuitState.COOLING, CircuitState.HALF_OPEN):
                # 探活通过但熔断文件还在 → 标记 recovery=CHECKING，由调用方决定是否 clear
                self.recovery = RecoveryState.CHECKING
        else:
            reason = (detail or {}).get('reason', '') or (detail or {}).get('detail', '')
            rl = reason.lower()
            if any(k in rl for k in ('登录', 'login', '扫码', 'captcha', '验证')):
                self.auth = AuthState.REQUIRED
                self.platform = PlatformState.VERIFY
            elif any(k in rl for k in ('ip', '300012', '风险', '风控', '频繁')):
                self.platform = PlatformState.IP_RISK
            elif any(k in rl for k in ('连接', 'connect', 'cdp', '浏览器', 'browser', 'timeout', '超时')):
                self.session = SessionState.BROWSER_DISCONNECTED
                self.platform = PlatformState.UNREACHABLE
            else:
                self.session = SessionState.BROWSER_CONNECTED
                self.platform = PlatformState.BLOCKED
            self.recovery = RecoveryState.FAILED

    # ── 采集器状态 ────────────────────────────

    def set_collector(self, state, detail=None):
        if isinstance(state, CollectorState):
            self.collector = state
        else:
            try:
                self.collector = CollectorState(str(state).lower())
            except Exception:
                self.collector = CollectorState.ERROR
        if detail:
            self.detail.update(detail)

    # ── overall 计算 ───────────────────────────

    def compute_overall(self):
        """按优先级计算整体状态字符串。"""
        if self.circuit == CircuitState.OPEN:
            return "circuit_open"
        if self.circuit == CircuitState.COOLING:
            return "circuit_cooling"
        if self.circuit == CircuitState.HALF_OPEN:
            return "circuit_half_open"
        if self.auth in (AuthState.EXPIRED, AuthState.REQUIRED):
            return "auth_required"
        if self.platform in (PlatformState.VERIFY, PlatformState.IP_RISK, PlatformState.BLOCKED):
            return "platform_blocked"
        if self.platform == PlatformState.UNREACHABLE:
            return "platform_unreachable"
        if self.session != SessionState.REAL_SESSION_VALID and self.auth != AuthState.UNKNOWN:
            return "session_invalid"
        if self.collector == CollectorState.ERROR:
            return "collector_error"
        if self.auth == AuthState.UNKNOWN and self.platform == PlatformState.UNREACHABLE:
            return "not_checked"
        return "healthy"

    def is_healthy(self):
        return self.compute_overall() == "healthy"

    # ── 序列化 ────────────────────────────────

    def to_dict(self):
        return {
            "overall": self.compute_overall(),
            "healthy": self.is_healthy(),
            "auth_state": self.auth.value,
            "session_state": self.session.value,
            "platform_state": self.platform.value,
            "collector_state": self.collector.value,
            "circuit_state": self.circuit.value,
            "recovery_state": self.recovery.value,
            "last_check": self.last_check,
            "circuit": self.circuit_data,
            "detail": self.detail,
        }

    def to_json(self, **kwargs):
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)


# ──────────────────────────────────────────────
# 便捷函数：从熔断文件快速构建状态
# ──────────────────────────────────────────────

def state_from_circuit(circuit_file):
    """便捷函数：仅加载熔断文件，返回 XhsRuntimeState。"""
    s = XhsRuntimeState()
    s.load_circuit(circuit_file)
    return s


def state_from_probe(circuit_file, healthy, detail=None):
    """便捷函数：加载熔断 + 写入探活结果，返回 XhsRuntimeState。"""
    s = state_from_circuit(circuit_file)
    s.set_health_probe_result(healthy, detail)
    return s
