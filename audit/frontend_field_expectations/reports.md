# 前端字段期望审计 · reports（报告中心）

> 审计时间：2026-09-08 · 只读静态分析

## 页面信息
- **模板文件**：`templates/cth/reports.html`（341 行）
- **路由**：`/lumenis/cth/reports`
- **初始化触发**：`DOMContentLoaded` → `loadReportsAll()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/weekly/events` | GET | reports.html:203 | 周报列表（数据源 1） |
| 2 | `/api/special-report/check-trigger` | GET | reports.html:204 | 专报列表（数据源 2） |
| 3 | `/api/reports/{id}` | GET | reports.html:314 | 报告预览内容 |
| 4 | `/api/daily` | POST | reports.html:301 (via REPORT_TYPES) | 生成日报 |
| 5 | `/api/weekly/events` | POST | reports.html:301 | 生成周报 |
| 6 | `/api/reports` | POST | reports.html:301 | 生成月报 |
| 7 | `/api/special-report/generate` | POST | reports.html:301 | 生成事件/风险/商业专报 |
| 8 | `{file_path}` (HEAD) | HEAD | reports.html:322 | 下载前文件存在性验证 |

## 期望响应字段树

### API 1: `/api/weekly/events`
```
response
└── events[]
    ├── id (string/number)
    ├── title / name (string)
    ├── range (string, 默认 '7d')
    ├── created_at / date (string)
    ├── file_size (number, bytes)
    ├── file_path / url (string)
    ├── file_exists (bool)
    └── status (string: completed/generating/pending/failed)
```

### API 2: `/api/special-report/check-trigger`
```
response
└── reports[]
    ├── id / report_id (string)
    ├── title / name (string)
    ├── type (string: event/risk/intelligence)
    ├── range (string)
    ├── created_at / generated_at (string)
    ├── file_size (number)
    ├── file_path / url (string)
    ├── file_exists (bool)
    └── status (string)
```

### API 3: `/api/reports/{id}`
```
response
└── content (string — 报告正文文本/HTML)
```

## 硬编码数据
| 内容 | 位置 | 说明 |
|---|---|---|
| REPORT_TYPES 6 类映射 | reports.html:184 | daily→/daily, weekly→/weekly/events, monthly→/reports, event/risk/intelligence→/special-report/generate |
| 时间范围 4 档 | reports.html:121-126,287 | today/7d/30d/90d，默认 7d |
| 输出格式 3 种 | reports.html:134-138 | pdf/docx/html，默认 pdf |
| 生成进度条模拟 | reports.html:299 | `Math.random()*15` 模拟进度，硬编码 |
| 向导步骤 UI | reports.html:79-84 | 3 步向导，硬编码 |

## 渲染假设与字段缺失处理
- 两个数据源并行 `Promise.all`，任一失败 `.catch(()=>null)` 不阻断另一源
- 报告字段多别名回退：`ev.id || ('weekly-'+Date.now())`，`ev.title || ev.name || '周报'`
- file_exists 三态：true→✓存在, false→✗缺失, null→未验证
- KPI 由前端从 reports 数组 filter 计算，非后端直接返回
- 生成进度条是前端模拟（非真实进度），到 90% 封顶等 API 返回
- 下载前必须 HEAD 验证文件存在，不存在则 alert

## 备注
- 报告列表由两个不同 API 聚合而成（周报 + 专报），无统一 `/api/reports/list`
- 生成报告走不同端点取决于类型
- 日报 KPI 始终为 0（因为不从 `/api/daily` 拉列表）
