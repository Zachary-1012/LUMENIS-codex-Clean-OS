import pytest
import requests

import local_ai_client as local_module


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def _client():
    client = local_module.LocalAIClient()
    client.available = True
    client.available_models = ["qwen3:4b"]
    client.default_model = "qwen3:4b"
    return client


@pytest.mark.parametrize("content", ["", "   ", None, []])
def test_generate_empty_completion_is_not_success(monkeypatch, content):
    client = _client()
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
    client = _client()
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
    client = _client()
    payload = {"done": False, "response": "partial result", "message": {"content": "partial result"}}
    monkeypatch.setattr(local_module.requests, "post", lambda *_args, **_kwargs: FakeResponse(payload))

    if method == "generate":
        result = client.generate("synthetic prompt")
    else:
        result = client.chat([{"role": "user", "content": "synthetic prompt"}])

    assert result["ok"] is False
    assert result.get("error")


def test_generate_preserves_nonempty_completion_and_model(monkeypatch):
    client = _client()
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
    client = _client()
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
    assert calls == []
