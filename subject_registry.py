# -*- coding: utf-8 -*-
"""LUMENIS 通用主体注册表（CTH/BMP 共用，生产事实不改写）。

本模块只负责主体的登记与读取，不负责切换当前生产主体，也不改变 CTH/BMP
既有运行规则。主体是产品上下文的配置对象：可归属 CTH（商业运营）或 BMP
（品牌市场），可标为品牌主体或商业主体，行业字段保持开放，避免把产品锁死
在地产场景。

安全边界：
* 数据写入沿用主库解析（ZBC_DB_PATH），测试可用临时库隔离；不写仓库 data/。
* POST 由全局 PermissionGate + 本路由的 CONFIG_MODIFY 高风险门保护；需人工审批。
* API 永不返回 Cookie、Session 或其他凭证；主体登记不会自动开启采集/发布。
* 既有 subject_context / subject_rules 继续作为默认主体与运行规则来源，本表只做增量配置。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, unquote, urlsplit

from flask import Blueprint, jsonify, request

from lumenis.system.security import OperationType, RiskLevel, require_permission


subject_registry_bp = Blueprint("subject_registry", __name__)
logger = logging.getLogger(__name__)

DOMAINS: Dict[str, Dict[str, str]] = {
    "CTH": {"name": "商业运营", "product": "CTH"},
    "BMP": {"name": "品牌市场", "product": "BMP"},
}

SUBJECT_TYPES: Dict[str, str] = {
    "brand": "品牌主体",
    "company": "商业主体",
}

TABLE_NAME = "lumenis_subject_registry"
OFFICIAL_NAME_SOURCE_FEATURE_ID = "SUBJECT_OFFICIAL_NAME_SOURCE"
_SENSITIVE_SOURCE_QUERY_TERMS = {
    "auth", "authorization", "bearer", "cookie", "credential", "credentials",
    "key", "password", "passwd", "pwd", "secret", "session", "sign",
    "signature", "sig", "token",
}
_SENSITIVE_SOURCE_QUERY_KEYS = {
    "access_key", "access_token", "api_key", "apikey", "appkey", "aws_access_key",
    "aws_secret_key", "client_id", "client_secret", "oauth_token", "private_key",
    "refresh_token", "secret_key", "session_id",
}


def _validate_official_source_url(source_url: Any) -> str:
    """Validate a declared official URL without reading or mutating the DB."""
    url = _text(source_url, field="source_url", max_len=500)
    if not url.lower().startswith(("https://", "http://")):
        raise SubjectValidationError("source_url 必须是品牌官网 http(s) 地址")
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        username = parts.username
        password = parts.password
    except ValueError as exc:
        raise SubjectValidationError("source_url 格式无效") from exc
    if (parts.scheme.lower() not in {"http", "https"} or not hostname
            or username is not None or password is not None):
        raise SubjectValidationError("source_url 不得包含凭证或无效主机名")

    def normalized_query_key(key: str) -> str:
        # Separate camelCase before casefolding (clientSecret -> client_secret),
        # then canonicalize punctuation so equivalent credential names match.
        separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    def contains_sensitive_assignment(query: str, *, depth: int = 0, seen=frozenset()) -> bool:
        """Inspect direct and bounded nested query values before persisting a URL.

        `parse_qsl` decodes one level of a value but does not expose credentials
        hidden inside redirect URLs or semicolon-delimited query assignments.
        The URL itself is capped at 500 characters; this additional depth bound
        keeps nested inspection small even for deliberately recursive values.
        """
        if not query or depth > 4 or query in seen:
            return False
        seen = seen | {query}
        for key, value in parse_qsl(query.replace(";", "&"), keep_blank_values=True):
            normalized_key = normalized_query_key(key)
            if (normalized_key in _SENSITIVE_SOURCE_QUERY_KEYS
                    or set(normalized_key.split("_")) & _SENSITIVE_SOURCE_QUERY_TERMS):
                return True
            if depth >= 4 or not value:
                continue

            nested_queries = []
            # Both the query-decoded and once-more-decoded forms are useful
            # when a redirect value was percent-encoded twice.
            # Bounded iterative decoding: a redirect may be percent-encoded
            # several times; inspect every layer until it stops changing.
            layers = [value]
            for _ in range(6):
                decoded = unquote(layers[-1])
                if decoded == layers[-1]:
                    break
                layers.append(decoded)
            else:
                if unquote(layers[-1]) != layers[-1]:
                    # Still encoded after the bound: it cannot be inspected,
                    # so treat it as credential-bearing (fail closed).
                    return True
            for candidate in dict.fromkeys(layers):
                try:
                    nested_parts = urlsplit(candidate)
                    nested_query = nested_parts.query
                    # A nested redirect authority can carry userinfo even
                    # when it has no query of its own.
                    if nested_parts.netloc and "@" in nested_parts.netloc:
                        return True
                    # The outer URL may not carry a fragment; an encoded
                    # nested fragment (#access_token=...) is held to the same
                    # rule: fail closed rather than persist it as Evidence.
                    if nested_parts.fragment:
                        return True
                except ValueError:
                    nested_query = ""
                if nested_query:
                    nested_queries.append(nested_query)
                elif re.search(r"(?:^|[?&;])[^?&;=]+=", candidate):
                    nested_queries.append(candidate)
            for nested in dict.fromkeys(nested_queries):
                if contains_sensitive_assignment(nested, depth=depth + 1, seen=seen):
                    return True
        return False

    if contains_sensitive_assignment(parts.query):
        raise SubjectValidationError("source_url 不得包含凭证查询参数")
    if parts.fragment:
        raise SubjectValidationError("source_url 不得包含片段数据")
    return url


class SubjectValidationError(ValueError):
    """请求字段不满足主体契约。"""


class SubjectRegistryUnavailableError(RuntimeError):
    """The canonical registry is absent or behind its migration."""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _text(value: Any, *, field: str, max_len: int = 160) -> str:
    value = str(value or "").strip()
    if len(value) > max_len:
        raise SubjectValidationError(f"{field} 长度不能超过 {max_len} 个字符")
    return value


def normalize_domain(value: Any) -> str:
    value = str(value or "").strip().upper()
    if value == "ZBMP":
        value = "BMP"
    if value not in DOMAINS:
        raise SubjectValidationError("domain_id 仅支持 CTH（商业运营）或 BMP（品牌市场）")
    return value


def normalize_subject_type(value: Any) -> str:
    value = str(value or "").strip().lower()
    aliases = {
        "brand": "brand",
        "品牌": "brand",
        "品牌主体": "brand",
        "company": "company",
        "commercial": "company",
        "business": "company",
        "商业": "company",
        "商业主体": "company",
    }
    if value not in aliases:
        raise SubjectValidationError("subject_type 仅支持 brand（品牌主体）或 company（商业主体）")
    return aliases[value]


def _canonical_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _keywords(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        values: Iterable[Any] = value.split(",")
    elif isinstance(value, list):
        values = value
    else:
        raise SubjectValidationError("keywords 必须是数组或逗号分隔文本")
    result: List[str] = []
    for item in values:
        word = _text(item, field="keywords", max_len=80)
        if word and word not in result:
            result.append(word)
    if len(result) > 50:
        raise SubjectValidationError("keywords 最多 50 个")
    return result


def _db_ready():
    """返回按运行时环境解析的连接上下文，不固化 import 时 DB_PATH。"""
    import db_paths
    import database as db

    path = db_paths.main_db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return db.get_db()


def _schema_version(conn):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if exists is None:
        return None
    versions = []
    for (value,) in conn.execute("SELECT version FROM schema_version").fetchall():
        try:
            versions.append(int(value))
        except (TypeError, ValueError):
            continue
    return max(versions) if versions else 0


def _ensure_legacy_evidence_schema() -> None:
    """Initialize canonical Evidence only for the supported unversioned DB."""
    with _db_ready() as conn:
        _require_registry_schema(conn)
        unversioned = _schema_version(conn) is None
    if not unversioned:
        return

    # Use the Shared Evidence owner's initializer so its additive contract,
    # chain, and integrity columns stay in sync. Versioned databases remain
    # exclusively owned by the Shared Database migrator.
    import db_paths
    from lumenis.shared.evidence.store import ensure_evidence_schema, init_evidence_store

    init_evidence_store(db_paths.main_db_path())
    with _db_ready() as conn:
        ensure_evidence_schema(conn)


def _require_registry_schema(conn) -> None:
    """Read the migrated registry contract without repairing it."""
    try:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE_NAME,),
        ).fetchone()
        if table is None:
            raise SubjectRegistryUnavailableError("canonical subject registry is unavailable")
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
        if "brand_focus_id" not in columns:
            raise SubjectRegistryUnavailableError("canonical subject registry migration is required")
        version = _schema_version(conn)
        if version is not None and version < 15:
            raise SubjectRegistryUnavailableError("canonical subject registry migration is required")
        brand_focus_unique = False
        for index_row in conn.execute(f"PRAGMA index_list({TABLE_NAME})").fetchall():
            if not bool(index_row[2]):
                continue
            index_name = str(index_row[1]).replace("\"", "\"\"")
            index_columns = tuple(
                item[2]
                for item in conn.execute(f'PRAGMA index_info("{index_name}")').fetchall()
            )
            if index_columns == ("brand_focus_id",):
                brand_focus_unique = True
                break
        if not brand_focus_unique:
            raise SubjectRegistryUnavailableError("canonical subject registry migration is required")
    except SubjectRegistryUnavailableError:
        raise
    except sqlite3.Error as exc:
        raise SubjectRegistryUnavailableError("canonical subject registry is unavailable") from exc


def ensure_schema(conn) -> None:
    """Migration helper: add BrandFocus identity to the canonical registry."""
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            subject_id TEXT PRIMARY KEY,
            brand_focus_id TEXT,
            domain_id TEXT NOT NULL,
            subject_type TEXT NOT NULL,
            name_en TEXT NOT NULL,
            name_zh TEXT NOT NULL,
            name_en_norm TEXT NOT NULL,
            name_zh_norm TEXT NOT NULL,
            industry TEXT NOT NULL DEFAULT '',
            keywords_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'configured',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain_id, subject_type, name_en_norm, name_zh_norm)
        )"""
    )
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()}
    if "brand_focus_id" not in columns:
        conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN brand_focus_id TEXT")

    missing_bmp_ids = conn.execute(
        f"SELECT subject_id, subject_type, name_en_norm, name_zh_norm FROM {TABLE_NAME} "
        "WHERE domain_id='BMP' AND (brand_focus_id IS NULL OR TRIM(brand_focus_id)='')"
    ).fetchall()
    for row in missing_bmp_ids:
        digest = hashlib.sha256(
            f"BMP|{row[1]}|{row[2]}|{row[3]}".encode("utf-8")
        ).hexdigest()[:24]
        conn.execute(
            f"UPDATE {TABLE_NAME} SET brand_focus_id=? WHERE subject_id=? "
            "AND (brand_focus_id IS NULL OR TRIM(brand_focus_id)='')",
            (f"BRAND-{digest}", row[0]),
        )
    conn.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_brand_focus "
        f"ON {TABLE_NAME}(brand_focus_id) WHERE brand_focus_id IS NOT NULL"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_domain ON {TABLE_NAME}(domain_id, status)"
    )


def _row_to_dict(row) -> Dict[str, Any]:
    data = dict(row)
    try:
        keywords = json.loads(data.pop("keywords_json", "[]") or "[]")
    except (TypeError, ValueError):
        keywords = []
    data["keywords"] = keywords if isinstance(keywords, list) else []
    data["domain_name"] = DOMAINS.get(data.get("domain_id"), {}).get("name", "未知领域")
    data["subject_type_name"] = SUBJECT_TYPES.get(data.get("subject_type"), "未知主体")
    # 内部去重列不属于对外契约。
    data.pop("name_en_norm", None)
    data.pop("name_zh_norm", None)
    return data


def _registry_read_connection(connection=None):
    """Borrow canonical scope reads without closing the caller's transaction."""
    if connection is None:
        return _db_ready()
    from contextlib import nullcontext
    from lumenis.system.security.permission import _require_canonical_scope_connection
    return nullcontext(_require_canonical_scope_connection(connection))


def list_subjects(domain_id: Optional[str] = None, *, connection=None) -> List[Dict[str, Any]]:
    normalized = normalize_domain(domain_id) if domain_id else None
    with _registry_read_connection(connection) as conn:
        _require_registry_schema(conn)
        if normalized:
            rows = conn.execute(
                f"SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
                f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
                "WHERE domain_id=? AND status != 'archived' ORDER BY updated_at DESC, name_en_norm",
                (normalized,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
                f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
                "WHERE status != 'archived' ORDER BY updated_at DESC, name_en_norm"
            ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_subject_by_id(domain_id: str, subject_id: str) -> Optional[Dict[str, Any]]:
    """Read one active canonical registry entry by typed domain and stable ID."""
    normalized = normalize_domain(domain_id)
    if not isinstance(subject_id, str) or not subject_id or subject_id != subject_id.strip():
        raise SubjectValidationError("subject_id 无效")
    with _db_ready() as conn:
        _require_registry_schema(conn)
        rows = conn.execute(
            f"SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
            f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
            "WHERE domain_id=? AND subject_id=? AND status != 'archived'",
            (normalized, subject_id),
        ).fetchall()
    if len(rows) > 1:
        raise SubjectRegistryUnavailableError("canonical subject identity is not unique")
    return _row_to_dict(rows[0]) if rows else None


def add_subject(payload: Dict[str, Any], *, strict_identity=False, _authorize_write=None) -> Tuple[Dict[str, Any], bool]:
    if not isinstance(payload, dict):
        raise SubjectValidationError("请求体必须是 JSON 对象")
    domain_id = normalize_domain(payload.get("domain_id"))
    subject_type = normalize_subject_type(payload.get("subject_type"))
    if (domain_id == "CTH" and subject_type != "company") or (
        domain_id == "BMP" and subject_type != "brand"
    ):
        raise SubjectValidationError(
            "domain_id 与 subject_type 不匹配：CTH 仅支持 company（商业主体），"
            "BMP 仅支持 brand（品牌主体）"
        )
    name_en = _text(payload.get("name_en"), field="name_en")
    name_zh = _text(payload.get("name_zh"), field="name_zh")
    if not name_en or not name_zh:
        raise SubjectValidationError("name_en 与 name_zh 必须同时填写")
    industry = _text(payload.get("industry"), field="industry", max_len=120)
    keywords = _keywords(payload.get("keywords"))
    en_norm = _canonical_name(name_en)
    zh_norm = _canonical_name(name_zh)
    digest = hashlib.sha256(
        f"{domain_id}|{subject_type}|{en_norm}|{zh_norm}".encode("utf-8")
    ).hexdigest()[:24]
    subject_id = f"SUBJ-{digest}"
    brand_focus_id = f"BRAND-{digest}" if domain_id == "BMP" else None
    now = _now()

    with _db_ready() as conn:
        if strict_identity:
            conn.execute("BEGIN IMMEDIATE")
        if _authorize_write is not None:
            _authorize_write()
        version = _schema_version(conn)
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE_NAME,),
        ).fetchone() is not None
        if version is not None and version < 15:
            raise SubjectRegistryUnavailableError("canonical subject registry migration is required")
        if table_exists:
            _require_registry_schema(conn)
        elif version is None:
            # Preserve the legacy unversioned bootstrap used by isolated tools/tests.
            # Versioned databases are changed only by the Shared Database migrator.
            ensure_schema(conn)
        else:
            raise SubjectRegistryUnavailableError("canonical subject registry is unavailable")
        if strict_identity:
            conflicts = conn.execute(
                f"SELECT subject_id,name_en,name_zh FROM {TABLE_NAME} WHERE domain_id=? AND subject_type=? "
                "AND ((name_en_norm=? AND name_zh_norm<>?) OR (name_zh_norm=? AND name_en_norm<>?))",
                (domain_id,subject_type,en_norm,zh_norm,zh_norm,en_norm)).fetchall()
            if conflicts:
                error = SubjectValidationError("SUBJECT_IDENTITY_CONFLICT")
                error.conflicts = [dict(zip(("subject_id","name_en","name_zh"),row)) for row in conflicts]
                raise error
        existing = conn.execute(
            f"SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
            f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
            "WHERE domain_id=? AND subject_type=? AND name_en_norm=? AND name_zh_norm=?",
            (domain_id, subject_type, en_norm, zh_norm),
        ).fetchone()
        if existing:
            if _authorize_write is not None:
                _authorize_write()
            return _row_to_dict(existing), False
        conn.execute(
            f"INSERT INTO {TABLE_NAME} (subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, "
            "name_en_norm, name_zh_norm, industry, keywords_json, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'configured', ?, ?)",
            (subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, en_norm, zh_norm,
             industry, json.dumps(keywords, ensure_ascii=False), now, now),
        )
        row = conn.execute(
            f"SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
            f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} WHERE subject_id=?",
            (subject_id,),
        ).fetchone()
        if _authorize_write is not None:
            _authorize_write()
    return _row_to_dict(row), True


def record_official_name(
    domain_id: str,
    subject_id: str,
    *,
    source_url: str,
    name_zh: Optional[str] = None,
    name_en: Optional[str] = None,
    keywords: Iterable[str] = (),
    permission_audit_id: Optional[str] = None,
    permission_caller: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a brand's own official name/aliases with a source declaration.

    LUMENIS does not rename brands: callers pass only names shown on the
    brand's official site, and ``source_url`` (http/https) is required.
    The stable subject_id is unchanged; aliases are appended to keywords.
    The declared URL and name transition are stored in scoped Shared Evidence
    in the same transaction as the registry update. An HTTP(S) prefix is only
    syntax validation: it does not verify the site or the entity's identity.
    Returns {"before", "after", "changed", "source_url", "source_provenance"}.
    """
    normalized = normalize_domain(domain_id)
    url = _validate_official_source_url(source_url)
    new_zh = _text(name_zh, field="name_zh") if name_zh else None
    new_en = _text(name_en, field="name_en") if name_en else None
    extra = _keywords(list(keywords or ()))
    if not (new_zh or new_en or extra):
        raise SubjectValidationError("没有可记录的官方名称")
    if permission_audit_id is not None:
        permission_audit_id = _text(
            permission_audit_id, field="permission_audit_id", max_len=200
        )
    if permission_caller is not None:
        permission_caller = _text(
            permission_caller, field="permission_caller", max_len=200
        )
    _ensure_legacy_evidence_schema()
    with _db_ready() as conn:
        _require_registry_schema(conn)
        cols = ("subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
                "keywords_json, status, created_at, updated_at")
        row = conn.execute(
            f"SELECT {cols} FROM {TABLE_NAME} WHERE domain_id=? AND subject_id=?",
            (normalized, subject_id),
        ).fetchone()
        if row is None:
            raise SubjectValidationError("subject_id 不存在")
        before = _row_to_dict(row)
        zh = new_zh or before["name_zh"]
        en = new_en or before["name_en"]
        merged = list(before["keywords"])
        for k in extra:
            if k not in merged:
                merged.append(k)
        changed = (zh, en, merged) != (before["name_zh"], before["name_en"], before["keywords"])
        if changed:
            try:
                conn.execute(
                    f"UPDATE {TABLE_NAME} SET name_zh=?, name_en=?, name_zh_norm=?, name_en_norm=?, "
                    "keywords_json=?, updated_at=? WHERE subject_id=?",
                    (zh, en, _canonical_name(zh), _canonical_name(en),
                     json.dumps(merged, ensure_ascii=False), _now(), subject_id),
                )
            except sqlite3.IntegrityError as exc:
                raise SubjectValidationError("官方名称与另一已登记主体重复") from exc
        after = _row_to_dict(conn.execute(
            f"SELECT {cols} FROM {TABLE_NAME} WHERE subject_id=?", (subject_id,)).fetchone())

        # This operation records an assertion supplied to the registry. Do not
        # turn a syntactically valid URL into site-origin or identity proof.
        from lumenis.shared.evidence.store import record_evidence

        evidence_scope = {"subject_id": subject_id} if normalized == "CTH" else {
            "brand_focus_id": before.get("brand_focus_id"),
        }
        if normalized == "BMP" and not evidence_scope["brand_focus_id"]:
            raise SubjectRegistryUnavailableError(
                "canonical BrandFocus identity is unavailable for source Evidence"
            )
        evidence_id = record_evidence(
            connection=conn,
            source="subject_registry",
            project="LUMENIS",
            product=normalized,
            domain_id=normalized.lower(),
            **evidence_scope,
            feature_id=OFFICIAL_NAME_SOURCE_FEATURE_ID,
            level="L4",
            test_name="official_name_source_declaration",
            capture_mode="manual_declaration",
            result="GAP",
            status="pending",
            subject_scope=(subject_id if normalized == "CTH" else before["brand_focus_id"]),
            inputs={
                "subject_id": subject_id,
                "source_url": url,
                "source_claim": "official_site",
                "name_before": {"name_en": before["name_en"], "name_zh": before["name_zh"]},
                "name_after": {"name_en": after["name_en"], "name_zh": after["name_zh"]},
                "keywords_before": list(before["keywords"]),
                "keywords_requested": list(extra),
                "permission_audit_id": permission_audit_id,
                "permission_caller": permission_caller,
            },
            outputs={
                "subject_id": subject_id,
                "keywords_after": list(after["keywords"]),
                "source_url": url,
                "origin_verification": "NOT_INDEPENDENTLY_VERIFIED",
                "identity_verification": "NOT_VERIFIED",
                "authenticity_score_state": "NOT_ASSESSED",
                "url_scheme_is_identity_proof": False,
                "network_fetch": "NOT_PERFORMED",
            },
            expected="Official source origin and identity require independent verification.",
            actual="URL was declared; no network request or identity verification was performed.",
            # No independent source or identity check was performed, so keep
            # the canonical numeric score unknown instead of encoding 0.0.
            authenticity_score=None,
            notes=(
                "HTTP(S) scheme validation records syntax only. The existing "
                "numeric authenticity score remains unassessed."
            ),
        )
        if type(evidence_id) is not int or evidence_id <= 0:
            raise SubjectRegistryUnavailableError(
                "official name source Evidence was not durably recorded"
            )
    source_provenance = {
        "source_url": url,
        "evidence_ref": f"app_evidence_records:{evidence_id}",
        "origin_verification": "NOT_INDEPENDENTLY_VERIFIED",
        "identity_verification": "NOT_VERIFIED",
    }
    return {
        "before": before,
        "after": after,
        "changed": changed,
        "source_url": url,
        "source_provenance": source_provenance,
    }


def _country_subject_projection(domain_id, country_iso, relation_type):
    """Read existing relation assertions without selecting focus or collecting."""
    from lumenis.shared.database import get_repository
    from lumenis.shared.database.entity_relations import EntityRelationRepository

    with get_repository().connection(read_only=True) as conn:
        projection = EntityRelationRepository(conn).query_country_entities(
            domain_id=domain_id, country_iso=country_iso, relation_type=relation_type,
        )
    # Rejected/archived assertions remain in the diagnostic claims, but cannot
    # become a selectable country membership. Unreviewed claims stay explicit.
    projection["entities"] = [
        entity for entity in projection["entities"]
        if str(entity.get("registry_status") or "").lower() not in {
            "archived", "disabled", "deleted",
        } and any(claim.get("status") != "REJECTED" for claim in entity["claims"])
    ]
    projection["observed_entity_count"] = len(projection["entities"])
    projection["coverage_total"] = None
    projection["coverage_status"] = "NOT_VERIFIED"
    return projection


def _relation_datetime(value):
    """Parse a relation/evidence timestamp in the server's local timezone."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    # Relation rows may retain either an explicit offset or the legacy local
    # timestamps used by Evidence. astimezone() interprets naive values in the
    # current server timezone without inventing a different date.
    return parsed.astimezone()


def _claim_current_time_state(claim, evaluated_at):
    kind = claim.get("valid_time_kind")
    if kind == "UNKNOWN":
        return "UNKNOWN"
    if kind == "AS_OF_CAPTURE":
        captured = _relation_datetime(claim.get("evidence_captured_at"))
        if captured is None:
            return "UNKNOWN"
        # A same-day capture is evidence about that capture date; it does not
        # establish that an operation is ongoing at this later instant.
        return "AS_OF_CAPTURE" if captured.date() == evaluated_at.date() else "OUTSIDE_CURRENT_RANGE"
    if kind == "INTERVAL":
        start = _relation_datetime(claim.get("valid_from"))
        end_value = claim.get("valid_to")
        end = _relation_datetime(end_value) if end_value else None
        if start is None or (end_value and end is None):
            return "UNKNOWN"
        return "CURRENT" if start <= evaluated_at and (end is None or evaluated_at < end) else "OUTSIDE_CURRENT_RANGE"
    return "UNKNOWN"


def _china_operation_for_subject(projection, subject_id, *, evaluated_at=None):
    """Project current CN operating evidence without inferring from identity.

    Only an Evidence-verified, accepted OPERATES_IN/CN assertion whose declared
    time covers the current observation can establish current operation. A
    name, headquarters, nationality, unreviewed assertion, or old capture does
    not qualify.
    """
    evaluated_at = evaluated_at or datetime.now().astimezone()
    claims = [
        claim for claim in projection.get("claims", [])
        if claim.get("subject_id") == subject_id
    ]
    projected_claims = []
    for claim in claims:
        raw_source_url = claim.get("source_note_url")
        source_url = None
        if raw_source_url:
            try:
                source_url = _validate_official_source_url(raw_source_url)
                source_url_state = "AVAILABLE"
            except SubjectValidationError:
                source_url_state = "REDACTED"
        else:
            source_url_state = "NOT_PROVIDED"
        projected_claims.append({
            "relation_type": claim.get("relation_type"),
            "claim_kind": claim.get("claim_kind"),
            "status": claim.get("status"),
            "review_status": claim.get("review_status"),
            "evidence_integrity": claim.get("evidence_integrity"),
            "time_state": _claim_current_time_state(claim, evaluated_at),
            "valid_time_kind": claim.get("valid_time_kind"),
            "valid_from": claim.get("valid_from"),
            "valid_to": claim.get("valid_to"),
            "captured_at": claim.get("evidence_captured_at"),
            "source_url": source_url,
            "source_url_state": source_url_state,
            "source_evidence_ref": claim.get("source_evidence_ref"),
            "source_note_id": claim.get("source_note_id"),
        })

    live = [
        claim for claim in projected_claims
        if claim["status"] != "REJECTED" and claim["time_state"] == "CURRENT"
    ]
    verified = [claim for claim in live if claim["evidence_integrity"] == "VERIFIED"]
    accepted_assertions = [
        claim for claim in verified
        if claim["review_status"] == "ACCEPTED" and claim["claim_kind"] == "ASSERTED"
    ]
    accepted_absences = [
        claim for claim in verified
        if claim["review_status"] == "ACCEPTED" and claim["claim_kind"] == "EXPLICIT_ABSENCE"
    ]
    observed = [
        claim for claim in projected_claims
        if claim["status"] != "REJECTED" and claim["time_state"] == "AS_OF_CAPTURE"
    ]
    verified_observed = [claim for claim in observed if claim["evidence_integrity"] == "VERIFIED"]
    accepted_observed_assertions = [
        claim for claim in verified_observed
        if claim["review_status"] == "ACCEPTED" and claim["claim_kind"] == "ASSERTED"
    ]
    accepted_observed_absences = [
        claim for claim in verified_observed
        if claim["review_status"] == "ACCEPTED" and claim["claim_kind"] == "EXPLICIT_ABSENCE"
    ]
    conflicted = [claim for claim in live if claim["status"] == "CONFLICTED"]
    unreviewed = [claim for claim in live if claim["status"] == "UNREVIEWED"]
    unreviewed_observed = [claim for claim in observed if claim["status"] == "UNREVIEWED"]
    invalid = [
        claim for claim in projected_claims
        if claim["status"] != "REJECTED" and claim["evidence_integrity"] != "VERIFIED"
    ]
    unresolved_counter_claim = any(
        claim["claim_kind"] == "EXPLICIT_ABSENCE" for claim in unreviewed
    ) if accepted_assertions else any(
        claim["claim_kind"] == "ASSERTED" for claim in unreviewed
    ) if accepted_absences else False

    if conflicted or (accepted_assertions and accepted_absences):
        status, currently_operating = "CONFLICT", None
    elif unresolved_counter_claim:
        status, currently_operating = "UNREVIEWED", None
    elif accepted_assertions:
        status, currently_operating = "CONFIRMED_CURRENT", True
    elif accepted_absences:
        status, currently_operating = "NOT_OPERATING_CURRENT", False
    elif accepted_observed_assertions and accepted_observed_absences:
        status, currently_operating = "CONFLICT_AS_OF_CAPTURE", None
    elif accepted_observed_assertions:
        status, currently_operating = "EVIDENCED_AS_OF_CAPTURE", None
    elif accepted_observed_absences:
        status, currently_operating = "NOT_OPERATING_AS_OF_CAPTURE", None
    elif unreviewed:
        status, currently_operating = "UNREVIEWED", None
    elif unreviewed_observed:
        status, currently_operating = "UNREVIEWED_AS_OF_CAPTURE", None
    elif invalid:
        status, currently_operating = "EVIDENCE_INVALID", None
    elif not claims:
        status, currently_operating = "NOT_COLLECTED", None
    elif all(claim.get("status") == "REJECTED" for claim in projected_claims):
        status, currently_operating = "REJECTED", None
    else:
        status, currently_operating = "NOT_ESTABLISHED_FOR_AS_OF", None

    return {
        "country_iso": "CN",
        "relation_type": "OPERATES_IN",
        "status": status,
        "currently_operating": currently_operating,
        "evaluated_at": evaluated_at.isoformat(timespec="seconds"),
        "claims": projected_claims,
    }


def _subject_directory_scope(domain_id):
    return {
        "domain_id": "cth" if domain_id == "CTH" else "zbmp",
        "subject_id": None,
        "brand_focus_id": None,
        "global_scope": True,
    }


def _subject_directory_actor(user=None, *, local_workspace=False, action="read"):
    if isinstance(user, dict) and type(user.get("id")) is int and user["id"] > 0:
        return user
    if not local_workspace:
        return None
    from lumenis.system.security.permission import resolve_local_workspace_principal
    return resolve_local_workspace_principal(module="reports", action=action)


def _subject_working_set_view(
    domain_id, actor, rows, *, china_operations=None, evidence_state="AVAILABLE",
):
    """Read an actor's evidence-qualified CN working set via SavedWork."""
    from lumenis.shared.reporting.delivery_preferences import read_preferences

    unavailable = {
        "state": "UNAVAILABLE", "mode": None, "subject_ids": None,
        "removed_subject_ids": [], "persisted": None, "preference_ref": None,
        "version": None, "draft_digest": None,
    }
    if actor is None:
        return unavailable
    try:
        saved = read_preferences(actor=actor, scope=_subject_directory_scope(domain_id))
    except Exception as exc:
        if str(exc) not in {"WORK_PERMISSION_DENIED", "WORK_SCOPE_INVALID"}:
            logger.exception("Subject directory preference readback unavailable")
        return unavailable
    preference = saved["preferences"]["subject_directory"]
    active_registry_ids = {
        row["subject_id"] for row in rows
        if row.get("status") in {"configured", "active"}
    }
    removed = sorted(set(preference["removed_subject_ids"]) & {
        row["subject_id"] for row in rows
    })
    if evidence_state != "AVAILABLE" or china_operations is None:
        return {
            "state": "EVIDENCE_UNAVAILABLE", "mode": preference["mode"],
            "subject_ids": None, "removed_subject_ids": removed,
            "persisted": saved["persisted"], "preference_ref": saved["artifact_ref"],
            "version": saved["version"], "draft_digest": saved["draft_digest"],
        }
    currently_operating_ids = {
        subject_id for subject_id, operation in china_operations.items()
        if subject_id in active_registry_ids
        and operation.get("status") == "CONFIRMED_CURRENT"
        and operation.get("currently_operating") is True
    }
    selected = sorted(currently_operating_ids - set(removed))
    return {
        "state": "READY", "mode": preference["mode"], "subject_ids": selected,
        "removed_subject_ids": removed, "persisted": saved["persisted"],
        "preference_ref": saved["artifact_ref"], "version": saved["version"],
        "draft_digest": saved["draft_digest"],
    }


@subject_registry_bp.route("/api/settings/subjects", methods=["GET"])
def get_subjects():
    # Account system is post-loop (PO): until ACCOUNT_SYSTEM_ENABLED=on, registry
    # reads do not require a product account session. Tables/data stay untouched.
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import local_workspace_read_allowed
    import os

    account_gate = os.environ.get("ACCOUNT_SYSTEM_ENABLED", "off").strip().lower() in (
        "1", "on", "true", "yes",
    )
    local_read = (not account_gate) or local_workspace_read_allowed("subject_registry")
    user = None if local_read else get_current_user()
    if not local_read and (not user or type(user.get("id")) is not int):
        return jsonify({"ok": False, "code": "AUTH_REQUIRED", "error": "需要有效账号会话"}), 401

    domain_arg = request.args.get("domain_id") or request.args.get("domain")
    try:
        requested_domain = normalize_domain(domain_arg) if domain_arg else None
    except SubjectValidationError as exc:
        return jsonify({"ok": False, "error": str(exc), "code": "INVALID_SUBJECT_SCOPE"}), 400

    try:
        from account.authorization import check_dual_domain_permission

        candidates = [requested_domain] if requested_domain else list(DOMAINS)
        authorized_domains = [
            domain for domain in candidates
            if local_read or check_dual_domain_permission(
                user["id"],
                "ZBMP" if domain == "BMP" else "CTH",
                module="subject_registry",
                action="read",
            )
        ]
    except Exception:
        logger.exception("Subject registry read authorization failed")
        return jsonify({"ok": False, "code": "AUTHORIZATION_UNAVAILABLE",
                        "error": "主体范围授权暂不可用"}), 503

    if not authorized_domains:
        return jsonify({"ok": False, "code": "SUBJECT_SCOPE_DENIED",
                        "error": "没有读取该主体范围的权限"}), 403

    country = request.args.get("country_iso")
    relation = request.args.get("relation_type")
    if (country is not None or relation is not None) and (
        not requested_domain or not country or not relation
    ):
        return jsonify({"ok": False, "code": "INVALID_COUNTRY_FILTER",
                        "error": "国家筛选需同时指定业务领域、国家和关系类型"}), 400

    country_projection = None
    subjects_by_domain = {}
    try:
        subjects_by_domain = {
            domain: list_subjects(domain) for domain in authorized_domains
        }
        subjects = [subject for domain in authorized_domains
                    for subject in subjects_by_domain[domain]]
        if country is not None:
            from lumenis.shared.database.entity_relations import EntityRelationError
            try:
                country_projection = _country_subject_projection(
                    requested_domain, country, relation,
                )
            except EntityRelationError:
                return jsonify({"ok": False, "code": "INVALID_COUNTRY_FILTER",
                                "error": "国家或关系类型无效"}), 400
            except (sqlite3.Error, RuntimeError):
                logger.exception("Country relation projection unavailable")
                return jsonify({"ok": False, "code": "COUNTRY_RELATIONS_UNAVAILABLE",
                                "error": "国家与市场关系暂不可用，请稍后重试"}), 503
            visible_ids = {item["subject_id"] for item in country_projection["entities"]}
            subjects = [item for item in subjects if item["subject_id"] in visible_ids]
    except SubjectValidationError as exc:
        return jsonify({"ok": False, "error": str(exc), "code": "INVALID_SUBJECT_SCOPE"}), 400
    except SubjectRegistryUnavailableError:
        logger.exception("Canonical subject registry is unavailable")
        return jsonify({"ok": False, "code": "SUBJECT_REGISTRY_UNAVAILABLE",
                        "error": "主体注册表暂不可用"}), 503

    # The registry remains searchable. Only a current, accepted, verified
    # CN/OPERATES_IN interval enters the default directory; other rows remain
    # explicit pending/evidence states and are never promoted by name or locale.
    evaluated_at = datetime.now().astimezone()
    china_projections = {}
    china_projection_states = {}
    for domain in authorized_domains:
        if (country_projection is not None and requested_domain == domain
                and country.upper() == "CN" and relation.upper() == "OPERATES_IN"):
            china_projections[domain] = country_projection
            china_projection_states[domain] = "AVAILABLE"
            continue
        try:
            china_projections[domain] = _country_subject_projection(
                domain, "CN", "OPERATES_IN",
            )
            china_projection_states[domain] = "AVAILABLE"
        except Exception:
            # The registry can still be read if relation Evidence is not
            # available. Report that boundary on each entry instead of
            # mislabeling missing source data as no China operation.
            logger.exception("China operating relation projection unavailable")
            china_projection_states[domain] = "UNAVAILABLE"

    for subject in subjects:
        domain = subject["domain_id"]
        projection = china_projections.get(domain)
        if projection is None:
            subject["china_operation"] = {
                "country_iso": "CN",
                "relation_type": "OPERATES_IN",
                "status": "UNAVAILABLE",
                "currently_operating": None,
                "evaluated_at": evaluated_at.isoformat(timespec="seconds"),
                "claims": [],
            }
        else:
            subject["china_operation"] = _china_operation_for_subject(
                projection, subject["subject_id"], evaluated_at=evaluated_at,
            )

    projection_states = set(china_projection_states.values())
    china_operation_source_state = (
        "AVAILABLE" if projection_states == {"AVAILABLE"}
        else "UNAVAILABLE" if projection_states == {"UNAVAILABLE"}
        else "PARTIAL"
    )
    preference_actor = _subject_directory_actor(
        user, local_workspace=local_read, action="read",
    )
    working_sets = {}
    for domain in authorized_domains:
        operations = {
            subject["subject_id"]: subject["china_operation"]
            for subject in subjects_by_domain[domain]
        }
        if domain not in china_projections:
            operations = None
        working_sets[domain] = _subject_working_set_view(
            domain, preference_actor, subjects_by_domain[domain],
            china_operations=operations,
            evidence_state=china_projection_states.get(domain, "UNAVAILABLE"),
        )

    return jsonify({
        "ok": True,
        "source": "lumenis_subject_registry",
        "selection_only": True,
        "domains": [
            {"id": key, "name": value["name"], "product": value["product"]}
            for key, value in DOMAINS.items() if key in authorized_domains
        ],
        "subject_types": [
            {"id": key, "name": value} for key, value in SUBJECT_TYPES.items()
        ],
        "subjects": subjects,
        "country_categories": [
            "CN", "KR", "JP", "GB", "FR", "US", "CA", "AU", "MY", "SG",
            "TH", "BR", "NO", "OTHER",
        ],
        "china_operation_source_state": china_operation_source_state,
        "china_operation_evaluated_at": evaluated_at.isoformat(timespec="seconds"),
        "working_sets": working_sets,
        "country_projection": country_projection,
    })


@subject_registry_bp.route("/api/settings/subjects", methods=["POST"])
@require_permission(
    OperationType.CONFIG_MODIFY,
    RiskLevel.HIGH,
    resource="/api/settings/subjects",
    deny_return=lambda: (jsonify({
        "ok": False,
        "code": "PERMISSION_DENIED",
        "error": "主体登记属于系统配置变更，需要人工审批",
    }), 403),
)
def create_subject():
    try:
        subject, created = add_subject(request.get_json(silent=True) or {})
    except SubjectValidationError as exc:
        return jsonify({"ok": False, "error": str(exc), "code": "INVALID_SUBJECT"}), 400
    except SubjectRegistryUnavailableError:
        logger.exception("Canonical subject registry migration is required for writes")
        return jsonify({"ok": False, "code": "SUBJECT_REGISTRY_UNAVAILABLE",
                        "error": "主体注册表暂不可用"}), 503
    if not created:
        return jsonify({"ok": True, "created": False, "duplicate": True,
                        "selection_only": True, "subject": subject}), 200
    return jsonify({"ok": True, "created": True, "selection_only": True,
                    "subject": subject}), 201


@subject_registry_bp.route("/api/settings/subjects/working-set", methods=["POST"])
def update_subject_working_set():
    """Add/remove one identity from this actor's personal directory scope.

    The canonical Subject/BrandFocus remains shared and unchanged. Persistence,
    actor binding, version checks and the write Permission are owned by the
    existing SavedWork delivery-preferences path.
    """
    try:
        from experience_runtime import _content_source_same_origin
        from lumenis.auth.service import get_current_user
        from lumenis.system.security.permission import local_workspace_read_allowed
        from lumenis.shared.reporting import delivery_preferences

        if not _content_source_same_origin():
            return jsonify({"ok": False, "code": "SUBJECT_DIRECTORY_ORIGIN_DENIED"}), 403
        body = request.get_json(silent=True)
        required = {"domain_id", "action", "subject_id", "request_id"}
        optional = {"previous_artifact_id", "expected_draft_digest"}
        if (not isinstance(body, dict) or not required.issubset(body)
                or set(body) - required - optional):
            raise SubjectValidationError("SUBJECT_DIRECTORY_REQUEST_INVALID")
        domain = normalize_domain(body.get("domain_id"))
        action = body.get("action")
        subject_id = body.get("subject_id")
        request_id = body.get("request_id")
        previous_artifact_id = body.get("previous_artifact_id")
        expected_draft_digest = body.get("expected_draft_digest")
        if (action not in {"add", "remove"}
                or not isinstance(subject_id, str) or not subject_id
                or subject_id != subject_id.strip() or len(subject_id) > 256
                or not isinstance(request_id, str)
                or re.fullmatch(r"[0-9a-f]{32}", request_id) is None):
            raise SubjectValidationError("SUBJECT_DIRECTORY_REQUEST_INVALID")
        if (previous_artifact_id is not None
                and (not isinstance(previous_artifact_id, str)
                     or not re.fullmatch(r"ART-[0-9a-f]{16}", previous_artifact_id))):
            raise SubjectValidationError("SUBJECT_DIRECTORY_REVISION_INVALID")
        if (expected_draft_digest is not None
                and (not isinstance(expected_draft_digest, str)
                     or re.fullmatch(r"[0-9a-f]{64}", expected_draft_digest) is None)):
            raise SubjectValidationError("SUBJECT_DIRECTORY_REVISION_INVALID")
        if (previous_artifact_id is None) != (expected_draft_digest is None):
            raise SubjectValidationError("SUBJECT_DIRECTORY_REVISION_INVALID")

        user = get_current_user(read_only=True)
        local_workspace = local_workspace_read_allowed("subject_registry")
        actor = _subject_directory_actor(
            user, local_workspace=local_workspace, action="write",
        )
        if actor is None:
            return jsonify({"ok": False, "code": "SUBJECT_DIRECTORY_ACTOR_REQUIRED"}), 401
        if isinstance(actor, dict):
            from account.authorization import check_dual_domain_permission
            if not check_dual_domain_permission(
                actor["id"], "ZBMP" if domain == "BMP" else "CTH",
                module="subject_registry", action="read",
            ):
                return jsonify({"ok": False, "code": "SUBJECT_SCOPE_DENIED"}), 403

        rows = list_subjects(domain)
        active_ids = {
            row["subject_id"] for row in rows
            if row.get("status") in {"configured", "active"}
        }
        if subject_id not in active_ids:
            return jsonify({"ok": False, "code": "SUBJECT_NOT_IN_DIRECTORY"}), 404
        subject_row = next(row for row in rows if row["subject_id"] == subject_id)

        china_operations = None
        evidence_state = "UNAVAILABLE"
        try:
            china_projection = _country_subject_projection(domain, "CN", "OPERATES_IN")
            evaluated_at = datetime.now().astimezone()
            china_operations = {
                row["subject_id"]: _china_operation_for_subject(
                    china_projection, row["subject_id"], evaluated_at=evaluated_at,
                )
                for row in rows
            }
            evidence_state = "AVAILABLE"
        except Exception:
            logger.exception("Subject directory CN evidence unavailable")
            if action == "add":
                return jsonify({
                    "ok": False, "code": "SUBJECT_CN_EVIDENCE_UNAVAILABLE",
                    "state": "EVIDENCE_UNAVAILABLE",
                }), 503

        target_operation = (china_operations or {}).get(subject_id)
        if action == "add" and (
                target_operation is None
                or target_operation["status"] != "CONFIRMED_CURRENT"
                or target_operation["currently_operating"] is not True):
            return jsonify({
                "ok": False, "code": "SUBJECT_CN_OPERATION_NOT_CONFIRMED",
                "china_operation": target_operation,
            }), 409

        scope = _subject_directory_scope(domain)
        saved = delivery_preferences.read_preferences(actor=actor, scope=scope)
        preferences = saved["preferences"]
        current = preferences["subject_directory"]
        registered_ids = {row["subject_id"] for row in rows}
        removed = set(current["removed_subject_ids"]) & registered_ids
        evidenced_ids = {
            current_subject_id for current_subject_id, operation in (china_operations or {}).items()
            if operation["status"] == "CONFIRMED_CURRENT"
            and operation["currently_operating"] is True
        }
        selected = evidenced_ids - removed

        changed = False
        if action == "remove" and subject_id not in removed:
            # A removal is a durable exclusion even when current CN Evidence is
            # unavailable or no longer current. It never changes Canonical data.
            removed.add(subject_id)
            changed = True
        elif action == "add" and subject_id not in selected:
            removed.discard(subject_id)
            changed = True

        def cancellation_receipt():
            if action != "remove":
                return None
            try:
                from lumenis.system.collector.adapters.secondary_collection import (
                    cancel_subject_collection_requests,
                )
                collection_scope = {
                    "domain_id": "cth" if domain == "CTH" else "bmp",
                    "subject_id": subject_id if domain == "CTH" else None,
                    "brand_focus_id": subject_row.get("brand_focus_id") if domain == "BMP" else None,
                    "global_scope": False,
                }
                if domain == "BMP":
                    collection_scope["subject_id"] = subject_id
                return cancel_subject_collection_requests(actor=actor, scope=collection_scope)
            except Exception:
                logger.exception("Subject directory task cancellation unavailable")
                return {
                    "state": "UNAVAILABLE", "matched": 0, "cancelled": 0,
                    "cancellation_pending": 0, "already_terminal": 0, "failed": 1,
                    "network_attempted": False,
                }

        if not changed:
            readback = _subject_working_set_view(
                domain, actor, rows, china_operations=china_operations,
                evidence_state=evidence_state,
            )
            cancellation = cancellation_receipt()
            return jsonify({
                "ok": True, "state": "UNCHANGED", "action": action,
                "subject_id": subject_id, "request_id": request_id,
                "preference_save": {"state": "UNCHANGED", "persisted": saved["persisted"],
                                    "preference_ref": saved["artifact_ref"], "version": saved["version"]},
                "task_cancellation": cancellation,
                "working_set": readback,
            })

        if saved["persisted"] and (
                previous_artifact_id is None or expected_draft_digest is None):
            return jsonify({
                "ok": False, "code": "SUBJECT_DIRECTORY_BASE_REQUIRED",
                "request_id": request_id,
                "working_set": _subject_working_set_view(
                    domain, actor, rows, china_operations=china_operations,
                ),
            }), 409
        preferences["subject_directory"] = {
            "mode": "EVIDENCED_CN",
            "subject_ids": [],
            "removed_subject_ids": sorted(removed),
        }
        result = delivery_preferences.save_preferences(
            preferences,
            actor=actor,
            scope=scope,
            request_id=request_id,
            previous_artifact_id=previous_artifact_id,
            expected_draft_digest=expected_draft_digest,
        )
        readback = _subject_working_set_view(
            domain, actor, list_subjects(domain),
            china_operations=china_operations, evidence_state=evidence_state,
        )
        if not readback["persisted"] or (action == "add" and readback["state"] != "READY"):
            return jsonify({
                "ok": False, "code": "SUBJECT_DIRECTORY_READBACK_UNAVAILABLE",
                "request_id": request_id,
            }), 503
        if (not result.get("replayed") and
                ((action == "remove" and readback["state"] == "READY"
                  and subject_id in readback["subject_ids"])
                 or (action == "remove" and subject_id not in readback["removed_subject_ids"])
                 or (action == "add" and subject_id not in readback["subject_ids"]))):
            return jsonify({
                "ok": False, "code": "SUBJECT_DIRECTORY_READBACK_MISMATCH",
                "request_id": request_id,
            }), 503
        cancellation = cancellation_receipt()
        return jsonify({
            "ok": True, "state": "REPLAYED" if result.get("replayed") else "SAVED",
            "action": action, "subject_id": subject_id, "request_id": request_id,
            "preference_ref": result["artifact"]["artifact_id"],
            "version": result["document"]["version"],
            "preference_save": {"state": "REPLAYED" if result.get("replayed") else "SAVED",
                                "persisted": True,
                                "preference_ref": result["artifact"]["artifact_id"],
                                "version": result["document"]["version"]},
            "task_cancellation": cancellation,
            "working_set": readback,
        })
    except SubjectValidationError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 400
    except PermissionError:
        return jsonify({"ok": False, "code": "SUBJECT_DIRECTORY_PERMISSION_DENIED"}), 403
    except Exception as exc:
        code = str(exc)
        if code in {"WORK_REVISION_CONFLICT", "WORK_DRAFT_REVISION_CONFLICT",
                    "WORK_REQUEST_REUSE_CONFLICT"}:
            return jsonify({"ok": False, "code": "SUBJECT_DIRECTORY_VERSION_CONFLICT"}), 409
        if code in {"WORK_PERMISSION_DENIED", "WORK_EFFECT_PERMISSION_DENIED"}:
            return jsonify({"ok": False, "code": "SUBJECT_DIRECTORY_PERMISSION_DENIED"}), 403
        logger.exception("Subject directory working-set update unavailable")
        return jsonify({"ok": False, "code": "SUBJECT_DIRECTORY_UNAVAILABLE"}), 503


__all__ = [
    "DOMAINS",
    "SUBJECT_TYPES",
    "TABLE_NAME",
    "SubjectRegistryUnavailableError",
    "add_subject",
    "ensure_schema",
    "get_subject_by_id",
    "list_subjects",
    "normalize_domain",
    "normalize_subject_type",
    "subject_registry_bp",
]


_NAMES_CACHE: Dict[str, Any] = {"at": 0.0, "names": ()}


def registered_subject_names(ttl_seconds: int = 300) -> Tuple[str, ...]:
    """Names/aliases of every active registered Subject/BrandFocus (cached).

    Consumers use this instead of hardcoding one subject (e.g. Taikoo Hui);
    returns () when the registry is unavailable.
    """
    import time as _time
    now = _time.time()
    if _NAMES_CACHE["names"] and now - _NAMES_CACHE["at"] < ttl_seconds:
        return _NAMES_CACHE["names"]
    names: List[str] = []
    try:
        for row in list_subjects():
            if str(row.get("status") or "").lower() in {"archived", "disabled", "deleted"}:
                continue
            for value in [row.get("name_zh"), row.get("name_en"), *(row.get("keywords") or [])]:
                value = str(value or "").strip()
                if len(value) >= 2 and value not in names:
                    names.append(value)
    except Exception:
        return _NAMES_CACHE["names"]
    _NAMES_CACHE.update(at=now, names=tuple(names))
    return _NAMES_CACHE["names"]


def _batch_actor(domains):
    """Server identity plus existing per-domain registry permission."""
    from lumenis.system.security.permission import resolve_local_workspace_principal
    from lumenis.auth.service import get_current_user
    from account.authorization import check_dual_domain_permission

    principal = resolve_local_workspace_principal(module="reports", action="write")
    if principal is not None:
        return principal, principal.principal_ref
    actor = get_current_user(read_only=True)
    if (
        not isinstance(actor, dict)
        or type(actor.get("id")) is not int
        or actor["id"] <= 0
    ):
        raise PermissionError("AUTH_REQUIRED")
    if not all(
        check_dual_domain_permission(
            actor["id"],
            "ZBMP" if d == "BMP" else "CTH",
            module="subject_registry",
            action="write",
        )
        for d in domains
    ):
        raise PermissionError("SUBJECT_REGISTRY_WRITE_DENIED")
    return actor, "actor:" + str(actor["id"])


def prepare_subject_batch(entries):
    from lumenis.shared.reporting.saved_work import _digest

    if not isinstance(entries, list) or not 1 <= len(entries) <= 1000:
        raise SubjectValidationError("SUBJECT_BATCH_SIZE_INVALID")
    normalized = []
    seen = set()
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"baseline_id", "identity"}
            or not isinstance(entry["baseline_id"], str)
            or not entry["baseline_id"]
            or entry["baseline_id"] in seen
        ):
            raise SubjectValidationError("SUBJECT_BATCH_ENTRY_INVALID")
        seen.add(entry["baseline_id"])
        identity = entry["identity"]
        if not isinstance(identity, dict) or set(identity) - {
            "domain_id",
            "subject_type",
            "name_en",
            "name_zh",
            "industry",
            "keywords",
        }:
            raise SubjectValidationError("SUBJECT_BATCH_IDENTITY_INVALID")
        domain = normalize_domain(identity.get("domain_id"))
        kind = normalize_subject_type(identity.get("subject_type"))
        if (domain == "CTH" and kind != "company") or (
            domain == "BMP" and kind != "brand"
        ):
            raise SubjectValidationError("SUBJECT_BATCH_DOMAIN_TYPE_MISMATCH")
        en = _text(identity.get("name_en"), field="name_en")
        zh = _text(identity.get("name_zh"), field="name_zh")
        if not en or not zh:
            raise SubjectValidationError("SUBJECT_BATCH_NAMES_REQUIRED")
        normalized.append(
            {
                "baseline_id": entry["baseline_id"],
                "identity": {
                    "domain_id": domain,
                    "subject_type": kind,
                    "name_en": en,
                    "name_zh": zh,
                    "industry": _text(
                        identity.get("industry"), field="industry", max_len=120
                    ),
                    "keywords": _keywords(identity.get("keywords")),
                },
            }
        )
    domains = sorted({row["identity"]["domain_id"] for row in normalized})
    actor, caller = _batch_actor(domains)
    resource = "subject-registry-batch:v1:" + _digest(
        {"caller": caller, "entries": normalized}
    )
    return {
        "entries": normalized,
        "domains": domains,
        "caller": caller,
        "resource": resource,
        "actor": actor,
    }


@subject_registry_bp.route("/api/settings/subjects/batch", methods=["POST"])
def subject_batch_workflow():
    """Explicit prepare, human confirmation, resumable existing-owner registration."""
    from experience_runtime import _content_source_same_origin
    from lumenis.system.security.permission import get_permission_gate, PermissionLevel
    from lumenis.system.security import OperationType, RiskLevel

    try:
        if not _content_source_same_origin():
            raise PermissionError("SUBJECT_BATCH_ORIGIN_DENIED")
        body = request.get_json(silent=True)
        if (
            not isinstance(body, dict)
            or set(body)
            - {"entries", "mode", "confirm", "confirmed_resource", "resume_index", "candidate_review"}
            or body.get("mode", "prepare") not in {"prepare", "apply", "revoke"}
        ):
            raise SubjectValidationError("SUBJECT_BATCH_REQUEST_INVALID")
        prepared = prepare_subject_batch(body.get("entries"))
        review_binding = None
        review_request = body.get("candidate_review")
        if review_request is not None:
            from lumenis.shared.reporting.entity_candidate_review import registration_proposal
            from lumenis.shared.reporting.saved_work import _digest
            if (not isinstance(review_request, dict)
                    or set(review_request) != {"artifact_id", "scope"}):
                raise SubjectValidationError("SUBJECT_CANDIDATE_REVIEW_INVALID")
            review_binding = registration_proposal(
                review_request["artifact_id"], actor=prepared["actor"], scope=review_request["scope"])
            if review_binding["entries"] != prepared["entries"]:
                raise SubjectValidationError("SUBJECT_CANDIDATE_ENTRY_CHANGED")
            prepared["resource"] = "subject-registry-batch:v1:" + _digest({
                "caller": prepared["caller"], "entries": prepared["entries"],
                "candidate_review": review_binding})
        if body.get("mode", "prepare") == "prepare":
            return jsonify(
                {
                    "ok": True,
                    "state": "PREPARED",
                    "resource": prepared["resource"],
                    "entries": prepared["entries"],
                    "count": len(prepared["entries"]),
                    "approval_issued": False,
                    "creates_identity_only": True,
                }
            )
        if (
            body.get("confirm") is not True
            or body.get("confirmed_resource") != prepared["resource"]
        ):
            raise PermissionError("SUBJECT_BATCH_EXACT_CONFIRMATION_REQUIRED")
        index = body.get("resume_index", 0)
        if type(index) is not int or not 0 <= index <= len(prepared["entries"]):
            raise SubjectValidationError("SUBJECT_BATCH_RESUME_INVALID")
        gate = get_permission_gate()
        if not gate.has_permission(
            PermissionLevel.HUMAN_APPROVAL
        ) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError("SUBJECT_BATCH_MANUAL_AUTHORITY_REQUIRED")
        token = gate.get_valid_approval_token(
            "config_modify", prepared["resource"], exact=True
        )
        if body["mode"] == "revoke":
            return jsonify(
                {"ok": True, "revoked": bool(token and gate.revoke_approval(token))}
            )
        if token is None:
            token = gate.grant_approval(
                "config_modify",
                resource=prepared["resource"],
                duration_minutes=5,
                granted_by=prepared["caller"],
            )
        results = []
        for index in range(index, len(prepared["entries"])):
            entry = prepared["entries"][index]
            try:

                def authorize_current_write():
                    _actor, caller = _batch_actor(prepared["domains"])
                    if caller != prepared["caller"]:
                        raise PermissionError("SUBJECT_BATCH_IDENTITY_CHANGED")
                    if review_binding is not None:
                        current_review = registration_proposal(
                            review_request["artifact_id"], actor=_actor, scope=review_request["scope"])
                        if current_review != review_binding:
                            raise PermissionError("SUBJECT_CANDIDATE_REVIEW_CHANGED")
                    decision = gate.check(
                        OperationType.CONFIG_MODIFY,
                        resource=prepared["resource"],
                        risk_level=RiskLevel.HIGH,
                        caller=caller,
                        domain_id="system",
                        exact_approval_required=True,
                    )
                    if not decision.allowed:
                        raise PermissionError("SUBJECT_BATCH_APPROVAL_REVOKED")

                authorize_current_write()
                # Canonical exact normalized pair is idempotent. A one-name
                # collision is unresolved; never silently merge or overwrite.
                identity = entry["identity"]
                try:
                    registered, created = add_subject(
                        identity,
                        strict_identity=True,
                        _authorize_write=authorize_current_write,
                    )
                except SubjectValidationError as exc:
                    if not hasattr(exc, "conflicts"):
                        raise
                    results.append(
                        {
                            "baseline_id": entry["baseline_id"],
                            "status": "IDENTITY_CONFLICT",
                            "conflicts": exc.conflicts,
                        }
                    )
                    continue
                results.append(
                    {
                        "baseline_id": entry["baseline_id"],
                        "status": "CREATED" if created else "EXISTING",
                        "subject": registered,
                    }
                )
            except Exception as exc:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "state": "PARTIAL",
                            "results": results,
                            "resume_index": index,
                            "code": (
                                str(exc)
                                if isinstance(
                                    exc, (SubjectValidationError, PermissionError)
                                )
                                else "SUBJECT_BATCH_WRITE_FAILED"
                            ),
                        }
                    ),
                    409,
                )
        return jsonify(
            {
                "ok": True,
                "state": (
                    "COMPLETED_WITH_CONFLICTS"
                    if any(r["status"] == "IDENTITY_CONFLICT" for r in results)
                    else "COMPLETED"
                ),
                "results": results,
                "resume_index": len(prepared["entries"]),
                "resource": prepared["resource"],
                "fact_admission": "NOT_PERFORMED_BY_IDENTITY_REGISTRATION",
            }
        )
    except PermissionError as exc:
        return jsonify({"ok": False, "code": str(exc)}), 403
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "code": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "code": "SUBJECT_BATCH_UNAVAILABLE"}), 503


def subject_batch_route_matches():
    return bool(
        request.endpoint == "subject_registry.subject_batch_workflow"
        and request.url_rule is not None
        and request.url_rule.rule == "/api/settings/subjects/batch"
        and request.method == "POST"
    )


def subject_batch_local_access_allowed():
    from lumenis.system.security.permission import LocalWorkspacePrincipal

    if not subject_batch_route_matches():
        return False
    try:
        actor, _caller = _batch_actor(["CTH", "BMP"])
        return type(actor) is LocalWorkspacePrincipal
    except (PermissionError, ValueError):
        return False
