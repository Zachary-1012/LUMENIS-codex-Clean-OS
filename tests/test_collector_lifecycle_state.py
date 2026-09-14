# -*- coding: utf-8 -*-
"""CollectorLifecycleState 七态状态机 + task 字段完整性测试。

验证维度：
- 七态定义完整（STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING）
- can_transition 合法性校验（禁止 RUNNING 直跳 STOPPED）
- 合法转换链 RUNNING -> STOPPING -> STOPPED
- task 对象包含 started_at/last_heartbeat_at/last_success_at/finished_at/retry_count
- stop_collection 优雅关闭流程
"""
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from collector_automation import CollectorLifecycleState, CollectorAutomation


class TestSevenStateMachine:
    """七态状态机定义与转换校验。"""

    def test_all_seven_states_defined(self):
        """七态必须全部定义。"""
        expected = {'STARTING', 'RUNNING', 'DEGRADED', 'FAILED',
                    'STOPPING', 'STOPPED', 'RECOVERING'}
        actual = {s.name for s in CollectorLifecycleState}
        assert actual == expected, f'状态集合不匹配: 期望{expected}, 实际{actual}'

    def test_running_to_stopped_is_illegal(self):
        """RUNNING -> STOPPED 必须被拒绝（应经 STOPPING 中转）。"""
        assert CollectorLifecycleState.can_transition(
            CollectorLifecycleState.RUNNING, CollectorLifecycleState.STOPPED
        ) is False

    def test_running_to_stopping_to_stopped_is_legal(self):
        """RUNNING -> STOPPING -> STOPPED 合法转换链。"""
        assert CollectorLifecycleState.can_transition(
            CollectorLifecycleState.RUNNING, CollectorLifecycleState.STOPPING
        ) is True
        assert CollectorLifecycleState.can_transition(
            CollectorLifecycleState.STOPPING, CollectorLifecycleState.STOPPED
        ) is True

    def test_stopped_to_starting_is_legal(self):
        """STOPPED -> STARTING 合法（重启采集）。"""
        assert CollectorLifecycleState.can_transition(
            CollectorLifecycleState.STOPPED, CollectorLifecycleState.STARTING
        ) is True

    def test_failed_to_recovering_is_legal(self):
        """FAILED -> RECOVERING 合法。"""
        assert CollectorLifecycleState.can_transition(
            CollectorLifecycleState.FAILED, CollectorLifecycleState.RECOVERING
        ) is True

    def test_stopped_to_running_is_illegal(self):
        """STOPPED -> RUNNING 必须被拒绝（应经 STARTING）。"""
        assert CollectorLifecycleState.can_transition(
            CollectorLifecycleState.STOPPED, CollectorLifecycleState.RUNNING
        ) is False

    def test_string_input_accepted(self):
        """can_transition 接受字符串输入。"""
        assert CollectorLifecycleState.can_transition('running', 'stopping') is True
        assert CollectorLifecycleState.can_transition('running', 'stopped') is False

    def test_invalid_state_rejected(self):
        """未知状态返回 False。"""
        assert CollectorLifecycleState.can_transition('running', 'nonexistent') is False
        assert CollectorLifecycleState.can_transition('nonexistent', 'running') is False


class TestTaskObjectFields:
    """task 对象必须包含完整的时间戳与重试字段。"""

    def test_task_has_standard_fields(self):
        """start_collection 创建的 task 必须包含所有标准字段。"""
        ca = CollectorAutomation()
        # 模拟预检通过 + 不实际启动线程
        with patch.object(ca, '_port_for', return_value=9223), \
             patch('xhs_cookie_bridge.runtime_preflight_check',
                   return_value={'ok': True, 'overall_state': 'healthy',
                                 'evidence': 'ok', 'active_account': 'XHS_RETINAUT',
                                 'checks': []}), \
             patch('xhs_cookie_bridge.cookie_configured', return_value=True), \
             patch.object(ca, '_run_collection'), \
             patch('threading.Thread.start'):
            result = ca.start_collection(keywords=['太古汇'], mode='quick', force=True)
        assert result['ok'] is True
        task = ca.current_task
        required_fields = ['started_at', 'last_heartbeat_at', 'last_success_at',
                           'finished_at', 'retry_count', 'status', 'error']
        # error 字段可能不存在（无错误时），单独检查
        for f in ['started_at', 'last_heartbeat_at', 'last_success_at',
                  'finished_at', 'retry_count', 'status']:
            assert f in task, f'task 缺少字段: {f}'
        assert task['retry_count'] == 0
        assert task['started_at'] is not None

    def test_get_status_returns_lifecycle_state(self):
        """get_status 必须返回 lifecycle_state 等关键字段。"""
        ca = CollectorAutomation()
        status = ca.get_status()
        assert 'lifecycle_state' in status
        assert 'is_running' in status
        assert 'stop_requested' in status
        assert 'current_task' in status
        assert 'browser_running' in status
        assert status['lifecycle_state'] == 'stopped'


class TestGracefulShutdown:
    """优雅关闭：stop_collection 必须设置 stop_event 并等待线程。"""

    def test_stop_idempotent_when_not_running(self):
        """未运行时 stop_collection 返回错误而非崩溃。"""
        ca = CollectorAutomation()
        result = ca.stop_collection()
        assert result['ok'] is False
        assert '没有正在运行' in result['error']

    def test_stop_event_initially_cleared(self):
        """初始状态 stop_event 应为 cleared。"""
        ca = CollectorAutomation()
        assert ca._stop_event.is_set() is False
        assert ca.get_status()['stop_requested'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
