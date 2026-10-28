import urllib.error
import urllib.request

import pytest

from lumenis.system.ai_gateway import core, user_api_adapter


def _approved_gateway(system, user, **kwargs):
    """Synthetic user confirms the exact preview; never bypasses Permission."""
    result = core.chat(system, user, **kwargs)
    if result[1] == "user_api_approval_required":
        preview = result[2]["approval_request"]
        return core.chat(system, user, **kwargs, external_approval={
            "confirmed": True, "confirmation_id": preview["confirmation_id"],
            "resource": preview["resource"],
        })
    return result


def _approved_adapter(system, user, **kwargs):
    result = user_api_adapter.chat(system, user, **kwargs)
    if result[1] == "user_api_approval_required":
        preview = result[2]["approval_request"]
        return user_api_adapter.chat(system, user, **kwargs, external_approval={
            "confirmed": True, "confirmation_id": preview["confirmation_id"],
            "resource": preview["resource"],
        })
    return result


def _configure_test_runtime(**values):
    """Fault injection on synthetic runtime state, never real env credentials."""
    _actor, gate, caller = user_api_adapter._identity()
    cfg = user_api_adapter._configurations[gate][caller]
    cfg.update(values)


def test_default_never_calls_third_party(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "k")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "m")
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert core._chat("s", "u") == (None, "provider_disabled")
    assert _approved_gateway("s", "u")[1] == "provider_disabled"


def test_explicit_user_api_is_used_without_fallback(configured, monkeypatch):
    import io
    import json
    monkeypatch.setenv("AI_PROVIDER", "user_api")
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "k")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "m")

    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    seen = {}
    def fake(req, timeout=None):
        seen["url"] = req.full_url
        return R(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())
    monkeypatch.setattr(user_api_adapter, "_open", fake)
    # Global API selection must not activate old data/learning call sites.
    assert core._chat("s", "u") == (None, "provider_disabled")
    assert _approved_gateway("s", "u")[1] == "provider_disabled"
    assert seen == {}
    assert _approved_gateway("s", "u", external_user_input=True)[:2] == ("ok", "user_api")
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"

    def boom(req, timeout=None): raise OSError("down")
    monkeypatch.setattr(user_api_adapter, "_open", boom)
    assert _approved_gateway("s", "u", external_user_input=True)[:2] == (None, "user_api_unavailable")


@pytest.fixture
def configured(monkeypatch):
    from lumenis.system.security import permission
    from flask import Flask
    # Real canonical Gate, isolated in memory, with testing bypass disabled.
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    gate = permission.PermissionGate()
    monkeypatch.setenv("AI_PROVIDER", "user_api")
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "test-private-key")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "openai/gpt-oss-20b")
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", method="POST", json={}, environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        user_api_adapter.configure({"provider": "user_api", "base_url": user_api_adapter.GROQ_BASE_URL,
                                    "api_key": "test-private-key", "model": "openai/gpt-oss-20b"})
        yield


def test_configuration_is_not_live_availability(configured, monkeypatch):
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("status performed external call"))
    result = user_api_adapter.status()
    assert result["configured"] is True
    assert result["available"] is False
    assert result["state"] == "CONFIGURED_NOT_VERIFIED"
    assert result["service_provider"] == "groq"
    assert result["fallback_allowed"] is False
    assert "test-private-key" not in str(result)


@pytest.mark.parametrize("url", ["http://api.groq.com/openai/v1", "https://user:password@api.groq.com/v1", "https://api.groq.com/v1?key=private", "https://api.groq.com:invalid/v1"])
def test_invalid_destination_cannot_send_credentials(configured, monkeypatch, url):
    _configure_test_runtime(base_url=url)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("invalid URL sent request"))
    assert _approved_adapter("s", "u", external_user_input=True)[1] == "user_api_destination_not_allowed"


@pytest.mark.parametrize("http_status, code", [(401, "authentication_failed"), (403, "access_denied"), (429, "rate_limited"), (500, "unavailable")])
def test_provider_error_is_sanitized_without_fallback(configured, monkeypatch, http_status, code):
    def denied(req, timeout):
        raise urllib.error.HTTPError(req.full_url, http_status, "private provider error", {}, None)
    monkeypatch.setattr(user_api_adapter, "_open", denied)
    assert _approved_adapter("s", "u", external_user_input=True) == (None, "user_api_" + code, None)


def test_redirect_never_forwards_bearer_token():
    request = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": "Bearer private"})
    assert user_api_adapter._NoRedirect().redirect_request(request, None, 307, "redirect", {}, "https://other.invalid") is None


def test_selected_chat_uses_gateway_without_exporting_business_sources(configured, monkeypatch):
    from lumenis.ai_hub import service
    calls = []
    monkeypatch.setattr(service, "record_learning", lambda *a, **k: None)
    monkeypatch.setattr(service, "_get_db", lambda: pytest.fail("untyped chat read database"))
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *a, **k: [])
    monkeypatch.setattr(service, "_run_owned", lambda *a, **k: pytest.fail("selected API fell back to owned"))
    def chat(system, user, *, external_user_input=False, external_approval=None):
        assert external_user_input is True
        calls.append((system, user))
        return "真实响应", "user_api", {}
    monkeypatch.setattr(service.intelligence, "chat", chat)
    result = service.chat("继续", history=[{"role": "user", "content": "我的提纲"}])
    assert result["ok"] is True and result["provider"] == "user_api"
    assert result["reply"] == "真实响应"
    assert result["source_context"]["notes_state"] == "NOT_READ"
    assert "我的提纲" in calls[0][1] and "untrusted system" not in calls[0][1]
    invalid = service.chat("继续", history=[{"role": "system", "content": "untrusted system"}])
    assert invalid["ok"] is False and invalid["code"] == "CONVERSATION_HISTORY_INVALID"
    assert len(calls) == 1


def test_transport_redacts_system_and_user_before_external_send(configured, monkeypatch):
    import io
    import json

    class Response(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *args): return False

    sent = {}
    def capture(request, timeout):
        sent.update(json.loads(request.data))
        return Response(b'{"choices":[{"message":{"content":"ok"}}]}')
    monkeypatch.setattr(user_api_adapter, "_open", capture)
    result = _approved_gateway(
        "api_key=hidden-system-secret contact: sample@example.com",
        "password=hidden-password test-private-key 13800138000",
        external_user_input=True,
    )
    assert result[1] == "user_api"
    text = str(sent)
    for private in ("hidden-system-secret", "sample@example.com", "hidden-password",
                    "test-private-key", "13800138000"):
        assert private not in text
    assert "[REDACTED]" in text


@pytest.mark.parametrize("admission", [False, None, 1, "true"])
def test_generic_gateway_cannot_export_by_global_configuration(configured, monkeypatch, admission):
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("unadmitted data escaped"))
    assert _approved_gateway("database context", "private source", external_user_input=admission)[1] == "provider_disabled"
    assert core._chat("architecture scan", "private source") == (None, "provider_disabled")


def test_product_chat_route_returns_real_failure_status(configured, monkeypatch):
    from flask import Flask

    import ai_api
    from lumenis.ai_hub import service
    monkeypatch.setattr(service, "record_learning", lambda *a, **k: None)
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *a, **k: [])
    monkeypatch.setattr(service.intelligence, "chat", lambda *a, **k: (None, "user_api_rate_limited", None))
    monkeypatch.setattr(ai_api, "_run_owned_analysis", lambda *a, **k: pytest.fail("fallback"))
    app = Flask(__name__)
    app.register_blueprint(ai_api.bp)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    result = app.test_client().post("/api/ai/chat", json={"message": "hello"})
    assert result.status_code == 503
    assert result.json["ok"] is False
    assert result.json["reply"] is None
    assert result.json["code"] == "USER_API_RATE_LIMITED"


def test_chat_persistence_retains_counts_not_conversation(configured, monkeypatch, tmp_path):
    import json

    from lumenis.ai_hub import service

    log_path = tmp_path / "learning.jsonl"
    monkeypatch.setattr(service, "LEARN_LOG", str(log_path))
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *a, **k: [])
    # Exercise the actual Gateway metadata wrapper, replacing only transport.
    monkeypatch.setattr(user_api_adapter, "chat", lambda *a, **k: (
        "private-response-sentinel", "user_api", {
            "prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20,
            "provider_debug": "private-provider-sentinel",
        },
    ))
    result = service.chat(
        "api_key=private-input-sentinel email=private@example.com 13800138000",
        history=[{"role": "user", "content": "private-history-sentinel"}],
        scope="private-scope-sentinel",
    )
    persisted = log_path.read_text(encoding="utf-8")
    for value in ("private-input-sentinel", "private@example.com", "13800138000",
                  "private-history-sentinel", "private-scope-sentinel",
                  "private-response-sentinel", "private-provider-sentinel"):
        assert value not in persisted
    receipt = json.loads(persisted)
    assert receipt["scope"] == "all"
    assert receipt["usage"] == result["usage"] == {
        "prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20,
    }
    assert receipt["status"] == "COMPLETED"


@pytest.mark.parametrize("value", [True, -1, "private-usage-sentinel", {"secret": "private"}])
def test_chat_usage_excludes_untrusted_non_counts(configured, monkeypatch, tmp_path, value):
    import json

    from lumenis.ai_hub import service

    log_path = tmp_path / "learning.jsonl"
    monkeypatch.setattr(service, "LEARN_LOG", str(log_path))
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *a, **k: [])
    monkeypatch.setattr(user_api_adapter, "chat", lambda *a, **k: (
        "ok", "user_api", {"prompt_tokens": value},
    ))
    assert service.chat("hello")["usage"] is None
    assert json.loads(log_path.read_text(encoding="utf-8"))["usage"] is None


@pytest.mark.parametrize("url", [
    "https://example.invalid/v1", "https://api.groq.com.evil.invalid/openai/v1",
    "https://api.groq.com/openai/v1?",
    "https://api.groq.com/openai/v1#", "https://api.groq.com/openai/v1/../other",
    "https://api.groq.com/openai/v1//", "https://api.groq.com:444/openai/v1",
    "https://api.groq.com./openai/v1", "https://api.groq.com/openai%2fv1",
    "https://api.groq.com/openai/v1\n/other", "https://@api.groq.com/openai/v1",
    "https://api.groq.com:/openai/v1", "https://127.0.0.1/openai/v1",
])
def test_unsafe_or_reserved_destination_is_denied(configured, monkeypatch, url):
    _configure_test_runtime(base_url=url)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("invalid destination"))
    assert user_api_adapter.status()["reason"] == "USER_API_DESTINATION_NOT_ALLOWED"
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_destination_not_allowed"


@pytest.mark.parametrize("url", [
    "https://api.groq.com/openai/v1", "https://api.groq.com/openai/v1/",
    "https://API.GROQ.COM:443/openai/v1",
])
def test_approved_url_is_normalized_to_fixed_transport(configured, monkeypatch, url):
    import io
    _configure_test_runtime(base_url=url)
    requests = []
    def fake(req, timeout):
        requests.append(req.full_url)
        return io.BytesIO(b'{"choices":[{"message":{"content":"result"}}]}')
    monkeypatch.setattr(user_api_adapter, "_open", fake)
    assert _approved_gateway("s", "u", external_user_input=True)[:2] == ("result", "user_api")
    assert requests == [user_api_adapter.GROQ_CHAT_URL]


@pytest.mark.parametrize("field,code", [
    ("BASE_URL", "BASE_URL"), ("KEY", "KEY"), ("MODEL", "MODEL"),
])
def test_missing_configuration_does_not_call_network(configured, monkeypatch, field, code):
    _configure_test_runtime(**{{"BASE_URL": "base_url", "KEY": "api_key", "MODEL": "model"}[field]: ""})
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("incomplete configuration"))
    assert user_api_adapter.status()["reason"] == "USER_API_" + code + "_REQUIRED"
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_" + code.lower() + "_required"


@pytest.mark.parametrize("admission", [False, None, 1, "true"])
def test_direct_transport_requires_explicit_data_admission(configured, monkeypatch, admission):
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("direct bypass"))
    result = _approved_adapter("s", "u", external_user_input=admission)
    assert result[:2] == (None, "provider_disabled")
    from lumenis.system.security import permission
    assert result[2]['audit_id'] == permission.get_permission_gate().get_audit_log()[-1]['audit_id']


def test_canonical_permission_denial_prevents_transport(configured, monkeypatch):
    from lumenis.system.security import permission
    gate = permission.PermissionGate(enabled_permissions=set())
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("denied call"))
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_permission_denied"
    assert gate.get_audit_log()[-1]["result"] == "denied"
    assert gate.get_audit_log()[-1]["audit_id"]
    assert gate.get_audit_log()[-1]["reason"] == "USER_API_ANALYZE_PERMISSION_REQUIRED"


def test_closed_workspace_prevents_transport(configured, monkeypatch):
    from flask import current_app
    current_app.config["LUMENIS_OPEN_WORKSPACE"] = False
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("missing context"))
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_permission_denied"


def test_permission_failure_is_sanitized_and_does_not_call_transport(configured, monkeypatch):
    from lumenis.system.security import permission
    def broken():
        raise RuntimeError("private-key-sentinel")
    monkeypatch.setattr(permission, "get_permission_gate", broken)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("permission failure"))
    result = _approved_gateway("s", "u", external_user_input=True)
    assert result[1] == "user_api_audit_unavailable"
    assert "private-key-sentinel" not in repr(result)


def test_configuration_validation_is_total():
    for cfg in (None, {}, {"base_url": []}, {"base_url": user_api_adapter.GROQ_BASE_URL}):
        assert user_api_adapter.configuration_is_complete(cfg) is False


@pytest.mark.parametrize("payload", [
    b"not-json", b"[]", b"null", b'{"choices":[null]}',
    b'{"choices":[{"message":{"content":""}}]}',
    b'{"choices":[{"message":{"content":"partial"},"finish_reason":"length"}]}',
    b'{"error":{"message":"private"},"choices":[{"message":{"content":"wrong"}}]}',
    b"x" * 2_000_001,
], ids=["not-json", "array", "null", "null-choice", "empty-content", "truncated-content", "error-with-choice", "oversized"])
def test_malformed_incomplete_provider_output_is_not_success(configured, monkeypatch, payload):
    import io
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: io.BytesIO(payload))
    assert _approved_adapter("s", "u", external_user_input=True) == (None, "user_api_invalid_response", None)


@pytest.mark.parametrize("kwargs", [
    {"temperature": float("nan")}, {"temperature": True}, {"temperature": 3},
    {"max_tokens": -1}, {"max_tokens": True}, {"timeout": float("inf")},
])
def test_invalid_request_never_leaves_transport(configured, monkeypatch, kwargs):
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("invalid request"))
    assert _approved_adapter("s", "u", external_user_input=True, **kwargs)[1] == "user_api_invalid_request"


def test_transport_usage_retains_only_nonnegative_counts(configured, monkeypatch):
    import io
    import json
    payload = {"choices": [{"message": {"content": "ok"}}], "usage": {
        "prompt_tokens": 3, "completion_tokens": True, "total_tokens": -1,
        "debug": "private-provider-content",
    }}
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    assert _approved_adapter("s", "u", external_user_input=True)[2] == {"prompt_tokens": 3}


def test_permission_is_rechecked_on_each_call_and_recovers(configured, monkeypatch):
    import io
    from lumenis.system.security import permission
    gate = permission.get_permission_gate()
    calls = []
    def fake(*a, **k):
        calls.append(True)
        return io.BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')
    monkeypatch.setattr(user_api_adapter, "_open", fake)
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api"
    gate._enabled_permissions.discard(permission.PermissionLevel.ANALYZE)
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_permission_denied"
    gate._enabled_permissions.add(permission.PermissionLevel.ANALYZE)
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api"
    assert len(calls) == 2


@pytest.mark.parametrize("headers", [
    {"X-Actor-ID": "1"}, {"X-Forwarded-For": "127.0.0.1"},
    {"Origin": "https://untrusted.invalid"}, {"Host": "untrusted.invalid"},
])
def test_client_identity_or_untrusted_origin_cannot_authorize_external_call(configured, monkeypatch, headers):
    from flask import current_app
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("forged request"))
    with current_app.test_request_context("/", headers=headers, environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_permission_denied"


def test_request_context_is_required_even_with_selected_provider(configured, monkeypatch):
    import flask
    monkeypatch.setattr(flask, "has_request_context", lambda: False)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("no identity context"))
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_permission_context_required"


def test_configuration_revocation_during_permission_check_prevents_send(configured, monkeypatch):
    from lumenis.system.security import permission
    gate = permission.get_permission_gate()
    original = gate.confirm_user_api_request
    def revoke(actor, binding, confirmation):
        token = original(actor, binding, confirmation)
        user_api_adapter.configure({"provider": "owned"})
        return token
    monkeypatch.setattr(gate, "confirm_user_api_request", revoke)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("revoked selection"))
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_configuration_changed"


def test_exact_prompt_and_model_are_bound_to_permission_without_raw_audit(configured, monkeypatch):
    import io
    from lumenis.system.security import permission
    gate = permission.get_permission_gate()
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: io.BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}'))
    resources = []
    for text, model in [("private-first", "model-a"), ("private-second", "model-a"), ("private-second", "model-b")]:
        _configure_test_runtime(model=model)
        assert _approved_gateway("s", text, external_user_input=True)[1] == "user_api"
        resources.append(gate.get_audit_log()[-1]["resource"])
    assert len(set(resources)) == 3
    audits = repr(gate.get_audit_log())
    assert "private-first" not in audits and "private-second" not in audits
    assert "test-private-key" not in audits
    assert gate._current_check_domain is None


def test_authenticated_shared_member_grant_is_rechecked(configured, monkeypatch):
    import io
    from lumenis.auth import service as auth
    from lumenis.system.security import permission
    monkeypatch.setattr(auth, "get_current_user", lambda **kw: {"id": 17})
    monkeypatch.setattr(permission, "_load_actor_scope_role", lambda *a, **k: "user")
    monkeypatch.setattr(permission, "_actor_has_scope_action", lambda actor, product, module, action, **kw:
                        (actor, product, module, action) == (17, "SHARED", "conversation", "write"))
    grants = [{"product_id": "SHARED", "module": "conversation", "action": "write"}]
    monkeypatch.setattr(permission, "_load_actor_scope_grants", lambda *a, **k: grants)
    user_api_adapter.configure({"provider": "user_api", "base_url": user_api_adapter.GROQ_BASE_URL,
                                "api_key": "test-private-key", "model": "openai/gpt-oss-20b"})
    calls = []
    def fake(*a, **k):
        calls.append(True)
        return io.BytesIO(b'{"choices":[{"message":{"content":"ok"}}]}')
    monkeypatch.setattr(user_api_adapter, "_open", fake)
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api"
    grants.clear()
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_permission_denied"
    assert len(calls) == 1


@pytest.mark.parametrize("module,action,resource", [
    ("content", "write", "user-api-conversation:v1:" + "a" * 64),
    ("conversation", "read", "user-api-conversation:v1:" + "a" * 64),
    ("conversation", "write", "https://other.invalid"),
    ("conversation", "write", "user-api-conversation:v1:invalid"),
])
def test_shared_ai_admission_cannot_be_reused_for_other_effects(configured, module, action, resource):
    from lumenis.system.security import permission
    principal = permission.resolve_local_workspace_principal(module="conversation", action="write")
    decision = permission.check_shared_workspace_effect(
        principal, {"scope_kind": "shared_workspace", "version": 1},
        permission.OperationType.AI_CALL, resource, module=module, action=action,
    )
    assert decision.allowed is False


def test_groq_route_normal_success_and_permission_denial(configured, monkeypatch):
    import io
    from flask import current_app
    import ai_api
    from lumenis.ai_hub import service
    from lumenis.system.security import permission
    current_app.register_blueprint(ai_api.bp)
    monkeypatch.setattr(service, "record_learning", lambda *a, **k: None)
    monkeypatch.setattr(service.freg, "search_function_metadata", lambda *a, **k: [])
    monkeypatch.setattr(service, "retrieve", lambda *a, **k: pytest.fail("business source exported"))
    calls = []
    def fake(*a, **k):
        calls.append(True)
        return io.BytesIO(b'{"choices":[{"message":{"content":"requested answer"}}]}')
    monkeypatch.setattr(user_api_adapter, "_open", fake)
    client = current_app.test_client()
    preview = client.post("/api/ai/chat", json={"message": "my own question"})
    assert preview.status_code == 409 and not calls
    consent = preview.json["approval_request"]
    result = client.post("/api/ai/chat", json={"message": "my own question", "external_approval": {
        "confirmed": True, "confirmation_id": consent["confirmation_id"], "resource": consent["resource"],
    }})
    assert result.status_code == 200 and result.json["reply"] == "requested answer"
    permission.get_permission_gate()._enabled_permissions.clear()
    denied = client.post("/api/ai/chat", json={"message": "my own question", "permission": True, "actor_id": 1})
    assert denied.status_code == 503 and denied.json["code"] == "USER_API_PERMISSION_DENIED"
    assert denied.json["reply"] is None and len(calls) == 1


@pytest.mark.parametrize("base,provider,destination,token_field", [
    ("https://api.groq.com/openai/v1", "groq", "https://api.groq.com/openai/v1/chat/completions", "max_tokens"),
    ("https://api.openai.com/v1", "openai", "https://api.openai.com/v1/chat/completions", "max_completion_tokens"),
    ("https://api.deepseek.com/v1/", "deepseek", "https://api.deepseek.com/chat/completions", "max_tokens"),
    ("https://CUSTOM.EXAMPLE.NET:443/inference/v1/", "custom.example.net", "https://custom.example.net/inference/v1/chat/completions", "max_tokens"),
])
def test_explicit_byok_protocol_and_destination_share_exact_consent(configured, monkeypatch, base, provider, destination, token_field):
    import hashlib
    import io
    import json
    user_api_adapter.configure({"provider": "user_api", "base_url": base,
                               "api_key": "synthetic-byok-key", "model": "synthetic-model",
                               "protocol": "openai_chat_completions"})
    monkeypatch.setattr(user_api_adapter.socket, "getaddrinfo", lambda *a, **k: pytest.fail("preview queried DNS"))
    status = user_api_adapter.status()
    assert status["service_provider"] == provider
    assert status["connection_origin"] == "user_api" and status["available"] is False
    assert status["destination"] == destination
    preview = core.chat("s", "u", external_user_input=True)[2]["approval_request"]
    assert preview["provider"] == provider and preview["destination"] == destination
    assert preview["request"][token_field] == 1200
    sent = []
    def opened(req, timeout):
        sent.append(req)
        assert req.full_url == destination
        assert req.headers["Authorization"] == "Bearer synthetic-byok-key"
        assert hashlib.sha256(req.data).hexdigest() == preview["body_sha256"]
        assert json.loads(req.data) == preview["request"]
        return io.BytesIO(b'{"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}')
    monkeypatch.setattr(user_api_adapter, "_open", opened)
    approval = {"confirmed": True, "confirmation_id": preview["confirmation_id"], "resource": preview["resource"]}
    assert core.chat("s", "u", external_user_input=True, external_approval=approval)[:2] == ("ok", "user_api")
    assert core.chat("s", "u", external_user_input=True, external_approval=approval)[1] == "user_api_confirmation_invalid"
    assert len(sent) == 1


def test_retired_builtin_brand_does_not_retire_explicit_byok():
    from lumenis.system.ai_gateway import providers
    for name, base in (("openai", "https://api.openai.com/v1"), ("deepseek", "https://api.deepseek.com")):
        assert providers.is_provider_retired(name)
        assert providers.provider_status(name) == providers.DISABLED
        connection = providers.user_api_connection(base)
        assert connection["connection_origin"] == "user_api"
        assert connection["service_provider"] == name
    assert providers.available_providers() == []


def test_unimplemented_native_protocol_is_explicit_and_never_sent(configured, monkeypatch):
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("unadapted protocol dispatched"))
    with pytest.raises(ValueError, match="USER_API_PROTOCOL_NOT_ADAPTED"):
        user_api_adapter.configure({"provider": "user_api", "base_url": "https://api.anthropic.com/v1",
                                   "api_key": "synthetic-key", "model": "synthetic-model", "protocol": "anthropic_messages"})
    # Failed validation preserves the previous working actor configuration.
    assert user_api_adapter.status()["service_provider"] == "groq"
    _configure_test_runtime(base_url="https://api.anthropic.com/v1", protocol="anthropic_messages")
    assert user_api_adapter.status()["admission_state"] == "NOT_ADAPTED"
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_protocol_not_adapted"


@pytest.mark.parametrize("url", [
    "https://localhost/v1", "https://foo.local/v1", "https://foo.internal/v1",
    "https://127.1/v1", "https://[::1]/v1", "https://10.0.0.1/v1", "https://8.8.8.8/v1",
    "https://custom.example.net:8443/v1", "https://custom.example.net/v1?x=1",
    "https://custom.example.net/v1#fragment", "https://key@custom.example.net/v1",
    "https://custom.example.net/../v1", "https://custom.example.net/v1%2fchat",
    "https://custom.example.net//v1", "https://custom.example.net./v1",
])
def test_custom_endpoint_unsafe_grammar_never_resolves(configured, monkeypatch, url):
    monkeypatch.setattr(user_api_adapter.socket, "getaddrinfo", lambda *a, **k: pytest.fail("unsafe URL resolved"))
    _configure_test_runtime(base_url=url)
    assert _approved_gateway("s", "u", external_user_input=True)[1] == "user_api_destination_not_allowed"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "100.64.0.1", "192.168.1.1",
    "192.0.0.8", "198.18.0.1", "224.0.0.1", "0.0.0.0", "::1", "fc00::1", "fe80::1",
    "::ffff:127.0.0.1", "::ffff:8.8.8.8", "64:ff9b::7f00:1", "2002:7f00:1::", "2001::1"])
def test_nonpublic_or_tunneled_addresses_are_denied(address):
    assert user_api_adapter._public_address(address) is False


def _dns_answer(address):
    import socket
    return (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 443))


@pytest.mark.parametrize("addresses", [[], [_dns_answer("127.0.0.1")], [_dns_answer("8.8.8.8"), _dns_answer("10.0.0.1")]])
def test_dns_private_empty_and_mixed_answers_fail_closed(monkeypatch, addresses):
    monkeypatch.setattr(user_api_adapter.socket, "getaddrinfo", lambda *a, **k: addresses)
    monkeypatch.setattr(user_api_adapter, "_PinnedHTTPSConnection", lambda *a, **k: pytest.fail("unvalidated address connected"))
    req = urllib.request.Request("https://custom.example.net/v1/chat/completions", data=b"{}", method="POST")
    with pytest.raises(PermissionError, match="USER_API_DESTINATION_NOT_ALLOWED"):
        with user_api_adapter._open(req, timeout=1):
            pytest.fail("invalid DNS was admitted")


def test_pinned_tls_authenticates_original_hostname_without_second_dns(monkeypatch):
    import ssl
    import socket
    connections = []
    class FakeSocket:
        def settimeout(self, timeout): assert timeout == 3
        def connect(self, address): connections.append(address)
        def close(self): pass
    monkeypatch.setattr(socket, "socket", lambda *a: FakeSocket())
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("DNS rebinding attempted"))
    conn = user_api_adapter._PinnedHTTPSConnection("custom.example.net", _dns_answer("8.8.8.8"), 3)
    assert conn._context.verify_mode == ssl.CERT_REQUIRED
    assert conn._context.check_hostname is True
    seen = []
    monkeypatch.setattr(conn._context, "wrap_socket", lambda sock, **kw: seen.append(kw["server_hostname"]) or sock)
    conn.connect()
    assert connections == [("8.8.8.8", 443)] and seen == ["custom.example.net"]
    conn.close()


@pytest.mark.parametrize("response_status", [200, 301, 302, 303, 307, 308, 401])
def test_transport_pins_once_ignores_proxies_and_never_redirects(monkeypatch, response_status):
    from types import SimpleNamespace
    lookups, calls, closed = [], [], []
    def resolve(host, port, **kw):
        lookups.append((host, port))
        return [_dns_answer("8.8.8.8")] if len(lookups) == 1 else [_dns_answer("127.0.0.1")]
    class FakeConnection:
        def __init__(self, host, address, timeout):
            assert host == "custom.example.net" and address == _dns_answer("8.8.8.8")
        def request(self, method, path, body, headers): calls.append((method, path, body, headers))
        def getresponse(self): return SimpleNamespace(status=response_status, headers={"Location": "http://127.0.0.1/secret"})
        def close(self): closed.append(True)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8888")
    monkeypatch.setattr(user_api_adapter.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(user_api_adapter, "_PinnedHTTPSConnection", FakeConnection)
    req = urllib.request.Request("https://custom.example.net/v1/chat/completions", data=b"{}", headers={"Authorization": "Bearer synthetic"}, method="POST")
    if response_status == 200:
        with user_api_adapter._open(req, 1) as response: assert response.status == 200
    else:
        with pytest.raises(urllib.error.HTTPError) as error:
            with user_api_adapter._open(req, 1): pytest.fail("redirect/error body accepted")
        assert error.value.code == response_status
    assert lookups == [("custom.example.net", 443)]
    assert len(calls) == 1 and len(closed) == 1
    assert calls[0][:3] == ("POST", "/v1/chat/completions", b"{}")


def test_tls_failure_closes_socket_before_credentials_are_transmitted(configured, monkeypatch):
    import ssl
    sockets = []
    class FakeSocket:
        def __init__(self): self.closed = False
        def settimeout(self, timeout): pass
        def connect(self, address): assert address == ('8.8.8.8', 443)
        def sendall(self, data): pytest.fail('credentials sent before TLS verification')
        def close(self): self.closed = True
    def new_socket(*args):
        item = FakeSocket(); sockets.append(item); return item
    context = ssl.create_default_context()
    def bad_certificate(*args, **kwargs):
        raise ssl.SSLCertVerificationError('synthetic certificate mismatch')
    monkeypatch.setattr(context, 'wrap_socket', bad_certificate)
    monkeypatch.setattr(user_api_adapter.ssl, 'create_default_context', lambda: context)
    monkeypatch.setattr(user_api_adapter.socket, 'getaddrinfo', lambda *a, **k: [_dns_answer('8.8.8.8')])
    monkeypatch.setattr(user_api_adapter.socket, 'socket', new_socket)
    _configure_test_runtime(base_url='https://custom.example.net/v1')
    assert _approved_adapter('s', 'u', external_user_input=True) == (None, 'user_api_unavailable', None)
    assert len(sockets) == 1 and sockets[0].closed


def test_dns_denial_happens_only_after_exact_consent_and_is_not_replayed(configured, monkeypatch):
    _configure_test_runtime(base_url='https://custom.example.net/v1')
    lookups = []
    def private_destination(*a, **k):
        lookups.append(True)
        return [_dns_answer('169.254.169.254')]
    monkeypatch.setattr(user_api_adapter.socket, 'getaddrinfo', private_destination)
    monkeypatch.setattr(user_api_adapter, '_PinnedHTTPSConnection', lambda *a, **k: pytest.fail('private socket opened'))
    preview = core.chat('s', 'u', external_user_input=True)[2]['approval_request']
    assert lookups == []
    approval = {'confirmed': True, 'confirmation_id': preview['confirmation_id'], 'resource': preview['resource']}
    assert core.chat('s', 'u', external_user_input=True, external_approval=approval)[1] == 'user_api_destination_not_allowed'
    assert core.chat('s', 'u', external_user_input=True, external_approval=approval)[1] == 'user_api_confirmation_invalid'
    assert lookups == [True]
