"""
设置模块完善 v1.0

[CURRENT COMPATIBILITY API / NOT RUNTIME CONFIGURATION AUTHORITY]
本模块仍由 app.py 注册以兼容现有设置接口，但运行时真相归当前 SYSTEM Owner：
Product Core、SYSTEM Collector、Owned AI Gateway、Permission 与受保护本机配置。
本模块只保存非运行时偏好；读取时必须重新投影当前 runtime-owned 字段。

功能：
1. 系统配置管理（采集/分析/报告/推送/AI/安全）
2. 账号管理（小红书账号/AI账号/邮件账号）
3. 域名/服务器接口配置
4. 开发者工具（代码执行/日志查看/数据库管理）
5. 系统信息（版本/运行时间/资源使用）
"""

import os
import sys
import json
import sqlite3
import platform
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from lumenis.shared.database import get_repository, main_db_path

# psutil可选
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

settings_bp = Blueprint('settings', __name__)

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'system_config.json')
DEVELOPER_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'logs', 'developer.log')


def load_config():
    """加载系统配置"""
    default_config = {
        'collection': {
            'auto_collect': os.getenv('REDNOTE_AUTO_RUN', 'false').lower() in ('1', 'true', 'yes', 'on'),
            'auto_hours': [8, 10, 12, 14, 16, 18, 20, 22, 23],
            'manual_daily_limit': 3,
            'request_delay': 2,
            'max_retries': 3,
            'max_scroll': 6
        },
        'analysis': {
            'ai_enabled': False,
            'sentiment_enabled': True,
            'event_classification': True,
            'brand_recognition': True,
            'auto_summary': True
        },
        'report': {
            'daily_enabled': True,
            'weekly_enabled': True,
            'monthly_enabled': True,
            'yearly_enabled': True,
            'export_format': ['word', 'excel'],
            'template_path': 'data/templates/'
        },
        'push': {
            'daily_popup': True,
            'email_enabled': False,
            'email_time': '09:00',
            'wechat_enabled': False,
            'high_risk_immediate': True
        },
        'ai': {
            'provider': 'owned',
            'local_enabled': False,
            'model': None,
            'service_binding': 'NOT_BOUND',
            'fallback_allowed': False,
            'status': 'UNAVAILABLE'
        },
        'security': {
            'http_auth': bool(os.getenv('TAIKOO_AUTH_USER', '').strip() and os.getenv('TAIKOO_AUTH_PASSWORD', '')),
            'auto_backup': True,
            'backup_interval_hours': 24,
            'file_integrity_check': True,
            'developer_mode': False
        },
        'domain': {
            'company_domain': '',
            'cloudflare_tunnel': '',
            'local_url': 'http://127.0.0.1:8201',
            'lan_url': ''
        }
    }

    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            # 深度合并
            for key, value in user_config.items():
                if key in default_config and isinstance(value, dict) and isinstance(default_config[key], dict):
                    default_config[key].update(value)
                else:
                    default_config[key] = value
    except Exception as e:
        print(f"[Settings] 加载配置失败: {e}", flush=True)

    # Compatibility file values never own current runtime truth. Project AI,
    # canonical Core port, Basic-auth presence and automatic collection state
    # are projected from their current owners every time this legacy API reads.
    try:
        from lumenis.system.ai_gateway.core import owned_inference_status
        owned = owned_inference_status()
    except Exception as exc:
        owned = {
            'available': False,
            'service_binding': 'NOT_BOUND',
            'state': 'UNAVAILABLE',
            'reason': type(exc).__name__,
            'model_id': None,
        }
    ai_available = (
        owned.get('available') is True and owned.get('service_binding') == 'BOUND'
    )
    default_config['collection']['auto_collect'] = (
        os.getenv('REDNOTE_AUTO_RUN', 'false').lower() in ('1', 'true', 'yes', 'on')
    )
    default_config['analysis']['ai_enabled'] = ai_available
    default_config['ai'] = {
        'provider': 'owned',
        'local_enabled': False,
        'model': owned.get('model_id'),
        'service_binding': owned.get('service_binding') or 'NOT_BOUND',
        'fallback_allowed': False,
        'status': owned.get('state') or ('AVAILABLE' if ai_available else 'UNAVAILABLE'),
        'reason': owned.get('reason'),
    }
    default_config['security']['http_auth'] = bool(
        os.getenv('TAIKOO_AUTH_USER', '').strip()
        and os.getenv('TAIKOO_AUTH_PASSWORD', '')
    )
    default_config['domain']['local_url'] = 'http://127.0.0.1:8201'

    return default_config


def save_config(config):
    """保存系统配置"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Settings] 保存配置失败: {e}", flush=True)
        return False


# ============================================
# 配置管理API
# ============================================

@settings_bp.route('/api/settings/config')
def get_config():
    """获取系统配置"""
    try:
        config = load_config()
        return jsonify({'ok': True, 'config': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/config', methods=['POST'])
def update_config():
    """更新系统配置"""
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({'ok': False, 'error': '配置必须是对象'}), 400
        config = load_config()
        ignored = []

        # This legacy settings file may persist user preferences only. Runtime
        # owners keep AI routing, collection activation, Basic auth and Core URL.
        incoming = dict(data)
        if 'ai' in incoming:
            ignored.append('ai')
            incoming.pop('ai', None)
        if isinstance(incoming.get('collection'), dict) and 'auto_collect' in incoming['collection']:
            incoming['collection'] = dict(incoming['collection'])
            incoming['collection'].pop('auto_collect', None)
            ignored.append('collection.auto_collect')
        if isinstance(incoming.get('security'), dict) and 'http_auth' in incoming['security']:
            incoming['security'] = dict(incoming['security'])
            incoming['security'].pop('http_auth', None)
            ignored.append('security.http_auth')
        if isinstance(incoming.get('domain'), dict) and 'local_url' in incoming['domain']:
            incoming['domain'] = dict(incoming['domain'])
            incoming['domain'].pop('local_url', None)
            ignored.append('domain.local_url')

        for key, value in incoming.items():
            if key in config and isinstance(value, dict) and isinstance(config[key], dict):
                config[key].update(value)
            else:
                config[key] = value

        if save_config(config):
            return jsonify({
                'ok': True,
                'message': '配置已保存',
                'ignored_runtime_owned_fields': ignored,
            })
        else:
            return jsonify({'ok': False, 'error': '保存失败'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 系统信息API
# ============================================

@settings_bp.route('/api/settings/system-info')
def system_info():
    """获取系统信息"""
    try:
        # 数据库统计
        db_path = main_db_path()
        db_size = os.path.getsize(db_path) / 1024 / 1024 if os.path.exists(db_path) else 0

        conn = get_repository().connect(timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes")
        notes_count = c.fetchone()[0]
        c.execute("SELECT MAX(collected_at) FROM notes")
        last_collect = c.fetchone()[0]
        conn.close()

        # 系统资源
        if HAS_PSUTIL:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            resources = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': round(memory.used / 1024 / 1024, 1),
                'memory_total_mb': round(memory.total / 1024 / 1024, 1),
                'disk_percent': disk.percent,
                'disk_used_gb': round(disk.used / 1024 / 1024 / 1024, 1),
                'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 1)
            }
        else:
            resources = {'cpu_percent': 0, 'memory_percent': 0, 'note': 'psutil未安装'}
            uptime = '未知'

        return jsonify({
            'ok': True,
            'system': {
                'version': 'v5.9.0',
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'uptime': str(uptime).split('.')[0]
            },
            'database': {
                'notes_count': notes_count,
                'last_collect': last_collect,
                'size_mb': round(db_size, 2)
            },
            'resources': resources
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 开发者工具API
# ============================================

@settings_bp.route('/api/settings/developer/execute', methods=['POST'])
def developer_execute():
    """开发者工具 - 执行代码（需开发者模式）"""
    try:
        config = load_config()
        if not config.get('security', {}).get('developer_mode', False):
            return jsonify({'ok': False, 'error': '开发者模式未开启'}), 403

        data = request.get_json(silent=True) or {}
        code = data.get('code', '')

        if not code:
            return jsonify({'ok': False, 'error': '代码不能为空'})

        # 记录日志
        os.makedirs(os.path.dirname(DEVELOPER_LOG_FILE), exist_ok=True)
        with open(DEVELOPER_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行代码:\n{code}\n\n")

        # 执行代码（安全限制：只允许特定操作）
        try:
            local_vars = {}
            exec(code, {'__builtins__': {}}, local_vars)
            return jsonify({'ok': True, 'result': str(local_vars)})
        except Exception as e:
            return jsonify({'ok': False, 'error': f'执行错误: {str(e)}'})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/developer/logs')
def developer_logs():
    """获取开发者日志"""
    try:
        if os.path.exists(DEVELOPER_LOG_FILE):
            with open(DEVELOPER_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = f.read()[-5000:]  # 最后5000字符
            return jsonify({'ok': True, 'logs': logs})
        return jsonify({'ok': True, 'logs': ''})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 域名/服务器接口API
# ============================================

@settings_bp.route('/api/settings/domain')
def get_domain_config():
    """获取域名配置"""
    try:
        config = load_config()
        return jsonify({'ok': True, 'domain': config.get('domain', {})})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/domain', methods=['POST'])
def update_domain_config():
    """更新域名配置"""
    try:
        data = request.get_json(silent=True) or {}
        config = load_config()
        if 'domain' not in config:
            config['domain'] = {}
        config['domain'].update(data)
        if save_config(config):
            return jsonify({'ok': True, 'message': '域名配置已保存'})
        return jsonify({'ok': False, 'error': '保存失败'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/domain/delete', methods=['POST'])
def delete_domain_config():
    """删除域名配置"""
    try:
        data = request.get_json(silent=True) or {}
        key = data.get('key', '')
        config = load_config()
        if key in config.get('domain', {}):
            del config['domain'][key]
            save_config(config)
            return jsonify({'ok': True, 'message': f'已删除 {key}'})
        return jsonify({'ok': False, 'error': '配置项不存在'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


print("[Settings] 设置模块已加载", flush=True)
