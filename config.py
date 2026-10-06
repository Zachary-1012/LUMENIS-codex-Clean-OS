"""
LUMENIS compatibility configuration adapter
统一.env配置，避免硬编码

使用方法：
    from config import get_config
    
    config = get_config()
    db_path = config.get('DATABASE_PATH')
    api_key = config.get('AI_API_KEY')
"""

import os
import json
from typing import Any, Optional, Dict
from dotenv import load_dotenv

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
ENV_FILE = os.path.join(BASE_DIR, '.env')
ENV_EXAMPLE_FILE = os.path.join(BASE_DIR, '.env.example')
SYSTEM_CONFIG_FILE = os.path.join(BASE_DIR, 'system_config.json')

# 全局配置缓存
_config = None
_config_loaded = False


def load_env():
    """加载.env文件"""
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE, override=True)
    elif os.path.exists(ENV_EXAMPLE_FILE):
        load_dotenv(ENV_EXAMPLE_FILE, override=True)


def load_system_config() -> Dict[str, Any]:
    """加载系统配置JSON文件"""
    if os.path.exists(SYSTEM_CONFIG_FILE):
        try:
            with open(SYSTEM_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  加载系统配置失败: {e}")
    return {}


def get_config(force_reload: bool = False) -> 'Config':
    """
    获取配置单例
    
    Args:
        force_reload: 是否强制重新加载
    
    Returns:
        Config 实例
    """
    global _config, _config_loaded
    
    if _config is None or force_reload or not _config_loaded:
        _config = Config()
        _config_loaded = True
    
    return _config


class Config:
    """配置管理类"""

    # 内置默认值（Track1 补齐：关键配置项在 .env 缺失时不返回 None）
    _DEFAULTS = {
        'APP_HOST': '0.0.0.0',
        'APP_PORT': 8200,
        'APP_DEBUG': False,
        'DATABASE_PATH': 'data/monitor.db',
        'AI_PROVIDER': 'auto',
        'AI_TIMEOUT_SECONDS': 90,
        'AI_LOCAL_ENABLED': False,
        'LOG_LEVEL': 'INFO',
        'COLLECTION_DAILY_LIMIT': 50,
        'COLLECTION_MANUAL_LIMIT': 20,
        'COLLECTION_AUTO_LIMIT': 30,
        'COLLECTION_COOLDOWN_MINUTES': 5,
        'AUTO_INTERVAL_MINUTES': 90,
        'DAILY_REPORT_HOUR': 9,
        'TAIKOO_HOST': '0.0.0.0',
        'TAIKOO_PORT': 8200,
        'TAIKOO_AUTH_USER': 'admin',
        'COMPANY_DOMAIN_ENABLED': False,
        'NOTIFICATION_DEDUP_TTL': 300,
        'NOTIFICATION_MAX_RETRIES': 3,
        'ZBC_SCHED_GATE_MODE': 'shadow',
        'ALLOW_CLOUD_AI': True,
        'LOCAL_AI_PREFERRED': False,
    }

    def __init__(self):
        """初始化配置"""
        load_env()
        self._system_config = load_system_config()
        self._env_overrides = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        优先级：环境变量覆盖 > 系统配置JSON > 默认值
        
        Args:
            key: 配置键名
            default: 默认值
        
        Returns:
            配置值
        """
        # 1. 检查环境变量覆盖
        if key in self._env_overrides:
            return self._env_overrides[key]
        
        # 2. 检查环境变量
        env_value = os.environ.get(key)
        if env_value is not None:
            return self._parse_value(env_value)
        
        # 3. 检查系统配置JSON（支持嵌套键，如 server.host）
        json_value = self._get_nested_value(key)
        if json_value is not None:
            return json_value
        
        # 4. 检查内置默认值
        if key in self._DEFAULTS:
            return self._DEFAULTS[key]

        # 5. 返回传入的兜底默认值
        return default
    
    def _get_nested_value(self, key: str) -> Any:
        """获取嵌套配置值"""
        if '.' in key:
            parts = key.split('.')
            value = self._system_config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return value
        else:
            return self._system_config.get(key)
    
    def _parse_value(self, value: str) -> Any:
        """解析配置值（字符串转对应类型）"""
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        if value.lower() in ('null', 'none', ''):
            return None
        
        # 尝试解析数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # 尝试解析JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
        
        return value
    
    def set(self, key: str, value: Any):
        """
        临时设置配置值（运行时覆盖，不保存到文件）
        
        Args:
            key: 配置键名
            value: 配置值
        """
        self._env_overrides[key] = value
    
    def save_to_env(self, key: str, value: Any):
        """
        保存配置到.env文件
        
        Args:
            key: 配置键名
            value: 配置值
        """
        # 读取现有.env内容
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        # 查找并替换或追加
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f'{key}=') or line.strip().startswith(f'#{key}='):
                new_lines.append(f'{key}={value}\n')
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f'{key}={value}\n')
        
        # 写回.env文件
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        # 重新加载
        load_env()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置（合并环境变量和系统配置）"""
        all_config = {}
        
        # 系统配置
        all_config.update(self._system_config)
        
        # 环境变量（只包含已知的配置键）
        known_keys = self.get_known_keys()
        for key in known_keys:
            value = os.environ.get(key)
            if value is not None:
                all_config[key] = self._parse_value(value)
        
        # 运行时覆盖
        all_config.update(self._env_overrides)
        
        return all_config
    
    def get_known_keys(self) -> list:
        """获取已知的配置键列表（2026-09-06 Phase 16 全量补齐）"""
        return [
            # 服务器配置
            'APP_HOST', 'APP_PORT', 'APP_DEBUG',
            'TAIKOO_HOST', 'TAIKOO_PORT',
            'TAIKOO_AUTH_USER', 'TAIKOO_AUTH_PASSWORD',
            'TAIKOO_COMPANY_DOMAIN', 'TAIKOO_COMPANY_NAME',
            # 数据库配置
            'DATABASE_PATH',
            # AI 配置（Provider-Agnostic）
            'AI_PROVIDER', 'AI_MODEL', 'AI_API_KEY',
            'AI_LOCAL_ENDPOINT', 'AI_LOCAL_ENABLED', 'AI_ASYNC_ENABLED',
            'AI_TIMEOUT_SECONDS', 'ALLOW_CLOUD_AI', 'LOCAL_AI_PREFERRED',
            # 本地 AI Runtime
            'OLLAMA_BASE_URL', 'OLLAMA_MODEL',
            'LMSTUDIO_BASE_URL', 'LMSTUDIO_MODEL',
            'LLAMA_CPP_BASE_URL', 'LLAMA_CPP_MODEL',
            # 云端 AI Provider
            'ZHIPU_API_KEY', 'ZHIPU_MODEL', 'ZHIPU_STRONG_MODEL', 'ZHIPU_BASE_URL',
            'DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL', 'QWEN_MODEL',
            'OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_PROXY',
            'DEEPSEEK_API_KEY', 'DEEPSEEK_MODEL',
            'ARK_API_KEY', 'ARK_MODEL', 'ARK_BASE_URL', 'ARK_MAX_DAILY_TOKEN',
            # 采集配置
            'COLLECTION_DAILY_LIMIT', 'COLLECTION_MANUAL_LIMIT',
            'COLLECTION_AUTO_LIMIT', 'COLLECTION_COOLDOWN_MINUTES',
            'AUTO_INTERVAL_MINUTES', 'DAILY_REPORT_HOUR',
            # 全网话题采集
            'WEB_ADAPTERS', 'WEB_BASE_QUERY', 'WEB_RSS_URLS', 'WEB_QUERIES',
            'TAIKOO_WEB_DISCOVERY', 'TAIKOO_WEB_DISCOVERY_TIMEOUT',
            # 小红书配置
            'XHS_CDP_URL', 'XHS_COOKIE_FILE', 'XHS_COOKIE', 'XHS_PROFILE_DIR',
            'XHS_CN_CDP_URL', 'XHS_HK_CDP_URL',
            # 凭证 / Cookie
            'ZBC_WEIBO_COOKIE_JSON', 'ZBC_BILI_COOKIE_JSON',
            'ZBC_API_KEY', 'V4_ACCESS_KEY',
            # 邮件配置（EMAIL_* 旧版 + SMTP_* 新版并存）
            'EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT', 'EMAIL_SMTP_USER',
            'EMAIL_SMTP_PASSWORD', 'EMAIL_FROM', 'EMAIL_TO',
            'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD',
            'SMTP_FROM', 'SMTP_SSL',
            # 公司域名
            'COMPANY_DOMAIN', 'COMPANY_DOMAIN_ENABLED',
            # 微信通知
            'WECOM_WEBHOOK_URL', 'SERVERCHAN_SEND_KEY', 'PUSHPLUS_TOKEN',
            'WECHAT_APP_ID', 'WECHAT_APP_SECRET', 'WECHAT_TEMPLATE_ID',
            'WECHAT_RECEIVER_OPENIDS',
            'NOTIFICATION_DEDUP_TTL', 'NOTIFICATION_MAX_RETRIES',
            'NOTIFICATION_HIGH_RISK_PUSH', 'NOTIFICATION_CRITICAL_PUSH',
            'NOTIFICATION_SYSTEM_ERROR_PUSH', 'NOTIFICATION_COLLECTION_FAILED_PUSH',
            'NOTIFICATION_LOGIN_EXPIRED_PUSH', 'NOTIFICATION_DAILY_REPORT_PUSH',
            'NOTIFICATION_WEEKLY_REPORT_PUSH',
            # 动态调度门控
            'ZBC_SCHED_GATE_MODE', 'ZBC_SCHED_GATE_PLATFORMS',
            # Repository Registry 路径
            'ZBC_REPO_ROOT', 'ZBC_CORE_DIR', 'ZBC_DATA_DIR', 'ZBC_RUNTIME_DIR',
            'ZBC_BACKUP_DIR', 'ZBC_EXPORT_DIR', 'ZBC_TEMP_DIR',
            'ZBC_AI_RUNTIME_DIR', 'ZBC_COLLECTOR_DIR', 'ZBC_LOG_DIR',
            'ZBC_CONFIG_DIR',
            # 日志 / Cloudflare
            'LOG_LEVEL', 'LOG_DIR',
            'CLOUDFLARED_PATH', 'CLOUDFLARE_TUNNEL_URL',
        ]
    
    def validate(self) -> Dict[str, Any]:
        """
        验证配置完整性
        
        Returns:
            验证结果字典
        """
        result = {
            'valid': True,
            'missing': [],
            'warnings': [],
            'details': {}
        }
        
        # 检查必需配置
        required_keys = ['APP_HOST', 'APP_PORT', 'DATABASE_PATH']
        for key in required_keys:
            if self.get(key) is None:
                result['missing'].append(key)
                result['valid'] = False
        
        # 检查认证配置
        if self.get('TAIKOO_AUTH_USER') is None:
            result['warnings'].append('TAIKOO_AUTH_USER 未设置，将使用默认认证')
        if self.get('TAIKOO_AUTH_PASSWORD') is None:
            result['warnings'].append('TAIKOO_AUTH_PASSWORD 未设置，将使用默认认证')
        
        # 检查AI配置
        if self.get('AI_API_KEY') is None and self.get('AI_LOCAL_ENABLED') is not True:
            result['warnings'].append('AI_API_KEY 未设置且本地AI未启用，AI分析功能可能不可用')
        
        # 检查邮件配置
        email_keys = ['EMAIL_SMTP_HOST', 'EMAIL_SMTP_USER', 'EMAIL_SMTP_PASSWORD']
        if any(self.get(k) is None for k in email_keys):
            result['warnings'].append('邮件配置不完整，日报推送功能可能不可用')
        
        result['details']['total_keys'] = len(self.get_known_keys())
        result['details']['configured_keys'] = sum(
            1 for k in self.get_known_keys() if self.get(k) is not None
        )
        
        return result
    
    def reload(self):
        """重新加载配置"""
        load_env()
        self._system_config = load_system_config()
        self._env_overrides.clear()


def get_config_value(key: str, default: Any = None) -> Any:
    """便捷函数：获取配置值"""
    return get_config().get(key, default)


def set_config_value(key: str, value: Any):
    """便捷函数：临时设置配置值"""
    get_config().set(key, value)


def save_config_value(key: str, value: Any):
    """便捷函数：保存配置到.env文件"""
    get_config().save_to_env(key, value)


def validate_config() -> Dict[str, Any]:
    """便捷函数：验证配置完整性"""
    return get_config().validate()


if __name__ == '__main__':
    # 测试配置系统
    print("=" * 60)
    print("📊 配置系统测试")
    print("=" * 60)
    
    config = get_config()
    
    # 显示基本配置
    print(f"\n🏠 服务器配置:")
    print(f"  HOST: {config.get('APP_HOST', '0.0.0.0')}")
    print(f"  PORT: {config.get('APP_PORT', 8200)}")
    
    print(f"\n💾 数据库配置:")
    print(f"  PATH: {config.get('DATABASE_PATH', 'data/monitor.db')}")
    
    print(f"\n🤖 AI配置:")
    print(f"  PROVIDER: {config.get('AI_PROVIDER', '未设置')}")
    print(f"  LOCAL_ENABLED: {config.get('AI_LOCAL_ENABLED', False)}")
    
    # 验证配置
    print(f"\n✅ 配置验证:")
    validation = config.validate()
    print(f"  有效: {validation['valid']}")
    print(f"  缺失: {validation['missing']}")
    print(f"  警告: {len(validation['warnings'])} 条")
    for warning in validation['warnings']:
        print(f"    ⚠️  {warning}")
    
    print(f"\n📊 配置统计:")
    print(f"  总配置键: {validation['details']['total_keys']}")
    print(f"  已配置: {validation['details']['configured_keys']}")
    
    print("\n✅ 配置系统测试完成")
