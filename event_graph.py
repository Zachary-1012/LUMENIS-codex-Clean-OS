"""
事件关系图谱（V3.0 P1.3 事件关系体系）
归属：Z-Brand Core / ZBMP / 品牌智能层

v5.9.9 修复：从纯内存实现改为数据库持久化
- 添加 event_graph_events 和 event_graph_relations 表
- 启动时从数据库加载，进程重启数据不丢失
- 可关联现有 events 表（source_event_id 字段）
- 添加写入 API（创建事件、添加关系）

目标：
  1. 建立营销事件、传播事件、舆情事件的统一事件模型
  2. 实现事件间的关系图谱：触发、衍生、继发、并行
  3. 为品牌传播分析提供事件维度的数据基础

事件类型定义：
  - marketing_event（营销事件）：品牌主动发起的营销活动
  - propagation_event（传播事件）：内容在社交媒体上的传播过程
  - public_opinion_event（舆情事件）：引发公众讨论的舆情事件

关系类型定义：
  - trigger（触发）：A事件直接导致B事件的发生
  - derive（衍生）：B事件是A事件的衍生或分支
  - follow（继发）：B事件在A事件之后发生，时间先后关系
  - parallel（并行）：A和B事件同时发生，相互影响但无直接因果
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# 事件类型定义
EVENT_TYPES = {
    'marketing_event': '营销事件',
    'propagation_event': '传播事件',
    'public_opinion_event': '舆情事件',
}

# 关系类型定义
RELATION_TYPES = {
    'trigger': '触发',
    'derive': '衍生',
    'follow': '继发',
    'parallel': '并行',
}

# 事件状态定义
EVENT_STATUS = {
    'ongoing': '进行中',
    'completed': '已完成',
    'cooling': '冷却中',
    'archived': '已归档',
}

# 数据库路径
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')


def _get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def init_db() -> None:
    """初始化数据库表"""
    with _get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS event_graph_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                event_time TEXT,
                source TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'ongoing',
                metadata TEXT DEFAULT '{}',
                source_event_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_event_graph_events_type ON event_graph_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_event_graph_events_status ON event_graph_events(status);
            CREATE INDEX IF NOT EXISTS idx_event_graph_events_source ON event_graph_events(source_event_id);

            CREATE TABLE IF NOT EXISTS event_graph_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_event_id TEXT NOT NULL,
                target_event_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                evidence TEXT DEFAULT '',
                confidence REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                UNIQUE(source_event_id, target_event_id, relation_type)
            );
            CREATE INDEX IF NOT EXISTS idx_event_graph_relations_source ON event_graph_relations(source_event_id);
            CREATE INDEX IF NOT EXISTS idx_event_graph_relations_target ON event_graph_relations(target_event_id);
            CREATE INDEX IF NOT EXISTS idx_event_graph_relations_type ON event_graph_relations(relation_type);
        """)
        conn.commit()


class BrandEvent:
    """品牌事件基类"""

    def __init__(self, event_type: str, title: str, event_time: str = None,
                 source: str = '', description: str = '', status: str = 'ongoing',
                 metadata: Dict[str, Any] = None, event_id: str = None,
                 source_event_id: int = None, created_at: str = None, updated_at: str = None):
        self.event_id = event_id or str(uuid.uuid4())[:8]
        self.event_type = event_type
        self.event_type_name = EVENT_TYPES.get(event_type, event_type)
        self.title = title
        self.event_time = event_time or _now()
        self.source = source
        self.description = description
        self.status = status
        self.status_name = EVENT_STATUS.get(status, status)
        self.metadata = metadata or {}
        self.source_event_id = source_event_id  # 关联现有events表的id
        self.created_at = created_at or _now()
        self.updated_at = updated_at or _now()
        self.relations: List[EventRelation] = []

    def add_relation(self, target_event: 'BrandEvent', relation_type: str,
                     evidence: str = '', confidence: float = 0.5) -> 'EventRelation':
        """添加与目标事件的关系"""
        relation = EventRelation(
            source_event=self,
            target_event=target_event,
            relation_type=relation_type,
            evidence=evidence,
            confidence=confidence,
        )
        self.relations.append(relation)
        return relation

    def get_related_events(self, relation_type: str = None) -> List['BrandEvent']:
        """获取相关事件"""
        results = []
        for rel in self.relations:
            if relation_type is None or rel.relation_type == relation_type:
                results.append(rel.target_event)
        return results

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'event_type_name': self.event_type_name,
            'title': self.title,
            'event_time': self.event_time,
            'source': self.source,
            'description': self.description,
            'status': self.status,
            'status_name': self.status_name,
            'metadata': self.metadata,
            'source_event_id': self.source_event_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'relations': [rel.to_dict() for rel in self.relations],
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'BrandEvent':
        """从数据库行创建"""
        try:
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return cls(
            event_type=row['event_type'],
            title=row['title'],
            event_time=row['event_time'],
            source=row['source'] or '',
            description=row['description'] or '',
            status=row['status'] or 'ongoing',
            metadata=metadata,
            event_id=row['event_id'],
            source_event_id=row['source_event_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def save_to_db(self, conn: sqlite3.Connection = None) -> None:
        """保存到数据库（插入或更新）"""
        close_conn = False
        if conn is None:
            conn = _get_db()
            close_conn = True
        try:
            now = _now()
            conn.execute("""
                INSERT INTO event_graph_events
                (event_id, event_type, title, event_time, source, description, status, metadata, source_event_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    event_type=excluded.event_type,
                    title=excluded.title,
                    event_time=excluded.event_time,
                    source=excluded.source,
                    description=excluded.description,
                    status=excluded.status,
                    metadata=excluded.metadata,
                    source_event_id=excluded.source_event_id,
                    updated_at=excluded.updated_at
            """, (
                self.event_id, self.event_type, self.title, self.event_time,
                self.source, self.description, self.status,
                json.dumps(self.metadata, ensure_ascii=False),
                self.source_event_id, self.created_at, now
            ))
            self.updated_at = now
            conn.commit()
        finally:
            if close_conn:
                conn.close()


class EventRelation:
    """事件关系"""

    def __init__(self, source_event: BrandEvent, target_event: BrandEvent,
                 relation_type: str, evidence: str = '', confidence: float = 0.5,
                 created_at: str = None):
        self.source_event = source_event
        self.target_event = target_event
        self.relation_type = relation_type
        self.relation_type_name = RELATION_TYPES.get(relation_type, relation_type)
        self.evidence = evidence
        self.confidence = confidence
        self.created_at = created_at or _now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_event_id': self.source_event.event_id,
            'source_event_title': self.source_event.title,
            'target_event_id': self.target_event.event_id,
            'target_event_title': self.target_event.title,
            'relation_type': self.relation_type,
            'relation_type_name': self.relation_type_name,
            'evidence': self.evidence,
            'confidence': self.confidence,
            'created_at': self.created_at,
        }

    def save_to_db(self, conn: sqlite3.Connection = None) -> None:
        """保存到数据库"""
        close_conn = False
        if conn is None:
            conn = _get_db()
            close_conn = True
        try:
            conn.execute("""
                INSERT OR IGNORE INTO event_graph_relations
                (source_event_id, target_event_id, relation_type, evidence, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.source_event.event_id, self.target_event.event_id,
                self.relation_type, self.evidence, self.confidence, self.created_at
            ))
            conn.commit()
        finally:
            if close_conn:
                conn.close()


class EventGraph:
    """事件关系图谱（数据库持久化版）"""

    def __init__(self, auto_load: bool = True):
        self.events: Dict[str, BrandEvent] = {}
        self.relations: List[EventRelation] = []
        init_db()
        if auto_load:
            self.load_from_db()

    def load_from_db(self) -> None:
        """从数据库加载所有事件和关系"""
        self.events.clear()
        self.relations.clear()

        with _get_db() as conn:
            # 加载事件
            rows = conn.execute("SELECT * FROM event_graph_events ORDER BY id").fetchall()
            for row in rows:
                event = BrandEvent.from_row(row)
                self.events[event.event_id] = event

            # 加载关系
            rel_rows = conn.execute("SELECT * FROM event_graph_relations ORDER BY id").fetchall()
            for rrow in rel_rows:
                source = self.events.get(rrow['source_event_id'])
                target = self.events.get(rrow['target_event_id'])
                if source and target:
                    relation = EventRelation(
                        source_event=source,
                        target_event=target,
                        relation_type=rrow['relation_type'],
                        evidence=rrow['evidence'] or '',
                        confidence=rrow['confidence'] or 0.5,
                        created_at=rrow['created_at'],
                    )
                    source.relations.append(relation)
                    self.relations.append(relation)

    def add_event(self, event: BrandEvent, persist: bool = True) -> BrandEvent:
        """添加事件"""
        self.events[event.event_id] = event
        if persist:
            event.save_to_db()
        return event

    def create_event(self, event_type: str, title: str, description: str = '',
                     event_time: str = None, source: str = '', status: str = 'ongoing',
                     metadata: Dict[str, Any] = None, source_event_id: int = None) -> BrandEvent:
        """创建并保存新事件"""
        event = BrandEvent(
            event_type=event_type,
            title=title,
            description=description,
            event_time=event_time,
            source=source,
            status=status,
            metadata=metadata,
            source_event_id=source_event_id,
        )
        return self.add_event(event)

    def get_event(self, event_id: str) -> Optional[BrandEvent]:
        """获取事件"""
        return self.events.get(event_id)

    def add_relation(self, source_id: str, target_id: str, relation_type: str,
                     evidence: str = '', confidence: float = 0.5, persist: bool = True) -> Optional[EventRelation]:
        """添加事件关系"""
        source = self.get_event(source_id)
        target = self.get_event(target_id)
        if not source or not target:
            return None
        relation = source.add_relation(target, relation_type, evidence, confidence)
        self.relations.append(relation)
        if persist:
            relation.save_to_db()
        return relation

    def get_events_by_type(self, event_type: str) -> List[BrandEvent]:
        """按类型获取事件"""
        return [e for e in self.events.values() if e.event_type == event_type]

    def get_event_chain(self, event_id: str, max_depth: int = 5) -> List[BrandEvent]:
        """获取事件链（从指定事件出发的所有关联事件）"""
        visited = set()
        chain = []
        queue = [(event_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            event = self.get_event(current_id)
            if event:
                chain.append(event)
                for rel in event.relations:
                    if rel.target_event.event_id not in visited:
                        queue.append((rel.target_event.event_id, depth + 1))

        return chain

    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计"""
        type_counts = {}
        for event in self.events.values():
            type_name = EVENT_TYPES.get(event.event_type, event.event_type)
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        relation_counts = {}
        for rel in self.relations:
            rel_name = RELATION_TYPES.get(rel.relation_type, rel.relation_type)
            relation_counts[rel_name] = relation_counts.get(rel_name, 0) + 1

        return {
            'total_events': len(self.events),
            'total_relations': len(self.relations),
            'events_by_type': type_counts,
            'relations_by_type': relation_counts,
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'events': [e.to_dict() for e in self.events.values()],
            'relations': [r.to_dict() for r in self.relations],
            'stats': self.get_stats(),
        }

    def export_json(self, filepath: str) -> bool:
        """导出为JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def import_from_existing_events(self, limit: int = 20) -> int:
        """从现有 events 表导入示例数据

        根据 risk_level 判断事件类型：
        - high/medium 风险且 negative_confirmed=1 → 舆情事件 (public_opinion_event)
        - 其他 → 传播事件 (propagation_event)

        只导入最近的 N 条，返回导入数量
        """
        with _get_db() as conn:
            try:
                rows = conn.execute("""
                    SELECT id, title, summary, event_date, first_seen, last_seen,
                           risk_level, risk_score, negative_confirmed, status,
                           mention_count, source_count, fact_status
                    FROM events
                    WHERE title IS NOT NULL AND title != ''
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,)).fetchall()
            except Exception as e:
                print(f'[EventGraph] 从events表导入失败: {e}')
                return 0

            imported = 0
            for row in rows:
                # 检查是否已导入（通过 source_event_id）
                existing = conn.execute(
                    "SELECT event_id FROM event_graph_events WHERE source_event_id=?",
                    (row['id'],)
                ).fetchone()
                if existing:
                    continue

                title = (row['title'] or '未命名事件')[:200]
                summary = (row['summary'] or '')[:500]
                event_time = row['event_date'] or row['first_seen'] or row['last_seen'] or _now()

                # 根据风险等级判断事件类型
                is_negative = row['negative_confirmed'] == 1
                risk_level = (row['risk_level'] or '').lower()
                if is_negative or risk_level in ('high', 'medium'):
                    event_type = 'public_opinion_event'
                else:
                    event_type = 'propagation_event'

                # 状态映射
                status_map = {'active': 'ongoing', 'resolved': 'completed', 'closed': 'archived'}
                status = status_map.get((row['status'] or '').lower(), 'ongoing')

                event = BrandEvent(
                    event_type=event_type,
                    title=title,
                    description=summary,
                    event_time=event_time,
                    source='imported_from_events',
                    status=status,
                    metadata={
                        'imported': True,
                        'original_event_id': row['id'],
                        'risk_level': row['risk_level'],
                        'mention_count': row['mention_count'],
                        'source_count': row['source_count'],
                        'fact_status': row['fact_status'],
                    },
                    source_event_id=row['id'],
                )
                event.save_to_db(conn)
                self.events[event.event_id] = event
                imported += 1

            conn.commit()
            return imported

    @staticmethod
    def get_all_event_types() -> Dict[str, str]:
        """获取所有事件类型"""
        return EVENT_TYPES.copy()

    @staticmethod
    def get_all_relation_types() -> Dict[str, str]:
        """获取所有关系类型"""
        return RELATION_TYPES.copy()


# 全局单例
_graph_instance: Optional[EventGraph] = None

def get_event_graph() -> EventGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = EventGraph(auto_load=True)
    return _graph_instance


def reset_event_graph() -> None:
    """重置全局单例（用于测试或强制重新加载）"""
    global _graph_instance
    _graph_instance = None
