# -*- coding: utf-8 -*-
"""Zachary OS AI · Unified Resource Library（统一资源库查询层）

Contract：OSAI 研究侧 → ZBC 生产侧。
对齐 AUDIT_HANDOFF："资源共享，真相隔离；能力共享，产品边界不共享"。

把三张平行知识表统一为 Resource 视图：
  - brand_knowledge       → resource_category = brand_theory（品牌理论）
  - case_deep_analysis    → resource_category = case_study（深度案例）
  - brand_industry_monitor→ resource_category = industry_monitor（行业监控）

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

DB_PATH = os.environ.get("ZBC_DB_PATH", str(Path(__file__).parent / "data" / "monitor.db"))

# 资源类别注册表：表名 → 类别配置
RESOURCE_REGISTRY = {
    "brand_theory": {
        "table": "brand_knowledge",
        "title_col": "title",
        "summary_cols": ["content"],
        "tag_col": "tags",
        "time_col": "created_at",
        "extra_cols": ["category", "source", "url", "relevance_score"],
    },
    "case_study": {
        "table": "case_deep_analysis",
        "title_col": "case_title",
        "summary_cols": ["big_idea", "challenge"],
        "tag_col": "industry",
        "time_col": "created_at",
        "extra_cols": ["case_id", "brand", "agency", "industry", "year", "case_type", "quality_score"],
    },
    "industry_monitor": {
        "table": "brand_industry_monitor",
        "title_col": "brand_name",
        "summary_cols": ["industry", "floor"],
        "tag_col": "industry",
        "time_col": "last_updated",
        "extra_cols": ["brand_name_cn", "note_count", "negative_count", "positive_count",
                       "total_engagement", "risk_level"],
    },
}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_resource(row: sqlite3.Row, category: str, cfg: dict) -> dict:
    """把表行统一转换为 Resource 输出格式。"""
    d = dict(row)
    # 摘要：拼接 summary_cols，截断
    summary_parts = []
    for col in cfg["summary_cols"]:
        val = d.get(col, "")
        if val:
            summary_parts.append(str(val))
    summary = " ".join(summary_parts)[:500]

    resource = {
        "resource_uid": d.get("resource_uid", ""),
        "resource_category": category,
        "title": d.get(cfg["title_col"], ""),
        "summary": summary,
        "tags": d.get(cfg["tag_col"], ""),
        "provenance": _safe_json(d.get("provenance")),
        "dedup_hash": d.get("dedup_hash", ""),
        "evidence_id": d.get("evidence_id"),
        "pipeline_stage": d.get("pipeline_stage", "resource"),
        "is_production_rule": bool(d.get("is_production_rule", 0)),
        "product_context": d.get("product_context", "CTH"),
        "normalized_at": d.get("normalized_at", ""),
        "created_at": d.get(cfg["time_col"], ""),
        "raw_id": d.get("id"),
    }
    # 附加类别特有字段
    extras = {}
    for col in cfg["extra_cols"]:
        if col in d:
            extras[col] = d[col]
    resource["extras"] = extras
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
    """统一搜索三张知识表，返回标准化 Resource 列表。

    Args:
      query: 标题/内容关键词（模糊匹配）
      category: 资源类别（brand_theory/case_study/industry_monitor），空=全部
      tags: 标签/行业关键词
      product_context: 产品上下文隔离（CTH/ZBMP），空=不过滤
      reference_only: True=只返回参考资源（is_production_rule=0），默认 True
      limit/offset: 分页

    Returns:
      {total, resources: [...], categories: {...}}
    """
    categories = [category] if category else list(RESOURCE_REGISTRY.keys())
    all_resources = []

    conn = _get_conn()
    try:
        for cat in categories:
            if cat not in RESOURCE_REGISTRY:
                continue
            cfg = RESOURCE_REGISTRY[cat]
            table = cfg["table"]
            title_col = cfg["title_col"]

            conditions = []
            params = []

            if query:
                # 标题或摘要列模糊匹配
                like_cols = [title_col] + cfg["summary_cols"]
                like_clause = " OR ".join([f"{col} LIKE ?" for col in like_cols])
                conditions.append(f"({like_clause})")
                params.extend([f"%{query}%"] * len(like_cols))

            if tags:
                tag_col = cfg["tag_col"]
                if tag_col:
                    conditions.append(f"{tag_col} LIKE ?")
                    params.append(f"%{tags}%")

            if product_context:
                conditions.append("product_context = ?")
                params.append(product_context)

            if reference_only:
                conditions.append("(is_production_rule = 0 OR is_production_rule IS NULL)")

            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            sql = f"SELECT * FROM [{table}]{where} ORDER BY id DESC"
            rows = conn.execute(sql, params).fetchall()
            for row in rows:
                all_resources.append(_row_to_resource(row, cat, cfg))

        # 统一按时间排序（新的在前）
        all_resources.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        total = len(all_resources)
        page = all_resources[offset:offset + limit]
        return {
            "total": total,
            "returned": len(page),
            "limit": limit,
            "offset": offset,
            "resources": page,
        }
    finally:
        conn.close()


def get_resource(resource_uid: str) -> Optional[dict]:
    """按 resource_uid 获取单条 Resource（跨表查找）。"""
    if not resource_uid:
        return None
    # uid 格式：category_id
    category = resource_uid.rsplit("_", 1)[0] if "_" in resource_uid else ""
    conn = _get_conn()
    try:
        for cat, cfg in RESOURCE_REGISTRY.items():
            if category and cat != category:
                continue
            table = cfg["table"]
            row = conn.execute(
                f"SELECT * FROM [{table}] WHERE resource_uid = ?", (resource_uid,)
            ).fetchone()
            if row:
                return _row_to_resource(row, cat, cfg)
        return None
    finally:
        conn.close()


def get_resource_stats() -> dict:
    """统一资源库统计。"""
    conn = _get_conn()
    stats = {"total": 0, "by_category": {}, "reference_vs_rule": {"reference": 0, "production_rule": 0},
             "by_product_context": {}}
    try:
        for cat, cfg in RESOURCE_REGISTRY.items():
            table = cfg["table"]
            cnt = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            stats["by_category"][cat] = cnt
            stats["total"] += cnt

            ref = conn.execute(
                f"SELECT COUNT(*) FROM [{table}] WHERE is_production_rule = 0 OR is_production_rule IS NULL"
            ).fetchone()[0]
            rule = cnt - ref
            stats["reference_vs_rule"]["reference"] += ref
            stats["reference_vs_rule"]["production_rule"] += rule

            for row in conn.execute(
                f"SELECT COALESCE(product_context,'CTH') as pc, COUNT(*) as cnt FROM [{table}] GROUP BY pc"
            ):
                pc = row["pc"]
                stats["by_product_context"][pc] = stats["by_product_context"].get(pc, 0) + row["cnt"]
        return stats
    finally:
        conn.close()


def list_categories() -> list[dict]:
    """列出所有资源类别及其配置。"""
    return [
        {"category": cat, "table": cfg["table"], "title_field": cfg["title_col"]}
        for cat, cfg in RESOURCE_REGISTRY.items()
    ]


__all__ = [
    "search_resources",
    "get_resource",
    "get_resource_stats",
    "list_categories",
    "RESOURCE_REGISTRY",
]
