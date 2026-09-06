# -*- coding: utf-8 -*-
"""Batch3 单元测试：CollectState 采集状态机。

验证维度：
- 状态定义完整性
- STOP_REQUEST集合正确性
- RISK集合正确性
- label()方法返回正确中文标签
- 状态值一致性
"""
import sys
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from collector_guard.state import CollectState


class TestCollectStateConstants:
    """测试状态常量定义。"""

    def test_all_states_defined(self):
        """所有7种状态应被定义。"""
        assert hasattr(CollectState, 'HEALTHY')
        assert hasattr(CollectState, 'WARNING')
        assert hasattr(CollectState, 'COOLDOWN')
        assert hasattr(CollectState, 'PAUSED')
        assert hasattr(CollectState, 'AUTH_REQUIRED')
        assert hasattr(CollectState, 'NEED_VERIFY')
        assert hasattr(CollectState, 'NETWORK_ERROR')

    def test_state_values_are_strings(self):
        """状态值应为字符串。"""
        assert isinstance(CollectState.HEALTHY, str)
        assert isinstance(CollectState.WARNING, str)
        assert isinstance(CollectState.COOLDOWN, str)

    def test_all_tuple_contains_all_states(self):
        """ALL元组应包含所有7种状态。"""
        assert len(CollectState.ALL) == 7
        assert CollectState.HEALTHY in CollectState.ALL
        assert CollectState.WARNING in CollectState.ALL
        assert CollectState.COOLDOWN in CollectState.ALL
        assert CollectState.PAUSED in CollectState.ALL
        assert CollectState.AUTH_REQUIRED in CollectState.ALL
        assert CollectState.NEED_VERIFY in CollectState.ALL
        assert CollectState.NETWORK_ERROR in CollectState.ALL


class TestStopRequest:
    """测试STOP_REQUEST集合（必须立即停止请求的状态）。"""

    def test_cooldown_in_stop_request(self):
        """COOLDOWN应在STOP_REQUEST中。"""
        assert CollectState.COOLDOWN in CollectState.STOP_REQUEST

    def test_paused_in_stop_request(self):
        """PAUSED应在STOP_REQUEST中。"""
        assert CollectState.PAUSED in CollectState.STOP_REQUEST

    def test_auth_required_in_stop_request(self):
        """AUTH_REQUIRED应在STOP_REQUEST中。"""
        assert CollectState.AUTH_REQUIRED in CollectState.STOP_REQUEST

    def test_need_verify_in_stop_request(self):
        """NEED_VERIFY应在STOP_REQUEST中。"""
        assert CollectState.NEED_VERIFY in CollectState.STOP_REQUEST

    def test_healthy_not_in_stop_request(self):
        """HEALTHY不应在STOP_REQUEST中。"""
        assert CollectState.HEALTHY not in CollectState.STOP_REQUEST

    def test_warning_not_in_stop_request(self):
        """WARNING不应在STOP_REQUEST中（仅降频，不停止）。"""
        assert CollectState.WARNING not in CollectState.STOP_REQUEST

    def test_network_error_not_in_stop_request(self):
        """NETWORK_ERROR不应在STOP_REQUEST中（可退避重试）。"""
        assert CollectState.NETWORK_ERROR not in CollectState.STOP_REQUEST


class TestRiskStates:
    """测试RISK集合（风险类状态）。"""

    def test_healthy_not_risk(self):
        """HEALTHY不应在RISK中。"""
        assert CollectState.HEALTHY not in CollectState.RISK

    def test_all_other_states_are_risk(self):
        """除HEALTHY外所有状态应在RISK中。"""
        for state in CollectState.ALL:
            if state != CollectState.HEALTHY:
                assert state in CollectState.RISK, f"{state} should be in RISK"


class TestLabelMethod:
    """测试label()方法返回中文标签。"""

    def test_healthy_label(self):
        assert CollectState.label(CollectState.HEALTHY) == '正常'

    def test_warning_label(self):
        assert CollectState.label(CollectState.WARNING) == '轻度风险·降频'

    def test_cooldown_label(self):
        assert CollectState.label(CollectState.COOLDOWN) == '熔断冷却'

    def test_paused_label(self):
        assert CollectState.label(CollectState.PAUSED) == '已暂停'

    def test_auth_required_label(self):
        assert CollectState.label(CollectState.AUTH_REQUIRED) == '登录失效'

    def test_need_verify_label(self):
        assert CollectState.label(CollectState.NEED_VERIFY) == '需要人机验证'

    def test_network_error_label(self):
        assert CollectState.label(CollectState.NETWORK_ERROR) == '网络异常'

    def test_unknown_state_returns_itself(self):
        """未知状态应返回其本身。"""
        assert CollectState.label('unknown_state') == 'unknown_state'

    def test_empty_string_returns_itself(self):
        assert CollectState.label('') == ''


class TestStateConsistency:
    """测试状态值与标签的一致性。"""

    def test_all_states_have_labels(self):
        """ALL中每个状态都应有对应的中文标签。"""
        for state in CollectState.ALL:
            label = CollectState.label(state)
            assert label != state, f"State {state} has no label mapping"
            assert len(label) > 0, f"State {state} has empty label"

    def test_no_duplicate_labels(self):
        """不同状态不应有相同标签。"""
        labels = [CollectState.label(s) for s in CollectState.ALL]
        assert len(labels) == len(set(labels)), "Duplicate labels found"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
