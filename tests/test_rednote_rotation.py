# -*- coding: utf-8 -*-
"""RedNote 生产区域门控：香港/国际 9223；大陆暂停。"""
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
        # 普通生产采集固定使用香港/国际入口
        last = None
        seq = []
        for _ in range(4):
            sel = rp.select_region(last_region=last)
            seq.append(sel["region"])
            last = sel["region"]
        assert seq[0] == "intl"
        assert seq == ["intl", "intl", "intl", "intl"]

    def test_kos_forced_intl(self):
        # KOS 品牌采集强制 intl(9223 RedNote)
        for last in (None, "cn", "intl"):
            sel = rp.select_region(kos_only=True, last_region=last)
            assert sel["region"] == "intl"
            assert sel["cdp_port"] == 9223
            assert "rednote" in sel["host"]

    def test_force_region(self):
        sel = rp.select_region(force_region="cn")
        assert sel["region"] == "intl"
        assert sel["cdp_port"] == 9223
        assert sel["blocked"] is True

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

    def test_collection_gate_allows_hk_and_blocks_mainland(self):
        assert rp.collection_gate(account="XHS_RETINAUT", region="intl")["ok"] is True
        blocked = rp.collection_gate(account="XHS_CN_PRIMARY", region="cn")
        assert blocked["ok"] is False
        assert blocked["code"] == "account_paused"
