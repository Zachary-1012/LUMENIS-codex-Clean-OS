"""
广州太古汇舆情监测系统 - 统一日志系统
便于排查问题，统一日志格式和管理

使用方法：
    from logger import get_logger
    
    logger = get_logger('app')
    logger.info('系统启动')
    logger.error('采集失败', exc_info=True)
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')

# 日志格式
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日志级别
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

# 全局日志器缓存
_loggers = {}


def ensure_log_dir():
    """确保日志目录存在"""
    os.makedirs(LOG_DIR, exist_ok=True)


def get_log_level() -> int:
    """获取日志级别（从环境变量或默认）"""
    level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
    return LOG_LEVELS.get(level_str, logging.INFO)


def create_file_handler(
    log_file: str,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: int = logging.DEBUG
) -> RotatingFileHandler:
    """创建按大小轮转的文件日志处理器"""
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, log_file)
    
    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    return handler


def create_timed_file_handler(
    log_file: str,
    when: str = 'midnight',
    interval: int = 1,
    backup_count: int = 30,
    level: int = logging.INFO
) -> TimedRotatingFileHandler:
    """创建按时间轮转的文件日志处理器"""
    ensure_log_dir()
    log_path = os.path.join(LOG_DIR, log_file)
    
    handler = TimedRotatingFileHandler(
        log_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    handler.suffix = '%Y%m%d'
    return handler


def create_console_handler(level: int = logging.INFO) -> logging.StreamHandler:
    """创建控制台日志处理器"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    return handler


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[int] = None,
    console: bool = True,
    file: bool = True
) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
        log_file: 日志文件名（默认: {name}.log）
        level: 日志级别（默认: 从环境变量获取或INFO）
        console: 是否输出到控制台
        file: 是否输出到文件
    
    Returns:
        logging.Logger 实例
    """
    global _loggers
    
    if name in _loggers:
        return _loggers[name]
    
    if level is None:
        level = get_log_level()
    
    if log_file is None:
        log_file = f'{name}.log'
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 控制台输出
    if console:
        logger.addHandler(create_console_handler(level))
    
    # 文件输出（按大小轮转）
    if file:
        logger.addHandler(create_file_handler(log_file, level=logging.DEBUG))
    
    _loggers[name] = logger
    return logger


def get_app_logger() -> logging.Logger:
    """获取应用主日志器"""
    return get_logger('app', 'app.log')


def get_collector_logger() -> logging.Logger:
    """获取采集器日志器"""
    return get_logger('collector', 'collector.log')


def get_ai_logger() -> logging.Logger:
    """获取AI分析日志器"""
    return get_logger('ai', 'ai.log')


def get_report_logger() -> logging.Logger:
    """获取报告生成日志器"""
    return get_logger('report', 'report.log')


def get_error_logger() -> logging.Logger:
    """获取错误日志器（仅记录ERROR及以上）"""
    logger = get_logger('error', 'error.log', level=logging.ERROR, console=False)
    return logger


def log_exception(logger: logging.Logger, message: str, exc: Exception):
    """
    统一异常日志记录
    
    Args:
        logger: 日志器
        message: 错误消息
        exc: 异常对象
    """
    logger.error(f"{message}: {type(exc).__name__}: {str(exc)}", exc_info=True)


def cleanup_old_logs(days: int = 30):
    """
    清理旧日志文件
    
    Args:
        days: 保留天数（默认30天）
    """
    ensure_log_dir()
    
    now = datetime.now()
    cleaned = 0
    
    for filename in os.listdir(LOG_DIR):
        filepath = os.path.join(LOG_DIR, filename)
        
        if not os.path.isfile(filepath):
            continue
        
        # 跳过当前正在使用的日志文件
        if not filename.endswith('.log') and '.log.' not in filename:
            continue
        
        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        age_days = (now - file_time).days
        
        if age_days > days:
            try:
                os.remove(filepath)
                cleaned += 1
                print(f"🗑️  已删除旧日志: {filename} ({age_days}天前)")
            except Exception as e:
                print(f"⚠️  删除日志失败 {filename}: {e}")
    
    print(f"✅ 日志清理完成，共删除 {cleaned} 个旧日志文件")


def get_log_summary() -> dict:
    """获取日志摘要信息"""
    ensure_log_dir()
    
    summary = {
        'log_dir': LOG_DIR,
        'total_files': 0,
        'total_size': 0,
        'files': []
    }
    
    for filename in sorted(os.listdir(LOG_DIR)):
        filepath = os.path.join(LOG_DIR, filename)
        
        if not os.path.isfile(filepath):
            continue
        
        size = os.path.getsize(filepath)
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        summary['files'].append({
            'name': filename,
            'size': size,
            'size_mb': round(size / 1024 / 1024, 2),
            'modified': mtime.isoformat()
        })
        summary['total_files'] += 1
        summary['total_size'] += size
    
    summary['total_size_mb'] = round(summary['total_size'] / 1024 / 1024, 2)
    return summary


# 初始化默认日志器
_default_logger = None


def get_default_logger() -> logging.Logger:
    """获取默认日志器"""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_app_logger()
    return _default_logger


# 便捷函数
def info(message: str, *args, **kwargs):
    """记录INFO级别日志"""
    get_default_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """记录WARNING级别日志"""
    get_default_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """记录ERROR级别日志"""
    get_default_logger().error(message, *args, **kwargs)


def debug(message: str, *args, **kwargs):
    """记录DEBUG级别日志"""
    get_default_logger().debug(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """记录CRITICAL级别日志"""
    get_default_logger().critical(message, *args, **kwargs)


if __name__ == '__main__':
    # 测试日志系统
    print("=" * 60)
    print("📊 日志系统测试")
    print("=" * 60)
    
    logger = get_app_logger()
    logger.debug("这是DEBUG日志")
    logger.info("这是INFO日志")
    logger.warning("这是WARNING日志")
    logger.error("这是ERROR日志")
    
    print("\n✅ 日志系统测试完成")
    print(f"📁 日志目录: {LOG_DIR}")
    
    # 显示日志摘要
    summary = get_log_summary()
    print(f"\n📊 日志摘要:")
    print(f"  总文件数: {summary['total_files']}")
    print(f"  总大小: {summary['total_size_mb']} MB")
