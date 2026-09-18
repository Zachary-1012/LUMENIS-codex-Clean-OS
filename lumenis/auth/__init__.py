"""认证模块包"""
from .models import init_auth_db, get_db
from .service import (
    login, login_by_key, logout, get_current_user, require_auth, require_permission,
    require_owner, require_security_verification, create_user, list_users,
    update_user_status, change_password, reset_user_password, ensure_initialized
)
from .audit import log_audit, query_audit_logs, get_audit_stats
from .security import verify_security_questions

__all__ = [
    "init_auth_db", "get_db", "login", "login_by_key", "logout", "get_current_user",
    "require_auth", "require_permission", "require_owner",
    "require_security_verification", "create_user", "list_users",
    "update_user_status", "change_password", "reset_user_password",
    "log_audit", "query_audit_logs", "get_audit_stats",
    "verify_security_questions", "ensure_initialized",
]
