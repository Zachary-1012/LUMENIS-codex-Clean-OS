# -*- coding: utf-8 -*-
"""P0-WRITEPERM-02 回归：AI composer (/api/experience/ai/intent) 四态写权限边界。

四态必须全部成立：
  granted          —— 权限通过才进入 canonical skill execution chain；
  pending_approval —— 权限等级够但高风险缺人工审批：HTTP 200，**不执行、不写证据**；
  denied           —— 权限不足/未注册：HTTP 403，**不执行、不写证据**；
  permanent_deny   —— PUSH 等 AI 派生层永不放行的类别：HTTP 403，不执行。

为确定性地证明“未通过权限门就绝不执行”，测试用桩替换 run_execution_chain：
只要桩被调用即代表进入了执行链（真实链路会落 skill_executions / evidence）。
全部在 tmp_path 隔离库 + 最小 Flask app 下进行，不启动全量 app、不碰生产库。
"""
import importlib
import os
import sys
import types

import pytest
from flask import Flask

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@pytest.fixture()
def client_and_gate(tmp_path, monkeypatch):
    db_file = tmp_path / "perm_isolated.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_file))
    monkeypatch.setenv("ZBC_ACTIVE_BRAND", "guangzhou_taikoo_hui")
    # 显式关闭 permission_gate 的 TESTING 旁路，保证 deny-by-default 真实生效
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)

    import database
    importlib.reload(database)
    database.DB_PATH = str(db_file)
    database.init_db()

    from lumenis.system import security as permission_gate
    importlib.reload(permission_gate)
    prior_testing_bypass = permission_gate.is_testing_bypass_enabled()
    # conftest enables a session-wide bypass for ordinary route tests; this
    # permission contract must exercise the canonical Gate in strict mode.
    permission_gate.set_testing_bypass(False)
    import experience_runtime
    importlib.reload(experience_runtime)
    # AI-01 executes only under a server-resolved FOCUS scope (BACKEND-GAP-029).
    monkeypatch.setattr(experience_runtime, "_ai_intent_trusted_domain",
                        lambda: ("cth", "CTH", "actor:7"))

    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    cli = app.test_client()

    gate = experience_runtime.get_permission_gate()
    # 复位为生产默认权限集（READ..VERIFY，不含 COMMIT/PUSH），清空审批令牌
    default_perms = {
        permission_gate.PermissionLevel.READ,
        permission_gate.PermissionLevel.AUDIT,
        permission_gate.PermissionLevel.ANALYZE,
        permission_gate.PermissionLevel.RESEARCH,
        permission_gate.PermissionLevel.PLAN,
        permission_gate.PermissionLevel.PATCH_PREVIEW,
        permission_gate.PermissionLevel.TEST,
        permission_gate.PermissionLevel.VERIFY,
    }
    gate._enabled_permissions = set(default_perms)
    gate.revoke_all_approvals()

    calls = {"n": 0}

    def _fake_run(*a, **k):
        calls["n"] += 1
        return types.SimpleNamespace(
            execution_id=f"exec-{calls['n']}",
            status=types.SimpleNamespace(value="completed"),
            evidence_record={"ok": False},
        )

    from agent_runtime import task_binding
    monkeypatch.setattr(experience_runtime, "_content_project_scope", lambda *_a, **_k: ({"id": 7}, {"domain_id": "cth", "global_scope": True, "subject_id": None, "brand_focus_id": None}))
    def create(*a, **k):
        result = _fake_run(*a, **k)
        return {"task_id": result.execution_id, "status": "pending"}
    monkeypatch.setattr(task_binding, "create_agent_task", create)
    monkeypatch.setattr(task_binding, "start_agent_task", lambda _: None)

    yield cli, gate, permission_gate, calls
    permission_gate.set_testing_bypass(prior_testing_bypass)


def _post(cli, action_type="ANALYZE", **extra):
    payload = {"task": "分析当前主体风险", "action_type": action_type}
    payload.update(extra)
    return cli.post("/api/experience/ai/intent", json=payload)


FORBIDDEN_IN_BODY = ["system_prompt", "developer_prompt", "cookie", "cdp",
                     "credential", "private_key", "browser_session"]


# ------------------------------- granted -------------------------------
def test_analyze_default_is_granted_and_executes(client_and_gate):
    cli, _gate, _pg, calls = client_and_gate
    r = _post(cli, "ANALYZE")
    assert r.status_code == 202
    j = r.get_json()
    assert j["ok"] is True
    assert j["permission_status"] == "granted"
    assert j["execution_id"] == "exec-1"
    assert calls["n"] == 1  # 确实进入执行链


# ------------------------------- denied --------------------------------
def test_write_without_commit_permission_is_denied_and_never_executes(client_and_gate):
    cli, _gate, _pg, calls = client_and_gate
    r = _post(cli, "WRITE")
    assert r.status_code == 403
    j = r.get_json()
    assert j["ok"] is False and j["status"] == "denied"
    assert j["requires_approval"] is False
    assert calls["n"] == 0  # 关键：权限拒绝绝不进入执行链 → 不写任何证据


# -------------------------- pending_approval ---------------------------
def test_high_risk_with_permission_but_no_approval_is_pending(client_and_gate):
    cli, gate, pg, calls = client_and_gate
    gate.grant_permission(pg.PermissionLevel.COMMIT)  # 等级够，但不发审批令牌
    r = _post(cli, "WRITE")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is False and j["status"] == "pending_approval"
    assert j["requires_approval"] is True
    assert calls["n"] == 0  # 等审批期间不执行、不写证据


def test_write_granted_after_human_approval(client_and_gate):
    cli, gate, pg, calls = client_and_gate
    gate.grant_permission(pg.PermissionLevel.COMMIT)
    gate.grant_approval(pg.OperationType.DB_WRITE.value, duration_minutes=15)
    r = _post(cli, "WRITE")
    assert r.status_code == 202
    j = r.get_json()
    assert j["ok"] is True and j["permission_status"] == "granted"
    assert calls["n"] == 1  # 人工审批后允许执行


# ---------------------------- permanent_deny ---------------------------
def test_push_is_permanently_denied_even_with_high_perms(client_and_gate):
    cli, gate, pg, calls = client_and_gate
    # 即便授予最高权限与审批，PUSH 在 AI composer 边界仍永久拒绝
    gate.grant_permission(pg.PermissionLevel.COMMIT)
    gate.grant_permission(pg.PermissionLevel.PUSH)
    gate.grant_approval("*", duration_minutes=15)
    r = _post(cli, "PUSH")
    assert r.status_code == 403
    j = r.get_json()
    assert j["status"] == "permanent_deny"
    assert calls["n"] == 0


# ------------------------------ edge cases -----------------------------
def test_unknown_action_type_rejected_and_not_executed(client_and_gate):
    cli, _g, _pg, calls = client_and_gate
    r = _post(cli, "FROBNIC")
    assert r.status_code != 200
    assert calls["n"] == 0


def test_denied_responses_never_leak_security_internals(client_and_gate):
    cli, _g, _pg, _calls = client_and_gate
    for action in ("WRITE", "PUSH"):
        r = _post(cli, action)
        blob = r.get_data(as_text=True).lower()
        for bad in FORBIDDEN_IN_BODY:
            assert bad not in blob, f"{action} 响应泄漏 {bad}"
        # 不得回显任何令牌字符串字段
        j = r.get_json()
        assert j is not None
        assert "approval_token" not in j
