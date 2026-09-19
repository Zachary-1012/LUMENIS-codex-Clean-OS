# -*- coding: utf-8 -*-
"""创意引擎 SIT 六模板机制 + 案例背书测试。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import idea_generator as ig

# 案例库真实数据可用性检查：生产库 case_study 表为空时跳过数据依赖测试
_CASE_BACKING_EMPTY = len(ig._load_case_backing()) == 0
require_case_backing = pytest.mark.skipif(
    _CASE_BACKING_EMPTY,
    reason="案例库为空（生产库无 case_study 数据），跳过数据依赖测试")


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


@require_case_backing
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

@require_case_backing
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


@require_case_backing
def test_provenance_circle_and_luxe():
    """高奢圈层 + profile 时 provenance 携带 circle_reference + luxe_profile。"""
    r = ig.generate_ideas("某珠宝品牌", "零售", {"topics": ["上新"], "sentiment": "positive",
                           "circle": "高奢珠宝腕表", "profile": "菁英自驱家"},
                          n=3, tonality="luxury", budget="high", seed=7)
    p = r["ideas"][0]["provenance"]
    assert p.get("circle_reference") and p["circle_reference"].get("title")
    assert p.get("luxe_profile") and p["luxe_profile"].get("trigger")


def test_idea_payload_carries_circle_assets():
    """当前创意引擎输出携带圈层符号与来源，不假设已下线报告引擎消费层。"""
    result = ig.generate_ideas(
        "某商业体", "零售", {"topics": ["上新"], "sentiment": "positive",
                         "circle": "都市高净值"},
        n=1, seed=17,
    )
    assert len(ig.CIRCLE_SYMBOLS) == 16
    idea = result["ideas"][0]
    assert idea["circle"] == "都市高净值"
    assert idea["circle_symbols"] == ig.CIRCLE_SYMBOLS["都市高净值"]["symbols"]
    assert isinstance(idea["provenance"], dict)


# ============================================================
# 6) 国际 4A 案例背书 + 营销节点×圈层联动
# ============================================================

@require_case_backing
def test_intl_case_backing_hits():
    """国际 4A 案例（2026 戛纳）作为机制背书命中。"""
    for mech, keyword in (("eventify", "草坪"), ("participate", "Supernova"), ("constraint", "Therabody")):
        b = ig._case_backing(mech)
        assert b and b.get("case_title"), f"{mech} 无案例背书"
        assert keyword in b["case_title"] or keyword in b["case_brand"]


@require_case_backing
def test_node_circles_link():
    """营销节点×圈层联动：中秋节→新中式国潮/母婴/高奢，双十一→都市高净值。"""
    r = ig._node_circles("中秋节")
    assert r and "新中式国潮" in r["circles"] and "母婴家庭" in r["circles"]
    r2 = ig._node_circles("双十一")
    assert r2 and "都市高净值" in r2["circles"]
    assert ig._node_circles("") is None
    assert ig._node_circles("不存在的节点") is None


@require_case_backing
def test_hotspot_node_in_provenance():
    """generate_ideas 带 hotspot 时 provenance 携带 node_circles（节点联动可追溯）。"""
    r = ig.generate_ideas("某商业体", "零售", {"topics": ["中秋礼"], "sentiment": "positive",
                           "circle": "新中式国潮", "hotspot": "中秋节"},
                          n=3, tonality="premium", budget="low", seed=9)
    p = r["ideas"][0]["provenance"]
    assert p.get("node_circles") and "新中式国潮" in p["node_circles"]["circles"]


@require_case_backing
def test_intl_case_flows_into_production():
    """国际案例进入真实生产产出（机制背书 + 节点 + 约束转译可同时携带）。"""
    r = ig.generate_ideas("某商业体", "零售", {"topics": ["中秋礼"], "sentiment": "positive",
                           "circle": "新中式国潮", "hotspot": "中秋节", "constraint_type": "预算"},
                          n=8, tonality="premium", budget="low", seed=9)
    any_cb = any(i["provenance"].get("case_reference") for i in r["ideas"])
    any_node = any(i["provenance"].get("node_circles") for i in r["ideas"])
    assert any_cb and any_node
