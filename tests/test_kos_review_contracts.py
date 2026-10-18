"""Focused regressions for KOS identity, suggestion and attribution review findings."""
import sys
from types import SimpleNamespace

import pytest


def test_kos_scope_keeps_sealed_local_workspace_identity_without_account_id(monkeypatch):
    from flask import Flask

    import kos_routes
    import subject_registry
    from lumenis.auth import service as auth_service
    from lumenis.system.security import permission

    app = Flask("kos-local-workspace-scope")
    monkeypatch.setattr(permission, "_local_workspace_transport_allowed", lambda **_kwargs: True)
    principal = permission.resolve_local_workspace_principal(module="reports", action="write")
    assert principal is not None
    monkeypatch.setattr(permission, "resolve_local_workspace_principal", lambda **_kwargs: principal)
    monkeypatch.setattr(auth_service, "get_current_user", lambda **_kwargs: pytest.fail("account lookup bypassed local principal"))
    selected = {
        "subject_id": "BRAND-SUBJECT-1", "brand_focus_id": "BRAND-1",
        "subject_type": "brand", "status": "active", "name_zh": "测试品牌",
    }
    monkeypatch.setattr(subject_registry, "normalize_domain", lambda _value: "BMP")
    monkeypatch.setattr(subject_registry, "list_subjects", lambda _domain: [selected])

    calls = []

    def allow_local_scope(actual_principal, *, module, action, **scope):
        calls.append((actual_principal, module, action, scope))
        return permission.ActorScopePermissionResult(
            allowed=True, reason="registered workspace scope", caller="workspace:local",
            domain_id="bmp", actor_id=None, subject_id=None,
            brand_focus_id="BRAND-1", global_scope=False, scope_action=action,
            scope_audit_id="scope-audit-1", verification_state="verified",
            principal_kind="local_workspace", principal_ref="workspace:local",
        )

    monkeypatch.setattr(permission, "check_local_workspace_scope_permission", allow_local_scope)
    monkeypatch.setattr(
        permission, "check_actor_scope_permission",
        lambda *_args, **_kwargs: pytest.fail("local workspace used account permission path"),
    )

    with app.test_request_context(
        "/api/kos/reply/generate",
        headers={
            "X-Domain-Id": "BMP", "X-Lumenis-Context-Mode": "FOCUS",
            "X-Brand-Focus-ID": "BRAND-1",
        },
    ):
        actor, actor_ref, scope, resolved, decision = kos_routes._resolve_kos_brand_scope("write")

    assert actor is principal
    assert actor_ref == decision.caller == "workspace:local"
    assert decision.actor_id is None
    assert decision.principal_ref == principal.principal_ref
    assert scope["brand_focus_id"] == resolved["brand_focus_id"] == "BRAND-1"
    assert calls and calls[0][0] is principal
    assert calls[0][1:3] == ("reports", "write")


def test_kos_scope_rejects_local_permission_receipt_with_invented_actor(monkeypatch):
    from flask import Flask

    import kos_routes
    import subject_registry
    from lumenis.auth import service as auth_service
    from lumenis.system.security import permission

    app = Flask("kos-local-workspace-invalid-receipt")
    monkeypatch.setattr(permission, "_local_workspace_transport_allowed", lambda **_kwargs: True)
    principal = permission.resolve_local_workspace_principal(module="reports", action="write")
    monkeypatch.setattr(permission, "resolve_local_workspace_principal", lambda **_kwargs: principal)
    monkeypatch.setattr(auth_service, "get_current_user", lambda **_kwargs: pytest.fail("account lookup bypassed local principal"))
    monkeypatch.setattr(subject_registry, "normalize_domain", lambda _value: "BMP")
    monkeypatch.setattr(subject_registry, "list_subjects", lambda _domain: [{
        "subject_id": "BRAND-SUBJECT-1", "brand_focus_id": "BRAND-1",
        "subject_type": "brand", "status": "active",
    }])
    monkeypatch.setattr(permission, "check_local_workspace_scope_permission", lambda *_args, **_kwargs:
        permission.ActorScopePermissionResult(
            allowed=True, reason="invalid identity receipt", caller="workspace:local",
            actor_id=42, brand_focus_id="BRAND-1", global_scope=False,
            scope_action="write", scope_audit_id="scope-audit-1",
            verification_state="verified", principal_kind="local_workspace",
            principal_ref="workspace:local",
        ))

    with app.test_request_context(
        "/api/kos/reply/generate",
        headers={
            "X-Domain-Id": "BMP", "X-Lumenis-Context-Mode": "FOCUS",
            "X-Brand-Focus-ID": "BRAND-1",
        },
    ), pytest.raises(PermissionError, match="SCOPE_IDENTITY_MISMATCH"):
        kos_routes._resolve_kos_brand_scope("write")


@pytest.mark.parametrize(
    ("path", "method", "owner_method", "expected"),
    [
        ("/api/kos/intent-analysis?note_id=N1&author_id=A1", "get",
         "analyze_comments_intent", {"intent": "warm"}),
        ("/api/kos/kos-identity?author_id=A1", "get",
         "recognize_kos_identity", {"is_kos": True}),
        ("/api/kos/kos-identity?limit=10", "post",
         "refresh_kos_identity", {"refreshed": 10}),
        ("/api/kos/competitor-benchmark", "get",
         "competitor_benchmark", {"sample_count": 3}),
    ],
)
def test_kos_intelligence_routes_resolve_existing_intel_owner(
    monkeypatch, path, method, owner_method, expected,
):
    from flask import Flask

    import kos_routes

    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return expected

    owner = SimpleNamespace(**{owner_method: record})
    monkeypatch.setitem(sys.modules, "kos_intel", owner)
    app = Flask("kos-intel-owner-binding")
    app.register_blueprint(kos_routes.kos_bp)

    response = app.test_client().open(path, method=method.upper())

    if owner_method in {"analyze_comments_intent", "competitor_benchmark", "recognize_kos_identity", "refresh_kos_identity"}:
        # Current readers require actual scope authorization before owner access.
        assert response.status_code == 401
        assert calls == []
    else:
        assert response.status_code == 200
        assert response.get_json() == {"ok": True, "data": expected}
        assert len(calls) == 1


@pytest.mark.parametrize(
    ("engine_result", "expected_status", "expected_code"),
    [
        ({"ok": True, "action": "SUGGEST_REPLY", "suggested_reply": "  展示给用户的原文  "}, 200, None),
        ({"ok": True, "action": "SUGGEST_REPLY", "suggested_reply": "   "}, 503, "SUGGESTED_REPLY_UNAVAILABLE"),
    ],
)
def test_reply_review_uses_exact_visible_suggestion_and_never_records_empty(
    monkeypatch, engine_result, expected_status, expected_code,
):
    from flask import Flask

    import kos_routes

    app = Flask("kos-reply-suggestion-contract")
    scope = {"domain_id": "zbmp", "subject_id": None,
             "brand_focus_id": "BRAND-1", "global_scope": False}
    decision = SimpleNamespace(
        caller="workspace:local", scope_audit_id="scope-audit-1",
        principal_kind="local_workspace", principal_ref="workspace:local",
    )
    selected = {"name_zh": "测试品牌", "brand_focus_id": "BRAND-1"}
    monkeypatch.setattr(
        kos_routes, "_resolve_kos_brand_scope",
        lambda _action: (object(), decision.caller, scope, selected, decision),
    )
    monkeypatch.setattr(
        kos_routes, "_engine",
        lambda: SimpleNamespace(generate_reply=lambda **_kwargs: dict(engine_result)),
    )
    executions = []
    monkeypatch.setitem(sys.modules, "kos_execution", SimpleNamespace(
        create_scoped_execution=lambda **kwargs: executions.append(kwargs) or {"execution": {
            "status": "AI_GENERATED", "execution_id": "KX-review-1",
        }}
    ))

    app.register_blueprint(kos_routes.kos_bp)
    response = app.test_client().post("/api/kos/reply/generate", json={"comment_text": "用户评论"})

    assert response.status_code == expected_status
    if expected_code:
        assert response.get_json()["code"] == expected_code
        assert executions == []
    else:
        payload = executions[0]["payload"]
        assert payload["generated_reply"] == engine_result["suggested_reply"]
        assert not isinstance(executions[0]["actor"], str)
        assert executions[0]["scope"] == scope
        assert payload["target_binding"] == "UNASSIGNED_RECIPIENT"
        assert "permission_identity" not in payload
        assert response.get_json()["suggested_reply"] == payload["generated_reply"]
