"""LUMENIS Provider Registry.

Retired provider identities remain denial/history metadata only. No probe or
execution adapter is retained here; current requests use the one Gateway.
"""
from typing import Dict, List, Optional

# Provider 状态枚举
ACTIVE = "ACTIVE"
ACTIVE_FALLBACK = "ACTIVE_FALLBACK"  # Historical status only; not dispatch permission.
AVAILABLE = "AVAILABLE"      # 已配置但未运行时验证（本地 Provider 默认态）
BLOCKED = "BLOCKED"          # 运行时探测失败，不可调用
LEGACY = "LEGACY"
DISABLED = "DISABLED"
REMOVE_CANDIDATE = "REMOVE_CANDIDATE"
NOT_CONFIGURED = "NOT_CONFIGURED"

# PO: only owned 序境 models; every third-party provider name is denied.
RETIRED_PROVIDERS = frozenset({"zhipu", "ollama", "lmstudio", "llama_cpp", "ark", "qwen", "openai", "deepseek"})
COMPATIBILITY_ONLY_PROVIDERS = frozenset()

# Canonical Provider Registry
PROVIDER_REGISTRY: Dict[str, Dict] = {
    name: {"status": DISABLED, "role": "denied_third_party", "env_key": None,
           "description": "第三方模型，PO 规定只用自有序境模型，禁止调用与兜底"}
    for name in sorted(RETIRED_PROVIDERS)
}


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
    """Whether Product Owner policy permanently disables this provider."""
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
