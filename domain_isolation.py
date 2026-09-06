"""LUMENIS Domain Isolation（V2 P0-1）

CTH 和 ZBMP 是 ZBC 的两个业务域，共享 Capability/AI/Skill/Evaluation/Security/UI，
但隔离 Data/Subject/Historical Truth/Evidence Namespace/Permission Scope/Runtime/Business Rules。

CTH = Guangzhou Taikoo Hui Protected Production Domain（生产真相域，受保护）
ZBMP = Multi-Subject Brand Management Platform（多主体平台域）
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from subject_context import (PRODUCT_CTH, PRODUCT_ZBMP, CTH_BRAND_KEY,
                             get_product_context, get_subject_context)


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
    name="Guangzhou Taikoo Hui Protected Production Domain",
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
    name="Multi-Subject Brand Management Platform",
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

DOMAINS = {"cth": CTH_DOMAIN, "zbmp": ZBMP_DOMAIN}


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


def domain_summary() -> Dict[str, Any]:
    """返回域隔离总览。"""
    return {
        "domains": {k: v.to_dict() for k, v in DOMAINS.items()},
        "current_domain": get_domain().domain_id,
        "current_product": get_product_context().product_id,
    }
