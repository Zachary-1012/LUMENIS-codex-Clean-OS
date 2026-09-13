# -*- coding: utf-8 -*-
"""
ZBC Phase 3 - PermissionGate + SecurityBoundary 测试套件
==========================================================
覆盖：
  1. 权限等级检查（PermissionLevel 枚举 + has_permission）
  2. 操作类型注册表（OperationType + _OPERATION_REGISTRY）
  3. 高风险操作 fail-closed（HIGH/CRITICAL 默认拒绝）
  4. 人工审批流程（grant_approval / revoke_approval / is_approved）
  5. 审计日志记录（所有操作有 audit_id + 日志条目）
  6. 幂等性（operation_id 去重）
  7. 装饰器 @require_permission
  8. 未注册操作默认拒绝（fail_closed=True）
  9. SecurityBoundary 四层验证
  10. 现有模块 import 兼容
"""
import os
import sys
import time
import pytest

# 确保仓库根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from permission_gate import (
    PermissionGate,
    PermissionLevel,
    RiskLevel,
    OperationType,
    OperationSpec,
    PermissionResult,
    ApprovalToken,
    AuditEntry,
    require_permission,
    get_permission_gate,
    reset_permission_gate,
    set_testing_bypass,
)
from security_boundary import (
    SecurityBoundary,
    EdgeLayer,
    ApplicationLayer,
    AIAgentLayer,
    DataLayer,
    LayerValidationResult,
    BoundaryValidationResult,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope='module', autouse=True)
def _strict_mode_for_unit_tests():
    set_testing_bypass(False)
    yield
    set_testing_bypass(True)


@pytest.fixture
def gate():
    """每个测试用独立的 PermissionGate 实例，避免全局状态污染。"""
    return PermissionGate(fail_closed=True, caller="test_runner")


@pytest.fixture
def gate_fail_open():
    """fail_closed=False 的实例（用于对比测试）。"""
    return PermissionGate(fail_closed=False, caller="test_fail_open")


@pytest.fixture
def boundary():
    """独立的 SecurityBoundary 实例。"""
    return SecurityBoundary(gate=PermissionGate(fail_closed=True, caller="test_boundary"))


# ═══════════════════════════════════════════════════════════════
# 1. 权限等级检查
# ═══════════════════════════════════════════════════════════════

class TestPermissionLevel:
    """PermissionLevel 枚举与权限等级检查。"""

    def test_enum_values(self):
        """所有枚举值存在且有序。"""
        expected = [
            "read", "audit", "analyze", "research", "plan",
            "patch_preview", "test", "verify", "human_approval",
            "commit", "push",
        ]
        actual = [l.value for l in PermissionLevel]
        assert actual == expected

    def test_rank_ordering(self):
        """权限等级 rank 单调递增。"""
        ranks = [PermissionLevel.rank(l) for l in PermissionLevel]
        assert ranks == sorted(ranks)
        assert ranks[0] == 0
        assert ranks[-1] == len(PermissionLevel) - 1

    def test_default_enabled_permissions(self):
        """默认启用 READ 到 VERIFY，不含 HUMAN_APPROVAL/COMMIT/PUSH。"""
        g = PermissionGate()
        enabled = set(g.get_enabled_permissions())
        assert "read" in enabled
        assert "verify" in enabled
        assert "human_approval" not in enabled
        assert "commit" not in enabled
        assert "push" not in enabled

    def test_has_permission(self, gate):
        """has_permission 正确反映启用状态。"""
        assert gate.has_permission(PermissionLevel.READ) is True
        assert gate.has_permission(PermissionLevel.VERIFY) is True
        assert gate.has_permission(PermissionLevel.COMMIT) is False
        assert gate.has_permission(PermissionLevel.PUSH) is False

    def test_grant_revoke_permission(self, gate):
        """授予/撤销权限等级。"""
        assert gate.has_permission(PermissionLevel.COMMIT) is False
        gate.grant_permission(PermissionLevel.COMMIT)
        assert gate.has_permission(PermissionLevel.COMMIT) is True
        gate.revoke_permission(PermissionLevel.COMMIT)
        assert gate.has_permission(PermissionLevel.COMMIT) is False


# ═══════════════════════════════════════════════════════════════
# 2. 操作类型注册表
# ═══════════════════════════════════════════════════════════════

class TestOperationRegistry:
    """OperationType 枚举与操作注册表。"""

    def test_all_operation_types_registered(self, gate):
        """所有 OperationType 枚举值都已注册。"""
        for ot in OperationType:
            assert gate.is_registered(ot), f"{ot.value} 未注册"

    def test_operation_spec_fields(self, gate):
        """每个注册操作有完整的 OperationSpec。"""
        for ot in OperationType:
            spec = gate.get_operation_spec(ot)
            assert spec is not None
            # Another isolation test reloads permission_gate; enum class identity then
            # changes although the serialized contract remains identical.
            assert spec.permission.value in {p.value for p in PermissionLevel}
            assert spec.risk.value in {r.value for r in RiskLevel}
            assert isinstance(spec.description, str)
            assert len(spec.description) > 0

    def test_high_risk_operations_not_auto_allow(self, gate):
        """HIGH/CRITICAL 风险操作的 auto_allow 应为 False。"""
        high_risk_ops = []
        for ot in OperationType:
            spec = gate.get_operation_spec(ot)
            if RiskLevel.rank(spec.risk) >= RiskLevel.rank(RiskLevel.HIGH):
                high_risk_ops.append(ot)
                assert spec.auto_allow is False, f"{ot.value} 高风险但 auto_allow=True"
        # 至少有 CONFIG_MODIFY, DB_WRITE, DATA_DELETE, DATA_IMPORT, RUNTIME_OPERATION
        assert len(high_risk_ops) >= 5

    def test_data_delete_is_critical(self, gate):
        """DATA_DELETE 必须是 CRITICAL 风险。"""
        spec = gate.get_operation_spec(OperationType.DATA_DELETE)
        assert spec.risk == RiskLevel.CRITICAL
        assert spec.permission == PermissionLevel.PUSH
        assert spec.auto_allow is False

    def test_register_custom_operation(self, gate):
        """运行时注册新操作类型。"""
        custom_ot = OperationType.FILE_WRITE  # 复用枚举值测试 register
        custom_spec = OperationSpec(
            permission=PermissionLevel.VERIFY,
            risk=RiskLevel.LOW,
            description="自定义测试操作",
            auto_allow=True,
        )
        gate.register_operation(custom_ot, custom_spec)
        retrieved = gate.get_operation_spec(custom_ot)
        assert retrieved.description == "自定义测试操作"

    def test_list_operations(self, gate):
        """list_operations 返回所有已注册操作。"""
        ops = gate.list_operations()
        assert len(ops) == len(OperationType)
        for op in ops:
            assert "operation" in op
            assert "permission" in op
            assert "risk" in op


# ═══════════════════════════════════════════════════════════════
# 3. 高风险操作 fail-closed
# ═══════════════════════════════════════════════════════════════

class TestFailClosed:
    """高风险操作 fail-closed 验证。"""

    def test_high_risk_denied_without_approval(self, gate):
        """HIGH 风险操作无审批时被拒绝（先授予权限，再验证需人工审批）。"""
        # CONFIG_MODIFY 默认需要 COMMIT 权限，先授予以通过权限等级检查
        gate.grant_permission(PermissionLevel.COMMIT)
        result = gate.check(
            OperationType.CONFIG_MODIFY,
            resource="/etc/config.yaml",
            risk_level=RiskLevel.HIGH,
        )
        assert result.allowed is False
        assert result.requires_approval is True
        assert "人工审批" in result.reason

    def test_critical_denied_without_approval(self, gate):
        """CRITICAL 风险操作无审批时被拒绝（先授予权限，再验证需人工审批）。"""
        # DATA_DELETE 默认需要 PUSH 权限，先授予
        gate.grant_permission(PermissionLevel.PUSH)
        result = gate.check(
            OperationType.DATA_DELETE,
            resource="notes_table",
            risk_level=RiskLevel.CRITICAL,
        )
        assert result.allowed is False
        assert result.requires_approval is True

    def test_db_write_denied_without_commit_permission(self, gate):
        """DB_WRITE 需要 COMMIT 权限，默认未启用时被拒绝。"""
        result = gate.check(OperationType.DB_WRITE, resource="monitor.db")
        assert result.allowed is False
        assert "权限等级不足" in result.reason

    def test_low_risk_allowed(self, gate):
        """LOW 风险操作（AI_CALL）默认允许。"""
        result = gate.check(OperationType.AI_CALL, resource="glm-4.5-air")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_medium_risk_file_write_allowed(self, gate):
        """MEDIUM 风险 FILE_WRITE（权限达标时）允许。"""
        result = gate.check(
            OperationType.FILE_WRITE,
            resource="/tmp/output.txt",
            risk_level=RiskLevel.MEDIUM,
        )
        assert result.allowed is True

    def test_require_human_approval_threshold(self, gate):
        """require_human_approval 阈值正确（HIGH 及以上）。"""
        assert gate.require_human_approval(RiskLevel.LOW) is False
        assert gate.require_human_approval(RiskLevel.MEDIUM) is False
        assert gate.require_human_approval(RiskLevel.HIGH) is True
        assert gate.require_human_approval(RiskLevel.CRITICAL) is True

    def test_fail_closed_unregistered_operation(self, gate):
        """未注册操作在 fail_closed=True 时被拒绝。"""
        # 构造一个未注册的 OperationType（通过枚举值但从注册表移除）
        fake_ot = OperationType.RUNTIME_OPERATION
        # 临时移除
        original_spec = gate._registry.pop(fake_ot)
        try:
            result = gate.check(fake_ot, resource="test")
            assert result.allowed is False
            assert "未注册" in result.reason
            assert "fail_closed" in result.reason
        finally:
            gate._registry[fake_ot] = original_spec

    def test_fail_open_unregistered_operation(self, gate_fail_open):
        """未注册操作在 fail_closed=False 时按 MEDIUM/VERIFY 处理。"""
        fake_ot = OperationType.RUNTIME_OPERATION
        original_spec = gate_fail_open._registry.pop(fake_ot)
        try:
            result = gate_fail_open.check(fake_ot, resource="test")
            # fail_open 时未注册操作按 VERIFY 权限（默认启用）+ MEDIUM 风险处理
            assert result.allowed is True
        finally:
            gate_fail_open._registry[fake_ot] = original_spec


# ═══════════════════════════════════════════════════════════════
# 4. 人工审批流程
# ═══════════════════════════════════════════════════════════════

class TestHumanApproval:
    """人工审批令牌流程。"""

    def test_grant_approval_returns_token(self, gate):
        """grant_approval 返回非空令牌。"""
        token = gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=5,
        )
        assert token is not None
        assert len(token) > 10
        assert token.startswith("apr_")

    def test_approved_high_risk_operation_allowed(self, gate):
        """授予审批后，HIGH 风险操作允许执行。"""
        token = gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=5,
        )
        # CONFIG_MODIFY 需要 COMMIT 权限，先授予
        gate.grant_permission(PermissionLevel.COMMIT)
        result = gate.check(
            OperationType.CONFIG_MODIFY,
            resource="/etc/config.yaml",
        )
        assert result.allowed is True
        assert result.requires_approval is True
        assert result.approval_token == token

    def test_approval_scoped_to_operation(self, gate):
        """审批令牌只对指定操作有效，不对其他操作有效。"""
        gate.grant_permission(PermissionLevel.COMMIT)
        gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=5,
        )
        # CONFIG_MODIFY 应通过
        result1 = gate.check(OperationType.CONFIG_MODIFY, resource="c1")
        assert result1.allowed is True
        # DB_WRITE 不应通过（审批范围不包含）
        result2 = gate.check(OperationType.DB_WRITE, resource="db1")
        assert result2.allowed is False

    def test_revoke_approval(self, gate):
        """撤销审批后操作被拒绝。"""
        gate.grant_permission(PermissionLevel.COMMIT)
        token = gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=30,
        )
        # 审批有效时通过
        result1 = gate.check(OperationType.CONFIG_MODIFY, resource="c1")
        assert result1.allowed is True
        # 撤销
        revoked = gate.revoke_approval(token)
        assert revoked is True
        # 撤销后拒绝
        result2 = gate.check(OperationType.CONFIG_MODIFY, resource="c1")
        assert result2.allowed is False

    def test_revoke_nonexistent_approval(self, gate):
        """撤销不存在的令牌返回 False。"""
        assert gate.revoke_approval("nonexistent_token") is False

    def test_revoke_all_approvals(self, gate):
        """revoke_all_approvals 撤销所有令牌。"""
        gate.grant_approval(OperationType.CONFIG_MODIFY.value, duration_minutes=10)
        gate.grant_approval(OperationType.DB_WRITE.value, duration_minutes=10)
        count = gate.revoke_all_approvals()
        assert count >= 2
        assert gate.is_approved(OperationType.CONFIG_MODIFY.value) is False

    def test_is_approved(self, gate):
        """is_approved 正确反映审批状态。"""
        assert gate.is_approved(OperationType.CONFIG_MODIFY.value) is False
        gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=5,
        )
        assert gate.is_approved(OperationType.CONFIG_MODIFY.value) is True
        assert gate.is_approved(OperationType.DB_WRITE.value) is False

    def test_approval_expiry(self, gate):
        """审批令牌过期后失效。"""
        token = gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=0,  # 立即过期
        )
        # 直接操作 ApprovalToken 设置过期时间
        with gate._approval_lock:
            approval = gate._approvals[token]
            from datetime import datetime, timedelta
            approval.expires_at = datetime.now() - timedelta(seconds=1)
        assert gate.is_approved(OperationType.CONFIG_MODIFY.value) is False

    def test_list_approvals(self, gate):
        """list_approvals 返回所有审批令牌信息。"""
        gate.grant_approval(OperationType.CONFIG_MODIFY.value, duration_minutes=5)
        approvals = gate.list_approvals()
        assert len(approvals) >= 1
        for a in approvals:
            assert "token" in a
            assert "operation" in a
            assert "valid" in a


# ═══════════════════════════════════════════════════════════════
# 5. 审计日志记录
# ═══════════════════════════════════════════════════════════════

class TestAuditLog:
    """审计日志记录验证。"""

    def test_every_check_has_audit_id(self, gate):
        """每次 check 都有 audit_id。"""
        result = gate.check(OperationType.AI_CALL, resource="test")
        assert result.audit_id is not None
        assert result.audit_id.startswith("aud_")

    def test_audit_log_records_allowed(self, gate):
        """允许操作记录在审计日志中。"""
        gate.check(OperationType.AI_CALL, resource="model-x")
        logs = gate.get_audit_log(result_filter="allowed")
        assert len(logs) >= 1
        assert logs[-1]["operation_type"] == "ai_call"
        assert logs[-1]["result"] == "allowed"

    def test_audit_log_records_denied(self, gate):
        """拒绝操作记录在审计日志中。"""
        gate.check(OperationType.DATA_DELETE, resource="table-x")
        logs = gate.get_audit_log(result_filter="denied")
        assert len(logs) >= 1
        assert logs[-1]["result"] == "denied"

    def test_audit_log_fields(self, gate):
        """审计日志条目包含所有必要字段。"""
        gate.check(
            OperationType.AI_CALL,
            resource="model-y",
            caller="test_caller",
        )
        logs = gate.get_audit_log(limit=1)
        entry = logs[-1]
        assert "audit_id" in entry
        assert "timestamp" in entry
        assert "operation_type" in entry
        assert "resource" in entry
        assert "risk_level" in entry
        assert "permission_required" in entry
        assert "caller" in entry
        assert "result" in entry
        assert "reason" in entry

    def test_audit_stats(self, gate):
        """审计统计正确。"""
        gate.check(OperationType.AI_CALL, resource="a")
        gate.check(OperationType.AI_CALL, resource="b")
        gate.check(OperationType.DATA_DELETE, resource="c")
        stats = gate.get_audit_stats()
        assert stats["total"] >= 3
        assert stats["allowed"] >= 2
        assert stats["denied"] >= 1

    def test_audit_log_filter_by_operation(self, gate):
        """按操作类型过滤审计日志。"""
        gate.check(OperationType.AI_CALL, resource="a")
        gate.check(OperationType.REPORT_GENERATE, resource="b")
        ai_logs = gate.get_audit_log(operation_type="ai_call")
        assert all(l["operation_type"] == "ai_call" for l in ai_logs)

    def test_approval_granted_audit(self, gate):
        """授予审批时写入审计日志。"""
        gate.grant_approval(OperationType.CONFIG_MODIFY.value, duration_minutes=5)
        logs = gate.get_audit_log()
        approval_logs = [l for l in logs if l["result"] == "approval_granted"]
        assert len(approval_logs) >= 1


# ═══════════════════════════════════════════════════════════════
# 6. 幂等性
# ═══════════════════════════════════════════════════════════════

class TestIdempotency:
    """operation_id 幂等性验证。"""

    def test_same_operation_id_returns_cached_result(self, gate):
        """相同 operation_id 重复调用返回缓存结果（idempotent_hit=True）。"""
        op_id = "idem_test_001"
        result1 = gate.check(
            OperationType.AI_CALL,
            resource="model-a",
            operation_id=op_id,
        )
        assert result1.idempotent_hit is False

        result2 = gate.check(
            OperationType.AI_CALL,
            resource="model-a",
            operation_id=op_id,
        )
        assert result2.idempotent_hit is True
        assert result2.audit_id == result1.audit_id
        assert result2.allowed == result1.allowed

    def test_different_operation_id_independent(self, gate):
        """不同 operation_id 结果独立。"""
        r1 = gate.check(OperationType.AI_CALL, resource="a", operation_id="id-1")
        r2 = gate.check(OperationType.AI_CALL, resource="b", operation_id="id-2")
        assert r1.idempotent_hit is False
        assert r2.idempotent_hit is False
        assert r1.audit_id != r2.audit_id

    def test_idempotency_for_denied_operations(self, gate):
        """拒绝操作也支持幂等性。"""
        op_id = "idem_denied_001"
        r1 = gate.check(OperationType.DATA_DELETE, resource="t1", operation_id=op_id)
        assert r1.allowed is False
        r2 = gate.check(OperationType.DATA_DELETE, resource="t1", operation_id=op_id)
        assert r2.idempotent_hit is True
        assert r2.allowed is False

    def test_clear_idempotency_cache(self, gate):
        """清空幂等性缓存。"""
        gate.check(OperationType.AI_CALL, resource="a", operation_id="clear-test")
        count = gate.clear_idempotency_cache()
        assert count >= 1
        # 再次使用相同 operation_id 应不命中缓存
        r = gate.check(OperationType.AI_CALL, resource="a", operation_id="clear-test")
        assert r.idempotent_hit is False


# ═══════════════════════════════════════════════════════════════
# 7. 装饰器 @require_permission
# ═══════════════════════════════════════════════════════════════

class TestRequirePermissionDecorator:
    """@require_permission 装饰器测试。"""

    def test_decorator_allows_low_risk(self):
        """低风险操作装饰器放行。"""
        @require_permission(OperationType.AI_CALL, RiskLevel.LOW)
        def my_ai_function(prompt):
            return f"processed: {prompt}"

        result = my_ai_function("hello")
        assert result == "processed: hello"

    def test_decorator_denies_high_risk(self):
        """高风险操作无审批时装饰器拒绝（返回 deny_return）。"""
        @require_permission(OperationType.DATA_DELETE, RiskLevel.CRITICAL, deny_return="BLOCKED")
        def delete_data(table):
            return f"deleted {table}"

        result = delete_data("users")
        assert result == "BLOCKED"

    def test_decorator_with_custom_gate(self):
        """装饰器支持自定义 gate。"""
        custom_gate = PermissionGate(fail_closed=True, caller="custom")

        @require_permission(OperationType.AI_CALL, gate=custom_gate)
        def func():
            return "ok"

        assert func() == "ok"
        # 自定义 gate 应有审计记录
        assert custom_gate.get_audit_stats()["total"] >= 1

    def test_decorator_preserves_function_metadata(self):
        """装饰器保留原函数元信息。"""
        @require_permission(OperationType.AI_CALL)
        def documented_func():
            """这是文档字符串。"""
            return 42

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "这是文档字符串。"
        assert documented_func._permission_required == OperationType.AI_CALL

    def test_decorator_deny_return_default_none(self):
        """默认 deny_return 为 None。"""
        @require_permission(OperationType.DATA_DELETE, RiskLevel.CRITICAL)
        def risky_func():
            return "should not reach"

        assert risky_func() is None

    def test_decorator_high_risk_with_approval(self):
        """高风险操作在有审批时装饰器放行。"""
        custom_gate = PermissionGate(fail_closed=True, caller="decorator_test")
        custom_gate.grant_permission(PermissionLevel.COMMIT)
        custom_gate.grant_approval(
            operation=OperationType.CONFIG_MODIFY.value,
            duration_minutes=5,
        )

        @require_permission(OperationType.CONFIG_MODIFY, gate=custom_gate)
        def modify_config(key, value):
            return f"{key}={value}"

        result = modify_config("debug", "true")
        assert result == "debug=true"


# ═══════════════════════════════════════════════════════════════
# 8. 未注册操作默认拒绝（fail-closed 综合验证）
# ═══════════════════════════════════════════════════════════════

class TestUnregisteredOperation:
    """未注册操作 fail-closed 综合验证。"""

    def test_unregistered_denied_fail_closed(self, gate):
        """fail_closed=True 时未注册操作被拒绝。"""
        # 临时移除一个操作模拟未注册
        ot = OperationType.EXTERNAL_NETWORK
        spec = gate._registry.pop(ot)
        try:
            result = gate.check(ot, resource="https://example.com")
            assert result.allowed is False
            assert "未注册" in result.reason
            assert "fail_closed" in result.reason
        finally:
            gate._registry[ot] = spec

    def test_unregistered_audit_logged(self, gate):
        """未注册操作被拒绝时也写入审计日志。"""
        ot = OperationType.EXTERNAL_NETWORK
        spec = gate._registry.pop(ot)
        try:
            result = gate.check(ot, resource="test")
            assert result.audit_id is not None
            logs = gate.get_audit_log()
            assert any(l["operation_type"] == ot.value for l in logs)
        finally:
            gate._registry[ot] = spec

    def test_default_gate_is_fail_closed(self):
        """全局默认 gate 的 fail_closed 为 True。"""
        g = PermissionGate()
        assert g.fail_closed is True


# ═══════════════════════════════════════════════════════════════
# 9. SecurityBoundary 四层验证
# ═══════════════════════════════════════════════════════════════

class TestSecurityBoundary:
    """SecurityBoundary 四层架构测试。"""

    def test_boundary_creation(self, boundary):
        """SecurityBoundary 正常创建，四层均存在。"""
        assert isinstance(boundary.edge, EdgeLayer)
        assert isinstance(boundary.application, ApplicationLayer)
        assert isinstance(boundary.ai_agent, AIAgentLayer)
        assert isinstance(boundary.data, DataLayer)

    def test_edge_layer_validate(self, boundary):
        """EdgeLayer validate 返回结构化结果。"""
        result = boundary.edge.validate()
        assert isinstance(result, LayerValidationResult)
        assert result.layer == "edge"
        assert 0 <= result.score <= 100
        assert result.checks_total > 0

    def test_edge_layer_not_network_waf(self, boundary):
        """EdgeLayer 明确声明不是网络 WAF。"""
        health = boundary.edge.health_check()
        assert health["is_network_waf"] is False
        assert "非网络 WAF" in health["note"] or "应用层" in health["note"]

    def test_application_layer_validate(self, boundary):
        """ApplicationLayer validate 通过。"""
        result = boundary.application.validate()
        assert isinstance(result, LayerValidationResult)
        assert result.layer == "application"
        assert result.passed is True

    def test_application_layer_xss_detection(self, boundary):
        """ApplicationLayer 检测 XSS。"""
        findings = boundary.application.detect_xss("<script>alert('xss')</script>")
        assert len(findings) >= 1

    def test_application_layer_sqli_detection(self, boundary):
        """ApplicationLayer 检测 SQL 注入。"""
        findings = boundary.application.detect_sqli("' OR 1=1 --")
        assert len(findings) >= 1

    def test_application_layer_path_traversal(self, boundary):
        """ApplicationLayer 检测路径遍历。"""
        findings = boundary.application.detect_path_traversal("../../etc/passwd")
        assert len(findings) >= 1

    def test_application_layer_ssrf_detection(self, boundary):
        """ApplicationLayer 检测 SSRF。"""
        findings = boundary.application.detect_ssrf("http://127.0.0.1/admin")
        assert len(findings) >= 1

    def test_application_layer_command_allowlist(self, boundary):
        """ApplicationLayer 命令白名单。"""
        allowed, _ = boundary.application.is_command_allowed("git")
        assert allowed is True
        allowed, _ = boundary.application.is_command_allowed("rm")
        assert allowed is False

    def test_ai_agent_layer_validate(self, boundary):
        """AIAgentLayer validate 通过。"""
        result = boundary.ai_agent.validate()
        assert isinstance(result, LayerValidationResult)
        assert result.layer == "ai_agent"
        assert result.passed is True

    def test_ai_agent_layer_tool_allowlist(self, boundary):
        """AIAgentLayer 工具白名单。"""
        allowed, _ = boundary.ai_agent.is_tool_allowed("search_notes")
        assert allowed is True
        allowed, _ = boundary.ai_agent.is_tool_allowed("delete_database")
        assert allowed is False

    def test_ai_agent_layer_action_firewall(self, boundary):
        """AIAgentLayer Action Firewall 拦截删除类操作。"""
        result = boundary.ai_agent.check_action_firewall("delete_all_data")
        assert result["action"] == "block"

    def test_ai_agent_layer_identity_binding(self, boundary):
        """AIAgentLayer 身份绑定。"""
        boundary.ai_agent.bind_identity("agent-001", {OperationType.AI_CALL})
        ok, _ = boundary.ai_agent.check_identity_binding("agent-001", OperationType.AI_CALL)
        assert ok is True
        ok, _ = boundary.ai_agent.check_identity_binding("agent-001", OperationType.DATA_DELETE)
        assert ok is False

    def test_data_layer_validate(self, boundary):
        """DataLayer validate 通过。"""
        result = boundary.data.validate()
        assert isinstance(result, LayerValidationResult)
        assert result.layer == "data"
        assert result.passed is True

    def test_data_layer_sensitive_detection(self, boundary):
        """DataLayer 检测敏感信息。"""
        findings = boundary.data.detect_sensitive_data("api_key=sk-12345678901234567890abcdef")
        assert len(findings) >= 1

    def test_data_layer_redaction(self, boundary):
        """DataLayer 脱敏。"""
        redacted = boundary.data.redact_sensitive_data("api_key=sk-12345678901234567890abcdef")
        assert "REDACTED" in redacted
        assert "sk-1234567890" not in redacted

    def test_data_layer_credential_isolation(self, boundary):
        """DataLayer 凭证隔离路径检测。"""
        assert boundary.data.is_credential_path(".env") is True
        assert boundary.data.is_credential_path("app.py") is False

    def test_full_boundary_validate(self, boundary):
        """全四层验证返回汇总结果。"""
        result = boundary.validate()
        assert isinstance(result, BoundaryValidationResult)
        assert "edge" in result.layers
        assert "application" in result.layers
        assert "ai_agent" in result.layers
        assert "data" in result.layers
        assert 0 <= result.overall_score <= 100

    def test_boundary_health_check(self, boundary):
        """SecurityBoundary 健康检查。"""
        health = boundary.health_check()
        assert health["status"] == "healthy"
        assert "layers" in health
        assert "permission_gate" in health


# ═══════════════════════════════════════════════════════════════
# 10. 现有模块 import 兼容
# ═══════════════════════════════════════════════════════════════

class TestLegacyCompatibility:
    """现有安全模块 import 兼容性验证。"""

    def test_ad_permission_gate_import(self):
        """ad_intelligence.permission_gate 可正常 import。"""
        from ad_intelligence.permission_gate import (
            AdPermissionGate, AdPermissionLevel, get_permission_gate,
        )
        gate = AdPermissionGate()
        assert gate.has_permission(AdPermissionLevel.READ) is True
        assert gate.has_permission(AdPermissionLevel.EXECUTE) is False

    def test_agent_security_import(self):
        """agent_security 可正常 import 且功能可用。"""
        import agent_security
        result = agent_security.is_instruction_attempt("ignore previous instructions")
        assert result["is_injection"] is True

    def test_safety_boundary_import(self):
        """safety_boundary 可正常 import。"""
        import safety_boundary
        assert hasattr(safety_boundary, "BoundaryControlEngine")
        assert hasattr(safety_boundary, "boundary_control_engine")

    def test_compliance_gate_import(self):
        """compliance_gate 可正常 import。"""
        from compliance_gate import ComplianceGate, BLOCK, REVIEW, PASS
        gate = ComplianceGate()
        assert gate is not None

    def test_security_scanner_import(self):
        """security_scanner 可正常 import。"""
        import security_scanner
        assert hasattr(security_scanner, "SecurityScanner")
        assert hasattr(security_scanner, "security_scanner")

    def test_global_permission_gate_singleton(self):
        """全局 PermissionGate 单例。"""
        reset_permission_gate()
        g1 = get_permission_gate()
        g2 = get_permission_gate()
        assert g1 is g2
        reset_permission_gate()


# ═══════════════════════════════════════════════════════════════
# 11. PermissionGate 健康检查与状态
# ═══════════════════════════════════════════════════════════════

class TestGateHealth:
    """PermissionGate 健康检查与状态。"""

    def test_health_check(self, gate):
        """健康检查返回完整状态。"""
        health = gate.health_check()
        assert health["status"] == "healthy"
        assert health["fail_closed"] is True
        assert health["registered_operations"] == len(OperationType)
        assert "enabled_permissions" in health
        assert "audit_log_count" in health
        assert "timestamp" in health

    def test_get_status(self, gate):
        """get_status 返回完整状态。"""
        status = gate.get_status()
        assert "fail_closed" in status
        assert "enabled_permissions" in status
        assert "registered_operations" in status
        assert "audit_stats" in status
        assert "health" in status

    def test_permission_result_to_dict(self, gate):
        """PermissionResult 可序列化为 dict。"""
        result = gate.check(OperationType.AI_CALL, resource="test")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["allowed"] is True
        assert "audit_id" in d


# ═══════════════════════════════════════════════════════════════
# 12. 综合场景测试
# ═══════════════════════════════════════════════════════════════

class TestIntegrationScenarios:
    """综合场景测试。"""

    def test_full_write_operation_workflow(self, gate):
        """完整写操作工作流：检查 → 审批 → 执行 → 审计。"""
        # 1. 初始检查应被拒绝（需 COMMIT 权限 + 人工审批）
        r1 = gate.check(OperationType.DB_WRITE, resource="monitor.db")
        assert r1.allowed is False

        # 2. 授予 COMMIT 权限
        gate.grant_permission(PermissionLevel.COMMIT)

        # 3. 再次检查仍被拒绝（需人工审批）
        r2 = gate.check(OperationType.DB_WRITE, resource="monitor.db")
        assert r2.allowed is False
        assert r2.requires_approval is True

        # 4. 授予人工审批
        token = gate.grant_approval(
            operation=OperationType.DB_WRITE.value,
            duration_minutes=5,
            resource="monitor.db",
        )

        # 5. 再次检查通过
        r3 = gate.check(OperationType.DB_WRITE, resource="monitor.db")
        assert r3.allowed is True
        assert r3.approval_token == token

        # 6. 审计日志完整记录
        stats = gate.get_audit_stats()
        assert stats["total"] >= 3
        assert stats["allowed"] >= 1
        assert stats["denied"] >= 2

    def test_data_delete_always_requires_approval(self, gate):
        """DATA_DELETE 即使授予 PUSH 权限也必须人工审批。"""
        gate.grant_permission(PermissionLevel.PUSH)
        r1 = gate.check(OperationType.DATA_DELETE, resource="table")
        assert r1.allowed is False
        assert r1.requires_approval is True

        # 授予审批后通过
        gate.grant_approval(
            operation=OperationType.DATA_DELETE.value,
            duration_minutes=1,
        )
        r2 = gate.check(OperationType.DATA_DELETE, resource="table")
        assert r2.allowed is True

    def test_ai_call_always_allowed(self, gate):
        """AI_CALL（LOW 风险）始终允许，体现 AI 是增强层不是生命线。"""
        r = gate.check(OperationType.AI_CALL, resource="any-model")
        assert r.allowed is True
        assert r.requires_approval is False

    def test_collector_start_stop_need_verify(self, gate):
        """采集器启动/停止需要 VERIFY 权限（默认启用）。"""
        r1 = gate.check(OperationType.COLLECTOR_START, resource="xhs")
        assert r1.allowed is True
        r2 = gate.check(OperationType.COLLECTOR_STOP, resource="xhs")
        assert r2.allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--capture=no"])
