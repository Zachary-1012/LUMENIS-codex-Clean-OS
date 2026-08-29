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


def backup_database(backup_name=None):
    """备份数据库"""
    print("=== 数据库备份 ===")

    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)

    if backup_name is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'monitor_backup_{timestamp}.db'

    backup_path = os.path.join(BACKUP_DIR, backup_name)

    # 使用sqlite3的backup API
    try:
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(backup_path)
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        print(f"✅ 备份成功: {backup_path}")
    except Exception as e:
        print(f"⚠️ SQLite备份失败，使用文件复制: {e}")
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ 文件复制备份成功: {backup_path}")

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
        print(f"❌ 备份文件不存在: {backup_path}")
        return False

    # 先备份当前数据库
    print("备份当前数据库...")
    backup_database('before_restore.db')

    # 恢复
    try:
        shutil.copy2(backup_path, DB_PATH)
        print(f"✅ 恢复成功: {backup_name}")
        return True
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
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
