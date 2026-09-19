# -*- coding: utf-8 -*-
"""ZBC → OSAI 证据自动流转（对账 P1-8）——只读、旁路、增量、可审计。

合法流向：ZBC（生产事实）→ Result/Evidence → OSAI（学习）。
设计约束：
- 源库一律 `mode=ro` 只读打开，物理上不可能写生产库；
- 只导出「已核准」证据：notes 必须 is_taikoo_verified=1（过主体口径），events 取 fact_status=verified；
- 白名单字段投影 + 复用 safe_collection 文本脱敏，天然最小化 PII，剔除 xsec_token/作者身份字段；
- 增量水位（按各表 id）幂等；产物 JSONL + manifest（含 sha256、production_unchanged=true，回应契约 V-06）；
- 默认写到本仓 outbox，不直接写 OSAI 仓库（解耦，由同步流程人工/自动带入），零网络。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:  # 同仓零副作用契约层
    from lumenis.system.collector.adapters.safe_collection import redact_text
except Exception:  # pragma: no cover - 兜底，不允许因脱敏缺失而导出明文联系方式
    import re
    _PATTERNS = [
        (re.compile(r"1[3-9]\d{9}"), "[PHONE]"),
        (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    ]

    def redact_text(s):  # type: ignore
        if not s:
            return s, 0
        hits = 0
        for p, r in _PATTERNS:
            s, n = p.subn(r, s)
            hits += n
        return s, hits

EXPORT_SCHEMA = "zbc.evidence-export.v1"

# 白名单投影：只导出学习所需字段，作者身份/凭证一律不带
NOTE_FIELDS = [
    "id", "note_id", "title", "content", "url", "likes", "comments", "collects",
    "shares", "publish_datetime", "captured_at", "sentiment", "risk_level",
    "source_platform", "matched_keywords", "subject_type", "is_taikoo_verified",
    "negative_confirmed",
]
EVENT_FIELDS = [
    "id", "event_key", "title", "summary", "fact_status", "risk_level",
    "mention_count", "source_count", "first_seen", "last_seen", "status",
    "event_date", "negative_confirmed",
]
REPORT_FIELDS = [
    "id", "report_type", "report_date", "period_start", "period_end",
    "total_notes", "positive_count", "neutral_count", "negative_count",
    "high_risk_count", "medium_risk_count", "low_risk_count",
    "total_engagements", "summary", "executive_summary", "generated_at",
]
# 即使在白名单内，这些键的文本值也要走联系方式脱敏
REDACT_TEXT_KEYS = {"title", "content", "summary", "executive_summary"}
# 绝不能出现在导出里的凭证/身份键（双保险）
FORBIDDEN_KEYS = {
    "xsec_token", "author_id", "author_nickname", "author_avatar", "cover",
    "cookie", "token", "api_key", "secret",
}


def _strip_token_url(url):
    if not isinstance(url, str):
        return url
    # 去掉 xsec_token / xsec_source 这类带凭证性质的 query
    base = url.split("?", 1)[0]
    return base


def project_row(row: sqlite3.Row | dict, fields: List[str]) -> Dict:
    d = dict(row)
    out = {}
    redacted = 0
    for k in fields:
        if k not in d or d[k] is None:
            continue
        v = d[k]
        if k == "url":
            v = _strip_token_url(v)
        if k in REDACT_TEXT_KEYS and isinstance(v, str):
            nv, hits = redact_text(v)
            redacted += hits
            v = nv
        out[k] = v
    return out, redacted


def _assert_no_forbidden(records: List[Dict]):
    for rec in records:
        for k in rec:
            assert k not in FORBIDDEN_KEYS, f"证据导出混入禁带字段: {k}"


def _safe_identifier(name: str) -> str:
    """校验SQL标识符仅含安全字符。"""
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name or ''):
        raise ValueError(f"非法SQL标识符: {name!r}")
    return name


def _fetch(conn, table, fields, where, params):
    # 只 SELECT 实际存在的列，兼容历史库缺列；fields 顺序即白名单投影顺序
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({_safe_identifier(table)})")}
    use = [f for f in fields if f in existing]
    cols = ", ".join(use)
    _safe_table = _safe_identifier(table)
    _safe_cols = ", ".join(_safe_identifier(c) for c in use)
    cur = conn.execute(f"SELECT {_safe_cols} FROM {_safe_table} WHERE {where}", params)
    rows = cur.fetchall()
    records, redacted = [], 0
    for r in rows:
        rec, n = project_row(r, use)
        redacted += n
        records.append(rec)
    return records, redacted


def build_export(conn: sqlite3.Connection, watermark: Optional[Dict[str, int]] = None):
    """纯读取：返回 (records_by_kind, new_watermark, redacted_count)。不写任何库。"""
    watermark = dict(watermark or {})
    out: Dict[str, List[Dict]] = {}
    redacted_total = 0

    notes, n1 = _fetch(
        conn, "notes", NOTE_FIELDS,
        "is_taikoo_verified=1 AND id>? ORDER BY id ASC", (watermark.get("notes", 0),))
    events, n2 = _fetch(
        conn, "events", EVENT_FIELDS,
        "COALESCE(fact_status,'') IN ('confirmed','partially_confirmed') AND id>? ORDER BY id ASC",
        (watermark.get("events", 0),))
    reports, n3 = _fetch(
        conn, "daily_reports", REPORT_FIELDS,
        "id>? ORDER BY id ASC", (watermark.get("daily_reports", 0),))

    for kind, recs in (("notes", notes), ("events", events), ("daily_reports", reports)):
        _assert_no_forbidden(recs)
        out[kind] = recs
    redacted_total = n1 + n2 + n3

    new_wm = {
        "notes": max([r["id"] for r in notes], default=watermark.get("notes", 0)),
        "events": max([r["id"] for r in events], default=watermark.get("events", 0)),
        "daily_reports": max([r["id"] for r in reports], default=watermark.get("daily_reports", 0)),
    }
    return out, new_wm, redacted_total


def build_manifest(records_by_kind, new_watermark, redacted_count, version="5.9.9"):
    counts = {k: len(v) for k, v in records_by_kind.items()}
    record_ids = sorted(r["id"] for kind in records_by_kind for r in records_by_kind[kind])
    return {
        "schema": EXPORT_SCHEMA,
        "source": "zbc",
        "destination": "osai",
        "app_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "total": sum(counts.values()),
        "redacted_count": redacted_count,
        "watermark": new_watermark,
        # 契约 V-06：证据导出绝不改变生产
        "production_unchanged": True,
        "approval_basis": {
            "notes": "is_taikoo_verified=1（过 SUBJECT 主体口径）",
            "events": "fact_status in (confirmed, partially_confirmed)",
            "daily_reports": "已生成日报",
        },
        "record_ids": record_ids,
    }


def _sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def export_evidence(db_path: str, outbox_dir: str,
                    version: str = "5.9.9", watermark_path: Optional[str] = None):
    """端到端只读导出。db_path 内部强制 ro；返回 manifest dict。"""
    os.makedirs(outbox_dir, exist_ok=True)
    watermark_path = watermark_path or os.path.join(outbox_dir, "_watermark.json")
    wm = {}
    if os.path.exists(watermark_path):
        wm = json.load(open(watermark_path, encoding="utf-8"))

    uri = db_path if db_path.startswith("file:") else "file:" + db_path.replace("\\", "/")
    if "mode=ro" not in uri:
        uri += ("&" if "?" in uri else "?") + "mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        records, new_wm, redacted = build_export(conn, wm)
    finally:
        conn.close()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    jsonl_path = os.path.join(outbox_dir, f"zbc-evidence-{ts}.jsonl")
    with open(jsonl_path, "w", encoding="utf-8", newline="") as f:
        for kind in ("notes", "events", "daily_reports"):
            for rec in records[kind]:
                f.write(json.dumps({"kind": kind, **rec}, ensure_ascii=False) + "\n")

    manifest = build_manifest(records, new_wm, redacted, version=version)
    manifest["jsonl"] = os.path.basename(jsonl_path)
    manifest["sha256"] = _sha256_file(jsonl_path)
    man_path = os.path.join(outbox_dir, f"zbc-evidence-{ts}.manifest.json")
    with open(man_path, "w", encoding="utf-8", newline="") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(watermark_path, "w", encoding="utf-8", newline="") as f:
        json.dump(new_wm, f, ensure_ascii=False, indent=2)
    return manifest