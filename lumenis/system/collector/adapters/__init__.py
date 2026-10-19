"""Platform adapter layer.

This layer is intentionally independent from the existing business engines.
Platform-specific collection code must only return normalized public/content data;
subject filtering, risk, event aggregation and reporting remain in the core system.
"""

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import get_adapter, list_adapters, register_adapter

# Registration uses the existing capability owner. Module import performs no
# collection, provider construction or authorization and enables no platform.
from importlib import import_module as _import_module
from .config import PLATFORM_CAPABILITIES as _capabilities
for _cap in _capabilities.values():
    if _cap.get("adapter_module"):
        _import_module(_cap["adapter_module"])
# Retain the existing XHS provider compatibility entry, not another platform.
from . import xhs_app_topic as _xhs_app_topic
del _cap

__all__ = [
    "BasePlatformAdapter",
    "AccessClass",
    "CollectionResult",
    "CollectionStatus",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
