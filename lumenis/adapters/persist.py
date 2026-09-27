# -*- coding: utf-8 -*-
"""
采集结果统一入库服务（Persistence Service）
=================================================
把各适配器返回的标准化 CollectedNote 落到现有 monitor.db，不新建重复表：

  · 社媒类（抖音 / Instagram / 小红书 / 知乎 / 大众点评 / 什么值得买 / 微博 / B站）
    → notes 表，以 source_platform 区分平台，note_id / url 去重，已存在则更新互动量；
  · 网页新闻类（搜狗 / Google / Bing / 百度 / 搜狗微信 / 豆包搜索）
    → web_mentions 表，canonical_url 去重；
  · 每次采集运行（含六态、抓取/采纳/去重计数、错误）→ web_runs 表，
    作为“全局采集健康状态中心”的数据底座。

严格区分发布时间与采集时间：publish_date/published_at 只取平台发布时间，
captured_at/fetched_at 由本服务写入当前采集时刻，二者不混用。
"""
import os
import json
import time
import sqlite3
import hashlib
import datetime
import re
from typing import List, Dict, Optional
from .base import CollectedNote, AdapterResult
from lumenis.shared.database import get_repository, main_db_path
from lumenis.shared.database.scope import ScopeValidationError, normalize_product_domain

import logging
logger = logging.getLogger(__name__)

# T4 Canonical Data 旁路接入（不影响主流程，失败仅记录日志）
try:
    from canonical_data import (
        collected_note_to_canonical, persist_canonical, ensure_canonical_table,
    )
    _CANONICAL_AVAILABLE = True
except Exception as _e:
    logger.warning(f"[T4] canonical_data 旁路不可用: {_e}")
    _CANONICAL_AVAILABLE = False


def _canonical_bypass(con, n, keyword, source_platform=""):
    """T4 旁路：将 CollectedNote 同步写入 canonical_data 表。

    调用链：CollectedNote -> collected_note_to_canonical() -> persist_canonical() -> canonical_data
    文件: canonical_data.py:320 (collected_note_to_canonical), :180 (persist_canonical)

    严格旁路：任何异常不影响主流程，仅记录日志。
    publish_datetime（平台发布时间）与 captured_at（采集时间）在 canonical_data 内部分离。
    """
    if not _CANONICAL_AVAILABLE:
        return
    try:
        ensure_canonical_table(main_db_path())
        rec = collected_note_to_canonical(n, source_platform=source_platform, keyword=keyword)
        persist_canonical(con, rec)
    except Exception as e:
        logger.warning(f"[T4] canonical 旁路写入失败（不影响主流程）: {e}")


def persist_existing_note_scope(
    con: sqlite3.Connection,
    note_ids: List[str],
    *,
    product_id: str,
    domain_id: str,
    subject_id: str = None,
    brand_focus_id: str = None,
    scope_evidence_ref: int,
) -> int:
    """Bind imported raw notes and Canonical rows to one signed exact scope.

    The collector supplies the raw identities and its completed Evidence id.
    The caller owns the connection and transaction; this savepoint keeps a
    partial raw/Canonical promotion from escaping if any item fails.
    """
    from canonical_data import ensure_canonical_table, note_to_canonical
    from lumenis.shared.database.scope import (
        ScopeValidationError, normalize_product_domain, resolve_scope,
    )
    from lumenis.shared.evidence.store import classify_evidence_integrity

    if not _CANONICAL_AVAILABLE:
        raise ScopeValidationError("Canonical writer is unavailable")
    product, domain = normalize_product_domain(product_id, domain_id)
    exact = resolve_scope(
        con, product_id=product, domain_id=domain,
        subject_id=subject_id, brand_focus_id=brand_focus_id,
    )
    if exact.status != "UNVERIFIED":
        raise ScopeValidationError("an exact registered Subject or BrandFocus is required")
    if type(scope_evidence_ref) is not int or scope_evidence_ref < 1:
        raise ScopeValidationError("a positive signed Evidence id is required")
    if not isinstance(note_ids, (list, tuple)):
        raise ScopeValidationError("raw note ids must be a bounded sequence")
    ids = [value for value in note_ids if isinstance(value, str) and value]
    if not ids or len(ids) > 100 or len(ids) != len(note_ids) or len(set(ids)) != len(ids):
        raise ScopeValidationError("raw note ids must be nonempty and unique")

    evidence_cursor = con.execute(
        "SELECT * FROM app_evidence_records WHERE id=?", (scope_evidence_ref,)
    )
    evidence_row = evidence_cursor.fetchone()
    if evidence_row is None:
        raise ScopeValidationError("scope Evidence is missing")
    evidence = dict(zip((item[0] for item in evidence_cursor.description), evidence_row))
    assurance = classify_evidence_integrity(evidence)
    if (
        not assurance.get("verified")
        or assurance.get("assurance") != "writer-authenticated"
        or str(evidence.get("result") or "").upper() != "PASS"
        or str(evidence.get("status") or "").lower() != "verified"
        or evidence.get("product_id") != product
        or evidence.get("domain_id") != domain
    ):
        raise ScopeValidationError("scope Evidence is not verified for this domain")
    try:
        inputs = json.loads(evidence.get("inputs_json") or "")
    except (TypeError, ValueError) as exc:
        raise ScopeValidationError("scope Evidence inputs are invalid") from exc
    marker = {"domain_id": domain, "product_id": product, "global": False}
    marker["subject_id" if domain == "cth" else "brand_focus_id"] = (
        exact.subject_id if domain == "cth" else exact.brand_focus_id
    )
    if (
        not isinstance(inputs, dict)
        or inputs.get("_lumenis_scope") != marker
        or not isinstance(inputs.get("source_ids"), list)
        or any(note_id not in inputs["source_ids"] for note_id in ids)
    ):
        raise ScopeValidationError("scope Evidence does not cover these exact raw notes")

    columns = {
        row[1] for row in con.execute("PRAGMA table_info(notes)").fetchall()
    }
    required = {
        "note_id", "product_id", "domain_id", "subject_id", "brand_focus_id",
        "scope_status", "scope_evidence_ref",
    }
    if not required.issubset(columns):
        raise ScopeValidationError("raw note scope storage is unavailable")
    con.execute("SAVEPOINT persist_existing_note_scope")
    try:
        ensure_canonical_table(connection=con)
        synced = 0
        for note_id in ids:
            note_cursor = con.execute("SELECT * FROM notes WHERE note_id=?", (note_id,))
            row = note_cursor.fetchone()
            if row is None:
                raise ScopeValidationError("imported raw note is missing")
            note = dict(zip((item[0] for item in note_cursor.description), row))
            prior_subject = note.get("subject_id") or None
            prior_brand = note.get("brand_focus_id") or None
            prior_status = str(note.get("scope_status") or "").upper()
            if prior_subject not in (None, exact.subject_id) or prior_brand not in (
                None, exact.brand_focus_id
            ):
                raise ScopeValidationError("existing raw identity belongs to another scope")
            if prior_status == "VERIFIED":
                if str(note.get("scope_evidence_ref") or "") != str(scope_evidence_ref):
                    raise ScopeValidationError("verified raw provenance cannot be rewritten")
                canonical_row = con.execute(
                    "SELECT subject_id, brand_focus_id, scope_status, scope_evidence_ref "
                    "FROM canonical_data WHERE external_id=? AND product_id=? LIMIT 1",
                    (note_id, product),
                ).fetchone()
                if (
                    canonical_row is None
                    or (canonical_row[0] or None) != exact.subject_id
                    or (canonical_row[1] or None) != exact.brand_focus_id
                    or canonical_row[2] != "VERIFIED"
                    or str(canonical_row[3] or "") != str(scope_evidence_ref)
                ):
                    raise ScopeValidationError("verified raw note lacks matching Canonical data")
                continue
            con.execute(
                "UPDATE notes SET product_id=?, domain_id=?, subject_id=?, "
                "brand_focus_id=?, scope_status='VERIFIED', scope_evidence_ref=? "
                "WHERE note_id=?",
                (product, domain, exact.subject_id, exact.brand_focus_id,
                 str(scope_evidence_ref), note_id),
            )
            note.update({
                "product_id": product, "domain_id": domain,
                "subject_id": exact.subject_id, "brand_focus_id": exact.brand_focus_id,
                "scope_status": "VERIFIED", "scope_evidence_ref": str(scope_evidence_ref),
            })
            canonical = note_to_canonical(note, product_id=product)
            canonical.domain_id = domain
            canonical.subject_id = exact.subject_id or ""
            canonical.brand_focus_id = exact.brand_focus_id or ""
            canonical.scope_status = "VERIFIED"
            canonical.scope_evidence_ref = str(scope_evidence_ref)
            persist_canonical(con, canonical)
            synced += 1
        con.execute("RELEASE SAVEPOINT persist_existing_note_scope")
        return synced
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT persist_existing_note_scope")
        con.execute("RELEASE SAVEPOINT persist_existing_note_scope")
        raise


def _scope_correction_resource(
    *, platform: str, domain_id: str, entity_id: str,
    old_evidence_id: int, source_ids: List[str], correction_key: str,
) -> str:
    digest = hashlib.sha256("\n".join(sorted(source_ids)).encode("utf-8")).hexdigest()
    return (
        f"scope-correction:unassign:{platform}:{domain_id}:{entity_id}:"
        f"evidence:{old_evidence_id}:ids:{digest}:change:{correction_key}"
    )


def scope_correction_approval_resource(
    *, platform: str, product_id: str, domain_id: str,
    expected_subject_id: Optional[str], expected_brand_focus_id: Optional[str],
    expected_scope_evidence_ref: int, source_ids: List[str], reason: str, actor: str,
) -> str:
    """Return the exact resource that must receive DATA_IMPORT approval."""
    product, domain = normalize_product_domain(product_id, domain_id)
    ids = sorted(source_ids)
    entity_id = expected_subject_id or expected_brand_focus_id or ""
    payload = {
        "platform": str(platform or "").strip().lower(), "product_id": product,
        "domain_id": domain, "expected_subject_id": expected_subject_id,
        "expected_brand_focus_id": expected_brand_focus_id,
        "expected_scope_evidence_ref": expected_scope_evidence_ref,
        "target_scope_status": "UNASSIGNED", "target_subject_id": None,
        "target_brand_focus_id": None, "source_ids": ids,
        "reason": reason.strip(), "actor": actor.strip(),
    }
    key = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return _scope_correction_resource(
        platform=payload["platform"], domain_id=domain, entity_id=entity_id,
        old_evidence_id=expected_scope_evidence_ref, source_ids=ids,
        correction_key=key,
    )


def _find_scope_correction(
    con: sqlite3.Connection, correction_key: str,
) -> Optional[Dict[str, object]]:
    from lumenis.shared.evidence.store import classify_evidence_integrity

    cursor = con.execute(
        "SELECT * FROM app_evidence_records WHERE feature_id='SCOPE_CORRECTION'"
    )
    names = [column[0] for column in cursor.description]
    for row in cursor.fetchall():
        evidence = dict(zip(names, row))
        try:
            inputs = json.loads(evidence.get("inputs_json") or "")
        except (TypeError, ValueError):
            continue
        correction = inputs.get("scope_correction") if isinstance(inputs, dict) else None
        if not isinstance(correction, dict) or correction.get("idempotency_key") != correction_key:
            continue
        if not classify_evidence_integrity(evidence).get("verified"):
            raise ScopeValidationError("prior scope correction Evidence is not signed")
        return evidence
    return None


def _validate_unassigned_correction_state(
    con: sqlite3.Connection, ids: List[str], platform: str,
    product: str, domain: str, correction_ref: int,
) -> None:
    from canonical_data import CANONICAL_TABLE

    for note_id in ids:
        raw = con.execute(
            "SELECT product_id,domain_id,subject_id,brand_focus_id,scope_status,"
            "scope_evidence_ref,source_platform FROM notes WHERE note_id=? LIMIT 1",
            (note_id,),
        ).fetchone()
        canonical = con.execute(
            f"SELECT product_id,domain_id,subject_id,brand_focus_id,scope_status,"
            f"scope_evidence_ref FROM {CANONICAL_TABLE} WHERE external_id=? LIMIT 1",
            (note_id,),
        ).fetchone()
        native = con.execute(
            "SELECT raw_data FROM platform_contents WHERE platform=? AND platform_content_id=? LIMIT 1",
            (platform, note_id),
        ).fetchone()
        try:
            native_data = json.loads(native[0] or "{}") if native else {}
        except (TypeError, ValueError):
            raise ScopeValidationError("corrected native source projection is invalid") from None
        if (
            raw is None
            or tuple(raw) != (product, domain, None, None, "UNASSIGNED", "", platform)
            or canonical is None
            or tuple(canonical) != (product, domain, "", "", "UNASSIGNED", "")
            or native is None
            or not isinstance(native_data, dict)
            or native_data.get("_lumenis_scope_correction_ref")
            != correction_ref
        ):
            raise ScopeValidationError(
                "prior correction Evidence exists but Raw and Canonical are not unassigned"
            )


def correct_existing_note_scope_to_unassigned(
    con: sqlite3.Connection,
    source_ids: List[str],
    *,
    platform: str,
    product_id: str,
    domain_id: str,
    expected_subject_id: Optional[str],
    expected_brand_focus_id: Optional[str],
    expected_scope_evidence_ref: int,
    reason: str,
    actor: str,
) -> Dict[str, object]:
    """Atomically append signed correction Evidence and unassign exact notes.

    Source content, timestamps, native metrics, author identity and the original
    collection Evidence are left untouched. Normal refresh cannot reassign a
    source once its correction Evidence exists.
    """
    from canonical_data import (
        CANONICAL_TABLE, ensure_canonical_table, persist_scope_correction,
    )
    from lumenis.shared.evidence.store import classify_evidence_integrity, record_evidence
    from lumenis.system.security import (
        OperationType, get_permission_gate, is_testing_bypass_enabled,
    )

    platform_key = str(platform or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", platform_key):
        raise ScopeValidationError("an exact source platform is required")
    product, domain = normalize_product_domain(product_id, domain_id)
    if (
        (domain == "cth" and (not expected_subject_id or expected_brand_focus_id is not None))
        or (domain == "zbmp" and (not expected_brand_focus_id or expected_subject_id is not None))
    ):
        raise ScopeValidationError("the expected old scope must be one exact Subject or BrandFocus")
    if type(expected_scope_evidence_ref) is not int or expected_scope_evidence_ref < 1:
        raise ScopeValidationError("the expected old signed Evidence id is required")
    ids = list(source_ids) if isinstance(source_ids, (list, tuple)) else []
    if (
        not ids or len(ids) > 100 or len(set(ids)) != len(ids)
        or any(type(value) is not str or not value or value != value.strip() for value in ids)
    ):
        raise ScopeValidationError("source identities must be a bounded unique exact list")
    ids.sort()
    reason = reason.strip() if isinstance(reason, str) else ""
    actor = actor.strip() if isinstance(actor, str) else ""
    if not 8 <= len(reason) <= 1000 or not actor or len(actor) > 160:
        raise ScopeValidationError("an explicit correction reason and operator identity are required")

    entity_id = expected_subject_id or expected_brand_focus_id or ""
    correction_payload = {
        "platform": platform_key, "product_id": product, "domain_id": domain,
        "expected_subject_id": expected_subject_id,
        "expected_brand_focus_id": expected_brand_focus_id,
        "expected_scope_evidence_ref": expected_scope_evidence_ref,
        "target_scope_status": "UNASSIGNED", "target_subject_id": None,
        "target_brand_focus_id": None, "source_ids": ids,
        "reason": reason, "actor": actor,
    }
    correction_key = hashlib.sha256(
        json.dumps(correction_payload, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    prior_correction = _find_scope_correction(con, correction_key)
    if prior_correction is not None:
        _validate_unassigned_correction_state(
            con, ids, platform_key, product, domain, int(prior_correction["id"]),
        )
        return {
            "corrected": 0, "evidence_id": int(prior_correction["id"]), "idempotent": True,
        }

    if is_testing_bypass_enabled():
        raise ScopeValidationError("testing bypass cannot authorize a scope correction")
    resource = _scope_correction_resource(
        platform=platform_key, domain_id=domain, entity_id=entity_id,
        old_evidence_id=expected_scope_evidence_ref, source_ids=ids,
        correction_key=correction_key,
    )
    permission = get_permission_gate().check(
        OperationType.DATA_IMPORT, resource,
        caller=actor, domain_id=domain, exact_approval_required=True,
    )
    if permission.allowed is not True or not permission.audit_id:
        raise PermissionError("exact DATA_IMPORT approval is required for this scope correction")

    cursor = con.execute(
        "SELECT * FROM app_evidence_records WHERE id=? LIMIT 1",
        (expected_scope_evidence_ref,),
    )
    prior_row = cursor.fetchone()
    if prior_row is None:
        raise ScopeValidationError("original scope Evidence is missing")
    prior_evidence = dict(zip((column[0] for column in cursor.description), prior_row))
    if (
        not classify_evidence_integrity(prior_evidence).get("verified")
        or prior_evidence.get("product_id") != product
        or prior_evidence.get("domain_id") != domain
        or str(prior_evidence.get("result") or "").upper() != "PASS"
        or str(prior_evidence.get("status") or "").lower() != "verified"
    ):
        raise ScopeValidationError("original scope Evidence is not signed and verified")
    try:
        prior_inputs = json.loads(prior_evidence.get("inputs_json") or "")
    except (TypeError, ValueError):
        raise ScopeValidationError("original scope Evidence inputs are invalid") from None
    old_scope = {"domain_id": domain, "product_id": product, "global": False}
    old_scope["subject_id" if domain == "cth" else "brand_focus_id"] = entity_id
    if (
        not isinstance(prior_inputs, dict)
        or prior_inputs.get("_lumenis_scope") != old_scope
        or not isinstance(prior_inputs.get("source_ids"), list)
        or any(value not in prior_inputs["source_ids"] for value in ids)
    ):
        raise ScopeValidationError("original scope Evidence does not cover the exact IDs and old scope")

    ensure_canonical_table(connection=con)
    con.execute("SAVEPOINT correct_existing_note_scope")
    try:
        for note_id in ids:
            raw = con.execute(
                "SELECT product_id,domain_id,subject_id,brand_focus_id,scope_status,"
                "scope_evidence_ref,source_platform FROM notes WHERE note_id=? LIMIT 1",
                (note_id,),
            ).fetchone()
            expected_raw = (
                product, domain, expected_subject_id, expected_brand_focus_id,
                "VERIFIED", str(expected_scope_evidence_ref), platform_key,
            )
            if raw is None or tuple(raw) != expected_raw:
                raise ScopeValidationError(f"Raw scope changed since correction review: {note_id}")
            canonical = con.execute(
                f"SELECT product_id,domain_id,subject_id,brand_focus_id,scope_status,"
                f"scope_evidence_ref FROM {CANONICAL_TABLE} WHERE external_id=? LIMIT 1",
                (note_id,),
            ).fetchone()
            expected_canonical = (
                product, domain, expected_subject_id or "", expected_brand_focus_id or "",
                "VERIFIED", str(expected_scope_evidence_ref),
            )
            if canonical is None or tuple(canonical) != expected_canonical:
                raise ScopeValidationError(f"Canonical scope differs from expected old scope: {note_id}")
            native = con.execute(
                "SELECT raw_data FROM platform_contents WHERE platform=? AND platform_content_id=? LIMIT 1",
                (platform_key, note_id),
            ).fetchone()
            if native is None:
                raise ScopeValidationError(f"native source projection is missing: {note_id}")
            try:
                native_data = json.loads(native[0] or "{}")
            except (TypeError, ValueError):
                raise ScopeValidationError(f"native source projection is invalid: {note_id}") from None
            if not isinstance(native_data, dict) or native_data.get("_lumenis_scope_correction_ref"):
                raise ScopeValidationError(f"native projection already has a scope correction: {note_id}")

        correction = dict(correction_payload)
        correction.update({
            "idempotency_key": correction_key, "permission_resource": resource,
            "permission_audit_id": permission.audit_id,
        })
        correction_evidence_id = record_evidence(
            source="manual_scope_correction", project="LUMENIS", product=product,
            feature_id="SCOPE_CORRECTION", level="L8",
            test_name="explicit source scope correction", result="PASS",
            status="verified", inputs={"source_ids": ids, "scope_correction": correction},
            outputs={"target_scope_status": "UNASSIGNED", "corrected_source_ids": ids},
            actual=f"actor={actor}; reason={reason}", notes=reason,
            account=actor, domain_id=domain,
            subject_id=expected_subject_id, brand_focus_id=expected_brand_focus_id,
            global_scope=False, connection=con,
        )
        if type(correction_evidence_id) is not int or correction_evidence_id < 1:
            raise ScopeValidationError("signed scope correction Evidence could not be appended")

        for note_id in ids:
            native = con.execute(
                "SELECT raw_data FROM platform_contents WHERE platform=? AND platform_content_id=?",
                (platform_key, note_id),
            ).fetchone()
            native_data = json.loads(native[0] or "{}")
            native_data["_lumenis_scope_correction_ref"] = correction_evidence_id
            con.execute(
                "UPDATE platform_contents SET raw_data=? WHERE platform=? AND platform_content_id=?",
                (json.dumps(native_data, ensure_ascii=False, sort_keys=True), platform_key, note_id),
            )
            con.execute(
                "UPDATE notes SET subject_id=NULL, brand_focus_id=NULL, "
                "scope_status='UNASSIGNED', scope_evidence_ref='' "
                "WHERE note_id=? AND product_id=? AND domain_id=? AND subject_id IS ? "
                "AND brand_focus_id IS ? AND scope_status='VERIFIED' AND scope_evidence_ref=?",
                (note_id, product, domain, expected_subject_id, expected_brand_focus_id,
                 str(expected_scope_evidence_ref)),
            )
            if con.execute("SELECT changes()").fetchone()[0] != 1:
                raise ScopeValidationError(f"Raw scope correction lost compare-and-set: {note_id}")
            persist_scope_correction(
                con, source_id=note_id, product_id=product, domain_id=domain,
                expected_subject_id=expected_subject_id,
                expected_brand_focus_id=expected_brand_focus_id,
                expected_scope_evidence_ref=expected_scope_evidence_ref,
                correction_evidence_id=correction_evidence_id,
            )
        con.execute("RELEASE SAVEPOINT correct_existing_note_scope")
        return {"corrected": len(ids), "evidence_id": correction_evidence_id, "idempotent": False}
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT correct_existing_note_scope")
        con.execute("RELEASE SAVEPOINT correct_existing_note_scope")
        raise

# 平台分流：社媒 → notes；其余搜索/网页 → web_mentions
SOCIAL_PLATFORMS = {
    "douyin", "instagram", "xiaohongshu", "rednote", "zhihu",
    "dianping", "smzdm", "weibo", "bilibili",
}
WEB_PLATFORMS = {
    "sogou_search", "google", "bing_search", "baidu_search",
    "sogou_wechat", "doubao_search",
}

# 六态（与系统采集状态机一致，失败绝不写成“0条成功”）
STATE_SUCCESS = "SUCCESS"
STATE_EMPTY = "EMPTY"
STATE_AUTH_REQUIRED = "AUTH_REQUIRED"
STATE_CAPTCHA = "CAPTCHA"
STATE_BLOCKED = "BLOCKED"
STATE_NETWORK_ERROR = "NETWORK_ERROR"
STATE_FAIL = "FAIL"

_AUTH_HINTS = ["登录", "login", "cookie", "登录态", "auth", "未登录", "扫码"]
_CAPTCHA_HINTS = ["验证码", "人机", "滑块", "captcha", "验证"]
_BLOCK_HINTS = ["300012", "风控", "频繁", "风险", "安全限制", "knitsail", "熔断", "unusual", "反爬"]
_NET_HINTS = ["网络", "timeout", "timed out", "连接", "network", "proxy", "代理", "无法访问"]


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    """连接唯一生产主库（调用方负责关闭）。"""
    return get_repository().connect(timeout=15)


def _md5(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8", "ignore")).hexdigest()


def classify_state(result: AdapterResult) -> str:
    """依据 success / notes / error 文本判定六态（失败细分，绝不与 EMPTY 混淆）。"""
    if result.success:
        return STATE_SUCCESS if result.notes else STATE_EMPTY
    err = (result.error or "").lower()
    if any(h in err for h in _AUTH_HINTS):
        return STATE_AUTH_REQUIRED
    if any(h in err for h in _CAPTCHA_HINTS):
        return STATE_CAPTCHA
    if any(h in err for h in _BLOCK_HINTS):
        return STATE_BLOCKED
    if any(h in err for h in _NET_HINTS):
        return STATE_NETWORK_ERROR
    return STATE_FAIL


def _social_note_id(platform: str, n: CollectedNote) -> str:
    """社媒笔记稳定主键：优先平台内部 id，其次 URL 哈希。"""
    rid = ""
    if isinstance(n.raw_data, dict):
        rid = str(n.raw_data.get("aweme_id") or n.raw_data.get("shortcode")
                  or n.raw_data.get("note_id") or n.raw_data.get("id") or "")
    if rid:
        return f"{platform}_{rid}"
    key = n.url or f"{n.author}:{n.title}"
    return f"{platform}_{_md5(key)[:16]}"


def _existing_id(con: sqlite3.Connection, table: str, col: str, val: str):
    row = con.execute(f"SELECT id FROM {table} WHERE {col}=? LIMIT 1", (val,)).fetchone()
    return row[0] if row else None


def persist_social_note(con, n: CollectedNote, keyword: str) -> str:
    """写入/更新一条社媒笔记到 notes。返回 inserted/updated/duplicate。"""
    platform = n.source_platform or "unknown"
    note_id = _social_note_id(platform, n)
    now = now_str()
    existing = _existing_id(con, "notes", "note_id", note_id)
    if existing:
        # 已存在：仅刷新互动量与最后出现时间，不覆盖已有人工标注/AI 结论
        con.execute(
            """UPDATE notes SET likes=?, comments=?, collects=?, shares=?,
               last_seen_at=?, captured_at=COALESCE(NULLIF(captured_at,''), ?)
               WHERE note_id=?""",
            (n.likes, n.comments, n.collects, n.shares, now, now, note_id),
        )
        # T4 旁路：同步更新 canonical_data（不影响主流程）
        _canonical_bypass(con, n, keyword, source_platform=platform)
        return "updated"
    con.execute(
        """INSERT INTO notes
           (note_id, title, content, body, url, cover, author_id, author_nickname,
            likes, comments, collects, shares, publish_date, publish_datetime,
            source_platform, source_keyword, captured_at, collected_at,
            collector_version, status, verification_status, ai_filter_status,
            is_taikoo_verified, relevance_status, data_quality_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (note_id, n.title, n.content, n.content, n.url, n.cover, n.author_id,
         n.author, n.likes, n.comments, n.collects, n.shares,
         n.publish_date, n.publish_date, platform, keyword, now, now,
         "v4-adapter", "active", "pending", "pending", 0, "unverified", "unknown"),
    )
    # T4 旁路：同步写入 canonical_data（不影响主流程）
    _canonical_bypass(con, n, keyword, source_platform=platform)
    return "inserted"


def persist_web_mention(con, n: CollectedNote, keyword: str, adapter: str) -> str:
    """写入/更新一条网页提及到 web_mentions。返回 inserted/updated。"""
    canonical = n.url or f"{adapter}:{n.title}"
    source_id = f"{adapter}_{_md5(canonical)[:16]}"
    domain = ""
    try:
        domain = urllib_domain(canonical)
    except Exception:
        domain = ""
    existing = _existing_id(con, "web_mentions", "source_id", source_id)
    if existing:
        con.execute(
            "UPDATE web_mentions SET fetched_at=? WHERE source_id=?", (now_str(), source_id))
        return "updated"
    con.execute(
        """INSERT INTO web_mentions
           (source_id, source_platform, source_type, title, content, url, domain,
            published_at, fetched_at, source_adapter, query, canonical_url,
            relevance, verification, ai_provider)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (source_id, adapter, "web", n.title, n.content, n.url, domain,
         n.publish_date, now_str(), adapter, keyword, canonical,
         "pending", "review", "rule"),
    )
    # T4 旁路：同步写入 canonical_data（不影响主流程）
    _canonical_bypass(con, n, keyword, source_platform=adapter)
    return "inserted"


def urllib_domain(url: str) -> str:
    import urllib.parse
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def persist_result(platform: str, adapter_display: str, result: AdapterResult,
                   keyword: str, con=None) -> Dict:
    """把单平台结果入库，并写一条 web_runs 运行记录。返回统计 dict。"""
    own = con is None
    con = con or get_conn()
    state = classify_state(result)
    inserted = updated = 0
    is_social = platform in SOCIAL_PLATFORMS
    try:
        if result.success:
            for n in result.notes:
                if is_social:
                    flag = persist_social_note(con, n, keyword)
                else:
                    flag = persist_web_mention(con, n, keyword, platform)
                if flag == "inserted":
                    inserted += 1
                elif flag == "updated":
                    updated += 1
        started = now_str()
        con.execute(
            """INSERT INTO web_runs
               (adapter, query, started_at, finished_at, fetched, accepted, rejected, error)
               VALUES (?,?,?,?,?,?,?,?)""",
            (platform, keyword, started, now_str(), len(result.notes),
             inserted, updated, "" if result.success else (result.error or state)),
        )
        # 同步刷新 web_sources 来源状态（健康灯用）
        con.execute(
            """INSERT INTO web_sources (source_key, source_name, adapter, enabled,
                 last_run_at, last_success_at, last_error, item_count)
               VALUES (?,?,?,1,?,?,?,?)
               ON CONFLICT(source_key) DO UPDATE SET
                 last_run_at=excluded.last_run_at,
                 last_success_at=excluded.last_success_at,
                 last_error=excluded.last_error, item_count=excluded.item_count""",
            (platform, adapter_display, platform, now_str(),
             now_str() if result.success else "",
             "" if result.success else (result.error or state), inserted),
        )
        if own:
            con.commit()
    finally:
        if own:
            con.close()
    return {
        "platform": platform, "display": adapter_display, "state": state,
        "success": result.success, "fetched": len(result.notes),
        "inserted": inserted, "updated": updated,
        "error": result.error, "duration": round(result.duration_seconds, 2),
    }
