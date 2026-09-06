# -*- coding: utf-8 -*-
"""
Permission 域感知测试（ZBC V2.0）
==================================
覆盖：
  1. 权限检查包含 domain_id
  2. ZBMP Analyst 不天然拥有 CTH Admin 权限
  3. require_permission 装饰器支持 domain_id 参数
  4. 危险操作 deny by default（域感知后仍生效）
  5. 角色-域权限矩阵
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from permission_gate import (
    PermissionGate, PermissionLevel, RiskLevel, OperationType,
    require_permission, get_permission_gate, reset_permission_gate,
)


@pytest.fixture
def gate():
    return PermissionGate(fail_closed=True, caller="test_runner")


class TestRoleDomainPermissions:
    """验证角色-域权限映射。"""

    def test_role_matrix_exists(self):
        matrix = PermissionGate.ROLE_DOMAIN_PERMISSIONS
        assert "cth_admin" in matrix
        assert "cth_analyst" in matrix
        assert "zbmp_admin" in matrix
        assert "zbmp_analyst" in matrix
        assert "system" in matrix

    def test_zbmp_analyst_no_cth_permission(self):
        """ZBMP Analyst 在 CTH 域无任何权限。"""
        perms = PermissionGate.ROLE_DOMAIN_PERMISSIONS["zbmp_analyst"]
        assert perms.get("cth") == set()

    def test_zbmp_analyst_has_zbmp_permission(self):
        perms = PermissionGate.ROLE_DOMAIN_PERMISSIONS["zbmp_analyst"]
        assert "zbmp" in perms
        assert len(perms["zbmp"]) > 0

    def test_cth_admin_has_cth_all(self):
        perms = PermissionGate.ROLE_DOMAIN_PERMISSIONS["cth_admin"]
        assert "*" in perms["cth"]

    def test_cth_admin_limited_zbmp(self):
        """CTH Admin 在 ZBMP 域只有只读权限。"""
        perms = PermissionGate.ROLE_DOMAIN_PERMISSIONS["cth_admin"]
        zbmp_perms = perms.get("zbmp", set())
        assert "*" not in zbmp_perms
        assert "read" in zbmp_perms

    def test_zbmp_admin_limited_cth(self):
        """ZBMP Admin 在 CTH 域只有只读权限。"""
        perms = PermissionGate.ROLE_DOMAIN_PERMISSIONS["zbmp_admin"]
        cth_perms = perms.get("cth", set())
        assert "*" not in cth_perms
        assert "read" in cth_perms


class TestDomainAwareCheck:
    """验证 check() 方法的域感知。"""

    def test_zbmp_analyst_denied_cth_write(self, gate):
        """ZBMP Analyst 尝试 CTH 域写操作应被拒绝。"""
        result = gate.check(
            OperationType.FILE_WRITE,
            resource="/cth/data/config.json",
            domain_id="cth",
            role="zbmp_analyst",
        )
        assert result.allowed is False
        assert "跨域" in result.reason or "domain" in result.reason.lower()

    def test_zbmp_analyst_denied_cth_db_write(self, gate):
        result = gate.check(
            OperationType.DB_WRITE,
            resource="cth_notes",
            domain_id="cth",
            role="zbmp_analyst",
        )
        assert result.allowed is False

    def test_zbmp_analyst_allowed_zbmp_read(self, gate):
        """ZBMP Analyst 在 ZBMP 域的读/分析操作应允许。"""
        result = gate.check(
            OperationType.AI_CALL,
            resource="zbmp_analysis",
            domain_id="zbmp",
            role="zbmp_analyst",
        )
        # AI_CALL 是 LOW 风险，ANALYZE 权限，ZBMP Analyst 应有
        assert result.allowed is True or result.requires_approval is False

    def test_cth_admin_allowed_cth_write(self, gate):
        result = gate.check(
            OperationType.FILE_WRITE,
            resource="/cth/data",
            domain_id="cth",
            role="cth_admin",
        )
        # CTH Admin 有 CTH 域全部权限，但 FILE_WRITE 是 MEDIUM 风险
        # 需要 PATCH_PREVIEW 权限，默认启用
        assert result.allowed is True

    def test_system_role_all_domains(self, gate):
        """system 角色在所有域都有权限。"""
        for domain in ["cth", "zbmp"]:
            result = gate.check(
                OperationType.AI_CALL,
                resource="test",
                domain_id=domain,
                role="system",
            )
            assert result.allowed is True

    def test_unknown_role_denied(self, gate):
        """未注册角色默认拒绝（fail-closed）。"""
        result = gate.check(
            OperationType.AI_CALL,
            resource="test",
            domain_id="cth",
            role="unknown_role_xyz",
        )
        assert result.allowed is False

    def test_result_contains_domain_id(self, gate):
        result = gate.check(
            OperationType.AI_CALL,
            resource="test",
            domain_id="cth",
            role="system",
        )
        assert result.domain_id == "cth"


class TestCrossDomainWriteDenied:
    """验证跨域写操作默认拒绝。"""

    def test_cth_analyst_denied_zbmp_write(self, gate):
        result = gate.check(
            OperationType.DB_WRITE,
            resource="zbmp_table",
            domain_id="zbmp",
            role="cth_analyst",
        )
        assert result.allowed is False

    def test_zbmp_admin_denied_cth_delete(self, gate):
        """ZBMP Admin 在 CTH 域不能删除数据。"""
        result = gate.check(
            OperationType.DATA_DELETE,
            resource="cth_records",
            domain_id="cth",
            role="zbmp_admin",
        )
        assert result.allowed is False


class TestDenyByDefault:
    """验证危险操作 deny by default 在域感知后仍生效。"""

    def test_data_delete_requires_approval(self, gate):
        result = gate.check(
            OperationType.DATA_DELETE,
            resource="test_table",
            domain_id="cth",
            role="cth_admin",
        )
        # DATA_DELETE 是 CRITICAL 风险，需要人工审批
        assert result.allowed is False or result.requires_approval is True

    def test_unregistered_operation_denied(self, gate):
        """未注册操作在 fail_closed=True 时默认拒绝。"""
        from permission_gate import OperationType
        # 用一个不存在的操作类型
        class FakeOp:
            value = "nonexistent_operation"
        result = gate.check(
            FakeOp(),
            resource="test",
            domain_id="cth",
            role="system",
        )
        assert result.allowed is False


class TestRequirePermissionDecorator:
    """验证 require_permission 装饰器支持 domain_id。"""

    def test_decorator_accepts_domain_id(self):
        """装饰器应能接受 domain_id 参数。"""
        @require_permission(OperationType.AI_CALL, domain_id="cth", role="system")
        def my_func():
            return "executed"

        result = my_func()
        # system 角色在 cth 域有 AI_CALL 权限
        assert result == "executed"

    def test_decorator_denies_cross_domain(self):
        @require_permission(OperationType.FILE_WRITE, domain_id="cth", role="zbmp_analyst")
        def sensitive_func():
            return "should_not_execute"

        result = sensitive_func()
        assert result is None  # deny_return 默认 None

    def test_decorator_with_custom_deny_return(self):
        @require_permission(
            OperationType.DB_WRITE, domain_id="cth", role="zbmp_analyst",
            deny_return={"error": "forbidden"},
        )
        def func():
            return "ok"

        result = func()
        assert result == {"error": "forbidden"}


class TestRoleDomainMatrix:
    def test_get_role_domain_matrix(self, gate):
        matrix = gate.get_role_domain_matrix()
        assert "roles" in matrix
        assert "matrix" in matrix
        assert "zbmp_analyst" in matrix["roles"]
        assert matrix["fail_closed"] is True
        assert "ZBMP Analyst" in matrix["key_rule"]
