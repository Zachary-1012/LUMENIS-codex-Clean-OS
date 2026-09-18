# -*- coding: utf-8 -*-
"""序境报告母模型测试（Decision Information First）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.shared.reporting.brand_report import BrandReportGenerator


def _gen_with_decision_model():
    g = BrandReportGenerator(brand_name="测试品牌", report_period="2026年9月")
    g.set_decision_model(
        problem_center={"question": "本周品牌舆情风险是否上升？", "context": "监测周期内出现多条负面信号"},
        events=[{"date": "2026-09-02", "subject": "某KOL", "title": "负面反馈事件",
                 "summary": "某KOL发布负面评价"}],
        impacts=[{"dimension": "品牌好感度", "direction": "down", "detail": "负面声量上升", "evidence_ids": ["EV-1"]}],
        risks=[{"level": "high", "topic": "负面扩散", "trigger": "KOL转发", "trend": "rising"}],
        evidence=[{"evidence_id": "EV-1", "kind": "note", "summary": "采集到负面笔记", "url": ""}],
        decisions={"short_term": ["24h内回应"], "medium_term": ["加强监测"], "long_term": ["建立KOL关系"]},
    )
    return g


def test_decision_model_full_structure():
    g = _gen_with_decision_model()
    rep = g.generate_report()
    assert "decision_model" in rep
    dm = rep["decision_model"]
    assert set(dm.keys()) >= {"problem_center", "events", "impacts", "risks", "evidence", "decisions"}
    assert dm["problem_center"]["question"].startswith("本周")
    assert len(dm["events"]) == 1
    assert dm["risks"][0]["level"] == "high"


def test_decision_model_empty_defaults():
    g = BrandReportGenerator()
    dm = g.generate_report()["decision_model"]
    # 未设置时为空 dict，不抛异常
    assert dm == {}


def test_decision_model_markdown_first_section():
    g = _gen_with_decision_model()
    g.set_executive_summary(["发现A"], {"指标": 1}, ["行动1"])
    md = g._to_markdown(g.generate_report())
    # 母模型章节在"执行摘要"之前（首屏决策信息）
    assert "问题中心（Decision Information First）" in md
    assert md.index("问题中心") < md.index("执行摘要")
    assert "核心问题" in md
    assert "关键事件" in md
    assert "影响" in md
    assert "风险" in md
    assert "证据" in md
    assert "建议" in md


def test_backward_compatible_v3():
    g = BrandReportGenerator()
    g.set_executive_summary(["发现A"], {"指标": 1}, ["行动1"])
    g.set_recommendations(["短期"], ["中期"], ["长期"])
    rep = g.generate_report()
    # v3.0 原有字段保留
    assert rep["executive_summary"]["core_findings"] == ["发现A"]
    assert rep["recommendations"]["short_term"] == ["短期"]
    assert rep["report_version"] == "v3.0"


def test_export_json_with_decision_model(tmp_path):
    g = _gen_with_decision_model()
    fp = str(tmp_path / "rep.json")
    assert g.export_json(fp)
    import json
    data = json.load(open(fp, encoding="utf-8"))
    assert "decision_model" in data


def test_report_trilingual_zh_en_ko():
    """序境中英韩：报告标题/母模型章节按 language 输出"""
    from lumenis.shared.reporting.brand_report import BrandReportGenerator
    expect = {
        "zh": "品牌传播与市场情报报告",
        "en": "Brand Communication & Market Intelligence Report",
        "ko": "브랜드 커뮤니케이션",
    }
    for lang, key in expect.items():
        g = BrandReportGenerator(brand_name="B", report_period="2026年9月", language=lang)
        g.set_decision_model(
            problem_center={"question": "Q"},
            events=[{"date": "2026-09-02", "subject": "S", "title": "T", "summary": "M"}],
            impacts=[{"dimension": "D", "direction": "down", "detail": "x"}],
            risks=[{"level": "high", "topic": "R", "trigger": "T", "trend": "rising"}],
            evidence=[{"evidence_id": "E1", "kind": "note", "summary": "s"}],
            decisions={"short_term": ["a"], "medium_term": [], "long_term": []},
        )
        rep = g.generate_report()
        assert rep["language"] == lang
        md = g._to_markdown(rep)
        assert key in md
        if lang != "zh":
            assert "问题中心" not in md  # 非中文时无中文章节标题
        else:
            assert "问题中心" in md


def test_report_language_default_zh():
    g = BrandReportGenerator()
    assert g.language == "zh"
    assert g.generate_report()["language"] == "zh"
    # 非法语言回退 zh
    g2 = BrandReportGenerator(language="xx")
    assert g2.language == "zh"
