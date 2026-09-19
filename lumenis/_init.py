"""
V4 升级模块入口
用法:
    from lumenis import create_v4_blueprint, init_v4_modules
    init_v4_modules()
    app.register_blueprint(create_v4_blueprint())

导入优化（2026-09-07）：blueprint / auth 为重量级子树（拉起 collect/importer/ai_hub 等），
改为 PEP 562 惰性导入，避免 `import lumenis.adapters.*` 等轻量场景被重子树拖慢。
config 为纯标准库轻量模块，保持直接导入。
"""
from .config import AUTH_CONFIG, ROLE_PERMISSIONS, ADAPTER_CONFIG

__version__ = "4.0.0"

__all__ = [
    "create_v4_blueprint", "init_v4_modules",
    "init_auth_db", "login", "logout", "get_current_user",
    "require_auth", "require_permission", "require_owner",
    "AUTH_CONFIG", "ROLE_PERMISSIONS", "ADAPTER_CONFIG",
]

_LAZY_ATTRS = {
    "create_v4_blueprint": (".blueprint", "create_v4_blueprint"),
    "init_v4_modules": (".blueprint", "init_v4_modules"),
    "init_auth_db": (".auth", "init_auth_db"),
    "login": (".auth", "login"),
    "logout": (".auth", "logout"),
    "get_current_user": (".auth", "get_current_user"),
    "require_auth": (".auth", "require_auth"),
    "require_permission": (".auth", "require_permission"),
    "require_owner": (".auth", "require_owner"),
}


def __getattr__(name):
    """PEP 562 惰性导入：仅在属性被实际访问时才加载重量级子模块。"""
    if name in _LAZY_ATTRS:
        module_path, attr_name = _LAZY_ATTRS[name]
        import importlib
        mod = importlib.import_module(module_path, __name__)
        value = getattr(mod, attr_name)
        globals()[name] = value  # 缓存，避免重复导入
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
