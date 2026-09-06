# -*- coding: utf-8 -*-
"""RedNote 区域轮番（intl 港版 9223 × cn 大陆 9222）+ KOS 强制 intl 测试。"""
import pytest

from platform_adapters import rednote_policy as rp


@pytest.fixture(autouse=True)
def _reset_state():
    rp._last_region_state["region"] = None
    rp._last_region_state["count"] = 0
    yield
    rp._last_region_state["region"] = None
    rp._last_region_state["count"] = 0


class TestRegionRotation:
    def test_normal_rotation_alternates(self):
        # 普通采集 intl/cn 交替轮番
        last = None
        seq = []
        for _ in range(4):
            sel = rp.select_region(last_region=last)
            seq.append(sel["region"])
            last = sel["region"]
        assert seq[0] == "intl"
        assert seq == ["intl", "cn", "intl", "cn"]

    def test_kos_forced_intl(self):
        # KOS 品牌采集强制 intl(9223 RedNote)
        for last in (None, "cn", "intl"):
            sel = rp.select_region(kos_only=True, last_region=last)
            assert sel["region"] == "intl"
            assert sel["cdp_port"] == 9223
            assert "rednote" in sel["host"]

    def test_force_region(self):
        sel = rp.select_region(force_region="cn")
        assert sel["region"] == "cn"
        assert sel["cdp_port"] == 9222

    def test_cn_paused_fallback_intl(self, monkeypatch):
        monkeypatch.setenv("REDNOTE_CN_PAUSED", "true")
        sel = rp.select_region(last_region="intl")
        assert sel["region"] == "intl"

    def test_port_mapping(self):
        assert rp.get_cdp_port("cn") == 9222
        assert rp.get_cdp_port("intl") == 9223

    def test_kos_consistent_with_cookie_bridge(self):
        # KOS 策略端口必须与 xhs_cookie_bridge.XHS_RETINAUT 端口一致(9223)
        try:
            from xhs_cookie_bridge import cdp_url_for, XHS_RETINAUT_NAME
            url = cdp_url_for(XHS_RETINAUT_NAME)
            assert "9223" in url
            sel = rp.select_region(kos_only=True)
            assert str(sel["cdp_port"]) in url
        except ImportError:
            pytest.skip("xhs_cookie_bridge unavailable")
