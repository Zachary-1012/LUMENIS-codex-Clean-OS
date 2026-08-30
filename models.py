"""
广州太古汇舆情监测系统 - 数据模型定义
基于SQLite数据库表结构的ORM模型
版本: v5.8.0
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any


class BaseModel:
    """基础模型类"""
    table_name: str = ""
    fields: List[str] = []

    def __init__(self, **kwargs):
        for field in self.fields:
            setattr(self, field, kwargs.get(field))

    def to_dict(self) -> Dict[str, Any]:
        return {field: getattr(self, field, None) for field in self.fields}

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'BaseModel':
        data = {key: row[key] for key in row.keys()}
        return cls(**data)


class Note(BaseModel):
    """小红书笔记模型"""
    table_name = "notes"
    fields = [
        'id', 'note_id', 'title', 'content', 'url', 'cover',
        'author_id', 'author_nickname', 'author_avatar',
        'likes', 'comments', 'collects', 'shares', 'note_type',
        'xsec_token', 'collected_at', 'publish_date',
        'sentiment', 'sentiment_score', 'risk_level', 'risk_score',
        'summary', 'topics', 'ai_provider', 'ai_analyzed_at',
        'is_official', 'category', 'status', 'last_seen_at',
        'is_taikoo_verified', 'verify_reason', 'source_platform',
        'relevance_status', 'verification_status', 'verification_confidence',
        'fact_basis', 'ai_reason', 'event_hint', 'translations',
        'relevance_score', 'content_quality', 'duplicate_of',
        'ai_model', 'last_reviewed_at', 'ai_filter_status',
        'ai_filter_reason', 'ai_filtered_at', 'content_quality_score',
        'is_duplicate', 'noise_type', 'ai_insight',
        'publish_datetime', 'captured_at', 'detail_fetched_at',
        'comments_fetched_at', 'comments_collected',
        'data_quality_status', 'data_quality_score', 'collector_version',
        'body', 'source_keyword', 'matched_keywords',
        'negative_confirmed', 'negative_confirmed_at', 'negative_confirmed_by'
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.negative_confirmed = kwargs.get('negative_confirmed', 0)  # 0待确认 1已确认 2已驳回


class Event(BaseModel):
    """舆情事件模型"""
    table_name = "events"
    fields = [
        'id', 'event_key', 'title', 'summary', 'fact_status',
        'impact', 'risk_reason', 'recommended_action',
        'first_seen', 'last_seen', 'mention_count', 'source_count',
        'risk_level', 'risk_score', 'status', 'keywords',
        'translations', 'ai_provider'
    ]


class Comment(BaseModel):
    """评论模型"""
    table_name = "comments"
    fields = [
        'id', 'note_id', 'comment_id', 'content',
        'author_id', 'author_nickname', 'likes', 'create_time',
        'sentiment', 'risk_level', 'risk_score', 'is_negative',
        'collected_at', 'is_taikoo_verified'
    ]


class NoteComment(BaseModel):
    """笔记评论模型（V2采集器）"""
    table_name = "note_comments"
    fields = [
        'id', 'comment_id', 'note_id', 'content',
        'author_id', 'author_nickname', 'likes', 'publish_time',
        'parent_id', 'raw_json', 'fetched_at'
    ]


class DailyReport(BaseModel):
    """日报模型"""
    table_name = "daily_reports"
    fields = [
        'id', 'report_type', 'report_date', 'period_start', 'period_end',
        'total_notes', 'positive_count', 'neutral_count', 'negative_count',
        'high_risk_count', 'medium_risk_count', 'low_risk_count',
        'total_likes', 'total_comments', 'total_engagements',
        'top_topics', 'hot_notes', 'risk_alerts', 'key_events',
        'event_summary', 'sentiment_analysis', 'summary', 'generated_at',
        'executive_summary', 'ai_summary', 'key_insights', 'action_items',
        'risk_index', 'brand_health_score'
    ]


class DailyDigest(BaseModel):
    """每日摘要模型"""
    table_name = "daily_digest"
    fields = [
        'id', 'digest_date', 'total_found', 'effective_count',
        'positive_count', 'neutral_count', 'risk_count',
        'risk_index', 'brand_health_score',
        'ai_summary', 'executive_summary', 'key_insights',
        'action_items', 'top_events', 'generated_at'
    ]


class WeeklyEvent(BaseModel):
    """周报事件模型"""
    table_name = "weekly_events"
    fields = [
        'id', 'week_key', 'event_title', 'event_type', 'urgency',
        'description', 'location', 'people_involved', 'process',
        'screenshot_path', 'user_demand', 'sentiment', 'risk_level',
        'status', 'confirmed_negative', 'created_at', 'updated_at'
    ]


class WebTopic(BaseModel):
    """全网话题模型"""
    table_name = "web_topics"
    fields = [
        'id', 'topic', 'source', 'sentiment', 'relevance_score',
        'mention_count', 'first_seen', 'last_seen', 'tags',
        'summary', 'created_at'
    ]


class WebEvent(BaseModel):
    """全网事件模型"""
    table_name = "web_events"
    fields = [
        'id', 'title', 'description', 'source', 'url',
        'published_at', 'discovered_at', 'sentiment', 'risk_level',
        'relevance_score', 'tags', 'status', 'created_at'
    ]


class WebMention(BaseModel):
    """全网提及模型"""
    table_name = "web_mentions"
    fields = [
        'id', 'source_id', 'source_platform', 'source_type',
        'title', 'content', 'url', 'domain',
        'published_at', 'fetched_at', 'relevance', 'verification',
        'confidence', 'sentiment', 'risk_level', 'risk_score',
        'summary', 'event_hint', 'topics', 'ai_provider',
        'related_event_id', 'source_adapter', 'query', 'canonical_url'
    ]


class BrandIndustryMonitor(BaseModel):
    """品牌业态监测模型"""
    table_name = "brand_industry_monitor"
    fields = [
        'id', 'brand_name', 'industry', 'source', 'mention_count',
        'sentiment', 'last_mention_at', 'keywords', 'summary',
        'created_at', 'updated_at'
    ]


class CollectionCounter(BaseModel):
    """采集计数模型"""
    table_name = "collection_counters"
    fields = [
        'id', 'date', 'daily_count', 'manual_count', 'auto_count',
        'last_collect_at', 'created_at', 'updated_at'
    ]


class CollectionLog(BaseModel):
    """采集日志模型"""
    table_name = "collection_logs"
    fields = [
        'id', 'keyword', 'notes_count', 'status', 'error_msg',
        'started_at', 'finished_at'
    ]


class CollectorQualityLog(BaseModel):
    """采集质量日志模型"""
    table_name = "collector_quality_log"
    fields = [
        'id', 'note_id', 'status', 'score', 'detail_status',
        'comments_collected', 'collector_version', 'checked_at', 'reason'
    ]


class AIFilterLog(BaseModel):
    """AI过滤日志模型"""
    table_name = "ai_filter_log"
    fields = [
        'id', 'note_id', 'filter_stage', 'filter_result',
        'filter_reason', 'noise_type', 'confidence', 'provider', 'filtered_at'
    ]


class EventInsight(BaseModel):
    """事件洞察模型"""
    table_name = "event_insights"
    fields = [
        'id', 'event_id', 'ai_summary', 'risk_assessment',
        'recommended_action', 'sentiment_trend', 'propagation_analysis',
        'key_voices', 'provider', 'generated_at'
    ]


class EventMention(BaseModel):
    """事件提及模型"""
    table_name = "event_mentions"
    fields = [
        'id', 'event_id', 'source_type', 'source_id', 'match_score', 'created_at'
    ]


class NoteReviewHistory(BaseModel):
    """笔记审核历史模型"""
    table_name = "note_review_history"
    fields = [
        'id', 'note_id', 'old_relevance', 'new_relevance',
        'old_sentiment', 'new_sentiment', 'old_risk', 'new_risk',
        'reason', 'provider', 'reviewed_at'
    ]


class FeedbackKeyword(BaseModel):
    """反馈关键词模型"""
    table_name = "feedback_keywords"
    fields = [
        'keyword', 'source', 'score', 'enabled',
        'first_seen', 'last_seen', 'used_count'
    ]


class SystemConfig(BaseModel):
    """系统配置模型"""
    table_name = "system_config"
    fields = [
        'id', 'config_key', 'config_value', 'description',
        'created_at', 'updated_at'
    ]


class WebSource(BaseModel):
    """全网数据源模型"""
    table_name = "web_sources"
    fields = [
        'id', 'source_key', 'source_name', 'adapter', 'enabled',
        'last_run_at', 'last_success_at', 'last_error', 'item_count'
    ]


class WebRun(BaseModel):
    """全网采集运行模型"""
    table_name = "web_runs"
    fields = [
        'id', 'adapter', 'query', 'started_at', 'finished_at',
        'fetched', 'accepted', 'rejected', 'error'
    ]


# 模型注册表
MODEL_REGISTRY = {
    'notes': Note,
    'events': Event,
    'comments': Comment,
    'note_comments': NoteComment,
    'daily_reports': DailyReport,
    'daily_digest': DailyDigest,
    'weekly_events': WeeklyEvent,
    'web_topics': WebTopic,
    'web_events': WebEvent,
    'web_mentions': WebMention,
    'brand_industry_monitor': BrandIndustryMonitor,
    'collection_counters': CollectionCounter,
    'collection_logs': CollectionLog,
    'collector_quality_log': CollectorQualityLog,
    'ai_filter_log': AIFilterLog,
    'event_insights': EventInsight,
    'event_mentions': EventMention,
    'note_review_history': NoteReviewHistory,
    'feedback_keywords': FeedbackKeyword,
    'system_config': SystemConfig,
    'web_sources': WebSource,
    'web_runs': WebRun,
}


def get_model(table_name: str) -> Optional[BaseModel]:
    """根据表名获取模型类"""
    return MODEL_REGISTRY.get(table_name)


def get_all_table_names() -> List[str]:
    """获取所有表名"""
    return list(MODEL_REGISTRY.keys())


if __name__ == "__main__":
    print("广州太古汇舆情监测系统 - 数据模型")
    print(f"版本: v5.8.8")
    print(f"模型数量: {len(MODEL_REGISTRY)}")
    print()
    print("数据表列表:")
    for table_name, model_class in MODEL_REGISTRY.items():
        print(f"  - {table_name} ({len(model_class.fields)}个字段)")
