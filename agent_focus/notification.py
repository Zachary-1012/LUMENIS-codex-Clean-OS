# -*- coding: utf-8 -*-
"""
Notification Core — 通知核心模块
==================================
三层通知机制：
  - SILENT_PROGRESS  : 静默进度（只写日志，不打扰用户）
  - IMPORTANT_SIGNAL : 重要信号（弹 toast，非阻塞）
  - HUMAN_DECISION   : 人工决策（弹 modal，阻塞等待用户输入）

FocusProtector 负责：
  - should_notify()  : 基于级别+事件类型+用户偏好+频率控制决定是否通知
  - classify_event() : 将事件分类到三层
  - should_suppress(): 是否应抑制（低价值/重复/静默期）
  - rate_limit_check(): 频率控制

NotificationRouter 负责：
  - silent  只写日志
  - important 弹 toast
  - decision 弹 modal

设计原则：
  - HUMAN_DECISION 必须通知，不可被抑制或频率限制
  - SILENT_PROGRESS 默认不通知（只写日志）
  - 重复事件在时间窗口内抑制
  - 静默期内仅 HUMAN_DECISION 可穿透
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .policy import FocusPolicy, default_policy, load_policy


# ──────────────────────────────────────────────────────────────
# 枚举与数据结构
# ──────────────────────────────────────────────────────────────

class NotificationLevel(str, Enum):
    """通知级别枚举。"""
    SILENT_PROGRESS = "silent_progress"
    IMPORTANT_SIGNAL = "important_signal"
    HUMAN_DECISION = "human_decision"


# 级别权重
_LEVEL_ORDER: Dict[str, int] = {
    NotificationLevel.SILENT_PROGRESS.value: 0,
    NotificationLevel.IMPORTANT_SIGNAL.value: 1,
    NotificationLevel.HUMAN_DECISION.value: 2,
}


@dataclass
class NotificationEvent:
    """通知事件。

    携带完整的事件信息与可选的操作选项、证据引用。
    """
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    level: str = NotificationLevel.SILENT_PROGRESS.value
    title: str = ""
    message: str = ""
    source: str = ""
    event_type: str = ""
    requires_action: bool = False
    action_options: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    auto_dismiss_seconds: int = 0  # 0 表示不自动消失

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def level_rank(self) -> int:
        return _LEVEL_ORDER.get(self.level, 0)


# ──────────────────────────────────────────────────────────────
# FocusProtector
# ──────────────────────────────────────────────────────────────

class FocusProtector:
    """注意力保护器：决定是否通知、以什么级别通知。

    用法：
        protector = FocusProtector()
        if protector.should_notify("important_signal", event_dict):
            router.route(event)
    """

    # 重复事件抑制窗口（秒）
    DUPLICATE_WINDOW_SECONDS = 60

    def __init__(
        self,
        policy: Optional[FocusPolicy] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            policy: 通知策略，None 则使用默认策略
            logger: 日志记录器，None 则使用模块默认 logger
        """
        self._policy = policy or default_policy()
        self._logger = logger or logging.getLogger("agent_focus")
        self._lock = threading.Lock()
        # 频率控制：{(source, level): [timestamp, ...]}
        self._rate_buckets: Dict[tuple, List[float]] = {}
        # 重复事件抑制：{(source, event_type, title_hash): last_timestamp}
        self._last_seen: Dict[tuple, float] = {}

    @property
    def policy(self) -> FocusPolicy:
        return self._policy

    def update_policy(self, policy: FocusPolicy) -> None:
        """更新通知策略。"""
        with self._lock:
            self._policy = policy

    def should_notify(
        self,
        level: NotificationLevel,
        event: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """主判断函数：基于级别+事件类型+用户偏好+频率控制决定是否通知。

        Args:
            level: 通知级别
            event: 事件字典（可选，包含 source, event_type, title 等）

        Returns:
            True 表示应该通知用户，False 表示应抑制
        """
        event = event or {}

        # HUMAN_DECISION 必须通知，不可抑制
        if level == NotificationLevel.HUMAN_DECISION:
            return True

        # SILENT_PROGRESS 默认不通知
        if level == NotificationLevel.SILENT_PROGRESS:
            return False

        # IMPORTANT_SIGNAL：检查抑制条件
        if self.should_suppress(event):
            return False

        # 频率控制
        source = str(event.get("source", "unknown"))
        if not self.rate_limit_check(source, level):
            self._logger.debug(
                "Rate limited notification: source=%s level=%s", source, level.value
            )
            return False

        return True

    def classify_event(self, event: Dict[str, Any]) -> NotificationLevel:
        """将事件分类到三层通知级别。

        分类优先级：
          1. event 中显式指定 level
          2. event_type 匹配 decision_event_types → HUMAN_DECISION
          3. event_type 匹配 important_event_types → IMPORTANT_SIGNAL
          4. source 匹配 silent_sources → SILENT_PROGRESS
          5. requires_action=True → HUMAN_DECISION
          6. 默认 SILENT_PROGRESS

        Args:
            event: 事件字典

        Returns:
            NotificationLevel
        """
        # 显式指定级别
        explicit_level = event.get("level")
        if explicit_level:
            if isinstance(explicit_level, NotificationLevel):
                return explicit_level
            level_str = str(explicit_level).lower()
            for lvl in NotificationLevel:
                if lvl.value == level_str:
                    return lvl

        event_type = str(event.get("event_type", "")).lower()
        source = str(event.get("source", "")).lower()

        # 决策事件
        if self._policy.is_decision_event(event_type):
            return NotificationLevel.HUMAN_DECISION

        # 需要操作的事件
        if event.get("requires_action") is True:
            return NotificationLevel.HUMAN_DECISION

        # 重要事件
        if self._policy.is_important_event(event_type):
            return NotificationLevel.IMPORTANT_SIGNAL

        # 静默来源
        if self._policy.is_silent_source(source):
            return NotificationLevel.SILENT_PROGRESS

        # 默认静默
        return NotificationLevel.SILENT_PROGRESS

    def should_suppress(self, event: Dict[str, Any]) -> bool:
        """判断是否应抑制通知（低价值/重复/静默期）。

        注意：HUMAN_DECISION 级别不会被此函数抑制（由 should_notify 短路）。

        Args:
            event: 事件字典

        Returns:
            True 表示应抑制
        """
        source = str(event.get("source", "")).lower()
        event_type = str(event.get("event_type", "")).lower()
        title = str(event.get("title", ""))

        # 静默来源
        if self._policy.is_silent_source(source):
            return True

        # 静默期（仅 HUMAN_DECISION 可穿透，此处非 HUMAN_DECISION）
        if self._policy.quiet_hours.is_quiet_now():
            return True

        # 重复事件抑制
        title_hash = hash(title) & 0xFFFFFFFF
        key = (source, event_type, title_hash)
        now = time.time()
        with self._lock:
            last = self._last_seen.get(key, 0)
            if now - last < self.DUPLICATE_WINDOW_SECONDS:
                return True
            self._last_seen[key] = now

        return False

    def rate_limit_check(
        self, source: str, level: NotificationLevel
    ) -> bool:
        """频率控制：检查该 source+level 是否超过每分钟最大通知数。

        HUMAN_DECISION 不受频率限制。

        Args:
            source: 事件来源
            level: 通知级别

        Returns:
            True 表示允许通知（未超限），False 表示应限流
        """
        if level == NotificationLevel.HUMAN_DECISION:
            return True

        max_per_min = self._policy.max_notifications_per_minute
        if max_per_min <= 0:
            return True

        key = (source, level.value)
        now = time.time()
        cutoff = now - 60.0

        with self._lock:
            bucket = self._rate_buckets.get(key, [])
            # 清理过期记录
            bucket = [t for t in bucket if t > cutoff]
            if len(bucket) >= max_per_min:
                self._rate_buckets[key] = bucket
                return False
            bucket.append(now)
            self._rate_buckets[key] = bucket
            return True

    def reset_rate_limits(self) -> None:
        """重置频率控制状态（仅测试用）。"""
        with self._lock:
            self._rate_buckets.clear()
            self._last_seen.clear()


# ──────────────────────────────────────────────────────────────
# NotificationRouter
# ──────────────────────────────────────────────────────────────

class NotificationRouter:
    """通知路由器：将通知事件路由到正确渠道。

    路由规则：
      - SILENT_PROGRESS → 只写日志（log_sink）
      - IMPORTANT_SIGNAL → 弹 toast（toast_sink）
      - HUMAN_DECISION   → 弹 modal（modal_sink）

    每个 sink 是一个可调用对象 callback(event: NotificationEvent) -> None。
    未设置的 sink 降级为写日志。
    """

    def __init__(
        self,
        protector: Optional[FocusProtector] = None,
        log_sink: Optional[Callable[[NotificationEvent], None]] = None,
        toast_sink: Optional[Callable[[NotificationEvent], None]] = None,
        modal_sink: Optional[Callable[[NotificationEvent], None]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            protector: 注意力保护器，None 则使用默认
            log_sink: 静默日志渠道回调
            toast_sink: Toast 通知渠道回调
            modal_sink: Modal 通知渠道回调
            logger: 日志记录器
        """
        self._protector = protector or FocusProtector()
        self._logger = logger or logging.getLogger("agent_focus.router")
        self._log_sink = log_sink or self._default_log_sink
        self._toast_sink = toast_sink
        self._modal_sink = modal_sink
        # 已路由事件记录（用于审计）
        self._routed: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    @property
    def protector(self) -> FocusProtector:
        return self._protector

    def route(self, event: NotificationEvent) -> bool:
        """路由通知事件到正确渠道。

        Args:
            event: 通知事件

        Returns:
            True 表示已通过保护器并路由（或静默记录），False 表示被抑制
        """
        level = NotificationLevel(event.level)

        # 通过保护器判断是否需要用户可见通知
        event_dict = event.to_dict()
        should_show = self._protector.should_notify(level, event_dict)

        record = {
            "event_id": event.event_id,
            "level": event.level,
            "source": event.source,
            "event_type": event.event_type,
            "shown_to_user": should_show,
            "channel": "silent",
            "timestamp": event.timestamp,
        }

        try:
            if level == NotificationLevel.HUMAN_DECISION:
                # 必须路由到 modal
                if self._modal_sink:
                    self._modal_sink(event)
                else:
                    self._default_log_sink(event)
                record["channel"] = "modal"
            elif level == NotificationLevel.IMPORTANT_SIGNAL and should_show:
                # 路由到 toast
                if self._toast_sink:
                    self._toast_sink(event)
                else:
                    self._default_log_sink(event)
                record["channel"] = "toast"
            else:
                # SILENT_PROGRESS 或被抑制的 IMPORTANT → 只写日志
                self._log_sink(event)
                record["channel"] = "silent"
        except Exception as e:
            self._logger.error("Notification route error: %s", e)
            record["channel"] = "error"
            record["error"] = str(e)

        with self._lock:
            self._routed.append(record)
        return should_show

    def route_from_dict(self, event_dict: Dict[str, Any]) -> bool:
        """从字典构建事件并路由（自动分类级别）。

        Args:
            event_dict: 事件字典

        Returns:
            True 表示已通知用户，False 表示被抑制或静默
        """
        level = self._protector.classify_event(event_dict)
        event = NotificationEvent(
            level=level.value,
            title=str(event_dict.get("title", "")),
            message=str(event_dict.get("message", "")),
            source=str(event_dict.get("source", "")),
            event_type=str(event_dict.get("event_type", "")),
            requires_action=bool(event_dict.get("requires_action", False)),
            action_options=list(event_dict.get("action_options", [])),
            evidence_refs=list(event_dict.get("evidence_refs", [])),
            auto_dismiss_seconds=int(event_dict.get("auto_dismiss_seconds", 0)),
        )
        return self.route(event)

    def get_routed_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取已路由事件历史。"""
        with self._lock:
            return list(self._routed[-limit:])

    def clear_history(self) -> None:
        """清空路由历史（仅测试用）。"""
        with self._lock:
            self._routed.clear()

    def _default_log_sink(self, event: NotificationEvent) -> None:
        """默认日志 sink。"""
        self._logger.info(
            "[%s] %s: %s (source=%s, type=%s)",
            event.level, event.title, event.message,
            event.source, event.event_type,
        )


# ──────────────────────────────────────────────────────────────
# 模块级便捷函数
# ──────────────────────────────────────────────────────────────

_default_protector: Optional[FocusProtector] = None


def _get_default_protector() -> FocusProtector:
    global _default_protector
    if _default_protector is None:
        _default_protector = FocusProtector()
    return _default_protector


def should_notify(level: str, event: Optional[Dict[str, Any]] = None) -> bool:
    """模块级便捷函数：判断是否应通知。

    Args:
        level: 通知级别字符串（silent_progress / important_signal / human_decision）
        event: 事件字典

    Returns:
        True 表示应该通知
    """
    level_str = str(level).lower()
    level_enum = NotificationLevel.SILENT_PROGRESS
    for lvl in NotificationLevel:
        if lvl.value == level_str:
            level_enum = lvl
            break
    return _get_default_protector().should_notify(level_enum, event)
