"""LUMENIS Provider Registry.

Retired providers keep their adapters for compatibility, but status mutation,
discovery and stale runtime state cannot make them callable again.
"""
from typing import Dict, List, Optional
import os
import json
import urllib.request
import urllib.error

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


def _probe_endpoint(base_url: str, path: str, timeout: float = 3.0) -> bool:
    """探测本地 HTTP 端点是否可访问且返回非空模型列表。"""
    try:
        url = base_url.rstrip("/") + path
        req = urllib.request.Request(url, headers={"User-Agent": "ZBC-ProviderProbe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode("utf-8", "replace"))
            # Ollama: {"models": [...]}; LM Studio / llama.cpp: {"data": [...]}
            models = data.get("models") or data.get("data") or []
            return len(models) > 0
    except Exception:
        return False


def probe_local_providers() -> Dict[str, str]:
    """运行时探测所有本地 Provider，更新 Registry 状态。

    返回 {provider_name: new_status} 映射。
    - 探测成功（有可用模型）→ ACTIVE
    - 探测失败 → BLOCKED
    仅影响 ollama / lmstudio / llama_cpp，不触碰云端 Provider。
    """
    results: Dict[str, str] = {}
    local_names = ["ollama", "lmstudio", "llama_cpp"]
    for name in local_names:
        if is_provider_retired(name):
            results[name] = DISABLED
            continue
        entry = PROVIDER_REGISTRY.get(name)
        if not entry:
            continue
        base_url = os.environ.get(entry.get("probe_url_env", ""), "") or entry.get("probe_url_default", "")
        path = entry.get("probe_path", "/api/tags")
        ok = _probe_endpoint(base_url, path)
        new_status = ACTIVE if ok else BLOCKED
        entry["status"] = new_status
        entry["last_probe"] = _now_iso()
        entry["probe_ok"] = ok
        results[name] = new_status
    return results


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


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
