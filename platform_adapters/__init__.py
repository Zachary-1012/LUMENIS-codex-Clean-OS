"""Platform adapter layer.

This layer is intentionally independent from the existing business engines.
Platform-specific collection code must only return normalized public/content data;
subject filtering, risk, event aggregation and reporting remain in the core system.
"""

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "BasePlatformAdapter",
    "CollectionResult",
    "CollectionStatus",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
