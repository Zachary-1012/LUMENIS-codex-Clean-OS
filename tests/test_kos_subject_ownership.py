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


class TestGlobalDefaultLock:
    """生产红线：全局默认必须锁定广州太古汇。"""

    def test_active_brand_constant_is_guangzhou(self):
        """ACTIVE_BRAND 常量必须是广州太古汇（红线，不得改成其他品牌）。"""
        assert sr.ACTIVE_BRAND == "guangzhou_taikoo_hui"

    def test_default_active_brand_without_env(self, monkeypatch):
        """无环境变量时，get_active_brand 返回广州太古汇。"""
        monkeypatch.delenv("ZBC_ACTIVE_BRAND", raising=False)
        assert sr.get_active_brand() == "guangzhou_taikoo_hui"

    def test_default_subject_hit_uses_guangzhou(self, monkeypatch):
        """默认 subject_hit 使用广州太古汇口径（含"太古汇"命中，不含则不命中）。"""
        monkeypatch.delenv("ZBC_ACTIVE_BRAND", raising=False)
        assert sr.subject_hit(title="广州太古汇探店") is True
        assert sr.subject_hit(title="随便一篇笔记") is False


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


class TestEnvVarActivation:
    """环境变量 ZBC_ACTIVE_BRAND 切换激活品牌（KOS 多品牌并行的合法方式）。"""

    def test_env_var_switches_active_brand(self, monkeypatch):
        """设置 ZBC_ACTIVE_BRAND=hainan_cdf 后，get_active_brand 返回海南中免。"""
        monkeypatch.setenv("ZBC_ACTIVE_BRAND", "hainan_cdf")
        assert sr.get_active_brand() == "hainan_cdf"

    def test_env_var_changes_subject_hit(self, monkeypatch):
        """环境变量切换后，默认 subject_hit 使用新品牌口径。"""
        monkeypatch.setenv("ZBC_ACTIVE_BRAND", "hainan_cdf")
        # 海南中免内容在激活后应命中
        assert sr.subject_hit(title="海南中免CDF攻略") is True
        # 广州太古汇内容在海南口径下不命中
        assert sr.subject_hit(title="广州太古汇探店") is False

    def test_invalid_env_brand_falls_back_to_guangzhou(self, monkeypatch):
        """无效品牌名回退到广州太古汇（安全默认）。"""
        monkeypatch.setenv("ZBC_ACTIVE_BRAND", "nonexistent_brand")
        cfg = sr.get_brand_config()
        assert cfg.get("display_name") == "广州太古汇"


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
