from lumenis.system.ai_gateway import channel, providers


def test_ark_doubao_remain_compatibility_only_even_with_key(monkeypatch):
    monkeypatch.setenv("ARK_API_KEY", "test-placeholder-never-sent")
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "ark,doubao,qwen")

    assert providers.provider_status("ark") == providers.LEGACY
    assert providers.provider_status("doubao") == providers.LEGACY
    assert providers.provider_info("ark")["role"] == "compatibility_only"
    assert providers.is_provider_available("ark") is False
    assert providers.is_provider_available("doubao") is False
    assert channel.provider_chain() == []


def test_explicit_legacy_ark_route_fails_before_dispatch(monkeypatch):
    monkeypatch.setenv("ARK_API_KEY", "test-placeholder-never-sent")
    calls = []

    result, provider = channel.route_with_fallback(
        lambda selected: (calls.append(selected) or ("unexpected", selected)),
        providers=["ark"],
    )

    assert result is None
    assert provider == "provider_disabled"
    assert calls == []


def test_legacy_provider_status_read_does_not_discover_configuration(monkeypatch):
    monkeypatch.setenv("ARK_API_KEY", "test-placeholder-never-sent")
    monkeypatch.setattr(
        channel, "ensure_env_loaded",
        lambda: (_ for _ in ()).throw(AssertionError("provider status must not load config")),
    )

    statuses = channel.get_provider_status_v1()

    assert statuses["ark"]["status"] == providers.LEGACY
    assert statuses["ark"]["role"] == "compatibility_only"
    assert statuses["ark"]["dispatchable"] is False
    assert statuses["ark"]["api_key_configured"] is None
    assert providers.provider_status("doubao") == providers.LEGACY
    assert providers.is_provider_available("doubao") is False
