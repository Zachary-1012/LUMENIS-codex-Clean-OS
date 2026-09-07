# Phase 8: ZBC 阶段2 DB生命周期 + 阶段3趋势闭环 只读验证证据

> 生成时间: 2026-09-07
> 数据库: `data/monitor.db` (SQLite, 只读 mode=ro)
> Flask: http://127.0.0.1:8201 (Basic auth)
> 验证方式: sqlite_master 实数查询 + curl 真实端点调用 + DB直查核对
> 约束: 禁止 pytest / 禁止修改文件 / 禁止删除或清空DB

---

## 1. DB实数表（阶段2生命周期核对）

### 1.1 表总数

| 指标 | 数量 | 说明 |
|------|------|------|
| sqlite_master 总表数 | **129** | `SELECT name FROM sqlite_master WHERE type='table'` |
| 业务表数（排除系统表） | **128** | 排除 `sqlite_sequence` |
| 系统表数 | **1** | `sqlite_sequence`（51行，追踪51张AUTOINCREMENT表） |

### 1.2 非空/空表分布

| 指标 | 数量 | 占比 |
|------|------|------|
| 非空表（行数>0） | **64** | 50.0% |
| 空表（行数=0） | **64** | 50.0% |
| 业务表合计 | **128** | 100% |

> **与 phase2 V2 文档差异**: V2记录为63非空/65空。当前实数为64/64，差异原因：自V2生成（2026-09-07 17:46）以来有1张原空表获得数据写入，属实时数据增长，非分类错误。

### 1.3 非空表 TOP10

| 排名 | 表名 | 行数 |
|------|------|------|
| 1 | schedule_decisions | 15,427 |
| 2 | note_review_history | 8,387 |
| 3 | ai_task_trace | 7,022 |
| 4 | ai_task_step | 5,584 |
| 5 | ai_task_evidence | 3,405 |
| 6 | runtime_guardian_workers | 2,943 |
| 7 | ai_task | 2,436 |
| 8 | ai_call_logs | 1,746 |
| 9 | browser_evidence | 1,629 |
| 10 | metric_snapshots | 1,087 |

### 1.4 空表分类（64张）

| 分类 | 数量 | 说明 |
|------|------|------|
| 全平台预留表（Adapter Raw层） | **32** | 11个平台前缀：bilibili/douyin/instagram/x/zhihu/reddit/tiktok/youtube/linkedin/github/channels |
| 统一平台表（Canonical汇聚层） | **4** | platform_accounts / platform_comments / platform_contents / platform_evidence |
| 其他空表 | **28** | 功能就绪待数据(15) + 预留扩展(含brands/collection_quality_log/event_graph_relations等) + MIGRATE(7) + DEPRECATE(3) |
| **空表合计** | **64** | |

#### 全平台预留表清单（32张）
bilibili_comments, bilibili_users, bilibili_videos, channels_comments, channels_videos, douyin_comments, douyin_users, douyin_videos, github_issues, github_pull_requests, github_releases, github_repositories, instagram_comments, instagram_media, instagram_users, linkedin_posts, linkedin_users, reddit_comments, reddit_posts, reddit_subreddits, tiktok_comments, tiktok_users, tiktok_videos, x_posts, x_users, youtube_channels, youtube_comments, youtube_videos, zhihu_answers, zhihu_articles, zhihu_comments, zhihu_questions

#### 统一平台表清单（4张）
platform_accounts, platform_comments, platform_contents, platform_evidence

### 1.5 生命周期分类计数（实数核对）

| 分类 | 数量 | 实数验证 |
|------|------|----------|
| **KEEP** | **118** | 生产核心表 + 平台预留 + 功能就绪待数据 |
| **MIGRATE** | **7** | 全部0行，逐一确认：brand_propagation_entities, brand_propagation_events, collection_runs, content_analysis, creators, evaluation_records, professional_metrics |
| **DEPRECATE** | **3** | 全部0行，逐一确认：xhs_note_comments, xhs_notes, xhs_users |
| **DELETE-CANDIDATE** | **0** | 无符合"无引用+无数据+无业务用途"严格标准的表 |
| **业务表合计** | **128** | 118+7+3+0=128 ✓ |

> 分类基线参考 `audit/convergence/phase2_db_lifecycle_v2.md`，本次用当前实数逐一核对MIGRATE和DEPRECATE表的行数，全部确认为0行，与V2一致。

### 1.6 128/129口径差异核对

| 口径 | 数量 | 原因 |
|------|------|------|
| 用户口径"129张表" | 129 | 包含 `sqlite_sequence` 系统表 |
| 业务表口径"128张表" | 128 | 排除 `sqlite_sequence` |
| 差异来源 | 1张 | `sqlite_sequence` 是SQLite内部系统表，存储AUTOINCREMENT序列号，非业务表，不参与生命周期分类 |

- `sqlite_sequence` 当前 **51行**（V2记录为50行，新增1张AUTOINCREMENT表）
- 结论：**128/129差异已澄清，非数据错误，是系统表是否计入的口径差异**

---

## 2. 4个趋势端点验证表（阶段3趋势闭环）

### 2.1 端点验证汇总

| 端点 | HTTP状态码 | 返回总条数 | 时间字段 | 日期范围 | 结论 |
|------|-----------|-----------|----------|----------|------|
| `/api/trend/notes?days=30` | **200** | **235** | `publish_datetime` | 2026-08-09 ~ 2026-09-07 | 契约修复后有数据，非真0 |
| `/api/trend/events?days=30` | **200** | **247** | `event_date`（优先） | 2026-08-09 ~ 2026-09-07 | 契约修复后有数据，非真0 |
| `/api/trend/risk?days=30` | **200** | **247** | `event_date`（继承events） | 2026-08-09 ~ 2026-09-07 | 契约修复后有数据，非真0 |
| `/api/trend/kos?days=30` | **200** | **130** | `notes.publish_datetime` | 2026-08-09 ~ 2026-09-07 | 契约修复后有数据，非真0 |

### 2.2 各端点详细证据

#### 端点1: `/api/trend/notes?days=30`
- **HTTP状态**: 200
- **返回结构**: `{ok:true, metric:"notes", days:30, series:[{date, label, count, total}]}`
- **总条数**: 235（30天daily count求和）
- **时间字段**: `publish_datetime` — 源码 `trend_api.py:136` 确认 `SELECT DATE(publish_datetime) ... FROM notes WHERE publish_datetime IS NOT NULL`
- **主体过滤**: 有（`_subject_clause()`）
- **日期范围**: 最早 2026-08-09，最晚 2026-09-07
- **峰值日**: 2026-08-28（27条）
- **判断**: 契约修复后有数据，**非真实0**

#### 端点2: `/api/trend/events?days=30`
- **HTTP状态**: 200
- **返回结构**: `{ok:true, metric:"events", days:30, series:[{date, label, count, total}]}`
- **总条数**: 247
- **时间字段**: `event_date` — 源码 `trend_api.py:173` 确认优先使用 `event_date`，降级链：event_date → first_seen → last_seen → negative_confirmed_at → start_time → discovered_at → created_at → first_seen_at
- **主体过滤**: 有（`_safe_subject_clause(conn, 'events')`）
- **日期范围**: 最早 2026-08-09，最晚 2026-09-07
- **峰值日**: 2026-08-28（25条）
- **判断**: 契约修复后有数据，**非真实0**

#### 端点3: `/api/trend/risk?days=30`
- **HTTP状态**: 200
- **返回结构**: `{ok:true, metric:"risk", days:30, series:[{date, label, high, medium, low, critical, total}]}`
- **总条数**: 247（与events趋势总数一致，因数据源同为events表）
- **数据源**: `events.risk_level` — 源码 `trend_api.py:214` 确认表优先级：events → risk_records → risks → note_risk_log；**`risk_records`表不存在**（DB直查确认），实际命中 `events` 表
- **时间字段**: `event_date`（继承events表查询的时间列）
- **30天风险分布**:
  | 等级 | 条数 | 占比 |
  |------|------|------|
  | high | 1 | 0.4% |
  | medium | 8 | 3.2% |
  | low | 238 | 96.4% |
  | critical | 0 | 0.0% |
  | **合计** | **247** | 100% |
- **日期范围**: 最早 2026-08-09，最晚 2026-09-07
- **high出现日**: 2026-09-05（1条）
- **判断**: 契约修复后有数据，**非真实0**；数据源确认为events.risk_level，risk_records表不存在

#### 端点4: `/api/trend/kos?days=30`
- **HTTP状态**: 200
- **返回结构**: `{ok:true, metric:"kos", days:30, series:[{date, label, count, total}]}`
- **总条数**: 130
- **时间字段**: `notes.publish_datetime` — 源码 `trend_api.py:329` 确认 `SELECT DATE(n.publish_datetime) ... FROM notes n`
- **JOIN确认**: `LEFT JOIN kos_profiles k ON n.author_id = k.author_id`（源码 `trend_api.py:331`）
- **KOS过滤条件**: `k.is_kos = 1 OR n.subject_type LIKE '%kos%' OR n.subject_type LIKE '%kol%' OR n.subject_type LIKE '%koc%'`（源码 `trend_api.py:342`）
- **主体过滤**: 有（`_subject_clause(alias='n')`）
- **日期范围**: 最早 2026-08-09，最晚 2026-09-07
- **峰值日**: 2026-08-28（17条）
- **判断**: 契约修复后有数据，**非真实0**；LEFT JOIN kos_profiles确认生效

---

## 3. DB直查核对表

### 3.1 核心表数据核对

| 核对项 | 查询语句 | 结果 |
|--------|----------|------|
| notes表总行数 | `SELECT COUNT(*) FROM notes` | **1,020** |
| notes publish_datetime非空 | `SELECT COUNT(*) FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != ''` | **1,019**（1行publish_datetime为空） |
| notes publish_datetime范围 | `SELECT MIN/MAX(publish_datetime) FROM notes` | 最早 **2018-01-08**，最晚 **2026-09-07** |
| events表总行数 | `SELECT COUNT(*) FROM events` | **494** |
| events event_date非空 | `SELECT COUNT(*) FROM events WHERE event_date IS NOT NULL AND event_date != ''` | **494**（100%非空） |
| events event_date范围 | `SELECT MIN/MAX(event_date) FROM events` | 最早 **2024-07-08**，最晚 **2026-09-06** |
| risk_records表是否存在 | `SELECT name FROM sqlite_master WHERE type='table' AND name='risk_records'` | **不存在**（False） |
| kos_profiles表总行数 | `SELECT COUNT(*) FROM kos_profiles` | **375** |
| kos_profiles is_kos=1 | `SELECT COUNT(*) FROM kos_profiles WHERE is_kos=1` | **375**（100%标记为KOS） |

### 3.2 events表risk_level全量分布（非30天窗口）

| risk_level | 行数 | 占比 |
|------------|------|------|
| high | 8 | 1.6% |
| medium | 53 | 10.7% |
| low | 433 | 87.7% |
| critical | 0 | 0.0% |
| **合计** | **494** | 100% |

> 注：30天窗口内 high=1, medium=8, low=238（见2.2端点3），全量表 high=8, medium=53, low=433。差异因30天窗口仅覆盖近期数据。

### 3.3 端点数据与DB直查交叉验证

| 验证点 | 端点返回 | DB直查 | 一致性 |
|--------|----------|--------|--------|
| notes趋势时间字段 | publish_datetime | notes有publish_datetime列，1019/1020非空 | ✓ 一致 |
| events趋势时间字段 | event_date | events有event_date列，494/494非空 | ✓ 一致 |
| risk趋势数据源 | events.risk_level | risk_records不存在，events有risk_level列 | ✓ 一致 |
| kos趋势JOIN | LEFT JOIN kos_profiles | kos_profiles存在，375行is_kos=1 | ✓ 一致 |
| risk趋势总数=events趋势总数 | 均为247 | 同源events表，按相同时间列聚合 | ✓ 逻辑一致 |

---

## 4. 结论

### 4.1 阶段2 DB生命周期：**VERIFIED ✓**

| 验证项 | 结果 |
|--------|------|
| 业务表总数 | 128张（129含系统表sqlite_sequence） |
| 非空/空表 | 64非空 / 64空（V2记录63/65，实时增长1张） |
| 空表分类 | 32全平台预留 + 4统一平台 + 28其他 |
| 生命周期分类 | KEEP=118, MIGRATE=7, DEPRECATE=3, DELETE-CANDIDATE=0 |
| MIGRATE表实数核对 | 7张全部0行 ✓ |
| DEPRECATE表实数核对 | 3张全部0行 ✓ |
| 128/129口径差异 | 已澄清：sqlite_sequence系统表是否计入 |

### 4.2 阶段3趋势闭环：**VERIFIED ✓**

| 验证项 | 结果 |
|--------|------|
| 4个端点HTTP状态 | 全部200 ✓ |
| 4个端点返回数据 | 全部非0（notes=235, events=247, risk=247, kos=130） |
| notes时间字段 | publish_datetime ✓ |
| events时间字段 | event_date（优先） ✓ |
| risk数据源 | events.risk_level，risk_records不存在 ✓ |
| kos JOIN | LEFT JOIN kos_profiles ON author_id ✓ |
| 主体过滤 | 4个端点均有主体过滤 ✓ |
| 日期范围 | 全部覆盖2026-08-09 ~ 2026-09-07（30天） ✓ |
| 真实0 vs 契约修复 | 全部为"契约修复后有数据"，无真实0 ✓ |

### 4.3 总体结论

**阶段2 DB生命周期 + 阶段3趋势闭环 = 双 VERIFIED**

- 阶段2：128张业务表分类基线与当前实数一致，MIGRATE/DEPRECATE表全部确认为0行，128/129口径差异已澄清为系统表计入问题。
- 阶段3：4个趋势端点全部返回200且有真实数据，时间字段口径与源码实现一致，risk数据源确认为events.risk_level（risk_records不存在），kos端点LEFT JOIN kos_profiles生效。
- 全程只读：未运行pytest，未修改任何源码/配置/DB文件，未删除或清空任何表。

---

## 附录：执行命令记录

```sql
-- 表清单
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- 逐表计数
SELECT COUNT(*) FROM "<table_name>";

-- 趋势核对
SELECT COUNT(*) FROM notes WHERE publish_datetime IS NOT NULL AND publish_datetime != '';
SELECT MIN(publish_datetime), MAX(publish_datetime) FROM notes WHERE publish_datetime IS NOT NULL;
SELECT COUNT(*) FROM events WHERE event_date IS NOT NULL AND event_date != '';
SELECT MIN(event_date), MAX(event_date) FROM events WHERE event_date IS NOT NULL;
SELECT risk_level, COUNT(*) FROM events GROUP BY risk_level ORDER BY risk_level;
SELECT name FROM sqlite_master WHERE type='table' AND name='risk_records';
SELECT COUNT(*) FROM kos_profiles WHERE is_kos=1;
```

```bash
# 端点调用（curl.exe，PowerShell环境需显式指定exe）
curl.exe -s -u Zachary:Zachary01 "http://127.0.0.1:8201/api/trend/notes?days=30"
curl.exe -s -u Zachary:Zachary01 "http://127.0.0.1:8201/api/trend/events?days=30"
curl.exe -s -u Zachary:Zachary01 "http://127.0.0.1:8201/api/trend/risk?days=30"
curl.exe -s -u Zachary:Zachary01 "http://127.0.0.1:8201/api/trend/kos?days=30"
```
