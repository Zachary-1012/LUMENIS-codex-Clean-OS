"""Platform capability configuration.

Current production release keeps the existing Hong Kong/International XHS path
separate from the CTH secondary collection surface.  Douyin, Weibo, Zhihu and
Instagram are now available for explicit, human-triggered, read-only search
collection through the canonical adapter boundary.  Their scheduled/background
collection remains disabled until an operating policy explicitly enables it.
Other platforms are event-monitoring extension points only and remain disabled.
"""

PLATFORM_CAPABILITIES = {
    "xhs": {
        "name": "小红书",
        "enabled": True,
        "priority": "primary",
        "search": True,
        "detail": True,
        "comments": True,
        "replies": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": True,
        "comment_wordcloud": True,
    },
    "douyin": {
        "name": "抖音",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "product_owner": "CTH",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": True,
        "enable_gate": "cookie_plus_browser_engine_verified",
    },
    "kuaishou": {"name": "快手", "enabled": False, "priority": "event"},
    "bilibili": {
        "name": "B站",
        "enabled": False,
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "cookie_plus_engine_verified",
    },
    "weibo": {
        "name": "微博",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "product_owner": "CTH",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "cookie_plus_engine_verified",
    },
    "tieba": {"name": "贴吧", "enabled": False, "priority": "event"},
    "zhihu": {
        "name": "知乎",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "product_owner": "CTH",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": False,
        "proxy_pool": False,
        "enable_gate": "engine_verified_no_cookie_required",
    },
    "instagram": {
        "name": "Instagram",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "product_owner": "CTH",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": True,
        "enable_gate": "proxy_plus_cookie_configured",
    },
    "facebook": {
        "name": "Facebook",
        "enabled": False,
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": True,
        "enable_gate": "proxy_plus_cookie_configured",
    },
    "x": {
        "name": "X",
        "enabled": False,
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "cookie_plus_browser_engine_verified",
    },
}


def get_platform_capabilities(platform: str) -> dict:
    key = platform.strip().lower()
    if key not in PLATFORM_CAPABILITIES:
        raise KeyError(f"Unsupported platform: {platform}")
    return dict(PLATFORM_CAPABILITIES[key])
