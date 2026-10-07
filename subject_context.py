"""LUMENIS Subject Context compatibility layer.

Current product context is selected by the canonical GLOBAL / ALL -> FOCUS
contract. CTH means LUMENIS Commerce Operations and BMP means LUMENIS Brand &
Market. Guangzhou Taikoo Hui is a controlled deep-reference Subject. Historical
no-argument CTH/Guangzhou fallbacks remain only for legacy callers and must not
be exposed as the product default.
"""
import os
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
        default_subject=CTH_SUBJECT_ID,
    ),
    PRODUCT_ZBMP: ProductContext(
        product_id=PRODUCT_ZBMP,
        name="LUMENIS Brand & Market",
        is_protected=False,
        default_subject=None,
    ),
}


def get_product_context(product_id: Optional[str] = None) -> ProductContext:
    """读取旧 product_id 域上下文。

    当前实现仍会将缺省或未识别标识回退为 CTH；这是待迁移的兼容行为，
    不是授权判断，也不是 GLOBAL / ALL 的产品默认。新入口应使用其现有
    严格域/范围校验；修改这里的行为须先核对调用方与持久化兼容。
    """
    pid = product_id or os.environ.get("ZBC_PRODUCT_ID", PRODUCT_CTH)
    return PRODUCTS.get(pid, PRODUCTS[PRODUCT_CTH])


def get_subject_context(brand_key: Optional[str] = None,
                        product_id: Optional[str] = None) -> SubjectContext:
    """获取主体上下文。

    优先级：显式 brand_key > 环境变量 ZBC_ACTIVE_BRAND > CTH 默认。
    CTH 保护由 domain_isolation 层在 SQL/执行边界强制执行，
    不在此强制 brand_key，以支持多品牌 KOS 场景的环境变量切换。
    不依赖 subject_rules，避免循环导入。
    """
    bk = brand_key or os.environ.get("ZBC_ACTIVE_BRAND", CTH_BRAND_KEY)
    product = get_product_context(product_id)
    subject_id = bk.upper().replace("-", "_").replace(" ", "_")

    return SubjectContext(
        subject_id=subject_id,
        brand_key=bk,
        product_id=product.product_id,
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

def get_request_brand():
    """从当前 Flask 请求中解析 brand_key（请求级，非全局）。

    优先级：
      1. 请求头 X-Brand-Key
      2. Session 中的 brand_key
      3. 查询参数 ?brand_key=
      4. 环境变量 ZBC_ACTIVE_BRAND（兼容旧行为）
      5. CTH 默认（guangzhou_taikoo_hui）

    不在 Flask 请求上下文中时返回 None，调用方应回退到 get_subject_context()。
    """
    try:
        from flask import request, session
    except Exception:
        return None

    # 1. Header
    brand = request.headers.get("X-Brand-Key", "").strip()
    if brand:
        return brand

    # 2. Session
    brand = session.get("brand_key", "")
    if brand:
        return brand

    # 3. Query param
    brand = request.args.get("brand_key", "").strip()
    if brand:
        return brand

    return None


def init_app(app):
    """注册 Flask before_request / after_request 钩子，实现请求级主体+域隔离。

    每个 HTTP 请求自动：
      - 从请求头 X-Domain-Id / X-Product-Id 解析域身份
      - 从请求上下文解析 brand_key
      - 设置线程级 SubjectContext + DomainContext
      - 请求结束后清除线程上下文（防止线程复用时的品牌/域泄漏）

    CTH 保护：当 domain_id=cth 或 ZBC_PRODUCT_ID=CTH 时，
    强制 brand_key=guangzhou_taikoo_hui，任何请求级 brand 切换都不允许覆盖 CTH 生产主体。

    双域核心扩展（V2.0）：除了 brand_key，还从 X-Domain-Id / X-Product-Id 解析域身份，
    before_request 中设置线程 DomainContext（product_id + domain_id），after_request 中清除。

    用法（在 app.py 中）：
        from subject_context import init_app
        init_app(app)
    """
    from flask import g

    @app.before_request
    def _set_subject_context():
        # 双域核心：从请求头解析 domain_id / product_id
        domain_id = ""
        product_id = None
        try:
            from flask import request as _req
            domain_id = _req.headers.get("X-Domain-Id", "").strip().lower()
            product_id_hdr = _req.headers.get("X-Product-Id", "").strip().upper()
            if product_id_hdr:
                product_id = product_id_hdr
        except Exception:
            pass

        brand = get_request_brand()

        # CTH 强制保护：domain_id=cth 或环境变量 ZBC_PRODUCT_ID=CTH
        is_cth = (domain_id == "cth" or os.environ.get("ZBC_PRODUCT_ID") == PRODUCT_CTH)
        if is_cth:
            brand = CTH_BRAND_KEY
            product_id = PRODUCT_CTH
            domain_id = "cth"
        elif domain_id == "zbmp":
            # 双域核心：显式 X-Domain-Id: zbmp 时强制 product_id=ZBMP
            # （否则 get_product_context 默认 CTH，导致域身份不一致）
            product_id = PRODUCT_ZBMP
        elif domain_id == "system":
            product_id = "SYSTEM"

        ctx = get_subject_context(brand_key=brand, product_id=product_id)
        set_thread_context(ctx)
        g.subject_context = ctx

        # 双域核心：设置线程 DomainContext（懒导入避免循环依赖）
        try:
            from domain_isolation import DomainContext, set_domain_context, domain_to_product
            if not domain_id:
                domain_id = "cth" if ctx.product_id == PRODUCT_CTH else "zbmp"
            dctx = DomainContext(
                domain_id=domain_id,
                product_id=ctx.product_id,
                brand_key=brand or CTH_BRAND_KEY,
                subject_id=ctx.subject_id,
            )
            set_domain_context(dctx)
            g.domain_context = dctx
        except Exception as _dc_err:
            # DomainContext 设置失败不阻断请求（SubjectContext 已设置）
            g.domain_context = None

    @app.after_request
    def _clear_subject_context(response):
        clear_thread_context()
        # 双域核心：清除 DomainContext
        try:
            from domain_isolation import clear_domain_context
            clear_domain_context()
        except Exception:
            pass
        return response

    @app.teardown_request
    def _teardown_subject_context(exc=None):
        clear_thread_context()
        try:
            from domain_isolation import clear_domain_context
            clear_domain_context()
        except Exception:
            pass

    return app


class brand_scope:
    """上下文管理器：在代码块内临时切换主体上下文，退出后自动恢复。

    用法：
        with brand_scope("hainan_cdf"):
            # 此块内所有 get_active_brand() 返回 hainan_cdf
            result = subject_hit("海南中免")
        # 退出后恢复原上下文

    这是显式的、局部的主体切换，不修改全局状态。
    CTH 保护：当 ZBC_PRODUCT_ID=CTH 时，不允许切换到非 CTH 品牌。
    """

    def __init__(self, brand_key: str, product_id: Optional[str] = None):
        self.brand_key = brand_key
        self.product_id = product_id
        self._previous = None

    def __enter__(self):
        # CTH 保护
        if os.environ.get("ZBC_PRODUCT_ID") == PRODUCT_CTH:
            if self.brand_key != CTH_BRAND_KEY:
                raise PermissionError(
                    f"CTH Protection: cannot switch brand to {self.brand_key} "
                    f"when ZBC_PRODUCT_ID=CTH"
                )
        self._previous = get_thread_context()
        ctx = get_subject_context(brand_key=self.brand_key, product_id=self.product_id)
        set_thread_context(ctx)
        return ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._previous is not None:
            set_thread_context(self._previous)
        else:
            clear_thread_context()
        return False
