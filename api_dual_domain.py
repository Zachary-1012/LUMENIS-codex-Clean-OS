# -*- coding: utf-8 -*-
"""
ZBC API Dual-Domain Namespace（双域核心扩展）
================================================
三个独立域路由蓝图：
  - zbmp_bp: /api/zbmp/*  多品牌平台域
  - cth_bp:  /api/cth/*   太古汇生产真相域
  - system_bp: /api/system/*  系统基础设施域

每个端点：
  1. 从请求头 X-Domain-Id / X-Product-Id 或 session 解析域身份
  2. 设置线程 SubjectContext + DomainContext
  3. 读真实数据库（canonical_data / notes / web_mentions / runtime_guardian）
  4. 返回统一 JSON: {success, data, error, domain_id, product_id}

Compatibility Layer：现有 /api/* 端点保持不变，本模块仅新增域命名空间端点。
硬约束：禁止假数据/Mock，禁止吞异常，ZBMP 不读 CTH 专项字段。
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime as _datetime, timedelta as _timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, g

from domain_isolation import (
    DomainContext,
    DOMAIN_CTH,
    DOMAIN_ZBMP,
    DOMAIN_SYSTEM,
    PRODUCT_CTH,
    PRODUCT_ZBMP,
    PRODUCT_SYSTEM,
    domain_summary,
    get_domain_context,
    set_domain_context,
    clear_domain_context,
    domain_to_product,
    product_to_domain,
)
from subject_context import (
    CTH_BRAND_KEY,
    PRODUCT_CTH as SC_PRODUCT_CTH,
    PRODUCT_ZBMP as SC_PRODUCT_ZBMP,
    SubjectContext,
    set_thread_context,
    clear_thread_context,
    get_subject_context,
)
from domain_adapter import get_adapter, CTH_ONLY_FIELDS, ZBMP_ONLY_FIELDS
from lumenis.shared.database import get_repository

# ---------------------------------------------------------------------------
# 数据库连接：统一通过 Shared Database repository
# ---------------------------------------------------------------------------
def _get_conn() -> sqlite3.Connection:
    return get_repository().connect(timeout=15)


# ---------------------------------------------------------------------------
# 统一响应格式
# ---------------------------------------------------------------------------
def _api_response(data: Any = None, error: str = "",
                  domain_id: str = "", product_id: str = "",
                  status: int = 200):
    """统一 JSON 响应格式：{success, data, error, domain_id, product_id}"""
    success = error == ""
    resp = {
        "success": success,
        "data": data if data is not None else {},
        "error": error,
        "domain_id": domain_id,
        "product_id": product_id,
    }
    return jsonify(resp), status


def _resolve_domain_from_request() -> Dict[str, str]:
    """从请求头 / session / 查询参数解析域身份。

    优先级：X-Domain-Id header > session domain_id > ?domain_id= > 默认 cth
    product_id 从 domain_id 映射，或从 X-Product-Id 显式指定。
    """
    domain_id = ""
    product_id = ""

    # 1. Header
    domain_id = request.headers.get("X-Domain-Id", "").strip().lower()
    product_id = request.headers.get("X-Product-Id", "").strip().upper()

    # 2. Session
    if not domain_id:
        try:
            domain_id = (request.session.get("domain_id") or "").strip().lower()
        except Exception:
            pass
    if not product_id:
        try:
            product_id = (request.session.get("product_id") or "").strip().upper()
        except Exception:
            pass

    # 3. Query param
    if not domain_id:
        domain_id = request.args.get("domain_id", "").strip().lower()
    if not product_id:
        product_id = request.args.get("product_id", "").strip().upper()

    # 4. 映射 + 默认
    if domain_id and domain_id not in (DOMAIN_CTH, DOMAIN_ZBMP, DOMAIN_SYSTEM):
        domain_id = DOMAIN_CTH  # 生产安全默认
    if not domain_id:
        domain_id = DOMAIN_CTH

    if not product_id:
        product_id = domain_to_product(domain_id)
    elif product_id not in (PRODUCT_CTH, PRODUCT_ZBMP, PRODUCT_SYSTEM):
        product_id = domain_to_product(domain_id)

    return {"domain_id": domain_id, "product_id": product_id}


def _setup_domain_context(domain_id: str, product_id: str) -> DomainContext:
    """设置线程级 DomainContext + SubjectContext。CTH 保护强制主体。"""
    brand_key = CTH_BRAND_KEY if domain_id == DOMAIN_CTH else ""
    ctx = DomainContext(
        domain_id=domain_id,
        product_id=product_id,
        brand_key=brand_key,
        subject_id=brand_key.upper().replace("-", "_").replace(" ", "_") if brand_key else "",
    )
    set_domain_context(ctx)

    # 同步设置 SubjectContext（兼容现有体系）
    subject_ctx = SubjectContext(
        subject_id=ctx.subject_id or "UNKNOWN",
        brand_key=ctx.brand_key or "default",
        product_id=product_id,
    )
    set_thread_context(subject_ctx)
    g.domain_context = ctx
    g.subject_context = subject_ctx
    return ctx


def _teardown_domain_context():
    """请求结束后清除线程上下文（防止线程复用泄漏）。"""
    clear_domain_context()
    clear_thread_context()


# ---------------------------------------------------------------------------
# 蓝图定义
# ---------------------------------------------------------------------------
zbmp_bp = Blueprint("zbmp_api", __name__, url_prefix="/api/zbmp")
cth_bp = Blueprint("cth_api", __name__, url_prefix="/api/cth")
system_bp = Blueprint("system_api", __name__, url_prefix="/api/system")


# ---------------------------------------------------------------------------
# ZBMP canonical snapshot
# ---------------------------------------------------------------------------
# ZBMP is a market-intelligence consumer of the canonical layer.  It must not
# infer a brand from a CTH author, source, or an unverified row in notes.  This
# snapshot is the single read path shared by the ZBMP APIs and Experience
# screen bindings; it intentionally does not create tables or write data.
def _optional_int(value: Any) -> Optional[int]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sum_optional(values: List[Any]) -> Optional[int]:
    observed = [_optional_int(value) for value in values]
    observed = [value for value in observed if value is not None]
    return sum(observed) if observed else None


def _canonical_from_row(row: sqlite3.Row):
    """Build the existing CanonicalRecord without inventing missing columns."""
    from canonical_data import CanonicalRecord

    keys = set(row.keys())
    values = {}
    for field_name in CanonicalRecord.__dataclass_fields__:
        if field_name in keys and row[field_name] is not None:
            values[field_name] = row[field_name]
    return CanonicalRecord(**values)


def _safe_zbmp_record(row: sqlite3.Row, adapter: Any) -> Optional[Dict[str, Any]]:
    """Adapt one already domain-filtered row and retain provenance only."""
    try:
        record = _canonical_from_row(row)
        domain_record = adapter.to_domain(record)
    except (TypeError, ValueError):
        return None

    raw = dict(row)
    safe = domain_record.to_dict()
    # These are generic trace fields, not CTH-specific data.  Keeping them at
    # the view boundary makes source -> canonical -> UI traceable without
    # exposing the rest of the raw row.
    for key in (
        "source_id", "external_id", "source_type", "source_table",
        "source_keyword", "provenance", "content_hash", "evidence_ref",
        "raw_ref", "verification_status", "quality_status",
    ):
        if key in raw:
            safe[key] = raw.get(key)

    # A brand is only a brand when an explicitly verified field exists.  The
    # current canonical schema has neither field, so current output is
    # intentionally empty instead of treating author_name as brand_key.
    if "brand_key" in raw and "brand_key_verified" in raw and raw.get("brand_key_verified"):
        brand_key = str(raw.get("brand_key") or "").strip()
        if brand_key:
            safe["brand_key"] = brand_key
    return safe


def _build_zbmp_brands(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for record in records:
        brand_key = str(record.get("brand_key") or "").strip()
        if not brand_key:
            continue
        item = grouped.setdefault(brand_key, {
            "brand_key": brand_key,
            "platforms": set(),
            "record_count": 0,
            "total_likes": [],
            "total_comments": [],
            "domain": DOMAIN_ZBMP,
        })
        platform = str(record.get("source_platform") or "").strip()
        if platform:
            item["platforms"].add(platform)
        item["record_count"] += 1
        item["total_likes"].append(record.get("engagement_likes"))
        item["total_comments"].append(record.get("engagement_comments"))

    result = []
    for item in grouped.values():
        result.append({
            "brand_key": item["brand_key"],
            "platforms": sorted(item["platforms"]),
            "record_count": item["record_count"],
            "total_likes": _sum_optional(item["total_likes"]),
            "total_comments": _sum_optional(item["total_comments"]),
            "domain": item["domain"],
        })
    result.sort(key=lambda value: (-value["record_count"], value["brand_key"]))
    return result[:100]


def _zbmp_capture_trend(records: List[Dict[str, Any]], days: int = 14) -> Dict[str, Any]:
    today = _datetime.now().date()
    counts: Dict[str, Dict[str, int]] = {}
    for record in records:
        captured_at = str(record.get("captured_at") or "")
        date_key = captured_at[:10]
        if len(date_key) != 10:
            continue
        bucket = counts.setdefault(date_key, {"total": 0, "negative": 0})
        bucket["total"] += 1
        if str(record.get("sentiment") or "").lower() == "negative":
            bucket["negative"] += 1

    labels = []
    totals = []
    negatives = []
    for back in range(days - 1, -1, -1):
        day = today - _timedelta(days=back)
        key = day.isoformat()
        bucket = counts.get(key, {"total": 0, "negative": 0})
        labels.append(key[5:])
        totals.append(bucket["total"])
        negatives.append(bucket["negative"])
    return {"labels": labels, "total": totals, "negative": negatives}


def get_zbmp_product_snapshot() -> Dict[str, Any]:
    """Read the verified ZBMP canonical slice used by API and UI.

    The function deliberately treats a missing table, no ZBMP rows, and rows
    rejected by the domain adapter as NOT_COLLECTED.  It never falls back to
    the CTH ``notes``/``web_mentions`` tables and never fills missing metrics
    with fabricated zeros.
    """
    from canonical_data import PRODUCT_ZBMP

    snapshot: Dict[str, Any] = {
        "data_state": "NOT_COLLECTED",
        "records": [],
        "canonical_records": [],
        "brands": [],
        "total_records": 0,
        "errors": [],
        "metrics": {
            "total_notes": 0,
            "total_web_mentions": 0,
            "total_canonical_zbmp": 0,
            "total_engagement": {
                "likes": None, "comments": None, "collects": None, "shares": None,
            },
            "sentiment_distribution": {},
            "risk_distribution": {},
            "platform_distribution": {},
            "latest_capture": "",
            "capture_trend": {"labels": [], "total": [], "negative": []},
        },
    }

    conn = None
    try:
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM canonical_data "
                "WHERE product_id = ? AND domain_id = ? "
                "ORDER BY captured_at DESC",
                (PRODUCT_ZBMP, DOMAIN_ZBMP),
            ).fetchall()
        except sqlite3.Error as exc:
            # A missing canonical table means the domain has not collected
            # data; it is not an API failure and must not trigger table writes.
            snapshot["errors"].append(f"canonical_data unavailable: {exc}")
            return snapshot

        adapter = get_adapter(DOMAIN_ZBMP)
        safe_records = []
        rejected = 0
        for row in rows:
            safe = _safe_zbmp_record(row, adapter)
            if safe is None:
                rejected += 1
                continue
            safe_records.append(safe)

        if rejected:
            snapshot["errors"].append(f"rejected_domain_records={rejected}")

        snapshot["records"] = safe_records
        snapshot["canonical_records"] = safe_records[:200]
        snapshot["total_records"] = len(safe_records)
        snapshot["brands"] = _build_zbmp_brands(safe_records)
        if not safe_records:
            return snapshot

        metrics = snapshot["metrics"]
        metrics["total_canonical_zbmp"] = len(safe_records)
        metrics["total_notes"] = sum(
            1 for record in safe_records
            if record.get("source_type") in ("note", "collected_note")
        )
        metrics["total_web_mentions"] = sum(
            1 for record in safe_records if record.get("source_type") == "web_mention"
        )
        for field_name, output_name in (
            ("engagement_likes", "likes"),
            ("engagement_comments", "comments"),
            ("engagement_collects", "collects"),
            ("engagement_shares", "shares"),
        ):
            metrics["total_engagement"][output_name] = _sum_optional(
                [record.get(field_name) for record in safe_records]
            )

        for record in safe_records:
            platform = str(record.get("source_platform") or "unknown")
            metrics["platform_distribution"][platform] = (
                metrics["platform_distribution"].get(platform, 0) + 1
            )
            sentiment = str(record.get("sentiment") or "").strip()
            if sentiment:
                metrics["sentiment_distribution"][sentiment] = (
                    metrics["sentiment_distribution"].get(sentiment, 0) + 1
                )
            risk = str(record.get("risk_level") or "").strip()
            if risk:
                metrics["risk_distribution"][risk] = (
                    metrics["risk_distribution"].get(risk, 0) + 1
                )

        captures = [str(record.get("captured_at") or "") for record in safe_records]
        captures = [value for value in captures if value]
        metrics["latest_capture"] = max(captures) if captures else ""
        metrics["capture_trend"] = _zbmp_capture_trend(safe_records)
        snapshot["data_state"] = "READY"
        return snapshot
    except Exception as exc:
        snapshot["errors"].append(str(exc))
        return snapshot
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------------
# before_request / after_request 钩子（每个蓝图独立）
# ---------------------------------------------------------------------------
@zbmp_bp.before_request
def _zbmp_before():
    identity = _resolve_domain_from_request()
    # ZBMP 蓝图强制 domain_id=zbmp
    identity["domain_id"] = DOMAIN_ZBMP
    identity["product_id"] = PRODUCT_ZBMP
    _setup_domain_context(identity["domain_id"], identity["product_id"])


@zbmp_bp.after_request
def _zbmp_after(response):
    _teardown_domain_context()
    return response


@cth_bp.before_request
def _cth_before():
    identity = _resolve_domain_from_request()
    # CTH 蓝图强制 domain_id=cth + 主体保护
    identity["domain_id"] = DOMAIN_CTH
    identity["product_id"] = PRODUCT_CTH
    _setup_domain_context(identity["domain_id"], identity["product_id"])


@cth_bp.after_request
def _cth_after(response):
    _teardown_domain_context()
    return response


@system_bp.before_request
def _system_before():
    identity = _resolve_domain_from_request()
    identity["domain_id"] = DOMAIN_SYSTEM
    identity["product_id"] = PRODUCT_SYSTEM
    _setup_domain_context(identity["domain_id"], identity["product_id"])


@system_bp.after_request
def _system_after(response):
    _teardown_domain_context()
    return response


# ===========================================================================
# ZBMP 端点
# ===========================================================================
@zbmp_bp.route("/overview", methods=["GET"])
def zbmp_overview():
    """ZBMP 品牌总览：只读经过域校验的 ZBMP canonical slice。"""
    try:
        snapshot = get_zbmp_product_snapshot()
        metrics = snapshot["metrics"]
        data = {
            "data_state": snapshot["data_state"],
            "brands": snapshot["brands"],
            "total_records": snapshot["total_records"],
            "by_platform": metrics["platform_distribution"],
            "by_sentiment": metrics["sentiment_distribution"],
            "canonical_records": snapshot["canonical_records"],
            "errors": snapshot["errors"],
        }
        return _api_response(data=data, domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP, status=500)


@zbmp_bp.route("/brands", methods=["GET"])
def zbmp_brands():
    """ZBMP 品牌列表：只接受 canonical 中显式且已验证的 brand_key。"""
    try:
        snapshot = get_zbmp_product_snapshot()
        data = {
            "data_state": snapshot["data_state"],
            "brands": snapshot["brands"],
            "total_brands": len(snapshot["brands"]),
            "errors": snapshot["errors"],
        }
        return _api_response(data=data, domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP, status=500)


@zbmp_bp.route("/metrics", methods=["GET"])
def zbmp_metrics():
    """ZBMP 指标：从同一 canonical snapshot 计算，避免重复口径。"""
    try:
        snapshot = get_zbmp_product_snapshot()
        metrics = dict(snapshot["metrics"])
        metrics["data_state"] = snapshot["data_state"]
        metrics["errors"] = snapshot["errors"]
        return _api_response(data=metrics, domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP, status=500)


# ===========================================================================
# CTH 端点
# ===========================================================================
@cth_bp.route("/overview", methods=["GET"])
def cth_overview():
    """CTH 太古汇总览：从 canonical_data 按 product_id=CTH 聚合 + subject_rules 过滤。

    读真实数据：canonical_data(product_id=CTH)、notes、web_mentions。
    CTH 保护：强制 subject=guangzhou_taikoo_hui，不读 ZBMP 多品牌字段。
    """
    try:
        conn = _get_conn()
        data = {
            "subject": "guangzhou_taikoo_hui",
            "total_canonical": 0,
            "total_notes": 0,
            "total_web_mentions": 0,
            "by_platform": {},
            "by_sentiment": {},
            "by_risk": {},
            "recent_records": [],
            "engagement_summary": {},
        }

        # canonical_data CTH 聚合
        try:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM canonical_data WHERE product_id = ?",
                (PRODUCT_CTH,)
            ).fetchone()
            data["total_canonical"] = row["c"] if row else 0

            # 最近记录（通过 CTHAdapter 剥离 ZBMP 字段）
            rows = conn.execute(
                "SELECT * FROM canonical_data WHERE product_id = ? ORDER BY captured_at DESC LIMIT 20",
                (PRODUCT_CTH,)
            ).fetchall()
            adapter = get_adapter(DOMAIN_CTH)
            from canonical_data import CanonicalRecord
            recent = []
            for r in rows:
                rec_dict = dict(r)
                rec = CanonicalRecord(**{k: v for k, v in rec_dict.items()
                                          if k in CanonicalRecord.__dataclass_fields__})
                try:
                    domain_rec = adapter.to_domain(rec)
                    recent.append(domain_rec.to_dict())
                except ValueError:
                    continue
            data["recent_records"] = recent
        except Exception as e:
            data["canonical_error"] = str(e)

        # notes 统计（CTH 主体过滤：subject_hit 逻辑简化为关键词匹配）
        try:
            row = conn.execute("SELECT COUNT(*) as c FROM notes").fetchone()
            data["total_notes"] = row["c"] if row else 0

            # 平台分布
            rows = conn.execute(
                "SELECT source_platform, COUNT(*) as cnt FROM notes GROUP BY source_platform"
            ).fetchall()
            data["by_platform"] = {r["source_platform"] or "unknown": r["cnt"] for r in rows}

            # 情感分布
            rows = conn.execute(
                "SELECT sentiment, COUNT(*) as cnt FROM notes WHERE sentiment != '' GROUP BY sentiment"
            ).fetchall()
            data["by_sentiment"] = {r["sentiment"]: r["cnt"] for r in rows}

            # 风险分布
            rows = conn.execute(
                "SELECT risk_level, COUNT(*) as cnt FROM notes WHERE risk_level != '' GROUP BY risk_level"
            ).fetchall()
            data["by_risk"] = {r["risk_level"]: r["cnt"] for r in rows}

            # 互动汇总
            row = conn.execute(
                "SELECT SUM(likes) as l, SUM(comments) as c, SUM(collects) as col, SUM(shares) as s FROM notes"
            ).fetchone()
            if row:
                data["engagement_summary"] = {
                    "likes": row["l"] or 0,
                    "comments": row["c"] or 0,
                    "collects": row["col"] or 0,
                    "shares": row["s"] or 0,
                }
        except Exception as e:
            data["notes_error"] = str(e)

        # web_mentions 统计
        try:
            row = conn.execute("SELECT COUNT(*) as c FROM web_mentions").fetchone()
            data["total_web_mentions"] = row["c"] if row else 0
        except Exception:
            pass

        conn.close()
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH, status=500)


@cth_bp.route("/events", methods=["GET"])
def cth_events():
    """CTH 事件列表：从 notes/canonical_data 中提取 event_hint 和话题事件。

    读真实数据：notes(topics/event_hint)、canonical_data(event_hint)。
    """
    try:
        conn = _get_conn()
        events = []

        # 从 canonical_data 提取事件
        try:
            rows = conn.execute(
                "SELECT canonical_id, title, event_hint, topics, tags, publish_datetime, "
                "captured_at, sentiment, risk_level, source_platform "
                "FROM canonical_data WHERE product_id = ? AND (event_hint != '' OR topics != '[]') "
                "ORDER BY captured_at DESC LIMIT 50",
                (PRODUCT_CTH,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                events.append({
                    "event_id": d["canonical_id"],
                    "title": d["title"],
                    "event_hint": d["event_hint"],
                    "topics": d["topics"],
                    "tags": d["tags"],
                    "publish_datetime": d["publish_datetime"],
                    "captured_at": d["captured_at"],
                    "sentiment": d["sentiment"],
                    "risk_level": d["risk_level"],
                    "platform": d["source_platform"],
                    "domain": DOMAIN_CTH,
                })
        except Exception as e:
            events.append({"error": f"canonical events: {e}"})

        # 从 notes 提取话题事件
        try:
            rows = conn.execute(
                "SELECT note_id, title, topics, publish_date, collected_at, "
                "sentiment, risk_level, source_platform "
                "FROM notes WHERE topics != '' AND topics IS NOT NULL AND topics != '[]' "
                "ORDER BY collected_at DESC LIMIT 30"
            ).fetchall()
            for r in rows:
                d = dict(r)
                events.append({
                    "event_id": f"note_{d['note_id']}",
                    "title": d["title"],
                    "event_hint": "",
                    "topics": d["topics"],
                    "tags": "[]",
                    "publish_datetime": d["publish_date"],
                    "captured_at": d["collected_at"],
                    "sentiment": d["sentiment"],
                    "risk_level": d["risk_level"],
                    "platform": d["source_platform"],
                    "domain": DOMAIN_CTH,
                })
        except Exception:
            pass

        conn.close()
        data = {"events": events, "total_events": len(events)}
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH, status=500)


@cth_bp.route("/xiaohongshu", methods=["GET"])
def cth_xiaohongshu():
    """CTH 小红书数据：从 notes 表筛选小红书平台的太古汇相关数据。

    读真实数据：notes(source_platform='xhs' 或 note_type 含 xhs)。
    CTH 保护：仅返回太古汇主体数据，不包含 ZBMP 多品牌字段。
    """
    try:
        conn = _get_conn()
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        # 筛选小红书数据（source_platform 包含 xhs 或 rednote）
        rows = conn.execute(
            "SELECT * FROM notes WHERE source_platform LIKE '%xhs%' "
            "OR source_platform LIKE '%rednote%' OR note_type LIKE '%xhs%' "
            "ORDER BY collected_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()

        records = []
        for r in rows:
            d = dict(r)
            # CTH 视图：剥离 ZBMP 多品牌字段，仅保留 CTH 相关字段
            records.append({
                "note_id": d.get("note_id", ""),
                "title": d.get("title", ""),
                "content": d.get("content", "")[:500],  # 截断长内容
                "url": d.get("url", ""),
                "author_nickname": d.get("author_nickname", ""),
                "publish_date": d.get("publish_date", ""),
                "collected_at": d.get("collected_at", ""),
                "sentiment": d.get("sentiment", ""),
                "sentiment_score": d.get("sentiment_score", 0),
                "risk_level": d.get("risk_level", ""),
                "likes": d.get("likes") or 0,
                "comments": d.get("comments") or 0,
                "collects": d.get("collects") or 0,
                "shares": d.get("shares") or 0,
                "topics": d.get("topics", "[]"),
                "is_taikoo_verified": bool(d.get("is_taikoo_verified", 0)),
                "platform": d.get("source_platform", "xhs"),
                "domain": DOMAIN_CTH,
            })

        # 统计
        total_row = conn.execute(
            "SELECT COUNT(*) as c FROM notes WHERE source_platform LIKE '%xhs%' "
            "OR source_platform LIKE '%rednote%' OR note_type LIKE '%xhs%'"
        ).fetchone()
        total = total_row["c"] if total_row else 0

        conn.close()
        data = {
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
            "platform": "xiaohongshu",
        }
        return _api_response(data=data, domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH, status=500)


# ===========================================================================
# System 端点
# ===========================================================================
@system_bp.route("/status", methods=["GET"])
def system_status():
    """系统状态：DB/Collector/AI/Guardian 健康度。

    读真实数据：runtime_guardian_workers、DB 连接状态、collector_automation 状态。
    """
    try:
        status = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "database": {"status": "unknown", "tables": 0},
            "collector": {"status": "unknown", "running": False},
            "ai": {"status": "unknown"},
            "guardian": {"status": "unknown", "workers": 0, "running": 0},
            "overall": "healthy",
        }

        # DB 健康度
        try:
            conn = _get_conn()
            tables = conn.execute(
                "SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'"
            ).fetchone()["c"]
            status["database"] = {"status": "healthy", "tables": tables}
            conn.close()
        except Exception as e:
            status["database"] = {"status": "error", "error": str(e)}
            status["overall"] = "degraded"

        # Guardian 健康度
        try:
            from runtime_guardian import get_guardian
            g = get_guardian("default")
            health = g.health_check()
            status["guardian"] = {
                "status": health.get("overall", "unknown"),
                "workers": health.get("workers", {}).get("total", 0),
                "running": health.get("workers", {}).get("running", 0),
                "failed": health.get("workers", {}).get("failed", 0),
                "dead": health.get("workers", {}).get("dead", 0),
                "dlq": health.get("dlq", {}),
            }
            if health.get("overall") == "degraded":
                status["overall"] = "degraded"
        except Exception as e:
            status["guardian"] = {"status": "error", "error": str(e)}

        # Collector 状态
        try:
            import collector_automation
            ca = collector_automation.get_collector_automation()
            ca_status = ca.get_status()
            status["collector"] = {
                "status": "running" if ca_status.get("is_running") else "idle",
                "running": ca_status.get("is_running", False),
                "current_task": ca_status.get("current_task", {}).get("id") if ca_status.get("current_task") else None,
                "state": ca_status.get("state", "unknown"),
            }
        except Exception as e:
            status["collector"] = {"status": "unknown", "error": str(e)}

        # AI 状态（检查 ai_analyzer 是否可导入）
        try:
            import ai_analyzer
            status["ai"] = {"status": "available", "module": "ai_analyzer"}
        except Exception as e:
            status["ai"] = {"status": "unavailable", "error": str(e)}

        return _api_response(data=status, domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM, status=500)


@system_bp.route("/runtime-workers", methods=["GET"])
def system_runtime_workers():
    """Runtime worker/task 列表，按域分组（详细视图）。

    注意：/api/system/runtime 已由 lumenis_agg_api 提供（含 runtime_by_domain 字段），
    本端点提供更详细的 worker/task 列表，统一 JSON 格式。
    读真实数据：runtime_guardian_workers（按 domain_id 分组）、runtime_guardian_dlq。
    """
    try:
        from runtime_guardian import get_guardian
        g = get_guardian("default")

        # 按域查询
        cth_tasks = g.get_tasks_by_domain(DOMAIN_CTH)
        zbmp_tasks = g.get_tasks_by_domain(DOMAIN_ZBMP)
        system_tasks = g.get_tasks_by_domain(DOMAIN_SYSTEM)

        # 全部 workers（含未分类）
        all_workers = g.list_workers()

        data = {
            "by_domain": {
                DOMAIN_CTH: {
                    "total_workers": cth_tasks["total_workers"],
                    "running": cth_tasks["running"],
                    "failed": cth_tasks["failed"],
                    "dlq_count": cth_tasks["dlq_count"],
                    "workers": [{"worker_id": w["worker_id"], "worker_name": w["worker_name"],
                                 "status": w["status"], "last_heartbeat_at": w.get("last_heartbeat_at", "")}
                                for w in cth_tasks["workers"]],
                },
                DOMAIN_ZBMP: {
                    "total_workers": zbmp_tasks["total_workers"],
                    "running": zbmp_tasks["running"],
                    "failed": zbmp_tasks["failed"],
                    "dlq_count": zbmp_tasks["dlq_count"],
                    "workers": [{"worker_id": w["worker_id"], "worker_name": w["worker_name"],
                                 "status": w["status"], "last_heartbeat_at": w.get("last_heartbeat_at", "")}
                                for w in zbmp_tasks["workers"]],
                },
                DOMAIN_SYSTEM: {
                    "total_workers": system_tasks["total_workers"],
                    "running": system_tasks["running"],
                    "failed": system_tasks["failed"],
                    "dlq_count": system_tasks["dlq_count"],
                    "workers": [{"worker_id": w["worker_id"], "worker_name": w["worker_name"],
                                 "status": w["status"], "last_heartbeat_at": w.get("last_heartbeat_at", "")}
                                for w in system_tasks["workers"]],
                },
            },
            "total_workers_all": len(all_workers),
            "guardian_health": g.health_check().get("overall", "unknown"),
        }

        return _api_response(data=data, domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM, status=500)


@system_bp.route("/domains", methods=["GET"])
def system_domains():
    """域隔离总览：调用 domain_isolation.domain_summary()。

    返回所有域的边界定义、当前域上下文、隔离资源/共享资源。
    """
    try:
        summary = domain_summary()
        # 补充各域 worker 数量
        try:
            from runtime_guardian import get_guardian
            g = get_guardian("default")
            for did in (DOMAIN_CTH, DOMAIN_ZBMP, DOMAIN_SYSTEM):
                tasks = g.get_tasks_by_domain(did)
                if did in summary.get("domains", {}):
                    summary["domains"][did]["runtime_workers"] = tasks["total_workers"]
                    summary["domains"][did]["running_workers"] = tasks["running"]
        except Exception:
            pass

        return _api_response(data=summary, domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM)
    except Exception as e:
        return _api_response(error=str(e), domain_id=DOMAIN_SYSTEM, product_id=PRODUCT_SYSTEM, status=500)


# ---------------------------------------------------------------------------
# 注册函数（供 app.py 调用）
# ---------------------------------------------------------------------------
def register_dual_domain_api(app):
    """注册三个双域 API 蓝图到 Flask app。

    用法（在 app.py 中）：
        from api_dual_domain import register_dual_domain_api
        register_dual_domain_api(app)
    """
    app.register_blueprint(zbmp_bp)
    app.register_blueprint(cth_bp)
    app.register_blueprint(system_bp)
    print("[dual-domain] API blueprints registered: /api/zbmp, /api/cth, /api/system")
    return app
