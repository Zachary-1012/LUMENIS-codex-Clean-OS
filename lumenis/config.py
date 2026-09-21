"""
V4 模块配置
所有配置集中在此，便于统一管理。
"""
import os

from lumenis.shared.database import main_db_path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 认证配置
AUTH_CONFIG = {
    "token_expire_hours": 24 * 7,          # Token有效期7天
    "token_secret_env": "V4_TOKEN_SECRET",  # 从环境变量读取，未设置则自动生成
    "max_login_attempts": 5,                # 最大登录失败次数
    "lockout_minutes": 15,                  # 锁定时长(分钟)
    "bcrypt_rounds": 12,                    # 密码哈希轮数
    "session_cookie_name": "cth_poms_v4_session",
    # 密钥登录（替代短信验证码）：密钥正确即以主账号(owner)身份登录；可用环境变量 V4_ACCESS_KEY 覆盖
    "master_access_key": os.environ.get("V4_ACCESS_KEY", "张志宏"),
}

# 安全问答配置（主账号可在设置页修改）
DEFAULT_SECURITY_QUESTIONS = [
    {"id": "phone", "question": "手机号", "answer": "18504635216"},
    {"id": "birthday", "question": "生日", "answer": "1012"},
]

# 角色权限定义
ROLE_PERMISSIONS = {
    "owner": {  # 主账号
        "browse_all": True, "update_data": True, "add_topic": True,
        "add_event": True, "add_note": True, "receive_reports": True,
        "trigger_collect": True, "export_reports": True,
        "view_audit": True, "view_task_status": True,
        "manage_accounts": True, "manage_security": True,
        "system_config": True, "manage_modules": True,
        "delete_raw_data": True, "lock_config": True,
        "developer_access": True,
    },
    "admin": {  # 管理员(最多3个)
        "browse_all": True, "update_data": True, "add_topic": True,
        "add_event": True, "add_note": True, "receive_reports": True,
        "trigger_collect": True, "export_reports": True,
        "view_audit": True, "view_task_status": True,
        "manage_accounts": False, "manage_security": False,
        "system_config": False, "manage_modules": False,
        "delete_raw_data": False, "lock_config": False,
        "developer_access": False,
    },
    "user": {  # 普通账号
        "browse_all": False, "update_data": False, "add_topic": False,
        "add_event": False, "add_note": False, "receive_reports": True,
        "trigger_collect": False, "export_reports": True,
        "view_audit": False, "view_task_status": False,
        "manage_accounts": False, "manage_security": False,
        "system_config": False, "manage_modules": False,
        "delete_raw_data": False, "lock_config": False,
        "developer_access": False,
    },
}

# 采集适配器配置
ADAPTER_CONFIG = {
    "request_timeout": 30,
    "max_retries": 3,
    "retry_delay": 2,
    "circuit_breaker_threshold": 5,   # 连续失败5次触发熔断
    "circuit_breaker_reset": 300,     # 熔断恢复时间(秒)
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 外部导入配置
IMPORTER_CONFIG = {
    "max_file_size_mb": 500,  # 对齐 INGESTION_AND_TERMINOLOGY_STANDARD 500MB
    "allowed_extensions": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt"],
    "preview_limit": 100,  # 导入预览最多显示100条
}

# 兼容属性；路径选择由 Shared Database 唯一 owner 负责。
DB_PATH = main_db_path()

# 受限工作区（ZBMP）访问密钥配置
WORKSPACE_CONFIG = {
    "key_prefix": "zbmp_",          # 工作区密钥明文前缀
    "grant_hours": 12,              # unlock 成功后会话对该工作区的授权有效期(小时)
    "default_workspaces": ["CTH-POMS"],  # 默认即可进入、无需密钥的工作区
}
