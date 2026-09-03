# -*- coding: utf-8 -*-
"""可比稿方案引擎测试。"""
from scripts.campaign_plan import CATEGORY_PLAYBOOKS, PLAN_SECTIONS, generate_plan


def test_plan_structure_complete():
    p = generate_plan("测试品牌", "餐饮", "新品上市", "500万", "18-30岁女性")
    assert p["meta"]["brand"] == "测试品牌"
    assert p["meta"]["category"] == "餐饮"
    assert len(p["sections"]) == 10
    # 10 段提案齐全
    for _, label in PLAN_SECTIONS:
        assert label in p["sections"]
        assert p["sections"][label]
    assert p["creative_directions"] and len(p["creative_directions"]) >= 2
    assert p["touchpoints"] and p["risk"]


def test_category_playbook_differs():
    a = generate_plan("X", "餐饮")
    b = generate_plan("X", "B2B")
    assert a["category_playbook"] != b["category_playbook"]
    assert a["creative_directions"] != b["creative_directions"]
    assert a["touchpoints"] != b["touchpoints"]


def test_all_categories_cover():
    for cat in CATEGORY_PLAYBOOKS:
        p = generate_plan("X", cat)
        assert p["meta"]["category"] == cat
        assert len(p["sections"]) == 10


def test_unknown_falls_back_generic():
    p = generate_plan("X", "不存在的品类")
    assert p["category_playbook"] == CATEGORY_PLAYBOOKS["通用"]["play"]
