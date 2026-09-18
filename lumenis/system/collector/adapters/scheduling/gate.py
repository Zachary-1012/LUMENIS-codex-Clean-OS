# -*- coding: utf-8 -*-
"""GAP-05 动态调度「影子 → 门控」三态切换器（已签字，默认保守）。

模式由环境变量 ZBC_SCHED_GATE_MODE 控制，**默认 shadow，上线零行为变化**：
- shadow（默认）：照常评估并落审计，但 should_run 完全沿用既有固定触发（hard_allow），不门控；
- canary：仅对 ZBC_SCHED_GATE_PLATFORMS（逗号分隔，默认空）列出的平台用 decision.allow 门控，其余同 shadow；
- enforce：所有平台用 decision.allow 门控。

铁律：
1. 门控**只收紧、不放松**：最终 should_run = hard_allow AND decision.allow（门控态）；
   shadow 态 should_run = hard_allow。既有熔断/冷却/活动窗口/让行等 hard_allow 上游逻辑一律不动，
   本层绝不可能把「上游已决定不跑」变成「跑」，因此不弱化任何熔断。
2. 门控器自身异常时 fail-open 回 hard_allow（新组件故障不卡死既有调度），并返回 mode 供日志区分。
3. 非法模式值回退 shadow（fail-safe）。
回滚：把 ZBC_SCHED_GATE_MODE 改回 shadow（或直接取消该变量）即完全恢复固定时钟，无需改代码。
"""
from __future__ import annotations

import os
from typing import Any, Optional, Tuple

_VALID_MODES = ('shadow', 'canary', 'enforce')


def gate_mode() -> str:
    m = (os.environ.get('ZBC_SCHED_GATE_MODE') or 'shadow').strip().lower()
    return m if m in _VALID_MODES else 'shadow'


def canary_platforms() -> set:
    raw = os.environ.get('ZBC_SCHED_GATE_PLATFORMS', '') or ''
    return {x.strip().lower() for x in raw.split(',') if x.strip()}


def gate_should_run(planner, platform: str, *, now, is_hotspot: bool = False,
                    hard_allow: bool = True, persist: bool = True
                    ) -> Tuple[bool, Optional[Any], str]:
    """返回 (should_run, decision, mode)。decision 在评估异常时为 None。"""
    mode = gate_mode()
    key = str(platform).lower()
    try:
        decision = planner.decide(key, now=now, is_hotspot=is_hotspot,
                                  trigger_source='gate_' + mode, persist=persist)
    except Exception:
        # 门控器自身故障：fail-open 到既有固定触发，绝不因新组件卡住生产调度
        return bool(hard_allow), None, mode

    gated = (mode == 'enforce') or (mode == 'canary' and key in canary_platforms())
    if not gated:
        return bool(hard_allow), decision, mode
    # 门控态：只可能把 True 收紧为 False，不可能放松
    return bool(hard_allow) and bool(getattr(decision, 'allow', False)), decision, mode
