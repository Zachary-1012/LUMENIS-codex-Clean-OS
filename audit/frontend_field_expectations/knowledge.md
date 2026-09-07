# 前端字段期望审计 · knowledge（品牌知识库）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/knowledge.html`
- **路由**：`/lumenis/cth/knowledge`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/brand-knowledge/search` | GET | knowledge.html:31 (`data-api`) | 品牌知识搜索（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → data / items / list / results / records / knowledge / rows
```

列名动态推断。每条记录可能包含：
- id / knowledge_id
- title / name
- category / type
- brand / brand_name
- content / description
- source / url
- tags[]
- created_at / updated_at

## 硬编码数据
- 页面标题"品牌知识库"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 端点名为 search，但当前无搜索参数传递（直接调用）
