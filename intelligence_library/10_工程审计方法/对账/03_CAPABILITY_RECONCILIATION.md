# 03 — CAPABILITY RECONCILIATION（能力对账）

> 审计日期：2026-09-02
> OSAI HEAD：`60af16a`（研究侧能力：AI / Research / Learning / Architecture / Contract / Capability）
> ZBC HEAD：`545a3ab`，v5.9.9（生产侧能力：Production Code / DB / Collection / Runtime / Test / E2E / Release）
> 状态四分类：EXISTS / PARTIAL / MISSING / UNKNOWN
> **注意**：OSAI 根目录旧的 `12_capability_matrix.md` 等 01–22 迁移期文档仅作历史参考，**不得**作为当前判断依据，必须以本地当前源码为准。

---

## 状态计数

| 能力域 | OSAI 状态 | ZBC 状态 |
|--------|-----------|-----------|
| 采集 | MISSING | EXISTS |
| 解析 | MISSING | EXISTS |
| 存储 | PARTIAL | EXISTS |
| 主题命中（最高保护层） | MISSING | EXISTS |
| 风险评估 | MISSING | PARTIAL |
| 报告 | MISSING | EXISTS |
| AI 分析 | PARTIAL | EXISTS |
| 学习 | EXISTS | EXISTS |
| Contract | EXISTS | PARTIAL |
| 权限 | MISSING | EXISTS |
| UI | EXISTS | EXISTS |
| 运维 | PARTIAL | EXISTS |
| 测试 | EXISTS | EXISTS |
| 发布 | MISSING | EXISTS |
| 事件图谱 | MISSING | EXISTS |
| 品牌情报 | MISSING | EXISTS |
| 舆情案例 | MISSING | EXISTS |
| 通知推送 | MISSING | EXISTS |
| 安全审计 | PARTIAL | EXISTS |
| **EXISTS 计数** | **5** | **17** |
| **PARTIAL 计数** | **4** | **2** |
| **MISSING 计数** | **11** | **0** |
| **UNKNOWN 计数** | **0** | **0** |

---

## 一、采集能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| 多平台采集（小红书/微博/B站/抖音） | MISSING | — | EXISTS | `collector_v2/xhs/collector.py` + `weibo/collector.py` + `platform_adapters/douyin.py` + `bilibili_login_manager.py` | ZBC 完整覆盖 |
| CDP 浏览器采集 | MISSING | — | EXISTS | `xhs_cdp_collector.py`(825行) + `cdp_helper.py`(485行) + `chrome-cdp-profile/` + `edge-cdp-*/`(4套) | Chrome/Edge CDP 自动化 |
| 官方信息抓取 | MISSING | — | EXISTS | `collector_v2/official_info_scraper.py`(25.6KB) | 官方账号信息 |
| 采集调度 | MISSING | — | EXISTS | `collector_v2/scheduler/collector_job.py` + `platform_adapters/scheduling/`(decision/planner/policy/gate/state_map/store) | 智能调度决策 |
| 采集守护/质量监控 | MISSING | — | EXISTS | `collector_guard/`(guard/analyzer/checkpoint/metrics/rate_limiter/risk_engine/state) | 采集质量闭环 |
| 采集自动化编排 | MISSING | — | EXISTS | `collector_automation.py`(600行) + `collector_auto_start.py` + `collector_v2_integration.py` | 自动化编排 |
| 安全采集 Contract | EXISTS（研究侧） | `AIDRH/src/contracts/safe_collection.py`(15.9KB) + `research/R-2026-0003-safe-xhs-collection.md` | PARTIAL | `safety_boundary.py`(365行) + `data_boundary.py`(198行) 实现了安全边界，但未 import OSAI safe_collection 模块 | OSAI 定义契约，ZBC 自行实现对应能力 |

---

## 二、解析能力

| 能力项 | OSAI 状态 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|----------|------|
| 小红书笔记解析 | MISSING | EXISTS | `collector_v2/xhs/parser.py`(7,872B) + `xhs/models.py` | 笔记/评论/详情解析 |
| 数据规范化 | MISSING | EXISTS | `collector_v2/pipeline/normalize.py`(7,523B) | 字段统一规范化 |
| 内容去重 | MISSING | EXISTS | `collector_v2/pipeline/deduplicate.py`(5,711B) + `database.py` L853 `find_duplicate_notes()` | 内容+语义去重 |
| 垃圾内容过滤 | MISSING | EXISTS | `collector_v2/pipeline/spam_filter.py`(4,377B) + `ai_filter.py`(308行) | 规则+AI 双层过滤 |
| 传播主体分类 | MISSING | EXISTS | `subject_classifier.py`(304行，SubjectClassifier 类：官方/媒体/机构/KOS) | 作者主体类型分类 |

---

## 三、存储能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| 关系型数据库 | MISSING | — | EXISTS | `data/monitor.db`（SQLite，53 表）+ `database.py`(968行/54函数) + `models.py` | 生产 DB |
| 数据库迁移 | MISSING | — | EXISTS | `database_migrations.py`(472行) + `migrations/009_*.sql` + `migrations/010_*.sql` | 版本化迁移 |
| 数据备份 | MISSING | — | EXISTS | `database.py` L623 `backup_database()` + `scripts/backup_db.py` + `deployment/数据库备份.py` + `backups/` | 备份机制 |
| JSON/JSONL 研究存储 | EXISTS | `AIDRH/data/research/records.jsonl`(42KB) + `data/learning/capability_registry.json` + `data/shadow/` 脱敏样本 | EXISTS | `data/` 576 文件（adaptive_history.json / ai_learning_log.jsonl / alerts.json / brand_directory.json 等） | 双端均有 JSON 存储，用途不同 |
| 证据存储 | EXISTS | `AIDRH/data/shadow/` + `architecture/ZACHARY-EXPERIENCE-SCHEMA-v1.md` | EXISTS | `app_evidence.py`（app_evidence_records 表，含 captured_at）+ `database.py` `save_event_insight()` | 双端均有证据存储 |

---

## 四、主题命中（最高保护层）

| 能力项 | OSAI 状态 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|----------|------|
| 主体词定义（SUBJECT_WORDS） | MISSING | EXISTS | `subject_rules.py` L13（18 个主体词：广州太古汇/太古汇/太古仓/汇悦台/LV太古汇 等） | **最高保护层** |
| 排除词定义（SUBJECT_EXCLUDE_WORDS） | MISSING | EXISTS | `subject_rules.py` L20（20 个排除词：上海太古汇/兴业太古汇/北京三里屯/南京西路 等） | **最高保护层，一票否决** |
| 主体判断函数（subject_hit） | MISSING | EXISTS | `subject_rules.py` L38（排除词优先→正向词匹配，5 字段检查） | **最高保护层** |
| 主体 SQL 过滤（_subject_sql_and_values） | MISSING | EXISTS | `subject_rules.py` L76（生成 WHERE 子句+参数）+ `database.py` L431 `_subject_clause()` + `app.py` L599（委托）+ `risk_engine.py` L9（委托） | **最高保护层，SQL 层硬过滤** |
| 主体过滤管线 | MISSING | EXISTS | `collector_v2/pipeline/subject_filter.py`(5,667B) | 采集管线中的主体过滤 |
| 主体分类 API | MISSING | EXISTS | `app.py` L237 `/api/subject-classifier/classify` + L256 `/api/subject-classifier/types` | 主体分类 HTTP API |
| aggregate_events（事件聚合） | MISSING | MISSING | 全仓无 `def aggregate_events`；仅在 `docs/7版方案x当前源码_深度匹配审计报告.docx`、`tests/audit_probe_4.py`、`tests/_archive_blueprint.py` 中被引用 | **最高保护层函数已消失**，事件聚合逻辑内联到 database.py/app.py 的 SQL 中 |

---

## 五、风险评估

| 能力项 | OSAI 状态 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|----------|------|
| 风险指数计算 | MISSING | EXISTS | `daily_report.py` L31 `calculate_risk_index(notes, events, period_days=1)` | 日报内风险计算 |
| 品牌健康度 | MISSING | EXISTS | `daily_report.py` L92 `calculate_brand_health_score(notes, risk_index)` | 品牌健康评分 |
| 风险引擎模块 | MISSING | PARTIAL | `risk_engine.py` 仅 14 行（委托层，无独立计算）；`collector_guard/risk_engine.py`(5,281B) 为采集守护风险引擎 | 根目录 risk_engine.py 已退化为兼容委托层，独立风险评估能力分散在 daily_report.py 和 collector_guard/ |
| 高危笔记识别 | MISSING | EXISTS | `database.py` L539 `get_high_risk_notes()` + `app.py` L1213 `/api/risk-alerts` | 高危笔记查询+预警 |
| 舆情预警 | MISSING | EXISTS | `app.py` L2782 `/api/alerts` + L2792 `/api/alerts/read` + L2807 `/api/alerts/refresh` + `data/alerts.json`(31KB) | 预警系统 |
| 负面评价审核 | MISSING | EXISTS | `app.py` L2833 `/api/negative/pending` + L2879 `/api/negative/confirm` + L2902 `/api/negative/reject` + L2925 `/api/negative-review/<id>/confirm` | 负面内容审核工作流 |

---

## 六、报告能力

| 能力项 | OSAI 状态 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|----------|------|
| 日报生成 | MISSING | EXISTS | `daily_report.py` L547 `generate_daily_digest()` + `report_engine.py` L31 `generate_report('daily')` | 完整日报流水线 |
| 周报/月报/年报 | MISSING | EXISTS | `report_engine.py` L17 `period_for()` 支持 daily/weekly/monthly/yearly | 多周期报告 |
| 报告存储 | MISSING | EXISTS | `database.py` L554 `save_daily_report()` + L884 `save_daily_digest()`（daily_reports 表 33 行 / daily_digest 表 7 行） | DB 持久化 |
| 报告导出 | MISSING | EXISTS | `export_report.py`(626行) + `report_export/report_engine.py`(15.9KB) + `app.py` L3115/L3141/L3151 导出路由 | 多格式导出 |
| 品牌报告 | MISSING | EXISTS | `brand_report_generator.py`(281行) + `app.py` L471 `/api/brand-report/generate` + L533 `/api/brand-report/export/<id>` | 品牌专项报告 |
| 专题报告 | MISSING | EXISTS | `app.py` L3758 `/api/special-report/generate` + L4108 `/api/report/special/export` | 专题报告 |
| 统计口径强制写回 | MISSING | EXISTS | `report_engine.py` L48-63（强制把 DB 统计写回报告，防止 AI 误写数字） | **最高保护层** |
| build_daily_report 函数 | MISSING | EXISTS | `risk_engine.py` L13 `build_daily_report(date_str=None)` → 委托 `daily_report.generate_daily_digest()` | 兼容层入口 |

---

## 七、AI 分析能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| AI 情感分析 | PARTIAL | `AIDRH/research/` 中有 AI 研究文档，但无生产情感分析代码 | EXISTS | `ai_analyzer.py`(595行) + `ark_llm.py`(316行) + `app.py` L1370 `/api/ark/sentiment` | ZBC 完整实现 |
| AI 摘要/关键词 | PARTIAL | — | EXISTS | `ai_analyzer.py` + `app.py` L1394 `/api/ark/summary` + L1423 `/api/ark/keywords` | 云端 LLM |
| AI 内容过滤 | PARTIAL | — | EXISTS | `ai_filter.py`(308行，`run_filter_batch()`) + `app.py` L2665 `/api/ai-filter/stats` + L2669 `/api/ai-filter/run` | AI 噪声/重复过滤 |
| AI 网关 | PARTIAL | — | EXISTS | `ai_gateway_v570.py`(202行) + `app.py` L2457 `/api/ai/analyze-v570` | 统一 AI 网关 |
| 本地 LLM | MISSING | — | EXISTS | `local_ai_client.py`(187行) + `.ollama/` + `app.py` L1317 `/api/ai/status` | Ollama 本地模型 |
| 远程 LLM | MISSING | — | EXISTS | `ark_llm.py`(316行，火山方舟) + `app.py` L1330 `/api/ark/status` + L1341 `/api/ark/chat` | 云端大模型 |
| AI 位置验证 | MISSING | — | EXISTS | `ai_analyzer.py` `verify_taikoo_location()`（被 app.py L2745 嵌套 subject_hit 调用） | AI 辅助主体判断 |
| AI 对话 | MISSING | — | EXISTS | `app.py` L2025 `/api/ai/chat` + L4916 `/api/ai/analyze` | AI 对话/分析 API |
| AI 研究/实验 | EXISTS | `AIDRH/research/R-2026-*.md`(8份) + `data/experiments/` + `benchmarks/` | PARTIAL | `evaluation_system.py`(389行) + `evaluate_system_timing.py`(230行) | OSAI 偏研究，ZBC 偏生产评估 |

---

## 八、学习能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| AI 学习引擎 | MISSING | — | EXISTS | `ai_learning_engine.py`(435行) + `app.py` L1705 `/api/ai-learning/status` + L1715 `/api/ai-learning/optimization/<op>` | 生产侧 AI 自学习 |
| 能力注册/提升生命周期 | EXISTS | `AIDRH/src/shared/capability_registry.py`(CapabilityRegistry: add/get/promote/deprecate/verify) + `data/learning/capability_registry.json` | PARTIAL | `function_registry.py`(111行) 为函数注册表，与 OSAI capability_registry 概念对应但非同一实现 | OSAI 定义能力生命周期，ZBC 有函数注册表 |
| 影子学习 | EXISTS | `AIDRH/src/shared/shadow_lifecycle.py`(状态机: can_transition/transition/is_shadow_safe) + `data/shadow/` + `DCC/server/shadow-learning.js`(21KB) + `DCC/docs/LEARNING-SHADOW-ARCHITECTURE.md`(22KB) | PARTIAL | `data_feedback_loop.py`(324行) + `v4_ai_shadow` 表(2行) | OSAI 有完整影子学习架构，ZBC 有数据反馈和 shadow 表 |
| 研究记录 | EXISTS | `AIDRH/src/contracts/research_record.py`(10.2KB: validate/sanitize/make_review/make_research_record) + `data/research/records.jsonl`(42KB) | MISSING | ZBC 无研究记录模块（生产侧不需要） | 双端职责差异 |
| 学习资料库 | EXISTS | `SICI-Core/docs/research-learning/`(PLATFORM_LEARNING_LIBRARY_v3 23KB + cth_poms_learning_records.json) + `SICI-Core/js/app.js`(31KB) PWA | MISSING | — | OSAI 独有学习资料分发 |
| 学习周期/提升工具 | EXISTS | `DCC/tools/learning_cycle.py` + `learning_promote.py` + `research_learning.py` + `tests/test_learning_cycle.py` + `test_promotion_gate.py`(12KB) | MISSING | — | OSAI 研究侧学习运维工具 |

---

## 九、Contract 能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| Research Record Contract | EXISTS | `AIDRH/src/contracts/research_record.py`(10.2KB) | MISSING | ZBC 无对应模块 | OSAI 独有 |
| Safe Collection Contract | EXISTS | `AIDRH/src/contracts/safe_collection.py`(15.9KB: redact_text/CollectionHygienePolicy/RateGovernor/build_collection_audit) | PARTIAL | `safety_boundary.py` + `data_boundary.py` 实现了安全边界，但未 import OSAI Contract | 概念对应，代码独立 |
| Domain Adapter Contract | EXISTS | `AIDRH/architecture/ZACHARY-DOMAIN-ADAPTER-CONTRACT-v1.md` | PARTIAL | `platform_adapters/base.py` + `registry.py` 实现了适配器框架 | 概念对应 |
| Learning Data Contract | EXISTS | `AIDRH/architecture/ZACHARY-LEARNING-DATA-CONTRACT-v1.json`(1.7KB) | MISSING | — | OSAI 独有 |
| Internal Learning Contract | EXISTS | `AIDRH/architecture/ZACHARY-INTERNAL-LEARNING-CONTRACT-v1.md`(6.2KB) | MISSING | — | OSAI 独有 |
| Bidirectional Learning Contract | EXISTS | `AIDRH/docs/ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901.md` | PARTIAL | `data_feedback_loop.py` 实现了生产→学习反馈，但无正式 Contract 模块 | 文档级契约，ZBC 部分实现 |
| Contract 代码级落地 | EXISTS（OSAI 侧） | OSAI src/contracts/ 2 份完整 Python Contract 模块 | PARTIAL | ZBC 未 import OSAI Contract 模块，自行实现了对应概念（function_registry/safety_boundary/data_boundary） | Contract 以文档/概念形式影响 ZBC，未代码级复用 |

---

## 十、权限能力

| 能力项 | OSAI 状态 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|----------|------|
| HTTP Basic Auth | MISSING | EXISTS | `app.py` L603 `@app.before_request _basic_auth()`（全局认证中间件） | 根路由统一 Basic Auth |
| v4 独立认证 | MISSING | EXISTS | `v4_upgrade/auth/service.py` + `app.py` L615 `from v4_upgrade.auth.service import get_current_user`（Basic 之外认可 v4 session） | /v4/ 路径独立 token/会话 |
| 认证恢复 | MISSING | EXISTS | `auth_recovery_center.py`(292行) + `auth_recovery_api.py` + `app.py` 相关路由 | 认证故障恢复 |
| 工作区权限 | MISSING | EXISTS | `v4_workspace_grants` 表(13行) + `v4_workspace_keys` 表(65行) + `v4_upgrade/` 权限模块 | 工作区级权限控制 |
| 用户管理 | MISSING | EXISTS | `v4_users` 表(1行) + `v4_sessions` 表(40行) + `v4_login_attempts` 表(26行) | 用户/会话/登录审计 |
| 安全边界 | MISSING | EXISTS | `safety_boundary.py`(365行) + `data_boundary.py`(198行) | 数据/操作安全边界 |
| 密钥扫描 | PARTIAL | `AIDRH/tools/secret_scan.py`(3,443B) + `research/R-2026-0007-ci-secret-scan-fix.md` | EXISTS | `security_scanner.py`(312行) | 双端均有安全扫描 |

---

## 十一、UI 能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| 生产 Dashboard | MISSING | — | EXISTS | `static/index.html`(81KB) + `static/js/app.js`(115KB) + `static/css/style.css`(88KB) | 主生产 UI |
| 研究控制台 | EXISTS | `DCC/index.html` + `server/server.js`(32KB) + `css/components.css`(14KB) | MISSING | — | OSAI 独有 |
| PWA 学习前端 | EXISTS | `SICI-Core/index.html` + `js/app.js`(31KB) + `manifest.json` + `sw.js` | MISSING | — | OSAI 独有 |
| 多主题 UI | PARTIAL | `AIDRH/design-system/`(ZBIP-DESIGN-TOKENS/ICON-SYSTEM/MOTION-TOKENS 6份) | EXISTS | `static/css/` 6+ 套主题（zb-gpt-theme 72KB / zb-theme 44KB / zbip-* 4份 / design-v8/v9） | ZBC 多主题并存，OSAI 有设计系统规范 |
| 话题活动 UI | MISSING | — | EXISTS | `static/topic_campaign.html` + `topic_campaign.js`(29KB) + `topic_campaign.css`(16KB) | 话题活动专项 UI |
| 移动端适配 | MISSING | — | EXISTS | `static/css/mobile.css`(20KB) | 移动端样式 |
| Flask 服务端模板 | MISSING | — | EXISTS | `templates/base.html` + `index.html` + `events.html` + `notes.html` + `report.html` | 服务端渲染 |

---

## 十二、运维能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| 系统健康检查 | MISSING | — | EXISTS | `app.py` L2619 `/healthz` + L2623 `/api/system/health` + `system_health_api.py`(500行) + `deployment/健康检查.py` | 健康检查 |
| 系统监控 | MISSING | — | EXISTS | `monitoring.py`(570行) + `stability_monitor.py`(435行) + `system_watchdog.py`(271行) + `system_guardian.py`(190行) | 多模块监控 |
| 自动恢复 | MISSING | — | EXISTS | `auto_recovery.py`(390行) + `系统守护闭环.ps1` + `start_system_guardian.bat` | 故障自动恢复 |
| 运行时预检 | PARTIAL | `AIDRH/tools/runtime_preflight.py`(7,030B) + `tests/test_runtime_preflight.py` | EXISTS | `runtime_preflight.py`(290行) + `app.py` 启动前检查 | 双端均有预检 |
| 日志管理 | MISSING | — | EXISTS | `logger.py`(268行) + `logs/` + 多份 prod_err/prod_out 日志 | 统一日志 |
| 缓存管理 | MISSING | — | EXISTS | `cache_manager.py`(291行) + `app.py` L2313 `/api/cache/status` + L2318 `/api/cache/data` | 缓存管理 |
| 内存优化 | MISSING | — | EXISTS | `memory_optimizer.py`(320行) | 内存优化 |
| 隧道/远程访问 | MISSING | — | EXISTS | `tunnel_guardian.py`(214行) + `cloudflared.exe`(54MB) + `start_cloudflare_*.bat`(多份) | Cloudflare Tunnel 远程访问 |
| 网络自适应 | MISSING | — | EXISTS | `network_adaptive.py`(197行) + `adaptive_engine.py`(325行) + `data/adaptive_history.json` + `adaptive_status.json` | 网络/采集自适应 |
| CI/CD | MISSING | — | EXISTS | `ci_cd.py`(435行) + `.github/workflows/` + `Dockerfile` + `docker-compose.yml` | 持续集成/部署 |
| 诊断脚本 | PARTIAL | — | EXISTS | 根目录 8 份 check_*.py + `quick_check.py` + `verify_system.py` + `verify_system_e2e.py`(290行) | 丰富的诊断工具 |

---

## 十三、测试能力

| 能力项 | OSAI 状态 | OSAI 证据 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|-----------|----------|------|
| 单元测试 | EXISTS | `AIDRH/tests/` 7 份（test_capability_registry/test_research_record/test_safe_collection 等）+ `DCC/tests/` 14 份 + `SICI-Core/tests/` 3 份 | EXISTS | `tests/` 295 份（test_database/test_ai/test_api/test_e2e 等） | 双端均有单元测试 |
| E2E 测试 | MISSING | — | EXISTS | `tests/test_e2e.py`(18KB) + `tests/test_browser_e2e.py` + `verify_system_e2e.py`(290行) | ZBC 完整 E2E |
| 审计探针 | MISSING | — | EXISTS | `tests/audit_probe_1~6.py`（架构/函数/依赖审计探针） | ZBC 独有审计测试 |
| 测试配置 | EXISTS | `DCC/.github/workflows/test.yml` + `SICI-Core/.github/workflows/platform-verify.yml` | EXISTS | `pytest.ini`(711B) + `tests/conftest.py` + `tests/run_all.py` | 双端均有 CI 测试 |
| 回归测试 | MISSING | — | EXISTS | `scripts/run_core_regression.py` + `tests/test_*` 覆盖核心模块 | ZBC 核心回归 |
| 影子运行测试 | EXISTS | `SICI-Core/shadow_run/`（SHADOW_RUN_REPORT.md + test_pyresilience.py + test_yyds_logger.py + xiaohongshu_bakeoff_report.md） | PARTIAL | `v4_ai_shadow` 表(2行) + `data_feedback_loop.py` | OSAI 有影子运行测试框架 |

---

## 十四、发布能力

| 能力项 | OSAI 状态 | ZBC 状态 | ZBC 证据 | 备注 |
|--------|-----------|-----------|----------|------|
| 版本管理 | MISSING | EXISTS | `VERSION`(5.9.9) + `CHANGELOG.md`(48KB) | 版本号+变更日志 |
| 发布策略 | MISSING | EXISTS | `RELEASE_POLICY.md` + `docs/DUAL_REPO_RELEASE_POLICY.md` + `docs/DUAL_REPO_RELEASE_STATE.md` | 发布策略文档 |
| 容器化发布 | MISSING | EXISTS | `Dockerfile` + `docker-compose.yml` + `docker-compose.staging.yml` + `docker/entrypoint.sh` | Docker 发布 |
| 预发布环境 | MISSING | EXISTS | `staging/` + `docker-compose.staging.yml` | Staging 环境 |
| 部署脚本 | MISSING | EXISTS | `deployment/`(16文件) + `scripts/start_production.ps1` + `run_production.py` + `start_system.bat` | 多种部署方式 |
| 升级协议 | MISSING | EXISTS | `UPGRADE.md` + `DOUBAO_GITHUB_UPGRADE_PROTOCOL.md` + `scripts/github_upgrade_check.py` | 升级流程 |
| 双仓库发布协调 | PARTIAL | `DCC/docs/DUAL_REPO_RELEASE_POLICY.md` + `DUAL_REPO_RELEASE_STATE.md` | EXISTS | `docs/DUAL_REPO_RELEASE_POLICY.md` + `docs/DUAL_REPO_RELEASE_STATE.md` | 双端均有双仓库发布策略文档 |

---

## 十五、其他生产能力（ZBC 独有）

| 能力域 | 状态 | ZBC 证据 | 说明 |
|--------|------|----------|------|
| 事件图谱 | EXISTS | `event_graph.py`(563行) + `app.py` L270 `/api/event-graph/stats` + L280 `/api/event-graph/events` + L295 `/api/event-graph/chain/<id>` | 事件/关系/链分析（event_graph_events 表 16 行 / event_graph_relations 表 1 行） |
| 品牌情报 | EXISTS | `brand_knowledge_base.py` + `brand_report_generator.py` + `brand_stats_recompute.py` + `swire_group.py`(417行) + `brand_directory.json`(49KB) + `brand_knowledge` 表(103行) | 品牌知识库/报告/统计 |
| 舆情案例库 | EXISTS | `public_opinion_cases.py`(510行) + `case_deep_analysis.py` + `pr_case_engine.py` + `pr_case_integration.py`(500行) + `case_library.json` + `pr_case_library.json` | 舆情/公关案例 |
| 话题活动 | EXISTS | `topic_campaign.py`(1,134行，最大模块) + `topic_monitor_policy.py` + `topic_note_detail_backfill.py` + `topic_campaigns` 表(1行) / `topic_campaign_topics`(7行) / `topic_campaign_notes`(120行) / `topic_campaign_snapshots`(325行) | 话题/活动监控 |
| 微信通知 | EXISTS | `wechat_notifier.py`(947行) + `app.py` L4025 `/api/weekly/send-email` + `notification_logs` 表(3行) | 微信/邮件通知推送 |
| Web 话题发现 | EXISTS | `web_topic_discovery.py` + `web_monitor.py` + `web_monitor_v570.py` + `web_topics` 表(96行) / `web_mentions`(79行) / `web_events`(20行) / `web_runs`(28行) | Web 端话题/提及发现 |
| 审核工作流 | EXISTS | `review_workflow.py`(348行) + `note_review_history` 表(8,327行) + `app.py` L2995 `/api/event-review/<id>/confirm` + L3014 `/api/event-review/pending` | 内容/事件审核 |
| 反馈关键词 | EXISTS | `database.py` L687 `upsert_feedback_keyword()` + `feedback_keywords` 表(16行) + `app.py` L1290 `/api/feedback-keywords` | 用户反馈关键词聚合 |
| 函数注册 | EXISTS | `function_registry.py`(111行) + `function_map.json`(7KB) + `app.py` L2021 `/api/function-map` | 函数注册/映射 |
| 系统配置 API | EXISTS | `settings_module.py`(276行) + `system_config.json` + `system_config` 表(10行) + `app.py` L3400 `/api/system/config` | 运行时配置管理 |

---

## 十六、能力对账总结

### 16.1 双端能力分布

| 端 | 核心能力 | 缺失能力 |
|----|----------|----------|
| **OSAI** | Contract 定义、能力注册/提升、影子学习、研究记录、学习资料库、研究控制台 UI、安全扫描、运行时预检、单元测试 | 采集、解析、生产存储、主题命中、风险评估、报告、生产 AI 分析、权限、生产 UI、运维、发布、事件图谱、品牌情报、舆情案例、通知推送 |
| **ZBC** | 全部生产能力（采集/解析/存储/主题命中/风险/报告/AI/权限/UI/运维/测试/发布/事件图谱/品牌情报/舆情案例/通知） | Research Record Contract、学习资料库 PWA、研究控制台、影子学习框架（仅有数据反馈） |

### 16.2 能力差距（PARTIAL/MISSING 项）

| 差距项 | 端 | 严重度 | 说明 |
|--------|-----|--------|------|
| `aggregate_events()` 缺失 | ZBC | P0 | 最高保护层函数不存在，事件聚合内联到 SQL |
| risk_engine.py 退化为委托层 | ZBC | P1 | 独立风险评估能力分散，无统一风险引擎 |
| Contract 未代码级落地 | ZBC | P1 | OSAI Contract 模块未被 ZBC import，ZBC 自行实现对应概念 |
| 双端数据流转非自动化 | 双端 | P2 | ZBC→OSAI 证据流转为手动文件复制 |
| AI 绕过规则主体判断 | ZBC | P1 | app.py L2743 嵌套 subject_hit 使用 AI 替代规则 |
| OSAI 无生产能力 | OSAI | 符合设计 | OSAI 定位为研究侧，无生产能力是预期架构 |
| 多套 UI 主题未统一 | ZBC | P2 | static/css/ 6+ 套主题并存 |
