from lumenis.system.ai_gateway import core, user_api_adapter


def test_default_never_calls_third_party(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "k")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "m")
    monkeypatch.setattr(user_api_adapter.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert core._chat("s", "u") == (None, "provider_disabled")
    assert core.chat("s", "u")[1] == "provider_disabled"


def test_explicit_user_api_is_used_without_fallback(monkeypatch):
    import io, json
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
    monkeypatch.setattr(user_api_adapter.urllib.request, "urlopen", fake)
    assert core._chat("s", "u") == ("ok", "user_api")
    assert seen["url"] == "https://example.invalid/v1/chat/completions"

    def boom(req, timeout=None): raise OSError("down")
    monkeypatch.setattr(user_api_adapter.urllib.request, "urlopen", boom)
    assert core._chat("s", "u") == (None, "user_api_unavailable")
