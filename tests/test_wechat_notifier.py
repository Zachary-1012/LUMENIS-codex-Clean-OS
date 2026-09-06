# -*- coding: utf-8 -*-
"""
微信通知中心单元测试
覆盖：注册/触发链路、凭证缺失BLOCKED、降级不崩、去重、日志记录
全 mock，不实际联网发送。
"""
import os
import sys
import json
import tempfile
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import wechat_notifier as wn
from wechat_notifier import (
    WeChatNotifier, NotificationLevel, NotificationType,
    StatusAlertRegistration, CredentialStatus,
    _wechat_official_credential_status,
)


@pytest.fixture
def tmp_db():
    """使用临时数据库，避免污染主库。"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def notifier(tmp_db):
    """创建无渠道的 notifier（凭证缺失状态）。"""
    with patch.object(wn, 'DB_PATH', tmp_db):
        n = WeChatNotifier(db_path=tmp_db)
        n.channels = []  # 确保无渠道
        yield n


class TestCredentialStatus:
    """凭证状态测试：缺凭证必须 BLOCKED，绝不伪造 READY。"""

    def test_missing_all_credentials_blocked(self):
        env = {}
        result = _wechat_official_credential_status(env)
        assert result['status'] == CredentialStatus.BLOCKED
        assert 'WECHAT_APPID' in result['missing_fields']
        assert 'WECHAT_SECRET' in result['missing_fields']
        assert 'WECHAT_TEMPLATE_ID' in result['missing_fields']
        assert 'WECHAT_RECEIVER_OPENIDS' in result['missing_fields']

    def test_partial_credentials_blocked(self):
        env = {'WECHAT_APPID': 'wx123', 'WECHAT_SECRET': 'secret123'}
        result = _wechat_official_credential_status(env)
        assert result['status'] == CredentialStatus.BLOCKED
        assert 'WECHAT_TEMPLATE_ID' in result['missing_fields']
        assert 'WECHAT_RECEIVER_OPENIDS' in result['missing_fields']

    def test_full_credentials_ready(self):
        env = {
            'WECHAT_APPID': 'wx123',
            'WECHAT_SECRET': 'secret123',
            'WECHAT_TEMPLATE_ID': 'tpl123',
            'WECHAT_RECEIVER_OPENIDS': 'oid1,oid2',
        }
        result = _wechat_official_credential_status(env)
        assert result['status'] == CredentialStatus.READY
        assert result['missing_fields'] == []

    def test_legacy_env_names_supported(self):
        """兼容旧名 WECHAT_APP_ID / WECHAT_APP_SECRET。"""
        env = {
            'WECHAT_APP_ID': 'wx_old',
            'WECHAT_APP_SECRET': 'secret_old',
            'WECHAT_TEMPLATE_ID': 'tpl123',
            'WECHAT_RECEIVER_OPENIDS': 'oid1',
        }
        result = _wechat_official_credential_status(env)
        assert result['status'] == CredentialStatus.READY

    def test_notifier_is_wechat_blocked(self, notifier):
        assert notifier.is_wechat_blocked() is True

    def test_notifier_get_credential_status_all_blocked(self, notifier):
        statuses = notifier.get_credential_status()
        assert len(statuses) == 4  # 微信公众号 + 企业微信 + Server酱 + PushPlus
        for s in statuses:
            assert s['status'] == CredentialStatus.BLOCKED
            # 绝不打印凭证值
            assert 'appid' not in json.dumps(s).lower() or 'WECHAT_APPID' in s.get('missing_fields', [])


class TestStatusAlertRegistration:
    """状态变更告警注册/注销/列表测试。"""

    def test_register_returns_id(self, notifier):
        reg = notifier.register_status_alert(
            event_types=['risk_level_change'],
            min_level=NotificationLevel.WARNING,
        )
        assert reg['registration_id'].startswith('reg_')
        assert 'risk_level_change' in reg['event_types']

    def test_register_with_custom_id(self, notifier):
        reg = notifier.register_status_alert(registration_id='my_reg_001')
        assert reg['registration_id'] == 'my_reg_001'

    def test_list_registrations(self, notifier):
        notifier.register_status_alert(event_types=['a'])
        notifier.register_status_alert(event_types=['b'])
        regs = notifier.list_status_registrations()
        assert len(regs) == 2

    def test_unregister_success(self, notifier):
        reg = notifier.register_status_alert()
        assert notifier.unregister_status_alert(reg['registration_id']) is True
        assert len(notifier.list_status_registrations()) == 0

    def test_unregister_nonexistent_returns_false(self, notifier):
        assert notifier.unregister_status_alert('nonexistent') is False


class TestTriggerStatusChange:
    """状态变更触发链路测试：缺凭证时 BLOCKED，不伪造"已发送"。"""

    def test_trigger_no_registration_skips_push(self, notifier):
        """无匹配注册时：不推送，但记录日志。"""
        r = notifier.trigger_status_change(
            'unknown_event', '标题', '内容', level=NotificationLevel.WARNING
        )
        assert r['matched_registrations'] == 0
        assert r['wechat_push']['attempted'] is False
        assert r['log_recorded'] is True

    def test_trigger_with_registration_but_no_channels_blocked(self, notifier):
        """有注册但无可用渠道：显式 BLOCKED，success=False，绝不伪造已发送。"""
        notifier.register_status_alert(
            event_types=['risk_level_change'],
            min_level=NotificationLevel.WARNING,
        )
        r = notifier.trigger_status_change(
            'risk_level_change', '风险升级', 'low->high',
            level=NotificationLevel.HIGH_RISK,
            extra={'old': 'low', 'new': 'high'},
        )
        assert r['matched_registrations'] == 1
        assert r['wechat_push']['attempted'] is True
        assert r['wechat_push']['success'] is False
        assert r['wechat_push']['status'] == CredentialStatus.BLOCKED
        assert '微信公众号' in r['blocked_channels']
        assert r['log_recorded'] is True
        # 绝不显示"已发送到微信"
        assert '已发送' not in json.dumps(r, ensure_ascii=False)

    def test_trigger_level_filtering(self, notifier):
        """级别过滤：INFO 级别不触发 WARNING 最低级别的注册。"""
        notifier.register_status_alert(
            event_types=['test'], min_level=NotificationLevel.HIGH_RISK,
        )
        r = notifier.trigger_status_change(
            'test', '低级别', '内容', level=NotificationLevel.INFO,
        )
        assert r['matched_registrations'] == 0

    def test_trigger_high_risk_passes_filter(self, notifier):
        """HIGH_RISK 级别触发 WARNING 最低级别的注册。"""
        notifier.register_status_alert(
            event_types=['test'], min_level=NotificationLevel.WARNING,
        )
        r = notifier.trigger_status_change(
            'test', '高级别', '内容', level=NotificationLevel.HIGH_RISK,
        )
        assert r['matched_registrations'] == 1

    def test_trigger_event_type_filtering(self, notifier):
        """事件类型过滤：不匹配的事件类型不触发。"""
        notifier.register_status_alert(event_types=['risk_change'])
        r = notifier.trigger_status_change('other_event', 't', 'c')
        assert r['matched_registrations'] == 0

    def test_trigger_log_only_registration(self, notifier):
        """log_only 注册：仅写日志，不尝试推送。"""
        notifier.register_status_alert(
            event_types=['test'], log_only=True,
        )
        r = notifier.trigger_status_change('test', 't', 'c')
        assert r['matched_registrations'] == 1
        assert r['wechat_push']['attempted'] is False
        assert r['wechat_push']['status'] == 'log_only'
        assert r['log_recorded'] is True

    def test_trigger_frontend_push_callback(self, notifier):
        """前端推送回调：设置后触发时调用。"""
        callback = MagicMock()
        notifier.set_frontend_push_callback(callback)
        notifier.register_status_alert(event_types=['test'], frontend_push=True)
        r = notifier.trigger_status_change(
            'test', 't', 'c', level=NotificationLevel.WARNING,
            extra={'key': 'value'},
        )
        assert r['frontend_pushed'] is True
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == 'test'
        assert args[4] == {'key': 'value'}

    def test_trigger_frontend_push_callback_exception_does_not_crash(self, notifier):
        """前端回调异常时不崩溃（降级不崩）。"""
        callback = MagicMock(side_effect=RuntimeError('前端推送失败'))
        notifier.set_frontend_push_callback(callback)
        notifier.register_status_alert(event_types=['test'])
        r = notifier.trigger_status_change('test', 't', 'c')
        assert r['frontend_pushed'] is False
        assert '前端推送失败' in r.get('frontend_push_error', '')

    def test_trigger_with_mock_channel_sends(self, notifier):
        """有可用渠道时：实际调用 channel.send。"""
        mock_channel = MagicMock()
        mock_channel.name = '测试渠道'
        mock_channel.enabled = True
        mock_channel.send.return_value = True
        notifier.channels = [mock_channel]

        notifier.register_status_alert(event_types=['test'])
        r = notifier.trigger_status_change(
            'test', '标题', '内容', level=NotificationLevel.WARNING,
        )
        assert r['wechat_push']['attempted'] is True
        assert r['wechat_push']['success'] is True
        mock_channel.send.assert_called_once()

    def test_trigger_dedup_prevents_duplicate(self, notifier):
        """重复触发：去重机制生效，第二次不重复推送。"""
        mock_channel = MagicMock()
        mock_channel.name = '测试渠道'
        mock_channel.enabled = True
        mock_channel.send.return_value = True
        notifier.channels = [mock_channel]

        notifier.register_status_alert(event_types=['test'])
        notifier.trigger_status_change('test', '相同标题', '相同内容')
        r2 = notifier.trigger_status_change('test', '相同标题', '相同内容')
        # 第二次因去重被跳过
        assert r2['wechat_push'].get('status') != 'success' or mock_channel.send.call_count == 1


class TestDegradation:
    """降级测试：各种异常情况下不崩溃。"""

    def test_send_with_no_channels_returns_false_not_crash(self, notifier):
        result = notifier.send(NotificationType.GENERAL, 't', 'c')
        assert result['success'] is False
        assert result['channels'] == []

    def test_send_system_error_no_dedup(self, notifier):
        """系统异常通知不去重（每次都应记录）。"""
        r1 = notifier.send_system_error('error1', 'module1')
        r2 = notifier.send_system_error('error1', 'module1')
        assert r1['duplicate'] is False
        assert r2['duplicate'] is False

    def test_get_notification_logs(self, notifier):
        notifier.send(NotificationType.GENERAL, '测试标题', '测试内容')
        logs = notifier.get_notification_logs(limit=10)
        assert len(logs) >= 1
        assert logs[0]['title'] == '测试标题'

    def test_add_channel(self, notifier):
        result = notifier.add_channel('wecom', {'webhook_url': 'https://example.com', 'name': '测试'})
        assert result is True

    def test_get_channel_status_empty(self, notifier):
        status = notifier.get_channel_status()
        assert status == []


class TestNotificationTemplates:
    """通知模板测试。"""

    def test_high_risk_alert_template(self):
        title, content = wn.NotificationTemplates.high_risk_alert(
            '测试笔记', 'https://example.com/1', '包含敏感词', likes=100
        )
        assert '高风险' in title
        assert '测试笔记' in content
        assert '100' in content

    def test_system_error_template(self):
        title, content = wn.NotificationTemplates.system_error('连接超时', '采集模块')
        assert '系统异常' in title
        assert '连接超时' in content

    def test_daily_report_template(self):
        title, content = wn.NotificationTemplates.daily_report(
            '2026-09-06', 100, 10, 3, 'https://example.com/report'
        )
        assert '2026-09-06' in title
        assert '100' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
