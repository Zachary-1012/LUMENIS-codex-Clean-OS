"""Mock-only regression for canonical AI Gateway result validation."""

import json
import pytest

from lumenis.system.ai_gateway import core


@pytest.fixture(autouse=True)
def _mock_only_gateway(monkeypatch):
    for key in (
        "ARK_API_KEY",
        "DASHSCOPE_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "AI_PROVIDER",
        "OPENAI_PROXY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ZHIPU_API_KEY", "test-only-placeholder-never-sent")
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

    assert result == (None, "rule")
    assert calls == ["https://mock.invalid/v1/chat/completions"]


def test_transport_error_is_rule_fallback(monkeypatch):
    def fake_transport(*args, **kwargs):
        raise OSError("mock transport error")

    monkeypatch.setattr(core.ai_channel, "post_with_retry", fake_transport)

    assert core._chat(
        "system", "user", temperature=0.0, max_tokens=16, model="glm-4.5-air"
    ) == (None, "rule")


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


def _local_payload(monkeypatch, payload):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(core.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    return core._call_local_chat(
        "ollama", "qwen3:4b", "http://127.0.0.1:11434",
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
    assert _local_payload(monkeypatch, {
        "message": {"content": "local final", "thinking": "hidden"},
        "done": True,
        "done_reason": "stop",
    }) == ("local final", "ollama")
