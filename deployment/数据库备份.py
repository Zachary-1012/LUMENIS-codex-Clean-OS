#!/usr/bin/env python3
"""
广州太古汇舆情监测系统 v5.3.2 - 数据库备份脚本

功能：
1. 使用 SQLite Online Backup API 生成一致性备份
2. 自动清理旧备份（保留最近30份）
3. 备份文件命名: monitor-YYYYMMDD-HHMMSS.db
4. 支持手动备份和定时备份

使用方式：
    python deployment/数据库备份.py          # 立即备份
    python deployment/数据库备份.py --list   # 列出备份
    python deployment/数据库备份.py --clean  # 清理旧备份
"""
import os
import sys
import argparse
from datetime import datetime

# 切换到项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)


def get_backup_dir():
    """获取备份目录"""
    return os.path.join(PROJECT_DIR, 'data', 'backups')


def create_backup():
    """创建数据库备份"""
    import database as db

    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = os.path.join(backup_dir, f'monitor-{timestamp}.db')

    print(f'[备份] 正在创建备份: {backup_path}')

    try:
        db.backup_database(backup_path)
        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        print(f'[备份] ✅ 备份完成: {backup_path} ({size_mb:.2f} MB)')

        # 自动清理旧备份
        cleaned = cleanup_old_backups(keep=30, dry_run=False)
        if cleaned:
            print(f'[备份] 已清理 {cleaned} 个旧备份')

        return backup_path
    except Exception as e:
        print(f'[备份] ❌ 备份失败: {e}')
        return None


def list_backups():
    """列出所有备份"""
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        print('暂无备份文件')
        return []

    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith('.db')],
        key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)),
        reverse=True
    )

    if not backups:
        print('暂无备份文件')
        return []

    print(f'共 {len(backups)} 个备份文件:')
    print('-' * 60)
    for i, f in enumerate(backups, 1):
        path = os.path.join(backup_dir, f)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
        marker = ' ← 最新' if i == 1 else ''
        print(f'  {i:2d}. {f}  {size_mb:6.2f} MB  {mtime}{marker}')
    print('-' * 60)
    return backups


def cleanup_old_backups(keep=30, dry_run=True):
    """清理旧备份"""
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return 0

    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith('.db')],
        key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)),
        reverse=True
    )

    if len(backups) <= keep:
        return 0

    to_delete = backups[keep:]
    count = 0
    for f in to_delete:
        path = os.path.join(backup_dir, f)
        if dry_run:
            print(f'[清理] 将删除: {f}')
        else:
            try:
                os.remove(path)
                count += 1
            except Exception as e:
                print(f'[清理] 删除失败 {f}: {e}')

    if dry_run and to_delete:
        print(f'[清理] 共 {len(to_delete)} 个旧备份将被清理（保留最近 {keep} 个）')
    return count


def main():
    parser = argparse.ArgumentParser(description='广州太古汇舆情监测系统 - 数据库备份')
    parser.add_argument('--list', action='store_true', help='列出所有备份')
    parser.add_argument('--clean', action='store_true', help='清理旧备份（保留最近30个）')
    parser.add_argument('--keep', type=int, default=30, help='保留备份数量（默认30）')
    parser.add_argument('--execute', action='store_true', help='实际执行清理（默认dry run）')
    args = parser.parse_args()

    print('=' * 60)
    print('  广州太古汇舆情监测系统 v5.3.2 - 数据库备份')
    print(f'  时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    print()

    if args.list:
        list_backups()
    elif args.clean:
        cleanup_old_backups(keep=args.keep, dry_run=not args.execute)
        if not args.execute:
            print()
            print('提示: 添加 --execute 参数实际执行清理')
    else:
        create_backup()

    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
