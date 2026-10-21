"""Retired vision routes must fail closed before provider discovery or I/O."""
import pytest

from lumenis.system.ai_gateway import core, channel, providers


@pytest.mark.parametrize(
    ("provider", "local_only"),
    [
        ("auto", False),
        ("ollama", False),
        ("lmstudio", False),
        ("llama_cpp", False),
        ("zhipu", False),
        ("glm", False),
        ("openai", True),
    ],
)
def test_legacy_vision_entry_fails_closed_without_provider_probe(monkeypatch, provider, local_only):
    monkeypatch.setenv("AI_PROVIDER", provider)
    monkeypatch.setenv("ALLOW_CLOUD_AI", "true")

    def forbidden(*_args, **_kwargs):
        pytest.fail("retired compatibility route attempted provider discovery or I/O")

    monkeypatch.setattr(core, "_ollama_vision_chat", forbidden)
    monkeypatch.setattr(providers, "is_provider_available", forbidden)
    monkeypatch.setattr(core, "_provider_config", forbidden)
    monkeypatch.setattr(core.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(core.urllib.request, "build_opener", forbidden)
    monkeypatch.setattr(channel, "route_with_fallback", forbidden)

    assert core.vision_chat("private system", "private prompt", "opaque-image",
                            local_only=local_only) == (None, "provider_disabled")
    assert core._get_call_meta()["provider"] == "provider_disabled"


@pytest.mark.parametrize("provider", ["auto", "ollama", "lmstudio", "llama_cpp", "zhipu", "glm"])
def test_text_gateway_retired_selection_fails_before_provider_or_network(monkeypatch, provider):
    monkeypatch.setenv("AI_PROVIDER", provider)
    monkeypatch.setenv("ALLOW_CLOUD_AI", "true")

    def forbidden(*_args, **_kwargs):
        pytest.fail("retired compatibility route attempted provider discovery or I/O")

    monkeypatch.setattr(core, "_provider_config", forbidden)
    monkeypatch.setattr(providers, "is_provider_available", forbidden)
    monkeypatch.setattr(core.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(channel, "route_with_fallback", forbidden)

    assert core._chat("private system", "private user") == (None, "provider_disabled")
    assert core._get_call_meta()["provider"] == "provider_disabled"
