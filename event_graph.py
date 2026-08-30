"""
事件关系图谱（V3.0 P1.3 事件关系体系）
归属：Z-Brand Core / ZBMP / 品牌智能层
目标：
  1. 建立营销事件、传播事件、舆情事件的统一事件模型
  2. 实现事件间的关系图谱：触发、衍生、继发、并行
  3. 为品牌传播分析提供事件维度的数据基础

事件类型定义：
  - marketing_event（营销事件）：品牌主动发起的营销活动，如新品发布、促销活动、品牌联名、线下活动等
  - propagation_event（传播事件）：内容在社交媒体上的传播过程，如话题发酵、KOL转发、用户UGC爆发等
  - public_opinion_event（舆情事件）：引发公众讨论的舆情事件，如负面曝光、危机事件、热点话题等

关系类型定义：
  - trigger（触发）：A事件直接导致B事件的发生（如营销活动触发用户讨论）
  - derive（衍生）：B事件是A事件的衍生或分支（如主话题衍生出多个子话题）
  - follow（继发）：B事件在A事件之后发生，存在时间上的先后关系（如危机后品牌回应）
  - parallel（并行）：A和B事件同时发生，相互影响但无直接因果（如两个品牌同时做活动）

设计原则（V3.0 基线要求）：
  - 事件模型统一：所有事件共享基础字段（id、type、title、time、source、status）
  - 关系有向图：事件关系是有向的，从源事件指向目标事件
  - 关系可追溯：每个关系都有证据（如时间戳、内容链接、数据来源）
  - 支持多关系：两个事件之间可以存在多种关系（如同时触发和并行）
"""
from __future__ import annotations

import json
import os
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


class BrandEvent:
    """品牌事件基类"""

    def __init__(self, event_type: str, title: str, event_time: str = None,
                 source: str = '', description: str = '', status: str = 'ongoing',
                 metadata: Dict[str, Any] = None, event_id: str = None):
        self.event_id = event_id or str(uuid.uuid4())[:8]
        self.event_type = event_type
        self.event_type_name = EVENT_TYPES.get(event_type, event_type)
        self.title = title
        self.event_time = event_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.source = source
        self.description = description
        self.status = status
        self.status_name = EVENT_STATUS.get(status, status)
        self.metadata = metadata or {}
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
            'relations': [rel.to_dict() for rel in self.relations],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrandEvent':
        """从字典创建"""
        event = cls(
            event_type=data['event_type'],
            title=data['title'],
            event_time=data.get('event_time'),
            source=data.get('source', ''),
            description=data.get('description', ''),
            status=data.get('status', 'ongoing'),
            metadata=data.get('metadata', {}),
            event_id=data.get('event_id'),
        )
        return event


class EventRelation:
    """事件关系"""

    def __init__(self, source_event: BrandEvent, target_event: BrandEvent,
                 relation_type: str, evidence: str = '', confidence: float = 0.5):
        self.source_event = source_event
        self.target_event = target_event
        self.relation_type = relation_type
        self.relation_type_name = RELATION_TYPES.get(relation_type, relation_type)
        self.evidence = evidence
        self.confidence = confidence
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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


class EventGraph:
    """事件关系图谱"""

    def __init__(self):
        self.events: Dict[str, BrandEvent] = {}
        self.relations: List[EventRelation] = []

    def add_event(self, event: BrandEvent) -> BrandEvent:
        """添加事件"""
        self.events[event.event_id] = event
        return event

    def get_event(self, event_id: str) -> Optional[BrandEvent]:
        """获取事件"""
        return self.events.get(event_id)

    def add_relation(self, source_id: str, target_id: str, relation_type: str,
                     evidence: str = '', confidence: float = 0.5) -> Optional[EventRelation]:
        """添加事件关系"""
        source = self.get_event(source_id)
        target = self.get_event(target_id)
        if not source or not target:
            return None
        relation = source.add_relation(target, relation_type, evidence, confidence)
        self.relations.append(relation)
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
        _graph_instance = EventGraph()
    return _graph_instance
