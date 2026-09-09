from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def snapshot(path: Path) -> tuple[sqlite3.Connection, dict[str, str | None]]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    tables = {
        str(name): sql
        for name, sql in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    return connection, tables


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SQLite schema and row-count delta")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    connections = []
    try:
        baseline, baseline_tables = snapshot(args.baseline)
        current, current_tables = snapshot(args.current)
        connections.extend([baseline, current])
        delta = []
        for name in sorted(set(baseline_tables) | set(current_tables)):
            quoted = '"' + name.replace('"', '""') + '"'
            before = baseline.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0] if name in baseline_tables else None
            after = current.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0] if name in current_tables else None
            schema_changed = baseline_tables.get(name) != current_tables.get(name)
            if before != after or schema_changed:
                delta.append({"table": name, "baseline_rows": before, "current_rows": after, "schema_changed": schema_changed})
        print(json.dumps(delta, ensure_ascii=False, indent=2))
        return 0
    finally:
        for connection in connections:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
