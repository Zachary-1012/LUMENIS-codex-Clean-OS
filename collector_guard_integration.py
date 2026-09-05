# -*- coding: utf-8 -*-
"""
Collector Guard 集成层（旁路模式 V1.0）
--------------------------------------
将 collector_guard（六态状态机/动态限速/指标/断点续采/DLQ/资源守护）
以旁路方式接入主系统，不改变现有采集行为。

设计原则：
- 旁路优先：先初始化 + 暴露状态 API，不立即包裹现有采集调用点
- 可关闭：GUARD_ENABLED=false 时完全直通，零影响
- 只读 API：/api/collector-guard/status 查看各平台 guard 状态
- 后续接入：验证稳定后，再将 guard.run() 包裹到采集调用点

使用：
    from collector_guard_integration import get_guard, get_all_status, is_enabled
    guard = get_guard("xhs")
    result = guard.run(collect_fn, keyword, **kwargs)  # 后续接入采集点
"""
import logging
from typing import Dict, Optional

from collector_guard import CollectorGuard, create_guard, guard_enabled

logger = logging.getLogger(__name__)

# 已接入 guard 的平台列表（与 platform_adapters 对齐）
PLATFORMS = ["xhs", "douyin", "weibo", "bilibili", "instagram", "zhihu"]

_GUARDS: Dict[str, CollectorGuard] = {}
_INITIALIZED = False


def init_guards(platforms=None) -> None:
    """初始化各平台 CollectorGuard（幂等，重复调用不重建）。"""
    global _INITIALIZED
    if _INITIALIZED:
        return
    for p in (platforms or PLATFORMS):
        if p not in _GUARDS:
            try:
                _GUARDS[p] = create_guard(p)
            except Exception as exc:
                logger.warning("初始化 %s guard 失败: %s", p, exc)
    _INITIALIZED = True
    logger.info("CollectorGuard 初始化完成: %d 平台, enabled=%s",
                len(_GUARDS), guard_enabled())


def get_guard(platform: str) -> Optional[CollectorGuard]:
    """获取指定平台的 guard（自动初始化）。"""
    init_guards()
    return _GUARDS.get(platform)


def get_all_status() -> dict:
    """获取所有平台 guard 状态（含限速器/指标快照）。"""
    init_guards()
    status = {}
    for p, g in _GUARDS.items():
        try:
            status[p] = g.status()
        except Exception as exc:
            status[p] = {"error": str(exc)}
    return status


def is_enabled() -> bool:
    """全局 guard 开关状态（来自环境变量 GUARD_ENABLED）。"""
    return guard_enabled()


def reset() -> None:
    """重置初始化状态（仅供测试使用）。"""
    global _INITIALIZED, _GUARDS
    _GUARDS = {}
    _INITIALIZED = False
