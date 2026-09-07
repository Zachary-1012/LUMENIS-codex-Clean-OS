# 前端字段期望审计 · topics（话题监测）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/topics.html`（190 行）
- **路由**：`/lumenis/cth/topics`
- **初始化触发**：`TC.init()` → `TC.loadAll()`（页面内 script）

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/topic-campaign/stats` | GET | topics.html:83 | KPI + 话题分布 |
| 2 | `/api/topic-campaign/topics` | GET | topics.html:86 | 话题列表（筛选下拉） |
| 3 | `/api/topic-campaign/timeline` | GET | topics.html:95 | 采集时间线 |
| 4 | `/api/topic-campaign/notes?limit=200` | GET | topics.html:98 | 笔记列表 |

## 期望响应字段树

### API 1: `/api/topic-campaign/stats`
```
response
├── ok (bool)
├── total
│   ├── unique_notes (number)
│   ├── new_notes_24h (number)
│   └── runs (number)
├── by_topic[]
│   ├── topic (string)
│   ├── unique_notes (number)
│   ├── new_notes (number)
│   └── runs (number)
├── campaign (object)
└── campaign_key (string)
```

### API 2: `/api/topic-campaign/topics`
```
response
├── ok (bool)
└── topics[]
    ├── topic / name (string)
```

### API 3: `/api/topic-campaign/timeline`
```
response
├── ok (bool)
└── snapshots[]
    ├── snapshot_at / created_at (string, ISO)
```

### API 4: `/api/topic-campaign/notes`
```
response
├── ok (bool)
└── notes[]
    ├── topic (string)
    ├── title (string)
    ├── author (string)
    ├── publish_datetime (string)
    ├── likes (number)
    ├── comments (number)
    ├── collects (number)
    ├── shares (number)
    └── note_url (string)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| limit=200 | topics.html:98 | 笔记拉取上限，硬编码 |
| perPage=20 | topics.html:74 | 分页大小，硬编码 |
| 活动状态"监测中" | topics.html:109 | 硬编码 badge，不读 API |
| SVG 柱状图配色 #00d4aa | topics.html:142 | 硬编码 |
| 互动图标 ❤💬⭐↗ | topics.html:170 | 硬编码 emoji |

## 渲染假设与字段缺失处理
- 所有 API 检查 `d.ok`，非 ok 静默跳过（不显示错误）
- KPI 缺失默认 0：`t.unique_notes || 0`
- 时间线按日期前端聚合（`snapshot_at.slice(0,10)`），非后端预聚合
- 笔记搜索/筛选/分页全在前端完成
- 时间线空数据 → "暂无时间线数据"
- 笔记列表空 → "暂无笔记数据"

## 备注
- 4 个 API 并行调用，无依赖关系
- 时间线图是纯前端 SVG 实现，不依赖图表库
- 活动状态硬编码为"监测中"，未从 API 读取真实状态
