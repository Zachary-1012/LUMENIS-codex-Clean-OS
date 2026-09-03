# -*- coding: utf-8 -*-
"""方案拆解结果 → Word 文档导出（可交付比稿/提案材料）。

用法（CLI）：
  python scripts/pitch_export.py <analysis.json> <out.docx>
  python scripts/pitch_export.py --text "方案需求文本" --brand 广州太古汇 --hotspot 15周年 --out out.docx

依赖：python-docx（ZBC .venv 已装 1.2.0）。个人业务资料只存本地，本模块不联网、不上传。
"""
import json
import os
import sys
import tempfile

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    _HAS_DOCX = True
except Exception:
    _HAS_DOCX = False

from scripts.pitch_parser import analyze_pitch

_ACCENT = RGBColor(0x2F, 0x3B, 0x66)
_SUB = RGBColor(0x6B, 0x72, 0x80)


def _h(doc, text, size=14, color=_ACCENT, space=6):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = color
    p.paragraph_format.space_before = Pt(space)
    p.paragraph_format.space_after = Pt(2)
    return p


def _p(doc, text, size=10.5, bold=False, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(3)
    return p


def _kv_table(doc, rows):
    if not rows:
        return
    t = doc.add_table(rows=0, cols=2)
    t.style = "Light Grid Accent 1"
    for k, v in rows:
        cells = t.add_row().cells
        cells[0].text = str(k)
        cells[1].text = str(v) if v not in (None, "") else "—"


def export_pitch_docx(analysis, out_path=None):
    """把 analyze_pitch 返回结果导出为可交付 Word 文档。返回输出路径。"""
    if not _HAS_DOCX:
        raise RuntimeError("python-docx 不可用，无法导出 Word")
    ex = (analysis.get("extracted") or {})
    doc = Document()
    # 封面标题
    t = doc.add_heading("", level=0)
    r = t.add_run("%s · %s 方案拆解" % (ex.get("brand") or "品牌", ex.get("category") or "品类"))
    r.font.size = Pt(20)
    r.font.color.rgb = _ACCENT
    _p(doc, "调性 %s ｜ 圈层 %s ｜ 预算 %s ｜ 来源：Zachary Creative 方案拆解引擎"
       % (ex.get("tonality") or "—", ex.get("circle") or "—",
          ("%s%s" % (ex.get("budget", {}).get("value", ""), ex.get("budget", {}).get("unit", ""))) if ex.get("budget") else "—"),
       size=9, color=_SUB)

    # 一、需求要素
    _h(doc, "一、需求要素提取")
    _kv_table(doc, [
        ("品牌", ex.get("brand")), ("品类", ex.get("category")),
        ("预算", ("%s%s" % (ex.get("budget", {}).get("value", ""), ex.get("budget", {}).get("unit", ""))) if ex.get("budget") else "—"),
        ("圈层", ex.get("circle")), ("调性", ex.get("tonality")),
        ("渠道", "、".join(ex.get("channels") or []) or "—"),
        ("目标", "、".join(ex.get("goals") or []) or "—"),
        ("创意线索", "；".join(ex.get("creative_leads") or []) or "—"),
    ])

    # 二、对标基准
    bm = analysis.get("benchmark") or {}
    _h(doc, "二、对标基准")
    _kv_table(doc, [("对标对象", bm.get("benchmark")), ("打法", bm.get("playbook"))])

    # 三、创意方向
    ideas = (analysis.get("ideas") or {}).get("ideas") or []
    if ideas:
        _h(doc, "三、创意方向")
        for i, idea in enumerate(ideas, 1):
            _p(doc, "方向%d ｜ %s（%s）" % (i, idea.get("mechanism", ""), idea.get("tension_type", "")), bold=True)
            _p(doc, idea.get("big_idea", ""), size=12, bold=True)
            _kv_table(doc, [
                ("角度", idea.get("angle")), ("张力", idea.get("tension_type")),
                ("预算", idea.get("budget")), ("时效", idea.get("timeliness")),
                ("触点", "、".join(idea.get("touchpoints") or [])),
                ("信号/依据", idea.get("why")), ("来源", idea.get("provenance")),
            ])
    else:
        _h(doc, "三、创意方向", color=_SUB)
        _p(doc, "（未提取到创意方向）")

    # 四、方案脉络（PITCH_TOC 为 list[dict]）
    toc = analysis.get("pitch_toc") or []
    if toc:
        _h(doc, "四、方案脉络")
        for item in toc:
            if isinstance(item, dict):
                _p(doc, "• %s（%s）：%s" % (item.get("sec", ""), item.get("layer", ""), item.get("desc", "")), size=10)
            else:
                _p(doc, "• %s" % item, size=10)

    if not out_path:
        fd, out_path = tempfile.mkstemp(suffix=".docx", prefix="pitch_")
        os.close(fd)
    doc.save(out_path)
    return out_path


def main():
    import argparse
    ap = argparse.ArgumentParser(description="方案拆解结果导出 Word")
    ap.add_argument("analysis_json", nargs="?", default="", help="analyze_pitch 的 JSON 文件")
    ap.add_argument("out", nargs="?", default="", help="输出 docx 路径")
    ap.add_argument("--text", default="", help="或直接传方案需求文本")
    ap.add_argument("--brand", default="")
    ap.add_argument("--hotspot", default="")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    if a.analysis_json:
        analysis = json.load(open(a.analysis_json, encoding="utf-8"))
    else:
        analysis = analyze_pitch(a.text or "（空方案）", a.brand, a.n, a.hotspot)
    out = export_pitch_docx(analysis, a.out or None)
    print("导出完成: %s" % out)


if __name__ == "__main__":
    main()
