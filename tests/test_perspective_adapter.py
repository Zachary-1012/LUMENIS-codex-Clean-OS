# -*- coding: utf-8 -*-
"""三方视角分级适配器测试（甲方/乙方/丙方）。"""
from scripts.campaign_plan import generate_plan
from scripts.idea_generator import generate_ideas
from scripts.perspective_adapter import (PERSPECTIVES, adapt_plan, adapt_idea,
                                         perspective_brief)


def test_three_perspectives_complete():
    """三方视角都必须有完整档案（定位/关切/语言/决策维度/KPI/证据要求/下一步）。"""
    assert set(PERSPECTIVES.keys()) == {"client", "agency", "vendor"}
    for role in ("client", "agency", "vendor"):
        p = perspective_brief(role)
        assert p["role"] and p["role_name"]
        assert p["core_concern"] and p["language"]
        assert len(p["decision_priorities"]) >= 3
        assert p["kpi"] and p["evidence_demands"] and p["call_to_action"]
        assert p["international_benchmark"]


def test_adapt_plan_perspective_views():
    """同一份方案，三方视角视图语言与章节顺序不同，且事实不变。"""
    plan = generate_plan("广州太古汇", "商业地产", "15周年声量+到店", "300万", "都市高净值")
    for role in ("client", "agency", "vendor"):
        v = adapt_plan(plan, role)
        assert v["role"] == {"client": "甲方", "agency": "乙方", "vendor": "丙方"}[role]
        assert v["brand"] == "广州太古汇"  # 事实不变
        assert v["sections"]  # 章节按视角重排
    # 三方核心关切的语言应当不同（不同视角看同一件事）
    assert "ROI" in perspective_brief("client")["core_concern"]
    assert "说服" in perspective_brief("agency")["core_concern"]
    assert "结算" in perspective_brief("vendor")["core_concern"]


def test_adapt_idea_perspective_pov():
    """同一个 idea 三方话术不同，创意本体不变。"""
    s = {"topics": ["方所"], "sentiment": "neutral", "negative_rate": 0.0, "risk_events": 0,
         "circle": "都市高净值", "hotspot": "", "volume_notes": 30}
    idea = generate_ideas("广州太古汇", "商业地产", s, 1, seed=7)["ideas"][0]
    cv = adapt_idea(idea, "client")
    av = adapt_idea(idea, "agency")
    vv = adapt_idea(idea, "vendor")
    # 创意本体一致
    assert cv["big_idea"] == av["big_idea"] == vv["big_idea"] == idea["big_idea"]
    # 三方话术不同且各有侧重
    assert "生意" in cv["perspective"]["audience_pitch"] or "回报" in cv["perspective"]["audience_pitch"]
    assert "比稿" in av["perspective"]["audience_pitch"] or "创意" in av["perspective"]["audience_pitch"]
    assert "资源" in vv["perspective"]["audience_pitch"] or "执行" in vv["perspective"]["audience_pitch"]
    assert cv["role"] == "甲方" and av["role"] == "乙方" and vv["role"] == "丙方"


def test_adapt_plan_default_agency():
    """默认视角为乙方（代理商）——比稿场景最常用。"""
    plan = generate_plan("测试品牌", "通用")
    v = adapt_plan(plan)
    assert v["role"] == "乙方"
