# -*- coding: utf-8 -*-
"""
IP 风控状态机（PROJECT_STATUS P0 项 4）
=========================================
归属：Z-Brand Core / P0 采集健康中心 / IP Risk State Machine
目标：300012/验证/IP风控进入状态机、熔断、冷却、告警体系。

状态定义（5态）：
  NORMAL      — 正常采集，无风险
  WATCH       — 观察态（出现偶发风控信号，未达熔断阈值）
  SUSPENDED   — 暂停态（连续风控信号，主动暂停采集，等待冷却）
  BLOCKED     — 熔断态（触发硬熔断，完全停止该平台/IP采集，需人工或冷却恢复）
  COOLDOWN    — 冷却态（熔断后倒计时冷却，冷却结束后半开探测，成功则回 NORMAL）

状态转换规则：
  NORMAL → WATCH          : 出现风控信号（300012/验证码/IP限制），连续次数 < 熔断阈值
  WATCH → NORMAL          : 连续成功次数 >= 恢复阈值
  WATCH → SUSPENDED       : 连续风控信号达到暂停阈值
  SUSPENDED → COOLDOWN    : 主动进入冷却（或连续风控达到熔断阈值）
  SUSPENDED → WATCH       : 冷却/暂停期结束，半开探测成功
  COOLDOWN → WATCH        : 冷却倒计时结束，半开探测成功
  COOLDOWN → BLOCKED      : 冷却结束后探测仍失败，或冷却期间再次触发风控
  BLOCKED → COOLDOWN      : 人工确认后进入冷却（或自动冷却到期）
  BLOCKED → NORMAL        : 人工解除（需明确确认，禁止自动解除 BLOCKED）

核心硬红线：
  1. 禁止伪造成功：风控信号必须如实记录，不得把 300012 当成 0 条成功
  2. 禁止绕过风控：不破解验证码、不模拟人工滑动、不切换 IP 绕过
  3. BLOCKED 必须人工确认才能解除，冷却只能回 WATCH 不能直接回 NORMAL
  4. 状态变更必须记录告警（日志 + 可选通知）
  5. 状态持久化到 SQLite，重启后恢复
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 状态与事件枚举
# ============================================================

class IPRiskState(str, Enum):
    """IP 风控状态。"""
    NORMAL = "normal"
    WATCH = "watch"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    COOLDOWN = "cooldown"


class IPRiskEvent(str, Enum):
    """触发状态转换的事件。"""
    RISK_SIGNAL = "risk_signal"              # 风控信号（300012/验证码/IP限制）
    SUCCESS = "success"                        # 采集成功
    SUSPEND = "suspend"                        # 主动暂停
    ENTER_COOLDOWN = "enter_cooldown"          # 进入冷却
    COOLDOWN_END = "cooldown_end"              # 冷却结束
    PROBE_SUCCESS = "probe_success"            # 半开探测成功
    PROBE_FAIL = "probe_fail"                  # 半开探测失败
    MANUAL_UNBLOCK = "manual_unblock"          # 人工解除熔断
    MANUAL_RESET = "manual_reset"              # 人工重置（管理员）


class RiskSignalType(str, Enum):
    """风控信号类型。"""
    CODE_300012 = "300012"               # 小红书 300012 风控码
    CAPTCHA = "captcha"                   # 验证码
    IP_LIMITED = "ip_limited"             # IP 被限制
    LOGIN_REQUIRED = "login_required"     # 需要登录
    SESSION_EXPIRED = "session_expired"   # 会话过期
    RATE_LIMITED = "rate_limited"         # 频率限制
    VERIFICATION_REQUIRED = "verification_required"  # 需要验证
    UNKNOWN = "unknown"                    # 未知风控


# ============================================================
# 配置
# ============================================================

@dataclass
class IPRiskConfig:
    """IP 风控状态机配置（可按平台覆盖）。"""
    # 阈值
    watch_threshold: int = 2           # 连续风控信号达到此值进入 WATCH
    suspend_threshold: int = 4         # 连续风控信号达到此值进入 SUSPENDED
    block_threshold: int = 6           # 连续风控信号达到此值进入 BLOCKED
    recovery_threshold: int = 3        # 连续成功达到此值从 WATCH 回 NORMAL

    # 冷却时间（秒）
    cooldown_duration: int = 2700      # 冷却时长（默认 45 分钟）
    suspended_cooldown: int = 900       # SUSPENDED 自动冷却时长（15 分钟）

    # 半开探测
    probe_max_attempts: int = 3         # 冷却后最大探测次数
    probe_interval: int = 60             # 探测间隔（秒）

    # 告警
    alert_on_state_change: bool = True   # 状态变更时告警
    alert_on_block: bool = True           # 进入 BLOCKED 时告警

    # 数据库路径
    db_path: str = ""

    def __post_init__(self):
        if not self.db_path:
            self.db_path = os.environ.get(
                "ZBC_DB_PATH",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "monitor.db")
            )


# ============================================================
# 状态记录
# ============================================================

@dataclass
class IPRiskStateRecord:
    """单个平台/IP 的风控状态记录。"""
    platform: str
    state: str = IPRiskState.NORMAL.value
    consecutive_risk_signals: int = 0
    consecutive_successes: int = 0
    total_risk_signals: int = 0
    last_risk_signal: str = ""
    last_risk_type: str = ""
    last_signal_time: str = ""
    state_entered_at: str = ""
    cooldown_until: str = ""           # 冷却结束时间
    cooldown_attempts: int = 0          # 冷却探测次数
    blocked_by: str = ""                # 触发 BLOCKED 的原因
    last_alert_time: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StateTransition:
    """状态转换记录（审计日志）。"""
    id: int = 0
    platform: str = ""
    from_state: str = ""
    to_state: str = ""
    event: str = ""
    risk_type: str = ""
    reason: str = ""
    consecutive_signals: int = 0
    created_at: str = ""


# ============================================================
# 告警回调
# ============================================================

_alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []


def register_alert_callback(callback: Callable[[Dict[str, Any]], None]) -> None:
    """注册告警回调（用于微信通知/日志/前端推送）。"""
    _alert_callbacks.append(callback)


def _trigger_alert(alert_type: str, platform: str, state: str,
                    reason: str, details: Optional[Dict] = None) -> None:
    """触发告警（调用所有注册的回调）。"""
    alert = {
        "type": alert_type,
        "platform": platform,
        "state": state,
        "reason": reason,
        "details": details or {},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    logger.warning(f"[IPRiskAlert] {alert_type}: platform={platform}, state={state}, reason={reason}")
    for callback in _alert_callbacks:
        try:
            callback(alert)
        except Exception as e:
            logger.error(f"[IPRiskAlert] 告警回调失败: {e}")


# ============================================================
# IP 风控状态机
# ============================================================

class IPRiskStateMachine:
    """IP 风控状态机（单例，按平台管理状态）。

    用法：
        sm = IPRiskStateMachine()
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, "检测到300012")
        state = sm.get_state("xiaohongshu")
        if state == IPRiskState.BLOCKED:
            # 拒绝采集
            pass
    """

    _instance: Optional["IPRiskStateMachine"] = None
    _lock = threading.RLock()

    def __new__(cls, config: Optional[IPRiskConfig] = None) -> "IPRiskStateMachine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[IPRiskConfig] = None):
        if self._initialized:
            return
        self._initialized = True
        self.config = config or IPRiskConfig()
        self._states: Dict[str, IPRiskStateRecord] = {}
        self._ensure_table()
        self._load_all_states()

    # ── 数据库 ────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.config.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        """确保状态表和转换日志表存在。"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ip_risk_states (
                    platform TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'normal',
                    consecutive_risk_signals INTEGER DEFAULT 0,
                    consecutive_successes INTEGER DEFAULT 0,
                    total_risk_signals INTEGER DEFAULT 0,
                    last_risk_signal TEXT DEFAULT '',
                    last_risk_type TEXT DEFAULT '',
                    last_signal_time TEXT DEFAULT '',
                    state_entered_at TEXT DEFAULT '',
                    cooldown_until TEXT DEFAULT '',
                    cooldown_attempts INTEGER DEFAULT 0,
                    blocked_by TEXT DEFAULT '',
                    last_alert_time TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    updated_at TEXT DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ip_risk_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    event TEXT NOT NULL,
                    risk_type TEXT DEFAULT '',
                    reason TEXT DEFAULT '',
                    consecutive_signals INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ip_risk_transitions_platform ON ip_risk_transitions(platform)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ip_risk_transitions_created ON ip_risk_transitions(created_at)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[IPRiskStateMachine] 创建表失败: {e}")

    def _load_all_states(self) -> None:
        """从数据库加载所有平台状态。"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM ip_risk_states")
            for row in cur.fetchall():
                record = IPRiskStateRecord(
                    platform=row["platform"],
                    state=row["state"],
                    consecutive_risk_signals=row["consecutive_risk_signals"],
                    consecutive_successes=row["consecutive_successes"],
                    total_risk_signals=row["total_risk_signals"],
                    last_risk_signal=row["last_risk_signal"],
                    last_risk_type=row["last_risk_type"],
                    last_signal_time=row["last_signal_time"],
                    state_entered_at=row["state_entered_at"],
                    cooldown_until=row["cooldown_until"],
                    cooldown_attempts=row["cooldown_attempts"],
                    blocked_by=row["blocked_by"],
                    last_alert_time=row["last_alert_time"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                self._states[row["platform"]] = record
            conn.close()
            logger.info(f"[IPRiskStateMachine] 已加载 {len(self._states)} 个平台的风控状态")
        except Exception as e:
            logger.error(f"[IPRiskStateMachine] 加载状态失败: {e}")

    def _save_state(self, record: IPRiskStateRecord) -> None:
        """保存平台状态到数据库。"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO ip_risk_states
                (platform, state, consecutive_risk_signals, consecutive_successes,
                 total_risk_signals, last_risk_signal, last_risk_type, last_signal_time,
                 state_entered_at, cooldown_until, cooldown_attempts, blocked_by,
                 last_alert_time, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.platform, record.state, record.consecutive_risk_signals,
                record.consecutive_successes, record.total_risk_signals,
                record.last_risk_signal, record.last_risk_type, record.last_signal_time,
                record.state_entered_at, record.cooldown_until, record.cooldown_attempts,
                record.blocked_by, record.last_alert_time,
                json.dumps(record.metadata, ensure_ascii=False), now,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[IPRiskStateMachine] 保存状态失败: {e}")

    def _log_transition(self, platform: str, from_state: str, to_state: str,
                          event: str, risk_type: str, reason: str,
                          consecutive_signals: int) -> None:
        """记录状态转换审计日志。"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ip_risk_transitions
                (platform, from_state, to_state, event, risk_type, reason, consecutive_signals, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (platform, from_state, to_state, event, risk_type, reason, consecutive_signals, now))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[IPRiskStateMachine] 记录转换日志失败: {e}")

    # ── 状态查询 ──────────────────────────────────────────────

    def get_state(self, platform: str) -> IPRiskState:
        """获取平台当前风控状态。"""
        with self._lock:
            record = self._states.get(platform)
            if not record:
                return IPRiskState.NORMAL
            # 检查冷却是否到期
            if record.state == IPRiskState.COOLDOWN.value and record.cooldown_until:
                now = datetime.now()
                try:
                    cooldown_end = datetime.strptime(record.cooldown_until, "%Y-%m-%d %H:%M:%S")
                    if now >= cooldown_end:
                        # 冷却到期，自动回 WATCH（等待半开探测）
                        self._transition(platform, IPRiskState.COOLDOWN, IPRiskState.WATCH,
                                         IPRiskEvent.COOLDOWN_END, "", "冷却倒计时结束，进入观察态等待探测")
                except (ValueError, TypeError):
                    pass
            return IPRiskState(record.state)

    def get_record(self, platform: str) -> IPRiskStateRecord:
        """获取平台完整状态记录。"""
        with self._lock:
            return self._states.get(platform, IPRiskStateRecord(platform=platform))

    def is_blocked(self, platform: str) -> bool:
        """平台是否被熔断（BLOCKED 或 COOLDOWN）。"""
        state = self.get_state(platform)
        return state in (IPRiskState.BLOCKED, IPRiskState.COOLDOWN, IPRiskState.SUSPENDED)

    def can_collect(self, platform: str) -> bool:
        """是否允许采集（NORMAL 或 WATCH 状态允许，SUSPENDED/BLOCKED/COOLDOWN 拒绝）。"""
        state = self.get_state(platform)
        return state in (IPRiskState.NORMAL, IPRiskState.WATCH)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台状态摘要（API 用）。"""
        with self._lock:
            return {
                platform: {
                    "state": record.state,
                    "consecutive_risk_signals": record.consecutive_risk_signals,
                    "total_risk_signals": record.total_risk_signals,
                    "last_risk_type": record.last_risk_type,
                    "last_signal_time": record.last_signal_time,
                    "cooldown_until": record.cooldown_until,
                    "blocked_by": record.blocked_by,
                }
                for platform, record in self._states.items()
            }

    # ── 状态转换核心 ───────────────────────────────────────────

    def _transition(self, platform: str, from_state: IPRiskState,
                     to_state: IPRiskState, event: IPRiskEvent,
                     risk_type: str, reason: str) -> None:
        """执行状态转换（内部方法，需持锁调用）。"""
        record = self._states.get(platform, IPRiskStateRecord(platform=platform))
        old_state = record.state

        if old_state == to_state.value:
            return  # 状态未变化

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record.state = to_state.value
        record.state_entered_at = now

        # 进入 COOLDOWN 时设置冷却结束时间
        if to_state == IPRiskState.COOLDOWN:
            cooldown_end = datetime.now().timestamp() + self.config.cooldown_duration
            record.cooldown_until = datetime.fromtimestamp(cooldown_end).strftime("%Y-%m-%d %H:%M:%S")
            record.cooldown_attempts = 0

        # 进入 BLOCKED 时记录原因
        if to_state == IPRiskState.BLOCKED:
            record.blocked_by = reason or f"连续风控信号达到阈值({self.config.block_threshold})"

        # 回 NORMAL 时重置连续计数（WATCH 不重置，因为仍在观察风控信号）
        if to_state == IPRiskState.NORMAL:
            record.consecutive_risk_signals = 0
            record.consecutive_successes = 0
            record.cooldown_until = ""
            record.blocked_by = ""
        elif to_state == IPRiskState.WATCH:
            record.cooldown_until = ""
            record.blocked_by = ""

        self._states[platform] = record
        self._save_state(record)
        self._log_transition(platform, old_state, to_state.value, event.value,
                              risk_type, reason, record.consecutive_risk_signals)

        # 告警
        if self.config.alert_on_state_change:
            alert_type = "ip_risk_blocked" if to_state == IPRiskState.BLOCKED else "ip_risk_state_change"
            _trigger_alert(alert_type, platform, to_state.value, reason, {
                "from_state": old_state,
                "event": event.value,
                "consecutive_signals": record.consecutive_risk_signals,
            })

        logger.info(f"[IPRiskStateMachine] {platform}: {old_state} → {to_state.value} "
                     f"(event={event.value}, reason={reason})")

    # ── 公共 API ───────────────────────────────────────────────

    def record_risk_signal(self, platform: str, risk_type: RiskSignalType,
                             reason: str = "") -> IPRiskState:
        """记录风控信号，驱动状态转换。

        这是核心入口：采集链路检测到 300012/验证码/IP限制时调用。

        Args:
            platform: 平台标识（xiaohongshu/douyin/weibo/...）
            risk_type: 风控信号类型
            reason: 详细原因

        Returns:
            转换后的新状态
        """
        with self._lock:
            record = self._states.get(platform, IPRiskStateRecord(platform=platform))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 更新信号计数
            record.consecutive_risk_signals += 1
            record.consecutive_successes = 0
            record.total_risk_signals += 1
            record.last_risk_signal = reason
            record.last_risk_type = risk_type.value
            record.last_signal_time = now
            self._states[platform] = record
            self._save_state(record)

            current_state = IPRiskState(record.state)

            # 状态转换逻辑
            if current_state == IPRiskState.NORMAL:
                if record.consecutive_risk_signals >= self.config.watch_threshold:
                    self._transition(platform, IPRiskState.NORMAL, IPRiskState.WATCH,
                                     IPRiskEvent.RISK_SIGNAL, risk_type.value,
                                     f"连续风控信号 {record.consecutive_risk_signals} 次，进入观察态")
            elif current_state == IPRiskState.WATCH:
                if record.consecutive_risk_signals >= self.config.suspend_threshold:
                    self._transition(platform, IPRiskState.WATCH, IPRiskState.SUSPENDED,
                                     IPRiskEvent.RISK_SIGNAL, risk_type.value,
                                     f"连续风控信号 {record.consecutive_risk_signals} 次，主动暂停")
                elif record.consecutive_risk_signals >= self.config.block_threshold:
                    self._transition(platform, IPRiskState.WATCH, IPRiskState.BLOCKED,
                                     IPRiskEvent.RISK_SIGNAL, risk_type.value,
                                     f"连续风控信号 {record.consecutive_risk_signals} 次，触发熔断")
            elif current_state == IPRiskState.SUSPENDED:
                if record.consecutive_risk_signals >= self.config.block_threshold:
                    self._transition(platform, IPRiskState.SUSPENDED, IPRiskState.BLOCKED,
                                     IPRiskEvent.RISK_SIGNAL, risk_type.value,
                                     f"暂停期间再次触发风控（{record.consecutive_risk_signals} 次），升级为熔断")
                else:
                    # SUSPENDED 期间再次风控，进入冷却
                    self._transition(platform, IPRiskState.SUSPENDED, IPRiskState.COOLDOWN,
                                     IPRiskEvent.ENTER_COOLDOWN, risk_type.value,
                                     "暂停期间再次触发风控，进入冷却")
            elif current_state == IPRiskState.COOLDOWN:
                # 冷却期间再次触发风控，升级为 BLOCKED
                self._transition(platform, IPRiskState.COOLDOWN, IPRiskState.BLOCKED,
                                 IPRiskEvent.RISK_SIGNAL, risk_type.value,
                                 "冷却期间再次触发风控，升级为熔断（需人工解除）")

            return self.get_state(platform)

    def record_success(self, platform: str) -> IPRiskState:
        """记录采集成功，驱动恢复转换。

        Args:
            platform: 平台标识

        Returns:
            转换后的新状态
        """
        with self._lock:
            record = self._states.get(platform, IPRiskStateRecord(platform=platform))
            record.consecutive_successes += 1
            record.consecutive_risk_signals = max(0, record.consecutive_risk_signals - 1)
            self._states[platform] = record
            self._save_state(record)

            current_state = IPRiskState(record.state)

            if current_state == IPRiskState.WATCH:
                if record.consecutive_successes >= self.config.recovery_threshold:
                    self._transition(platform, IPRiskState.WATCH, IPRiskState.NORMAL,
                                     IPRiskEvent.SUCCESS, "",
                                     f"连续成功 {record.consecutive_successes} 次，恢复正常")
            # SUSPENDED/BLOCKED/COOLDOWN 状态下的成功不自动恢复，需半开探测

            return self.get_state(platform)

    def enter_cooldown(self, platform: str, reason: str = "主动进入冷却") -> IPRiskState:
        """主动进入冷却状态。"""
        with self._lock:
            current = self.get_state(platform)
            if current in (IPRiskState.SUSPENDED, IPRiskState.WATCH):
                self._transition(platform, current, IPRiskState.COOLDOWN,
                                 IPRiskEvent.ENTER_COOLDOWN, "", reason)
            return self.get_state(platform)

    def probe_success(self, platform: str) -> IPRiskState:
        """半开探测成功（冷却后小流量验证通过）。"""
        with self._lock:
            current = self.get_state(platform)
            if current == IPRiskState.COOLDOWN:
                self._transition(platform, IPRiskState.COOLDOWN, IPRiskState.WATCH,
                                 IPRiskEvent.PROBE_SUCCESS, "", "半开探测成功，进入观察态")
            elif current == IPRiskState.SUSPENDED:
                self._transition(platform, IPRiskState.SUSPENDED, IPRiskState.WATCH,
                                 IPRiskEvent.PROBE_SUCCESS, "", "探测成功，进入观察态")
            return self.get_state(platform)

    def probe_fail(self, platform: str, reason: str = "半开探测失败") -> IPRiskState:
        """半开探测失败（冷却后验证仍有风控）。"""
        with self._lock:
            current = self.get_state(platform)
            record = self._states.get(platform, IPRiskStateRecord(platform=platform))
            record.cooldown_attempts += 1
            self._states[platform] = record
            self._save_state(record)

            if current == IPRiskState.COOLDOWN:
                if record.cooldown_attempts >= self.config.probe_max_attempts:
                    self._transition(platform, IPRiskState.COOLDOWN, IPRiskState.BLOCKED,
                                     IPRiskEvent.PROBE_FAIL, "",
                                     f"探测失败 {record.cooldown_attempts} 次，升级为熔断（需人工解除）")
                else:
                    # 重新冷却
                    cooldown_end = datetime.now().timestamp() + self.config.cooldown_duration
                    record.cooldown_until = datetime.fromtimestamp(cooldown_end).strftime("%Y-%m-%d %H:%M:%S")
                    self._save_state(record)
                    logger.info(f"[IPRiskStateMachine] {platform}: 探测失败，重新冷却至 {record.cooldown_until}")
            return self.get_state(platform)

    def manual_unblock(self, platform: str, reason: str = "人工解除熔断") -> IPRiskState:
        """人工解除熔断（BLOCKED → COOLDOWN，需明确确认）。

        硬红线：BLOCKED 不能直接回 NORMAL，必须先经过 COOLDOWN → WATCH → NORMAL。
        """
        with self._lock:
            current = self.get_state(platform)
            if current == IPRiskState.BLOCKED:
                self._transition(platform, IPRiskState.BLOCKED, IPRiskState.COOLDOWN,
                                 IPRiskEvent.MANUAL_UNBLOCK, "", reason)
                _trigger_alert("ip_risk_manual_unblock", platform, IPRiskState.COOLDOWN.value, reason)
            return self.get_state(platform)

    def manual_reset(self, platform: str, reason: str = "管理员重置") -> IPRiskState:
        """管理员强制重置（直接回 NORMAL，仅限紧急情况）。"""
        with self._lock:
            record = self._states.get(platform, IPRiskStateRecord(platform=platform))
            old_state = record.state
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record.state = IPRiskState.NORMAL.value
            record.consecutive_risk_signals = 0
            record.consecutive_successes = 0
            record.cooldown_until = ""
            record.blocked_by = ""
            record.state_entered_at = now
            self._states[platform] = record
            self._save_state(record)
            self._log_transition(platform, old_state, IPRiskState.NORMAL.value,
                                  IPRiskEvent.MANUAL_RESET.value, "", reason, 0)
            _trigger_alert("ip_risk_manual_reset", platform, IPRiskState.NORMAL.value, reason)
            return IPRiskState.NORMAL

    def get_transition_history(self, platform: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取平台状态转换历史（审计用）。"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM ip_risk_transitions
                WHERE platform = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (platform, limit))
            history = [dict(row) for row in cur.fetchall()]
            conn.close()
            return history
        except Exception as e:
            logger.error(f"[IPRiskStateMachine] 获取转换历史失败: {e}")
            return []


# ============================================================
# 便捷函数
# ============================================================

def get_ip_risk_state_machine() -> IPRiskStateMachine:
    """获取 IP 风控状态机单例。"""
    return IPRiskStateMachine()


def check_and_record_risk(platform: str, risk_signal: str,
                            reason: str = "") -> Dict[str, Any]:
    """便捷函数：检测风控信号并记录，返回是否允许继续采集。

    Args:
        platform: 平台标识
        risk_signal: 风控信号（300012/captcha/ip_limited/...）
        reason: 详细原因

    Returns:
        {"can_continue": bool, "state": str, "reason": str}
    """
    sm = get_ip_risk_state_machine()

    # 映射风控信号类型
    signal_map = {
        "300012": RiskSignalType.CODE_300012,
        "captcha": RiskSignalType.CAPTCHA,
        "ip_limited": RiskSignalType.IP_LIMITED,
        "login_required": RiskSignalType.LOGIN_REQUIRED,
        "session_expired": RiskSignalType.SESSION_EXPIRED,
        "rate_limited": RiskSignalType.RATE_LIMITED,
        "verification_required": RiskSignalType.VERIFICATION_REQUIRED,
    }
    risk_type = signal_map.get(risk_signal.lower(), RiskSignalType.UNKNOWN)

    new_state = sm.record_risk_signal(platform, risk_type, reason)
    can_continue = sm.can_collect(platform)

    return {
        "can_continue": can_continue,
        "state": new_state.value,
        "is_blocked": sm.is_blocked(platform),
        "reason": reason,
    }
