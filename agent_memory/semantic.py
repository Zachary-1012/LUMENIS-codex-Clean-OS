# -*- coding: utf-8 -*-
"""Semantic Memory（语义记忆）— 品牌知识、规则、配置、事实。

存储：复用已授权的 Source / intelligence_assets + rule_version_registry
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
      1. intelligence_assets — 有原始 Source 绑定的情报资产库（证据/知识状态/标签）
      2. rule_version_registry — 规则版本管理（主体词/排除词哈希校验）
    """

    LAYER_NAME = "semantic"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        super().__init__(db_path=db_path, enabled=enabled)

    # ── 情报资产检索（基于 intelligence_assets） ─────────────────

    def _available(self):
        if not self.enabled or not self.db_path:
            self.last_read_status = "disabled"
            return False
        if self._task_binding is None:
            self.last_read_status = "scope_required"
            return False
        self.last_read_status = "reading"
        return True

    def _research_actor_scope(self, conn):
        from agent_runtime.task_binding import authorized_context
        binding = self._binding_context(conn)
        task = dict(conn.execute("SELECT * FROM ai_task WHERE task_id=?", (binding["task_id"],)).fetchone())
        task["context"] = json.loads(task.get("context_json") or "{}")
        context = authorized_context(task, connection=conn)
        return context["actor"], {"domain_id": context["domain_id"], **context["scope"]}

    def _research_assets(self, conn, **selectors):
        from intelligence_library_api import discover_research_sources
        actor, scope = self._research_actor_scope(conn)
        rows, offset = [], 0
        while True:
            result = discover_research_sources(conn, actor=actor, scope=scope,
                limit=100, offset=offset, facts_only=True, catalog_only=True, **selectors)
            if not result["verification_complete"]:
                self.last_read_status = "partial"
            rows.extend(result["records"])
            if not result["has_more"]:
                from intelligence_library_api import verified_research_source
                from lumenis.shared.reporting.saved_work import authorize_saved_work
                context = authorize_saved_work(actor, scope, action="read", connection=conn)
                for previous in rows:
                    current = verified_research_source(conn, previous["evidence_id"],
                        actor=actor, context=context, facts_only=True)
                    if current != previous:
                        raise PermissionError("MEMORY_SOURCE_CHANGED")
                self._binding_context(conn)
                if self.last_read_status != "partial":
                    self.last_read_status = "ready" if rows else "empty"
                return rows
            offset = result["next_offset"]

    def _canonical_rows(self, limit=30, *, source_ids=None, canonical_ids=None):
        """Keep external Canonical facts and original research authority separate."""
        if not self._available():
            return []
        from canonical_data import list_scoped_canonical, CanonicalRecord, _validate_canonical_scope
        from intelligence_library_api import verified_research_source
        conn = get_db_connection(self.db_path)
        try:
            binding = self._binding_context(conn)
            actor_scope = None
            rows, offset, snapshots, originals = [], 0, {}, {}
            has_catalog = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone()
            while True:
                result = list_scoped_canonical(conn, product_id=binding["domain_id"],
                    subject_id=binding["scope"].get("subject_id"),
                    brand_focus_id=binding["scope"].get("brand_focus_id"), limit=100,
                    offset=offset, source_ids=source_ids, canonical_ids=canonical_ids, complete=True)
                for row in result["records"]:
                    snapshot = {key: value for key, value in row.items() if key != "scope_evidence"}
                    # A generic Canonical copy cannot bypass its original source
                    # or catalog. Select the producer using original Evidence.
                    evidence = conn.execute("SELECT feature_id FROM app_evidence_records WHERE id=?",
                                            (row["scope_evidence_ref"],)).fetchone()
                    catalog_id = has_catalog and conn.execute("SELECT 1 FROM intelligence_assets WHERE asset_id=?",
                                                              (row["source_id"],)).fetchone()
                    if row.get("source_table") == "intelligence_assets" or catalog_id:
                        # Catalog access is resolved by exact asset_id below,
                        # never source_id/canonical_id impersonation.
                        continue
                    if evidence and evidence[0] in {"DOCUMENT_IMPORT", "COLLECTED_SOURCE"}:
                        if actor_scope is None:
                            actor_scope = self._research_actor_scope(conn)
                        from lumenis.shared.reporting.saved_work import authorize_saved_work, SavedWorkError
                        actor, scope = actor_scope
                        context = authorize_saved_work(actor, scope, action="read", connection=conn)
                        try:
                            original = verified_research_source(conn, int(row["scope_evidence_ref"]),
                                actor=actor, context=context, facts_only=True)
                        except (SavedWorkError, ValueError, PermissionError):
                            self.last_read_status = "partial"
                            continue
                        if original["source_id"] != row["source_id"] or original["catalog_bound"]:
                            continue
                        originals[row["canonical_id"]] = original
                        row = {**row, "title": original["title"], "content": original["text"],
                               "summary": original["text"], "truth_kind": "source_reference"}
                    raw_tags = row.get("tags") or []
                    row["tags"] = json.loads(raw_tags) if isinstance(raw_tags, str) else raw_tags
                    if type(row["tags"]) is not list or any(type(tag) is not str for tag in row["tags"]):
                        raise ValueError("MEMORY_SOURCE_TAGS_INVALID")
                    rows.append(row)
                    snapshots[row["canonical_id"]] = snapshot
                if not result["truncated"] or limit is not None and len(rows) >= limit:
                    break
                offset = result["next_offset"]
            for identity, snapshot in snapshots.items():
                found = conn.execute("SELECT * FROM canonical_data WHERE canonical_id=?", (identity,)).fetchone()
                if found is None or dict(found) != snapshot:
                    raise PermissionError("MEMORY_SOURCE_CHANGED")
                record = CanonicalRecord(**{key: value for key, value in snapshot.items()
                                            if key in CanonicalRecord.__dataclass_fields__})
                if _validate_canonical_scope(conn, record) is None:
                    raise PermissionError("MEMORY_SOURCE_CHANGED")
                if identity in originals:
                    actor, scope = actor_scope
                    context = authorize_saved_work(actor, scope, action="read", connection=conn)
                    if verified_research_source(conn, int(record.scope_evidence_ref), actor=actor,
                            context=context, facts_only=True) != originals[identity]:
                        raise PermissionError("MEMORY_SOURCE_CHANGED")
            self._binding_context(conn)
            if self.last_read_status != "partial":
                self.last_read_status = "ready" if rows else "empty"
            return rows if limit is None else rows[:limit]
        finally:
            conn.close()

    def search_assets(self, query, sub_library=None, tags=None, limit=30):
        if type(limit) is not int or not 1 <= limit <= 200 or not isinstance(query, str):
            raise ValueError("MEMORY_SEARCH_INVALID")
        if tags is not None and (type(tags) is not list or any(type(tag) is not str for tag in tags)):
            raise ValueError("MEMORY_TAGS_INVALID")
        if not self._available():
            return []
        tokens = [token for token in re.split(r"[\s,，。！？、/|:：;；]+", query.casefold()) if token]
        # Search all authorized candidates before ranking/limit. A relevant old
        # source must not vanish behind 100 newer unrelated records.
        conn = get_db_connection(self.db_path)
        try:
            snapshot = (conn.execute("PRAGMA data_version").fetchone()[0], conn.total_changes)
            canonical = self._canonical_rows(None) if not sub_library else []
            partial = self.last_read_status == "partial"
            research = []
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone():
                research = self._research_assets(conn, filters={"sub_library": sub_library} if sub_library else None,
                                                 tags=tags)
            partial = partial or self.last_read_status == "partial"
            # DB versions cannot detect a deleted/replaced original Artifact.
            # Revalidate the complete combined result after both scan stages.
            if not sub_library and self._canonical_rows(None) != canonical:
                raise PermissionError("MEMORY_SOURCE_CHANGED")
            if research:
                from intelligence_library_api import verified_research_source
                from lumenis.shared.reporting.saved_work import authorize_saved_work
                actor, scope = self._research_actor_scope(conn)
                context = authorize_saved_work(actor, scope, action="read", connection=conn)
                for previous in research:
                    if verified_research_source(conn, previous["evidence_id"], actor=actor,
                            context=context, facts_only=True) != previous:
                        raise PermissionError("MEMORY_SOURCE_CHANGED")
            if partial:
                self.last_read_status = "partial"
            rows = canonical + research
            self._binding_context(conn)
            if snapshot != (conn.execute("PRAGMA data_version").fetchone()[0], conn.total_changes):
                raise PermissionError("MEMORY_SOURCE_CHANGED")
        finally:
            conn.close()
        scored = []
        for row in rows:
            if sub_library and row.get("sub_library") != sub_library:
                continue
            if tags and not all(tag in (row.get("tags") or []) for tag in tags):
                continue
            text = "\n".join(str(row.get(key) or "") for key in ("title", "summary", "content", "text", "tags")).casefold()
            score = sum(token in text for token in tokens)
            if score or not tokens:
                scored.append((score, row))
        result = [row for _, row in sorted(scored, key=lambda value: value[0], reverse=True)][:limit]
        if self.last_read_status != "partial":
            self.last_read_status = "ready" if result else "empty"
        return result

    def get_asset(self, asset_id):
        """Resolve catalog IDs first; retain exact legacy Canonical lookups.

        A known catalog identity never falls back to a generic Canonical copy,
        including when the catalog parent or source-use has been withdrawn.
        """
        if not self._available():
            return None
        if type(asset_id) is not str or not asset_id or asset_id != asset_id.strip():
            raise ValueError("LIBRARY_ASSET_ID_INVALID")
        conn = get_db_connection(self.db_path)
        try:
            self._binding_context(conn)
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone()
            catalog = exists and conn.execute("SELECT 1 FROM intelligence_assets WHERE asset_id=?", (asset_id,)).fetchone()
            if catalog:
                rows = self._research_assets(conn, asset_id=asset_id)
                self._binding_context(conn)
                return rows[0] if rows else None
        finally:
            conn.close()
        return self.get_canonical(asset_id)

    def get_canonical(self, canonical_id):
        """Explicit compatibility access to a different stable identity kind."""
        rows = self._canonical_rows(1, canonical_ids=[canonical_id])
        return rows[0] if rows else None

    def get_assets_by_library(self, sub_library, limit=50):
        return self.search_assets("", sub_library=sub_library, limit=limit)

    def get_active_rule_version(self):
        rows = self._rule_rows(1, active_only=True)
        return rows[0] if rows else None

    def _rule_rows(self, limit, *, active_only=False):
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("MEMORY_RULE_LIMIT_INVALID")
        if not self._available():
            return []
        conn = get_db_connection(self.db_path)
        try:
            self._binding_context(conn)
            rows = conn.execute("SELECT version,description,is_active,applied_at FROM rule_version_registry "
                + ("WHERE is_active=1 " if active_only else "")
                + "ORDER BY applied_at DESC,version ASC LIMIT ?", (limit,)).fetchall()
            self._binding_context(conn)
            self.last_read_status = "ready" if rows else "empty"
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_rule_history(self, limit=20):
        return self._rule_rows(limit)

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
            summary = (a.get("summary") or a.get("content") or a.get("text") or "")[:200]
            tags = a.get("tags", "")
            lines.append(f"- [{a.get('sub_library','')}] {title}: {summary} (tags: {tags})")
        return "\n".join(lines)

    def stats(self):
        return {**super().stats(), "visible_canonical_count": len(self._canonical_rows(None))}
