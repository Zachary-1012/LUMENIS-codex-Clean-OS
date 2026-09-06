# 02 — ARCHITECTURE RECONCILIATION（架构对账）

> 审计日期：2026-09-02
> OSAI HEAD：`60af16a`（研究侧：AI / Research / Learning / Architecture / Contract / Capability）
> ZBC HEAD：`545a3ab`，v5.9.9（生产侧：Production Code / DB / Collection / Runtime / Test / E2E / Release）
> 状态四分类：EXISTS / PARTIAL / MISSING / UNKNOWN
> 基线：双子星双库架构 — OSAI 负责研究/契约/能力，ZBC 负责生产/数据/运行时

---

## 状态计数

| 架构维度 | EXISTS | PARTIAL | MISSING | UNKNOWN |
|----------|--------|---------|---------|---------|
| 分层架构 | 5 | 1 | 0 | 0 |
| 模块边界 | 6 | 1 | 0 | 0 |
| 入口点 | 4 | 0 | 0 | 0 |
| 运行时 | 3 | 1 | 0 | 0 |
| 采集管线 | 4 | 1 | 0 | 0 |
| 报告管线 | 4 | 0 | 0 | 0 |
| AI 模块 | 5 | 1 | 0 | 0 |
| 双端流向 | 3 | 1 | 0 | 0 |
| 边界违规检查 | 4 | 0 | 2 | 0 |
| **合计** | **38** | **5** | **2** | **0** |

---

## 一、分层架构

### 1.1 表现层（UI / API Gateway）

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| Flask Web 应用入口 | EXISTS | `ZBC/app.py` L1188 `@app.route('/')`，5,131 行，203 个路由 | 单一 Flask 应用承载所有 API + 静态页面 |
| 前端静态资源 | EXISTS | `ZBC/static/index.html`(81KB)、`static/js/app.js`(115KB)、`static/css/` 25 份 | 多套主题并存（zb-gpt-theme / zb-theme / zbip-* / design-v8/v9） |
| Flask 模板 | EXISTS | `ZBC/templates/base.html` / `index.html` / `events.html` / `notes.html` / `report.html` | 5 份服务端渲染模板 |
| OSAI 研究控制台 UI | EXISTS | `OSAI/components/Development-Command-Console/index.html` + `server/server.js`(32KB) | Node.js 全栈控制台，独立于 ZBC 生产 UI |
| OSAI PWA 前端 | EXISTS | `OSAI/components/SICI-Core/index.html` + `js/app.js`(31KB) + `manifest.json` | PWA 学习资料库前端 |
| UI 跨边界污染 | PARTIAL | `ZBC/static/css/` 存在 6+ 套并行主题（style.css 88KB / zb-gpt-theme 72KB / zb-theme 44KB / zbip-* 4 份 / design-v8/v9） | 多套主题未统一，存在 UI 层冗余，但无 OSAI→ZBC 直接代码复制 |

### 1.2 业务逻辑层（Service / Engine）

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| 报告引擎 | EXISTS | `ZBC/report_engine.py`（generate_report/generate_all/get_bundle）+ `report_export/report_engine.py`(15.9KB 独立导出引擎) | 两层报告引擎并存 |
| 日报引擎 | EXISTS | `ZBC/daily_report.py` 618+ 行，12 个函数（generate_daily_digest L547 / calculate_risk_index L31 / generate_executive_summary L507） | 核心日报逻辑 |
| 风险引擎 | PARTIAL | `ZBC/risk_engine.py` 仅 14 行，为兼容委托层（`_subject_sql_and_values`→subject_rules、`build_daily_report`→daily_report）；`collector_guard/risk_engine.py`(5,281B) 为采集守护风险引擎 | 根目录 risk_engine.py 无独立风险计算逻辑，已退化为委托层 |
| 事件图谱 | EXISTS | `ZBC/event_graph.py` 563 行（事件/关系/链分析） | 独立事件图谱模块 |
| 话题活动 | EXISTS | `ZBC/topic_campaign.py` 1,134 行（最大业务模块） | 话题/活动/笔记关联 |
| 舆情案例 | EXISTS | `ZBC/public_opinion_cases.py` 510 行 + `case_deep_analysis.py` + `pr_case_engine.py` + `pr_case_integration.py` | 案例/公关子系统 |
| 品牌情报 | EXISTS | `ZBC/brand_report_generator.py` + `brand_knowledge_base.py` + `brand_stats_recompute.py` + `swire_group.py`(417行) | 品牌情报子系统 |
| 情报模块 | EXISTS | `ZBC/intelligence.py` 219 行 + `context_intelligence.py` | 情报刷新/聚合 |

### 1.3 数据访问层（DAO / Repository）

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| 数据库核心层 | EXISTS | `ZBC/database.py` 968+ 行，54 个函数（init_db/get_db/insert_note/get_notes/save_daily_report/find_duplicate_notes 等） | 单一 database.py 承载全部 DAO |
| 数据模型 | EXISTS | `ZBC/models.py` 259 行 | ORM/数据类定义 |
| 数据库迁移 | EXISTS | `ZBC/database_migrations.py` 472 行 + `migrations/009_*.sql` + `migrations/010_*.sql` | 迁移管理 + SQL 脚本 |
| 主体过滤 SQL 子句 | EXISTS | `ZBC/database.py` L431 `_subject_clause()` + `subject_rules.py` L76 `_subject_sql_and_values()` | 最高保护层，SQL 层主体硬过滤 |
| 数据边界 | EXISTS | `ZBC/data_boundary.py` 198 行 + `safety_boundary.py` 365 行 | 数据/安全边界控制 |

### 1.4 采集层（Collection / Ingestion）

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| 基础采集器 | EXISTS | `ZBC/collector.py` 282 行 | 第一代采集器 |
| 第二代采集管线 | EXISTS | `ZBC/collector_v2/` 30 文件：`pipeline/`(deduplicate/normalize/persist/spam_filter/subject_filter) + `scheduler/` + `session/` + `weibo/` + `xhs/` | 完整管线架构（采集→去重→规范化→主体过滤→垃圾过滤→持久化） |
| 采集守护 | EXISTS | `ZBC/collector_guard/` 8 文件（guard/analyzer/checkpoint/metrics/rate_limiter/risk_engine/state） | 采集质量守护闭环 |
| 平台适配器 | EXISTS | `ZBC/platform_adapters/` 32 文件（base/xhs/douyin/rednote_policy + scheduling/ 决策子系统） | 多平台适配 + 智能调度 |
| 小红书专项采集 | EXISTS | `ZBC/xhs_cdp_collector.py`(825行) + `xhs_cookie_bridge.py`(811行) + `xhs_p0_orchestrator.py` + `xhs_runtime_state.py` | CDP 浏览器采集 + Cookie 管理 + P0 编排 |
| 微博/B站登录 | EXISTS | `ZBC/weibo_login_manager.py`(294行) + `bilibili_login_manager.py`(185行) | 平台登录态管理 |
| 采集自动化 | EXISTS | `ZBC/collector_automation.py` 600 行 + `collector_auto_start.py` + `collector_v2_integration.py` | 自动化编排 |

### 1.5 基础设施层（Infrastructure / Cross-cutting）

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| 配置管理 | EXISTS | `ZBC/config.py` 327 行 + `.env` + `config/industry_platforms.json` + `system_config.json` | 多层配置 |
| 日志 | EXISTS | `ZBC/logger.py` 268 行 | 统一日志 |
| 缓存 | EXISTS | `ZBC/cache_manager.py` 291 行 | 缓存管理 |
| 认证/权限 | EXISTS | `ZBC/app.py` L603 `@app.before_request _basic_auth()`（HTTP Basic + v4 session）+ `v4_upgrade/auth/service.py` + `auth_recovery_center.py` | 双层认证：根路由 Basic Auth，/v4/ 独立 token |
| 系统监控 | EXISTS | `ZBC/monitoring.py`(570行) + `system_health_api.py`(500行) + `stability_monitor.py`(435行) + `system_watchdog.py` + `system_guardian.py` | 多模块监控并存 |
| 安全扫描 | EXISTS | `ZBC/security_scanner.py` 312 行 | 安全扫描 |
| 运行时预检 | EXISTS | `ZBC/runtime_preflight.py` 290 行 | 启动前检查 |
| 自动恢复 | EXISTS | `ZBC/auto_recovery.py` 390 行 + `auth_recovery_api.py` | 故障自动恢复 |
| CI/CD | EXISTS | `ZBC/ci_cd.py` 435 行 + `.github/workflows/` + `Dockerfile` + `docker-compose.yml` | 持续集成/容器化 |

---

## 二、模块边界

### 2.1 OSAI 模块边界

| 模块 | 状态 | 证据路径 | 职责边界 |
|------|------|----------|----------|
| AIDRH（AI 研发枢纽） | EXISTS | `OSAI/components/AI-Development-Research-Hub/` | Research Record Contract / Safe Collection Contract / Capability Registry / Shadow Lifecycle — 纯研究契约，无生产代码 |
| DCC（研发控制台） | EXISTS | `OSAI/components/Development-Command-Console/` | Node.js 学习/影子/证据/变更计划控制台 — 研究运维，不连接生产 DB |
| SICI-Core | EXISTS | `OSAI/components/SICI-Core/` | PWA 学习资料库 + 平台校验 + upgrade_modules（base_adapter/dual_pool/unified_logger）— 学习资料分发 |
| OSAI 根目录 | EXISTS | `OSAI/01-22_*.md` + `README.md` | 历史对账文档（迁移期产物，仅参考） |
| OSAI 生产代码 | MISSING | — | OSAI 无生产运行时代码、无生产数据库、无生产 API。全部源码为 untracked 研究/契约代码 |

### 2.2 ZBC 模块边界

| 模块 | 状态 | 证据路径 | 职责边界 |
|------|------|----------|----------|
| Web/API 层 | EXISTS | `ZBC/app.py` | 203 路由，HTTP 入口，认证中间件 |
| 主体保护层 | EXISTS | `ZBC/subject_rules.py` | 唯一权威：SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() / _subject_sql_and_values() |
| 数据层 | EXISTS | `ZBC/database.py` + `models.py` | 全部 DB 访问，主体 SQL 过滤 |
| 采集层 | EXISTS | `ZBC/collector_v2/` + `collector_guard/` + `platform_adapters/` + `xhs_*.py` | 多平台采集→管线→守护 |
| 报告层 | EXISTS | `ZBC/report_engine.py` + `daily_report.py` + `report_export/` + `export_report.py` | 日报/周报/月报/导出 |
| AI 层 | EXISTS | `ZBC/ai_*.py` + `ark_llm.py` + `local_ai_client.py` | AI 分析/过滤/学习/网关 — 仅增强层，不改变主体规则 |
| 业务层 | EXISTS | `ZBC/topic_campaign.py` + `event_graph.py` + `public_opinion_cases.py` + `brand_*.py` + `swire_group.py` | 话题/事件/案例/品牌 |
| 系统层 | EXISTS | `ZBC/monitoring.py` + `system_*.py` + `stability_monitor.py` + `auto_recovery.py` | 监控/健康/恢复 |
| 模块边界模糊 | PARTIAL | `ZBC/app.py` 5,131 行包含路由+业务逻辑+嵌套函数（如 L2743 嵌套 subject_hit）；`database.py` 968 行包含 DAO+业务统计+去重逻辑 | 核心模块过大，app.py 和 database.py 存在"上帝模块"倾向，边界不够清晰 |

---

## 三、入口点

| 入口点 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| Flask 生产入口 | EXISTS | `ZBC/app.py` L1188 `@app.route('/')`，文件末尾 `if __name__ == '__main__'` | 主 Web 应用 |
| 生产启动脚本 | EXISTS | `ZBC/run_production.py`(5,287B) + `run_supervised.py`(7,767B) + `run.ps1` + `start_system.bat` + `start_all.bat` | 多种启动入口 |
| 采集入口 | EXISTS | `ZBC/collector_automation.py` + `collector_v2/run_live_engine.py` + `scripts/collect_now.py` | 采集任务入口 |
| OSAI 研究入口 | EXISTS | `OSAI/components/Development-Command-Console/server/server.js` + `SICI-Core/index.html` | Node.js 控制台 + PWA，非生产入口 |
| OSAI 生产入口 | MISSING | — | OSAI 无生产运行时入口 |

---

## 四、运行时

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| Python 运行时 | EXISTS | `ZBC/.venv/` + `requirements.txt`(873B) | Flask + 数据采集 + AI 依赖 |
| Node.js 运行时 | EXISTS | `ZBC/nodejs/` + `node_modules/` + `package.json` | 前端构建 + 小红书 JS 采集脚本（rednote_collector.cjs / xhs_*.js） |
| 本地 LLM 运行时 | EXISTS | `ZBC/.ollama/` + `local_ai_client.py` | Ollama 本地模型 |
| 容器化运行时 | EXISTS | `ZBC/Dockerfile` + `docker-compose.yml` + `docker/entrypoint.sh` | Docker 部署 |
| 运行时环境复杂度 | PARTIAL | 同时存在 Python venv + Node.js + Ollama + Chrome/Edge CDP 浏览器（6 套 profile）+ Cloudflare Tunnel + 代理池 | 多运行时并存，运维复杂度高，但无跨仓库运行时依赖 |

---

## 五、采集管线

### 5.1 管线阶段

| 阶段 | 状态 | 证据路径 | 说明 |
|------|------|----------|------|
| 平台接入 | EXISTS | `ZBC/platform_adapters/xhs.py` + `xhs_app_topic.py` + `douyin.py` + `weibo_login_manager.py` + `bilibili_login_manager.py` | 多平台适配器 |
| 浏览器会话 | EXISTS | `ZBC/collector_v2/session/browser_session.py` + `cdp_helper.py`(485行) + `chrome-cdp-profile/` + `edge-cdp-*/`(4套) | CDP 浏览器自动化 |
| 数据抓取 | EXISTS | `ZBC/collector_v2/xhs/collector.py` + `weibo/collector.py` + `official_info_scraper.py`(25.6KB) + `xhs_cdp_collector.py`(825行) | 多源抓取 |
| 解析 | EXISTS | `ZBC/collector_v2/xhs/parser.py` + `xhs/models.py` | 数据解析/建模 |
| 去重 | EXISTS | `ZBC/collector_v2/pipeline/deduplicate.py` + `database.py` L853 `find_duplicate_notes()` | 内容去重 |
| 规范化 | EXISTS | `ZBC/collector_v2/pipeline/normalize.py` | 字段规范化 |
| 主体过滤 | EXISTS | `ZBC/collector_v2/pipeline/subject_filter.py` + `subject_rules.py`（最高保护层） | 广州太古汇主体硬过滤 |
| 垃圾过滤 | EXISTS | `ZBC/collector_v2/pipeline/spam_filter.py` + `ai_filter.py` | 规则+AI 双层过滤 |
| 持久化 | EXISTS | `ZBC/collector_v2/pipeline/persist.py` + `database.py` `insert_note()` | 写入 monitor.db |
| 采集守护 | EXISTS | `ZBC/collector_guard/guard.py` + `rate_limiter.py` + `checkpoint.py` + `metrics.py` + `analyzer.py` | 采集质量/速率/检查点 |
| 调度 | EXISTS | `ZBC/collector_v2/scheduler/collector_job.py`(9,680B) + `platform_adapters/scheduling/`(decision/planner/policy/gate/state_map/store) | 智能调度决策 |
| 管线完整性 | PARTIAL | `collector_v2/pipeline/` 5 阶段齐全，但 `app.py` L2743 存在独立嵌套 `subject_hit()`（调用 AI verify_taikoo_location 而非 subject_rules.subject_hit），与管线 subject_filter 口径不一致 | rednote 采集路径绕过了统一管线的主体过滤，使用 AI 替代规则判断 |

---

## 六、报告管线

| 阶段 | 状态 | 证据路径 | 说明 |
|------|------|----------|------|
| 数据获取 | EXISTS | `ZBC/database.py` `get_notes_by_date_range()`(L594) + `get_stats_by_date_range()`(L599) | 从 DB 获取主体过滤后的数据 |
| AI 过滤预跑 | EXISTS | `ZBC/report_engine.py` L39 `ai_filter.run_filter_batch(limit=500)` | 报告生成前先跑 AI 过滤 |
| AI 分析 | EXISTS | `ZBC/ai_analyzer.py` `generate_period_report()` + `daily_report.py` `_ai_summarize_event()`(L327) + `_ai_generate_daily_summary()`(L618) | AI 增强报告内容 |
| 日报生成 | EXISTS | `ZBC/daily_report.py` `generate_daily_digest()`(L547) → calculate_risk_index → generate_today_summary → generate_key_insights → generate_action_items → generate_executive_summary | 完整日报流水线 |
| 周期报告 | EXISTS | `ZBC/report_engine.py` `generate_report()`(L31) 支持 daily/weekly/monthly/yearly | 多周期报告 |
| 报告存储 | EXISTS | `ZBC/database.py` `save_daily_report()`(L554) + `save_daily_digest()`(L884) | 写入 daily_reports / daily_digest 表 |
| 报告导出 | EXISTS | `ZBC/export_report.py`(626行) + `report_export/report_engine.py`(15.9KB) + `app.py` L3115/L3141/L3151 导出路由 | 多格式导出 |
| 统计口径强制写回 | EXISTS | `ZBC/report_engine.py` L48-63 强制把 DB 统计口径写回报告（total_notes/positive/negative/high_risk 等） | 防止 AI 摘要误写数字 — 最高保护层 |
| 品牌报告 | EXISTS | `ZBC/brand_report_generator.py` + `app.py` L471 `/api/brand-report/generate` | 品牌专项报告 |

---

## 七、AI 模块

| 模块 | 状态 | 证据路径 | 说明 |
|------|------|----------|------|
| AI 分析器 | EXISTS | `ZBC/ai_analyzer.py` 595 行（含 `verify_taikoo_location()`） | 情感分析/摘要/关键词/位置验证 |
| AI 过滤器 | EXISTS | `ZBC/ai_filter.py` 308 行（`run_filter_batch()`） | AI 噪声/重复过滤 |
| AI 网关 | EXISTS | `ZBC/ai_gateway_v570.py` 202 行 | v5.7.0 AI 网关统一入口 |
| AI 学习引擎 | EXISTS | `ZBC/ai_learning_engine.py` 435 行 | AI 自学习/优化 |
| 远程 LLM | EXISTS | `ZBC/ark_llm.py` 316 行（火山方舟） | 云端大模型 |
| 本地 LLM | EXISTS | `ZBC/local_ai_client.py` 187 行 + `.ollama/` | Ollama 本地模型 |
| 数据反馈闭环 | EXISTS | `ZBC/data_feedback_loop.py` 324 行 | 生产数据→AI 学习反馈 |
| AI 作为规则增强 | EXISTS | `ZBC/report_engine.py` L38-42（AI 过滤异常不阻塞规则报告）+ `subject_rules.py`（规则为最高权威，AI 不改变主体口径） | AI 仅增强层，规则+DB 为最高判断 |
| AI 绕过规则风险 | PARTIAL | `ZBC/app.py` L2743 嵌套 `subject_hit()` 调用 `ai_analyzer.verify_taikoo_location()` 而非 `subject_rules.subject_hit()`；`collector_v2/run_live_engine.py` L16/L20 存在 `subject_hit` stub（一个调用 AI，一个直接 return False） | rednote/直播采集路径使用 AI 替代规则主体判断，存在与最高保护层口径不一致的风险 |

---

## 八、双端流向

### 8.1 OSAI → Contract/Plan → ZBC（研究→生产）

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| Contract 定义 | EXISTS | `OSAI/components/AI-Development-Research-Hub/src/contracts/research_record.py`(10.2KB) + `safe_collection.py`(15.9KB) + `architecture/ZACHARY-*-CONTRACT-v1.md`(多份) | Research Record / Safe Collection / Domain Adapter 等契约 |
| Capability Registry | EXISTS | `OSAI/components/AI-Development-Research-Hub/src/shared/capability_registry.py` + `data/learning/capability_registry.json` | 能力注册/提升/废弃生命周期 |
| Bidirectional Learning Contract | EXISTS | `OSAI/components/AI-Development-Research-Hub/docs/ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901.md` | 明确"Zachary 不得直接改写 ZBC 权威规则或生产数据" |
| Immutable Baseline | EXISTS | `OSAI/components/AI-Development-Research-Hub/docs/ZACHARY-IMMUTABLE-BASELINE-20260902.md` + `ZBC/CURRENT_BASELINE.md` | 不可变基线 |
| Contract 在 ZBC 落地 | PARTIAL | OSAI Contract（research_record / safe_collection / capability_registry）为 Python 模块，但 ZBC 生产代码中**无 import** 这些 OSAI 模块；ZBC 有独立的 `function_registry.py`、`data_feedback_loop.py`、`safety_boundary.py`，与 OSAI Contract 概念对应但非同一代码 | Contract 以文档/概念形式影响 ZBC 架构，但未通过代码级 import 落地；ZBC 自行实现了对应能力 |
| Plan/工单驱动 | EXISTS | `OSAI/components/Development-Command-Console/server/change-plan.js` + `ZBC/docs/` 中 FEATURE-GAP-REGISTER / TECHNOLOGY-OPTIMIZATION-BACKLOG | 变更计划/工单体系 |

### 8.2 ZBC → Result/Evidence → OSAI（生产→研究）

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| 生产数据导出 | EXISTS | `ZBC/data/` 576 文件（JSON/JSONL/日志）+ `database.py` `backup_database()`(L623) + `scripts/backup_db.py` | 生产数据可导出为研究素材 |
| 证据记录 | EXISTS | `ZBC/app_evidence.py`（app_evidence_records 表，含 captured_at 字段）+ `OSAI/components/AI-Development-Research-Hub/data/shadow/`（脱敏样本：audit_xhs_guangzhou_tgk_20notes.json 等） | 生产证据→研究侧脱敏样本 |
| 研究记录 | EXISTS | `OSAI/components/AI-Development-Research-Hub/data/research/records.jsonl`(42KB) + `src/contracts/research_record.py` | 研究记录存储 |
| Shadow Learning | EXISTS | `OSAI/components/AI-Development-Research-Hub/src/shared/shadow_lifecycle.py` + `data/shadow/` + `DCC/docs/LEARNING-SHADOW-ARCHITECTURE.md`(22KB) + `DCC/server/shadow-learning.js`(21KB) | 影子学习架构，生产数据在研究侧影子运行 |
| 反馈闭环 | EXISTS | `ZBC/data_feedback_loop.py` + `OSAI/components/Development-Command-Console/server/learning-store.js`(26KB) | 生产结果→学习存储 |
| 证据→OSAI 自动化 | PARTIAL | 生产数据到 OSAI 研究侧的流转主要靠手动导出/文件复制，无自动化 ETL 管线；OSAI `data/shadow/` 样本为静态脱敏文件 | 双端数据流转为文件级手动同步，非自动化管线 |

---

## 九、边界违规检查

### 9.1 越权调用

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| OSAI 调用 ZBC 生产 API/DB | MISSING（未发现违规） | Grep `OSAI/components/**/*.py` for `taikoo|monitor|app\.py|database|collector` → 0 命中 | OSAI 研究代码无直接调用 ZBC 生产代码 |
| ZBC 调用 OSAI 研究模块 | MISSING（未发现违规） | Grep `ZBC/**/*.py` for `osai|zachary_os|zachary-os` → 0 命中 | ZBC 生产代码无直接 import OSAI 模块 |
| 越权调用结论 | EXISTS（合规） | 双端无代码级直接调用，通过 Contract/Plan/数据文件交互 | 符合双子星边界规范 |

### 9.2 反向生产写入

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| OSAI 写入 ZBC 生产 DB | MISSING（未发现违规） | OSAI 无数据库连接代码，无 monitor.db 写入 | OSAI 不接触生产 DB |
| OSAI 修改 ZBC 生产代码 | MISSING（未发现违规） | OSAI 仓库独立，无 ZBC 源码副本（archive/ 为历史归档，非当前） | 无反向写入 |
| Agent 绕过 Permission 直接写生产 | UNKNOWN | 无法从静态源码判断运行时 Agent 行为；`ZBC/app.py` L3495 `/api/config/run-code` 和 L5081 `/api/dev/run-code` 存在代码执行端点，需运行时审计确认是否有 Agent 绕过 | 存在代码执行 API 端点，静态分析无法确认是否被 Agent 绕过权限直接写入生产 |

### 9.3 代码复制

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| OSAI→ZBC 代码复制 | MISSING（未发现直接复制） | OSAI `src/contracts/` 与 ZBC 无同名模块；OSAI `upgrade_modules/`（base_adapter_enhanced/dual_pool/unified_logger）在 ZBC 中无对应文件 | 无直接代码复制 |
| ZBC→OSAI 代码复制 | PARTIAL | `OSAI/archive/desktop-legacy/2026-08/app.py`(20KB) / `database.py`(35KB) / `intelligence.py`(12KB) 为 ZBC 旧版本代码快照，但位于 archive/ 历史归档目录，非当前 OSAI 组件代码 | 历史归档中存在 ZBC 旧代码快照，但已归档，不构成当前代码复制 |
| ZBC 内部代码复制 | EXISTS | `app.py` L599 `_subject_sql_and_values()` 与 `risk_engine.py` L9 与 `subject_rules.py` L76 为同一函数的三份副本（后两者为委托）；`app.py.bak_p0_20260902_094442` + `app_backup_v589.py` 为 app.py 备份；`collector_v2/` 下多份 `.v5.3.2-pre-opt` 备份文件 | 存在函数多份委托副本和备份文件，但属于兼容层/备份，非恶意复制 |

### 9.4 DB 乱连

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| OSAI 连接 ZBC DB | MISSING（未发现违规） | OSAI 无 sqlite3.connect('monitor.db') 或任何 ZBC DB 连接代码 | OSAI 不连接生产 DB |
| ZBC 多 DB 连接 | EXISTS | `ZBC/database.py` `get_db()` 单例连接 `data/monitor.db`；根目录存在 `monitor.db`(12KB，疑似空/旧) + `你的数据库文件名.db`(0字节，空文件) + `data/monitor.db`(主生产库) | 根目录存在冗余/空 DB 文件，但生产代码统一连接 `data/monitor.db`，无乱连 |
| DB 连接结论 | EXISTS（合规） | 生产代码统一使用 `data/monitor.db`，OSAI 不连接生产 DB | 符合边界规范 |

### 9.5 UI 跨边界

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| OSAI UI 嵌入 ZBC 生产 | MISSING（未发现违规） | OSAI DCC/SICI 为独立前端，ZBC `static/` 无 OSAI 组件引用 | 无 UI 跨边界 |
| ZBC UI 引用 OSAI | PARTIAL | `ZBC/tools/development-command-console/` 为 DCC 的 Git 子模块（git status 显示 modified），作为 ZBC 的工具嵌入，但位于 `tools/` 而非 `static/`，不直接影响生产 UI | DCC 作为子模块存在于 ZBC tools/ 目录，但未嵌入生产 UI 渲染流程 |
| UI 跨边界结论 | EXISTS（基本合规） | 生产 UI（static/）与 OSAI UI 分离；DCC 子模块位于 tools/ 不影响生产渲染 | 符合边界规范 |

### 9.6 Agent 绕过 Permission

| 检查项 | 状态 | 证据路径 | 说明 |
|--------|------|----------|------|
| 代码执行端点 | EXISTS | `ZBC/app.py` L3495 `/api/config/run-code`（POST）+ L5081 `/api/dev/run-code`（POST）+ L1987 `/api/developer/run`（POST） | 存在 3 个代码执行 API，需 Basic Auth 或 v4 session 保护 |
| 工作区终端 | EXISTS | `ZBC/app.py` L5171 `/api/workspace/term`（POST）+ L5138 `/api/workspace/file-tree` | 存在远程终端/文件管理 API |
| Agent 绕过风险 | UNKNOWN | 静态分析无法确认运行时是否有 Agent 通过这些端点绕过权限直接操作生产；这些端点受 `@app.before_request _basic_auth()` 保护（L603），但 `/v4/` 路径使用独立认证 | 存在代码执行/终端端点，认证机制存在，但是否被 Agent 绕过需运行时审计 |
| 权限边界 | EXISTS | `ZBC/safety_boundary.py`(365行) + `data_boundary.py`(198行) + `v4_upgrade/` 权限模块 + `app.py` L603 全局认证中间件 | 权限控制代码存在 |

---

## 十、架构对账总结

### 10.1 架构合规性

| 维度 | 结论 |
|------|------|
| 双子星职责分离 | EXISTS — OSAI 纯研究/契约/能力，ZBC 纯生产/数据/运行时，无代码级交叉调用 |
| 分层架构 | EXISTS — ZBC 有清晰的 UI→API→业务→DAO→DB 分层；OSAI 有 Contract→Research→Learning 分层 |
| 最高保护层 | EXISTS — subject_rules.py 为唯一权威，app.py/risk_engine.py 均委托；报告层强制写回统计口径 |
| 双端流向 | PARTIAL — Contract/Plan 流向存在但未代码级落地；Result/Evidence 流向为文件级手动同步，无自动化管线 |
| 边界违规 | 未发现越权调用/反向生产写入/DB 乱连/UI 跨边界；代码复制仅限历史归档和兼容委托层；Agent 绕过 Permission 为 UNKNOWN（需运行时审计） |

### 10.2 架构风险（PARTIAL/MISSING 项）

| 风险项 | 严重度 | 说明 |
|--------|--------|------|
| `aggregate_events()` 已消失 | P1 | 最高保护层函数不存在，事件聚合逻辑内联到 database.py/app.py，无法按函数名做保护与交接 |
| app.py 嵌套 subject_hit 绕过规则 | P1 | L2743 rednote 采集使用 AI verify_taikoo_location 替代 subject_rules.subject_hit，口径不一致 |
| 上帝模块 | P2 | app.py 5,131 行 / database.py 968 行，模块边界模糊 |
| 多套 UI 主题并存 | P2 | static/css/ 6+ 套主题，未统一 |
| 双端数据流转非自动化 | P2 | ZBC→OSAI 证据流转为手动文件复制 |
| 代码执行/终端端点 | P2 | 3 个 run-code API + workspace/term，需运行时审计 Agent 绕过风险 |
| 根目录冗余 DB 文件 | P3 | monitor.db(12KB) + 你的数据库文件名.db(0B) 与 data/monitor.db 并存 |
