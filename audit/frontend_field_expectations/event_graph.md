# 前端字段期望审计 · event_graph（事件图谱）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/event_graph.html`
- **路由**：`/lumenis/cth/event-graph`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/event-graph/events` | GET | event_graph.html:31 (`data-api`) | 事件列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → events / data / items / list / results / records / cases / rows
```

列名动态推断。每条记录可能包含：
- id / event_id
- title / event_title / name
- type / event_type (marketing/propagation/crisis)
- status (active/ongoing/resolved/closed)
- brands / related_brands
- volume / note_count
- sentiment
- risk_level
- start_time / created_at
- end_time
- related_events[] (event_relation)

## 硬编码数据
- 页面标题"事件图谱"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 events.html 的 `/api/event-graph/events` 调用相同端点，但 events 页有专用渲染逻辑
- AGENTS.md 9.3 要求事件支持生命周期和 event_relation
