from __future__ import annotations

import pytest


def _clear_current_config_env(monkeypatch):
    for key in (
        "APP_PORT", "TAIKOO_PORT", "TAIKOO_AUTH_USER", "TAIKOO_AUTH_PASSWORD",
        "AI_PROVIDER", "ALLOW_CLOUD_AI", "LOCAL_AI_PREFERRED",
    ):
        monkeypatch.delenv(key, raising=False)


def test_env_example_is_documentation_only(tmp_path, monkeypatch):
    import config

    _clear_current_config_env(monkeypatch)
    example = tmp_path / ".env.example"
    example.write_text("LUMENIS_EXAMPLE_SENTINEL=must-not-load\n", encoding="utf-8")
    monkeypatch.setattr(config, "ENV_FILE", str(tmp_path / ".env-missing"))
    monkeypatch.setattr(config, "ENV_EXAMPLE_FILE", str(example))
    monkeypatch.delenv("LUMENIS_EXAMPLE_SENTINEL", raising=False)
    config.load_env()
    assert "LUMENIS_EXAMPLE_SENTINEL" not in config.os.environ


def test_compatibility_config_defaults_are_current_and_fail_closed(tmp_path, monkeypatch):
    import config

    _clear_current_config_env(monkeypatch)
    monkeypatch.setattr(config, "ENV_FILE", str(tmp_path / ".env-missing"))
    monkeypatch.setattr(config, "SYSTEM_CONFIG_FILE", str(tmp_path / "system-config-missing.json"))
    current = config.Config()
    assert current.get("APP_PORT") == 8201
    assert current.get("TAIKOO_PORT") == 8201
    assert current.get("TAIKOO_AUTH_USER") == ""
    assert current.get("AI_PROVIDER") == "owned"
    assert current.get("ALLOW_CLOUD_AI") is False
    assert current.get("LOCAL_AI_PREFERRED") is False
    result = current.validate()
    assert result["valid"] is True
    assert result["details"]["product_ai_provider"] == "owned"
    assert result["details"]["external_ai_fallback_allowed"] is False
    assert result["details"]["email_required_by_current_product"] is False


def test_compatibility_config_rejects_retired_provider_and_cloud_fallback(tmp_path, monkeypatch):
    import config

    _clear_current_config_env(monkeypatch)
    monkeypatch.setattr(config, "ENV_FILE", str(tmp_path / ".env-missing"))
    monkeypatch.setattr(config, "SYSTEM_CONFIG_FILE", str(tmp_path / "system-config-missing.json"))
    current = config.Config()
    current.set("AI_PROVIDER", "zhipu")
    current.set("ALLOW_CLOUD_AI", True)
    result = current.validate()
    assert result["valid"] is False
    assert any("AI_PROVIDER" in item for item in result["warnings"])
    assert any("ALLOW_CLOUD_AI" in item for item in result["warnings"])


def test_explicit_user_api_configuration_keeps_no_fallback(tmp_path, monkeypatch):
    import config
    _clear_current_config_env(monkeypatch)
    monkeypatch.setattr(config, "ENV_FILE", str(tmp_path / ".env-missing"))
    monkeypatch.setattr(config, "SYSTEM_CONFIG_FILE", str(tmp_path / "system-config-missing.json"))
    current = config.Config()
    current.set("AI_PROVIDER", "user_api")
    assert current.validate()["valid"] is False
    current.set("USER_MODEL_API_BASE_URL", "https://api.groq.com/openai/v1")
    current.set("USER_MODEL_API_KEY", "not-a-real-key")
    current.set("USER_MODEL_API_MODEL", "model")
    result = current.validate()
    assert result["valid"] is True
    assert result["details"]["product_ai_provider"] == "user_api"
    assert result["details"]["external_ai_fallback_allowed"] is False


def test_retired_unicode_tunnel_path_cannot_return(monkeypatch):
    from pathlib import Path

    from scripts.audit_tools import verify_current_configuration as guard

    old_exists = Path.exists
    target = guard.ROOT / "deployment/deployment/启动远程访问.bat"
    monkeypatch.setattr(Path, "exists", lambda p: p == target or old_exists(p))
    with pytest.raises(AssertionError, match="removed public-tunnel launcher must not return"):
        guard.validate()

def test_legacy_settings_api_projects_current_runtime_truth(tmp_path, monkeypatch):
    import settings_module
    from lumenis.system.ai_gateway import core as gateway

    old_config = {
        "collection": {"auto_collect": True},
        "analysis": {"ai_enabled": True},
        "ai": {"provider": "local", "local_enabled": True, "model": "qwen2:7b"},
        "security": {"http_auth": True},
        "domain": {"local_url": "http://127.0.0.1:8200"},
    }
    path = tmp_path / "system_config.json"
    path.write_text(__import__("json").dumps(old_config), encoding="utf-8")
    monkeypatch.setattr(settings_module, "CONFIG_FILE", str(path))
    monkeypatch.delenv("REDNOTE_AUTO_RUN", raising=False)
    monkeypatch.delenv("TAIKOO_AUTH_USER", raising=False)
    monkeypatch.delenv("TAIKOO_AUTH_PASSWORD", raising=False)
    monkeypatch.setattr(
        gateway,
        "owned_inference_status",
        lambda: {
            "available": False,
            "service_binding": "NOT_BOUND",
            "state": "UNAVAILABLE",
            "reason": "OWNED_RUNTIME_NOT_BOUND",
            "model_id": None,
        },
    )

    current = settings_module.load_config()
    assert current["collection"]["auto_collect"] is False
    assert current["analysis"]["ai_enabled"] is False
    assert current["ai"]["provider"] == "owned"
    assert current["ai"]["local_enabled"] is False
    assert current["ai"]["fallback_allowed"] is False
    assert current["ai"]["service_binding"] == "NOT_BOUND"
    assert current["security"]["http_auth"] is False
    assert current["domain"]["local_url"] == "http://127.0.0.1:8201"


def test_settings_explicit_external_configuration_is_not_live_inference(tmp_path, monkeypatch):
    import settings_module

    monkeypatch.setattr(settings_module, "CONFIG_FILE", str(tmp_path / "missing.json"))
    monkeypatch.setenv("AI_PROVIDER", "user_api")
    monkeypatch.setenv("USER_MODEL_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("USER_MODEL_API_KEY", "not-a-real-key")
    monkeypatch.setenv("USER_MODEL_API_MODEL", "model")
    current = settings_module.load_config()["ai"]
    assert current["provider"] == "user_api"
    assert current["model"] == "model"
    assert current["available"] is False
    assert current["status"] == "CONFIGURED_NOT_VERIFIED"
    assert current["fallback_allowed"] is False
    assert "not-a-real-key" not in repr(current)
