"""SQLite 在线备份，不直接复制 WAL 状态中的 monitor.db。"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import database as db

out = ROOT / 'data' / 'backups' / f"monitor-v5.6.3-{datetime.now():%Y%m%d-%H%M%S}.db"
print(db.backup_database(str(out)))
