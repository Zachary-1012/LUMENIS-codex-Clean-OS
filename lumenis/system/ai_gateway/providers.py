"""LUMENIS Provider Registry.

Retired built-in routes remain denial/history metadata only. Explicit user API
connections have separate origin-scoped protocol metadata in this same registry.
Registration never selects a connection, grants Permission or proves inference.
"""
from typing import Dict, List, Optional
from urllib.parse import urlsplit
import ipaddress
import re

# Provider 状态枚举
ACTIVE = "ACTIVE"
ACTIVE_FALLBACK = "ACTIVE_FALLBACK"  # Historical status only; not dispatch permission.
AVAILABLE = "AVAILABLE"      # 已配置但未运行时验证（本地 Provider 默认态）
BLOCKED = "BLOCKED"          # 运行时探测失败，不可调用
LEGACY = "LEGACY"
DISABLED = "DISABLED"
REMOVE_CANDIDATE = "REMOVE_CANDIDATE"
NOT_CONFIGURED = "NOT_CONFIGURED"

# Retirement applies to historical built-in routes, not to a user-owned
# connection merely because its service has the same brand name.
RETIRED_PROVIDERS = frozenset({"zhipu", "ollama", "lmstudio", "llama_cpp", "ark", "qwen", "openai", "deepseek"})
COMPATIBILITY_ONLY_PROVIDERS = frozenset()

# Canonical Provider Registry
PROVIDER_REGISTRY: Dict[str, Dict] = {
    name: {"status": DISABLED, "role": "retired_builtin_route", "env_key": None,
           "description": "退役内置路由，不可调用、探测或兜底；独立用户连接按其来源和准入核验"}
    for name in sorted(RETIRED_PROVIDERS)
}


# Reviewed official text-chat connections, not the final BYOK product scope.
# Extend these protocol defaults in the existing registry. User-supplied HTTPS
# compatibility connections use the same validation/transport without requiring
# a registry edit; never import credentials or revive built-in transports.
# Sources: https://console.groq.com/docs/openai
# https://platform.openai.com/docs/api-reference/chat/create
# https://api-docs.deepseek.com/
for _name, _bases, _destination, _token_field in (
    ("groq", ("https://api.groq.com/openai/v1",),
     "https://api.groq.com/openai/v1/chat/completions", "max_tokens"),
    ("openai", ("https://api.openai.com/v1",),
     "https://api.openai.com/v1/chat/completions", "max_completion_tokens"),
    ("deepseek", ("https://api.deepseek.com", "https://api.deepseek.com/v1"),
     "https://api.deepseek.com/chat/completions", "max_tokens"),
):
    PROVIDER_REGISTRY.setdefault(_name, {
        "status": DISABLED, "role": "explicit_connection_only", "env_key": None,
        "description": "Explicit connection metadata; never automatic dispatch",
    })["user_api"] = {
        "base_urls": _bases, "destination": _destination,
        "protocol": "openai_chat_completions", "token_field": _token_field,
    }


def _https_base(value):
    """Strict URL grammar before matching reviewed metadata; never DNS/probe."""
    if (type(value) is not str or not value or not value.isascii()
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
            or any(c in value for c in "?#%\\")):
        return None
    try:
        url = urlsplit(value)
        host = url.hostname
        if (url.scheme != "https" or not host or url.username is not None
                or url.password is not None or url.port not in (None, 443)
                or url.netloc.lower() not in {host, host + ":443"}
                or "//" in url.path or any(part in {".", ".."} for part in url.path.split("/"))):
            return None
        if (len(host) > 253 or "." not in host or host.rsplit(".", 1)[-1].isdigit() or host.endswith(
                (".localhost", ".local", ".internal", ".home", ".lan", ".invalid", ".test"))
                or any(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) is None
                       for label in host.split("."))
                or re.fullmatch(r"(?:/[A-Za-z0-9._~-]+)*/?", url.path) is None):
            return None
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return None  # Require a TLS hostname, never an IP-literal endpoint.
        return "https://" + host + url.path.rstrip("/")
    except (ValueError, TypeError):
        return None


def user_api_connection(base_url, protocol="openai_chat_completions"):
    """Resolve a user-origin connection, independent of retired built-in routes.

    Official entries supply protocol-specific defaults, not a provider ceiling.
    Other HTTPS hosts use the explicitly chosen compatibility protocol. They
    still require public-address DNS validation and IP-pinned TLS at each send;
    configuring a host is neither network validation nor permission to send.
    Unknown/native protocols stay NOT_ADAPTED in the adapter, never silently
    interpreted as compatible or dispatched through retired transports.
    """
    normalized = _https_base(base_url)
    if normalized is None:
        return None
    for name, entry in PROVIDER_REGISTRY.items():
        connection = entry.get("user_api")
        if not isinstance(connection, dict):
            continue
        bases = connection.get("base_urls")
        if not isinstance(bases, (tuple, list)) or normalized not in bases:
            continue
        destination = connection.get("destination")
        canonical = _https_base(destination)
        # Metadata may not forward credentials to a different origin, query or
        # normalized spelling. Sending always uses the exact reviewed constant.
        if (canonical != destination or canonical is None
                or urlsplit(canonical).netloc != urlsplit(normalized).netloc):
            return None
        return {"service_provider": name, "connection_origin": "user_api",
                "destination": destination, "protocol": protocol,
                "token_field": connection.get("token_field") if protocol == connection.get("protocol") else None,
                "endpoint_kind": "official_preset"}
    return {"service_provider": urlsplit(normalized).hostname,
            "connection_origin": "user_api", "protocol": protocol,
            "destination": normalized + "/chat/completions",
            "token_field": "max_tokens" if protocol == "openai_chat_completions" else None,
            "endpoint_kind": "custom"}


def provider_status(name: str) -> str:
    """获取 Provider 状态。"""
    key = _canonical_name(name)
    if key in RETIRED_PROVIDERS:
        return DISABLED
    if key in COMPATIBILITY_ONLY_PROVIDERS:
        return LEGACY
    entry = PROVIDER_REGISTRY.get(key)
    return entry["status"] if entry else DISABLED


def _canonical_name(name: str) -> str:
    key = str(name or "").lower().strip().split(":", 1)[0]
    return {"glm": "zhipu", "doubao": "ark", "dashscope": "qwen"}.get(key, key)


def is_provider_retired(name: str) -> bool:
    """Whether the historical built-in route is retired (not brand-level BYOK)."""
    return _canonical_name(name) in RETIRED_PROVIDERS


def is_provider_available(name: str) -> bool:
    """Return whether the current registry explicitly permits dispatch.

    Legacy and ACTIVE_FALLBACK are retained status labels, not call permission.
    """
    return not is_provider_retired(name) and provider_status(name) in (
        ACTIVE, AVAILABLE,
    )


def is_provider_active(name: str) -> bool:
    """Provider 是否经过运行时验证为 ACTIVE（严格判断）。"""
    return not is_provider_retired(name) and provider_status(name) == ACTIVE


def active_providers() -> List[str]:
    """返回所有 ACTIVE 状态的 Provider 名称（严格：仅运行时已验证）。"""
    return [k for k in PROVIDER_REGISTRY if is_provider_active(k)]


def available_providers() -> List[str]:
    """Return providers explicitly permitted for dispatch (ACTIVE/AVAILABLE)."""
    return [k for k in PROVIDER_REGISTRY if is_provider_available(k)]


def filter_available(names: List[str]) -> List[str]:
    """从列表中过滤出可用 Provider。"""
    return [n for n in names if is_provider_available(n)]


def provider_info(name: str) -> Optional[Dict]:
    """获取 Provider 完整信息。"""
    key = _canonical_name(name)
    entry = PROVIDER_REGISTRY.get(key)
    if entry is None:
        return None
    result = dict(entry)
    if key in RETIRED_PROVIDERS:
        result["status"] = DISABLED
    elif key in COMPATIBILITY_ONLY_PROVIDERS:
        result["status"] = LEGACY
        result["role"] = "compatibility_only"
    return result


def registry_summary() -> Dict[str, int]:
    """返回 Registry 状态统计。"""
    counts = {}
    for name in PROVIDER_REGISTRY:
        s = provider_status(name)
        counts[s] = counts.get(s, 0) + 1
    return counts


def probe_local_providers() -> Dict[str, str]:
    """Read historical local-provider denial states; never probe an endpoint."""
    return {name: DISABLED for name in ("ollama", "lmstudio", "llama_cpp")}


def set_provider_status(name: str, status: str) -> None:
    """显式设置 Provider 状态（供治理层/审计调用）。"""
    key = _canonical_name(name)
    entry = PROVIDER_REGISTRY.get(key)
    if entry:
        if key in RETIRED_PROVIDERS:
            entry["status"] = DISABLED
        elif key in COMPATIBILITY_ONLY_PROVIDERS:
            entry["status"] = LEGACY
        else:
            entry["status"] = status
