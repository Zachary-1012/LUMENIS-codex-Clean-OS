"""
数据库备份脚本
版本: v5.8.0
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not __package__:
    sys.path.insert(0, PROJECT_ROOT)

from lumenis.shared.database import migrations
from lumenis.shared.database.connection import connect_sqlite

DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'monitor.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'data', 'backups')


def verify_backup(backup_path):
    """备份完整性校验：只读打开备份，确认核心表存在且可读（WAL 下 backup API 本就一致，双保险）。"""
    try:
        con = connect_sqlite(str(backup_path), read_only=True, immutable=True, wal=False, timeout=10)
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
            if any(os.path.lexists(old_path + suffix) for suffix in
                   ('.signing-manifest.json', '.evidence-signing.dpapi', '.evidence-signing.json')):
                continue
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


def restore_database(backup_name, *, target_directory=None):
    """Verify and restore into an explicitly chosen new directory, never online."""
    print("=== 数据库恢复 ===")
    if (not isinstance(backup_name, str) or not backup_name or backup_name in {'.', '..'}
            or os.path.basename(backup_name) != backup_name or '/' in backup_name or '\\' in backup_name):
        print('[ERROR] RESTORE_BACKUP_NAME_INVALID')
        return False
    backup_path = Path(migrations.get_db_path()).parent / 'backups' / backup_name
    if target_directory is None:
        print('[ERROR] RESTORE_ONLINE_OVERWRITE_DENIED: 现有数据库未改动；请用 --target-directory 指定不存在的新目录完成验证恢复。')
        return False
    try:
        result = migrations.restore_database_to_directory(backup_path, target_directory)
        print(f"[OK] 已验证恢复到新目录: {result['target_root']}")
        print('   原数据库未切换，服务未启动；切换需停服务及对应批准。')
        return True
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(f"[ERROR] 恢复失败: {error}")
        return False


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args:
        command = args[0]
        if command == 'backup':
            return 0 if backup_database() else 1
        elif command == 'list':
            list_backups()
            return 0
        elif command == 'restore' and len(args) == 2:
            return 0 if restore_database(args[1]) else 1
        elif command == 'restore' and len(args) == 4 and args[2] == '--target-directory':
            return 0 if restore_database(args[1], target_directory=args[3]) else 1
        else:
            print('用法: python scripts/backup_db.py [backup|list|restore <backup_name> --target-directory <new_directory>]')
            return 2
    else:
        result = backup_database()
        list_backups()
        return 0 if result else 1


if __name__ == '__main__':
    raise SystemExit(main())
