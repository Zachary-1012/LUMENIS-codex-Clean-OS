"""
数据库备份脚本
版本: v5.8.0
"""

import sqlite3
import os
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'monitor.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'data', 'backups')


def verify_backup(backup_path):
    """备份完整性校验：只读打开备份，确认核心表存在且可读（WAL 下 backup API 本就一致，双保险）。"""
    import sqlite3 as _sq
    try:
        con = _sq.connect(f'file:{backup_path}?mode=ro', uri=True, timeout=10)
        try:
            tabs = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            core = {'notes', 'events', 'daily_reports', 'collection_logs', 'metric_snapshots'}
            missing = core - tabs
            # 快速一致性检查：PRAGMA quick_check（仅读）
            qc = con.execute('PRAGMA quick_check').fetchone()[0]
            ok = (qc == 'ok') and not missing
            return {'ok': ok, 'tables': len(tabs), 'missing': sorted(missing), 'quick_check': qc}
        finally:
            con.close()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def backup_database(backup_name=None):
    """备份数据库"""
    print("=== 数据库备份 ===")

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 数据库文件不存在: {DB_PATH}")
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)

    if backup_name is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'monitor_backup_{timestamp}.db'

    backup_path = os.path.join(BACKUP_DIR, backup_name)

    # 使用sqlite3的backup API（WAL 下在线一致性备份，不锁生产）
    used_fallback = False
    try:
        src_conn = sqlite3.connect(DB_PATH, timeout=30)
        dst_conn = sqlite3.connect(backup_path, timeout=30)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        print(f"[OK] SQLite backup API 备份成功: {backup_path}")
    except Exception as e:
        # 仅当明确是"数据库被独占锁定"类错误才走文件拷贝（WAL 下拷贝可能不一致）；
        # 其他错误直接报失败，避免产生不可用的"假备份"。
        msg = str(e)
        if any(k in msg for k in ('locked', 'Locked', 'busy', 'Busy', 'cannot open')):
            print(f"[WARN] backup API 锁定异常({e})，尝试文件拷贝兜底...")
            shutil.copy2(DB_PATH, backup_path)
            used_fallback = True
        else:
            print(f"[ERROR] 备份失败(非锁定类): {e}")
            return None

    # 备份完整性校验（文件拷贝兜底时尤其必要）
    v = verify_backup(backup_path)
    if not v.get('ok'):
        print(f"[ERROR] 备份校验失败: {v}")
        try:
            os.remove(backup_path)
        except Exception:
            pass
        return None
    print(f"   校验OK: 表数={v.get('tables')} 缺失={v.get('missing') or '无'} quick_check={v.get('quick_check')}"
          + (" (fallback拷贝)" if used_fallback else ""))

    # 显示备份信息
    backup_size = os.path.getsize(backup_path)
    print(f"   备份大小: {backup_size / 1024 / 1024:.2f} MB")

    # 清理旧备份（保留最近10个）
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], reverse=True)
    if len(backups) > 10:
        for old_backup in backups[10:]:
            old_path = os.path.join(BACKUP_DIR, old_backup)
            os.remove(old_path)
            print(f"   清理旧备份: {old_backup}")

    return backup_path


def list_backups():
    """列出所有备份"""
    print("=== 备份列表 ===")
    if not os.path.exists(BACKUP_DIR):
        print("无备份")
        return

    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], reverse=True)
    if not backups:
        print("无备份")
        return

    for i, backup in enumerate(backups, 1):
        backup_path = os.path.join(BACKUP_DIR, backup)
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
