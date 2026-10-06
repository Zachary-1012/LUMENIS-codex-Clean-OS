"""LUMENIS business-domain isolation compatibility layer.

CTH is LUMENIS Commerce Operations. BMP is LUMENIS Brand & Market; zbmp/ZBMP
remains a persisted compatibility identifier. Guangzhou Taikoo Hui is a
controlled reference Subject, not the default product context. GLOBAL / ALL
selection is owned by the canonical context contract.
"""
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from subject_context import (PRODUCT_CTH, PRODUCT_ZBMP, CTH_BRAND_KEY,
                             get_product_context, get_subject_context,
                             SubjectContext, ScopeContext)

PRODUCT_SYSTEM = "SYSTEM"
DOMAIN_CTH = "cth"
DOMAIN_ZBMP = "zbmp"
DOMAIN_SYSTEM = "system"

# product_id <-> domain_id 双向映射
_PRODUCT_TO_DOMAIN = {
    PRODUCT_CTH: DOMAIN_CTH,
    PRODUCT_ZBMP: DOMAIN_ZBMP,
    PRODUCT_SYSTEM: DOMAIN_SYSTEM,
}
_DOMAIN_TO_PRODUCT = {v: k for k, v in _PRODUCT_TO_DOMAIN.items()}


def product_to_domain(product_id: str) -> str:
    """product_id -> domain_id 映射。未知默认 cth（生产安全默认）。"""
    return _PRODUCT_TO_DOMAIN.get(product_id, DOMAIN_CTH)


def domain_to_product(domain_id: str) -> str:
    """domain_id -> product_id 映射。未知默认 CTH。"""
    return _DOMAIN_TO_PRODUCT.get(domain_id, PRODUCT_CTH)


@dataclass
class DomainBoundary:
    """域隔离边界定义。"""
    domain_id: str
    product_id: str
    name: str
    is_protected: bool
    isolated_resources: List[str] = field(default_factory=list)
    shared_resources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "product_id": self.product_id,
            "name": self.name,
            "is_protected": self.is_protected,
            "isolated_resources": self.isolated_resources,
            "shared_resources": self.shared_resources,
        }


# CTH 域：生产真相域，数据/主体/历史/证据/权限/运行时全部隔离
CTH_DOMAIN = DomainBoundary(
    domain_id="cth",
    product_id=PRODUCT_CTH,
    name="LUMENIS Commerce Operations",
    is_protected=True,
    isolated_resources=[
        "database", "subject_words", "subject_exclude_words",
        "historical_data", "evidence_namespace", "permission_scope",
        "runtime_instance", "business_rules", "report_templates",
    ],
    shared_resources=[
        "ai_gateway", "skill_registry", "evaluation_framework",
        "security_framework", "ui_design_system", "runtime_framework",
        "report_engine",
    ],
)

# ZBMP 域：多主体平台域
ZBMP_DOMAIN = DomainBoundary(
    domain_id="zbmp",
    product_id=PRODUCT_ZBMP,
    name="LUMENIS Brand & Market (ZBMP compatibility id)",
    is_protected=False,
    isolated_resources=[
        "brand_profiles", "campaigns", "subject_configs",
        "permission_scope", "evidence_namespace",
    ],
    shared_resources=[
        "ai_gateway", "skill_registry", "evaluation_framework",
        "security_framework", "ui_design_system", "runtime_framework",
        "report_engine", "collector_framework",
    ],
)

# SYSTEM 域：系统基础设施域，所有域共享的 Guardian/Collector/AI/Runtime
SYSTEM_DOMAIN = DomainBoundary(
    domain_id="system",
    product_id=PRODUCT_SYSTEM,
    name="System Infrastructure Domain",
    is_protected=False,
    isolated_resources=[
        "guardian_state", "runtime_leases", "system_config",
    ],
    shared_resources=[
        "ai_gateway", "skill_registry", "evaluation_framework",
        "security_framework", "ui_design_system", "runtime_framework",
        "report_engine", "collector_framework", "database",
        "logger", "cache_manager", "config",
    ],
)

DOMAINS = {"cth": CTH_DOMAIN, "zbmp": ZBMP_DOMAIN, "system": SYSTEM_DOMAIN}


def get_domain(domain_id: Optional[str] = None) -> DomainBoundary:
    """获取域边界。默认 CTH（生产安全默认）。"""
    did = domain_id or os.environ.get("ZBC_DOMAIN", "cth")
    return DOMAINS.get(did, CTH_DOMAIN)


def assert_isolation(domain_id: str, resource: str) -> None:
    """断言资源隔离：CTH 的隔离资源不允许被 ZBMP 访问，反之亦然。"""
    domain = get_domain(domain_id)
    other = DOMAINS["zbmp"] if domain_id == "cth" else DOMAINS["cth"]
    if resource in other.isolated_resources and domain.domain_id != other.domain_id:
        raise PermissionError(
            f"Domain Isolation Violation: {domain.domain_id} cannot access "
            f"{other.domain_id}'s isolated resource: {resource}"
        )


def assert_cth_protection() -> None:
    """CTH 保护断言：确保当前操作在 CTH 域内且主体正确。"""
    ctx = get_subject_context()
    if ctx.product_id != PRODUCT_CTH or ctx.brand_key != CTH_BRAND_KEY:
        raise PermissionError(
            f"CTH Protection Violation: expected {CTH_BRAND_KEY}, "
            f"got {ctx.brand_key} (product={ctx.product_id})"
        )


def cross_domain_access_allowed(from_domain: str, to_domain: str,
                                resource: str) -> bool:
    """检查跨域访问是否允许。共享资源允许，隔离资源拒绝。"""
    if from_domain == to_domain:
        return True
    target = get_domain(to_domain)
    return resource in target.shared_resources


# ---------------------------------------------------------------------------
# DomainContext：所有操作的域身份载体（整合 product_id + domain_id + subject_id + scope）
# ---------------------------------------------------------------------------
_domain_local = threading.local()


@dataclass
class DomainContext:
    """域身份上下文：整合 product_id + domain_id + subject_id + scope。

    作为所有数据操作、API 请求、Runtime 任务的域身份载体。
    domain_id 和 product_id 同时存在，二者通过映射保持一致。
    """
    domain_id: str = DOMAIN_CTH
    product_id: str = PRODUCT_CTH
    subject_id: str = ""
    brand_key: str = CTH_BRAND_KEY
    scope: ScopeContext = field(default_factory=ScopeContext)
    trace_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 确保 domain_id 和 product_id 一致
        if self.domain_id == DOMAIN_CTH and self.product_id != PRODUCT_CTH:
            self.product_id = PRODUCT_CTH
        elif self.domain_id == DOMAIN_ZBMP and self.product_id != PRODUCT_ZBMP:
            self.product_id = PRODUCT_ZBMP
        elif self.domain_id == DOMAIN_SYSTEM and self.product_id != PRODUCT_SYSTEM:
            self.product_id = PRODUCT_SYSTEM
        # CTH 保护：强制 subject
        if self.domain_id == DOMAIN_CTH:
            self.brand_key = CTH_BRAND_KEY
            self.subject_id = CTH_BRAND_KEY.upper().replace("-", "_").replace(" ", "_")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "product_id": self.product_id,
            "subject_id": self.subject_id,
            "brand_key": self.brand_key,
            "trace_id": self.trace_id,
            "scope": {
                "time_range": self.scope.time_range,
                "data_partition": self.scope.data_partition,
                "permission_scope": self.scope.permission_scope,
            },
            "metadata": self.metadata,
        }

    def to_subject_context(self) -> SubjectContext:
        """转换为 SubjectContext（兼容现有 subject_context 体系）。"""
        return SubjectContext(
            subject_id=self.subject_id or self.brand_key.upper().replace("-", "_").replace(" ", "_"),
            brand_key=self.brand_key,
            product_id=self.product_id,
            scope=self.scope,
        )

    @classmethod
    def from_product(cls, product_id: str, subject_id: str = "",
                     brand_key: str = "", trace_id: str = "") -> "DomainContext":
        """从 product_id 构建 DomainContext，自动映射 domain_id。"""
        domain_id = product_to_domain(product_id)
        bk = brand_key or (CTH_BRAND_KEY if domain_id == DOMAIN_CTH else "")
        sid = subject_id or bk.upper().replace("-", "_").replace(" ", "_")
        return cls(
            domain_id=domain_id,
            product_id=product_id,
            subject_id=sid,
            brand_key=bk,
            trace_id=trace_id,
        )

    @classmethod
    def from_domain(cls, domain_id: str, subject_id: str = "",
                    brand_key: str = "", trace_id: str = "") -> "DomainContext":
        """从 domain_id 构建 DomainContext，自动映射 product_id。"""
        product_id = domain_to_product(domain_id)
        return cls.from_product(product_id, subject_id, brand_key, trace_id)


def set_domain_context(ctx: DomainContext) -> None:
    """设置当前线程的 DomainContext。"""
    _domain_local.domain_context = ctx


def get_domain_context() -> Optional[DomainContext]:
    """获取当前线程的 DomainContext。不存在时从环境变量/默认构建。"""
    ctx = getattr(_domain_local, "domain_context", None)
    if ctx is not None:
        return ctx
    # 回退：从环境变量构建
    domain_id = os.environ.get("ZBC_DOMAIN", DOMAIN_CTH)
    return DomainContext.from_domain(domain_id)


def clear_domain_context() -> None:
    """清除当前线程的 DomainContext。"""
    if hasattr(_domain_local, "domain_context"):
        del _domain_local.domain_context


def domain_summary() -> Dict[str, Any]:
    """返回域隔离总览。"""
    return {
        "domains": {k: v.to_dict() for k, v in DOMAINS.items()},
        "current_domain": get_domain().domain_id,
        "current_product": get_product_context().product_id,
        "current_domain_context": get_domain_context().to_dict() if get_domain_context() else None,
    }
