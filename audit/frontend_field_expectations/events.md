# 前端字段期望审计 · events（事件中心）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/events.html`（371 行）
- **路由**：`/lumenis/cth/events`
- **初始化触发**：`DOMContentLoaded` → `loadEventsAll()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/event-graph/stats` | GET | events.html:150 | KPI 统计 |
| 2 | `/api/event-graph/events` | GET | events.html:170 | 事件列表（主源），参数 type/range/limit |
| 3 | `/api/cases/list` | GET | events.html:179 | 事件列表（降级源） |
| 4 | `/api/trend/notes` | GET | ZBCTrendLine | 全局趋势线 |
| 5 | `/api/trend/engagement` | GET | ZBCTrendLine | 全局趋势线 |
| 6 | `/api/trend/sentiment` | GET | ZBCTrendLine | 全局趋势线 |

## 期望响应字段树

### API 1: `/api/event-graph/stats`
```
response
├── stats / data (直接对象)
│   ├── total_events / events (number)
│   ├── active_events / ongoing (number)
│   ├── total_volume / volume (number)
│   └── brand_count / brands (number)
```

### API 2-3: 事件列表
```
response
├── events[] / data[] / cases[]
│   ├── id / event_id / case_id (string/number)
│   ├── title / event_title / case_title / name (string)
│   ├── type / event_type / category (string: marketing/propagation/crisis/product/service/other)
│   ├── status (string: active/ongoing/monitoring/pending/resolved/closed/archived)
│   ├── brands[] (string[]) 或 related_brands / brand_names (string)
│   ├── volume / note_count (number)
│   ├── sentiment (string)
│   ├── risk_level (string)
│   ├── start_time / created_at (string)
│   ├── end_time (string, 可空)
│   ├── description / summary (string)
│   └── related_notes[] (array, 可空)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| 事件类型 6 类映射 | events.html:6-14,137 | marketing/propagation/crisis/product/service/other |
| 时间范围 4 档 | events.html:15-20 | 7d/30d/90d/all，默认 30d |
| 状态标签颜色映射 | events.html:133 | active/ongoing→high, monitoring/pending→medium, resolved/closed→low |
| 列表 limit=50 | events.html:168 | 硬编码分页大小 |

## 渲染假设与字段缺失处理
- KPI 双路径回退：`stats.total_events != null ? stats.total_events : stats.events`
- 列表双路径回退：`d.events || d.data || []`，降级源 `d.cases || d.data || []`
- 事件字段多别名回退：`ev.id || ev.event_id || ev.case_id`
- brands 字段兼容数组和字符串：`Array.isArray(ev.brands) ? join : ev.related_brands`
- 主源失败自动降级到 `/api/cases/list`
- 详情面板未选择 → placeholder 态

## 备注
- 事件列表主源 `/api/event-graph/events`，降级源 `/api/cases/list`
- 支持事件详情弹窗
- 三类事件（营销/传播/舆情）通过 type 筛选
