"""LUMENIS Provider Registry（V2 P0-5 + Track3 审计修复）

统一管理 AI Provider 状态。Provider 逻辑收敛为 Zhipu + Local，
ARK 保留为 LEGACY（豆包兜底，用户明确要求），Qwen/OpenAI/DeepSeek 标记 DISABLED。

Track3 修复（2026-09-06）：
- 新增 AVAILABLE / BLOCKED 状态：本地 Provider（ollama/lmstudio/llama_cpp）
  默认 AVAILABLE，仅当运行时探测到实际可调用才升级为 ACTIVE；
  探测失败标记 BLOCKED。禁止 ACTIVE 但实际无法调用。
- 新增 probe_local_providers() 运行时探测函数。
- zhipu 保持 ACTIVE（.env 中 ZHIPU_API_KEY 已验证连通）。

不删除旧 provider 代码，只通过 Registry 控制可用性。
"""
from typing import Dict, List, Optional
import os
import json
import urllib.request
import urllib.error

# Provider 状态枚举
ACTIVE = "ACTIVE"
ACTIVE_FALLBACK = "ACTIVE_FALLBACK"  # V1.0: 可用兜底Provider
AVAILABLE = "AVAILABLE"      # 已配置但未运行时验证（本地 Provider 默认态）
BLOCKED = "BLOCKED"          # 运行时探测失败，不可调用
LEGACY = "LEGACY"
DISABLED = "DISABLED"
REMOVE_CANDIDATE = "REMOVE_CANDIDATE"
NOT_CONFIGURED = "NOT_CONFIGURED"
ACTIVE_FALLBACK = "ACTIVE_FALLBACK"

# Canonical Provider Registry
PROVIDER_REGISTRY: Dict[str, Dict] = {
    "zhipu": {
        "status": ACTIVE,
        "role": "cloud_primary",
        "models": ["glm-4.5-air", "glm-5.3", "glm-4.6v", "web-search-pro"],
        "env_key": "ZHIPU_API_KEY",
        "description": "智谱云端主力 Provider",
    },
    "ollama": {
        "status": AVAILABLE,
        "role": "local_primary",
        "models": ["local-model"],
        "env_key": None,
        "probe_url_env": "OLLAMA_BASE_URL",
        "probe_url_default": "http://127.0.0.1:11434",
        "probe_path": "/api/tags",
        "description": "本地离线兜底（Ollama / LM Studio / llama.cpp）",
    },
    "lmstudio": {
        "status": AVAILABLE,
        "role": "local_secondary",
        "models": ["local-model"],
        "env_key": None,
        "probe_url_env": "LMSTUDIO_BASE_URL",
        "probe_url_default": "http://127.0.0.1:1234",
        "probe_path": "/v1/models",
        "description": "LM Studio 本地推理",
    },
    "llama_cpp": {
        "status": AVAILABLE,
        "role": "local_secondary",
        "models": ["local-model"],
        "env_key": None,
        "probe_url_env": "LLAMA_CPP_BASE_URL",
        "probe_url_default": "http://127.0.0.1:8080",
        "probe_path": "/v1/models",
        "description": "llama.cpp server 本地推理",
    },
    "ark": {
        "status": ACTIVE_FALLBACK,
        "role": "cloud_fallback",
        "models": ["doubao-seed-evolving-latest-version"],
        "env_key": "ARK_API_KEY",
        "description": "豆包 ARK 兜底（用户要求保留，不作为主力）",
    },
    "doubao": {
        "status": ACTIVE_FALLBACK,
        "role": "cloud_fallback",
        "alias_of": "ark",
        "env_key": "ARK_API_KEY",
        "description": "豆包别名，映射到 ark",
    },
    "qwen": {
        "status": NOT_CONFIGURED,
        "role": "cloud_standby",
        "env_key": "DASHSCOPE_API_KEY",
        "description": "qwen L3 standby V1.0 (no key configured)",
    },
    "openai": {
        "status": DISABLED,
        "role": "deprecated",
        "env_key": "OPENAI_API_KEY",
        "description": "已禁用。V2 收敛后不再作为可选 Provider。",
    },
    "deepseek": {
        "status": DISABLED,
        "role": "deprecated",
        "env_key": "DEEPSEEK_API_KEY",
        "description": "已禁用。V2 收敛后不再作为可选 Provider。",
    },
}


def provider_status(name: str) -> str:
    """获取 Provider 状态。"""
    entry = PROVIDER_REGISTRY.get(name.lower())
    return entry["status"] if entry else DISABLED


def is_provider_available(name: str) -> bool:
    """Provider 是否可用（ACTIVE / AVAILABLE / LEGACY 均视为可尝试调用）。

    AVAILABLE 表示已配置但未验证；调用方应先 probe 再使用。
    BLOCKED / DISABLED 不可用。
    """
    return provider_status(name) in (ACTIVE, ACTIVE_FALLBACK, AVAILABLE, LEGACY)


def is_provider_active(name: str) -> bool:
    """Provider 是否经过运行时验证为 ACTIVE（严格判断）。"""
    return provider_status(name) == ACTIVE


def active_providers() -> List[str]:
    """返回所有 ACTIVE 状态的 Provider 名称（严格：仅运行时已验证）。"""
    return [k for k, v in PROVIDER_REGISTRY.items() if v["status"] == ACTIVE]


def available_providers() -> List[str]:
    """返回所有可尝试的 Provider（ACTIVE + AVAILABLE + LEGACY）。"""
    return [k for k, v in PROVIDER_REGISTRY.items() if v["status"] in (ACTIVE, ACTIVE_FALLBACK, AVAILABLE, LEGACY)]


def filter_available(names: List[str]) -> List[str]:
    """从列表中过滤出可用 Provider。"""
    return [n for n in names if is_provider_available(n)]


def provider_info(name: str) -> Optional[Dict]:
    """获取 Provider 完整信息。"""
    return PROVIDER_REGISTRY.get(name.lower())


def registry_summary() -> Dict[str, int]:
    """返回 Registry 状态统计。"""
    counts = {}
    for v in PROVIDER_REGISTRY.values():
        s = v["status"]
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
    entry = PROVIDER_REGISTRY.get(name.lower())
    if entry:
        entry["status"] = status
