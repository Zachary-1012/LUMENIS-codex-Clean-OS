from __future__ import annotations

from typing import Dict, Type
from copy import deepcopy

from .base import BasePlatformAdapter
from .config import PLATFORM_CAPABILITIES, resolve_platform_config_key

_ADAPTERS: Dict[str, Type[BasePlatformAdapter]] = {}


def register_adapter(platform: str, adapter_cls: Type[BasePlatformAdapter]) -> None:
    key = resolve_platform_config_key(platform)
    if not issubclass(adapter_cls, BasePlatformAdapter):
        raise TypeError("adapter_cls must inherit BasePlatformAdapter")
    _ADAPTERS[key] = adapter_cls


def list_adapters() -> list[str]:
    return sorted(_ADAPTERS)


def get_adapter(platform: str, **kwargs):
    key = resolve_platform_config_key(platform)
    adapter_cls = _ADAPTERS.get(key)
    if adapter_cls is None:
        raise KeyError(
            f"No adapter registered for {platform!r}. "
            "Register the platform implementation before enabling it."
        )
    return adapter_cls(**kwargs)


def capability_matrix() -> dict:
    return deepcopy(PLATFORM_CAPABILITIES)
