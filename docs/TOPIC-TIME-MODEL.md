# Topic 数据能力：五时间口径数据模型（P1-B）
> 基线《UNIFIED-ENGINEERING-BASELINE》§11 数据时间模型 落地文档。

## 原则
**发布日期 ≠ 采集日期 ≠ 事件发生日期**，三者分别保存；不能获取的数据禁止伪造。

## 五时间口径（TIME_MODEL）
| 口径 | 含义 | 必填 | 示例 |
|---|---|---|---|
| `event_date` | 事件发生日期（业务语义） | 否（无则不填） | 2026-08-01 |
| `note_publish_date` | 笔记发布日期 | 否 | 2026-08-02 |
| `collection_date` | 本次采集日期（独立时间轴） | 是 | 2026-08-03T09:00 |
| `update_date` | 记录更新时间 | 是 | 2026-08-03T09:00 |
| `snapshot_date` | 快照写入时间 | 是 | 2026-08-03T09:00 |

## 存储
Topic 指标快照写入 `metric_snapshots`（entity_type='topic'），
`browse_count / discussion_count / note_count` 随时间变化逐条快照，五时间口径写入 `raw_json.extra`。
变化才写（无变化不重复刷表）；旁路不抛错（不影响采集主链路）。

## 接入
```python
from topic_snapshot import TopicSnapshotManager
mgr = TopicSnapshotManager()
mgr.record(topic_key='xxx', browse=12345, discussion=678, notes=90,
           source='live', event_date='2026-08-01', note_publish_date='2026-08-02')
```
采集器在真实采集到 Topic 计数时调用；展示层用 `/api/metric-trend?entity_type=topic&entity_key=xxx` 拉时间序列。
