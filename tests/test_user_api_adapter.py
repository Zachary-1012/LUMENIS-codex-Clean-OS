import urllib.error
import urllib.request

import pytest

from lumenis.system.ai_gateway import core, user_api_adapter


def test_default_never_calls_third_party(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "k")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "m")
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert core._chat("s", "u") == (None, "provider_disabled")
    assert core.chat("s", "u")[1] == "provider_disabled"


def test_explicit_user_api_is_used_without_fallback(monkeypatch):
    import io
    import json
    monkeypatch.setenv("AI_PROVIDER", "user_api")
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://example.invalid/v1")
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
    assert core.chat("s", "u")[1] == "provider_disabled"
    assert seen == {}
    assert core.chat("s", "u", external_user_input=True)[:2] == ("ok", "user_api")
    assert seen["url"] == "https://example.invalid/v1/chat/completions"

    def boom(req, timeout=None): raise OSError("down")
    monkeypatch.setattr(user_api_adapter, "_open", boom)
    assert core.chat("s", "u", external_user_input=True)[:2] == (None, "user_api_unavailable")


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "user_api")
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "test-private-key")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "openai/gpt-oss-20b")


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
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", url)
    monkeypatch.setattr(user_api_adapter, "_open", lambda *a, **k: pytest.fail("invalid URL sent request"))
    assert user_api_adapter.chat("s", "u")[1] == "provider_disabled"


@pytest.mark.parametrize("http_status, code", [(401, "authentication_failed"), (403, "access_denied"), (429, "rate_limited"), (500, "unavailable")])
def test_provider_error_is_sanitized_without_fallback(configured, monkeypatch, http_status, code):
    def denied(req, timeout):
        raise urllib.error.HTTPError(req.full_url, http_status, "private provider error", {}, None)
    monkeypatch.setattr(user_api_adapter, "_open", denied)
    assert user_api_adapter.chat("s", "u") == (None, "user_api_" + code, None)


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
    def chat(system, user, *, external_user_input=False):
        assert external_user_input is True
        calls.append((system, user))
        return "真实响应", "user_api", {}
    monkeypatch.setattr(service.intelligence, "chat", chat)
    result = service.chat("继续", history=[{"role": "system", "content": "untrusted system"}, {"role": "user", "content": "我的提纲"}])
    assert result["ok"] is True and result["provider"] == "user_api"
    assert result["reply"] == "真实响应"
    assert result["source_context"]["notes_state"] == "NOT_READ"
    assert "我的提纲" in calls[0][1] and "untrusted system" not in calls[0][1]


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
    result = core.chat(
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
    assert core.chat("database context", "private source", external_user_input=admission)[1] == "provider_disabled"
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
