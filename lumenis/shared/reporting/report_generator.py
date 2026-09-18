"""
标准化报告生成器
================
支持CTH太古汇专属 + ZBMP通用品牌两套话术
支持日报/周报/月报/年报/专项报告
输出结构化数据，供Word/PDF导出使用

设计原则：
- 不改动现有daily_report.py/brand_report_generator.py，作为增强层
- 所有结论可追溯到原始数据
- 不把单一用户指控写成已证实事实
- 数据不完整时明确标注，不据空数据下结论
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .standard_taxonomy import (
    EventType, RiskLevel, Sentiment, SubjectType, ReportPeriod, FactStatus,
    classify_risk_level, classify_sentiment, classify_subject,
)
from . import cth_phrases
from . import zbmp_phrases


class ReportGenerator:
    """标准化报告生成器"""

    def __init__(self, brand_mode: str = "cth", brand_config: dict = None):
        """
        brand_mode: "cth"（太古汇专属）或 "zbmp"（通用品牌）
        brand_config: ZBMP模式下的品牌配置
        """
        self.brand_mode = brand_mode
        self.brand_config = brand_config or {}
        self.phrases = cth_phrases if brand_mode == "cth" else zbmp_phrases

    def generate(self, period: str, start_date: str = None, end_date: str = None,
                 notes: List[dict] = None, events: List[dict] = None,
                 stats: dict = None) -> dict:
        """
        生成标准化报告

        Args:
            period: daily/weekly/monthly/yearly/event
            start_date/end_date: 日期范围 YYYY-MM-DD
            notes: 笔记列表（可选，不传则从数据库获取）
            events: 事件列表（可选）
            stats: 统计数据（可选）

        Returns:
            结构化报告字典
        """
        period_enum = ReportPeriod(period)
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            days = period_enum.default_days
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # 获取数据（优先用传入的，否则从数据库获取）
        if notes is None:
            notes = self._get_notes_from_db(start_date, end_date)
        if events is None:
            events = self._get_events_from_db(start_date, end_date)
        if stats is None:
            stats = self._calculate_stats(notes, events)

        # 生成各部分
        report = {
            "report_id": f"{period.upper()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "brand_mode": self.brand_mode,
            "brand_name": self._get_brand_name(),
            "period": period,
            "period_label": period_enum.label,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "executive_summary": self._generate_executive_summary(stats, notes, events),
            "key_metrics": self._generate_key_metrics(stats),
            "risk_events": self._generate_risk_events(events, notes),
            "sentiment_analysis": self._generate_sentiment_analysis(notes),
            "propagation_analysis": self._generate_propagation_analysis(notes, events),
            "key_insights": self._generate_key_insights(notes, events, stats),
            "action_items": self._generate_action_items(events, stats),
            "data_quality": self._generate_data_quality(notes),
            "appendix": self._generate_appendix(notes, events),
        }

        if self.brand_mode == "cth":
            report["cth_specific"] = self._generate_cth_specific(notes, events, stats)
        else:
            report["zbmp_specific"] = self._generate_zbmp_specific(notes, events, stats)

        return report

    # ============ 数据获取 ============

    def _get_notes_from_db(self, start_date: str, end_date: str) -> List[dict]:
        """从数据库获取笔记（兼容现有database模块）"""
        try:
            import database as db
            notes = db.get_notes_by_date_range(start_date, end_date)
            return notes or []
        except Exception:
            return []

    def _get_events_from_db(self, start_date: str, end_date: str) -> List[dict]:
        """从数据库获取事件"""
        try:
            import database as db
            events = db.get_events(50)
            # 过滤日期范围内的事件
            result = []
            for e in events:
                first = (e.get("first_seen") or "")[:10]
                last = (e.get("last_seen") or "")[:10]
                if first <= end_date and (not last or last >= start_date):
                    result.append(e)
            return result
        except Exception:
            return []

    def _calculate_stats(self, notes: List[dict], events: List[dict]) -> dict:
        """计算统计数据"""
        total = len(notes)
        # [Canonical P0] 情感/风险分桶统一走 canonical_metrics；方案甲 high 不含 critical(critical 独立)
        from canonical_metrics import sentiment_count as _sc_fn, risk_count as _rc_fn
        _sc = _sc_fn(notes); _rc = _rc_fn(notes)
        positive, negative, neutral = _sc["positive"], _sc["negative"], _sc["neutral"]
        high_risk = _rc["high"]
        medium_risk = _rc["medium"]
        total_engagement = sum(
            int(n.get("likes", 0) or 0) + int(n.get("comments", 0) or 0) * 2
            for n in notes
        )
        # 风险指数（复用现有算法）
        try:
            from daily_report import calculate_risk_index, calculate_brand_health_score
            risk_index = calculate_risk_index(notes, events)
            brand_health = calculate_brand_health_score(notes, risk_index)
        except Exception:
            risk_index = round(min(100, (negative / total * 60) if total > 0 else 0), 1)
            brand_health = round(100 - risk_index, 1)

        return {
            "total_notes": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_ratio": round(positive / total * 100, 1) if total > 0 else 0,
            "negative_ratio": round(negative / total * 100, 1) if total > 0 else 0,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "total_engagement": total_engagement,
            "risk_index": risk_index,
            "brand_health": brand_health,
            "event_count": len(events),
            "active_events": sum(1 for e in events if e.get("status") == "active"),
        }

    # ============ 报告各部分生成 ============

    def _get_brand_name(self) -> str:
        if self.brand_mode == "cth":
            return cth_phrases.BRAND_INFO["full_name"]
        return self.brand_config.get("brand_name", "Z-Brand")

    def _generate_executive_summary(self, stats: dict, notes: List[dict], events: List[dict]) -> str:
        """生成执行摘要（一句话）"""
        risk_index = stats.get("risk_index", 0)
        health = stats.get("brand_health", 50)
        effective = stats.get("total_notes", 0)
        risk_count = stats.get("high_risk", 0) + stats.get("medium_risk", 0)

        # 数据完整性保护
        if effective == 0:
            if self.brand_mode == "cth":
                return self.phrases.REPORT_PHRASES["executive_summary"]["data_incomplete"]
            else:
                return f"{self._get_brand_name()}本周期无有效舆情数据，建议检查采集任务是否正常运行。"

        if risk_index >= 60:
            mood = "negative" if self.brand_mode == "zbmp" else "negative_rising"
        elif stats.get("positive_ratio", 0) > 60:
            mood = "positive" if self.brand_mode == "zbmp" else "positive_dominant"
        else:
            mood = "neutral" if self.brand_mode == "zbmp" else "stable"

        if self.brand_mode == "cth":
            base = self.phrases.REPORT_PHRASES["executive_summary"].get(mood, "")
            if mood == "positive_dominant":
                return base.format(活动或节点="本周期", 增长比例=f"{stats.get('positive_ratio',0)}%")
            return base
        else:
            return self.phrases.generate_zbmp_phrase(
                "executive_summary", mood,
                brand=self._get_brand_name(),
                metric="声量", direction="增长", value=f"{stats.get('positive_ratio',0)}%",
                issue_type="用户反馈", action="持续监测",
            )

    def _generate_key_metrics(self, stats: dict) -> List[dict]:
        """生成关键指标"""
        return [
            {"name": "有效舆情数", "value": stats.get("total_notes", 0), "unit": "条"},
            {"name": "正面占比", "value": stats.get("positive_ratio", 0), "unit": "%"},
            {"name": "负面占比", "value": stats.get("negative_ratio", 0), "unit": "%"},
            {"name": "风险指数", "value": stats.get("risk_index", 0), "unit": "/100"},
            {"name": "品牌健康度", "value": stats.get("brand_health", 0), "unit": "/100"},
            {"name": "总互动量", "value": stats.get("total_engagement", 0), "unit": "次"},
            {"name": "活跃事件", "value": stats.get("active_events", 0), "unit": "个"},
        ]

    def _generate_risk_events(self, events: List[dict], notes: List[dict]) -> List[dict]:
        """生成风险事件列表"""
        risk_events = []
        for e in sorted(events, key=lambda x: x.get("risk_score", 0), reverse=True)[:5]:
            risk_level = e.get("risk_level", "low")
            title = e.get("title", "未命名事件")[:50]
            score = e.get("risk_score", 0)

            if self.brand_mode == "cth":
                alert = cth_phrases.get_risk_phrase(risk_level, title, score)
            else:
                alert = zbmp_phrases.generate_zbmp_phrase(
                    "risk_alert", risk_level,
                    brand=self._get_brand_name(), event=title, score=score,
                    time=RiskLevel(risk_level).response_time if risk_level in [l.value for l in RiskLevel] else "持续观察",
                    trend="上升" if score > 60 else "平稳",
                )

            risk_events.append({
                "event_id": e.get("id", ""),
                "title": title,
                "risk_level": risk_level,
                "risk_label": RiskLevel(risk_level).label if risk_level in [l.value for l in RiskLevel] else risk_level,
                "risk_score": score,
                "mention_count": e.get("mention_count", 0),
                "source_count": e.get("source_count", 1),
                "fact_status": e.get("fact_status", "unconfirmed"),
                "alert_message": alert,
                "first_seen": e.get("first_seen", ""),
                "last_seen": e.get("last_seen", ""),
            })
        return risk_events

    def _generate_sentiment_analysis(self, notes: List[dict]) -> dict:
        """生成情感分析"""
        total = len(notes)
        positive = sum(1 for n in notes if n.get("sentiment") == "positive")
        negative = sum(1 for n in notes if n.get("sentiment") == "negative")
        neutral = sum(1 for n in notes if n.get("sentiment") == "neutral")

        overall = classify_sentiment(positive, negative, neutral)

        # 按平台分布
        platform_dist = {}
        for n in notes:
            plat = n.get("source_platform", n.get("platform", "unknown"))
            platform_dist.setdefault(plat, {"total": 0, "positive": 0, "negative": 0})
            platform_dist[plat]["total"] += 1
            if n.get("sentiment") == "positive":
                platform_dist[plat]["positive"] += 1
            elif n.get("sentiment") == "negative":
                platform_dist[plat]["negative"] += 1

        return {
            "overall": overall.value,
            "overall_label": overall.label,
            "distribution": {
                "positive": positive, "negative": negative, "neutral": neutral,
                "positive_ratio": round(positive / total * 100, 1) if total > 0 else 0,
                "negative_ratio": round(negative / total * 100, 1) if total > 0 else 0,
            },
            "platform_distribution": platform_dist,
        }

    def _generate_propagation_analysis(self, notes: List[dict], events: List[dict]) -> dict:
        """生成传播分析"""
        total_eng = sum(int(n.get("likes", 0) or 0) + int(n.get("comments", 0) or 0) for n in notes)

        if total_eng > 1000:
            level = "high"
        elif total_eng > 200:
            level = "medium"
        else:
            level = "low"

        # 传播主体分布
        subject_dist = {}
        for n in notes:
            author_type = n.get("author_type", "normal_user")
            subject_dist[author_type] = subject_dist.get(author_type, 0) + 1

        # 热门笔记Top5
        top_notes = sorted(
            notes,
            key=lambda x: int(x.get("likes", 0) or 0) + int(x.get("comments", 0) or 0),
            reverse=True
        )[:5]

        return {
            "engagement_level": level,
            "total_engagement": total_eng,
            "subject_distribution": subject_dist,
            "top_notes": [
                {
                    "title": (n.get("title", "") or "无标题")[:40],
                    "author": n.get("author_nickname", n.get("author", "匿名")),
                    "engagement": int(n.get("likes", 0) or 0) + int(n.get("comments", 0) or 0),
                    "sentiment": n.get("sentiment", "neutral"),
                    "url": n.get("url", ""),
                }
                for n in top_notes
            ],
        }

    def _generate_key_insights(self, notes: List[dict], events: List[dict], stats: dict) -> List[dict]:
        """生成关键洞察（3-5条）"""
        insights = []
        total = stats.get("total_notes", 0)

        if total == 0:
            return [{"insight": "本周期无有效数据，建议检查采集任务。", "type": "system"}]

        # 洞察1：情感格局
        pos_ratio = stats.get("positive_ratio", 0)
        neg_ratio = stats.get("negative_ratio", 0)
        if neg_ratio > 30:
            insights.append({
                "insight": f"负面占比{neg_ratio}%，高于警戒线30%，需重点关注负面内容扩散。",
                "type": "risk", "metric": f"负面{stats['negative']}条"
            })
        elif pos_ratio > 60:
            insights.append({
                "insight": f"正面占比{pos_ratio}%，品牌口碑健康，可关注正向内容传播放大机会。",
                "type": "opportunity", "metric": f"正面{stats['positive']}条"
            })
        else:
            insights.append({
                "insight": f"正负声量接近（正面{pos_ratio}%/负面{neg_ratio}%），舆情中性观察。",
                "type": "neutral", "metric": f"共{total}条"
            })

        # 洞察2：风险事件
        high_events = [e for e in events if e.get("risk_level") in ("high", "critical")]
        if high_events:
            insights.append({
                "insight": f"存在{len(high_events)}个高风险事件，建议优先处置。",
                "type": "risk", "metric": f"高风险{len(high_events)}个"
            })

        # 洞察3：传播力
        if stats.get("total_engagement", 0) > 500 and notes:
            hot = max(notes, key=lambda x: int(x.get("likes", 0) or 0) + int(x.get("comments", 0) or 0))
            insights.append({
                "insight": f"总互动量{stats['total_engagement']}，最热内容「{(hot.get('title','') or '无标题')[:20]}」，建议关注传播走向。",
                "type": "trend", "metric": f"互动{stats['total_engagement']}"
            })

        return insights[:5]

    def _generate_action_items(self, events: List[dict], stats: dict) -> List[dict]:
        """生成行动建议"""
        actions = []

        # 高风险事件 -> 紧急
        for e in [x for x in events if x.get("risk_level") in ("high", "critical")][:2]:
            actions.append({
                "priority": "紧急",
                "action": f"核查事件「{e.get('title','')[:20]}」事实真相，收集独立来源验证。",
                "owner": "舆情/客服团队",
                "deadline": RiskLevel(e.get("risk_level", "high")).response_time,
                "event_id": e.get("id"),
            })

        # 中风险 -> 高优先级
        med_events = [e for e in events if e.get("risk_level") == "medium"]
        if med_events:
            actions.append({
                "priority": "高",
                "action": f"持续关注{len(med_events)}个中风险事件，准备应对预案。",
                "owner": "舆情/运营团队",
                "deadline": "本周内",
            })

        # 负面多 -> 客服
        if stats.get("high_risk", 0) + stats.get("medium_risk", 0) > 3:
            actions.append({
                "priority": "高",
                "action": f"有{stats['high_risk'] + stats['medium_risk']}条风险内容，建议客服逐一查看负面笔记主动联系。",
                "owner": "客服团队",
                "deadline": "48小时内",
            })

        # 正面多 -> 营销
        if stats.get("positive_ratio", 0) > 60:
            actions.append({
                "priority": "中",
                "action": "正面声量占优，建议筛选优质UGC考虑转发或二次传播。",
                "owner": "营销/社媒团队",
                "deadline": "本周内",
            })

        if not actions:
            actions.append({
                "priority": "常规",
                "action": "舆情整体平稳，按常规节奏监测即可。",
                "owner": "舆情团队",
                "deadline": "持续",
            })

        return actions[:5]

    def _generate_data_quality(self, notes: List[dict]) -> dict:
        """生成数据质量评估"""
        total = len(notes)
        empty_content = sum(1 for n in notes if not n.get("content") and not n.get("title"))
        missing_date = sum(1 for n in notes if not n.get("publish_date") and not n.get("publish_at"))
        no_sentiment = sum(1 for n in notes if not n.get("sentiment"))

        return {
            "total_collected": total,
            "empty_content": empty_content,
            "missing_date": missing_date,
            "no_sentiment": no_sentiment,
            "quality_score": round(max(0, 100 - (empty_content + missing_date + no_sentiment) / max(total, 1) * 100), 1),
            "warnings": [
                f"{empty_content}条笔记正文为空" if empty_content else None,
                f"{missing_date}条笔记缺少发布时间" if missing_date else None,
            ],
            "collection_complete": total > 0,
        }

    def _generate_appendix(self, notes: List[dict], events: List[dict]) -> dict:
        """生成附录（原始数据索引）"""
        return {
            "note_count": len(notes),
            "event_count": len(events),
            "note_ids": [n.get("note_id", n.get("id", "")) for n in notes[:50]],
            "event_ids": [e.get("id", "") for e in events],
            "data_source": "monitor.db notes/events表",
            "generated_by": "lumenis.shared.reporting.ReportGenerator",
        }

    # ============ CTH专属 ============

    def _generate_cth_specific(self, notes: List[dict], events: List[dict], stats: dict) -> dict:
        """太古汇专属内容"""
        # 活动节点匹配
        current_month = datetime.now().month
        active_nodes = []
        for key, node in cth_phrases.ACTIVITY_NODES.items():
            if str(current_month) in node.get("month", ""):
                active_nodes.append(node)

        # 太古汇调性评估
        tone_score = self._evaluate_tone(notes)

        return {
            "brand_info": cth_phrases.BRAND_INFO,
            "active_activity_nodes": active_nodes,
            "tone_evaluation": tone_score,
            "column_structure": cth_phrases.COLUMN_STRUCTURE,
            "competitors": cth_phrases.COMPETITORS,
            "report_header": cth_phrases.REPORT_HEADER,
            "report_footer": cth_phrases.REPORT_FOOTER,
        }

    def _evaluate_tone(self, notes: List[dict]) -> dict:
        """评估笔记是否符合太古汇调性（温暖/精致/仪式感）"""
        tone_keywords = {
            "温暖": ["温暖", "治愈", "贴心", "用心", "关怀", "感动"],
            "精致": ["精致", "品质", "细节", "高级", "质感", "优雅"],
            "仪式感": ["仪式", "纪念", "专属", "限定", "尊享", "礼遇"],
        }
        scores = {}
        for tone, keywords in tone_keywords.items():
            count = sum(
                1 for n in notes
                if any(kw in (n.get("title", "") + n.get("content", "")) for kw in keywords)
            )
            scores[tone] = count

        total = len(notes) or 1
        return {
            "scores": scores,
            "warm_ratio": round(scores["温暖"] / total * 100, 1),
            "refined_ratio": round(scores["精致"] / total * 100, 1),
            "ritual_ratio": round(scores["仪式感"] / total * 100, 1),
            "overall": "符合太古汇调性" if sum(scores.values()) / total > 0.2 else "调性匹配度待提升",
        }

    # ============ ZBMP专属 ============

    def _generate_zbmp_specific(self, notes: List[dict], events: List[dict], stats: dict) -> dict:
        """通用品牌专属内容"""
        industry = self.brand_config.get("industry", "retail")
        industry_focus = zbmp_phrases.get_industry_focus(industry)

        return {
            "brand_config": self.brand_config,
            "industry_focus": industry_focus,
            "multi_brand_comparison": zbmp_phrases.MULTI_BRAND_COMPARISON,
            "period_focus": zbmp_phrases.get_period_focus("daily"),
        }
