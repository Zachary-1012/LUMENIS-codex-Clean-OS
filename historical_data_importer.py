"""
ZBC Phase 15 - Historical Data Importer
========================================
Hash -> Dedup -> Provenance -> Timestamp -> Source -> Product -> Subject
"""
from __future__ import annotations
import hashlib, json, os, re, sqlite3
import hashlib, json, os, re, sqlite3
from datetime import datetime
from typing import Any, Optional
from lumenis.shared.database import DatabaseRepository, main_db_path

DEFAULT_PRODUCT_ID = "CTH"
HISTORICAL_RULE_VERSION = "hist-v1.0"
IMPORT_BATCH_PREFIX = "hist_import"
IMPORT_STATUS_INSERTED = "inserted"
IMPORT_STATUS_DEDUP_SKIPPED = "dedup_skipped"
IMPORT_STATUS_SUBJECT_REJECTED = "subject_rejected"
IMPORT_STATUS_ERROR = "error"

# ZBC Lifecycle Contract V1.0 (bypass-mode)
try:
    from lifecycle_mixin import LifecycleMixin as _LifecycleMixin
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _LifecycleMixin = None
    _LIFECYCLE_AVAILABLE = False


def _get_db_path():
    return main_db_path()


def _get_connection(db_path=None):
    path = db_path or _get_db_path()
    return DatabaseRepository(path).connect(timeout=10)


def normalize_content(title="", content="", body=""):
    raw = " ".join(str(x or "") for x in (title, content, body))
    raw = re.sub(r"https?://\S+", "", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw.lower()


def compute_content_hash(title="", content="", body=""):
    normalized = normalize_content(title, content, body)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _safe_identifier(name: str) -> str:
    """校验SQL标识符仅含安全字符。"""
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name or ''):
        raise ValueError(f"非法SQL标识符: {name!r}")
    return name


def check_duplicate(conn, content_hash, note_id="", table="notes"):
    result = {"is_duplicate": False, "dedup_type": "", "existing_id": ""}
    if not content_hash and not note_id:
        return result
    cur = conn.execute(f"PRAGMA table_info({_safe_identifier(table)})")
    cols = {r["name"] for r in cur.fetchall()}
    if content_hash and "content_hash" in cols:
        cur = conn.execute(
            f"SELECT note_id, id FROM {_safe_identifier(table)} WHERE content_hash=? AND content_hash IS NOT NULL AND content_hash != '' LIMIT 1",
            (content_hash,))
        row = cur.fetchone()
        if row:
            result["is_duplicate"] = True
            result["dedup_type"] = "content_hash"
            result["existing_id"] = str(row["note_id"] or row["id"])
            return result
    if note_id:
        id_col = "note_id" if "note_id" in cols else "source_id"
        if id_col in cols:
            cur = conn.execute(f"SELECT {_safe_identifier(id_col)}, id FROM {_safe_identifier(table)} WHERE {_safe_identifier(id_col)}=? LIMIT 1", (note_id,))
            row = cur.fetchone()
            if row:
                result["is_duplicate"] = True
                result["dedup_type"] = id_col
                result["existing_id"] = str(row[id_col])
                return result
    return result


def build_provenance(source_table, source_id, source_url="", captured_at="", publish_datetime=""):
    return f"{source_table}:{source_id}"


def build_provenance_detail(source_type, source_url, captured_at, publish_datetime, source_table="", source_id=""):
    return {
        "source_type": source_type or "",
        "source_url": source_url or "",
        "captured_at": captured_at or "",
        "publish_datetime": publish_datetime or "",
        "source_table": source_table or "",
        "source_id": source_id or "",
    }


def validate_timestamps(publish_datetime="", captured_at="", publish_date=""):
    warnings = []
    pub = (publish_datetime or publish_date or "").strip()
    cap = (captured_at or "").strip()
    if not pub and cap:
        warnings.append("publish_datetime missing; captured_at NOT used as substitute")
    if pub and not re.match(r"\d{4}-\d{2}-\d{2}", pub):
        warnings.append(f"publish_datetime format unusual: {pub}")
    return {"publish_datetime": pub, "captured_at": cap, "publish_date": pub[:10] if pub else "", "warnings": warnings}


def normalize_platform(source_platform=""):
    sp = (source_platform or "").strip().lower()
    platform_map = {
        "xhs": "xiaohongshu", "xiaohongshu": "xiaohongshu", "rednote": "xiaohongshu",
        "weibo": "weibo", "bilibili": "bilibili", "b站": "bilibili",
        "web": "web", "sogou_search": "sogou_search", "sogou": "sogou_search",
    }
    return platform_map.get(sp, sp or "unknown")


def resolve_product_id(product_id=""):
    pid = (product_id or "").strip().upper()
    if pid in ("CTH", "ZBC", ""):
        return pid or DEFAULT_PRODUCT_ID
    return pid


def _optional_text(raw, field):
    value = raw.get(field)
    if value is None:
        return None
    text = str(value)
    return text if text.strip() else None


def _optional_int(raw, field):
    value = raw.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return int(value)


def apply_subject_filter(title="", body="", content="", source_keyword="", matched_keywords=""):
    try:
        from subject_rules import subject_hit, subject_reason
        note_dict = {
            "title": title, "body": body or content, "content": content,
            "source_keyword": source_keyword, "matched_keywords": matched_keywords,
        }
        hit = subject_hit(title=title, body=body or content, content=content,
                          source_keyword=source_keyword, matched_keywords=matched_keywords)
        reason = subject_reason(note_dict)
        return {"subject_hit": hit, "subject_reason": reason}
    except ImportError:
        text = " ".join(str(x or "") for x in (title, body, content, source_keyword, matched_keywords)).lower()
        hit = any(kw in text for kw in ["太古汇", "广州太古汇"])
        return {"subject_hit": hit, "subject_reason": "fallback_keyword_match"}


def get_current_rule_version(conn):
    try:
        cur = conn.execute("SELECT version FROM rule_version_registry WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row["version"] if row else HISTORICAL_RULE_VERSION
    except sqlite3.OperationalError:
        return HISTORICAL_RULE_VERSION


def register_rule_version(conn, version, description="", rule_type="subject",
                          subject_words=None, exclude_words=None, changelog=None):
    sw = subject_words or []
    ew = exclude_words or []
    sw_hash = hashlib.sha256("|".join(sw).encode("utf-8")).hexdigest()[:16] if sw else ""
    ew_hash = hashlib.sha256("|".join(ew).encode("utf-8")).hexdigest()[:16] if ew else ""
    conn.execute("UPDATE rule_version_registry SET is_active=0 WHERE is_active=1")
    cur = conn.execute(
        """INSERT INTO rule_version_registry
           (version, rule_type, description, subject_words_count, exclude_words_count,
            subject_words_hash, exclude_words_hash, applied_at, applied_by, is_active, changelog)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (version, rule_type, description, len(sw), len(ew), sw_hash, ew_hash,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "historical_importer",
         json.dumps(changelog or {}, ensure_ascii=False)))
    conn.commit()
    return cur.lastrowid


def ensure_baseline_rule_version(conn):
    cur = conn.execute("SELECT version FROM rule_version_registry WHERE version=? LIMIT 1", (HISTORICAL_RULE_VERSION,))
    if cur.fetchone():
        return HISTORICAL_RULE_VERSION
    try:
        from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS
        sw, ew = list(SUBJECT_WORDS), list(SUBJECT_EXCLUDE_WORDS)
    except ImportError:
        sw, ew = [], []
    register_rule_version(conn, version=HISTORICAL_RULE_VERSION,
        description="ZBC Phase15 historical baseline rule version", rule_type="subject",
        subject_words=sw, exclude_words=ew, changelog={"baseline": True, "phase": "zbc-phase15"})
    return HISTORICAL_RULE_VERSION


def log_import(conn, batch_id, source_table, source_id, target_table, target_id="",
               content_hash="", rule_version="", product_id=DEFAULT_PRODUCT_ID,
               subject_hit_result=0, subject_reason="", publish_datetime="", captured_at="",
               source_platform="", import_status=IMPORT_STATUS_INSERTED, dedup_hit=0,
               dedup_of="", notes=""):
    cur = conn.execute(
        """INSERT INTO historical_import_log
           (import_batch_id, source_table, source_id, target_table, target_id, content_hash,
            rule_version, product_id, subject_hit, subject_reason, publish_datetime,
            captured_at, source_platform, import_status, dedup_hit, dedup_of,
            imported_at, imported_by, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (batch_id, source_table, source_id, target_table, target_id, content_hash,
         rule_version, product_id, subject_hit_result, subject_reason, publish_datetime,
         captured_at, source_platform, import_status, dedup_hit, dedup_of,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "historical_importer", notes))
    return cur.lastrowid


def import_historical_note(raw, conn=None, batch_id="", product_id=DEFAULT_PRODUCT_ID,
                           rule_version="", dry_run=False):
    own_conn = conn is None
    if own_conn:
        conn = _get_connection()
    result = {
        "status": "", "note_id": "", "content_hash": "", "subject_hit": False,
        "subject_reason": "", "dedup": False, "dedup_type": "", "warnings": [],
        "inserted_id": None, "log_id": None, "persistence_state": "NOT_WRITTEN",
    }
    savepoint_open = False
    write_scope_started = False
    transaction_started_here = False

    def _begin_write_scope():
        nonlocal savepoint_open, write_scope_started, transaction_started_here
        if savepoint_open:
            return
        # A caller-owned connection must retain control of COMMIT/ROLLBACK.
        # BEGIN first so releasing the outermost SAVEPOINT cannot auto-commit.
        if not conn.in_transaction:
            conn.execute("BEGIN")
            transaction_started_here = True
        conn.execute("SAVEPOINT historical_import_note")
        savepoint_open = True
        write_scope_started = True

    def _finish_write_scope():
        nonlocal savepoint_open
        if savepoint_open:
            conn.execute("RELEASE SAVEPOINT historical_import_note")
            savepoint_open = False
        if own_conn and write_scope_started:
            conn.commit()
            result["persistence_state"] = "COMMITTED"
        elif write_scope_started:
            result["persistence_state"] = "PENDING_CALLER_COMMIT"

    try:
        note_id = str(raw.get("note_id") or raw.get("source_id") or "").strip()
        title = str(raw.get("title") or "")
        content = str(raw.get("content") or "")
        body = str(raw.get("body") or content)
        url = str(raw.get("url") or raw.get("source_url") or "")
        source_platform = normalize_platform(raw.get("source_platform") or raw.get("platform") or "")
        publish_datetime = str(raw.get("publish_datetime") or raw.get("published_at") or "")
        publish_date = str(raw.get("publish_date") or "")
        captured_at = str(raw.get("captured_at") or raw.get("collected_at") or raw.get("fetched_at") or "")
        source_table = str(raw.get("source_table") or "historical_import")
        source_id = note_id or str(raw.get("source_id") or "")
        result["note_id"] = note_id
        if not note_id:
            result["status"] = IMPORT_STATUS_ERROR
            result["warnings"].append("note_id is required")
            return result
        content_hash = compute_content_hash(title, content, body)
        result["content_hash"] = content_hash
        dedup = check_duplicate(conn, content_hash, note_id, table="notes")
        if dedup["is_duplicate"]:
            result["status"] = IMPORT_STATUS_DEDUP_SKIPPED
            result["dedup"] = True
            result["dedup_type"] = dedup["dedup_type"]
            result["warnings"].append(f"duplicate of {dedup['existing_id']} via {dedup['dedup_type']}")
            if not dry_run:
                _begin_write_scope()
                log_import(conn, batch_id, source_table, source_id, "notes",
                    target_id=dedup["existing_id"], content_hash=content_hash,
                    rule_version=rule_version or HISTORICAL_RULE_VERSION,
                    product_id=product_id, import_status=IMPORT_STATUS_DEDUP_SKIPPED,
                    dedup_hit=1, dedup_of=dedup["existing_id"],
                    notes="; ".join(result["warnings"]))
                _finish_write_scope()
            else:
                result["persistence_state"] = "NOT_WRITTEN"
            return result
        subj = apply_subject_filter(
            title=title, body=body, content=content,
            source_keyword=str(raw.get("source_keyword") or ""),
            matched_keywords=str(raw.get("matched_keywords") or ""))
        result["subject_hit"] = subj["subject_hit"]
        result["subject_reason"] = subj["subject_reason"]
        ts = validate_timestamps(publish_datetime, captured_at, publish_date)
        result["warnings"].extend(ts["warnings"])
        provenance = build_provenance(source_table, source_id, url, captured_at, ts["publish_datetime"])
        pid = resolve_product_id(product_id)
        rv = rule_version or get_current_rule_version(conn)
        if not dry_run:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _begin_write_scope()
            cur = conn.execute(
                """INSERT INTO notes
                   (note_id, title, content, body, url, source_platform, publish_date,
                    publish_datetime, captured_at, is_taikoo_verified, verify_reason,
                    content_hash, provenance, product_id, rule_version, subject_type,
                    content_type, status, collected_at, last_seen_at, source_keyword,
                    matched_keywords, likes, comments, collects, shares, sentiment,
                    risk_level, risk_score, summary, topics, author_id, author_nickname,
                    author_avatar, note_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (note_id, title, content, body, url, source_platform, ts["publish_date"],
                 ts["publish_datetime"], ts["captured_at"],
                 1 if subj["subject_hit"] else 0, subj["subject_reason"],
                 content_hash, provenance, pid, rv,
                 str(raw.get("subject_type") or ""), str(raw.get("content_type") or "ugc"),
                 "active", ts["captured_at"] or now, now,
                 str(raw.get("source_keyword") or ""), str(raw.get("matched_keywords") or ""),
                 _optional_int(raw, "likes"), _optional_int(raw, "comments"),
                 _optional_int(raw, "collects"), _optional_int(raw, "shares"),
                 _optional_text(raw, "sentiment"),
                 _optional_text(raw, "risk_level"), _optional_int(raw, "risk_score"),
                 str(raw.get("summary") or ""), str(raw.get("topics") or "[]"),
                 str(raw.get("author_id") or ""), str(raw.get("author_nickname") or ""),
                 str(raw.get("author_avatar") or ""), str(raw.get("note_type") or "normal")))
            result["inserted_id"] = cur.lastrowid
            result["log_id"] = log_import(
                conn, batch_id, source_table, source_id, "notes",
                target_id=str(cur.lastrowid), content_hash=content_hash,
                rule_version=rv, product_id=pid,
                subject_hit_result=1 if subj["subject_hit"] else 0,
                subject_reason=subj["subject_reason"],
                publish_datetime=ts["publish_datetime"], captured_at=ts["captured_at"],
                source_platform=source_platform, import_status=IMPORT_STATUS_INSERTED,
                notes="; ".join(result["warnings"]))
            _finish_write_scope()
        else:
            result["persistence_state"] = "NOT_WRITTEN"
        result["status"] = IMPORT_STATUS_INSERTED
        return result
    except Exception as e:
        result["status"] = IMPORT_STATUS_ERROR
        result["warnings"].append(f"import error: {e}")
        if write_scope_started or transaction_started_here:
            try:
                if savepoint_open and conn.in_transaction:
                    conn.execute("ROLLBACK TO SAVEPOINT historical_import_note")
                    conn.execute("RELEASE SAVEPOINT historical_import_note")
                    savepoint_open = False
                if own_conn or transaction_started_here:
                    conn.rollback()
                    result["persistence_state"] = "ROLLED_BACK"
                elif not conn.in_transaction:
                    # SQLite RAISE(ROLLBACK) may invalidate the savepoint and
                    # abort the whole caller transaction before control returns.
                    result["persistence_state"] = "ROLLED_BACK"
                else:
                    result["persistence_state"] = "ROLLED_BACK_TO_SAVEPOINT"
                result["inserted_id"] = None
                result["log_id"] = None
            except Exception:
                result["persistence_state"] = "UNKNOWN"
                result["warnings"].append(
                    "write rollback could not be confirmed; persistence state is unknown"
                )
        else:
            result["persistence_state"] = "NOT_WRITTEN"
        return result
    finally:
        if own_conn:
            conn.close()


def import_historical_batch(records, db_path=None, product_id=DEFAULT_PRODUCT_ID,
                            rule_version="", dry_run=False):
    batch_id = f"{IMPORT_BATCH_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    conn = _get_connection(db_path)
    if not dry_run:
        ensure_baseline_rule_version(conn)
    stats = {"batch_id": batch_id, "total": len(records), "inserted": 0,
             "dedup_skipped": 0, "subject_rejected": 0, "errors": 0, "details": []}
    batch_rolled_back = False
    for index, raw in enumerate(records):
        r = import_historical_note(raw, conn=conn, batch_id=batch_id,
                                   product_id=product_id, rule_version=rule_version,
                                   dry_run=dry_run)
        stats["details"].append(r)
        if r["status"] == IMPORT_STATUS_INSERTED:
            stats["inserted"] += 1
        elif r["status"] == IMPORT_STATUS_DEDUP_SKIPPED:
            stats["dedup_skipped"] += 1
        elif r["status"] == IMPORT_STATUS_SUBJECT_REJECTED:
            stats["subject_rejected"] += 1
        elif r["status"] == IMPORT_STATUS_ERROR:
            stats["errors"] += 1
        prior_pending_writes = any(
            detail.get("persistence_state") == "PENDING_CALLER_COMMIT"
            for detail in stats["details"][:-1]
        )
        if (r["status"] == IMPORT_STATUS_ERROR
                and r.get("persistence_state") == "ROLLED_BACK"
                and not conn.in_transaction
                and prior_pending_writes):
            # A transaction-wide rollback invalidates every earlier pending
            # result. Stop so later rows cannot make this batch look partially
            # committed after its shared write scope was aborted.
            batch_rolled_back = True
            for detail in stats["details"][:-1]:
                if detail.get("persistence_state") == "PENDING_CALLER_COMMIT":
                    detail["persistence_state"] = "ROLLED_BACK"
                    # Both IDs referred to rows removed by the rollback.
                    detail["inserted_id"] = None
                    detail["log_id"] = None
                    prior_status = detail.get("status")
                    if prior_status in (IMPORT_STATUS_INSERTED, IMPORT_STATUS_DEDUP_SKIPPED):
                        # A rolled-back dedup skip may point at a same-batch
                        # insert that no longer exists; reclassify as an error
                        # so error-only retry cannot lose the record.
                        detail["status"] = IMPORT_STATUS_ERROR
                        detail["warnings"].append(
                            "batch transaction rolled back after a later write failure"
                        )
                        if prior_status == IMPORT_STATUS_INSERTED:
                            stats["inserted"] -= 1
                        else:
                            stats["dedup_skipped"] -= 1
                        stats["errors"] += 1
            for pending in records[index + 1:]:
                pending_id = (
                    str(pending.get("note_id") or pending.get("source_id") or "")
                    if isinstance(pending, dict) else ""
                )
                stats["details"].append({
                    "status": IMPORT_STATUS_ERROR,
                    "note_id": pending_id,
                    "content_hash": "", "subject_hit": False, "subject_reason": "",
                    "dedup": False, "dedup_type": "",
                    "warnings": [
                        "batch stopped after transaction-wide rollback; record not processed"
                    ],
                    "inserted_id": None, "log_id": None,
                    "persistence_state": "NOT_WRITTEN",
                })
                stats["errors"] += 1
            break
    try:
        if not dry_run:
            if batch_rolled_back:
                if conn.in_transaction:
                    conn.rollback()
            else:
                conn.commit()
                for detail in stats["details"]:
                    if detail.get("persistence_state") == "PENDING_CALLER_COMMIT":
                        detail["persistence_state"] = "COMMITTED"
    finally:
        conn.close()
    return stats


def verify_historical_integrity(db_path=None):
    conn = _get_connection(db_path)
    report = {
        "notes_total": 0, "notes_with_rule_version": 0, "notes_without_rule_version": 0,
        "notes_with_content_hash": 0, "notes_with_product_id": 0,
        "notes_cth": 0, "notes_zbc": 0, "notes_other_product": 0,
        "canonical_total": 0, "canonical_with_rule_version": 0, "canonical_cth": 0,
        "import_log_count": 0, "rule_versions_registered": 0, "warnings": [],
    }
    cur = conn.execute("SELECT COUNT(*) FROM notes")
    report["notes_total"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM notes WHERE rule_version IS NOT NULL AND rule_version != ''")
    report["notes_with_rule_version"] = cur.fetchone()[0]
    report["notes_without_rule_version"] = report["notes_total"] - report["notes_with_rule_version"]
    cur.execute("SELECT COUNT(*) FROM notes WHERE content_hash IS NOT NULL AND content_hash != ''")
    report["notes_with_content_hash"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM notes WHERE product_id IS NOT NULL AND product_id != ''")
    report["notes_with_product_id"] = cur.fetchone()[0]
    cur.execute("SELECT product_id, COUNT(*) FROM notes WHERE product_id IS NOT NULL AND product_id != '' GROUP BY product_id")
    for row in cur.fetchall():
        pid = row["product_id"]
        if pid == "CTH":
            report["notes_cth"] = row[1]
        elif pid == "ZBC":
            report["notes_zbc"] = row[1]
        else:
            report["notes_other_product"] += row[1]
    cur.execute("SELECT COUNT(*) FROM canonical_data")
    report["canonical_total"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM canonical_data WHERE rule_version IS NOT NULL AND rule_version != ''")
    report["canonical_with_rule_version"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM canonical_data WHERE product_id='CTH'")
    report["canonical_cth"] = cur.fetchone()[0]
    try:
        cur.execute("SELECT COUNT(*) FROM historical_import_log")
        report["import_log_count"] = cur.fetchone()[0]
    except sqlite3.OperationalError:
        report["import_log_count"] = -1
    try:
        cur.execute("SELECT COUNT(*) FROM rule_version_registry")
        report["rule_versions_registered"] = cur.fetchone()[0]
    except sqlite3.OperationalError:
        report["rule_versions_registered"] = -1
    if report["notes_without_rule_version"] > 0:
        report["warnings"].append(
            f"{report['notes_without_rule_version']} notes have no rule_version "
            f"(pre-Phase15 historical data) - these must NOT be silently overwritten by reprocess.py")
    conn.close()
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ZBC Phase15 Historical Data Importer")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", type=str)
    parser.add_argument("--product", type=str, default="CTH")
    args = parser.parse_args()
    if args.audit:
        print(json.dumps(verify_historical_integrity(), ensure_ascii=False, indent=2))
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            records = json.load(f)
        stats = import_historical_batch(records, product_id=args.product, dry_run=args.dry_run)
        print(json.dumps({k: v for k, v in stats.items() if k != "details"}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
