# -*- coding: utf-8 -*-
"""Collector Guard —— 可插拔采集韧性增强包（V1.0）。

包在现有采集器外层，提供：六态状态机 / 动态限速退避 / 成功率与延迟指标 / 断点续采 / 统一响应归因。
默认开关 GUARD_ENABLED（默认 true，但仅在被显式接入时生效）；不重写采集核心、不改主体口径、
不实现验证码绕过或风控对抗；任何异常回退，不拖垮主系统。
"""
import os

from .state import CollectState
from .analyzer import ResponseAnalyzer, Reason
from .rate_limiter import AdaptiveRateLimiter
from .metrics import GuardMetrics
from .checkpoint import Checkpoint
from .guard import CollectorGuard, GuardResult
from .runtime_guardian import RuntimeGuardian

__all__ = ['CollectState', 'ResponseAnalyzer', 'Reason', 'AdaptiveRateLimiter',
           'GuardMetrics', 'Checkpoint', 'CollectorGuard', 'GuardResult',
           'RuntimeGuardian', 'create_guard', 'guard_enabled']


def guard_enabled():
    return os.getenv('GUARD_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes', 'on', 'y')


def create_guard(platform, enabled=None, base_interval=None, checkpoint_dir=None):
    """工厂：enabled 默认跟随 GUARD_ENABLED。"""
    if enabled is None:
        enabled = guard_enabled()
    return CollectorGuard(platform, enabled=enabled, base_interval=base_interval,
                          checkpoint_dir=checkpoint_dir)
