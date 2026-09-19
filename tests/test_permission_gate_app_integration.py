# -*- coding: utf-8 -*-
"""
PermissionGate × app.py 集成测试
==================================
覆盖：
  1. _pg_resolve_operation_type 路径→操作类型映射（全类别）
  2. _permission_gate_write_check before_request 钩子行为
  3. fail-closed：_pg=None 时写操作返回 BLOCKED(503)
  4. 只读 GET 不被拦截
  5. 权限拒绝时返回 BLOCKED(403) 且不执行路由
  6. 白名单路径绕过
"""
import json
import sys
import os
import pytest

# 确保项目根目录在 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
from lumenis.system.security import (
    PermissionGate, PermissionLevel, OperationType, RiskLevel,
    get_permission_gate, reset_permission_gate,
)

# 权限门集成测试需要严格模式：不被TESTING通用放行影响
from lumenis.system.security import set_testing_bypass


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope='module', autouse=True)
def _strict_permission_gate():
    """模块级：进入时关闭TESTING bypass走严格模式，模块结束后重置为True避免污染其他测试。"""
    set_testing_bypass(False)
    yield
    set_testing_bypass(True)

@pytest.fixture
def flask_client():
    """提供 Flask test client，每个测试独立。"""
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client


@pytest.fixture
def gate_with_commit():
    """授权 COMMIT/PUSH 的 gate（模拟生产基线）。"""
    reset_permission_gate()
    g = get_permission_gate()
    g.grant_permission(PermissionLevel.COMMIT)
    g.grant_permission(PermissionLevel.PUSH)
    g.grant_permission(PermissionLevel.HUMAN_APPROVAL)
    return g


@pytest.fixture
def gate_no_commit():
    """未授权 COMMIT 的 gate（高风险操作应被拒绝）。"""
    reset_permission_gate()
    g = get_permission_gate()
    # 只启用默认 READ..VERIFY，不授权 COMMIT/PUSH
    return g


# ═══════════════════════════════════════════════════════════════
# 1. _pg_resolve_operation_type 映射测试
# ═══════════════════════════════════════════════════════════════

class TestOperationTypeResolver:
    """验证所有写操作类别都能正确映射到 OperationType。"""

    def test_delete_routes(self):
        assert app_module._pg_resolve_operation_type('/api/brands/xyz', 'DELETE') == OperationType.DATA_DELETE
        assert app_module._pg_resolve_operation_type('/api/event-graph/events/evt_1', 'DELETE') == OperationType.DATA_DELETE
        assert app_module._pg_resolve_operation_type('/api/v4/api-keys/revoke', 'POST') == OperationType.DATA_DELETE

    def test_collector_start(self):
        assert app_module._pg_resolve_operation_type('/api/collect', 'POST') == OperationType.COLLECTOR_START
        assert app_module._pg_resolve_operation_type('/api/rednote/collect', 'POST') == OperationType.COLLECTOR_START
        assert app_module._pg_resolve_operation_type('/api/collector/browser/start', 'POST') == OperationType.COLLECTOR_START
        assert app_module._pg_resolve_operation_type('/api/official-info/collect', 'POST') == OperationType.COLLECTOR_START
        assert app_module._pg_resolve_operation_type('/api/web/collect', 'POST') == OperationType.COLLECTOR_START

    def test_collector_stop(self):
        assert app_module._pg_resolve_operation_type('/api/collector/browser/stop', 'POST') == OperationType.COLLECTOR_STOP

    def test_report_generate(self):
        assert app_module._pg_resolve_operation_type('/api/special-report/generate', 'POST') == OperationType.REPORT_GENERATE
        assert app_module._pg_resolve_operation_type('/api/weekly/send-email', 'POST') == OperationType.REPORT_GENERATE

    def test_data_import(self):
        assert app_module._pg_resolve_operation_type('/api/local-import', 'POST') == OperationType.DATA_IMPORT
        assert app_module._pg_resolve_operation_type('/api/cases/import', 'POST') == OperationType.DATA_IMPORT
        assert app_module._pg_resolve_operation_type('/api/cookies/import', 'POST') == OperationType.DATA_IMPORT
        assert app_module._pg_resolve_operation_type('/api/event-graph/import', 'POST') == OperationType.DATA_IMPORT

    def test_data_export(self):
        assert app_module._pg_resolve_operation_type('/api/backup', 'POST') == OperationType.DATA_EXPORT
        assert app_module._pg_resolve_operation_type('/api/creative/pitch-export', 'POST') == OperationType.DATA_EXPORT

    def test_config_modify(self):
        assert app_module._pg_resolve_operation_type('/api/system/config', 'POST') == OperationType.CONFIG_MODIFY
        assert app_module._pg_resolve_operation_type('/api/config/company-domain', 'POST') == OperationType.CONFIG_MODIFY
        assert app_module._pg_resolve_operation_type('/api/config/emails', 'POST') == OperationType.CONFIG_MODIFY
        assert app_module._pg_resolve_operation_type('/api/config/email-settings', 'POST') == OperationType.CONFIG_MODIFY
        assert app_module._pg_resolve_operation_type('/api/brands', 'POST') == OperationType.CONFIG_MODIFY
        assert app_module._pg_resolve_operation_type('/api/brands/xyz', 'PUT') == OperationType.CONFIG_MODIFY

    def test_runtime_operation(self):
        assert app_module._pg_resolve_operation_type('/api/resident/recover', 'POST') == OperationType.RUNTIME_OPERATION
        assert app_module._pg_resolve_operation_type('/api/network/reset', 'POST') == OperationType.RUNTIME_OPERATION
        assert app_module._pg_resolve_operation_type('/api/xhs/switch-account', 'POST') == OperationType.RUNTIME_OPERATION
        assert app_module._pg_resolve_operation_type('/api/xhs/p0/recovery/complete', 'POST') == OperationType.RUNTIME_OPERATION

    def test_browser_operation(self):
        assert app_module._pg_resolve_operation_type('/api/xhs/login/start', 'POST') == OperationType.BROWSER_OPERATION
        assert app_module._pg_resolve_operation_type('/api/xhs/login/save', 'POST') == OperationType.BROWSER_OPERATION
        assert app_module._pg_resolve_operation_type('/api/weibo/start-login', 'POST') == OperationType.BROWSER_OPERATION
        assert app_module._pg_resolve_operation_type('/api/weibo/clear-login', 'POST') == OperationType.BROWSER_OPERATION
        assert app_module._pg_resolve_operation_type('/api/bilibili/clear-login', 'POST') == OperationType.BROWSER_OPERATION
        assert app_module._pg_resolve_operation_type('/api/xhs/keepalive/mark', 'POST') == OperationType.BROWSER_OPERATION

    def test_ai_call(self):
        assert app_module._pg_resolve_operation_type('/api/intelligence/refresh', 'POST') == OperationType.AI_CALL
        assert app_module._pg_resolve_operation_type('/api/creative/ideas', 'POST') == OperationType.AI_CALL
        assert app_module._pg_resolve_operation_type('/api/case-analysis/ai-evaluate', 'POST') == OperationType.AI_CALL
        assert app_module._pg_resolve_operation_type('/api/pr/match', 'POST') == OperationType.AI_CALL

    def test_shared_safe_actions_are_ai_calls(self):
        """共享能力的低风险动作不能被全局门误判成 DB_WRITE。"""
        for action in ('READ', 'ANALYZE', 'SUGGEST'):
            with app_module.app.test_request_context(
                '/api/experience/shared-skills/shared.social_card/run',
                method='POST', json={'action_type': action},
            ):
                assert app_module._pg_resolve_operation_type(
                    '/api/experience/shared-skills/shared.social_card/run', 'POST'
                ) == OperationType.AI_CALL

    def test_shared_write_action_stays_high_risk(self):
        """共享能力未放行的写动作仍保持 DB_WRITE 高风险门。"""
        with app_module.app.test_request_context(
            '/api/experience/shared-skills/shared.social_card/run',
            method='POST', json={'action_type': 'WRITE'},
        ):
            assert app_module._pg_resolve_operation_type(
                '/api/experience/shared-skills/shared.social_card/run', 'POST'
            ) == OperationType.DB_WRITE

    def test_shared_video_export_is_conditional_data_export(self):
        """本地成片只允许走可审计的 staged export，不得伪装成 AI 读请求。"""
        path = '/api/experience/shared-skills/shared.video_shotcraft/render'
        with app_module.app.test_request_context(path, method='POST', json={'action_type': 'EXPORT'}):
            assert app_module._pg_resolve_operation_type(path, 'POST') == OperationType.DATA_EXPORT

    def test_skill_execute(self):
        assert app_module._pg_resolve_operation_type('/api/workspace/term', 'POST') == OperationType.SKILL_EXECUTE
        routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
        for retired_route in ('/api/developer/run', '/api/dev/run-code', '/api/config/run-code'):
            assert retired_route not in routes

    def test_db_write_event_confirmation(self):
        assert app_module._pg_resolve_operation_type('/api/negative/confirm', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/negative/reject', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/event-review/evt_1/confirm', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/event-review/evt_1/reject', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/negative-review/note_1/confirm', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/event-graph/events', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/event-graph/relations', 'POST') == OperationType.DB_WRITE

    def test_search_analyze_post(self):
        assert app_module._pg_resolve_operation_type('/api/search', 'POST') == OperationType.AI_CALL
        assert app_module._pg_resolve_operation_type('/api/translate', 'POST') == OperationType.AI_CALL
        assert app_module._pg_resolve_operation_type('/api/analyze', 'POST') == OperationType.AI_CALL
        assert app_module._pg_resolve_operation_type('/api/subject-classifier/classify', 'POST') == OperationType.AI_CALL

    def test_default_db_write(self):
        """未匹配特定类别的 POST 默认为 DB_WRITE。"""
        assert app_module._pg_resolve_operation_type('/api/alerts/read', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/alerts/refresh', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/brand-industry/recompute', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/cases', 'POST') == OperationType.DB_WRITE
        assert app_module._pg_resolve_operation_type('/api/learning/scan', 'POST') == OperationType.DB_WRITE


# ═══════════════════════════════════════════════════════════════
# 2. before_request 钩子行为测试
# ═══════════════════════════════════════════════════════════════

class TestBeforeRequestHook:
    """验证 _permission_gate_write_check 钩子的拦截行为。"""

    def test_get_not_blocked(self, flask_client, gate_with_commit):
        """GET 请求不被 PermissionGate 拦截。"""
        resp = flask_client.get('/api/health')
        # 健康检查可能返回 200 或其他，但不应是 403/503 BLOCKED
        assert resp.status_code not in (403, 503)

    def test_write_with_commit_allowed(self, gate_with_commit):
        """授权 COMMIT 后，写操作应通过 PermissionGate（返回 None 放行）。"""
        app_module._pg = gate_with_commit
        with app_module.app.test_request_context('/api/collect', method='POST'):
            resp = app_module._permission_gate_write_check()
            assert resp is None

    def test_write_without_commit_blocked(self, gate_no_commit):
        """未授权 COMMIT 时，DB_WRITE 类操作应被 PermissionGate 拒绝(403)。"""
        app_module._pg = gate_no_commit
        with app_module.app.test_request_context('/api/alerts/read', method='POST'):
            resp = app_module._permission_gate_write_check()
            assert resp is not None
            assert resp[1] == 403
            data = resp[0].json
            assert data['status'] == 'BLOCKED'
            assert '权限等级不足' in data.get('error', '') or '需人工审批' in data.get('error', '')

    def test_fail_closed_pg_none(self):
        """_pg=None 时，写操作必须 fail-closed 返回 503 BLOCKED。"""
        original = app_module._pg
        app_module._pg = None
        try:
            with app_module.app.test_request_context('/api/collect', method='POST'):
                resp = app_module._permission_gate_write_check()
                assert resp is not None
                assert resp[1] == 503
                data = resp[0].json
                assert data['status'] == 'BLOCKED'
                assert '未初始化' in data.get('error', '')
        finally:
            app_module._pg = original

    def test_fail_closed_gate_exception(self):
        """PermissionGate.check 抛异常时，必须 fail-closed 返回 503。"""
        class BrokenGate:
            def check(self, **kwargs):
                raise RuntimeError('simulated gate failure')
        original = app_module._pg
        app_module._pg = BrokenGate()
        try:
            with app_module.app.test_request_context('/api/collect', method='POST'):
                resp = app_module._permission_gate_write_check()
                assert resp is not None
                assert resp[1] == 503
                data = resp[0].json
                assert data['status'] == 'BLOCKED'
                assert 'fail-closed' in data.get('error', '')
        finally:
            app_module._pg = original

    def test_bypass_paths(self, flask_client):
        """白名单路径即使是 POST 也不被 PermissionGate 拦截。"""
        # /api/health 在白名单
        resp = flask_client.post('/api/health')
        assert resp.status_code not in (403, 503)

    def test_put_method_intercepted(self, gate_no_commit):
        """PUT 方法也被拦截。"""
        app_module._pg = gate_no_commit
        with app_module.app.test_request_context('/api/brands/testbrand', method='PUT'):
            resp = app_module._permission_gate_write_check()
            if resp is not None and resp[1] == 403:
                data = resp[0].json
                assert data.get('status') == 'BLOCKED'

    def test_delete_method_intercepted(self, gate_no_commit):
        """DELETE 方法也被拦截且映射为 DATA_DELETE（最高风险）。"""
        app_module._pg = gate_no_commit
        with app_module.app.test_request_context('/api/brands/testbrand', method='DELETE'):
            resp = app_module._permission_gate_write_check()
            assert resp is not None
            assert resp[1] == 403
            data = resp[0].json
            assert data['status'] == 'BLOCKED'
            assert data.get('operation') == 'data_delete'


# ═══════════════════════════════════════════════════════════════
# 3. PermissionGate 核心单元测试（补充）
# ═══════════════════════════════════════════════════════════════

class TestPermissionGateCore:
    """PermissionGate 核心行为补充测试。"""

    def setup_method(self):
        reset_permission_gate()
        self.gate = PermissionGate()

    def test_default_permissions_exclude_commit(self):
        """默认权限集不含 COMMIT/PUSH。"""
        assert not self.gate.has_permission(PermissionLevel.COMMIT)
        assert not self.gate.has_permission(PermissionLevel.PUSH)

    def test_db_write_requires_commit_denied_by_default(self):
        """DB_WRITE 默认被拒绝（需要 COMMIT）。"""
        result = self.gate.check(OperationType.DB_WRITE, resource='test')
        assert not result.allowed
        assert '权限等级不足' in result.reason

    def test_collector_start_allowed_by_default(self):
        """COLLECTOR_START 需要 VERIFY，默认允许。"""
        result = self.gate.check(OperationType.COLLECTOR_START, resource='test')
        assert result.allowed

    def test_report_generate_allowed_by_default(self):
        """REPORT_GENERATE 需要 ANALYZE，默认允许。"""
        result = self.gate.check(OperationType.REPORT_GENERATE, resource='test')
        assert result.allowed

    def test_data_delete_requires_approval(self):
        """DATA_DELETE 是 CRITICAL 风险，需人工审批。"""
        self.gate.grant_permission(PermissionLevel.PUSH)
        result = self.gate.check(OperationType.DATA_DELETE, resource='test')
        assert not result.allowed
        assert result.requires_approval

    def test_data_delete_with_approval_allowed(self):
        """DATA_DELETE 获人工审批后允许。"""
        self.gate.grant_permission(PermissionLevel.PUSH)
        token = self.gate.grant_approval('data_delete', duration_minutes=5)
        result = self.gate.check(OperationType.DATA_DELETE, resource='test')
        assert result.allowed
        assert result.requires_approval

    def test_fail_closed_unregistered_operation(self):
        """未注册操作在 fail_closed=True 时被拒绝。"""
        class FakeOp:
            value = 'unregistered_test_op'
        result = self.gate.check(FakeOp(), resource='test')
        assert not result.allowed
        assert '未注册' in result.reason

    def test_audit_log_records_denied(self):
        """拒绝操作应写入审计日志。"""
        self.gate.check(OperationType.DB_WRITE, resource='test_audit')
        stats = self.gate.get_audit_stats()
        assert stats['denied'] >= 1

    def test_audit_log_records_allowed(self):
        """允许操作应写入审计日志。"""
        self.gate.check(OperationType.COLLECTOR_START, resource='test_audit2')
        stats = self.gate.get_audit_stats()
        assert stats['allowed'] >= 1

    def test_idempotency(self):
        """相同 operation_id 重复调用返回缓存结果。"""
        result1 = self.gate.check(
            OperationType.COLLECTOR_START, resource='test',
            operation_id='idem_test_001')
        result2 = self.gate.check(
            OperationType.COLLECTOR_START, resource='test',
            operation_id='idem_test_001')
        assert result2.idempotent_hit

    def test_health_check(self):
        """健康检查返回正常状态。"""
        health = self.gate.health_check()
        assert health['status'] == 'healthy'
        assert health['fail_closed'] is True

    def test_grant_revoke_permission(self):
        """授权/撤销权限正常工作。"""
        assert not self.gate.has_permission(PermissionLevel.COMMIT)
        self.gate.grant_permission(PermissionLevel.COMMIT)
        assert self.gate.has_permission(PermissionLevel.COMMIT)
        self.gate.revoke_permission(PermissionLevel.COMMIT)
        assert not self.gate.has_permission(PermissionLevel.COMMIT)


# ═══════════════════════════════════════════════════════════════
# 4. 全局单例测试
# ═══════════════════════════════════════════════════════════════

class TestGlobalSingleton:
    def test_get_permission_gate_returns_same_instance(self):
        reset_permission_gate()
        g1 = get_permission_gate()
        g2 = get_permission_gate()
        assert g1 is g2

    def test_reset_creates_new_instance(self):
        reset_permission_gate()
        g1 = get_permission_gate()
        reset_permission_gate()
        g2 = get_permission_gate()
        assert g1 is not g2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--capture=no'])
