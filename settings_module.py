"""
设置模块完善 v1.0
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
            'auto_collect': True,
            'auto_hours': [8, 10, 12, 14, 16, 18, 20, 22, 23],
            'manual_daily_limit': 3,
            'request_delay': 2,
            'max_retries': 3,
            'max_scroll': 6
        },
        'analysis': {
            'ai_enabled': True,
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
            'provider': 'local',
            'local_enabled': True,
            'doubao_api_key': '',
            'gpt_api_key': '',
            'trae_api_key': '',
            'model': 'qwen2:7b'
        },
        'security': {
            'http_auth': True,
            'auto_backup': True,
            'backup_interval_hours': 24,
            'file_integrity_check': True,
            'developer_mode': False
        },
        'domain': {
            'company_domain': '',
            'cloudflare_tunnel': '',
            'local_url': 'http://127.0.0.1:8200',
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
        # 隐藏敏感信息
        if 'ai' in config:
            for key in ['doubao_api_key', 'gpt_api_key', 'trae_api_key']:
                if config['ai'].get(key):
                    config['ai'][key] = '***' + config['ai'][key][-4:] if len(config['ai'][key]) > 4 else '***'
        return jsonify({'ok': True, 'config': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/config', methods=['POST'])
def update_config():
    """更新系统配置"""
    try:
        data = request.get_json(silent=True) or {}
        config = load_config()

        # 合并配置
        for key, value in data.items():
            if key in config and isinstance(value, dict) and isinstance(config[key], dict):
                config[key].update(value)
            else:
                config[key] = value

        # 处理API Key（如果是***开头则不更新）
        if 'ai' in data:
            for key in ['doubao_api_key', 'gpt_api_key', 'trae_api_key']:
                if key in data['ai'] and data['ai'][key] and not data['ai'][key].startswith('***'):
                    config['ai'][key] = data['ai'][key]

        if save_config(config):
            return jsonify({'ok': True, 'message': '配置已保存'})
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
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')
        db_size = os.path.getsize(db_path) / 1024 / 1024 if os.path.exists(db_path) else 0

        conn = sqlite3.connect(db_path, timeout=5)
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
