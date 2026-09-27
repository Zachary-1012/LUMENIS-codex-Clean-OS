"""One-time v18 correction of note publication-time quality labels.

Only previously misclassified rows are eligible. Source content, timestamps,
Evidence, scope, and Canonical identity are immutable in this operation.
Dry-run is the default; --apply snapshots the selected database first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_quality_gate import DataQualityGate
from lumenis.shared.database import DatabaseRepository


def _fingerprint(conn: sqlite3.Connection) -> str:
    """Hash stored source and lineage fields, excluding derived quality labels."""
    digest = hashlib.sha256()
    for query in (
        "SELECT note_id,title,content,url,publish_date,publish_datetime,captured_at,"
        "subject_id,brand_focus_id,scope_status,scope_evidence_ref "
        "FROM notes ORDER BY note_id",
        "SELECT canonical_id,source_id,content_hash,publish_datetime,captured_at,"
        "subject_id,brand_focus_id,scope_status,scope_evidence_ref "
        "FROM canonical_data ORDER BY canonical_id",
    ):
        for row in conn.execute(query):
            digest.update(json.dumps(tuple(row), ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _eligible(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    gate = DataQualityGate()
    rows = conn.execute(
        "SELECT n.note_id,n.title,n.url,n.risk_level,n.publish_date,"
        "n.data_quality_score,n.scope_status,n.scope_evidence_ref,"
        "c.canonical_id,c.quality_status,c.quality_score,"
        "c.scope_status AS canonical_scope,c.scope_evidence_ref AS canonical_evidence "
        "FROM notes n JOIN canonical_data c "
        "ON c.source_table='notes' AND c.source_id=n.note_id "
        "WHERE n.data_quality_status='error' ORDER BY n.note_id"
    ).fetchall()
    error_total = conn.execute(
        "SELECT COUNT(*) FROM notes WHERE data_quality_status='error'"
    ).fetchone()[0]
    if len(rows) != error_total:
        raise RuntimeError("error notes lack a unique Canonical note binding")
    eligible = []
    for row in rows:
        if (row["scope_status"] != "VERIFIED"
                or row["canonical_scope"] != "VERIFIED"
                or not row["scope_evidence_ref"]
                or str(row["scope_evidence_ref"]) != str(row["canonical_evidence"])
                or row["quality_status"] != "error"
                or float(row["quality_score"]) != float(row["data_quality_score"])):
            raise RuntimeError("quality or exact Evidence binding diverged")
        result = gate.enrich_quality_record("note", {
            "title": row["title"], "url": row["url"],
            "risk_level": row["risk_level"] or "unconfirmed",
            "publish_date": row["publish_date"],
        })
        if result["data_quality_status"] == "error":
            continue  # Malformed supplied data remains invalid.
        if result["data_quality_status"] not in ("missing", "ok"):
            raise RuntimeError("unexpected quality classification")
        eligible.append((row["note_id"], result["data_quality_status"],
                         result["data_quality_score"]))
    return eligible


def _snapshot(db: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="lumenis-publish-quality-backup-")) / "monitor-before.db"
    with DatabaseRepository(str(db)).connection(read_only=True, wal=False) as source:
        with sqlite3.connect(str(backup)) as destination:
            source.backup(destination)
    with DatabaseRepository(str(backup)).connection(read_only=True, wal=False) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("backup integrity failed")
    return backup


def run(db: Path, *, apply: bool = False) -> dict:
    db = db.resolve(strict=True)
    repo = DatabaseRepository(str(db))
    with repo.connection(read_only=True, wal=False) as conn:
        if conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] != 18:
            raise RuntimeError("product database must be v18")
        eligible = _eligible(conn)
        before = _fingerprint(conn)
    counts = {state: sum(row[1] == state for row in eligible)
              for state in ("missing", "ok")}
    if not apply:
        return {"mode": "DRY_RUN", "eligible": len(eligible), "new_status": counts}
    backup = _snapshot(db)
    with repo.transaction() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if _fingerprint(conn) != before or _eligible(conn) != eligible:
            raise RuntimeError("database changed after snapshot; retry with fresh dry-run")
        for note_id, status, score in eligible:
            note = conn.execute(
                "UPDATE notes SET data_quality_status=?,data_quality_score=? "
                "WHERE note_id=? AND data_quality_status='error'",
                (status, score, note_id),
            )
            canonical = conn.execute(
                "UPDATE canonical_data SET quality_status=?,quality_score=? "
                "WHERE source_table='notes' AND source_id=? AND quality_status='error'",
                (status, score, note_id),
            )
            if note.rowcount != 1 or canonical.rowcount != 1:
                raise RuntimeError("concurrent quality update detected")
        if _fingerprint(conn) != before:
            raise RuntimeError("source or Evidence fields changed")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("database integrity failed")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("foreign key violation")
    with repo.connection(read_only=True, wal=False) as conn:
        if _fingerprint(conn) != before or _eligible(conn):
            raise RuntimeError("quality reclassification readback failed")
    return {"mode": "APPLIED", "updated": len(eligible), "new_status": counts,
            "backup": str(backup), "integrity": "ok", "foreign_key_violations": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.db, apply=args.apply), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
