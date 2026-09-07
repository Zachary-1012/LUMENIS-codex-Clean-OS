# 前端字段期望审计 · data_center/index（数据中心概览）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/data_center/index.html`
- **路由**：`/lumenis/cth/data-center`
- **初始化触发**：页面内 script 自动执行

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/data-center/stats/overview` | GET | data_center/index.html (script) | 数据中心统计概览 |

## 期望响应字段树

```
response
├── ok (bool)
├── data / stats
│   ├── total_notes (number)
│   ├── total_comments (number)
│   ├── total_events (number)
│   ├── total_reports (number)
│   ├── platforms[] — 各平台数据量
│   │   ├── name (string)
│   │   └── count (number)
│   ├── daily_growth (number)
│   └── last_crawl_time (string)
```

## 硬编码数据
- 平台卡片布局、KPI 标签均为硬编码 HTML 结构

## 渲染假设与字段缺失处理
- 字段缺失显示 `—` 或 0
- 平台列表动态渲染

## 备注
- 数据中心入口页，展示全局数据资产统计
- 子页面 `platform.html` 负责单平台详情
