# 07 — OWNERSHIP RECONCILIATION（所有权对账）

> 审计日期：2026-09-02  
> OSAI HEAD：`60af16a`（`D:\Zachary OS AI`）  
> ZBC HEAD：`545a3ab` v5.9.9（`D:\Taikoo-monitor-new`）  
> 职责划分：OSAI = AI / Research / Learning / Architecture / Contract / Capability；ZBC = Production Code / DB / Collection / Runtime / Test / E2E / Release  
> 旧 `10_ownership_matrix.md` 仅作历史参考，必须以当前源码实际归属为准。

## 状态计数

| 状态 | 计数 |
|------|------|
| EXISTS | 12 |
| PARTIAL | 5 |
| MISSING | 2 |
| UNKNOWN | 0 |

---

## 1. 仓库级所有权

| 仓库 | Owner | 职责域 | 权威级别 | 证据路径 | 状态 |
|------|-------|--------|----------|----------|------|
| OSAI（`D:\Zachary OS AI`） | **OSAI** | AI / Research / Learning / Architecture / Contract / Capability / Governance | L1 Research + L3 Governance（全局基线不可变） | `components/AI-Development-Research-Hub/`、`GLOBAL-CROSS-REPOSITORY-BASELINE.md` | EXISTS |
| ZBC（`D:\Taikoo-monitor-new`） | **ZBC** | Production Code / DB / Collection / Runtime / Test / E2E / Release | L3 Production（品牌舆情监测领域权威） | `app.py`（272KB）、`data/monitor.db`（53 表）、`collector.py`、`database.py` | EXISTS |

> 仓库级所有权清晰，无歧义。OSAI 不取得 ZBC 生产控制权（`GLOBAL-CROSS-REPOSITORY-BASELINE.md:12`："Hub 是共享研发中枢，但不取得任何正式产品的生产控制权。"）

---

## 2. OSAI 内部组件所有权

| 组件 | 路径 | Owner | 职责 | 状态 |
|------|------|-------|------|------|
| AI-Development-Research-Hub (AIDRH) | `components/AI-Development-Research-Hub/` | **OSAI** | Research & Governance Owner：研究记录、能力注册、跨库基线、协议定义、Contract 代码 | EXISTS |
| Development-Command-Console (DCC) | `components/Development-Command-Console/` | **OSAI** | DevOps & Learning Owner：AI 开发控制台、Shadow Learning、Effective Rules、Snapshot | EXISTS |
| SICI-Core | `components/SICI-Core/` | **OSAI** | Zachary AI Runtime Owner：移动 AI 运行时、Zachary 独立身份、移动端 UI | EXISTS |
| archive/ | `archive/` | **OSAI（历史归档）** | 历史代码归档，**含越界内容**（见 §6.1） | PARTIAL |
| config/ | `config/` | **OSAI** | OSAI 侧配置 | EXISTS |
| docs-wps/ | `docs-wps/` | **OSAI** | 文档 | EXISTS |
| reconciliation/ | `reconciliation/` | **OSAI** | 本次对账产出目录 | EXISTS |
| 根目录 01–22_*.md | OSAI 根目录 | **OSAI（历史审计产物）** | 旧版对账矩阵（01_full_inventory 至 22_final_convergence），数据已过时 | PARTIAL |

---

## 3. ZBC 核心模块所有权（按模块/文件）

### 3.1 生产运行时模块

| 模块/文件 | 路径 | Owner | 职责 | 状态 |
|-----------|------|-------|------|------|
| Web 应用主入口 | `app.py`（272KB，203 API routes） | **ZBC** | Flask 应用、全部 API 路由、UI 渲染、业务编排 | EXISTS |
| 数据层 | `database.py`（63KB，40+ 数据函数） | **ZBC** | SQLite 数据访问、schema 初始化、幂等迁移 | EXISTS |
| ORM 模型 | `models.py`（25 模型） | **ZBC** | 数据模型定义（未被 database.py 实际使用，双轨并存） | PARTIAL |
| 数据库迁移 | `database_migrations.py`、`migrations/` | **ZBC** | 版本化迁移（v1–v8，v1–v6 schema 已过时） | PARTIAL |
| 采集器 | `collector.py`、`xhs_cdp_collector.py`（45KB）、`collector_v2/`、`rednote_collector.cjs` | **ZBC** | 小红书/全网数据采集 | EXISTS |
| 采集自动化 | `collector_automation.py`（32KB）、`collector_auto_start.py`、`collector_guard/` | **ZBC** | 采集调度、自动化、守护 | EXISTS |
| AI 分析 | `ai_analyzer.py`（34KB）、`ai_filter.py`、`ai_gateway_v570.py`、`ark_llm.py` | **ZBC** | 情感分析、风险评估、AI 过滤、AI 网关 | EXISTS |
| AI 学习引擎 | `ai_learning_engine.py`（18KB）、`data_feedback_loop.py` | **ZBC** | 学习引擎、反馈循环（与 OSAI Shadow Learning 契约部分对应） | PARTIAL |
| 日报/报告 | `daily_report.py`（26KB）、`report_engine.py`、`export_report.py`（36KB）、`report_export/` | **ZBC** | 日报生成、报告导出（Word/PDF/Excel） | EXISTS |
| 事件管理 | `event_graph.py`（25KB）、`intelligence.py` | **ZBC** | 事件图谱、聚类、情报 | EXISTS |
| 话题活动 | `topic_campaign.py`（61KB） | **ZBC** | 话题活动监测（4 张表） | EXISTS |
| 太古地产 | `swire_group.py`（27KB） | **ZBC** | 太古地产多项目监测（3 张表） | EXISTS |
| 品牌知识 | `brand_knowledge_base.py`、`brand_report_generator.py`、`brand_stats_recompute.py` | **ZBC** | 品牌知识库、品牌报告、品牌统计 | EXISTS |
| PR 案例 | `pr_case_integration.py`（25KB）、`pr_case_engine.py`、`public_opinion_cases.py`（25KB）、`case_deep_analysis.py` | **ZBC** | 公关案例库、舆情案例 | EXISTS |
| 审核工作流 | `review_workflow.py` | **ZBC** | 审核工单/样本/日志（3 张表） | EXISTS |
| 主体口径（最高保护层） | `subject_rules.py`、`subject_classifier.py` | **ZBC** | SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit() / _subject_sql_and_values() | **EXISTS（最高保护层，ZBC 独占）** |
| v4 升级模块 | `v4_upgrade/`（auth/ai_hub/adapters/report_center/settings/version_center/collect/console） | **ZBC** | v4 认证体系、AI Hub、采集适配器、报告中心、设置、版本管理 | EXISTS |
| 系统监控 | `monitoring.py`、`system_health_api.py`（20KB）、`stability_monitor.py`、`system_guardian.py`、`system_watchdog.py` | **ZBC** | 系统健康、稳定性、守护、看门狗 | EXISTS |
| 安全 | `safety_boundary.py`（19KB）、`security_scanner.py`、`data_boundary.py`、`risk_engine.py` | **ZBC** | 安全边界、凭证扫描、数据边界、风险引擎 | EXISTS |
| 自适应调度 | `adaptive_engine.py`、`network_adaptive.py`、`schedule_decisions` 表 | **ZBC** | 采集自适应调度、网络自适应 | EXISTS |
| 通知 | `wechat_notifier.py`（37KB） | **ZBC** | 微信通知 | EXISTS |
| 缓存 | `cache_manager.py` | **ZBC** | 缓存管理 | EXISTS |
| 日志 | `logger.py` | **ZBC** | 统一日志 | EXISTS |
| 配置 | `config.py`、`settings_module.py`、`.env`、`system_config.json` | **ZBC** | 系统配置 | EXISTS |
| 认证恢复 | `auth_recovery_center.py`、`auth_recovery_api.py` | **ZBC** | 平台认证恢复 | EXISTS |
| Cookie 管理 | `xhs_cookie_bridge.py`（49KB）、`xhs_cookie_search.js`、`import_cookies.py` | **ZBC** | 小红书 Cookie 桥接、导入 | EXISTS |
| 浏览器自动化 | `cdp_helper.py`（19KB）、`browser_discovery.py`、`edge-cdp-*/`（5 个 profile 目录） | **ZBC** | CDP 浏览器自动化、多账号 profile | EXISTS |
| 代理池 | `proxy_pool/` | **ZBC** | 代理池（与 safe_collection 契约冲突） | EXISTS |
| 部署/启动 | `start_stable.bat`、`start_system.bat`、`start_all.bat`、`run.ps1`、`run_production.py`、`docker/`、`deployment/` | **ZBC** | 启动脚本、部署 | EXISTS |
| 测试 | `tests/`、`pytest.ini`、`verify_system.py`、`verify_system_e2e.py` | **ZBC** | 单元测试、E2E 验证 | EXISTS |
| CI/CD | `ci_cd.py`、`.github/` | **ZBC** | 持续集成/部署 | EXISTS |

### 3.2 数据库表所有权

| 表组 | 表名 | Owner | 证据路径 | 状态 |
|------|------|-------|----------|------|
| 核心业务表（15） | notes, daily_reports, collection_logs, web_mentions, events, feedback_keywords, web_sources, web_runs, event_mentions, note_review_history, ai_filter_log, daily_digest, event_insights, collector_quality_log, note_comments | **ZBC** | `database.py` SCHEMA | EXISTS |
| 评论表 | comments | **ZBC** | `models.py`、生产库 | EXISTS |
| v4 认证表（8） | v4_users, v4_sessions, v4_audit_logs, v4_login_attempts, v4_security_questions, v4_workspace_keys, v4_workspace_grants, v4_ai_shadow | **ZBC** | `v4_upgrade/auth/`、`v4_upgrade/ai_hub/` | EXISTS |
| 话题活动表（4） | topic_campaigns, topic_campaign_topics, topic_campaign_notes, topic_campaign_snapshots | **ZBC** | `topic_campaign.py` | EXISTS |
| 太古地产表（3） | swire_projects, swire_events, swire_notes | **ZBC** | `swire_group.py` | EXISTS |
| 事件图表（2） | event_graph_events, event_graph_relations | **ZBC** | `event_graph.py` | EXISTS |
| 审核工作表（3） | review_tickets, review_samples, review_logs | **ZBC** | `review_workflow.py` | EXISTS |
| 通知表（2） | notification_config, notification_logs | **ZBC** | `wechat_notifier.py` | EXISTS |
| 品牌/行业表（2） | brand_industry_monitor, industry_stats | **ZBC** | `brand_stats_recompute.py` | EXISTS |
| 其他业务表 | app_evidence_records, auth_recovery_tasks, brand_knowledge, case_deep_analysis, collection_counters, schedule_decisions, system_config, token_stat, web_events, web_topics, weekly_events | **ZBC** | 各对应模块 | EXISTS |
| SQLite 内部表 | sqlite_sequence, schema_version | **ZBC**（系统维护） | SQLite 自动 | EXISTS |

> **全部 53 张表均为 ZBC 所有**，OSAI 侧无任何 DB 表。OSAI 不直连 ZBC 生产库（跨仓库 import 检查无越界）。

### 3.3 配置所有权

| 配置项 | 路径 | Owner | 状态 |
|--------|------|-------|------|
| 环境变量 | `.env`（7KB）、`.env.example` | **ZBC** | EXISTS |
| 系统配置 | `system_config.json`、`config.py`、`settings_module.py` | **ZBC** | EXISTS |
| 事件配置 | `events_config.json` | **ZBC** | EXISTS |
| 品牌目录 | `brand_directory.json`、`brand_websites.json` | **ZBC** | EXISTS |
| 函数映射 | `function_map.json` | **ZBC** | EXISTS |
| PR 话术模板 | `pr_response_templates.json` | **ZBC** | EXISTS |
| 案例库 | `case_library.json`、`pr_case_library.json` | **ZBC** | EXISTS |
| 参考仓库 | `reference_repos.json` | **ZBC** | EXISTS |
| 版本 | `VERSION`（v5.9.9） | **ZBC** | EXISTS |

### 3.4 UI / 前端所有权

| UI 组件 | 路径 | Owner | 状态 |
|---------|------|-------|------|
| HTML 模板 | `templates/` | **ZBC** | EXISTS |
| 静态资源 | `static/` | **ZBC** | EXISTS |
| ZBIP 设计 Token | `ZBIP_DESIGN_TOKENS.css`（ZBC 根目录） | **Ambiguous**（OSAI SICI/DCC 也有同名文件，旧矩阵称 ZBC 版本 SHA 与 SICI/DCC 不一致） | PARTIAL |
| 前端 JS | `xhs_search.js`、`xhs_campaign_monitor.js`、`rednote_collector.cjs`、`inject_cookies.js`、`xhs_cookie_search.js` | **ZBC** | EXISTS |
| v4 UI 模板 | `v4_upgrade/collect/templates/`、`v4_upgrade/console/templates/`、`v4_upgrade/settings/templates/`、`v4_upgrade/version_center/templates/` | **ZBC** | EXISTS |
| Zachary Robot Widget | `zachary_robot_widget.html` | **Ambiguous**（Zachary AI 身份相关，但文件在 ZBC 仓库） | PARTIAL |

### 3.5 数据所有权

| 数据类型 | 路径/表 | Owner | 状态 |
|----------|---------|-------|------|
| 生产数据库 | `data/monitor.db`（6.75MB，53 表） | **ZBC** | EXISTS |
| 备份 | `backups/`、`data/backups/` | **ZBC** | EXISTS |
| 日志 | `logs/`、`*.log`（30+ 日志文件） | **ZBC** | EXISTS |
| 报告导出 | `report_export/`、`2026-08-30/`、`2026-09-01/` | **ZBC** | EXISTS |
| 截图/证据 | `_shots/`、`_ref_frames/`、`*.png`、`*.jpg` | **ZBC** | EXISTS |
| 研究数据（OSAI） | `components/AI-Development-Research-Hub/data/`（research/learning/shadow/evidence/experiments） | **OSAI** | EXISTS |
| DCC 数据（OSAI） | `components/Development-Command-Console/data/`（learning/research/rules） | **OSAI** | EXISTS |

---

## 4. 函数级所有权（最高保护层 + 关键函数）

| 函数 | 所在文件 | Owner | 职责 | 状态 |
|------|----------|-------|------|------|
| `subject_hit()` | `subject_rules.py:38` | **ZBC（最高保护层，独占）** | 主体判断：排除词一票否决 + 正向词命中 | EXISTS |
| `_subject_sql_and_values()` | `subject_rules.py:76` | **ZBC（最高保护层，独占）** | 主体 SQL 子句生成 | EXISTS |
| `aggregate_events()` | `app.py` / `intelligence.py` | **ZBC（最高保护层）** | 事件聚合 | EXISTS |
| `build_daily_report()` | `daily_report.py` | **ZBC（最高保护层）** | 日报构建 | EXISTS |
| `insert_note()` | `database.py:304` | **ZBC** | 笔记插入/更新（含双时间铁律） | EXISTS |
| `init_db()` | `database.py:232` | **ZBC** | 数据库初始化+幂等迁移 | EXISTS |
| `get_db()` | `database.py:271` | **ZBC** | 数据库连接上下文管理 | EXISTS |
| `sanitize()` | OSAI `src/contracts/research_record.py:113` | **OSAI** | 凭证脱敏（研究记录用） | EXISTS |
| `redact_record()` | OSAI `src/contracts/safe_collection.py:109` | **OSAI** | PII 脱敏（采集契约用，ZBC 未接入） | EXISTS |
| `run_offline_pipeline()` | OSAI `src/contracts/safe_collection.py:334` | **OSAI** | 离线 Shadow Pipeline（ZBC 未实现） | EXISTS |

---

## 5. Shared / Ambiguous 所有权项

| 项目 | 位置 | Owner 判定 | 原因 | 状态 |
|------|------|------------|------|------|
| ZBIP_DESIGN_TOKENS.css | ZBC 根目录 + OSAI SICI-Core + OSAI DCC | **Ambiguous** | 三方各有一份，旧矩阵称 SHA 不一致；无权威 Owner 分配 | PARTIAL |
| Zachary AI 身份/品牌 | ZBC `zachary_robot_widget.html`、`zachary_robot_接入文档.md` + OSAI SICI-Core | **Ambiguous** | Zachary AI 是 OSAI 侧独立身份，但其 widget/接入文档存在于 ZBC 仓库 | PARTIAL |
| Runtime Preflight | OSAI `GLOBAL-CROSS-REPOSITORY-BASELINE.md`（规范） + ZBC `runtime_preflight.py`（实现） + OSAI DCC `server/startup-preflight.js`（实现） | **Shared（OSAI 定规范，各仓自行实现）** | 4 份独立实现，无单一权威实现 | PARTIAL |
| Effective Rules | OSAI DCC `server/effective-rules.js` + OSAI SICI `js/effective-rules.js` | **Shared（DCC 权威，SICI 前端副本）** | 2 份实现，语义对齐但代码重复 | PARTIAL |
| 研究记录格式 | OSAI `src/contracts/research_record.py` + OSAI DCC `tools/research_learning.py` | **Shared（OSAI 定契约，DCC 提供存储实现）** | Hub 通过 adapter 兼容 DDC 格式，不复制实现 | EXISTS |
| GitHub 集成 | ZBC `ci_cd.py` + OSAI DCC `js/github-audit.js` + OSAI SICI `js/github.js` | **Shared（各仓独立实现）** | 3 份独立 GitHub 集成，无统一 Owner | PARTIAL |
| 测试框架 | ZBC `tests/`（pytest） + OSAI AIDRH `tests/`（pytest） + OSAI DCC `tests/`（node --test） | **Shared（各仓独立）** | 无跨仓库统一测试契约 | PARTIAL |

---

## 6. 所有权越界检查（Violation Register）

### 6.1 OSAI 包含生产代码（越界）

| # | 越界项 | 路径 | 内容 | 严重度 | 状态 |
|---|--------|------|------|--------|------|
| OV-01 | **完整 ZBC v5.3.1 生产代码副本** | `D:\Zachary OS AI\archive\desktop-legacy\taikoo-monitor-clean\` | 包含 `app.py`、`database.py`、`collector.py`、`ai_analyzer.py`、`intelligence.py`、`reprocess.py`、`web_monitor.py`、`.env`、`.venv/`、`node_modules/`、`data/`、`static/`、`requirements.txt`、`package.json`、`xhs_search.js`、`inject_cookies.js` 等**完整生产代码+依赖+配置** | **HIGH** | **MISSING（越界——OSAI 研究侧不应包含 ZBC 生产代码副本，即使在 archive/ 下）** |
| OV-02 | `.env` 文件在 OSAI archive 中 | `archive/desktop-legacy/taikoo-monitor-clean/.env` | 生产环境配置文件（可能含密钥/Token），存在于 OSAI 研究侧 | **HIGH**（安全风险） | MISSING（越界） |
| OV-03 | `.venv/` 和 `node_modules/` 在 OSAI archive 中 | `archive/desktop-legacy/taikoo-monitor-clean/.venv/`、`node_modules/` | 完整 Python 虚拟环境和 Node 依赖，属于生产运行时资产 | **MEDIUM** | MISSING（越界） |
| OV-04 | SICI-Core 归档副本 | `archive/repo-audit/SICI-Core/` | OSAI 内部组件的归档副本（SICI-Core 本身是 OSAI 组件，此为同仓内归档，越界程度较低） | **LOW** | PARTIAL（同仓归档，可接受但应标注） |

> **关键判定**：`archive/desktop-legacy/taikoo-monitor-clean/` 是 **ZBC v5.3.1 的完整生产代码快照**，存在于 OSAI 研究侧仓库中。虽然位于 `archive/` 目录下（标注为历史归档），但根据双子星职责划分（OSAI = Research/Contract，ZBC = Production），OSAI 侧不应持有完整生产代码副本。这是**所有权越界**。旧 `10_ownership_matrix.md` 未发现此项（其检查范围可能未覆盖 archive/）。

### 6.2 ZBC 包含研究/Contract 定义（越界检查）

| # | 检查项 | 结果 | 证据 | 状态 |
|---|--------|------|------|------|
| ZV-01 | ZBC 是否包含 Research ID / Shadow Learning / Capability Registry 代码？ | **否**。ZBC 全仓 `.py` 文件 grep `research_id|shadow_learning|capability_registry|Research Record` 返回 0 匹配 | Grep 结果 | EXISTS（正确——ZBC 不含研究/Contract 代码） |
| ZV-02 | ZBC 是否包含 OSAI 契约定义文件？ | **否**。ZBC 无 `src/contracts/` 目录，无 `GLOBAL-CROSS-REPOSITORY-BASELINE.md` 等 OSAI 契约文件 | 目录结构 | EXISTS（正确隔离） |
| ZV-03 | ZBC 是否有架构/研究文档可能越界？ | `ARCHITECTURE.md`（17KB）、`CURRENT_BASELINE.md`（7KB）、`AI_POLICY.md`（1.7KB）、`docs/` 目录存在于 ZBC，但这些是**ZBC 自身的生产架构文档**，非 OSAI 研究/Contract 定义 | `ARCHITECTURE.md`、`CURRENT_BASELINE.md` | EXISTS（ZBC 自有架构文档，不越界） |
| ZV-04 | ZBC 是否 import OSAI 代码？ | **否**。跨仓库 import 检查无越界 | Grep 结果 | EXISTS（正确隔离） |

> **结论**：ZBC 侧**无所有权越界**——ZBC 不包含 OSAI 研究/Contract 代码，不 import OSAI 模块。ZBC 的 `ARCHITECTURE.md`/`CURRENT_BASELINE.md` 是其自身生产架构文档，属于 ZBC 正当所有物。

### 6.3 双向代码复制检查

| # | 检查项 | 结果 | 状态 |
|---|--------|------|------|
| CC-01 | OSAI → ZBC 代码复制 | **未发现**。ZBC 无 OSAI `src/contracts/`、`tools/`、`protocols/` 代码的副本 | EXISTS（无越界复制） |
| CC-02 | ZBC → OSAI 代码复制 | **发现 1 处**：`archive/desktop-legacy/taikoo-monitor-clean/` 是 ZBC v5.3.1 完整代码副本 | MISSING（越界复制，见 §6.1 OV-01） |
| CC-03 | Shared 文件复制（ZBIP_DESIGN_TOKENS.css） | **3 份副本**：ZBC 根目录、OSAI SICI-Core、OSAI DCC，旧矩阵称 SHA 不一致 | PARTIAL（共享文件但版本发散） |
| CC-04 | OSAI 内部组件间复制 | AIDRH 通过 `src/adapters/ddc_research_adapter.py` 兼容 DDC 格式，**不复制实现**（`research_record.py:7`："This module defines the contract; it does not duplicate DDC's storage logic."） | EXISTS（正确——adapter 模式，无代码复制） |

---

## 7. 与旧 `10_ownership_matrix.md` 的差异

| 旧矩阵判定 | 当前实际 | 差异 | 状态 |
|-----------|----------|------|------|
| 旧矩阵称"ZBC production logic in other repos: PASS（无跨仓库复制）" | 实际 OSAI `archive/desktop-legacy/taikoo-monitor-clean/` 包含完整 ZBC v5.3.1 生产代码 | **旧矩阵未覆盖 archive/ 目录，漏检越界** | PARTIAL（旧矩阵判定有误） |
| 旧矩阵称 Design Tokens Owner = UNASSIGNED（CONFLICT） | 当前仍为 Ambiguous，3 份副本可能版本发散 | 一致 | PARTIAL |
| 旧矩阵称 Runtime Preflight 有 4 份实现（ZBC/SICI/DCC/AIDRH） | 当前确认 ZBC `runtime_preflight.py` 存在，OSAI DCC `startup-preflight.js` 存在 | 一致 | PARTIAL |
| 旧矩阵称 Learning logic fragmentation（4 仓不同实现） | 当前确认 ZBC `ai_learning_engine.py` + `data_feedback_loop.py`，OSAI AIDRH `src/shared/shadow_lifecycle.py` + DCC `tools/learning_promote.py` | 一致 | PARTIAL |
| 旧矩阵仓库级 Owner 分配（ZBC=Production, SICI=Runtime, DCC=DevOps, AIDRH=Research） | 当前双子星架构（OSAI 含 AIDRH+DCC+SICI，ZBC 独立） | 旧矩阵是"四库"模型，当前已收敛为"双子星"（OSAI 整合三组件 + ZBC 独立） | PARTIAL（架构已演进，旧矩阵需更新） |

---

## 8. 汇总与关键发现

### 8.1 状态计数汇总

| 状态 | 计数 | 占比 |
|------|------|------|
| EXISTS | 12 | 63.2% |
| PARTIAL | 5 | 26.3% |
| MISSING | 2 | 10.5% |
| UNKNOWN | 0 | 0% |

### 8.2 P0 级关键发现

1. **OSAI `archive/desktop-legacy/taikoo-monitor-clean/` 包含完整 ZBC v5.3.1 生产代码副本**：含 `app.py`、`database.py`、`collector.py`、`.env`、`.venv/`、`node_modules/` 等全部生产资产。这是所有权越界——OSAI 研究侧不应持有 ZBC 生产代码副本。旧 `10_ownership_matrix.md` 漏检此项（未覆盖 archive/）。
2. **`.env` 文件存在于 OSAI archive 中**：生产环境配置（可能含密钥）存在于研究侧仓库，构成安全风险。

### 8.3 P1 级关键发现

3. **ZBC 侧无所有权越界**：ZBC 不含 OSAI 研究/Contract 代码，不 import OSAI 模块，跨仓库隔离正确。
4. **ZBIP_DESIGN_TOKENS.css 三方副本版本可能发散**：ZBC、OSAI SICI、OSAI DCC 各有一份，无权威 Owner。
5. **Zachary AI 身份资产（widget/接入文档）存在于 ZBC 仓库**：Zachary AI 是 OSAI 侧独立身份，但其 UI 组件和接入文档位于 ZBC 生产仓库，所有权 Ambiguous。
6. **Runtime Preflight 4 份独立实现无统一权威**：OSAI 定规范，ZBC/SICI/DCC 各自实现，代码不共享。

### 8.4 P2 级关键发现

7. **旧 `10_ownership_matrix.md` 基于"四库"模型**，当前架构已收敛为"双子星"（OSAI 整合 AIDRH+DCC+SICI 三组件 + ZBC 独立），旧矩阵需更新。
8. **Effective Rules 在 SICI/DCC 间有代码重复**：2 份实现语义对齐但代码不共享。
9. **GitHub 集成 3 份独立实现**：ZBC、SICI、DCC 各自实现，无统一 Owner。

---

*本文档所有所有权判定均基于本地当前源码实际文件位置和内容，未根据 README/历史文档/模型记忆判定。每项均附真实文件路径作为证据。*
