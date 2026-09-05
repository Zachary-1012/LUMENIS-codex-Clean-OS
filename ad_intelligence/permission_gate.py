# -*- coding: utf-8 -*-
"""
广告投流权限控制
================
投流操作涉及资金，必须严格控制权限。

权限等级：
- READ: 只读数据采集与查看（默认启用）
- ANALYZE: 分析、预测、生成建议（默认启用）
- PREVIEW: 策略预览、模拟投流（需授权）
- EXECUTE: 实际投流操作（默认关闭，必须人工确认）

所有 EXECUTE 级操作必须：
1. 通过 Permission Gate 检查
2. 记录操作人、时间、前后状态
3. 人工二次确认（资金操作）
4. 写入 Evidence Chain
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)


class AdPermissionLevel(str, Enum):
    """广告投流权限等级。"""
    READ = "read"
    ANALYZE = "analyze"
    PREVIEW = "preview"
    EXECUTE = "execute"


class AdPermissionGate:
    """广告投流权限控制器。

    默认只允许 READ 和 ANALYZE 级操作。
    PREVIEW 和 EXECUTE 必须显式授权。
    EXECUTE 级操作必须人工确认。
    """

    def __init__(self, config_path: Optional[str] = None):
        self._enabled_levels = {AdPermissionLevel.READ, AdPermissionLevel.ANALYZE}
        self._human_approved = False
        self._approval_expiry = None
        self._operation_log = []
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[str]):
        """从环境变量或配置文件加载权限。"""
        # 环境变量控制（仅当显式设置时才覆盖默认）
        env_level = os.environ.get("AD_PERMISSION_LEVEL")
        if env_level:
            level_map = {
                "read": {AdPermissionLevel.READ},
                "analyze": {AdPermissionLevel.READ, AdPermissionLevel.ANALYZE},
                "preview": {AdPermissionLevel.READ, AdPermissionLevel.ANALYZE, AdPermissionLevel.PREVIEW},
                "execute": {AdPermissionLevel.READ, AdPermissionLevel.ANALYZE, AdPermissionLevel.PREVIEW, AdPermissionLevel.EXECUTE},
            }
            if env_level.lower() in level_map:
                self._enabled_levels = level_map[env_level.lower()]

    def has_permission(self, level: AdPermissionLevel) -> bool:
        """检查是否有指定权限。"""
        return level in self._enabled_levels

    def require(self, level: AdPermissionLevel, operation: str = "") -> bool:
        """权限检查，失败则记录并返回 False。"""
        if not self.has_permission(level):
            logger.warning(f"[AdPermissionGate] 权限拒绝: {level.value} - {operation}")
            return False
        if level == AdPermissionLevel.EXECUTE and not self._human_approved:
            logger.warning(f"[AdPermissionGate] EXECUTE 操作需人工确认: {operation}")
            return False
        return True

    def grant_human_approval(self, duration_minutes: int = 30):
        """人工授权 EXECUTE 级操作（有时效）。"""
        self._human_approved = True
        from datetime import timedelta
        self._approval_expiry = datetime.now() + timedelta(minutes=duration_minutes)
        logger.info(f"[AdPermissionGate] 人工授权已授予，有效期 {duration_minutes} 分钟")

    def revoke_human_approval(self):
        """撤销人工授权。"""
        self._human_approved = False
        self._approval_expiry = None
        logger.info("[AdPermissionGate] 人工授权已撤销")

    def _check_approval_expiry(self):
        """检查授权是否过期。"""
        if self._approval_expiry and datetime.now() > self._approval_expiry:
            self._human_approved = False
            self._approval_expiry = None
            logger.info("[AdPermissionGate] 人工授权已过期")

    def log_operation(self, level: AdPermissionLevel, operation: str,
                      details: dict, success: bool):
        """记录操作日志（Evidence Chain）。"""
        self._check_approval_expiry()
        record = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "operation": operation,
            "details": details,
            "success": success,
            "human_approved": self._human_approved,
        }
        self._operation_log.append(record)
        logger.info(f"[AdPermissionGate] 操作记录: {operation} - {'成功' if success else '失败'}")

    def execute_with_gate(self, level: AdPermissionLevel, operation: str,
                          func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """带权限门控的执行包装器。

        Returns:
            (success, result_or_error_message)
        """
        if not self.require(level, operation):
            return False, f"权限不足: 需要 {level.value} 级别"

        try:
            result = func(*args, **kwargs)
            self.log_operation(level, operation, {"args": str(args), "kwargs": str(kwargs)}, True)
            return True, result
        except Exception as e:
            self.log_operation(level, operation, {"error": str(e)}, False)
            return False, str(e)

    def get_status(self) -> dict:
        """获取权限状态。"""
        self._check_approval_expiry()
        return {
            "enabled_levels": [l.value for l in self._enabled_levels],
            "human_approved": self._human_approved,
            "approval_expiry": self._approval_expiry.isoformat() if self._approval_expiry else None,
            "operation_count": len(self._operation_log),
        }


# 全局权限门控实例
_default_gate: Optional[AdPermissionGate] = None

def get_permission_gate() -> AdPermissionGate:
    """获取全局权限门控实例。"""
    global _default_gate
    if _default_gate is None:
        _default_gate = AdPermissionGate()
    return _default_gate
