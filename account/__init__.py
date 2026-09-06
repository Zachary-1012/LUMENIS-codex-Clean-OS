"""
account/ — ZBC/LUMENIS 主线账户体系模块（P1-F Apple ID 式账户）

将 v4_upgrade/auth/ 提升为一级主线模块，保留 v4_ 表名保护现有数据。
新增：名额硬约束(1+3+5)、双域授权矩阵、TOTP动态口令、随机数字验证码、
产品保护配置(ZBMP=TOTP/CTH=密码/SYSTEM=二次确认)、导航自定义、技能管理、
静态密钥迁移。

不删表、不丢数据；v4_upgrade/auth/ 保留为 deprecated 兼容层。
"""
from .models import init_account_db, get_db, ACCOUNT_TABLES_SQL
from .service import (
    get_current_user, require_auth, require_owner, require_admin_or_owner,
    create_member, list_members, update_member, remove_member,
    get_quota_counts, change_password, update_profile,
    list_sessions, revoke_session, ensure_account_initialized,
)
from .verification import (
    request_verification_code, verify_code, resend_code,
    list_pending_codes, VERIFICATION_CONFIG,
)
from .workspace_keys import (
    list_workspace_keys, create_workspace_key, revoke_workspace_key,
    get_rotation_required_count,
)
from .authorization import (
    get_member_authorizations, set_member_authorizations,
    check_dual_domain_permission,
)
from .audit import log_audit, query_audit_logs, get_audit_stats
from .totp import (
    get_totp_status, setup_totp, confirm_totp, verify_user_totp, reset_totp,
    TOTP_CONFIG, get_totp as _get_totp,
)
from .product_protection import (
    get_protection_config, set_protection_config, check_protection_required,
)
from .nav_config import (
    get_nav_config, save_nav_config, reset_nav_config, DEFAULT_NAV,
)
from .skills import (
    list_skills, set_skill_status, get_enabled_skills,
)
from .api import account_bp
from .compat import compat_bp

__version__ = "1.0.0"
__all__ = [
    "init_account_db", "get_db", "ACCOUNT_TABLES_SQL",
    "get_current_user", "require_auth", "require_owner", "require_admin_or_owner",
    "create_member", "list_members", "update_member", "remove_member",
    "get_quota_counts", "change_password", "update_profile",
    "list_sessions", "revoke_session", "ensure_account_initialized",
    "request_verification_code", "verify_code", "resend_code",
    "list_pending_codes", "VERIFICATION_CONFIG",
    "list_workspace_keys", "create_workspace_key", "revoke_workspace_key",
    "get_rotation_required_count",
    "get_member_authorizations", "set_member_authorizations",
    "check_dual_domain_permission",
    "log_audit", "query_audit_logs", "get_audit_stats",
    "get_totp_status", "setup_totp", "confirm_totp", "verify_user_totp", "reset_totp",
    "TOTP_CONFIG",
    "get_protection_config", "set_protection_config", "check_protection_required",
    "get_nav_config", "save_nav_config", "reset_nav_config", "DEFAULT_NAV",
    "list_skills", "set_skill_status", "get_enabled_skills",
    "account_bp", "compat_bp",
]
