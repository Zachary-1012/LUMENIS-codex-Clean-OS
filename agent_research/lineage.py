# -*- coding: utf-8 -*-
"""
Evidence Lineage — 证据血缘追踪
仅记录调用者提供的标识和路径；不解析外部证据、不验证来源存在性或授权。
纯内存追踪，无外部依赖。真实SourceBrief分析见source_bound.py。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from agent_research.specialist import _short_id, _utc_now_iso


@dataclass
class EvidenceLineage:
    """单条证据血缘记录：lineage_id/evidence_id/source/path/provenance/timestamp。"""
    lineage_id: str
    evidence_id: str
    source: str
    path: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LineageTracker:
    """证据血缘追踪器：track/query/query_by_evidence/query_by_source/query_by_hypothesis/export。"""

    def __init__(self) -> None:
        self._lineages: Dict[str, EvidenceLineage] = {}
        self._by_evidence: Dict[str, List[str]] = {}
        self._by_source: Dict[str, List[str]] = {}
        self._by_hypothesis: Dict[str, List[str]] = {}

    def track(
        self, evidence_id: str, source: str,
        path: Optional[List[str]] = None, provenance: Optional[Dict[str, Any]] = None,
    ) -> str:
        """追踪一条证据血缘，返回 lineage_id。"""
        lineage_id = _short_id("lin")
        record = EvidenceLineage(
            lineage_id=lineage_id, evidence_id=evidence_id, source=source,
            path=list(path) if path else [evidence_id],
            provenance=dict(provenance) if provenance else {},
        )
        self._lineages[lineage_id] = record
        self._by_evidence.setdefault(evidence_id, []).append(lineage_id)
        self._by_source.setdefault(source, []).append(lineage_id)
        if record.path:
            self._by_hypothesis.setdefault(record.path[0], []).append(lineage_id)
        return lineage_id

    def query(self, lineage_id: str) -> Optional[EvidenceLineage]:
        return self._lineages.get(lineage_id)

    def query_by_evidence(self, evidence_id: str) -> List[EvidenceLineage]:
        return [self._lineages[i] for i in self._by_evidence.get(evidence_id, []) if i in self._lineages]

    def query_by_source(self, source: str) -> List[EvidenceLineage]:
        return [self._lineages[i] for i in self._by_source.get(source, []) if i in self._lineages]

    def query_by_hypothesis(self, hypothesis_id: str) -> List[EvidenceLineage]:
        return [self._lineages[i] for i in self._by_hypothesis.get(hypothesis_id, []) if i in self._lineages]

    def list_all(self) -> List[EvidenceLineage]:
        records = list(self._lineages.values())
        records.sort(key=lambda r: r.timestamp)
        return records

    def export(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.list_all()]

    def export_json(self, indent: int = 2) -> str:
        return json.dumps(self.export(), ensure_ascii=False, indent=indent)

    def __len__(self) -> int:
        return len(self._lineages)
