from lumenis.system.security import (
    ActionRequest,
    AgentAction,
    OperationType,
    PermissionGate,
    PermissionLevel,
    get_effect_fence,
    validate_action,
)


def test_action_firewall_consumes_canonical_permission():
    gate = PermissionGate()
    permission = gate.check(
        OperationType.SKILL_EXECUTE,
        resource="skill:test",
        caller="test",
        operation_id="fw-read-1",
        domain_id="system",
    )
    assert permission.allowed is True

    result = validate_action(
        ActionRequest(
            identity="test-agent",
            intent="analyze",
            tool="skill:test",
            parameters={},
            target="staging",
            scope="system",
            action=AgentAction.ANALYZE,
        ),
        permission_result=permission,
    )
    assert result.allowed is True
    assert result.checks["permission"]["verified"] is True


def test_action_firewall_rejects_action_type_spoofing():
    result = validate_action(
        ActionRequest(
            identity="test-agent",
            intent="pretend read",
            tool="deploy_runtime",
            parameters={},
            target="staging",
            scope="system",
            action=AgentAction.ANALYZE,
        )
    )
    assert result.allowed is False
    assert result.risk_level == "CRITICAL"


def test_effect_fence_blocks_unstaged_write_before_execution():
    fence = get_effect_fence()
    fence.clear_for_testing()
    result = fence.check(
        action=AgentAction.WRITE,
        target="working_copy",
        payload={"value": 1},
        operation_id="write-no-stage",
    )
    assert result.allowed is False
    assert result.requires_staging is True
    assert result.auto_admit is False


def test_effect_fence_hard_denies_production_truth_mutation():
    fence = get_effect_fence()
    fence.clear_for_testing()
    result = fence.check(
        action=AgentAction.WRITE,
        target="production_db:zbc_canonical_data",
        payload={"staging": True},
        operation_id="prod-write",
    )
    assert result.allowed is False
    assert result.effect_mode == "blocked"


def test_effect_fence_idempotency_blocks_duplicate_side_effect():
    fence = get_effect_fence()
    fence.clear_for_testing()
    payload = {"staging": True, "value": 1}

    first = fence.check(
        action=AgentAction.WRITE,
        target="staging_db",
        payload=payload,
        operation_id="same-operation",
    )
    second = fence.check(
        action=AgentAction.WRITE,
        target="staging_db",
        payload=payload,
        operation_id="same-operation",
    )

    assert first.allowed is True
    assert first.reservation_status == "reserved"
    assert second.allowed is False
    assert second.idempotent_hit is True


def test_high_risk_permission_still_requires_human_approval(monkeypatch):
    # conftest enables an explicit global TESTING bypass for broad suites;
    # this contract test must exercise the production fail-closed path.
    from lumenis.system.security import permission as permission_module
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    gate = PermissionGate()
    gate.grant_permission(PermissionLevel.COMMIT)

    denied = gate.check(
        OperationType.DB_WRITE,
        resource="staging_db",
        caller="test",
        operation_id="write-approval-1",
        domain_id="system",
    )
    assert denied.allowed is False
    assert denied.requires_approval is True

    gate.grant_approval(OperationType.DB_WRITE.value, duration_minutes=5)
    allowed = gate.check(
        OperationType.DB_WRITE,
        resource="staging_db",
        caller="test",
        operation_id="write-approval-2",
        domain_id="system",
    )
    assert allowed.allowed is True
    assert allowed.approval_token


def test_agent_runtime_uses_canonical_security_and_completes_fence(monkeypatch):
    from agent_runtime.loop import AgentLoop
    from agent_runtime.planner import PlanStep
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    from lumenis.system.security import (
        AgentAction,
        OperationType,
        PermissionLevel,
        get_effect_fence,
        is_testing_bypass_enabled,
        set_testing_bypass,
    )

    previous_bypass = is_testing_bypass_enabled()
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    set_testing_bypass(False)
    fence = get_effect_fence()
    fence.clear_for_testing()

    try:
        gate = PermissionGate()
        gate.grant_permission(PermissionLevel.COMMIT)
        gate.grant_approval(OperationType.DB_WRITE.value, duration_minutes=5)

        loop = AgentLoop(
            permission_gate=gate,
            durable_adapter=DurableExecutionAdapter(enabled=False),
            tool_executor=lambda step, context: {"success": True, "output": "staged"},
        )
        step = PlanStep(
            action="write staged result",
            tool="staging_writer",
            params={"target": "staging_db", "staging": True, "value": 1},
            risk_level="high",
        )

        security = loop._check_security(
            step, {"domain": "SYSTEM", "domain_id": "system"},
        )
        assert security["allowed"] is True
        assert security["permission"]["allowed"] is True
        assert security["firewall"]["requires_effect_fence"] is True
        assert security["effect_fence"]["reservation_status"] == "reserved"

        result = loop._execute_step(
            step, {}, "test-task", 0, security=security)
        assert result["success"] is True

        duplicate = fence.check(
            action=AgentAction.WRITE,
            target="staging_db",
            payload=step.params,
            operation_id=step.step_id,
        )
        assert duplicate.allowed is False
        assert duplicate.idempotent_hit is True
        assert duplicate.reservation_status == "completed"
    finally:
        fence.clear_for_testing()
        set_testing_bypass(previous_bypass)
