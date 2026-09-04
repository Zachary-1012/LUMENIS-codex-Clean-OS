# -*- coding: utf-8 -*-
"""IC-020/028/047 Contract 测试（DB 隔离：独立临时库 + module 级 autouse fixture 重置 env）。"""
import os
import sys
import tempfile

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import alert_engine as ae
import kos_scenarios as ks


@pytest.fixture(autouse=True)
def _iso_db():
    """模块级 DB 隔离：每次测试用独立临时库（ZBC_DB_PATH 强制指向）。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    old = os.environ.get("ZBC_DB_PATH")
    os.environ["ZBC_DB_PATH"] = path
    yield
    if old is None:
        os.environ.pop("ZBC_DB_PATH", None)
    else:
        os.environ["ZBC_DB_PATH"] = old
    try:
        os.remove(path)
    except Exception:
        pass


# ============ IC-020 alert_engine ============

class TestAlertEngine:
    def test_init_tables_idempotent(self):
        ae.init_alert_tables()
        ae.init_alert_tables()  # 二次调用不抛错
        cfg = ae.get_config()
        assert cfg["enabled"] is True
        assert cfg["risk_index_high"] == 70.0
        assert "neg_ratio_high" in cfg
        assert "cooldown_hours" in cfg

    def test_default_config_seeded_once(self):
        ae.init_alert_tables()
        cfg = ae.get_config()
        assert len(cfg) == len(ae.DEFAULT_ALERT_CONFIG)

    def test_set_config_updates_only_valid_keys(self):
        ae.init_alert_tables()
        out = ae.set_config({"risk_index_high": 80.0, "not_a_real_key": 999})
        assert out["risk_index_high"] == 80.0
        assert "not_a_real_key" not in out

    def test_evaluate_alerts_disabled_returns_no_alerts(self):
        ae.init_alert_tables()
        ae.set_config({"enabled": False})
        r = ae.evaluate_alerts([], risk_index=100, brand_health=0)
        assert r["enabled"] is False
        assert r["alerts"] == []

    def test_evaluate_alerts_high_risk(self):
        ae.init_alert_tables()
        notes = [
            {"sentiment": "negative", "risk_level": "high", "likes": 100, "comments": 10},
            {"sentiment": "negative", "risk_level": "medium", "likes": 5, "comments": 1},
            {"sentiment": "positive", "risk_level": "low", "likes": 3, "comments": 0},
            {"sentiment": "neutral", "risk_level": "low", "likes": 1, "comments": 0},
        ]
        r = ae.evaluate_alerts(notes, risk_index=75.0, brand_health=55.0, event_high_count=4)
        assert len(r["alerts"]) >= 3
        types = {a["type"] for a in r["alerts"]}
        assert "risk_index" in types
        assert "negative_surge" in types
        assert "high_risk_cluster" in types

    def test_state_machine_valid_chain(self):
        ae.init_alert_tables()
        ae.evaluate_alerts([], risk_index=90.0)
        rec = ae.list_records(limit=1)[0]
        aid = rec["id"]
        ae.transition_state(aid, "NOTIFIED", operator="test")
        ae.transition_state(aid, "ESCALATED", operator="test")
        ae.transition_state(aid, "RESOLVED", operator="test")
        assert ae.list_records(state="RESOLVED", limit=1)[0]["state"] == "RESOLVED"

    def test_state_machine_illegal_transition_blocked(self):
        ae.init_alert_tables()
        ae.evaluate_alerts([], risk_index=90.0)
        rec = ae.list_records(limit=1)[0]
        with pytest.raises(ValueError):
            ae.transition_state(rec["id"], "DETECTED", operator="test")  # RESOLVED→DETECTED 非法
        with pytest.raises(ValueError):
            ae.transition_state(rec["id"], "INVALID_STATE", operator="test")

    def test_evaluate_alerts_cooldown_dedup(self):
        ae.init_alert_tables()
        notes = [{"sentiment": "negative", "risk_level": "high", "likes": 5, "comments": 1}]
        r1 = ae.evaluate_alerts(notes, risk_index=80.0)
        r2 = ae.evaluate_alerts(notes, risk_index=80.0)  # 冷却期内不重复
        assert len(r1["alerts"]) >= 1
        assert r2["alerts"] == []


# ============ IC-028 marketing_calendar（import 走 scripts 包） ============

class TestMarketingCalendarEnhance:
    @pytest.fixture()
    def mc(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mc_test", os.path.join(BASE, "scripts", "marketing_calendar.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_nodes_gain_ic028_fields(self, mc):
        jun = mc.nodes_for_month(6)
        assert jun, "6月应有节点"
        for n in jun:
            assert "priority" in n
            assert "lead_days" in n
            assert "burst" in n

    def test_priority_rules(self, mc):
        jun = {n["name"]: n for n in mc.nodes_for_month(6)}
        assert jun["618 大促"]["priority"] == "core"
        assert jun["618 大促"]["lead_days"] == 14
        assert jun["618 大促"]["burst"] is True
        assert jun["夏至"]["priority"] == "solar"
        assert jun["夏至"]["burst"] is False

    def test_original_fields_preserved(self, mc):
        n = mc.nodes_for_month(6)[0]
        for k in ("name", "date", "kind", "theme", "cats"):
            assert k in n, f"原字段 {k} 丢失（向后兼容破坏）"

    def test_hotspot_injects_enrich(self, mc):
        hs = mc.suggest_hotspot("2026-06-18", "数码")
        assert hs["nodes"]
        assert all("priority" in n for n in hs["nodes"])

    def test_node_on_enriched(self, mc):
        hits = mc.node_on("06-18")
        assert hits
        assert all("priority" in n for n in hits)


# ============ IC-047 kos_scenarios ============

class TestKosScenarios:
    def test_scenario_tags_tax_free(self):
        tags = ks.scenario_tags("海南中免")
        assert "tax_free" in tags
        assert "vip" in tags
        assert "private" in tags

    def test_scenario_tags_other_brand(self):
        assert ks.scenario_tags("广州太古汇") == ["private"]

    def test_recommend_no_write(self):
        """只读聚合：不写 kos_profiles 主表，不改变 profile 条数。"""
        before = len(ks.kos_engine.list_profiles(limit=1000))
        r = ks.recommend("海南中免", limit=5)
        after = len(ks.kos_engine.list_profiles(limit=1000))
        assert before == after  # 主表未被写
        assert "message" in r
        assert "tags" in r

    def test_recommend_structure(self):
        r = ks.recommend("海南中免", limit=5)
        assert r["brand"] == "海南中免"
        assert "collection_stats" in r
        assert "profiles" in r
        # 有真实采集数据时 profiles 应含 scenario_advice
        if r.get("note_count"):
            for p in r["profiles"]:
                assert "scenario_advice" in p
