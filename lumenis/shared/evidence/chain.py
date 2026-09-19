# -*- coding: utf-8 -*-
"""LUMENIS Shared Evidence / Canonical Data 数据链核心模块

统一数据生命周期：
  External Source → Evidence → Canonical Data → Event → Case → Finding
  → Insight → Decision → Action → Outcome → Evaluation → Feedback → Learning Asset

核心原则（不可违反）：
  1. 原始证据(Evidence)不可被分析结果覆盖 —— Evidence 表 raw_content/content_hash/source
     字段写入后禁止 UPDATE，只能追加新记录。
  2. AI 输出与人工最终判断分离 —— CanonicalData.ai_analysis 与 human_correction 为
     独立 JSON 字段，人工修正不覆盖 AI 原始输出。
  3. historical data 不得被新规则静默改写 —— rule_version 追踪每条规范数据的规则版本，
     新规则只对新数据生效，历史数据保留原 rule_version。
  4. hash 去重 —— 相同 content_hash(SHA256) 的证据不重复入库。
  5. 完整 provenance —— 每条 Evidence 携带 hash/timestamp/source/subject_scope/
     collection_metadata/provider/authenticity_score。

本模块使用受治理的 Evidence/Canonical lifecycle 表（历史物理表名保持 zbc_evidence / zbc_canonical_data / zbc_lifecycle_tracking），
不修改、不覆盖现有 canonical_data、app_evidence_records、notes 等生产表。
新字段一律可空，向后兼容。
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from functools import lru_cache
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 配置
# ============================================================
# P0-DBISO-01：统一走 db_paths（ZBC_EVIDENCE_DB_PATH -> ZBC_DB_PATH -> 默认），call-time
from lumenis.shared.database import DatabaseRepository, main_db_path
DB_PATH = main_db_path()

# 规则版本：每次规则变更递增，历史数据保留创建时的版本
RULE_VERSION = "evidence-chain-v1.0.0"

# 数据生命周期阶段定义（13 阶段，每阶段有明确输入/输出/转换规则）
LIFECYCLE_STAGES: Dict[str, Dict[str, Any]] = {
    "EXTERNAL_SOURCE": {
        "order": 0,
        "input": "平台原始内容（小红书笔记/微博/全网提及等）",
        "output": "未处理的原始文本+元数据",
        "transform": "仅读取，不修改；记录 source_url/source_type",
        "immutable": True,
    },
    "EVIDENCE": {
        "order": 1,
        "input": "EXTERNAL_SOURCE 输出",
        "output": "Evidence 记录（含 content_hash/provenance）",
        "transform": "计算 SHA256 content_hash；记录 captured_at/publish_datetime/"
                     "subject_scope/collection_metadata/provider/authenticity_score；hash 去重",
        "immutable": True,
    },
    "CANONICAL_DATA": {
        "order": 2,
        "input": "Evidence 记录",
        "output": "CanonicalData 记录（规范化+主体过滤+质量门+情感/风险）",
        "transform": "内容规范化；subject_hit 判定；sentiment/risk_level 计算；"
                     "engagement_metrics 聚合；rule_version 标记；AI 分析与人工修正分离存储",
        "immutable": False,
    },
    "EVENT": {
        "order": 3,
        "input": "CanonicalData 集合",
        "output": "Event（事件聚合）",
        "transform": "事件聚类；生命周期标记；mention_count/source_count 统计",
        "immutable": False,
    },
    "CASE": {
        "order": 4,
        "input": "Event + 人工判断",
        "output": "Case（案例/工单）",
        "transform": "事件升级为案例；分配负责人；状态跟踪",
        "immutable": False,
    },
    "FINDING": {
        "order": 5,
        "input": "Case 分析结果",
        "output": "Finding（发现/结论）",
        "transform": "根因分析；事实确认；影响评估",
        "immutable": False,
    },
    "INSIGHT": {
        "order": 6,
        "input": "Finding + 历史数据",
        "output": "Insight（洞察）",
        "transform": "趋势识别；模式提炼；跨事件关联",
        "immutable": False,
    },
    "DECISION": {
        "order": 7,
        "input": "Insight + 业务目标",
        "output": "Decision（决策）",
        "transform": "策略选择；优先级排序；资源分配",
        "immutable": False,
    },
    "ACTION": {
        "order": 8,
        "input": "Decision",
        "output": "Action（执行动作）",
        "transform": "任务分解；执行跟踪；责任人分配",
        "immutable": False,
    },
    "OUTCOME": {
        "order": 9,
        "input": "Action 执行结果",
        "output": "Outcome（结果）",
        "transform": "效果度量；KPI 对比；成功/失败判定",
        "immutable": True,
    },
    "EVALUATION": {
        "order": 10,
        "input": "Outcome + 预期目标",
        "output": "Evaluation（评估）",
        "transform": "ROI 分析；经验总结；差距识别",
        "immutable": False,
    },
    "FEEDBACK": {
        "order": 11,
        "input": "Evaluation",
        "output": "Feedback（反馈）",
        "transform": "规则优化建议；采集策略调整；词表更新",
        "immutable": False,
    },
    "LEARNING_ASSET": {
        "order": 12,
        "input": "Feedback + 历史案例",
        "output": "Learning Asset（学习资产）",
        "transform": "样本沉淀；规则更新；模型微调数据；知识库条目",
        "immutable": True,
    },
}


# ============================================================
# 数据类
# ============================================================
@dataclass
class Evidence:
    """原始证据 —— 写入后不可变（immutable）。

    核心约束：raw_content / content_hash / source_type / source_url /
    captured_at / publish_datetime / subject_scope / collection_metadata /
    provider / authenticity_score 写入后禁止 UPDATE。
    """
    evidence_id: str
    source_type: str               # xhs_note / xhs_comment / weibo / web_mention / app_screenshot ...
    source_url: str
    raw_content: str
    content_hash: str              # SHA256 完整哈希（64字符）
    captured_at: str               # 系统采集时间
    source_id: str = ""            # Track3：原始来源 ID（平台笔记 ID 等），可追溯
    task_id: str = ""              # Track3：采集任务 ID，关联采集批次
    trace_id: str = ""             # Track3：全链路追踪 ID
    publish_datetime: Optional[str] = None  # 内容真实发布时间
    subject_scope: str = "CTH"     # 主体范围（广州太古汇=CTH）
    collection_metadata: Dict[str, Any] = field(default_factory=dict)
    provider: str = "rule"         # 采集提供者/适配器
    authenticity_score: float = 1.0  # 真实性评分 0-1
    domain_id: str = "cth"           # ZBC V2.0 双域隔离：域身份
    product_id: str = "CTH"          # 产品 ID（CTH/ZBMP）
    evaluation_id: str = ""          # 关联评估 ID
    final_decision: str = ""         # 最终判断（Rule→AI辅助→Evidence→Evaluation→Final Decision）
    rule_id: str = ""                # 经过的规则 ID
    ai_call_id: str = ""             # 关联的 AI 调用 ID
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now()
        if not self.content_hash:
            self.content_hash = compute_content_hash(self.raw_content)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["collection_metadata"] = json.dumps(self.collection_metadata, ensure_ascii=False)
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Evidence":
        data = dict(row)
        if isinstance(data.get("collection_metadata"), str):
            try:
                data["collection_metadata"] = json.loads(data["collection_metadata"])
            except (json.JSONDecodeError, TypeError):
                data["collection_metadata"] = {}
        return cls(**data)


@dataclass
class CanonicalData:
    """规范数据 —— 从 Evidence 转换而来，AI 输出与人工修正分离。

    核心约束：
      - ai_analysis 存储 AI 原始输出，永不被人工修正覆盖
      - human_correction 存储人工最终判断，独立字段
      - rule_version 标记创建时的规则版本，历史数据不被新规则静默改写
      - evidence_id 为 FK，关联不可变的原始证据
    """
    canonical_id: str
    evidence_id: str               # FK → Evidence.evidence_id
    normalized_content: str
    subject_hit: bool = False
    subject_keywords: List[str] = field(default_factory=list)
    sentiment: str = "neutral"     # positive / neutral / negative / unknown
    risk_level: str = "low"        # low / medium / high / critical
    engagement_metrics: Dict[str, Any] = field(default_factory=dict)
    rule_version: str = RULE_VERSION
    ai_analysis: Dict[str, Any] = field(default_factory=dict)       # AI 原始输出（独立）
    human_correction: Dict[str, Any] = field(default_factory=dict)  # 人工最终判断（独立）
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = _now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subject_keywords"] = json.dumps(self.subject_keywords, ensure_ascii=False)
        d["engagement_metrics"] = json.dumps(self.engagement_metrics, ensure_ascii=False)
        d["ai_analysis"] = json.dumps(self.ai_analysis, ensure_ascii=False)
        d["human_correction"] = json.dumps(self.human_correction, ensure_ascii=False)
        d["subject_hit"] = 1 if self.subject_hit else 0
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "CanonicalData":
        data = dict(row)
        for json_field in ("subject_keywords", "engagement_metrics", "ai_analysis", "human_correction"):
            if isinstance(data.get(json_field), str):
                try:
                    data[json_field] = json.loads(data[json_field])
                except (json.JSONDecodeError, TypeError):
                    data[json_field] = {} if json_field != "subject_keywords" else []
        data["subject_hit"] = bool(data.get("subject_hit", 0))
        return cls(**data)


# ============================================================
# 工具函数
# ============================================================
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def compute_content_hash(raw_content: str) -> str:
    """计算内容 SHA256 完整哈希（64字符十六进制）。

    用于证据去重和完整性校验。与现有 evidence_store 的 16 字符截断哈希不同，
    这里使用完整 SHA256 以降低碰撞概率。
    """
    if raw_content is None:
        raw_content = ""
    return hashlib.sha256(str(raw_content).encode("utf-8")).hexdigest()


def generate_evidence_id() -> str:
    return "ev_" + uuid.uuid4().hex[:16]


def generate_canonical_id() -> str:
    return "can_" + uuid.uuid4().hex[:16]


# ============================================================
# 数据库 Schema（独立表，不碰现有生产表）
# ============================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS zbc_evidence (
    evidence_id        TEXT PRIMARY KEY,
    source_type        TEXT NOT NULL DEFAULT 'unknown',
    source_url         TEXT NOT NULL DEFAULT '',
    source_id          TEXT NOT NULL DEFAULT '',
    raw_content        TEXT NOT NULL DEFAULT '',
    content_hash       TEXT NOT NULL DEFAULT '',
    captured_at        TEXT NOT NULL DEFAULT '',
    publish_datetime   TEXT,
    subject_scope      TEXT NOT NULL DEFAULT 'CTH',
    task_id            TEXT NOT NULL DEFAULT '',
    trace_id           TEXT NOT NULL DEFAULT '',
    collection_metadata TEXT NOT NULL DEFAULT '{}',
    provider           TEXT NOT NULL DEFAULT 'rule',
    authenticity_score REAL NOT NULL DEFAULT 1.0,
    domain_id          TEXT NOT NULL DEFAULT 'cth',
    product_id         TEXT NOT NULL DEFAULT 'CTH',
    evaluation_id      TEXT NOT NULL DEFAULT '',
    final_decision     TEXT NOT NULL DEFAULT '',
    rule_id            TEXT NOT NULL DEFAULT '',
    ai_call_id         TEXT NOT NULL DEFAULT '',
    created_at         TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_zbc_evidence_hash ON zbc_evidence(content_hash);
CREATE INDEX IF NOT EXISTS idx_zbc_evidence_source ON zbc_evidence(source_type);
CREATE INDEX IF NOT EXISTS idx_zbc_evidence_scope ON zbc_evidence(subject_scope);
CREATE INDEX IF NOT EXISTS idx_zbc_evidence_domain ON zbc_evidence(domain_id);
CREATE INDEX IF NOT EXISTS idx_zbc_evidence_product ON zbc_evidence(product_id);
CREATE INDEX IF NOT EXISTS idx_zbc_evidence_trace ON zbc_evidence(trace_id);

CREATE TABLE IF NOT EXISTS zbc_canonical_data (
    canonical_id       TEXT PRIMARY KEY,
    evidence_id        TEXT NOT NULL DEFAULT '',
    normalized_content TEXT NOT NULL DEFAULT '',
    subject_hit        INTEGER NOT NULL DEFAULT 0,
    subject_keywords   TEXT NOT NULL DEFAULT '[]',
    sentiment          TEXT NOT NULL DEFAULT 'neutral',
    risk_level         TEXT NOT NULL DEFAULT 'low',
    engagement_metrics TEXT NOT NULL DEFAULT '{}',
    rule_version       TEXT NOT NULL DEFAULT 'evidence-chain-v1.0.0',
    ai_analysis        TEXT NOT NULL DEFAULT '{}',
    human_correction   TEXT NOT NULL DEFAULT '{}',
    created_at         TEXT NOT NULL DEFAULT '',
    updated_at         TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (evidence_id) REFERENCES zbc_evidence(evidence_id)
);
CREATE INDEX IF NOT EXISTS idx_zbc_canonical_evidence ON zbc_canonical_data(evidence_id);
CREATE INDEX IF NOT EXISTS idx_zbc_canonical_rule ON zbc_canonical_data(rule_version);
CREATE INDEX IF NOT EXISTS idx_zbc_canonical_sentiment ON zbc_canonical_data(sentiment);
CREATE INDEX IF NOT EXISTS idx_zbc_canonical_risk ON zbc_canonical_data(risk_level);

CREATE TABLE IF NOT EXISTS zbc_lifecycle_tracking (
    tracking_id        TEXT PRIMARY KEY,
    evidence_id        TEXT NOT NULL DEFAULT '',
    canonical_id       TEXT NOT NULL DEFAULT '',
    stage              TEXT NOT NULL DEFAULT '',
    stage_order        INTEGER NOT NULL DEFAULT 0,
    input_ref          TEXT NOT NULL DEFAULT '',
    output_ref         TEXT NOT NULL DEFAULT '',
    transform_rule     TEXT NOT NULL DEFAULT '',
    rule_version       TEXT NOT NULL DEFAULT 'evidence-chain-v1.0.0',
    operator           TEXT NOT NULL DEFAULT 'system',
    task_id            TEXT NOT NULL DEFAULT '',
    trace_id           TEXT NOT NULL DEFAULT '',
    evaluation_id      TEXT NOT NULL DEFAULT '',
    metadata           TEXT NOT NULL DEFAULT '{}',
    created_at         TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_zbc_lifecycle_evidence ON zbc_lifecycle_tracking(evidence_id);
CREATE INDEX IF NOT EXISTS idx_zbc_lifecycle_canonical ON zbc_lifecycle_tracking(canonical_id);
CREATE INDEX IF NOT EXISTS idx_zbc_lifecycle_stage ON zbc_lifecycle_tracking(stage);
"""


def _get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = DatabaseRepository(db_path or main_db_path()).connect(timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """初始化证据链表（独立表，不碰现有生产表）。Track3：自动迁移补列。"""
    conn = _get_conn(db_path)
    try:
        conn.executescript(SCHEMA)
        _migrate_evidence_chain(conn)
        conn.commit()
    finally:
        conn.close()


# Track3：旧表迁移——为已存在的表补齐缺失列（幂等）
_EVIDENCE_NEW_COLS = [
    ("source_id", "TEXT NOT NULL DEFAULT ''"),
    ("task_id", "TEXT NOT NULL DEFAULT ''"),
    ("trace_id", "TEXT NOT NULL DEFAULT ''"),
    ("domain_id", "TEXT NOT NULL DEFAULT 'cth'"),
    ("product_id", "TEXT NOT NULL DEFAULT 'CTH'"),
    ("evaluation_id", "TEXT NOT NULL DEFAULT ''"),
    ("final_decision", "TEXT NOT NULL DEFAULT ''"),
    ("rule_id", "TEXT NOT NULL DEFAULT ''"),
    ("ai_call_id", "TEXT NOT NULL DEFAULT ''"),
]
_LIFECYCLE_NEW_COLS = [
    ("task_id", "TEXT NOT NULL DEFAULT ''"),
    ("trace_id", "TEXT NOT NULL DEFAULT ''"),
    ("evaluation_id", "TEXT NOT NULL DEFAULT ''"),
]


def _migrate_evidence_chain(conn):
    """对已存在的表执行 ALTER TABLE 补列（忽略已存在的列）。"""
    for table, cols in (("zbc_evidence", _EVIDENCE_NEW_COLS),
                         ("zbc_lifecycle_tracking", _LIFECYCLE_NEW_COLS)):
        try:
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            continue
        for col, col_def in cols:
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                except Exception:
                    pass


# ============================================================
# Evidence Store —— 原始证据不可变
# ============================================================
class EvidenceStore:
    """原始证据存储。

    硬约束：
      - 相同 content_hash 不重复入库（返回已有记录）
      - Evidence 写入后禁止 UPDATE raw_content/content_hash/source 等不可变字段
      - 只能追加，不能修改或删除
    """

    # 不可变字段列表 —— 写入后禁止修改
    IMMUTABLE_FIELDS = frozenset({
        "evidence_id", "source_type", "source_url", "raw_content",
        "content_hash", "captured_at", "publish_datetime", "subject_scope",
        "collection_metadata", "provider", "authenticity_score", "created_at",
    })

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        init_db(self.db_path)

    def add_evidence(
        self,
        *,
        source_type: str,
        source_url: str,
        raw_content: str,
        source_id: str = "",
        captured_at: str = "",
        publish_datetime: Optional[str] = None,
        subject_scope: str = "CTH",
        task_id: str = "",
        trace_id: str = "",
        collection_metadata: Optional[Dict[str, Any]] = None,
        provider: str = "rule",
        dedupe_by_source: bool = False,
        authenticity_score: float = 1.0,
        domain_id: str = "",
        product_id: str = "",
        evaluation_id: str = "",
        final_decision: str = "",
        rule_id: str = "",
        ai_call_id: str = "",
    ) -> Tuple[Evidence, bool]:
        """添加一条证据。

        Returns:
            (Evidence, is_new) —— is_new=True 表示新插入，False 表示 hash 命中已有记录
        """
        content_hash = compute_content_hash(raw_content)
        captured_at = captured_at or _now()
        # ZBC V2.0 双域隔离：默认从线程上下文解析域身份
        if not domain_id or not product_id:
            try:
                from ai_domain_context import get_current_domain, product_id_to_domain
                from subject_context import get_subject_context
                _ctx = get_subject_context()
                if not domain_id:
                    domain_id = get_current_domain()
                if not product_id:
                    product_id = _ctx.product_id
            except ImportError:
                domain_id = domain_id or "cth"
                product_id = product_id or "CTH"

        conn = _get_conn(self.db_path)
        try:
            # 默认保持历史上的全局内容哈希去重；采集入口可按来源身份收窄，
            # 避免不同笔记恰好同文时复用首条 Evidence、丢失后续 source/provider。
            if dedupe_by_source:
                existing = conn.execute(
                    "SELECT * FROM zbc_evidence WHERE content_hash = ? AND source_type = ? "
                    "AND source_id = ? AND source_url = ? AND provider = ? "
                    "AND subject_scope = ? AND domain_id = ? AND product_id = ? "
                    "ORDER BY created_at LIMIT 1",
                    (content_hash, str(source_type or "unknown"), str(source_id or ""),
                     str(source_url or ""), str(provider or "rule"),
                     str(subject_scope or "CTH"), str(domain_id or "cth"),
                     str(product_id or "CTH")),
                ).fetchone()
            else:
                existing = conn.execute(
                    "SELECT * FROM zbc_evidence WHERE content_hash = ?",
                    (content_hash,),
                ).fetchone()
            if existing:
                return Evidence.from_row(existing), False

            evidence_id = generate_evidence_id()
            ev = Evidence(
                evidence_id=evidence_id,
                source_type=source_type,
                source_url=source_url,
                source_id=source_id,
                raw_content=raw_content,
                content_hash=content_hash,
                captured_at=captured_at,
                publish_datetime=publish_datetime,
                subject_scope=subject_scope,
                task_id=task_id,
                trace_id=trace_id,
                collection_metadata=collection_metadata or {},
                provider=provider,
                authenticity_score=authenticity_score,
                domain_id=domain_id,
                product_id=product_id,
                evaluation_id=evaluation_id,
                final_decision=final_decision,
                rule_id=rule_id,
                ai_call_id=ai_call_id,
            )
            d = ev.to_dict()
            cols = ", ".join(d.keys())
            placeholders = ", ".join(["?"] * len(d))
            conn.execute(
                f"INSERT INTO zbc_evidence ({cols}) VALUES ({placeholders})",
                list(d.values()),
            )
            conn.commit()
            return ev, True
        finally:
            conn.close()

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        conn = _get_conn(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM zbc_evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
            return Evidence.from_row(row) if row else None
        finally:
            conn.close()

    def get_by_hash(self, content_hash: str) -> Optional[Evidence]:
        conn = _get_conn(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM zbc_evidence WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
            return Evidence.from_row(row) if row else None
        finally:
            conn.close()

    def list_evidence(
        self,
        *,
        source_type: str = "",
        subject_scope: str = "",
        domain_id: str = "",
        product_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Evidence]:
        conditions = []
        params: List[Any] = []
        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        if subject_scope:
            conditions.append("subject_scope = ?")
            params.append(subject_scope)
        if domain_id:
            conditions.append("domain_id = ?")
            params.append(domain_id)
        if product_id:
            conditions.append("product_id = ?")
            params.append(product_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM zbc_evidence{where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        conn = _get_conn(self.db_path)
        try:
            rows = conn.execute(sql, params).fetchall()
            return [Evidence.from_row(r) for r in rows]
        finally:
            conn.close()

    def count(self) -> int:
        conn = _get_conn(self.db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM zbc_evidence").fetchone()[0]
        finally:
            conn.close()

    def verify_immutability(self, evidence_id: str) -> Dict[str, Any]:
        """验证证据不可变性 —— 尝试 UPDATE 不可变字段应被拒绝。

        返回验证报告，不实际执行修改。
        """
        ev = self.get_evidence(evidence_id)
        if not ev:
            return {"valid": False, "error": "证据不存在"}
        return {
            "valid": True,
            "evidence_id": evidence_id,
            "content_hash": ev.content_hash,
            "immutable_fields": sorted(self.IMMUTABLE_FIELDS),
            "raw_content_length": len(ev.raw_content),
            "note": "Evidence 表所有字段写入后不可 UPDATE；如需修正请追加新 Evidence",
        }


# ============================================================
# CanonicalData Store —— AI 与人工分离，rule_version 追踪
# ============================================================
class CanonicalDataStore:
    """规范数据存储。

    核心约束：
      - ai_analysis 与 human_correction 为独立 JSON 字段，互不覆盖
      - rule_version 标记创建时规则版本，历史数据不被新规则静默改写
      - evidence_id FK 关联不可变原始证据
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        init_db(self.db_path)

    def create_canonical(
        self,
        *,
        evidence_id: str,
        normalized_content: str,
        subject_hit: bool = False,
        subject_keywords: Optional[List[str]] = None,
        sentiment: str = "neutral",
        risk_level: str = "low",
        engagement_metrics: Optional[Dict[str, Any]] = None,
        ai_analysis: Optional[Dict[str, Any]] = None,
        human_correction: Optional[Dict[str, Any]] = None,
        rule_version: str = RULE_VERSION,
    ) -> CanonicalData:
        """从 Evidence 创建 CanonicalData。

        rule_version 默认使用当前模块版本；调用方可显式传入以标记特定规则版本。
        """
        canonical_id = generate_canonical_id()
        cd = CanonicalData(
            canonical_id=canonical_id,
            evidence_id=evidence_id,
            normalized_content=normalized_content,
            subject_hit=subject_hit,
            subject_keywords=subject_keywords or [],
            sentiment=sentiment,
            risk_level=risk_level,
            engagement_metrics=engagement_metrics or {},
            rule_version=rule_version,
            ai_analysis=ai_analysis or {},
            human_correction=human_correction or {},
        )
        d = cd.to_dict()
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        conn = _get_conn(self.db_path)
        try:
            conn.execute(
                f"INSERT INTO zbc_canonical_data ({cols}) VALUES ({placeholders})",
                list(d.values()),
            )
            conn.commit()
            return cd
        finally:
            conn.close()

    def get_canonical(self, canonical_id: str) -> Optional[CanonicalData]:
        conn = _get_conn(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM zbc_canonical_data WHERE canonical_id = ?",
                (canonical_id,),
            ).fetchone()
            return CanonicalData.from_row(row) if row else None
        finally:
            conn.close()

    def get_by_evidence(self, evidence_id: str) -> List[CanonicalData]:
        conn = _get_conn(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM zbc_canonical_data WHERE evidence_id = ? ORDER BY created_at",
                (evidence_id,),
            ).fetchall()
            return [CanonicalData.from_row(r) for r in rows]
        finally:
            conn.close()

    def apply_human_correction(
        self,
        canonical_id: str,
        correction: Dict[str, Any],
        operator: str = "human",
    ) -> Optional[CanonicalData]:
        """应用人工修正 —— 只更新 human_correction 字段，不覆盖 ai_analysis。

        这是 AI 输出与人工判断分离的核心实现：
          - ai_analysis 保持 AI 原始输出不变
          - human_correction 记录人工最终判断
          - updated_at 更新
          - rule_version 不变（历史数据不被新规则静默改写）
        """
        conn = _get_conn(self.db_path)
        try:
            row = conn.execute(
                "SELECT human_correction FROM zbc_canonical_data WHERE canonical_id = ?",
                (canonical_id,),
            ).fetchone()
            if not row:
                return None
            existing = {}
            if row["human_correction"]:
                try:
                    existing = json.loads(row["human_correction"])
                except (json.JSONDecodeError, TypeError):
                    existing = {}
            # 合并修正（不覆盖 AI 输出），记录修正人和时间
            merged = {**existing, **correction}
            merged["_last_corrected_at"] = _now()
            merged["_corrected_by"] = operator
            merged_json = json.dumps(merged, ensure_ascii=False)
            conn.execute(
                "UPDATE zbc_canonical_data SET human_correction = ?, updated_at = ? "
                "WHERE canonical_id = ?",
                (merged_json, _now(), canonical_id),
            )
            conn.commit()
            return self.get_canonical(canonical_id)
        finally:
            conn.close()

    def update_ai_analysis(
        self,
        canonical_id: str,
        ai_output: Dict[str, Any],
    ) -> Optional[CanonicalData]:
        """更新 AI 分析 —— 只更新 ai_analysis 字段，不影响 human_correction。"""
        conn = _get_conn(self.db_path)
        try:
            row = conn.execute(
                "SELECT ai_analysis FROM zbc_canonical_data WHERE canonical_id = ?",
                (canonical_id,),
            ).fetchone()
            if not row:
                return None
            existing = {}
            if row["ai_analysis"]:
                try:
                    existing = json.loads(row["ai_analysis"])
                except (json.JSONDecodeError, TypeError):
                    existing = {}
            # 保留 AI 分析历史（版本化），不覆盖
            history = existing.get("_history", [])
            if existing:
                snapshot = {k: v for k, v in existing.items() if not k.startswith("_")}
                if snapshot:
                    history.append({"at": existing.get("_last_analyzed_at", ""), "data": snapshot})
            merged = {**ai_output, "_history": history[-20:], "_last_analyzed_at": _now()}
            merged_json = json.dumps(merged, ensure_ascii=False)
            conn.execute(
                "UPDATE zbc_canonical_data SET ai_analysis = ?, updated_at = ? "
                "WHERE canonical_id = ?",
                (merged_json, _now(), canonical_id),
            )
            conn.commit()
            return self.get_canonical(canonical_id)
        finally:
            conn.close()

    def list_by_rule_version(self, rule_version: str) -> List[CanonicalData]:
        """按 rule_version 列出 —— 用于验证历史数据不被新规则静默改写。"""
        conn = _get_conn(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM zbc_canonical_data WHERE rule_version = ? ORDER BY created_at",
                (rule_version,),
            ).fetchall()
            return [CanonicalData.from_row(r) for r in rows]
        finally:
            conn.close()

    def count(self) -> int:
        conn = _get_conn(self.db_path)
        try:
            return conn.execute("SELECT COUNT(*) FROM zbc_canonical_data").fetchone()[0]
        finally:
            conn.close()


# ============================================================
# 数据生命周期追踪
# ============================================================
class LifecycleTracker:
    """数据生命周期追踪器。

    记录每条数据在 13 个阶段中的流转：输入/输出/转换规则/规则版本/操作者。
    支持 trace_data_lineage(evidence_id) 返回完整生命周期。
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        init_db(self.db_path)

    def record_stage(
        self,
        *,
        evidence_id: str = "",
        canonical_id: str = "",
        stage: str,
        input_ref: str = "",
        output_ref: str = "",
        transform_rule: str = "",
        rule_version: str = RULE_VERSION,
        operator: str = "system",
        task_id: str = "",
        trace_id: str = "",
        evaluation_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """记录一个生命周期阶段。"""
        if stage not in LIFECYCLE_STAGES:
            raise ValueError(f"未知生命周期阶段: {stage}，有效阶段: {list(LIFECYCLE_STAGES.keys())}")
        tracking_id = "tr_" + uuid.uuid4().hex[:16]
        stage_order = LIFECYCLE_STAGES[stage]["order"]
        conn = _get_conn(self.db_path)
        try:
            conn.execute(
                """INSERT INTO zbc_lifecycle_tracking
                   (tracking_id, evidence_id, canonical_id, stage, stage_order,
                    input_ref, output_ref, transform_rule, rule_version, operator,
                    task_id, trace_id, evaluation_id, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tracking_id, evidence_id, canonical_id, stage, stage_order,
                    input_ref, output_ref, transform_rule, rule_version, operator,
                    task_id, trace_id, evaluation_id,
                    json.dumps(metadata or {}, ensure_ascii=False), _now(),
                ),
            )
            conn.commit()
            return tracking_id
        finally:
            conn.close()

    def trace_data_lineage(self, evidence_id: str) -> Dict[str, Any]:
        """追踪一条证据的完整数据生命周期。

        Returns:
            {
                "evidence_id": ...,
                "evidence": {...},
                "canonical_data": [...],
                "lifecycle_stages": [
                    {"stage": ..., "stage_order": ..., "input_ref": ...,
                     "output_ref": ..., "transform_rule": ..., "rule_version": ...,
                     "operator": ..., "metadata": ..., "created_at": ...},
                    ...
                ],
                "stage_summary": {stage_name: count, ...},
                "rule_versions": [...],
            }
        """
        conn = _get_conn(self.db_path)
        try:
            # 获取 Evidence
            ev_row = conn.execute(
                "SELECT * FROM zbc_evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
            evidence = dict(ev_row) if ev_row else None

            # 获取关联的 CanonicalData
            can_rows = conn.execute(
                "SELECT * FROM zbc_canonical_data WHERE evidence_id = ? ORDER BY created_at",
                (evidence_id,),
            ).fetchall()
            canonical_data = [dict(r) for r in can_rows]

            # 获取生命周期追踪
            track_rows = conn.execute(
                "SELECT * FROM zbc_lifecycle_tracking WHERE evidence_id = ? "
                "OR canonical_id IN (SELECT canonical_id FROM zbc_canonical_data WHERE evidence_id = ?) "
                "ORDER BY stage_order, created_at",
                (evidence_id, evidence_id),
            ).fetchall()

            lifecycle_stages = []
            stage_summary: Dict[str, int] = {}
            rule_versions = set()
            for r in track_rows:
                d = dict(r)
                meta = d.get("metadata", "{}")
                if isinstance(meta, str):
                    try:
                        d["metadata"] = json.loads(meta)
                    except (json.JSONDecodeError, TypeError):
                        d["metadata"] = {}
                lifecycle_stages.append(d)
                stage_summary[d["stage"]] = stage_summary.get(d["stage"], 0) + 1
                if d.get("rule_version"):
                    rule_versions.add(d["rule_version"])

            return {
                "evidence_id": evidence_id,
                "evidence": evidence,
                "canonical_data": canonical_data,
                "lifecycle_stages": lifecycle_stages,
                "stage_summary": stage_summary,
                "rule_versions": sorted(rule_versions),
                "total_stages_recorded": len(lifecycle_stages),
            }
        finally:
            conn.close()

    def get_stage_definition(self, stage: str) -> Optional[Dict[str, Any]]:
        return LIFECYCLE_STAGES.get(stage)

    def list_all_stages(self) -> List[Dict[str, Any]]:
        return [
            {"stage": name, **info}
            for name, info in sorted(LIFECYCLE_STAGES.items(), key=lambda x: x[1]["order"])
        ]


# ============================================================
# 统一门面 —— EvidenceChain
# ============================================================
class EvidenceChain:
    """证据链统一门面。

    封装 EvidenceStore + CanonicalDataStore + LifecycleTracker，
    提供端到端的证据→规范数据→生命周期追踪能力。
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or main_db_path()
        self.evidence_store = EvidenceStore(self.db_path)
        self.canonical_store = CanonicalDataStore(self.db_path)
        self.lifecycle = LifecycleTracker(self.db_path)

    def capture_and_canonicalize(
        self,
        *,
        source_type: str,
        source_url: str,
        raw_content: str,
        source_id: str = "",
        captured_at: Optional[str] = None,
        normalized_content: str = "",
        subject_hit: bool = False,
        subject_keywords: Optional[List[str]] = None,
        sentiment: str = "neutral",
        risk_level: str = "low",
        engagement_metrics: Optional[Dict[str, Any]] = None,
        ai_analysis: Optional[Dict[str, Any]] = None,
        publish_datetime: Optional[str] = None,
        subject_scope: str = "CTH",
        task_id: str = "",
        trace_id: str = "",
        evaluation_id: str = "",
        collection_metadata: Optional[Dict[str, Any]] = None,
        provider: str = "rule",
        dedupe_by_source: bool = False,
        rule_version: str = RULE_VERSION,
        domain_id: str = "",
        product_id: str = "",
        final_decision: str = "",
        rule_id: str = "",
        ai_call_id: str = "",
    ) -> Dict[str, Any]:
        """端到端：采集证据 → hash 去重 → 创建规范数据 → 记录生命周期。

        Returns:
            {
                "evidence": Evidence,
                "is_new_evidence": bool,
                "canonical": CanonicalData,
                "tracking_ids": [...],
            }
        """
        # 1. Evidence 阶段（含 hash 去重）
        ev, is_new = self.evidence_store.add_evidence(
            source_type=source_type,
            source_url=source_url,
            source_id=source_id,
            raw_content=raw_content,
            captured_at=captured_at or "",
            publish_datetime=publish_datetime,
            subject_scope=subject_scope,
            task_id=task_id,
            trace_id=trace_id,
            collection_metadata=collection_metadata,
            provider=provider,
            dedupe_by_source=dedupe_by_source,
            domain_id=domain_id,
            product_id=product_id,
            evaluation_id=evaluation_id,
            final_decision=final_decision,
            rule_id=rule_id,
            ai_call_id=ai_call_id,
        )
        tracking_ids = []
        tracking_ids.append(self.lifecycle.record_stage(
            evidence_id=ev.evidence_id,
            stage="EVIDENCE",
            input_ref=source_url,
            output_ref=ev.evidence_id,
            transform_rule=f"SHA256 hash + provenance capture (dedup by content_hash)",
            rule_version=rule_version,
            operator=provider,
            task_id=task_id,
            trace_id=trace_id,
            evaluation_id=evaluation_id,
            metadata={"is_new": is_new, "content_hash": ev.content_hash, "source_id": source_id},
        ))

        # 2. CanonicalData 阶段
        cd = self.canonical_store.create_canonical(
            evidence_id=ev.evidence_id,
            normalized_content=normalized_content or raw_content[:500],
            subject_hit=subject_hit,
            subject_keywords=subject_keywords,
            sentiment=sentiment,
            risk_level=risk_level,
            engagement_metrics=engagement_metrics,
            ai_analysis=ai_analysis,
            rule_version=rule_version,
        )
        tracking_ids.append(self.lifecycle.record_stage(
            evidence_id=ev.evidence_id,
            canonical_id=cd.canonical_id,
            stage="CANONICAL_DATA",
            input_ref=ev.evidence_id,
            output_ref=cd.canonical_id,
            transform_rule="normalize + subject_filter + sentiment/risk + engagement + rule_version tag",
            rule_version=rule_version,
            operator="system",
            task_id=task_id,
            trace_id=trace_id,
            evaluation_id=evaluation_id,
            metadata={"subject_hit": subject_hit, "sentiment": sentiment, "risk_level": risk_level},
        ))

        return {
            "evidence": ev,
            "is_new_evidence": is_new,
            "canonical": cd,
            "tracking_ids": tracking_ids,
            "task_id": task_id,
            "trace_id": trace_id,
            "evaluation_id": evaluation_id,
            "source_id": source_id,
        }

    def trace_lineage(self, evidence_id: str) -> Dict[str, Any]:
        return self.lifecycle.trace_data_lineage(evidence_id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "evidence_count": self.evidence_store.count(),
            "canonical_count": self.canonical_store.count(),
            "rule_version": RULE_VERSION,
            "lifecycle_stages": len(LIFECYCLE_STAGES),
        }


@lru_cache(maxsize=8)
def _note_lineage_chain(db_path: str) -> EvidenceChain:
    """每个数据库路径只初始化一次证据链 schema；采集批次内复用连接工厂。"""
    return EvidenceChain(db_path)


@lru_cache(maxsize=8)
def _note_canonical_data_module(db_path: str):
    """按数据库路径幂等准备现有 Canonical 表，避免每条笔记重复跑 DDL。"""
    import canonical_data as _canonical_data

    _canonical_data.ensure_canonical_table(db_path)
    return _canonical_data


def capture_note_lineage(
    note_data: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
    provider: str = "unknown",
    subject_scope: str = "CTH",
    domain_id: str = "cth",
    product_id: str = "CTH",
) -> Dict[str, Any]:
    """以现有 Evidence 与 Canonical 契约记录已入库笔记的可失败旁路。

    主业务 ``notes`` 写入由调用方先完成；本函数独立记录不可变来源证据、
    zbc canonical/lifecycle 和 ``canonical_data``。两侧分别容错，不能让
    任一旁路故障回滚主业务事实。来源范围去重保留不同笔记的 source/provider。
    """
    note = dict(note_data or {})
    source_id = str(note.get("note_id") or note.get("source_id") or "").strip()
    if not source_id:
        return {"ok": False, "errors": [{"stage": "validation", "error_type": "missing_source_id"}]}

    path = db_path or main_db_path()
    captured_at = str(note.get("captured_at") or note.get("collected_at") or _now())
    note["captured_at"] = captured_at
    title = str(note.get("title") or "").strip()
    content = str(note.get("content") or note.get("body") or "").strip()
    raw_content = " ".join(part for part in (title, content) if part)
    if not raw_content:
        return {"ok": False, "errors": [{"stage": "validation", "error_type": "missing_source_content"}]}

    source_url = str(note.get("url") or "")
    source_platform = str(note.get("source_platform") or "xhs")
    source_keyword = str(note.get("source_keyword") or note.get("keyword") or "")
    matched = note.get("matched_keywords") or []
    if isinstance(matched, str):
        matched = [item.strip() for item in matched.replace("，", ",").replace("、", ",").split(",") if item.strip()]
    elif not isinstance(matched, (list, tuple, set)):
        matched = []
    subject_keywords = [str(item).strip() for item in matched if str(item).strip()]
    if source_keyword and source_keyword not in subject_keywords:
        subject_keywords.append(source_keyword)

    collection_metadata = build_provenance_metadata(
        source_type="xhs_note",
        source_url=source_url,
        captured_at=captured_at,
        subject_scope=subject_scope,
        provider=provider,
        source_platform=source_platform,
        source_id=source_id,
        source_keyword=source_keyword,
        collector_version=str(note.get("collector_version") or ""),
    )
    result: Dict[str, Any] = {
        "ok": False,
        "source_id": source_id,
        "captured_at": captured_at,
        "evidence_id": "",
        "chain_canonical_id": "",
        "canonical_id": "",
        "canonical_action": "",
        "errors": [],
    }

    try:
        chain_result = _note_lineage_chain(path).capture_and_canonicalize(
            source_type="xhs_note",
            source_url=source_url,
            raw_content=raw_content,
            source_id=source_id,
            captured_at=captured_at,
            normalized_content=raw_content[:500],
            subject_hit=bool(note.get("is_taikoo_verified")),
            subject_keywords=subject_keywords,
            sentiment=str(note.get("sentiment") or "neutral"),
            risk_level=str(note.get("risk_level") or "low"),
            engagement_metrics={
                "likes": note.get("likes"),
                "comments": note.get("comments"),
                "collects": note.get("collects"),
                "shares": note.get("shares"),
            },
            publish_datetime=note.get("publish_datetime") or note.get("publish_date") or None,
            subject_scope=subject_scope,
            task_id=str(note.get("task_id") or ""),
            trace_id=str(note.get("trace_id") or ""),
            collection_metadata=collection_metadata,
            provider=provider,
            dedupe_by_source=True,
            domain_id=domain_id,
            product_id=product_id,
        )
        result["evidence_id"] = chain_result["evidence"].evidence_id
        result["chain_canonical_id"] = chain_result["canonical"].canonical_id
    except Exception as exc:
        result["errors"].append({"stage": "evidence_chain", "error_type": type(exc).__name__})

    try:
        _canonical_data = _note_canonical_data_module(path)
        record = _canonical_data.note_to_canonical(note, product_id=product_id)
        conn = _canonical_data.get_connection(path)
        try:
            result["canonical_action"] = _canonical_data.persist_canonical(conn, record)
            conn.commit()
        finally:
            conn.close()
        result["canonical_id"] = record.canonical_id
    except Exception as exc:
        result["errors"].append({"stage": "canonical_data", "error_type": type(exc).__name__})

    result["ok"] = bool(result["evidence_id"] and result["chain_canonical_id"] and result["canonical_id"] and not result["errors"])
    return result


# ============================================================
# 向后兼容适配 —— 现有模块增强（不修改原文件，提供适配函数）
# ============================================================
def adapt_evidence_store_hash(raw_content: str) -> str:
    """为现有 evidence_store 提供完整 SHA256 哈希适配。

    现有 evidence_store._evidence_hash 使用 16 字符截断哈希，
    此函数提供完整 64 字符 SHA256，可用于新字段 provenance_hash。
    """
    return compute_content_hash(raw_content)


def build_provenance_metadata(
    *,
    source_type: str,
    source_url: str,
    captured_at: str,
    subject_scope: str = "CTH",
    provider: str = "rule",
    **extra: Any,
) -> Dict[str, Any]:
    """构建标准 provenance 元数据，供现有模块补充 collection_metadata 字段。"""
    meta = {
        "source_type": source_type,
        "source_url": source_url,
        "captured_at": captured_at,
        "subject_scope": subject_scope,
        "provider": provider,
        "schema_version": "evidence-chain-v1.0.0",
    }
    meta.update(extra)
    return meta


# ============================================================
# 模块导出
# ============================================================
__all__ = [
    "Evidence",
    "CanonicalData",
    "EvidenceStore",
    "CanonicalDataStore",
    "LifecycleTracker",
    "EvidenceChain",
    "capture_note_lineage",
    "LIFECYCLE_STAGES",
    "RULE_VERSION",
    "compute_content_hash",
    "generate_evidence_id",
    "generate_canonical_id",
    "init_db",
    "adapt_evidence_store_hash",
    "build_provenance_metadata",
]


# ============================================================
# ZBC V2.0 双域证据查询便捷函数
# ============================================================
def list_evidence_by_domain(
    db_path: str = None,
    domain_id: str = "cth",
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """按域查询证据（CTH 和 ZBMP 证据存储在同一表但 domain_id 区分）。

    默认按当前域过滤，禁止跨域混查。
    """
    store = EvidenceStore(db_path)
    evidence_list = store.list_evidence(domain_id=domain_id, limit=limit, offset=offset)
    return [
        {
            "evidence_id": ev.evidence_id,
            "domain_id": ev.domain_id,
            "product_id": ev.product_id,
            "source_type": ev.source_type,
            "source_id": ev.source_id,
            "task_id": ev.task_id,
            "trace_id": ev.trace_id,
            "evaluation_id": ev.evaluation_id,
            "final_decision": ev.final_decision,
            "rule_id": ev.rule_id,
            "ai_call_id": ev.ai_call_id,
            "content_hash": ev.content_hash,
            "captured_at": ev.captured_at,
            "subject_scope": ev.subject_scope,
        }
        for ev in evidence_list
    ]


def get_evidence_domain_summary(db_path: str = None) -> Dict[str, Any]:
    """获取证据按域分布的统计（用于审计验证域隔离）。"""
    store = EvidenceStore(db_path)
    conn = _get_conn(store.db_path)
    try:
        rows = conn.execute(
            "SELECT domain_id, product_id, COUNT(*) as cnt FROM zbc_evidence "
            "GROUP BY domain_id, product_id ORDER BY cnt DESC"
        ).fetchall()
        return {
            "by_domain": [dict(r) for r in rows],
            "total": store.count(),
            "domains_present": sorted(set(r["domain_id"] for r in rows)),
            "isolation_note": "CTH and ZBMP evidence share table but are separated by domain_id field",
        }
    finally:
        conn.close()