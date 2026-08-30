"""Platform capability configuration.

Current production release keeps only the existing XHS collector active through the
adapter boundary. Douyin is a planned secondary platform and remains disabled until a
verified, compliant backend is implemented and regression-tested. Other platforms are
event-monitoring extension points only.
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
        "planned_capabilities": [
            "search",
            "detail",
            "comments",
            "replies",
            "creator",
            "session_cache",
            "proxy_pool",
            "comment_wordcloud",
        ],
        "enable_gate": "verified_compliant_backend_plus_regression_tests",
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
