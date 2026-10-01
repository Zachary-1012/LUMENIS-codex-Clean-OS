import pytest
import requests

import local_ai_client as local_module


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def _enable_mock_provider(monkeypatch):
    from lumenis.system.ai_gateway import providers
    monkeypatch.setattr(
        providers, 'RETIRED_PROVIDERS', providers.RETIRED_PROVIDERS - {'ollama'},
    )
    monkeypatch.setitem(providers.PROVIDER_REGISTRY['ollama'], 'status', providers.ACTIVE)


def _client(monkeypatch):
    _enable_mock_provider(monkeypatch)
    client = local_module.LocalAIClient()
    client.available = True
    client.available_models = ["qwen3:4b"]
    client.default_model = "qwen3:4b"
    return client


@pytest.mark.parametrize("content", ["", "   ", None, []])
def test_generate_empty_completion_is_not_success(monkeypatch, content):
    client = _client(monkeypatch)
    monkeypatch.setattr(
        local_module.requests,
        "post",
        lambda *_args, **_kwargs: FakeResponse({"response": content}),
    )

    result = client.generate("synthetic prompt")

    assert result["ok"] is False
    assert result.get("response") in (None, "")
    assert result.get("error")


@pytest.mark.parametrize(
    "message",
    [
        {"content": ""},
        {"content": "   "},
        {"content": None},
        {"content": "", "thinking": "private reasoning only"},
    ],
)
def test_chat_empty_or_reasoning_only_completion_is_not_success(monkeypatch, message):
    client = _client(monkeypatch)
    monkeypatch.setattr(
        local_module.requests,
        "post",
        lambda *_args, **_kwargs: FakeResponse({"message": message}),
    )

    result = client.chat([{"role": "user", "content": "synthetic prompt"}])

    assert result["ok"] is False
    assert result.get("message") in (None, "")
    assert result.get("error")


@pytest.mark.parametrize("method", ["generate", "chat"])
def test_unfinished_response_is_not_success(monkeypatch, method):
    client = _client(monkeypatch)
    payload = {"done": False, "response": "partial result", "message": {"content": "partial result"}}
    monkeypatch.setattr(local_module.requests, "post", lambda *_args, **_kwargs: FakeResponse(payload))

    if method == "generate":
        result = client.generate("synthetic prompt")
    else:
        result = client.chat([{"role": "user", "content": "synthetic prompt"}])

    assert result["ok"] is False
    assert result.get("error")


def test_generate_preserves_nonempty_completion_and_model(monkeypatch):
    client = _client(monkeypatch)
    captured = {}

    def fake_post(_url, json, **_kwargs):
        captured.update(json)
        return FakeResponse({"response": "synthetic result", "eval_count": 3})

    monkeypatch.setattr(local_module.requests, "post", fake_post)
    result = client.generate("synthetic prompt")

    assert result["ok"] is True
    assert result["response"] == "synthetic result"
    assert result["model"] == "qwen3:4b"
    assert captured["model"] == "qwen3:4b"


def test_chat_preserves_nonempty_completion_and_model(monkeypatch):
    client = _client(monkeypatch)
    captured = {}

    def fake_post(_url, json, **_kwargs):
        captured.update(json)
        return FakeResponse({"message": {"content": "synthetic result"}})

    monkeypatch.setattr(local_module.requests, "post", fake_post)
    result = client.chat([{"role": "user", "content": "synthetic prompt"}])

    assert result["ok"] is True
    assert result["message"] == "synthetic result"
    assert result["model"] == "qwen3:4b"
    assert captured["model"] == "qwen3:4b"


@pytest.mark.parametrize("method", ["generate", "chat"])
def test_unavailable_ollama_stays_unavailable(monkeypatch, method):
    _enable_mock_provider(monkeypatch)
    client = local_module.LocalAIClient()
    calls = []

    def unavailable(*_args, **_kwargs):
        raise requests.exceptions.ConnectionError("synthetic unavailable")

    monkeypatch.setattr(local_module.requests, "get", unavailable)
    monkeypatch.setattr(local_module.requests, "post", lambda *_args, **_kwargs: calls.append(True))

    if method == "generate":
        result = client.generate("synthetic prompt")
    else:
        result = client.chat([{"role": "user", "content": "synthetic prompt"}])

    assert result["ok"] is False
    assert result.get('status') == 'unavailable'
    assert calls == []


def test_enabled_but_unreachable_status_is_not_provider_disabled(monkeypatch):
    _enable_mock_provider(monkeypatch)
    client = local_module.LocalAIClient()
    monkeypatch.setattr(
        local_module.requests, 'get',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            requests.exceptions.ConnectionError('synthetic unavailable')
        ),
    )

    status = client.get_status()

    assert status['available'] is False
    assert status['status'] == 'unavailable'
    assert status['reason'] == 'unavailable'


def test_stale_available_client_cannot_probe_or_generate_when_retired(monkeypatch):
    client = local_module.LocalAIClient()
    client.available = True
    client.available_models = ['stale-model']
    get_calls = []
    post_calls = []
    monkeypatch.setattr(local_module.requests, 'get', lambda *_args, **_kwargs: get_calls.append(True))
    monkeypatch.setattr(local_module.requests, 'post', lambda *_args, **_kwargs: post_calls.append(True))

    generated = client.generate('synthetic prompt')
    chatted = client.chat([{'role': 'user', 'content': 'synthetic prompt'}])
    health = client.health_check(retries=5, retry_interval=0)
    status = client.get_status()

    assert generated == {'ok': False, 'status': 'provider_disabled', 'error': 'provider_disabled'}
    assert chatted == {'ok': False, 'status': 'provider_disabled', 'error': 'provider_disabled'}
    assert health['blocked_reason'] == 'provider_disabled'
    assert status['status'] == 'provider_disabled'
    assert client.available is False
    assert client.available_models == []
    assert get_calls == []
    assert post_calls == []
