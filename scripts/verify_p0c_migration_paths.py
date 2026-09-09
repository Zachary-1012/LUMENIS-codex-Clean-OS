"""Verify P0-C migration paths against isolated SQLite copies only."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import database
import database_migrations as migrations
from canonical_data import ensure_canonical_table
from database_isolation import (
    backup_to_isolated_copy,
    database_identity,
    foreign_key_details,
)
from evidence_chain import init_db as init_evidence_db


def _bind(path: Path) -> None:
    database.DB_PATH = str(path)
    migrations.DB_PATH = str(path)
    migrations.BACKUP_DIR = str(path.parent / "backups")


def _counts(path: Path):
    connection = sqlite3.connect(path)
    try:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        result = {}
        for table in tables:
            quoted = table.replace('"', '""')
            result[table] = int(connection.execute(
                f'SELECT COUNT(*) FROM "{quoted}"'
            ).fetchone()[0])
        return result
    finally:
        connection.close()


def _version(path: Path):
    connection = sqlite3.connect(path)
    try:
        return migrations.get_current_version(connection)
    finally:
        connection.close()


def _read_compatibility(path: Path):
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        notes = int(connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
        canonical_columns = {row[1] for row in connection.execute(
            "PRAGMA table_info(canonical_data)"
        )}
        evidence_columns = {row[1] for row in connection.execute(
            "PRAGMA table_info(zbc_canonical_data)"
        )}
        return {
            "notes_readable": notes >= 0,
            "canonical_rule_version": "rule_version" in canonical_columns,
            "evidence_domain_identity": {"domain_id", "product_id"}.issubset(evidence_columns),
            "pass": bool(notes >= 0 and "rule_version" in canonical_columns and
                         {"domain_id", "product_id"}.issubset(evidence_columns)),
        }
    finally:
        connection.close()


def _migrate_copy(source: Path, destination: Path):
    source_before = database_identity(source)
    fk_before = foreign_key_details(source)
    backup_to_isolated_copy(source, destination)
    copy_counts_before = _counts(destination)
    _bind(destination)
    database.init_db()
    migration_ok = migrations.migrate()
    if migration_ok:
        init_evidence_db(str(destination))
        ensure_canonical_table(str(destination))
    copy_counts_after = _counts(destination)
    read_compatibility = _read_compatibility(destination)
    source_after = database_identity(source)
    decreased = {
        table: {"before": count, "after": copy_counts_after.get(table)}
        for table, count in copy_counts_before.items()
        if copy_counts_after.get(table, -1) < count
    }
    return {
        "source_before": source_before.to_dict(),
        "source_after": source_after.to_dict(),
        "source_unchanged": source_before == source_after,
        "source_fk_details": fk_before,
        "copy_path": str(destination),
        "migration_ok": migration_ok,
        "copy_version": _version(destination),
        "copy_identity": database_identity(destination).to_dict(),
        "row_count_decreases": decreased,
        "read_compatibility": read_compatibility,
        "pass": bool(
            migration_ok and source_before == source_after and not decreased and
            _version(destination) == migrations.CURRENT_VERSION and
            database_identity(destination).integrity == "ok" and read_compatibility["pass"]
        ),
    }


def _clean_bootstrap(destination: Path):
    _bind(destination)
    database.init_db()
    migration_ok = migrations.migrate()
    if migration_ok:
        init_evidence_db(str(destination))
        ensure_canonical_table(str(destination))
    identity = database_identity(destination)
    return {
        "migration_ok": migration_ok,
        "version": _version(destination),
        "identity": identity.to_dict(),
        "pass": bool(migration_ok and _version(destination) == migrations.CURRENT_VERSION and
                     identity.integrity == "ok"),
    }


def _historical_v9_upgrade(destination: Path):
    _bind(destination)
    database.init_db()
    connection = sqlite3.connect(destination)
    try:
        migrations.init_version_table(connection)
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version(version, description) VALUES (9, 'P0-C v9 fixture')")
        connection.execute(
            "INSERT INTO notes(note_id,title,content) VALUES ('p0c-history','广州太古汇','历史数据')"
        )
        connection.commit()
    finally:
        connection.close()
    migration_ok = migrations.migrate()
    read = _read_compatibility(destination) if migration_ok else {"pass": False}
    connection = sqlite3.connect(destination)
    try:
        preserved = connection.execute(
            "SELECT title FROM notes WHERE note_id='p0c-history'"
        ).fetchone() == ("广州太古汇",)
    finally:
        connection.close()
    return {
        "migration_ok": migration_ok,
        "version": _version(destination),
        "historical_row_preserved": preserved,
        "read_compatibility": read,
        "pass": bool(migration_ok and preserved and read["pass"] and
                     _version(destination) == migrations.CURRENT_VERSION),
    }


def _rollback_fault_injection(destination: Path):
    _bind(destination)
    database.init_db()
    connection = sqlite3.connect(destination)
    try:
        migrations.init_version_table(connection)
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version(version, description) VALUES (9, 'P0-C rollback fixture')")
        connection.commit()
    finally:
        connection.close()

    original = migrations.MIGRATIONS[9]
    def fail_after_ddl(connection):
        connection.execute("ALTER TABLE notes ADD COLUMN p0c_should_rollback TEXT")
        raise RuntimeError("P0-C fault injection")
    migrations.MIGRATIONS[9] = fail_after_ddl
    try:
        rejected = migrations.migrate(target_version=10) is False
    finally:
        migrations.MIGRATIONS[9] = original
    connection = sqlite3.connect(destination)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(notes)")}
        readable = connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0] >= 0
    finally:
        connection.close()
    rolled_back = "p0c_should_rollback" not in columns and _version(destination) == 9
    return {"failure_rejected": rejected, "schema_and_version_rolled_back": rolled_back,
            "legacy_read_compatible": readable,
            "pass": bool(rejected and rolled_back and readable)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[], help="label=absolute.db")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lumenis-p0c-migrate-") as temp_name:
        temp_root = Path(temp_name)
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": "source databases opened read-only; migrations run on SQLite backup copies",
            "clean_bootstrap": _clean_bootstrap(temp_root / "clean" / "monitor.db"),
            "historical_v9_upgrade": _historical_v9_upgrade(temp_root / "historical-v9" / "monitor.db"),
            "rollback_read_compatibility": _rollback_fault_injection(temp_root / "rollback" / "monitor.db"),
            "sources": {},
        }
        for index, item in enumerate(args.source, start=1):
            label, raw_path = item.split("=", 1)
            result["sources"][label] = _migrate_copy(
                Path(raw_path).resolve(), temp_root / f"copy-{index}" / "monitor.db"
            )
        result["overall_pass"] = bool(
            result["clean_bootstrap"]["pass"] and
            result["historical_v9_upgrade"]["pass"] and
            result["rollback_read_compatibility"]["pass"] and
            all(item["pass"] for item in result["sources"].values())
        )
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output), "overall_pass": result["overall_pass"],
        "sources": {
            key: {"pass": value["pass"],
                  "source_unchanged": value["source_unchanged"],
                  "fk_count": len(value["source_fk_details"]),
                  "copy_version": value["copy_version"]}
            for key, value in result["sources"].items()
        },
    }, ensure_ascii=False))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
