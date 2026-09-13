# -*- coding: utf-8 -*-
"""Semantic Memory（语义记忆）— 品牌知识、规则、配置、事实。

存储：复用 intelligence_assets 表（711行）+ rule_version_registry 表
检索：关键词 + 标签检索
与 OSAI memory_lifecycle.py 的 semantic dict 对齐。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMemoryLayer, MemoryRecord, get_db_connection


class SemanticMemory(BaseMemoryLayer):
    """语义记忆：品牌知识库 + 规则版本库。

    两个数据源：
      1. intelligence_assets — 情报资产库（711条，含证据等级/知识状态/标签）
      2. rule_version_registry — 规则版本管理（主体词/排除词哈希校验）
    """

    LAYER_NAME = "semantic"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        super().__init__(db_path=db_path, enabled=enabled)

    # ── 情报资产检索（基于 intelligence_assets） ─────────────────

    def search_assets(self, query: str, sub_library: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      limit: int = 30) -> List[Dict[str, Any]]:
        """按关键词 + 标签检索情报资产。"""
        if not self.enabled or not self.db_path:
            return []
        tokens = [t for t in re.split(r"[\s,，。！？、/|:：;；]+", query.lower()) if len(t) >= 2]
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM intelligence_assets WHERE knowledge_status IN ('FACT','VERIFIED') AND admission_status='ADMITTED'"
                params: list = []
                if sub_library:
                    sql += " AND sub_library=?"
                    params.append(sub_library)
                sql += " ORDER BY updated_at DESC LIMIT 500"
                rows = conn.execute(sql, params).fetchall()

                scored: List[Tuple[int, Dict[str, Any]]] = []
                for row in rows:
                    d = dict(row)
                    text = " ".join(str(d.get(k, "")) for k in
                                    ("title", "summary", "tags", "sub_library")).lower()
                    score = 0
                    if tokens:
                        score = sum(2 for t in tokens if t in text)
                    if tags:
                        row_tags = (d.get("tags") or "").lower()
                        score += sum(3 for t in tags if t.lower() in row_tags)
                    if score > 0 or not tokens:
                        scored.append((score, d))
                scored.sort(key=lambda x: x[0], reverse=True)
                return [r for _, r in scored[:limit]]
            finally:
                conn.close()
        except Exception:
            return []

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """按 asset_id 获取情报资产详情。"""
        if not self.enabled or not self.db_path:
            return None
        try:
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute(
                    "SELECT * FROM intelligence_assets WHERE asset_id=? AND knowledge_status IN ('FACT','VERIFIED') AND admission_status='ADMITTED'", (asset_id,)
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except Exception:
            return None

    def get_assets_by_library(self, sub_library: str,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """按子库获取情报资产。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    """SELECT * FROM intelligence_assets
                       WHERE sub_library=? AND knowledge_status IN ('FACT','VERIFIED')
                       AND admission_status='ADMITTED' ORDER BY updated_at DESC LIMIT ?""",
                    (sub_library, limit),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    # ── 规则版本检索（基于 rule_version_registry） ───────────────

    def get_active_rule_version(self) -> Optional[Dict[str, Any]]:
        """获取当前激活的规则版本。"""
        if not self.enabled or not self.db_path:
            return None
        try:
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute(
                    "SELECT * FROM rule_version_registry WHERE is_active=1 LIMIT 1"
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except Exception:
            return None

    def get_rule_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取规则版本历史。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                rows = conn.execute(
                    "SELECT * FROM rule_version_registry ORDER BY applied_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    # ── 知识存储（内存，不直接写 intelligence_assets） ───────────

    def store_knowledge(self, key: str, knowledge: Dict[str, Any],
                        tags: Optional[List[str]] = None) -> Optional[MemoryRecord]:
        """存储语义知识到内存（不直接写 intelligence_assets 表）。"""
        return self.store(
            key=key,
            value=knowledge,
            metadata={"type": "semantic_knowledge", "tags": tags or []},
        )

    def get_knowledge_context(self, query: str, limit: int = 5) -> str:
        """为 AI prompt 生成知识上下文（检索 top-N 资产摘要）。"""
        assets = self.search_assets(query, limit=limit)
        if not assets:
            return ""
        lines = ["【语义记忆检索结果】"]
        for a in assets:
            title = a.get("title", "未知")
            summary = (a.get("summary") or "")[:200]
            tags = a.get("tags", "")
            lines.append(f"- [{a.get('sub_library','')}] {title}: {summary} (tags: {tags})")
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        if self.db_path:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    ia = conn.execute("SELECT COUNT(*) FROM intelligence_assets WHERE knowledge_status IN ('FACT','VERIFIED') AND admission_status='ADMITTED'").fetchone()[0]
                    rv = conn.execute("SELECT COUNT(*) FROM rule_version_registry").fetchone()[0]
                    s["intelligence_assets_total"] = ia
                    s["rule_version_total"] = rv
                finally:
                    conn.close()
            except Exception:
                pass
        return s
