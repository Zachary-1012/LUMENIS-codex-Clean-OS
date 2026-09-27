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


def list_subjects(domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
    normalized = normalize_domain(domain_id) if domain_id else None
    with _db_ready() as conn:
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


def add_subject(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    if not isinstance(payload, dict):
        raise SubjectValidationError("请求体必须是 JSON 对象")
    domain_id = normalize_domain(payload.get("domain_id"))
    subject_type = normalize_subject_type(payload.get("subject_type"))
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
        existing = conn.execute(
            f"SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, industry, "
            f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
            "WHERE domain_id=? AND subject_type=? AND name_en_norm=? AND name_zh_norm=?",
            (domain_id, subject_type, en_norm, zh_norm),
        ).fetchone()
        if existing:
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
    return _row_to_dict(row), True


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


@subject_registry_bp.route("/api/settings/subjects", methods=["GET"])
def get_subjects():
    # Listing is scoped to the authenticated account and this registry module.
    # Basic auth alone has no product identity, so it cannot authorize this
    # domain-sensitive response.
    from lumenis.auth.service import get_current_user

    user = get_current_user()
    if not user or not isinstance(user.get("id"), int):
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
            if check_dual_domain_permission(
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
    try:
        subjects = [
            subject
            for domain in authorized_domains
            for subject in list_subjects(domain)
        ]
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
