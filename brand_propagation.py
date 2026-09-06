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
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


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
    heat_score: float = 0.0         # 热度评分 0-100
    mention_count: int = 0          # 提及次数
    engagement_total: int = 0       # 总互动量
    start_time: str = ""
    end_time: str = ""
    summary: str = ""
    key_contents: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class PropagationDashboard:
    """传播事件看板（三类看板统一结构）。"""
    category: str = ""              # brand_event / product_event / industry_event
    title: str = ""
    total_events: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    avg_heat: float = 0.0
    top_events: List[PropagationEvent] = field(default_factory=list)
    platform_distribution: Dict[str, int] = field(default_factory=dict)
    time_range: Dict[str, str] = field(default_factory=dict)
    filters_applied: Dict[str, Any] = field(default_factory=dict)


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
        self.db_path = db_path or os.environ.get(
            "ZBC_DB_PATH",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "monitor.db")
        )
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
                      sentiment: str = "unknown", heat_score: float = 0.0,
                      mention_count: int = 0, engagement_total: int = 0,
                      start_time: str = "", end_time: str = "",
                      summary: str = "") -> PropagationEvent:
        """创建传播事件。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_id = f"event_{int(datetime.now().timestamp())}_{abs(hash(title)) % 10000}"
        event = PropagationEvent(
            event_id=event_id, title=title, category=category,
            entity_type=entity_type, entity_ids=entity_ids or [],
            content_type=content_type, platform=platform, sentiment=sentiment,
            heat_score=heat_score, mention_count=mention_count,
            engagement_total=engagement_total, start_time=start_time,
            end_time=end_time, summary=summary, created_at=now,
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
                      offset: int = 0) -> Tuple[List[PropagationEvent], int]:
        """多维度筛选查询传播事件。

        Returns:
            (events列表, 总数)
        """
        try:
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
            events = []
            for row in cur.fetchall():
                events.append(PropagationEvent(
                    event_id=row["event_id"], title=row["title"], category=row["category"],
                    entity_type=row["entity_type"],
                    entity_ids=json.loads(row["entity_ids"]) if row["entity_ids"] else [],
                    content_type=row["content_type"], platform=row["platform"],
                    sentiment=row["sentiment"], heat_score=row["heat_score"],
                    mention_count=row["mention_count"], engagement_total=row["engagement_total"],
                    start_time=row["start_time"], end_time=row["end_time"],
                    summary=row["summary"],
                    key_contents=json.loads(row["key_contents"]) if row["key_contents"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                ))
            conn.close()
            return events, total
        except Exception as e:
            print(f"[BrandPropagation] 查询事件失败: {e}")
            return [], 0

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

        events, total = self.query_events(
            category=category, platform=platform, sentiment=sentiment,
            start_date=start_date, end_date=end_date, limit=top_n,
        )

        # 统计情感分布
        pos = sum(1 for e in events if e.sentiment == PropagationSentiment.POSITIVE.value)
        neu = sum(1 for e in events if e.sentiment == PropagationSentiment.NEUTRAL.value)
        neg = sum(1 for e in events if e.sentiment == PropagationSentiment.NEGATIVE.value)

        # 平台分布
        platform_dist: Dict[str, int] = {}
        for e in events:
            if e.platform:
                platform_dist[e.platform] = platform_dist.get(e.platform, 0) + 1

        # 平均热度
        avg_heat = sum(e.heat_score for e in events) / len(events) if events else 0.0

        return PropagationDashboard(
            category=category,
            title=category_titles.get(category, f"{category} 看板"),
            total_events=total,
            positive_count=pos,
            neutral_count=neu,
            negative_count=neg,
            avg_heat=round(avg_heat, 2),
            top_events=events,
            platform_distribution=platform_dist,
            time_range={"start": start_date, "end": end_date},
            filters_applied={"platform": platform, "sentiment": sentiment},
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
