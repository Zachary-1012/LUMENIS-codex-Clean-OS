# -*- coding: utf-8 -*-
"""KOS 主体归属硬规则单元测试（Contract 第六条核心红线）

覆盖：
1. 全局默认锁定广州太古汇（生产红线，不得被弱化/切换）
2. 海南中免主体命中（正向词）
3. 海南中免排除词一票否决（"日上免税"含"免税"但非海南中免）
4. 多品牌隔离（海南中免命中 ≠ 广州太古汇命中）
5. subject_hit_for_brand 显式激活非默认品牌
6. 环境变量 ZBC_ACTIVE_BRAND 切换激活品牌
7. 空内容不命中
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import subject_rules as sr  # noqa: E402


class TestNoImplicitSubjectScope:
    """The controlled Taikoo reference remains explicit, never the global default."""

    def test_no_thread_scope_does_not_select_a_reference(self, monkeypatch):
        monkeypatch.setattr("subject_context.get_thread_context", lambda: None)
        monkeypatch.setenv("ZBC_ACTIVE_BRAND", "guangzhou_taikoo_hui")
        assert sr.get_active_brand() == ""
        assert sr.get_brand_config()["collect_keywords"] == []
        assert sr.subject_hit(title="广州太古汇探店") is False

    def test_controlled_reference_requires_explicit_profile(self):
        assert sr.subject_hit_for_brand(
            title="广州太古汇探店", brand_key="guangzhou_taikoo_hui",
        ) is True
        assert sr.subject_hit_for_brand(title="广州太古汇探店") is False

    def test_environment_variable_does_not_supply_subject_scope(self, monkeypatch):
        monkeypatch.setattr("subject_context.get_thread_context", lambda: None)
        monkeypatch.setenv("ZBC_ACTIVE_BRAND", "hainan_cdf")
        assert sr.get_active_brand() == ""
        assert sr.subject_hit(title="海南中免CDF攻略") is False


class TestHainanCdfSubjectHit:
    """海南中免主体归属：正向词命中 + 排除词一票否决。"""

    def test_hainan_positive_words_hit(self):
        """海南中免正向词应命中。"""
        for title in ["海南中免购物攻略", "CDF三亚免税城测评", "中免集团海口店", "离岛免税经验"]:
            assert sr.subject_hit_for_brand(title=title, brand_key="hainan_cdf") is True, f"{title} 应命中"

    def test_hainan_exclude_words_veto(self):
        """排除词一票否决：含其他免税品牌即使有"免税"也不命中海南中免。"""
        for title in ["日上免税店攻略", "海旅免税城", "深免购物中心", "中出服免税", "珠海免税"]:
            assert sr.subject_hit_for_brand(title=title, brand_key="hainan_cdf") is False, f"{title} 应被排除"

    def test_hainan_exclude_other_regions(self):
        """其他地区中免（北京/上海/深圳）不属于海南中免。"""
        for title in ["北京中免大厦", "上海中免旗舰店", "深圳中免体验店"]:
            assert sr.subject_hit_for_brand(title=title, brand_key="hainan_cdf") is False, f"{title} 应被排除"

    def test_hainan_empty_content_no_hit(self):
        """空内容不命中。"""
        assert sr.subject_hit_for_brand(title="", body="", brand_key="hainan_cdf") is False


class TestMultiBrandIsolation:
    """多品牌隔离：一个品牌命中 ≠ 另一个品牌命中。"""

    def test_guangzhou_hit_not_hainan(self):
        """广州太古汇命中的内容，不应命中海南中免。"""
        title = "广州太古汇LV快闪店"
        assert sr.subject_hit_for_brand(title=title, brand_key="guangzhou_taikoo_hui") is True
        assert sr.subject_hit_for_brand(title=title, brand_key="hainan_cdf") is False

    def test_hainan_hit_not_guangzhou(self):
        """海南中免命中的内容，不应命中广州太古汇。"""
        title = "三亚国际免税城CDF购物"
        assert sr.subject_hit_for_brand(title=title, brand_key="hainan_cdf") is True
        assert sr.subject_hit_for_brand(title=title, brand_key="guangzhou_taikoo_hui") is False

    def test_dfs_brands_isolated(self):
        """各 DFS 品牌互相隔离（香港DFS ≠ 澳门DFS）。"""
        title = "尖沙咀DFS T广场"
        assert sr.subject_hit_for_brand(title=title, brand_key="hongkong_dfs") is True
        assert sr.subject_hit_for_brand(title=title, brand_key="macau_dfs") is False


class TestExplicitProfileValidation:
    def test_unknown_explicit_profile_is_rejected(self):
        with pytest.raises(ValueError, match="UNKNOWN_SUBJECT_PROFILE"):
            sr.get_brand_config("nonexistent_brand")


def test_kos_collection_uses_canonical_scoped_secondary_writer(monkeypatch):
    from flask import Flask
    import experience_runtime
    import kos_routes
    import subject_registry
    import xhs_cookie_bridge
    from lumenis.system.collector.adapters import secondary_collection

    actor = {"id": 17}
    scope = {
        "domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": "BRAND-1", "global_scope": False,
    }
    entry = {
        "subject_id": "SUBJECT-1", "brand_focus_id": "BRAND-1", "domain_id": "BMP",
        "subject_type": "brand", "name_zh": "海南中免", "name_en": "Hainan CDF",
        "keywords": ["海南中免", "CDF", "三亚免税"],
    }
    calls = []
    monkeypatch.setattr(experience_runtime, "_content_project_scope", lambda *_a, **_k: (actor, scope))
    monkeypatch.setattr(subject_registry, "list_subjects", lambda _domain: [entry])
    monkeypatch.setattr(xhs_cookie_bridge, "is_user_paused", lambda: None)
    monkeypatch.setattr(
        secondary_collection, "collect_search",
        lambda platform, keyword, **kwargs: calls.append((platform, keyword, kwargs)) or {
            "ok": True, "status": "SUCCESS", "imported": 1, "updated": 0,
            "details": [{"content": "source body must stay behind the Evidence API"}],
        },
    )
    monkeypatch.setattr(kos_routes, "_engine", lambda: type(
        "FakeKOS", (), {"brand_collection_stats": lambda _self, _brand: {"records": 1}}
    )())

    app = Flask("kos-secondary-collection")
    app.register_blueprint(kos_routes.kos_bp)
    response = app.test_client().post("/api/kos/collect", json={
        "brand": "hainan_cdf", "operator": "human", "confirm_read_only": True,
        "max_results": 2,
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["brand_focus_id"] == "BRAND-1"
    assert body["accepted_total"] == len(calls)
    assert all("details" not in result for result in body["results"])
    assert calls
    assert all(platform == "xiaohongshu" for platform, _keyword, _kwargs in calls)
    assert all(kwargs["actor"] is actor and kwargs["scope"] is scope for _, _, kwargs in calls)
    assert {keyword for _, keyword, _ in calls} == {"海南中免", "Hainan CDF", "CDF", "三亚免税"}


def test_kos_collection_requires_read_only_confirmation_before_collection(monkeypatch):
    from flask import Flask
    import kos_routes

    app = Flask("kos-confirmation-required")
    app.register_blueprint(kos_routes.kos_bp)
    response = app.test_client().post("/api/kos/collect", json={
        "brand": "hainan_cdf", "operator": "human",
    })

    assert response.status_code == 400
    assert response.get_json()["code"] == "READ_ONLY_CONFIRMATION_REQUIRED"


class TestSubjectHitNote:
    """subject_hit_note 对 note dict 的主体判断。"""

    def test_note_dict_hit(self):
        """note dict 含主体词应命中。"""
        note = {"title": "海南中免CDF", "body": "", "content": "", "source_keywords": ""}
        assert sr.subject_hit_for_brand(title=note["title"], brand_key="hainan_cdf") is True

    def test_note_dict_no_hit(self):
        """note dict 不含主体词不命中。"""
        note = {"title": "日常分享", "body": "", "content": "", "source_keywords": ""}
        assert sr.subject_hit_for_brand(title=note["title"], brand_key="hainan_cdf") is False
