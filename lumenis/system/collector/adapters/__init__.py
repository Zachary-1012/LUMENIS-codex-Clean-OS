"""Platform adapter layer.

This layer is intentionally independent from the existing business engines.
Platform-specific collection code must only return normalized public/content data;
subject filtering, risk, event aggregation and reporting remain in the core system.
"""

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import get_adapter, list_adapters, register_adapter

# Import built-in adapters so registration happens when the package is imported.
# Their implementations are deliberately thin and do not replace the existing core.
from . import douyin as _douyin  # noqa: F401,E402
from . import xhs as _xhs  # noqa: F401,E402
from . import xhs_app_topic as _xhs_app_topic  # noqa: F401,E402  V3.0 P1: XHS App Topic Adapter
from . import instagram as _instagram  # noqa: F401,E402
from . import bilibili as _bilibili  # noqa: F401,E402
from . import weibo as _weibo  # noqa: F401,E402
from . import zhihu as _zhihu  # noqa: F401,E402
from . import kuaishou as _kuaishou  # noqa: F401,E402
from . import web_rss as _web_rss  # noqa: F401,E402
from . import public_http as _public_http  # noqa: F401,E402
from . import web_atom as _web_atom  # noqa: F401,E402
from . import sitemap as _sitemap  # noqa: F401,E402
from . import facebook as _facebook  # noqa: F401,E402
from . import x_platform as _x_platform  # noqa: F401,E402
from . import github as _github  # noqa: F401,E402

__all__ = [
    "BasePlatformAdapter",
    "AccessClass",
    "CollectionResult",
    "CollectionStatus",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
