# -*- coding: utf-8 -*-
"""平台命名与字段规范单元测试（2026-09 全网研究后建立）。"""
import os
import sys
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lumenis.system.collector.adapters.platform_naming import (
    normalize_platform,
    platform_display_name,
    to_canonical_record,
    safe_content_id,
    classify_historical_platform_values,
    PLATFORM_NATIVE_FIELDS,
    PLATFORM_ALIASES,
    CANONICAL_FIELDS,
    # Shard C 新增接口
    normalize_platform_name,
    get_platform_fields,
    normalize_content_id,
    build_content_url,
    get_platform_aliases,
    PLATFORM_FIELD_MAPPING,
    map_raw_to_normalized,
)


def test_xhs_aliases_all_normalize():
    for alias in ("xhs", "xiaohongshu", "xiaohongshu-cdp", "xhs-cdp", "rednote", "小红书", "XHS"):
        assert normalize_platform(alias) == "xiaohongshu", alias


def test_registry_and_capability_config_resolve_xhs_aliases_without_session_access(monkeypatch):
    from lumenis.adapters import cookie_vault
    from lumenis.system.collector.adapters.config import get_platform_capabilities
    from lumenis.system.collector.adapters.registry import get_adapter

    def forbidden(*_args, **_kwargs):
        raise AssertionError("alias resolution must not read or probe any Cookie/session")

    monkeypatch.setattr(cookie_vault, "load_cookies", forbidden)
    monkeypatch.setattr(cookie_vault, "check_cookie_status", forbidden)

    for alias in ("xhs", "xiaohongshu", "rednote", "xiaohongshu-cdp", "小红书"):
        adapter = get_adapter(alias, backend=object())
        assert adapter.platform == "xhs"
        assert get_platform_capabilities(alias)["name"] == "小红书"


def test_other_platform_aliases():
    assert normalize_platform("aweme") == "douyin"
    assert normalize_platform("抖音") == "douyin"
    assert normalize_platform("b站") == "bilibili"
    assert normalize_platform("bili") == "bilibili"
    assert normalize_platform("ins") == "instagram"
    assert normalize_platform("twitter") == "x"
    assert normalize_platform("微博") == "weibo"


def test_unknown_returns_none_not_fake():
    # 未登记标识必须返回 None（显式未知），禁止编造默认平台
    assert normalize_platform("unknown_xxx") is None
    assert normalize_platform("") is None
    assert normalize_platform(None) is None
    assert normalize_platform("   ") is None


def test_display_name():
    assert platform_display_name("xiaohongshu") == "小红书"
    assert platform_display_name("douyin") == "抖音"
    assert platform_display_name(None) == "unknown"


def test_xhs_raw_to_canonical_uses_native_fields():
    raw = {
        "note_id": "n1", "xsec_token": "tok", "user_id": "u1", "time": 1700000000,
        "liked_count": 100, "comment_count": 20, "collected_count": 30,
        "share_count": 5, "type": "normal", "title": "t",
    }
    out = to_canonical_record(raw, "xhs")
    assert out["platform"] == "xiaohongshu"
    assert out["content_id"] == "n1"
    assert out["author_id"] == "u1"
    assert out["published_at"] == 1700000000
    assert out["like_count"] == 100
    assert out["collect_count"] == 30
    assert out["content_type"] == "normal"
    assert out["raw"] is raw  # 原始记录保留可追溯


def test_douyin_bigint_id_preserved():
    raw = {"aweme_id": "7342000000000000000", "sec_uid": "MS4w", "digg_count": 999}
    out = to_canonical_record(raw, "douyin")
    assert out["content_id"] == "7342000000000000000"  # 19位字符串不丢精度
    assert out["author_id"] == "MS4w"
    assert out["like_count"] == 999
    assert PLATFORM_NATIVE_FIELDS["douyin"].id_is_bigint is True


def test_missing_native_field_is_none_not_zero():
    raw = {"aweme_id": "1"}  # 缺互动字段
    out = to_canonical_record(raw, "douyin")
    assert out["comment_count"] is None
    assert out["share_count"] is None
    assert out["collect_count"] is None  # 禁止用 0 静默填充


def test_each_platform_has_core_field_spec():
    required = ("content_id", "author_id", "like_field", "comment_field", "share_field")
    for plat, spec in PLATFORM_NATIVE_FIELDS.items():
        for attr in required:
            assert getattr(spec, attr), f"{plat} 缺 {attr}"


def test_xhs_requires_signature_token():
    # 小红书详情必须 note_id + xsec_token（2026 平台规则）
    spec = PLATFORM_NATIVE_FIELDS["xiaohongshu"]
    assert spec.content_id == "note_id"
    assert spec.signature_token == "xsec_token"


def test_bilibili_uses_bvid():
    spec = PLATFORM_NATIVE_FIELDS["bilibili"]
    assert spec.content_id == "bvid"
    assert spec.like_field == "like"
    assert spec.collect_field == "favorite"


def test_bilibili_unix_publication_is_normalized_to_utc_iso_without_mutation():
    raw = {
        "bvid": "BV1timestamp",
        "pubdate": 1789704000,
        "pubdate_ts": 1789704000,
        "captured_at": "2026-10-02T00:00:00+00:00",
    }
    original = deepcopy(raw)

    canonical = to_canonical_record(raw, "bilibili")

    assert canonical["published_at"] == "2026-09-18T04:00:00+00:00"
    assert canonical["captured_at"] == raw["captured_at"]
    assert canonical["raw"] is raw
    assert raw == original


def test_bilibili_iso_publication_is_kept_in_utc():
    raw = {"bvid": "BV1isoTime", "pubdate": "2026-09-18T12:00:00+08:00"}

    canonical = to_canonical_record(raw, "bilibili")

    assert canonical["published_at"] == "2026-09-18T04:00:00+00:00"


def test_bilibili_invalid_publication_stays_unknown_without_capture_fallback():
    expected = "2026-09-18T04:00:00+00:00"
    assert to_canonical_record(
        {"bvid": "BV1numericText", "pubdate": "1789704000"}, "bilibili",
    )["published_at"] == expected

    invalid_values = (
        True,
        False,
        0,
        1789704000.5,
        "not-a-timestamp",
        "2026-09-18T04:00:00",
        253402300800,
        "0001-01-01T00:00:00+23:59",
    )
    for value in invalid_values:
        raw = {
            "bvid": "BV1invalidTimestamp",
            "pubdate": value,
            "pubdate_ts": value,
            "captured_at": "2026-10-02T00:00:00+00:00",
        }
        assert to_canonical_record(raw, "bilibili")["published_at"] is None

    without_publication = {
        "bvid": "BV1missingTimestamp",
        "captured_at": "2026-10-02T00:00:00+00:00",
    }
    assert to_canonical_record(without_publication, "bilibili")["published_at"] is None


def test_safe_content_id_stringifies():
    assert safe_content_id(1234567890123456789) == "1234567890123456789"
    assert safe_content_id("abc") == "abc"
    assert safe_content_id(None) is None


def test_historical_value_grouping():
    result = classify_historical_platform_values(
        ["xhs", "xiaohongshu", "xiaohongshu-cdp", "weibo", "wb", "ghost"]
    )
    groups = result["canonical_groups"]
    assert set(groups["xiaohongshu"]) == {"xhs", "xiaohongshu", "xiaohongshu-cdp"}
    assert set(groups["weibo"]) == {"weibo", "wb"}
    assert result["unknown_values"] == ["ghost"]


def test_canonical_fields_contract_complete():
    for must in ("content_id", "author_id", "platform", "published_at", "captured_at", "raw"):
        assert must in CANONICAL_FIELDS


def test_to_canonical_does_not_mutate_input():
    raw = {"note_id": "n", "liked_count": 1}
    before = dict(raw)
    to_canonical_record(raw, "xhs")
    assert raw == before


def test_alias_table_no_duplicate_canonical_conflict():
    # 每个别名只能映射到一个 canonical（一致性）
    assert PLATFORM_ALIASES["xhs"] == "xiaohongshu"
    assert PLATFORM_ALIASES["rednote"] == "xiaohongshu"


# ============================================================
# Shard C 新增测试：三标识归一化 + 四平台字段映射 + ID精度 + URL
# ============================================================
def test_shard_c_three_identifiers_unify():
    """验收标准2：xhs / xiaohongshu / xiaohongshu-cdp 归一化为同一 canonical。"""
    assert normalize_platform_name("xhs") == "xiaohongshu"
    assert normalize_platform_name("xiaohongshu") == "xiaohongshu"
    assert normalize_platform_name("xiaohongshu-cdp") == "xiaohongshu"
    # 三者全等
    assert (normalize_platform_name("xhs")
            == normalize_platform_name("xiaohongshu")
            == normalize_platform_name("xiaohongshu-cdp"))


def test_shard_c_normalize_platform_name_alias_behavior():
    """normalize_platform_name 与 normalize_platform 行为一致。"""
    assert normalize_platform_name("douyin") == normalize_platform("douyin")
    assert normalize_platform_name(None) is None
    assert normalize_platform_name("") is None
    assert normalize_platform_name("unknown_zzz") is None


def test_shard_c_get_platform_fields_xhs():
    spec = get_platform_fields("xhs")  # 别名也能查
    assert spec is not None
    assert spec.content_id == "note_id"
    assert spec.author_id == "user_id"
    assert spec.signature_token == "xsec_token"
    assert spec.published_at == "time"
    assert spec.id_is_bigint is False


def test_shard_c_get_platform_fields_douyin():
    spec = get_platform_fields("douyin")
    assert spec is not None
    assert spec.content_id == "aweme_id"
    assert spec.author_id == "sec_uid"
    assert spec.id_is_bigint is True
    assert spec.published_at == "create_time"
    assert spec.like_field == "digg_count"


def test_shard_c_get_platform_fields_bilibili():
    spec = get_platform_fields("bilibili")
    assert spec is not None
    assert spec.content_id == "bvid"
    assert spec.author_id == "mid"
    assert spec.published_at == "pubdate"
    assert spec.like_field == "like"
    assert spec.collect_field == "favorite"


def test_shard_c_get_platform_fields_weibo():
    spec = get_platform_fields("weibo")
    assert spec is not None
    assert spec.content_id == "mid"
    assert spec.author_id == "user_id"
    assert spec.id_is_bigint is True
    assert spec.published_at == "created_at"
    assert spec.share_field == "reposts_count"


def test_weibo_mapping_uses_post_and_author_ids_separately():
    post_id = 5012345678901234567
    raw = {
        "mid": post_id,
        "idstr": "post-idstr-5012345678901234567",
        "user_id": "author-42",
        "screen_name": "Example author",
        "created_at": "2026-10-02T10:00:00+08:00",
        "text": "Weibo post text",
        "attitudes_count": 12,
        "comments_count": 3,
        "reposts_count": 4,
    }

    canonical = to_canonical_record(raw, "weibo")
    normalized = map_raw_to_normalized(raw, "weibo")

    assert canonical["content_id"] == post_id
    assert normalize_content_id("weibo", canonical["content_id"]) == str(post_id)
    assert canonical["author_id"] == "author-42"
    assert canonical["author_id"] != raw["idstr"]
    assert normalized["platform_content_id"] == post_id
    assert normalized["author_id"] == "author-42"
    assert normalized["author_name"] == "Example author"
    assert normalized["published_at"] == raw["created_at"]
    assert normalized["content"] == raw["text"]
    assert (normalized["like_count"], normalized["comment_count"], normalized["share_count"]) == (12, 3, 4)
    assert normalized["collect_count"] is None
    assert "collect_count" not in PLATFORM_FIELD_MAPPING["weibo"]


def test_weibo_missing_user_id_does_not_promote_post_idstr_to_author():
    raw = {"mid": "5012345678901234567", "idstr": "post-idstr-only"}

    canonical = to_canonical_record(raw, "weibo")
    normalized = map_raw_to_normalized(raw, "weibo")

    assert canonical["content_id"] == raw["mid"]
    assert canonical["author_id"] is None
    assert normalized["author_id"] is None


def test_x_native_favorite_metrics_match_canonical_and_normalized_aliases():
    assert PLATFORM_FIELD_MAPPING["x"]["like_count"] == "favorite_count"

    for alias in ("x", "twitter"):
        for index, (native_metric, expected) in enumerate((
            ({"favorite_count": 17}, 17),
            ({"favorite_count": 0}, 0),
            ({"favorite_count": None}, None),
            ({}, None),
        )):
            raw = {
                "tweet_id": f"post-{index}",
                "screen_name": "author",
                "created_at": "2026-10-10T12:00:00Z",
                "text": "Source body",
                "reply_count": 4,
                "retweet_count": 5,
                "impression_count": 43,
                **native_metric,
            }
            original = deepcopy(raw)

            canonical = to_canonical_record(raw, alias)
            normalized = map_raw_to_normalized(raw, alias)

            assert canonical["platform"] == normalized["platform"] == "x"
            assert canonical["like_count"] == normalized["like_count"] == expected
            assert canonical["comment_count"] == normalized["comment_count"] == 4
            assert canonical["share_count"] == normalized["share_count"] == 5
            assert normalized["collect_count"] is None
            assert normalized["view_count"] == 43
            assert normalized["content"] == raw["text"]
            assert normalized["published_at"] == raw["created_at"]
            assert canonical["raw"] is raw
            assert normalized["raw_data"] is raw
            assert raw == original


def test_x_legacy_like_count_fallback_only_applies_when_native_key_is_absent():
    for native_metric, expected in ((17, 17), (0, 0), (None, None)):
        raw = {"favorite_count": native_metric, "like_count": 99}
        normalized = map_raw_to_normalized(raw, "x")
        assert normalized["like_count"] == expected
        assert normalized["raw_data"] is raw

    legacy_only = {"like_count": 9}
    normalized = map_raw_to_normalized(legacy_only, "twitter")
    canonical = to_canonical_record(legacy_only, "twitter")
    assert normalized["like_count"] == 9
    # Canonical continues to read the native favorite_count field only.
    assert canonical["like_count"] is None
    assert normalized["raw_data"] is legacy_only
    assert canonical["raw"] is legacy_only


def test_instagram_native_media_urls_project_without_losing_post_or_child_identity():
    repeated_image_url = "https://cdn.example.test/media/carousel-image.jpg"
    raw = {
        "platform": "instagram",
        "media_id": "ig-post-42",
        "shortcode": "AbC_42",
        "media_type": "carousel",
        "permalink": "https://www.instagram.com/p/AbC_42/",
        "caption": "Original caption body",
        "like_count": 18,
        "display_uri": "https://cdn.example.test/media/post-cover.jpg",
        "video_versions": [{
            "type": "video/mp4",
            "url": "https://cdn.example.test/media/post-video.mp4",
            "width": 720,
            "height": 1280,
        }],
        "children": [
            {"media_id": "ig-child-1", "media_type": "image", "display_uri": repeated_image_url},
            {"media_id": "ig-child-2", "media_type": "video", "video_versions": [{
                "type": "video/mp4",
                "url": "https://cdn.example.test/media/child-video.mp4",
                "width": 1080,
                "height": 1920,
            }]},
            {"media_id": "ig-child-3", "media_type": "image", "url": repeated_image_url},
        ],
    }
    original = deepcopy(raw)

    normalized = map_raw_to_normalized(raw, "instagram")

    media = normalized["media_list"]
    assert [item["url"] for item in media] == [
        repeated_image_url,
        "https://cdn.example.test/media/child-video.mp4",
        repeated_image_url,
        "https://cdn.example.test/media/post-cover.jpg",
        "https://cdn.example.test/media/post-video.mp4",
    ]
    assert media[0]["media_id"] == "ig-child-1"
    assert media[1]["media_id"] == "ig-child-2"
    assert media[1]["media_type"] == "video"
    assert media[2]["media_id"] == "ig-child-3"
    assert media[3] == {"url": "https://cdn.example.test/media/post-cover.jpg"}
    assert media[4]["width"] == 720
    assert normalized["platform_content_id"] == "ig-post-42"
    assert normalized["url"] == raw["permalink"]
    assert normalized["content"] == "Original caption body"
    assert normalized["like_count"] == 18
    assert normalized["raw_data"] is raw
    assert raw == original


def test_instagram_media_missing_invalid_and_explicit_empty_states_stay_distinct():
    assert map_raw_to_normalized(
        {"platform": "instagram", "media_id": "ig-missing", "caption": "body"}
    )["media_list"] is None
    assert map_raw_to_normalized(
        {"platform": "instagram", "media_id": "ig-empty", "children": []}
    )["media_list"] == []

    invalid = {
        "platform": "instagram",
        "media_id": "ig-invalid",
        "children": [None, 7, {"unrelated": "no media clue"}, {"display_uri": "   "}],
        "display_uri": 42,
        "video_versions": [None, {"url": ""}, {"quality": 720}],
    }
    normalized = map_raw_to_normalized(invalid)
    assert normalized["media_list"] is None
    assert normalized["raw_data"] is invalid


def test_media_metadata_without_url_is_preserved_as_an_unknown_url_observation():
    instagram_raw = {
        "platform": "instagram",
        "media_id": "ig-post-with-media-clues",
        "children": [
            {"media_id": "ig-child-no-url", "media_type": "image"},
            {"media_id": "ig-child-video", "media_type": "video", "video_versions": [
                {"type": "video/mp4", "width": 720, "height": 1280},
            ]},
        ],
    }
    instagram_original = deepcopy(instagram_raw)
    instagram = map_raw_to_normalized(instagram_raw, "instagram")

    assert instagram["media_list"] == [
        {"media_id": "ig-child-no-url", "media_type": "image", "url": None},
        {
            "type": "video/mp4", "width": 720, "height": 1280,
            "media_id": "ig-child-video", "media_type": "video", "url": None,
        },
    ]
    assert instagram["media_list"] is not None
    assert map_raw_to_normalized(
        {"platform": "instagram", "media_id": "ig-post-without-media-observation"}
    )["media_list"] is None
    assert instagram["raw_data"] is instagram_raw
    assert instagram_raw == instagram_original

    wechat_raw = {
        "platform": "wechat",
        "article_id": "biz-1|mid-media-clue",
        "images": [{"alt": "Observed chart description", "type": "image"}],
    }
    wechat_original = deepcopy(wechat_raw)
    wechat = map_raw_to_normalized(wechat_raw, "wechat")
    assert wechat["media_list"] == [
        {"alt": "Observed chart description", "type": "image", "url": None},
    ]
    assert wechat["raw_data"] is wechat_raw
    assert wechat_raw == wechat_original


def test_wechat_image_urls_keep_alt_and_body_and_distinguish_empty_or_invalid():
    image_url = "https://mmbiz.example.test/article/image.jpg"
    raw = {
        "platform": "wechat",
        "article_id": "biz-1|mid-2|idx-1|sn-abc",
        "url": "https://mp.weixin.qq.com/s/article-token",
        "title": "Article title",
        "content": "Original article body",
        "images": [
            {"url": image_url, "alt": "Article diagram"},
            {"url": "   ", "alt": "Observed image description with unavailable URL"},
            {"url": image_url, "alt": "Repeated source URL"},
        ],
    }
    original = deepcopy(raw)

    normalized = map_raw_to_normalized(raw, "wechat")

    assert normalized["media_list"] == [
        {"url": image_url, "alt": "Article diagram"},
        {"url": None, "alt": "Observed image description with unavailable URL"},
        {"url": image_url, "alt": "Repeated source URL"},
    ]
    assert normalized["platform_content_id"] == raw["article_id"]
    assert normalized["url"] == raw["url"]
    assert normalized["content"] == "Original article body"
    assert normalized["raw_data"] is raw
    assert raw == original
    assert map_raw_to_normalized(
        {"platform": "wechat", "article_id": "biz-1|mid-3", "images": []}
    )["media_list"] == []
    assert map_raw_to_normalized(
        {"platform": "wechat", "article_id": "biz-1|mid-4"}
    )["media_list"] is None
    assert map_raw_to_normalized(
        {"platform": "wechat", "article_id": "biz-1|mid-5", "images": [None, 3, {}, {"url": " ", "alt": "  "}]}
    )["media_list"] is None


def test_wechat_embedded_media_hints_survive_projection_without_inventing_resources():
    raw = {"platform": "wechat", "article_id": "native-article", "content": "原文",
           "images": [], "media_hints": [
               {"media_type": "audio", "media_id": "voice-1", "url": None,
                "native_attributes": {"name": "发布者音频标题"},
                "native_locator": {"container": "#js_content", "media_element_index": 0}},
               {"media_type": "video", "media_id": "finder-1", "url": None,
                "observed_data_url": "https://example.test/cover.jpg",
                "observed_data_url_role": "UNKNOWN"},
           ]}
    original = deepcopy(raw)
    normalized = map_raw_to_normalized(raw, "wechat")
    assert normalized["media_list"] == raw["media_hints"]
    assert normalized["raw_data"] is raw and raw == original
    assert normalized["content"] == "原文"
    assert all(item["url"] is None for item in normalized["media_list"])
    assert map_raw_to_normalized({"platform": "wechat", "images": [], "media_hints": []})["media_list"] == []
    assert map_raw_to_normalized({"platform": "wechat", "images": [], "media_hints": [{}]})["media_list"] is None


def test_native_platform_without_full_mapping_uses_known_core_fields():
    raw = {
        "content_id": "rss-item-1",
        "source_id": "publisher-1",
        "published_at": "2026-10-01T08:00:00Z",
        "like_count": 0,
        "comment_count": None,
        "share_count": 5,
        "type": "article",
        "title": "Public item",
        "content": "Public content",
        "url": "https://public.example.test/item-1",
        "captured_at": "2026-10-02T08:00:00Z",
        "tags": ["unmapped extension"],
    }
    original = deepcopy(raw)

    normalized = map_raw_to_normalized(raw, "web_rss")

    assert normalized["platform"] == "web_rss"
    assert normalized["platform_content_id"] == "rss-item-1"
    assert normalized["author_id"] == "publisher-1"
    assert normalized["content_type"] == "article"
    assert normalized["published_at"] == "2026-10-01T08:00:00Z"
    assert normalized["like_count"] == 0
    assert normalized["comment_count"] is None
    assert normalized["share_count"] == 5
    assert normalized["collect_count"] is None
    assert normalized["title"] == "Public item"
    assert normalized["content"] == "Public content"
    assert normalized["url"] == "https://public.example.test/item-1"
    assert normalized["collected_at"] == "2026-10-02T08:00:00Z"
    assert normalized["hashtag_list"] is None
    assert normalized["raw_data"] is raw
    assert raw == original


def test_sitemap_lastmod_stays_raw_and_does_not_become_publication():
    spec = get_platform_fields("sitemap")
    raw = {
        "platform": "sitemap",
        "content_id": "page-1",
        "url": "https://public.example.test/page-1",
        "lastmod": "2026-10-01T08:00:00Z",
        "captured_at": "2026-10-02T08:00:00Z",
    }

    normalized = map_raw_to_normalized(raw, "sitemap")

    assert spec is not None
    assert spec.published_at == "published_at"
    assert normalized["published_at"] is None
    assert normalized["collected_at"] == raw["captured_at"]
    assert normalized["raw_data"] is raw
    assert normalized["raw_data"]["lastmod"] == "2026-10-01T08:00:00Z"


def test_weibo_bigint_ids_reject_float_boolean_and_scientific_strings():
    exact_int = 5012345678901234567
    exact_string = "5012345678901234567"

    assert normalize_content_id("weibo", exact_int) == exact_string
    assert normalize_content_id("weibo", exact_string) == exact_string
    assert normalize_content_id("weibo", 5.012345678901234e18) is None
    assert normalize_content_id("weibo", "5.012345678901234e+18") is None
    assert normalize_content_id("weibo", "5.012345678901234E18") is None
    assert normalize_content_id("weibo", True) is None


def test_unknown_platform_does_not_map_known_looking_fields():
    raw = {
        "platform": "unlisted_platform",
        "content_id": "source-id",
        "author_id": "source-author",
        "published_at": "2026-10-01T08:00:00Z",
        "like_count": 9,
        "title": "Unmapped title",
        "content": "Unmapped content",
        "url": "https://public.example.test/unmapped",
    }

    normalized = map_raw_to_normalized(raw)

    assert normalized["platform"] is None
    assert normalized["platform_content_id"] is None
    assert normalized["author_id"] is None
    assert normalized["published_at"] is None
    assert normalized["like_count"] is None
    assert normalized["title"] is None
    assert normalized["content"] is None
    assert normalized["url"] is None
    assert normalized["raw_data"] is raw


def test_shard_c_get_platform_fields_unknown_returns_none():
    assert get_platform_fields("ghost_platform") is None
    assert get_platform_fields(None) is None


def test_shard_c_four_platforms_all_have_url_template():
    """验收标准3：四平台字段映射表完整（含 URL 构建方式）。"""
    for plat in ("xiaohongshu", "douyin", "bilibili", "weibo"):
        spec = get_platform_fields(plat)
        assert spec is not None, f"{plat} 缺字段映射"
        assert spec.content_id, f"{plat} 缺 content_id"
        assert spec.author_id, f"{plat} 缺 author_id"
        assert spec.published_at, f"{plat} 缺 published_at"
        assert spec.url_template, f"{plat} 缺 url_template"


def test_shard_c_normalize_content_id_douyin_19digit_string():
    """验收标准4：抖音 19 位 aweme_id 以字符串保留精度。"""
    raw = "7342000000000000000"
    result = normalize_content_id("douyin", raw)
    assert result == raw
    assert isinstance(result, str)
    assert len(result) == 19
    # int 入参也转 str
    result_int = normalize_content_id("douyin", 7342000000000000000)
    assert result_int == "7342000000000000000"
    assert isinstance(result_int, str)


def test_shard_c_normalize_content_id_xhs_passthrough():
    assert normalize_content_id("xhs", "abc123") == "abc123"
    assert normalize_content_id("xhs", "  abc123  ") == "abc123"


def test_shard_c_normalize_content_id_empty_returns_none():
    assert normalize_content_id("douyin", "") is None
    assert normalize_content_id("douyin", None) is None
    assert normalize_content_id("douyin", "   ") is None


def test_shard_c_normalize_content_id_bilibili_bvid():
    assert normalize_content_id("bilibili", "BV1xx411c7mD") == "BV1xx411c7mD"


def test_shard_c_normalize_content_id_weibo_mid():
    mid = "5012345678901234"
    assert normalize_content_id("weibo", mid) == mid
    assert isinstance(normalize_content_id("weibo", mid), str)


def test_shard_c_build_url_xhs():
    url = build_content_url("xhs", "note123", token="tok456")
    assert "xiaohongshu.com/explore/note123" in url
    assert "xsec_token=tok456" in url


def test_shard_c_build_url_xhs_without_token():
    url = build_content_url("xhs", "note123")
    assert "xiaohongshu.com/explore/note123" in url
    assert "xsec_token=" not in url  # 空 token 已清理


def test_shard_c_build_url_douyin():
    url = build_content_url("douyin", "7342000000000000000")
    assert url == "https://www.douyin.com/video/7342000000000000000"


def test_shard_c_build_url_bilibili():
    url = build_content_url("bilibili", "BV1xx411c7mD")
    assert url == "https://www.bilibili.com/video/BV1xx411c7mD"


def test_shard_c_build_url_weibo():
    url = build_content_url("weibo", "5012345678901234")
    assert url == "https://m.weibo.cn/detail/5012345678901234"


def test_shard_c_build_url_unknown_platform_returns_none():
    assert build_content_url("ghost", "123") is None
    assert build_content_url("xhs", None) is None


def test_shard_c_get_platform_aliases_reverse_lookup():
    """反向查询：canonical → 所有别名列表。"""
    aliases = get_platform_aliases("xiaohongshu")
    assert "xhs" in aliases
    assert "xiaohongshu" in aliases
    assert "xiaohongshu-cdp" in aliases
    assert "rednote" in aliases

    aliases_dy = get_platform_aliases("douyin")
    assert "aweme" in aliases_dy
    assert "douyin" in aliases_dy

    assert get_platform_aliases("ghost") == []


def test_shard_c_douyin_canonical_record_preserves_bigint():
    """端到端：抖音 raw → canonical → normalize_content_id，19 位 ID 全程不丢精度。"""
    raw = {"aweme_id": "7342000000000000000", "sec_uid": "MS4w", "digg_count": 999}
    canonical = to_canonical_record(raw, "aweme")  # 用别名
    assert canonical["platform"] == "douyin"
    cid = normalize_content_id("douyin", canonical["content_id"])
    assert cid == "7342000000000000000"
    assert isinstance(cid, str)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            passed += 1
            print(f"PASS {fn.__name__}")
        except Exception:
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
