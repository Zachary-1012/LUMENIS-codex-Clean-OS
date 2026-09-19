# -*- coding: utf-8 -*-
"""
LUMENIS SYSTEM Permission（唯一权限模型）
====================================================
LUMENIS SYSTEM 唯一应用层权限控制。所有受治理操作必须经过本 Gate 检查，
高风险操作 fail-closed 并需人工审批。

定位：
  - 应用层权限控制（Application-Layer Authorization），**不是**网络 WAF。
  - 本模块是唯一 Permission state / approval / operation authorization owner。
  - ad_intelligence/permission_gate.py 仅是 Domain Adapter，必须委托本 Gate，
    不得拥有独立审批状态或最终授权权。
  - agent_security / safety_boundary / compliance_gate 只保留各自专项安全能力，
    不得形成第二权限 owner。

核心原则（AGENTS.md §13 修改安全协议）：
  审计 → 备份/确认 → 最小修改 → 单测 → E2E → 真实数据验证 → 回归 → CHANGELOG → 交付
  fail-closed：未注册的操作默认拒绝。
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# TESTING bypass 全局开关：默认 False（OWASP deny-by-default / fail-closed，生产永远严格）。
# 测试环境由 conftest session fixture 显式 set_testing_bypass(True) 开启；权限专项模块用 module fixture 覆盖为严格。
_TESTING_BYPASS_ENABLED = False

def set_testing_bypass(enabled: bool) -> None:
    """设置 TESTING bypass 开关（仅测试用）。"""
    global _TESTING_BYPASS_ENABLED
    _TESTING_BYPASS_ENABLED = enabled

def is_testing_bypass_enabled() -> bool:
    """返回显式 TESTING bypass 状态；生产代码不得根据 pytest 自动推断。"""
    return bool(_TESTING_BYPASS_ENABLED) or os.environ.get("PERMISSION_GATE_TESTING") == "1"

# ═══════════════════════════════════════════════════════════════
# 1. 枚举定义
# ═══════════════════════════════════════════════════════════════


class PermissionLevel(str, Enum):
    """权限等级（从低到高）。

    低等级为只读/分析类，高等级为写操作/变更类。
    HUMAN_APPROVAL 是人工审批令牌等级，不直接对应操作。
    """
    READ = "read"                          # 只读查看
    AUDIT = "audit"                        # 审计/日志查看
    ANALYZE = "analyze"                    # 分析/计算
    RESEARCH = "research"                  # 调研/检索
    PLAN = "plan"                          # 方案规划（不执行）
    PATCH_PREVIEW = "patch_preview"        # 补丁预览（dry-run）
    TEST = "test"                          # 测试执行（隔离环境）
    VERIFY = "verify"                      # 验证/校验
    HUMAN_APPROVAL = "human_approval"      # 人工审批令牌等级
    COMMIT = "commit"                      # 代码/配置提交
    PUSH = "push"                          # 推送/发布/上线

    @classmethod
    def rank(cls, level: "PermissionLevel") -> int:
        """返回权限等级数值（越大权限越高）。"""
        order = list(cls)
        return order.index(level)


class RiskLevel(str, Enum):
    """风险等级。"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def rank(cls, level: "RiskLevel") -> int:
        order = list(cls)
        return order.index(level)


class OperationType(str, Enum):
    """操作类型枚举。

    每个操作类型在 _OPERATION_REGISTRY 中注册默认权限等级和风险等级。
    未注册的操作在 fail_closed=True 时默认拒绝。
    """
    FILE_WRITE = "file_write"                    # 文件写入/修改
    CONFIG_MODIFY = "config_modify"              # 配置修改
    DB_WRITE = "db_write"                        # 数据库写入
    DATA_DELETE = "data_delete"                  # 数据删除
    AI_CALL = "ai_call"                          # AI 模型调用
    COLLECTOR_START = "collector_start"          # 采集器启动
    COLLECTOR_STOP = "collector_stop"            # 采集器停止
    DATA_IMPORT = "data_import"                  # 数据导入
    DATA_EXPORT = "data_export"                  # 数据导出
    REPORT_GENERATE = "report_generate"          # 报告生成
    SKILL_EXECUTE = "skill_execute"              # Skill 执行
    BROWSER_OPERATION = "browser_operation"      # 浏览器操作
    EXTERNAL_NETWORK = "external_network"        # 外部网络请求
    RUNTIME_OPERATION = "runtime_operation"      # 运行时操作（重启/切换等）
    AD_PREVIEW = "ad_preview"                    # 广告策略预览/模拟
    AD_EXECUTE = "ad_execute"                    # 广告投放/资金性外部动作


# ═══════════════════════════════════════════════════════════════
# 2. 操作注册表（Operation Registry）
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OperationSpec:
    """操作规格：默认权限等级、默认风险等级、描述。"""
    permission: PermissionLevel
    risk: RiskLevel
    description: str
    # 是否允许在无人工审批时自动放行（仅 LOW/MEDIUM 且权限等级 <= VERIFY 时为 True）
    auto_allow: bool = True


# 全局操作注册表：operation_type → OperationSpec
# 设计原则：
#   - 读/分析类：LOW 风险，低权限，auto_allow=True
#   - 写/修改类：MEDIUM 风险，中高权限，auto_allow=True（但需权限等级达标）
#   - 删除/高风险写：HIGH 风险，需人工审批，auto_allow=False
#   - CRITICAL：必须人工审批，fail-closed
_OPERATION_REGISTRY: Dict[OperationType, OperationSpec] = {
    # ── 低风险 / 只读分析类 ──
    OperationType.AI_CALL: OperationSpec(
        PermissionLevel.ANALYZE, RiskLevel.LOW,
        "AI 模型调用（增强层，不改变系统状态）", auto_allow=True),
    OperationType.REPORT_GENERATE: OperationSpec(
        PermissionLevel.ANALYZE, RiskLevel.LOW,
        "报告生成（只读聚合，不修改源数据）", auto_allow=True),

    # ── 中风险 / 写操作类 ──
    OperationType.FILE_WRITE: OperationSpec(
        PermissionLevel.PATCH_PREVIEW, RiskLevel.MEDIUM,
        "文件写入/修改（非配置/非核心代码）", auto_allow=True),
    OperationType.CONFIG_MODIFY: OperationSpec(
        PermissionLevel.COMMIT, RiskLevel.HIGH,
        "配置修改（影响运行时行为，需人工审批）", auto_allow=False),
    OperationType.DB_WRITE: OperationSpec(
        PermissionLevel.COMMIT, RiskLevel.HIGH,
        "数据库写入（INSERT/UPDATE，需人工审批）", auto_allow=False),
    OperationType.COLLECTOR_START: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "采集器启动（影响外部交互，需权限达标）", auto_allow=True),
    OperationType.COLLECTOR_STOP: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "采集器停止（中断采集链路，需权限达标）", auto_allow=True),
    OperationType.DATA_IMPORT: OperationSpec(
        PermissionLevel.COMMIT, RiskLevel.HIGH,
        "数据导入（批量写入，需人工审批）", auto_allow=False),
    OperationType.DATA_EXPORT: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "数据导出（可能含敏感数据，需权限达标）", auto_allow=True),
    OperationType.SKILL_EXECUTE: OperationSpec(
        PermissionLevel.TEST, RiskLevel.MEDIUM,
        "Skill 执行（需权限达标）", auto_allow=True),
    OperationType.BROWSER_OPERATION: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "浏览器操作（只读允许，写操作禁止——见 AGENTS.md §7 官方账号只读保护）",
        auto_allow=True),
    OperationType.EXTERNAL_NETWORK: OperationSpec(
        PermissionLevel.RESEARCH, RiskLevel.LOW,
        "外部网络请求（只读检索）", auto_allow=True),
    OperationType.RUNTIME_OPERATION: OperationSpec(
        PermissionLevel.COMMIT, RiskLevel.HIGH,
        "运行时操作（重启/切换/降级，需人工审批）", auto_allow=False),
    OperationType.AD_PREVIEW: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "广告策略预览/模拟（不得产生真实投放或资金副作用）", auto_allow=True),
    OperationType.AD_EXECUTE: OperationSpec(
        PermissionLevel.PUSH, RiskLevel.CRITICAL,
        "广告真实投放/资金性外部动作（必须人工审批，fail-closed）", auto_allow=False),

    # ── 高风险 / 删除类 ──
    OperationType.DATA_DELETE: OperationSpec(
        PermissionLevel.PUSH, RiskLevel.CRITICAL,
        "数据删除（不可逆，必须人工审批，fail-closed）", auto_allow=False),
}


# ═══════════════════════════════════════════════════════════════
# 3. PermissionResult
# ═══════════════════════════════════════════════════════════════

@dataclass
class PermissionResult:
    """权限检查结果。"""
    allowed: bool
    reason: str
    requires_approval: bool = False
    approval_token: Optional[str] = None
    audit_id: Optional[str] = None
    # 附加信息
    operation_type: Optional[str] = None
    resource: Optional[str] = None
    risk_level: Optional[str] = None
    permission_required: Optional[str] = None
    caller: Optional[str] = None
    operation_id: Optional[str] = None
    idempotent_hit: bool = False
    domain_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# 4. 人工审批令牌
# ═══════════════════════════════════════════════════════════════

@dataclass
class ApprovalToken:
    """人工审批令牌。"""
    token: str
    operation: str                       # 操作类型标识（OperationType.value 或自定义）
    resource: Optional[str]              # 授权的资源范围（None 表示该操作类型全部）
    granted_at: datetime
    expires_at: datetime
    granted_by: str = "human"
    revoked: bool = False

    def is_valid(self, operation: str, resource: Optional[str] = None) -> bool:
        """检查令牌是否对指定操作/资源有效。"""
        if self.revoked:
            return False
        if datetime.now() > self.expires_at:
            return False
        if self.operation != operation and self.operation != "*":
            return False
        if self.resource and resource and self.resource != resource:
            return False
        return True


# ═══════════════════════════════════════════════════════════════
# 5. 审计日志条目
# ═══════════════════════════════════════════════════════════════

@dataclass
class AuditEntry:
    """审计日志条目。"""
    audit_id: str
    timestamp: str
    operation_type: str
    resource: Optional[str]
    risk_level: str
    permission_required: str
    caller: Optional[str]
    result: str                       # "allowed" | "denied" | "needs_approval"
    reason: str
    operation_id: Optional[str]
    approval_token: Optional[str]
    idempotent_hit: bool


# ═══════════════════════════════════════════════════════════════
# 6. PermissionGate 核心类
# ═══════════════════════════════════════════════════════════════

class PermissionGate:
    """LUMENIS SYSTEM 统一权限门。

    用法：
        gate = PermissionGate()
        result = gate.check(OperationType.FILE_WRITE, "/path/to/file", RiskLevel.MEDIUM)
        if result.allowed:
            ... 执行操作 ...

    fail-closed：
        - 未在 _OPERATION_REGISTRY 注册的操作类型 → 默认拒绝
        - HIGH/CRITICAL 风险 → 默认拒绝，需人工审批
        - 权限等级不足 → 拒绝
    """

    def __init__(
        self,
        fail_closed: bool = True,
        caller: str = "system",
        audit_log_path: Optional[str] = None,
        enabled_permissions: Optional[Set[PermissionLevel]] = None,
    ):
        """
        Args:
            fail_closed: 未注册操作是否默认拒绝（默认 True）
            caller: 默认调用者标识
            audit_log_path: 审计日志持久化路径（None 则仅内存）
            enabled_permissions: 当前启用的权限等级集合（None 则默认启用 READ..VERIFY）
        """
        self.fail_closed = fail_closed
        self.default_caller = caller
        self.audit_log_path = audit_log_path

        # 默认启用权限：READ 到 VERIFY（不含 HUMAN_APPROVAL/COMMIT/PUSH）
        if enabled_permissions is None:
            self._enabled_permissions: Set[PermissionLevel] = {
                PermissionLevel.READ,
                PermissionLevel.AUDIT,
                PermissionLevel.ANALYZE,
                PermissionLevel.RESEARCH,
                PermissionLevel.PLAN,
                PermissionLevel.PATCH_PREVIEW,
                PermissionLevel.TEST,
                PermissionLevel.VERIFY,
            }
        else:
            self._enabled_permissions = set(enabled_permissions)

        # 审计日志（内存）
        self._audit_log: List[AuditEntry] = []
        self._audit_lock = threading.Lock()

        # 人工审批令牌
        self._approvals: Dict[str, ApprovalToken] = {}
        self._approval_lock = threading.Lock()

        # 幂等性缓存：operation_id → PermissionResult
        self._idempotency_cache: Dict[str, PermissionResult] = {}
        self._idempotency_lock = threading.Lock()

        # 操作注册表（可运行时扩展）
        self._registry: Dict[OperationType, OperationSpec] = dict(_OPERATION_REGISTRY)

    # ──────────────────────────────────────────────────────────
    # 权限等级管理
    # ──────────────────────────────────────────────────────────

    def has_permission(self, level: PermissionLevel) -> bool:
        """检查当前是否拥有指定权限等级。"""
        return level in self._enabled_permissions

    def grant_permission(self, level: PermissionLevel) -> None:
        """授予权限等级（运行时，不持久化）。"""
        self._enabled_permissions.add(level)
        logger.info(f"[PermissionGate] 权限已授予: {level.value}")

    def revoke_permission(self, level: PermissionLevel) -> None:
        """撤销权限等级。"""
        self._enabled_permissions.discard(level)
        logger.info(f"[PermissionGate] 权限已撤销: {level.value}")

    def get_enabled_permissions(self) -> List[str]:
        """返回当前启用的权限等级列表。"""
        return sorted([l.value for l in self._enabled_permissions],
                      key=lambda v: PermissionLevel.rank(PermissionLevel(v)))

    # ──────────────────────────────────────────────────────────
    # 操作注册表管理
    # ──────────────────────────────────────────────────────────

    def register_operation(
        self,
        operation_type: OperationType,
        spec: OperationSpec,
    ) -> None:
        """注册新操作类型（或覆盖已有）。"""
        self._registry[operation_type] = spec
        logger.info(f"[PermissionGate] 操作已注册: {operation_type.value} → "
                     f"perm={spec.permission.value}, risk={spec.risk.value}")

    def is_registered(self, operation_type: OperationType) -> bool:
        """检查操作类型是否已注册。"""
        return operation_type in self._registry

    def get_operation_spec(self, operation_type: OperationType) -> Optional[OperationSpec]:
        """获取操作规格。"""
        return self._registry.get(operation_type)

    def list_operations(self) -> List[Dict[str, str]]:
        """列出所有已注册操作。"""
        return [
            {
                "operation": ot.value,
                "permission": spec.permission.value,
                "risk": spec.risk.value,
                "description": spec.description,
                "auto_allow": str(spec.auto_allow),
            }
            for ot, spec in self._registry.items()
        ]

    # ──────────────────────────────────────────────────────────
    # 核心：权限检查
    # ──────────────────────────────────────────────────────────

    def check(
        self,
        operation_type: OperationType,
        resource: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        caller: Optional[str] = None,
        operation_id: Optional[str] = None,
        domain_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> PermissionResult:
        """执行权限检查。

        Args:
            operation_type: 操作类型
            resource: 操作目标资源（路径/表名/URL 等）
            risk_level: 显式风险等级（None 则使用操作注册表默认值）
            caller: 调用者标识
            operation_id: 幂等性 ID（相同 ID 重复调用返回缓存结果）
            domain_id: 域身份（cth/zbmp），None 则从线程上下文读取
            role: 调用者角色（如 zbmp_analyst, cth_admin），用于跨域权限检查

        Returns:
            PermissionResult
        """
        # 0a. TESTING 旁路：必须显式开启（set_testing_bypass(True) 或 PERMISSION_GATE_TESTING=1）。
        # OWASP deny-by-default：不得因检测到 pytest 环境或 Flask TESTING 就自动放行（那会使权限测试失效、生产也存在被绕过风险）。
        _is_testing = bool(_TESTING_BYPASS_ENABLED) or os.environ.get('PERMISSION_GATE_TESTING') == '1' 
        if _is_testing:
            logger.debug(f"[PermissionGate] TESTING模式放行: op={operation_type.value}, resource={resource}")
            return PermissionResult(
                allowed=True,
                operation_type=operation_type,
                resource=resource or 'unknown',
                risk_level=risk_level or RiskLevel.LOW,
                permission_required=PermissionLevel.VERIFY,
                reason='TESTING mode - all operations allowed (audit only)',
                caller=caller or 'test_runner',
            )

        # 0. 域身份解析（默认从线程上下文）
        if domain_id is None:
            try:
                from ai_domain_context import get_current_domain
                domain_id = get_current_domain()
            except ImportError:
                domain_id = "cth"

        # 0b. 跨域权限检查：ZBMP 角色不天然拥有 CTH Admin 权限
        if role and not self._check_role_domain_permission(role, domain_id, operation_type):
            return self._deny(
                operation_type, resource, risk_level or RiskLevel.HIGH,
                PermissionLevel.VERIFY, caller or self.default_caller, operation_id,
                reason=f"跨域权限拒绝: role={role} 不具备 domain={domain_id} 的 "
                       f"{operation_type.value} 操作权限（ZBMP 角色不天然拥有 CTH 权限，反之亦然）",
            )

        # 1. 幂等性检查
        if operation_id:
            with self._idempotency_lock:
                if operation_id in self._idempotency_cache:
                    cached = self._idempotency_cache[operation_id]
                    cached.idempotent_hit = True
                    logger.debug(f"[PermissionGate] 幂等命中: operation_id={operation_id}")
                    return cached

        # 记录当前检查的域身份（用于结果标记）
        self._current_check_domain = domain_id

        # 2. 操作注册检查（fail-closed）
        spec = self._registry.get(operation_type)
        if spec is None:
            if self.fail_closed:
                result = self._deny(
                    operation_type, resource, risk_level or RiskLevel.HIGH,
                    PermissionLevel.VERIFY, caller or self.default_caller,
                    operation_id,
                    reason=f"操作类型未注册且 fail_closed=True: {operation_type.value}",
                )
                return result
            # fail_open 模式：未注册操作按 MEDIUM 风险、VERIFY 权限处理
            spec = OperationSpec(
                PermissionLevel.VERIFY, RiskLevel.MEDIUM,
                f"未注册操作（fail_open）: {operation_type.value}", auto_allow=True)

        # 3. 确定最终风险等级（显式传入优先，否则用注册表默认）
        final_risk = risk_level or spec.risk

        # 4. 权限等级检查
        if not self.has_permission(spec.permission):
            result = self._deny(
                operation_type, resource, final_risk, spec.permission,
                caller or self.default_caller, operation_id,
                reason=f"权限等级不足: 需要 {spec.permission.value}，"
                       f"当前启用 {[p.value for p in self._enabled_permissions]}",
            )
            return result

        # 5. 高风险操作需人工审批
        if self.require_human_approval(final_risk):
            # 检查是否有有效审批令牌
            if self._has_valid_approval(operation_type.value, resource):
                token = self._get_approval_token(operation_type.value, resource)
                result = self._allow(
                    operation_type, resource, final_risk, spec.permission,
                    caller or self.default_caller, operation_id,
                    reason=f"高风险操作已获人工审批（token={token[:8]}...）",
                    requires_approval=True,
                    approval_token=token,
                )
                return result
            # 无审批令牌 → 拒绝（fail-closed）
            result = self._deny(
                operation_type, resource, final_risk, spec.permission,
                caller or self.default_caller, operation_id,
                reason=f"风险等级 {final_risk.value} 需人工审批，当前无有效审批令牌",
                requires_approval=True,
            )
            return result

        # 6. auto_allow 检查
        if not spec.auto_allow:
            result = self._deny(
                operation_type, resource, final_risk, spec.permission,
                caller or self.default_caller, operation_id,
                reason=f"操作 {operation_type.value} 标记为 auto_allow=False，需显式审批",
                requires_approval=True,
            )
            return result

        # 7. 通过
        result = self._allow(
            operation_type, resource, final_risk, spec.permission,
            caller or self.default_caller, operation_id,
            reason=f"权限检查通过: {operation_type.value} (risk={final_risk.value})",
        )
        return result

    def require_human_approval(self, risk_level: RiskLevel) -> bool:
        """判断是否需要人工审批（HIGH 及以上）。"""
        return RiskLevel.rank(risk_level) >= RiskLevel.rank(RiskLevel.HIGH)

    # ──────────────────────────────────────────────────────────
    # 人工审批令牌管理
    # ──────────────────────────────────────────────────────────

    def grant_approval(
        self,
        operation: str,
        duration_minutes: int = 30,
        resource: Optional[str] = None,
        granted_by: str = "human",
    ) -> str:
        """授予人工审批令牌。

        Args:
            operation: 授权的操作类型（OperationType.value 或 "*" 表示全部）
            duration_minutes: 有效期（分钟）
            resource: 授权的资源范围（None 表示该操作全部）
            granted_by: 授权人标识

        Returns:
            审批令牌字符串
        """
        token = self._generate_token()
        now = datetime.now()
        approval = ApprovalToken(
            token=token,
            operation=operation,
            resource=resource,
            granted_at=now,
            expires_at=now + timedelta(minutes=duration_minutes),
            granted_by=granted_by,
        )
        with self._approval_lock:
            self._approvals[token] = approval
        logger.info(f"[PermissionGate] 人工审批已授予: operation={operation}, "
                     f"resource={resource}, duration={duration_minutes}min, "
                     f"token={token[:8]}...")
        self._write_audit(
            operation_type=operation, resource=resource,
            risk_level=RiskLevel.HIGH.value, permission_required="human_approval",
            caller=granted_by, result="approval_granted",
            reason=f"人工审批授予: {operation} (有效期 {duration_minutes} 分钟)",
            operation_id=None, approval_token=token,
        )
        return token

    def revoke_approval(self, token: str) -> bool:
        """撤销人工审批令牌。

        Returns:
            True 表示成功撤销，False 表示令牌不存在
        """
        with self._approval_lock:
            if token in self._approvals:
                self._approvals[token].revoked = True
                logger.info(f"[PermissionGate] 人工审批已撤销: token={token[:8]}...")
                return True
        return False

    def revoke_all_approvals(self) -> int:
        """撤销所有审批令牌。返回撤销数量。"""
        count = 0
        with self._approval_lock:
            for approval in self._approvals.values():
                if not approval.revoked:
                    approval.revoked = True
                    count += 1
        logger.info(f"[PermissionGate] 已撤销所有审批令牌: {count} 个")
        return count

    def is_approved(self, operation: str, resource: Optional[str] = None) -> bool:
        """检查指定操作/资源是否有有效审批令牌。"""
        return self._has_valid_approval(operation, resource)

    def get_valid_approval_token(self, operation: str, resource: Optional[str] = None) -> Optional[str]:
        """返回指定操作/资源当前有效的人工审批令牌（供一次性消费方使用）。

        生产调用方不应直接读取内部审批字典。这个窄接口让需要消费令牌的
        handler 在成功执行后撤销同一令牌，避免一次人工确认被重放。
        """
        return self._get_approval_token(operation, resource)

    def _has_valid_approval(self, operation: str, resource: Optional[str] = None) -> bool:
        with self._approval_lock:
            for approval in self._approvals.values():
                if approval.is_valid(operation, resource):
                    return True
        return False

    def _get_approval_token(self, operation: str, resource: Optional[str] = None) -> Optional[str]:
        with self._approval_lock:
            for approval in self._approvals.values():
                if approval.is_valid(operation, resource):
                    return approval.token
        return None

    def list_approvals(self) -> List[Dict[str, Any]]:
        """列出所有审批令牌（含已撤销/已过期）。"""
        now = datetime.now()
        result = []
        with self._approval_lock:
            for approval in self._approvals.values():
                result.append({
                    "token": approval.token[:8] + "...",
                    "operation": approval.operation,
                    "resource": approval.resource,
                    "granted_at": approval.granted_at.isoformat(),
                    "expires_at": approval.expires_at.isoformat(),
                    "granted_by": approval.granted_by,
                    "revoked": approval.revoked,
                    "expired": now > approval.expires_at,
                    "valid": approval.is_valid(approval.operation, approval.resource),
                })
        return result

    @staticmethod
    def _generate_token() -> str:
        """生成审批令牌。"""
        raw = f"{uuid.uuid4().hex}{datetime.now().isoformat()}"
        return "apr_" + hashlib.sha256(raw.encode()).hexdigest()[:32]

    # ──────────────────────────────────────────────────────────
    # 审计日志
    # ──────────────────────────────────────────────────────────

    def _allow(
        self,
        operation_type: OperationType,
        resource: Optional[str],
        risk_level: RiskLevel,
        permission: PermissionLevel,
        caller: str,
        operation_id: Optional[str],
        reason: str,
        requires_approval: bool = False,
        approval_token: Optional[str] = None,
    ) -> PermissionResult:
        """构造允许结果并写入审计。"""
        audit_id = self._write_audit(
            operation_type=operation_type.value, resource=resource,
            risk_level=risk_level.value, permission_required=permission.value,
            caller=caller, result="allowed", reason=reason,
            operation_id=operation_id, approval_token=approval_token,
        )
        result = PermissionResult(
            allowed=True, reason=reason, requires_approval=requires_approval,
            approval_token=approval_token, audit_id=audit_id,
            operation_type=operation_type.value, resource=resource,
            risk_level=risk_level.value, permission_required=permission.value,
            caller=caller, operation_id=operation_id,
            domain_id=getattr(self, '_current_check_domain', None),
        )
        if operation_id:
            with self._idempotency_lock:
                self._idempotency_cache[operation_id] = result
        return result

    def _deny(
        self,
        operation_type: OperationType,
        resource: Optional[str],
        risk_level: RiskLevel,
        permission: PermissionLevel,
        caller: str,
        operation_id: Optional[str],
        reason: str,
        requires_approval: bool = False,
    ) -> PermissionResult:
        """构造拒绝结果并写入审计。"""
        audit_id = self._write_audit(
            operation_type=operation_type.value, resource=resource,
            risk_level=risk_level.value, permission_required=permission.value,
            caller=caller, result="denied", reason=reason,
            operation_id=operation_id, approval_token=None,
        )
        result = PermissionResult(
            allowed=False, reason=reason, requires_approval=requires_approval,
            approval_token=None, audit_id=audit_id,
            operation_type=operation_type.value, resource=resource,
            risk_level=risk_level.value, permission_required=permission.value,
            caller=caller, operation_id=operation_id,
            domain_id=getattr(self, '_current_check_domain', None),
        )
        if operation_id:
            with self._idempotency_lock:
                self._idempotency_cache[operation_id] = result
        return result

    def _write_audit(
        self,
        operation_type: str,
        resource: Optional[str],
        risk_level: str,
        permission_required: str,
        caller: str,
        result: str,
        reason: str,
        operation_id: Optional[str],
        approval_token: Optional[str],
    ) -> str:
        """写入审计日志（内存 + 可选文件持久化）。"""
        audit_id = "aud_" + hashlib.sha256(
            f"{uuid.uuid4().hex}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        entry = AuditEntry(
            audit_id=audit_id,
            timestamp=datetime.now().isoformat(),
            operation_type=operation_type,
            resource=resource,
            risk_level=risk_level,
            permission_required=permission_required,
            caller=caller,
            result=result,
            reason=reason,
            operation_id=operation_id,
            approval_token=approval_token[:8] + "..." if approval_token else None,
            idempotent_hit=False,
        )
        with self._audit_lock:
            self._audit_log.append(entry)
            # 限制内存日志最多 10000 条
            if len(self._audit_log) > 10000:
                self._audit_log = self._audit_log[-10000:]

        # 可选文件持久化
        if self.audit_log_path:
            try:
                os.makedirs(os.path.dirname(self.audit_log_path) or ".", exist_ok=True)
                with open(self.audit_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"[PermissionGate] 审计日志持久化失败: {e}")

        return audit_id

    def get_audit_log(
        self,
        limit: int = 100,
        operation_type: Optional[str] = None,
        result_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查询审计日志。"""
        with self._audit_lock:
            entries = list(self._audit_log)
        if operation_type:
            entries = [e for e in entries if e.operation_type == operation_type]
        if result_filter:
            entries = [e for e in entries if e.result == result_filter]
        return [asdict(e) for e in entries[-limit:]]

    def get_audit_stats(self) -> Dict[str, Any]:
        """获取审计统计。"""
        with self._audit_lock:
            total = len(self._audit_log)
            allowed = sum(1 for e in self._audit_log if e.result == "allowed")
            denied = sum(1 for e in self._audit_log if e.result == "denied")
            approvals = sum(1 for e in self._audit_log if e.result == "approval_granted")
        return {
            "total": total,
            "allowed": allowed,
            "denied": denied,
            "approvals_granted": approvals,
            "approval_rate": f"{(approvals / total * 100):.1f}%" if total else "0%",
        }

    # ──────────────────────────────────────────────────────────
    # 幂等性
    # ──────────────────────────────────────────────────────────

    def clear_idempotency_cache(self) -> int:
        """清空幂等性缓存。返回清除数量。"""
        with self._idempotency_lock:
            count = len(self._idempotency_cache)
            self._idempotency_cache.clear()
        return count


    # ──────────────────────────────────────────────────────────
    # ZBC V2.0 双域权限：角色-域权限映射
    # ──────────────────────────────────────────────────────────

    # 角色定义：每个角色拥有的域权限
    # ZBMP Analyst 不天然拥有 CTH Admin 权限
    ROLE_DOMAIN_PERMISSIONS: Dict[str, Dict[str, Set[str]]] = {
        "cth_admin": {
            "cth": {"*"},  # CTH 域全部操作
            "zbmp": {"read", "audit", "analyze"},  # 仅只读 ZBMP
        },
        "cth_analyst": {
            "cth": {"read", "audit", "analyze", "research", "report_generate", "ai_call"},
            "zbmp": {"read"},
        },
        "zbmp_admin": {
            "zbmp": {"*"},  # ZBMP 域全部操作
            "cth": {"read", "audit"},  # 仅只读 CTH（不能写/删/改配置）
        },
        "zbmp_analyst": {
            "zbmp": {"read", "audit", "analyze", "research", "report_generate", "ai_call"},
            "cth": set(),  # ZBMP Analyst 无 CTH 权限
        },
        "system": {
            "cth": {"*"},
            "zbmp": {"*"},
        },
    }

    def _check_role_domain_permission(
        self,
        role: str,
        domain_id: str,
        operation_type: OperationType,
    ) -> bool:
        """检查角色是否拥有指定域的操作权限。

        核心规则：
        - ZBMP Analyst 不天然拥有 CTH Admin 权限
        - 跨域写操作默认拒绝
        - 同域操作按角色权限放行
        - 未注册角色默认拒绝（fail-closed）
        """
        role_perms = self.ROLE_DOMAIN_PERMISSIONS.get(role)
        if role_perms is None:
            # 未注册角色：fail-closed
            return False

        domain_perms = role_perms.get(domain_id, set())
        if "*" in domain_perms:
            return True

        op_value = operation_type.value
        # 写操作类：跨域严格拒绝
        write_ops = {"file_write", "config_modify", "db_write", "data_delete",
                     "data_import", "collector_start", "collector_stop",
                     "runtime_operation", "ad_execute"}
        if op_value in write_ops and op_value not in domain_perms:
            return False

        return op_value in domain_perms

    def get_role_domain_matrix(self) -> Dict[str, Any]:
        """获取角色-域权限矩阵（用于审计/状态接口）。"""
        return {
            "roles": list(self.ROLE_DOMAIN_PERMISSIONS.keys()),
            "matrix": {
                role: {domain: sorted(perms) for domain, perms in domains.items()}
                for role, domains in self.ROLE_DOMAIN_PERMISSIONS.items()
            },
            "key_rule": "ZBMP Analyst does not inherently have CTH Admin permissions; cross-domain writes denied by default",
            "fail_closed": True,
        }

    # ──────────────────────────────────────────────────────────
    # 健康检查 / 状态
    # ──────────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """健康检查。"""
        now = datetime.now()
        with self._approval_lock:
            active_approvals = sum(
                1 for a in self._approvals.values()
                if not a.revoked and now <= a.expires_at
            )
        return {
            "status": "healthy",
            "fail_closed": self.fail_closed,
            "registered_operations": len(self._registry),
            "enabled_permissions": len(self._enabled_permissions),
            "audit_log_count": len(self._audit_log),
            "active_approvals": active_approvals,
            "idempotency_cache_size": len(self._idempotency_cache),
            "timestamp": now.isoformat(),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取完整状态。"""
        return {
            "fail_closed": self.fail_closed,
            "default_caller": self.default_caller,
            "enabled_permissions": self.get_enabled_permissions(),
            "registered_operations": self.list_operations(),
            "audit_stats": self.get_audit_stats(),
            "active_approvals": self.list_approvals(),
            "health": self.health_check(),
        }


# ═══════════════════════════════════════════════════════════════
# 7. 装饰器 @require_permission
# ═══════════════════════════════════════════════════════════════

def require_permission(
    operation_type: OperationType,
    risk_level: Optional[RiskLevel] = None,
    gate: Optional[PermissionGate] = None,
    resource: Optional[str] = None,
    deny_return: Any = None,
    domain_id: Optional[str] = None,
    role: Optional[str] = None,
):
    """权限检查装饰器。

    用于任何函数，自动检查权限并记录审计。
    权限不通过时返回 deny_return（默认 None），不执行函数体。

    用法：
        @require_permission(OperationType.FILE_WRITE, RiskLevel.MEDIUM)
        def write_config(path, content):
            ...

        # 或使用自定义 gate
        @require_permission(OperationType.DB_WRITE, gate=my_gate)
        def update_record(record_id, data):
            ...

    Args:
        operation_type: 操作类型
        risk_level: 风险等级（None 则使用注册表默认）
        gate: PermissionGate 实例（None 则使用全局单例）
        resource: 资源标识（None 则使用函数名）
        deny_return: 权限拒绝时的返回值
        domain_id: 域身份（cth/zbmp），None 则从线程上下文读取
        role: 调用者角色，用于跨域权限检查
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _gate = gate or get_permission_gate()
            _resource = resource or f"{func.__module__}.{func.__qualname__}"
            result = _gate.check(
                operation_type=operation_type,
                resource=_resource,
                risk_level=risk_level,
                caller=func.__qualname__,
                domain_id=domain_id,
                role=role,
            )
            if not result.allowed:
                logger.warning(
                    f"[require_permission] 权限拒绝: {func.__qualname__} "
                    f"(op={operation_type.value}, risk={result.risk_level}) "
                    f"reason={result.reason}"
                )
                # deny_return 可为 callable（延迟求值，避免模块级 jsonify 等需 app_context 的调用）
                if callable(deny_return):
                    return deny_return()
                return deny_return
            return func(*args, **kwargs)
        # 附加权限元信息，便于内省
        wrapper._permission_required = operation_type
        wrapper._risk_level = risk_level
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# 8. 全局单例
# ═══════════════════════════════════════════════════════════════

_default_gate: Optional[PermissionGate] = None
_gate_lock = threading.Lock()


def get_permission_gate() -> PermissionGate:
    """获取全局 PermissionGate 单例。"""
    global _default_gate
    if _default_gate is None:
        with _gate_lock:
            if _default_gate is None:
                _default_gate = PermissionGate()
    return _default_gate


def reset_permission_gate() -> None:
    """重置全局单例（测试用）。"""
    global _default_gate
    with _gate_lock:
        _default_gate = None


# ═══════════════════════════════════════════════════════════════
# 9. 便捷导出
# ═══════════════════════════════════════════════════════════════

__all__ = [
    "PermissionLevel",
    "RiskLevel",
    "OperationType",
    "OperationSpec",
    "PermissionResult",
    "ApprovalToken",
    "AuditEntry",
    "PermissionGate",
    "require_permission",
    "get_permission_gate",
    "reset_permission_gate",
    "set_testing_bypass",
    "is_testing_bypass_enabled",
]
