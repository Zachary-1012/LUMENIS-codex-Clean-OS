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
import uuid

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    _HAS_DOCX = True
except Exception:
    _HAS_DOCX = False

from scripts.pitch_parser import analyze_pitch

_ACCENT = RGBColor(0x2F, 0x3B, 0x66) if _HAS_DOCX else None
_SUB = RGBColor(0x6B, 0x72, 0x80) if _HAS_DOCX else None


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


def _save_new_document(doc, out_path, check_continue):
    """Stage and validate locally; publish a new file without replacing a revision."""
    from lumenis.shared.reporting.artifact import assert_artifact_or_raise

    destination = os.path.abspath(os.fspath(out_path)) if out_path else os.path.join(
        tempfile.gettempdir(), "pitch_%s.docx" % uuid.uuid4().hex)
    if not destination.lower().endswith(".docx"):
        raise ValueError("输出必须为 .docx 文件")
    if os.path.lexists(destination):
        raise FileExistsError("输出已存在，请为修订选择新文件")
    if check_continue:
        check_continue()
    fd, staged = tempfile.mkstemp(prefix=".pitch-stage-", suffix=".docx",
                                  dir=os.path.dirname(destination))
    try:
        with os.fdopen(fd, "wb") as stream:
            doc.save(stream)
            stream.flush()
            os.fsync(stream.fileno())
        # The shared verifier proves bytes/hash only; reopen also verifies OOXML.
        assert_artifact_or_raise(staged)
        Document(staged)
        if check_continue:
            check_continue()
        os.link(staged, destination)
        return destination
    finally:
        os.unlink(staged)


def _manuscript_document(manuscript):
    """Export supplied final prose. This function neither generates nor approves it."""
    if not isinstance(manuscript, dict):
        raise ValueError("成稿必须包含标题、说明和正文段落")
    title, summary = manuscript.get("title"), manuscript.get("summary")
    sections = manuscript.get("sections")
    if (not isinstance(title, str) or not title.strip()
            or not isinstance(summary, str) or not summary.strip()
            or not isinstance(sections, list) or not sections):
        raise ValueError("成稿标题、说明和正文不能为空")
    for section in sections:
        if (not isinstance(section, dict)
                or not isinstance(section.get("heading"), str)
                or not section["heading"].strip()
                or not isinstance(section.get("body"), str)
                or not section["body"].strip()):
            raise ValueError("每节成稿必须有标题和实际正文")
    authorship = manuscript.get("authorship", "assisted")
    labels = {
        "zh": {"assisted": "开发辅助原创草案 未获客户批准",
               "user_supplied": "用户提供的成稿 审阅及使用授权待确认"},
        "en": {"assisted": "Original draft prepared with development assistance. Client approval pending.",
               "user_supplied": "Supplied manuscript. Review and usage approval pending."},
        "ko": {"assisted": "개발 지원으로 작성한 독창적 초안 고객 승인 대기",
               "user_supplied": "제공된 원고 검토 및 사용 승인 대기"},
    }
    language = manuscript.get("language", "zh")
    if language not in labels:
        raise ValueError("成稿语言必须为 zh、en 或 ko")
    if authorship not in labels[language]:
        raise ValueError("成稿来源必须为 assisted 或 user_supplied")
    doc = Document()
    for name in ("Title", "Heading 1", "Normal"):
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_paragraph(title, style="Title")
    doc.add_paragraph(summary)
    doc.add_paragraph(labels[language][authorship])
    for section in sections:
        doc.add_heading(section["heading"], level=1)
        # Preserve blank paragraphs, line breaks and all authored words.
        for paragraph in section["body"].split("\n\n"):
            doc.add_paragraph(paragraph)
    doc.core_properties.title = title
    doc.core_properties.language = language
    doc.core_properties.comments = "authorship=%s; approval=not_verified" % authorship
    return doc


def export_pitch_docx(analysis, out_path=None, *, manuscript=None, check_continue=None):
    """导出需求分析或实际提供的成稿；新版本须新路径，不覆盖旧件。"""
    if not _HAS_DOCX:
        raise RuntimeError("python-docx 不可用，无法导出 Word")
    if not isinstance(analysis, dict):
        raise ValueError("需求分析必须为对象")
    if check_continue:
        check_continue()
    if manuscript is None:
        manuscript = analysis.get("manuscript")
    if manuscript is not None:
        return _save_new_document(_manuscript_document(manuscript), out_path, check_continue)
    ex = (analysis.get("extracted") or {})
    doc = Document()
    # 封面标题
    t = doc.add_heading("", level=0)
    r = t.add_run("%s · %s 方案拆解" % (ex.get("brand") or "品牌", ex.get("category") or "品类"))
    r.font.size = Pt(20)
    r.font.color.rgb = _ACCENT
    _p(doc, "本材料为需求分析和创意候选，不是完整提案成稿。历史对标尚未经本次核验。")
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

    return _save_new_document(doc, out_path, check_continue)


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
