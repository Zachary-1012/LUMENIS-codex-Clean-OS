"""LUMENIS Subject Context compatibility layer.

Current product context is selected by the canonical GLOBAL / ALL -> FOCUS
contract. CTH means LUMENIS Commerce Operations and BMP means LUMENIS Brand &
Market. Guangzhou Taikoo Hui is a controlled deep-reference Subject. Missing selection stays GLOBAL / ALL. Reference-Subject compatibility filters
explicitly bind their own subject; no machine environment can select it for users.
"""
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

# 历史接口的域标识（不是独立产品）；用户可见名称为 CTH / BMP。
PRODUCT_CTH = "CTH"
PRODUCT_ZBMP = "ZBMP"

# 旧 CTH 调用的参考主体；不能据此建立 GLOBAL / ALL 的默认聚焦。
CTH_SUBJECT_ID = "GUANGZHOU_TAIKOO_HUI"
CTH_BRAND_KEY = "guangzhou_taikoo_hui"

# 线程本地上下文
_local = threading.local()


@dataclass
class ScopeContext:
    """资源作用域：时间范围、数据分区、权限边界。"""
    time_range: Optional[str] = None
    data_partition: Optional[str] = None
    permission_scope: str = "read"
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SubjectContext:
    """主体上下文：品牌/主体的唯一标识。"""
    subject_id: str
    brand_key: str
    product_id: str
    policy_version: str = "v1"
    scope: ScopeContext = field(default_factory=ScopeContext)

    def to_dict(self) -> Dict:
        return {
            "subject_id": self.subject_id,
            "brand_key": self.brand_key,
            "product_id": self.product_id,
            "policy_version": self.policy_version,
            "scope": {
                "time_range": self.scope.time_range,
                "data_partition": self.scope.data_partition,
                "permission_scope": self.scope.permission_scope,
            },
        }


@dataclass(frozen=True)
class ContextSelection:
    """Typed Product Core focus selection; it carries no permission grant."""

    mode: str
    domain_id: Optional[str] = None
    subject_id: Optional[str] = None
    brand_focus_id: Optional[str] = None

    @classmethod
    def global_all(cls) -> "ContextSelection":
        return cls(mode="GLOBAL_ALL")

    @classmethod
    def focus(
        cls,
        *,
        domain_id: str,
        subject_id: str,
        brand_focus_id: Optional[str] = None,
    ) -> "ContextSelection":
        return cls(
            mode="FOCUS",
            domain_id=domain_id,
            subject_id=subject_id,
            brand_focus_id=brand_focus_id,
        )

    def to_dict(self) -> Dict[str, Optional[str]]:
        resource_type = (
            "GLOBAL" if self.mode == "GLOBAL_ALL"
            else "SUBJECT" if self.domain_id == "CTH"
            else "BRAND_FOCUS"
        )
        return {
            "mode": self.mode,
            "domain_id": self.domain_id,
            "subject_id": self.subject_id,
            "brand_focus_id": self.brand_focus_id,
            "resource_type": resource_type,
        }


@dataclass
class ProductContext:
    """产品上下文：CTH 或 ZBMP。"""
    product_id: str
    name: str
    is_protected: bool = False
    default_subject: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "is_protected": self.is_protected,
            "default_subject": self.default_subject,
        }


# 兼容 product_id 字段的域上下文；存储标识保留，不执行 ID 迁移。
PRODUCTS = {
    PRODUCT_CTH: ProductContext(
        product_id=PRODUCT_CTH,
        name="LUMENIS Commerce Operations",
        is_protected=True,
        default_subject=None,
    ),
    PRODUCT_ZBMP: ProductContext(
        product_id=PRODUCT_ZBMP,
        name="LUMENIS Brand & Market",
        is_protected=False,
        default_subject=None,
    ),
    "SYSTEM": ProductContext(product_id="SYSTEM", name="System Infrastructure Domain"),
}


def get_product_context(product_id: Optional[str] = None) -> ProductContext:
    """Return a validated domain label or an unselected GLOBAL context."""
    from domain_isolation import resolve_domain_identity
    if product_id is None:
        ctx = get_thread_context()
        product_id = ctx.product_id if ctx else None
    _, pid = resolve_domain_identity(product_id=product_id)
    return PRODUCTS[pid] if pid else ProductContext("", "LUMENIS / GLOBAL")


def get_subject_context(brand_key: Optional[str] = None,
                        product_id: Optional[str] = None) -> SubjectContext:
    """Read the bound selection or construct an explicitly selected subject.

    Blank fields represent no focus, not a synthetic subject or authorization.
    Environment defaults never establish a request's domain or subject.
    """
    bound = get_thread_context()
    if brand_key is None and product_id is None and bound is not None:
        return bound
    product = get_product_context(product_id)
    bk = (brand_key or "").strip()
    if bk and not product.product_id:
        raise ValueError("FOCUS_DOMAIN_REQUIRED")
    return SubjectContext(
        subject_id=bk.upper().replace("-", "_").replace(" ", "_"),
        brand_key=bk, product_id=product.product_id,
    )


def set_thread_context(ctx: SubjectContext) -> None:
    """设置当前线程的 Subject Context。"""
    _local.subject_context = ctx


def get_thread_context() -> Optional[SubjectContext]:
    """获取当前线程的 Subject Context。"""
    return getattr(_local, "subject_context", None)


def clear_thread_context() -> None:
    """清除当前线程的 Subject Context。"""
    if hasattr(_local, "subject_context"):
        del _local.subject_context


def current_scope() -> Dict:
    """获取当前操作的完整 Scope 信息（用于日志/审计/Evidence）。"""
    ctx = get_thread_context() or get_subject_context()
    product = get_product_context(ctx.product_id)
    return {
        "product": product.to_dict(),
        "subject": ctx.to_dict(),
    }


def assert_cth_protection() -> None:
    """CTH 保护断言：确保当前主体是 CTH。"""
    ctx = get_thread_context() or get_subject_context()
    if ctx.product_id != PRODUCT_CTH or ctx.brand_key != CTH_BRAND_KEY:
        raise PermissionError(
            f"CTH Protection Violation: expected {CTH_BRAND_KEY}, "
            f"got {ctx.brand_key} (product={ctx.product_id})"
        )


# ---------------------------------------------------------------------------
# Flask Request-Level Isolation (Shard D / Team 1)
# ---------------------------------------------------------------------------

def resolve_request_identity(default_domain=None):
    """Resolve a whole identity pair at one precedence level, then bind a route.

    Headers precede session, which precedes query. Values from different levels
    cannot form a contradictory identity. Empty supplied values are invalid.
    Domain routes establish a domain, never a reference Subject or Permission.
    """
    from flask import request, session
    from domain_isolation import resolve_domain_identity
    pairs = (
        (request.headers.get("X-Domain-Id"), request.headers.get("X-Product-Id")),
        (session.get("domain_id"), session.get("product_id")),
        (request.args.get("domain_id"), request.args.get("product_id")),
    )
    domain, product = "", ""
    for raw_domain, raw_product in pairs:
        if raw_domain is not None or raw_product is not None:
            for raw in (raw_domain, raw_product):
                if raw is not None and (not isinstance(raw, str) or not raw.strip()):
                    raise ValueError("INVALID_DOMAIN_IDENTITY")
            domain, product = resolve_domain_identity(raw_domain, raw_product)
            break
    if default_domain is not None:
        route_domain, route_product = resolve_domain_identity(default_domain)
        if domain and domain != route_domain:
            raise ValueError("ROUTE_DOMAIN_MISMATCH")
        domain, product = route_domain, route_product
    return domain, product


def get_request_brand():
    """Explicit request brand only; no environment or reference fallback."""
    from flask import has_request_context, request, session
    if not has_request_context():
        return None
    explicit_identity = any(key in request.headers for key in ("X-Domain-Id", "X-Product-Id")) or any(
        key in request.args for key in ("domain_id", "product_id"))
    # Changing a request's domain must not inherit the previous session's focus.
    for brand in (request.headers.get("X-Brand-Key"), request.args.get("brand_key"),
                  None if explicit_identity else session.get("brand_key")):
        if brand is not None:
            if not isinstance(brand, str) or not brand.strip():
                raise ValueError("INVALID_BRAND_KEY")
            return brand.strip()
    return None


def bind_request_context(default_domain=None):
    """Bind validated request metadata. Permission still belongs to its owner."""
    from flask import g, request
    from domain_isolation import DomainContext, set_domain_context
    domain, product = resolve_request_identity(default_domain)
    brand = get_request_brand() or ""
    raw_subject_id = request.headers.get("X-Subject-Id")
    if raw_subject_id is not None and (
        not raw_subject_id.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in raw_subject_id)
    ):
        raise ValueError("INVALID_SUBJECT_ID")
    subject_id = raw_subject_id.strip() if raw_subject_id is not None else ""
    ctx = DomainContext(domain_id=domain, product_id=product,
                        brand_key=brand, subject_id=subject_id)
    set_domain_context(ctx)
    subject = ctx.to_subject_context()
    set_thread_context(subject)
    g.domain_context = ctx
    g.subject_context = subject
    # This is untrusted request metadata, not a validated Focus selection.
    # The existing settings/Scope/Permission owners perform registry admission.
    return ctx


def init_app(app):
    """Bind request identity and reliably clear it across success and errors."""
    from flask import jsonify, request
    from domain_isolation import clear_domain_context

    @app.before_request
    def _set_subject_context():
        clear_thread_context()
        clear_domain_context()
        try:
            route_domain = {"cth_api": "cth", "zbmp_api": "zbmp", "system_api": "system"}.get(
                request.blueprint)
            bind_request_context(route_domain)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.after_request
    def _clear_subject_context(response):
        clear_thread_context()
        clear_domain_context()
        return response

    @app.teardown_request
    def _teardown_subject_context(exc=None):
        clear_thread_context()
        clear_domain_context()

    return app


class brand_scope:
    """上下文管理器：在代码块内临时切换主体上下文，退出后自动恢复。

    用法：
        with brand_scope("hainan_cdf"):
            # 此块内所有 get_active_brand() 返回 hainan_cdf
            result = subject_hit("海南中免")
        # 退出后恢复原上下文

    这是显式的、局部的主体切换，不修改全局状态。
    A domain must be explicit or already bound; process environment is not consent.
    """

    def __init__(self, brand_key: str, product_id: Optional[str] = None):
        self.brand_key = brand_key
        self.product_id = product_id
        self._previous = None
        self._previous_domain = None

    def __enter__(self):
        from domain_isolation import DomainContext, get_domain_context, set_domain_context
        self._previous = get_thread_context()
        self._previous_domain = get_domain_context()
        ctx = get_subject_context(brand_key=self.brand_key, product_id=self.product_id)
        domain = DomainContext.from_product(ctx.product_id, ctx.subject_id, ctx.brand_key)
        set_thread_context(ctx)
        set_domain_context(domain)
        return ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        from domain_isolation import clear_domain_context, set_domain_context
        if self._previous is not None:
            set_thread_context(self._previous)
        else:
            clear_thread_context()
        if self._previous_domain is None:
            clear_domain_context()
        else:
            set_domain_context(self._previous_domain)
        return False
