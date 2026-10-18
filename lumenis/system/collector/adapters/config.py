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


# Sole static discovery metadata: registration and read-only catalog projections
# consume this existing capability owner. Metadata never grants source access.
for _key, _name in (("channels", "视频号"), ("youtube", "YouTube"),
                    ("tiktok", "TikTok"), ("reddit", "Reddit"), ("linkedin", "LinkedIn")):
    PLATFORM_CAPABILITIES[_key] = {
        "name": _name, "enabled": False, "manual_collection_enabled": False,
        "priority": "planned", "search": False, "detail": False, "comments": False,
        "creator": False, "author": False, "author_posts": False, "healthcheck": False,
        "implementation_state": "PLANNED",
        "provider_state": "implementation_and_authorized_provider_required",
    }
PLATFORM_CAPABILITIES["github"] = {
    "name": "GitHub", "enabled": False, "manual_collection_enabled": False,
    "priority": "optional", "provider_state": "authorized_connector_required",
}
# Preserve existing physical schema names; no table/schema is created here.
_RAW_CATALOG_TABLES = {'xiaohongshu': ['xhs_notes', 'xhs_note_comments', 'xhs_users'],
 'douyin': ['douyin_videos', 'douyin_comments', 'douyin_users'],
 'bilibili': ['bilibili_videos', 'bilibili_comments', 'bilibili_users'],
 'channels': ['channels_videos', 'channels_comments'],
 'youtube': ['youtube_videos', 'youtube_comments', 'youtube_channels'],
 'tiktok': ['tiktok_videos', 'tiktok_comments', 'tiktok_users'],
 'instagram': ['instagram_media', 'instagram_comments', 'instagram_users'],
 'x': ['x_posts', 'x_users'],
 'reddit': ['reddit_posts', 'reddit_comments', 'reddit_subreddits'],
 'linkedin': ['linkedin_posts', 'linkedin_users'],
 'github': ['github_repositories', 'github_issues', 'github_pull_requests', 'github_releases'],
 'zhihu': ['zhihu_answers', 'zhihu_questions', 'zhihu_articles', 'zhihu_comments']}
for _key, _cap in PLATFORM_CAPABILITIES.items():
    _canonical = "xiaohongshu" if _key == "xhs" else _key
    _module = {"x": "x_platform", "google": None, "tieba": None}.get(_key, _key)
    _kind = ("public_web" if _key in {"public_http", "web_rss", "web_atom", "sitemap"}
             else "discovery" if _key == "google"
             else "developer_source" if _key == "github" else "social")
    _cap.update(canonical_id=_canonical, source_kind=_kind,
                adapter_module="lumenis.system.collector.adapters." + _module if _module else None,
                raw_tables=list(_RAW_CATALOG_TABLES.get(_canonical, [])))
    _cap.setdefault("implementation_state", "IMPLEMENTED_BOUNDARY" if _module else "PLANNED")
    _cap["collection_surface_visible"] = _kind in {"social", "public_web"}
    # Preserve the existing 14 dispatchable source identities. Google has a
    # legacy manual flag but is not bound to this SYSTEM collection entry.
    _cap["collection_entry_enabled"] = _cap["collection_surface_visible"] and (
        _key == "xhs" or bool(_cap.get("manual_collection_enabled")))
    _cap["catalog_status"] = ("ACTIVE" if _key == "xhs" else
        "PLANNED" if _cap["implementation_state"] == "PLANNED" else "PARTIAL")
del _key, _name, _cap, _canonical, _module, _kind, _RAW_CATALOG_TABLES


def resolve_platform_config_key(platform: str) -> str:
    """Resolve XHS/RedNote aliases to the existing adapter/config key.

    Canonical source identity remains ``xiaohongshu`` in platform naming and
    stored data; the registered adapter's stable key remains ``xhs`` for
    compatibility. All known aliases resolve through the existing naming owner.
    """
    key = str(platform or "").strip().lower()
    from .platform_naming import normalize_platform_name

    canonical = normalize_platform_name(key)
    return "xhs" if canonical == "xiaohongshu" else (canonical or key)


def get_platform_capabilities(platform: str) -> dict:
    key = resolve_platform_config_key(platform)
    if key not in PLATFORM_CAPABILITIES:
        raise KeyError(f"Unsupported platform: {platform}")
    from copy import deepcopy
    return deepcopy(PLATFORM_CAPABILITIES[key])
