# -*- coding: utf-8 -*-
"""平台命名与字段规范单元测试（2026-09 全网研究后建立）。"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from platform_adapters.platform_naming import (
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
)


def test_xhs_aliases_all_normalize():
    for alias in ("xhs", "xiaohongshu", "xiaohongshu-cdp", "xhs-cdp", "rednote", "小红书", "XHS"):
        assert normalize_platform(alias) == "xiaohongshu", alias


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
    assert spec.author_id == "idstr"
    assert spec.id_is_bigint is True
    assert spec.published_at == "created_at"
    assert spec.share_field == "reposts_count"


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
