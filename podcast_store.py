# -*- coding: utf-8 -*-
"""
播客情报模块 · 存储层（Podcast Store）
统一实体图模型，对齐 podcast/contracts/podcast-domain-v1.schema.json：
  show/episode/person/transcript/segment/story_node/question/topic/
  content_asset/platform_observation/audience_signal/learning_case/ai_run
设计原则：
  - 复用主库 data/monitor.db，不引入第二数据库引擎
  - 播客数据与品牌舆情事实物理隔离（独立表 + 显式 relations 跨链）
  - 每个实体必须带来源 source + observed_at + evidence_status，缺失指标留 NULL 不填 0
"""
import os
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()

# domain contract 允许的实体类型
ENTITY_TYPES = (
    "show", "episode", "person", "transcript", "segment", "story_node",
    "question", "topic", "content_asset", "platform_observation",
    "audience_signal", "learning_case", "ai_run",
)
EVIDENCE_STATES = ("observed", "derived", "ai_suggested", "human_verified", "unverified")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _get_conn():
    return get_repository().connect(timeout=30)


def init_db():
    """创建播客实体图与 AI 运行记录表（幂等）。"""
    conn = _get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS podcast_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL UNIQUE,
                parent_id TEXT,
                title TEXT,
                start_ms INTEGER,
                end_ms INTEGER,
                speaker_id TEXT,
                attributes_json TEXT DEFAULT '{}',
                relations_json TEXT DEFAULT '[]',
                evidence_ids_json TEXT DEFAULT '[]',
                evidence_status TEXT NOT NULL DEFAULT 'unverified',
                confidence REAL,
                source_json TEXT DEFAULT '{}',
                observed_at TEXT,
                runtime_seconds REAL,
                published_at TEXT,
                metrics_json TEXT DEFAULT '{}',
                tags_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_podcast_entity_type ON podcast_entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_podcast_parent ON podcast_entities(parent_id);
            CREATE INDEX IF NOT EXISTS idx_podcast_evidence ON podcast_entities(evidence_status);

            CREATE TABLE IF NOT EXISTS podcast_ai_runs (
                run_id TEXT PRIMARY KEY,
                entity_id TEXT,
                model TEXT,
                prompt TEXT,
                input_hash TEXT,
                runtime_ms INTEGER,
                status TEXT DEFAULT 'pending',
                output_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_podcast_airun_entity ON podcast_ai_runs(entity_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


def upsert_entity(entity_type, entity_id=None, title=None, parent_id=None,
                  start_ms=None, end_ms=None, speaker_id=None, attributes=None,
                  relations=None, evidence_ids=None, evidence_status="unverified",
                  confidence=None, source=None, observed_at=None, runtime_seconds=None,
                  published_at=None, metrics=None, tags=None):
    """新增或更新一个播客实体。entity_id 缺省自动生成。"""
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"非法实体类型: {entity_type}")
    if evidence_status not in EVIDENCE_STATES:
        raise ValueError(f"非法证据状态: {evidence_status}")
    init_db()
    eid = entity_id or f"{entity_type}_{uuid.uuid4().hex[:12]}"
    now = _now()
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO podcast_entities
              (entity_type, entity_id, parent_id, title, start_ms, end_ms, speaker_id,
               attributes_json, relations_json, evidence_ids_json, evidence_status,
               confidence, source_json, observed_at, runtime_seconds, published_at,
               metrics_json, tags_json, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(entity_id) DO UPDATE SET
               parent_id=excluded.parent_id, title=excluded.title,
               start_ms=excluded.start_ms, end_ms=excluded.end_ms, speaker_id=excluded.speaker_id,
               attributes_json=excluded.attributes_json, relations_json=excluded.relations_json,
               evidence_ids_json=excluded.evidence_ids_json, evidence_status=excluded.evidence_status,
               confidence=excluded.confidence, source_json=excluded.source_json,
               observed_at=excluded.observed_at, runtime_seconds=excluded.runtime_seconds,
               published_at=excluded.published_at, metrics_json=excluded.metrics_json,
               tags_json=excluded.tags_json, updated_at=excluded.updated_at
            """,
            (entity_type, eid, parent_id, title, start_ms, end_ms, speaker_id,
             json.dumps(attributes or {}, ensure_ascii=False),
             json.dumps(relations or [], ensure_ascii=False),
             json.dumps(evidence_ids or [], ensure_ascii=False),
             evidence_status, confidence,
             json.dumps(source or {}, ensure_ascii=False),
             # Write time is not source observation time. Preserve an unknown
             # observation as SQL NULL; created_at/updated_at keep write time.
             observed_at or None, runtime_seconds, published_at,
             json.dumps(metrics or {}, ensure_ascii=False),
             json.dumps(tags or [], ensure_ascii=False), now, now),
        )
        conn.commit()
        return eid
    finally:
        conn.close()


def list_entities(entity_type=None, parent_id=None, evidence_status=None, limit=100, offset=0):
    """按条件列出实体。"""
    init_db()
    where, params = [], []
    if entity_type:
        where.append("entity_type=?"); params.append(entity_type)
    if parent_id is not None:
        where.append("parent_id=?"); params.append(parent_id)
    if evidence_status:
        where.append("evidence_status=?"); params.append(evidence_status)
    sql = "SELECT * FROM podcast_entities"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    conn = _get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_safe_row(r) for r in rows]
    finally:
        conn.close()


def _safe_row(r):
    d = dict(r)
    for jk, dk in (("attributes_json","attributes"),("relations_json","relations"),
                   ("evidence_ids_json","evidence_ids"),("source_json","source"),
                   ("metrics_json","metrics"),("tags_json","tags")):
        raw = d.pop(jk, None)
        try:
            d[dk] = json.loads(raw) if raw else ([] if dk in ("relations","evidence_ids","tags") else {})
        except Exception:
            d[dk] = [] if dk in ("relations","evidence_ids","tags") else {}
    return d


def get_entity(entity_id):
    init_db()
    conn = _get_conn()
    try:
        r = conn.execute("SELECT * FROM podcast_entities WHERE entity_id=?", (entity_id,)).fetchone()
        return _safe_row(r) if r else None
    finally:
        conn.close()


def get_stats():
    """实体图统计：按类型/证据状态计数。"""
    init_db()
    conn = _get_conn()
    try:
        by_type = {r["entity_type"]: r["c"] for r in conn.execute(
            "SELECT entity_type, COUNT(*) c FROM podcast_entities GROUP BY entity_type")}
        by_evidence = {r["evidence_status"]: r["c"] for r in conn.execute(
            "SELECT evidence_status, COUNT(*) c FROM podcast_entities GROUP BY evidence_status")}
        total = conn.execute("SELECT COUNT(*) c FROM podcast_entities").fetchone()["c"]
        return {"total": total, "by_type": by_type, "by_evidence": by_evidence}
    finally:
        conn.close()


def record_ai_run(run_id=None, entity_id=None, model=None, prompt=None, input_hash=None,
                  runtime_ms=None, status="pending", output=None, error=None):
    """记录一次 AI 运行（模型/输入哈希/运行时/状态可追溯）。"""
    init_db()
    rid = run_id or f"airun_{uuid.uuid4().hex[:12]}"
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO podcast_ai_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rid, entity_id, model, prompt, input_hash, runtime_ms, status,
             json.dumps(output or {}, ensure_ascii=False), error, _now()),
        )
        conn.commit()
        return rid
    finally:
        conn.close()
