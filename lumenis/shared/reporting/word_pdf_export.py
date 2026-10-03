"""
Word / PDF 报告导出模块
========================
将标准化报告数据导出为Word(.docx)和PDF文件
支持 CTH / 序境·商业运营与 BMP / 序境·品牌市场模板

依赖：python-docx（Word）、docx2pdf或reportlab（PDF）
"""
import os
from datetime import datetime
from typing import Optional

from .report_generator import ReportGenerator
from .standard_taxonomy import RiskLevel, Sentiment


class ReportExporter:
    """报告导出器"""

    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def export_saved_document(document: dict, *, sources: list, format: str) -> bytes:
        """Export the complete saved snapshot in memory, including source lineage.

        Uses the existing Reporting exporter dependencies. A missing converter
        raises an error; a requested PDF never returns a Word file. No output
        directory or database is created by this method.
        """
        import io
        import json
        snapshot = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
        sections = [document["title"], document["markdown"],
                    "Sources / original scope / rights", json.dumps(sources, ensure_ascii=False, indent=2),
                    "Complete saved snapshot", snapshot]
        output = io.BytesIO()
        if format == "docx":
            from docx import Document
            doc = Document()
            for section in sections:
                for line in section.splitlines():
                    doc.add_paragraph(line)
            doc.save(output)
        elif format == "pdf":
            from html import escape
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            style = ParagraphStyle("SavedWork", fontName="STSong-Light", fontSize=9,
                                   leading=13, wordWrap="CJK")
            story = []
            for section in sections:
                for line in section.splitlines():
                    story.append(Paragraph(escape(line) or "&#160;", style))
                story.append(Spacer(1, 12))
            SimpleDocTemplate(output, pagesize=A4).build(story)
        elif format == "xlsx":
            from openpyxl import Workbook
            book = Workbook()
            sheet = book.active
            sheet.title = "Saved snapshot"
            for label, section in zip(("Title", "Report", "Lineage", "Sources", "Snapshot", "JSON"), sections):
                # Excel cells truncate at 32767 characters. Preserve every
                # character in ordered chunks, and force text to avoid formulas.
                for index, start in enumerate(range(0, len(section), 30000), 1):
                    sheet.append([label, index, section[start:start + 30000]])
                    sheet.cell(sheet.max_row, 3).data_type = "s"
            book.save(output)
        else:
            raise ValueError("unsupported saved document export format")
        return output.getvalue()

    def export_word(self, report: dict, filename: str = None) -> str:
        """导出为Word文档"""
        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            return ""

        doc = Document()

        # 设置默认字体
        style = doc.styles["Normal"]
        style.font.name = "微软雅黑"
        style.font.size = Pt(10.5)

        # 标题
        brand_name = report.get("brand_name", "品牌")
        period_label = report.get("period_label", "报告")
        title = doc.add_heading(f"{brand_name} {period_label}", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 报告信息
        info = doc.add_paragraph()
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        info.add_run(f"报告周期：{report.get('start_date', '')} 至 {report.get('end_date', '')}\n").font.size = Pt(9)
        info.add_run(f"生成时间：{report.get('generated_at', '')}\n").font.size = Pt(9)
        info.add_run(f"报告ID：{report.get('report_id', '')}").font.size = Pt(9)

        doc.add_paragraph()  # 空行

        # 1. 执行摘要
        doc.add_heading("一、执行摘要", level=1)
        p = doc.add_paragraph()
        p.add_run(report.get("executive_summary", "")).bold = True

        # 2. 关键指标
        doc.add_heading("二、关键指标", level=1)
        metrics = report.get("key_metrics", [])
        table = doc.add_table(rows=1, cols=3)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "指标"
        hdr[1].text = "数值"
        hdr[2].text = "单位"
        for m in metrics:
            row = table.add_row().cells
            row[0].text = m.get("name", "")
            row[1].text = str(m.get("value", ""))
            row[2].text = m.get("unit", "")

        # 3. 风险事件
        doc.add_heading("三、风险事件", level=1)
        risk_events = report.get("risk_events", [])
        if not risk_events:
            doc.add_paragraph("本周期无风险事件。")
        for evt in risk_events:
            p = doc.add_paragraph()
            risk_label = evt.get("risk_label", evt.get("risk_level", ""))
            run = p.add_run(f"【{risk_label}】{evt.get('title', '')}")
            run.bold = True
            if evt.get("risk_level") in ("critical", "high"):
                run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
            doc.add_paragraph(f"风险指数：{evt.get('risk_score', 0)} | 提及数：{evt.get('mention_count', 0)} | 来源数：{evt.get('source_count', 1)}")
            doc.add_paragraph(f"预警：{evt.get('alert_message', '')}")
            doc.add_paragraph()

        # 4. 情感分析
        doc.add_heading("四、情感分析", level=1)
        sentiment = report.get("sentiment_analysis", {})
        dist = sentiment.get("distribution", {})
        doc.add_paragraph(
            f"整体情感：{sentiment.get('overall_label', '')} | "
            f"正面{dist.get('positive', 0)}条（{dist.get('positive_ratio', 0)}%） | "
            f"负面{dist.get('negative', 0)}条（{dist.get('negative_ratio', 0)}%） | "
            f"中性{dist.get('neutral', 0)}条"
        )

        # 5. 传播分析
        doc.add_heading("五、传播分析", level=1)
        prop = report.get("propagation_analysis", {})
        doc.add_paragraph(f"互动水平：{prop.get('engagement_level', '')} | 总互动量：{prop.get('total_engagement', 0)}")
        top_notes = prop.get("top_notes", [])
        if top_notes:
            doc.add_paragraph("热门笔记Top5：")
            for i, n in enumerate(top_notes, 1):
                doc.add_paragraph(
                    f"{i}. {n.get('title', '')}（{n.get('author', '')}）"
                    f" - 互动{n.get('engagement', 0)} - {n.get('sentiment', '')}",
                    style="List Bullet"
                )

        # 6. 关键洞察
        doc.add_heading("六、关键洞察", level=1)
        for ins in report.get("key_insights", []):
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(f"[{ins.get('type', '')}] {ins.get('insight', '')}")
            if ins.get("metric"):
                p.add_run(f"（{ins['metric']}）").font.size = Pt(9)

        # 7. 行动建议
        doc.add_heading("七、行动建议", level=1)
        for act in report.get("action_items", []):
            p = doc.add_paragraph()
            priority = act.get("priority", "")
            run = p.add_run(f"【{priority}】")
            if priority == "紧急":
                run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
                run.bold = True
            p.add_run(f"{act.get('action', '')}")
            p_owner = doc.add_paragraph(f"负责：{act.get('owner', '')} | 时限：{act.get('deadline', '')}")
            p_owner.runs[0].font.size = Pt(9)

        # 8. 数据质量
        doc.add_heading("八、数据质量", level=1)
        dq = report.get("data_quality", {})
        doc.add_paragraph(
            f"采集总数：{dq.get('total_collected', 0)}条 | "
            f"质量评分：{dq.get('quality_score', 0)}/100 | "
            f"采集完整：{'是' if dq.get('collection_complete') else '否'}"
        )
        for w in dq.get("warnings", []):
            if w:
                doc.add_paragraph(f"⚠️ {w}", style="List Bullet")

        # 9. CTH专属（如果有）
        if "cth_specific" in report:
            doc.add_heading("九、太古汇专属分析", level=1)
            cth = report["cth_specific"]
            tone = cth.get("tone_evaluation", {})
            doc.add_paragraph(
                f"调性匹配：{tone.get('overall', '')} | "
                f"温暖{tone.get('warm_ratio', 0)}% | 精致{tone.get('refined_ratio', 0)}% | 仪式感{tone.get('ritual_ratio', 0)}%"
            )
            nodes = cth.get("active_activity_nodes", [])
            if nodes:
                doc.add_paragraph("当前活动节点：")
                for n in nodes:
                    doc.add_paragraph(f"{n.get('name', '')}（{n.get('month', '')}）- {n.get('tone', '')}", style="List Bullet")

        # 页脚
        doc.add_paragraph()
        footer = doc.add_paragraph()
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run(
            f"本报告由 {'LUMENIS Commerce Operations (CTH)' if report.get('brand_mode') == 'cth' else 'LUMENIS Brand & Market (BMP)'} 自动生成 | "
            f"数据来源可追溯 | {datetime.now().strftime('%Y-%m-%d')}"
        ).font.size = Pt(8)

        # 保存
        if not filename:
            brand = brand_name.replace(" ", "_")
            period = report.get("period", "report")
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{brand}_{period}_{date_str}.docx"

        filepath = os.path.join(self.output_dir, filename)
        doc.save(filepath)
        return filepath

    def export_pdf(self, report: dict, filename: str = None) -> str:
        """
        导出为PDF
        优先用docx2pdf（需要Word），回退用reportlab
        """
        # 先生成Word
        word_path = self.export_word(report, filename.replace(".pdf", ".docx") if filename else None)
        if not word_path:
            return ""

        # 尝试docx2pdf
        try:
            from docx2pdf import convert
            pdf_path = word_path.replace(".docx", ".pdf")
            convert(word_path, pdf_path)
            return pdf_path
        except Exception:
            pass

        # 回退：用reportlab生成简单PDF
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
            from reportlab.lib.units import cm

            if not filename:
                brand = report.get("brand_name", "report").replace(" ", "_")
                period = report.get("period", "report")
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{brand}_{period}_{date_str}.pdf"

            pdf_path = os.path.join(self.output_dir, filename)
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph(f"{report.get('brand_name', '')} {report.get('period_label', '')}", styles["Title"]))
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph(f"周期：{report.get('start_date', '')} 至 {report.get('end_date', '')}", styles["Normal"]))
            story.append(Paragraph(f"生成：{report.get('generated_at', '')}", styles["Normal"]))
            story.append(Spacer(1, 0.5 * cm))

            story.append(Paragraph("执行摘要", styles["Heading2"]))
            story.append(Paragraph(report.get("executive_summary", ""), styles["Normal"]))
            story.append(Spacer(1, 0.3 * cm))

            story.append(Paragraph("关键指标", styles["Heading2"]))
            metric_data = [["指标", "数值", "单位"]]
            for m in report.get("key_metrics", []):
                metric_data.append([m.get("name", ""), str(m.get("value", "")), m.get("unit", "")])
            story.append(Table(metric_data))
            story.append(Spacer(1, 0.3 * cm))

            story.append(Paragraph("风险事件", styles["Heading2"]))
            for evt in report.get("risk_events", []):
                story.append(Paragraph(
                    f"【{evt.get('risk_label', '')}】{evt.get('title', '')} - 风险指数{evt.get('risk_score', 0)}",
                    styles["Normal"]
                ))
            story.append(Spacer(1, 0.3 * cm))

            story.append(Paragraph("行动建议", styles["Heading2"]))
            for act in report.get("action_items", []):
                story.append(Paragraph(
                    f"【{act.get('priority', '')}】{act.get('action', '')}（{act.get('owner', '')}，{act.get('deadline', '')}）",
                    styles["Normal"]
                ))

            doc.build(story)
            return pdf_path
        except Exception as e:
            print(f"PDF导出失败: {e}")
            return word_path  # 返回Word路径作为兜底

    def generate_and_export(self, brand_mode: str = "cth", period: str = "daily",
                            start_date: str = None, end_date: str = None,
                            export_formats: list = None, brand_config: dict = None) -> dict:
        """
        一键生成并导出报告

        Args:
            brand_mode: cth/zbmp
            period: daily/weekly/monthly/yearly/event
            export_formats: ["word", "pdf"]，默认两者都导出
            brand_config: BMP 模式品牌配置

        Returns:
            {"report": 报告数据, "word_path": ..., "pdf_path": ...}
        """
        if export_formats is None:
            export_formats = ["word", "pdf"]

        generator = ReportGenerator(brand_mode=brand_mode, brand_config=brand_config)
        report = generator.generate(period, start_date, end_date)

        result = {"report": report, "word_path": "", "pdf_path": ""}

        if "word" in export_formats:
            result["word_path"] = self.export_word(report)
        if "pdf" in export_formats:
            result["pdf_path"] = self.export_pdf(report)

        return result
