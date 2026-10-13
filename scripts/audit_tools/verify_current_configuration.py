from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_TEMPLATE = ROOT / ".env.example"
CONFIG = ROOT / "config.py"
APP = ROOT / "app.py"
SETTINGS_MODULE = ROOT / "settings_module.py"
TOOLCHAIN = ROOT / "app" / "toolchain.json"
APP_WORKFLOW = ROOT / ".github" / "workflows" / "app-verify.yml"
CURRENT = ROOT / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md"
DEPLOYMENT_README = ROOT / "deployment" / "README.md"
DEPLOYMENT_LOCAL = ROOT / "deployment" / "start_local.bat"
REMOVED_PUBLIC_LAUNCHERS = ('tunnel_guardian.py', 'deployment/start_remote.bat', 'deployment/启动远程访问.bat', 'start_tunnel.bat', 'start_cloudflare_stable.bat', 'cloudflared_guardian.ps1', 'monitor_cloudflare_tunnel.bat', 'start_cf.ps1', 'start_cloudflare_tunnel.bat', 'start_cloudflare_guardian.bat', 'start_cloudflare_hidden.vbs', 'start_cloudflare_hidden_new.vbs', 'deployment/deployment/σÉ»σè¿Φ┐£τ¿ïΦ«┐Θù«.bat')
INSTANCE_INSPECTOR = ROOT / "scripts" / "inspect_instances.ps1"


def fail(message: str) -> None:
    raise AssertionError(message)


def env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    keys: list[str] = []
    for raw in ENV_TEMPLATE.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        keys.append(key)
        values[key] = value.strip()
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        fail(f".env.example contains duplicate keys: {duplicates}")
    return values


def config_defaults() -> tuple[dict, str]:
    source = CONFIG.read_text(encoding="utf-8")
    tree = ast.parse(source)
    defaults = None
    load_source = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Config":
            for child in node.body:
                if isinstance(child, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "_DEFAULTS" for target in child.targets
                ):
                    defaults = ast.literal_eval(child.value)
        if isinstance(node, ast.FunctionDef) and node.name == "load_env":
            load_source = ast.get_source_segment(source, node) or ""
    if not isinstance(defaults, dict) or not load_source:
        fail("config.py Config._DEFAULTS/load_env not found")
    return defaults, load_source


def validate() -> None:
    env = env_values()
    exact = {
        "TAIKOO_PORT": "8201",
        "TAIKOO_AUTH_USER": "",
        "TAIKOO_AUTH_PASSWORD": "",
        "WEB_ADAPTERS": "",
        "WEB_BASE_QUERY": "",
        "TAIKOO_WEB_DISCOVERY": "0",
        "ZBC_WEIBO_COOKIE_JSON": "",
        "ZBC_BILI_COOKIE_JSON": "",
        "EMAIL_SMTP_HOST": "",
        "EMAIL_SMTP_USER": "",
        "EMAIL_SMTP_PASSWORD": "",
        "ALLOW_CLOUD_AI": "false",
        "DOUYIN_CDP_URL": "",
        "DOUYIN_LOCAL_WORKER_ENABLED": "false",
        "DOUYIN_LOCAL_WORKER_ACCOUNT": "",
        "X_READONLY_CDP_URL": "",
        "X_READONLY_LOCAL_WORKER_ENABLED": "false",
        "X_READONLY_LOCAL_WORKER_ACCOUNT": "",
        "LUMENIS_FFMPEG_PATH": "",
        "LUMENIS_FFPROBE_PATH": "",
        "LUMENIS_EVIDENCE_HMAC_KEY_RING": "",
        "LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID": "",
        "LUMENIS_TRAINING_RECEIPT_KEY_RING": "",
        "LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID": "",
        "LUMENIS_TRAINING_SSH_ENDPOINT_PATH": "",
        "LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK": "false",
    }
    for key, expected in exact.items():
        if env.get(key) != expected:
            fail(f".env.example {key} must be {expected!r}, got {env.get(key)!r}")
    retired = {
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "LMSTUDIO_BASE_URL", "LMSTUDIO_MODEL",
        "LLAMA_CPP_BASE_URL", "LLAMA_CPP_MODEL", "DASHSCOPE_API_KEY", "QWEN_MODEL",
        "OPENAI_API_KEY", "OPENAI_MODEL", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL",
        "ZHIPU_API_KEY", "ZHIPU_MODEL", "ZHIPU_STRONG_MODEL", "ZHIPU_BASE_URL",
        "ARK_API_KEY", "ARK_MODEL", "ARK_BASE_URL", "ARK_MAX_DAILY_TOKEN", "DASHSCOPE_BASE_URL",
    }
    present = sorted(key for key in retired if key in env)
    if present:
        fail(f"third-party provider keys must be deleted from .env.example: {present}")

    defaults, load_source = config_defaults()
    required_defaults = {
        "APP_PORT": 8201,
        "TAIKOO_PORT": 8201,
        "TAIKOO_AUTH_USER": "",
        "AI_PROVIDER": "owned",
        "ALLOW_CLOUD_AI": False,
        "LOCAL_AI_PREFERRED": False,
    }
    for key, expected in required_defaults.items():
        if defaults.get(key) != expected:
            fail(f"config.py default {key} drifted: {defaults.get(key)!r}")
    if "ENV_EXAMPLE_FILE" in load_source or "env.example" in load_source:
        fail("config.load_env must never load .env.example")
    config_source = CONFIG.read_text(encoding="utf-8")
    if "config.get(\'APP_PORT\', 8200)" in config_source:
        fail("config.py must not expose a fallback port 8200 in active diagnostics")

    app = APP.read_text(encoding="utf-8")
    forbidden = (
        "os.getenv('TAIKOO_WEB_DISCOVERY','1')",
        "os.getenv('TAIKOO_PORT','8200')",
        "env.get('TAIKOO_PORT', '8200')",
        "configured_production_port = 8200",
        "Playwright/XHS search + rednote CDP",
        "AI provider + auditable rule fallback",
        "公开网页发现 → 关键词反馈 → 小红书/rednote浏览器采集",
        "'auto_collect': True",
        "'company_name': os.getenv('TAIKOO_COMPANY_NAME', '广州太古汇')",
        "else ['广州太古汇']",
        "'ai_enabled': ARK_LLM_AVAILABLE",
    )
    present = [token for token in forbidden if token in app]
    if present:
        fail(f"active app configuration/status still contains stale defaults: {present}")
    required_app = (
        "os.getenv('TAIKOO_WEB_DISCOVERY','0')",
        "APP_PORT=int(os.getenv('TAIKOO_PORT','8201'))",
        "'ai_provider': 'owned'",
        "'ai_fallback_allowed': False",
        "'data_source': 'Source → Evidence → Canonical'",
        "'last_collection_semantics': 'historical_observation_not_current_readiness'",
        "'product_account_redesign_deferred': True",
        "'default_context': 'GLOBAL_ALL'",
        "'default_subject': None",
        "'collector_type': 'SYSTEM Collector / source-specific adapters'",
    )
    missing = [token for token in required_app if token not in app]
    if missing:
        fail(f"app.py missing current truthful configuration/status markers: {missing}")

    settings = SETTINGS_MODULE.read_text(encoding="utf-8")
    forbidden_settings = (
        "'provider': 'local'",
        "'local_enabled': True",
        "'model': 'qwen2:7b'",
        "'local_url': 'http://127.0.0.1:8200'",
    )
    present_settings = [token for token in forbidden_settings if token in settings]
    if present_settings:
        fail(f"settings_module.py still exposes retired runtime defaults: {present_settings}")
    for token in (
        "CURRENT COMPATIBILITY API / NOT RUNTIME CONFIGURATION AUTHORITY",
        "'provider': 'owned'",
        "'fallback_allowed': False",
        "'local_url': 'http://127.0.0.1:8201'",
        "ignored_runtime_owned_fields",
    ):
        if token not in settings:
            fail(f"settings_module.py missing current runtime-boundary marker: {token}")

    deployment_readme = DEPLOYMENT_README.read_text(encoding="utf-8")
    deployment_local = DEPLOYMENT_LOCAL.read_text(encoding="utf-8")
    if "SUPPORTING COMPATIBILITY / NOT CURRENT RUNTIME AUTHORITY" not in deployment_readme:
        fail("deployment/README.md must classify compatibility wrappers")
    if "8200" in deployment_local or "start_production.ps1" not in deployment_local:
        fail("local deployment must converge through the canonical production launcher")
    for relative in REMOVED_PUBLIC_LAUNCHERS:
        if (ROOT / relative).exists():
            fail(f"removed public-tunnel launcher must not return: {relative}")
    tree = ast.parse(app)
    remote = next(node for node in tree.body
                  if isinstance(node, ast.FunctionDef) and node.name == "remote_access")
    remote_source = ast.get_source_segment(app, remote) or ""
    if "PUBLIC_REMOTE_ACCESS_UNAVAILABLE" not in remote_source or "410" not in remote_source:
        fail("old remote bookmarks must report unavailable")
    for node in ast.walk(remote):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"open", "redirect"}):
            fail("remote compatibility route cannot read or redirect to external tunnel state")

    compatibility_launchers = [
        ROOT / "check_local_ai.bat",
        ROOT / "cloudflared_guardian.ps1",
        ROOT / "monitor_cloudflare_tunnel.bat",
        ROOT / "start_cf.ps1",
        ROOT / "start_cloudflare_stable.bat",
        ROOT / "start_cloudflare_tunnel.bat",
        ROOT / "start_tunnel.bat",
        ROOT / "scripts" / "stability_fix.py",
        *sorted((ROOT / "deployment" / "deployment").glob("*.bat")),
    ]
    for path in compatibility_launchers:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if "127.0.0.1:8200" in text or "localhost:8200" in text:
            fail(f"{path.relative_to(ROOT)} still routes an executable compatibility path to legacy 8200")
    local_ai_check = (ROOT / "check_local_ai.bat").read_text(encoding="utf-8-sig", errors="replace")
    if "owned_inference_status" not in local_ai_check:
        fail("check_local_ai.bat must inspect the sole owned Gateway rather than retired local providers")

    inspector = INSTANCE_INSPECTOR.read_text(encoding="utf-8")
    for token in ("8201=canonical Product Core", "LEGACY_LISTEN(REVIEW)", "CANONICAL_LISTEN(KEEP)"):
        if token not in inspector:
            fail(f"scripts/inspect_instances.ps1 missing current port semantics: {token}")

    toolchain = json.loads(TOOLCHAIN.read_text(encoding="utf-8"))
    expected_toolchain = {
        "contract": "lumenis.flutter-toolchain/v1",
        "channel": "stable",
        "flutter_version": "3.47.5",
        "flutter_revision": "6a19cca56475dbfba1478ee68d7bd0c2ef891da1",
        "dart_version": "3.13.4",
    }
    for key, expected in expected_toolchain.items():
        if toolchain.get(key) != expected:
            fail(f"app/toolchain.json {key} drifted: {toolchain.get(key)!r}")

    workflow = APP_WORKFLOW.read_text(encoding="utf-8")
    if "app/toolchain.json" not in workflow or "verify_current_configuration.py" not in workflow:
        fail("App Gate must consume the toolchain/configuration contract")
    if "flutter pub get --enforce-lockfile" not in workflow:
        fail("App Gate must enforce the committed Flutter dependency lockfile")
    if re.search(r"--branch\s+3\.47\.\d+", workflow):
        fail("App Gate must not hardcode a second Flutter version")

    current = CURRENT.read_text(encoding="utf-8")
    for marker in (
        "CURRENT CONFIGURATION / TOOLCHAIN CONVERGENCE",
        "`.env.example` is documentation only",
        "app/toolchain.json",
        "local private C2 runtime specification",
    ):
        if marker not in current:
            fail(f"CURRENT missing configuration convergence marker: {marker}")


if __name__ == "__main__":
    validate()
    print("LUMENIS current configuration/toolchain contract: PASS")
