# -*- coding: utf-8 -*-
"""
Focus Policy — 通知策略
========================
定义通知抑制、路由与频率控制的策略配置。

策略维度：
  - silent_sources          : 始终静默的来源列表（只写日志）
  - important_event_types   : 升级为 IMPORTANT_SIGNAL 的事件类型
  - decision_event_types    : 升级为 HUMAN_DECISION 的事件类型
  - quiet_hours             : 静默期配置（开始/结束小时，24h 制）
  - max_notifications_per_minute : 每分钟最大通知数（频率控制）
  - user_preferences        : 用户自定义偏好（覆盖默认）
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class QuietHours:
    """静默期配置。

    在静默期内，仅 HUMAN_DECISION 可穿透通知；
    IMPORTANT_SIGNAL 降级为静默（写日志）；
    SILENT_PROGRESS 保持静默。
    """
    enabled: bool = False
    start_hour: int = 22      # 22:00 开始
    end_hour: int = 8         # 08:00 结束（跨夜）
    timezone: str = "Asia/Shanghai"

    def is_quiet_now(self, hour: Optional[int] = None) -> bool:
        """判断当前是否处于静默期。

        Args:
            hour: 指定小时（0-23），None 则使用系统当前小时

        Returns:
            True 表示处于静默期
        """
        if not self.enabled:
            return False
        if hour is None:
            from datetime import datetime
            hour = datetime.now().hour
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        # 跨夜：start_hour >= end_hour
        return hour >= self.start_hour or hour < self.end_hour


@dataclass
class FocusPolicy:
    """通知策略配置。

    控制哪些事件应该通知、以什么级别通知、何时抑制。
    """
    # 始终静默的来源（匹配 event["source"]）
    silent_sources: List[str] = field(default_factory=lambda: [
        "heartbeat",
        "progress_tick",
        "metric_snapshot",
        "cache_refresh",
        "log_rotation",
    ])

    # 升级为 IMPORTANT_SIGNAL 的事件类型
    important_event_types: List[str] = field(default_factory=lambda: [
        "anomaly",
        "risk_escalation",
        "trend_change",
        "performance_degrade",
        "task_warning",
        "data_quality_warning",
    ])

    # 升级为 HUMAN_DECISION 的事件类型（必须通知，不可抑制）
    decision_event_types: List[str] = field(default_factory=lambda: [
        "approval_required",
        "task_blocked",
        "risk_critical",
        "auth_expired",
        "collection_blocked",
        "data_missing_critical",
        "system_failure",
    ])

    # 静默期
    quiet_hours: QuietHours = field(default_factory=QuietHours)

    # 频率控制：每分钟最大通知数（按 source+level 维度）
    max_notifications_per_minute: int = 5

    # 用户自定义偏好（可覆盖上述任何字段）
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quiet_hours"] = asdict(self.quiet_hours)
        return d

    def is_silent_source(self, source: str) -> bool:
        """判断来源是否为静默来源。"""
        return source in self.silent_sources

    def is_decision_event(self, event_type: str) -> bool:
        """判断事件类型是否为人工决策事件。"""
        return event_type in self.decision_event_types

    def is_important_event(self, event_type: str) -> bool:
        """判断事件类型是否为重要事件。"""
        return event_type in self.important_event_types


def default_policy() -> FocusPolicy:
    """返回默认通知策略。

    Returns:
        FocusPolicy 实例，使用内置默认值
    """
    return FocusPolicy()


def load_policy(config: Optional[Dict[str, Any]] = None) -> FocusPolicy:
    """从配置字典加载通知策略。

    支持的配置键（均可选）：
      - silent_sources: list[str]
      - important_event_types: list[str]
      - decision_event_types: list[str]
      - quiet_hours: dict（enabled, start_hour, end_hour, timezone）
      - max_notifications_per_minute: int
      - user_preferences: dict

    Args:
        config: 配置字典，None 则返回默认策略

    Returns:
        FocusPolicy 实例
    """
    if not config:
        return default_policy()

    policy = default_policy()

    if isinstance(config.get("silent_sources"), list):
        policy.silent_sources = [str(s) for s in config["silent_sources"]]

    if isinstance(config.get("important_event_types"), list):
        policy.important_event_types = [str(s) for s in config["important_event_types"]]

    if isinstance(config.get("decision_event_types"), list):
        policy.decision_event_types = [str(s) for s in config["decision_event_types"]]

    if isinstance(config.get("max_notifications_per_minute"), int):
        val = config["max_notifications_per_minute"]
        if val > 0:
            policy.max_notifications_per_minute = val

    if isinstance(config.get("user_preferences"), dict):
        policy.user_preferences = dict(config["user_preferences"])

    qh_config = config.get("quiet_hours")
    if isinstance(qh_config, dict):
        if "enabled" in qh_config:
            policy.quiet_hours.enabled = bool(qh_config["enabled"])
        if "start_hour" in qh_config:
            try:
                policy.quiet_hours.start_hour = int(qh_config["start_hour"])
            except (TypeError, ValueError):
                pass
        if "end_hour" in qh_config:
            try:
                policy.quiet_hours.end_hour = int(qh_config["end_hour"])
            except (TypeError, ValueError):
                pass
        if "timezone" in qh_config:
            policy.quiet_hours.timezone = str(qh_config["timezone"])

    return policy
