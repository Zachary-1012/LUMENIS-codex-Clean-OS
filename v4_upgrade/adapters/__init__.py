"""
采集适配器包
用法:
    from v4_upgrade.adapters import registry, register_default_adapters
    register_default_adapters()
    results = registry.search_all("广州太古汇", max_results=10)
"""
from .base import BaseAdapter, AdapterResult, CollectedNote, CircuitBreaker
from .registry import AdapterRegistry, registry, register_default_adapters

__all__ = [
    "BaseAdapter", "AdapterResult", "CollectedNote", "CircuitBreaker",
    "AdapterRegistry", "registry", "register_default_adapters",
]
