"""Current Gateway completion integrity; synthetic permission and transport only.

Retired local/provider transports are checked as inert, never reactivated to
exercise obsolete fixtures. Completion semantics run through the admitted
user API Gateway with the real Permission preview/confirmation boundary.
"""
import io
import json
import pytest
from lumenis.system.ai_gateway import core, user_api_adapter, providers
from tests.test_user_api_adapter import configured, _approved_gateway


@pytest.fixture(autouse=True)
def no_unmocked_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("unexpected network or provider discovery")
    monkeypatch.setattr(user_api_adapter, "_open", forbidden)
    monkeypatch.setattr(core.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(core.urllib.request, "build_opener", forbidden)


def _return_payload(monkeypatch, payload):
    calls = []
    class Response(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def transport(request, timeout=None):
        calls.append(request.full_url)
        return Response(json.dumps(payload).encode())
    monkeypatch.setattr(user_api_adapter, "_open", transport)
    result = _approved_gateway("synthetic system", "synthetic user", external_user_input=True)
    return result, calls


@pytest.mark.parametrize("payload", [
    {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]},
    {"choices": [{"message": {"content": "", "reasoning_content": "hidden"}, "finish_reason": "stop"}]},
    {"error": {"message": "mock error"}, "choices": [{"message": {"content": "must not escape"}, "finish_reason": "stop"}]},
    {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]},
    {"status": "incomplete", "choices": [{"message": {"content": "partial"}, "finish_reason": "stop"}]},
    {"status": "failed", "choices": [{"message": {"content": "partial"}}]},
    {"status": "in_progress", "choices": [{"message": {"content": "partial"}}]},
    {"status": True, "choices": [{"message": {"content": "partial"}}]},
    {"choices": "malformed"}, {"choices": []}, {"choices": [{"message": []}]},
    {"choices": [{"message": {"content": 1}}]}, [], None,
])
def test_unusable_provider_result_is_not_success(configured, monkeypatch, payload):
    result, calls = _return_payload(monkeypatch, payload)
    assert result[:2] == (None, "user_api_invalid_response")
    assert calls == [user_api_adapter.GROQ_CHAT_URL]


@pytest.mark.parametrize("status", [None, "completed"])
def test_complete_nonempty_provider_result_remains_success(configured, monkeypatch, status):
    result, calls = _return_payload(monkeypatch, {"status": status, "choices": [{"message": {"content": "complete answer"}, "finish_reason": "stop"}]})
    assert result[:2] == ("complete answer", "user_api")
    assert calls == [user_api_adapter.GROQ_CHAT_URL]


def test_transport_error_is_unavailable_not_policy_disabled(configured, monkeypatch):
    def failed(*args, **kwargs): raise OSError("synthetic transport failure")
    monkeypatch.setattr(user_api_adapter, "_open", failed)
    assert _approved_gateway("s", "u", external_user_input=True)[:2] == (None, "user_api_unavailable")


@pytest.mark.parametrize("model", ["qwen3:4b", "qwen3:cloud", "qwen3: cloud", "qwen3:4b-cloud", "qwen3:4b:cloud", "qwen3:4b:cloud:local", "qwen3:4b:local:local"])
@pytest.mark.parametrize("base", ["http://127.0.0.1:11434", "https://ollama.example/api"])
def test_retired_local_transport_is_inert_for_all_model_and_endpoint_forms(model, base):
    assert core._call_local_chat("ollama", model, base, "private system", "private user", 0, 16, 3) == (None, "provider_disabled")
    assert providers.is_provider_available("ollama") is False


def test_untyped_chat_cannot_use_configured_transport_or_create_success(configured):
    assert core.chat("source context", "source material", use_cache=True)[:2] == (None, "provider_disabled")
    assert core._chat("s", "u") == (None, "provider_disabled")


def test_legacy_analysis_helpers_use_owned_gateway_and_never_fabricate_fallbacks(monkeypatch):
    calls = []

    def unavailable(*, text, analysis_type, note_id=None):
        calls.append((analysis_type, text, note_id))
        return {
            'ok': False, 'status': 'UNAVAILABLE', 'code': 'OWNED_RUNTIME_NOT_BOUND',
            'provider': 'owned', 'analysis': None,
        }

    monkeypatch.setattr(core, 'run_owned_analysis', unavailable)
    monkeypatch.setattr(
        core, 'chat', lambda *_args, **_kwargs: pytest.fail('legacy provider chat called'),
    )

    connection = core.test_connection('source')
    sentiment = core.analyze_sentiment('source')
    summary = core.generate_summary('source')
    keywords = core.extract_keywords('source')

    assert connection['ok'] is False and connection['reply'] is None
    assert sentiment['ok'] is False and sentiment['sentiment'] is None
    assert sentiment['label'] is None and sentiment['summary'] is None
    assert summary == ''
    assert keywords == []
    assert [item[0] for item in calls] == [
        'connection_test', 'sentiment', 'summary', 'keywords',
    ]
