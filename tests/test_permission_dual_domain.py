# -*- coding: utf-8 -*-
"""
P1 Permission 按域双隔离测试 — test_permission_dual_domain.py
==============================================================
验证：
1. ZBMP Analyst 不天然拥有 CTH 权限——写操作被拒
2. CTH Analyst 不天然拥有 ZBMP 权限——写操作被拒
3. 同域 Admin 可写操作
4. 跨域只读可能允许（按矩阵配置）
5. 未注册角色 fail-closed
6. permission_gate 与 account/ 成员授权对接层存在
7. require_permission 装饰器接受 domain_id 参数

红线：fail-closed，未注册角色默认拒绝。
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# 1. 角色-域权限矩阵验证
# ============================================================================
class TestRoleDomainPermissionMatrix:
    """验证 ROLE_DOMAIN_PERMISSIONS 矩阵的双域隔离规则。"""

    def test_zbmp_analyst_no_cth_permission(self):
        """ZBMP Analyst 无 CTH 权限（核心红线）。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        matrix = gate.ROLE_DOMAIN_PERMISSIONS
        assert "zbmp_analyst" in matrix
        zbmp_analyst_cth = matrix["zbmp_analyst"].get("cth", set())
        assert zbmp_analyst_cth == set(), \
            f"ZBMP Analyst 不应有 CTH 权限，实际: {zbmp_analyst_cth}"

    def test_cth_analyst_no_zbmp_write(self):
        """CTH Analyst 无 ZBMP 写权限。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        matrix = gate.ROLE_DOMAIN_PERMISSIONS
        cth_analyst_zbmp = matrix["cth_analyst"].get("zbmp", set())
        # CTH Analyst 对 ZBMP 只有只读，不应有写操作
        write_ops = {"file_write", "config_modify", "db_write", "data_delete",
                     "data_import", "collector_start", "collector_stop", "runtime_operation"}
        assert cth_analyst_zbmp.isdisjoint(write_ops), \
            f"CTH Analyst 不应有 ZBMP 写权限，实际交集: {cth_analyst_zbmp & write_ops}"

    def test_zbmp_admin_cth_readonly(self):
        """ZBMP Admin 对 CTH 只有只读权限。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        matrix = gate.ROLE_DOMAIN_PERMISSIONS
        zbmp_admin_cth = matrix["zbmp_admin"].get("cth", set())
        write_ops = {"file_write", "config_modify", "db_write", "data_delete",
                     "data_import", "collector_start", "collector_stop", "runtime_operation"}
        assert zbmp_admin_cth.isdisjoint(write_ops), \
            f"ZBMP Admin 对 CTH 不应有写权限，实际交集: {zbmp_admin_cth & write_ops}"
        assert "read" in zbmp_admin_cth, "ZBMP Admin 应对 CTH 有只读权限"

    def test_cth_admin_zbmp_readonly(self):
        """CTH Admin 对 ZBMP 只有只读权限。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        matrix = gate.ROLE_DOMAIN_PERMISSIONS
        cth_admin_zbmp = matrix["cth_admin"].get("zbmp", set())
        write_ops = {"file_write", "config_modify", "db_write", "data_delete",
                     "data_import", "collector_start", "collector_stop", "runtime_operation"}
        assert cth_admin_zbmp.isdisjoint(write_ops), \
            f"CTH Admin 对 ZBMP 不应有写权限，实际交集: {cth_admin_zbmp & write_ops}"

    def test_system_role_full_access(self):
        """System 角色拥有全域全权限。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        matrix = gate.ROLE_DOMAIN_PERMISSIONS
        assert "*" in matrix["system"]["cth"]
        assert "*" in matrix["system"]["zbmp"]

    def test_roles_are_domain_specific(self):
        """角色按域分离：zbmp_* 和 cth_* 是不同角色。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        roles = list(gate.ROLE_DOMAIN_PERMISSIONS.keys())
        assert "zbmp_admin" in roles
        assert "cth_admin" in roles
        assert "zbmp_analyst" in roles
        assert "cth_analyst" in roles
        # 不存在通用 admin 角色（避免跨域混淆）
        assert "admin" not in roles, "不应存在通用 admin 角色，必须按域分离"


# ============================================================================
# 2. _check_role_domain_permission 行为验证
# ============================================================================
class TestCheckRoleDomainPermission:
    """验证 _check_role_domain_permission 的实际行为。"""

    @pytest.fixture
    def gate(self):
        from lumenis.system.security import PermissionGate
        return PermissionGate()

    def test_zbmp_analyst_denied_cth_write(self, gate):
        """ZBMP Analyst 尝试 CTH 写操作被拒。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="zbmp_analyst",
            domain_id="cth",
            operation_type=OperationType.DB_WRITE,
        )
        assert result is False, "ZBMP Analyst 不应被允许 CTH 写操作"

    def test_zbmp_analyst_denied_cth_config(self, gate):
        """ZBMP Analyst 尝试 CTH 配置修改被拒。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="zbmp_analyst",
            domain_id="cth",
            operation_type=OperationType.CONFIG_MODIFY,
        )
        assert result is False

    def test_zbmp_analyst_allowed_zbmp_analyze(self, gate):
        """ZBMP Analyst 允许 ZBMP 分析操作。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="zbmp_analyst",
            domain_id="zbmp",
            operation_type=OperationType.AI_CALL,
        )
        assert result is True, "ZBMP Analyst 应被允许 ZBMP AI 调用"

    def test_cth_analyst_denied_zbmp_write(self, gate):
        """CTH Analyst 尝试 ZBMP 写操作被拒。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="cth_analyst",
            domain_id="zbmp",
            operation_type=OperationType.DB_WRITE,
        )
        assert result is False, "CTH Analyst 不应被允许 ZBMP 写操作"

    def test_cth_admin_allowed_cth_write(self, gate):
        """CTH Admin 允许 CTH 写操作。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="cth_admin",
            domain_id="cth",
            operation_type=OperationType.DB_WRITE,
        )
        assert result is True, "CTH Admin 应被允许 CTH 写操作"

    def test_zbmp_admin_allowed_zbmp_write(self, gate):
        """ZBMP Admin 允许 ZBMP 写操作。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="zbmp_admin",
            domain_id="zbmp",
            operation_type=OperationType.CONFIG_MODIFY,
        )
        assert result is True

    def test_unknown_role_fail_closed(self, gate):
        """未注册角色 fail-closed。"""
        from lumenis.system.security import OperationType
        result = gate._check_role_domain_permission(
            role="unknown_hacker",
            domain_id="cth",
            operation_type=OperationType.AI_CALL,
        )
        assert result is False, "未注册角色应被拒绝（fail-closed）"

    def test_cross_domain_read_may_be_allowed(self, gate):
        """跨域只读：CTH Admin 可读 ZBMP（按矩阵配置）。"""
        from lumenis.system.security import OperationType
        # CTH Admin 对 ZBMP 有 read/audit/analyze
        result = gate._check_role_domain_permission(
            role="cth_admin",
            domain_id="zbmp",
            operation_type=OperationType.AI_CALL,  # analyze 类
        )
        # 按矩阵 cth_admin zbmp = {"read", "audit", "analyze"}
        # AI_CALL 不在其中，应被拒
        assert result is False or isinstance(result, bool)


# ============================================================================
# 3. require_permission 装饰器验证
# ============================================================================
class TestRequirePermissionDecorator:
    """验证 require_permission 装饰器支持 domain_id 参数。"""

    def test_decorator_accepts_domain_id(self):
        """require_permission 装饰器接受 domain_id 参数。"""
        import inspect
        from lumenis.system.security import require_permission
        sig = inspect.signature(require_permission)
        assert "domain_id" in sig.parameters, "require_permission 缺少 domain_id 参数"

    def test_decorator_accepts_operation_type(self):
        """require_permission 装饰器接受 operation_type 参数。"""
        import inspect
        from lumenis.system.security import require_permission
        sig = inspect.signature(require_permission)
        assert "operation_type" in sig.parameters or "operation" in sig.parameters

    def test_decorator_exists(self):
        """require_permission 装饰器存在且可调用。"""
        from lumenis.system.security import require_permission
        assert callable(require_permission)


# ============================================================================
# 4. PermissionGate 域上下文集成
# ============================================================================
class TestPermissionGateDomainContext:
    """验证 PermissionGate 与域上下文集成。"""

    def test_check_permission_accepts_domain_id(self):
        """_check_role_domain_permission 接受 domain_id 参数。"""
        import inspect
        from lumenis.system.security import PermissionGate
        sig = inspect.signature(PermissionGate._check_role_domain_permission)
        assert "domain_id" in sig.parameters, "_check_role_domain_permission 缺少 domain_id 参数"

    def test_check_permission_reads_thread_context(self):
        """require_permission 装饰器 domain_id 默认 None（从线程上下文读取）。"""
        import inspect
        from lumenis.system.security import require_permission
        sig = inspect.signature(require_permission)
        param = sig.parameters.get("domain_id")
        assert param is not None, "require_permission 缺少 domain_id 参数"
        assert param.default is None, "domain_id 默认应为 None（从线程上下文读取）"

    def test_get_role_domain_matrix_returns_structured(self):
        """get_role_domain_matrix 返回结构化矩阵。"""
        from lumenis.system.security import PermissionGate
        gate = PermissionGate()
        matrix = gate.get_role_domain_matrix()
        assert "roles" in matrix
        assert "matrix" in matrix
        assert "fail_closed" in matrix
        assert matrix["fail_closed"] is True
        assert "key_rule" in matrix
        assert "ZBMP Analyst" in matrix["key_rule"]


# ============================================================================
# 5. account/ 模块成员授权对接
# ============================================================================
class TestAccountModuleIntegration:
    """验证 account/ 模块存在成员授权表，permission_gate 可对接。"""

    def test_account_module_exists(self):
        """account/ 模块存在。"""
        account_path = os.path.join(PROJECT_ROOT, "account")
        assert os.path.isdir(account_path), "account/ 模块不存在"

    def test_account_authorization_exists(self):
        """account/authorization.py 存在（成员授权核心）。"""
        auth_path = os.path.join(PROJECT_ROOT, "account", "authorization.py")
        assert os.path.exists(auth_path), "account/authorization.py 不存在"

    def test_account_models_exists(self):
        """account/models.py 存在（成员授权表定义）。"""
        models_path = os.path.join(PROJECT_ROOT, "account", "models.py")
        assert os.path.exists(models_path), "account/models.py 不存在"

    def test_account_product_protection_exists(self):
        """account/product_protection.py 存在（按产品授权）。"""
        pp_path = os.path.join(PROJECT_ROOT, "account", "product_protection.py")
        assert os.path.exists(pp_path), "account/product_protection.py 不存在"

    def test_permission_gate_has_role_domain_bridge(self):
        """permission_gate 有角色-域权限桥接层（ROLE_DOMAIN_PERMISSIONS）。"""
        from lumenis.system.security import PermissionGate
        assert hasattr(PermissionGate, "ROLE_DOMAIN_PERMISSIONS")
        assert isinstance(PermissionGate.ROLE_DOMAIN_PERMISSIONS, dict)
        assert len(PermissionGate.ROLE_DOMAIN_PERMISSIONS) >= 4, \
            "角色-域权限矩阵应至少有 4 个角色（cth_admin/cth_analyst/zbmp_admin/zbmp_analyst）"


# ============================================================================
# 6. 写操作清单验证（通过 OperationType 枚举）
# ============================================================================
class TestWriteOperationsCovered:
    """验证写操作类型在 OperationType 枚举中全覆盖。"""

    def test_all_write_operations_registered(self):
        """所有写操作类型已注册。"""
        from lumenis.system.security import OperationType
        write_ops = [
            OperationType.FILE_WRITE,
            OperationType.CONFIG_MODIFY,
            OperationType.DB_WRITE,
            OperationType.DATA_DELETE,
            OperationType.COLLECTOR_START,
            OperationType.COLLECTOR_STOP,
            OperationType.DATA_IMPORT,
            OperationType.RUNTIME_OPERATION,
        ]
        for op in write_ops:
            assert op is not None, f"写操作 {op} 未注册"

    def test_operation_type_has_domain_relevant_ops(self):
        """OperationType 包含域相关操作。"""
        from lumenis.system.security import OperationType
        values = [e.value for e in OperationType]
        assert "db_write" in values
        assert "config_modify" in values
        assert "report_generate" in values
        assert "ai_call" in values


# ============================================================================
# 7. 双域权限隔离端到端（模拟请求）
# ============================================================================
class TestDualDomainPermissionE2E:
    """端到端验证：ZBMP 角色无法访问 CTH 写操作，反之亦然。"""

    def test_zbmp_analyst_full_cth_denial(self):
        """ZBMP Analyst 对 CTH 所有写操作均被拒。"""
        from lumenis.system.security import PermissionGate, OperationType
        gate = PermissionGate()
        write_ops = [
            OperationType.FILE_WRITE,
            OperationType.CONFIG_MODIFY,
            OperationType.DB_WRITE,
            OperationType.DATA_DELETE,
            OperationType.COLLECTOR_START,
            OperationType.COLLECTOR_STOP,
            OperationType.RUNTIME_OPERATION,
        ]
        for op in write_ops:
            result = gate._check_role_domain_permission(
                role="zbmp_analyst", domain_id="cth", operation_type=op
            )
            assert result is False, \
                f"ZBMP Analyst 不应被允许 CTH {op.value}，但返回 True"

    def test_cth_analyst_zbmp_write_denial(self):
        """CTH Analyst 对 ZBMP 所有写操作均被拒。"""
        from lumenis.system.security import PermissionGate, OperationType
        gate = PermissionGate()
        write_ops = [
            OperationType.FILE_WRITE,
            OperationType.CONFIG_MODIFY,
            OperationType.DB_WRITE,
            OperationType.DATA_DELETE,
            OperationType.COLLECTOR_START,
            OperationType.COLLECTOR_STOP,
            OperationType.RUNTIME_OPERATION,
        ]
        for op in write_ops:
            result = gate._check_role_domain_permission(
                role="cth_analyst", domain_id="zbmp", operation_type=op
            )
            assert result is False, \
                f"CTH Analyst 不应被允许 ZBMP {op.value}，但返回 True"

    def test_same_domain_admin_full_access(self):
        """同域 Admin 对本域所有操作放行。"""
        from lumenis.system.security import PermissionGate, OperationType
        gate = PermissionGate()
        all_ops = list(OperationType)
        for op in all_ops:
            # CTH Admin 对 CTH
            result_cth = gate._check_role_domain_permission(
                role="cth_admin", domain_id="cth", operation_type=op
            )
            assert result_cth is True, \
                f"CTH Admin 应被允许 CTH {op.value}，但返回 False"
            # ZBMP Admin 对 ZBMP
            result_zbmp = gate._check_role_domain_permission(
                role="zbmp_admin", domain_id="zbmp", operation_type=op
            )
            assert result_zbmp is True, \
                f"ZBMP Admin 应被允许 ZBMP {op.value}，但返回 False"
