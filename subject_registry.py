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
import os
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import Blueprint, jsonify, request

from permission_gate import OperationType, RiskLevel, require_permission


subject_registry_bp = Blueprint("subject_registry", __name__)

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


def ensure_schema(conn) -> None:
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            subject_id TEXT PRIMARY KEY,
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
        ensure_schema(conn)
        if normalized:
            rows = conn.execute(
                f"SELECT subject_id, domain_id, subject_type, name_en, name_zh, industry, "
                f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
                "WHERE domain_id=? AND status != 'archived' ORDER BY updated_at DESC, name_en_norm",
                (normalized,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT subject_id, domain_id, subject_type, name_en, name_zh, industry, "
                f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
                "WHERE status != 'archived' ORDER BY updated_at DESC, name_en_norm"
            ).fetchall()
    return [_row_to_dict(row) for row in rows]


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
    now = _now()

    with _db_ready() as conn:
        ensure_schema(conn)
        existing = conn.execute(
            f"SELECT subject_id, domain_id, subject_type, name_en, name_zh, industry, "
            f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} "
            "WHERE domain_id=? AND subject_type=? AND name_en_norm=? AND name_zh_norm=?",
            (domain_id, subject_type, en_norm, zh_norm),
        ).fetchone()
        if existing:
            return _row_to_dict(existing), False
        conn.execute(
            f"INSERT INTO {TABLE_NAME} (subject_id, domain_id, subject_type, name_en, name_zh, "
            "name_en_norm, name_zh_norm, industry, keywords_json, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'configured', ?, ?)",
            (subject_id, domain_id, subject_type, name_en, name_zh, en_norm, zh_norm,
             industry, json.dumps(keywords, ensure_ascii=False), now, now),
        )
        row = conn.execute(
            f"SELECT subject_id, domain_id, subject_type, name_en, name_zh, industry, "
            f"keywords_json, status, created_at, updated_at FROM {TABLE_NAME} WHERE subject_id=?",
            (subject_id,),
        ).fetchone()
    return _row_to_dict(row), True


@subject_registry_bp.route("/api/settings/subjects", methods=["GET"])
def get_subjects():
    domain_arg = request.args.get("domain_id") or request.args.get("domain")
    try:
        subjects = list_subjects(domain_arg)
    except SubjectValidationError as exc:
        return jsonify({"ok": False, "error": str(exc), "code": "INVALID_SUBJECT_SCOPE"}), 400
    return jsonify({
        "ok": True,
        "source": "lumenis_subject_registry",
        "selection_only": True,
        "domains": [
            {"id": key, "name": value["name"], "product": value["product"]}
            for key, value in DOMAINS.items()
        ],
        "subject_types": [
            {"id": key, "name": value} for key, value in SUBJECT_TYPES.items()
        ],
        "subjects": subjects,
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
    if not created:
        return jsonify({"ok": True, "created": False, "duplicate": True,
                        "selection_only": True, "subject": subject}), 200
    return jsonify({"ok": True, "created": True, "selection_only": True,
                    "subject": subject}), 201


__all__ = [
    "DOMAINS",
    "SUBJECT_TYPES",
    "TABLE_NAME",
    "add_subject",
    "ensure_schema",
    "list_subjects",
    "normalize_domain",
    "normalize_subject_type",
    "subject_registry_bp",
]
