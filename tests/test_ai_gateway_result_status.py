"""Mock-only regression for canonical AI Gateway result validation."""

import json
from urllib.parse import urlsplit
import pytest

import ai_call_logger as acl
from lumenis.shared.database.repository import DatabaseRepository
from lumenis.system.ai_gateway import core


@pytest.fixture(autouse=True)
def _mock_only_gateway(monkeypatch):
    for key in (
        "ARK_API_KEY",
        "DASHSCOPE_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "OPENAI_PROXY",
    ):
        monkeypatch.delenv(key, raising=False)
    from lumenis.system.ai_gateway import providers
    monkeypatch.setattr(
        providers, "RETIRED_PROVIDERS", providers.RETIRED_PROVIDERS - {"zhipu", "ollama"},
    )
    monkeypatch.setitem(providers.PROVIDER_REGISTRY["zhipu"], "status", providers.ACTIVE)
    monkeypatch.setitem(providers.PROVIDER_REGISTRY["ollama"], "status", providers.ACTIVE)
    monkeypatch.setenv("AI_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-only-placeholder-never-sent")
    # These cases validate the mocked cloud transport, which requires explicit opt-in.
    monkeypatch.setenv("ALLOW_CLOUD_AI", "true")
    monkeypatch.setenv("ZHIPU_BASE_URL", "https://mock.invalid/v1")
    monkeypatch.setattr(core, "_provider_config", lambda: None)
    monkeypatch.setattr(core, "_detect_local", lambda: None)
    monkeypatch.setattr(
        core.urllib.request,
        "build_opener",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        core.urllib.request,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("unexpected direct provider request"),
    )
    core.ai_channel._PROVIDER_BREAKERS.clear()
    yield
    core.ai_channel._PROVIDER_BREAKERS.clear()


def _return_payload(monkeypatch, payload):
    calls = []
    body = json.dumps(payload).encode("utf-8")

    def fake_transport(url, payload_bytes, headers, **kwargs):
        calls.append(url)
        return body, 1

    monkeypatch.setattr(core.ai_channel, "post_with_retry", fake_transport)
    result = core._chat(
        "system", "user", temperature=0.0, max_tokens=16, model="glm-4.5-air"
    )
    return result, calls


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]},
            id="empty-content",
        ),
        pytest.param(
            {"choices": [{"message": {"content": "", "reasoning_content": "hidden"}, "finish_reason": "stop"}]},
            id="reasoning-only",
        ),
        pytest.param(
            {
                "error": {"message": "mock provider error"},
                "choices": [
                    {"message": {"content": "must not escape"}, "finish_reason": "stop"}
                ],
            },
            id="provider-error-body",
        ),
        pytest.param(
            {
                "choices": [
                    {"message": {"content": "partial output"}, "finish_reason": "length"}
                ]
            },
            id="length-finish-reason",
        ),
        pytest.param(
            {
                "status": "incomplete",
                "choices": [
                    {"message": {"content": "partial output"}, "finish_reason": "stop"}
                ],
            },
            id="incomplete-response-status",
        ),
    ],
)
def test_unusable_provider_result_is_not_success(monkeypatch, payload):
    result, calls = _return_payload(monkeypatch, payload)

    assert result == (None, "unavailable")
    assert calls == ["https://mock.invalid/v1/chat/completions"]


def test_transport_error_is_unavailable_not_policy_disabled(monkeypatch):
    def fake_transport(*args, **kwargs):
        raise OSError("mock transport error")

    monkeypatch.setattr(core.ai_channel, "post_with_retry", fake_transport)

    assert core._chat(
        "system", "user", temperature=0.0, max_tokens=16, model="glm-4.5-air"
    ) == (None, "unavailable")


def test_direct_local_chat_cannot_bypass_retired_provider(monkeypatch):
    from lumenis.system.ai_gateway import providers

    monkeypatch.setattr(
        providers, 'RETIRED_PROVIDERS', providers.RETIRED_PROVIDERS | {'ollama'},
    )
    calls = []
    monkeypatch.setattr(
        core, '_ollama_vision_json',
        lambda *_args, **_kwargs: calls.append(True),
    )

    result = core._call_local_chat(
        'ollama', 'qwen3:4b', 'http://127.0.0.1:11434',
        'system', 'user', 0.0, 16, 3,
    )

    assert result == (None, 'provider_disabled')
    assert calls == []


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


def test_complete_nonempty_provider_result_remains_success(monkeypatch):
    result, calls = _return_payload(
        monkeypatch,
        {
            "choices": [
                {"message": {"content": "complete answer"}, "finish_reason": "stop"}
            ]
        },
    )

    assert result == ("complete answer", "zhipu")
    assert calls == ["https://mock.invalid/v1/chat/completions"]


def _local_payload(monkeypatch, payload, *, show_payload=None, calls=None, base=None, model='qwen3:4b'):
    transport_calls = calls if calls is not None else []

    class Response:
        def __init__(self, body, url):
            self.body = json.dumps(body).encode("utf-8")
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

        def geturl(self):
            return self.url

    class Opener:
        def open(self, request, timeout):
            path = urlsplit(request.full_url).path
            body = json.loads(request.data.decode("utf-8"))
            transport_calls.append((path, body, timeout))
            response_body = show_payload if path == "/api/show" else payload
            return Response(response_body or {}, request.full_url)

    monkeypatch.setattr(core.urllib.request, "build_opener", lambda *_args, **_kwargs: Opener())

    return core._call_local_chat(
        "ollama", model, base or "http://127.0.0.1:11434",
        "system", "user", 0.0, 16, 3,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"message": {"content": "partial"}, "done": False, "done_reason": "length"},
        {"message": {"content": "partial"}, "done": True, "done_reason": "length"},
        {"message": {"content": "no completion marker"}, "done_reason": "stop"},
        {"message": {"content": "string completion marker"}, "done": "true", "done_reason": "stop"},
        {"message": {"content": "", "thinking": "hidden only"}, "done": True, "done_reason": "stop"},
    ],
)
def test_ollama_partial_or_thinking_only_response_is_not_success(monkeypatch, payload):
    with pytest.raises(ValueError):
        _local_payload(monkeypatch, payload)


def test_ollama_complete_final_content_remains_success(monkeypatch):
    calls = []
    assert _local_payload(monkeypatch, {
        "message": {"content": "local final", "thinking": "hidden"},
        "done": True,
        "done_reason": "stop",
    }, calls=calls) == ("local final", "ollama")
    assert calls == [
        ("/api/show", {"model": "qwen3:4b:local"}, 3),
        ("/api/chat", {
            "model": "qwen3:4b:local",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 16},
            "think": False,
        }, 3),
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("remote_model", "hosted-model"),
        ("remote_host", "https://inference.invalid"),
        ("remote_model", []),
    ],
)
def test_ollama_preflight_remote_or_malformed_metadata_sends_no_user_content(
    monkeypatch, field, value,
):
    calls = []

    with pytest.raises(ValueError, match="remote inference"):
        _local_payload(
            monkeypatch,
            {"message": {"content": "should not be reached"}, "done": True, "done_reason": "stop"},
            show_payload={field: value}, calls=calls,
        )

    assert [call[0] for call in calls] == ["/api/show"]
    assert calls[0][1] == {"model": "qwen3:4b:local"}


@pytest.mark.parametrize("field", ["remote_model", "remote_host"])
def test_ollama_rejects_remote_metadata_on_chat_response(monkeypatch, field):
    calls = []
    response = {
        "message": {"content": "must not be accepted"},
        "done": True,
        "done_reason": "stop",
        field: "hosted-model",
    }

    with pytest.raises(ValueError, match="remote inference"):
        _local_payload(monkeypatch, response, show_payload={}, calls=calls)

    assert [call[0] for call in calls] == ["/api/show", "/api/chat"]
    assert calls[0][1] == {"model": "qwen3:4b:local"}


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("qwen3:local", "qwen3:local"),
        ("qwen3:4b:local", "qwen3:4b:local"),
        ("qwen3: local", "qwen3:local"),
        ("my-cloud", "my-cloud:local"),
        ("registry.example:5000/team/model:tag", "registry.example:5000/team/model:tag:local"),
    ],
)
def test_ollama_local_transport_selector_preserves_valid_model_refs(model, expected):
    assert core._ollama_local_transport_model(model) == expected


@pytest.mark.parametrize(
    "model",
    [
        "qwen3:cloud",
        "qwen3: cloud",
        "qwen3:4b-cloud",
        "qwen3:4b:cloud",
        "qwen3:4b:cloud:local",
        "qwen3:4b:local:local",
    ],
)
def test_ollama_cloud_or_nested_source_model_is_rejected_before_any_call(monkeypatch, model):
    calls = []

    with pytest.raises(ValueError):
        _local_payload(monkeypatch, {}, calls=calls, model=model)

    assert calls == []


def test_ollama_rejects_non_loopback_base_before_network(monkeypatch):
    def forbid_network(*_args, **_kwargs):
        pytest.fail("non-loopback Ollama endpoint was contacted")

    monkeypatch.setattr(core.urllib.request, "build_opener", forbid_network)

    with pytest.raises(ValueError, match="loopback HTTP"):
        _local_payload(monkeypatch, {}, base="https://ollama.example/api")


def _mock_local_gateway_chat(monkeypatch, result):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setattr(
        core,
        "_provider_config",
        lambda: ("ollama", "qwen3:4b", "http://127.0.0.1:11434"),
    )
    monkeypatch.setattr(core, "_chat", lambda *_args, **_kwargs: result)
    monkeypatch.setattr(
        core,
        "_get_call_meta",
        lambda: {
            "model": "qwen3:4b",
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        },
    )


def test_chat_exposes_call_id_for_recorded_provider_result(tmp_path, monkeypatch):
    repository = DatabaseRepository(str(tmp_path / "gateway_calls.db"))
    monkeypatch.setattr(acl, "get_repository", lambda: repository)
    assert acl.init_db() is True
    _mock_local_gateway_chat(monkeypatch, ("synthetic answer", "ollama"))

    output, provider, meta = core.chat(
        "synthetic system", "synthetic user", track=False
    )

    assert output == "synthetic answer"
    assert provider == "ollama"
    assert isinstance(meta["call_id"], int)
    row = repository.query_one(
        "SELECT provider, model, output, success FROM ai_call_logs WHERE id = ?",
        (meta["call_id"],),
    )
    assert tuple(row) == ("ollama", "qwen3:4b", "synthetic answer", 1)


def test_logger_failure_preserves_unavailable_gateway_result(monkeypatch):
    _mock_local_gateway_chat(monkeypatch, (None, "rule"))

    def fail_database(*_args, **_kwargs):
        raise RuntimeError("isolated logger database failure")

    monkeypatch.setattr(acl, "_get_conn", fail_database)

    output, provider, meta = core.chat(
        "synthetic system", "synthetic unavailable-model request", track=False
    )

    assert output is None
    assert provider == "rule"
    assert meta["call_id"] is None
