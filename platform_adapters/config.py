"""Platform capability configuration.

Only Xiaohongshu and Douyin are enabled for deep implementation in the current
release. Other platforms remain extension points for event monitoring.
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
        "enabled": True,
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "replies": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": True,
        "comment_wordcloud": True,
    },
    "kuaishou": {"name": "快手", "enabled": False, "priority": "event"},
    "bilibili": {"name": "B站", "enabled": False, "priority": "event"},
    "weibo": {"name": "微博", "enabled": False, "priority": "event"},
    "tieba": {"name": "贴吧", "enabled": False, "priority": "event"},
    "zhihu": {"name": "知乎", "enabled": False, "priority": "event"},
}


def get_platform_capabilities(platform: str) -> dict:
    key = platform.strip().lower()
    if key not in PLATFORM_CAPABILITIES:
        raise KeyError(f"Unsupported platform: {platform}")
    return dict(PLATFORM_CAPABILITIES[key])
