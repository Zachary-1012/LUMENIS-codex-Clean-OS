# 前端字段期望审计 · kos（KOS 传播主体）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/kos.html`
- **路由**：`/lumenis/cth/kos`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/kos/list` | GET | kos.html:31 (`data-api`) | KOS 列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → data / items / list / results / records / notes / cases / events / rows
```

列名动态推断。每条记录可能包含：
- id / kos_id / user_id
- name / nickname / author_name
- platform / source_platform
- followers / follower_count
- content_count / note_count
- engagement_rate
- brand_relation / related_brands
- subject_type (KOS/KOL/KOC/普通用户/媒体/官方)
- level / tier

## 硬编码数据
- 页面标题"KOS 传播主体"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 evidence/industries/negative/official/event_graph/calendar/analysis/cases/case_analysis/knowledge/notes 共享相同模板
- AGENTS.md 9.1 要求主体身份与内容属性严格分开（subject_type ≠ content_type）
