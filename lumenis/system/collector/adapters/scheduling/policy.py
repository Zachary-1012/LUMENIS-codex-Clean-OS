# -*- coding: utf-8 -*-
"""平台独立采集调度策略（配置驱动，同时锁定序境自动采集硬边界）。

对齐《序境｜双子库全量收敛与产品研发总执行指令》第十三条 + 《采集调度与风控最终执行指令》：
- 自动采集：默认关闭 / UI 隐藏（enabled=False），可开关；固定每日 00:00、12:00 最多两次；
  单次工作流最长 60 分钟（run_duration_auto 上限默认 1800s = 30min，绝不超过 3600s）。
- 手动采集：单次最长 30 分钟（run_duration_manual 默认 1200s = 20min，绝不超过 1800s）。
- 每个平台自带 minimum/maximum 间隔、退避、冷却、恢复、热点上限等动态策略，统一 Scheduler 读取策略做决策。
- 下列数值是**初始策略**，可由配置/构造覆盖，但平台硬上限（时长/频率）在任何状态（含热点）下都不得突破。

AI 不参与本层任何决策：这里只有确定性规则。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Dict, Tuple


@dataclass
class PlatformSchedulePolicy:
    platform: str
    name: str = ""
    enabled: bool = False
    priority: str = "event"            # primary / secondary / event

    # —— 固定单次运行时长（保留，单位秒）——
    run_duration_auto: int = 1800      # 自动任务单次最长（默认 30min，硬上限 3600s=60min）
    run_duration_manual: int = 1200    # 手动任务单次最长（默认 20min，硬上限 1800s=30min）

    # —— 序境自动采集固定时间槽（每日最多两次）——
    auto_slots: Tuple[str, ...] = ("00:00", "12:00")

    # —— 序境硬边界常量（不可被热点/动态策略突破）——
    MAX_AUTO_DURATION: int = 3600      # 自动单次工作流硬上限 60 分钟
    MAX_MANUAL_DURATION: int = 1800    # 手动单次工作流硬上限 30 分钟

    def __post_init__(self) -> None:
        # 构造时即夹紧时长硬上限，杜绝任何调用方传入超限值
        if self.run_duration_auto > self.MAX_AUTO_DURATION:
            self.run_duration_auto = self.MAX_AUTO_DURATION
        if self.run_duration_manual > self.MAX_MANUAL_DURATION:
            self.run_duration_manual = self.MAX_MANUAL_DURATION

    # —— 动态频率（单位秒）——
    normal_interval: int = 3600        # 健康时两次运行的基准间隔
    min_interval: int = 1200           # 平台级硬上限：任何情况（含热点）不得比这更密
    max_interval: int = 21600          # 连续无新数据/低活跃时，间隔延长上限（6h）
    no_new_data_factor: float = 1.5    # 连续 NO_NEW_DATA：间隔乘该系数延长
    no_new_data_streak_to_grow: int = 1

    # —— 网络异常退避（单位秒）——
    network_retry_base: int = 60
    network_retry_factor: float = 2.0
    network_retry_cap: int = 900
    network_fail_to_cooldown: int = 3  # 连续网络失败达到该次数进入冷却

    # —— 风险退避 / 冷却（单位秒）——
    warning_factor: float = 1.5        # RISK_WARNING 轻度风险：间隔拉长
    cooldown_base: int = 900           # BLOCKED/COOLING_DOWN 基础冷却
    cooldown_factor: float = 2.0       # 连续命中冷却：逐级翻倍
    cooldown_cap: int = 1800
    circuit_open_hold: int = 1800      # 熔断后至少保持这么久，期间只做健康检查

    # —— 恢复策略：恢复后不立即回最高频 ——
    recovery_probe_interval: int = 1800   # 恢复后首次低频试探间隔
    recovery_success_streak: int = 3      # 连续成功这么多次才逐步回到 normal_interval

    # —— 热点策略：可提频但不突破平台硬上限 ——
    hotspot_enabled: bool = True
    hotspot_interval: int = 1200       # 热点时目标间隔（>= min_interval，受硬上限约束）

    # —— 历史窗口：决策时参考最近多少次结果 ——
    history_window: int = 12

    def clamped_interval(self, value: float) -> int:
        """任何间隔都夹在 [min_interval, max_interval]，热点也无法突破硬上限。"""
        return int(max(self.min_interval, min(self.max_interval, round(value))))

    def to_dict(self) -> Dict:
        return asdict(self)


def _xhs_policy() -> PlatformSchedulePolicy:
    return PlatformSchedulePolicy(
        platform="xhs", name="小红书", enabled=True, priority="primary",
        # 主监测平台：健康基线 1h，硬上限 20min，低活跃最长 6h；其余取通用默认
    )


def _disabled(platform: str, name: str, priority: str = "event") -> PlatformSchedulePolicy:
    # 未启用平台只保留策略槽位，enabled=False 时统一 Scheduler 不会放行
    return PlatformSchedulePolicy(platform=platform, name=name, enabled=False, priority=priority)


def build_default_policies() -> Dict[str, PlatformSchedulePolicy]:
    return {
        "xhs": _xhs_policy(),
        "douyin": _disabled("douyin", "抖音", "secondary"),
        "weibo": _disabled("weibo", "微博"),
        "bilibili": _disabled("bilibili", "B站"),
        "kuaishou": _disabled("kuaishou", "快手"),
        "tieba": _disabled("tieba", "贴吧"),
        "zhihu": _disabled("zhihu", "知乎"),
    }


DEFAULT_POLICIES: Dict[str, PlatformSchedulePolicy] = build_default_policies()
