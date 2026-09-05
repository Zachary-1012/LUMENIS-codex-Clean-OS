"""LUMENIS Provider Registry（V2 P0-5）

统一管理 AI Provider 状态。Provider 逻辑收敛为 Zhipu + Local，
ARK 保留为 LEGACY（豆包兜底，用户明确要求），Qwen/OpenAI/DeepSeek 标记 DISABLED。

不删除旧 provider 代码，只通过 Registry 控制可用性。
"""
from typing import Dict, List, Optional

# Provider 状态枚举
ACTIVE = "ACTIVE"
LEGACY = "LEGACY"
DISABLED = "DISABLED"
REMOVE_CANDIDATE = "REMOVE_CANDIDATE"

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
        "status": ACTIVE,
        "role": "local_primary",
        "models": ["local-model"],
        "env_key": None,
        "description": "本地离线兜底（Ollama / LM Studio / llama.cpp）",
    },
    "ark": {
        "status": LEGACY,
        "role": "cloud_fallback",
        "models": ["doubao-seed-evolving-latest-version"],
        "env_key": "ARK_API_KEY",
        "description": "豆包 ARK 兜底（用户要求保留，不作为主力）",
    },
    "doubao": {
        "status": LEGACY,
        "role": "cloud_fallback",
        "alias_of": "ark",
        "env_key": "ARK_API_KEY",
        "description": "豆包别名，映射到 ark",
    },
    "qwen": {
        "status": DISABLED,
        "role": "deprecated",
        "env_key": "DASHSCOPE_API_KEY",
        "description": "已禁用。V2 收敛后不再作为可选 Provider。代码保留为 LEGACY 参考。",
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
    """Provider 是否可用（ACTIVE 或 LEGACY）。"""
    return provider_status(name) in (ACTIVE, LEGACY)


def active_providers() -> List[str]:
    """返回所有可用 Provider 名称。"""
    return [k for k, v in PROVIDER_REGISTRY.items() if v["status"] in (ACTIVE, LEGACY)]


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
