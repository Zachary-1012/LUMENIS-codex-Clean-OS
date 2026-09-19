# -*- coding: utf-8 -*-
"""LUMENIS Shared Learning Loop — 反馈→规则→prompt 影响链路。

核心链路：
  用户对AI输出的修正 → 记录到 Learning Memory → 沉淀为规则建议
  → 写入 rule_version_registry（需人工确认）→ 影响后续AI调用的prompt context

  AI输出人工确认 → 标记为 verified sample → 进入正样本库
  AI输出被拒绝 → 标记为 negative sample → 进入负样本库

安全约束：
  - 学习结果不直接成为 Production Truth，需规则验证或人工确认
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
        )
        if rec:
            sample = {
                "original": original_output,
                "corrected": corrected_output,
                "context": context or {},
                "related_task_id": related_task_id,
                "learning_record_id": rec.record_id,
            }
            if accepted:
                self.learning_memory.add_positive_sample(sample)
            else:
                self.learning_memory.add_negative_sample(sample)
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
            suggestion_text=json.dumps(content, ensure_ascii=False)[:500],
            evidence={"learning_type": learning_type, "content": content},
            confidence=confidence,
        )
        # 同时记录到 Learning Memory，并保存真实 record_id 作为治理关联键。
        learning_record = self.learning_memory.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={
                "suggestion_id": suggestion.suggestion_id,
                "rule_type": rule_type,
                "suggestion_text": suggestion.suggestion_text,
                "confidence": confidence,
            },
            source="lumenis.shared.learning.loop",
            confidence=confidence,
            lifecycle_stage=LifecycleStage.RAW,
        )
        if learning_record:
            suggestion.learning_record_id = learning_record.record_id
        self._rule_suggestions.append(suggestion)
        return suggestion

    def review_rule_suggestion(self, suggestion_id: str, approved: bool,
                               reviewer: str = "human") -> bool:
        """人工审核规则建议。

        approved=True → status=approved → 可写入 rule_version_registry
        approved=False → status=rejected
        """
        for s in self._rule_suggestions:
            if s.suggestion_id == suggestion_id:
                s.status = "approved" if approved else "rejected"
                s.reviewed_by = reviewer
                s.reviewed_at = _utc_now_iso()
                if s.learning_record_id:
                    target_stage = (
                        LifecycleStage.REVIEWED if approved
                        else LifecycleStage.ARCHIVED
                    )
                    self.learning_memory.promote_record(
                        s.learning_record_id, target_stage)
                return True
        return False

    def apply_approved_rule(self, suggestion_id: str,
                            applied_by: str = "human") -> bool:
        """将已批准的规则建议写入 rule_version_registry（需人工触发）。

        安全约束：只有 status=approved 的建议才能写入，且写入后 is_active=0
        （不自动激活，需额外人工激活步骤）。
        """
        if not self.enabled or not self.db_path:
            return False
        suggestion = next((s for s in self._rule_suggestions
                           if s.suggestion_id == suggestion_id), None)
        if not suggestion or suggestion.status != "approved":
            return False

        try:
            conn = get_db_connection(self.db_path)
            try:
                # 获取当前活跃版本的计数作为基线
                current = conn.execute(
                    "SELECT subject_words_count, exclude_words_count FROM rule_version_registry WHERE is_active=1 LIMIT 1"
                ).fetchone()
                sw_count = current["subject_words_count"] if current else 0
                ew_count = current["exclude_words_count"] if current else 0

                new_version = f"learning_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                conn.execute(
                    """INSERT INTO rule_version_registry
                       (version, rule_type, description, subject_words_count,
                        exclude_words_count, subject_words_hash, exclude_words_hash,
                        applied_at, applied_by, is_active, changelog)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        new_version,
                        suggestion.rule_type,
                        f"Learning Loop auto-suggestion: {suggestion.suggestion_text[:200]}",
                        sw_count, ew_count,
                        "", "",  # 哈希需人工计算后补充
                        _utc_now_iso(),
                        applied_by,
                        0,  # 不自动激活
                        json.dumps(suggestion.to_dict(), ensure_ascii=False)[:1000],
                    ),
                )
                conn.commit()
                suggestion.status = "applied"
                # 写入的是 inactive 候选版本，只能推进到 validated；
                # promoted 必须由后续显式激活/治理步骤完成。
                if suggestion.learning_record_id:
                    self.learning_memory.promote_record(
                        suggestion.learning_record_id, LifecycleStage.VALIDATED)
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error("LearningLoop: apply_approved_rule failed: %s", e)
            return False

    def list_rule_suggestions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出规则建议。"""
        results = [s.to_dict() for s in self._rule_suggestions]
        if status:
            results = [s for s in results if s["status"] == status]
        return results

    # ── AI 调用质量分析（复用 ai_call_logs） ─────────────────────

    def analyze_call_quality(self, days: int = 7,
                             provider: Optional[str] = None) -> Dict[str, Any]:
        """分析 ai_call_logs 的调用质量。

        维度：总调用数、成功率、平均延迟、人审修正率、失败原因分布。
        """
        if not self.enabled or not self.db_path:
            return {"enabled": False}
        try:
            conn = get_db_connection(self.db_path)
            try:
                sql = "SELECT * FROM ai_call_logs WHERE created_at >= datetime('now', ?)"
                params = [f"-{days} days"]
                if provider:
                    sql += " AND provider=?"
                    params.append(provider)
                rows = conn.execute(sql, params).fetchall()

                total = len(rows)
                success = sum(1 for r in rows if r["success"])
                corrections = sum(1 for r in rows if r["human_correction"])
                avg_latency = (sum(r["latency_ms"] or 0 for r in rows) / total
                               if total > 0 else 0)
                failure_reasons: Dict[str, int] = {}
                for r in rows:
                    if not r["success"] and r["failure_reason"]:
                        fr = r["failure_reason"]
                        failure_reasons[fr] = failure_reasons.get(fr, 0) + 1

                return {
                    "period_days": days,
                    "total_calls": total,
                    "success_count": success,
                    "success_rate": round(success / total, 4) if total > 0 else 0.0,
                    "human_correction_count": corrections,
                    "human_correction_rate": round(corrections / total, 4) if total > 0 else 0.0,
                    "avg_latency_ms": round(avg_latency, 2),
                    "failure_reasons": failure_reasons,
                    "provider_filter": provider,
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
        keywords = self.learning_memory.list_feedback_keywords(enabled_only=True)[:10]
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
