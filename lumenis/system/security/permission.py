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
import ipaddress
import json
import logging
import os
import re
import secrets
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple
from urllib.parse import urlsplit

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


def _local_workspace_authority_allowed(authority: str) -> bool:
    if type(authority) is not str:
        return False
    match = re.fullmatch(
        r"(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?",
        authority,
        flags=re.IGNORECASE,
    )
    if match is None:
        return False
    port = match.group(1)
    return port is None or 1 <= int(port) <= 65535


_LOCAL_WORKSPACE_IDENTITY_HEADERS = frozenset({
    "x-actor-id",
    "x-user-id",
    "x-lumenis-actor-id",
    "x-lumenis-user-id",
    "x-principal-id",
    "x-principal-ref",
})


def _local_workspace_transport_allowed(
    *, reject_identity_headers: bool = False,
) -> bool:
    """Validate the explicit open-workspace loopback transport boundary."""
    try:
        from flask import current_app, has_request_context, request

        if not has_request_context():
            return False
        if current_app.config.get("LUMENIS_OPEN_WORKSPACE") is not True:
            return False

        headers = request.headers
        names = {name.casefold() for name in headers.keys()}
        if reject_identity_headers and names.intersection(
            _LOCAL_WORKSPACE_IDENTITY_HEADERS
        ):
            return False
        if any(
            name == "forwarded" or name.startswith("x-forwarded-")
            for name in names
        ):
            return False
        if "authorization" in names:
            return False

        from lumenis.config import AUTH_CONFIG

        session_cookie = AUTH_CONFIG.get("session_cookie_name")
        if type(session_cookie) is not str or not session_cookie:
            return False
        raw_cookie = headers.get("Cookie", "")
        if session_cookie in request.cookies or any(
            part.partition("=")[0].strip() == session_cookie
            for part in raw_cookie.split(";")
        ):
            return False

        if not _local_workspace_authority_allowed(headers.get("Host")):
            return False
        origin = headers.get("Origin")
        if origin is not None:
            if origin != origin.strip() or any(
                ord(char) < 32 or ord(char) == 127 for char in origin
            ):
                return False
            if "?" in origin or "#" in origin:
                return False
            parsed = urlsplit(origin)
            if (
                parsed.scheme.casefold() not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or not _local_workspace_authority_allowed(parsed.netloc)
            ):
                return False

        remote_addr = request.remote_addr
        if type(remote_addr) is not str or "%" in remote_addr:
            return False
        return ipaddress.ip_address(remote_addr).is_loopback
    except Exception:
        # Missing request/auth context and malformed client input fail closed.
        return False


def local_workspace_read_allowed(
    module: str = "subject_registry", action: str = "read"
) -> bool:
    """Allow anonymous loopback reads only when the owner opens the workspace."""
    if type(module) is not str or module not in {
        "subject_registry", "commercial_realtime_stream", "brand_market_overview"
    }:
        return False
    if type(action) is not str or action != "read":
        return False
    return _local_workspace_transport_allowed()


_LOCAL_WORKSPACE_PRINCIPAL_SEAL = object()


@dataclass(frozen=True, init=False)
class LocalWorkspacePrincipal:
    """Server-issued principal for the one explicitly opened local workspace."""

    principal_kind: str
    principal_ref: str
    actor_id: None
    _issuer: object = field(repr=False, compare=False)

    def __init__(self, *, _issuer: object):
        if _issuer is not _LOCAL_WORKSPACE_PRINCIPAL_SEAL:
            raise TypeError("LocalWorkspacePrincipal is server-issued")
        object.__setattr__(self, "principal_kind", "local_workspace")
        object.__setattr__(self, "principal_ref", "workspace:local")
        object.__setattr__(self, "actor_id", None)
        object.__setattr__(self, "_issuer", _issuer)


def _is_server_local_workspace_principal(value: Any) -> bool:
    try:
        return (
            type(value) is LocalWorkspacePrincipal
            and value._issuer is _LOCAL_WORKSPACE_PRINCIPAL_SEAL
            and value.principal_kind == "local_workspace"
            and value.principal_ref == "workspace:local"
            and value.actor_id is None
        )
    except Exception:
        return False


def resolve_local_workspace_principal(
    *, module: str = "content", action: str = "read",
) -> Optional[LocalWorkspacePrincipal]:
    """Resolve the fixed workspace principal from the current server request."""
    if (
        type(module) is not str
        or module not in {"content", "reports", "cases", "collector", "owned_training", "owned_model_admission", "skills", "browser", "evidence"}
        or type(action) is not str
        or action not in _RESOURCE_SCOPE_ACTIONS
    ):
        return None
    if not _local_workspace_transport_allowed(reject_identity_headers=True):
        return None
    return LocalWorkspacePrincipal(_issuer=_LOCAL_WORKSPACE_PRINCIPAL_SEAL)


def owned_training_identity(
    *, actor_id: Optional[int] = None,
    principal: Optional[LocalWorkspacePrincipal] = None,
) -> Dict[str, Any]:
    """Resolve an authenticated account or the explicitly open local workspace."""
    if actor_id is not None:
        if principal is not None:
            raise ValueError("account and local workspace identities cannot be mixed")
        if type(actor_id) is not int or actor_id <= 0:
            raise ValueError("a positive authenticated actor id is required")
        return {
            "actor_id": actor_id,
            "caller": f"actor:{actor_id}",
            "principal_kind": None,
            "principal_ref": None,
            "identity_kind": "account",
        }

    if principal is None or not _is_server_local_workspace_principal(principal):
        raise ValueError("a server-issued local workspace principal is required")
    current = resolve_local_workspace_principal(
        module="owned_training", action="write",
    )
    if current is None:
        raise ValueError("the local workspace is not currently open")
    return {
        "actor_id": None,
        "caller": "workspace:local",
        "principal_kind": "local_workspace",
        "principal_ref": "workspace:local",
        "identity_kind": "workspace",
    }

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
    MODEL_TRAIN = "model_train"                  # 经批准的模型训练
    OWNED_TRAINING_REVIEW_PREVIEW = "owned_training_review_preview"
    COLLECTOR_START = "collector_start"          # 采集器启动
    COLLECTOR_STOP = "collector_stop"            # 采集器停止
    DATA_IMPORT = "data_import"                  # 数据导入
    COLLECTOR_SOURCE_READ = "collector_source_read"
    COLLECTOR_SOURCE_ANALYZE = "collector_source_analyze"
    DATA_EXPORT = "data_export"                  # 数据导出
    REPORT_GENERATE = "report_generate"          # 报告生成
    REPORT_REVIEW = "report_review"              # 既有报告的追加审核意见
    CTH_CASE_CREATE = "cth_case_create"           # 只登记有来源的内部工作 Case
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
    OperationType.REPORT_REVIEW: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "追加指定报告的审核意见，不改原产物/源事实，不发布或执行建议", auto_allow=True),
    OperationType.MODEL_TRAIN: OperationSpec(
        PermissionLevel.COMMIT, RiskLevel.HIGH,
        "绑定精确模型、配方、数据和授权范围的训练（需人工审批）", auto_allow=False),
    OperationType.OWNED_TRAINING_REVIEW_PREVIEW: OperationSpec(
        PermissionLevel.PLAN, RiskLevel.LOW,
        "只读准备精确训练材料审核资源；不授予权利、目标或训练批准", auto_allow=True),
    OperationType.CTH_CASE_CREATE: OperationSpec(
        PermissionLevel.VERIFY, RiskLevel.MEDIUM,
        "登记有来源的内部CTH工作Case，不修改源事实、不执行Action或外部发布", auto_allow=True),

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
    OperationType.COLLECTOR_SOURCE_READ: OperationSpec(
        PermissionLevel.READ, RiskLevel.LOW,
        "读取精确收集原文供获准的内部采后处理", auto_allow=False),
    OperationType.COLLECTOR_SOURCE_ANALYZE: OperationSpec(
        PermissionLevel.ANALYZE, RiskLevel.LOW,
        "精确收集原文的内部关键词候选分析", auto_allow=False),
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
class ActorScopePermissionResult(PermissionResult):
    """Exact actor/resource decision while keeping the legacy serializer stable."""

    actor_id: Optional[int] = None
    subject_id: Optional[str] = None
    brand_focus_id: Optional[str] = None
    global_scope: bool = False
    scope_action: Optional[str] = None
    scope_audit_id: Optional[str] = None
    verification_state: str = "verified"
    code: Optional[str] = None
    principal_kind: Optional[str] = None
    principal_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Keep existing PermissionResult JSON keys for compatibility."""
        return {
            name: getattr(self, name)
            for name in PermissionResult.__dataclass_fields__
        }

    def to_scope_dict(self) -> Dict[str, Any]:
        """Serialize exact-scope evidence only for callers that opt in."""
        payload = self.to_dict()
        payload.update({
            "actor_id": self.actor_id,
            "subject_id": self.subject_id,
            "brand_focus_id": self.brand_focus_id,
            "global_scope": self.global_scope,
            "scope_action": self.scope_action,
            "scope_audit_id": self.scope_audit_id,
            "verification_state": self.verification_state,
            "code": self.code,
            "principal_kind": self.principal_kind,
            "principal_ref": self.principal_ref,
        })
        return payload


_RESOURCE_SCOPE_DOMAINS = {
    "cth": ("CTH", "subject_ids", "CTH", "company"),
    "bmp": ("ZBMP", "brand_focus_ids", "BMP", "brand"),
}
_RESOURCE_SCOPE_ACTIONS = frozenset({"read", "write"})


def _canonical_business_domain_id(domain_id: Any) -> str:
    """Resolve an accepted domain alias to its persisted identity for comparisons.

    Permission lookup keys and serialized resources intentionally retain the
    historical ``bmp`` spelling. Scope and approval receipts use ``zbmp``.
    This helper is only for comparing those identities; callers must keep
    their existing resource construction and authorization checks unchanged.
    """
    if type(domain_id) is not str or not domain_id or domain_id != domain_id.strip():
        return ""
    try:
        from domain_isolation import resolve_domain_identity

        canonical, _ = resolve_domain_identity(domain_id=domain_id)
    except (TypeError, ValueError):
        return ""
    return canonical if canonical in {"cth", "zbmp"} else ""


def _is_valid_scope_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and len(value) <= 256
        and not any(ord(character) < 32 for character in value)
    )


def _scope_grant_matches(
    data_scope: Any,
    *,
    domain_id: str,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    global_scope: bool,
) -> bool:
    """Match the account owner's explicit, domain-specific JSON data_scope."""
    if not isinstance(data_scope, str) or not data_scope.strip():
        return False
    try:
        scope = json.loads(data_scope)
    except (TypeError, ValueError):
        return False
    if not isinstance(scope, dict):
        return False

    domain_config = _RESOURCE_SCOPE_DOMAINS.get(domain_id)
    if domain_config is None:
        return False
    _product_id, scope_key, _registry_domain, _subject_type = domain_config
    if not set(scope).issubset({"global", scope_key}):
        return False
    global_grant = scope.get("global", False)
    if type(global_grant) is not bool:
        return False

    scoped_ids = scope.get(scope_key, [])
    if not isinstance(scoped_ids, list) or any(
        not _is_valid_scope_id(value) for value in scoped_ids
    ):
        return False
    if global_scope:
        return global_grant is True
    requested_id = subject_id if domain_id == "cth" else brand_focus_id
    return global_grant is True or requested_id in scoped_ids


def _require_canonical_scope_connection(connection):
    """Validate a borrowed real SQLite connection against the Shared repository.

    This does not open, commit, close or upgrade a database connection. Client
    dictionaries, alternate files, attached stores and altered row readers are
    never accepted as canonical account/registry authority.
    """
    import sqlite3
    from pathlib import Path
    from lumenis.shared.database import DatabaseRepository, get_repository, main_db_path

    if (type(connection) is not sqlite3.Connection
            or connection.row_factory is not sqlite3.Row
            or connection.text_factory is not str):
        raise ValueError("RESOURCE_SCOPE_CONNECTION_INVALID")
    repository = get_repository()
    if type(repository) is not DatabaseRepository:
        raise ValueError("RESOURCE_SCOPE_CONNECTION_INVALID")
    try:
        expected = Path(repository.db_path or main_db_path()).resolve(strict=True)
        databases = connection.execute("PRAGMA database_list").fetchall()
        if (len(databases) != 1 or databases[0][1] != "main" or not databases[0][2]
                or Path(databases[0][2]).resolve(strict=True) != expected
                or not os.path.samefile(databases[0][2], expected)
                or connection.execute("PRAGMA read_uncommitted").fetchone()[0] != 0):
            raise ValueError("RESOURCE_SCOPE_CONNECTION_INVALID")
    except (OSError, sqlite3.Error) as exc:
        raise ValueError("RESOURCE_SCOPE_CONNECTION_INVALID") from exc
    return connection


def _registered_resource_scope_exists(
    domain_id: str,
    *,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    connection=None,
) -> bool:
    """Require an active canonical registry row for every selected focus."""
    from subject_registry import list_subjects

    _product_id, _scope_key, registry_domain, subject_type = (
        _RESOURCE_SCOPE_DOMAINS[domain_id]
    )
    rows = (list_subjects(registry_domain) if connection is None else
            list_subjects(registry_domain, connection=_require_canonical_scope_connection(connection)))
    if not isinstance(rows, list):
        raise RuntimeError("canonical subject registry response is invalid")

    if domain_id == "cth":
        matches = [
            row for row in rows
            if isinstance(row, Mapping)
            and row.get("domain_id") == registry_domain
            and row.get("subject_type") == subject_type
            and row.get("subject_id") == subject_id
        ]
    else:
        matches = [
            row for row in rows
            if isinstance(row, Mapping)
            and row.get("domain_id") == registry_domain
            and row.get("subject_type") == subject_type
            and row.get("brand_focus_id") == brand_focus_id
        ]
    if len(matches) > 1:
        raise RuntimeError("canonical resource scope is not unique")
    # Registry listings retain some inactive rows for diagnosis. Existence
    # alone cannot authorize their use, including use by an owner/admin.
    return len(matches) == 1 and matches[0].get("status") in {"configured", "active"}


def _load_actor_scope_role(actor_id: int, *, connection=None) -> Optional[str]:
    """Resolve the active role from the account owner, never from request data."""
    from account.models import get_db

    conn = get_db() if connection is None else _require_canonical_scope_connection(connection)
    try:
        row = conn.execute(
            "SELECT role FROM v4_users WHERE id = ? AND status = 'active'",
            (actor_id,),
        ).fetchone()
        return str(row["role"]).strip().lower() if row else None
    finally:
        if connection is None:
            conn.close()


def _load_actor_scope_grants(actor_id: int, *, connection=None) -> List[Dict[str, Any]]:
    """Read existing account grants; their data_scope is evaluated here."""
    from account.authorization import get_member_authorizations

    grants = (get_member_authorizations(actor_id) if connection is None else
              get_member_authorizations(actor_id, connection=_require_canonical_scope_connection(connection)))
    if not isinstance(grants, list):
        raise RuntimeError("account authorization response is invalid")
    return grants


def _actor_has_scope_action(
    actor_id: int, product_id: str, module: str, action: str, *, connection=None
) -> bool:
    """Retain the account owner's active-user and product/module/action gate."""
    from account.authorization import check_dual_domain_permission

    connection_options = {} if connection is None else {
        "connection": _require_canonical_scope_connection(connection)}
    return bool(check_dual_domain_permission(
        actor_id, product_id, module=module, action=action, **connection_options
    ))


def check_actor_scope_permission(
    actor: Optional[Mapping[str, Any]],
    *,
    domain_id: str,
    action: str,
    module: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
    gate: Optional["PermissionGate"] = None,
    connection=None,
) -> ActorScopePermissionResult:
    """Check one authenticated actor against one exact CTH Subject or BMP focus.

    Actor identity must come from the server-authenticated session. Context
    selects a resource but never grants permission. Non-owner grants require an
    explicit matching JSON data_scope; only a literal global=true is global.
    Selected resources are verified against the canonical subject registry.
    """
    try:
        from domain_isolation import resolve_domain_identity
        receipt_domain, _ = resolve_domain_identity(domain_id=domain_id)
    except (TypeError, ValueError):
        receipt_domain = ""
    # Permission lookup uses the BMP compatibility key while receipts use the
    # canonical persisted domain ID, matching PermissionGate.check().
    normalized_domain = "bmp" if receipt_domain == "zbmp" else receipt_domain
    domain_config = _RESOURCE_SCOPE_DOMAINS.get(normalized_domain)

    try:
        actor_id = actor.get("id") if isinstance(actor, Mapping) else None
    except Exception:
        actor_id = None
    valid_actor_id = type(actor_id) is int and actor_id > 0

    action_value = action.strip().lower() if isinstance(action, str) else ""
    module_value = module.strip() if isinstance(module, str) else ""
    scope_subject_id: Optional[str] = None
    scope_brand_focus_id: Optional[str] = None
    valid_scope_form = False
    if domain_config is not None and type(global_scope) is bool:
        if global_scope:
            valid_scope_form = subject_id is None and brand_focus_id is None
        elif normalized_domain == "cth":
            valid_scope_form = (
                brand_focus_id is None and _is_valid_scope_id(subject_id)
            )
            if valid_scope_form:
                scope_subject_id = subject_id
        else:
            valid_scope_form = (
                subject_id is None and _is_valid_scope_id(brand_focus_id)
            )
            if valid_scope_form:
                scope_brand_focus_id = brand_focus_id

    valid_request = (
        valid_actor_id
        and domain_config is not None
        and action_value in _RESOURCE_SCOPE_ACTIONS
        and 0 < len(module_value) <= 128
        and module_value != "*"
        and not any(ord(character) < 32 for character in module_value)
        and type(global_scope) is bool
        and valid_scope_form
    )
    allowed = False
    verified = True
    reason = "actor or requested resource scope is invalid"

    if valid_request:
        product_id = domain_config[0]
        try:
            connection_options = {} if connection is None else {
                "connection": _require_canonical_scope_connection(connection)}
            if not _actor_has_scope_action(
                actor_id, product_id, module_value, action_value, **connection_options
            ):
                reason = "actor lacks active product, module, or action permission"
            else:
                role = _load_actor_scope_role(actor_id, **connection_options)
                if role is None:
                    raise RuntimeError("active actor role unavailable")
                if not global_scope and not _registered_resource_scope_exists(
                    normalized_domain,
                    subject_id=scope_subject_id,
                    brand_focus_id=scope_brand_focus_id, **connection_options,
                ):
                    reason = "requested resource is not a registered active scope"
                elif role in {"owner", "admin"}:
                    # An active owner/admin role is an explicit account-wide
                    # authority, not an empty or missing data_scope grant.
                    allowed = True
                    reason = "active account role has account-wide authority"
                else:
                    grants = _load_actor_scope_grants(actor_id, **connection_options)
                    for grant in grants:
                        if not isinstance(grant, Mapping):
                            continue
                        grant_product = grant.get("product_id")
                        grant_module = grant.get("module")
                        grant_action = grant.get("action")
                        time_range = grant.get("time_range")
                        if (
                            not isinstance(grant_product, str)
                            or grant_product.upper() != product_id
                            or grant_module not in {"*", module_value}
                            or grant_action != action_value
                            # No time-window contract exists in this checker.
                            # Do not silently widen a grant that declares one.
                            or time_range not in (None, "")
                        ):
                            continue
                        if _scope_grant_matches(
                            grant.get("data_scope"),
                            domain_id=normalized_domain,
                            subject_id=scope_subject_id,
                            brand_focus_id=scope_brand_focus_id,
                            global_scope=global_scope,
                        ):
                            allowed = True
                            break
                    reason = (
                        "actor has an explicit grant for the requested scope"
                        if allowed
                        else "actor has no explicit grant for the requested scope"
                    )
        except Exception:
            logger.exception("Resource scope permission lookup failed")
            verified = False
            reason = "resource scope permission could not be verified"

    selected_resource = (
        "GLOBAL / ALL"
        if global_scope is True
        else (scope_subject_id or scope_brand_focus_id or "missing")
    )
    audit_id: Optional[str] = None
    try:
        permission_gate = gate if gate is not None else get_permission_gate()
        audit_id = permission_gate._write_audit(
            operation_type=f"resource_scope_{action_value or 'invalid'}",
            resource=f"{normalized_domain or 'unknown'}:{selected_resource}",
            risk_level="low" if action_value == "read" else "medium",
            permission_required=action_value or "read",
            caller=f"actor:{actor_id}" if valid_actor_id else "anonymous",
            result="allowed" if allowed else "denied",
            reason=reason,
            operation_id=None,
            approval_token=None,
        )
        if not isinstance(audit_id, str) or not audit_id:
            raise RuntimeError("permission audit identifier unavailable")
    except Exception:
        logger.exception("Resource scope permission audit failed")
        allowed = False
        verified = False
        audit_id = None
        reason = "resource scope permission could not be verified"

    return ActorScopePermissionResult(
        allowed=allowed,
        reason=reason,
        audit_id=audit_id,
        operation_type=f"resource_scope_{action_value or 'invalid'}",
        resource=f"{normalized_domain or 'unknown'}:{selected_resource}",
        risk_level="low" if action_value == "read" else "medium",
        permission_required=action_value or "read",
        caller=f"actor:{actor_id}" if valid_actor_id else "anonymous",
        domain_id=receipt_domain or None,
        actor_id=actor_id if valid_actor_id else None,
        subject_id=scope_subject_id,
        brand_focus_id=scope_brand_focus_id,
        global_scope=global_scope is True,
        scope_action=action_value or None,
        scope_audit_id=audit_id,
        verification_state="verified" if verified else "unavailable",
    )


def check_local_workspace_scope_permission(
    principal: Any,
    *,
    domain_id: str,
    action: str,
    module: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
    gate: Optional["PermissionGate"] = None,
    connection=None,
) -> ActorScopePermissionResult:
    """Admit one local workspace principal to an exact registered module scope.

    This is scope admission, not approval or an Effect Fence capability. The
    workspace transport boundary is revalidated for every call.
    """
    principal_valid = _is_server_local_workspace_principal(principal)
    caller = "workspace:local" if principal_valid else "anonymous"
    normalized_domain = (
        domain_id.strip().lower() if isinstance(domain_id, str) else ""
    )
    if normalized_domain == "zbmp":
        normalized_domain = "bmp"
    domain_config = _RESOURCE_SCOPE_DOMAINS.get(normalized_domain)
    action_value = action if type(action) is str else ""
    module_value = module if type(module) is str else ""

    scope_subject_id: Optional[str] = None
    scope_brand_focus_id: Optional[str] = None
    valid_scope_form = False
    if domain_config is not None and type(global_scope) is bool:
        if global_scope:
            valid_scope_form = subject_id is None and brand_focus_id is None
        elif normalized_domain == "cth":
            valid_scope_form = (
                brand_focus_id is None and _is_valid_scope_id(subject_id)
            )
            if valid_scope_form:
                scope_subject_id = subject_id
        else:
            valid_scope_form = (
                subject_id is None and _is_valid_scope_id(brand_focus_id)
            )
            if valid_scope_form:
                scope_brand_focus_id = brand_focus_id

    valid_request = (
        domain_config is not None
        and module_value in {"content", "reports", "cases", "collector", "owned_training", "owned_model_admission", "skills", "evidence"}
        and (module_value != "cases" or normalized_domain == "cth")
        and action_value in _RESOURCE_SCOPE_ACTIONS
        and type(global_scope) is bool
        and valid_scope_form
    )
    transport_allowed = (
        principal_valid
        and _local_workspace_transport_allowed(reject_identity_headers=True)
    )
    allowed = False
    verified = True
    code: Optional[str] = None
    if not principal_valid:
        reason = "local workspace principal is invalid"
        code = "invalid_principal"
    elif not transport_allowed:
        reason = "local workspace request is unavailable"
        code = "workspace_unavailable"
    elif not valid_request:
        reason = "requested Content scope is invalid"
        code = "invalid_scope"
    else:
        try:
            connection_options = {} if connection is None else {
                "connection": _require_canonical_scope_connection(connection)}
            if global_scope:
                allowed = True
                reason = "local workspace may access the explicit canonical global scope"
            elif _registered_resource_scope_exists(
                normalized_domain,
                subject_id=scope_subject_id,
                brand_focus_id=scope_brand_focus_id, **connection_options,
            ):
                allowed = True
                reason = "local workspace may access the registered exact scope"
            else:
                reason = "requested resource is not a registered active scope"
                code = "scope_not_registered"
        except Exception:
            logger.exception("Local workspace scope verification failed")
            verified = False
            reason = "resource scope permission could not be verified"
            code = "scope_unavailable"

    selected_resource = (
        "GLOBAL / ALL"
        if global_scope is True and valid_scope_form
        else (scope_subject_id or scope_brand_focus_id or "invalid")
    )
    audit_id: Optional[str] = None
    try:
        permission_gate = gate if gate is not None else get_permission_gate()
        audit_id = permission_gate._write_audit(
            operation_type=f"resource_scope_{action_value or 'invalid'}",
            resource=f"{normalized_domain if domain_config else 'unknown'}:{selected_resource}",
            risk_level="low" if action_value == "read" else "medium",
            permission_required=action_value or "read",
            caller=caller,
            result="allowed" if allowed else "denied",
            reason=reason,
            operation_id=None,
            approval_token=None,
        )
        if not isinstance(audit_id, str) or not audit_id:
            raise RuntimeError("permission audit identifier unavailable")
    except Exception:
        logger.exception("Local workspace scope audit failed")
        allowed = False
        verified = False
        code = "audit_unavailable"
        audit_id = None
        reason = "resource scope permission could not be verified"

    principal_kind = "local_workspace" if principal_valid else None
    principal_ref = "workspace:local" if principal_valid else None
    resource = f"{normalized_domain if domain_config else 'unknown'}:{selected_resource}"
    return ActorScopePermissionResult(
        allowed=allowed,
        reason=reason,
        audit_id=audit_id,
        operation_type=f"resource_scope_{action_value or 'invalid'}",
        resource=resource,
        risk_level="low" if action_value == "read" else "medium",
        permission_required=action_value or "read",
        caller=caller,
        domain_id=normalized_domain or None,
        actor_id=None,
        subject_id=scope_subject_id,
        brand_focus_id=scope_brand_focus_id,
        global_scope=global_scope is True,
        scope_action=action_value or None,
        scope_audit_id=audit_id,
        verification_state="verified" if verified else "unavailable",
        code=code,
        principal_kind=principal_kind,
        principal_ref=principal_ref,
    )


def bind_scope_permission_approval(
    scope_permission: ActorScopePermissionResult,
    approval_permission: PermissionResult,
    *,
    gate: Optional["PermissionGate"] = None,
) -> ActorScopePermissionResult:
    """Bind server receipts to a live exact approval without granting an effect.

    Both receipts must have been audited by this Gate. The caller must still
    recheck account scope and approval immediately before performing a write.
    Scope fields remain opt-in through ``to_scope_dict``.
    """
    permission_gate = gate if gate is not None else get_permission_gate()
    scope = (
        scope_permission if type(scope_permission) is ActorScopePermissionResult
        else ActorScopePermissionResult(allowed=False, reason="invalid scope receipt")
    )
    approval = (
        approval_permission if isinstance(approval_permission, PermissionResult)
        else PermissionResult(allowed=False, reason="invalid approval receipt")
    )
    verified = scope.verification_state == "verified"
    try:
        from domain_isolation import resolve_domain_identity
        scope_domain, _ = resolve_domain_identity(domain_id=scope.domain_id)
        approval_domain, _ = resolve_domain_identity(domain_id=approval.domain_id)
    except (TypeError, ValueError):
        scope_domain = approval_domain = ""
    # The scope owner retains `bmp` as its internal compatibility key, while
    # receipts and PermissionGate use canonical `zbmp`. Compare identity after
    # the shared resolver, but retain exact operation/resource/audit matching.
    scope_lookup_domain = "bmp" if scope_domain == "zbmp" else scope_domain
    focus = scope.subject_id if scope_lookup_domain == "cth" else scope.brand_focus_id
    other_focus = scope.brand_focus_id if scope_lookup_domain == "cth" else scope.subject_id
    valid_scope = (
        scope_domain in {"cth", "zbmp"}
        and scope_lookup_domain in _RESOURCE_SCOPE_DOMAINS
        and type(scope.global_scope) is bool
        and (
            focus is None and other_focus is None if scope.global_scope
            else _is_valid_scope_id(focus) and other_focus is None
        )
    )
    scope_resource = f"{scope_lookup_domain}:{'GLOBAL / ALL' if scope.global_scope else focus}"
    matched = (
        not is_testing_bypass_enabled()
        and valid_scope and scope.resource == scope_resource
        and scope.allowed is True and verified
        and scope.scope_action == "write"
        and scope.operation_type == "resource_scope_write"
        and type(scope.actor_id) is int and scope.actor_id > 0
        and scope.caller == f"actor:{scope.actor_id}"
        and bool(scope.audit_id) and scope.scope_audit_id == scope.audit_id
        and approval.allowed is True and approval.requires_approval is True
        and bool(approval.approval_token) and bool(approval.audit_id)
        and approval.resource == scope.resource
        and approval.caller == scope.caller
        and approval_domain == scope_domain
    )
    try:
        if matched:
            audits = permission_gate.get_audit_log(limit=10000, result_filter="allowed")
            matched = (
                permission_gate.get_valid_approval_token(
                    approval.operation_type, approval.resource, exact=True
                ) == approval.approval_token
                and any(
                    entry["audit_id"] == scope.audit_id
                    and entry["operation_type"] == "resource_scope_write"
                    and entry["resource"] == scope.resource
                    and entry["caller"] == scope.caller
                    and entry["permission_required"] == "write"
                    for entry in audits
                )
                and any(
                    entry["audit_id"] == approval.audit_id
                    and entry["operation_type"] == approval.operation_type
                    and entry["resource"] == approval.resource
                    and entry["caller"] == approval.caller
                    and entry["approval_token"] == approval.approval_token[:8] + "..."
                    for entry in audits
                )
            )
    except Exception:
        logger.exception("Resource scope approval verification failed")
        matched, verified = False, False
    reason = (
        "human approval is bound to the authorized resource scope"
        if matched else "matching audited scope and live exact approval are required"
    )
    audit_id = None
    try:
        audit_id = permission_gate._write_audit(
            operation_type="resource_scope_approval", resource=scope.resource,
            risk_level="high", permission_required="write+human_approval",
            caller=scope.caller or "unknown", result="allowed" if matched else "denied",
            reason=reason, operation_id=approval.operation_id if matched else None,
            approval_token=approval.approval_token if matched else None,
        )
        if not isinstance(audit_id, str) or not audit_id:
            raise RuntimeError("permission audit identifier unavailable")
    except Exception:
        logger.exception("Resource scope approval audit failed")
        matched, verified, audit_id = False, False, None
        reason = "resource scope approval could not be verified"
    return ActorScopePermissionResult(
        allowed=matched, reason=reason, requires_approval=True,
        approval_token=approval.approval_token if matched else None, audit_id=audit_id,
        operation_type=approval.operation_type, resource=scope.resource,
        risk_level="high", permission_required="write+human_approval",
        caller=scope.caller, operation_id=approval.operation_id if matched else None,
        domain_id=scope_domain or scope.domain_id, actor_id=scope.actor_id,
        subject_id=scope.subject_id, brand_focus_id=scope.brand_focus_id,
        global_scope=scope.global_scope, scope_action=scope.scope_action,
        scope_audit_id=scope.audit_id,
        verification_state="verified" if verified else "unavailable",
    )


_OWNED_TRAINING_SCOPE_DESCRIPTOR_FIELDS = frozenset({
    "domain_id", "product_id", "global_scope", "subject_id", "brand_focus_id",
})


def _owned_training_payload(
    request: Any, *, actor_id: Optional[int] = None, domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[LocalWorkspacePrincipal] = None,
) -> Dict[str, Any]:
    """Validate a typed training request and canonical CTH/BMP scope mapping."""
    from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest

    if type(request) is not TrainingApprovalRequest:
        raise ValueError("a canonical TrainingApprovalRequest is required")
    identity = owned_training_identity(actor_id=actor_id, principal=principal)
    actor_id = identity["actor_id"]
    if type(domain_id) is not str or not domain_id or domain_id != domain_id.strip():
        raise ValueError("a canonical training domain is required")
    normalized_domain = domain_id.lower()
    if normalized_domain == "zbmp":
        normalized_domain = "bmp"
    domain_config = _RESOURCE_SCOPE_DOMAINS.get(normalized_domain)
    if domain_config is None:
        raise ValueError("training domain must be CTH or BMP")
    canonical_domain = _canonical_business_domain_id(normalized_domain)
    if not canonical_domain:
        raise ValueError("training domain must be CTH or BMP")
    if type(request.domain_id) is not str or request.domain_id != normalized_domain:
        raise ValueError("training request domain must match the authorized domain")
    product_id = domain_config[0]

    def valid_text(value: Any, *, limit: int = 512) -> bool:
        return (type(value) is str and bool(value) and value == value.strip()
                and len(value) <= limit and not any(ord(char) < 32 for char in value))

    if not all(valid_text(value) for value in (
        request.model_id, request.model_revision, request.recipe,
    )):
        raise ValueError("training model, revision, and recipe must be explicit")
    hashes = (request.manifest_sha256, request.train_sha256, request.heldout_sha256)
    if any(type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value)
           for value in hashes):
        raise ValueError("training manifest and dataset hashes must be SHA-256")
    scopes = request.scopes
    if (type(scopes) is not tuple or not scopes
            or any(not valid_text(scope, limit=256) for scope in scopes)
            or len(set(scopes)) != len(scopes)):
        raise ValueError("training scopes must be a unique explicit tuple")
    if type(context) is not dict or set(context) != {"scope_descriptors"}:
        raise ValueError("canonical scope descriptors are required")
    descriptors = context.get("scope_descriptors")
    if type(descriptors) is not dict or set(descriptors) != set(scopes):
        raise ValueError("every training scope needs exactly one descriptor")

    normalized_descriptors = []
    for scope in scopes:
        descriptor = descriptors[scope]
        if (type(descriptor) is not dict
                or set(descriptor) != _OWNED_TRAINING_SCOPE_DESCRIPTOR_FIELDS
                or descriptor.get("domain_id") != normalized_domain
                or descriptor.get("product_id") != product_id
                or type(descriptor.get("global_scope")) is not bool):
            raise ValueError("training scope descriptor is invalid or cross-domain")
        is_global = descriptor["global_scope"]
        subject_id = descriptor.get("subject_id")
        brand_focus_id = descriptor.get("brand_focus_id")
        if is_global:
            if scope != "GLOBAL / ALL" or subject_id is not None or brand_focus_id is not None:
                raise ValueError("global training scope must use the exact global descriptor")
        elif normalized_domain == "cth":
            if (not _is_valid_scope_id(subject_id) or brand_focus_id is not None
                    or scope != subject_id):
                raise ValueError("CTH training scope must name its exact registered Subject")
        elif (subject_id is not None or not _is_valid_scope_id(brand_focus_id)
              or scope != brand_focus_id):
            raise ValueError("BMP training scope must name its exact registered BrandFocus")
        normalized_descriptors.append({
            "scope": scope, "domain_id": normalized_domain, "product_id": product_id,
            "global_scope": is_global, "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
        })
    payload = {
        "schema_version": 1, "operation": OperationType.MODEL_TRAIN.value,
        "actor_id": actor_id, "domain_id": normalized_domain,
        "request_domain_id": request.domain_id,
        "model_id": request.model_id, "model_revision": request.model_revision,
        "recipe": request.recipe, "manifest_sha256": request.manifest_sha256,
        "train_sha256": request.train_sha256,
        "heldout_sha256": request.heldout_sha256,
        "scopes": list(scopes), "scope_descriptors": normalized_descriptors,
    }
    if identity["identity_kind"] == "workspace":
        payload["principal_kind"] = identity["principal_kind"]
        payload["principal_ref"] = identity["principal_ref"]
    return payload


def owned_training_approval_resource(
    request: Any, *, actor_id: Optional[int] = None, domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[LocalWorkspacePrincipal] = None,
) -> str:
    """Build the exact opaque Permission resource for one training request.

    ``context`` is ``{"scope_descriptors": {scope: descriptor}}``. Each
    descriptor has exactly ``domain_id``, ``product_id``, ``global_scope``,
    ``subject_id`` and ``brand_focus_id``. It identifies resources; it never
    grants access. GLOBAL / ALL is an exact label, not a permission wildcard.
    """
    payload = _owned_training_payload(
        request, actor_id=actor_id, domain_id=domain_id, context=context,
        principal=principal,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
    return "owned_training:v1:" + hashlib.sha256(canonical).hexdigest()


def owned_training_phase_fingerprints(
    request: Any, *, actor_id: Optional[int] = None, domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[LocalWorkspacePrincipal] = None,
) -> Dict[str, str]:
    """Bind public phase challenges to the validated private training request.

    All hashes use UTF-8, sorted JSON keys, compact separators and no NaN.
    Identity and approval tokens are deliberately excluded from public hashes;
    the TaskEngine binding retains the exact private Permission resource.
    A recipe identifies the fixed Gateway recipe, not a claim of source quality.
    """
    payload = _owned_training_payload(
        request, actor_id=actor_id, domain_id=domain_id, context=context,
        principal=principal,
    )

    def digest(value: Any) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    scope = {
        "schema_version": 1, "domain_id": payload["domain_id"],
        "scopes": payload["scopes"], "scope_descriptors": payload["scope_descriptors"],
    }
    model = {
        "schema_version": 1, "model_id": payload["model_id"],
        "model_revision": payload["model_revision"],
    }
    recipe = {"schema_version": 1, "recipe": payload["recipe"]}
    public_request = {
        "schema_version": 1, "operation": OperationType.MODEL_TRAIN.value,
        "domain_id": payload["domain_id"], "model_id": payload["model_id"],
        "model_revision": payload["model_revision"], "recipe": payload["recipe"],
        "manifest_sha256": payload["manifest_sha256"],
        "train_sha256": payload["train_sha256"], "heldout_sha256": payload["heldout_sha256"],
        "scopes": payload["scopes"], "scope_descriptors": payload["scope_descriptors"],
    }
    return {
        "request_sha256": digest(public_request), "model_identity_sha256": digest(model),
        "manifest_sha256": payload["manifest_sha256"],
        "train_sha256": payload["train_sha256"], "heldout_sha256": payload["heldout_sha256"],
        "recipe_sha256": digest(recipe), "scope_sha256": digest(scope),
    }


def make_owned_training_approval_verifier(
    gate: "PermissionGate", *, actor_id: Optional[int] = None,
    domain_id: str, context: Mapping[str, Any],
    principal: Optional[LocalWorkspacePrincipal] = None,
) -> Callable[[Any], bool]:
    """Create a fail-closed verifier that rechecks exact scope and training approval."""
    if type(gate) is not PermissionGate:
        raise ValueError("the canonical PermissionGate is required")
    frozen_identity = dict(owned_training_identity(
        actor_id=actor_id, principal=principal,
    ))
    if type(domain_id) is not str or not domain_id or domain_id != domain_id.strip():
        raise ValueError("a canonical training domain is required")
    normalized_domain = domain_id.lower()
    if normalized_domain == "zbmp":
        normalized_domain = "bmp"
    domain_config = _RESOURCE_SCOPE_DOMAINS.get(normalized_domain)
    if domain_config is None:
        raise ValueError("training domain must be CTH or BMP")
    canonical_domain = _canonical_business_domain_id(normalized_domain)
    if not canonical_domain:
        raise ValueError("training domain must be CTH or BMP")
    # Copy and validate the descriptor map once so caller mutation cannot widen it.
    if type(context) is not dict or set(context) != {"scope_descriptors"}:
        raise ValueError("canonical scope descriptors are required")
    descriptors = context.get("scope_descriptors")
    if type(descriptors) is not dict:
        raise ValueError("canonical scope descriptors are required")
    frozen_context = {"scope_descriptors": {
        key: dict(value) if type(value) is dict else value
        for key, value in descriptors.items()
    }}

    def verify(request: Any) -> bool:
        try:
            identity = owned_training_identity(
                actor_id=actor_id, principal=principal,
            )
            if identity != frozen_identity:
                return False
            resource = owned_training_approval_resource(
                request, actor_id=actor_id, domain_id=normalized_domain,
                context=frozen_context, principal=principal,
            )
            if is_testing_bypass_enabled() or not gate.has_permission(PermissionLevel.COMMIT):
                return False
            payload = _owned_training_payload(
                request, actor_id=actor_id, domain_id=normalized_domain,
                context=frozen_context, principal=principal,
            )
            caller = identity["caller"]
            for descriptor in payload["scope_descriptors"]:
                if identity["identity_kind"] == "workspace":
                    scope = check_local_workspace_scope_permission(
                        principal, domain_id=normalized_domain, action="write",
                        module="owned_training", subject_id=descriptor["subject_id"],
                        brand_focus_id=descriptor["brand_focus_id"],
                        global_scope=descriptor["global_scope"], gate=gate,
                    )
                else:
                    scope = check_actor_scope_permission(
                        {"id": actor_id}, domain_id=normalized_domain, action="write",
                        module="owned_training", subject_id=descriptor["subject_id"],
                        brand_focus_id=descriptor["brand_focus_id"],
                        global_scope=descriptor["global_scope"], gate=gate,
                    )
                expected_focus = (
                    descriptor["subject_id"]
                    if normalized_domain == "cth"
                    else descriptor["brand_focus_id"]
                )
                expected_resource = f"{normalized_domain}:{'GLOBAL / ALL' if descriptor['global_scope'] else expected_focus}"
                if not (
                    type(scope) is ActorScopePermissionResult and scope.allowed is True
                    and scope.verification_state == "verified"
                    and scope.actor_id == identity["actor_id"]
                    and scope.caller == caller
                    and _canonical_business_domain_id(scope.domain_id) == canonical_domain
                    and scope.principal_kind == identity["principal_kind"]
                    and scope.principal_ref == identity["principal_ref"]
                    and scope.subject_id == descriptor["subject_id"]
                    and scope.brand_focus_id == descriptor["brand_focus_id"]
                    and scope.global_scope is descriptor["global_scope"]
                    and scope.scope_action == "write"
                    and scope.operation_type == "resource_scope_write"
                    and scope.resource == expected_resource and bool(scope.audit_id)
                    and scope.scope_audit_id == scope.audit_id
                ):
                    return False
            approval = gate.check(
                OperationType.MODEL_TRAIN, resource=resource, caller=caller,
                domain_id=normalized_domain, exact_approval_required=True,
            )
            token = gate.get_valid_approval_token(
                OperationType.MODEL_TRAIN.value, resource, exact=True,
            )
            return bool(
                approval.allowed is True and approval.requires_approval is True
                and approval.operation_type == OperationType.MODEL_TRAIN.value
                and approval.resource == resource and approval.caller == caller
                and _canonical_business_domain_id(approval.domain_id) == canonical_domain
                and approval.approval_token and token == approval.approval_token
            )
        except Exception:
            logger.exception("Owned training approval verification failed")
            return False

    return verify


@dataclass(frozen=True)
class SkillMetadataPermissionDecision:
    """Fresh metadata authority; serialized evidence contains no approval token."""

    allowed: bool
    code: str
    resource: Optional[str] = None
    operation_id: Optional[str] = None
    candidate_sha256: Optional[str] = None
    actor_id: Optional[int] = None
    caller: Optional[str] = None
    principal_kind: Optional[str] = None
    principal_ref: Optional[str] = None
    domain_id: Optional[str] = None
    subject_id: Optional[str] = None
    brand_focus_id: Optional[str] = None
    global_scope: bool = False
    permission_audit_id: Optional[str] = None
    scope_audit_id: Optional[str] = None
    approval_token_sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _skill_metadata_identity(
    *, actor_id: Optional[int], principal: Optional[LocalWorkspacePrincipal],
) -> Dict[str, Any]:
    if actor_id is not None:
        if principal is not None or type(actor_id) is not int or actor_id <= 0:
            raise ValueError("SKILL_METADATA_IDENTITY_INVALID")
        from flask import has_request_context
        from lumenis.auth.service import get_current_user

        if not has_request_context():
            raise ValueError("SKILL_METADATA_AUTHENTICATED_REQUEST_REQUIRED")
        actor = get_current_user(read_only=True)
        if type(actor) is not dict or type(actor.get("id")) is not int or actor["id"] != actor_id:
            raise ValueError("SKILL_METADATA_ACTOR_MISMATCH")
        return dict(actor_id=actor_id, caller=f"actor:{actor_id}",
                    principal_kind=None, principal_ref=None)
    if not _is_server_local_workspace_principal(principal) or \
            resolve_local_workspace_principal(module="skills", action="write") is None:
        raise ValueError("SKILL_METADATA_WORKSPACE_UNAVAILABLE")
    return dict(actor_id=None, caller="workspace:local",
                principal_kind="local_workspace", principal_ref="workspace:local")


def _skill_metadata_payload(
    candidate: Any, *, actor_id: Optional[int],
    principal: Optional[LocalWorkspacePrincipal], domain_id: str,
    subject_id: Optional[str], brand_focus_id: Optional[str], global_scope: bool,
) -> Dict[str, Any]:
    from lumenis.shared.agents.skills.lifecycle import SCHEMA_VERSION, _validate_candidate

    _validate_candidate(candidate)
    identity = _skill_metadata_identity(actor_id=actor_id, principal=principal)
    if type(domain_id) is not str or domain_id != domain_id.strip():
        raise ValueError("SKILL_METADATA_SCOPE_INVALID")
    domain = domain_id.lower()
    if domain == "zbmp":
        domain = "bmp"
    if domain not in _RESOURCE_SCOPE_DOMAINS or type(global_scope) is not bool:
        raise ValueError("SKILL_METADATA_SCOPE_INVALID")
    if global_scope:
        valid = subject_id is None and brand_focus_id is None
    elif domain == "cth":
        valid = _is_valid_scope_id(subject_id) and brand_focus_id is None
    else:
        valid = _is_valid_scope_id(brand_focus_id) and subject_id is None
    if not valid:
        raise ValueError("SKILL_METADATA_SCOPE_INVALID")
    return {
        "schema_version": SCHEMA_VERSION, "skill_id": candidate.skill_id,
        "action": candidate.action, "operation_id": candidate.operation_id,
        "before_sha256": candidate.before_sha256, "after_sha256": candidate.after_sha256,
        "candidate_sha256": candidate.candidate_sha256,
        "config_sha256": candidate.config_sha256,
        "restore_evidence_ref": candidate.restore_evidence_ref,
        "identity": identity,
        "scope": dict(domain_id=domain, subject_id=subject_id,
                      brand_focus_id=brand_focus_id, global_scope=global_scope),
    }


def skill_metadata_approval_resource(
    candidate: Any, *, actor_id: Optional[int] = None,
    principal: Optional[LocalWorkspacePrincipal] = None, domain_id: str,
    subject_id: Optional[str] = None, brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
) -> str:
    """Bind the server-prepared candidate, actual identity and exact scope."""
    payload = _skill_metadata_payload(
        candidate, actor_id=actor_id, principal=principal, domain_id=domain_id,
        subject_id=subject_id, brand_focus_id=brand_focus_id, global_scope=global_scope,
    )
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "skills_registry_change:v1:" + hashlib.sha256(canonical).hexdigest()


def check_skill_metadata_change_permission(
    candidate: Any, *, gate: "PermissionGate", actor_id: Optional[int] = None,
    principal: Optional[LocalWorkspacePrincipal] = None, domain_id: str,
    subject_id: Optional[str] = None, brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
) -> SkillMetadataPermissionDecision:
    """Recheck live role, scope and exact manual approval without cached grants."""
    fields: Dict[str, Any] = {}

    def denied(code: str) -> SkillMetadataPermissionDecision:
        if type(gate) is PermissionGate:
            try:
                audit_id = gate._write_audit(
                    operation_type="skill_metadata_permission", resource=fields.get("resource"),
                    risk_level=RiskLevel.HIGH.value, permission_required=PermissionLevel.COMMIT.value,
                    caller=fields.get("caller") or "anonymous", result="denied", reason=code,
                    operation_id=None, approval_token=None,
                )
                if type(audit_id) is str and audit_id:
                    fields["permission_audit_id"] = audit_id
            except Exception:
                pass
        return SkillMetadataPermissionDecision(allowed=False, code=code, **fields)

    try:
        if type(gate) is not PermissionGate or gate is not get_permission_gate() or not gate.fail_closed:
            return denied("SKILL_METADATA_CANONICAL_PERMISSION_REQUIRED")
        payload = _skill_metadata_payload(
            candidate, actor_id=actor_id, principal=principal, domain_id=domain_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id, global_scope=global_scope,
        )
        identity, scope_args = payload["identity"], payload["scope"]
        fields.update(identity, **scope_args, operation_id=candidate.operation_id,
                      candidate_sha256=candidate.candidate_sha256)
        fields["resource"] = skill_metadata_approval_resource(
            candidate, actor_id=actor_id, principal=principal, **scope_args,
        )
        spec = gate.get_operation_spec(OperationType.CONFIG_MODIFY)
        if (is_testing_bypass_enabled() or not gate.has_permission(PermissionLevel.COMMIT)
                or type(spec) is not OperationSpec or spec.permission is not PermissionLevel.COMMIT
                or spec.risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL} or spec.auto_allow is not False):
            return denied("SKILL_METADATA_MANUAL_APPROVAL_REQUIRED")
        if actor_id is not None and _load_actor_scope_role(actor_id) not in {"owner", "admin"}:
            return denied("SKILL_METADATA_ADMIN_REQUIRED")
        if actor_id is None:
            scope = check_local_workspace_scope_permission(
                principal, module="skills", action="write", gate=gate, **scope_args,
            )
        else:
            scope = check_actor_scope_permission(
                {"id": actor_id}, module="skills", action="write", gate=gate, **scope_args,
            )
        canonical_domain = _canonical_business_domain_id(scope_args["domain_id"])
        if not canonical_domain:
            return denied("SKILL_METADATA_SCOPE_DENIED")
        focus = scope_args["subject_id"] or scope_args["brand_focus_id"]
        scope_resource = f"{scope_args['domain_id']}:{'GLOBAL / ALL' if scope_args['global_scope'] else focus}"
        expected_scope = {**identity, **scope_args}
        expected_scope.pop("domain_id", None)
        if not (type(scope) is ActorScopePermissionResult and scope.allowed is True
                and scope.verification_state == "verified" and scope.scope_action == "write"
                and scope.operation_type == "resource_scope_write" and scope.resource == scope_resource
                and scope.audit_id and scope.scope_audit_id == scope.audit_id
                and _canonical_business_domain_id(scope.domain_id) == canonical_domain
                and all(getattr(scope, key) == value for key, value in expected_scope.items())):
            return denied("SKILL_METADATA_SCOPE_DENIED")
        fields["scope_audit_id"] = scope.scope_audit_id
        approval = gate.check(
            OperationType.CONFIG_MODIFY, resource=fields["resource"], caller=identity["caller"],
            domain_id=scope_args["domain_id"], exact_approval_required=True,
        )
        token = gate.get_valid_approval_token(OperationType.CONFIG_MODIFY.value, fields["resource"], exact=True)
        if not (type(approval) is PermissionResult and approval.allowed is True
                and approval.requires_approval is True and approval.operation_id is None
                and approval.idempotent_hit is False and approval.audit_id
                and approval.operation_type == OperationType.CONFIG_MODIFY.value
                and approval.resource == fields["resource"] and approval.caller == identity["caller"]
                and _canonical_business_domain_id(approval.domain_id) == canonical_domain
                and approval.risk_level in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}
                and approval.permission_required == PermissionLevel.COMMIT.value
                and type(token) is str and bool(token) and token == approval.approval_token):
            return denied("SKILL_METADATA_MANUAL_APPROVAL_REQUIRED")
        fields.update(permission_audit_id=approval.audit_id,
                      approval_token_sha256=hashlib.sha256(token.encode("utf-8")).hexdigest())
        return SkillMetadataPermissionDecision(allowed=True, code="SKILL_METADATA_APPROVED", **fields)
    except Exception:
        return denied("SKILL_METADATA_PERMISSION_UNVERIFIED")


@dataclass(frozen=True)
class ContentSourceImport:
    """Server-derived upload identity, never a client-deserialized permission."""
    actor_id: Optional[int]
    domain_id: str
    subject_id: Optional[str]
    brand_focus_id: Optional[str]
    global_scope: bool
    filename: str
    size_bytes: int
    body_sha256: str
    principal_kind: Optional[str] = None
    principal_ref: Optional[str] = None


@dataclass
class _ContentSourceImportConfirmation:
    """Gate-owned nonce state; stores descriptor metadata, never file bytes."""
    confirmation_id: str
    actor_id: Optional[int]
    caller: str
    upload: ContentSourceImport
    resource: str
    expires_at: datetime
    state: str = "pending"
    approval_token: Optional[str] = None
    approval_expires_at: Optional[datetime] = None


@dataclass
class _ContentSourceImportGrant:
    """Caller/resource-bound authority layered over one exact approval token."""
    token: str
    actor_id: Optional[int]
    caller: str
    resource: str
    expires_at: datetime
    confirmation_id: str


_CONTENT_SOURCE_CONFIRMATION_TTL = timedelta(minutes=5)
_CONTENT_SOURCE_IMPORT_GRANT_TTL = timedelta(minutes=1)
_CONTENT_SOURCE_CONFIRMATION_CAPACITY = 128


def _content_source_actor_id(actor: Optional[Mapping[str, Any]]) -> Optional[int]:
    if not isinstance(actor, Mapping):
        return None
    actor_id = actor.get("id")
    return actor_id if type(actor_id) is int and actor_id > 0 else None


def _content_source_identity(
    actor: Optional[Mapping[str, Any]],
    principal: Optional[LocalWorkspacePrincipal],
) -> Tuple[Optional[int], str, Optional[str], Optional[str], Optional[str]]:
    """Return the server-derived caller identity; never infer it from JSON."""
    actor_id = _content_source_actor_id(actor)
    if principal is not None:
        if actor is None and _is_server_local_workspace_principal(principal):
            return None, "workspace:local", "local_workspace", "workspace:local", "local_workspace"
        return actor_id, "anonymous", None, None, None
    if actor_id is not None:
        return actor_id, f"actor:{actor_id}", None, None, "account"
    return None, "anonymous", None, None, None


def _content_source_upload_matches_identity(
    upload: ContentSourceImport,
    identity: Tuple[Optional[int], str, Optional[str], Optional[str], Optional[str]],
) -> bool:
    actor_id, caller, principal_kind, principal_ref, identity_kind = identity
    if type(upload) is not ContentSourceImport:
        return False
    if identity_kind == "account":
        return (
            type(actor_id) is int and actor_id > 0
            and type(upload.actor_id) is int and upload.actor_id == actor_id
            and upload.principal_kind is None and upload.principal_ref is None
        )
    if identity_kind == "local_workspace":
        return (
            caller == "workspace:local" and actor_id is None
            and upload.actor_id is None
            and upload.principal_kind == principal_kind
            and upload.principal_ref == principal_ref
        )
    return False


def _content_source_confirmation_denial(
    gate: "PermissionGate",
    code: str,
    *,
    actor_id: Optional[int] = None,
    upload: Optional[ContentSourceImport] = None,
    scope: Optional[ActorScopePermissionResult] = None,
    resource: Optional[str] = None,
    verification_state: str = "not_checked",
    caller: Optional[str] = None,
    principal_kind: Optional[str] = None,
    principal_ref: Optional[str] = None,
) -> ActorScopePermissionResult:
    caller = scope.caller if scope else caller or (
        f"actor:{actor_id}" if actor_id else "anonymous"
    )
    decision = gate._deny(
        OperationType.DB_WRITE, resource, RiskLevel.HIGH, PermissionLevel.COMMIT,
        caller, None, reason=code, requires_approval=True,
    )
    return ActorScopePermissionResult(
        **decision.to_dict(),
        actor_id=scope.actor_id if scope else actor_id,
        subject_id=scope.subject_id if scope else getattr(upload, "subject_id", None),
        brand_focus_id=scope.brand_focus_id if scope else getattr(upload, "brand_focus_id", None),
        global_scope=scope.global_scope if scope else bool(getattr(upload, "global_scope", False)),
        scope_action="write",
        scope_audit_id=scope.audit_id if scope else None,
        verification_state=scope.verification_state if scope else verification_state,
        code=code,
        principal_kind=scope.principal_kind if scope else principal_kind,
        principal_ref=scope.principal_ref if scope else principal_ref,
    )


def content_source_import_resource(
    scope_permission: ActorScopePermissionResult,
    upload: ContentSourceImport,
    *,
    gate: Optional["PermissionGate"] = None,
) -> str:
    """Bind an audited scope to actual upload bytes; grants no rights or effects."""
    account_identity = (
        type(upload) is ContentSourceImport
        and type(upload.actor_id) is int and upload.actor_id > 0
        and scope_permission.actor_id == upload.actor_id
        and scope_permission.caller == f"actor:{upload.actor_id}"
        and upload.principal_kind is None and upload.principal_ref is None
        and scope_permission.principal_kind is None
        and scope_permission.principal_ref is None
    ) if type(scope_permission) is ActorScopePermissionResult else False
    workspace_identity = (
        type(upload) is ContentSourceImport
        and upload.actor_id is None and scope_permission.actor_id is None
        and upload.principal_kind == "local_workspace"
        and upload.principal_ref == "workspace:local"
        and scope_permission.principal_kind == "local_workspace"
        and scope_permission.principal_ref == "workspace:local"
        and scope_permission.caller == "workspace:local"
    ) if type(scope_permission) is ActorScopePermissionResult else False
    if (
        type(scope_permission) is not ActorScopePermissionResult
        or scope_permission.allowed is not True
        or scope_permission.verification_state != "verified"
        or scope_permission.scope_action != "write"
        or scope_permission.operation_type != "resource_scope_write"
        or not scope_permission.audit_id
        or scope_permission.scope_audit_id != scope_permission.audit_id
        or type(upload) is not ContentSourceImport
        or not (account_identity or workspace_identity)
        or type(upload.global_scope) is not bool
        or _canonical_business_domain_id(upload.domain_id)
        != _canonical_business_domain_id(scope_permission.domain_id)
        or any(getattr(upload, key) != getattr(scope_permission, key) for key in (
            "actor_id", "subject_id", "brand_focus_id", "global_scope"
        ))
        or upload.domain_id not in {"cth", "bmp"}
        or type(upload.size_bytes) is not int
        or not 0 < upload.size_bytes <= 128 * 1024 * 1024
        or not isinstance(upload.body_sha256, str) or len(upload.body_sha256) != 64
        or any(character not in "0123456789abcdef" for character in upload.body_sha256)
        or not isinstance(upload.filename, str) or not 0 < len(upload.filename) <= 255
        or upload.filename.startswith(".") or upload.filename != upload.filename.strip()
        or upload.filename.endswith(".")
        or any(ord(character) < 32 or character in '/\\\\:*?"<>|' for character in upload.filename)
    ):
        raise ValueError("CONTENT_SOURCE_RESOURCE_BINDING_INVALID")
    focus = upload.subject_id if upload.domain_id == "cth" else upload.brand_focus_id
    other_focus = upload.brand_focus_id if upload.domain_id == "cth" else upload.subject_id
    valid_scope = (
        focus is None and other_focus is None if upload.global_scope
        else _is_valid_scope_id(focus) and other_focus is None
    )
    scope_resource = f"{upload.domain_id}:{'GLOBAL / ALL' if upload.global_scope else focus}"
    permission_gate = gate if gate is not None else get_permission_gate()
    if workspace_identity:
        principal = resolve_local_workspace_principal(module="content", action="write")
        if principal is None:
            permission_gate._revoke_local_content_source_import(upload)
            raise ValueError("CONTENT_SOURCE_SCOPE_AUDIT_UNVERIFIED")
        live_scope = check_local_workspace_scope_permission(
            principal, domain_id=upload.domain_id, action="write", module="content",
            subject_id=upload.subject_id, brand_focus_id=upload.brand_focus_id,
            global_scope=upload.global_scope, gate=permission_gate,
        )
        if (
            live_scope.allowed is not True
            or live_scope.resource != scope_resource
            or live_scope.caller != scope_permission.caller
        ):
            permission_gate._revoke_local_content_source_import(upload)
            raise ValueError("CONTENT_SOURCE_SCOPE_AUDIT_UNVERIFIED")
    if not valid_scope or scope_permission.resource != scope_resource or not any(
        entry["audit_id"] == scope_permission.audit_id
        and entry["caller"] == scope_permission.caller
        and entry["resource"] == scope_resource
        and entry["permission_required"] == "write"
        for entry in permission_gate.get_audit_log(
            limit=10000, operation_type="resource_scope_write", result_filter="allowed"
        )
    ):
        raise ValueError("CONTENT_SOURCE_SCOPE_AUDIT_UNVERIFIED")
    descriptor = asdict(upload)
    if upload.principal_kind is None and upload.principal_ref is None:
        # Keep the legacy actor resource hash stable for descriptors created
        # before the optional workspace-principal fields existed.
        descriptor.pop("principal_kind", None)
        descriptor.pop("principal_ref", None)
    binding = {
        "operation": OperationType.DB_WRITE.value, "scope_action": "write",
        "module": "content", **descriptor,
    }
    encoded = json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "content-source-import:v1:" + hashlib.sha256(encoded).hexdigest()


def check_content_source_import_permission(
    actor: Optional[Mapping[str, Any]],
    upload: ContentSourceImport,
    *,
    principal: Optional[LocalWorkspacePrincipal] = None,
    gate: Optional["PermissionGate"] = None,
) -> ActorScopePermissionResult:
    """Recheck live account/workspace scope and exact approval, without import.

    The caller must authenticate actor and derive the descriptor from bytes.
    This decision is a check-time receipt, not a reusable execution permit.
    Approval expiry/revocation is rechecked each call; source rights stay unknown.
    """
    permission_gate = gate if gate is not None else get_permission_gate()
    identity = _content_source_identity(actor, principal)
    actor_id, caller, principal_kind, principal_ref, identity_kind = identity
    if type(upload) is not ContentSourceImport:
        # A client dictionary is not a permission descriptor.  Refuse it at
        # the typed boundary instead of attempting attribute access or
        # accepting caller-supplied rights/approval fields.
        raise ValueError("CONTENT_SOURCE_RESOURCE_BINDING_INVALID")
    if not _content_source_upload_matches_identity(upload, identity):
        code = (
            "CONTENT_SOURCE_PRINCIPAL_MISMATCH"
            if identity_kind == "local_workspace" or upload.principal_kind is not None
            else "CONTENT_SOURCE_ACTOR_MISMATCH"
        )
        return _content_source_confirmation_denial(
            permission_gate, code, actor_id=actor_id, upload=upload,
            caller=caller, principal_kind=principal_kind, principal_ref=principal_ref,
        )
    try:
        scope = _content_source_scope_receipt(
            actor, principal=principal, domain_id=upload.domain_id,
            subject_id=upload.subject_id, brand_focus_id=upload.brand_focus_id,
            global_scope=upload.global_scope, gate=permission_gate,
        )
    except Exception:
        if identity_kind == "local_workspace":
            permission_gate._revoke_local_content_source_import(upload)
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
            actor_id=actor_id, upload=upload, verification_state="unavailable",
            caller=caller, principal_kind=principal_kind, principal_ref=principal_ref,
        )
    if scope.verification_state != "verified":
        if identity_kind == "local_workspace":
            permission_gate._revoke_local_content_source_import(upload)
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
            actor_id=actor_id, upload=upload, scope=scope,
            verification_state="unavailable",
        )
    if scope.allowed is not True:
        if identity_kind == "local_workspace":
            permission_gate._revoke_local_content_source_import(upload)
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_SCOPE_DENIED",
            actor_id=actor_id, upload=upload, scope=scope,
            verification_state="verified",
        )
    try:
        resource = content_source_import_resource(scope, upload, gate=permission_gate)
    except ValueError:
        if identity_kind == "local_workspace":
            permission_gate._revoke_local_content_source_import(upload)
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_RESOURCE_BINDING_INVALID",
            actor_id=actor_id, upload=upload, scope=scope, resource=scope.resource,
            verification_state="verified",
        )
    except Exception:
        if identity_kind == "local_workspace":
            permission_gate._revoke_local_content_source_import(upload)
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
            actor_id=actor_id, upload=upload, scope=scope, resource=scope.resource,
            verification_state="unavailable",
        )
    if is_testing_bypass_enabled():
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_TESTING_BYPASS_FORBIDDEN",
            actor_id=actor_id, upload=upload, scope=scope, resource=resource,
            verification_state="verified",
        )
    grant_token = permission_gate._find_content_import_grant(resource, scope.caller)
    try:
        # No operation_id: each invocation rechecks current account scope,
        # restricted confirmation grant, and the exact live approval token.
        decision = permission_gate.check(
            OperationType.DB_WRITE, resource=resource, risk_level=RiskLevel.HIGH,
            caller=scope.caller, domain_id=upload.domain_id,
            exact_approval_required=True, content_import_grant=grant_token,
        )
    except Exception:
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
            actor_id=actor_id, upload=upload, scope=scope, resource=resource,
            verification_state="unavailable",
        )
    if not decision.allowed:
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_CONFIRMATION_REQUIRED",
            actor_id=actor_id, upload=upload, scope=scope, resource=resource,
            verification_state="verified",
        )
    if (
        not decision.requires_approval
        or not decision.approval_token
        or not permission_gate._approval_token_is_valid(
            decision.approval_token, OperationType.DB_WRITE.value, resource,
        )
    ):
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_APPROVAL_UNVERIFIED",
            actor_id=actor_id, upload=upload, scope=scope, resource=resource,
            verification_state="unavailable",
        )
    return ActorScopePermissionResult(
        **decision.to_dict(), actor_id=scope.actor_id,
        subject_id=scope.subject_id, brand_focus_id=scope.brand_focus_id,
        global_scope=scope.global_scope, scope_action="write",
        scope_audit_id=scope.audit_id, verification_state="verified",
        code="CONTENT_SOURCE_IMPORT_ALLOWED",
        principal_kind=scope.principal_kind, principal_ref=scope.principal_ref,
    )


def _content_source_scope_receipt(
    actor: Optional[Mapping[str, Any]], *, domain_id: str,
    subject_id: Optional[str], brand_focus_id: Optional[str],
    global_scope: bool, gate: "PermissionGate",
    principal: Optional[LocalWorkspacePrincipal] = None,
) -> ActorScopePermissionResult:
    if principal is not None:
        if actor is not None:
            return _content_source_confirmation_denial(
                gate, "CONTENT_SOURCE_PRINCIPAL_MISMATCH",
                caller="anonymous", verification_state="verified",
            )
        return check_local_workspace_scope_permission(
            principal, domain_id=domain_id, action="write", module="content",
            subject_id=subject_id, brand_focus_id=brand_focus_id,
            global_scope=global_scope, gate=gate,
        )
    return check_actor_scope_permission(
        actor, domain_id=domain_id, action="write", module="content",
        subject_id=subject_id, brand_focus_id=brand_focus_id,
        global_scope=global_scope, gate=gate,
    )


def prepare_content_source_import_confirmation(
    actor: Optional[Mapping[str, Any]], upload: ContentSourceImport, *,
    principal: Optional[LocalWorkspacePrincipal] = None,
    gate: Optional["PermissionGate"] = None,
) -> dict:
    """Create a short-lived in-memory confirmation for a server-derived upload.

    No client JSON is converted into ``ContentSourceImport`` here. This call
    records only immutable descriptor metadata; media bytes are never retained.
    """
    permission_gate = gate if gate is not None else get_permission_gate()
    identity = _content_source_identity(actor, principal)
    actor_id, caller, principal_kind, principal_ref, identity_kind = identity
    if type(upload) is not ContentSourceImport:
        return {"allowed": False, "code": "CONTENT_SOURCE_RESOURCE_BINDING_INVALID",
                "verification_state": "unavailable"}
    if not _content_source_upload_matches_identity(upload, identity):
        code = (
            "CONTENT_SOURCE_PRINCIPAL_MISMATCH"
            if identity_kind == "local_workspace" or upload.principal_kind is not None
            else "CONTENT_SOURCE_ACTOR_MISMATCH"
        )
        return {"allowed": False, "code": code,
                "verification_state": "verified"}
    if is_testing_bypass_enabled():
        return {"allowed": False, "code": "CONTENT_SOURCE_TESTING_BYPASS_FORBIDDEN",
                "verification_state": "verified"}
    try:
        scope = _content_source_scope_receipt(
            actor, principal=principal, domain_id=upload.domain_id,
            subject_id=upload.subject_id,
            brand_focus_id=upload.brand_focus_id, global_scope=upload.global_scope,
            gate=permission_gate,
        )
        if scope.verification_state != "verified":
            return {"allowed": False, "code": "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
                    "verification_state": "unavailable"}
        if scope.allowed is not True:
            return {"allowed": False, "code": "CONTENT_SOURCE_SCOPE_DENIED",
                    "verification_state": "verified"}
        resource = content_source_import_resource(scope, upload, gate=permission_gate)
    except ValueError:
        return {"allowed": False, "code": "CONTENT_SOURCE_RESOURCE_BINDING_INVALID",
                "verification_state": "verified"}
    except Exception:
        logger.exception("Content source import confirmation preparation failed")
        return {"allowed": False, "code": "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
                "verification_state": "unavailable"}

    now = datetime.now()
    permission_gate._prune_content_source_import_state(now)
    with permission_gate._content_import_lock:
        if len(permission_gate._content_import_confirmations) >= _CONTENT_SOURCE_CONFIRMATION_CAPACITY:
            return {"allowed": False, "code": "CONTENT_SOURCE_CONFIRMATION_CAPACITY",
                    "verification_state": "verified"}
        confirmation_id = secrets.token_urlsafe(32)
        expires_at = now + _CONTENT_SOURCE_CONFIRMATION_TTL
        permission_gate._content_import_confirmations[confirmation_id] = (
            _ContentSourceImportConfirmation(
                confirmation_id=confirmation_id, actor_id=actor_id, caller=caller,
                upload=upload, resource=resource, expires_at=expires_at,
            )
        )
    return {
        "allowed": True, "code": "CONTENT_SOURCE_CONFIRMATION_PENDING",
        "verification_state": "verified", "confirmation_id": confirmation_id,
        "resource": resource, "expires_at": expires_at.isoformat(),
        "filename": upload.filename, "size_bytes": upload.size_bytes,
        "body_sha256": upload.body_sha256,
    }


def confirm_content_source_import(
    actor: Optional[Mapping[str, Any]], confirmation_id: str, *,
    domain_id: str, subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None, global_scope: bool = False,
    confirmed: bool, principal: Optional[LocalWorkspacePrincipal] = None,
    gate: Optional["PermissionGate"] = None,
) -> ActorScopePermissionResult:
    """Bind an explicit user confirmation to one exact live import resource."""
    permission_gate = gate if gate is not None else get_permission_gate()
    identity = _content_source_identity(actor, principal)
    actor_id, caller, principal_kind, principal_ref, identity_kind = identity
    if identity_kind is None or type(confirmation_id) is not str or not confirmation_id:
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_CONFIRMATION_INVALID", actor_id=actor_id,
            verification_state="unavailable", caller=caller,
            principal_kind=principal_kind, principal_ref=principal_ref,
        )
    if confirmed is not True:
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_CONFIRMATION_DECLINED", actor_id=actor_id,
        )
    if is_testing_bypass_enabled():
        return _content_source_confirmation_denial(
            permission_gate, "CONTENT_SOURCE_TESTING_BYPASS_FORBIDDEN", actor_id=actor_id,
        )

    permission_gate._prune_content_source_import_state()
    with permission_gate._content_import_lock:
        confirmation = permission_gate._content_import_confirmations.get(confirmation_id)
        if confirmation is None:
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_CONFIRMATION_UNKNOWN", actor_id=actor_id,
            )
        if confirmation.actor_id != actor_id or confirmation.caller != caller:
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_ACTOR_MISMATCH", actor_id=actor_id,
                upload=confirmation.upload, resource=confirmation.resource,
                caller=caller, principal_kind=principal_kind, principal_ref=principal_ref,
            )
        if confirmation.state != "pending":
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_CONFIRMATION_NOT_PENDING",
                actor_id=actor_id, upload=confirmation.upload,
                resource=confirmation.resource,
            )
        upload = confirmation.upload
        if not _content_source_upload_matches_identity(upload, identity):
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_PRINCIPAL_MISMATCH",
                actor_id=actor_id, upload=upload, resource=confirmation.resource,
                caller=caller, principal_kind=principal_kind, principal_ref=principal_ref,
            )
        if (
            domain_id != upload.domain_id or subject_id != upload.subject_id
            or brand_focus_id != upload.brand_focus_id
            or type(global_scope) is not bool or global_scope is not upload.global_scope
        ):
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_SCOPE_MISMATCH", actor_id=actor_id,
                upload=upload, resource=confirmation.resource,
            )
        try:
            scope = _content_source_scope_receipt(
                actor, principal=principal, domain_id=domain_id, subject_id=subject_id,
                brand_focus_id=brand_focus_id, global_scope=global_scope,
                gate=permission_gate,
            )
            if scope.verification_state != "verified":
                return _content_source_confirmation_denial(
                    permission_gate, "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
                    actor_id=actor_id, upload=upload, scope=scope,
                    resource=confirmation.resource, verification_state="unavailable",
                )
            if scope.allowed is not True:
                if identity_kind == "local_workspace":
                    confirmation.state = "cancelled"
                return _content_source_confirmation_denial(
                    permission_gate, "CONTENT_SOURCE_SCOPE_DENIED", actor_id=actor_id,
                    upload=upload, scope=scope, resource=confirmation.resource,
                )
            resource = content_source_import_resource(scope, upload, gate=permission_gate)
        except Exception:
            logger.exception("Content source import confirmation scope check failed")
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_PERMISSION_UNAVAILABLE",
                actor_id=actor_id, upload=upload, resource=confirmation.resource,
                verification_state="unavailable",
            )
        if resource != confirmation.resource:
            return _content_source_confirmation_denial(
                permission_gate, "CONTENT_SOURCE_RESOURCE_BINDING_INVALID",
                actor_id=actor_id, upload=upload, scope=scope, resource=resource,
            )

        token = permission_gate.grant_approval(
            OperationType.DB_WRITE.value, duration_minutes=1, resource=resource,
            granted_by=caller,
        )
        confirmation.state = "confirmed"
        confirmation.approval_token = token
        confirmation.approval_expires_at = datetime.now() + _CONTENT_SOURCE_IMPORT_GRANT_TTL
        permission_gate._content_import_grants[token] = _ContentSourceImportGrant(
            token=token, actor_id=actor_id, caller=scope.caller, resource=resource,
            expires_at=confirmation.approval_expires_at,
            confirmation_id=confirmation_id,
        )

    decision = check_content_source_import_permission(
        actor, upload, principal=principal, gate=permission_gate,
    )
    if decision.allowed is not True:
        permission_gate.revoke_approval(token)
        with permission_gate._content_import_lock:
            permission_gate._content_import_grants.pop(token, None)
            confirmation.state = "denied"
        return decision
    # Keep the approval token inside the Gate only; this result may be returned
    # by an API confirmation endpoint.
    return replace(decision, approval_token=None)


def cancel_content_source_import_confirmation(
    actor: Optional[Mapping[str, Any]], confirmation_id: str,
    current_scope: Mapping[str, Any], *,
    principal: Optional[LocalWorkspacePrincipal] = None,
    gate: Optional["PermissionGate"] = None,
) -> bool:
    """Cancel one owner's pending/issued confirmation without revoking others."""
    permission_gate = gate if gate is not None else get_permission_gate()
    identity = _content_source_identity(actor, principal)
    actor_id, caller, _principal_kind, _principal_ref, identity_kind = identity
    if identity_kind is None or not isinstance(current_scope, Mapping):
        return False
    domain_id = current_scope.get("domain_id")
    subject_id = current_scope.get("subject_id")
    brand_focus_id = current_scope.get("brand_focus_id")
    global_scope = current_scope.get("global_scope")
    if type(global_scope) is not bool:
        return False
    permission_gate._prune_content_source_import_state()
    with permission_gate._content_import_lock:
        confirmation = permission_gate._content_import_confirmations.get(confirmation_id)
        if (
            confirmation is None or confirmation.actor_id != actor_id
            or confirmation.caller != caller
            or confirmation.state not in {"pending", "confirmed"}
        ):
            return False
        upload = confirmation.upload
        if not _content_source_upload_matches_identity(upload, identity):
            return False
        if (domain_id != upload.domain_id or subject_id != upload.subject_id
                or brand_focus_id != upload.brand_focus_id
                or global_scope is not upload.global_scope):
            return False
        try:
            scope = _content_source_scope_receipt(
                actor, principal=principal, domain_id=domain_id, subject_id=subject_id,
                brand_focus_id=brand_focus_id, global_scope=global_scope,
                gate=permission_gate,
            )
            if scope.allowed is not True or scope.verification_state != "verified":
                if identity_kind == "local_workspace":
                    confirmation.state = "cancelled"
                    if confirmation.approval_token:
                        permission_gate._content_import_grants.pop(confirmation.approval_token, None)
                        permission_gate.revoke_approval(confirmation.approval_token)
                return False
            if content_source_import_resource(scope, upload, gate=permission_gate) != confirmation.resource:
                return False
        except Exception:
            logger.exception("Content source import confirmation cancellation check failed")
            return False
        confirmation.state = "cancelled"
        if confirmation.approval_token:
            permission_gate.revoke_approval(confirmation.approval_token)
            permission_gate._content_import_grants.pop(confirmation.approval_token, None)
        return True


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
    issuance_audit_id: Optional[str] = None

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

        # Content import confirmations stay inside the canonical Gate. Records
        # retain a frozen descriptor and metadata, never media bytes.
        self._content_import_lock = threading.RLock()
        self._content_import_confirmations: Dict[str, _ContentSourceImportConfirmation] = {}
        self._content_import_grants: Dict[str, _ContentSourceImportGrant] = {}

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

    def _prune_content_source_import_state(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now()
        with self._content_import_lock:
            for confirmation_id, confirmation in list(self._content_import_confirmations.items()):
                if now < confirmation.expires_at:
                    continue
                if confirmation.approval_token:
                    self._content_import_grants.pop(confirmation.approval_token, None)
                    self.revoke_approval(confirmation.approval_token)
                self._content_import_confirmations.pop(confirmation_id, None)
            for token, grant in list(self._content_import_grants.items()):
                if now >= grant.expires_at or not self._approval_token_is_valid(
                    token, OperationType.DB_WRITE.value, grant.resource,
                ):
                    # Removing the restriction must never leave a live token
                    # which an ordinary DB-write caller could borrow.
                    self.revoke_approval(token)
                    self._content_import_grants.pop(token, None)

    def _revoke_local_content_source_import(self, upload: ContentSourceImport) -> None:
        """Invalidate this workspace descriptor's pending and confirmed grants."""
        if (
            type(upload) is not ContentSourceImport
            or upload.actor_id is not None
            or upload.principal_kind != "local_workspace"
            or upload.principal_ref != "workspace:local"
        ):
            return
        with self._content_import_lock:
            for confirmation in self._content_import_confirmations.values():
                if (
                    confirmation.caller != "workspace:local"
                    or confirmation.upload != upload
                    or confirmation.state not in {"pending", "confirmed"}
                ):
                    continue
                confirmation.state = "cancelled"
                token = confirmation.approval_token
                if token:
                    self._content_import_grants.pop(token, None)
                    self.revoke_approval(token)

    def _content_import_grant_is_valid(
        self,
        token: Optional[str],
        operation_type: OperationType,
        resource: Optional[str],
        caller: Optional[str],
    ) -> bool:
        if type(token) is not str or operation_type is not OperationType.DB_WRITE:
            return False
        with self._content_import_lock:
            grant = self._content_import_grants.get(token)
            if (
                grant is None
                or datetime.now() >= grant.expires_at
                or grant.resource != resource
                or caller != grant.caller
            ):
                return False
            confirmation = self._content_import_confirmations.get(grant.confirmation_id)
            if (
                confirmation is None
                or confirmation.state != "confirmed"
                or confirmation.approval_token != token
                or confirmation.resource != resource
                or confirmation.actor_id != grant.actor_id
                or confirmation.caller != grant.caller
            ):
                return False
            upload = confirmation.upload
            if upload.principal_kind == "local_workspace" or upload.principal_ref is not None:
                principal = resolve_local_workspace_principal(
                    module="content", action="write",
                )
                scope = (
                    check_local_workspace_scope_permission(
                        principal, domain_id=upload.domain_id, action="write",
                        module="content", subject_id=upload.subject_id,
                        brand_focus_id=upload.brand_focus_id,
                        global_scope=upload.global_scope, gate=self,
                    ) if principal is not None else None
                )
                if (
                    upload.actor_id is not None
                    or upload.principal_kind != "local_workspace"
                    or upload.principal_ref != "workspace:local"
                    or principal is None
                    or scope is None or scope.allowed is not True
                    or scope.caller != grant.caller
                    or scope.resource != f"{upload.domain_id}:{'GLOBAL / ALL' if upload.global_scope else (upload.subject_id if upload.domain_id == 'cth' else upload.brand_focus_id)}"
                ):
                    confirmation.state = "cancelled"
                    self._content_import_grants.pop(token, None)
                    self.revoke_approval(token)
                    return False
            elif (
                type(upload.actor_id) is not int or upload.actor_id < 1
                or upload.principal_kind is not None or upload.principal_ref is not None
                or grant.caller != f"actor:{upload.actor_id}"
            ):
                return False
            return self._approval_token_is_valid(
                token, OperationType.DB_WRITE.value, resource,
            )

    def _find_content_import_grant(self, resource: str, caller: str) -> Optional[str]:
        with self._content_import_lock:
            for token in list(self._content_import_grants):
                if self._content_import_grant_is_valid(
                    token, OperationType.DB_WRITE, resource, caller,
                ):
                    return token
        return None

    def _approval_token_is_valid(
        self, token: Optional[str], operation: str, resource: Optional[str],
    ) -> bool:
        if type(token) is not str:
            return False
        with self._approval_lock:
            approval = self._approvals.get(token)
            return bool(
                approval
                and approval.operation == operation
                and approval.resource == resource
                and approval.is_valid(operation, resource)
            )

    def _standard_approval_token(
        self, operation: str, resource: Optional[str], *, exact: bool,
    ) -> Optional[str]:
        with self._content_import_lock:
            restricted_tokens = set(self._content_import_grants)
        with self._approval_lock:
            for token, approval in self._approvals.items():
                if token in restricted_tokens:
                    continue
                if exact and (approval.operation != operation or approval.resource != resource):
                    continue
                if approval.is_valid(operation, resource):
                    return token
        return None

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

    def check_prelaunch_maintenance(self, authorization, *, source_url: str,
                                   platform: str, scope: Dict[str, Any],
                                   business_query=None, max_results=None) -> PermissionResult:
        """Evaluate a revocable signed service grant for one public source.

        The durable plan records the owner's explicit prelaunch authorization.
        Reloading it on every effect keeps revocation and restart behavior real;
        this does not grant COMMIT, issue human approvals, or authorize user AUTO.
        """
        allowed = False
        reason = "PRELAUNCH_SERVICE_AUTHORIZATION_REQUIRED"
        resource = "prelaunch:invalid"
        domain = scope.get("domain_id") if isinstance(scope, dict) else None
        try:
            from lumenis.system.collector.adapters.secondary_collection import (
                _prelaunch_public_import_resource,
            )
            from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
                PURPOSE_POLICY, PrelaunchMaintenanceAuthorization,
                load_prelaunch_baseline_config, _purpose_query,
            )
            if _TESTING_BYPASS_ENABLED or os.environ.get("PERMISSION_GATE_TESTING") == "1":
                raise ValueError("testing bypass cannot authorize maintenance")
            if isinstance(authorization, PrelaunchMaintenanceAuthorization):
                loaded = load_prelaunch_baseline_config(
                    os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG") or None,
                )
                for plan in loaded.get("plans", []):
                    if authorization.matches(plan, source_url=source_url,
                                             platform=platform, scope=scope):
                        if max_results is not None and (
                                type(max_results) is not int or not 1 <= max_results <= plan.max_results):
                            break
                        if plan.policy_id == PURPOSE_POLICY:
                            from lumenis.system.collector.acquisition_plan import AcquisitionQuery
                            if (type(business_query) is not AcquisitionQuery
                                    or max_results is None
                                    or json.dumps(business_query.to_dict(), sort_keys=True) !=
                                    json.dumps(_purpose_query(plan.purpose_query).to_dict(), sort_keys=True)):
                                break
                            resource = "prelaunch-purpose:" + plan.plan_id
                        else:
                            if business_query is not None:
                                break
                            resource = _prelaunch_public_import_resource(scope, source_url, platform=platform)
                        allowed = True
                        reason = "SIGNED_PRELAUNCH_SERVICE_GRANT"
                        break
        except Exception:
            # Config errors must not leak key values or become implicit grants.
            allowed = False
        caller = "prelaunch_baseline_maintenance"
        audit_id = self._write_audit(
            operation_type=OperationType.DATA_IMPORT.value, resource=resource,
            risk_level=RiskLevel.HIGH.value, permission_required="signed_prelaunch_service_grant",
            caller=caller, result="allowed" if allowed else "denied", reason=reason,
            operation_id=None, approval_token=None,
        )
        return PermissionResult(
            allowed=allowed, reason=reason, requires_approval=not allowed,
            audit_id=audit_id, operation_type=OperationType.DATA_IMPORT.value,
            resource=resource, risk_level=RiskLevel.HIGH.value,
            permission_required="signed_prelaunch_service_grant", caller=caller,
            domain_id=domain,
        )

    def check_prelaunch_post_intake(
        self, authorization, *, action: str, source_evidence_ref: str,
        source_fingerprint: str, source_version: str, body_sha256: str,
        processing_version: str, scope: Dict[str, Any], connection,
    ) -> PermissionResult:
        """Authorize one current internal use, independently from DATA_IMPORT.

        The maintenance principal is the server-held, revocable signed plan;
        it is not a user account or Reporting/third-party rights grant. Each
        action reloads that plan and verifies the immutable physical Source and
        live Registry/Canonical binding. No cached allow result authorizes a
        subsequent read, analysis or derivative write.
        """
        operations = {
            "READ": OperationType.COLLECTOR_SOURCE_READ,
            "ANALYZE": OperationType.COLLECTOR_SOURCE_ANALYZE,
            "DERIVED_SAVE": OperationType.DB_WRITE,
        }
        operation = operations.get(action if type(action) is str else None,
                                   OperationType.COLLECTOR_SOURCE_ANALYZE)
        risk = RiskLevel.HIGH if action == "DERIVED_SAVE" else RiskLevel.LOW
        allowed = False
        reason = "POST_INTAKE_CURRENT_USE_DENIED"
        resource = "collector-post-intake:invalid"
        domain = scope.get("domain_id") if isinstance(scope, dict) else None
        try:
            from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
                PURPOSE_POLICY, POST_INTAKE_KEYWORD_POLICY,
                PrelaunchMaintenanceAuthorization, load_prelaunch_baseline_config,
            )
            from lumenis.system.collector.adapters.platform_naming import normalize_platform
            from lumenis.importer.documents import _source_bytes
            from lumenis.shared.evidence import store

            if (is_testing_bypass_enabled() or self is not get_permission_gate()
                    or not self.fail_closed or type(action) is not str or action not in operations
                    or type(authorization) is not PrelaunchMaintenanceAuthorization
                    or authorization.policy_id != PURPOSE_POLICY
                    or processing_version != POST_INTAKE_KEYWORD_POLICY["processing_version"]
                    or type(scope) is not dict or set(scope) != {
                        "domain_id", "subject_id", "brand_focus_id"}
                    or not re.fullmatch(r"app_evidence_records:[1-9][0-9]*", source_evidence_ref)
                    or not re.fullmatch(r"[0-9a-f]{64}", source_fingerprint)
                    or not re.fullmatch(r"[0-9a-f]{64}", body_sha256)
                    or source_version not in {"collected-native-source:live-v1",
                                              "collected-native-source:pending-v1"}):
                raise ValueError("POST_INTAKE_REQUEST_INVALID")
            loaded = load_prelaunch_baseline_config(
                os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG") or None)
            plans = [plan for plan in loaded.get("plans", []) if authorization.matches(
                plan, source_url=authorization.source_url,
                platform=authorization.platform, scope=scope)]
            if len(plans) != 1 or not plans[0].post_intake_policy:
                raise ValueError("POST_INTAKE_POLICY_REVOKED_OR_MISSING")
            plan = plans[0]
            policy = plan.post_intake_policy
            if action not in policy["actions"]:
                raise ValueError("POST_INTAKE_ACTION_NOT_GRANTED")
            con = _require_canonical_scope_connection(connection)
            if not _registered_resource_scope_exists(
                    scope["domain_id"], subject_id=scope["subject_id"],
                    brand_focus_id=scope["brand_focus_id"],
                    connection=con):
                raise ValueError("POST_INTAKE_REGISTRY_SCOPE_UNAVAILABLE")
            row = con.execute("SELECT * FROM app_evidence_records WHERE id=?",
                              (int(source_evidence_ref.split(":")[1]),)).fetchone()
            if row is None:
                raise ValueError("POST_INTAKE_SOURCE_UNAVAILABLE")
            evidence = dict(row)
            metadata = json.loads(evidence.get("collection_metadata") or "{}")
            context = metadata.get("context") or {}
            native_binding = metadata.get("native_source_binding") or {}
            source_rights = (metadata.get("provenance") or {}).get("rights") or {}
            integrity = store.classify_evidence_integrity(evidence)
            if (evidence.get("feature_id") != "COLLECTED_SOURCE"
                    or evidence.get("status") != "verified" or evidence.get("result") != "PASS"
                    or integrity.get("verified") is not True
                    or integrity.get("assurance") != "writer-authenticated"
                    or evidence.get("version") != source_version
                    or metadata.get("source_fingerprint") != source_fingerprint
                    or native_binding.get("body_sha256") != body_sha256
                    or context.get("collector_plan_id") != plan.plan_id
                    or context.get("collector_authorization_ref") != plan.authorization_ref
                    or context.get("global_scope") is not False
                    or context.get("domain_id") != ("zbmp" if scope["domain_id"] == "bmp" else "cth")
                    or (context.get("subject_id") or None) != scope["subject_id"]
                    or (context.get("brand_focus_id") or None) != scope["brand_focus_id"]
                    or normalize_platform(native_binding.get("platform")) != normalize_platform(plan.platform)
                    or source_rights.get("status") not in {
                        "UNREVIEWED", "owner-approved", "public-reference-only"}):
                raise ValueError("POST_INTAKE_SOURCE_BINDING_INVALID")
            # There is no general Source privacy enum yet. Explicit restrictions
            # on the actual Source stop this narrow use; absent fields never
            # become a claim of privacy review or broader third-party permission.
            for material in (metadata, metadata.get("provenance") or {}, source_rights):
                if (any(material.get(name) is True for name in (
                        "revoked", "private", "restricted", "confidential", "use_prohibited"))
                        or material.get("privacy_status") in {"PRIVATE", "RESTRICTED", "CONFIDENTIAL"}
                        or material.get("use_status") in {"DENIED", "REVOKED", "WITHDRAWN"}):
                    raise ValueError("POST_INTAKE_SOURCE_RESTRICTED")
            raw, artifact = _source_bytes(con, {**evidence, "provenance": metadata})
            original = json.loads(raw)
            body = original.get("body")
            if (hashlib.sha256(raw).hexdigest() != source_fingerprint
                    or not isinstance(body, str) or not body.strip()
                    or hashlib.sha256(body.encode("utf-8")).hexdigest() != body_sha256
                    or original.get("rights") != (metadata.get("provenance") or {}).get("rights")):
                raise ValueError("POST_INTAKE_PHYSICAL_SOURCE_INVALID")
            original_rights = original.get("rights") or {}
            if (any(original_rights.get(name) is True for name in (
                    "revoked", "private", "restricted", "confidential", "use_prohibited"))
                    or original_rights.get("privacy_status") in {"PRIVATE", "RESTRICTED", "CONFIDENTIAL"}
                    or original_rights.get("use_status") in {"DENIED", "REVOKED", "WITHDRAWN"}):
                raise ValueError("POST_INTAKE_SOURCE_RESTRICTED")
            pending = source_version == "collected-native-source:pending-v1"
            assignment = metadata.get("entity_assignment")
            canonical_ref = None
            if pending:
                # The exact signed acquisition context grants this internal
                # Source use; it does not assign the observed post to that
                # entity. The Source reader verifies its separate pending
                # parent/observation contract before any analysis or write.
                if (not isinstance(assignment, dict)
                        or assignment != original.get("entity_assignment")
                        or assignment.get("state") != "PENDING"
                        or assignment.get("context_role") != "ACQUISITION_PERMISSION_CONTEXT_ONLY"
                        or any(assignment.get(key) is not None for key in
                               ("subject_id", "brand_focus_id", "canonical_ref"))):
                    raise ValueError("POST_INTAKE_SOURCE_BINDING_INVALID")
            else:
                from dataclasses import fields
                from canonical_data import CanonicalRecord, _validate_canonical_scope
                canonical = con.execute(
                    "SELECT * FROM canonical_data WHERE source_table='notes' AND source_type='note' "
                    "AND source_id=? AND domain_id=? AND NULLIF(subject_id,'') IS ? "
                    "AND NULLIF(brand_focus_id,'') IS ? AND product_id=? AND scope_status='VERIFIED'",
                    (str(evidence["asset_id"]), context["domain_id"], scope["subject_id"],
                     scope["brand_focus_id"], "CTH" if context["domain_id"] == "cth" else "ZBMP")).fetchall()
                if len(canonical) != 1 or canonical[0]["content"] != body:
                    raise ValueError("POST_INTAKE_CANONICAL_SOURCE_UNAVAILABLE")
                canonical_row = dict(canonical[0])
                record = CanonicalRecord(**{field.name: canonical_row[field.name]
                                            for field in fields(CanonicalRecord)
                                            if field.name in canonical_row})
                try:
                    if _validate_canonical_scope(con, record) is None:
                        raise ValueError("canonical source is not verified")
                except (TypeError, ValueError, RuntimeError) as exc:
                    raise ValueError("POST_INTAKE_CANONICAL_SOURCE_UNAVAILABLE") from exc
                canonical_ref = canonical[0]["canonical_id"]
            use = {
                "action": action, "plan_id": plan.plan_id, "scope": scope,
                "source_evidence_ref": source_evidence_ref, "source_version": source_version,
                "source_fingerprint": source_fingerprint, "body_sha256": body_sha256,
                "source_artifact_ref": artifact["artifact_id"],
                "canonical_ref": canonical_ref, "policy": policy,
                "principal": "prelaunch_baseline_maintenance",
            }
            if pending:
                use["entity_assignment"] = assignment
            digest = hashlib.sha256(json.dumps(
                use, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            resource = "collector-post-intake:" + action + ":" + digest
            allowed = True
            reason = "SIGNED_INTERNAL_POST_INTAKE_USE:SOURCE_RIGHTS_UNCHANGED"
        except Exception as exc:
            if isinstance(exc, ValueError) and re.fullmatch(r"POST_INTAKE_[A-Z_]+", str(exc)):
                reason = str(exc)
        caller = "prelaunch_baseline_maintenance"
        audit_id = self._write_audit(
            operation_type=operation.value, resource=resource, risk_level=risk.value,
            permission_required="signed_internal_post_intake_" + str(action), caller=caller,
            result="allowed" if allowed else "denied", reason=reason,
            operation_id=None, approval_token=None)
        return PermissionResult(
            allowed=allowed, reason=reason, requires_approval=not allowed,
            audit_id=audit_id, operation_type=operation.value, resource=resource,
            risk_level=risk.value, permission_required="signed_internal_post_intake_" + str(action),
            caller=caller, domain_id=domain)

    def check(
        self,
        operation_type: OperationType,
        resource: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        caller: Optional[str] = None,
        operation_id: Optional[str] = None,
        domain_id: Optional[str] = None,
        role: Optional[str] = None,
        exact_approval_required: bool = False,
        content_import_grant: Optional[str] = None,
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
            exact_approval_required: 仅接受操作和资源均完全匹配的审批令牌；
                默认 False 以保留现有调用方兼容性
            content_import_grant: Gate 内确认产生的精确 Content Import capability。

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

        # 0. 域身份解析。未知域不得继承上一次检查或静默落入 CTH。
        self._current_check_domain = None
        try:
            from domain_isolation import resolve_domain_identity
            if domain_id is None:
                from ai_domain_context import get_current_domain
                domain_id = get_current_domain()
            else:
                domain_id, _ = resolve_domain_identity(domain_id=domain_id)
            if not domain_id:
                raise ValueError("DOMAIN_NOT_SELECTED")
        except (ImportError, TypeError, ValueError) as exc:
            return self._deny(
                operation_type, resource, risk_level or RiskLevel.HIGH,
                PermissionLevel.VERIFY, caller or self.default_caller, operation_id,
                reason=f"domain_context_unavailable:{exc}",
            )

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
        restricted_import_grant = self._content_import_grant_is_valid(
            content_import_grant, operation_type, resource,
            caller or self.default_caller,
        )

        # 4. 权限等级检查
        if not self.has_permission(spec.permission) and not restricted_import_grant:
            result = self._deny(
                operation_type, resource, final_risk, spec.permission,
                caller or self.default_caller, operation_id,
                reason=f"权限等级不足: 需要 {spec.permission.value}，"
                       f"当前启用 {[p.value for p in self._enabled_permissions]}",
            )
            return result

        # 5. 高风险操作需人工审批
        if self.require_human_approval(final_risk):
            token = (
                content_import_grant if restricted_import_grant else
                self._standard_approval_token(
                    operation_type.value, resource, exact=exact_approval_required,
                ) if operation_type is OperationType.DB_WRITE else
                self._get_approval_token(
                    operation_type.value, resource, exact=exact_approval_required,
                )
            )
            if token:
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
        issuance_audit_id = self._write_audit(
            operation_type=operation, resource=resource,
            risk_level=RiskLevel.HIGH.value, permission_required="human_approval",
            caller=granted_by, result="approval_granted",
            reason=f"人工审批授予: {operation} (有效期 {duration_minutes} 分钟)",
            operation_id=None, approval_token=token,
        )
        with self._approval_lock:
            approval.issuance_audit_id = issuance_audit_id
        return token

    @contextmanager
    def skill_metadata_commit_lease(
        self, candidate: Any, *, connection: Any, decision: Any,
        actor_id: Optional[int] = None, principal: Optional[LocalWorkspacePrincipal] = None,
        domain_id: str, subject_id: Optional[str] = None,
        brand_focus_id: Optional[str] = None, global_scope: bool = False,
        timeout_seconds: float = 2.0,
    ):
        """Serialize one metadata SQL commit with same-process approval revocation.

        The caller obtains BEGIN IMMEDIATE, completes its fresh Fence check,
        then holds this lease only for connection.commit(). No Gate.check or
        other approval-lock-taking method may run inside the lease.
        """
        from .effect_fence import EffectFence, SkillMetadataFenceDecision

        if (type(self) is not PermissionGate or self is not get_permission_gate()
                or not self.fail_closed or is_testing_bypass_enabled()
                or not EffectFence._skill_metadata_connection_is_canonical(connection)):
            raise PermissionError("SKILL_METADATA_COMMIT_LEASE_UNAVAILABLE")
        if type(timeout_seconds) not in {int, float} or not 0 < timeout_seconds <= 2.0:
            raise ValueError("SKILL_METADATA_COMMIT_LEASE_TIMEOUT_INVALID")
        payload = _skill_metadata_payload(
            candidate, actor_id=actor_id, principal=principal, domain_id=domain_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id, global_scope=global_scope,
        )
        resource = skill_metadata_approval_resource(
            candidate, actor_id=actor_id, principal=principal, **payload["scope"],
        )
        expected = {**payload["identity"], **payload["scope"], "resource": resource,
                    "operation_id": candidate.operation_id, "candidate_sha256": candidate.candidate_sha256}
        if (type(decision) is not SkillMetadataFenceDecision or decision.allowed is not True
                or decision.state != "commit_verified" or decision.idempotent_hit is not False
                or any(getattr(decision, name) != value for name, value in expected.items())
                or any(not re.fullmatch(r"aud_[0-9a-f]{16}", str(getattr(decision, name)))
                       for name in ("permission_audit_id", "scope_audit_id", "fence_audit_id"))
                or not re.fullmatch(r"[0-9a-f]{64}", str(decision.approval_token_sha256))):
            raise PermissionError("SKILL_METADATA_COMMIT_LEASE_BINDING_INVALID")
        if not self._approval_lock.acquire(timeout=float(timeout_seconds)):
            raise PermissionError("SKILL_METADATA_COMMIT_LEASE_TIMEOUT")
        try:
            # Recheck transport/session after a possible lock wait. The active
            # writer transaction prevents concurrent canonical account changes.
            if _skill_metadata_identity(actor_id=actor_id, principal=principal) != payload["identity"]:
                raise PermissionError("SKILL_METADATA_COMMIT_LEASE_IDENTITY_CHANGED")
            spec = self.get_operation_spec(OperationType.CONFIG_MODIFY)
            if (is_testing_bypass_enabled() or not self.fail_closed or not self.has_permission(PermissionLevel.COMMIT)
                    or type(spec) is not OperationSpec or spec.permission is not PermissionLevel.COMMIT
                    or spec.risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL} or spec.auto_allow is not False):
                raise PermissionError("SKILL_METADATA_COMMIT_LEASE_APPROVAL_REQUIRED")
            valid = any(
                approval.operation == OperationType.CONFIG_MODIFY.value and approval.resource == resource
                and approval.is_valid(OperationType.CONFIG_MODIFY.value, resource)
                and secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(), decision.approval_token_sha256)
                for token, approval in self._approvals.items()
            )
            if not valid:
                raise PermissionError("SKILL_METADATA_COMMIT_LEASE_APPROVAL_REQUIRED")
            yield
        finally:
            self._approval_lock.release()

    @contextmanager
    def owned_evaluation_capture_commit_lease(
        self, *, material: Mapping[str, Any], resource: str,
        authorization: Mapping[str, Any], connection: Any,
        timeout_seconds: float = 1.0,
    ):
        """Serialize the exact evaluation Evidence commit with grant revocation.

        The caller holds the canonical writer transaction and has completed
        scope/approval checks. Hold this lease only around connection.commit;
        never invoke Gate.check while the non-reentrant approval lock is held.
        """
        from .effect_fence import EffectFence
        from lumenis.system.ai_gateway.owned_evaluation import (
            _capture_identity, _evaluation_capture_resource,
        )

        if (type(self) is not PermissionGate or self is not get_permission_gate()
                or not self.fail_closed or is_testing_bypass_enabled()
                or not EffectFence._skill_metadata_connection_is_canonical(connection)):
            raise PermissionError("OWNED_EVALUATION_COMMIT_LEASE_UNAVAILABLE")
        if type(timeout_seconds) not in {int, float} or not 0 < timeout_seconds <= 2:
            raise ValueError("OWNED_EVALUATION_COMMIT_LEASE_TIMEOUT_INVALID")
        if (resource != _evaluation_capture_resource(material)
                or type(authorization) is not dict
                or set(authorization) != {"scope_audit_id", "permission_audit_id", "approval_token"}
                or any(not isinstance(authorization.get(key), str) or not authorization[key]
                       for key in authorization)
                or any(re.fullmatch(r"aud_[0-9a-f]{16}", authorization[key]) is None
                       for key in ("scope_audit_id", "permission_audit_id"))):
            raise PermissionError("OWNED_EVALUATION_COMMIT_LEASE_BINDING_INVALID")
        token = authorization["approval_token"]
        if not self._approval_lock.acquire(timeout=float(timeout_seconds)):
            raise PermissionError("OWNED_EVALUATION_COMMIT_LEASE_TIMEOUT")
        try:
            identity = material["identity"]
            current_identity = _capture_identity(
                {"id": identity["actor_id"]} if identity["identity_kind"] == "account" else None,
                material["principal"],
            )
            if current_identity != identity:
                raise PermissionError("OWNED_EVALUATION_IDENTITY_CHANGED")
            spec = self.get_operation_spec(OperationType.DB_WRITE)
            if (not self.fail_closed or is_testing_bypass_enabled()
                    or not self.has_permission(PermissionLevel.COMMIT)
                    or type(spec) is not OperationSpec
                    or spec.permission is not PermissionLevel.COMMIT
                    or spec.risk is not RiskLevel.HIGH or spec.auto_allow is not False):
                raise PermissionError("OWNED_EVALUATION_DB_WRITE_POLICY_CHANGED")
            grant = self._approvals.get(token)
            if (type(grant) is not ApprovalToken
                    or grant.operation != OperationType.DB_WRITE.value
                    or grant.resource != resource
                    or type(grant.token) is not str
                    or not secrets.compare_digest(grant.token, token)
                    or not grant.is_valid(OperationType.DB_WRITE.value, resource)):
                raise PermissionError("OWNED_EVALUATION_EXACT_DB_WRITE_APPROVAL_REQUIRED")
            yield
        finally:
            self._approval_lock.release()

    def owned_training_approval_reference(
        self, *, training_request: Any, actor_id: Optional[int] = None,
        principal: Optional[LocalWorkspacePrincipal] = None, domain_id: str,
        context: Mapping[str, Any], approval: PermissionResult,
    ) -> Dict[str, Any]:
        """Identify one live exact grant without exporting its private token.

        A check audit is distinct from the original human grant's issuance
        audit. Durable task state records this reference for one execution;
        it cannot restore an expired, revoked or lost in-memory grant.
        """
        if (type(self) is not PermissionGate or self is not get_permission_gate()
                or not self.fail_closed or is_testing_bypass_enabled()
                or not self.has_permission(PermissionLevel.COMMIT)):
            raise PermissionError("OWNED_TRAINING_PHASE_PERMISSION_UNAVAILABLE")
        payload = _owned_training_payload(
            training_request, actor_id=actor_id, principal=principal,
            domain_id=domain_id, context=context,
        )
        identity = owned_training_identity(actor_id=actor_id, principal=principal)
        resource = owned_training_approval_resource(
            training_request, actor_id=actor_id, principal=principal,
            domain_id=domain_id, context=context,
        )
        if (type(approval) is not PermissionResult or approval.allowed is not True
                or approval.requires_approval is not True
                or approval.operation_type != OperationType.MODEL_TRAIN.value
                or approval.resource != resource or approval.caller != identity["caller"]
                or _canonical_business_domain_id(approval.domain_id)
                != _canonical_business_domain_id(payload["domain_id"])
                or type(approval.audit_id) is not str
                or re.fullmatch(r"aud_[0-9a-f]{16}", approval.audit_id) is None
                or type(approval.approval_token) is not str or not approval.approval_token):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        spec = self.get_operation_spec(OperationType.MODEL_TRAIN)
        if (type(spec) is not OperationSpec or spec.permission is not PermissionLevel.COMMIT
                or spec.risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL} or spec.auto_allow is not False):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        with self._approval_lock:
            return self._owned_training_approval_reference_locked(
                approval=approval, resource=resource,
            )

    def owned_training_history_approval_reference(
        self, binding: Mapping[str, Any], *, actor_id: Optional[int] = None,
        principal: Optional[LocalWorkspacePrincipal] = None,
    ) -> Dict[str, Any]:
        """Recheck a sealed task's exact live grant for read-only history.

        The Task owner supplies its validated private binding after the server
        identity check. This cannot issue a grant, admit a phase or restore a
        lost grant from its persisted digest. No private reference is public API.
        """
        from ai_task_engine import _validate_training_receipt_binding

        if (type(self) is not PermissionGate or self is not get_permission_gate()
                or not self.fail_closed or is_testing_bypass_enabled()
                or not self.has_permission(PermissionLevel.COMMIT)):
            raise PermissionError("OWNED_TRAINING_PHASE_PERMISSION_UNAVAILABLE")
        value = _validate_training_receipt_binding(binding)
        identity = owned_training_identity(actor_id=actor_id, principal=principal)
        names = ("actor_id", "caller", "principal_kind", "principal_ref")
        if value["identity"] != {name: identity[name] for name in names}:
            raise PermissionError("OWNED_TRAINING_PHASE_IDENTITY_CHANGED")
        if actor_id is not None:
            from flask import has_request_context
            from lumenis.auth.service import get_current_user

            if not has_request_context():
                raise PermissionError("OWNED_TRAINING_PHASE_AUTH_REQUIRED")
            current = get_current_user(read_only=True)
            if type(current) is not dict or type(current.get("id")) is not int or current["id"] != actor_id:
                raise PermissionError("OWNED_TRAINING_PHASE_IDENTITY_CHANGED")
        domains = {d["domain_id"] for d in value["scope_descriptors"].values()}
        if len(domains) != 1:
            raise PermissionError("OWNED_TRAINING_PHASE_BINDING_MISMATCH")
        domain = next(iter(domains))
        canonical_domain = _canonical_business_domain_id(domain)
        if not canonical_domain:
            raise PermissionError("OWNED_TRAINING_PHASE_BINDING_MISMATCH")
        for descriptor in value["scope_descriptors"].values():
            scope_args = {"domain_id": domain, "action": "write", "module": "owned_training",
                          "subject_id": descriptor["subject_id"], "brand_focus_id": descriptor["brand_focus_id"],
                          "global_scope": descriptor["global_scope"], "gate": self}
            scoped = (check_local_workspace_scope_permission(principal, **scope_args)
                      if identity["identity_kind"] == "workspace"
                      else check_actor_scope_permission({"id": actor_id}, **scope_args))
            expected_focus = descriptor["subject_id"] if domain == "cth" else descriptor["brand_focus_id"]
            expected_resource = f"{domain}:{'GLOBAL / ALL' if descriptor['global_scope'] else expected_focus}"
            if (type(scoped) is not ActorScopePermissionResult or scoped.allowed is not True
                    or scoped.verification_state != "verified"
                    or scoped.actor_id != identity["actor_id"] or scoped.caller != identity["caller"]
                    or scoped.principal_kind != identity["principal_kind"] or scoped.principal_ref != identity["principal_ref"]
                    or _canonical_business_domain_id(scoped.domain_id) != canonical_domain
                    or scoped.subject_id != descriptor["subject_id"]
                    or scoped.brand_focus_id != descriptor["brand_focus_id"]
                    or scoped.global_scope is not descriptor["global_scope"] or scoped.resource != expected_resource
                    or type(scoped.audit_id) is not str or re.fullmatch(r"aud_[0-9a-f]{16}", scoped.audit_id) is None):
                raise PermissionError("OWNED_TRAINING_PHASE_SCOPE_DENIED")
        spec = self.get_operation_spec(OperationType.MODEL_TRAIN)
        if (type(spec) is not OperationSpec or spec.permission is not PermissionLevel.COMMIT
                or spec.risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL} or spec.auto_allow is not False):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        approval = self.check(OperationType.MODEL_TRAIN, resource=value["resource"],
                              caller=identity["caller"], domain_id=domain, exact_approval_required=True)
        if (type(approval) is not PermissionResult or approval.allowed is not True
                or approval.requires_approval is not True or approval.resource != value["resource"]
                or approval.operation_type != OperationType.MODEL_TRAIN.value
                or approval.caller != identity["caller"]
                or _canonical_business_domain_id(approval.domain_id) != canonical_domain
                or not approval.approval_token or type(approval.audit_id) is not str
                or re.fullmatch(r"aud_[0-9a-f]{16}", approval.audit_id) is None):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        with self._approval_lock:
            return self._owned_training_approval_reference_locked(approval=approval, resource=value["resource"])

    def _owned_training_approval_reference_locked(
        self, *, approval: PermissionResult, resource: str,
    ) -> Dict[str, Any]:
        """Read a validated live grant while the caller holds the approval lock.

        Both public entry points validate identity, policy and exact resource
        before calling this helper. It must not acquire the non-reentrant lock
        again while the phase commit lease serializes revocation.
        """
        grant = self._approvals.get(approval.approval_token)
        if (type(grant) is not ApprovalToken
                or grant.operation != OperationType.MODEL_TRAIN.value
                or grant.resource != resource
                or type(grant.token) is not str
                or not secrets.compare_digest(grant.token, approval.approval_token)
                or not grant.is_valid(OperationType.MODEL_TRAIN.value, resource)
                or type(grant.issuance_audit_id) is not str
                or re.fullmatch(r"aud_[0-9a-f]{16}", grant.issuance_audit_id) is None
                or type(grant.granted_by) is not str or not grant.granted_by.strip()):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REFERENCE_UNAVAILABLE")
        return {
            "schema_version": 1,
            "operation": grant.operation,
            "resource": grant.resource,
            "approval_token_sha256": hashlib.sha256(grant.token.encode("utf-8")).hexdigest(),
            "issuance_audit_id": grant.issuance_audit_id,
            "granted_by": grant.granted_by,
            "granted_at": grant.granted_at.isoformat(),
            "expires_at": grant.expires_at.isoformat(),
        }

    @contextmanager
    def owned_training_phase_commit_lease(
        self, *, training_request: Any, actor_id: Optional[int] = None,
        principal: Optional[LocalWorkspacePrincipal] = None, domain_id: str,
        context: Mapping[str, Any], approval: PermissionResult, connection: Any,
        timeout_seconds: float = 1.0,
        expected_approval_reference: Optional[Mapping[str, Any]] = None,
    ):
        """Commit one phase task/receipt while serializing exact approval revocation.

        The caller holds a canonical BEGIN IMMEDIATE transaction and has just
        rechecked every scope and MODEL_TRAIN approval. Hold this lease only for
        connection.commit(), never for signing, Gate.check or model execution.
        """
        from ai_task_engine import TaskEngine

        TaskEngine._require_training_receipt_connection(connection)
        if (type(self) is not PermissionGate or self is not get_permission_gate()
                or not self.fail_closed or is_testing_bypass_enabled()):
            raise PermissionError("OWNED_TRAINING_PHASE_PERMISSION_UNAVAILABLE")
        if type(timeout_seconds) not in {int, float} or not 0 < timeout_seconds <= 2:
            raise ValueError("OWNED_TRAINING_PHASE_LEASE_TIMEOUT_INVALID")
        payload = _owned_training_payload(
            training_request, actor_id=actor_id, principal=principal,
            domain_id=domain_id, context=context,
        )
        identity = owned_training_identity(actor_id=actor_id, principal=principal)
        resource = owned_training_approval_resource(
            training_request, actor_id=actor_id, principal=principal,
            domain_id=domain_id, context=context,
        )
        if (type(approval) is not PermissionResult or approval.allowed is not True
                or approval.requires_approval is not True
                or approval.operation_type != OperationType.MODEL_TRAIN.value
                or approval.resource != resource or approval.caller != identity["caller"]
                or _canonical_business_domain_id(approval.domain_id)
                != _canonical_business_domain_id(payload["domain_id"])
                or not approval.audit_id or not approval.approval_token):
            raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
        token_hash = hashlib.sha256(approval.approval_token.encode("utf-8")).hexdigest()
        if not self._approval_lock.acquire(timeout=float(timeout_seconds)):
            raise PermissionError("OWNED_TRAINING_PHASE_LEASE_TIMEOUT")
        try:
            current = owned_training_identity(actor_id=actor_id, principal=principal)
            if current != identity:
                raise PermissionError("OWNED_TRAINING_PHASE_IDENTITY_CHANGED")
            if actor_id is not None:
                from flask import has_request_context
                from lumenis.auth.service import get_current_user

                if not has_request_context():
                    raise PermissionError("OWNED_TRAINING_PHASE_AUTH_REQUIRED")
                actor = get_current_user(read_only=True)
                if type(actor) is not dict or type(actor.get("id")) is not int or actor["id"] != actor_id:
                    raise PermissionError("OWNED_TRAINING_PHASE_IDENTITY_CHANGED")
            spec = self.get_operation_spec(OperationType.MODEL_TRAIN)
            if (not self.fail_closed or is_testing_bypass_enabled()
                    or not self.has_permission(PermissionLevel.COMMIT)
                    or type(spec) is not OperationSpec or spec.permission is not PermissionLevel.COMMIT
                    or spec.risk not in {RiskLevel.HIGH, RiskLevel.CRITICAL} or spec.auto_allow is not False):
                raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
            valid = any(
                item.operation == OperationType.MODEL_TRAIN.value and item.resource == resource
                and item.is_valid(OperationType.MODEL_TRAIN.value, resource)
                and secrets.compare_digest(hashlib.sha256(token.encode("utf-8")).hexdigest(), token_hash)
                for token, item in self._approvals.items()
            )
            if not valid:
                raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED")
            if expected_approval_reference is not None:
                current_reference = self._owned_training_approval_reference_locked(
                    approval=approval, resource=resource,
                )
                if current_reference != expected_approval_reference:
                    raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REPLACED")
            yield
        finally:
            self._approval_lock.release()

    def require_current_training_checkpoint_admission(
        self, admission, *, operation, training_request, context, domain_id,
        engine, task_id, worker, connection, approval, approval_reference,
        pinned_public_key, actor_id=None, principal=None,
    ):
        """Check the exact live start admission on its canonical transaction.

        The bound client must CAS to WRITING/LOADING, pass the checkpoint
        metadata Fence and commit under owned_training_phase_commit_lease
        before physical IO. This returned current operation is no reusable
        permission token. v1.3 renewal and start serialize on that transaction.
        """
        from ai_task_engine import TaskEngine, get_task_engine
        from lumenis.system.ai_gateway.owned_training_runtime import TrainingProcessFence
        from .training_receipts import VerifiedTrainingCheckpointAdmission

        if (type(self) is not PermissionGate or self is not get_permission_gate()
                or not self.fail_closed or is_testing_bypass_enabled()
                or type(engine) is not TaskEngine or engine is not get_task_engine()
                or type(worker) is not TrainingProcessFence
                or type(admission) is not VerifiedTrainingCheckpointAdmission
                or operation not in {"save", "load"}):
            raise PermissionError("CHECKPOINT_PERMISSION_REQUIRED")
        TaskEngine._require_training_receipt_connection(connection)
        identity_args = {"actor_id": actor_id, "principal": principal}
        identity = owned_training_identity(**identity_args)
        resource = owned_training_approval_resource(
            training_request, domain_id=domain_id, context=context, **identity_args)
        binding = {"resource": resource, "scope_descriptors": context["scope_descriptors"],
                   "identity": {name: identity[name] for name in
                       ("actor_id", "caller", "principal_kind", "principal_ref")}}
        fingerprints = owned_training_phase_fingerprints(
            training_request, domain_id=domain_id, context=context, **identity_args)
        worker_binding = worker.worker_binding
        worker.require_live(worker_binding)
        verifier = make_owned_training_approval_verifier(
            self, domain_id=domain_id, context=context, **identity_args)
        if not verifier(training_request):
            raise PermissionError("CHECKPOINT_PERMISSION_REQUIRED")
        reference = self.owned_training_approval_reference(
            training_request=training_request, context=context, domain_id=domain_id,
            approval=approval, **identity_args)
        if reference != approval_reference:
            raise PermissionError("CHECKPOINT_PERMISSION_REQUIRED")
        current = engine.training_require_current_checkpoint_admission(
            task_id, admission=admission, operation=operation,
            expected_fingerprints=fingerprints, worker_binding=worker_binding,
            expected_binding=binding, expected_approval_reference=reference,
            pinned_public_key=pinned_public_key, connection=connection)
        worker.require_live(worker_binding)
        return current


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

    def get_valid_approval_token(
        self,
        operation: str,
        resource: Optional[str] = None,
        exact: bool = False,
    ) -> Optional[str]:
        """返回指定操作/资源当前有效的人工审批令牌（供一次性消费方使用）。

        生产调用方不应直接读取内部审批字典。这个窄接口让需要消费令牌的
        handler 在成功执行后撤销同一令牌，避免一次人工确认被重放。exact=True
        时只返回 operation 与 resource 都完全匹配的审批，不接受通配授权。
        """
        return self._get_approval_token(operation, resource, exact=exact)

    def _has_valid_approval(
        self,
        operation: str,
        resource: Optional[str] = None,
        exact: bool = False,
    ) -> bool:
        with self._approval_lock:
            for approval in self._approvals.values():
                if exact and (
                    approval.operation != operation or approval.resource != resource
                ):
                    continue
                if approval.is_valid(operation, resource):
                    return True
        return False

    def _get_approval_token(
        self,
        operation: str,
        resource: Optional[str] = None,
        exact: bool = False,
    ) -> Optional[str]:
        with self._approval_lock:
            for approval in self._approvals.values():
                if exact and (
                    approval.operation != operation or approval.resource != resource
                ):
                    continue
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
            "cth": {"read", "audit", "analyze", "research", "report_generate", "ai_call", "skill_execute"},
            "zbmp": {"read"},
        },
        "cth_operator": {
            "cth": {"read", "audit", "analyze", "research", "report_generate", "ai_call", "skill_execute", "db_write"},
        },
        "zbmp_admin": {
            "zbmp": {"*"},  # ZBMP 域全部操作
            "cth": {"read", "audit"},  # 仅只读 CTH（不能写/删/改配置）
        },
        "zbmp_analyst": {
            "zbmp": {"read", "audit", "analyze", "research", "report_generate", "ai_call", "skill_execute"},
            "cth": set(),  # ZBMP Analyst 无 CTH 权限
        },
        "zbmp_operator": {
            "zbmp": {"read", "audit", "analyze", "research", "report_generate", "ai_call", "skill_execute", "db_write"},
        },
        "system_admin": {"system": {"*"}},
        "system_operator": {
            "system": {"read", "audit", "analyze", "research", "report_generate", "ai_call", "skill_execute", "runtime_operation"},
        },
        "system_writer": {
            "system": {"read", "audit", "analyze", "research", "report_generate", "ai_call", "skill_execute", "db_write"},
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
    "ActorScopePermissionResult",
    "LocalWorkspacePrincipal",
    "owned_training_identity",
    "check_actor_scope_permission",
    "check_local_workspace_scope_permission",
    "resolve_local_workspace_principal",
    "bind_scope_permission_approval",
    "owned_training_approval_resource",
    "owned_training_phase_fingerprints",
    "make_owned_training_approval_verifier",
    "SkillMetadataPermissionDecision",
    "skill_metadata_approval_resource",
    "check_skill_metadata_change_permission",
    "ContentSourceImport",
    "content_source_import_resource",
    "check_content_source_import_permission",
    "prepare_content_source_import_confirmation",
    "confirm_content_source_import",
    "cancel_content_source_import_confirmation",
    "local_workspace_read_allowed",
    "ApprovalToken",
    "AuditEntry",
    "PermissionGate",
    "require_permission",
    "get_permission_gate",
    "reset_permission_gate",
    "set_testing_bypass",
    "is_testing_bypass_enabled",
]
