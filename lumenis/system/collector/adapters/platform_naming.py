# -*- coding: utf-8 -*-
"""LUMENIS SYSTEM Collector 平台命名与字段规范（Platform Naming Contract）。

依据 2026-09 全网/GitHub 最新平台字段研究（MediaCrawler field 体系、TikHub 术语表、
各平台开放平台文档与主流开源采集器），结合 ZBC Raw→Canonical 分层原则制定：

1. 采集层（Raw）**保留平台原生字段名**，不强行改名，确保与平台接口/页面字段一一对应、可追溯；
2. Canonical 层用统一内部字段（content_id/author_id/published_at/...）做跨平台对齐；
3. 本模块只提供「标准平台 ID + 别名归一化 + 原生↔统一字段映射 + ID 精度规则」，
   不做任何业务判断（主体过滤/风险/统计仍在核心模块）；
4. 历史数据只增不删：不物理改历史 source_platform，归一化在查询/Canonical 层完成。

所有映射均为显式字典，缺失即 None / unknown，禁止用 0 或 "未知" 静默填充。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ============================================================
# 1. 标准平台 ID 与别名归一化
# ============================================================
# canonical id 采用数据多数派 + 语义清晰原则；历史别名全部可归一化到 canonical。
PLATFORM_ALIASES: Dict[str, str] = {
    # 小红书（大陆）/ RedNote（港版同源）
    "xiaohongshu": "xiaohongshu", "xhs": "xiaohongshu", "xiaohongshu-cdp": "xiaohongshu",
    "xhs-cdp": "xiaohongshu", "rednote": "xiaohongshu", "xhs_app": "xiaohongshu",
    "小红书": "xiaohongshu",
    # 抖音（aweme 为其内部代号）
    "douyin": "douyin", "aweme": "douyin", "dy": "douyin", "抖音": "douyin",
    # 快手
    "kuaishou": "kuaishou", "ks": "kuaishou", "快手": "kuaishou",
    # 公开 RSS 聚合源（不是社交平台账号）
    "web_rss": "web_rss", "rss": "web_rss", "google_news_rss": "web_rss",
    "public_http": "public_http", "http": "public_http", "web_http": "public_http",
    "web_atom": "web_atom", "atom": "web_atom",
    "sitemap": "sitemap", "xml_sitemap": "sitemap",
    # 微博
    "weibo": "weibo", "wb": "weibo", "微博": "weibo",
    # B 站
    "bilibili": "bilibili", "bili": "bilibili", "b站": "bilibili", "哔哩哔哩": "bilibili",
    # 知乎
    "zhihu": "zhihu", "知乎": "zhihu",
    # 贴吧
    "tieba": "tieba", "贴吧": "tieba", "baidu_tieba": "tieba",
    # Instagram
    "instagram": "instagram", "ins": "instagram", "ig": "instagram",
    # Facebook
    "facebook": "facebook", "fb": "facebook",
    "wechat": "wechat", "weixin": "wechat", "微信公众号": "wechat", "sogou_wechat": "wechat",
    # X / Twitter
    "x": "x", "twitter": "x", "tweet": "x",
    # 视频号（微信视频号，无公开API，部分字段unavailable）
    "channels": "channels", "wechat_channels": "channels", "shipinhao": "channels",
    "weixin_channels": "channels", "视频号": "channels",
    # YouTube
    "youtube": "youtube", "yt": "youtube", "youtube_v3": "youtube",
    # TikTok
    "tiktok": "tiktok", "tt": "tiktok", "douyin_intl": "tiktok",
    # Reddit
    "reddit": "reddit", "rd": "reddit",
    # LinkedIn
    "linkedin": "linkedin", "ln": "linkedin",
    # GitHub
    "github": "github", "gh": "github",
}

# canonical → 标准展示名（中/英/韩三语由 i18n 层处理，这里给中文名）
PLATFORM_DISPLAY_NAME: Dict[str, str] = {
    "xiaohongshu": "小红书", "douyin": "抖音", "kuaishou": "快手", "weibo": "微博",
    "web_rss": "Web RSS",
    "public_http": "Public HTTP", "web_atom": "Web Atom", "sitemap": "Sitemap",
    "bilibili": "B站", "zhihu": "知乎", "tieba": "贴吧",
    "instagram": "Instagram", "facebook": "Facebook", "x": "X",
    "wechat": "微信公众号",
    "channels": "视频号", "youtube": "YouTube", "tiktok": "TikTok",
    "reddit": "Reddit", "linkedin": "LinkedIn", "github": "GitHub",
}

# 平台区域（小红书区分大陆/港版 RedNote，同源不同通道）
PLATFORM_REGION: Dict[str, Dict[str, str]] = {
    "xiaohongshu": {"cn": "xiaohongshu (大陆)", "intl": "RedNote (港版)"},
}


def normalize_platform(raw: Optional[str]) -> Optional[str]:
    """把任意历史/别名平台标识归一化到 canonical id；无法识别返回 None（显式未知，不编造）。"""
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if not key:
        return None
    return PLATFORM_ALIASES.get(key)  # 未登记别名返回 None，由调用方标记 unknown


def platform_display_name(canonical: Optional[str]) -> str:
    if not canonical:
        return "unknown"
    return PLATFORM_DISPLAY_NAME.get(canonical, canonical)


# ============================================================
# 2. 平台原生 ID / 字段命名（采集层保留这些原名）
# ============================================================
@dataclass(frozen=True)
class PlatformFieldSpec:
    content_id: str                 # 平台原生内容主键
    author_id: str                  # 平台原生作者主键
    id_is_bigint: bool = False      # 是否 19 位大整数（必须字符串保精度，禁止 float/int 丢精度）
    signature_token: Optional[str] = None   # 访问详情所需短期签名令牌（如小红书 xsec_token）
    published_at: str = "published_at"      # 平台原生发布时间字段
    # 平台原生互动字段
    like_field: str = "like_count"
    comment_field: str = "comment_count"
    collect_field: Optional[str] = "collect_count"
    share_field: str = "share_count"
    # 内容类型字段与枚举
    type_field: str = "type"
    # 内容详情页 URL 模板（{content_id} / {author_id} / {token} 占位符）
    url_template: str = ""
    notes: str = ""


# 依据各平台官方/主流开源采集器真实字段（2026-09 核对）
PLATFORM_NATIVE_FIELDS: Dict[str, PlatformFieldSpec] = {
    "xiaohongshu": PlatformFieldSpec(
        content_id="note_id", author_id="user_id", signature_token="xsec_token",
        published_at="time", like_field="liked_count", comment_field="comment_count",
        collect_field="collected_count", share_field="share_count",
        type_field="type", url_template="https://www.xiaohongshu.com/explore/{content_id}?xsec_token={token}",
        notes="type=normal/video；详情必须 note_id+xsec_token；xsec_token 为短期令牌"),
    "douyin": PlatformFieldSpec(
        content_id="aweme_id", author_id="sec_uid", id_is_bigint=True,
        published_at="create_time", like_field="digg_count", comment_field="comment_count",
        collect_field="collect_count", share_field="share_count",
        type_field="aweme_type", url_template="https://www.douyin.com/video/{content_id}",
        notes="aweme_id 19 位 BigInt 必须字符串保精度；sec_uid 为加密用户ID，另有数字 uid"),
    "kuaishou": PlatformFieldSpec(
        content_id="photo_id", author_id="user_id", id_is_bigint=True,
        published_at="timestamp", like_field="like_count", comment_field="comment_count",
        collect_field=None, share_field="share_count",
        url_template="https://www.kuaishou.com/short-video/{content_id}"),
    "web_rss": PlatformFieldSpec(
        content_id="content_id", author_id="source_id",
        published_at="published_at", like_field="like_count", comment_field="comment_count",
        collect_field=None, share_field="share_count", url_template="",
        notes="公共 RSS 来源；仅保留文章标题、来源、URL 与发布时间，互动指标不可用"),
    "public_http": PlatformFieldSpec(
        content_id="content_id", author_id="author_id", published_at="published_at",
        like_field="like_count", comment_field="comment_count", collect_field=None,
        share_field="share_count", url_template="",
        notes="公共 HTML 页面；只保留公开标题、摘要、URL、发布时间与采集时间"),
    "web_atom": PlatformFieldSpec(
        content_id="content_id", author_id="author_id", published_at="published_at",
        like_field="like_count", comment_field="comment_count", collect_field=None,
        share_field="share_count", url_template="",
        notes="公共 Atom 订阅；条目 identity/link 是来源主键，互动指标不可用"),
    "sitemap": PlatformFieldSpec(
        content_id="content_id", author_id="author_id", published_at="published_at",
        like_field="like_count", comment_field="comment_count", collect_field=None,
        share_field="share_count", url_template="",
        notes="公共 Sitemap URL discovery；lastmod 仅表示页面最后修改，不作为发布时间"),
    "weibo": PlatformFieldSpec(
        content_id="mid", author_id="user_id", id_is_bigint=True,
        published_at="created_at", like_field="attitudes_count", comment_field="comments_count",
        collect_field=None, share_field="reposts_count",
        url_template="https://m.weibo.cn/detail/{content_id}",
        notes="mid/idstr 为微博内容 ID；作者 ID 使用 user_id；转发=reposts_count"),
    "bilibili": PlatformFieldSpec(
        content_id="bvid", author_id="mid",
        published_at="pubdate", like_field="like", comment_field="reply",
        collect_field="favorite", share_field="share",
        url_template="https://www.bilibili.com/video/{content_id}",
        notes="bvid(Base58)/aid(数字)一一对应；UP主=mid；硬币 coin、弹幕 danmaku 为 B 站特有"),
    "zhihu": PlatformFieldSpec(
        content_id="answer_id", author_id="url_token", id_is_bigint=True,
        published_at="created_time", like_field="voteup_count", comment_field="comment_count",
        collect_field=None, share_field="share_count",
        url_template="https://www.zhihu.com/answer/{content_id}",
        notes="回答 answer_id 归属问题 question_id；赞同=voteup_count"),
    "instagram": PlatformFieldSpec(
        content_id="media_id", author_id="username", id_is_bigint=True,
        published_at="taken_at", like_field="like_count", comment_field="comment_count",
        collect_field=None, share_field="share_count",
        url_template="https://www.instagram.com/p/{content_id}/",
        notes="另有 shortcode 短链；media_id 为 BigInt"),
    "facebook": PlatformFieldSpec(
        content_id="post_id", author_id="user_id", id_is_bigint=True,
        published_at="created_time", like_field="reactions", comment_field="comments",
        collect_field=None, share_field="shares",
        url_template="https://www.facebook.com/{author_id}/posts/{content_id}"),
    "x": PlatformFieldSpec(
        content_id="tweet_id", author_id="screen_name", id_is_bigint=True,
        published_at="created_at", like_field="favorite_count", comment_field="reply_count",
        collect_field=None, share_field="retweet_count",
        url_template="https://x.com/{author_id}/status/{content_id}",
        notes="转推=retweet_count，引用=quote_count，回复=reply_count"),
    "tieba": PlatformFieldSpec(
        content_id="tid", author_id="user_id",
        published_at="create_time", like_field="agree_count", comment_field="reply_num",
        collect_field=None, share_field="share_count",
        url_template="https://tieba.baidu.com/p/{content_id}"),
    # ---- V1.0 新增6平台 ----
    "wechat": PlatformFieldSpec(
        content_id="article_id", author_id="author_id", id_is_bigint=False,
        published_at="published_at", like_field="like_num", comment_field="comment_count",
        collect_field=None, share_field="share_count", type_field="content_type",
        url_template=None, notes="公众号原文；索引时间不充当发表时间，缺失指标保持NULL。",
    ),
    "channels": PlatformFieldSpec(
        content_id="object_id", author_id="author_id",
        published_at="create_time", like_field="like_count", comment_field="comment_count",
        collect_field="collect_count", share_field="share_count",
        type_field="media_type",
        url_template="",
        notes="视频号无公开API，comment/share/collect/view等字段可能unavailable；object_id为平台原生对象ID"),
    "youtube": PlatformFieldSpec(
        content_id="video_id", author_id="channel_id",
        published_at="published_at", like_field="like_count", comment_field="comment_count",
        collect_field="favorite_count", share_field="share_count",
        type_field="media_type",
        url_template="https://www.youtube.com/watch?v={content_id}",
        notes="YouTube Data API v3；duration为ISO 8601格式(PTxxMxxS)；view_count为观看数"),
    "tiktok": PlatformFieldSpec(
        content_id="video_id", author_id="author_id", id_is_bigint=True,
        published_at="create_time", like_field="digg_count", comment_field="comment_count",
        collect_field="collect_count", share_field="share_count",
        type_field="media_type",
        url_template="https://www.tiktok.com/@{author_username}/video/{content_id}",
        notes="TikTok；digg_count=点赞；author_username为@用户名；video_id为BigInt字符串保精度"),
    "reddit": PlatformFieldSpec(
        content_id="post_id", author_id="author_fullname",
        published_at="created_utc", like_field="score", comment_field="num_comments",
        collect_field=None, share_field="num_crossposts",
        type_field="post_hint",
        url_template="https://www.reddit.com{permalink}",
        notes="Reddit；score=upvotes-downvotes；created_utc为Unix时间戳(float)；upvote_ratio为点赞比例"),
    "linkedin": PlatformFieldSpec(
        content_id="post_id", author_id="author_id",
        published_at="created_at", like_field="like_count", comment_field="comment_count",
        collect_field=None, share_field="share_count",
        type_field="share_type",
        url_template="",
        notes="LinkedIn；post_id为URN格式(urn:li:activity:xxx)；impression_count为展示数；需官方API权限"),
    "github": PlatformFieldSpec(
        content_id="repo_id", author_id="owner_id",
        published_at="created_at", like_field="stargazers_count", comment_field="open_issues_count",
        collect_field=None, share_field="forks_count",
        type_field="object_type",
        url_template="https://github.com/{full_name}",
        notes="GitHub REST API v3；按原生对象模型分repositories/issues/pull_requests/releases四表；repo_id为INTEGER"),
}


# ============================================================
# 3. Canonical 统一字段 ← 平台原生字段
# ============================================================
# 统一内部字段（跨平台分析/Canonical 层使用）
CANONICAL_FIELDS = (
    "content_id", "author_id", "platform", "published_at", "captured_at",
    "like_count", "comment_count", "collect_count", "share_count",
    "content_type", "url", "title", "raw",
)

# canonical 字段 → 各平台原生字段名（用于从 raw 记录抽取统一字段）
def _inverse_like(spec: PlatformFieldSpec) -> Dict[str, str]:
    m = {
        "content_id": spec.content_id,
        "author_id": spec.author_id,
        "published_at": spec.published_at,
        "like_count": spec.like_field,
        "comment_count": spec.comment_field,
        "share_count": spec.share_field,
        "content_type": spec.type_field,
    }
    if spec.collect_field:
        m["collect_count"] = spec.collect_field
    return m


CANONICAL_FROM_NATIVE: Dict[str, Dict[str, str]] = {
    p: _inverse_like(spec) for p, spec in PLATFORM_NATIVE_FIELDS.items()
}


def _exact_nonempty_text(value: Any) -> Optional[str]:
    """Return source text unchanged when it contains a non-whitespace value."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def _native_media_url_observation(value: Any) -> Optional[Dict[str, Any]]:
    """Project one native media clue, keeping an unavailable URL explicitly unknown."""
    if isinstance(value, str):
        url = _exact_nonempty_text(value)
        return {"url": url} if url is not None else None
    if not isinstance(value, dict):
        return None
    url = _exact_nonempty_text(value.get("url"))
    if url is None:
        url = _exact_nonempty_text(value.get("display_uri"))
    media_clue_fields = (
        "media_id", "id", "pk", "media_type", "product_type", "alt",
        "type", "width", "height", "mime_type", "content_type",
    )
    has_media_clue = any(
        _exact_nonempty_text(value.get(key)) is not None
        or (isinstance(value.get(key), int) and not isinstance(value.get(key), bool))
        for key in media_clue_fields
    )
    if url is None and not has_media_clue:
        return None
    observation = dict(value)
    observation["url"] = url
    return observation


def _instagram_media_observations(raw_record: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Map observed Instagram media clues to the existing media_list shape."""
    observations: List[Dict[str, Any]] = []
    children = raw_record.get("children")
    children_explicitly_empty = isinstance(children, list) and not children

    if isinstance(children, list):
        for child in children:
            observation = _native_media_url_observation(child)
            child_versions = child.get("video_versions") if isinstance(child, dict) else None
            version_observations = []
            if isinstance(child_versions, list):
                for version in child_versions:
                    version_observation = _native_media_url_observation(version)
                    if version_observation is None:
                        continue
                    for native_key in ("media_id", "id", "pk", "media_type", "product_type"):
                        if native_key in child:
                            version_observation.setdefault(native_key, child[native_key])
                    version_observations.append(version_observation)
            if observation is not None and (observation.get("url") is not None or not version_observations):
                observations.append(observation)
            observations.extend(version_observations)

    display_observation = _native_media_url_observation(raw_record.get("display_uri"))
    if display_observation is not None:
        observations.append(display_observation)

    versions = raw_record.get("video_versions")
    if isinstance(versions, list):
        for version in versions:
            observation = _native_media_url_observation(version)
            if observation is not None:
                observations.append(observation)

    if observations:
        return observations
    return [] if children_explicitly_empty else None


def _wechat_media_observations(raw_record: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Map public article image URL/alt observations to the existing media_list."""
    images = raw_record.get("images")
    if not isinstance(images, list):
        return None
    observations = [
        observation for image in images
        if (observation := _native_media_url_observation(image)) is not None
    ]
    if observations:
        return observations
    return [] if not images else None


def _normalize_author_identity(value: Any) -> Optional[str]:
    """Keep author IDs as exact text without coercing lossy or ambiguous types.

    Platform author identities may be opaque handles/tokens, so their text is
    never passed through content-ID normalization. Python integers are exact
    and can be represented as decimal text; booleans, floats and containers do
    not establish a trustworthy identity.
    """
    text = _exact_nonempty_text(value)
    if text is not None:
        return text
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    return None


def _normalize_bilibili_publication(value: Any) -> Optional[str]:
    """Normalize Bilibili's Unix-second publication value to UTC ISO text."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        timestamp = value
    elif isinstance(value, str):
        source_text = value.strip()
        if not source_text:
            return None
        if re.fullmatch(r"[+-]?\d+", source_text):
            try:
                timestamp = int(source_text)
            except ValueError:
                return None
        else:
            try:
                published = datetime.fromisoformat(source_text.replace("Z", "+00:00"))
            except ValueError:
                return None
            if published.tzinfo is None:
                return None
            try:
                published = published.astimezone(timezone.utc)
            except (OverflowError, ValueError):
                return None
            timespec = "microseconds" if published.microsecond else "seconds"
            return published.isoformat(timespec=timespec)
    else:
        # Bilibili's API supplies integer seconds. Floats and other types may
        # already have lost source precision, so they do not become timestamps.
        return None

    # The source adapter treats zero as its missing timestamp sentinel.
    if timestamp == 0:
        return None
    try:
        published = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    timespec = "microseconds" if published.microsecond else "seconds"
    return published.isoformat(timespec=timespec)


def to_canonical_record(raw_record: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, Any]:
    """把一条平台原生 raw 记录映射为 canonical 记录（不修改入参，不臆造缺失值）。

    - platform 未传时尝试从 raw_record['source_platform']/['platform'] 归一化；
    - 原生字段缺失时 canonical 对应值为 None（显式缺失，不填 0/未知）；
    - 原始记录整体保留在 'raw' 键，保证全链路可追溯。
    """
    plat = normalize_platform(platform or raw_record.get("source_platform") or raw_record.get("platform"))
    out: Dict[str, Any] = {k: None for k in CANONICAL_FIELDS}
    out["platform"] = plat  # 无法识别则为 None（unknown），不编造
    out["raw"] = raw_record
    if plat and plat in CANONICAL_FROM_NATIVE:
        mapping = CANONICAL_FROM_NATIVE[plat]
        for canon_key, native_key in mapping.items():
            if native_key in raw_record:
                out[canon_key] = raw_record[native_key]
        out["author_id"] = _normalize_author_identity(out["author_id"])
        for passthrough in ("url", "title", "captured_at"):
            if passthrough in raw_record:
                out[passthrough] = raw_record[passthrough]
        if plat == "instagram" and out["content_id"] in (None, ""):
            out["content_id"] = _exact_nonempty_text(raw_record.get("shortcode"))
        if plat == "bilibili":
            out["published_at"] = _normalize_bilibili_publication(out["published_at"])
    return out


def safe_content_id(value: Any, spec: Optional[PlatformFieldSpec] = None) -> Optional[str]:
    """大整数 ID 统一转字符串保精度（抖音/微博/IG/X 19 位 ID 禁止用 int/float 丢失精度）。"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # int 在 Python 任意精度不丢，但 JSON 序列化到前端可能丢，统一转 str
    return str(value)


# ============================================================
# 4. source_platform 历史取值体检（用于数据治理，不改历史数据）
# ============================================================
def classify_historical_platform_values(values: List[str]) -> Dict[str, Any]:
    """对历史 source_platform 取值做归一化分类，返回 {canonical: [别名...], unknown: [...]}。"""
    groups: Dict[str, List[str]] = {}
    unknown: List[str] = []
    for v in values:
        canon = normalize_platform(v)
        if canon is None:
            if v not in unknown:
                unknown.append(v)
        else:
            groups.setdefault(canon, [])
            if v not in groups[canon]:
                groups[canon].append(v)
    return {"canonical_groups": groups, "unknown_values": unknown}


# ============================================================
# 5. Shard C 任务指定接口：normalize_platform_name / get_platform_fields / normalize_content_id
# ============================================================
def normalize_platform_name(raw: Optional[str]) -> Optional[str]:
    """任务指定接口名：把任意历史/别名平台标识归一化到 canonical id。

    与 normalize_platform() 行为完全一致，此处提供任务契约要求的函数名。
    无法识别返回 None（显式未知，不编造默认平台）。
    """
    return normalize_platform(raw)


def get_platform_fields(canonical_name: Optional[str]) -> Optional[PlatformFieldSpec]:
    """根据 canonical 平台名返回字段映射规范（PlatformFieldSpec）。

    入参自动归一化（允许传别名如 'xhs'）；未登记平台返回 None。
    """
    canon = normalize_platform(canonical_name)
    if canon is None:
        return None
    return PLATFORM_NATIVE_FIELDS.get(canon)


def normalize_content_id(platform: Optional[str], raw_id: Any) -> Optional[str]:
    """标准化内容 ID：大整数平台强制字符串保精度，其余去空白。

    - 抖音 aweme_id（19 位）、微博 mid/idstr、IG media_id、X tweet_id 等 id_is_bigint=True
      的平台，无论入参是 int 还是 str，统一返回 str，禁止 float/int 序列化丢精度；
    - 小红书 note_id、B站 bvid 等本身为字符串的平台，去空白后原样返回；
    - 空值返回 None（显式缺失）。
    """
    if raw_id is None or isinstance(raw_id, bool):
        return None
    spec = get_platform_fields(platform)
    if spec and spec.id_is_bigint:
        if isinstance(raw_id, float):
            return None
        if isinstance(raw_id, int):
            return str(raw_id)
        if not isinstance(raw_id, str):
            return None
        s = raw_id.strip()
        if not s or re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+", s):
            return None
        return s
    # 统一转字符串去空白；bigint 平台额外确保不经过 float
    s = str(raw_id).strip()
    if not s:
        return None
    return s


def build_content_url(
    platform: Optional[str],
    content_id: Optional[str],
    author_id: Optional[str] = None,
    token: Optional[str] = None,
) -> Optional[str]:
    """根据平台 URL 模板构建内容详情页 URL。

    占位符：{content_id} / {author_id} / {token}；缺失的可选占位符留空（不报错）。
    平台无 URL 模板或 content_id 缺失时返回 None。
    """
    spec = get_platform_fields(platform)
    if not spec or not spec.url_template or not content_id:
        return None
    url = spec.url_template.replace("{content_id}", str(content_id))
    url = url.replace("{author_id}", str(author_id) if author_id else "")
    url = url.replace("{token}", str(token) if token else "")
    # 仅在可选 token 缺失时清理空查询参数（如 ?xsec_token=），token 存在时保留
    if not token:
        url = url.replace("?xsec_token=", "").replace("&xsec_token=", "")
    return url


def get_platform_aliases(canonical_name: Optional[str]) -> List[str]:
    """反向查询：给定 canonical 平台名，返回所有已登记的别名（含 canonical 自身）。

    用于历史数据治理、UI 下拉选项、SQL IN 条件构建等场景。
    """
    canon = normalize_platform(canonical_name)
    if canon is None:
        return []
    aliases = [alias for alias, target in PLATFORM_ALIASES.items() if target == canon]
    return aliases


# ============================================================
# 6. V1.0 新增：12平台 Raw 表 Schema 注册
# ============================================================
# 每个平台的 Raw 层表名清单（与数据库迁移脚本一一对应）
PLATFORM_RAW_TABLES: Dict[str, Dict[str, str]] = {
    "xiaohongshu": {"content": "xhs_notes", "comment": "xhs_note_comments", "user": "xhs_users"},
    "douyin": {"content": "douyin_videos", "comment": "douyin_comments", "user": "douyin_users"},
    "bilibili": {"content": "bilibili_videos", "comment": "bilibili_comments", "user": "bilibili_users"},
    "channels": {"content": "channels_videos", "comment": "channels_comments", "user": None},
    "youtube": {"content": "youtube_videos", "comment": "youtube_comments", "user": "youtube_channels"},
    "tiktok": {"content": "tiktok_videos", "comment": "tiktok_comments", "user": "tiktok_users"},
    "instagram": {"content": "instagram_media", "comment": "instagram_comments", "user": "instagram_users"},
    "x": {"content": "x_posts", "comment": None, "user": "x_users"},
    "reddit": {"content": "reddit_posts", "comment": "reddit_comments", "user": "reddit_subreddits"},
    "linkedin": {"content": "linkedin_posts", "comment": None, "user": "linkedin_users"},
    "github": {"content": "github_repositories", "comment": "github_issues", "user": None},
    "zhihu": {"content": "zhihu_answers", "comment": "zhihu_comments", "user": None},
}

# 12平台标准清单（数据字典V1.0定义）
V1_PLATFORMS: List[str] = [
    "xiaohongshu", "douyin", "bilibili", "channels",
    "youtube", "tiktok", "instagram", "x",
    "reddit", "linkedin", "github", "zhihu",
]


def get_raw_table(platform: Optional[str], table_type: str = "content") -> Optional[str]:
    """获取平台 Raw 层表名。table_type: content/comment/user。"""
    canon = normalize_platform(platform)
    if canon is None or canon not in PLATFORM_RAW_TABLES:
        return None
    return PLATFORM_RAW_TABLES[canon].get(table_type)


# ============================================================
# 7. V1.0 新增：全字段映射（Raw → Normalized platform_contents）
# ============================================================
# 每个平台 Raw 内容表字段 → platform_contents 统一字段的完整映射
# 仅列需要映射的字段，raw_data 整体保留
PLATFORM_FIELD_MAPPING: Dict[str, Dict[str, str]] = {
    "xiaohongshu": {
        "platform_content_id": "note_id", "content_type": "type",
        "author_id": "user_id", "author_name": "nickname",
        "title": "title", "content": "desc",
        "published_at": "time", "url": "url",
        "like_count": "liked_count", "comment_count": "comment_count",
        "share_count": "share_count", "collect_count": "collected_count",
        "topic_list": "tag_list", "media_list": "image_list",
    },
    "douyin": {
        "platform_content_id": "aweme_id", "content_type": "aweme_type",
        "author_id": "author_id", "author_name": "nickname",
        "title": "desc", "content": "desc",
        "published_at": "create_time", "url": "url",
        "like_count": "digg_count", "comment_count": "comment_count",
        "share_count": "share_count", "collect_count": "collect_count",
        "view_count": "play_count", "hashtag_list": "hashtag_list",
        "location": "location",
    },
    "bilibili": {
        "platform_content_id": "bvid", "content_type": "tname",
        "author_id": "owner_mid", "author_name": "owner_name",
        "title": "title", "content": "description",
        "published_at": "pubdate", "url": "url",
        "like_count": "like", "comment_count": "reply",
        "share_count": "share", "collect_count": "favorite",
        "view_count": "view",
    },
    "weibo": {
        "platform_content_id": "mid", "author_id": "user_id",
        "author_name": "screen_name", "title": "text", "content": "text",
        "published_at": "created_at", "url": "url",
        "like_count": "attitudes_count", "comment_count": "comments_count",
        "share_count": "reposts_count",
    },
    "channels": {
        "platform_content_id": "object_id",
        "author_id": "author_id", "author_name": "author_name",
        "title": "desc", "content": "desc",
        "published_at": "create_time", "url": "url",
        "like_count": "like_count", "comment_count": "comment_count",
        "share_count": "share_count", "collect_count": "collect_count",
        "view_count": "view_count", "location": "location",
    },
    "public_http": {
        "platform_content_id": "content_id", "content_type": "content_type",
        "author_id": "author_id", "author_name": "author_name",
        "title": "title", "content": "content",
        "published_at": "published_at", "url": "url",
        "collected_at": "captured_at",
    },
    "web_atom": {
        "platform_content_id": "content_id", "content_type": "content_type",
        "author_id": "author_id", "author_name": "author_name",
        "title": "title", "content": "content",
        "published_at": "published_at", "url": "url",
        "view_count": "view_count", "media_list": "media_list",
    },
    "youtube": {
        "platform_content_id": "video_id", "content_type": "media_type",
        "author_id": "channel_id", "author_name": "channel_title",
        "title": "title", "content": "description",
        "published_at": "published_at", "url": "url",
        "like_count": "like_count", "comment_count": "comment_count",
        "collect_count": "favorite_count", "view_count": "view_count",
        "hashtag_list": "tags", "language": "default_language",
    },
    "tiktok": {
        "platform_content_id": "video_id",
        "author_id": "author_id", "author_name": "author_username",
        "title": "desc", "content": "desc",
        "published_at": "create_time", "url": "url",
        "like_count": "digg_count", "comment_count": "comment_count",
        "share_count": "share_count", "collect_count": "collect_count",
        "view_count": "play_count", "hashtag_list": "hashtag_list",
    },
    "instagram": {
        "platform_content_id": "media_id", "content_type": "media_type",
        "author_id": "author_id", "author_name": "author_username",
        "title": "caption", "content": "caption",
        "published_at": "taken_at", "url": "permalink",
        "like_count": "like_count", "comment_count": "comment_count",
        "hashtag_list": "hashtags", "mention_list": "mentions",
        "media_list": "children", "location": "location",
    },
    "x": {
        "platform_content_id": "tweet_id", "content_type": "tweet_type",
        "author_id": "author_id", "author_name": "author_username",
        "title": "text", "content": "text",
        "published_at": "created_at", "url": "url",
        "like_count": "like_count", "comment_count": "reply_count",
        "share_count": "retweet_count", "view_count": "impression_count",
        "hashtag_list": "hashtag_list", "mention_list": "mention_list",
    },
    "reddit": {
        "platform_content_id": "post_id", "content_type": "post_hint",
        "author_id": "author_fullname", "author_name": "author",
        "title": "title", "content": "selftext",
        "published_at": "created_utc", "url": "permalink",
        "like_count": "score", "comment_count": "num_comments",
        "share_count": "num_crossposts",
    },
    "linkedin": {
        "platform_content_id": "post_id",
        "author_id": "author_id", "author_name": "author_name",
        "title": "commentary", "content": "commentary",
        "published_at": "created_at", "url": "url",
        "like_count": "like_count", "comment_count": "comment_count",
        "share_count": "share_count", "view_count": "impression_count",
    },
    "github": {
        "platform_content_id": "repo_id", "content_type": "object_type",
        "author_id": "owner_id", "author_name": "owner",
        "title": "name", "content": "description",
        "published_at": "created_at", "url": "homepage",
        "like_count": "stargazers_count", "comment_count": "open_issues_count",
        "share_count": "forks_count", "view_count": "watchers_count",
    },
    "zhihu": {
        "platform_content_id": "answer_id", "content_type": "answer_type",
        "author_id": "author_id", "author_name": "author_name",
        "title": "question_title", "content": "content",
        "published_at": "created_time", "url": "url",
        "like_count": "voteup_count", "comment_count": "comment_count",
        "collect_count": "favlists_count",
    },
}


def map_raw_to_normalized(raw_record: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, Any]:
    """V1.0：将平台 Raw 记录完整映射为 platform_contents 统一字段。

    与 to_canonical_record() 的区别：
    - to_canonical_record() 是早期轻量映射（仅核心字段）
    - map_raw_to_normalized() 是 V1.0 完整映射（覆盖 platform_contents 全部字段）

    缺失字段值为 None（显式缺失，不填0/未知），raw_data 整体保留。
    """
    plat = normalize_platform(platform or raw_record.get("source_platform") or raw_record.get("platform"))
    # platform_contents 全部字段
    normalized: Dict[str, Any] = {
        "platform": plat, "platform_content_id": None, "content_type": None,
        "author_id": None, "author_name": None, "title": None, "content": None,
        "published_at": None, "url": None,
        "like_count": None, "comment_count": None, "share_count": None,
        "collect_count": None, "view_count": None,
        "topic_list": None, "hashtag_list": None, "mention_list": None,
        "media_list": None, "language": None, "location": None,
        "raw_data": raw_record, "collected_at": raw_record.get("collected_at"),
    }
    if plat and plat in PLATFORM_FIELD_MAPPING:
        mapping = PLATFORM_FIELD_MAPPING[plat]
        for norm_key, raw_key in mapping.items():
            if raw_key in raw_record:
                normalized[norm_key] = raw_record[raw_key]
    elif plat and plat in CANONICAL_FROM_NATIVE:
        canonical = to_canonical_record(raw_record, plat)
        for normalized_key, canonical_key in (
            ("platform_content_id", "content_id"),
            ("author_id", "author_id"),
            ("content_type", "content_type"),
            ("published_at", "published_at"),
            ("like_count", "like_count"),
            ("comment_count", "comment_count"),
            ("collect_count", "collect_count"),
            ("share_count", "share_count"),
        ):
            normalized[normalized_key] = canonical[canonical_key]
        for field_name in ("title", "url"):
            normalized[field_name] = canonical[field_name]
        if "content" in raw_record:
            normalized["content"] = raw_record["content"]
        if "captured_at" in raw_record:
            normalized["collected_at"] = canonical["captured_at"]
    if plat == "instagram":
        normalized["media_list"] = _instagram_media_observations(raw_record)
    elif plat == "wechat":
        normalized["media_list"] = _wechat_media_observations(raw_record)
    if plat:
        normalized["author_id"] = _normalize_author_identity(normalized["author_id"])
        if plat == "instagram" and normalized["platform_content_id"] in (None, ""):
            normalized["platform_content_id"] = _exact_nonempty_text(raw_record.get("shortcode"))
    return normalized


# ============================================================
# 8. Collector platform catalog / product visibility configuration
# ============================================================
@dataclass(frozen=True)
class PlatformConnectionStatus:
    """静态平台目录配置；运行健康和观测到的数据量由运行时单独维护。"""
    status: str
    ui_visible: bool
    has_collector: bool
    has_api_routes: bool
    has_real_data: Optional[bool]
    raw_tables: List[str]
    adapter_module: Optional[str]
    notes: str = ""


PLATFORM_CATALOG_NOTE = "Static capability metadata only; runtime health and observed data are not asserted."

from .config import PLATFORM_CAPABILITIES as _CAPABILITY_MANIFEST
PLATFORM_CONNECTION: Dict[str, PlatformConnectionStatus] = {
    cap["canonical_id"]: PlatformConnectionStatus(
        status=cap["catalog_status"], ui_visible=cap["collection_surface_visible"],
        has_collector=bool(cap["adapter_module"]) and cap["implementation_state"] != "PLANNED",
        has_api_routes=cap["collection_entry_enabled"], has_real_data=None,
        raw_tables=list(cap["raw_tables"]), adapter_module=cap["adapter_module"],
        notes=PLATFORM_CATALOG_NOTE)
    for cap in _CAPABILITY_MANIFEST.values()
}

def get_connection_status(platform: Optional[str]) -> Optional[PlatformConnectionStatus]:
    """获取平台接入状态。"""
    canon = normalize_platform(platform)
    if canon is None:
        return None
    return PLATFORM_CONNECTION.get(canon)


def get_ui_visible_platforms() -> List[str]:
    """获取前端可见的平台列表（ui_visible=True）。"""
    return [p for p, s in PLATFORM_CONNECTION.items() if s.ui_visible]


def get_all_platforms_with_status() -> List[Dict[str, Any]]:
    """获取所有平台及其接入状态（用于系统设置/运营管理页）。"""
    result = []
    for p in PLATFORM_CONNECTION:
        s = PLATFORM_CONNECTION.get(p)
        if s:
            result.append({
                "platform": p,
                "display_name": PLATFORM_DISPLAY_NAME.get(p, p),
                "status": s.status,
                "ui_visible": s.ui_visible,
                "has_collector": s.has_collector,
                "has_api_routes": s.has_api_routes,
                "has_real_data": s.has_real_data,
                "raw_tables": s.raw_tables,
                "adapter_module": s.adapter_module,
                "notes": s.notes,
            })
    return result


def get_platform_registry_catalog() -> List[Dict[str, Any]]:
    """Return the sole static SYSTEM Collector catalog used to seed DB metadata.

    Runtime status, visibility and observed-data fields on existing rows are
    owned by the registry/runtime and are not overwritten by schema migration.
    """
    catalog = []
    for platform, connection in PLATFORM_CONNECTION.items():
        catalog.append({
            "platform_id": platform,
            "platform_name": platform,
            "display_name": PLATFORM_DISPLAY_NAME.get(platform, platform),
            "status": connection.status,
            "ui_visible": int(connection.ui_visible),
            "adapter_module": connection.adapter_module,
            "raw_tables": list(connection.raw_tables),
            "normalized_mapping": dict(PLATFORM_FIELD_MAPPING.get(platform, {})),
            "has_collector": int(connection.has_collector),
            "has_api_routes": int(connection.has_api_routes),
            "has_real_data": None,
            "notes": PLATFORM_CATALOG_NOTE,
        })
    return catalog


# ============================================================
# 9. V1.0 新增：互动量统一计算
# ============================================================
def calculate_engagement(
    like_count: Optional[int] = None,
    collect_count: Optional[int] = None,
    comment_count: Optional[int] = None,
    share_count: Optional[int] = None,
) -> Optional[int]:
    """统一互动量 = 点赞 + 收藏 + 评论 + 分享。

    与现有笔记报告计算逻辑一致。
    - view_count/play_count 不计入互动量（属于曝光指标）
    - 所有输入为None时返回None（显式缺失，不返回0）
    - 部分为None时，仅累加有值的字段
    """
    values = [v for v in (like_count, collect_count, comment_count, share_count) if v is not None]
    if not values:
        return None
    return sum(values)


def calculate_engagement_rate(engagement: Optional[int], follower_count: Optional[int]) -> Optional[float]:
    """互动率 = 互动量 / 粉丝数。

    - follower_count 为 None 或 <= 0 时返回 None
    - engagement 为 None 时返回 None
    """
    if engagement is None or follower_count is None or follower_count <= 0:
        return None
    return round(engagement / follower_count, 6)


def engagement_from_normalized(record: Dict[str, Any]) -> Optional[int]:
    """从 platform_contents 统一记录计算互动量。"""
    return calculate_engagement(
        like_count=record.get("like_count"),
        collect_count=record.get("collect_count"),
        comment_count=record.get("comment_count"),
        share_count=record.get("share_count"),
    )
