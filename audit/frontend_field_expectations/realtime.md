# 前端字段期望审计 · realtime（实时舆情流）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/realtime.html`（643 行）
- **路由**：`/lumenis/cth/realtime`
- **初始化触发**：`DOMContentLoaded` → `loadAll()`，自动刷新开关（默认 30s）

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/realtime/feed` | GET | realtime.html:245 | 实时笔记流（主源） |
| 2 | `/api/notes` | GET | realtime.html:257 | 实时笔记流（降级源） |
| 3 | `/api/realtime/stats` | GET | realtime.html:300 | KPI 统计（主源） |
| 4 | `/api/stats` | GET | realtime.html:310 | KPI 统计（降级源） |
| 5 | `/api/trend/notes` | GET | realtime.html:20（ZBCTrendLine） | 全局趋势线-笔记 |
| 6 | `/api/trend/engagement` | GET | realtime.html:21 | 全局趋势线-互动 |
| 7 | `/api/trend/sentiment` | GET | realtime.html:22 | 全局趋势线-情感 |

## 期望响应字段树

### API 1-2: `/api/realtime/feed` / `/api/notes`
```
response
├── total (number)
└── notes[]
    ├── id (string/number)
    ├── title (string)
    ├── content / text (string)
    ├── author / author_name (string)
    ├── brand_name / brand (string)
    ├── source_platform / platform (string)
    ├── sentiment (string: positive/negative/neutral)
    ├── risk_level (string: critical/high/medium/low/none)
    ├── likes / like_count (number)
    ├── comments / comment_count (number)
    ├── collects / collect_count (number)
    ├── shares / share_count (number)
    ├── publish_datetime / created_at (string)
    └── note_url / url (string)
```

### API 3-4: `/api/realtime/stats` / `/api/stats`
```
response
└── stats / data
    ├── total_notes / total (number)
    ├── today_count (number)
    ├── positive (number)
    ├── negative (number)
    ├── neutral (number)
    ├── high_risk (number)
    └── total_engagements (number)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| 30000ms 自动刷新间隔 | realtime.html:640 | 轮询间隔 |
| 平台图标映射（小红书/微博/B站） | realtime.html:~380 | 硬编码 emoji/图标 |
| 情感标签颜色映射 | realtime.html:~390 | 硬编码 |

## 渲染假设与字段缺失处理
- 笔记流字段缺失用 `||` 链回退（如 `n.title || '无标题'`）
- KPI 缺失显示 `—` + "数据采集中"
- 自动刷新可手动暂停/恢复
- 降级横幅：任一 API 失败显示顶部降级提示

## 备注
- 与 overview 共享 ZBCTrendLine 全局趋势线组件
- 实时流支持品牌筛选、平台筛选、情感筛选
