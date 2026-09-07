# 前端字段期望审计 · analysis（深度分析）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/analysis.html`
- **路由**：`/lumenis/cth/analysis`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/trend/overview` | GET | analysis.html:31 (`data-api`) | 趋势分析数据（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → data / items / list / results / records / trends / rows
```

列名动态推断。数据可能包含：
- date / day
- note_count / volume
- positive / negative / neutral
- engagement
- top_topics[]
- top_brands[]

## 硬编码数据
- 页面标题"深度分析"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 trend.html 的 `/api/trend/overview` 调用相同端点
- trend.html 是通用数据面板（原始 JSON 渲染），本页是六态面板（动态表格）
