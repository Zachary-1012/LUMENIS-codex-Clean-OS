# -*- coding: utf-8 -*-
"""
ZBC AI Task Permission Matrix 测试套件
========================================
覆盖：
  1. 越权DENY测试（永久DENY/Admin需求/未注册操作）
  2. 人工审批流程（L3/L4任务 → awaiting_approval → approve → execute）
  3. Permission Matrix六级粒度（READ/ANALYZE/ACT/WRITE/HIGH_RISK/ADMIN）
  4. fail-closed原则验证
  5. Case4: 高风险动作DENY
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_task_parser import TaskParser, Intent, TaskRiskLevel, get_task_parser, reset_task_parser
from ai_task_engine import (
    TaskEngine, TaskStatus, init_task_engine_db,
    get_task_engine, reset_task_engine,
)
from lumenis.system.security import (
    PermissionGate, PermissionLevel, RiskLevel, OperationType,
    get_permission_gate, reset_permission_gate, set_testing_bypass,
)


@pytest.fixture
def parser():
    reset_task_parser()
    return get_task_parser()


@pytest.fixture
def engine():
    reset_task_engine()
    init_task_engine_db()
    return get_task_engine()


@pytest.fixture
def gate():
    reset_permission_gate()
    return get_permission_gate()


# ═══════════════════════════════════════════════════════════════
# 1. 永久DENY测试
# ═══════════════════════════════════════════════════════════════

class TestPermanentDeny:
    def test_payment_permanently_denied(self, parser):
        """支付操作永久DENY"""
        result = parser.parse("帮我支付100元")
        assert result.permanent_deny is True
        assert result.risk_level == TaskRiskLevel.L4

    def test_payment_variants_denied(self, parser):
        for text in ["付款", "转账", "充值", "提现", "pay now"]:
            result = parser.parse(text)
            assert result.permanent_deny is True, f"{text} should be permanently denied"

    def test_permanent_deny_blocks_execution(self, engine):
        """永久DENY任务在parse阶段即被终止，不进入执行"""
        created = engine.create_task("帮我支付100元")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["permanent_deny"] == 1
        assert "PERMANENT_DENY" in result["error"]


# ═══════════════════════════════════════════════════════════════
# 2. Admin需求测试
# ═══════════════════════════════════════════════════════════════

class TestAdminRequired:
    def test_delete_data_requires_admin(self, parser):
        result = parser.parse("删除数据库所有表")
        assert result.admin_required is True
        assert result.risk_level == TaskRiskLevel.L4

    def test_modify_config_requires_admin(self, parser):
        result = parser.parse("修改系统核心配置")
        assert result.admin_required is True

    def test_modify_code_requires_admin(self, parser):
        result = parser.parse("修改生产代码并部署")
        assert result.admin_required is True

    def test_admin_required_blocks_execution(self, engine):
        """Admin需求任务在parse阶段即被终止（当前系统无Admin角色）"""
        created = engine.create_task("删除数据库所有表")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["admin_required"] == 1
        assert "ADMIN_REQUIRED" in result["error"]


# ═══════════════════════════════════════════════════════════════
# 3. 人工审批流程测试
# ═══════════════════════════════════════════════════════════════

class TestHumanApproval:
    def test_publish_requires_approval(self, parser):
        result = parser.parse("帮我发布一条小红书笔记")
        assert result.human_approval_required is True
        assert result.risk_level == TaskRiskLevel.L3

    def test_login_requires_approval(self, parser):
        result = parser.parse("帮我登录账号")
        assert result.human_approval_required is True

    def test_upload_requires_approval(self, parser):
        result = parser.parse("上传一个文件")
        assert result.human_approval_required is True

    def test_send_message_requires_approval(self, parser):
        result = parser.parse("发送消息给用户")
        assert result.human_approval_required is True

    def test_approval_flow_awaiting_then_approve(self, engine):
        """完整人工审批流程：创建 → parse(awaiting) → approve → execute"""
        created = engine.create_task("帮我发布一条笔记")

        # parse后应为awaiting_approval
        parsed = engine.parse_task(created["task_id"])
        assert parsed["status"] == TaskStatus.AWAITING_APPROVAL.value

        # 审批后应为ready
        approved = engine.approve_task(created["task_id"], approved_by="tester", approval_note="test approval")
        assert approved["status"] == TaskStatus.READY.value
        assert approved["approval_token"] is not None
        assert approved["approved_by"] == "tester"

        # 执行后应成功（或因intent=unknown而失败，但不应是awaiting）
        result = engine.run_task(created["task_id"])
        assert result["status"] in (TaskStatus.SUCCEEDED.value, TaskStatus.FAILED.value)
        assert result["status"] != TaskStatus.AWAITING_APPROVAL.value

    def test_l3_risk_triggers_approval(self, parser):
        """L3风险等级任务应触发人工审批"""
        result = parser.parse("帮我发布内容")
        assert result.risk_level == TaskRiskLevel.L3
        assert result.human_approval_required is True

    def test_l4_risk_triggers_approval_or_deny(self, parser):
        """L4风险等级任务应被DENY或需审批"""
        result = parser.parse("删除数据")
        assert result.risk_level == TaskRiskLevel.L4


# ═══════════════════════════════════════════════════════════════
# 4. Permission Gate 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPermissionGateIntegration:
    @pytest.fixture(autouse=True)
    def _explicit_system_domain_for_gate_checks(self):
        """Low-level gate behavior is evaluated in an explicit SYSTEM domain."""
        from domain_isolation import (
            DomainContext, clear_domain_context, get_domain_context,
            set_domain_context,
        )
        from subject_context import (
            clear_thread_context, get_thread_context, set_thread_context,
        )

        prior_domain = get_domain_context()
        prior_thread = get_thread_context()
        clear_domain_context()
        clear_thread_context()
        set_domain_context(DomainContext(domain_id="system", product_id="SYSTEM"))
        yield
        clear_domain_context()
        clear_thread_context()
        if prior_domain is not None:
            set_domain_context(prior_domain)
        if prior_thread is not None:
            set_thread_context(prior_thread)

    @pytest.fixture(autouse=True)
    def _strict_permission_gate(self):
        # 本类验证权限门严格模式（fail-closed/高风险审批/审计/审批令牌），必须关闭 TESTING 旁路
        set_testing_bypass(False)
        yield
        set_testing_bypass(True)

    def test_gate_fail_closed_unregistered_operation(self, gate):
        """未注册操作默认拒绝（fail-closed）"""
        class FakeOp:
            value = "unregistered_test_op"
        result = gate.check(FakeOp(), resource="test")
        assert result.allowed is False

    def test_gate_high_risk_requires_approval(self, gate):
        """高风险操作需人工审批（先启用PUSH权限使检查到达审批阶段）"""
        gate.grant_permission(PermissionLevel.PUSH)
        result = gate.check(OperationType.DATA_DELETE, resource="test_table")
        assert result.allowed is False
        assert result.requires_approval is True

    def test_gate_low_risk_allowed(self, gate):
        """低风险操作（AI调用）应允许"""
        result = gate.check(OperationType.AI_CALL, resource="test")
        assert result.allowed is True

    def test_gate_audit_logged(self, gate):
        """所有权限检查应有审计记录"""
        gate.check(OperationType.AI_CALL, resource="audit_test")
        stats = gate.get_audit_stats()
        assert stats["total"] >= 1

    def test_gate_approval_token_works(self, gate):
        """审批令牌可解锁高风险操作"""
        gate.grant_permission(PermissionLevel.PUSH)
        # 先拒绝
        result1 = gate.check(OperationType.DATA_DELETE, resource="token_test")
        assert result1.allowed is False

        # 授予审批（operation 传字符串）
        token = gate.grant_approval("data_delete", duration_minutes=5, resource="token_test")
        assert token is not None

        # 再次检查应通过
        result2 = gate.check(OperationType.DATA_DELETE, resource="token_test")
        assert result2.allowed is True

    def test_gate_enabled_permissions(self, gate):
        """默认启用权限应包含READ/ANALYZE等低等级"""
        perms = gate.get_enabled_permissions()
        assert "read" in perms
        assert "analyze" in perms


# ═══════════════════════════════════════════════════════════════
# 5. Case4: 高风险动作DENY（E2E）
# ═══════════════════════════════════════════════════════════════

class TestCase4HighRiskDeny:
    def test_case4_delete_denied(self, engine):
        """Case4: 高风险动作（删除数据）DENY"""
        created = engine.create_task("删除数据库所有表")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["risk_level"] == "L4"
        assert result["admin_required"] == 1
        assert "ADMIN_REQUIRED" in result["error"]

        # 应有DENY evidence
        evidence = engine.get_evidence(created["task_id"])
        assert any(e["evidence_type"] == "permission_deny" for e in evidence)

    def test_case4_payment_denied(self, engine):
        """Case4变体: 支付永久DENY"""
        created = engine.create_task("帮我支付100元")
        result = engine.run_task(created["task_id"])
        assert result["status"] == TaskStatus.FAILED.value
        assert result["permanent_deny"] == 1
        assert "PERMANENT_DENY" in result["error"]

    def test_case4_no_execution_for_denied(self, engine):
        """被DENY的任务不应进入execute阶段"""
        created = engine.create_task("删除数据库所有表")
        engine.run_task(created["task_id"])
        steps = engine.get_steps(created["task_id"])
        step_phases = [s["phase"] for s in steps]
        assert "execute" not in step_phases, "Denied task should not reach execute phase"


# ═══════════════════════════════════════════════════════════════
# 6. fail-closed原则验证
# ═══════════════════════════════════════════════════════════════

class TestFailClosed:
    def test_unknown_intent_is_l3(self, parser):
        """未知Intent应为L3（fail-closed，需人工审查）"""
        result = parser.parse("asdfghjkl随机无意义文本")
        assert result.intent == Intent.UNKNOWN
        assert result.risk_level == TaskRiskLevel.L3

    def test_empty_input_is_unknown(self, parser):
        result = parser.parse("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0

    def test_no_agent_for_unknown_intent(self, engine):
        """未知Intent任务不应找到Agent"""
        created = engine.create_task("asdfghjkl随机无意义文本")
        engine.parse_task(created["task_id"])
        # 未知intent → L3 → awaiting_approval，不会到agent选择
        task = engine.get_task(created["task_id"])
        assert task["status"] == TaskStatus.AWAITING_APPROVAL.value
