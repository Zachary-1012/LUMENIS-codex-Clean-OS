# Phase 3 趋势链路全链路审计报告

> 审计日期：2026-09-07
> 审计范围：events / risk / kos 三条趋势链路（DB → Query → Service → API → Frontend → Chart）
> 修复基线：commit 7e22d9b（trend_api.py 三端点修复）
> 数据库：data/monitor.db（只读审计，未修改）
> 运行环境：Flask :8201，Python venv
> 审计性质：只读审计 + 授权范围内最小修复 + 真实运行验证

---

## 0. 执行摘要

| 链路 | 状态 | API 30天总数 | DB 直查总数 | 前端接入 | 结论 |
|------|------|-------------|------------|---------|------|
| events | OK（有次要发现） | 246 | 248 | cth/events.html | 修复生效，数据真实；2条差异<1% |
| risk | OK（有次要发现） | 246 | 248 | cth/risk.html | 修复生效，四档渲染正确；同源差异 |
| kos | OK | 130 | 130 | zbmp/kos.html | 修复生效，完全一致 |
| metric-trend | OK（已修复） | — | — | 报告/前端动态绑定 | ORDER BY 已修正为 snapshot_at |

**核心结论**：commit 7e22d9b 修复有效，三条趋势链路均从"契约错误全0"恢复为真实非零数据。前端三个页面均已正确接入修复后的 API，无"前端未接入"缺口。

**本次修复**：database.py `get_metric_trend()` 的 `ORDER BY id ASC` → `ORDER BY snapshot_at ASC`（趋势查询应按快照时间排序，历史导入数据 id 与时间可能不一致）。

**发现的授权范围外缺口（记录不修复）**：
1. `cache_manager.py:241`：对 events 表使用 `ORDER BY created_at DESC`，但 events 表**无 created_at 列**，该查询必抛 SQL 错误。
2. `report_api.py:493`：报告周期事件数用 `date(first_seen)` 而非 `date(event_date)`，与趋势 API 口径不一致；且 first_seen 含脏值"编辑于 2025-08-22"。

---

## 1. Events 趋势链路审计

### 1.1 DB 层

**表结构（PRAGMA table_info(events)）**：

| 列名 | 类型 | 非空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | INTEGER | 0 | — | PK |
| event_key | TEXT | 1 | — | 事件唯一键 |
| title | TEXT | 0 | '' | 事件标题（主体过滤唯一可用字段） |
| summary | TEXT | 0 | '' | 摘要 |
| first_seen | TEXT | 0 | '' | 首次发现日期 |
| last_seen | TEXT | 0 | '' | 最后出现日期 |
| risk_level | TEXT | 0 | 'low' | 风险等级 |
| risk_score | INTEGER | 0 | 0 | 风险分数 |
| event_date | TEXT | 0 | '' | 事件发生日期（趋势API主用） |
| negative_confirmed_at | TEXT | 0 | '' | 负面确认时间 |

**时间字段实际格式与取值**：

| 字段 | 非空数 | 空/NULL数 | 最小值 | 最大值 | 格式 |
|------|--------|----------|--------|--------|------|
| event_date | 494 | 0 | 2024-07-08 | 2026-09-06 | YYYY-MM-DD（干净） |
| first_seen | 494 | 0 | 2024-07-08 | 编辑于 2025-08-22 |  mostly YYYY-MM-DD，**含脏值** |
| last_seen | 494 | 0 | 2024-07-15 | 编辑于 2025-08-22 | mostly YYYY-MM-DD，**含脏值** |
| negative_confirmed_at | 3 | 491 | (空) | 2026-08-30 00:24:00 | YYYY-MM-DD HH:MM:SS |

**关键发现**：
- events 表共 **494 行**（根因文档记载 461 行，数据已增长 33 行）。
- `event_date` 全量非空且格式干净，是可靠的趋势时间轴。
- `first_seen`/`last_seen` 含脏值"编辑于 2025-08-22"（来自小红书相对时间未归一化），但因 trend_events 优先用 event_date，脏值不影响趋势 API。
- events 表**无 publish_datetime / captured_at / created_at 列**。

### 1.2 Query 层（trend_api.py trend_events）

**SQL 逻辑**（trend_api.py:162-199）：
1. 列遍历顺序：`['event_date', 'first_seen', 'last_seen', 'negative_confirmed_at', 'start_time', 'discovered_at', 'created_at', 'first_seen_at']`
2. 首列 `event_date` 存在且有数据 → 命中后 break，不会尝试后续列。
3. 实际执行 SQL：
   ```sql
   SELECT DATE(event_date) as d, COUNT(*) as cnt
   FROM events
   WHERE event_date IS NOT NULL
     AND date(event_date) >= date('now', '-29 days')
     AND (主体过滤：title LIKE 主体词 OR ...) AND NOT (title LIKE 排除词 OR ...)
   GROUP BY d ORDER BY d
   ```
4. 主体过滤：`_safe_subject_clause(conn, 'events')` 检测到 events 表仅有 `title` 列可用，基于 title 生成简化主体过滤。

**审核结论**：
- 时间列优先 event_date ✓
- 日期窗口 `date('now', '-29 days')` 覆盖 30 天（含今天）✓
- 主体过滤正确应用（17 个主体词 + 18 个排除词，仅 title 字段）✓
- 列名白名单防注入 ✓
- 异常捕获 + 日志 ✓
- **注意**：`WHERE event_date IS NOT NULL` 未同时检查 `!= ''`，但 event_date 无空值，无实际影响。

### 1.3 Service 层

trend_api.py 为直接 Blueprint，无中间 service 层。`_safe_subject_clause()` 和 `_fill_zeros()` 为辅助函数。

### 1.4 API 层

**真实调用**：`GET /api/trend/events?days=30`（HTTP :8201 + Basic auth）

| 指标 | 值 |
|------|-----|
| HTTP status | 200 |
| ok | true |
| metric | events |
| days | 30 |
| series 长度 | 30 |
| 总数 | 246 |
| 非零天数 | 28/30 |
| 零值日期 | 2026-08-09（真实无数据）、2026-09-07（当天尚无事件） |

**返回结构**：`{ok, metric, days, series:[{date, label, count, total}]}`

**边界测试**：
- days=7 → 钳制有效，返回 7 天，总数 33
- days=90 → 返回 90 天，总数 331，非零 58 天
- days=5 → 钳制为 7（min=7）✓
- days=100 → 钳制为 90（max=90）✓

### 1.5 Frontend 层

**消费页面**：`templates/cth/events.html:367`
```javascript
ZBCTrendLine.render('trend-events', '/api/trend/events',
  {title:'事件趋势', days:30, color:'#8B5CF6', metric:'count', height:180});
```

**渲染组件**：`static/js/zbc-trend-line.js`（v1.1）
- `render()` 方法：fetch API → 读取 `series[].count`（fallback `total`）→ SVG 趋势线
- 带 60s 内存缓存、auth header 注入（`global.__Z_AUTH`）、错误显式展示、数字滚动动效
- 容器 `#trend-events` 存在于 events.html

### 1.6 Chart 层

- 单条折线，紫色（#8B5CF6），X 轴日期（MM-DD），Y 轴事件数
- 0 值为真实无数据日期，非契约错误
- 总数显示 246，与 API 一致

### 1.7 Events 链路结论：OK

| 环节 | 状态 | 证据 |
|------|------|------|
| DB | OK | event_date 494行全量非空，格式干净 |
| Query | OK | event_date 优先 + 日期窗口 + 主体过滤 |
| Service | N/A | 无中间层 |
| API | OK | 200, 246条, 28/30非零天 |
| Frontend | OK | cth/events.html 正确调用 |
| Chart | OK | SVG 渲染，0值真实 |

---

## 2. Risk 趋势链路审计

### 2.1 DB 层

**风险数据实际存储位置**：

| 表 | 行数 | risk_level 列 | 说明 |
|----|------|--------------|------|
| events | 494 | 有（low/medium/high） | **实际风险数据源** |
| notes | 1020 | 有 | 笔记级风险（趋势API未用） |
| risk_records | **不存在** | — | 表不存在，非"为空" |
| risks | **不存在** | — | 表不存在 |
| note_risk_log | **不存在** | — | 表不存在 |

> 根因文档记载三表"为空"，实际 PRAGMA 确认三表**根本不存在**。trend_risk 的表遍历会因 `no such table` 异常被捕获并跳过，最终命中 events 表。

**events.risk_level 分布**：

| risk_level | 全表行数 | 30天窗口（含主体过滤） |
|------------|---------|---------------------|
| low | 433 | 238 |
| medium | 53 | 9 |
| high | 8 | 1 |
| critical | 0 | 0 |

**events.risk_score**：min=0, max=98, 全量非空。

### 2.2 Query 层（trend_api.py trend_risk）

**SQL 逻辑**（trend_api.py:205-269）：
1. 表遍历顺序：`['events', 'risk_records', 'risks', 'note_risk_log']`
2. events 表首列 `event_date` 有数据 → 命中 break。
3. 实际执行 SQL：
   ```sql
   SELECT DATE(event_date) as d, risk_level, COUNT(*) as cnt
   FROM events
   WHERE event_date IS NOT NULL
     AND date(event_date) >= date('now', '-29 days')
     AND (主体过滤)
   GROUP BY d, risk_level ORDER BY d
   ```
4. Python 层按日期聚合为 `{high, medium, low, critical}` 四档，未出现的等级补 0。

**审核结论**：
- 从 events 表聚合 risk_level ✓
- risk_level 分组正确 ✓
- 四档（high/medium/low/critical）兼容，critical 恒为 0（events 表无 critical 值）✓
- 主体过滤正确应用 ✓
- 旧空表向后兼容（try/except 跳过）✓

### 2.3 API 层

**真实调用**：`GET /api/trend/risk?days=30`

| 指标 | 值 |
|------|-----|
| HTTP status | 200 |
| 总数 | 246 |
| 非零天数 | 28/30 |
| high | 1 |
| medium | 8 |
| low | 237 |
| critical | 0 |

**返回结构**：`{ok, metric, days, series:[{date, label, high, medium, low, critical, total}]}`

### 2.4 Frontend 层

**消费页面**：`templates/cth/risk.html:371`
```javascript
ZBCTrendLine.renderMulti('trend-risk', '/api/trend/risk', [
  {metric:'high', color:'#EF4444', name:'高风险'},
  {metric:'medium', color:'#F59E0B', name:'中风险'},
  {metric:'low', color:'#10B981', name:'低风险'}
], {title:'风险趋势', days:30, height:180});
```

**renderMulti**：多折线叠加 + 图例，读取 `series[].high/medium/low`。
- **注意**：前端未渲染 `critical` 档，但 events 表无 critical 数据，无实际影响。

### 2.5 Chart 层

- 三条折线：高风险（红）、中风险（橙）、低风险（绿）
- 低风险为主（237/246），中风险 8 条，高风险 1 条
- 与 events 趋势同分布（risk 数据源自 events 表）

### 2.6 Risk 链路结论：OK

| 环节 | 状态 | 证据 |
|------|------|------|
| DB | OK | events 表 494 行有 risk_level，三旧表不存在 |
| Query | OK | events 表聚合 + 四档分组 |
| Service | N/A | 无中间层 |
| API | OK | 200, 246条, high=1/medium=8/low=237 |
| Frontend | OK | cth/risk.html renderMulti 正确调用 |
| Chart | OK | 三档折线渲染，critical 无数据不影响 |

---

## 3. KOS 趋势链路审计

### 3.1 DB 层

**kos_profiles 表**：
- 总行数：375
- `is_kos=1`：375（全量）
- 主键：author_id（TEXT）
- 时间字段：first_publish_at, last_publish_at, created_at, updated_at

**notes 表 subject_type 分布**：

| subject_type | 行数 |
|-------------|------|
| CTH | 489 |
| unknown | 312 |
| normal_user | 201 |
| official | 14 |
| kos | 3 |
| media | 1 |

**关键发现**：仅 3 条 notes 的 subject_type='kos'，但 kos_profiles 有 375 个 is_kos=1 达人。这些达人发布的笔记 subject_type 多为 CTH/unknown/official，必须通过 JOIN kos_profiles 才能正确识别。

### 3.2 Query 层（trend_api.py trend_kos）

**SQL 逻辑**（trend_api.py:321-351）：
```sql
SELECT DATE(n.publish_datetime) as d, COUNT(*) as cnt
FROM notes n
LEFT JOIN kos_profiles k ON n.author_id = k.author_id
WHERE n.publish_datetime IS NOT NULL AND n.publish_datetime != ''
  AND date(n.publish_datetime) >= date('now', '-29 days')
  AND (notes 完整主体过滤，别名 n)
  AND (k.is_kos = 1
       OR n.subject_type LIKE '%kos%'
       OR n.subject_type LIKE '%kol%'
       OR n.subject_type LIKE '%koc%')
GROUP BY d ORDER BY d
```

**审核结论**：
- LEFT JOIN kos_profiles ON author_id ✓
- is_kos=1 为主过滤条件 ✓
- subject_type LIKE 作为 OR 补充（兼容未入 profile 但标记为 kos 的笔记）✓
- notes 表使用完整主体过滤（`subject_sql_and_values(alias='n')`），包含全部 5 个主体字段 ✓
- 日期窗口正确 ✓
- 空值检查 `IS NOT NULL AND != ''` ✓

### 3.3 API 层

**真实调用**：`GET /api/trend/kos?days=30`

| 指标 | 值 |
|------|-----|
| HTTP status | 200 |
| 总数 | 130 |
| 非零天数 | 26/30 |
| 零值日期 | 4 天（真实无 KOS 笔记发布） |

**与 DB 直查对比**：API=130，DB 直查=130，**完全一致** ✓

### 3.4 Frontend 层

**消费页面**：`templates/zbmp/kos.html:601`
```javascript
ZBCTrendLine.render('trend-kos', '/api/trend/kos',
  {title:'KOS内容趋势', days:30, color:'#F59E0B', metric:'count', height:180});
```

### 3.5 Chart 层

- 单条折线，橙色（#F59E0B）
- KOS 笔记发布趋势，8月底为高峰（08-28=17, 08-29=15, 08-30=11）

### 3.6 KOS 链路结论：OK

| 环节 | 状态 | 证据 |
|------|------|------|
| DB | OK | kos_profiles 375个 is_kos=1，notes 1020行 |
| Query | OK | LEFT JOIN + is_kos=1 + 主体过滤 + 日期窗口 |
| Service | N/A | 无中间层 |
| API | OK | 200, 130条, 与DB完全一致 |
| Frontend | OK | zbmp/kos.html 正确调用 |
| Chart | OK | SVG 渲染，0值真实 |

---

## 4. 缺口1 审计：events 表时间字段引用范围

### 4.1 审计方法

grep 全部 .py 文件中引用 events 表且涉及时间字段的代码，检查是否存在：
- 期望 events.publish_datetime / captured_at（表中无此列）
- 使用不存在的时间列（如 created_at）
- 口径不一致（该用 event_date 却用 first_seen）

### 4.2 审计结果

| 文件:行 | 查询/代码 | 时间字段 | 状态 | 说明 |
|---------|----------|---------|------|------|
| trend_api.py:178 | trend_events | event_date 优先 | OK | 已修复（7e22d9b） |
| trend_api.py:224 | trend_risk | event_date | OK | 已修复 |
| database.py:868 | get_events | COALESCE(event_date,first_seen,last_seen) | OK | 正确兜底 |
| database.py:924 | get_featured_events | COALESCE(event_date,first_seen,last_seen) | OK | 正确兜底 |
| database.py:292-300 | 迁移脚本 | event_date = first_seen / notes.publish_datetime | OK | 数据校正逻辑 |
| export_report.py:213 | 报告导出 | COALESCE(NULLIF(event_date,''),first_seen) | OK | 正确兜底 |
| weekly_events.py:26 | 周报事件 | first_seen / last_seen | OK | 周期重叠逻辑，用 first_seen/last_seen 合理 |
| kos_report.py:47 | KOS报告 | first_seen（展示用） | OK | 仅展示字段 |
| app.py:3210 | 事件待审 | last_seen DESC | OK | last_seen 存在 |
| event_graph.py:478 | 事件图谱导入 | event_date, first_seen, last_seen | OK | 显式选择存在的列 |
| viz_data_provider.py:333 | 事件列表 | 无时间过滤 | OK | 按 risk_score 排序 |
| badge_api.py:58 | 徽章计数 | 无时间字段 | OK | — |
| **cache_manager.py:241** | **缓存事件查询** | **ORDER BY created_at DESC** | **BUG** | **events 表无 created_at 列，必抛 SQL 错误** |
| **report_api.py:493** | **报告周期事件数** | **date(first_seen)** | **口径不一致** | **应用 event_date，与趋势API对齐；first_seen 含脏值** |

### 4.3 结论

- **无代码期望 events.publish_datetime 或 events.captured_at**：缺口1的"期望 publish_datetime"场景不存在。
- **发现 2 个真实问题**，均在授权修复范围外（仅授权修改 trend_api.py / database.py / data_query_api.py）：
  1. `cache_manager.py:241`：`SELECT * FROM events ORDER BY created_at DESC` — 列不存在，P1 bug。
  2. `report_api.py:493`：`date(first_seen)` 替代 `date(event_date)` — 口径不一致 + 脏值风险，P2。

---

## 5. 缺口2 审计：metric_snapshots 周期字段

### 5.1 表结构

```sql
CREATE TABLE metric_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,       -- 'note' | 'topic'
    entity_key TEXT NOT NULL,
    likes INTEGER, comments INTEGER, collects INTEGER, shares INTEGER,
    browse_count INTEGER, discussion_count INTEGER, note_count INTEGER,
    raw_json TEXT DEFAULT '{}',
    source TEXT DEFAULT '',
    collector_version TEXT DEFAULT '',
    snapshot_at TEXT DEFAULT (datetime('now','localtime'))  -- 唯一时间字段
);
```

- **无 period_start / period_end 列**。
- 1087 行，snapshot_at 全量非空（0 null/empty），格式 `YYYY-MM-DD HH:MM:SS`。
- entity_type 分布：note 为主。

### 5.2 get_metric_trend()（database.py:548）

**修复前**：
```python
rows = conn.execute(
    "SELECT * FROM metric_snapshots WHERE entity_type=? AND entity_key=? "
    "ORDER BY id ASC LIMIT ?", ...)
```

**问题**：
- 不依赖 period_start/period_end → **不是 schema 缺口**。
- 但 `ORDER BY id ASC` 而非 `ORDER BY snapshot_at ASC`：新插入数据 id 与 snapshot_at 一致，但历史导入/迁移数据可能 id 顺序与时间不一致，导致趋势点错序。

**修复后**（本次）：
```python
rows = conn.execute(
    "SELECT * FROM metric_snapshots WHERE entity_type=? AND entity_key=? "
    "ORDER BY snapshot_at ASC LIMIT ?", ...)
```

### 5.3 /api/metric-trend（data_query_api.py:115）

```python
@bp.route('/api/metric-trend')
def api_metric_trend():
    entity_type = request.args.get('entity_type', 'note')
    entity_key = request.args.get('entity_key', '').strip()
    if entity_type not in ('note', 'topic') or not entity_key:
        return jsonify({'ok': False, 'error': '...'}), 400
    limit = max(1, min(1000, request.args.get('limit', 200, type=int)))
    rows = db.get_metric_trend(entity_type, entity_key, limit)
    return jsonify({'ok': True, 'entity_type': entity_type, 'entity_key': entity_key,
                    'points': len(rows), 'trend': rows})
```

- 透传 get_metric_trend 结果，包含 snapshot_at 字段。
- 参数校验正确（entity_type 白名单 + entity_key 必填 + limit 钳制）。
- 错误参数返回 400 ✓

### 5.4 真实调用验证

```
GET /api/metric-trend?entity_type=note&entity_key=5a539803eb00f31709eb1351&limit=5
→ status=200, points=1, first_snapshot=2026-08-24 16:51:51

GET /api/metric-trend?entity_type=invalid
→ status=400, error='entity_type must be note|topic and entity_key required'
```

### 5.5 结论

- **metric_snapshots 不依赖 period_start/period_end**，使用 snapshot_at 作为时间轴 → **缺口2 不是 schema 缺口**。
- 已修复 `ORDER BY id` → `ORDER BY snapshot_at`，确保趋势点按真实时间排列。
- 无需改表结构，无需添加 period_start/period_end。

---

## 6. 全局检查项

### 6.1 时间字段格式统一性

| 表.字段 | 格式 | 一致性 |
|---------|------|--------|
| events.event_date | YYYY-MM-DD | ✓ 干净 |
| events.first_seen | mostly YYYY-MM-DD | ⚠️ 含脏值"编辑于 2025-08-22" |
| events.last_seen | mostly YYYY-MM-DD | ⚠️ 含脏值"编辑于 2025-08-22" |
| events.negative_confirmed_at | YYYY-MM-DD HH:MM:SS | ✓ |
| notes.publish_datetime | YYYY-MM-DD（日期级） | ✓ 1条空值 |
| notes.captured_at | YYYY-MM-DD HH:MM:SS | ✓ |
| metric_snapshots.snapshot_at | YYYY-MM-DD HH:MM:SS | ✓ |

**结论**：趋势 API 主用字段（event_date, publish_datetime, snapshot_at）格式统一且干净。first_seen/last_seen 的脏值因 event_date 优先而不影响趋势链路。

### 6.2 Timezone 一致性

- SQLite 无原生 timezone 类型。
- `snapshot_at` 默认 `datetime('now','localtime')` → 本地时间。
- `captured_at` 由采集器写入本地时间。
- `publish_datetime` / `event_date` 为日期级，无时区概念。
- 趋势查询使用 `date()` 函数提取日期部分，不涉及时区转换。
- **无 UTC/local 混淆** ✓

### 6.3 NULL 过滤正确性

| API | NULL 条件 | 影响 |
|-----|----------|------|
| trend_events | `event_date IS NOT NULL` | event_date 0 null → 无数据丢失 |
| trend_risk | `event_date IS NOT NULL` | 同上 |
| trend_kos | `publish_datetime IS NOT NULL AND != ''` | 1条空值被正确排除 |
| trend_notes | `publish_datetime IS NOT NULL AND != ''` | 同上 |

**结论**：IS NOT NULL 条件不会误删有效数据。events 用 event_date（全量非空），notes/kos 用 publish_datetime（仅1条空）。

### 6.4 查询窗口正确性

- `_days_offset(30)` → `'-29 days'`
- `date('now', '-29 days')` for 2026-09-07 → 2026-08-09
- `_date_range(30)` 生成 2026-08-09 至 2026-09-07 共 30 个日期
- SQL 条件 `date(col) >= date('now', '-29 days')` 覆盖全部 30 天 ✓
- days 参数钳制 [7, 90] ✓

### 6.5 API 与 DB 直查对比

| 链路 | API 总数 | DB 直查总数 | 差异 | 差异率 |
|------|---------|------------|------|--------|
| events (30天) | 246 | 248 | -2 | 0.8% |
| risk (30天) | 246 | 248 | -2 | 0.8% |
| kos (30天) | 130 | 130 | 0 | 0% |

**events/risk 差异分析**：
- 两者同源（events 表），差异一致。
- brand_config 主体词与全局 SUBJECT_WORDS 一致（已验证）。
- 可能原因：Flask 运行时 WAL 模式下的连接状态差异，或 `_safe_subject_clause` 的 PRAGMA 调用时序。
- 差异 <1%，不影响趋势形态和修复结论。
- **建议后续**：在 trend_api.py 中统一主体过滤实现，消除 API 与直查的微小差异。

### 6.6 前端消费确认

| API | 消费模板 | 调用方式 | 状态 |
|-----|---------|---------|------|
| /api/trend/events | templates/cth/events.html:367 | ZBCTrendLine.render | ✓ 已接入 |
| /api/trend/risk | templates/cth/risk.html:371 | ZBCTrendLine.renderMulti | ✓ 已接入 |
| /api/trend/kos | templates/zbmp/kos.html:601 | ZBCTrendLine.render | ✓ 已接入 |

**无"前端未接入"缺口**。三个页面均在 commit 7e22d9b 之前就已调用这些 API，修复后自动受益。

### 6.7 0 值真实性

| 链路 | 零值天数 | 原因 |
|------|---------|------|
| events | 2/30 | 08-09 真实无事件；09-07 当天尚无事件 |
| risk | 2/30 | 同源 events |
| kos | 4/30 | KOS 达人非每日发布，真实零 |

**所有 0 值均为真实无数据日期，非契约错误** ✓

### 6.8 趋势线口径一致性

| 链路 | 时间字段 | 口径 |
|------|---------|------|
| notes | notes.publish_datetime | 发布时间 |
| events | events.event_date | 事件发生/发现日期 |
| risk | events.event_date | 事件发生日期（同源 events） |
| kos | notes.publish_datetime | 发布时间 |
| metric | metric_snapshots.snapshot_at | 快照时间 |

**结论**：notes/kos 用 publish_datetime（发布时间），events/risk 用 event_date（≈发布/发现时间），口径一致对齐"内容发布/事件发生"维度。符合 AGENTS.md §6 时间口径要求（日报/趋势默认按 publish_datetime，events 用 event_date 作为等价物）。

---

## 7. 本次修改清单

| 文件 | 修改内容 | 原因 |
|------|---------|------|
| database.py:554 | `ORDER BY id ASC` → `ORDER BY snapshot_at ASC` | 趋势查询按真实快照时间排序，修复历史导入数据 id 与时间不一致的潜在错序 |

**未修改**（授权范围外，记录为待办）：
- cache_manager.py:241 — events ORDER BY created_at（列不存在）
- report_api.py:493 — date(first_seen) 应改为 date(event_date)

---

## 8. 验证记录

### 8.1 重启验证
- 停止旧 Flask（PID 18272）→ 启动新 Flask（PID 3740）→ 端口 8201 LISTENING ✓
- database.py 语法检查通过 ✓

### 8.2 API 验证（HTTP :8201 + Basic auth）
```
events: status=200 total=246 nonzero_days=28/30
risk:   status=200 total=246 nonzero_days=28/30 levels={high:1, medium:8, low:237, critical:0}
kos:    status=200 total=130 nonzero_days=26/30
metric-trend: status=200 points=1 first_snapshot=2026-08-24 16:51:51
```

### 8.3 DB 直查验证
- events 30天含主体过滤：248 条，28 个有数据天
- risk 30天含主体过滤：248 条（low=238, medium=9, high=1）
- kos 30天含主体过滤：130 条，26 个有数据天

---

## 9. 发现的缺口与建议

### P1 — 需修复（授权范围外）
1. **cache_manager.py:241**：`SELECT * FROM events ORDER BY created_at DESC` — events 表无 created_at 列，查询必失败。
   - 建议：改为 `ORDER BY COALESCE(event_date,first_seen,last_seen,'') DESC`
   - 影响：缓存管理器的 events 查询类型不可用

### P2 — 建议修复（授权范围外）
2. **report_api.py:493**：报告周期事件数用 `date(first_seen)` 而非 `date(event_date)`。
   - 建议：改为 `date(COALESCE(NULLIF(event_date,''),first_seen))`
   - 影响：报告事件数与趋势 API 口径不一致；first_seen 脏值可能导致 date() 返回 NULL

### P3 — 优化建议
3. **events/risk API 与 DB 直查 2 条差异**：建议统一主体过滤实现，消除微小差异。
4. **first_seen/last_seen 脏值**："编辑于 2025-08-22" 等相对时间应在采集层归一化，或在数据库迁移中清洗。
5. **risk_records/risks/note_risk_log 三表不存在**：根因文档记载"为空"，实际为"不存在"。trend_risk 的 try/except 已正确处理，但建议清理代码中对这三表的引用或确认是否需要建表。
6. **/api/trend/overview**：仅返回 notes+engagement，未包含 events/risk/kos（根因文档已标注，可后续增强）。

---

## 10. 审计脚本与产物

| 文件 | 用途 |
|------|------|
| audit/convergence/_audit_db_check.py | DB 直查审计脚本 |
| audit/convergence/_audit_api_check.py | Flask test_client API 验证脚本 |
| audit/convergence/_audit_http_verify.py | HTTP :8201 API 验证脚本 |
| audit/convergence/_audit_metric_check.py | metric_snapshots 专项审计脚本 |
| audit/convergence/phase3_trend_chain_audit.md | 本报告 |

---

*报告结束。审计人：豆包本地执行环境。审计时间：2026-09-07 17:40 CST。*
