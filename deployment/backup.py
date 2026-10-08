"""SQLite 在线备份，不直接复制 WAL 状态中的 monitor.db。"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import database as db

    backup_dir = Path(db.main_db_path()).parent / "backups"
    out = backup_dir / f"monitor-v5.6.3-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
    print(db.backup_database(str(out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
