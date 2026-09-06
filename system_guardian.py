"""
系统稳定性监控模块 v1.0
功能：
1. 全局异常捕获和记录
2. 系统健康检查
3. 自动恢复机制
4. 性能监控

[LEGACY NOTICE - ZBC Phase 2 Runtime Guardian 统一收敛]
本模块已由 runtime_guardian.py 接管为统一生命周期守护者。
保留全部原有函数与行为（向后兼容），health_check() 内部同步委托给
RuntimeGuardian 记录状态；新代码请直接使用 runtime_guardian.RuntimeGuardian。
不删除本文件，保持 import 兼容。
收敛工单：ZBC-PHASE2-RUNTIME-GUARDIAN-001
"""

import os
import sys
import time
import json
import logging
import traceback
from datetime import datetime
from functools import wraps

# Runtime Guardian 委托层（延迟导入，避免循环依赖；失败不阻断原模块）
_RUNTIME_GUARDIAN = None
try:
    from runtime_guardian import get_guardian as _rg_get_guardian
    _RUNTIME_GUARDIAN = _rg_get_guardian("system_guardian_legacy")
except Exception:
    _RUNTIME_GUARDIAN = None

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'system.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SystemGuardian')

# 系统状态文件
STATUS_FILE = os.path.join(LOG_DIR, 'system_status.json')

# 错误统计
ERROR_STATS = {
    'total_errors': 0,
    'errors_by_type': {},
    'last_error': None,
    'last_error_time': None,
    'system_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'restart_count': 0
}


def load_status():
    """加载系统状态"""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return ERROR_STATS.copy()


def save_status(status):
    """保存系统状态"""
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存系统状态失败: {e}")


def global_exception_handler(func):
    """全局异常捕获装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            error_trace = traceback.format_exc()

            # 记录错误
            status = load_status()
            status['total_errors'] += 1
            status['errors_by_type'][error_type] = status['errors_by_type'].get(error_type, 0) + 1
            status['last_error'] = f"{error_type}: {error_msg}"
            status['last_error_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_status(status)

            # 委托 RuntimeGuardian 记录（不阻断原行为）
            try:
                if _RUNTIME_GUARDIAN:
                    _wid = _RUNTIME_GUARDIAN.register_worker(f"legacy_{func.__name__}")
                    _RUNTIME_GUARDIAN._update_worker_fields(
                        _wid,
                        failure_count=1,
                        recovery_reason=f"{error_type}: {error_msg}",
                    )
            except Exception:
                pass

            # 记录日志
            logger.error(f"函数 {func.__name__} 发生异常: {error_type}: {error_msg}")
            logger.error(f"堆栈信息:\n{error_trace}")

            # 尝试自动恢复
            try:
                recovery_result = auto_recovery(func, e, args, kwargs)
                if recovery_result:
                    logger.info(f"自动恢复成功: {func.__name__}")
                    return recovery_result
            except Exception as recovery_error:
                logger.error(f"自动恢复失败: {recovery_error}")

            raise
    return wrapper


def auto_recovery(func, error, args, kwargs):
    """自动恢复机制"""
    error_type = type(error).__name__

    # 数据库连接错误 - 重试
    if 'OperationalError' in error_type or 'DatabaseError' in error_type:
        logger.info(f"数据库错误，尝试重试...")
        time.sleep(1)
        try:
            return func(*args, **kwargs)
        except Exception:
            return None

    # 文件不存在错误 - 创建默认文件
    if 'FileNotFoundError' in error_type:
        logger.info(f"文件不存在，尝试创建默认文件...")
        try:
            file_path = str(error.filename) if hasattr(error, 'filename') else ''
            if file_path and not os.path.exists(file_path):
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('{}')
                return func(*args, **kwargs)
        except Exception:
            return None

    return None


def health_check():
    """系统健康检查（Legacy：保留原返回格式，内部同步委托 RuntimeGuardian）"""
    checks = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'healthy',
        'checks': {}
    }

    # 检查数据库
    try:
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notes")
        notes_count = c.fetchone()[0]
        conn.close()
        checks['checks']['database'] = {'status': 'ok', 'notes_count': notes_count}
    except Exception as e:
        checks['checks']['database'] = {'status': 'error', 'message': str(e)}
        checks['status'] = 'degraded'

    # 检查磁盘空间
    try:
        import shutil
        total, used, free = shutil.disk_usage(os.path.dirname(os.path.abspath(__file__)))
        free_gb = round(free / (1024**3), 2)
        checks['checks']['disk'] = {'status': 'ok' if free_gb > 1 else 'warning', 'free_gb': free_gb}
        if free_gb < 1:
            checks['status'] = 'degraded'
    except Exception as e:
        checks['checks']['disk'] = {'status': 'error', 'message': str(e)}

    # 检查错误统计
    status = load_status()
    checks['error_stats'] = {
        'total_errors': status.get('total_errors', 0),
        'last_error': status.get('last_error'),
        'last_error_time': status.get('last_error_time'),
        'system_start_time': status.get('system_start_time'),
        'restart_count': status.get('restart_count', 0)
    }

    # 如果最近1小时内错误超过10个，标记为不健康
    if status.get('total_errors', 0) > 50:
        checks['status'] = 'unhealthy'

    # 委托 RuntimeGuardian 同步记录（不阻断原返回）
    try:
        if _RUNTIME_GUARDIAN:
            _rg_health = _RUNTIME_GUARDIAN.health_check()
            checks['runtime_guardian'] = _rg_health
    except Exception:
        pass

    return checks


def get_system_logs(limit=50, level='ERROR'):
    """获取系统日志"""
    log_file = os.path.join(LOG_DIR, 'system.log')
    if not os.path.exists(log_file):
        return []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 过滤指定级别
        filtered = [line.strip() for line in lines if level in line]
        return filtered[-limit:]
    except Exception as e:
        logger.error(f"读取日志失败: {e}")
        return []


def cleanup_old_logs(days=7):
    """清理旧日志"""
    try:
        now = time.time()
        for filename in os.listdir(LOG_DIR):
            filepath = os.path.join(LOG_DIR, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > days * 86400:
                    os.remove(filepath)
                    logger.info(f"清理旧日志: {filename}")
    except Exception as e:
        logger.error(f"清理日志失败: {e}")


# 初始化时记录启动
logger.info("=" * 50)
logger.info("系统稳定性监控模块已启动")
logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info("=" * 50)

# 加载历史状态
_status = load_status()
_status['restart_count'] = _status.get('restart_count', 0) + 1
_status['system_start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
save_status(_status)
