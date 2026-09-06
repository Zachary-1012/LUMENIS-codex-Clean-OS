# -*- coding: utf-8 -*-
"""ZBC 平台命名与字段规范（Platform Naming Contract）。

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

from dataclasses import dataclass, field
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
    # X / Twitter
    "x": "x", "twitter": "x", "tweet": "x",
}

# canonical → 标准展示名（中/英/韩三语由 i18n 层处理，这里给中文名）
PLATFORM_DISPLAY_NAME: Dict[str, str] = {
    "xiaohongshu": "小红书", "douyin": "抖音", "kuaishou": "快手", "weibo": "微博",
    "bilibili": "B站", "zhihu": "知乎", "tieba": "贴吧",
    "instagram": "Instagram", "facebook": "Facebook", "x": "X",
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
    "weibo": PlatformFieldSpec(
        content_id="mid", author_id="idstr", id_is_bigint=True,
        published_at="created_at", like_field="attitudes_count", comment_field="comments_count",
        collect_field=None, share_field="reposts_count",
        url_template="https://m.weibo.cn/detail/{content_id}",
        notes="mid/id/idstr 并存，idstr 为字符串保精度；转发=reposts_count"),
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
        for passthrough in ("url", "title", "captured_at"):
            if passthrough in raw_record:
                out[passthrough] = raw_record[passthrough]
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
    if raw_id is None:
        return None
    spec = get_platform_fields(platform)
    # 统一转字符串去空白；bigint 平台额外确保不经过 float
    s = str(raw_id).strip()
    if not s:
        return None
    if spec and spec.id_is_bigint:
        # 防御：如果传入的是科学计数法字符串（如 7.34e18），尝试还原；无法还原则保留原串
        if "e" in s.lower() and "." in s:
            try:
                s = str(int(float(s)))
            except (ValueError, OverflowError):
                pass
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
