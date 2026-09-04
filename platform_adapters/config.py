"""Platform capability configuration.

Current production release keeps only the existing XHS collector active through the
adapter boundary. Secondary platforms (douyin/instagram/bilibili/weibo/zhihu) have
v4 engines and main-chain thin wrappers, but remain disabled by default pending
cookie/proxy verification and E2E validation. Other platforms are event-monitoring
extension points only.
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
        "priority": "secondary",
        "search": True,
        "detail": False,
        "comments": False,
        "creator": False,
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
        "detail": False,
        "comments": False,
        "creator": False,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "cookie_plus_engine_verified",
    },
    "weibo": {
        "name": "微博",
        "enabled": False,
        "priority": "secondary",
        "search": True,
        "detail": False,
        "comments": False,
        "creator": False,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "cookie_plus_engine_verified",
    },
    "tieba": {"name": "贴吧", "enabled": False, "priority": "event"},
    "zhihu": {
        "name": "知乎",
        "enabled": False,
        "priority": "secondary",
        "search": True,
        "detail": False,
        "comments": False,
        "creator": False,
        "session_cache": False,
        "proxy_pool": False,
        "enable_gate": "engine_verified_no_cookie_required",
    },
    "instagram": {
        "name": "Instagram",
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
}


def get_platform_capabilities(platform: str) -> dict:
    key = platform.strip().lower()
    if key not in PLATFORM_CAPABILITIES:
        raise KeyError(f"Unsupported platform: {platform}")
    return dict(PLATFORM_CAPABILITIES[key])
