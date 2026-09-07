# Z-Brand-Core Main 分支全链路审计报告

> **审计基线**: main @ 46502f11（生产基线）
> **审计日期**: 2026-09-07
> **审计范围**: Product→Domain→Module→Function→Call Graph→DB→Producer→API→Metric→View Model→UI→Evidence→Report→Runtime
> **数据库**: data/monitor.db（SQLite，128表，只读查询，未修改）
> **审计原则**: 只读审计，不修改任何源码或数据库

---

## 一、各维度审计结果表

### 1. 数据口径

| 检查项 | 状态 | 严重程度 | 证据（文件:行号） |
|--------|------|----------|-------------------|
| SUBJECT_WORDS 词表数量 | WARN | P2 | subject_rules.py:13-18 — 实际18词（非文档所称17词） |
| SUBJECT_EXCLUDE_WORDS 词表数量 | WARN | P2 | subject_rules.py:20-25 — 实际19词（非文档所称18词） |
| subject_hit() 调用链一致性 | PASS | — | 所有嵌套定义均委托 subject_rules.subject_hit_text（app.py:2836-2843, collector_v2/run_profile.py:46-50, collector_v2/run_live_engine.py:15-20） |
| subject_hit 代码重复 | WARN | P2 | 4处独立定义（app.py:2836, collector_v2/run_profile.py:46, collector_v2/run_live_engine.py:17, data/test_persist.py:6），虽口径一致但维护成本高 |
| _subject_sql_and_values 一致性 | PASS | — | app.py:975-977, risk_engine.py:292-293 均委托 subject_rules.subject_sql_and_values |
| publish_datetime vs captured_at 分离 | PASS | — | notes表963条：null publish_datetime=1, null captured_at=0；canonical_data.py:12,90 明确P0红线分离 |
| 双域隔离 active_brand 隐式污染 | WARN | P1 | subject_rules.py:115-140 get_active_brand() 委托 SubjectContext，但 zbc_canonical_data 表无 domain/product 字段；notes 仅有 product_id 无 domain_id |
| **trend_api 未做主体过滤** | **FAIL** | **P0** | trend_api.py:47,145,179,201 — 6个端点查询 notes 表均未调用 _subject_sql_and_values()，统计全量笔记而非太古汇主体相关 |
| 重复统计口径 | WARN | P1 | trend_api.py:250 _get_notes_series 与 trend_notes() 重复实现相同SQL；app.py:2785 另有一套按 publish_date 聚合的趋势统计，与 trend_api 按 publish_datetime 口径不一致 |

### 2. 趋势查询性能

| 检查项 | 状态 | 严重程度 | 证据（文件:行号） |
|--------|------|----------|-------------------|
| **SQL 无日期范围约束（全表扫描）** | **FAIL** | **P0** | trend_api.py:47,74,100,145,179,201 — 所有查询 `WHERE publish_datetime IS NOT NULL` 后直接 GROUP BY，无 `AND date(publish_datetime) >= ?`，扫描全表后 Python 端 _fill_zeros 仅取请求天数 |
| **publish_datetime 无索引** | **FAIL** | **P0** | DB 索引检查：仅有 idx_notes_publish_date（publish_date 列），无 publish_datetime 索引；trend_api 全部使用 publish_datetime |
| N+1 查询 | PASS | — | 各端点单次聚合查询，无循环内查询 |
| f-string 拼接列名/表名 | WARN | P1 | trend_api.py:74,98-100,201 — 列名/表名通过 f-string 拼接，虽来自硬编码列表但 `except: continue` 静默吞错，可能选到错误列 |
| 前端缓存/防抖 | WARN | P1 | static/js/zbc-trend-line.js:19-77 — 无内存缓存、无请求防抖；autoRefresh（:72-74）使用 setTimeout 递归，组件重渲染时可能产生重复定时器 |
| DB_PATH 硬编码相对路径 | WARN | P2 | trend_api.py:12 — `DB_PATH = 'data/monitor.db'`，CWD 变化时连接失败 |
| trend_overview 仅返回2项 | WARN | P2 | trend_api.py:234-245 — 命名 overview 但仅返回 notes+engagement，缺 events/risk/sentiment |

### 3. 安全

| 检查项 | 状态 | 严重程度 | 证据（文件:行号） |
|--------|------|----------|-------------------|
| 模板 XSS（\|safe） | PASS | — | templates/ 下39个HTML模板均未使用 \|safe，Jinja2 autoescape 默认开启 |
| Markup()/render_template_string | PASS | — | 全仓库无 render_template_string；仅 app.py:4631,4886 使用 html.unescape 处理采集内容（非渲染路径） |
| SQL 注入（用户输入 f-string） | WARN | P1 | app.py:2547 `sql=f"SELECT {','.join(select_cols)} FROM notes WHERE 1=1"` — select_cols 动态构建需确认来源；其余 f-string 多为硬编码表名/列名或 _subject_sql_and_values()（参数化） |
| **Auth 白名单过宽** | **FAIL** | **P1** | app.py:1000 — `/api/zbmp/`, `/api/cth/`, `/api/system/`, `/api/viz/` 前缀全部免密；_is_cth_readonly_get（app.py:962-972）进一步放行 CTH 只读 GET |
| PermissionGate 实现 | PASS | — | permission_gate.py:1-911 — 12级权限等级（READ→PUSH），fail-closed，OperationType 枚举，人工审批令牌 |
| P2 Action Firewall | PASS | — | p2_action_firewall.py:1-192 — 9步校验链（Identity→Action），生产DB直写硬拒绝，COMMIT/PUSH 默认 DENY |
| Agent Security（Prompt Injection） | PASS | — | agent_security.py:1-371 — 5层防御（输入净化/指令检测/参数校验/输出过滤/蜜罐），14种注入模式，敏感信息redaction |
| API Key 硬编码 | PASS | — | 全仓库 .py 文件无硬编码 sk-/glm-/api key；均通过 os.getenv/.env 注入（ai_channel.py:769-775, ark_llm.py:28, provider_registry.py:38） |
| API Key 泄露防护 | PASS | — | agent_security.py:67 — sk- 模式 redaction；ai_browser_runtime.py:186 — 敏感字段黑名单 |

### 4. Runtime/Collector 恢复

| 检查项 | 状态 | 严重程度 | 证据（文件:行号） |
|--------|------|----------|-------------------|
| collector_guard 模块完整性 | PASS | — | collector_guard/ 16个Python模块：checkpoint, dlq_replay, guard, state, queue_worker, rate_limiter, resource_guard, risk_engine, runtime_guardian, runtime_switch, schedule_adapter, task_queue, analyzer, metrics, __init__ |
| Checkpoint 断点续采 | PASS | — | collector_guard/checkpoint.py:14-85 — JSON原子写入（tmp+replace），线程安全，seen ID 上限5000，文件损坏自动重置 |
| DLQ 死信队列 | PASS | — | collector_guard/dlq_replay.py:29-145 — 追加式 JSONL，task_id+上下文+错误+重试计数，replay 成功 ack 失败保留，业务拒绝不入队 |
| auto_recovery 自动修复 | PASS | — | auto_recovery.py:1-475 — 5层闭环，6类自动修复（进程崩溃/网络/DB/超时/推送/API）+6类人工介入（DB结构/主体规则/风控等） |
| runtime_guardian 统一守护 | PASS | — | runtime_guardian.py:1-1468 — Worker→Lease→Heartbeat→Checkpoint→Reaper→Retry→DLQ→Resume 完整生命周期；熔断器（5次失败→300s冷却），指数退避 |
| system_watchdog | WARN | P2 | system_watchdog.py:1-283 — 标记 LEGACY，已由 runtime_guardian 接管；端口硬编码8200（:44）与生产8201不一致 |
| 双账号轮换 | PASS | — | dual_account_rotation.py:1-240 — 评分-based选择（成功率/风控/失败/冷却/连续使用/抖动），切换失败回退，双账号均失败安全停止返回 None |
| **collection_quality_log 表不存在** | **FAIL** | **P1** | DB 检查：collection_quality_log 表未创建；collection_quality_gate.py:45-65 定义了 DDL 和索引但 ensure_quality_log_table() 未在启动链路调用 |

### 5. Evidence 可追溯

| 检查项 | 状态 | 严重程度 | 证据（文件:行号） |
|--------|------|----------|-------------------|
| evidence_chain 生命周期定义 | PASS | — | evidence_chain.py:47-100 — 13阶段（EXTERNAL_SOURCE→EVIDENCE→CANONICAL_DATA→EVENT→CASE→FINDING→INSIGHT→DECISION→...），immutable 标记 |
| zbc_evidence 表结构 | PASS | — | DB 检查：22字段（evidence_id, source_type, source_url, content_hash, captured_at, publish_datetime, subject_scope, domain_id, product_id, authenticity_score, ai_call_id 等） |
| evidence_store 旧证据存储 | PASS | — | evidence_store.py:1-1260 — app_evidence_records 表（43字段），L0-L10 级别，PASS/FAIL/ENV/GAP/REGRESSION 结果 |
| evidence_api 只读查询 | PASS | — | evidence_api.py:14-103 — stats/list/detail/timeline 4个只读端点，分页+筛选，无删除/修改 |
| **zbc_evidence 数据量** | **FAIL** | **P0** | DB 检查：仅6条记录；采集主链路未写入 evidence_chain |
| **zbc_canonical_data 数据量** | **FAIL** | **P0** | DB 检查：仅4条记录；canonical_data.py 实现完整但未接入生产采集链路 |
| **报告→原始笔记回溯链路** | **FAIL** | **P1** | zbc_evidence.source_id 与 notes.id/note_id 无外键约束；daily_reports（30条）与 evidence 无关联字段；无法从报告回溯到原始笔记/评论 |
| app_evidence_records 数据量 | WARN | P2 | DB 检查：13条记录；旧证据存储有少量数据但与 zbc_evidence 双轨并存，未统一 |

### 6. UI 状态

| 检查项 | 状态 | 严重程度 | 证据（文件:行号） |
|--------|------|----------|-------------------|
| 模板总数 | WARN | P2 | templates/ 下39个HTML（用户所称38个）；含 cth/, zbmp/, system/, auth/ 子目录 |
| Loading 状态 | PASS | — | 34/39模板含 loading/骨架屏/加载中模式 |
| Empty 状态 | PASS | — | 31/39模板含 暂无数据/empty/no-data 模式 |
| Error 状态 | PASS | — | 34/39模板含 error/失败/异常模式 |
| Stale/Partial/Permission 状态 | WARN | P1 | 29/39模板含相关关键词，但多为文字提及而非统一的状态组件；无 Stale（数据过期）/Partial（部分加载）/Permission Denied 的标准化组件 |
| base.html JS 基础设施 | PASS | — | templates/base.html:1-375 — 域切换（CTH/ZBMP/SYS）、导航分组、i18n（data-i18n）、主题（data-theme）、字体本地化 |
| 趋势线组件 | PASS | — | static/js/zbc-trend-line.js — 统一趋势线组件，SVG渲染，支持 autoRefresh |

### 7. 已有系统盘点（8项目标能力）

| 目标能力 | 当前实现状态 | 严重程度 | 证据 |
|----------|-------------|----------|------|
| **Canonical Metric Registry** | **PARTIAL** | P1 | canonical_metrics.py:1-277 — 纯函数计算层完整（sentiment_count/risk_count/engagement），口径锁定；但未形成 Registry 注册机制，各 API 仍可能自行计算 |
| **Canonical Data Grid** | **PARTIAL** | P0 | canonical_data.py 实现完整（1000+行），但 zbc_canonical_data 表仅4条数据，未接入生产链路 |
| **Collector Health** | **PARTIAL** | P1 | collector_status_api.py:1-150 — 8状态+18平台+缓存文件；但 collection_quality_gate.py 的 quality_log 表未创建，健康数据不完整 |
| **Intelligence Data Grid** | **PARTIAL** | P1 | intelligence_library_api.py:1-244 — 情报资产库API，13子库，多维度筛选；intelligence.py AI网关完整；但 intelligence_assets 表数据量未验证 |
| **AI Provider Capability-Based Routing** | **PARTIAL** | P1 | provider_registry.py:33-130 — 9 Provider 注册（zhipu ACTIVE/ollama AVAILABLE/ark FALLBACK等），状态机完整；但 intelligence.py _chat 主要按 provider 优先级路由，未按 capability（视觉→glm-4.6v/联网→web-search-pro）自动匹配 |
| **Evidence Chain** | **FAIL** | P0 | evidence_chain.py/evidence_store.py/evidence_api.py 代码完整，但 zbc_evidence 仅6条，未接入采集主链路 |
| **Runtime Guardian** | **PASS** | — | runtime_guardian.py:1-1468 — 完整生命周期守护，熔断器+退避+DLQ+Lease |
| **Permission Gate** | **PASS** | — | permission_gate.py:1-911 — 12级权限+fail-closed+审批令牌 |

---

## 二、P0 缺陷清单（必须修复）

### P0-1: trend_api 全端点未做主体过滤
- **文件**: trend_api.py:47, 74, 100, 145, 179, 201, 250, 259
- **问题**: 6个趋势端点（notes/events/risk/engagement/kos/sentiment）查询 notes 表时未调用 `_subject_sql_and_values()`，统计全量笔记（含非太古汇主体内容），与系统其他模块的主体口径不一致
- **影响**: 趋势图数据虚高，与舆情监测/风险预警/日报的主体过滤数据对不上
- **修复建议**: 每个端点的 WHERE 子句追加 `AND {_subject_sql_and_values()[0]}`，传入对应参数

### P0-2: trend_api SQL 无日期范围约束 + publish_datetime 无索引
- **文件**: trend_api.py:47, 145, 179, 201, 250, 259；DB 索引缺失
- **问题**: SQL 仅 `WHERE publish_datetime IS NOT NULL` 后全表 GROUP BY，Python 端 `_fill_zeros` 才取请求天数；且 `publish_datetime` 列无索引（仅有 `publish_date` 索引）
- **影响**: 数据量增长后趋势查询性能线性下降，每次请求扫描全表
- **修复建议**: (1) SQL 追加 `AND date(publish_datetime) >= date('now', ?)` 限定天数；(2) 创建 `CREATE INDEX idx_notes_publish_datetime ON notes(publish_datetime)`

### P0-3: Evidence Chain 未接入生产链路（zbc_evidence 仅6条）
- **文件**: evidence_chain.py（完整实现但未被调用）；DB: zbc_evidence=6, zbc_canonical_data=4
- **问题**: evidence_chain.py 定义了13阶段生命周期和完整的 Evidence→Canonical→Event 链路，但采集主链路（persist_rednote_data/persist_live）未写入 zbc_evidence 和 zbc_canonical_data
- **影响**: 报告无法回溯到原始证据，违反"任何分析结论必须能追溯到原始证据"原则
- **修复建议**: 在 persist_rednote_data/persist_live 入库后调用 evidence_chain.create_evidence()，将笔记元信息+content_hash 写入 zbc_evidence

### P0-4: Canonical Data 未接入生产链路（zbc_canonical_data 仅4条）
- **文件**: canonical_data.py（1000+行完整实现）；DB: zbc_canonical_data=4
- **问题**: canonical_data.py 实现了规范化+主体过滤+质量门+去重，但生产采集仍直接写 notes 表，未经过 Canonical 层
- **影响**: 数据规范化口径不统一，canonical_metrics.py 的纯函数计算层无数据可消费
- **修复建议**: 采集入库后旁路写入 zbc_canonical_data（先旁路验证，不替换主链路）

---

## 三、P1 改进清单

### P1-1: Auth 白名单过宽
- **文件**: app.py:1000
- **问题**: `/api/zbmp/`, `/api/cth/`, `/api/system/`, `/api/viz/` 前缀全部免密，可能暴露敏感 API
- **建议**: 收窄白名单，仅放行健康检查/公开只读端点；CTH 免密浏览态应限定具体路径而非整个前缀

### P1-2: collection_quality_log 表未创建
- **文件**: collection_quality_gate.py:45-78；DB 表不存在
- **问题**: 五步质量门禁定义了 DDL 但 `ensure_quality_log_table()` 未在 app 启动时调用，质量失败无记录
- **建议**: 在 app.py 启动流程或 before_first_request 中调用 `ensure_quality_log_table()`

### P1-3: 双域隔离字段不完整
- **文件**: subject_rules.py:115-140；DB: zbc_canonical_data 无 domain/product 列
- **问题**: notes 仅有 product_id 无 domain_id；zbc_canonical_data 完全无域隔离字段；active_brand 通过 SubjectContext 管理但下游表未持久化域信息
- **建议**: zbc_canonical_data 增加 domain_id/product_id 列；notes 增加 domain_id 列（向后兼容可空）

### P1-4: 报告→原始证据回溯链路未贯通
- **文件**: evidence_api.py；DB: zbc_evidence.source_id 与 notes 无外键
- **问题**: daily_reports（30条）与 zbc_evidence 无关联字段；无法从报告条目回溯到具体笔记/评论
- **建议**: daily_reports 增加 evidence_ids JSON 字段；zbc_evidence.source_id 建立与 notes.note_id 的映射约束

### P1-5: AI Provider 路由非 capability-based
- **文件**: intelligence.py, provider_registry.py
- **问题**: provider_registry 注册了各 provider 的 models（含 glm-4.6v 视觉、web-search-pro 联网），但 intelligence._chat 按 provider 优先级选择，未根据任务类型（视觉/联网/强推理）自动匹配 capability
- **建议**: 在 intelligence.py 增加 `select_model_by_capability(capability)` 函数，视觉任务→glm-4.6v，联网→web-search-pro，强推理→glm-5.3

### P1-6: 趋势统计口径重复且不一致
- **文件**: trend_api.py:250 _get_notes_series vs trend_notes(); app.py:2785 按 publish_date 聚合
- **问题**: 同一"笔记趋势"指标在 trend_api（按 publish_datetime）和 app.py dashboard（按 publish_date）使用不同时间列，结果可能不一致
- **建议**: 统一使用 publish_datetime；app.py:2785 的 publish_date 聚合迁移到 publish_datetime

### P1-7: 前端趋势组件无缓存/防抖
- **文件**: static/js/zbc-trend-line.js:19-77
- **问题**: 每次 render 都发起 fetch，无内存缓存；autoRefresh 使用 setTimeout 递归，组件重渲染可能产生重复定时器
- **建议**: 增加按 endpoint+days 的内存缓存（TTL 60s）；autoRefresh 定时器存储在 container data 属性上，重渲染前 clearTimeout

### P1-8: SQL f-string 动态列名
- **文件**: trend_api.py:74, 98-100, 201; app.py:2547
- **问题**: 列名/表名通过 f-string 拼接，`except: continue` 静默吞错可能选到错误列；app.py:2547 的 select_cols 需确认是否用户可控
- **建议**: 列名用白名单校验后再拼接；去掉裸 except，至少记录 warning

---

## 四、已有能力与目标能力差距矩阵

| # | 目标能力 | 目标状态 | 当前实现 | 代码完整性 | 数据/接入状态 | 差距等级 |
|---|----------|----------|----------|-----------|--------------|----------|
| 1 | Canonical Metric Registry | 统一注册+所有消费方调用 | canonical_metrics.py 纯函数层 | 完整（277行） | 未形成 Registry，API 可能自行计算 | GAP-P1 |
| 2 | Canonical Data Grid | 采集→规范化→主体过滤→质量门 | canonical_data.py | 完整（1000+行） | zbc_canonical_data 仅4条，未接入生产 | GAP-P0 |
| 3 | Collector Health | 状态+质量+恢复 三位一体 | collector_status_api.py + collection_quality_gate.py | 代码完整 | quality_log 表未创建，健康数据不完整 | GAP-P1 |
| 4 | Intelligence Data Grid | 情报资产+AI网关+知识库 | intelligence_library_api.py + intelligence.py | 代码完整 | 资产库数据量未验证，AI网关已接入 | GAP-P1 |
| 5 | AI Capability-Based Routing | 按任务能力自动选模型 | provider_registry.py + intelligence.py | Registry 完整 | 路由按 provider 优先级，非 capability | GAP-P1 |
| 6 | Evidence Chain | 采集→证据→规范→事件→报告 全链路可追溯 | evidence_chain.py + evidence_store.py + evidence_api.py | 代码完整 | zbc_evidence 仅6条，未接入采集，报告无回溯 | GAP-P0 |
| 7 | Runtime Guardian | 生命周期+熔断+恢复+DLQ | runtime_guardian.py + collector_guard/ + auto_recovery.py | 完整（1400+行+16模块） | 已接入，熔断器+退避+DLQ 完整 | ACHIEVED |
| 8 | Permission Gate | 统一权限+fail-closed+审批 | permission_gate.py + p2_action_firewall.py + agent_security.py | 完整（900+行+192行+371行） | 已接入，Auth 白名单过宽需收窄 | ACHIEVED（带P1） |

---

## 五、数据库只读盘点摘要

| 指标 | 值 |
|------|-----|
| 总表数 | 128 |
| notes | 963 条 |
| events | 427 条 |
| daily_reports | 30 条 |
| collection_logs | 479 条 |
| ai_call_logs | 203 条 |
| app_evidence_records | 13 条 |
| **zbc_evidence** | **6 条** |
| **zbc_canonical_data** | **4 条** |
| zbc_lifecycle_tracking | 8 条 |
| comments / crawl_logs / keywords / risk_records / risks | 表不存在 |
| collection_quality_log | 表不存在（DDL已定义但未创建） |
| notes null publish_datetime | 1 条 |
| notes null captured_at | 0 条 |
| notes publish_datetime 索引 | 无（仅有 publish_date 索引） |

---

## 六、审计结论

### 核心判断
Z-Brand-Core main 分支在 **代码架构完整性** 上达到较高水平：Runtime Guardian、Permission Gate、Evidence Chain、Canonical Data、AI Provider Registry 等核心模块均有完整实现。但在 **生产链路接入** 和 **数据口径一致性** 上存在显著差距：

1. **4个P0缺陷** 全部集中在"代码写了但没接入生产"或"口径不一致"——trend_api 缺主体过滤+全表扫描、Evidence/Canonical 未接入采集链路
2. **8个P1改进** 集中在安全边界收窄、表结构补全、回溯链路贯通、前端性能优化
3. **8项目标能力中 2项 ACHIEVED、4项 GAP-P1、2项 GAP-P0**

### 修复优先级建议
1. **立即（P0）**: trend_api 主体过滤+日期约束+索引；Evidence/Canonical 旁路接入采集
2. **短期（P1）**: Auth 白名单收窄；quality_log 表创建；域隔离字段补全；报告回溯链路
3. **中期（P2）**: subject_hit 代码去重；UI 六状态组件化；system_watchdog 端口对齐；capability-based 路由

---

*报告生成时间: 2026-09-07 | 审计工具: 只读源码扫描 + SQLite 只读查询 | 未修改任何源码或数据库*
