# -*- coding: utf-8 -*-
"""统一动态调度决策器（纯规则、无 IO、不触网、不依赖 AI）。

职责边界：
- 只回答“某平台现在是否允许运行、为什么、下一次应在何时( next_run_at )”；
- 平台状态彼此独立：每个平台一个 ScheduleDecider + 一份 PlatformScheduleState；
- 不包含主体过滤/风险最终判定/事件/报告，也不直接驱动生产（第一版为影子模式，由上层选择是否门控）。

对齐指令：健康→正常间隔；NO_NEW_DATA 延长；RISK_WARNING 降频；风控/验证→停、冷却、等人；
NETWORK_ERROR 退避；恢复后先低频试探、连续成功再逐步回正；热点可提频但不突破平台硬上限。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .policy import PlatformSchedulePolicy
from . import state_map as sm

_FMT = "%Y-%m-%d %H:%M:%S"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime(_FMT) if isinstance(dt, datetime) else None


@dataclass
class PlatformScheduleState:
    """单平台可持久化调度状态（平台隔离的载体）。"""
    platform: str
    last_run_at: Optional[str] = None
    last_canon: Optional[str] = None
    current_interval: Optional[int] = None      # 当前动态间隔（秒）
    consecutive_no_new: int = 0
    consecutive_network_fail: int = 0
    consecutive_risk: int = 0
    recovery_streak: int = 0
    in_recovery: bool = False
    paused_for_human: bool = False
    cooldown_until: Optional[str] = None
    risk_status: str = "NORMAL"
    last_items_found: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlatformScheduleState":
        fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in (d or {}).items() if k in fields})


@dataclass
class ScheduleDecision:
    platform: str
    allow: bool
    reason_code: str
    scheduler_decision: str
    target_interval_sec: int
    next_run_at: Optional[str] = None
    cooldown_until: Optional[str] = None
    verification_required: bool = False
    risk_status: str = "NORMAL"
    trigger_source: str = "scheduler"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScheduleDecider:
    """单平台调度决策器；线程内使用，多平台请各建实例（平台隔离）。"""

    def __init__(self, policy: PlatformSchedulePolicy, state: Optional[PlatformScheduleState] = None):
        self.policy = policy
        self.state = state or PlatformScheduleState(platform=policy.platform)
        if self.state.current_interval is None:
            self.state.current_interval = policy.normal_interval

    # ---------- 结果回写：更新动态间隔 / 冷却 / 恢复 ----------
    def record_result(self, canon: str, *, now: datetime, items_found: int = 0,
                      risk_score: float = 0.0, error_code: str = "") -> PlatformScheduleState:
        p, st = self.policy, self.state
        st.last_run_at = _iso(now)
        st.last_canon = canon
        st.last_items_found = items_found
        st.risk_status = self._risk_status(canon, risk_score)

        if canon == sm.CS.SUCCESS:
            st.consecutive_no_new = 0
            st.consecutive_network_fail = 0
            st.consecutive_risk = 0
            st.cooldown_until = None
            self._recover_step(now, had_new_data=True)
        elif canon == sm.CS.NO_NEW_DATA:
            st.consecutive_no_new += 1
            st.consecutive_network_fail = 0
            # 连续无新数据：延长间隔，不为“证明在工作”而高频搜索
            grown = p.normal_interval * (p.no_new_data_factor ** st.consecutive_no_new)
            st.current_interval = p.clamped_interval(grown)
            self._recover_step(now, had_new_data=False)
        elif canon == sm.CS.RISK_WARNING:
            st.recovery_streak = 0
            st.in_recovery = True
            st.current_interval = p.clamped_interval(p.normal_interval * p.warning_factor)
        elif canon in (sm.CS.BLOCKED, sm.CS.COOLING_DOWN):
            st.consecutive_risk += 1
            grow = min(p.cooldown_base * (p.cooldown_factor ** max(0, st.consecutive_risk - 1)),
                       p.cooldown_cap)
            st.cooldown_until = _iso(now + timedelta(seconds=grow))
            st.current_interval = int(grow)
            st.recovery_streak = 0
            st.in_recovery = True
        elif canon in (sm.CS.SESSION_EXPIRED, sm.CS.NEED_VERIFY):
            # A/B 类：暂停等人，不自动撞，不设自动恢复时间
            st.paused_for_human = True
            st.cooldown_until = None
            st.recovery_streak = 0
            st.in_recovery = True
        elif sm.is_network(canon):
            st.consecutive_network_fail += 1
            backoff = min(p.network_retry_base *
                          (p.network_retry_factor ** max(0, st.consecutive_network_fail - 1)),
                          p.network_retry_cap)
            st.current_interval = int(backoff)
            st.recovery_streak = 0
            st.in_recovery = True
            if st.consecutive_network_fail >= p.network_fail_to_cooldown:
                st.cooldown_until = _iso(now + timedelta(seconds=backoff))
        return st

    def mark_human_resolved(self, *, now: datetime) -> PlatformScheduleState:
        """合法登录/验证完成后调用：解除人等状态，进入低频健康检查试探（不立即回最高频）。"""
        st = self.state
        st.paused_for_human = False
        st.cooldown_until = None
        st.in_recovery = True
        st.recovery_streak = 0
        st.current_interval = self.policy.recovery_probe_interval
        return st

    def _recover_step(self, now: datetime, *, had_new_data: bool) -> None:
        p, st = self.policy, self.state
        if st.in_recovery:
            st.recovery_streak += 1
            if st.recovery_streak >= p.recovery_success_streak:
                # 连续稳定 → 逐步恢复到正常频率
                st.in_recovery = False
                st.current_interval = p.normal_interval
            else:
                st.current_interval = p.recovery_probe_interval
        else:
            # 健康态：有新数据回到基准间隔；无新数据已在上方延长
            if had_new_data:
                st.current_interval = p.normal_interval

    @staticmethod
    def _risk_status(canon: str, score: float) -> str:
        if canon in (sm.CS.BLOCKED, sm.CS.COOLING_DOWN):
            return "CIRCUIT/COOLDOWN"
        if canon in (sm.CS.SESSION_EXPIRED, sm.CS.NEED_VERIFY):
            return "AWAIT_HUMAN"
        if canon == sm.CS.RISK_WARNING:
            return "WATCH/THROTTLED"
        if sm.is_network(canon):
            return "NETWORK"
        return "NORMAL"

    # ---------- 决策：现在能不能跑 ----------
    def decide(self, *, now: datetime, is_hotspot: bool = False,
               trigger_source: str = "scheduler") -> ScheduleDecision:
        p, st = self.policy, self.state

        if not p.enabled:
            return self._deny("PLATFORM_DISABLED", "平台未启用，统一调度不放行", now, trigger_source)

        if st.paused_for_human:
            need_verify = st.last_canon == sm.CS.NEED_VERIFY
            msg = ("需要人工人机验证，任务保持暂停，验证后经健康检查再续采" if need_verify
                   else "登录态失效，任务保持暂停，等待统一 Auth 恢复，不自动重试")
            return ScheduleDecision(p.platform, False, "AWAIT_HUMAN", msg,
                                    st.current_interval or p.normal_interval,
                                    next_run_at=None, verification_required=True,
                                    risk_status=st.risk_status, trigger_source=trigger_source)

        cdu = self._parse(st.cooldown_until)
        if cdu and now < cdu:
            return ScheduleDecision(
                p.platform, False, "IN_COOLDOWN",
                f"熔断/退避冷却中，剩余 {int((cdu - now).total_seconds())}s，不连续重试",
                st.current_interval or p.normal_interval, next_run_at=_iso(cdu),
                cooldown_until=_iso(cdu), risk_status=st.risk_status, trigger_source=trigger_source)

        # 目标间隔：热点可提频，但绝不低于平台硬上限 min_interval
        target = st.current_interval or p.normal_interval
        if is_hotspot and p.hotspot_enabled:
            target = max(p.min_interval, min(target, p.hotspot_interval))
        target = p.clamped_interval(target)

        if st.last_run_at is None:
            return ScheduleDecision(p.platform, True, "FIRST_RUN", "首次运行，允许采集",
                                    target, next_run_at=_iso(now + timedelta(seconds=target)),
                                    risk_status=st.risk_status, trigger_source=trigger_source)

        last = self._parse(st.last_run_at)
        if last is None:
            return ScheduleDecision(p.platform, True, "FIRST_RUN", "无有效上次时间，允许采集",
                                    target, next_run_at=_iso(now + timedelta(seconds=target)),
                                    trigger_source=trigger_source)
        elapsed = (now - last).total_seconds()
        due_at = last + timedelta(seconds=target)
        if elapsed + 1e-6 < target:
            reason = "热点提频窗口内" if is_hotspot else "未达该平台动态间隔，避免高频请求"
            return ScheduleDecision(p.platform, False, "WAIT_INTERVAL",
                                    f"{reason}，还需 {int(target - elapsed)}s",
                                    target, next_run_at=_iso(due_at),
                                    risk_status=st.risk_status, trigger_source=trigger_source)

        code = "HOTSPOT_BOOST" if is_hotspot and p.hotspot_enabled else "RUN_DUE"
        return ScheduleDecision(p.platform, True, code, "到达动态间隔，允许采集",
                                target, next_run_at=_iso(now + timedelta(seconds=target)),
                                risk_status=st.risk_status, trigger_source=trigger_source)

    @staticmethod
    def _parse(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.strptime(s, _FMT)
        except Exception:
            return None
