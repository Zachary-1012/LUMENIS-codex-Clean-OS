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


def test_high_risk_permission_still_requires_human_approval():
    gate = PermissionGate()
    gate.grant_permission(PermissionLevel.COMMIT)

    denied = gate.check(
        OperationType.DB_WRITE,
        resource="staging_db",
        caller="test",
        operation_id="write-approval-1",
    )
    assert denied.allowed is False
    assert denied.requires_approval is True

    gate.grant_approval(OperationType.DB_WRITE.value, duration_minutes=5)
    allowed = gate.check(
        OperationType.DB_WRITE,
        resource="staging_db",
        caller="test",
        operation_id="write-approval-2",
    )
    assert allowed.allowed is True
    assert allowed.approval_token
