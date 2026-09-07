# 前端字段期望审计 · notes（笔记搜索）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/notes.html`
- **路由**：`/lumenis/cth/notes`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/notes` | GET | notes.html:31 (`data-api`) | 笔记列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → notes / data / items / list / results / records / rows
```

列名动态推断。每条记录可能包含：
- id / note_id
- title
- content / text
- author / author_name
- brand_name / brand
- source_platform / platform
- sentiment
- risk_level
- likes / comments / collects / shares
- publish_datetime / created_at
- note_url / url

## 硬编码数据
- 页面标题"笔记搜索"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 overview/realtime 的 `/api/notes` 调用相同端点，但那些页面有专用渲染逻辑
- 当前无搜索参数传递（直接调用全量）
