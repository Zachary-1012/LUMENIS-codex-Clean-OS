# -*- coding: utf-8 -*-
"""TopicSnapshotManager（P1-B｜Topic 数据能力）。

database.record_topic_snapshot 能力已就绪（变化才写、旁路不抛错）。本层将
「事件 / 发布 / 采集 / 更新 / 快照」五时间口径（基线 §11）固化，并作为采集器
真实写入 Topic 快照的适配入口，保证浏览量 / 讨论量 / 笔记数随时间变化可追溯。

时间口径：
  event_date          事件发生日期（业务语义，可能无则不伪造）
  note_publish_date   笔记发布日期（≠采集日期）
  collection_date     本次采集日期（独立时间轴，必填）
  update_date         记录更新时间
  snapshot_date       快照写入时间

用法（采集器接线）：
  from topic_snapshot import TopicSnapshotManager
  mgr = TopicSnapshotManager()
  mgr.record(topic_key='xxx', browse=12345, discussion=678, notes=90,
             source='live', event_date='2026-08-01', note_publish_date='2026-08-02')
"""
import time as _time
from datetime import datetime

import database as db

EVENT_DATE = "event_date"
NOTE_PUBLISH_DATE = "note_publish_date"
COLLECTION_DATE = "collection_date"
UPDATE_DATE = "update_date"
SNAPSHOT_DATE = "snapshot_date"

# 五时间口径顺序（文档/校验用）
TIME_MODEL = (EVENT_DATE, NOTE_PUBLISH_DATE, COLLECTION_DATE, UPDATE_DATE, SNAPSHOT_DATE)


def _iso(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")


class TopicSnapshotManager:
    """Topic 快照写入适配器：五时间口径自动附带 + 委托 db.record_topic_snapshot。"""

    def __init__(self, now=None):
        self._now = now or _time.time

    def describe_time_model(self):
        """返回五时间口径说明（供文档/前端展示，非伪造数据）。"""
        return {
            "model": TIME_MODEL,
            "event_date": "事件发生日期（业务语义；无法获取则不填）",
            "note_publish_date": "笔记发布日期（≠采集日期）",
            "collection_date": "本次采集日期（独立时间轴，必填）",
            "update_date": "记录更新时间",
            "snapshot_date": "快照写入时间",
            "principle": "发布日期 ≠ 采集日期 ≠ 事件发生日期，三者分别保存；不能获取的数据禁止伪造。",
        }

    def record(self, topic_key, browse=None, discussion=None, notes=None,
               source="live", event_date=None, note_publish_date=None,
               collection_date=None, **extra):
        """写入一条 Topic 指标快照，自动附带五时间口径。返回 True=已写 / False=跳过或关闭。"""
        now_ts = self._now()
        if collection_date is None:
            collection_date = _iso(now_ts)
        ctx = dict(extra)
        ctx[COLLECTION_DATE] = collection_date
        ctx[UPDATE_DATE] = _iso(now_ts)
        ctx[SNAPSHOT_DATE] = _iso(now_ts)
        ctx[EVENT_DATE] = event_date
        ctx[NOTE_PUBLISH_DATE] = note_publish_date
        return db.record_topic_snapshot(
            topic_key, browse_count=browse, discussion_count=discussion,
            note_count=notes, source=source, extra=ctx)
