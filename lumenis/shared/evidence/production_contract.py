"""LUMENIS Production Evidence Contract（Shared Evidence）

生产证据契约：LUMENIS 的受保护生产操作必须产生可验证证据。
保护 Production Truth：AI/Agent 不得直接修改生产数据，必须经过 Evidence → Evaluation → Human Approval。
与 OSAI Canonical Data 的 Evidence 实体通过 Contract 对接。
"""
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProductionEvidence:
    """生产证据。"""
    evidence_id: str
    evidence_type: str  # collection / subject_filter / risk_judgment / event_aggregation / report_generation / config_change
    source: str  # 数据来源
    content_hash: str
    product_id: str = "CTH"
    subject_id: str = ""
    timestamp: float = field(default_factory=time.time)
    status: str = "CREATED"  # CREATED / VERIFIED / REJECTED / SUPERSEDED
    verified_by: str = ""  # human / rule / ai_assist
    verification_method: str = ""
    related_db_tables: List[str] = field(default_factory=list)
    related_records: List[str] = field(default_factory=list)
    ai_assisted: bool = False
    human_approved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "content_hash": self.content_hash,
            "product_id": self.product_id,
            "subject_id": self.subject_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "verified_by": self.verified_by,
            "verification_method": self.verification_method,
            "related_db_tables": self.related_db_tables,
            "ai_assisted": self.ai_assisted,
            "human_approved": self.human_approved,
        }


class ProductionEvidenceContract:
    """生产证据契约管理器。"""

    # 受保护的生产操作：必须产生证据
    PROTECTED_OPERATIONS = {
        "subject_rule_change": "修改主体词/排除词",
        "risk_threshold_change": "修改风险阈值",
        "data_deletion": "删除生产数据",
        "db_migration": "数据库迁移",
        "collector_config_change": "采集器配置变更",
        "report_regeneration": "报告重新生成",
    }

    def __init__(self):
        self._evidence: Dict[str, ProductionEvidence] = {}

    def create_evidence(self, evidence_type: str, source: str,
                        content: Any, product_id: str = "CTH",
                        subject_id: str = "",
                        related_db_tables: List[str] = None,
                        ai_assisted: bool = False) -> ProductionEvidence:
        """创建生产证据。"""
        content_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True, default=str, ensure_ascii=False).encode()
        ).hexdigest()[:16]
        ev = ProductionEvidence(
            evidence_id=f"pev_{uuid.uuid4().hex[:12]}",
            evidence_type=evidence_type,
            source=source,
            content_hash=content_hash,
            product_id=product_id,
            subject_id=subject_id,
            related_db_tables=related_db_tables or [],
            ai_assisted=ai_assisted,
        )
        self._evidence[ev.evidence_id] = ev
        return ev

    def verify(self, evidence_id: str, verified_by: str = "rule",
               method: str = "") -> bool:
        """验证证据。"""
        ev = self._evidence.get(evidence_id)
        if not ev:
            return False
        ev.status = "VERIFIED"
        ev.verified_by = verified_by
        ev.verification_method = method
        return True

    def require_human_approval(self, evidence_id: str) -> bool:
        """AI 辅助的生产变更必须人工批准。"""
        ev = self._evidence.get(evidence_id)
        if not ev:
            return False
        if ev.ai_assisted and ev.evidence_type in self.PROTECTED_OPERATIONS:
            return True
        return False

    def approve(self, evidence_id: str) -> bool:
        """人工批准。"""
        ev = self._evidence.get(evidence_id)
        if not ev:
            return False
        ev.human_approved = True
        ev.status = "VERIFIED"
        return True

    def can_execute_production_change(self, evidence_id: str) -> Dict[str, Any]:
        """检查是否可以执行生产变更。

        AI 辅助的受保护操作必须：Evidence CREATED → VERIFIED → HUMAN APPROVED。
        """
        ev = self._evidence.get(evidence_id)
        if not ev:
            return {"allowed": False, "reason": "evidence not found"}
        if ev.status != "VERIFIED":
            return {"allowed": False, "reason": f"evidence status is {ev.status}, not VERIFIED"}
        if self.require_human_approval(evidence_id) and not ev.human_approved:
            return {"allowed": False, "reason": "AI-assisted protected operation requires human approval"}
        return {"allowed": True, "evidence": ev.to_dict()}

    def list_evidence(self, evidence_type: str = None,
                      status: str = None) -> List[ProductionEvidence]:
        results = list(self._evidence.values())
        if evidence_type:
            results = [e for e in results if e.evidence_type == evidence_type]
        if status:
            results = [e for e in results if e.status == status]
        return results

    def summary(self) -> Dict[str, Any]:
        by_type = {}
        by_status = {}
        for e in self._evidence.values():
            by_type[e.evidence_type] = by_type.get(e.evidence_type, 0) + 1
            by_status[e.status] = by_status.get(e.status, 0) + 1
        return {
            "total": len(self._evidence),
            "by_type": by_type,
            "by_status": by_status,
            "ai_assisted": sum(1 for e in self._evidence.values() if e.ai_assisted),
            "human_approved": sum(1 for e in self._evidence.values() if e.human_approved),
        }