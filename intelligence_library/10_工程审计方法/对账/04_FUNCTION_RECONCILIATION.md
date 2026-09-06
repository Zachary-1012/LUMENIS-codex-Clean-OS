# 04 — FUNCTION RECONCILIATION（函数/符号对账）

> 审计日期：2026-09-02
> OSAI HEAD：`60af16a`
> ZBC HEAD：`545a3ab`，v5.9.9
> 状态四分类：EXISTS / PARTIAL / MISSING / UNKNOWN
> **ZBC 最高保护层**：SUBJECT_WORDS、SUBJECT_EXCLUDE_WORDS、subject_hit()、_subject_sql_and_values()、aggregate_events()、build_daily_report()、publish_datetime、captured_at、Production DB、生产报告口径、最终风险口径

---

## 状态计数

| 类别 | EXISTS | PARTIAL | MISSING | UNKNOWN |
|------|--------|---------|---------|---------|
| 最高保护层函数/常量（6 项） | 4 | 1 | 1 | 0 |
| 核心入口函数（app.py 路由组） | 12 | 0 | 0 | 0 |
| collector 系列 | 5 | 0 | 0 | 0 |
| report_engine 系列 | 4 | 0 | 0 | 0 |
| risk_engine 系列 | 0 | 2 | 0 | 0 |
| ai_* 系列 | 6 | 0 | 0 | 0 |
| database 核心函数 | 8 | 0 | 0 | 0 |
| daily_report 系列 | 6 | 0 | 0 | 0 |
| OSAI Contract 声明→ZBC 落地 | 2 | 3 | 3 | 0 |
| **合计** | **47** | **6** | **4** | **0** |

---

## 一、ZBC 最高保护层函数/常量

### 1.1 SUBJECT_WORDS（主体词常量）

| 属性 | 值 |
|------|-----|
| 状态 | **EXISTS** |
| 权威定义路径 | `ZBC/subject_rules.py` L13 |
| 签名 | `SUBJECT_WORDS = ['广州太古汇', '太古汇', '太古汇商场', '太古仓', '汇悦台', '太古汇保安', '太古汇停车场', '太古汇售后', '太古汇客服台', 'LV太古汇', '香奈儿太古汇', '迪奥太古汇', 'Dior太古汇', '太古汇发廊', '太古汇日料', '太古汇理发店', '太古汇总监']` |
| 词数量 | 18 个 |
| 引用位置 | `subject_rules.py` L38(subject_hit)、L51、L64、L81；`risk_engine.py` L5 import；`app.py` 间接通过 `_subject_sql_and_values` 委托 |
| 重复定义 | 无其他文件重新定义 SUBJECT_WORDS（全仓 grep 仅 subject_rules.py L13 一处赋值） |
| 备注 | **最高保护层，唯一权威定义**。OSAI 侧无此常量。 |

### 1.2 SUBJECT_EXCLUDE_WORDS（排除词常量）

| 属性 | 值 |
|------|-----|
| 状态 | **EXISTS** |
| 权威定义路径 | `ZBC/subject_rules.py` L20 |
| 签名 | `SUBJECT_EXCLUDE_WORDS = ['上海太古汇', '兴业太古汇', '上海兴业太古汇', '北京太古汇', '三里屯太古汇', '成都太古汇', '成都远洋太古汇', '远洋太古汇', '深圳太古汇', '香港太古汇', '太古城', '上海站', '上海静安', '上海静安区', '南京西路', '魔都', '新天地', '北京三里屯']` |
| 词数量 | 20 个 |
| 引用位置 | `subject_rules.py` L48(subject_hit 一票否决)、L61、L86；`risk_engine.py` L5 import |
| 重复定义 | 无 |
| 备注 | **最高保护层，一票否决优先于正向匹配**。 |

### 1.3 subject_hit()（主体判断函数）

| 副本 | 状态 | 路径:行号 | 签名 | 说明 |
|------|------|-----------|------|------|
| **权威实现** | **EXISTS** | `ZBC/subject_rules.py` L38 | `def subject_hit(title: object = '', body: object = '', content: object = '', source_keyword: object = '', matched_keyword: object = '') -> bool` | 排除词一票否决→5 字段正向词匹配，**规则层最高权威** |
| 兼容别名 | EXISTS | `ZBC/subject_rules.py` L54 | `def subject_hit_note(note: dict) -> bool` | 包装函数，从 dict 取字段调用 subject_hit |
| app.py 嵌套副本 | **PARTIAL** | `ZBC/app.py` L2743 | `def subject_hit(text)` | **嵌套在 rednote 采集 worker 内**，调用 `ai_analyzer.verify_taikoo_location(text, '')` 而非 `subject_rules.subject_hit()`；使用 AI 替代规则判断，口径不一致 |
| run_live_engine 嵌套副本 1 | PARTIAL | `ZBC/collector_v2/run_live_engine.py` L16 | `def subject_hit(text)` | 嵌套函数，调用 AI 验证 |
| run_live_engine 嵌套副本 2 | PARTIAL | `ZBC/collector_v2/run_live_engine.py` L20 | `def subject_hit(_): return False` | **stub，直接返回 False**，疑似调试/降级残留 |
| 历史备份副本 | EXISTS（非当前） | `ZBC/app_backup_v589.py` L2522、`app.py.bak_p0_20260902_094442` L2742 | 同 app.py 嵌套 | 历史备份，非当前运行代码 |

**subject_hit() 对账结论**：
- 权威实现 EXISTS（subject_rules.py L38），规则层完整。
- **PARTIAL 风险**：app.py L2743 和 collector_v2/run_live_engine.py L16/L20 存在 3 处嵌套/替代副本，其中 1 处为 AI 替代规则、1 处为 stub return False。这些副本绕过了最高保护层的统一规则口径。
- 全仓无 `def subject_hit` 的其他独立模块级定义。

### 1.4 _subject_sql_and_values()（主体 SQL 过滤函数）

| 副本 | 状态 | 路径:行号 | 签名 | 说明 |
|------|------|-----------|------|------|
| **权威实现** | **EXISTS** | `ZBC/subject_rules.py` L76 | `def _subject_sql_and_values(alias: str = '') -> tuple[str, list[str]]` | 生成 WHERE 子句（正向 OR + 排除 NOT）+ 参数列表，**SQL 层最高权威** |
| 兼容别名 | EXISTS | `ZBC/subject_rules.py` L93 | `subject_sql_and_values = _subject_sql_and_values` | 历史命名别名，避免旧调用断裂 |
| app.py 委托 | EXISTS | `ZBC/app.py` L599 | `def _subject_sql_and_values(alias='')` | **纯委托**：`return subject_sql_and_values(alias)`，无独立逻辑 |
| risk_engine.py 委托 | EXISTS | `ZBC/risk_engine.py` L9 | `def _subject_sql_and_values(alias='')` | **纯委托**：`return subject_sql_and_values(alias)` |
| database.py 内部 | EXISTS | `ZBC/database.py` L431 | `def _subject_clause(alias='')` | 数据库层内部主体子句函数（命名不同，功能对应） |
| 历史备份 | EXISTS（非当前） | `app_backup_v589.py` L522、`app.py.bak_p0_20260902_094442` L598 | 同 app.py | 历史备份 |

**_subject_sql_and_values() 对账结论**：
- 权威实现 EXISTS（subject_rules.py L76），SQL 层完整。
- app.py 和 risk_engine.py 均为纯委托，无逻辑分叉。
- database.py 有独立命名的 `_subject_clause()`（L431），需确认是否与 `_subject_sql_and_values()` 口径一致（静态分析无法确认运行时调用关系）。
- 全仓无其他独立实现。

### 1.5 aggregate_events()（事件聚合函数）

| 属性 | 值 |
|------|-----|
| 状态 | **MISSING** |
| 权威定义 | **不存在** — 全仓 `def aggregate_events` 0 命中 |
| 引用位置（仅文档/测试） | `ZBC/docs/7版方案x当前源码_深度匹配审计报告.docx` L11（明确记载"aggregate_events() 已不存在"）；`ZBC/tests/audit_probe_4.py` L28（`show('4 aggregate_events 引用', r'aggregate_events')`）；`ZBC/tests/_archive_blueprint.py` L15（文档引用）；`ZBC/scripts/github_upgrade_check.py` L97（文档引用） |
| 替代实现 | 事件聚合逻辑已内联/分散到：`database.py`（get_events L710、get_events_curated L761、classify_event_quality L746、_event_title_is_noise L732）、`app.py`（事件相关路由 L280-L449）、`event_graph.py`（事件图谱聚合） |
| 备注 | **最高保护层函数 MISSING**。按 SPEC 第 4 条，此项为 PARTIAL/MISSING 时应在 11_GAP_REGISTER 标 P0。事件聚合无法按函数名做保护与交接，逻辑分散在多处 SQL 和业务代码中。 |

### 1.6 build_daily_report()（日报构建函数）

| 副本 | 状态 | 路径:行号 | 签名 | 说明 |
|------|------|-----------|------|------|
| 兼容层入口 | **EXISTS** | `ZBC/risk_engine.py` L13 | `def build_daily_report(date_str=None)` | **纯委托**：`return daily_report.generate_daily_digest(date_str)` |
| 实际实现 | EXISTS | `ZBC/daily_report.py` L547 | `def generate_daily_digest(date_str=None)` | 日报实际生成函数（calculate_risk_index → generate_today_summary → generate_key_insights → generate_action_items → generate_executive_summary） |
| 报告引擎包装 | EXISTS | `ZBC/report_engine.py` L31 | `def generate_report(report_type, start=None, end=None)` | 多周期报告入口，daily 类型调用 `daily_report.generate_daily_digest(end)`（L68） |
| AI 日报（旧名） | EXISTS | `ZBC/ai_analyzer.py` L394 | `def generate_daily_report(notes, stats, date_str=None)` | AI 层日报生成（与 build_daily_report 不同，为 AI 分析子步骤） |
| 备注 | `build_daily_report()` 作为函数名 EXISTS，但仅为 risk_engine.py 的 1 行委托；实际逻辑在 daily_report.py 的 `generate_daily_digest()`。函数名保留为兼容层。 |

### 1.7 最高保护层字段（publish_datetime / captured_at）

| 字段 | 状态 | 定义路径 | 写入路径 | 备注 |
|------|------|----------|----------|------|
| `publish_datetime` | EXISTS | `database.py` L185（migration: `ALTER TABLE notes ADD COLUMN publish_datetime TEXT DEFAULT ''`）；`database_migrations.py` L322 | `app.py` L775（`'publish_datetime': n.get('detail_publish_time') or n.get('publish_time','')`） | notes 表字段，最高保护层 |
| `captured_at` | EXISTS | `database.py` L186（migration）；`database_migrations.py` L323；`app_evidence.py` L63（app_evidence_records 表） | `app.py` L782（`'captured_at': n.get('captured_at') or datetime.now().isoformat()`）；`collector_automation.py` L511；`app_evidence.py` L109/L144 | notes + app_evidence_records 表字段 |

---

## 二、核心入口函数（app.py 路由组）

> app.py 共 5,131 行，203 个 `@app.route` / `@app.get` 路由。以下按功能域列出核心入口。

### 2.1 认证/健康

| 函数/路由 | 状态 | 路径:行号 | 说明 |
|-----------|------|-----------|------|
| `_basic_auth()` | EXISTS | `app.py` L604（`@app.before_request`） | 全局认证中间件：HTTP Basic + v4 session 兼容 |
| `/healthz` | EXISTS | `app.py` L2619 | 健康检查（免认证） |
| `/api/system/health` | EXISTS | `app.py` L2623 | 系统健康 API |
| `/api/status` | EXISTS | `app.py` L2705 | 状态总览 |
| `/api/overview` | EXISTS | `app.py` L2688 | Dashboard 概览 |

### 2.2 数据查询

| 路由 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `/api/stats` | EXISTS | L1194 | 统计数据 |
| `/api/notes` | EXISTS | L1196 | 笔记列表 |
| `/api/risk-alerts` | EXISTS | L1213 | 风险预警 |
| `/api/hot-notes` | EXISTS | L1215 | 热门笔记 |
| `/api/comments` | EXISTS | L1217 | 评论 |
| `/api/events` | EXISTS | L1220 | 事件列表 |
| `/api/note/<note_id>` | EXISTS | L2377 | 笔记详情 |
| `/api/notes/historical` | EXISTS | L2197 | 历史笔记 |
| `/api/search` | EXISTS | L2014 | 搜索 |

### 2.3 采集控制

| 路由 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `/api/collector/status` | EXISTS | L1453 | 采集器状态 |
| `/api/collector/start` | EXISTS | L1533 | 启动采集（POST） |
| `/api/collector/stop` | EXISTS | L1549 | 停止采集（POST） |
| `/api/collector/history` | EXISTS | L1559 | 采集历史 |
| `/api/collect` | EXISTS | L2337 | 触发采集（POST） |
| `/api/collect/status/<task_id>` | EXISTS | L2350 | 采集任务状态 |
| `/api/rednote/collect` | EXISTS | L2713 | Rednote 采集（POST，**含嵌套 subject_hit L2743**） |
| `/api/xhs/runtime-check` | EXISTS | L1595 | 小红书运行时检查 |
| `/api/xhs/switch-account` | EXISTS | L1623 | 小红书切换账号（POST） |
| `/api/xhs/accounts` | EXISTS | L1652 | 小红书账号列表 |
| `/api/xhs/cookie/status` | EXISTS | L2227 | Cookie 状态 |
| `/api/xhs/cookie/sync` | EXISTS | L2232 | Cookie 同步（POST） |
| `/api/xhs/p0/status` | EXISTS | L4339 | 小红书 P0 状态 |
| `/api/xhs/p0/collection` | EXISTS | L4357 | 小红书 P0 采集（POST） |

### 2.4 报告

| 路由 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `/api/report/daily` | EXISTS | L1231 | 日报 |
| `/api/report/<report_type>` | EXISTS | L2060 | 周期报告（daily/weekly/monthly/yearly） |
| `/api/report/generate` | EXISTS | L2076 | 生成报告（POST） |
| `/api/report/v2/<report_type>` | EXISTS | L2085 | v2 报告 |
| `/api/report/v2/stats` | EXISTS | L2153 | v2 报告统计 |
| `/api/report/verify` | EXISTS | L2540 | 报告验证 |
| `/api/reports/export` | EXISTS | L3115/L3152 | 报告导出 |
| `/api/reports/export-all` | EXISTS | L3141 | 全部导出 |
| `/api/v2/report/export` | EXISTS | L3151 | v2 导出 |
| `/api/digest/today` | EXISTS | L2642 | 今日摘要 |
| `/api/digest/generate` | EXISTS | L2654 | 生成摘要（POST） |
| `/api/brand-report/generate` | EXISTS | L471 | 品牌报告生成（POST） |
| `/api/brand-report/export/<id>` | EXISTS | L533 | 品牌报告导出 |
| `/api/special-report/generate` | EXISTS | L3758 | 专题报告生成（POST） |

### 2.5 AI

| 路由 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `/api/ai/status` | EXISTS | L1317 | AI 状态 |
| `/api/ai/test` | EXISTS | L1322 | AI 测试（POST） |
| `/api/ai/chat` | EXISTS | L2025 | AI 对话（POST） |
| `/api/ai/analyze` | EXISTS | L4916 | AI 分析（POST） |
| `/api/ai/analyze-v570` | EXISTS | L2457 | AI v570 分析（POST） |
| `/api/ai/providers` | EXISTS | L2445 | AI 提供商列表 |
| `/api/ai-filter/stats` | EXISTS | L2665 | AI 过滤统计 |
| `/api/ai-filter/run` | EXISTS | L2669 | AI 过滤运行（POST） |
| `/api/ai-filter/cleanup` | EXISTS | L2681 | AI 过滤清理（POST） |
| `/api/ai-learning/status` | EXISTS | L1705 | AI 学习状态 |
| `/api/ai-learning/optimization/<op>` | EXISTS | L1715 | AI 学习优化 |
| `/api/ark/status` | EXISTS | L1330 | 方舟状态 |
| `/api/ark/chat` | EXISTS | L1341 | 方舟对话（POST） |
| `/api/ark/sentiment` | EXISTS | L1370 | 方舟情感分析（POST） |
| `/api/ark/summary` | EXISTS | L1394 | 方舟摘要（POST） |
| `/api/ark/keywords` | EXISTS | L1423 | 方舟关键词（POST） |

### 2.6 系统/运维/代码执行

| 路由 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `/api/config/run-code` | EXISTS | L3495 | **代码执行端点**（POST） |
| `/api/dev/run-code` | EXISTS | L5081 | **开发者代码执行**（POST） |
| `/api/developer/run` | EXISTS | L1987 | 开发者运行（POST） |
| `/api/workspace/file-tree` | EXISTS | L5138 | 工作区文件树 |
| `/api/workspace/term` | EXISTS | L5171 | **工作区终端**（POST） |
| `/api/system/config` | EXISTS | L3400/L3416 | 系统配置（GET/POST） |
| `/api/cache/status` | EXISTS | L2313 | 缓存状态 |
| `/api/stability/status` | EXISTS | L4371 | 稳定性状态 |
| `/api/stability/heartbeat` | EXISTS | L4382 | 稳定性心跳 |
| `/api/dashboard/all` | EXISTS | L4422 | Dashboard 全部数据 |

---

## 三、collector 系列函数

| 函数 | 状态 | 路径:行号 | 签名 | 说明 |
|------|------|-----------|------|------|
| `search_xiaohongshu()` | EXISTS | `collector.py` L212 | `def search_xiaohongshu(keyword, max_scroll=4, output_path=None, max_details=10)` | 小红书搜索主入口 |
| `collect_all()` | EXISTS | `collector.py` L235 | `def collect_all(keywords=None, max_scroll=4)` | 批量采集 |
| `import_from_file()` | EXISTS | `collector.py` L288 | `def import_from_file(filepath)` | 从文件导入 |
| `_norm_cdp_note()` | EXISTS | `collector.py` L99 | `def _norm_cdp_note(rec)` | CDP 笔记规范化 |
| `_search_via_cdp()` | EXISTS | `collector.py` L137 | `def _search_via_cdp(keyword, max_scroll, output_path, max_details=10)` | CDP 搜索 |
| `_ensure_cdp_online()` | EXISTS | `collector.py` L79 | `def _ensure_cdp_online(timeout=30)` | CDP 在线保障 |
| `classify_collect_state()` | EXISTS | `collector.py` L295 | `def classify_collect_state(error='', guard_state='', count=0)` | 采集状态分类 |

### collector_v2 管线函数

| 模块 | 状态 | 路径 | 核心函数 |
|------|------|------|----------|
| 去重 | EXISTS | `collector_v2/pipeline/deduplicate.py` | 去重逻辑 |
| 规范化 | EXISTS | `collector_v2/pipeline/normalize.py` | 字段规范化 |
| 持久化 | EXISTS | `collector_v2/pipeline/persist.py` | DB 写入 |
| 垃圾过滤 | EXISTS | `collector_v2/pipeline/spam_filter.py` | 垃圾内容过滤 |
| 主体过滤 | EXISTS | `collector_v2/pipeline/subject_filter.py` | 主体过滤（调用 subject_rules） |
| 调度 | EXISTS | `collector_v2/scheduler/collector_job.py` | 采集作业调度 |
| 小红书采集 | EXISTS | `collector_v2/xhs/collector.py` + `client.py` + `parser.py` | 小红书采集/解析 |
| 微博采集 | EXISTS | `collector_v2/weibo/collector.py` | 微博采集 |

---

## 四、report_engine 系列函数

| 函数 | 状态 | 路径:行号 | 签名 | 说明 |
|------|------|-----------|------|------|
| `period_for()` | EXISTS | `report_engine.py` L17 | `def period_for(report_type: str, now: datetime \| None = None)` | 计算报告周期 |
| `generate_report()` | EXISTS | `report_engine.py` L31 | `def generate_report(report_type: str, start: str \| None = None, end: str \| None = None)` | **报告生成主入口**，先跑 AI 过滤→DB 查询→AI 分析→强制写回统计口径→存储 |
| `generate_all()` | EXISTS | `report_engine.py` L72 | `def generate_all(now: datetime \| None = None)` | 生成全部周期报告 |
| `get_bundle()` | EXISTS | `report_engine.py` L80 | `def get_bundle(report_type: str, date_str: str \| None = None)` | 获取报告+摘要包 |
| `REPORT_TYPES` | EXISTS | `report_engine.py` L14 | `REPORT_TYPES = ('daily', 'weekly', 'monthly', 'yearly')` | 支持的报告类型常量 |

### report_export 独立引擎

| 函数 | 状态 | 路径 | 说明 |
|------|------|------|------|
| 报告导出引擎 | EXISTS | `report_export/report_engine.py`(15,884 B) | 独立报告导出模块，与根目录 report_engine.py 并存 |
| API patch | EXISTS | `report_export/app_report_api_patch.py`(870 B) | 报告导出 API 补丁 |

---

## 五、risk_engine 系列函数

| 函数 | 状态 | 路径:行号 | 签名 | 说明 |
|------|------|-----------|------|------|
| `_subject_sql_and_values()` | **PARTIAL** | `risk_engine.py` L9 | `def _subject_sql_and_values(alias='')` | 纯委托 `subject_sql_and_values(alias)`，无独立逻辑 |
| `build_daily_report()` | **PARTIAL** | `risk_engine.py` L13 | `def build_daily_report(date_str=None)` | 纯委托 `daily_report.generate_daily_digest(date_str)`，无独立逻辑 |
| 独立风险计算 | **MISSING** | — | — | risk_engine.py 仅 14 行，无独立风险评估/计算函数；风险计算分散在 `daily_report.py` L31 `calculate_risk_index()` 和 `collector_guard/risk_engine.py` |

**risk_engine 对账结论**：根目录 risk_engine.py 已退化为纯兼容委托层（2 个函数各 1 行委托），无独立风险计算能力。按双子星基线"risk_engine 应为独立风险评估模块"的定位，当前状态为 PARTIAL。

---

## 六、ai_* 系列函数

### 6.1 ai_analyzer.py（14 个函数）

| 函数 | 状态 | 行号 | 签名 |
|------|------|------|------|
| `verify_taikoo_location()` | EXISTS | L139 | `def verify_taikoo_location(title, content='')` |
| `analyze_sentiment()` | EXISTS | L170 | `def analyze_sentiment(title, content='', topics=None, return_reasons=False)` |
| `assess_risk()` | EXISTS | L258 | `def assess_risk(title, content, likes, comments, author_nickname='')` |
| `extract_topics()` | EXISTS | L314 | `def extract_topics(title, content='')` |
| `categorize()` | EXISTS | L324 | `def categorize(title, content='')` |
| `generate_summary()` | EXISTS | L333 | `def generate_summary(title, content, sentiment, risk_level, topics)` |
| `analyze_note()` | EXISTS | L345 | `def analyze_note(note, provider='hybrid')` |
| `batch_analyze()` | EXISTS | L385 | `def batch_analyze(notes, provider='hybrid')` |
| `generate_daily_report()` | EXISTS | L394 | `def generate_daily_report(notes, stats, date_str=None)` |
| `generate_period_report()` | EXISTS | L595 | `def generate_period_report(notes, stats, report_type='daily', period_start='', period_end='')` |
| `_extract_key_events()` | EXISTS | L467 | 内部函数 |
| `_build_event_summary()` | EXISTS | L504 | 内部函数 |
| `_build_sentiment_analysis()` | EXISTS | L541 | 内部函数 |
| `_safe_int()` | EXISTS | L163 | 内部工具 |

### 6.2 ai_filter.py（7 个函数）

| 函数 | 状态 | 行号 | 签名 |
|------|------|------|------|
| `assess_content_quality()` | EXISTS | L51 | `def assess_content_quality(title, content, likes=0, comments=0)` |
| `detect_noise_type()` | EXISTS | L108 | `def detect_noise_type(title, content)` |
| `ai_secondary_review()` | EXISTS | L145 | `def ai_secondary_review(note)` |
| `run_filter_batch()` | EXISTS | L291 | `def run_filter_batch(limit=500)` |
| `cleanup_rejected_notes()` | EXISTS | L329 | `def cleanup_rejected_notes(dry_run=True)` |
| `_ai_deep_review()` | EXISTS | L232 | 内部函数 |
| `_generate_rule_insight()` | EXISTS | L276 | 内部函数 |

### 6.3 ai_gateway_v570.py（5 个函数）

| 函数 | 状态 | 行号 | 签名 |
|------|------|------|------|
| `providers()` | EXISTS | L10 | `def providers()` |
| `analyze()` | EXISTS | L48 | `def analyze(text, context='')` |
| `_rule_based_analysis()` | EXISTS | L143 | 内部函数 |
| `_detect_sentiment()` | EXISTS | L179 | 内部函数 |
| `_detect_risk()` | EXISTS | L194 | 内部函数 |

### 6.4 ai_learning_engine.py（2 类 + 2 工厂函数）

| 符号 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `AILearningEngine` 类 | EXISTS | L20 | AI 学习引擎主类 |
| `WebSentimentSearch` 类 | EXISTS | L214 | Web 情感搜索类 |
| `get_ai_learning_engine()` | EXISTS | L409 | 工厂函数（单例） |
| `get_web_sentiment_search()` | EXISTS | L416 | 工厂函数（单例） |

### 6.5 其他 AI 模块

| 模块 | 状态 | 路径 | 核心符号 |
|------|------|------|----------|
| local_ai_client.py | EXISTS | `local_ai_client.py`(187行) | Ollama 本地 LLM 客户端 |
| ark_llm.py | EXISTS | `ark_llm.py`(316行) | 火山方舟 LLM 客户端 |
| data_feedback_loop.py | EXISTS | `data_feedback_loop.py`(324行) | 数据反馈闭环 |

---

## 七、database 核心函数

| 函数 | 状态 | 行号 | 说明 |
|------|------|------|------|
| `init_db()` | EXISTS | L232 | 数据库初始化 |
| `get_db()` | EXISTS | L272 | DB 连接单例 |
| `insert_note()` | EXISTS | L304 | 插入笔记 |
| `_subject_clause()` | EXISTS | L431 | 主体 SQL 子句（与 _subject_sql_and_values 功能对应） |
| `_verified_base()` | EXISTS | L436 | 已验证基础查询 |
| `get_notes()` | EXISTS | L463 | 笔记查询（支持 filters） |
| `get_stats()` | EXISTS | L478 | 统计数据 |
| `get_notes_by_date_range()` | EXISTS | L594 | 按日期范围查笔记 |
| `get_stats_by_date_range()` | EXISTS | L599 | 按日期范围查统计 |
| `save_daily_report()` | EXISTS | L554 | 保存日报 |
| `save_daily_digest()` | EXISTS | L884 | 保存日报摘要 |
| `find_duplicate_notes()` | EXISTS | L853 | 去重查找 |
| `get_pending_filter_notes()` | EXISTS | L827 | 待过滤笔记 |
| `update_note_ai_filter()` | EXISTS | L817 | 更新 AI 过滤结果 |
| `backup_database()` | EXISTS | L623 | 数据库备份 |
| `get_high_risk_notes()` | EXISTS | L539 | 高危笔记 |
| `get_events()` | EXISTS | L710 | 事件查询 |
| `get_events_curated()` | EXISTS | L761 | 策展事件（含质量分类） |
| `classify_event_quality()` | EXISTS | L746 | 事件质量分类（**aggregate_events 的替代实现之一**） |
| `upsert_event()` | EXISTS | L698 | 事件插入/更新 |
| `link_event_mentions()` | EXISTS | L807 | 事件-提及关联 |
| `note_to_dict()` | EXISTS | L287 | 行转字典 |

---

## 八、daily_report 系列函数

| 函数 | 状态 | 行号 | 签名 |
|------|------|------|------|
| `calculate_risk_index()` | EXISTS | L31 | `def calculate_risk_index(notes, events, period_days=1)` |
| `calculate_brand_health_score()` | EXISTS | L92 | `def calculate_brand_health_score(notes, risk_index)` |
| `generate_today_summary()` | EXISTS | L165 | `def generate_today_summary(date_str=None)` |
| `generate_event_insight()` | EXISTS | L223 | `def generate_event_insight(event, notes)` |
| `generate_key_insights()` | EXISTS | L359 | `def generate_key_insights(notes, events, summary)` |
| `generate_action_items()` | EXISTS | L438 | `def generate_action_items(insights, events, summary)` |
| `generate_executive_summary()` | EXISTS | L507 | `def generate_executive_summary(summary, insights, actions)` |
| `generate_daily_digest()` | EXISTS | L547 | `def generate_daily_digest(date_str=None)` — **日报主入口** |
| `_collection_health()` | EXISTS | L131 | 内部：采集健康度 |
| `_ai_summarize_event()` | EXISTS | L327 | 内部：AI 事件摘要 |
| `_ai_generate_daily_summary()` | EXISTS | L618 | 内部：AI 日报摘要 |

---

## 九、OSAI Contract/Plan 声明函数 → ZBC 落地对账

> 核对 OSAI Contract/Plan 中声明的函数/能力是否在 ZBC 生产代码中落地。

### 9.1 Research Record Contract（OSAI AIDRH/src/contracts/research_record.py）

| OSAI 声明函数 | OSAI 行号 | ZBC 落地状态 | ZBC 证据 | 备注 |
|---------------|-----------|-------------|----------|------|
| `validate(record)` | L158 | **MISSING** | ZBC 无研究记录验证函数 | 生产侧不需要研究记录 |
| `sanitize(value)` | L113 | **PARTIAL** | `ZBC/safety_boundary.py` + `data_boundary.py` 有数据脱敏/边界控制，但非同一函数 | 概念对应，实现独立 |
| `validate_research_id(rid)` | L131 | **MISSING** | — | OSAI 独有 |
| `make_review()` | L225 | **MISSING** | — | OSAI 独有 |
| `add_review()` | L241 | **MISSING** | — | OSAI 独有 |
| `make_research_record()` | L249 | **MISSING** | — | OSAI 独有 |
| `to_ddc_record()` | L192 | **MISSING** | — | OSAI 内部转换 |
| `is_sensitive_key()` | L97 | **PARTIAL** | `ZBC/security_scanner.py` 有密钥扫描，但函数名/签名不同 | 概念对应 |

### 9.2 Safe Collection Contract（OSAI AIDRH/src/contracts/safe_collection.py）

| OSAI 声明函数 | OSAI 行号 | ZBC 落地状态 | ZBC 证据 | 备注 |
|---------------|-----------|-------------|----------|------|
| `redact_text(text)` | L92 | **PARTIAL** | `ZBC/safety_boundary.py` 有数据脱敏逻辑，但无同名函数 | 概念对应 |
| `redact_record()` | L109 | **PARTIAL** | 同上 | 概念对应 |
| `CollectionHygienePolicy.validate()` | L183 | **MISSING** | ZBC 无采集卫生策略验证 | — |
| `CollectionHygienePolicy.is_safe()` | L215 | **PARTIAL** | `ZBC/collector_guard/guard.py` + `rate_limiter.py` 有采集安全/速率控制 | 概念对应 |
| `RateGovernor.permit()` | L228 | **PARTIAL** | `ZBC/collector_guard/rate_limiter.py` 有限流器 | 概念对应 |
| `RateGovernor.within_daily_cap()` | L240 | **MISSING** | ZBC 无日采集量上限函数 | — |
| `build_collection_audit()` | L266 | **PARTIAL** | `ZBC/collector_guard/analyzer.py` + `metrics.py` 有采集审计/指标 | 概念对应 |
| `run_offline_pipeline()` | L334 | **MISSING** | ZBC 无离线采集管线函数（全部为在线采集） | — |

### 9.3 Capability Registry（OSAI AIDRH/src/shared/capability_registry.py）

| OSAI 声明函数 | ZBC 落地状态 | ZBC 证据 | 备注 |
|---------------|-------------|----------|------|
| `CapabilityRegistry.add()` | **PARTIAL** | `ZBC/function_registry.py` 有函数注册，但非能力注册 | 概念对应 |
| `CapabilityRegistry.promote()` | **MISSING** | ZBC 无能力提升函数 | OSAI 研究侧独有 |
| `CapabilityRegistry.deprecate()` | **MISSING** | — | — |
| `CapabilityRegistry.verify()` | **MISSING** | — | — |
| `CapabilityRegistry.list_reusable()` | **PARTIAL** | `ZBC/function_map.json` + `function_registry.py` 有函数映射 | 概念对应 |

### 9.4 Shadow Lifecycle（OSAI AIDRH/src/shared/shadow_lifecycle.py）

| OSAI 声明函数 | ZBC 落地状态 | ZBC 证据 | 备注 |
|---------------|-------------|----------|------|
| `can_transition(current, target)` | **MISSING** | ZBC 无影子状态转换函数 | — |
| `transition(record, target, reason)` | **MISSING** | — | — |
| `is_shadow_safe(record)` | **PARTIAL** | `ZBC/v4_ai_shadow` 表(2行) + `data_feedback_loop.py` 有影子数据，但无状态安全判断函数 | 概念对应 |
| `required_exit_evidence(state)` | **MISSING** | — | — |

### 9.5 OSAI Contract 落地总结

| Contract 模块 | 声明函数数 | ZBC EXISTS | ZBC PARTIAL | ZBC MISSING | 落地率 |
|---------------|-----------|------------|-------------|-------------|--------|
| Research Record | 8 | 0 | 2 | 6 | 0% EXISTS / 25% PARTIAL |
| Safe Collection | 8 | 0 | 4 | 4 | 0% EXISTS / 50% PARTIAL |
| Capability Registry | 5 | 0 | 2 | 3 | 0% EXISTS / 40% PARTIAL |
| Shadow Lifecycle | 4 | 0 | 1 | 3 | 0% EXISTS / 25% PARTIAL |
| **合计** | **25** | **0** | **9** | **16** | **0% EXISTS / 36% PARTIAL** |

> **关键发现**：OSAI Contract 中声明的 25 个函数，ZBC 中 **0 个完全同名落地**，9 个有概念对应但实现独立（PARTIAL），16 个完全缺失（MISSING）。Contract 以文档/概念形式影响 ZBC 架构，但未通过代码级 import 或同名函数落地。这符合双子星"OSAI 定义契约、ZBC 自行实现生产代码"的架构定位，但也意味着 Contract 与实现之间缺乏自动化校验机制。

---

## 十、函数对账总结

### 10.1 最高保护层状态

| 函数/常量 | 状态 | 严重度 |
|-----------|------|--------|
| SUBJECT_WORDS | EXISTS | — |
| SUBJECT_EXCLUDE_WORDS | EXISTS | — |
| subject_hit() | PARTIAL（权威 EXISTS，但有 3 处 AI/stub 替代副本） | P1 |
| _subject_sql_and_values() | EXISTS（权威+2 处纯委托） | — |
| aggregate_events() | **MISSING** | **P0** |
| build_daily_report() | EXISTS（纯委托，实际逻辑在 daily_report.generate_daily_digest） | — |
| publish_datetime | EXISTS | — |
| captured_at | EXISTS | — |

### 10.2 核心问题

1. **P0 — `aggregate_events()` 已消失**：全仓无此函数定义，事件聚合逻辑内联到 database.py（classify_event_quality/get_events_curated）、app.py、event_graph.py，无法按函数名做保护与交接。
2. **P1 — subject_hit() 存在 AI/stub 替代副本**：app.py L2743（AI verify_taikoo_location 替代规则）、collector_v2/run_live_engine.py L16（AI）/L20（stub return False），与最高保护层 subject_rules.subject_hit() 口径不一致。
3. **P1 — risk_engine.py 退化为纯委托层**：仅 14 行，2 个函数各 1 行委托，无独立风险计算能力。
4. **P2 — OSAI Contract 函数零代码级落地**：25 个声明函数中 0 个同名落地，9 个概念对应，16 个缺失。
5. **P2 — 多份报告引擎并存**：根目录 report_engine.py(3.4KB) + report_export/report_engine.py(15.9KB)，职责边界不清。
6. **P2 — database.py `_subject_clause()` 与 `subject_rules._subject_sql_and_values()` 命名/实现分离**，需确认口径一致。
