"""
品牌分析报告生成器（V3.0 P1.4 品牌分析报告升级）
归属：Z-Brand Core / ZBMP / 品牌智能层
目标：
  1. 从传统舆情报告升级为品牌传播与市场情报报告
  2. 整合品牌传播分析、市场情报分析、舆情分析、事件关系图谱
  3. 生成结构化、可操作的品牌分析报告

报告结构（V3.0 升级后）：
  1. 执行摘要（Executive Summary）
     - 核心发现
     - 关键指标
     - 行动建议
  2. 品牌传播分析（Brand Communication Analysis）
     - 传播主体分布（官方/KOS/KOL/KOC/普通用户/媒体/机构）
     - 传播渠道分析
     - 传播效果评估（曝光、互动、转化）
     - 内容类型分布
  3. 市场情报分析（Market Intelligence）
     - 竞品动态
     - 行业趋势
     - 市场机会与威胁
  4. 舆情分析（Public Opinion Analysis）
     - 情感分布（正面/负面/中性）
     - 热点话题
     - 关键意见领袖
     - 风险预警
  5. 事件关系图谱（Event Relation Graph）
     - 营销事件
     - 传播事件
     - 舆情事件
     - 事件关系链
  6. 建议与行动方案（Recommendations & Action Plan）
     - 短期行动（1-2周）
     - 中期策略（1-3月）
     - 长期规划（3-12月）

设计原则（V3.0 基线要求）：
  - 数据驱动：所有结论基于真实数据，不编造
  - 结构化：报告结构清晰，便于阅读和决策
  - 可操作：每个分析都有对应的建议和行动方案
  - 可追溯：数据来源可追溯，支持验证
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class BrandReportGenerator:
    """品牌分析报告生成器"""

    def __init__(self, brand_name: str = 'Z-Brand', report_period: str = ''):
        self.brand_name = brand_name
        self.report_period = report_period or f"{datetime.now().strftime('%Y年%m月')}"
        self.report_id = f"BR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 报告各部分数据
        self.executive_summary = {}
        self.communication_analysis = {}
        self.market_intelligence = {}
        self.public_opinion_analysis = {}
        self.event_graph_analysis = {}
        self.recommendations = {}

    def set_executive_summary(self, core_findings: List[str], key_metrics: Dict[str, Any],
                               action_items: List[str]):
        """设置执行摘要"""
        self.executive_summary = {
            'core_findings': core_findings,
            'key_metrics': key_metrics,
            'action_items': action_items,
        }

    def set_communication_analysis(self, subject_distribution: Dict[str, int],
                                     channel_analysis: Dict[str, Any],
                                     effect_evaluation: Dict[str, Any],
                                     content_type_distribution: Dict[str, int]):
        """设置品牌传播分析"""
        self.communication_analysis = {
            'subject_distribution': subject_distribution,
            'channel_analysis': channel_analysis,
            'effect_evaluation': effect_evaluation,
            'content_type_distribution': content_type_distribution,
        }

    def set_market_intelligence(self, competitor_updates: List[Dict[str, Any]],
                                  industry_trends: List[str],
                                  opportunities: List[str], threats: List[str]):
        """设置市场情报分析"""
        self.market_intelligence = {
            'competitor_updates': competitor_updates,
            'industry_trends': industry_trends,
            'opportunities': opportunities,
            'threats': threats,
        }

    def set_public_opinion_analysis(self, sentiment_distribution: Dict[str, int],
                                      hot_topics: List[Dict[str, Any]],
                                      key_influencers: List[Dict[str, Any]],
                                      risk_warnings: List[str]):
        """设置舆情分析"""
        self.public_opinion_analysis = {
            'sentiment_distribution': sentiment_distribution,
            'hot_topics': hot_topics,
            'key_influencers': key_influencers,
            'risk_warnings': risk_warnings,
        }

    def set_event_graph_analysis(self, marketing_events: List[Dict[str, Any]],
                                   propagation_events: List[Dict[str, Any]],
                                   opinion_events: List[Dict[str, Any]],
                                   event_chains: List[Dict[str, Any]]):
        """设置事件关系图谱分析"""
        self.event_graph_analysis = {
            'marketing_events': marketing_events,
            'propagation_events': propagation_events,
            'opinion_events': opinion_events,
            'event_chains': event_chains,
        }

    def set_recommendations(self, short_term: List[str], medium_term: List[str],
                             long_term: List[str]):
        """设置建议与行动方案"""
        self.recommendations = {
            'short_term': short_term,
            'medium_term': medium_term,
            'long_term': long_term,
        }

    def generate_report(self) -> Dict[str, Any]:
        """生成完整报告"""
        return {
            'report_id': self.report_id,
            'brand_name': self.brand_name,
            'report_period': self.report_period,
            'generated_at': self.generated_at,
            'report_version': 'v3.0',
            'report_type': '品牌传播与市场情报报告',
            'executive_summary': self.executive_summary,
            'communication_analysis': self.communication_analysis,
            'market_intelligence': self.market_intelligence,
            'public_opinion_analysis': self.public_opinion_analysis,
            'event_graph_analysis': self.event_graph_analysis,
            'recommendations': self.recommendations,
        }

    def export_json(self, filepath: str) -> bool:
        """导出为JSON"""
        try:
            report = self.generate_report()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def export_markdown(self, filepath: str) -> bool:
        """导出为Markdown"""
        try:
            report = self.generate_report()
            md = self._to_markdown(report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md)
            return True
        except Exception:
            return False

    def _to_markdown(self, report: Dict[str, Any]) -> str:
        """转换为Markdown格式"""
        lines = []
        lines.append(f"# {report['brand_name']} 品牌传播与市场情报报告")
        lines.append(f"")
        lines.append(f"- **报告ID**: {report['report_id']}")
        lines.append(f"- **报告周期**: {report['report_period']}")
        lines.append(f"- **生成时间**: {report['generated_at']}")
        lines.append(f"- **报告版本**: {report['report_version']}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # 执行摘要
        es = report.get('executive_summary', {})
        if es:
            lines.append(f"## 1. 执行摘要")
            lines.append(f"")
            if es.get('core_findings'):
                lines.append(f"### 核心发现")
                for finding in es['core_findings']:
                    lines.append(f"- {finding}")
                lines.append(f"")
            if es.get('key_metrics'):
                lines.append(f"### 关键指标")
                for key, value in es['key_metrics'].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append(f"")
            if es.get('action_items'):
                lines.append(f"### 行动建议")
                for item in es['action_items']:
                    lines.append(f"- {item}")
                lines.append(f"")

        # 品牌传播分析
        ca = report.get('communication_analysis', {})
        if ca:
            lines.append(f"## 2. 品牌传播分析")
            lines.append(f"")
            if ca.get('subject_distribution'):
                lines.append(f"### 传播主体分布")
                for subject, count in ca['subject_distribution'].items():
                    lines.append(f"- {subject}: {count}")
                lines.append(f"")
            if ca.get('effect_evaluation'):
                lines.append(f"### 传播效果评估")
                for key, value in ca['effect_evaluation'].items():
                    lines.append(f"- **{key}**: {value}")
                lines.append(f"")

        # 市场情报分析
        mi = report.get('market_intelligence', {})
        if mi:
            lines.append(f"## 3. 市场情报分析")
            lines.append(f"")
            if mi.get('industry_trends'):
                lines.append(f"### 行业趋势")
                for trend in mi['industry_trends']:
                    lines.append(f"- {trend}")
                lines.append(f"")
            if mi.get('opportunities'):
                lines.append(f"### 市场机会")
                for opp in mi['opportunities']:
                    lines.append(f"- {opp}")
                lines.append(f"")
            if mi.get('threats'):
                lines.append(f"### 市场威胁")
                for threat in mi['threats']:
                    lines.append(f"- {threat}")
                lines.append(f"")

        # 舆情分析
        po = report.get('public_opinion_analysis', {})
        if po:
            lines.append(f"## 4. 舆情分析")
            lines.append(f"")
            if po.get('sentiment_distribution'):
                lines.append(f"### 情感分布")
                for sentiment, count in po['sentiment_distribution'].items():
                    lines.append(f"- {sentiment}: {count}")
                lines.append(f"")
            if po.get('risk_warnings'):
                lines.append(f"### 风险预警")
                for warning in po['risk_warnings']:
                    lines.append(f"- ⚠️ {warning}")
                lines.append(f"")

        # 事件关系图谱
        eg = report.get('event_graph_analysis', {})
        if eg:
            lines.append(f"## 5. 事件关系图谱")
            lines.append(f"")
            if eg.get('marketing_events'):
                lines.append(f"### 营销事件")
                for event in eg['marketing_events']:
                    lines.append(f"- **{event.get('title', '')}**: {event.get('description', '')}")
                lines.append(f"")
            if eg.get('event_chains'):
                lines.append(f"### 事件关系链")
                for chain in eg['event_chains']:
                    lines.append(f"- {chain.get('description', '')}")
                lines.append(f"")

        # 建议与行动方案
        rec = report.get('recommendations', {})
        if rec:
            lines.append(f"## 6. 建议与行动方案")
            lines.append(f"")
            if rec.get('short_term'):
                lines.append(f"### 短期行动（1-2周）")
                for item in rec['short_term']:
                    lines.append(f"- {item}")
                lines.append(f"")
            if rec.get('medium_term'):
                lines.append(f"### 中期策略（1-3月）")
                for item in rec['medium_term']:
                    lines.append(f"- {item}")
                lines.append(f"")
            if rec.get('long_term'):
                lines.append(f"### 长期规划（3-12月）")
                for item in rec['long_term']:
                    lines.append(f"- {item}")
                lines.append(f"")

        lines.append(f"---")
        lines.append(f"*本报告由序境 品牌智能系统自动生成，数据来源可追溯。*")

        return '\n'.join(lines)


# 全局单例
_generator_instance: Optional[BrandReportGenerator] = None

def get_report_generator(brand_name: str = 'Z-Brand', report_period: str = '') -> BrandReportGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = BrandReportGenerator(brand_name, report_period)
    return _generator_instance
