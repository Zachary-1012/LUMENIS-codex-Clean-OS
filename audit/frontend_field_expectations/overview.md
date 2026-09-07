# 前端字段期望审计 · overview（CTH 总览页）

> 审计时间：2026-09-08 · 只读静态分析 · 未运行服务

## 页面信息
- **模板文件**：`templates/cth/overview.html`（759 行）
- **路由**：`/lumenis/cth/overview`
- **布局**：继承 `base.html`，6 KPI + 3 趋势线 + 趋势图 + 业态环形图 + 实时流 + 风险看板
- **初始化触发**：`DOMContentLoaded` → `loadAll()`，30 秒轮询 `setInterval(loadAll, 30000)`

## API 调用清单

> 所有 `xjViz.api(path)` 会自动 prepend `/api`，即 `xjViz.api('/notes')` → `GET /api/notes`。

| # | 端点（实际 URL） | 方法 | 调用位置 | 用途 | 降级链 |
|---|---|---|---|---|---|
| 1 | `/api/viz/overview.stats?time_range=today` | GET | overview.html:324 | KPI 今日笔记数（主源） | → `/api/cth/overview` → `/api/stats` |
| 2 | `/api/cth/overview` | GET | overview.html:330,350,652,714 | KPI 降级源 / 风险降级 / 权限检查 | — |
| 3 | `/api/stats` | GET | overview.html:333,342,361,369 | KPI 最终降级源 | — |
| 4 | `/api/brand-stats` | GET | overview.html:357,368,461,491 | KPI 活跃品牌 / 趋势降级 / 业态环形图 | — |
| 5 | `/api/viz/risk.active?time_range=7d&level=high&limit=100` | GET | overview.html:375 | KPI 风险事件（主源） | → `/api/risks/active` |
| 6 | `/api/risks/active` | GET | overview.html:383,393,640 | KPI 风险降级 / 风险看板主源 | → `/api/cth/overview` |
| 7 | `/api/negative/pending` | GET | overview.html:402 | KPI 待审核 | — |
| 8 | `/healthz` | GET | overview.html:408 | KPI 采集状态 + 系统健康 | — |
| 9 | `/api/viz/overview.trend?time_range=30d` | GET | overview.html:442 | 舆情声量趋势（主源） | → `/api/brand-stats` |
| 10 | `/api/notes` | GET | overview.html:584 | 实时舆情流 | — |
| 11 | `/api/trend/notes` | GET | overview.html:216（ZBCTrendLine） | 全局趋势线-笔记 | — |
| 12 | `/api/trend/engagement` | GET | overview.html:217（ZBCTrendLine） | 全局趋势线-互动 | — |
| 13 | `/api/trend/sentiment` | GET | overview.html:218（ZBCTrendLine） | 全局趋势线-情感 | — |

## 期望响应字段树

### API 1: `/api/viz/overview.stats`
```
response
├── success (bool)
├── data
│   └── items[]
│       └── total (number) — 今日笔记数
```

### API 2: `/api/cth/overview`
```
response
├── data
│   ├── total_notes (number)
│   └── recent_records[]
│       ├── risk_level (string: critical/high/medium/low/none)
│       ├── title (string)
│       ├── brand_name / brand (string)
│       ├── sentiment (string)
│       └── publish_datetime / captured_at / created_at (string)
```

### API 3: `/api/stats`
```
response
└── stats
    ├── total / total_notes (number)
    ├── active_brands / brand_count (number)
    ├── positive (number)
    ├── neutral (number)
    ├── negative (number)
    ├── high_risk (number)
    └── total_engagements (number)
```

### API 4: `/api/brand-stats`
```
response
├── total_brands (number)
├── pie_data[]
│   ├── category (string: fashion/beauty/food/jewelry/lifestyle/tech/sports/kids/entertainment)
│   ├── note_count (number)
│   └── brand_count (number)
└── trend_data[]
    ├── date (string)
    ├── note_count (number)
    └── negative_count (number)
```

### API 5: `/api/viz/risk.active`
```
response
├── success (bool)
└── data
    ├── record_count (number)
    └── current_value (number)
```

### API 6: `/api/risks/active`
```
response
├── total (number)
└── risks[]
    ├── risk_level (string: critical/high/medium/low)
    ├── title (string)
    ├── brand_name / brand (string)
    ├── sentiment (string)
    └── publish_datetime / captured_at / created_at (string)
```

### API 7: `/api/negative/pending`
```
response
└── total (number)
```

### API 8: `/healthz`
```
response
├── status (string: ok/healthy/degraded)
├── ok (bool)
└── (其他健康检查字段)
```

### API 9: `/api/viz/overview.trend`
```
response
├── success (bool)
└── data
    └── items[]
        ├── day (string)
        ├── note_count (number)
        └── negative_count (number)
```

### API 10: `/api/notes`
```
response
├── total (number)
└── notes[]
    ├── title (string)
    ├── brand_name / brand (string)
    ├── category / industry (string)
    ├── sentiment (string: positive/negative/neutral)
    ├── risk_level (string: critical/high/medium/low/none)
    ├── source_platform / platform (string)
    └── publish_datetime / captured_at / created_at (string)
```

### API 11-13: `/api/trend/*`（ZBCTrendLine）
```
response
└── (趋势数据数组，每项含 date + 对应指标值)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| `INDUSTRY_COLORS` 9 色数组 | overview.html:238 | 业态环形图配色，硬编码 |
| `INDUSTRY_NAMES` 9 业态中英映射 | overview.html:239-244 | 业态名称映射，硬编码 |
| `NINE_INDUSTRY_KEYS` 9 业态白名单 | overview.html:246-247 | P0-R6 数据红线，硬编码 |
| `/ 199 品牌` 文案 | overview.html:362,365,370 | 品牌总数分母，硬编码 |
| `CTH 主体保护` 文案 | overview.html:335 等 | KPI 副标题，硬编码 |
| 30000ms 轮询间隔 | overview.html:762 | 刷新间隔，硬编码 |

## 渲染假设与字段缺失处理
- **KPI 缺失**：`isMissing()` 判断 null/undefined/''/'unknown'/'null'/NaN → 显示 `—` + "数据采集中"，**不显示 0**
- **趋势空数据**：所有数据点 value=0 → 显示 empty 态
- **业态过滤**：`filterNineIndustries()` 严格白名单，非 9 业态 key 一律过滤不渲染
- **风险排序**：`{critical:0, high:1, medium:2, low:3}`，未知排最后
- **权限检查**：`/api/cth/overview` 返回 403 → 隐藏主内容，显示无权限页
- **降级横幅**：任一 API 失败 → `markDegraded()` 显示顶部降级横幅，已加载数据正常显示
- **实时流**：`d.notes` 为空 → empty 态；字段缺失用 `||` 链回退

## 备注
- 本页是 CTH 最复杂页面，共 13 个 API 端点（含 3 个 ZBCTrendLine 全局趋势线）
- 大量使用多级降级链（主源 → 降级源 → 最终降级），确保数据不静默
- 9 业态白名单是 P0 数据红线，禁止用内容分类或平台分布冒充业态
