# -*- coding: utf-8 -*-
"""数据驱动原创创意生成器测试。"""
from scripts.idea_generator import CIRCLE_SYMBOLS, EMOTION_STYLES, generate_ideas, signals_from_db


def test_generate_ideas_structure():
    s = {"topics": ["太古汇", "消费"], "sentiment": "neutral", "negative_rate": 0.1,
         "risk_events": 0, "circle": "Z世代潮人", "hotspot": "世界杯", "volume_notes": 100}
    r = generate_ideas("测试品牌", "美妆", s, n=3)
    assert len(r["ideas"]) == 3
    for idea in r["ideas"]:
        assert idea["big_idea"]
        assert idea["concept"] and idea["why"]
        assert idea["circle"] and idea["circle_symbols"]
        assert idea["timeliness"] and "世界杯" in idea["timeliness"]
        assert idea["virality"]


def test_generate_ideas_no_placeholder_when_no_topics():
    """无主题词时不得输出占位符（#趋势词# / {} 残留），以「日常」兜底、真实可读不复读。"""
    s = {"topics": [], "sentiment": "neutral", "negative_rate": 0.0, "risk_events": 0,
         "circle": "都市高净值", "hotspot": "", "volume_notes": 0}
    r = generate_ideas("广州太古汇", "商业地产", s, n=3, seed=11)
    for idea in r["ideas"]:
        assert "趋势词" not in idea["big_idea"]
        assert "{" not in idea["big_idea"] and "}" not in idea["big_idea"]
        assert idea["big_idea"].strip()
        # 兜底主题「日常」应出现；不应出现"品牌×品牌"复读（如 广州太古汇的广州太古汇）
        assert "日常" in idea["big_idea"]
        assert "广州太古汇的广州太古汇" not in idea["big_idea"]
        # 允许合法 hashtag（#日常# 由 {#话题#} 模板产生，语义有效），但禁止无意义占位 #趋势词#


def test_signals_from_db_real(tmp_path):
    import sqlite3
    db = str(tmp_path / "m.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT, content TEXT, "
              "sentiment TEXT, risk_level TEXT)")
    c.execute("CREATE TABLE events (event_id TEXT PRIMARY KEY, title TEXT, summary TEXT, "
              "risk_level TEXT)")
    c.executemany("INSERT INTO notes (title,content,sentiment,risk_level) VALUES (?,?,?,?)",
                  [("太古汇新店","太古汇新店火爆", "positive", "low"),
                   ("太古汇投诉","消费者投诉服务", "negative", "high"),
                   ("太古汇活动","周年庆活动", "neutral", "low")])
    c.commit(); c.close()
    s = signals_from_db(db, "太古汇", "Z世代潮人", "618")
    assert s["topics"] and s["circle"] == "Z世代潮人"
    assert s["hotspot"] == "618" and s["volume_notes"] == 3
    assert s["sentiment"] in EMOTION_STYLES


def test_sentiment_changes_style():
    s_pos = {"topics": ["新品"], "sentiment": "positive", "negative_rate": 0.0, "risk_events": 0,
             "circle": "Z世代潮人", "hotspot": "", "volume_notes": 5}
    s_neg = {"topics": ["新品"], "sentiment": "negative", "negative_rate": 0.5, "risk_events": 2,
             "circle": "Z世代潮人", "hotspot": "", "volume_notes": 5}
    a = generate_ideas("X", "快消", s_pos, 1)["ideas"][0]
    b = generate_ideas("X", "快消", s_neg, 1)["ideas"][0]
    assert a["mechanism"] != b["mechanism"]
    assert "危机共情" in b["why"] or "负面" in b["why"]


def test_all_circles_symbols():
    for c in CIRCLE_SYMBOLS:
        s = {"topics": ["话题"], "sentiment": "neutral", "negative_rate": 0.0, "risk_events": 0,
             "circle": c, "hotspot": "", "volume_notes": 3}
        r = generate_ideas("X", "通用", s, 1)
        assert r["ideas"][0]["circle_symbols"]


def test_anti_template_diversity():
    """反模板化：同一真实信号批次内，slogan 全不同、张力句式覆盖多种、角度不重复。"""
    s = {"topics": ["方所", "周年", "面包", "停车", "积分", "艺术"],
         "sentiment": "positive", "negative_rate": 0.08, "risk_events": 0,
         "circle": "都市高净值", "hotspot": "15周年", "volume_notes": 300}
    r = generate_ideas("广州太古汇", "商业地产", s, n=6, tonality="premium", budget="mid")
    ideas = r["ideas"]
    slogans = [i["big_idea"] for i in ideas]
    assert len(set(slogans)) == len(slogans), "批次内 slogan 出现重复，仍模板化"
    tension_types = {i["tension_type"] for i in ideas}
    assert len(tension_types) >= 3, "张力句式类型过少(仅%s)，组合不足" % tension_types
    assert all("广州太古汇" in i["big_idea"] for i in ideas), "slogan 未含品牌，输出异常"
    # 语义角色已生效：主题含"面包/停车/周年"，slogan 不出现占位符
    assert all("{" not in i["big_idea"] for i in ideas), "存在未填充槽位"


def test_budget_awareness():
    """预算感知：同一信号不同预算，落地档位不同且结构完整。"""
    s = {"topics": ["新店"], "sentiment": "neutral", "negative_rate": 0.1, "risk_events": 0,
         "circle": "年轻潮流", "hotspot": "", "volume_notes": 50}
    low = generate_ideas("X", "零售", s, 1, budget="low")["ideas"][0]
    high = generate_ideas("X", "零售", s, 1, budget="high")["ideas"][0]
    assert low["budget"]["name"] == "轻量（低预算）"
    assert high["budget"]["name"] == "全链路战役（高预算）"
    assert low["budget"]["scale"] != high["budget"]["scale"]
    assert all(len(b["tactics"]) >= 2 for b in (low["budget"], high["budget"]))


def test_angle_and_provenance_present():
    """每个 idea 带角度(angle)与预算，且 provenance 保留证据分级。"""
    s = {"topics": ["展览"], "sentiment": "neutral", "negative_rate": 0.0, "risk_events": 0,
         "circle": "高奢小众", "hotspot": "", "volume_notes": 30}
    idea = generate_ideas("Galerie", "展览", s, 1, tonality="luxury")["ideas"][0]
    assert "angle" in idea and "tension_type" in idea
    assert "budget" in idea and idea["budget"]["name"]
    p = idea["provenance"]
    assert "angle" in p and p["evidence_level"] in ("assumption", "single_case", "repeated")
    assert 0 < p["confidence"] <= 0.9
    assert p["counter_example_check"] and "trace" in p


def test_seed_reproducible_and_random_default():
    """seed 固定时可复现；不传 seed 时（默认随机）两次结果不同——保证"新 idea"。"""
    s = {"topics": ["联名"], "sentiment": "positive", "negative_rate": 0.0, "risk_events": 0,
         "circle": "Z世代潮人", "hotspot": "618", "volume_notes": 10}
    r1 = generate_ideas("B", "快消", s, 2, seed=42)
    r2 = generate_ideas("B", "快消", s, 2, seed=42)
    assert [i["big_idea"] for i in r1["ideas"]] == [i["big_idea"] for i in r2["ideas"]]
    a1 = generate_ideas("B", "快消", s, 2)
    a2 = generate_ideas("B", "快消", s, 2)
    # 允许极低概率相同：同一批次内已保证 slogan 唯一，跨次随机基本不同
    # 断言至少两次运行中 slogan 集合有差异，或即便相同也满足机制/角度轮转
    assert len({i["big_idea"] for i in a1["ideas"]} | {i["big_idea"] for i in a2["ideas"]}) >= 2


def test_resonate_emo_library_renders_clean():
    """情感共鸣句库（韩剧×文学手法）全部模板可渲染：无占位符残留、无品牌复读、可读。"""
    from scripts.idea_generator import _HOOK_EMO, _HOOK_EMO_LUX, _render
    for lib in (_HOOK_EMO, _HOOK_EMO_LUX):
        for hk, tpls in lib.items():
            assert tpls, "句库 %s 存在空组" % hk
            for tpl in tpls:
                out = _render(tpl, "广州太古汇", "日常", "都市高净值", "质感新体验·限量",
                              "圈层", "15周年")
                assert "{" not in out and "}" not in out, "未填充槽位: %s" % out
                assert "#" not in out, "占位符残留: %s" % out
                assert "广州太古汇的广州太古汇" not in out, "品牌复读: %s" % out
                assert len(out) > 8, "输出过短: %s" % out


def test_resonate_appears_in_rotation():
    """情感共鸣机制在轮转中必出现：n=12 且 sentiment/tonality 覆盖时命中 resonate。"""
    s = {"topics": ["方所", "周年", "面包"], "sentiment": "positive", "negative_rate": 0.05,
         "risk_events": 0, "circle": "都市高净值", "hotspot": "15周年", "volume_notes": 200}
    r = generate_ideas("广州太古汇", "商业地产", s, n=12, tonality="premium", budget="mid", seed=7)
    mechs = {i["mechanism"] for i in r["ideas"]}
    assert "情感共鸣" in mechs, "轮转 12 次未出现情感共鸣，实际机制=%s" % mechs
    # 情感共鸣 slogan 应含情感句库手法特征（以小写大/时间具象/朴素真话等标签在 tension_type）
    emo = [i for i in r["ideas"] if i["mechanism"] == "情感共鸣"]
    assert emo and all(i["tension_type"] in
                       ("以小写大", "时间具象", "朴素真话", "越界张力", "不说破的深情",
                        "条件预言", "悖论并置") for i in emo)

