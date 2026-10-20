# -*- coding: utf-8 -*-
"""Zachary OS AI · Unified Resource Library（统一资源库查询层）

Contract：OSAI 研究侧 → ZBC 生产侧。
对齐 AUDIT_HANDOFF："资源共享，真相隔离；能力共享，产品边界不共享"。

物理并表后统一查询 resources 表：
  - resource_category = brand_theory（品牌理论，原 brand_knowledge）
  - resource_category = case_study（深度案例，原 case_deep_analysis）
  - resource_category = industry_monitor（行业监控，原 brand_industry_monitor）

原表保留为 _legacy 兼容旧代码写入；sync_from_legacy_tables() 做增量同步。

核心原则：
  1. 资源作为参考，不直接成为生产规则（is_production_rule=0 的才是参考资源）
  2. 统一 Resource Pipeline 元数据（resource_uid/provenance/dedup_hash/evidence_id）
  3. Context Isolation：查询时可按 product_context 隔离
  4. Zachary 检索只返回参考资源，生产规则需显式标记
"""
from __future__ import annotations
import json
import sqlite3
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()

# 资源类别元数据（物理并表后不再关联表名，仅作类别配置）
RESOURCE_REGISTRY = {
    "brand_theory": {
        "label": "品牌理论",
        "legacy_table": "brand_knowledge",
        "title_col": "title",
    },
    "case_study": {
        "label": "深度案例",
        "legacy_table": "case_deep_analysis",
        "title_col": "case_title",
    },
    "industry_monitor": {
        "label": "行业监控",
        "legacy_table": "brand_industry_monitor",
        "title_col": "brand_name",
    },
}


def _get_conn() -> sqlite3.Connection:
    return get_repository().connect(timeout=10)


def _row_to_resource(row: sqlite3.Row) -> dict:
    """把 resources 表行统一转换为 Resource 输出格式。"""
    d = dict(row)
    resource = {
        "resource_uid": d.get("resource_uid", ""),
        "resource_category": d.get("resource_category", ""),
        "title": d.get("title", ""),
        "summary": (d.get("content", "") or "")[:500],
        "content": d.get("content", ""),
        "tags": d.get("tags", ""),
        "source": d.get("source", ""),
        "url": d.get("url", ""),
        "provenance": _safe_json(d.get("provenance")),
        "dedup_hash": d.get("dedup_hash", ""),
        "evidence_id": d.get("evidence_id"),
        "pipeline_stage": d.get("pipeline_stage", "resource"),
        "is_production_rule": bool(d.get("is_production_rule", 0)),
        "product_context": d.get("product_context", "CTH"),
        "normalized_at": d.get("normalized_at", ""),
        "created_at": d.get("created_at", ""),
        "updated_at": d.get("updated_at", ""),
        "raw_id": d.get("id"),
        "extras": _safe_json(d.get("extra_json")),
    }
    return resource


def _safe_json(val):
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return val


def search_resources(
    *,
    query: str = "",
    category: str = "",
    tags: str = "",
    product_context: str = "",
    reference_only: bool = True,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """统一搜索 resources 表，返回标准化 Resource 列表。

    Args:
      query: 标题/内容关键词（模糊匹配）
      category: 资源类别（brand_theory/case_study/industry_monitor），空=全部
      tags: 标签/行业关键词
      product_context: 产品上下文隔离（CTH/ZBMP），空=不过滤
      reference_only: True=只返回参考资源（is_production_rule=0），默认 True
      limit/offset: 分页

    Returns:
      {total, returned, limit, offset, resources: [...]}
    """
    conditions = []
    params = []

    if query:
        conditions.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
        params.extend([f"%{query}%"] * 3)

    if category:
        conditions.append("resource_category = ?")
        params.append(category)

    if tags:
        conditions.append("tags LIKE ?")
        params.append(f"%{tags}%")

    if product_context:
        conditions.append("product_context = ?")
        params.append(product_context)

    if reference_only:
        conditions.append("(is_production_rule = 0 OR is_production_rule IS NULL)")

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = _get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) as cnt FROM resources{where}", params).fetchone()["cnt"]
        sql = f"SELECT * FROM resources{where} ORDER BY COALESCE(updated_at, created_at) DESC LIMIT ? OFFSET ?"
        rows = conn.execute(sql, params + [limit, offset]).fetchall()
        resources = [_row_to_resource(row) for row in rows]
        return {
            "total": total,
            "returned": len(resources),
            "limit": limit,
            "offset": offset,
            "resources": resources,
        }
    finally:
        conn.close()


def get_resource(resource_uid: str) -> Optional[dict]:
    """按 resource_uid 获取单条 Resource。"""
    if not resource_uid:
        return None
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM resources WHERE resource_uid = ?", (resource_uid,)).fetchone()
        if row:
            return _row_to_resource(row)
        return None
    finally:
        conn.close()


def get_resource_stats() -> dict:
    """统一资源库统计（直接查 resources 表）。"""
    conn = _get_conn()
    stats = {"total": 0, "by_category": {}, "reference_vs_rule": {"reference": 0, "production_rule": 0},
             "by_product_context": {}}
    try:
        stats["total"] = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]

        for row in conn.execute("SELECT resource_category, COUNT(*) as cnt FROM resources GROUP BY resource_category"):
            stats["by_category"][row["resource_category"]] = row["cnt"]

        ref = conn.execute(
            "SELECT COUNT(*) FROM resources WHERE is_production_rule = 0 OR is_production_rule IS NULL"
        ).fetchone()[0]
        stats["reference_vs_rule"]["reference"] = ref
        stats["reference_vs_rule"]["production_rule"] = stats["total"] - ref

        for row in conn.execute(
            "SELECT COALESCE(product_context,'CTH') as pc, COUNT(*) as cnt FROM resources GROUP BY pc"
        ):
            stats["by_product_context"][row["pc"]] = row["cnt"]
        return stats
    finally:
        conn.close()


def list_categories() -> list[dict]:
    """列出所有资源类别及其配置。"""
    return [
        {"category": cat, "label": cfg["label"], "legacy_table": cfg["legacy_table"]}
        for cat, cfg in RESOURCE_REGISTRY.items()
    ]


def sync_from_legacy_tables() -> dict:
    """从原三张表增量同步到 resources 表（物理并表后的兼容同步）。

    原表保留供旧代码写入；每次查询前可调用此函数确保 resources 表数据最新。
    重复资源采用 INSERT OR IGNORE：保留已存资源及出处元数据，不刷新既有行。
    返回同步统计。
    """
    conn = _get_conn()
    synced = {"brand_theory": 0, "case_study": 0, "industry_monitor": 0, "total": 0}
    try:
        # brand_knowledge → brand_theory
        for row in conn.execute("SELECT * FROM brand_knowledge"):
            d = dict(row)
            extra = json.dumps({"relevance_score": d.get("relevance_score"), "content_hash": d.get("content_hash"),
                                 "category_original": d.get("category")}, ensure_ascii=False)
            insert_result = conn.execute("""INSERT OR IGNORE INTO resources
                (resource_uid, resource_category, title, content, tags, source, url,
                 provenance, pipeline_stage, evidence_id, normalized_at, dedup_hash,
                 is_production_rule, product_context, extra_json, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d.get("resource_uid") or f"brand_theory_{d['id']}", "brand_theory",
                 d.get("title"), d.get("content"), d.get("tags"), d.get("source"), d.get("url"),
                 d.get("provenance"), d.get("pipeline_stage"), d.get("evidence_id"), d.get("normalized_at"),
                 d.get("dedup_hash") or d.get("content_hash"), d.get("is_production_rule") or 0,
                 d.get("product_context") or "CTH", extra, d.get("created_at"), d.get("updated_at")))
            if insert_result.rowcount == 1:
                synced["brand_theory"] += 1

        # case_deep_analysis → case_study
        for row in conn.execute("SELECT * FROM case_deep_analysis"):
            d = dict(row)
            content_parts = [f"[{k}]\n{d[k]}" for k in
                             ["basic_info", "challenge", "strategy", "big_idea", "execution", "results",
                              "success_factors", "system_insights"] if d.get(k)]
            content = "\n\n".join(content_parts)
            tags = ",".join(filter(None, [d.get("case_type") or "", d.get("industry") or "", d.get("brand") or ""]))
            extra_keys = set(d.keys()) - {"id", "resource_uid", "resource_category", "pipeline_stage",
                "provenance", "evidence_id", "normalized_at", "dedup_hash", "is_production_rule",
                "product_context", "case_title", "basic_info", "challenge", "strategy", "big_idea",
                "execution", "results", "success_factors", "system_insights", "case_type", "industry",
                "brand", "created_at", "updated_at"}
            extra = json.dumps({k: d[k] for k in extra_keys}, ensure_ascii=False)
            insert_result = conn.execute("""INSERT OR IGNORE INTO resources
                (resource_uid, resource_category, title, content, tags, source, url,
                 provenance, pipeline_stage, evidence_id, normalized_at, dedup_hash,
                 is_production_rule, product_context, extra_json, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d.get("resource_uid") or f"case_study_{d['id']}", "case_study",
                 d.get("case_title"), content, tags, d.get("brand") or "", "",
                 d.get("provenance"), d.get("pipeline_stage"), d.get("evidence_id"), d.get("normalized_at"),
                 d.get("dedup_hash") or f"case_{d.get('case_id') or d['id']}", d.get("is_production_rule") or 0,
                 d.get("product_context") or "CTH", extra, d.get("created_at"), d.get("updated_at")))
            if insert_result.rowcount == 1:
                synced["case_study"] += 1

        # brand_industry_monitor → industry_monitor
        for row in conn.execute("SELECT * FROM brand_industry_monitor"):
            d = dict(row)
            title = d.get("brand_name_cn") or d.get("brand_name") or f"brand_{d['id']}"
            content = f"行业: {d.get('industry') or ''}\n楼层: {d.get('floor') or ''}\n铺位: {d.get('shop_number') or ''}\n风险等级: {d.get('risk_level') or ''}"
            tags = ",".join(filter(None, [d.get("industry") or "", d.get("risk_level") or ""]))
            extra_keys = set(d.keys()) - {"id", "resource_uid", "resource_category", "pipeline_stage",
                "provenance", "evidence_id", "normalized_at", "dedup_hash", "is_production_rule",
                "product_context", "brand_name", "brand_name_cn", "industry", "floor", "shop_number",
                "risk_level", "last_updated", "created_at", "updated_at"}
            extra = json.dumps({k: d[k] for k in extra_keys}, ensure_ascii=False)
            insert_result = conn.execute("""INSERT OR IGNORE INTO resources
                (resource_uid, resource_category, title, content, tags, source, url,
                 provenance, pipeline_stage, evidence_id, normalized_at, dedup_hash,
                 is_production_rule, product_context, extra_json, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (d.get("resource_uid") or f"industry_monitor_{d['id']}", "industry_monitor",
                 title, content, tags, "", "",
                 d.get("provenance"), d.get("pipeline_stage"), d.get("evidence_id"), d.get("normalized_at"),
                 d.get("dedup_hash") or f"brand_{d.get('brand_name') or d['id']}", d.get("is_production_rule") or 0,
                 d.get("product_context") or "CTH", extra, d.get("last_updated") or d.get("created_at"),
                 d.get("last_updated") or d.get("updated_at")))
            if insert_result.rowcount == 1:
                synced["industry_monitor"] += 1

        conn.commit()
        synced["total"] = sum(
            synced[category] for category in ("brand_theory", "case_study", "industry_monitor")
        )
        return synced
    except Exception as e:
        conn.rollback()
        return {"error": str(e), "total": 0}
    finally:
        conn.close()


__all__ = [
    "search_resources",
    "get_resource",
    "get_resource_stats",
    "list_categories",
    "sync_from_legacy_tables",
    "RESOURCE_REGISTRY",
]
