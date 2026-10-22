# -*- coding: utf-8 -*-
"""
品牌传播平台 Phase 1（PROJECT_STATUS P1 项 6）
================================================
归属：Z-Brand Core / 品牌传播平台
目标：品牌传播平台 Phase 1 基础结构：主体类型、内容类型、事件关系、三类事件看板与筛选。

Phase 1 范围：
1. 主体类型定义（品牌/产品/人物/机构/事件/话题）
2. 内容类型定义（新闻/社交媒体/论坛/博客/视频/播客）
3. 事件关系模型（传播事件与主体/内容的关联）
4. 三类事件看板：
   - 品牌事件（品牌相关的传播事件）
   - 产品事件（产品相关的传播事件）
   - 行业事件（行业趋势/竞品相关事件）
5. 筛选能力：按时间/平台/情感/热度/主体类型筛选

设计原则：
- 数据模型与现有 notes/events/evidence 表兼容，不重建内容库
- 纯数据层 + API 层，前端页面由 UIUX 组对接
- 不伪造数据，无数据时显式返回空
- 可扩展为 Phase 2/3（六维主体画像、事件图谱、因果溯源）
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from lumenis.shared.database import DatabaseRepository, main_db_path


# ============================================================
# 枚举定义
# ============================================================

class PropagationEntityType(str, Enum):
    """传播主体类型。"""
    BRAND = "brand"           # 品牌
    PRODUCT = "product"       # 产品
    PERSON = "person"         # 人物（KOL/CEO/明星）
    ORGANIZATION = "organization"  # 机构（公司/媒体/协会）
    EVENT = "event"           # 事件（活动/发布会/危机）
    TOPIC = "topic"           # 话题（趋势/热点/争议）


class PropagationContentType(str, Enum):
    """传播内容类型。"""
    NEWS = "news"                 # 新闻
    SOCIAL_MEDIA = "social_media"  # 社交媒体（小红书/微博/抖音）
    FORUM = "forum"               # 论坛（知乎/贴吧）
    BLOG = "blog"                 # 博客/长文
    VIDEO = "video"               # 视频（B站/抖音/视频号）
    PODCAST = "podcast"           # 播客
    OFFICIAL = "official"         # 官方发布（官网/公众号）


class PropagationEventCategory(str, Enum):
    """传播事件分类（三类看板）。"""
    BRAND_EVENT = "brand_event"      # 品牌事件
    PRODUCT_EVENT = "product_event"  # 产品事件
    INDUSTRY_EVENT = "industry_event"  # 行业事件


class PropagationSentiment(str, Enum):
    """传播情感倾向。"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


# ============================================================
# 数据模型
# ============================================================

@dataclass
class PropagationEntity:
    """传播主体。"""
    entity_id: str = ""
    name: str = ""
    entity_type: str = ""           # PropagationEntityType
    description: str = ""
    aliases: List[str] = field(default_factory=list)
    parent_entity_id: str = ""      # 父主体（如产品属于品牌）
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class PropagationEvent:
    """传播事件。"""
    event_id: str = ""
    title: str = ""
    category: str = ""              # PropagationEventCategory
    entity_type: str = ""           # 关联主体类型
    entity_ids: List[str] = field(default_factory=list)  # 关联主体ID列表
    content_type: str = ""          # 主要内容类型
    platform: str = ""              # 主要平台
    sentiment: str = "unknown"      # PropagationSentiment
    heat_score: float | None = None  # 热度评分 0-100
    mention_count: int | None = None # 提及次数
    engagement_total: int | None = None # 总互动量
    start_time: str = ""
    end_time: str = ""
    summary: str = ""
    key_contents: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    metric_basis: str = "UNKNOWN"
    metric_freshness: str = "UNKNOWN"
    metric_completeness: str = "UNKNOWN"
    source_verification: str = "NOT_ESTABLISHED"


@dataclass
class PropagationDashboard:
    """传播事件看板（三类看板统一结构）。"""
    category: str = ""              # brand_event / product_event / industry_event
    title: str = ""
    total_events: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    avg_heat: float | None = None
    top_events: List[PropagationEvent] = field(default_factory=list)
    platform_distribution: Dict[str, int] = field(default_factory=dict)
    time_range: Dict[str, str] = field(default_factory=dict)
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    unknown_sentiment_count: int = 0
    heat_observed_count: int = 0
    heat_unknown_count: int = 0
    metric_freshness: str = "UNKNOWN"
    metric_completeness: str = "UNKNOWN"
    source_verification: str = "NOT_ESTABLISHED"


def _event_metric_observation(metadata: dict[str, Any], name: str, stored_value: Any):
    """Read only values explicitly saved through the current event writer."""
    if not isinstance(metadata, dict):
        return None
    observation = metadata.get('metric_observations')
    if not isinstance(observation, dict) or observation.get('basis') != 'EXPLICIT_CALLER_INPUT':
        return None
    values = observation.get('values')
    if not isinstance(values, dict) or name not in values:
        return None
    value = values[name]
    if name == 'heat_score':
        if type(value) not in (int, float) or not math.isfinite(float(value)) or not 0 <= float(value) <= 100:
            return None
        try:
            return float(value) if float(stored_value) == float(value) else None
        except (TypeError, ValueError):
            return None
    if type(value) is not int or value < 0 or value != stored_value:
        return None
    return value


# ============================================================
# 品牌传播引擎
# ============================================================

class BrandPropagationEngine:
    """品牌传播平台 Phase 1 引擎。

    提供：
    - 主体管理（CRUD）
    - 事件管理（从现有 notes/events 表聚合）
    - 三类看板查询（品牌/产品/行业事件）
    - 多维度筛选（时间/平台/情感/热度/主体类型）
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        return DatabaseRepository(self.db_path).connect()

    def _ensure_tables(self) -> None:
        """确保传播平台表存在（Phase 1 基础表）。"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS brand_propagation_entities (
                    entity_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    aliases TEXT DEFAULT '[]',
                    parent_entity_id TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS brand_propagation_events (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    entity_type TEXT DEFAULT '',
                    entity_ids TEXT DEFAULT '[]',
                    content_type TEXT DEFAULT '',
                    platform TEXT DEFAULT '',
                    sentiment TEXT DEFAULT 'unknown',
                    heat_score REAL DEFAULT 0,
                    mention_count INTEGER DEFAULT 0,
                    engagement_total INTEGER DEFAULT 0,
                    start_time TEXT DEFAULT '',
                    end_time TEXT DEFAULT '',
                    summary TEXT DEFAULT '',
                    key_contents TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT ''
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bpe_category ON brand_propagation_events(category)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bpe_sentiment ON brand_propagation_events(sentiment)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bpe_platform ON brand_propagation_events(platform)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bpe_start_time ON brand_propagation_events(start_time)")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[BrandPropagation] 创建表失败: {e}")

    # ── 主体管理 ──────────────────────────────────────────────

    def create_entity(self, name: str, entity_type: str,
                       description: str = "", aliases: Optional[List[str]] = None,
                       parent_entity_id: str = "",
                       metadata: Optional[Dict] = None) -> PropagationEntity:
        """创建传播主体。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entity_id = f"entity_{int(datetime.now().timestamp())}_{abs(hash(name)) % 10000}"
        entity = PropagationEntity(
            entity_id=entity_id, name=name, entity_type=entity_type,
            description=description, aliases=aliases or [],
            parent_entity_id=parent_entity_id, metadata=metadata or {},
            created_at=now, updated_at=now,
        )
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO brand_propagation_entities
                (entity_id, name, entity_type, description, aliases, parent_entity_id, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entity.entity_id, entity.name, entity.entity_type, entity.description,
                  json.dumps(entity.aliases, ensure_ascii=False), entity.parent_entity_id,
                  json.dumps(entity.metadata, ensure_ascii=False), entity.created_at, entity.updated_at))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[BrandPropagation] 创建主体失败: {e}")
        return entity

    def list_entities(self, entity_type: str = "",
                       parent_id: str = "") -> List[PropagationEntity]:
        """列出传播主体（可按类型/父主体筛选）。"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            query = "SELECT * FROM brand_propagation_entities WHERE 1=1"
            params = []
            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)
            if parent_id:
                query += " AND parent_entity_id = ?"
                params.append(parent_id)
            query += " ORDER BY created_at DESC"
            cur.execute(query, params)
            entities = []
            for row in cur.fetchall():
                entities.append(PropagationEntity(
                    entity_id=row["entity_id"], name=row["name"],
                    entity_type=row["entity_type"], description=row["description"],
                    aliases=json.loads(row["aliases"]) if row["aliases"] else [],
                    parent_entity_id=row["parent_entity_id"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"], updated_at=row["updated_at"],
                ))
            conn.close()
            return entities
        except Exception as e:
            print(f"[BrandPropagation] 列出主体失败: {e}")
            return []

    # ── 事件管理 ──────────────────────────────────────────────

    def create_event(self, title: str, category: str,
                      entity_type: str = "", entity_ids: Optional[List[str]] = None,
                      content_type: str = "", platform: str = "",
                      sentiment: str = "unknown", heat_score: float | None = None,
                      mention_count: int | None = None, engagement_total: int | None = None,
                      start_time: str = "", end_time: str = "",
                      summary: str = "", metadata: dict[str, Any] | None = None) -> PropagationEvent:
        """创建传播事件。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_id = f"event_{int(datetime.now().timestamp())}_{abs(hash(title)) % 10000}"
        metadata_value = dict(metadata or {})
        observed_metrics = {}
        if type(heat_score) in (int, float) and math.isfinite(float(heat_score)) and 0 <= float(heat_score) <= 100:
            observed_metrics['heat_score'] = float(heat_score)
        if type(mention_count) is int and mention_count >= 0:
            observed_metrics['mention_count'] = mention_count
        if type(engagement_total) is int and engagement_total >= 0:
            observed_metrics['engagement_total'] = engagement_total
        if observed_metrics:
            metadata_value['metric_observations'] = {
                'basis': 'EXPLICIT_CALLER_INPUT',
                'values': observed_metrics,
            }
        event = PropagationEvent(
            event_id=event_id, title=title, category=category,
            entity_type=entity_type, entity_ids=entity_ids or [],
            content_type=content_type, platform=platform, sentiment=sentiment,
            heat_score=heat_score, mention_count=mention_count,
            engagement_total=engagement_total, start_time=start_time,
            end_time=end_time, summary=summary, metadata=metadata_value, created_at=now,
        )
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO brand_propagation_events
                (event_id, title, category, entity_type, entity_ids, content_type,
                 platform, sentiment, heat_score, mention_count, engagement_total,
                 start_time, end_time, summary, key_contents, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event.event_id, event.title, event.category, event.entity_type,
                  json.dumps(event.entity_ids, ensure_ascii=False), event.content_type,
                  event.platform, event.sentiment, event.heat_score, event.mention_count,
                  event.engagement_total, event.start_time, event.end_time, event.summary,
                  json.dumps(event.key_contents, ensure_ascii=False),
                  json.dumps(event.metadata, ensure_ascii=False), event.created_at))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[BrandPropagation] 创建事件失败: {e}")
        return event

    def query_events(self, category: str = "", platform: str = "",
                      sentiment: str = "", entity_type: str = "",
                      start_date: str = "", end_date: str = "",
                      min_heat: float = 0.0, limit: int = 50,
                      offset: int = 0, *,
                      _connection: sqlite3.Connection | None = None) -> tuple[list[PropagationEvent], int]:
        """多维度筛选查询传播事件。

        Returns:
            (events列表, 总数)
        """
        owns_connection = _connection is None
        conn = _connection
        try:
            if conn is None:
                conn = self._get_conn()
            cur = conn.cursor()
            query = "SELECT * FROM brand_propagation_events WHERE 1=1"
            count_query = "SELECT COUNT(*) as cnt FROM brand_propagation_events WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                count_query += " AND category = ?"
                params.append(category)
            if platform:
                query += " AND platform = ?"
                count_query += " AND platform = ?"
                params.append(platform)
            if sentiment:
                query += " AND sentiment = ?"
                count_query += " AND sentiment = ?"
                params.append(sentiment)
            if entity_type:
                query += " AND entity_type = ?"
                count_query += " AND entity_type = ?"
                params.append(entity_type)
            if start_date:
                query += " AND start_time >= ?"
                count_query += " AND start_time >= ?"
                params.append(start_date)
            if end_date:
                query += " AND start_time <= ?"
                count_query += " AND start_time <= ?"
                params.append(end_date)
            if min_heat > 0:
                query += " AND heat_score >= ?"
                count_query += " AND heat_score >= ?"
                params.append(min_heat)

            query += " ORDER BY heat_score DESC, created_at DESC LIMIT ? OFFSET ?"
            cur.execute(count_query, params)
            total = cur.fetchone()["cnt"]
            cur.execute(query, params + [limit, offset])
            events: list[PropagationEvent] = []
            for row in cur.fetchall():
                try:
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                except (TypeError, ValueError):
                    metadata = {}
                heat = _event_metric_observation(metadata, 'heat_score', row['heat_score'])
                mentions = _event_metric_observation(metadata, 'mention_count', row['mention_count'])
                engagement = _event_metric_observation(metadata, 'engagement_total', row['engagement_total'])
                observed = any(value is not None for value in (heat, mentions, engagement))
                events.append(PropagationEvent(
                    event_id=row["event_id"], title=row["title"], category=row["category"],
                    entity_type=row["entity_type"],
                    entity_ids=json.loads(row["entity_ids"]) if row["entity_ids"] else [],
                    content_type=row["content_type"], platform=row["platform"],
                    sentiment=row["sentiment"] or "unknown", heat_score=heat,
                    mention_count=mentions, engagement_total=engagement,
                    start_time=row["start_time"], end_time=row["end_time"],
                    summary=row["summary"],
                    key_contents=json.loads(row["key_contents"]) if row["key_contents"] else [],
                    metadata=metadata,
                    created_at=row["created_at"],
                    metric_basis='EXPLICIT_CALLER_INPUT' if observed else 'UNKNOWN',
                    metric_freshness='UNKNOWN', metric_completeness='UNKNOWN',
                    source_verification='NOT_ESTABLISHED',
                ))
            return events, total
        except Exception as e:
            print(f"[BrandPropagation] 查询事件失败: {e}")
            return [], 0
        finally:
            if owns_connection and conn is not None:
                conn.close()

    # ── 三类看板 ──────────────────────────────────────────────

    def get_dashboard(self, category: str,
                      start_date: str = "", end_date: str = "",
                      platform: str = "", sentiment: str = "",
                      top_n: int = 10) -> PropagationDashboard:
        """获取三类事件看板之一（品牌/产品/行业）。

        Args:
            category: brand_event / product_event / industry_event
            start_date/end_date: 时间范围筛选
            platform: 平台筛选
            sentiment: 情感筛选
            top_n: 看板展示的 Top 事件数

        Returns:
            PropagationDashboard 看板数据（无数据时显式返回空，不伪造）
        """
        category_titles = {
            PropagationEventCategory.BRAND_EVENT.value: "品牌事件看板",
            PropagationEventCategory.PRODUCT_EVENT.value: "产品事件看板",
            PropagationEventCategory.INDUSTRY_EVENT.value: "行业事件看板",
        }

        clauses = ['category = ?']
        params: list[Any] = [category]
        if platform:
            clauses.append('platform = ?')
            params.append(platform)
        if sentiment:
            clauses.append('sentiment = ?')
            params.append(sentiment)
        if start_date:
            clauses.append('start_time >= ?')
            params.append(start_date)
        if end_date:
            clauses.append('start_time <= ?')
            params.append(end_date)
        conn = self._get_conn()
        try:
            conn.execute('BEGIN')
            events, _ = self.query_events(
                category=category, platform=platform, sentiment=sentiment,
                start_date=start_date, end_date=end_date, limit=top_n,
                _connection=conn,
            )
            rows = conn.execute(
                'SELECT sentiment,platform,heat_score,mention_count,engagement_total,metadata '
                'FROM brand_propagation_events WHERE ' + ' AND '.join(clauses), params,
            ).fetchall()
        finally:
            if conn.in_transaction:
                conn.rollback()
            conn.close()

        total = len(rows)
        sentiment_counts = {name: 0 for name in ('positive', 'neutral', 'negative', 'unknown')}
        platform_dist: Dict[str, int] = {}
        observed_heat = []
        for row in rows:
            value = row['sentiment'] if row['sentiment'] in sentiment_counts else 'unknown'
            sentiment_counts[value] += 1
            platform_name = row['platform']
            if platform_name:
                platform_dist[platform_name] = platform_dist.get(platform_name, 0) + 1
            try:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
            except (TypeError, ValueError):
                metadata = {}
            heat = _event_metric_observation(metadata, 'heat_score', row['heat_score'])
            if heat is not None:
                observed_heat.append(heat)

        avg_heat = round(sum(observed_heat) / total, 2) if total and len(observed_heat) == total else None

        return PropagationDashboard(
            category=category,
            title=category_titles.get(category, f"{category} 看板"),
            total_events=total,
            positive_count=sentiment_counts['positive'],
            neutral_count=sentiment_counts['neutral'],
            negative_count=sentiment_counts['negative'],
            avg_heat=avg_heat,
            top_events=events,
            platform_distribution=platform_dist,
            time_range={"start": start_date, "end": end_date},
            filters_applied={"platform": platform, "sentiment": sentiment},
            unknown_sentiment_count=sentiment_counts['unknown'],
            heat_observed_count=len(observed_heat),
            heat_unknown_count=max(0, total - len(observed_heat)),
            metric_freshness='UNKNOWN', metric_completeness='UNKNOWN',
            source_verification='NOT_ESTABLISHED',
        )

    def get_all_dashboards(self, start_date: str = "", end_date: str = "",
                            platform: str = "") -> Dict[str, PropagationDashboard]:
        """获取全部三类看板（品牌/产品/行业）。"""
        return {
            "brand_event": self.get_dashboard(
                PropagationEventCategory.BRAND_EVENT.value,
                start_date=start_date, end_date=end_date, platform=platform),
            "product_event": self.get_dashboard(
                PropagationEventCategory.PRODUCT_EVENT.value,
                start_date=start_date, end_date=end_date, platform=platform),
            "industry_event": self.get_dashboard(
                PropagationEventCategory.INDUSTRY_EVENT.value,
                start_date=start_date, end_date=end_date, platform=platform),
        }


# ============================================================
# 便捷函数
# ============================================================

_engine: Optional[BrandPropagationEngine] = None


def get_brand_propagation_engine() -> BrandPropagationEngine:
    """获取品牌传播引擎单例。"""
    global _engine
    if _engine is None:
        _engine = BrandPropagationEngine()
    return _engine


def list_entity_types() -> List[Dict[str, str]]:
    """列出所有主体类型（API 用）。"""
    return [
        {"value": t.value, "label": t.name, "description": _entity_type_desc(t)}
        for t in PropagationEntityType
    ]


def _entity_type_desc(t: PropagationEntityType) -> str:
    descs = {
        PropagationEntityType.BRAND: "品牌主体（如太古汇、LV）",
        PropagationEntityType.PRODUCT: "产品主体（如某款香水、某款手机）",
        PropagationEntityType.PERSON: "人物主体（KOL/CEO/明星）",
        PropagationEntityType.ORGANIZATION: "机构主体（公司/媒体/协会）",
        PropagationEntityType.EVENT: "事件主体（活动/发布会/危机）",
        PropagationEntityType.TOPIC: "话题主体（趋势/热点/争议）",
    }
    return descs.get(t, "")


def list_content_types() -> List[Dict[str, str]]:
    """列出所有内容类型（API 用）。"""
    return [
        {"value": t.value, "label": t.name}
        for t in PropagationContentType
    ]


def list_event_categories() -> List[Dict[str, str]]:
    """列出所有事件分类（三类看板）。"""
    return [
        {"value": c.value, "label": c.name, "dashboard_title": _category_title(c)}
        for c in PropagationEventCategory
    ]


def _category_title(c: PropagationEventCategory) -> str:
    titles = {
        PropagationEventCategory.BRAND_EVENT: "品牌事件看板",
        PropagationEventCategory.PRODUCT_EVENT: "产品事件看板",
        PropagationEventCategory.INDUSTRY_EVENT: "行业事件看板",
    }
    return titles.get(c, c.value)


def read_scoped_propagation(binding):
    """Reuse signed source observations and existing exact-scope curated events.

    Legacy propagation rows have no trustworthy subject binding and are not
    silently assigned to a brand. Curated event count and source observations
    remain distinct; engagement is not relabelled as reach or heat.
    """
    from kos_engine import _read_scoped_canonical_material
    import database
    material = _read_scoped_canonical_material(binding)
    focused = binding["canonical_scope"] == "FOCUS"
    scope = database._normalize_event_scope({"domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": binding.get("brand_focus_id") if focused else None, "global_scope": not focused}, allow_global=True)
    events = database.get_events_curated(100, scope=scope)
    records = material["records"]
    counts = {key: 0 for key in ("positive", "neutral", "negative", "unknown")}
    platforms = {}
    for record in records:
        sentiment = record.get("sentiment")
        counts[sentiment if sentiment in {"positive", "neutral", "negative"} else "unknown"] += 1
        platform = record.get("source_platform") or "UNKNOWN"
        platforms[platform] = platforms.get(platform, 0) + 1
    source_incomplete = (material.get("truncated") is not False
        or type(material.get("rejected_count")) is not int or material.get("rejected_count", 0) != 0)
    event_metadata = events if isinstance(events, dict) else {}
    event_incomplete = event_metadata.get("read_complete") is not True
    return {"events": events,
            "source_count": None if source_incomplete else len(records),
            "observed_source_count": len(records),
            "source_truncated": material.get("truncated"),
            "source_observations": [{"id": row["canonical_id"], "title": row.get("title"),
                "platform": row.get("source_platform"), "scope_evidence": row["scope_evidence"]}
                for row in records],
            "source_read_complete": not source_incomplete,
            "rejected_source_count": material.get("rejected_count", 0),
            "event_read_complete": not event_incomplete,
            "rejected_event_count": event_metadata.get("rejected_count"),
            "event_scanned_count": event_metadata.get("scanned_count"),
            "event_returned_count": event_metadata.get("returned_count"),
            "data_state": "PARTIAL" if source_incomplete or event_incomplete else "READY" if records or event_metadata.get("total") else "EMPTY",
            "observed_sentiment_counts": counts,
            "platform_counts": platforms, "heat": None, "reach": None,
            "source_refs": [{"canonical_id": record["canonical_id"], "scope_evidence": record["scope_evidence"]} for record in records],
            "truncated": bool(material.get("truncated")) or bool(event_metadata.get("truncated")),
            "coverage": "NOT_VERIFIED", "legacy_event_scope": "UNKNOWN_NOT_ASSIGNED",
            "method": "signed-source-observations-and-curated-events:v1"}


# Explicit human business classifications, stored by the existing propagation owner.
# They are not source facts, brand ownership assertions, or inferred popularity.
def prepare_scoped_classification(*, actor, scope, source_event_id, category, request_id):
    import re
    import database
    from lumenis.shared.reporting.saved_work import authorize, _digest
    if (scope.get('domain_id') not in {'bmp', 'zbmp'} or scope.get('global_scope') is not False
            or type(source_event_id) is not int or source_event_id <= 0
            or category not in {x.value for x in PropagationEventCategory}
            or not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', request_id)):
        raise ValueError('PROPAGATION_CLASSIFICATION_INVALID')
    context = authorize(actor, scope, action='write')
    event = database.get_scoped_event(source_event_id, scope)
    if not event:
        raise PermissionError('PROPAGATION_SOURCE_NOT_IN_SCOPE')
    from lumenis.shared.database import get_repository
    classification_id = 'PE-S-' + _digest({'context': context, 'source_event_id': source_event_id})[:32]
    with get_repository().connection(read_only=True, wal=False) as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='brand_propagation_events'").fetchone()
        previous = con.execute('SELECT metadata FROM brand_propagation_events WHERE event_id=?', (classification_id,)).fetchone() if exists else None
    previous_version = _digest(previous[0]) if previous else None
    body = {'schema': 'lumenis.propagation-classification/v1', 'context': context,
            'source_event_id': source_event_id, 'source_evidence_ref': str(event['scope_evidence_ref']),
            'category': category, 'request_id': request_id, 'previous_version': previous_version, 'claim_type': 'human_business_classification'}
    if previous:
        old = json.loads(previous[0])
        if old.get('request_id') == request_id:
            if any(old.get(k) != v for k,v in body.items() if k != 'previous_version'):
                raise ValueError('PROPAGATION_REQUEST_REUSE')
            body['previous_version'] = old.get('previous_version')
    return {'body': body, 'resource': 'propagation-classification:v1:' + _digest(body)}


def write_scoped_classification(*, actor, scope, source_event_id, category, request_id, resource, authorize_current=None):
    import database
    from lumenis.shared.database import get_repository
    from lumenis.shared.reporting.saved_work import authorize, _digest, _check_effect
    from lumenis.system.security.permission import get_permission_gate, OperationType
    prepared = prepare_scoped_classification(actor=actor, scope=scope, source_event_id=source_event_id,
                                             category=category, request_id=request_id)
    if prepared['resource'] != resource:
        raise PermissionError('PROPAGATION_PREVIEW_CHANGED')
    gate = get_permission_gate()
    if gate.get_valid_approval_token('db_write', resource, exact=True) is None:
        raise ValueError('WORK_EFFECT_PERMISSION_DENIED')
    _check_effect(actor, scope, OperationType.DB_WRITE, resource)
    body = prepared['body']; proof = {**body, 'sha256': _digest(body)}
    # Existing table, no global migration and no mutation of source observations.
    with get_repository().transaction() as con:
        if authorize_current is not None and authorize_current() != body['context']:
            raise PermissionError('PROPAGATION_ACTOR_CHANGED')
        context = authorize(actor, scope, action='write', connection=con)
        event = database.get_scoped_event(source_event_id, scope, connection=con)
        if context != body['context'] or not event or str(event['scope_evidence_ref']) != body['source_evidence_ref']:
            raise PermissionError('PROPAGATION_SOURCE_CHANGED')
        con.execute('''CREATE TABLE IF NOT EXISTS brand_propagation_events (
            event_id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
            entity_type TEXT DEFAULT '', entity_ids TEXT DEFAULT '[]', content_type TEXT DEFAULT '',
            platform TEXT DEFAULT '', sentiment TEXT DEFAULT 'unknown', heat_score REAL DEFAULT 0,
            mention_count INTEGER DEFAULT 0, engagement_total INTEGER DEFAULT 0,
            start_time TEXT DEFAULT '', end_time TEXT DEFAULT '', summary TEXT DEFAULT '',
            key_contents TEXT DEFAULT '[]', metadata TEXT DEFAULT '{}', created_at TEXT DEFAULT '')''')
        event_id = 'PE-S-' + _digest({'context': context, 'source_event_id': source_event_id})[:32]
        previous = con.execute('SELECT metadata FROM brand_propagation_events WHERE event_id=?', (event_id,)).fetchone()
        identical = previous and json.loads(previous[0]) == proof
        if not identical and (_digest(previous[0]) if previous else None) != body['previous_version']:
            raise ValueError('PROPAGATION_CONCURRENT_CHANGE')
        con.execute('''INSERT INTO brand_propagation_events(event_id,title,category,metadata)
            VALUES(?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET title=excluded.title,
            category=excluded.category,metadata=excluded.metadata''',
            (event_id, event['title'], category, json.dumps(proof, sort_keys=True)))
        authorize(actor, scope, action='write', connection=con)
        if authorize_current is not None and authorize_current() != body['context']:
            raise PermissionError('PROPAGATION_ACTOR_CHANGED')
        if gate.get_valid_approval_token('db_write', resource, exact=True) is None:
            raise ValueError('WORK_EFFECT_PERMISSION_DENIED')
        _check_effect(actor, scope, OperationType.DB_WRITE, resource)
    return {'ok': True, 'classification_id': event_id, 'category': category,
            'source_event_id': source_event_id, 'claim_type': body['claim_type']}


def read_scoped_classifications(*, actor, scope):
    import database
    from lumenis.shared.database import get_repository
    from lumenis.shared.reporting.saved_work import authorize, _digest
    context = authorize(actor, scope, action='read')
    rows, rejected, seen_events = [], 0, set()
    with get_repository().connection(read_only=True, wal=False) as con:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='brand_propagation_events'").fetchone():
            return {'rows': [], 'rejected': 0, 'state': 'EMPTY'}
        # Filter authorized context before pagination. CASE protects JSON functions
        # from malformed historical metadata; unrelated rows cannot consume a page.
        predicates = ["json_extract(safe_metadata, '$.schema') = ?",
                      "json_type(safe_metadata, '$.context') = 'object'",
                      "(SELECT COUNT(*) FROM json_each(safe_metadata, '$.context')) = ?"]
        params = ['lumenis.propagation-classification/v1', len(context)]
        predicates.append("NOT EXISTS (SELECT 1 FROM json_each(safe_metadata, '$.context') "
                          "WHERE key NOT IN (" + ','.join('?' for _ in context) + "))")
        params.extend(context)
        for key, value in context.items():
            if context['global_scope'] is True and key in {'global_scope', 'brand_focus_id'}:
                continue
            predicates.append("json_extract(safe_metadata, ?) IS ?")
            params.extend(('$.context.' + key, value))
        if context['global_scope'] is True:
            predicates.extend(["json_type(safe_metadata, '$.context.global_scope') = 'false'",
                               "json_type(safe_metadata, '$.context.brand_focus_id') = 'text'",
                               "length(json_extract(safe_metadata, '$.context.brand_focus_id')) > 0",
                               "(SELECT COUNT(*) FROM lumenis_subject_registry AS registry "
                               "WHERE registry.brand_focus_id = json_extract(safe_metadata, '$.context.brand_focus_id') "
                               "AND registry.domain_id = ? AND registry.subject_type = ? "
                               "AND registry.status IN (?,?)) = 1"])
            params.extend(('BMP', 'brand', 'configured', 'active'))
        else:
            predicates.append("json_type(safe_metadata, '$.context.global_scope') = 'false'")
        query = ("WITH safe_rows AS (SELECT event_id,category,metadata, "
                 "CASE WHEN json_valid(metadata) THEN metadata ELSE '{}' END AS safe_metadata "
                 "FROM brand_propagation_events) "
                 "SELECT event_id,category,metadata FROM safe_rows WHERE "
                 + " AND ".join(predicates) + " ORDER BY event_id LIMIT 1001")
        candidates = con.execute(query, params).fetchall()
        truncated = len(candidates) > 1000
        for raw in candidates[:1000]:
            row = dict(raw)
            try:
                proof = json.loads(row['metadata'])
                stored_context = proof.get('context')
                same_context = stored_context == context
                if context['global_scope'] is True and isinstance(stored_context, dict):
                    same_context = (stored_context.get('global_scope') is False and bool(stored_context.get('brand_focus_id'))
                        and {k:v for k,v in stored_context.items() if k not in {'global_scope','brand_focus_id'}}
                        == {k:v for k,v in context.items() if k not in {'global_scope','brand_focus_id'}})
                if proof.get('schema') != 'lumenis.propagation-classification/v1' or not same_context:
                    continue
                expected_id = 'PE-S-' + _digest({'context': stored_context,
                    'source_event_id': proof['source_event_id']})[:32]
                if row['event_id'] != expected_id or type(proof['source_event_id']) is not int:
                    raise ValueError('PROPAGATION_CLASSIFICATION_ID_CHANGED')
                body = {k:v for k,v in proof.items() if k != 'sha256'}
                if proof.get('sha256') != _digest(body) or row['category'] != proof['category']:
                    raise ValueError('PROPAGATION_CLASSIFICATION_CHANGED')
                if proof['category'] not in {x.value for x in PropagationEventCategory}:
                    raise ValueError('PROPAGATION_CATEGORY_INVALID')
                event = database.get_scoped_event(proof['source_event_id'], scope, connection=con)
                if not event or str(event['scope_evidence_ref']) != proof['source_evidence_ref']:
                    raise ValueError('PROPAGATION_SOURCE_CHANGED')
                if proof['source_event_id'] in seen_events:
                    raise ValueError('PROPAGATION_CLASSIFICATION_DUPLICATE')
                seen_events.add(proof['source_event_id'])
                rows.append({'classification_id': row['event_id'], 'category': proof['category'],
                             'event': event, 'claim_type': 'human_business_classification',
                             'source_evidence': event['scope_evidence']})
            except (ValueError, TypeError, KeyError):
                rejected += 1
        authorize(actor, scope, action='read', connection=con)
    return {'rows': rows, 'rejected': rejected, 'truncated': truncated, 'state': 'PARTIAL' if rejected or truncated else 'READY' if rows else 'EMPTY'}


def classification_route_matches():
    from flask import request
    return bool(request.endpoint == 'experience_runtime.propagation_classify'
        and request.url_rule is not None and request.url_rule.rule == '/api/experience/propagation/classify'
        and request.method == 'POST')


def classification_access_allowed():
    from experience_runtime import _shared_work_actor_scope
    from lumenis.system.security.permission import LocalWorkspacePrincipal
    if not classification_route_matches():
        return False
    try:
        actor, scope = _shared_work_actor_scope('write')
        return actor is not None and scope['domain_id'] == 'zbmp' and scope['global_scope'] is False
    except (ValueError, PermissionError):
        return False


def classification_http():
    from flask import request, jsonify
    from experience_runtime import _shared_work_actor_scope, _content_source_same_origin
    from lumenis.system.security.permission import get_permission_gate, PermissionLevel
    try:
        if not classification_route_matches() or not _content_source_same_origin():
            raise PermissionError('PROPAGATION_ROUTE_DENIED')
        actor, scope = _shared_work_actor_scope('write')
        body = request.get_json(silent=True)
        if (not isinstance(body, dict) or set(body) - {'source_event_id','category','request_id','confirm','confirmed_resource'}
                or type(body.get('confirm',False)) is not bool):
            raise ValueError('PROPAGATION_EXACT_REQUEST_REQUIRED')
        args = {key: body.get(key) for key in ('source_event_id','category','request_id')}
        preview = prepare_scoped_classification(actor=actor, scope=scope, **args)
        if body.get('confirm') is not True:
            return jsonify({'ok': True, 'state': 'PREPARED', 'resource': preview['resource'], 'approval_issued': False})
        if body.get('confirmed_resource') != preview['resource']:
            raise PermissionError('PROPAGATION_PREVIEW_CHANGED')
        gate = get_permission_gate()
        if not gate.has_permission(PermissionLevel.HUMAN_APPROVAL) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError('PROPAGATION_MANUAL_AUTHORITY_REQUIRED')
        token = gate.grant_approval('db_write', resource=preview['resource'], duration_minutes=5,
            granted_by=preview['body']['context'].get('principal_ref') or 'actor:'+str(preview['body']['context']['actor_id']))
        def current_identity():
            from lumenis.shared.reporting.saved_work import authorize
            current_actor, current_scope = _shared_work_actor_scope('write')
            return authorize(current_actor, current_scope, action='write')
        try:
            return jsonify(write_scoped_classification(actor=actor, scope=scope, resource=preview['resource'], authorize_current=current_identity, **args))
        except Exception:
            gate.revoke_approval(token)
            raise
    except PermissionError:
        return jsonify({'ok': False, 'code':'PROPAGATION_PERMISSION_DENIED'}),403
    except (ValueError,TypeError):
        return jsonify({'ok': False, 'code':'PROPAGATION_REQUEST_INVALID'}),400
    except Exception:
        return jsonify({'ok': False, 'code':'PROPAGATION_UNAVAILABLE'}),503
