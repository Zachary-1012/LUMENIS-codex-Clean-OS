#!/usr/bin/env python3
"""
广州太古汇舆情监测系统 v5.3.2 - 健康检查脚本

检查项：
1. Python 环境
2. 依赖包
3. 数据库连接
4. 数据库表结构
5. 数据统计
6. AI 状态
7. 端口占用
8. 磁盘空间

使用方式：
    python deployment/健康检查.py
"""
import os
import sys
import sqlite3
from datetime import datetime

# 切换到项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)


def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    ok = version >= (3, 8)
    return ok, f'Python {version.major}.{version.minor}.{version.micro}'


def check_dependencies():
    """检查依赖包"""
    required = ['flask', 'sqlite3']
    optional = ['playwright', 'requests']
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    ok = len(missing) == 0
    msg = '全部依赖正常' if ok else f'缺少: {", ".join(missing)}'
    return ok, msg


def check_database():
    """检查数据库连接和表结构"""
    try:
        import database as db
        db.init_db()
        with db.get_db() as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t['name'] for t in tables]
            required_tables = ['notes', 'daily_reports', 'events', 'web_mentions']
            missing = [t for t in required_tables if t not in table_names]
            if missing:
                return False, f'缺少表: {", ".join(missing)}'
            # v5.3.2 新表
            new_tables = ['ai_filter_log', 'daily_digest', 'event_insights']
            has_new = all(t in table_names for t in new_tables)
            # 统计数据
            total = conn.execute("SELECT COUNT(*) c FROM notes WHERE is_taikoo_verified=1").fetchone()['c']
            msg = f'数据库正常，共 {total} 条有效笔记'
            if has_new:
                msg += '，v5.3.2 新表已就绪'
            else:
                msg += '，v5.3.2 新表缺失（首次启动会自动创建）'
            return True, msg
    except Exception as e:
        return False, f'数据库检查失败: {e}'


def check_data_stats():
    """检查数据统计"""
    try:
        import database as db
        stats = db.get_stats()
        filter_stats = db.get_filter_stats()
        msg = (f'总{stats["total"]}条 | 正{stats["positive"]} 中{stats["neutral"]} 负{stats["negative"]} | '
               f'高风险{stats["high_risk"]} | AI过滤: 已通过{filter_stats["accepted"]} 待处理{filter_stats["pending"]}')
        return True, msg
    except Exception as e:
        return False, f'数据统计失败: {e}'


def check_ai_status():
    """检查 AI 状态"""
    try:
        import intelligence
        status = intelligence.ai_status()
        if status.get('enabled'):
            return True, f'AI已连接: {status.get("provider")} / {status.get("model")}'
        else:
            return True, f'AI未配置，使用本地规则引擎（{status.get("detail", "")}）'
    except Exception as e:
        return False, f'AI检查失败: {e}'


def check_port(port=8200):
    """检查端口是否被占用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                return True, f'端口 {port} 已被占用（系统可能正在运行）'
            else:
                return True, f'端口 {port} 空闲（可启动系统）'
    except Exception as e:
        return False, f'端口检查失败: {e}'


def check_disk_space():
    """检查磁盘空间"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(PROJECT_DIR)
        free_gb = free / (1024 ** 3)
        ok = free_gb > 1
        msg = f'磁盘剩余 {free_gb:.1f} GB'
        return ok, msg
    except Exception as e:
        return False, f'磁盘检查失败: {e}'


def main():
    print('=' * 60)
    print('  广州太古汇舆情监测系统 v5.3.2 - 健康检查')
    print(f'  检查时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    print()

    checks = [
        ('Python 环境', check_python),
        ('依赖包', check_dependencies),
        ('数据库', check_database),
        ('数据统计', check_data_stats),
        ('AI 状态', check_ai_status),
        ('端口 (8200)', check_port),
        ('磁盘空间', check_disk_space),
    ]

    passed = 0
    failed = 0
    for name, check_func in checks:
        try:
            ok, msg = check_func()
            status = '✅ 通过' if ok else '⚠️  警告'
            if ok:
                passed += 1
            else:
                failed += 1
            print(f'  {status}  {name:<12} {msg}')
        except Exception as e:
            failed += 1
            print(f'  ❌ 失败  {name:<12} 异常: {e}')

    print()
    print('=' * 60)
    print(f'  检查完成: {passed} 项通过, {failed} 项警告/失败')
    if failed == 0:
        print('  ✅ 系统状态良好，可以启动')
    else:
        print('  ⚠️  存在警告项，请检查后再启动')
    print('=' * 60)
    print()

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
