# -*- coding: utf-8 -*-
"""统一动态调度子包：平台独立策略 + 纯决策 + 状态映射 + 旁路决策审计 + 平台隔离规划器。

第一版为影子模式：不替换生产采集主链、不门控固定时钟；经回归与确认后再灰度为门控。
"""
from .policy import PlatformSchedulePolicy, DEFAULT_POLICIES, build_default_policies
from .decision import ScheduleDecider, ScheduleDecision, PlatformScheduleState
from .planner import PlatformSchedulePlanner
from .store import ScheduleDecisionStore
from .gate import gate_should_run, gate_mode, canary_platforms
from . import state_map
import os as _os
import threading as _threading

_PLANNER = None
_PLANNER_LOCK = _threading.Lock()


def get_planner() -> PlatformSchedulePlanner:
    """进程级单例：scheduler 唤醒评估与采集结果回写共用同一内存状态，避免多实例互相覆盖状态文件。"""
    global _PLANNER
    if _PLANNER is None:
        with _PLANNER_LOCK:
            if _PLANNER is None:
                root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
                from db_paths import main_db_path
                store = ScheduleDecisionStore(main_db_path())
                _PLANNER = PlatformSchedulePlanner(
                    state_file=_os.path.join(root, "data", "schedule_state.json"), store=store)
    return _PLANNER


__all__ = [
    "PlatformSchedulePolicy", "DEFAULT_POLICIES", "build_default_policies",
    "ScheduleDecider", "ScheduleDecision", "PlatformScheduleState",
    "PlatformSchedulePlanner", "ScheduleDecisionStore", "state_map",
    "get_planner", "gate_should_run", "gate_mode", "canary_platforms",
]
