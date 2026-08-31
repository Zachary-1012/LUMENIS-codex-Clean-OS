# -*- coding: utf-8 -*-
"""临时话题监测策略：业务配额与数据质量控制。

本模块只定义业务任务预算、去重和数据质量门槛，不承担平台风控规避功能。

设计目标：
1. 当前国内 XHS 主账号仅处于 WARNING，不视为封禁；
2. 话题监测作为 TEMPORARY 策略，避免把当前方案永久写死；
3. 每日最多 10 个 batch，每 batch 最多接受 10 个新 note；
4. 重复 note 不进入分析流水线；
5. 若未来官方 API / 合规 Provider / 用户 Evidence 成为更优数据源，可无损替换 Browser Adapter；
6. 任意平台警告、验证、限制、错误状态均由现有 Runtime/Guard/Scheduler 决定是否继续，不能由本模块覆盖。

注意：10×10 是业务任务预算，不是“保证不触发平台风控”的参数。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, MutableSet, Tuple


@dataclass(frozen=True)
class TemporaryTopicMonitorPolicy:
    strategy: str = "TEMPORARY"
    enabled: bool = True
    max_batches_per_day: int = 10
    max_new_notes_per_batch: int = 10
    deduplicate: bool = True
    source_priority: Tuple[str, ...] = (
        "official_api",
        "licensed_provider",
        "user_evidence",
        "temporary_browser",
    )

    # 仅表示业务执行的最长单次运行窗口；不是平台安全保证。
    auto_run_seconds: int = 1800
    manual_run_seconds: int = 1200


DEFAULT_TOPIC_MONITOR_POLICY = TemporaryTopicMonitorPolicy()


def can_start_batch(run_count_today: int, policy: TemporaryTopicMonitorPolicy = DEFAULT_TOPIC_MONITOR_POLICY) -> bool:
    """业务预算门槛。平台状态必须由外层 Runtime/Guard 另行判定。"""
    return bool(policy.enabled and run_count_today < policy.max_batches_per_day)


def select_new_notes(
    notes: Iterable[Mapping],
    seen_note_ids: MutableSet[str],
    policy: TemporaryTopicMonitorPolicy = DEFAULT_TOPIC_MONITOR_POLICY,
) -> Tuple[list, MutableSet[str]]:
    """去重并限制单批新增笔记数量。

    note_id 优先取 note_id，其次取 id；没有稳定 ID 的对象不进入自动入库批次。
    """
    selected = []
    for note in notes:
        note_id = str(note.get("note_id") or note.get("id") or "").strip()
        if not note_id:
            continue
        if policy.deduplicate and note_id in seen_note_ids:
            continue
        if len(selected) >= policy.max_new_notes_per_batch:
            break
        selected.append(note)
        seen_note_ids.add(note_id)
    return selected, seen_note_ids


def reset_daily_budget(current_day: date, stored_day: date | None, run_count: int) -> int:
    """跨自然日时重置业务批次计数。"""
    return 0 if stored_day != current_day else run_count
