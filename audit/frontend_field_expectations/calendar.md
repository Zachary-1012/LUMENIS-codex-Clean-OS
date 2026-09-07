# 前端字段期望审计 · calendar（舆情日历）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/calendar.html`
- **路由**：`/lumenis/cth/calendar`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/weekly/events` | GET | calendar.html:31 (`data-api`) | 日历事件列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → events / data / items / list / results / records / rows
```

列名动态推断。每条记录可能包含：
- id / event_id
- title / name
- date / event_date / start_date
- type / category
- description / summary
- related_notes / note_count
- status

## 硬编码数据
- 页面标题"舆情日历"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 reports.html 的 `/api/weekly/events` 调用相同端点
- 当前为通用表格渲染，非真正日历视图
