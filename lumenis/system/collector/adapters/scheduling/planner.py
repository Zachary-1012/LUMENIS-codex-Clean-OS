# -*- coding: utf-8 -*-
"""平台隔离的统一调度规划器（第一版为“影子模式”，只计算与记录，不门控生产固定时钟）。

- 每个平台独立持有 policy + ScheduleDecider + PlatformScheduleState，小红书风控不会停掉其他平台；
- 状态持久化到 JSON（重启不丢失动态间隔/冷却/恢复进度），决策审计落 schedule_decisions；
- 不 import app / collector，不直接发起任何采集，不决定业务口径；AI 不参与任何决策。
- 灰度路径（后续经确认再切换）：生产 scheduler 触发前 consult self.decide(...)，用 allow 门控。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .policy import DEFAULT_POLICIES, PlatformSchedulePolicy
from .decision import ScheduleDecider, PlatformScheduleState, ScheduleDecision, _FMT
from . import state_map as sm
from .store import ScheduleDecisionStore


class PlatformSchedulePlanner:
    def __init__(self, policies: Optional[Dict[str, PlatformSchedulePolicy]] = None,
                 state_file: Optional[str] = None, store: Optional[ScheduleDecisionStore] = None):
        self.policies = {k: v for k, v in (policies or DEFAULT_POLICIES).items()}
        self.state_file = state_file
        self.store = store
        self._states: Dict[str, PlatformScheduleState] = {}
        self._deciders: Dict[str, ScheduleDecider] = {}
        self._load_states()

    # ---------- 平台隔离的 decider ----------
    def decider(self, platform: str) -> ScheduleDecider:
        key = platform.lower()
        if key not in self._deciders:
            if key not in self.policies:
                raise KeyError(f"未配置调度策略的平台: {platform}")
            self._states[key] = self._states.get(key) or PlatformScheduleState(platform=key)
            self._deciders[key] = ScheduleDecider(self.policies[key], self._states[key])
        return self._deciders[key]

    def enabled_platforms(self) -> List[str]:
        return sorted(k for k, p in self.policies.items() if p.enabled)

    # ---------- 结果归一 + 回写（兼容任意来源状态）----------
    def record_result(self, platform: str, raw_status: Optional[str], *, now: datetime,
                      items_found: int = 0, risk_score: float = 0.0, error_code: str = "",
                      xhs_code: Optional[str] = None, **store_kw) -> str:
        canon = sm.to_canonical(raw_status, items=items_found, xhs_code=xhs_code or error_code or None)
        d = self.decider(platform)
        d.record_result(canon, now=now, items_found=items_found, risk_score=risk_score,
                        error_code=error_code)
        self._save_states()
        if self.store is not None:
            st = d.state
            self.store.ensure_schema()
            self.store.record(platform=platform, allow=False,
                              scheduler_decision=f"回写结果 {canon}，动态间隔 {st.current_interval}s",
                              result_status=canon, items_found=items_found,
                              risk_status=st.risk_status, cooldown_until=st.cooldown_until,
                              next_run_at=self._next_after_record(d, now),
                              verification_required=st.paused_for_human, **store_kw)
        return canon

    def mark_human_resolved(self, platform: str, *, now: datetime) -> None:
        self.decider(platform).mark_human_resolved(now=now)
        self._save_states()

    # ---------- 决策 ----------
    def decide(self, platform: str, *, now: datetime, is_hotspot: bool = False,
               trigger_source: str = "scheduler", persist: bool = False) -> ScheduleDecision:
        decision = self.decider(platform).decide(now=now, is_hotspot=is_hotspot,
                                                 trigger_source=trigger_source)
        if persist and self.store is not None:
            self.store.ensure_schema()
            self.store.record(platform=decision.platform, allow=decision.allow,
                              scheduler_decision=decision.scheduler_decision,
                              result_status=self.decider(platform).state.last_canon,
                              risk_status=decision.risk_status,
                              cooldown_until=decision.cooldown_until,
                              next_run_at=decision.next_run_at,
                              verification_required=decision.verification_required,
                              trigger_source=trigger_source)
        return decision

    def shadow_evaluate(self, *, now: datetime, is_hotspot: bool = False) -> List[ScheduleDecision]:
        """影子模式：只评估所有启用平台并返回决策，不触发、不门控任何生产采集。"""
        out = []
        for key in self.enabled_platforms():
            out.append(self.decide(key, now=now, is_hotspot=is_hotspot, trigger_source="shadow"))
        return out

    def snapshot(self) -> Dict[str, Any]:
        return {k: self.decider(k).state.to_dict() for k in self.policies}

    # ---------- 内部 ----------
    @staticmethod
    def _next_after_record(d: ScheduleDecider, now: datetime) -> Optional[str]:
        decision = d.decide(now=now)
        return decision.next_run_at

    def _load_states(self) -> None:
        if not self.state_file or not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self.policies:
                    self._states[k] = PlatformScheduleState.from_dict(v)
        except Exception:
            self._states = {}

    def _save_states(self) -> None:
        if not self.state_file:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
        tmp = self.state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in self._states.items()}, f,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, self.state_file)
