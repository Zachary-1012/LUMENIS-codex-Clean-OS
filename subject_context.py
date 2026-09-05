"""LUMENIS Subject Context（V2 P0-19）

建立 ProductContext → SubjectContext → ScopeContext → Resource 四层上下文。
消除 active_brand 作为系统真实数据边界，所有数据操作携带 Subject Scope。

CTH = Guangzhou Taikoo Hui Protected Production Domain（生产真相域）
ZBMP = Multi-Subject Brand Management Platform（多主体平台域）

向后兼容：get_active_brand() 仍可用，但内部通过 SubjectContext 管理。
"""
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional

# 产品域常量
PRODUCT_CTH = "CTH"
PRODUCT_ZBMP = "ZBMP"

# CTH 固定主体
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


# 预定义产品上下文
PRODUCTS = {
    PRODUCT_CTH: ProductContext(
        product_id=PRODUCT_CTH,
        name="Guangzhou Taikoo Hui Protected Production Domain",
        is_protected=True,
        default_subject=CTH_SUBJECT_ID,
    ),
    PRODUCT_ZBMP: ProductContext(
        product_id=PRODUCT_ZBMP,
        name="Multi-Subject Brand Management Platform",
        is_protected=False,
        default_subject=None,
    ),
}


def get_product_context(product_id: Optional[str] = None) -> ProductContext:
    """获取产品上下文。默认 CTH（生产安全默认）。"""
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
    """注册 Flask before_request / after_request 钩子，实现请求级主体隔离。

    每个 HTTP 请求自动：
      - 从请求上下文解析 brand_key
      - 设置线程级 SubjectContext
      - 请求结束后清除线程上下文（防止线程复用时的品牌泄漏）

    CTH 保护：当 ZBC_PRODUCT_ID=CTH 时，强制 brand_key=guangzhou_taikoo_hui，
    任何请求级 brand 切换都不允许覆盖 CTH 生产主体。

    用法（在 app.py 中）：
        from subject_context import init_app
        init_app(app)
    """
    from flask import g

    @app.before_request
    def _set_subject_context():
        brand = get_request_brand()
        product_id = None

        # CTH 强制保护
        if os.environ.get("ZBC_PRODUCT_ID") == PRODUCT_CTH:
            brand = CTH_BRAND_KEY
            product_id = PRODUCT_CTH

        ctx = get_subject_context(brand_key=brand, product_id=product_id)
        set_thread_context(ctx)
        g.subject_context = ctx

    @app.after_request
    def _clear_subject_context(response):
        clear_thread_context()
        return response

    @app.teardown_request
    def _teardown_subject_context(exc=None):
        clear_thread_context()

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
