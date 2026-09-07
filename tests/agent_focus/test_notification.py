# -*- coding: utf-8 -*-
"""
Unit tests for agent_focus.notification & policy
覆盖：SILENT不通知、IMPORTANT通知、HUMAN_DECISION必须通知、
重复事件抑制、频率限制、静默期、事件分类、策略加载、路由
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_focus.notification import (
    FocusProtector, NotificationRouter, NotificationEvent,
    NotificationLevel, should_notify,
)
from agent_focus.policy import (
    FocusPolicy, QuietHours, default_policy, load_policy,
)


@pytest.fixture
def protector():
    p = FocusProtector()
    yield p
    p.reset_rate_limits()


@pytest.fixture
def router():
    r = NotificationRouter()
    yield r
    r.clear_history()
    r.protector.reset_rate_limits()


class TestNotificationLevel:
    def test_level_values(self):
        assert NotificationLevel.SILENT_PROGRESS.value == "silent_progress"
        assert NotificationLevel.IMPORTANT_SIGNAL.value == "important_signal"
        assert NotificationLevel.HUMAN_DECISION.value == "human_decision"


class TestSilentProgress:
    def test_silent_does_not_notify(self, protector):
        """SILENT_PROGRESS 默认不通知。"""
        event = {"source": "collector", "event_type": "progress",
                 "title": "采集进度 50%"}
        assert protector.should_notify(
            NotificationLevel.SILENT_PROGRESS, event
        ) is False

    def test_silent_even_high_freq(self, protector):
        """SILENT 不受频率控制影响，始终不通知。"""
        for _ in range(100):
            assert protector.should_notify(
                NotificationLevel.SILENT_PROGRESS, {}
            ) is False


class TestImportantSignal:
    def test_important_notifies(self, protector):
        """IMPORTANT_SIGNAL 正常通知。"""
        event = {"source": "risk_engine", "event_type": "anomaly",
                 "title": "CPU 异常"}
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, event
        ) is True

    def test_important_silent_source_suppressed(self, protector):
        """IMPORTANT 但来源是静默来源时被抑制。"""
        event = {"source": "heartbeat", "event_type": "anomaly",
                 "title": "心跳异常"}
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, event
        ) is False


class TestHumanDecision:
    def test_decision_always_notifies(self, protector):
        """HUMAN_DECISION 必须通知，不可抑制。"""
        event = {"source": "any", "event_type": "anything",
                 "title": "需要审批"}
        assert protector.should_notify(
            NotificationLevel.HUMAN_DECISION, event
        ) is True

    def test_decision_passes_silent_source(self, protector):
        """HUMAN_DECISION 即使来源是静默来源也必须通知。"""
        event = {"source": "heartbeat", "event_type": "approval_required",
                 "title": "审批"}
        assert protector.should_notify(
            NotificationLevel.HUMAN_DECISION, event
        ) is True

    def test_decision_passes_rate_limit(self, protector):
        """HUMAN_DECISION 不受频率限制。"""
        event = {"source": "x", "event_type": "approval_required"}
        for _ in range(50):
            assert protector.should_notify(
                NotificationLevel.HUMAN_DECISION, event
            ) is True

    def test_decision_passes_quiet_hours(self, protector):
        """HUMAN_DECISION 在静默期也必须通知。"""
        policy = FocusPolicy()
        policy.quiet_hours = QuietHours(enabled=True, start_hour=0, end_hour=23)
        protector.update_policy(policy)
        event = {"source": "x", "event_type": "approval_required"}
        assert protector.should_notify(
            NotificationLevel.HUMAN_DECISION, event
        ) is True


class TestDuplicateSuppression:
    def test_duplicate_suppressed(self, protector):
        """重复事件在窗口内被抑制。"""
        event = {"source": "risk", "event_type": "anomaly",
                 "title": "CPU 95%"}
        # 第一次通知
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, event
        ) is True
        # 第二次（重复）被抑制
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, event
        ) is False

    def test_different_title_not_duplicate(self, protector):
        """不同标题不算重复。"""
        e1 = {"source": "risk", "event_type": "anomaly", "title": "CPU 95%"}
        e2 = {"source": "risk", "event_type": "anomaly", "title": "内存 90%"}
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, e1
        ) is True
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, e2
        ) is True


class TestRateLimit:
    def test_rate_limit_blocks_excess(self, protector):
        """超过每分钟最大通知数后被限流。"""
        policy = FocusPolicy(max_notifications_per_minute=2)
        protector.update_policy(policy)
        event_base = {"source": "collector", "event_type": "anomaly"}

        results = []
        for i in range(5):
            evt = dict(event_base, title=f"事件{i}")
            results.append(
                protector.should_notify(
                    NotificationLevel.IMPORTANT_SIGNAL, evt
                )
            )
        # 前2个通过，后3个被限流
        assert results[0] is True
        assert results[1] is True
        assert results[2] is False
        assert results[3] is False
        assert results[4] is False


class TestQuietHours:
    def test_quiet_hours_suppresses_important(self, protector):
        """静默期内 IMPORTANT 被抑制。"""
        policy = FocusPolicy()
        # 设为全天静默
        policy.quiet_hours = QuietHours(enabled=True, start_hour=0, end_hour=23)
        protector.update_policy(policy)
        event = {"source": "risk", "event_type": "anomaly", "title": "x"}
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, event
        ) is False

    def test_quiet_hours_disabled_allows(self, protector):
        """静默期关闭时正常通知。"""
        policy = FocusPolicy()
        policy.quiet_hours = QuietHours(enabled=False)
        protector.update_policy(policy)
        event = {"source": "risk", "event_type": "anomaly", "title": "x"}
        assert protector.should_notify(
            NotificationLevel.IMPORTANT_SIGNAL, event
        ) is True

    def test_quiet_hours_is_quiet_now(self):
        qh = QuietHours(enabled=True, start_hour=22, end_hour=8)
        assert qh.is_quiet_now(hour=23) is True
        assert qh.is_quiet_now(hour=2) is True
        assert qh.is_quiet_now(hour=12) is False
        qh2 = QuietHours(enabled=True, start_hour=9, end_hour=17)
        assert qh2.is_quiet_now(hour=10) is True
        assert qh2.is_quiet_now(hour=20) is False


class TestEventClassification:
    def test_classify_decision_event(self, protector):
        event = {"event_type": "approval_required"}
        assert protector.classify_event(event) == NotificationLevel.HUMAN_DECISION

    def test_classify_important_event(self, protector):
        event = {"event_type": "anomaly"}
        assert protector.classify_event(event) == NotificationLevel.IMPORTANT_SIGNAL

    def test_classify_silent_source(self, protector):
        event = {"source": "heartbeat", "event_type": "unknown"}
        assert protector.classify_event(event) == NotificationLevel.SILENT_PROGRESS

    def test_classify_requires_action(self, protector):
        event = {"event_type": "custom", "requires_action": True}
        assert protector.classify_event(event) == NotificationLevel.HUMAN_DECISION

    def test_classify_default_silent(self, protector):
        event = {"source": "unknown", "event_type": "unknown"}
        assert protector.classify_event(event) == NotificationLevel.SILENT_PROGRESS

    def test_classify_explicit_level(self, protector):
        event = {"level": "human_decision", "event_type": "anything"}
        assert protector.classify_event(event) == NotificationLevel.HUMAN_DECISION


class TestPolicyLoading:
    def test_default_policy(self):
        p = default_policy()
        assert isinstance(p, FocusPolicy)
        assert p.max_notifications_per_minute > 0
        assert len(p.silent_sources) > 0

    def test_load_policy_custom(self):
        config = {
            "silent_sources": ["custom_silent"],
            "important_event_types": ["custom_important"],
            "decision_event_types": ["custom_decision"],
            "max_notifications_per_minute": 10,
            "quiet_hours": {"enabled": True, "start_hour": 23, "end_hour": 7},
        }
        p = load_policy(config)
        assert p.silent_sources == ["custom_silent"]
        assert p.important_event_types == ["custom_important"]
        assert p.decision_event_types == ["custom_decision"]
        assert p.max_notifications_per_minute == 10
        assert p.quiet_hours.enabled is True
        assert p.quiet_hours.start_hour == 23

    def test_load_policy_none_returns_default(self):
        p = load_policy(None)
        assert p.max_notifications_per_minute == default_policy().max_notifications_per_minute

    def test_load_policy_empty_returns_default(self):
        p = load_policy({})
        assert isinstance(p, FocusPolicy)


class TestNotificationRouter:
    def test_route_silent_writes_log(self, router):
        event = NotificationEvent(
            level=NotificationLevel.SILENT_PROGRESS.value,
            title="进度", source="collector", event_type="progress",
        )
        result = router.route(event)
        assert result is False
        history = router.get_routed_history()
        assert history[-1]["channel"] == "silent"

    def test_route_important_toast(self, router):
        toast_calls = []
        router._toast_sink = lambda e: toast_calls.append(e)
        event = NotificationEvent(
            level=NotificationLevel.IMPORTANT_SIGNAL.value,
            title="异常", source="risk", event_type="anomaly",
        )
        result = router.route(event)
        assert result is True
        assert len(toast_calls) == 1
        assert router.get_routed_history()[-1]["channel"] == "toast"

    def test_route_decision_modal(self, router):
        modal_calls = []
        router._modal_sink = lambda e: modal_calls.append(e)
        event = NotificationEvent(
            level=NotificationLevel.HUMAN_DECISION.value,
            title="审批", source="any", event_type="approval_required",
        )
        result = router.route(event)
        assert result is True
        assert len(modal_calls) == 1
        assert router.get_routed_history()[-1]["channel"] == "modal"

    def test_route_from_dict_auto_classify(self, router):
        result = router.route_from_dict({
            "source": "risk", "event_type": "anomaly",
            "title": "CPU异常", "message": "CPU 95%",
        })
        assert result is True

    def test_route_from_dict_silent(self, router):
        result = router.route_from_dict({
            "source": "heartbeat", "event_type": "tick",
            "title": "心跳",
        })
        assert result is False


class TestModuleLevelFunction:
    def test_should_notify_silent_string(self):
        assert should_notify("silent_progress", {}) is False

    def test_should_notify_decision_string(self):
        assert should_notify("human_decision", {}) is True
