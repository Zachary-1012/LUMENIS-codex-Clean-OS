# 前端字段期望审计 · xiaohongshu（小红书平台页）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/xiaohongshu.html`（552 行）
- **路由**：`/lumenis/cth/xiaohongshu`
- **初始化触发**：`DOMContentLoaded` → `loadAll()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/xiaohongshu/notes` | GET | xiaohongshu.html:~200 | 笔记列表（主源） |
| 2 | `/api/notes?platform=xiaohongshu` | GET | xiaohongshu.html:~210 | 笔记列表（降级源） |
| 3 | `/api/xiaohongshu/stats` | GET | xiaohongshu.html:~250 | KPI 统计（主源） |
| 4 | `/api/stats` | GET | xiaohongshu.html:~260 | KPI 统计（降级源） |
| 5 | `/api/xiaohongshu/auth-status` | GET | xiaohongshu.html:~280 | 登录态检查 |
| 6 | `/api/xiaohongshu/start-crawl` | POST | xiaohongshu.html:~300 | 触发采集（按钮） |
| 7 | `/api/trend/notes` | GET | ZBCTrendLine | 全局趋势线 |
| 8 | `/api/trend/engagement` | GET | ZBCTrendLine | 全局趋势线 |
| 9 | `/api/trend/sentiment` | GET | ZBCTrendLine | 全局趋势线 |

## 期望响应字段树

### API 1-2: 笔记列表
```
response
├── total (number)
└── notes[]
    ├── id / note_id (string)
    ├── title (string)
    ├── content (string)
    ├── author / author_name / nickname (string)
    ├── author_id / user_id (string)
    ├── brand_name / brand (string)
    ├── likes / liked_count (number)
    ├── comments / comment_count (number)
    ├── collects / collected_count (number)
    ├── shares / share_count (number)
    ├── sentiment (string)
    ├── risk_level (string)
    ├── publish_datetime / publish_time / created_at (string)
    ├── note_url / url (string)
    └── images[] (string[]) — 图片 URL
```

### API 3-4: 统计
```
response
└── stats / data
    ├── total_notes (number)
    ├── today_count (number)
    ├── total_likes (number)
    ├── total_comments (number)
    ├── total_collects (number)
    ├── positive (number)
    ├── negative (number)
    └── high_risk (number)
```

### API 5: 登录态
```
response
├── logged_in (bool)
├── username (string)
├── status (string: active/expired/need_verify)
└── last_check (string)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| 平台名称"小红书" | 多处 | 硬编码文案 |
| 采集状态标签映射 | ~350 | SUCCESS/NO_NEW_DATA/RISK_WARNING 等 |
| 互动图标（❤💬⭐↗） | ~400 | 硬编码 emoji |

## 渲染假设与字段缺失处理
- 笔记字段缺失用 `||` 回退
- 登录态未登录 → 显示登录引导卡片
- 采集按钮触发后显示 loading 态
- 图片缺失不渲染图片区域

## 备注
- 小红书是当前主采集平台，页面含 Auth 状态展示
- 遵循 AGENTS.md 官方账号只读保护红线
