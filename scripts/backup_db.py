"""
数据库备份脚本
版本: v5.8.0
"""

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path

from lumenis.shared.database import migrations

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'monitor.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'data', 'backups')


def verify_backup(backup_path):
    """备份完整性校验：只读打开备份，确认核心表存在且可读（WAL 下 backup API 本就一致，双保险）。"""
    import sqlite3 as _sq
    try:
        backup_uri = f'{Path(backup_path).resolve().as_uri()}?mode=ro'
        con = _sq.connect(backup_uri, uri=True, timeout=10)
        try:
            tabs = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            core = {'notes', 'events', 'daily_reports', 'collection_logs', 'metric_snapshots'}
            missing = core - tabs
            # Full read-only integrity check complements the Shared Database snapshot.
            qc_rows = [row[0] for row in con.execute('PRAGMA integrity_check').fetchall()]
            qc = qc_rows[0] if len(qc_rows) == 1 else ' | '.join(qc_rows)
            ok = (qc_rows == ['ok']) and not missing
            return {'ok': ok, 'tables': len(tabs), 'missing': sorted(missing), 'quick_check': qc}
        finally:
            con.close()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def backup_database(backup_name=None):
    """备份数据库"""
    print("=== 数据库备份 ===")

    try:
        backup_path = migrations.backup_database(backup_name)
    except Exception as e:
        print(f"[ERROR] 备份失败: {e}")
        return None

    # Business-required tables stay at the script boundary; the shared owner
    # validates SQLite integrity for both product and minimal disposable DBs.
    v = verify_backup(backup_path)
    if not v.get('ok'):
        print(f"[ERROR] 备份校验失败: {v}")
        try:
            os.remove(backup_path)
        except OSError as e:
            print(f"[ERROR] 无法清理本次未通过业务校验的快照: {e}")
        return None
    print(f"[OK] SQLite Online Backup API 备份成功: {backup_path}")
    print(f"   校验OK: 表数={v.get('tables')} 缺失={v.get('missing') or '无'} integrity_check={v.get('quick_check')}")

    # 显示备份信息
    backup_size = os.path.getsize(backup_path)
    print(f"   备份大小: {backup_size / 1024 / 1024:.2f} MB")

    # 清理旧备份（保留最近10个）
    backup_dir = os.path.dirname(backup_path)
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
    if len(backups) > 10:
        for old_backup in backups[10:]:
            old_path = os.path.join(backup_dir, old_backup)
            try:
                os.remove(old_path)
            except OSError as e:
                print(f"[WARN] 清理旧备份失败 {old_backup}: {e}")
            else:
                print(f"   清理旧备份: {old_backup}")

    return backup_path


def list_backups():
    """列出所有备份"""
    print("=== 备份列表 ===")
    backup_dir = os.path.join(os.path.dirname(migrations.get_db_path()), 'backups')
    if not os.path.exists(backup_dir):
        print("无备份")
        return

    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
    if not backups:
        print("无备份")
        return

    for i, backup in enumerate(backups, 1):
        backup_path = os.path.join(backup_dir, backup)
        size = os.path.getsize(backup_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
        print(f"{i}. {backup} | {size/1024/1024:.2f} MB | {mtime}")


def restore_database(backup_name):
    """恢复数据库"""
    print("=== 数据库恢复 ===")
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if not os.path.exists(backup_path):
        print(f"[ERROR] 备份文件不存在: {backup_path}")
        return False

    # 先备份当前数据库
    print("备份当前数据库...")
    backup_database('before_restore.db')

    # 恢复
    try:
        shutil.copy2(backup_path, DB_PATH)
        print(f"[OK] 恢复成功: {backup_name}")
        return True
    except Exception as e:
        print(f"[ERROR] 恢复失败: {e}")
        return False


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'backup':
            backup_database()
        elif command == 'list':
            list_backups()
        elif command == 'restore' and len(sys.argv) > 2:
            restore_database(sys.argv[2])
        else:
            print("用法: python backup_db.py [backup|list|restore <backup_name>]")
    else:
        backup_database()
        list_backups()
