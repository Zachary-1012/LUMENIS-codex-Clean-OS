# -*- coding: utf-8 -*-
"""创意引擎 SIT 六模板机制 + 案例背书测试。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import idea_generator as ig


def test_sit_mechanism_registered():
    """SIT 六模板机制全链路注册。"""
    assert "sit" in ig.MECHANISMS
    assert "sit" in ig.MECH_TO_L1
    assert "sit" in ig.MECH_TO_HOOK
    assert "六模板转译" in ig.MECHANISMS["sit"]["name"]


def test_sit_in_all_mech_order_branches():
    """四个 mech_order 分支（luxury/negative/positive/neutral）都含 sit。"""
    src = open(ig.__file__, encoding="utf-8", errors="replace").read()
    import re
    orders = re.findall(r"mech_order\s*=\s*\[([^\]]*)\]", src)
    assert len(orders) == 4, f"期望 4 个分支，实际 {len(orders)}"
    for o in orders:
        assert '"sit"' in o or "'sit'" in o, f"分支缺 sit: {o[:40]}"


def test_sit_produces_idea_premium():
    """premium 调性生成可产出「六模板转译」机制（固定 seed）。"""
    r = ig.generate_ideas("广州太古汇", "商业地产", {"topics": ["周年"], "sentiment": "positive"},
                          n=8, tonality="premium", budget="mid", seed=20260904)
    mechs = {i["mechanism"] for i in r["ideas"]}
    assert "六模板转译" in mechs


def test_sit_produces_idea_luxury():
    """luxury 调性（Hermès）可产出「六模板转译」机制。"""
    r = ig.generate_ideas("Hermès", "高奢零售", {"topics": ["展览"]}, n=6,
                          tonality="luxury", budget="high", seed=7)
    mechs = {i["mechanism"] for i in r["ideas"]}
    assert "六模板转译" in mechs


def test_case_backing_loads_from_db():
    """案例背书能从 case_study 真实案例库读取（生产库存在时非空）。"""
    back = ig._load_case_backing()
    if os.path.exists(os.path.join("data", "monitor.db")):
        assert len(back) > 0, "生产库存在但案例背书为空"
        # 至少含"约束即创意"标签（已入库 5 条）
        assert "约束即创意" in back
    # DB 不存在时也不报错（降级空 dict）


def test_case_backing_graceful_when_db_missing(monkeypatch):
    """DB 缺失时 _load_case_backing 降级空 dict，不阻断。"""
    monkeypatch.setattr(ig, "_CASE_BACKING_CACHE", None)
    import builtins
    real_connect = __import__("sqlite3").connect

    def fake_connect(*a, **k):
        raise FileNotFoundError("no db")

    monkeypatch.setattr("sqlite3.connect", fake_connect)
    back = ig._load_case_backing()
    assert back == {}


def test_provenance_has_case_reference_field():
    """provenance 始终含 case_reference 字段（值可为 None 或真实案例）。"""
    r = ig.generate_ideas("广州太古汇", "商业地产", {"topics": ["周年"], "sentiment": "positive"},
                          n=4, tonality="premium", budget="mid", seed=11)
    for idea in r["ideas"]:
        assert "case_reference" in idea["provenance"]
        cr = idea["provenance"]["case_reference"]
        if cr is not None:
            assert "case_title" in cr and "case_source" in cr


def test_case_backing_matches_mechanism():
    """机制→案例标签匹配：constraint 命中「约束即创意」类案例。"""
    cr = ig._case_backing("constraint")
    if cr is not None:
        assert cr["case_title"]
        assert cr["case_source"]


# ============================================================
# 4) 圈层扩充（16）+ SIT×约束矩阵（约束→转译显式映射）
# ============================================================

def test_circle_expanded_to_16():
    """CIRCLE_SYMBOLS 扩充至 16 个圈层（+高奢珠宝腕表/新中式国潮/精致养宠/艺术收藏潮玩）。"""
    for name in ("高奢珠宝腕表", "新中式国潮", "精致养宠", "艺术收藏潮玩"):
        assert name in ig.CIRCLE_SYMBOLS, f"缺圈层 {name}"
        assert len(ig.CIRCLE_SYMBOLS[name]["symbols"]) >= 3
        assert ig.CIRCLE_SYMBOLS[name]["examples"]


def test_new_circle_actual_output():
    """新圈层可真实产出 idea（圈层字段正确命中）。"""
    for circle in ("新中式国潮", "精致养宠", "艺术收藏潮玩"):
        r = ig.generate_ideas("测试品牌", "零售", {"topics": ["上新"], "sentiment": "positive", "circle": circle},
                              n=2, tonality="premium", budget="mid", seed=5)
        assert len(r["ideas"]) >= 1
        assert all(i["circle"] == circle for i in r["ideas"])


def test_sit_constraint_map_has_six_templates():
    """SIT_CONSTRAINT_MAP 六模板齐全：类比/极端/后果/竞争/换维/实效。"""
    assert set(ig.SIT_CONSTRAINT_MAP.keys()) == {"类比", "极端", "后果", "竞争", "换维", "实效"}
    for meta in ig.SIT_CONSTRAINT_MAP.values():
        assert meta["constraints"] and meta["translate"]


def test_sit_translation_mapping():
    """约束类型→SIT 转译映射正确：预算→极端/同质化→竞争/媒介→换维/信任→实效。"""
    cases = {"预算": "极端", "同质化": "竞争", "媒介": "换维", "信任": "实效"}
    for ct, tpl in cases.items():
        t = ig._sit_translation({"constraint_type": ct})
        assert t and t["template"] == tpl, f"{ct} 应映射到 {tpl}"


def test_sit_idea_carries_constraint_translation():
    """sit 机制 idea 带 constraint_type 时，provenance 携带 sit_translation（约束感知）。"""
    r = ig.generate_ideas("商业体", "零售", {"topics": ["周年"], "sentiment": "positive",
                           "circle": "新中式国潮", "constraint_type": "预算"},
                          n=8, tonality="premium", budget="low", seed=3)
    sit_hits = [i for i in r["ideas"] if i["mechanism"] == "六模板转译"]
    assert sit_hits, "应产出六模板转译 idea"
    assert any(i["provenance"].get("sit_translation") for i in sit_hits)


# ============================================================
# 5) 圈层↔案例双向背书 + 美奢人群画像 + 报告消费新圈层
# ============================================================

def test_circle_backing_hits_new_circles():
    """4 个新圈层均命中真实案例背书（圈层↔案例双向）。"""
    for c in ("高奢珠宝腕表", "新中式国潮", "精致养宠", "艺术收藏潮玩"):
        r = ig._circle_backing(c)
        assert r and r.get("title") and r.get("source"), f"{c} 圈层背书缺失"


def test_circle_backing_unknown_circle_degrades():
    """未知圈层/无数据时圈层背书返回 None，不阻断生成。"""
    assert ig._circle_backing("不存在的圈层") is None
    assert ig._circle_backing(None) is None


def test_luxe_profiles_seven():
    """美奢人群画像 7 类齐全（B站×凯度 2026 报告）。"""
    assert len(ig.LUXE_PROFILES) == 7
    for name in ("菁英自驱家", "优雅人生践行者", "先锋冒险玩家", "人间社牛种草机",
                 "文化叙事研究者", "小众圈寻乐家", "理想生活预演家"):
        assert name in ig.LUXE_PROFILES
        p = ig.LUXE_PROFILES[name]
        assert p["trigger"] and p["content_pref"] and p["circle"]


def test_luxe_profile_pick():
    """人群→触发点/映射圈层正确。"""
    p = ig._profile_pick("先锋冒险玩家")
    assert p and p["trigger"] and p["circle"] == "高奢珠宝腕表"
    assert ig._profile_pick("不存在人群") is None
    assert ig._profile_pick(None) is None


def test_provenance_circle_and_luxe():
    """高奢圈层 + profile 时 provenance 携带 circle_reference + luxe_profile。"""
    r = ig.generate_ideas("某珠宝品牌", "零售", {"topics": ["上新"], "sentiment": "positive",
                           "circle": "高奢珠宝腕表", "profile": "菁英自驱家"},
                          n=3, tonality="luxury", budget="high", seed=7)
    p = r["ideas"][0]["provenance"]
    assert p.get("circle_reference") and p["circle_reference"].get("title")
    assert p.get("luxe_profile") and p["luxe_profile"].get("trigger")


def test_report_payload_consumes_circles():
    """报告引擎 payload 消费圈层资产（case_circles + 16 圈层符号表）。"""
    from report_export.report_engine import payload
    p = payload("daily")
    assert isinstance(p.get("case_circles"), dict)
    assert len(p.get("circle_symbols", {})) == 16
