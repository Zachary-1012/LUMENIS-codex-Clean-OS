"""
v4_upgrade.report_center 标准化报告中心
======================================
CTH太古汇专属 + ZBMP通用品牌 两套话术
日报/周报/月报/年报/专项报告
Word & PDF 导出

模块：
- standard_taxonomy: 标准化分类体系（事件类型/风险等级/情感/传播主体/报告周期）
- cth_phrases: 太古汇专属话术库（基于运营SOP提取）
- zbmp_phrases: 通用品牌话术库（多行业适配）
- report_generator: 标准化报告生成器
- word_pdf_export: Word/PDF导出器

用法：
    from v4_upgrade.report_center import ReportGenerator, ReportExporter

    # 生成CTH日报
    gen = ReportGenerator(brand_mode="cth")
    report = gen.generate("daily")

    # 导出Word和PDF
    exporter = ReportExporter()
    result = exporter.generate_and_export(brand_mode="cth", period="daily")
    print(result["word_path"], result["pdf_path"])
"""
from .standard_taxonomy import (
    EventType, RiskLevel, Sentiment, SubjectType, ReportPeriod, FactStatus,
    StandardizedEvent, StandardizedNote,
    classify_risk_level, classify_sentiment, classify_subject,
)
from .report_generator import ReportGenerator
from .word_pdf_export import ReportExporter

__all__ = [
    "EventType", "RiskLevel", "Sentiment", "SubjectType", "ReportPeriod", "FactStatus",
    "StandardizedEvent", "StandardizedNote",
    "classify_risk_level", "classify_sentiment", "classify_subject",
    "ReportGenerator", "ReportExporter",
]
