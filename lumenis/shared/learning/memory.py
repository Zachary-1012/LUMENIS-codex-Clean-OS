# -*- coding: utf-8 -*-
"""LUMENIS Shared Learning Memory — 用户反馈、修正记录、规则沉淀。

存储：复用 feedback_keywords 表（16行）+ 新建 agent_learning_records 表（迁移脚本，不执行）
能力：用户修正 → 沉淀为规则/样本 → 影响后续 AI prompt
与 OSAI learning_record_contract.py 的 LearningRecord 对齐。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from agent_memory.base import BaseMemoryLayer, MemoryRecord, get_db_connection, _utc_now_iso


class LearningType(str, Enum):
    FEEDBACK = "feedback"           # 用户反馈
    CORRECTION = "correction"       # AI输出修正
    OUTCOME = "outcome"             # 执行结果
    PATTERN = "pattern"             # 模式识别
    RULE_SUGGESTION = "rule_suggestion"  # 规则建议


class LifecycleStage(str, Enum):
    RAW = "raw"                     # 原始记录
    REVIEWED = "reviewed"           # 已审核
    VALIDATED = "validated"         # 已验证
    PROMOTED = "promoted"           # 已提升为规则/样本
    ARCHIVED = "archived"           # 已归档


class SampleType(str, Enum):
    POSITIVE = "positive"           # 正样本（人工确认）
    NEGATIVE = "negative"           # 负样本（被拒绝）
    NEUTRAL = "neutral"             # 中性样本


class LearningMemory(BaseMemoryLayer):
    """学习记忆：用户反馈 + AI修正 + 规则沉淀。

    两个数据源：
      1. feedback_keywords — 反馈关键词（16条，含启用状态和使用计数）
      2. agent_learning_records — 学习记录表（迁移脚本定义，默认不创建）
    """

    LAYER_NAME = "learning"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False):
        super().__init__(db_path=db_path, enabled=enabled)

    # ── 反馈关键词（基于 feedback_keywords） ─────────────────────

    def list_feedback_keywords(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出反馈关键词。"""
        if not self.enabled or not self.db_path:
            return []
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM feedback_keywords"
                if enabled_only:
                    sql += " WHERE enabled=1"
                sql += " ORDER BY used_count DESC"
                rows = conn.execute(sql).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def get_feedback_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        """获取单个反馈关键词。"""
        if not self.enabled or not self.db_path:
            return None
        try:
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute(
                    "SELECT * FROM feedback_keywords WHERE keyword=?", (keyword,)
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except Exception:
            return None

    # ── 学习记录（内存 + 可选 agent_learning_records 表） ────────

    def record_learning(self, learning_type: LearningType,
                        content: Dict[str, Any],
                        source: str = "agent_runtime",
                        confidence: float = 0.5,
                        related_task_id: Optional[str] = None,
                        lifecycle_stage: LifecycleStage = LifecycleStage.RAW,
                        ) -> Optional[MemoryRecord]:
        """记录一条学习记忆。

        学习结果不直接成为 Production Truth，lifecycle_stage 初始为 raw，
        需经过 reviewed → validated → promoted 才能影响生产。
        """
        record_data = {
            "learning_type": learning_type.value,
            "content": content,
            "source": source,
            "confidence": confidence,
            "related_task_id": related_task_id,
            "lifecycle_stage": lifecycle_stage.value,
            "recorded_at": _utc_now_iso(),
        }
        rec = self.store(
            key=f"learning:{uuid.uuid4().hex[:12]}",
            value=record_data,
            metadata={
                "type": "learning_record",
                "learning_type": learning_type.value,
                "lifecycle_stage": lifecycle_stage.value,
            },
        )
        # 持久化到 agent_learning_records 表（如果表已存在）
        if rec and self.db_path is not None:
            self._persist_learning_record(rec, record_data)
        return rec

    def record_feedback(self, feedback_text: str,
                        context: Optional[Dict[str, Any]] = None,
                        source: str = "user",
                        related_task_id: Optional[str] = None) -> Optional[MemoryRecord]:
        """记录用户反馈。"""
        return self.record_learning(
            learning_type=LearningType.FEEDBACK,
            content={"feedback_text": feedback_text, "context": context or {}},
            source=source,
            confidence=0.8,  # 用户反馈置信度较高
            related_task_id=related_task_id,
        )

    def record_correction(self, original_output: str, corrected_output: str,
                          context: Optional[Dict[str, Any]] = None,
                          source: str = "human",
                          related_task_id: Optional[str] = None,
                          sample_type: Optional[SampleType] = None) -> Optional[MemoryRecord]:
        """记录 AI 输出修正（original → corrected 的 diff）。"""
        content = {
            "original_output": original_output,
            "corrected_output": corrected_output,
            "context": context or {},
        }
        if sample_type is not None:
            content["sample_type"] = sample_type.value
        return self.record_learning(
            learning_type=LearningType.CORRECTION,
            content=content,
            source=source,
            confidence=0.9,  # 人工修正置信度高
            related_task_id=related_task_id,
        )

    # ── 样本库管理 ───────────────────────────────────────────────

    def add_positive_sample(self, sample: Dict[str, Any]) -> bool:
        """记录候选正样本；只有该记录经生命周期提升后才可读取。"""
        if not self.enabled:
            return False
        return self._record_sample(sample, SampleType.POSITIVE) is not None

    def add_negative_sample(self, sample: Dict[str, Any]) -> bool:
        """记录候选负样本；只有该记录经生命周期提升后才可读取。"""
        if not self.enabled:
            return False
        return self._record_sample(sample, SampleType.NEGATIVE) is not None

    def _record_sample(self, sample: Dict[str, Any],
                       sample_type: SampleType) -> Optional[MemoryRecord]:
        payload = dict(sample)
        content = {
            "sample_type": sample_type.value,
            "sample": payload,
            "original_output": payload.get("original", payload.get("original_output", "")),
            "corrected_output": payload.get("corrected", payload.get("corrected_output", "")),
            "context": payload.get("context") or {},
        }
        return self.record_learning(
            learning_type=LearningType.CORRECTION,
            content=content,
            source="learning_sample_api",
            confidence=0.9,
        )

    def get_positive_samples(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._get_promoted_samples(SampleType.POSITIVE, limit)

    def get_negative_samples(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._get_promoted_samples(SampleType.NEGATIVE, limit)

    def _get_promoted_samples(self, sample_type: SampleType,
                              limit: int) -> List[Dict[str, Any]]:
        """Read only promoted samples from the configured lifecycle authority."""
        if not self.enabled or limit <= 0:
            return []

        records: Dict[str, Dict[str, Any]] = {}
        if self.db_path is not None:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    rows = conn.execute(
                        """SELECT record_id, content_json, lifecycle_stage, created_at
                           FROM agent_learning_records
                           WHERE learning_type=? AND lifecycle_stage=?
                           ORDER BY created_at DESC""",
                        (LearningType.CORRECTION.value, LifecycleStage.PROMOTED.value),
                    )
                    for row in rows:
                        try:
                            content = json.loads(row["content_json"] or "{}")
                        except (TypeError, json.JSONDecodeError):
                            continue
                        if not isinstance(content, dict):
                            continue
                        if content.get("sample_type") != sample_type.value:
                            continue
                        records[row["record_id"]] = self._sample_from_content(
                            row["record_id"], content, row["created_at"])
                finally:
                    conn.close()
            except Exception:
                # A configured persistence owner is authoritative. A read
                # failure must not revive a stale promoted in-memory copy.
                return []
            return list(reversed(list(records.values())[:limit]))

        # Memory-only operation is explicit: it is available only when no DB
        # owner was configured for this LearningMemory instance.
        for record in self._in_memory.values():
            value = record.value
            if value.get("learning_type") != LearningType.CORRECTION.value:
                continue
            if value.get("lifecycle_stage") != LifecycleStage.PROMOTED.value:
                continue
            if value.get("content", {}).get("sample_type") != sample_type.value:
                continue
            records.setdefault(
                record.record_id,
                self._sample_from_content(
                    record.record_id, value.get("content", {}), record.timestamp),
            )

        ordered = sorted(
            records.values(), key=lambda item: item.get("recorded_at", ""))
        return ordered[-limit:]

    @staticmethod
    def _sample_from_content(record_id: str, content: Dict[str, Any],
                             recorded_at: Optional[str]) -> Dict[str, Any]:
        sample = content.get("sample")
        if not isinstance(sample, dict):
            sample = {
                "original": content.get("original_output", ""),
                "corrected": content.get("corrected_output", ""),
                "context": content.get("context") or {},
            }
        else:
            sample = dict(sample)
        sample.update({
            "sample_type": content.get("sample_type"),
            "learning_record_id": record_id,
            "lifecycle_stage": LifecycleStage.PROMOTED.value,
            "recorded_at": recorded_at,
        })
        return sample

    # ── 生命周期推进 ─────────────────────────────────────────────

    def promote_record(self, record_id: str,
                       new_stage: LifecycleStage) -> bool:
        """推进学习记录生命周期，并同步持久化状态。

        合法链路：
          raw → reviewed → validated → promoted → archived

        archived 也可作为任一非终态的人工拒绝/收口终点。
        只有 promoted 阶段的记录才能进入 prompt context 或影响后续规则使用。
        """
        rec = next((r for r in self._in_memory.values()
                    if r.record_id == record_id), None)

        allowed = {
            LifecycleStage.RAW.value: {
                LifecycleStage.REVIEWED.value,
                LifecycleStage.ARCHIVED.value,
            },
            LifecycleStage.REVIEWED.value: {
                LifecycleStage.VALIDATED.value,
                LifecycleStage.ARCHIVED.value,
            },
            LifecycleStage.VALIDATED.value: {
                LifecycleStage.PROMOTED.value,
                LifecycleStage.ARCHIVED.value,
            },
            LifecycleStage.PROMOTED.value: {
                LifecycleStage.ARCHIVED.value,
            },
            LifecycleStage.ARCHIVED.value: set(),
        }

        if self.db_path is not None:
            conn = None
            try:
                conn = get_db_connection(self.db_path)
                row = conn.execute(
                    "SELECT lifecycle_stage FROM agent_learning_records WHERE record_id=?",
                    (record_id,),
                ).fetchone()
                if not row:
                    return False
                current_stage = row["lifecycle_stage"]
                if current_stage == new_stage.value:
                    if rec:
                        rec.value["lifecycle_stage"] = current_stage
                        rec.metadata["lifecycle_stage"] = current_stage
                    return True
                if new_stage.value not in allowed.get(current_stage, set()):
                    return False
                updated = conn.execute(
                    """UPDATE agent_learning_records SET lifecycle_stage=?
                       WHERE record_id=? AND lifecycle_stage=?""",
                    (new_stage.value, record_id, current_stage),
                )
                if updated.rowcount != 1:
                    return False
                conn.commit()
            except Exception:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                return False
            finally:
                if conn:
                    conn.close()

            if rec:
                rec.value["lifecycle_stage"] = new_stage.value
                rec.metadata["lifecycle_stage"] = new_stage.value
            return True

        # Without a configured DB, only this explicit in-memory owner may
        # advance records; no persisted record is inferred from a stale cache.
        if not rec:
            return False
        current_stage = rec.value.get("lifecycle_stage", LifecycleStage.RAW.value)
        if current_stage == new_stage.value:
            return True
        if new_stage.value not in allowed.get(current_stage, set()):
            return False

        rec.value["lifecycle_stage"] = new_stage.value
        rec.metadata["lifecycle_stage"] = new_stage.value

        return True

    def get_promoted_rules(self) -> List[Dict[str, Any]]:
        """获取已提升规则；优先读取持久化记录，保证重启后仍可追溯。"""
        if not self.enabled:
            return []

        if self.db_path is not None:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    rows = conn.execute(
                        """SELECT record_id, learning_type, source, content_json,
                                  confidence, lifecycle_stage, related_task_id, created_at
                           FROM agent_learning_records
                           WHERE learning_type=? AND lifecycle_stage=?
                           ORDER BY created_at DESC LIMIT 100""",
                        (LearningType.RULE_SUGGESTION.value, LifecycleStage.PROMOTED.value),
                    )
                    persisted = []
                    for row in rows:
                        try:
                            content = json.loads(row["content_json"] or "{}")
                        except (TypeError, json.JSONDecodeError):
                            continue
                        if not isinstance(content, dict):
                            continue
                        persisted.append({
                            "record_id": row["record_id"],
                            "learning_type": row["learning_type"],
                            "content": content,
                            "source": row["source"],
                            "confidence": row["confidence"],
                            "related_task_id": row["related_task_id"],
                            "lifecycle_stage": row["lifecycle_stage"],
                            "recorded_at": row["created_at"],
                        })
                finally:
                    conn.close()
                return persisted
            except Exception:
                # Do not revive a cached promotion when the configured
                # persistence owner cannot establish current lifecycle state.
                return []

        results = self.query({"learning_type": "rule_suggestion"}, limit=100)
        return [
            r.value for r in results
            if r.value.get("lifecycle_stage") == LifecycleStage.PROMOTED.value
        ]

    # ── 持久化（agent_learning_records 表，迁移脚本定义） ────────

    def _persist_learning_record(self, rec: MemoryRecord,
                                 data: Dict[str, Any]) -> None:
        """尝试写入 agent_learning_records 表（表不存在时静默跳过）。"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO agent_learning_records
                       (record_id, learning_type, source, content_json, confidence,
                        lifecycle_stage, related_task_id, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        rec.record_id,
                        data["learning_type"],
                        data["source"],
                        json.dumps(data["content"], ensure_ascii=False, default=str)[:4000],
                        data["confidence"],
                        data["lifecycle_stage"],
                        data.get("related_task_id"),
                        data["recorded_at"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass  # 表不存在时静默跳过（迁移脚本未执行）

    def stats(self) -> Dict[str, Any]:
        s = super().stats()
        if self.db_path:
            try:
                conn = get_db_connection(self.db_path)
                try:
                    fk = conn.execute("SELECT COUNT(*) FROM feedback_keywords").fetchone()[0]
                    s["feedback_keywords_total"] = fk
                finally:
                    conn.close()
            except Exception:
                pass
        s["positive_samples"] = len(self.get_positive_samples())
        s["negative_samples"] = len(self.get_negative_samples())
        return s
