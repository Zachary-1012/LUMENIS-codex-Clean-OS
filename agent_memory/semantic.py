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


def _source_context(actor, scope, connection):
    from lumenis.shared.reporting import saved_work
    try:
        return saved_work.authorize_saved_work(actor, scope, action='read', connection=connection)
    except saved_work.SavedWorkError as exc:
        raise PermissionError('MEMORY_SOURCE_ACCESS_DENIED') from exc


def _reference_fields(reference):
    common = {'type', 'sha256', 'version', 'start', 'end'}
    kinds = {'evidence': {'evidence_id', 'integrity_digest'},
             'private_document': {'artifact_id', 'source_sha256', 'text_sha256'},
             'saved_work': {'artifact_id'}}
    if (type(reference) is not dict or type(reference.get('type')) is not str
            or reference['type'] not in kinds):
        raise ValueError('MEMORY_REFERENCE_INVALID')
    if set(reference) != common | kinds[reference['type']]:
        raise ValueError('MEMORY_REFERENCE_INVALID')
    for key in ('sha256', 'integrity_digest', 'source_sha256', 'text_sha256'):
        if key in reference and (type(reference[key]) is not str or not re.fullmatch(r'[0-9a-f]{64}', reference[key])):
            raise ValueError('MEMORY_REFERENCE_INVALID')
    if (any(type(reference[key]) is not int for key in ('start', 'end'))
            or not 0 <= reference['start'] < reference['end']
            or reference['end'] - reference['start'] > 64000):
        raise ValueError('MEMORY_REFERENCE_RANGE_INVALID')
    if reference['type'] == 'evidence':
        if (type(reference['evidence_id']) is not int or reference['evidence_id'] <= 0
                or type(reference['version']) is not str or not reference['version']
                or len(reference['version']) > 256):
            raise ValueError('MEMORY_REFERENCE_INVALID')
    elif (type(reference['artifact_id']) is not str or not re.fullmatch(r'ART-[0-9a-f]{16}', reference['artifact_id'])
            or type(reference['version']) is not int or reference['version'] < 1):
        raise ValueError('MEMORY_REFERENCE_INVALID')


def _workspace_work_source(item, *, actor, scope, connection):
    from lumenis.importer.documents import _read_private_document_material
    document, artifact = item['document'], item['artifact']
    reference = {'type': 'saved_work', 'artifact_id': artifact['artifact_id'],
                 'sha256': artifact['sha256'], 'version': document['version']}
    text, basis = document['markdown'], 'saved_document_markdown'
    if 'source_material' in document['payload']:
        record, parsed = _read_private_document_material(artifact['artifact_id'], actor=actor,
                                                        scope=scope, connection=connection)
        reference.update(type='private_document', source_sha256=record['source_fingerprint'],
                         text_sha256=record['content_hash'])
        text, basis = parsed.text, 'retained_original_parsed_text'
    return {'title': document['title'], 'text': text, 'reference': reference,
            'text_basis': basis, 'fact_verification': 'NOT_VERIFIED', 'truth_kind': 'source_reference'}


def read_source_reference(reference, *, actor, scope, connection):
    """Reopen exact original bytes; this reference grants no model or effect use."""
    from intelligence_library_api import verified_research_source
    from lumenis.shared.reporting import saved_work
    _reference_fields(reference)
    context = _source_context(actor, scope, connection)
    snapshot = (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes)
    try:
        if reference['type'] == 'evidence':
            source = verified_research_source(connection, reference['evidence_id'], actor=actor, context=context)
            expected = {'type': 'evidence', 'evidence_id': source['evidence_id'], 'sha256': source['content_hash'],
                        'integrity_digest': source['integrity_digest'], 'version': source['version']}
            item = {'title': source['title'], 'text': source['text'], 'reference': expected,
                    'text_basis': 'signed_source_parsed_text', 'fact_verification': 'NOT_VERIFIED',
                    'truth_kind': 'source_reference'}
        else:
            work = saved_work.read_committed_work(reference['artifact_id'], actor=actor, scope=scope, connection=connection)
            versions = saved_work._versions(connection, work['document']['work_id'], context, actor)
            if not versions or versions[-1]['artifact']['artifact_id'] != reference['artifact_id']:
                raise RuntimeError('MEMORY_REFERENCE_CHANGED')
            item = _workspace_work_source(work, actor=actor, scope=scope, connection=connection)
            expected = item['reference']
        if (expected != {key: value for key, value in reference.items() if key not in {'start', 'end'}}
                or reference['end'] > len(item['text']) or not item['text'][reference['start']:reference['end']].strip()):
            raise RuntimeError('MEMORY_REFERENCE_CHANGED')
    except (saved_work.SavedWorkError, PermissionError, OSError, ValueError) as exc:
        if isinstance(exc, PermissionError) or any(word in str(exc) for word in ('PERMISSION', 'RIGHTS', 'AUTHORIZATION')):
            raise PermissionError('MEMORY_SOURCE_ACCESS_DENIED') from exc
        raise RuntimeError('MEMORY_REFERENCE_CHANGED') from exc
    _source_context(actor, scope, connection)
    if snapshot != (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes):
        raise RuntimeError('MEMORY_REFERENCE_CHANGED')
    return {**item, 'reference': dict(reference), 'text': item['text'][reference['start']:reference['end']],
            'character_count': len(item['text']), 'state': 'available', 'offset_unit': 'unicode_codepoint',
            'model_source_use': 'NOT_GRANTED', 'training_admission': 'NOT_GRANTED'}


def search_authorized_sources(query, *, actor, scope, connection, limit=30, offset=0, expected_snapshot=None):
    """Normal workspace search without manufacturing a Task or a second library."""
    from intelligence_library_api import discover_research_sources
    from lumenis.shared.reporting import saved_work

    from .retrieval import lexical_search, original_passage
    if (type(query) is not str or not query.strip() or len(query) > 2000
            or type(limit) is not int or not 1 <= limit <= 50
            or type(offset) is not int or offset < 0):
        raise ValueError('MEMORY_SEARCH_INVALID')
    if expected_snapshot is not None and (type(expected_snapshot) is not str
            or not re.fullmatch(r'[0-9a-f]{64}', expected_snapshot)):
        raise ValueError('MEMORY_SEARCH_INVALID')
    if offset and expected_snapshot is None:
        raise RuntimeError('MEMORY_SEARCH_SNAPSHOT_REQUIRED')
    _source_context(actor, scope, connection)
    snapshot = (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes)
    candidates, complete, total_bytes, cursor = [], True, 0, None
    while True:
        page = saved_work.search_work(actor=actor, scope=scope, limit=100, cursor=cursor, latest_only=True)
        complete = complete and page['verification_complete']
        for work in page['items']:
            try:
                candidate = _workspace_work_source(work, actor=actor, scope=scope, connection=connection)
            except (saved_work.SavedWorkError, PermissionError, OSError, ValueError):
                complete = False
                continue
            candidates.append(candidate)
            total_bytes += len(candidate['text'].encode('utf-8'))
        if total_bytes > 64 * 1024 * 1024:
            raise RuntimeError('MEMORY_SEARCH_CAPACITY_EXCEEDED')
        if not page['has_more']:
            break
        cursor = page['next_cursor']
    position = 0
    while True:
        page = discover_research_sources(connection, actor=actor, scope=scope, limit=100, offset=position)
        complete = complete and page['verification_complete']
        for source in page['records']:
            candidates.append({'title': source['title'], 'text': source['text'],
                'reference': {'type': 'evidence', 'evidence_id': source['evidence_id'], 'sha256': source['content_hash'],
                    'integrity_digest': source['integrity_digest'], 'version': source['version']},
                'text_basis': 'signed_source_parsed_text', 'fact_verification': 'NOT_VERIFIED', 'truth_kind': 'source_reference'})
            total_bytes += len(source['text'].encode('utf-8'))
        if total_bytes > 64 * 1024 * 1024:
            raise RuntimeError('MEMORY_SEARCH_CAPACITY_EXCEEDED')
        if not page['has_more']:
            break
        position = page['next_offset']
    ranked, report = lexical_search(query, candidates, limit=len(candidates))
    if expected_snapshot is not None and report['source_snapshot_sha256'] != expected_snapshot:
        raise RuntimeError('MEMORY_SEARCH_SNAPSHOT_CHANGED')
    selected = ranked[offset:offset + limit]
    result = []
    for position, candidate in enumerate(selected, offset):
        # Preserve the very original range that established this source's rank.
        # Re-ranking only this document can select a different, weaker passage.
        passage = report['ranked_passages'][position] or original_passage(query, candidate['text'])
        if passage and candidate['text'][passage['start']:passage['end']].strip():
            source = read_source_reference({**candidate['reference'], 'start': passage['start'], 'end': passage['end']},
                actor=actor, scope=scope, connection=connection)
            result.append({**source, 'passage': passage})
    _source_context(actor, scope, connection)
    if snapshot != (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes):
        raise RuntimeError('MEMORY_SEARCH_SNAPSHOT_CHANGED')
    more = offset + limit < len(ranked)
    report['preview_policy'] = 'ranked_original_passage/v1'
    return {'records': result, 'retrieval': report, 'verification_complete': complete,
            'has_more': more, 'next_offset': offset + limit if more else None,
            'offset': offset, 'limit': limit, 'model_execution': 'NOT_RUN'}


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
        self.last_search_report = {'mode': 'NOT_RUN', 'neural_retrieval_performed': False}
        if type(limit) is not int or not 1 <= limit <= 200 or not isinstance(query, str):
            raise ValueError("MEMORY_SEARCH_INVALID")
        if tags is not None and (type(tags) is not list or any(type(tag) is not str for tag in tags)):
            raise ValueError("MEMORY_TAGS_INVALID")
        if not self._available():
            return []
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
            rows = [row for row in rows if (not sub_library or row.get('sub_library') == sub_library)
                    and (not tags or all(tag in (row.get('tags') or []) for tag in tags))]
            from .retrieval import lexical_search
            result, self.last_search_report = lexical_search(query, rows, limit=limit)
            selected_sources = [row for row in result if 'evidence_id' in row
                                or row.get('truth_kind') == 'source_reference']
            if selected_sources:
                from intelligence_library_api import verified_research_source
                from lumenis.shared.reporting.saved_work import (
                    SavedWorkError,
                    authorize_saved_work,
                )
                actor, scope = self._research_actor_scope(conn)
                context = authorize_saved_work(actor, scope, action="read", connection=conn)
                for previous in selected_sources:
                    try:
                        reference = previous.get('evidence_id', previous.get('scope_evidence_ref'))
                        current = verified_research_source(conn, int(reference), actor=actor,
                                                           context=context, facts_only=True)
                        matches = (current == previous if 'evidence_id' in previous else
                            not current['catalog_bound'] and current['source_id'] == previous['source_id']
                            and current['title'] == previous['title'] and current['text'] == previous['content'])
                        if not matches:
                            raise PermissionError("MEMORY_SOURCE_CHANGED")
                    except (SavedWorkError, ValueError, PermissionError) as exc:
                        raise PermissionError("MEMORY_SOURCE_CHANGED") from exc
            self._binding_context(conn)
            if snapshot != (conn.execute("PRAGMA data_version").fetchone()[0], conn.total_changes):
                raise PermissionError("MEMORY_SOURCE_CHANGED")
        finally:
            conn.close()
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
