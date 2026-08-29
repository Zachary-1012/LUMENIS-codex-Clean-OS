"""
V4 升级模块入口
用法:
    from v4_upgrade import create_v4_blueprint, init_v4_modules
    init_v4_modules()
    app.register_blueprint(create_v4_blueprint())
"""
from .blueprint import create_v4_blueprint, init_v4_modules
from .auth import (
    init_auth_db, login, logout, get_current_user,
    require_auth, require_permission, require_owner,
)
from .config import AUTH_CONFIG, ROLE_PERMISSIONS, ADAPTER_CONFIG

__version__ = "4.0.0"
__all__ = [
    "create_v4_blueprint", "init_v4_modules",
    "init_auth_db", "login", "logout", "get_current_user",
    "require_auth", "require_permission", "require_owner",
    "AUTH_CONFIG", "ROLE_PERMISSIONS", "ADAPTER_CONFIG",
]
