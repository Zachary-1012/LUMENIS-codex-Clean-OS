# 前端字段期望审计 · case_analysis（案例分析）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/case_analysis.html`
- **路由**：`/lumenis/cth/case-analysis`
- **模板类型**：六态面板
- **初始化触发**：`LUMENIS.ready` → `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/case-analysis/list` | GET | case_analysis.html:31 (`data-api`) | 案例分析列表（唯一 API） |

## 期望响应字段树

通用 `extractList()` 多路径探测：
```
response → data / items / list / results / records / analyses / rows
```

列名动态推断。每条记录可能包含：
- id / analysis_id
- title / name
- case_id / related_case
- brand / brand_name
- analysis_type / type
- findings / insights
- metrics / kpi
- created_at / generated_at
- status

## 硬编码数据
- 页面标题"案例分析"、空态文案硬编码

## 渲染假设与字段缺失处理
- 同六态面板通用逻辑
- 无固定字段契约

## 备注
- 与 cases.html 是不同端点（cases 是案例库，本页是案例分析结果）
