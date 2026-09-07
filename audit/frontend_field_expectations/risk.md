# 前端字段期望审计 · risk（风险中心）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/risk.html`（379 行）
- **路由**：`/lumenis/cth/risk`
- **初始化触发**：`DOMContentLoaded` → `loadRiskAll()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/negative/stats` | GET | risk.html:152 | KPI + 风险等级环形图（主源） |
| 2 | `/api/negative-review/stats` | GET | risk.html:173 | 风险类型分布环形图 |
| 3 | `/api/negative/pending` | GET | risk.html:194 | 风险列表（主源），参数 type/level/limit |
| 4 | `/api/trend/notes` | GET | ZBCTrendLine | 全局趋势线 |
| 5 | `/api/trend/engagement` | GET | ZBCTrendLine | 全局趋势线 |
| 6 | `/api/trend/sentiment` | GET | ZBCTrendLine | 全局趋势线 |

## 期望响应字段树

### API 1: `/api/negative/stats`
```
response
├── stats / data (直接对象)
│   ├── pending / pending_count (number)
│   ├── processing / processing_count (number)
│   ├── resolved / resolved_count (number)
│   ├── avg_response_time (number, 单位 min)
│   └── (FN_RISK_COUNT 解析: critical/high/medium/low 分布)
```

### API 2: `/api/negative-review/stats`
```
response
├── stats / data
│   └── by_type / type_distribution (object)
│       └── {type_key: count} — key: diffusion/safety/discrimination/koc_concentration/negative/service/other
```

### API 3: `/api/negative/pending`
```
response
├── negatives[] / data[] / items[]
│   ├── id / risk_id (string/number)
│   ├── title (string)
│   ├── type / risk_type (string)
│   ├── level / risk_level (string: critical/high/medium/low/unknown)
│   ├── status (string: pending/open/processing/investigating/resolved/closed/dismissed)
│   ├── brand_name / brand (string)
│   ├── source_platform / platform (string)
│   ├── description / content (string)
│   ├── created_at / detected_at (string)
│   └── note_url / url (string)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| 风险类型 7 类映射 | risk.html:6-15,146 | diffusion/safety/discrimination/koc_concentration/negative/service/other |
| 风险等级 5 级映射 | risk.html:16-23,144 | critical/high/medium/low/unknown |
| 状态标签颜色映射 | risk.html:145 | pending/open→high, processing/investigating→medium, resolved/closed→low |
| 环形图配色 | risk.html:161-164,178 | 硬编码颜色数组 |
| "CTH 专项风险策略已启用"横幅 | risk.html:36 | 硬编码文案 |

## 渲染假设与字段缺失处理
- KPI 字段双路径回退：`stats.pending != null ? stats.pending : stats.pending_count`
- KPI 缺失 → `—` + "数据采集中"
- 列表数据三路径回退：`d.negatives || d.data || d.items || []`
- 环形图无数据 → "数据采集中…"
- 类型分布全 0 → "数据采集中…"
- 详情面板未选择 → placeholder 态

## 备注
- 风险类型与等级筛选通过 query params 传递
- 支持风险详情弹窗（完整字段展示）
- CTH 风险策略与 ZBMP 隔离（横幅声明）
