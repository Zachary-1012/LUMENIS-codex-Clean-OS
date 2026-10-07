"""LUMENIS business-domain isolation compatibility layer.

CTH is LUMENIS Commerce Operations. BMP is LUMENIS Brand & Market; zbmp/ZBMP
remains a persisted compatibility identifier. Guangzhou Taikoo Hui is a
controlled reference Subject, not the default product context. GLOBAL / ALL
selection is owned by the canonical context contract.
"""
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
    """Validate a domain identity; BMP retains the persisted ZBMP identifier."""
    key = product_id.strip().upper() if isinstance(product_id, str) else ""
    if key == "BMP":
        key = PRODUCT_ZBMP
    if key not in _PRODUCT_TO_DOMAIN:
        raise ValueError("INVALID_PRODUCT_ID")
    return _PRODUCT_TO_DOMAIN[key]


def domain_to_product(domain_id: str) -> str:
    """Validate domain IDs without assigning unknown inputs to CTH."""
    key = domain_id.strip().lower() if isinstance(domain_id, str) else ""
    if key == "bmp":
        key = DOMAIN_ZBMP
    if key not in _DOMAIN_TO_PRODUCT:
        raise ValueError("INVALID_DOMAIN_ID")
    return _DOMAIN_TO_PRODUCT[key]


def resolve_domain_identity(domain_id=None, product_id=None):
    """Resolve an optional coherent pair. Empty pair means no selected domain.

    It grants no permission and selects no Subject. Explicit mismatches fail
    before downstream routing; callers requiring a domain must reject ('', '').
    """
    did = product_to_domain(domain_to_product(domain_id)) if domain_id is not None and domain_id != "" else ""
    pid = domain_to_product(product_to_domain(product_id)) if product_id is not None and product_id != "" else ""
    if did and pid and domain_to_product(did) != pid:
        raise ValueError("DOMAIN_PRODUCT_MISMATCH")
    if did:
        return did, domain_to_product(did)
    if pid:
        return product_to_domain(pid), pid
    return "", ""


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
    """Read an explicit or bound domain; a global selection is not CTH."""
    if domain_id is None:
        ctx = get_domain_context()
        domain_id = ctx.domain_id if ctx else None
    return DOMAINS[product_to_domain(domain_to_product(domain_id))]


def assert_isolation(domain_id: str, resource: str) -> None:
    """断言资源隔离：CTH 的隔离资源不允许被 ZBMP 访问，反之亦然。"""
    domain = get_domain(domain_id)
    other = DOMAINS["zbmp"] if domain.domain_id == "cth" else DOMAINS["cth"]
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
    source = get_domain(from_domain)
    target = get_domain(to_domain)
    if source.domain_id == target.domain_id:
        return True
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
    domain_id: str = ""
    product_id: str = ""
    subject_id: str = ""
    brand_key: str = ""
    scope: ScopeContext = field(default_factory=ScopeContext)
    trace_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.domain_id, self.product_id = resolve_domain_identity(
            self.domain_id, self.product_id)
        if (self.subject_id or self.brand_key) and not self.domain_id:
            raise ValueError("FOCUS_DOMAIN_REQUIRED")
        if (self.subject_id or self.brand_key) and self.domain_id == DOMAIN_SYSTEM:
            raise ValueError("SYSTEM_BUSINESS_FOCUS_FORBIDDEN")

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
        bk = brand_key
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
    """Return only the bound context; machine environment cannot select a user."""
    return getattr(_domain_local, "domain_context", None)


def clear_domain_context() -> None:
    """清除当前线程的 DomainContext。"""
    if hasattr(_domain_local, "domain_context"):
        del _domain_local.domain_context


def domain_summary() -> Dict[str, Any]:
    """返回域隔离总览。"""
    ctx = get_domain_context()
    return {
        "domains": {k: v.to_dict() for k, v in DOMAINS.items()},
        "current_domain": ctx.domain_id if ctx else None,
        "current_product": ctx.product_id if ctx else None,
        "current_domain_context": ctx.to_dict() if ctx else None,
    }
