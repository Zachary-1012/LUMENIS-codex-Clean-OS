# -*- coding: utf-8 -*-
"""方案需求拆解分析引擎测试。"""
import json
import os
from scripts.pitch_parser import (analyze_pitch, analyze_pitch_file, detect_category,
                                  detect_circle, detect_tonality, detect_channels,
                                  detect_goals, PITCH_TOC)


def test_analyze_pitch_full():
    text = ("我们想做一款高端小众香水品牌「岚序」，预算300万，目标人群是高净值贵妇和小众藏家，"
            "主要渠道小红书和私域，希望做新品上市和品牌建设，创意方向是东方节气与稀缺仪式感，"
            "可以比稿。")
    r = analyze_pitch(text, n_ideas=2)
    e = r["extracted"]
    assert e["category"] == "美妆个护"
    assert e["circle"] == "高奢小众"
    assert e["tonality"] == "luxury"
    assert "小红书" in e["channels"]
    assert set(e["goals"]) >= {"新品上市", "品牌建设"}
    assert e["budget"]["value"] == 300
    assert len(r["ideas"]["ideas"]) == 2
    # 高奢调性 → 不追热点叙事
    assert "不参与流量狂欢" in r["ideas"]["ideas"][0]["timeliness"] or \
           "不追热点" in r["ideas"]["ideas"][0]["timeliness"]
    assert len(r["pitch_toc"]) == 8
    assert r["pitch_toc"][0]["layer"] == "数据层"


def test_mass_tonality_differs():
    r1 = analyze_pitch("大众美妆品牌，预算50万，目标年轻女性，抖音小红书，爆款破圈", n_ideas=1)
    r2 = analyze_pitch("高奢珠宝品牌，预算1000万，目标高净值贵妇，私域，稀缺限量", n_ideas=1)
    assert r1["extracted"]["tonality"] != r2["extracted"]["tonality"]
    assert r1["ideas"]["ideas"][0]["tonality"] == "大众"
    assert r2["ideas"]["ideas"][0]["tonality"] == "高奢"


def test_pitch_file_formats(tmp_path):
    # md
    md = tmp_path / "req.md"
    md.write_text("餐饮品牌「拾味」，预算200万，目标都市白领，线下+抖音，做开业活动引爆", encoding="utf-8")
    r = analyze_pitch_file(str(md), n_ideas=1)
    assert r["source_file"] == str(md)
    assert r["extracted"]["category"] == "餐饮"
    # json
    jf = tmp_path / "req.json"
    jf.write_text(json.dumps({"brand": "岚序", "type": "香水", "budget": "300万"}, ensure_ascii=False),
                  encoding="utf-8")
    rj = analyze_pitch_file(str(jf), n_ideas=1)
    assert "美妆" in rj["extracted"]["category"]
    # csv
    cf = tmp_path / "req.csv"
    cf.write_text("字段,内容\n品牌,拾味\n品类,餐饮\n预算,200万\n", encoding="utf-8-sig")
    rc = analyze_pitch_file(str(cf), n_ideas=1)
    assert rc["extracted"]["category"] == "餐饮"


def test_detectors():
    assert detect_category("我们要做新能源汽车") == "汽车"
    assert detect_category("文旅景区门票活动") == "文旅"
    assert detect_circle("目标人群是宝妈和亲子家庭") == "母婴家庭"
    assert detect_tonality("顶奢限量稀缺") == "luxury"
    assert detect_channels("小红书+抖音+线下") == ["小红书", "抖音", "线下"]
    assert set(detect_goals("要破圈上热搜")) & {"声量传播"}
    assert len(PITCH_TOC) == 8


def test_pitch_has_marketing_field():
    """方案拆解返回营销节点适配（当月节点+情感主题+建议调性）。"""
    from scripts.pitch_parser import analyze_pitch
    r = analyze_pitch("广州太古汇 商业地产 15周年 预算200万 高净值 小红书 核心诉求提升到访", "广州太古汇", 2, "15周年")
    assert "marketing" in r, "缺 marketing 字段"
    m = r["marketing"]
    assert m is None or ("nodes" in m and "themes" in m and "tonality_advice" in m), m

def test_new_topic_roles_covered():
    """美妆/母婴/户外/酒饮 语义角色可识别并产出意象。"""
    from scripts.idea_generator import _topic_role
    assert _topic_role("面霜") == "beauty"
    assert _topic_role("亲子乐园") == "family"
    assert _topic_role("露营") == "sport"
    assert _topic_role("威士忌") == "wine"
