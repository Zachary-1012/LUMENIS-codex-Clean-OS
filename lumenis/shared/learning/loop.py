# -*- coding: utf-8 -*-
"""LUMENIS Shared Learning Loop — 反馈→规则→prompt 影响链路。

核心链路：
  用户对AI输出的修正 → 记录到 Learning Memory → 沉淀为规则建议
  → 写入 rule_version_registry（需人工确认）→ 影响后续AI调用的prompt context

  AI输出人工确认/拒绝 → 记录带类型的原始样本
  → 经过现有生命周期晋级后才进入可消费样本库

安全约束：
  - 学习结果不直接成为 Production Truth；样本必须走完现有生命周期
  - 复用 ai_call_logs（1587行）做调用质量分析
  - 复用 rule_version_registry 做规则版本管理
  - 默认不启用，通过 Feature Flag 控制

与 OSAI learning_record_contract.py 的 LearningLoop 对齐。
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import fsum, isfinite
from typing import Any, Dict, List, Optional, Tuple

from agent_memory.base import get_db_connection, _utc_now_iso
from .memory import (
    LearningMemory, LearningType, LifecycleStage, SampleType,
)

logger = logging.getLogger(__name__)


@dataclass
class RuleSuggestion:
    """规则建议（学习沉淀的中间产物，不直接成为 Production Truth）。"""
    suggestion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    source: str = "lumenis.shared.learning.loop"
    rule_type: str = ""                  # subject_words / exclude_words / risk / sentiment
    suggestion_text: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    learning_record_id: Optional[str] = None
    status: str = "proposed"             # proposed / approved / rejected / applied
    created_at: str = field(default_factory=_utc_now_iso)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    schema_version: int = 1
    revision: int = 1
    applied_version: Optional[str] = None
    approved_content_sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "source": self.source,
            "rule_type": self.rule_type,
            "suggestion_text": self.suggestion_text,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "learning_record_id": self.learning_record_id,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "schema_version": self.schema_version,
            "revision": self.revision,
            "applied_version": self.applied_version,
            "approved_content_sha256": self.approved_content_sha256,
        }


class LearningLoop:
    """学习闭环引擎。

    职责：
      1. 接收用户反馈/AI修正 → 写入 Learning Memory
      2. 从学习记录中提取规则建议 → 人工确认后写入 rule_version_registry
      3. 管理正/负样本库
      4. 分析 ai_call_logs 调用质量 → 生成优化建议
      5. 为 AI 调用生成 prompt context（注入已验证的规则和样本）
    """

    def __init__(self, db_path: Optional[str] = None, enabled: bool = False,
                 learning_memory: Optional[LearningMemory] = None):
        self.db_path = db_path
        self.enabled = enabled
        self.learning_memory = learning_memory or LearningMemory(
            db_path=db_path, enabled=enabled)
        self._rule_suggestions: List[RuleSuggestion] = []
        self._prompt_context_cache: Optional[str] = None

    def bind_source_task(self, task_id, actor_id):
        self.learning_memory.bind_source_task(task_id, actor_id)
        return self

    def build_reviewed_research_context(self, candidate_ids, *, actor, actor_id, expected_scope):
        """Revalidate selected adopted research references, without invoking AI.

        The Gateway still owns exact model consent and source-use admission.
        Disabled learning does not block ordinary deterministic business work.
        """
        if not self.enabled:
            return {"state": "disabled", "references": []}
        from .contribution import build_reviewed_context
        return build_reviewed_context(candidate_ids, actor=actor, actor_id=actor_id,
                                      expected_scope=expected_scope)

    # ── 反馈入口 ─────────────────────────────────────────────────

    def record_user_feedback(self, feedback_text: str,
                             context: Optional[Dict[str, Any]] = None,
                             related_task_id: Optional[str] = None) -> Optional[str]:
        """记录用户反馈 → Learning Memory。

        Returns:
            learning record_id，失败返回 None
        """
        if not self.enabled:
            return None
        rec = self.learning_memory.record_feedback(
            feedback_text=feedback_text,
            context=context,
            source="user",
            related_task_id=related_task_id,
        )
        if rec:
            logger.info("LearningLoop: user feedback recorded %s", rec.record_id)
        return rec.record_id if rec else None

    def record_ai_correction(self, original_output: str, corrected_output: str,
                             context: Optional[Dict[str, Any]] = None,
                             related_task_id: Optional[str] = None,
                             accepted: bool = True) -> Optional[str]:
        """记录 AI 输出修正 → Learning Memory + 样本库。

        Args:
            accepted: True=人工确认（正样本），False=被拒绝（负样本）
        """
        if not self.enabled:
            return None
        rec = self.learning_memory.record_correction(
            original_output=original_output,
            corrected_output=corrected_output,
            context=context,
            source="human",
            related_task_id=related_task_id,
            sample_type=(
                SampleType.POSITIVE if accepted else SampleType.NEGATIVE
            ),
        )
        return rec.record_id if rec else None

    # ── 规则沉淀 ─────────────────────────────────────────────────

    def generate_rule_suggestion(self, learning_type: str,
                                 content: Dict[str, Any],
                                 rule_type: str = "general",
                                 confidence: float = 0.5) -> Optional[RuleSuggestion]:
        """从学习记录中生成规则建议（不直接写入生产规则）。

        规则建议需要人工确认后才能写入 rule_version_registry。
        """
        if not self.enabled:
            return None
        suggestion = RuleSuggestion(
            rule_type=rule_type,
            suggestion_text=json.dumps(content, ensure_ascii=False, allow_nan=False),
            evidence={"learning_type": learning_type, "content": content},
            confidence=confidence,
        )
        learning_record = self.learning_memory.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content=suggestion.to_dict(), source="lumenis.shared.learning.loop",
            confidence=confidence, lifecycle_stage=LifecycleStage.RAW)
        if not learning_record:
            return None
        suggestion.learning_record_id = learning_record.record_id
        if self.db_path:
            # The configured DB owner must confirm persistence, never silently
            # replace a failed write with process memory.
            persisted = self._read_suggestions()
            found = next((item for item in persisted if item.suggestion_id == suggestion.suggestion_id), None)
            if found is None:
                return None
            self._rule_suggestions = persisted
            return found
        self._rule_suggestions.append(suggestion)
        return suggestion

    @staticmethod
    def _decode_suggestion(row):
        try:
            data = json.loads(row["content_json"] or "{}")
            if data.get("schema_version") != 1 or type(data.get("revision")) is not int:
                return None
            fields = RuleSuggestion.__dataclass_fields__
            item = RuleSuggestion(**{key: value for key, value in data.items() if key in fields})
            item.learning_record_id = row["record_id"]
            # Lifecycle is a second persisted constraint, not a cached approval.
            expected = {"proposed": "raw", "approved": "reviewed", "applied": "validated", "rejected": "archived"}
            if expected.get(item.status) != row["lifecycle_stage"]:
                return None
            return item
        except (ValueError, TypeError, KeyError):
            return None

    def _read_suggestions(self, connection=None):
        if not self.enabled:
            return []
        if not self.db_path:
            return list(self._rule_suggestions)
        conn = connection or get_db_connection(self.db_path)
        try:
            rows = conn.execute("SELECT * FROM agent_learning_records "
                                "WHERE learning_type=? ORDER BY created_at,record_id",
                                (LearningType.RULE_SUGGESTION.value,)).fetchall()
            return [item for row in rows if self.learning_memory._row_visible(row, conn)
                    and (item := self._decode_suggestion(row)) is not None]
        finally:
            if connection is None:
                conn.close()

    @staticmethod
    def _suggestion_hash(item):
        import hashlib
        content = item.to_dict()
        material = {key: content[key] for key in (
            "suggestion_id", "source", "rule_type", "suggestion_text", "evidence", "confidence", "created_at")}
        return hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False,
            allow_nan=False, separators=(",", ":")).encode()).hexdigest()

    def _save_suggestion(self, conn, suggestion, stage, previous_revision):
        payload = json.dumps(suggestion.to_dict(), ensure_ascii=False, allow_nan=False)
        row = conn.execute("SELECT metadata_json FROM agent_learning_records WHERE record_id=?", (suggestion.learning_record_id,)).fetchone()
        metadata = json.loads(row["metadata_json"] or "{}") if row else {}
        admission = getattr(self.learning_memory, "_review_admission", None)
        transition = {"from_revision": previous_revision, "to_revision": suggestion.revision,
            "status": suggestion.status, "actor_ref": suggestion.reviewed_by,
            "recorded_at": _utc_now_iso(), "active_policy_changed": False}
        if admission is not None:
            transition.update(candidate_ref=admission.resource, action=admission.action, approved=admission.approved)
        metadata["transitions"] = [*metadata.get("transitions", []), transition]
        metadata_payload = json.dumps(metadata, ensure_ascii=False, allow_nan=False)
        if len(payload.encode()) + len(metadata_payload.encode()) > 8 * 1024 * 1024:
            raise ValueError("LEARNING_CONTENT_TOO_LARGE")
        changed = conn.execute("UPDATE agent_learning_records SET content_json=?,lifecycle_stage=?,metadata_json=? "
            "WHERE record_id=? AND json_extract(content_json,'$.revision')=?",
            (payload, stage, metadata_payload, suggestion.learning_record_id, previous_revision)).rowcount
        if changed != 1:
            raise RuntimeError("LEARNING_SUGGESTION_REVISION_CONFLICT")

    def review_rule_suggestion(self, suggestion_id: str, approved: bool,
                               reviewer: str = "human", *, expected_revision=None) -> bool:
        if not self.enabled or not reviewer:
            return False
        if not self.db_path:
            for item in self._rule_suggestions:
                if item.suggestion_id == suggestion_id and item.status in ("proposed", "approved"):
                    if expected_revision is not None and item.revision != expected_revision:
                        return False
                    item.approved_content_sha256 = self._suggestion_hash(item) if approved else None
                    item.status = "approved" if approved else "rejected"
                    item.reviewed_by, item.reviewed_at = reviewer, _utc_now_iso()
                    item.revision += 1
                    return True
            return False
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            binding = self.learning_memory._scoped_check(connection=conn, write=True, review=True)
            if binding is not None:
                reviewer = "workspace:local" if binding["actor_id"] is None else "actor:" + str(binding["actor_id"])
            item = next((s for s in self._read_suggestions(conn) if s.suggestion_id == suggestion_id), None)
            if not item or (expected_revision is not None and item.revision != expected_revision):
                return False
            if item.status not in ("proposed", "approved", "applied") or (approved and item.status == "applied"):
                return False
            if item.status == "applied":
                version = conn.execute("SELECT is_active FROM rule_version_registry WHERE version=?", (item.applied_version,)).fetchone()
                if not version or version["is_active"] != 0:
                    # Activated rules belong to the existing rule rollback owner.
                    return False
            previous = item.revision
            item.approved_content_sha256 = self._suggestion_hash(item) if approved else None
            item.status = "approved" if approved else "rejected"
            item.reviewed_by, item.reviewed_at = reviewer, _utc_now_iso()
            item.revision += 1
            self._save_suggestion(conn, item, "reviewed" if approved else "archived", previous)
            self.learning_memory._scoped_check(connection=conn, write=True, review=True, after_write=True)
            admission = getattr(self.learning_memory, "_review_admission", None)
            if admission is not None:
                from lumenis.system.security.permission import get_permission_gate
                with get_permission_gate().learning_candidate_commit_lease(admission, connection=conn):
                    conn.commit()
            else:
                conn.commit()
            try:
                self._rule_suggestions = self._read_suggestions()
            except Exception:
                self._rule_suggestions = []  # Cache failure cannot undo a confirmed commit.
            return True
        except Exception:
            conn.rollback()
            logger.exception("Learning suggestion review did not commit")
            if getattr(self.learning_memory, "_scope_owner", None) is not None:
                raise
            return False
        finally:
            conn.close()

    def apply_approved_rule(self, suggestion_id: str,
                            applied_by: str = "human", *, expected_revision=None) -> bool:
        """Atomically create one inactive candidate and advance its learning row.

        This cannot activate a rule or promote training. Approval must still be
        current when the write transaction holds its existing DB reservation.
        """
        if not self.enabled or not self.db_path or not applied_by:
            return False
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            binding = self.learning_memory._scoped_check(connection=conn, write=True, review=True)
            if binding is not None:
                applied_by = "workspace:local" if binding["actor_id"] is None else "actor:" + str(binding["actor_id"])
            item = next((s for s in self._read_suggestions(conn) if s.suggestion_id == suggestion_id), None)
            if not item or (expected_revision is not None and item.revision != expected_revision):
                return False
            if item.approved_content_sha256 != self._suggestion_hash(item):
                return False
            if item.status == "applied":
                row = conn.execute("SELECT is_active,changelog FROM rule_version_registry WHERE version=?", (item.applied_version,)).fetchone()
                return bool(row and row["is_active"] == 0 and json.loads(row["changelog"])["suggestion_id"] == suggestion_id)
            if item.status != "approved":
                return False
            current = conn.execute("SELECT subject_words_count,exclude_words_count FROM rule_version_registry WHERE is_active=1 LIMIT 1").fetchone()
            previous = item.revision
            item.status, item.applied_version = "applied", "learning_" + item.suggestion_id
            item.revision += 1
            conn.execute("""INSERT INTO rule_version_registry
                (version,rule_type,description,subject_words_count,exclude_words_count,
                 subject_words_hash,exclude_words_hash,applied_at,applied_by,is_active,changelog)
                VALUES(?,?,?,?,?,?,?,?,?,0,?)""", (
                item.applied_version, item.rule_type, "Learning Loop candidate: " + item.suggestion_text[:200],
                current["subject_words_count"] if current else 0,
                current["exclude_words_count"] if current else 0, "", "", _utc_now_iso(), applied_by,
                json.dumps(item.to_dict(), ensure_ascii=False, allow_nan=False)))
            self._save_suggestion(conn, item, "validated", previous)
            self.learning_memory._scoped_check(connection=conn, write=True, review=True, after_write=True)
            admission = getattr(self.learning_memory, "_review_admission", None)
            if admission is not None:
                from lumenis.system.security.permission import get_permission_gate
                with get_permission_gate().learning_candidate_commit_lease(admission, connection=conn):
                    conn.commit()
            else:
                conn.commit()
            try:
                self._rule_suggestions = self._read_suggestions()
            except Exception:
                self._rule_suggestions = []  # Cache failure cannot undo a confirmed commit.
            return True
        except Exception:
            conn.rollback()
            logger.exception("Learning inactive candidate did not commit")
            if getattr(self.learning_memory, "_scope_owner", None) is not None:
                raise
            return False
        finally:
            conn.close()

    def list_rule_suggestions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            self._rule_suggestions = self._read_suggestions()
            return [s.to_dict() for s in self._rule_suggestions if status is None or s.status == status]
        except Exception:
            return []

    # ── AI 调用质量分析（复用 ai_call_logs） ─────────────────────

    def analyze_call_quality(self, days: int = 7,
                             provider: Optional[str] = None) -> Dict[str, Any]:
        """分析 ai_call_logs 的调用质量。

        返回调用数、可计算的成功率/延迟和失败原因分布。
        修正记录可计数；因未记录复核分母，修正率保持未知。
        每个数值指标单独报告有效/未知样本数；缺失值不会变成零。
        """
        if not self.enabled or not self.db_path:
            return {"enabled": False}
        try:
            conn = get_db_connection(self.db_path)
            try:
                # Parse stored ISO-8601 timestamps before comparing. Comparing
                # the raw text against SQLite's space-separated datetime can
                # include records just outside the requested window because
                # the ISO ``T`` separator sorts after a space.
                sql = "SELECT * FROM ai_call_logs WHERE datetime(created_at) >= datetime('now', ?)"
                params = [f"-{days} days"]
                if provider:
                    sql += " AND provider=?"
                    params.append(provider)
                rows = conn.execute(sql, params).fetchall()

                total = len(rows)
                success_samples = []
                latency_samples = []
                latency_zero_samples = 0
                corrections = 0
                failure_reasons: Dict[str, int] = {}
                for r in rows:
                    success_value = r["success"]
                    if type(success_value) is int and success_value in (0, 1):
                        success_samples.append(success_value)
                        if success_value == 0:
                            reason = r["failure_reason"]
                            if type(reason) is str and reason:
                                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

                    correction_value = r["human_correction"]
                    if type(correction_value) is str and correction_value:
                        corrections += 1

                    latency_value = r["latency_ms"]
                    if (type(latency_value) in (int, float)
                            and isfinite(latency_value) and latency_value >= 0):
                        if latency_value == 0:
                            latency_zero_samples += 1
                        else:
                            latency_samples.append(latency_value)

                success = sum(value == 1 for value in success_samples)

                def sample_status(valid_count: int) -> Dict[str, Any]:
                    unknown_count = total - valid_count
                    if total == 0:
                        state = "no_data"
                    elif valid_count == 0:
                        state = "unknown"
                    elif unknown_count:
                        state = "partial"
                    else:
                        state = "available"
                    return {
                        "state": state,
                        "valid_samples": valid_count,
                        "unknown_samples": unknown_count,
                    }

                success_rate = (round(success / len(success_samples), 4)
                                if success_samples else None)
                # The field stores corrections but has no explicit reviewed /
                # not-reviewed state. Its denominator is therefore unknown.
                correction_rate = None
                avg_latency = (
                    round(fsum(value / len(latency_samples) for value in latency_samples), 2)
                    if latency_samples else None
                )
                latency_sample_status = sample_status(len(latency_samples))
                latency_sample_status.update({
                    "zero_value_samples": latency_zero_samples,
                    "zero_value_provenance": (
                        "unresolved_legacy_default_or_measured_zero"
                        if latency_zero_samples else "no_zero_values"
                    ),
                })

                return {
                    "period_days": days,
                    "total_calls": total,
                    "success_count": success,
                    "success_rate": success_rate,
                    "human_correction_count": corrections,
                    "human_correction_rate": correction_rate,
                    "avg_latency_ms": avg_latency,
                    "failure_reasons": failure_reasons,
                    "provider_filter": provider,
                    "metric_definitions": {
                        "human_correction_rate": {
                            "numerator": "calls_with_nonempty_human_correction",
                            "denominator": "reviewed_calls_not_recorded",
                            "meaning": (
                                "rate is unavailable because the reviewed-call denominator "
                                "is not recorded; the numerator is an observed correction count"
                            ),
                        },
                    },
                    "human_correction_state": "REVIEW_DENOMINATOR_NOT_RECORDED",
                    "human_review_coverage": {
                        "state": "unknown",
                        "reviewed_calls": None,
                        "coverage_rate": None,
                    },
                    "metric_samples": {
                        "success_rate": sample_status(len(success_samples)),
                        "human_correction_rate": {
                            "state": "no_data" if total == 0 else "unknown",
                            "valid_samples": 0,
                            "unknown_samples": total,
                            "observed_corrections": corrections,
                            "denominator_state": "REVIEWED_CALLS_NOT_RECORDED",
                        },
                        "avg_latency_ms": latency_sample_status,
                    },
                }
            finally:
                conn.close()
        except Exception as e:
            logger.error("LearningLoop: analyze_call_quality failed: %s", e)
            return {"error": str(e)}

    # ── Prompt Context 生成 ──────────────────────────────────────

    def build_prompt_context(self, task_type: str = "general",
                             max_rules: int = 5,
                             max_samples: int = 3) -> str:
        """为 AI 调用生成学习上下文（注入已验证的规则和样本）。

        只注入 lifecycle_stage=promoted 的规则和正样本，
        不注入 raw/reviewed 阶段的未验证内容。
        """
        if not self.enabled:
            return ""
        parts: List[str] = []

        # 1. 已提升的规则
        promoted_rules = self.learning_memory.get_promoted_rules()[:max_rules]
        if promoted_rules:
            parts.append("【已验证学习规则】")
            for r in promoted_rules:
                content = r.get("content", {})
                text = content.get("suggestion_text", str(content))[:200]
                parts.append(f"- {text}")

        # 2. 正样本（few-shot）
        positive = self.learning_memory.get_positive_samples(limit=max_samples)
        if positive:
            parts.append("\n【参考正样本】")
            for i, s in enumerate(positive, 1):
                corrected = str(s.get("corrected", ""))[:150]
                parts.append(f"{i}. {corrected}")

        # 3. 反馈关键词（高频）
        keywords = ([] if getattr(self.learning_memory, "_scope_owner", None) is not None
                    else self.learning_memory.list_feedback_keywords(enabled_only=True)[:10])
        if keywords:
            parts.append("\n【关注关键词】")
            kw_text = ", ".join(k["keyword"] for k in keywords)
            parts.append(kw_text)

        context = "\n".join(parts)
        self._prompt_context_cache = context
        return context

    # ── 全链路：反馈→规则→prompt ─────────────────────────────────

    def run_learning_cycle(self, feedback_text: str,
                           original_output: str = "",
                           corrected_output: str = "",
                           context: Optional[Dict[str, Any]] = None,
                           ) -> Dict[str, Any]:
        """执行一次完整的学习闭环。

        流程：反馈记录 → 规则建议生成 → prompt context 更新
        （规则建议不自动应用，需人工 review + apply）
        """
        if not self.enabled:
            return {"enabled": False}

        result: Dict[str, Any] = {"cycle_id": uuid.uuid4().hex[:12]}

        # 1. 记录反馈
        fb_id = self.record_user_feedback(
            feedback_text=feedback_text, context=context)
        result["feedback_record_id"] = fb_id

        # 2. 如果有修正，记录修正
        if original_output and corrected_output:
            corr_id = self.record_ai_correction(
                original_output=original_output,
                corrected_output=corrected_output,
                context=context,
                accepted=True,
            )
            result["correction_record_id"] = corr_id

            # 3. 生成规则建议（低置信度，需人工确认）
            suggestion = self.generate_rule_suggestion(
                learning_type="correction",
                content={
                    "feedback": feedback_text,
                    "original": original_output[:200],
                    "corrected": corrected_output[:200],
                },
                rule_type="general",
                confidence=0.4,  # 自动生成的建议置信度低
            )
            if suggestion:
                result["rule_suggestion_id"] = suggestion.suggestion_id
                result["rule_suggestion_status"] = "proposed (requires human review)"

        # 4. 更新 prompt context
        result["prompt_context_updated"] = bool(self.build_prompt_context())

        return result

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "rule_suggestions_total": len(self._rule_suggestions),
            "rule_suggestions_approved": sum(
                1 for s in self._rule_suggestions if s.status == "approved"),
            "learning_memory_stats": self.learning_memory.stats(),
        }
