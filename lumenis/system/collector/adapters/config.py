"""Platform capability configuration.

The existing Hong Kong/International XHS path remains on its current primary
collector. CTH secondary collection is explicit, human-triggered and read-only.
Scheduled/background collection remains disabled. A registered adapter does not
imply that credentials, platform permissions, or a live provider are configured.
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
        "enable_gate": "managed_remote_worker_plus_authorized_session",
        "readonly_worker": {"account": "DOUYIN_READONLY", "port": 9225,
                            "profile": "douyin-readonly", "env_prefix": "DOUYIN"},
    },
    "kuaishou": {
        "name": "快手", "enabled": False, "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only", "product_owner": "CTH",
        "priority": "secondary", "search": False, "detail": False,
        "comments": False, "creator": False, "author": False,
        "author_posts": False, "healthcheck": True,
        "provider_state": "not_configured_authorized_session_required",
    },
    "bilibili": {
        "name": "B站",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "product_owner": "CTH",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "author": True,
        "author_posts": False,
        "healthcheck": True,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "server_authorized_session_and_manual_live_verification",
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
        "author": True,
        "author_posts": False,
        "healthcheck": True,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "server_authorized_session_and_manual_live_verification",
    },
    "web_rss": {
        "name": "Web RSS", "enabled": False, "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only", "product_owner": "CTH",
        "priority": "secondary", "search": True, "detail": False,
        "comments": False, "creator": False, "author": False,
        "author_posts": False, "healthcheck": True,
        "provider_state": "public_keyless_rss",
    },
    "public_http": {
        "name": "Public HTTP", "enabled": False, "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only", "product_owner": "CTH",
        "priority": "secondary", "search": True, "detail": True,
        "comments": False, "creator": False, "author": False, "author_posts": False,
        "healthcheck": True, "provider_state": "public_keyless_http",
    },
    "web_atom": {
        "name": "Web Atom", "enabled": False, "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only", "product_owner": "CTH",
        "priority": "secondary", "search": True, "detail": False,
        "comments": False, "creator": False, "author": False, "author_posts": False,
        "healthcheck": True, "provider_state": "public_keyless_atom",
    },
    "sitemap": {
        "name": "Sitemap", "enabled": False, "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only", "product_owner": "CTH",
        "priority": "secondary", "search": True, "detail": False,
        "comments": False, "creator": False, "author": False, "author_posts": False,
        "healthcheck": True, "provider_state": "public_keyless_sitemap",
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
    "google": {
        "name": "Google 搜索",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "product_owner": "CTH",
        "priority": "secondary",
        "search": True,
        "detail": False,
        "comments": False,
        "creator": False,
        "session_cache": False,
        "proxy_pool": False,
        "enable_gate": "registered_background_worker",
        "readonly_worker": {
            "account": "GOOGLE_READONLY",
            "port": 9230,
            "profile": "google-readonly",
            "env_prefix": "GOOGLE_READONLY",
        },
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
        "enable_gate": "registered_readonly_worker_and_actual_session",
        "readonly_worker": {"account": "INSTAGRAM_READONLY", "port": 9227,
                            "profile": "instagram-readonly", "env_prefix": "INSTAGRAM_READONLY"},
    },
    "wechat": {
        "name": "微信公众号", "enabled": False, "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only", "product_owner": "SYSTEM",
        "priority": "primary", "search": True, "detail": True,
        "comments": False, "creator": False, "session_cache": False,
        "proxy_pool": False, "enable_gate": "public_original_article_and_actual_permission",
    },
    "facebook": {
        "name": "Facebook",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": True,
        "enable_gate": "registered_readonly_worker_and_actual_session",
        "readonly_worker": {"account": "FACEBOOK_READONLY", "port": 9228,
                            "profile": "facebook-readonly", "env_prefix": "FACEBOOK_READONLY"},
    },
    "x": {
        "name": "X",
        "enabled": False,
        "manual_collection_enabled": True,
        "collection_mode": "human_triggered_read_only",
        "priority": "secondary",
        "search": True,
        "detail": True,
        "comments": True,
        "creator": True,
        "session_cache": True,
        "proxy_pool": False,
        "enable_gate": "cookie_plus_browser_engine_verified",
        "readonly_worker": {"account": "X_READONLY", "port": 9226,
                            "profile": "x-readonly", "env_prefix": "X_READONLY"},
    },
}


def resolve_platform_config_key(platform: str) -> str:
    """Resolve XHS/RedNote aliases to the existing adapter/config key.

    Canonical source identity remains ``xiaohongshu`` in platform naming and
    stored data; the registered adapter's stable key remains ``xhs`` for
    compatibility. Other platform/provider aliases retain their exact keys.
    """
    key = str(platform or "").strip().lower()
    from .platform_naming import normalize_platform_name

    return "xhs" if normalize_platform_name(key) == "xiaohongshu" else key


def get_platform_capabilities(platform: str) -> dict:
    key = resolve_platform_config_key(platform)
    if key not in PLATFORM_CAPABILITIES:
        raise KeyError(f"Unsupported platform: {platform}")
    return dict(PLATFORM_CAPABILITIES[key])
