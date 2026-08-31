# -*- coding: utf-8 -*-
"""Z-Brand Core Staging 数据库准备工具（只读源、在线一致备份，不锁生产库）。

用途：把生产 data/monitor.db 通过 SQLite Online Backup API 一致复制到
     staging/monitor.staging.db，供轻量 Staging（独立端口/独立库/禁采集）使用。

安全：
- 源库以只读 URI 打开，绝不写入生产库；
- 生产运行中（WAL）也可安全得到一致快照；
- 副本是独立文件，Staging 的任何写操作都不影响生产。

用法：.venv\\Scripts\\python.exe scripts/staging_setup.py
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'monitor.db')
STAGE_DIR = os.path.join(ROOT, 'staging')
DST = os.path.join(STAGE_DIR, 'monitor.staging.db')


def main():
    if not os.path.exists(SRC):
        print(f'[staging] source db not found: {SRC}', file=sys.stderr)
        return 2
    os.makedirs(STAGE_DIR, exist_ok=True)
    # 源只读打开（URI mode=ro），保证不动生产
    src = sqlite3.connect(f'file:{SRC}?mode=ro', uri=True)
    if os.path.exists(DST):
        os.remove(DST)
    dst = sqlite3.connect(DST)
    try:
        src.backup(dst)  # 在线一致备份，自动处理 WAL
        def n(c, t):
            try:
                return c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            except sqlite3.Error:
                return 'NA'
        print('[staging] backup OK ->', DST)
        for t in ('notes', 'events', 'collection_logs'):
            print(f'  {t:16s} src={n(src,t)}  staging_copy={n(dst,t)}')
        return 0
    finally:
        dst.close()
        src.close()


if __name__ == '__main__':
    sys.exit(main())
