"""Trusted actor and product-scope contracts for account Skill execution."""

import sqlite3
from types import SimpleNamespace

import pytest

import account.skills as account_skills
import account.authorization as account_authorization
import lumenis.shared.agents.skills.execution as canonical_execution


@pytest.fixture
def account_db(tmp_path, monkeypatch):
    """Use a disposable SQLite DB for actor and member-scope authorization."""
    db_path = tmp_path / "account-skill-scope.sqlite3"
    connections = []

    def get_test_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        connections.append(conn)
        return conn

    with get_test_db() as conn:
        conn.executescript(
            """
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                module TEXT NOT NULL,
                action TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO v4_users (id, role, status) VALUES (1, 'user', 'active')"
        )
        conn.execute(
            "INSERT INTO v4_users (id, role, status) VALUES (2, 'admin', 'inactive')"
        )

    monkeypatch.setattr(account_skills, "get_db", get_test_db)
    monkeypatch.setattr(account_authorization, "get_db", get_test_db)
    yield get_test_db
    for conn in connections:
        conn.close()


@pytest.fixture
def execution_spy(monkeypatch):
    calls = []

    def run_execution_chain(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            status=SimpleNamespace(value="completed"),
            execution_id="test-execution",
            execute_result={"success": True},
            evidence={"source": "test"},
            evaluation={"state": "test"},
            permission_result={"allowed": True},
            firewall_result={"allowed": True},
            effect_fence_result={"allowed": True},
            error=None,
        )

    monkeypatch.setattr(
        canonical_execution, "run_execution_chain", run_execution_chain
    )
    return calls


def _skill_info(product="SHARED", domain="shared"):
    return {
        "skill_id": "shared_demo",
        "name": "Shared demo",
        "product": product,
        "domain": domain,
        "status": "enabled",
        "config": {},
    }


def _grant(account_db, product_id, action="read"):
    with account_db() as conn:
        conn.execute(
            """INSERT INTO v4_member_authorizations
               (user_id, product_id, module, action) VALUES (1, ?, 'shared_demo', ?)""",
            (product_id, action),
        )


def _install_skill_info(monkeypatch, product="SHARED", domain="shared"):
    monkeypatch.setattr(
        account_skills, "get_skill_info", lambda _skill_id: _skill_info(product, domain)
    )


def test_missing_actor_is_rejected_before_execution(monkeypatch, execution_spy):
    _install_skill_info(monkeypatch)

    result = account_skills.execute_skill_api("shared_demo", product="CTH")

    assert result["code"] == "ACTOR_REQUIRED"
    assert execution_spy == []


def test_inactive_actor_is_rejected_before_execution(
    account_db, monkeypatch, execution_spy
):
    _install_skill_info(monkeypatch)

    result = account_skills.execute_skill_api(
        "shared_demo", user_id=2, product="CTH"
    )

    assert result["code"] == "ACTOR_INVALID"
    assert execution_spy == []


def test_shared_skill_requires_explicit_cth_bmp_or_system_context(
    account_db, monkeypatch, execution_spy
):
    _install_skill_info(monkeypatch)

    result = account_skills.execute_skill_api("shared_demo", user_id=1)

    assert result["code"] == "PRODUCT_CONTEXT_REQUIRED"
    assert execution_spy == []


def test_unapproved_product_scope_is_rejected_before_execution(
    account_db, monkeypatch, execution_spy
):
    _install_skill_info(monkeypatch)

    result = account_skills.execute_skill_api(
        "shared_demo", user_id=1, product="BMP"
    )

    assert result["code"] == "PRODUCT_SCOPE_DENIED"
    assert execution_spy == []


def test_read_authorization_does_not_grant_module_write(
    account_db, monkeypatch, execution_spy
):
    _install_skill_info(monkeypatch)
    _grant(account_db, "CTH", action="read")

    result = account_skills.execute_skill_api(
        "shared_demo", action_type="WRITE", user_id=1, product="CTH"
    )

    assert result["code"] == "PRODUCT_SCOPE_DENIED"
    assert execution_spy == []


@pytest.mark.parametrize(
    ("product", "product_id", "domain_id", "permission_role"),
    [
        ("CTH", "CTH", "cth", "cth_analyst"),
        ("BMP", "ZBMP", "zbmp", "zbmp_analyst"),
    ],
)
def test_authorized_cth_bmp_scope_comes_from_server_selection_and_ignores_spoofs(
    account_db,
    monkeypatch,
    execution_spy,
    product,
    product_id,
    domain_id,
    permission_role,
):
    _install_skill_info(monkeypatch)
    _grant(account_db, product_id)
    untrusted_input = {
        "user_id": 999,
        "user_role": "owner",
        "role": "owner",
        "product": "SYSTEM",
        "product_id": "SYSTEM",
        "domain": "system",
        "domain_id": "system",
    }

    result = account_skills.execute_skill_api(
        "shared_demo",
        task="analyze",
        input_payload=untrusted_input,
        user_id=1,
        user_role="owner",  # Caller-provided role is not the source of truth.
        product=product,
    )

    assert result["success"] is True
    assert len(execution_spy) == 1
    call = execution_spy[0]
    assert call["user_id"] == 1
    assert call["user_role"] == "user"
    assert call["product"] == product_id
    assert call["domain"] == domain_id
    assert call["permission_role"] == permission_role
    # Payload is carried as user data; it cannot alter the separately derived
    # authenticated actor or execution scope passed to the canonical chain.
    assert call["input_payload"] == untrusted_input


def test_system_scope_is_explicitly_authorized_and_server_derived(
    account_db, monkeypatch, execution_spy
):
    _install_skill_info(monkeypatch, product="SYSTEM", domain="system")
    _grant(account_db, "SYSTEM")

    result = account_skills.execute_skill_api(
        "shared_demo", user_id=1, product="SYSTEM"
    )

    assert result["success"] is True
    assert len(execution_spy) == 1
    call = execution_spy[0]
    assert (call["user_id"], call["user_role"]) == (1, "user")
    assert (call["product"], call["domain"]) == ("SYSTEM", "system")
    assert call["permission_role"] == "system_operator"


@pytest.mark.parametrize(
    ("product", "product_id", "domain_id", "permission_role"),
    [
        ("CTH", "CTH", "cth", "cth_operator"),
        ("BMP", "ZBMP", "zbmp", "zbmp_operator"),
        ("SYSTEM", "SYSTEM", "system", "system_writer"),
    ],
)
def test_member_module_write_uses_low_domain_role_not_admin(
    account_db, monkeypatch, execution_spy, product, product_id, domain_id,
    permission_role,
):
    _install_skill_info(monkeypatch)
    _grant(account_db, product_id, action="write")

    result = account_skills.execute_skill_api(
        "shared_demo",
        action_type="WRITE",
        user_id=1,
        user_role="owner",  # Caller-supplied role must not override the DB role.
        product=product,
    )

    assert result["success"] is True
    assert len(execution_spy) == 1
    assert execution_spy[0]["user_role"] == "user"
    assert execution_spy[0]["product"] == product_id
    assert execution_spy[0]["domain"] == domain_id
    assert execution_spy[0]["permission_role"] == permission_role


@pytest.mark.parametrize("action_type", ["COMMIT", "PUSH"])
def test_member_module_write_does_not_grant_commit_or_push(
    account_db, monkeypatch, execution_spy, action_type
):
    _install_skill_info(monkeypatch)
    _grant(account_db, "CTH", action="write")

    result = account_skills.execute_skill_api(
        "shared_demo", action_type=action_type, user_id=1, product="CTH"
    )

    assert result["code"] == "DOMAIN_ROLE_REQUIRED"
    assert execution_spy == []


def test_low_domain_writer_role_cannot_change_configuration(monkeypatch):
    from lumenis.system.security import (
        OperationType, PermissionGate, PermissionLevel,
    )
    from lumenis.system.security import permission as permission_module

    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    target = "skill:shared_demo"
    gate = PermissionGate(enabled_permissions={PermissionLevel.COMMIT})

    denied_without_human = gate.check(
        OperationType.DB_WRITE,
        resource=target,
        caller="test_skill",
        domain_id="cth",
        role="cth_operator",
    )
    assert denied_without_human.allowed is False
    assert denied_without_human.requires_approval is True

    gate.grant_approval(
        OperationType.DB_WRITE.value,
        duration_minutes=5,
        resource=target,
        granted_by="test_owner",
    )

    from lumenis.shared.agents.skills.execution import (
        ActionType, SkillExecutionContext, check_permission,
    )
    from lumenis.system import security

    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    context = SkillExecutionContext(
        skill_id="shared_demo",
        user_id=1,
        permission_role="cth_operator",
        domain="cth",
        product="CTH",
        input_payload={"target": target},
        action_type=ActionType.WRITE,
    )
    execution_permission = check_permission(context, user_role="user")

    low_write = gate.check(
        OperationType.DB_WRITE,
        resource=target,
        caller="test_skill",
        domain_id="cth",
        role="cth_operator",
    )
    config_write = gate.check(
        OperationType.CONFIG_MODIFY,
        resource=target,
        caller="test_skill",
        domain_id="cth",
        role="cth_operator",
    )
    cross_domain_write = gate.check(
        OperationType.DB_WRITE,
        resource=target,
        caller="test_skill",
        domain_id="zbmp",
        role="cth_operator",
    )

    assert low_write.allowed is True
    assert low_write.requires_approval is True
    assert low_write.approval_token
    assert execution_permission["allowed"] is True
    assert config_write.allowed is False
    assert cross_domain_write.allowed is False
