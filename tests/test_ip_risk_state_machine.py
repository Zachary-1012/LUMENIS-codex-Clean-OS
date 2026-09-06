# -*- coding: utf-8 -*-
"""IP 风控状态机 单元测试（PROJECT_STATUS P0 项 4）

验证：
1. 5 态状态机（NORMAL/WATCH/SUSPENDED/BLOCKED/COOLDOWN）
2. 状态转换规则（风控信号驱动、成功驱动恢复）
3. 熔断机制（连续风控达到阈值触发 BLOCKED）
4. 冷却机制（COOLDOWN 倒计时、半开探测）
5. 告警机制（状态变更告警、BLOCKED 告警）
6. 持久化（SQLite 存储、重启恢复）
7. 硬红线：BLOCKED 必须人工解除、禁止伪造成功
"""
import sys
import os
import tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试隔离。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    old_env = os.environ.get("ZBC_DB_PATH")
    os.environ["ZBC_DB_PATH"] = path
    # 重置单例
    import ip_risk_state_machine as ipm
    ipm.IPRiskStateMachine._instance = None
    yield path
    if old_env:
        os.environ["ZBC_DB_PATH"] = old_env
    else:
        os.environ.pop("ZBC_DB_PATH", None)
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sm(temp_db):
    """创建状态机实例。"""
    from ip_risk_state_machine import IPRiskStateMachine, IPRiskConfig
    config = IPRiskConfig(
        watch_threshold=2,
        suspend_threshold=4,
        block_threshold=6,
        recovery_threshold=3,
        cooldown_duration=60,  # 测试用短冷却
        db_path=temp_db,
    )
    return IPRiskStateMachine(config)


class TestStateTransitions:
    """状态转换测试。"""

    def test_initial_state_is_normal(self, sm):
        from ip_risk_state_machine import IPRiskState
        assert sm.get_state("xiaohongshu") == IPRiskState.NORMAL

    def test_normal_to_watch_after_risk_signals(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, "第一次300012")
        assert sm.get_state("xiaohongshu") == IPRiskState.NORMAL  # 1次还在NORMAL
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, "第二次300012")
        assert sm.get_state("xiaohongshu") == IPRiskState.WATCH  # 2次进入WATCH

    def test_watch_to_suspended_after_more_signals(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"第{i+1}次验证码")
        assert sm.get_state("xiaohongshu") == IPRiskState.SUSPENDED

    def test_watch_to_blocked_after_threshold(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(6):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.IP_LIMITED, f"第{i+1}次IP限制")
        assert sm.get_state("xiaohongshu") == IPRiskState.BLOCKED

    def test_watch_recovery_after_successes(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        # 进入 WATCH
        for i in range(2):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        assert sm.get_state("xiaohongshu") == IPRiskState.WATCH
        # 连续成功恢复
        for i in range(3):
            sm.record_success("xiaohongshu")
        assert sm.get_state("xiaohongshu") == IPRiskState.NORMAL

    def test_suspended_to_cooldown_on_continued_risk(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        assert sm.get_state("xiaohongshu") == IPRiskState.SUSPENDED
        # SUSPENDED 期间再次风控（未达 block_threshold=6）
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, "暂停期间再次风控")
        assert sm.get_state("xiaohongshu") == IPRiskState.COOLDOWN

    def test_cooldown_to_blocked_on_continued_risk(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        # 进入 COOLDOWN
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, "暂停期间风控")
        assert sm.get_state("xiaohongshu") == IPRiskState.COOLDOWN
        # 冷却期间再次风控 → BLOCKED
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, "冷却期间风控")
        assert sm.get_state("xiaohongshu") == IPRiskState.BLOCKED


class TestCircuitBreaker:
    """熔断机制测试。"""

    def test_blocked_cannot_collect(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(6):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        assert sm.is_blocked("xiaohongshu") is True
        assert sm.can_collect("xiaohongshu") is False

    def test_suspended_cannot_collect(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        assert sm.can_collect("xiaohongshu") is False

    def test_watch_can_collect(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(2):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        assert sm.can_collect("xiaohongshu") is True  # WATCH 允许采集

    def test_normal_can_collect(self, sm):
        assert sm.can_collect("xiaohongshu") is True


class TestCooldownAndProbe:
    """冷却与半开探测测试。"""

    def test_enter_cooldown_sets_expiry(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        sm.enter_cooldown("xiaohongshu", "测试冷却")
        record = sm.get_record("xiaohongshu")
        assert record.state == IPRiskState.COOLDOWN.value
        assert record.cooldown_until != ""

    def test_probe_success_from_cooldown(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        sm.enter_cooldown("xiaohongshu", "测试冷却")
        sm.probe_success("xiaohongshu")
        assert sm.get_state("xiaohongshu") == IPRiskState.WATCH

    def test_probe_fail_recooldown(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        sm.enter_cooldown("xiaohongshu", "测试冷却")
        sm.probe_fail("xiaohongshu", "探测失败")
        record = sm.get_record("xiaohongshu")
        assert record.cooldown_attempts == 1
        assert sm.get_state("xiaohongshu") == IPRiskState.COOLDOWN  # 仍在冷却

    def test_probe_fail_multiple_times_blocks(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(4):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, f"风控{i}")
        sm.enter_cooldown("xiaohongshu", "测试冷却")
        for i in range(3):  # probe_max_attempts=3
            sm.probe_fail("xiaohongshu", f"探测失败{i}")
        assert sm.get_state("xiaohongshu") == IPRiskState.BLOCKED


class TestManualUnblock:
    """人工解除熔断测试（硬红线）。"""

    def test_manual_unblock_goes_to_cooldown_not_normal(self, sm):
        """硬红线：BLOCKED 不能直接回 NORMAL，必须先 COOLDOWN。"""
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(6):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        assert sm.get_state("xiaohongshu") == IPRiskState.BLOCKED
        sm.manual_unblock("xiaohongshu", "管理员确认解除")
        assert sm.get_state("xiaohongshu") == IPRiskState.COOLDOWN  # 不是 NORMAL！

    def test_manual_reset_goes_directly_to_normal(self, sm):
        """管理员强制重置（仅限紧急情况）。"""
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(6):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        sm.manual_reset("xiaohongshu", "紧急重置")
        assert sm.get_state("xiaohongshu") == IPRiskState.NORMAL


class TestPersistence:
    """持久化测试。"""

    def test_state_persists_to_db(self, sm, temp_db):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        for i in range(6):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        # 重新创建实例，验证状态恢复
        import ip_risk_state_machine as ipm
        ipm.IPRiskStateMachine._instance = None
        from ip_risk_state_machine import IPRiskStateMachine, IPRiskConfig
        config = IPRiskConfig(db_path=temp_db)
        sm2 = IPRiskStateMachine(config)
        assert sm2.get_state("xiaohongshu") == IPRiskState.BLOCKED

    def test_transition_history_logged(self, sm):
        from ip_risk_state_machine import RiskSignalType
        for i in range(3):
            sm.record_risk_signal("douyin", RiskSignalType.CAPTCHA, f"风控{i}")
        history = sm.get_transition_history("douyin")
        assert len(history) > 0
        assert all(h["platform"] == "douyin" for h in history)


class TestAlertSystem:
    """告警系统测试。"""

    def test_alert_callback_triggered_on_state_change(self, sm):
        from ip_risk_state_machine import register_alert_callback, RiskSignalType
        alerts = []
        register_alert_callback(lambda a: alerts.append(a))
        for i in range(6):
            sm.record_risk_signal("weibo", RiskSignalType.IP_LIMITED, f"风控{i}")
        assert len(alerts) > 0
        # 应该有 BLOCKED 告警
        block_alerts = [a for a in alerts if a["type"] == "ip_risk_blocked"]
        assert len(block_alerts) > 0


class TestConvenienceFunction:
    """便捷函数测试。"""

    def test_check_and_record_risk(self, temp_db):
        from ip_risk_state_machine import check_and_record_risk, IPRiskStateMachine
        # 重置单例
        IPRiskStateMachine._instance = None
        result = check_and_record_risk("xiaohongshu", "300012", "检测到300012")
        assert "can_continue" in result
        assert "state" in result
        assert "is_blocked" in result
        assert result["can_continue"] is True  # 1次风控还在 NORMAL

    def test_check_and_record_risk_blocks_after_threshold(self, temp_db):
        from ip_risk_state_machine import check_and_record_risk, IPRiskStateMachine, IPRiskConfig
        IPRiskStateMachine._instance = None
        # 用短阈值配置
        from ip_risk_state_machine import IPRiskStateMachine
        config = IPRiskConfig(watch_threshold=1, suspend_threshold=2,
                               block_threshold=3, recovery_threshold=2,
                               cooldown_duration=60, db_path=temp_db)
        IPRiskStateMachine._instance = None
        # 先创建带配置的实例
        sm = IPRiskStateMachine(config)
        for i in range(3):
            result = check_and_record_risk("xiaohongshu", "300012", f"风控{i}")
        assert result["is_blocked"] is True
        assert result["can_continue"] is False


class TestMultiplePlatforms:
    """多平台隔离测试。"""

    def test_platforms_isolated(self, sm):
        from ip_risk_state_machine import IPRiskState, RiskSignalType
        # xiaohongshu 被熔断
        for i in range(6):
            sm.record_risk_signal("xiaohongshu", RiskSignalType.CODE_300012, f"风控{i}")
        # douyin 仍然正常
        assert sm.get_state("xiaohongshu") == IPRiskState.BLOCKED
        assert sm.get_state("douyin") == IPRiskState.NORMAL
        assert sm.can_collect("douyin") is True

    def test_get_all_states(self, sm):
        from ip_risk_state_machine import RiskSignalType
        sm.record_risk_signal("xiaohongshu", RiskSignalType.CAPTCHA, "测试")
        sm.record_risk_signal("douyin", RiskSignalType.IP_LIMITED, "测试")
        all_states = sm.get_all_states()
        assert "xiaohongshu" in all_states
        assert "douyin" in all_states
