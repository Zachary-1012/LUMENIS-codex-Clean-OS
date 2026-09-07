# 前端字段期望审计 · negative（负面确认）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/negative.html`
- **路由**：`/lumenis/cth/negative`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/negative/pending` | GET | negative.html:31 (`data-api`) | 待确认负面列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → negatives / data / items / list / results / records / notes / cases / events / rows
```

列名动态推断。每条记录可能包含：
- id / negative_id / note_id
- title / content
- author / author_name
- brand_name / brand
- source_platform / platform
- sentiment (negative)
- risk_level (critical/high/medium/low)
- status (pending/confirmed/dismissed)
- publish_datetime / created_at
- note_url / url

## 硬编码数据
- 页面标题"负面确认"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 risk.html 的 `/api/negative/pending` 调用相同端点，但 risk 页有专用渲染逻辑，本页是通用动态表格
