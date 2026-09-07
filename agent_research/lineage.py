# -*- coding: utf-8 -*-
"""
Evidence Lineage — 证据血缘追踪
================================
研究流程中的证据血缘（Evidence Lineage）追踪器。

确保每个结论可追溯到：假设 → 专家 → 证据 → 探索路径。
Lineage 以有向无环图（DAG）形式记录祖先链，支持查询和导出。

设计原则：
  - 纯内存追踪，无外部依赖
  - 每个 finding 必须带 evidence_refs 和 lineage_id
  - 支持按 evidence_id / hypothesis_id / specialist_id 查询血缘
  - 可导出为 JSON 可序列化结构
  - 与 agent_runtime 风格一致
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_research.specialist import _short_id, _utc_now_iso


@dataclass
class EvidenceLineage:
    """
    单条证据血缘记录。

    Attributes:
        lineage_id: 血缘记录唯一标识
        evidence_id: 关联的证据 ID
        source: 证据来源（specialist_id / hypothesis_id / external）
        path: 祖先链（从根到当前节点的 ID 列表，如 [hyp_id, finding_id, evidence_id]）
        provenance: 来源描述（dict，含生成方式、时间戳、专家等）
        timestamp: 记录时间
    """
    lineage_id: str
    evidence_id: str
    source: str
    path: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LineageTracker:
    """
    证据血缘追踪器。

    维护 lineage_id -> EvidenceLineage 的映射，以及反向索引：
      - evidence_id -> [lineage_id]
      - source (specialist_id) -> [lineage_id]
      - path 中包含某 hypothesis_id -> [lineage_id]

    用法：
      tracker = LineageTracker()
      lid = tracker.track(evidence_id="ev_001", source="analyst",
                           path=["hyp_001", "finding_001", "ev_001"],
                           provenance={"method": "rule_based"})
      record = tracker.query(lineage_id=lid)
      all_records = tracker.export()
    """

    def __init__(self) -> None:
        self._lineages: Dict[str, EvidenceLineage] = {}
        # 反向索引
        self._by_evidence: Dict[str, List[str]] = {}
        self._by_source: Dict[str, List[str]] = {}
        self._by_hypothesis: Dict[str, List[str]] = {}

    def track(
        self,
        evidence_id: str,
        source: str,
        path: Optional[List[str]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        追踪一条证据血缘。

        Args:
            evidence_id: 证据 ID
            source: 来源（specialist_id 或其他标识）
            path: 祖先链 ID 列表；为 None 时自动生成 [evidence_id]
            provenance: 来源元数据

        Returns:
            新创建的 lineage_id
        """
        lineage_id = _short_id("lin")
        if path is None:
            path = [evidence_id]
        if provenance is None:
            provenance = {}

        record = EvidenceLineage(
            lineage_id=lineage_id,
            evidence_id=evidence_id,
            source=source,
            path=list(path),
            provenance=dict(provenance),
        )
        self._lineages[lineage_id] = record

        # 更新反向索引
        self._by_evidence.setdefault(evidence_id, []).append(lineage_id)
        self._by_source.setdefault(source, []).append(lineage_id)
        # path 中第一个元素通常是 hypothesis_id
        if path:
            hyp_id = path[0]
            self._by_hypothesis.setdefault(hyp_id, []).append(lineage_id)

        return lineage_id

    def query(self, lineage_id: str) -> Optional[EvidenceLineage]:
        """
        按 lineage_id 查询血缘记录。

        Args:
            lineage_id: 血缘 ID

        Returns:
            EvidenceLineage 对象，不存在返回 None
        """
        return self._lineages.get(lineage_id)

    def query_by_evidence(self, evidence_id: str) -> List[EvidenceLineage]:
        """按 evidence_id 查询所有关联血缘记录。"""
        ids = self._by_evidence.get(evidence_id, [])
        return [self._lineages[i] for i in ids if i in self._lineages]

    def query_by_source(self, source: str) -> List[EvidenceLineage]:
        """按 source（specialist_id）查询所有血缘记录。"""
        ids = self._by_source.get(source, [])
        return [self._lineages[i] for i in ids if i in self._lineages]

    def query_by_hypothesis(self, hypothesis_id: str) -> List[EvidenceLineage]:
        """按 hypothesis_id（path 首元素）查询所有血缘记录。"""
        ids = self._by_hypothesis.get(hypothesis_id, [])
        return [self._lineages[i] for i in ids if i in self._lineages]

    def list_all(self) -> List[EvidenceLineage]:
        """返回所有血缘记录（按 timestamp 排序）。"""
        records = list(self._lineages.values())
        records.sort(key=lambda r: r.timestamp)
        return records

    def export(self) -> List[Dict[str, Any]]:
        """
        导出所有血缘记录为 JSON 可序列化的字典列表。

        Returns:
            字典列表，每个元素为一条 EvidenceLineage 的 asdict
        """
        return [r.to_dict() for r in self.list_all()]

    def export_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串。"""
        return json.dumps(self.export(), ensure_ascii=False, indent=indent)

    def __len__(self) -> int:
        return len(self._lineages)
