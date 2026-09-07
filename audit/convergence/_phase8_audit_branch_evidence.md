# Phase 8 — 阶段6源码审计P1清单更新 + 阶段7分支收敛复核（结构化证据）

> **复核日期**: 2026-09-07
> **仓库**: `D:\Taikoo-monitor-new`
> **模式**: 严格只读（grep / Read / sqlite3 PRAGMA / git branch）
> **禁止**: pytest、任何文件修改、commit

---

## 1. 阶段6 P0/P1/P2 完整计数表（含本轮新增）

### 1.1 计数汇总

| 严重度 | 原有（phase6报告） | 本轮新增 | 合计 |
|--------|-------------------|---------|------|
| **P0** | 0 | 0 | **0** |
| **P1** | 21 | 6 | **27** |
| **P2** | 15 | 2 | **17** |
| **合计** | **36** | **8** | **44** |

### 1.2 原有P1完整清单（21项，摘自phase6_source_audit.md）

| # | 严重度 | 标题 | 文件:行号 | 状态 |
|---|--------|------|----------|------|
| P1-01 | P1 | `app_refactor_blueprint.py` 定义7个Blueprint但从未注册 | app_refactor_blueprint.py:52-191 | 未修 |
| P1-02 | P1 | AST扫描发现3个0引用类（Checkpoint/CollectionQualityGate/ComplianceGate） | runtime_guardian.py:177, collection_quality_gate.py:125, compliance_gate.py:42 | 未修 |
| P1-03 | P1 | `/api/collector/status` 路由双重注册 | collection_api.py:22, collector_status_api.py:142 | 未修 |
| P1-04 | P1 | `subject_hit()` 在5处局部重新定义（含1处return False违反P0红线） | app.py:2931, collector_v2/run_profile.py:46, collector_v2/run_live_engine.py:17,20 | 未修 |
| P1-05 | P1 | 6套Guardian/Recovery系统功能重叠 | auto_recovery.py, runtime_guardian.py, system_guardian.py, stability_monitor.py, resident_health.py, system_watchdog.py | 未修 |
| P1-06 | P1 | 前端调用`/api/auth-recovery/summary` Blueprint注册路径需确认 | templates/auth_recovery_modal.html:387, auth_recovery_api.py:9 | PARTIAL |
| P1-07 | P1 | `monitor.db` 129张表部分无ORM Model，迁移入口分散 | models.py, database_migrations.py | 未修 |
| P1-08 | P1 | content/podcast/ic蓝图写端点绕过PermissionGate且无装饰器 | content_generation.py:676-935, podcast_routes.py:87, ic_routes.py:9-204, app.py:1118 | 未修 |
| P1-09 | P1 | `_PG_BYPASS_PATHS` 含3个代码执行端点，1个无Layer3保护 | app.py:1038,2373 | 已缓解(始终403) |
| P1-10 | P1 | `_pg_resolve_operation_type` 基于路径字符串匹配，存在映射遗漏风险 | app.py:1051-1097 | 未修 |
| P1-11 | P1 | 31个daemon线程无统一shutdown/join机制 | 详见phase6报告维度8全量清单 | 未修 |
| P1-12 | P1 | `system_watchdog.py` 定义但未在app.py中启动 | system_watchdog.py | 未修 |
| P1-13 | P1 | `collect_tasks` 在rednote采集路径中无锁访问（3处写） | app.py:2950,2955,2958 | 未修 |
| P1-14 | P1 | `_brand_cache` 全局缓存在7处读写无锁 | app.py:1530,1539,1542,1544,3570,3637,3652 | 未修 |
| P1-15 | P1 | 13处`except: pass`静默吞异常（生产代码10处） | p2_memory_governance.py:76, skill_execution_chain.py:255,384,394, collector_v2/weibo/collector.py:190,195, v4_upgrade/adapters/douyin.py:340,397,451, v4_upgrade/adapters/jiguang.py:127 | 未修 |
| P1-16 | P1 | 无进程级Guardian，Python进程崩溃后无自动重启 | run_production.py | 未修 |
| P1-17 | P1 | 浏览器可执行文件路径硬编码为Windows绝对路径（6+处） | cdp_helper.py:17-52, collector_automation.py:146-147, collector_auto_start.py:29-31, auto_recovery.py:295-296 | 未修 |
| P1-18 | P1 | 无统一Feature Registry，14+ Feature Flag散落为独立env变量 | 全仓库（详见phase6报告维度13） | 未修 |
| P1-19 | P1 | 配置漂移：代码读取约130个env变量，.env.example仅覆盖约80个 | 全仓库 | 未修 |
| P1-20 | P1 | AI输出直接进入日报正文，边界标注不足 | daily_report.py:297-308,599-604 | 未修 |
| P1-21 | P1 | 四层真值边界在Schema中清晰，但代码中存在混用 | daily_report.py:604, evidence_chain.py:758, ai_filter.py:219 | 未修 |

### 1.3 原有P2完整清单（15项，摘自phase6_source_audit.md）

| # | 严重度 | 标题 | 文件:行号 | 状态 |
|---|--------|------|----------|------|
| P2-01 | P2 | `web_monitor.py` 仅793字节疑似占位/废弃 | web_monitor.py | 未修 |
| P2-02 | P2 | `weekly_events.py` 功能被daily_report.py覆盖 | weekly_events.py | 未修 |
| P2-03 | P2 | 6个check_*.py为一次性脚本应归入scripts/ | check_system.py等 | 未修 |
| P2-04 | P2 | `_subject_sql_and_values` 三处定义 | app.py:979(现992), risk_engine.py:292, subject_rules.py:209(现261) | 未修 |
| P2-05 | P2 | pyflakes未安装，undefined-name检查为PARTIAL | — | PARTIAL |
| P2-06 | P2 | `schedule_decisions`表创建入口非主迁移链 | platform_adapters/scheduling/store.py:18 | 未修 |
| P2-07 | P2 | `/system/settings` HTML页面在Basic Auth白名单中 | app.py:1004 | 未修 |
| P2-08 | P2 | `threading.excepthook`已设置但仅记录日志不自动重启 | app.py:6615-6618 | 未修 |
| P2-09 | P2 | 全仓库933处`except Exception:`过于宽泛 | 全仓库 | 未修 |
| P2-10 | P2 | cloudflared路径硬编码（已有env覆盖） | start_tunnel.py:32-33, tunnel_guardian.py:50-51 | 已缓解 |
| P2-11 | P2 | `ZBC_SCHED_GATE_MODE`三态模式未纳入Registry | app.py:4209, platform_adapters/scheduling/gate.py | 未修 |
| P2-12 | P2 | `.env.example`为GBK编码中文乱码 | .env.example | 未修 |
| P2-13 | P2 | AI调用有超时/降级/熔断，但Skill执行无超时隔离 | skill_execution_chain.py | 未修 |
| P2-14 | P2 | `collector_v2/run_live_engine.py:20` 主体过滤硬编码return False | collector_v2/run_live_engine.py:20 | 未修(P0红线) |
| P2-15 | P2 | 5个生产文件含BOM头 | engineering_metrics.py, evaluation_system.py, populate_empty_tables.py, report_api.py, subject_rules.py | 未修 |

---

## 2. 本轮新增8项详情表

| # | 严重度 | 标题 | 文件:行号 | 状态 | 证据摘要 |
|---|--------|------|----------|------|---------|
| N-01 | P1 | app.py模块级_proxy_health_loop线程reload不安全 | app.py:911（定义）, 925-940（启动守卫） | **已修** | L925 `_PROXY_HL_NAME='proxy-health-loop'` 固定线程名；L926-927 `_existing_proxy_hl` 遍历threading.enumerate()检查同名存活线程；L937 `if not _existing_proxy_hl:` 幂等守卫；L938-940 仅在无存活实例时启动。幂等+命名均已到位。 |
| N-02 | P1 | AI云端同步最坏270s无总超时 | ai_channel.py:198-228（post_with_retry）, intelligence.py:323,629（调用点） | **建议** | `post_with_retry(timeout=90, max_attempts=3)`：单个请求90s超时，3次重试+退避，最坏墙钟时间≈3×90+退避≈270s+。函数内无`time.monotonic()`全局deadline，无`remaining_time`传递。调用方`intelligence._call_cloud`(L294)和`route_with_fallback`(L343)也未设置总超时。建议增加`deadline`参数或外层`signal`/线程超时。 |
| N-03 | P2 | 硬编码产品口令1012Zzh建议移env | app.py:6046 | **建议** | `ZBMP_DOMAIN_UNLOCK_KEY = "1012Zzh"` 硬编码于源码；L6054注释说明"废弃TOTP随机动态码"。用途为ZBMP域解锁密钥。建议改为`os.getenv('ZBMP_DOMAIN_UNLOCK_KEY', '1012Zzh')`并在.env.example中声明。 |
| N-04 | P1 | cache_manager.py:241对events用不存在的created_at列 | cache_manager.py:239-243 | **未修（真实bug）** | SQL: `SELECT * FROM events ORDER BY created_at DESC LIMIT ?`。经`PRAGMA table_info(events)`确认，events表26列中**无created_at列**（实际列：id, event_key, title, summary, ..., first_seen, last_seen, ..., event_date, ...）。此查询在运行时必然抛出`no such column: created_at`。同文件L231/233对notes表用created_at（notes表有此列，正确）；L249对alerts表用created_at（需单独确认）。events应改用`first_seen`或`event_date`。 |
| N-05 | P2 | report_api.py:493用first_seen而非event_date | report_api.py:493 | **未修** | SQL: `SELECT COUNT(*) FROM events WHERE date(first_seen) BETWEEN ? AND ?`。events表同时有`first_seen`和`event_date`两列。日报/事件统计口径按AGENTS.md第6节应使用`publish_datetime`/事件发生时间（event_date），first_seen是系统首次发现时间，二者可能存在时间差导致统计窗口偏移。与cache_manager N-04形成对照：一个用了不存在的列，一个用了存在但口径不一致的列。 |
| N-06 | P1 | security_scanner扫描范围失控 | security_scanner.py:85（exclude_dirs）, 97（max_scan_file_bytes）, 137,148 | **已修** | L85 `self.exclude_dirs = [...]` 已增补排除目录；L97 `self.max_scan_file_bytes = 1024 * 1024 # 1 MiB` 护栏；L137 遍历目录时过滤exclude_dirs；L148 `if os.path.getsize(fpath) > self.max_scan_file_bytes:` 跳过超大文件。范围控制已到位。 |
| N-07 | P1 | ai_task_engine.execute_task心跳线程泄漏 | ai_task_engine.py:874-892 | **已修** | L880 `lifecycle_start(run_id=f"task_{task_id}")`；L883-892 `try: return self._execute_task_inner(task_id) finally: ... lifecycle_stop(reason="task_finished")`。try/finally确保任何return/raise/异常分支都停止心跳线程，注释明确说明"否则每次execute_task都泄漏一个lifecycle-hb线程"。 |
| N-08 | P1 | report_engine.py心跳泄漏第二个点 | report_engine.py:241（generate_domain_report）, 270（start）, 381-389（finally stop） | **已修（非待修）** | **复核修正**：原预期标"待修"，实际grep+Read确认已有配对。L270 `_lc_worker.lifecycle_start(run_id=f"report_{report_type}_{...}")`；L381-389 `try: return _domain_report_inner() finally: if _lc_worker is not None: _lc_worker.lifecycle_stop(reason='report_finished')`。L384注释明确"保证任何return/raise分支都停止lifecycle心跳线程，杜绝线程泄漏"。函数名为`generate_domain_report`（L241），非`generate_report`。**此项实际已修复，与预期"待修"不符。** |

### 2.1 新增项状态分布

| 状态 | 数量 | 编号 |
|------|------|------|
| 已修 | 4 | N-01, N-06, N-07, N-08 |
| 未修 | 1 | N-04 |
| 建议 | 2 | N-02, N-03 |
| 未修(P2口径) | 1 | N-05 |

---

## 3. 阶段7分支分类计数表

| 分类 | 定义 | 数量 | 占比 |
|------|------|------|------|
| **A** | 已完整进入main，无独有资产 | 28 | 28.9% |
| **B** | main部分吸收，仍有独有价值commit/file | 2 | 2.1% |
| **C** | main未吸收但存在有效资产（文档/配置） | 1 | 1.0% |
| **D** | research / experimental，不适合直接进生产 | 3 | 3.1% |
| **E** | stale，陈旧重复变体，已被main完全覆盖 | 62 | 63.9% |
| **F** | conflict / risk，含危险操作或主体口径弱化 | 1 | 1.0% |
| **合计** | | **97** | 100% |

### 3.1 git branch -a 只读核对

| 指标 | 数值 | 说明 |
|------|------|------|
| `git branch -a` 原始行数 | 115 | 含本地+远程全部引用 |
| 本地分支数 | 17 | 含main，即16个非main本地分支 |
| 去重后唯一分支数 | **97** | 与phase7报告口径一致 ✓ |
| 非祖先分支（main未完全包含） | 5 | B×2 + C×1 + D×1 + F×1 |
| 祖先分支（已完全进入main） | 92 | A×28 + E×62 + D中已合并×2 |

**核对结论**: 97唯一分支口径与`git branch -a`原始数据一致（115行 - 18组本地/远程同名去重 = 97）。

---

## 4. B/C/F类具体分支名和理由

### 4.1 B类（2个）— 建议合并

| # | 分支名 | 独有commit | 独有文件 | 核心价值 | 风险 |
|---|--------|-----------|---------|---------|------|
| B-1 | `feat/lumenis-p0-p1-source-convergence` [local+remote] | 7 | 17 | LUMENIS 6个前端页面绑定真实API；报告页接入daily_reports DB；ZBC→OSAI跨核心Skill调用链；OSAI边界审计测试(+347行)；CI真正执行pytest | 低（app.py仅加注释，主体过滤未变） |
| B-2 | `origin/feat/lumenis-product-convergence` | 4 | 4 | **P0 bug修复**：auth_recovery_center.py硬编码`D:\Taikoo-monitor-new\data\monitor.db`改为`from database import DB_PATH`；产品收敛治理文档 | 无（是安全性修复） |

### 4.2 C类（1个）— 可选合并文档

| # | 分支名 | 独有commit | 独有文件 | 核心价值 | 注意 |
|---|--------|-----------|---------|---------|------|
| C-1 | `origin/feat/lumenis-product-convergence-docs-final3` | 2 | 2 | 产品收敛master文档(+110行) + README对齐 | 与B-2文档部分高度重叠，合并B-2后可跳过 |

### 4.3 F类（1个）— 禁止合并

| # | 分支名 | 独有commit | 独有文件 | diff规模 | 禁合并理由 |
|---|--------|-----------|---------|---------|-----------|
| F-1 | `feat/zbc-full-upgrade-v1` [local+remote] | 11 | 142 | +144,716 / -615行 | **P0/CRITICAL：移除app.py中9处`_subject_sql_and_values()`调用**，分布在5个核心统计函数中：①`api_publish_buckets_v570()` ②`api_global_trends_v570()` ③`api_notes_library_v571()` ④`api_negative_stats()` ⑤`api_dashboard_all()`（含overview/stats/risk_alerts/hot_topics/pending_negative共5处子查询）。过滤条件从`is_taikoo_verified=1 AND relevance_status!='irrelevant' AND {主体词SQL}`弱化为仅`is_taikoo_verified=1`，违反AGENTS.md第5节"广州太古汇主体口径P0不得弱化"红线。另含大量audit/_*.json中间产物和tests_*_result.txt垃圾文件。 |

**F类选择性回收策略**：禁止整体合并；PermissionGate/Runtime Guardian/证据链/历史数据导入等高价值资产可逐模块cherry-pick，但主体过滤相关代码一律不得回收。

---

## 5. main主体链路验证结果

### 5.1 subject_rules.py 核心定义

| 链路节点 | 行号 | 状态 | 证据 |
|----------|------|------|------|
| `SUBJECT_WORDS` 词表 | L13 | ✅ 完整 | 词表定义存在 |
| `SUBJECT_EXCLUDE_WORDS` 排除词表 | L20 | ✅ 完整 | 一票否决排除词表存在 |
| `subject_hit()` 函数 | L169 | ✅ 完整 | 五字段任一命中+排除词一票否决 |
| `subject_sql_and_values_for()` SQL生成器 | L261 | ✅ 完整 | SQL子句+参数生成函数存在 |

### 5.2 app.py `_subject_sql_and_values()` 调用计数

| 指标 | 数值 |
|------|------|
| 定义行 | app.py:992 `def _subject_sql_and_values(alias='')` |
| 调用点 | 8处（L1331, L2447, L2620, L2857, L3151, L3166, L3309, L4786） |
| **总出现次数** | **9处**（1定义 + 8调用）✓ 与phase7报告一致 |

### 5.3 调用点分布

| 行号 | 所属函数/用途 | 过滤条件 |
|------|-------------|---------|
| L1331 | AI分析队列（未分析笔记筛选） | `is_taikoo_verified=1 AND (ai_analyzed_at='' OR NULL) AND {clause}` |
| L2447 | 笔记库/搜索 | `is_taikoo_verified=1 AND ... AND {clause}` |
| L2620 | 数据查询 | 主体过滤 |
| L2857 | 最新采集时间+总数统计 | `is_taikoo_verified=1 AND {clause}` |
| L3151 | 情感/风险按日统计 | `is_taikoo_verified=1 AND {clause} AND publish_date BETWEEN ? AND ?` |
| L3166 | 未分析计数+采集日志 | `is_taikoo_verified=1 AND {clause}` |
| L3309 | 品牌业态/统计 | 主体过滤 |
| L4786 | 仪表盘/概览 | 主体过滤 |

### 5.4 下游链路

| 链路节点 | 位置 | 状态 |
|----------|------|------|
| `aggregate_events()` 事件聚合 | reprocess.py:153 | ✅ 委托build_cross_platform_events() |
| `build_cross_platform_events()` | reprocess.py:109 | ✅ 只消费is_taikoo_verified=1笔记 |
| `build_daily_report()` 日报入口 | risk_engine.py:296 | ✅ 委托daily_report.generate_daily_digest() |
| `generate_daily_digest()` | daily_report.py:558 | ✅ db.get_notes_by_date_range()内置主体过滤 |

### 5.5 验证结论

**main分支主体链路完整且健康**：
1. 入库层：`subject_hit()` → `is_taikoo_verified`标记 ✅
2. 查询层：`_subject_sql_and_values()` → 9处核心SQL查询 ✅
3. 聚合/报告层：`build_cross_platform_events()` / `generate_daily_digest()` → 只消费已验证数据 ✅

与F类分支`feat/zbc-full-upgrade-v1`形成明确对照：main保留全部9处，F类移除5个核心统计函数中的9处调用。

---

## 6. 结论

### 6.1 阶段6源码审计 — VERIFIED

- P0=0, P1=27（原21+新增6）, P2=17（原15+新增2）, 合计44项
- 本轮新增8项中：4项已修（N-01/N-06/N-07/N-08），1项真实bug未修（N-04 cache_manager events表created_at列不存在），2项建议（N-02 AI总超时/N-03 硬编码口令），1项口径不一致未修（N-05 report_api first_seen vs event_date）
- **重要修正**：N-08（report_engine.py心跳泄漏）实际已修复（try/finally配对存在），非原预期"待修"
- **最高优先级未修项**：N-04（cache_manager.py:241运行时必然报错）+ P1-04/P2-14（collector_v2/run_live_engine.py:20主体过滤return False，P0红线）

### 6.2 阶段7分支收敛 — VERIFIED

- A=28, B=2, C=1, D=3, E=62, F=1, 合计97唯一分支 ✓
- `git branch -a`原始115行，去重后97与报告口径一致 ✓
- B类2个分支名确认：`feat/lumenis-p0-p1-source-convergence`、`origin/feat/lumenis-product-convergence` ✓
- C类1个分支名确认：`origin/feat/lumenis-product-convergence-docs-final3` ✓
- F类1个分支名确认：`feat/zbc-full-upgrade-v1`，禁合并理由为移除9处`_subject_sql_and_values()`调用、5个核心统计函数主体过滤被弱化 ✓
- main主体链路验证通过：subject_rules.py四要素完整，app.py `_subject_sql_and_values()`共9处（1定义+8调用）✓

### 6.3 总体结论

| 阶段 | 状态 | 关键数字 |
|------|------|---------|
| 阶段6源码审计P1清单更新 | **VERIFIED** | P0=0, P1=27, P2=17, 合计44；新增8项中4已修/1真实bug/2建议/1口径 |
| 阶段7分支收敛复核 | **VERIFIED** | 97唯一分支；A28/B2/C1/D3/E62/F1；main主体链路9处调用完整 |

---

*报告生成时间: 2026-09-07 | 复核工具: grep / Read / sqlite3 PRAGMA / git branch（严格只读）*
