# 前端字段期望审计 · cases（品牌营销案例库）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/cases.html`
- **路由**：`/lumenis/cth/cases`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/cases/list` | GET | cases.html:31 (`data-api`) | 案例列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → cases / data / items / list / results / records / rows
```

列名动态推断。每条记录可能包含：
- id / case_id
- title / case_title / name
- brand / brand_name
- category / industry
- campaign_type / type
- start_date / end_date
- description / summary
- results / metrics
- url / link

## 硬编码数据
- 页面标题"品牌营销案例库"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 events.html 的降级源 `/api/cases/list` 调用相同端点
