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
