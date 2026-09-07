# 前端字段期望审计 · industries（业态分析）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/industries.html`
- **路由**：`/lumenis/cth/industries`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/industries/list` | GET | industries.html:31 (`data-api`) | 业态列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测（同 evidence）：
```
response → data / items / list / results / records / notes / cases / events / rows
```

列名 `inferColumns()` 动态推断。每条记录可能包含：
- id / industry_id
- name / industry_name / category
- note_count / count
- brand_count
- engagement / total_engagements
- positive / negative / neutral
- trend (string/number)

## 硬编码数据
- 页面标题"业态分析"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑（见 evidence.md）
- 无固定字段契约

## 备注
- 与 evidence/kos/negative/official/event_graph/calendar/analysis/cases/case_analysis/knowledge/notes 共享相同模板
