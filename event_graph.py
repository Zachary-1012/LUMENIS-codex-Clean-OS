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
from lumenis.shared.database import get_repository, main_db_path
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
_DB_PATH = main_db_path()


def _get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    return get_repository().connect()


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ===== GAP-07 关系推断：保守、可解释、无证据不连边 =====
AUTO_REL_PREFIX = '[auto]'
# 全域高频通用 bigram（所有事件几乎都含，会造成“全相连”伪关系），不计入主题重叠
_STOP_BIGRAM = {'太古', '古汇', '广州', '商场', '活动', '事件', '品牌', '门店', '顾客', '消费',
                '购物', '中心', '广场', '有限', '公司', '我们', '他们', '这个', '一个', '可以',
                # 自动摘要/免责样板套话（description 常见，防止模板化全相连）
                '相关', '讨论', '事实', '仅能', '仍需', '关提', '关讨', '需要', '以及', '关的',
                '仅供', '参考', '不构', '建议', '信息', '来源', '网络', '整理', '编辑'}


_DROP_PHRASES = ['广州太古汇', '太古汇', '太古', '广州']  # 先整体剔除全域通用名，避免跨界 bigram 噪声


def _text_tokens(text: str) -> set:
    """先整体剔除全域通用短语，再做中文 2-gram（去停用）+ 英文/数字词，作为主题重叠证据。"""
    import re as _re
    s = str(text or '').lower()
    for _ph in _DROP_PHRASES:
        s = s.replace(_ph, ' ')
    toks = set()
    for seg in _re.findall(r'[一-龥]{2,}', s):
        for i in range(len(seg) - 1):
            g = seg[i:i + 2]
            if g not in _STOP_BIGRAM:
                toks.add(g)
    for w in _re.findall(r'[a-z0-9]{2,}', s):
        toks.add(w)
    return toks


def _parse_dt(value: str):
    """宽松解析事件时间为 datetime；无法判定返回 None（时间不可比则不自动连边，保守）。"""
    s = str(value or '').strip().replace('T', ' ')
    if not s:
        return None
    try:
        if len(s) >= 19:
            return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
        if len(s) >= 16:
            return datetime.strptime(s[:16], '%Y-%m-%d %H:%M')
        return datetime.strptime(s[:10], '%Y-%m-%d')
    except Exception:
        return None


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
                if is_negative or risk_level in ('critical', 'high', 'medium'):
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

    def infer_and_link_relations(self, days_window: int = 21, parallel_hours: float = 36,
                                 min_follow_overlap: int = 1, min_derive_overlap: int = 3,
                                 persist: bool = True, drop_auto_first: bool = True) -> Dict[str, Any]:
        """GAP-07：基于【时间 + 主题词】双证据保守推断 follow/derive/parallel。
        - 无主题重叠或时间不可比 -> 不连边（绝不伪造关系）；
        - trigger 属强因果，不在此自动生成，保留人工/直接证据；
        - 自动关系 evidence 以 [auto] 开头，重算只清理自动关系，手工关系保留；
        - 幂等：(source,target,type) UNIQUE + INSERT OR IGNORE。
        """
        dropped = 0
        if drop_auto_first:
            before = len(self.relations)
            self.relations = [r for r in self.relations
                              if not str(r.evidence or '').startswith(AUTO_REL_PREFIX)]
            dropped = before - len(self.relations)
            if persist:
                with _get_db() as conn:
                    cur = conn.execute(
                        "DELETE FROM event_graph_relations WHERE evidence LIKE ?",
                        (AUTO_REL_PREFIX + '%',))
                    dropped = max(dropped, cur.rowcount or 0)
                    conn.commit()

        items = []
        for e in self.events.values():
            dt = _parse_dt(e.event_time)
            if dt is not None:
                items.append((dt, e))
        items.sort(key=lambda x: x[0])

        by_type = {'follow': 0, 'derive': 0, 'parallel': 0}
        added = 0
        no_evidence = 0
        existing = {(r.source_event.event_id, r.target_event.event_id, r.relation_type)
                    for r in self.relations}
        for i in range(len(items)):
            dt_a, a = items[i]
            ta = _text_tokens(a.title)
            if not ta:
                continue
            for j in range(i + 1, len(items)):
                dt_b, b = items[j]
                shared = sorted(ta & _text_tokens(b.title))
                if not shared:
                    no_evidence += 1
                    continue
                gap_h = (dt_b - dt_a).total_seconds() / 3600.0
                rtype, conf = None, 0.5
                if abs(gap_h) <= parallel_hours:
                    rtype, conf = 'parallel', 0.55
                elif 0 < gap_h <= days_window * 24:
                    if len(shared) >= min_derive_overlap:
                        rtype, conf = 'derive', 0.7
                    elif len(shared) >= min_follow_overlap:
                        rtype, conf = 'follow', 0.5
                if not rtype:
                    no_evidence += 1
                    continue
                key = (a.event_id, b.event_id, rtype)
                if key in existing:
                    continue
                ev = (f"{AUTO_REL_PREFIX} 时间差{gap_h / 24:.1f}天/"
                      f"共享主题词:{','.join(shared[:5])}/规则{rtype}")
                rel = self.add_relation(a.event_id, b.event_id, rtype,
                                        evidence=ev, confidence=conf, persist=persist)
                if rel is not None:
                    existing.add(key)
                    added += 1
                    by_type[rtype] += 1
        return {'dropped_auto': dropped, 'added': added,
                'by_type': by_type, 'no_evidence_pairs': no_evidence}


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


def infer_and_persist_relations(**kwargs) -> Dict[str, Any]:
    """便捷入口：对全局图谱执行一次保守关系推断并持久化。

    【生产状态文档（2026-09-06）】

    复杂度：
        当前实现为 O(n^2) 全量扫描——对 events 表中所有事件两两计算相似度
        并推断关系。事件量较大时（>数千条）单次运行可能耗时数十秒至分钟级，
        且随事件量呈平方增长。未来优化方向：分块/索引/增量计算（仅对新增
        或变更事件做配对），但需先做性能压测再切换。

    调度状态：
        未接入自动调度。当前不会在采集后、日报生成时或定时任务中自动触发，
        必须由运维手动调用。

    手动触发方式：
        POST /api/event-graph/rebuild-relations
        （见 app.py 中 event_graph_rebuild_relations 路由）

    未来接入自动调度的前置要求：
        1. try/except 隔离：关系推断失败不得影响采集、风险判断、日报等主链路；
        2. 限频（rate-limit）：同一时间窗口内只允许一次全量重建，避免重复
           O(n^2) 扫描叠加导致 CPU/IO 耗尽；
        3. 性能压测：在接近生产数据量的 events 表上实测单次耗时与资源占用，
           确认在可接受窗口内完成后再接入定时调度；
        4. 状态可见：运行中/完成/失败状态应在系统内可见，不得静默失败。
    """
    return get_event_graph().infer_and_link_relations(**kwargs)


# Scoped HTTP owner. Existing tables remain the sole event graph store; old rows
# lacking this versioned server binding retain UNKNOWN ownership.
def _graph_identity(actor, scope, action='read', connection=None):
    from lumenis.shared.reporting.saved_work import authorize
    return authorize(actor, scope, action=action, connection=connection)


def _graph_hash(value):
    from lumenis.shared.reporting.saved_work import _digest
    return _digest(value)


def read_scoped_graph(*, actor, scope, connection=None):
    import contextlib
    context = _graph_identity(actor, scope)
    manager = contextlib.nullcontext(connection) if connection is not None else get_repository().connection(read_only=True, wal=False)
    with manager as con:
        if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='event_graph_events'").fetchone() is None:
            return {'events': [], 'relations': [], 'rejected': 0, 'legacy_scope': 'UNKNOWN'}
        events, rejected = {}, 0
        for raw in con.execute('SELECT * FROM event_graph_events ORDER BY id'):
            row = dict(raw)
            try:
                meta = json.loads(row['metadata'])
                if meta.get('schema') != 'lumenis.scoped-event-graph/v1' or meta.get('context') != context:
                    continue
                content = {key: row[key] for key in ('event_id','event_type','title','event_time','source','description','status','source_event_id')}
                if meta.get('sha256') != _graph_hash({'content':content,'context':context,'request_id':meta['request_id'],'origin':meta['origin']}):
                    raise ValueError('GRAPH_EVENT_INTEGRITY_FAILED')
                if meta['origin']['kind'] == 'verified_scoped_source':
                    import database
                    source = database.get_scoped_event(row['source_event_id'], scope, connection=con)
                    if not source or source.get('scope_evidence_ref') != meta['origin'].get('scope_evidence_ref'):
                        raise ValueError('GRAPH_SOURCE_CHANGED')
                row['metadata'] = meta
                row['evidence_state'] = meta['origin']['kind']
                events[row['event_id']] = row
            except (ValueError, TypeError, KeyError, LookupError):
                rejected += 1
        relations = []
        for raw in con.execute('SELECT * FROM event_graph_relations ORDER BY id'):
            row = dict(raw)
            if row['source_event_id'] not in events or row['target_event_id'] not in events:
                continue
            try:
                proof = json.loads(row['evidence'])
                if proof.get('schema') != 'lumenis.scoped-event-relation/v1' or proof.get('context') != context:
                    continue
                material = {key:value for key,value in proof.items() if key != 'sha256'}
                if proof.get('sha256') != _graph_hash(material):
                    raise ValueError('GRAPH_RELATION_INTEGRITY_FAILED')
                if (proof['source_sha256'] != events[row['source_event_id']]['metadata']['sha256']
                        or proof['target_sha256'] != events[row['target_event_id']]['metadata']['sha256']
                        or proof['relation_type'] != row['relation_type']):
                    raise ValueError('GRAPH_RELATION_SOURCE_CHANGED')
                row['evidence'] = proof
                relations.append(row)
            except (ValueError,TypeError,KeyError):
                rejected += 1
        _graph_identity(actor,scope,connection=con)
    return {'events':list(events.values()),'relations':relations,'rejected':rejected,'legacy_scope':'UNKNOWN'}


def _graph_inference_options(payload):
    """Preserve main HTTP int()/float() inputs, excluding bool/nonfinite data.

    These are inference windows, not authority or a new retention boundary.
    Keep raw payload in the approval hash; normalization only drives the rule.
    """
    import math
    days=payload.get('days_window',21)
    parallel=payload.get('parallel_hours',36)
    try:
        if type(days) not in (str,int,float) or type(parallel) not in (str,int,float):
            raise ValueError('GRAPH_WINDOW_INVALID')
        if isinstance(days,float) and not math.isfinite(days):
            raise ValueError('GRAPH_WINDOW_INVALID')
        days=int(days)
        parallel=float(parallel)
        if not math.isfinite(parallel):
            raise ValueError('GRAPH_PARALLEL_WINDOW_INVALID')
    except (ValueError,TypeError,OverflowError) as exc:
        raise ValueError('GRAPH_WINDOW_INVALID') from exc
    return {'days_window':days,'parallel_hours':parallel}


def prepare_scoped_graph_command(command, payload, *, actor, scope, request_id):
    import re
    from lumenis.shared.reporting.saved_work import _safe_payload
    if (command not in {'create','relation','import','infer'} or not isinstance(payload,dict)
            or not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',request_id)):
        raise ValueError('GRAPH_COMMAND_INVALID')
    _safe_payload(payload)
    fields = {'create':{'event_type','title','description','event_time','status'},
              'relation':{'source_event_id','target_event_id','relation_type','evidence'},
              'import':{'source_event_ids'},'infer':{'days_window','parallel_hours'}}
    if set(payload)-fields[command]:
        raise ValueError('GRAPH_FIELDS_INVALID')
    context=_graph_identity(actor,scope,'write')
    current=read_scoped_graph(actor=actor,scope=scope)
    if command=='create':
        if payload.get('event_type') not in EVENT_TYPES or payload.get('status','ongoing') not in EVENT_STATUS:
            raise ValueError('GRAPH_EVENT_CLASS_INVALID')
        if not isinstance(payload.get('title'),str) or not payload['title'].strip() or len(payload['title'])>500:
            raise ValueError('GRAPH_TITLE_INVALID')
        for key in ('description','event_time'):
            if key in payload and (not isinstance(payload[key],str) or len(payload[key])>10000):
                raise ValueError('GRAPH_TEXT_INVALID')
    if command=='relation':
        ids={row['event_id'] for row in current['events']}
        if (payload.get('source_event_id') not in ids or payload.get('target_event_id') not in ids
                or payload['source_event_id']==payload['target_event_id'] or payload.get('relation_type') not in RELATION_TYPES):
            raise ValueError('GRAPH_RELATION_ENDPOINT_INVALID')
        if not isinstance(payload.get('evidence',''),str) or len(payload.get('evidence',''))>10000:
            raise ValueError('GRAPH_RELATION_EVIDENCE_INVALID')
    imported=[]
    if command=='import':
        import database
        ids=payload.get('source_event_ids')
        if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(type(i) is not int or i<=0 for i in ids) or len(set(ids))!=len(ids):
            raise ValueError('GRAPH_SOURCE_IDS_INVALID')
        for source_id in ids:
            source=database.get_scoped_event(source_id,scope)
            if not source:
                raise PermissionError('GRAPH_SOURCE_NOT_IN_SCOPE')
            imported.append(source)
    inference_options=_graph_inference_options(payload) if command=='infer' else None
    # Existing nodes and sources are pinned, so a preview cannot authorize a
    # different graph after concurrent edits or source revocation.
    pins=([{'event_id':r['event_id'],'sha256':r['metadata']['sha256']} for r in current['events']]
          if command in {'relation','infer'} else [])
    # Rebuild also mutates automatic edges: bind the reviewed relation set,
    # not just node hashes, to exact confirmation. Never authorize global cleanup.
    relation_pins=([{'id':r['id'],'sha256':r['evidence']['sha256']} for r in current['relations']]
                   if command=='infer' else [])
    material={'context':context,'command':command,'payload':payload,
        'request_id':request_id,'pins':pins,'sources':imported}
    if command=='infer':
        material['relation_pins']=relation_pins
    resource='event-graph:v1:'+_graph_hash(material)
    return {'resource':resource,'context':context,'current':current,'imported':imported,
        'inference_options':inference_options}


def write_scoped_graph_command(command,payload,*,actor,scope,request_id,resource):
    from lumenis.shared.reporting.saved_work import _check_effect
    from lumenis.system.security.permission import OperationType, get_permission_gate
    prepared=prepare_scoped_graph_command(command,payload,actor=actor,scope=scope,request_id=request_id)
    if prepared['resource']!=resource:
        raise PermissionError('GRAPH_PREVIEW_CHANGED')
    if get_permission_gate().get_valid_approval_token('db_write',resource,exact=True) is None:
        raise ValueError('WORK_EFFECT_PERMISSION_DENIED')
    _check_effect(actor,scope,OperationType.DB_WRITE,resource)
    context=prepared['context']
    init_db()
    with get_repository().transaction() as con:
        _graph_identity(actor,scope,'write',connection=con)
        fresh=read_scoped_graph(actor=actor,scope=scope,connection=con)
        if command in {'relation','infer'} and fresh!=prepared['current']:
            raise ValueError('GRAPH_CONCURRENT_CHANGE')
        output=[]
        inference_result={'dropped_auto':0,'added':0,
            'by_type':{'follow':0,'derive':0,'parallel':0},'no_evidence_pairs':0}
        inference_stats=None
        def node(data,origin,source_id=None,suffix=''):
            event_id='GE-S-'+_graph_hash({'context':context,'request_id':request_id,'suffix':suffix})[:32]
            content={'event_id':event_id,'event_type':data['event_type'],'title':data['title'],
                'event_time':data.get('event_time'),'source':origin['kind'],'description':data.get('description',''),
                'status':data.get('status','ongoing'),'source_event_id':source_id}
            meta={'schema':'lumenis.scoped-event-graph/v1','context':context,'request_id':request_id,'origin':origin}
            meta['sha256']=_graph_hash({'content':content,'context':context,'request_id':request_id,'origin':origin})
            old=con.execute('SELECT metadata FROM event_graph_events WHERE event_id=?',(event_id,)).fetchone()
            if old and json.loads(old[0])!=meta:
                raise ValueError('GRAPH_REQUEST_CONFLICT')
            if not old:
                con.execute('INSERT INTO event_graph_events(event_id,event_type,title,event_time,source,description,status,source_event_id,metadata,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    tuple(content.values())+(json.dumps(meta,ensure_ascii=False),_now(),_now()))
            output.append(event_id)
        def relation(source,target,kind,claim,statement):
            proof={'schema':'lumenis.scoped-event-relation/v1','context':context,'relation_type':kind,
                'source_sha256':source['metadata']['sha256'],'target_sha256':target['metadata']['sha256'],
                'claim_type':claim,'statement':statement,'request_id':request_id,
                'causality_verified':False}
            proof['sha256']=_graph_hash(proof)
            old=con.execute('SELECT evidence FROM event_graph_relations WHERE source_event_id=? AND target_event_id=? AND relation_type=?',
                (source['event_id'],target['event_id'],kind)).fetchone()
            if old:
                existing=json.loads(old[0])
                if existing.get('claim_type')=='user_statement' and claim=='automatic_inference':
                    return
                if existing!=proof:
                    raise ValueError('GRAPH_RELATION_ALREADY_EXISTS')
            else:
                con.execute('INSERT INTO event_graph_relations(source_event_id,target_event_id,relation_type,evidence,confidence,created_at) VALUES(?,?,?,?,?,?)',
                    (source['event_id'],target['event_id'],kind,json.dumps(proof,ensure_ascii=False),None,_now()))
            output.append({'source':source['event_id'],'target':target['event_id'],'type':kind,'claim_type':claim})
        if command=='create':
            node(payload,{'kind':'user_statement','verification':'NOT_ESTABLISHED'})
        elif command=='import':
            import database
            for source in prepared['imported']:
                checked=database.get_scoped_event(source['id'],scope,connection=con)
                if checked!=source:
                    raise PermissionError('GRAPH_SOURCE_CHANGED')
                node({'event_type':'public_opinion_event','title':source['title'],'description':source.get('summary',''),
                      'event_time':source.get('event_date'),'status':'ongoing'},
                     {'kind':'verified_scoped_source','scope_evidence_ref':source['scope_evidence_ref'],
                      'causality_verified':False},source['id'],str(source['id']))
        elif command=='relation':
            nodes={row['event_id']:row for row in fresh['events']}
            relation(nodes[payload['source_event_id']],nodes[payload['target_event_id']],payload['relation_type'],
                     'user_statement',payload.get('evidence',''))
        else:
            # Only integrity-verified automatic edges belonging to this exact
            # actor/scope are replaceable. Manual, legacy, rejected and other
            # scope rows are never deleted by inference. The transaction rolls
            # cleanup back if either final authorization check fails.
            for row in fresh['relations']:
                if row['evidence'].get('claim_type')=='automatic_inference':
                    con.execute('DELETE FROM event_graph_relations WHERE id=?',(row['id'],))
                    inference_result['dropped_auto']+=1
            items=[(_parse_dt(row['event_time']),row) for row in fresh['events']]
            items=sorted((item for item in items if item[0] is not None),key=lambda item:item[0])
            for i,(at,a) in enumerate(items):
                if not _text_tokens(a['title']):
                    continue
                for bt,b in items[i+1:]:
                    shared=_text_tokens(a['title']) & _text_tokens(b['title'])
                    if not shared:
                        inference_result['no_evidence_pairs']+=1
                        continue
                    gap_hours=(bt-at).total_seconds()/3600
                    kind=None
                    if gap_hours<=prepared['inference_options']['parallel_hours']:
                        kind='parallel'
                    elif 0<gap_hours<=prepared['inference_options']['days_window']*24:
                        kind='derive' if len(shared)>=3 else 'follow'
                    if kind is None:
                        inference_result['no_evidence_pairs']+=1
                    else:
                        relation(a,b,kind,'automatic_inference',{'shared_terms':sorted(shared),
                            'time_order':gap_hours>0,'gap_hours':gap_hours,
                            'basis':'temporal-and-title-overlap; not causality'})
            inference_result['added']=len(output)
            for row in output:
                inference_result['by_type'][row['type']]+=1
            updated=read_scoped_graph(actor=actor,scope=scope,connection=con)
            event_counts={}
            relation_counts={}
            for row in updated['events']:
                name=EVENT_TYPES.get(row['event_type'],row['event_type'])
                event_counts[name]=event_counts.get(name,0)+1
            for row in updated['relations']:
                name=RELATION_TYPES.get(row['relation_type'],row['relation_type'])
                relation_counts[name]=relation_counts.get(name,0)+1
            inference_stats={'total_events':len(updated['events']),'total_relations':len(updated['relations']),
                'events_by_type':event_counts,'relations_by_type':relation_counts}
        _graph_identity(actor,scope,'write',connection=con)
        if get_permission_gate().get_valid_approval_token('db_write',resource,exact=True) is None:
            raise ValueError('WORK_EFFECT_PERMISSION_DENIED')
        _check_effect(actor,scope,OperationType.DB_WRITE,resource)
    result={'ok':True,'output':output,'external_effect':'not_performed','claim_types':['user_statement','automatic_inference','verified_scoped_source']}
    if command=='infer':
        result.update(result=inference_result,stats=inference_stats)
    return result


def graph_http(mode, event_id=None):
    from flask import request, jsonify
    from experience_runtime import _shared_work_actor_scope, _content_source_same_origin
    from lumenis.system.security.permission import get_permission_gate, PermissionLevel
    try:
        action='read' if request.method=='GET' else 'write'
        actor,scope=_shared_work_actor_scope(action)
        if action=='read':
            result=read_scoped_graph(actor=actor,scope=scope)
            if mode=='stats':
                return jsonify({'ok':True,'data':{'events':len(result['events']),'relations':len(result['relations']),
                    'by_type':{kind:sum(r['event_type']==kind for r in result['events']) for kind in EVENT_TYPES},
                    'rejected':result['rejected'],'legacy_scope':'UNKNOWN'}})
            if mode=='chain':
                depth=int(request.args.get('max_depth','5'))
                if not 0<=depth<=20:
                    raise ValueError('GRAPH_DEPTH_INVALID')
                nodes={r['event_id']:r for r in result['events']}
                if event_id not in nodes:
                    raise LookupError('GRAPH_EVENT_NOT_FOUND_IN_SCOPE')
                reached={event_id}; frontier={event_id}
                for _ in range(depth):
                    frontier={r['target_event_id'] for r in result['relations'] if r['source_event_id'] in frontier}-reached
                    reached.update(frontier)
                return jsonify({'ok':True,'chain':[nodes[key] for key in sorted(reached)],
                    'relations':[r for r in result['relations'] if r['source_event_id'] in reached and r['target_event_id'] in reached],
                    'count':len(reached)})
            kind=request.args.get('type')
            if kind is not None and kind not in EVENT_TYPES:
                raise ValueError('GRAPH_TYPE_INVALID')
            rows=[r for r in result['events'] if not kind or r['event_type']==kind]
            return jsonify({'ok':True,**result,'events':rows,'count':len(rows)})
        if not _content_source_same_origin():
            raise PermissionError('GRAPH_ORIGIN_DENIED')
        body=request.get_json(silent=True)
        if (not isinstance(body,dict) or set(body)-{'request_id','payload','confirm','confirmed_resource','command'}
                or type(body.get('confirm',False)) is not bool):
            raise ValueError('GRAPH_EXACT_REQUEST_REQUIRED')
        command=body.get('command') if mode=='revoke' else mode
        preview=prepare_scoped_graph_command(command,body.get('payload'),actor=actor,scope=scope,request_id=body.get('request_id'))
        if body.get('confirm') is not True:
            return jsonify({'ok':True,'state':'PREPARED','resource':preview['resource'],
                'operation_type':'db_write','approval_issued':False,'external_effect':'not_performed'})
        if body.get('confirmed_resource')!=preview['resource']:
            raise PermissionError('GRAPH_PREVIEW_CHANGED')
        gate=get_permission_gate()
        if not gate.has_permission(PermissionLevel.HUMAN_APPROVAL) or not gate.has_permission(PermissionLevel.COMMIT):
            raise PermissionError('GRAPH_MANUAL_AUTHORITY_REQUIRED')
        resource=preview['resource']
        token=gate.get_valid_approval_token('db_write',resource,exact=True)
        if mode=='revoke':
            return jsonify({'ok':True,'revoked':bool(token and gate.revoke_approval(token))})
        if token is None:
            token=gate.grant_approval('db_write',resource=resource,duration_minutes=5,
                granted_by=preview['context'].get('principal_ref') or 'actor:'+str(preview['context']['actor_id']))
        try:
            result=write_scoped_graph_command(command,body['payload'],actor=actor,scope=scope,
                request_id=body['request_id'],resource=resource)
        except Exception:
            gate.revoke_approval(token)
            raise
        return jsonify(result)
    except PermissionError as exc:
        return jsonify({'ok':False,'code':str(exc)}),403
    except LookupError as exc:
        return jsonify({'ok':False,'code':str(exc)}),404
    except (TypeError,ValueError) as exc:
        return jsonify({'ok':False,'code':str(exc)}),400
    except Exception:
        return jsonify({'ok':False,'code':'SCOPED_GRAPH_UNAVAILABLE'}),503


_GRAPH_HTTP_ROUTES={
    'event_graph_stats':('/api/event-graph/stats','GET'),
    'event_graph_events':('/api/event-graph/events','GET'),
    'event_graph_chain':('/api/event-graph/chain/<event_id>','GET'),
    'event_graph_create_event':('/api/event-graph/events','POST'),
    'event_graph_add_relation':('/api/event-graph/relations','POST'),
    'event_graph_import_existing':('/api/event-graph/import','POST'),
    'event_graph_rebuild_relations':('/api/event-graph/rebuild-relations','POST'),
    'event_graph_revoke_approval':('/api/event-graph/approval/revoke','POST'),
}


def scoped_graph_route_matches():
    from flask import request
    return bool(request.url_rule is not None and _GRAPH_HTTP_ROUTES.get(request.endpoint)==(request.url_rule.rule,request.method))


def scoped_graph_local_access_allowed():
    from flask import request
    from experience_runtime import _shared_work_actor_scope
    from lumenis.system.security.permission import LocalWorkspacePrincipal
    if not scoped_graph_route_matches():
        return False
    try:
        actor,_scope=_shared_work_actor_scope('read' if request.method=='GET' else 'write')
        return type(actor) is LocalWorkspacePrincipal
    except (ValueError,PermissionError):
        return False
