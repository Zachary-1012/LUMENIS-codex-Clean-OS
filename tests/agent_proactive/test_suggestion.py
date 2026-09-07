# -*- coding: utf-8 -*-
"""
Unit tests for agent_proactive.suggestion
覆盖：建议生成、审批流程、默认不自动执行、回滚计划、
批量生成、严重度映射、审批状态转换
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_proactive.detector import Signal, SignalType, SignalSeverity
from agent_proactive.suggestion import (
    SuggestionGenerator, SuggestedAction, ApprovalFlow,
    ActionType, ApprovalStatus, RiskLevel, generate_suggestion,
)


@pytest.fixture
def generator():
    return SuggestionGenerator()


def _make_signal(
    signal_type=SignalType.ANOMALY,
    severity=SignalSeverity.WARNING,
    title="测试信号",
):
    return Signal(
        signal_type=signal_type.value,
        severity=severity.value,
        source="test",
        title=title,
        description="测试描述",
        evidence_refs=["ref1", "ref2"],
    )


class TestSuggestedActionDataclass:
    def test_default_action_type_require_approval(self):
        action = SuggestedAction(title="t")
        assert action.action_type == ActionType.REQUIRE_APPROVAL.value

    def test_default_approval_pending(self):
        action = SuggestedAction(title="t")
        assert action.approval_status == ApprovalStatus.PENDING.value

    def test_not_auto_executable_by_default(self):
        action = SuggestedAction(title="t")
        assert action.is_auto_executable is False


class TestSuggestionGeneration:
    def test_generate_basic(self, generator):
        sig = _make_signal()
        action = generator.generate_suggestion(sig)
        assert action.title
        assert action.description
        assert action.signal_id == sig.signal_id
        assert action.signal_type == sig.signal_type

    def test_default_require_approval(self, generator):
        """硬约束：action_type 默认 require_approval，不得默认 auto_execute。"""
        sig = _make_signal(severity=SignalSeverity.CRITICAL)
        action = generator.generate_suggestion(sig)
        assert action.action_type == ActionType.REQUIRE_APPROVAL.value

    def test_info_low_risk_notify(self, generator):
        sig = _make_signal(
            signal_type=SignalType.BETTER_PATH,
            severity=SignalSeverity.INFO,
        )
        action = generator.generate_suggestion(sig)
        # INFO + LOW 可设为 notify，但仍不是 auto_execute
        assert action.action_type in (
            ActionType.NOTIFY.value, ActionType.REQUIRE_APPROVAL.value
        )
        assert action.action_type != ActionType.AUTO_EXECUTE.value

    def test_rollback_plan_present(self, generator):
        """硬约束：每个 SuggestedAction 必须携带 rollback_plan。"""
        for st in SignalType:
            sig = _make_signal(signal_type=st)
            action = generator.generate_suggestion(sig)
            assert action.rollback_plan, f"Missing rollback_plan for {st}"

    def test_evidence_refs_preserved(self, generator):
        sig = _make_signal()
        action = generator.generate_suggestion(sig)
        assert action.evidence_refs == ["ref1", "ref2"]

    def test_critical_signal_high_risk(self, generator):
        sig = _make_signal(severity=SignalSeverity.CRITICAL)
        action = generator.generate_suggestion(sig)
        assert action.risk_level == RiskLevel.HIGH.value

    def test_expires_at_set(self, generator):
        sig = _make_signal()
        action = generator.generate_suggestion(sig)
        assert action.expires_at

    def test_unknown_signal_type_fallback(self, generator):
        sig = Signal(signal_type="unknown_type", severity="warning",
                     source="test", title="未知")
        action = generator.generate_suggestion(sig)
        assert action.title
        assert action.rollback_plan


class TestBatchGeneration:
    def test_generate_batch(self, generator):
        signals = [
            _make_signal(signal_type=SignalType.ANOMALY),
            _make_signal(signal_type=SignalType.RISK_ESCALATION),
            _make_signal(signal_type=SignalType.DATA_MISSING),
        ]
        actions = generator.generate_batch(signals)
        assert len(actions) == 3
        for a in actions:
            assert a.action_type == ActionType.REQUIRE_APPROVAL.value
            assert a.rollback_plan


class TestApprovalFlow:
    def test_approve(self):
        action = SuggestedAction(title="t")
        flow = ApprovalFlow(action)
        result = flow.approve(approver="admin", note="ok")
        assert result == ApprovalStatus.APPROVED
        assert action.approval_status == ApprovalStatus.APPROVED.value
        assert action.approved_by == "admin"

    def test_reject(self):
        action = SuggestedAction(title="t")
        flow = ApprovalFlow(action)
        result = flow.reject(reason="风险过高", rejecter="user")
        assert result == ApprovalStatus.REJECTED
        assert action.rejected_reason == "风险过高"

    def test_expire(self):
        action = SuggestedAction(title="t")
        flow = ApprovalFlow(action)
        result = flow.expire()
        assert result == ApprovalStatus.EXPIRED

    def test_cannot_approve_after_reject(self):
        action = SuggestedAction(title="t")
        flow = ApprovalFlow(action)
        flow.reject(reason="no")
        with pytest.raises(ValueError):
            flow.approve()

    def test_cannot_reject_after_approve(self):
        action = SuggestedAction(title="t")
        flow = ApprovalFlow(action)
        flow.approve()
        with pytest.raises(ValueError):
            flow.reject()

    def test_history_recorded(self):
        action = SuggestedAction(title="t")
        flow = ApprovalFlow(action)
        flow.approve(approver="a")
        history = flow.history()
        assert len(history) >= 1
        assert history[0]["action"] == "approve"

    def test_check_expiry_not_expired(self):
        from datetime import datetime, timezone, timedelta
        action = SuggestedAction(title="t")
        action.expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()
        flow = ApprovalFlow(action)
        assert flow.check_expiry() is False

    def test_check_expiry_expired(self):
        from datetime import datetime, timezone, timedelta
        action = SuggestedAction(title="t")
        action.expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        flow = ApprovalFlow(action)
        assert flow.check_expiry() is True
        assert flow.status == ApprovalStatus.EXPIRED


class TestModuleLevelFunction:
    def test_generate_suggestion_fn(self):
        sig = _make_signal()
        action = generate_suggestion(sig)
        assert action.action_type == ActionType.REQUIRE_APPROVAL.value
        assert action.rollback_plan
