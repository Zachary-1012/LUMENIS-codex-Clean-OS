# 01 — SOURCE INVENTORY（双子星双库源清单）

> 审计日期：2026-09-02
> OSAI HEAD：`60af16a`（branch main）
> ZBC HEAD：`545a3ab`（branch main，VERSION=5.9.9）
> 状态四分类：EXISTS / PARTIAL / MISSING / UNKNOWN
> 事实优先级：本地当前源码 > Git > 历史文档

---

## 状态计数

| 维度 | EXISTS | PARTIAL | MISSING | UNKNOWN |
|------|--------|---------|---------|---------|
| OSAI 顶层目录 | 6 | 0 | 0 | 0 |
| OSAI 关键文件类别 | 5 | 1 | 0 | 0 |
| ZBC 顶层目录 | 44 | 0 | 0 | 0 |
| ZBC 关键源码文件 | 90 | 0 | 0 | 0 |
| ZBC 子目录 | 12 | 0 | 0 | 0 |

---

## 一、OSAI（研究侧）= `D:\Zachary OS AI`

### 1.1 顶层目录（6/6 EXISTS）

| 路径 | 状态 | 规模/说明 | Tracked? |
|------|------|-----------|----------|
| `.git/` | EXISTS | Git 仓库元数据 | — |
| `archive/` | EXISTS | 历史归档（desktop-legacy 旧代码+素材、repo-audit 旧仓库快照） | 否（untracked） |
| `components/` | EXISTS | 三个子组件：AI-Development-Research-Hub / Development-Command-Console / SICI-Core | 部分 tracked（仅 6 个文件），其余 untracked |
| `config/` | EXISTS | `codex/` 下 AGENTS.md(0字节) + config.toml(3765B) | 否（untracked） |
| `docs-wps/` | EXISTS | 2 个 docx：研发测试文档 + 双子库收敛研发总指令 V1.0 | 否（untracked） |
| `reconciliation/` | EXISTS | 本对账目录（含 _SPEC.md） | 否（untracked，新建） |

### 1.2 根目录文件（Tracked = 34 文件）

| 类别 | 状态 | 文件 | 规模 |
|------|------|------|------|
| 旧对账文档（01–22） | EXISTS（历史参考，非当前判断依据） | `01_full_inventory.md` … `22_final_convergence.md`（共 22 份） | 6KB–20KB/份，合计约 230KB |
| 项目文档 | EXISTS | `README.md` | 45,248 B |
| 变更日志 | EXISTS | `CHANGELOG.md` | 6,168 B |
| Git 配置 | EXISTS | `.gitignore` | 1,390 B |

> **注意**：根目录 `12_capability_matrix.md` 等 01–22 文档均为迁移期历史产物，按 SPEC 仅作历史参考，**不得**作为当前架构/能力判断依据。

### 1.3 components/ 子组件详单

#### 1.3.1 AI-Development-Research-Hub（AIDRH）

| 路径 | 状态 | 说明 | Tracked? |
|------|------|------|----------|
| `src/__init__.py` | EXISTS | 0 B 包标记 | 否 |
| `src/adapters/__init__.py` | EXISTS | 0 B | 否 |
| `src/adapters/ddc_research_adapter.py` | EXISTS | DDCResearchAdapter 类（append/read_all/find_by_id），2,312 B | 否 |
| `src/contracts/__init__.py` | EXISTS | 0 B | 否 |
| `src/contracts/research_record.py` | EXISTS | Research Record Contract（validate/sanitize/make_review 等），10,249 B | 否 |
| `src/contracts/safe_collection.py` | EXISTS | Safe Collection Contract（redact_text/CollectionHygienePolicy/RateGovernor 等），15,917 B | 否 |
| `src/shared/__init__.py` | EXISTS | 0 B | 否 |
| `src/shared/capability_registry.py` | EXISTS | CapabilityRegistry 类（add/get/promote/deprecate/verify），5,776 B | 否 |
| `src/shared/shadow_lifecycle.py` | EXISTS | Shadow 生命周期状态机（can_transition/transition/is_shadow_safe），3,686 B | 否 |
| `tests/test_*.py`（7 份） | EXISTS | capability_registry / ddc_adapter / research_record / runtime_preflight / safe_collection / shadow_lifecycle | 否 |
| `tools/research_id.py` | EXISTS | 2,962 B | 否 |
| `tools/runtime_preflight.py` | EXISTS | 7,030 B | 否 |
| `tools/secret_scan.py` | EXISTS | 3,443 B | 否 |
| `architecture/*.md`（11 份） | EXISTS | ADR-0001、CONTENT-INTELLIGENCE-SPEC、ZACHARY-*-v1 等架构契约文档 | 否 |
| `research/R-2026-*.md`（8 份） | EXISTS | R-0002~0008 研究报告 + content-intelligence 案例 | 否 |
| `cases/` | EXISTS | 5 份案例 + INDEX.json | 否 |
| `data/` | EXISTS | repository_matrix.json、learning/capability_registry.json、research/records.jsonl(42KB)、shadow/ 脱敏样本 | 否 |
| `docs/` | EXISTS | M5 集成状态、ZACHARY-IMMUTABLE-BASELINE、BIDIRECTIONAL-LEARNING-CONTRACT 等 + operations/protocols 子目录 | 部分（ZBIP_EXECUTION_LOG_2026-09-02.md tracked） |
| `logs/` | EXISTS | 4 份研发日志 | 否 |
| `design-system/` | EXISTS | ZBIP 设计令牌/图标/动效/架构图（6 份 md） | 否 |
| `benchmarks/` | EXISTS | 仅 .gitkeep | 否 |
| `protocols/` | EXISTS | 仅 .gitkeep + CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY.md | 否 |
| `.github/workflows/research-validation.yml` | EXISTS | 3,663 B | 否 |
| 根级 md（README/CAPABILITY-REGISTRY/PLATFORM_BASELINE 等 8 份） | EXISTS | 部分 tracked（CAPABILITY-REGISTRY.md、PLATFORM_BASELINE.md） | 部分 |

**AIDRH 小结**：以 Python Contract/Research 代码为主（src/ 约 38KB），无生产运行时代码，无数据库。全部 src/ 代码均为 untracked。

#### 1.3.2 Development-Command-Console（DCC）

| 路径 | 状态 | 说明 | Tracked? |
|------|------|------|----------|
| `index.html` | EXISTS | 18,062 B 前端入口 | 否 |
| `package.json` | EXISTS | 1,379 B | 否 |
| `css/`（2 份） | EXISTS | components.css(14KB) + tokens.css(4.9KB) | 否 |
| `js/`（5 份） | EXISTS | bridge.js / github-audit.js(15KB) / search.js / task.js / theme.js | 否 |
| `server/`（11 份 .js） | EXISTS | server.js(32KB) / learning-store.js(26KB) / shadow-learning.js(21KB) / evidence-bundle.js(17KB) 等 Node.js 服务端 | 否 |
| `tests/`（14 份） | EXISTS | 11 份 .test.js + 3 份 .py（test_capability_delta / test_learning_cycle / test_promotion_gate / test_research_registry） | 否 |
| `tools/`（8 份 .py） | EXISTS | capability_delta.py / learning_cycle.py / learning_promote.py / platform_inspection.py / research_learning.py / research_registry.py 等 | 否 |
| `docs/`（40+ 份 .md） | EXISTS | AI-INTEGRATION / LEARNING-SHADOW-ARCHITECTURE(22KB) / V041-EVIDENCE-SCHEMA(24KB) / ROADMAP(14KB) 等 | 部分（PRE_CHANGE_THREE_REPO_CHECKLIST.md、THREE_REPOSITORY_SYSTEM_MATRIX.md、ZBIP_EXECUTION_LOG_2026-09-02.md tracked） |
| `data/` | EXISTS | baseline.json / rules/ / research/ / learning/ | 否 |
| `protocols/registry.json` | EXISTS | 3,450 B | 否 |
| `.devcontainer/` / `.github/` | EXISTS | devcontainer.json + 3 个 workflow | 否 |

**DCC 小结**：Node.js 全栈控制台（前端+server+tests），以学习/影子/证据/变更计划为核心。全部代码均为 untracked。

#### 1.3.3 SICI-Core

| 路径 | 状态 | 说明 | Tracked? |
|------|------|------|----------|
| `index.html` | EXISTS | 18,271 B PWA 入口 | 否 |
| `manifest.json` / `sw.js` | EXISTS | PWA 配置 + Service Worker | 否 |
| `css/style.css` | EXISTS | 31,372 B | 否 |
| `js/`（11 份） | EXISTS | app.js(31KB) / effective-rules.js(12.7KB) / tester.js(11.5KB) / preflight.js(9.9KB) / runner.js 等 | 否 |
| `tests/`（3 份 .test.js） | EXISTS | capability-registry / effective-rules / preflight | 否 |
| `docs/`（20+ 份 .md） | EXISTS | research-learning/ 子目录含 PLATFORM_LEARNING_LIBRARY_v3(23KB) + 多个审计文档 | 部分（PLATFORM_README.md、THREE_REPOSITORY_MATRIX_POINTER.md、ZBIP_EXECUTION_LOG_2026-09-02.md tracked） |
| `upgrade_modules/`（4 份） | EXISTS | base_adapter_enhanced.py(13.8KB) / dual_pool.py(15.3KB) / unified_logger.py + 接入指南 | 否 |
| `shadow_run/`（4 份） | EXISTS | SHADOW_RUN_REPORT.md + 2 份测试 .py + xiaohongshu_bakeoff_report.md | 否 |
| `.github/workflows/platform-verify.yml` | EXISTS | 562 B | 否 |

**SICI-Core 小结**：PWA 前端 + 少量 Python 升级模块，以学习资料库和平台校验为核心。全部代码均为 untracked。

### 1.4 archive/ 历史归档

| 子目录 | 状态 | 说明 |
|--------|------|------|
| `archive/desktop-legacy/` | EXISTS（历史归档） | 含 2026-08/ 旧代码快照（app.py 20KB、database.py 35KB、intelligence.py 12KB）+ 大量业务素材（PDF/PPTX/XLSX/ZIP/MP4），static.zip + templates.zip |
| `archive/repo-audit/` | EXISTS（历史归档） | SICI-Core 旧仓库完整快照（含 .git/），用于历史审计 |

> archive/ 全部为 untracked 历史归档，**不得**作为当前源码判断依据。

### 1.5 OSAI 源码统计

| 指标 | 数值 |
|------|------|
| Git tracked 文件总数 | 34 |
| Tracked 中 .py 文件 | 0（OSAI 根目录无 tracked Python 源码） |
| components/ 下 .py 文件（全部 untracked） | ~25 份（AIDRH src+tools+tests ≈17，DCC tools+tests ≈7，SICI upgrade_modules+shadow_run ≈6） |
| components/ 下 .js 文件（全部 untracked） | ~30 份 |
| 生产数据库 | 无 |
| 生产运行时入口 | 无（DCC server.js 为研究控制台，非生产） |

---

## 二、ZBC（生产侧）= `D:\Taikoo-monitor-new`

### 2.1 顶层目录（44/44 EXISTS）

| 路径 | 状态 | 规模/说明 | Tracked? |
|------|------|-----------|----------|
| `.git/` | EXISTS | Git 仓库元数据 | — |
| `.github/` | EXISTS | CI/CD workflows | 是 |
| `.ollama/` | EXISTS | 本地 LLM 模型缓存 | 否（运行时） |
| `.pytest_cache/` | EXISTS | 测试缓存 | 否（运行时） |
| `.skills-router/` | EXISTS | Skill 路由配置 | 否 |
| `.trae-cn/` | EXISTS | IDE 配置 | 否 |
| `.venv/` | EXISTS | Python 虚拟环境 | 否（运行时） |
| `.vscode/` | EXISTS | VS Code 配置 | 否 |
| `2026-08-30/` / `2026-09-01/` | EXISTS | 日期目录（运行时输出/备份） | 否 |
| `backups/` | EXISTS | 数据库备份 | 否 |
| `chrome-cdp-profile/` | EXISTS | Chrome CDP 浏览器配置 | 否（运行时） |
| `collector_guard/` | EXISTS | 采集守护模块（8 份 .py） | 是 |
| `collector_v2/` | EXISTS | 第二代采集管线（30 文件，含 pipeline/scheduler/session/weibo/xhs 子目录） | 是 |
| `config/` | EXISTS | industry_platforms.json + proxy_nodes.example.json | 是 |
| `data/` | EXISTS | **生产数据目录**：monitor.db（53 表）+ 576 个数据/日志/配置文件 | 部分（.example tracked，其余运行时） |
| `dependencies/` | EXISTS | 空目录 | 否 |
| `deployment/` | EXISTS | 部署脚本（16 文件，含嵌套 deployment/ 乱码副本） | 是 |
| `docker/` | EXISTS | entrypoint.sh | 是 |
| `docs/` | EXISTS | 411 份文档（架构/基线/审计/研究） | 是 |
| `edge-cdp-newaccount/` | EXISTS | CDP 新账号浏览器配置 | 否（运行时） |
| `edge-cdp-profile/` / `edge-cdp-profile-new/` / `edge-cdp-proxy/` | EXISTS | Edge CDP 浏览器配置（多套） | 否（运行时） |
| `logs/` | EXISTS | 运行日志 | 否 |
| `migrations/` | EXISTS | SQL 迁移脚本（009_global_bil_staging.sql、010_notes_subject_content_type.sql） | 是 |
| `nodejs/` | EXISTS | Node.js 运行时 | 否 |
| `node_modules/` | EXISTS | npm 依赖 | 否 |
| `platform_adapters/` | EXISTS | 平台适配器（32 文件，含 scheduling/ 子目录） | 是 |
| `proxy_pool/` | EXISTS | 代理池 | 否（运行时） |
| `ref_gpt_v2/` | EXISTS | 参考代码 | 否 |
| `report_export/` | EXISTS | 报告导出模块（report_engine.py 15.9KB + app_report_api_patch.py） | 是 |
| `scripts/` | EXISTS | 运维脚本（26 文件，含 inventory/ 子目录 4 份） | 是 |
| `staging/` | EXISTS | 预发布环境 | 否 |
| `static/` | EXISTS | 前端静态资源（80 文件：html/css/js/img） | 是 |
| `templates/` | EXISTS | Flask 模板（5 份 html） | 是 |
| `tests/` | EXISTS | **295 份测试文件**（含 audit_probe、test_*、e2e） | 是 |
| `tools/` | EXISTS | 工具目录（含 cloudflared.exe 54MB + development-command-console 子模块） | 部分（DCC 子模块 modified） |
| `v4_upgrade/` | EXISTS | v4 升级模块（auth/service 等） | 是 |
| `_ref_frames/` / `_shots/` / `_u/` | EXISTS | 参考帧/截图/临时目录 | 否 |
| `__pycache__/` | EXISTS | Python 缓存 | 否 |
| `监测系统-ui架构&互动视频参考案例/` | EXISTS | UI 参考素材 | 否 |

### 2.2 根目录关键源码文件（90 份 .py，全部 EXISTS，全部 tracked）

#### 2.2.1 核心入口与主体保护层

| 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|
| `app.py` | **5,131** | 272,295 B | **Flask 主应用**，203 个路由，含 `_subject_sql_and_values()`(L599 委托)、嵌套 `subject_hit()`(L2743) |
| `subject_rules.py` | 96 | 3,637 B | **最高保护层**：SUBJECT_WORDS(L13)、SUBJECT_EXCLUDE_WORDS(L20)、`subject_hit()`(L38)、`_subject_sql_and_values()`(L76) |
| `subject_classifier.py` | 304 | 14,334 B | 传播主体分类器（SubjectClassifier 类，官方/媒体/机构/KOS 分类） |
| `risk_engine.py` | 14 | 438 B | 兼容层：`_subject_sql_and_values()`(L9 委托)、`build_daily_report()`(L13 委托) |
| `daily_report.py` | 618+ | 26,560 B | 日报引擎：`generate_daily_digest()`(L547)、`calculate_risk_index()`(L31)、`generate_executive_summary()`(L507) 等 12 个函数 |
| `report_engine.py` | 90 | 3,462 B | 报告中心：`generate_report()`(L31)、`generate_all()`(L72)、`get_bundle()`(L80) |

#### 2.2.2 数据层

| 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|
| `database.py` | 968+ | 63,014 B | **数据库层**：54 个函数（init_db/get_db/insert_note/get_notes/save_daily_report/find_duplicate_notes 等），含 `_subject_clause()`(L431) |
| `models.py` | 259 | 10,023 B | 数据模型定义 |
| `database_migrations.py` | 472 | 18,324 B | 数据库迁移（含 publish_datetime/captured_at 字段添加，L322-323） |

#### 2.2.3 采集层

| 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|
| `collector.py` | 282 | 15,510 B | 基础采集器 |
| `collector_automation.py` | 600 | 31,988 B | 采集自动化编排 |
| `collector_v2_integration.py` | 222 | 8,319 B | v2 采集集成 |
| `collector_auto_start.py` | 160 | 6,573 B | 采集自动启动 |
| `xhs_cdp_collector.py` | 825 | 45,160 B | 小红书 CDP 采集器 |
| `xhs_cookie_bridge.py` | 811 | 49,108 B | 小红书 Cookie 桥接 |
| `xhs_p0_orchestrator.py` | 271 | 14,321 B | 小红书 P0 编排器 |
| `xhs_runtime_state.py` | 213 | 10,538 B | 小红书运行时状态 |
| `weibo_login_manager.py` | 294 | 11,531 B | 微博登录管理 |
| `bilibili_login_manager.py` | 185 | 6,876 B | B站登录管理 |
| `cdp_helper.py` | 485 | 19,758 B | CDP 辅助工具 |
| `browser_discovery.py` | 28 | 1,800 B | 浏览器发现 |

#### 2.2.4 AI 模块

| 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|
| `ai_analyzer.py` | 595 | 34,418 B | AI 分析器（含 `verify_taikoo_location()`） |
| `ai_filter.py` | 308 | 13,190 B | AI 过滤器（`run_filter_batch()`） |
| `ai_gateway_v570.py` | 202 | 8,314 B | AI 网关 v5.7.0 |
| `ai_learning_engine.py` | 435 | 18,483 B | AI 学习引擎 |
| `local_ai_client.py` | 187 | 7,852 B | 本地 AI 客户端（Ollama） |
| `ark_llm.py` | 316 | 12,866 B | 火山方舟 LLM 客户端 |

#### 2.2.5 业务模块

| 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|
| `intelligence.py` | 219 | 16,889 B | 情报模块 |
| `monitoring.py` | 570 | 19,774 B | 监控模块 |
| `event_graph.py` | 563 | 25,588 B | 事件图谱 |
| `export_report.py` | 626 | 36,386 B | 报告导出 |
| `evaluation_system.py` | 389 | 19,091 B | 评估系统 |
| `topic_campaign.py` | 1,134 | 61,820 B | 话题活动（最大业务模块） |
| `topic_monitor_policy.py` | 59 | 2,921 B | 话题监控策略 |
| `topic_note_detail_backfill.py` | 234 | 10,560 B | 话题笔记详情回填 |
| `public_opinion_cases.py` | 510 | 25,174 B | 舆情案例库 |
| `case_deep_analysis.py` | 280 | 14,164 B | 案例深度分析 |
| `pr_case_engine.py` | 277 | 10,945 B | 公关案例引擎 |
| `pr_case_integration.py` | 500 | 24,964 B | 公关案例集成 |
| `brand_report_generator.py` | 281 | 12,550 B | 品牌报告生成器 |
| `brand_knowledge_base.py` | 176 | 8,115 B | 品牌知识库 |
| `brand_stats_recompute.py` | 104 | 4,940 B | 品牌统计重算 |
| `swire_group.py` | 417 | 26,955 B | 太古汇集团模块 |
| `wechat_notifier.py` | 947 | 37,713 B | 微信通知器 |
| `weekly_events.py` | 26 | 2,170 B | 周报事件 |
| `review_workflow.py` | 348 | 13,361 B | 审核工作流 |
| `context_intelligence.py` | 136 | 6,532 B | 上下文情报 |
| `adaptive_engine.py` | 325 | 14,597 B | 自适应引擎 |
| `network_adaptive.py` | 197 | 8,041 B | 网络自适应 |

#### 2.2.6 系统/运维/安全

| 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|
| `config.py` | 327 | 10,861 B | 配置管理 |
| `logger.py` | 268 | 8,649 B | 日志 |
| `cache_manager.py` | 291 | 10,324 B | 缓存管理 |
| `memory_optimizer.py` | 320 | 11,857 B | 内存优化 |
| `function_registry.py` | 111 | 7,204 B | 函数注册表 |
| `safety_boundary.py` | 365 | 19,256 B | 安全边界 |
| `data_boundary.py` | 198 | 11,058 B | 数据边界 |
| `data_feedback_loop.py` | 324 | 16,244 B | 数据反馈闭环 |
| `security_scanner.py` | 312 | 14,506 B | 安全扫描器 |
| `runtime_preflight.py` | 290 | 15,263 B | 运行时预检 |
| `auto_recovery.py` | 390 | 17,156 B | 自动恢复 |
| `auth_recovery_center.py` | 292 | 13,165 B | 认证恢复中心 |
| `auth_recovery_api.py` | — | 4,267 B | 认证恢复 API |
| `stability_monitor.py` | 435 | 18,471 B | 稳定性监控 |
| `system_guardian.py` | 190 | 7,292 B | 系统守护 |
| `system_health_api.py` | 500 | 20,409 B | 系统健康 API |
| `system_watchdog.py` | 271 | 11,818 B | 系统看门狗 |
| `system_features_api.py` | 173 | 7,153 B | 系统特性 API |
| `architecture_api.py` | 351 | 13,906 B | 架构 API |
| `app_evidence.py` | 322 | 15,430 B | 应用证据（含 captured_at 字段，L63） |
| `ci_cd.py` | 435 | 13,647 B | CI/CD |
| `tunnel_guardian.py` | 214 | 7,954 B | 隧道守护 |
| `update_reference.py` | 210 | 10,147 B | 更新参考 |
| `settings_module.py` | 276 | 11,329 B | 设置模块 |
| `monitor_pipeline.py` | 25 | 1,357 B | 监控管线 |
| `populate_empty_tables.py` | 255 | 10,923 B | 填充空表 |
| `reprocess.py` | 145 | 9,922 B | 重处理 |
| `web_monitor.py` | 71 | 5,143 B | Web 监控 |
| `web_monitor_v570.py` | 175 | 6,045 B | Web 监控 v570 |
| `web_topic_discovery.py` | 171 | 5,412 B | Web 话题发现 |
| `verify_system.py` | 66 | 2,491 B | 系统验证 |
| `verify_system_e2e.py` | 290 | 13,216 B | E2E 验证 |
| `evaluate_system_timing.py` | 230 | 9,838 B | 系统时序评估 |
| `read_docx.py` | 31 | 1,386 B | 读取 docx |
| `_reanalyze.py` | 40 | 2,073 B | 重新分析 |

#### 2.2.7 检查/诊断脚本（根目录）

| 文件 | 说明 |
|------|------|
| `check_collection.py` / `check_collection_detail.py` / `check_db_dates.py` / `check_empty_tables.py` / `check_logs.py` / `check_system.py` / `check_warnings.py` / `quick_check.py` | 各类检查诊断脚本（17–43 行） |

### 2.3 关键子目录详单

#### 2.3.1 collector_v2/（30 文件，EXISTS）

| 路径 | 说明 |
|------|------|
| `base.py` | 采集基类（3,516 B） |
| `browser_session.py` | 浏览器会话（6,284 B） |
| `official_info_scraper.py` | 官方信息抓取（25,660 B） |
| `pipeline/deduplicate.py` | 去重（5,711 B） |
| `pipeline/normalize.py` | 规范化（7,523 B） |
| `pipeline/persist.py` | 持久化（7,147 B） |
| `pipeline/spam_filter.py` | 垃圾过滤（4,377 B） |
| `pipeline/subject_filter.py` | 主体过滤（5,667 B） |
| `scheduler/collector_job.py` | 采集调度作业（9,680 B） |
| `session/browser_session.py` | 会话浏览器（3,464 B，含 .v5.3.2-pre-opt 备份） |
| `weibo/collector.py` | 微博采集器（10,272 B） |
| `xhs/client.py` | 小红书客户端（7,728 B，含 .v5.3.2-pre-opt 备份） |
| `xhs/collector.py` | 小红书采集器（9,202 B，含 .v5.3.2-pre-opt 备份） |
| `xhs/live_engine.py` | 小红书直播引擎（3,750 B） |
| `xhs/models.py` | 小红书模型（760 B） |
| `xhs/parser.py` | 小红书解析器（7,872 B，含 .v5.3.2-pre-opt 备份） |
| `run_live_engine.py` / `run_xhs_live.py` | 运行入口（含嵌套 `subject_hit` stub，L16/L20） |

#### 2.3.2 collector_guard/（8 文件，EXISTS）

`analyzer.py` / `checkpoint.py` / `guard.py` / `metrics.py` / `rate_limiter.py` / `risk_engine.py` / `state.py` / `__init__.py`

#### 2.3.3 platform_adapters/（32 文件，EXISTS）

| 路径 | 说明 |
|------|------|
| `base.py` / `config.py` / `registry.py` / `health_center.py` | 适配器基础框架 |
| `xhs.py` / `xhs_app_topic.py` / `douyin.py` / `rednote_policy.py` | 平台适配器 |
| `scheduling/decision.py`(11,757 B) / `gate.py` / `planner.py` / `policy.py` / `state_map.py` / `store.py` | 调度决策子系统 |

#### 2.3.4 report_export/（4 文件，EXISTS）

`report_engine.py`(15,884 B，独立报告导出引擎) / `app_report_api_patch.py` / `requirements_report_export.txt`

#### 2.3.5 tests/（295 文件，EXISTS）

涵盖：audit_probe_1~6、conftest、test_adapter_resilience、test_ai、test_api、test_api_smoke、test_auth_api、test_auto_recovery、test_bilibili、test_brand_library、test_browser_e2e、test_collection_full、test_collect_pipeline、test_database、test_data_feedback、test_e2e(18KB)、test_event_graph_relations、test_llm_gateway、test_llm_online、test_subject（推测）、等 295 份。

#### 2.3.6 scripts/（26 文件，EXISTS）

`backfill_empty_body.py` / `backup_db.py` / `check_system.py` / `collect_now.py` / `daily_git_sync.py` / `export_report.py` / `github_upgrade_check.py` / `init_database_data.py`(16KB) / `init_db.py`(12.6KB) / `license_audit.py` / `run_core_regression.py` / `stability_fix.py` / `staging_setup.py` / `sync_xhs_cookie_from_cdp.py` / `inventory/`(asset_scan.py / build_asset_registry.py / feature_crosscheck.py / feature_final_verify.py) + PowerShell 脚本

#### 2.3.7 其他子目录

| 目录 | 状态 | 说明 |
|------|------|------|
| `migrations/` | EXISTS | 2 份 SQL（009、010） |
| `deployment/` | EXISTS | 16 文件（含嵌套 deployment/ 乱码副本，疑似编码问题） |
| `config/` | EXISTS | industry_platforms.json(6KB) + proxy_nodes.example.json |
| `static/` | EXISTS | 80 文件：index.html(81KB)、css/ 25 份（含多套主题 zb-gpt-theme/zb-theme/zbip-*）、js/ app.js(115KB) + 多份、img/ |
| `templates/` | EXISTS | 5 份 Flask 模板（base/index/events/notes/report.html） |
| `docker/` | EXISTS | entrypoint.sh + 根目录 Dockerfile / docker-compose.yml / docker-compose.staging.yml |
| `v4_upgrade/` | EXISTS | v4 认证/权限/工作区模块（被 app.py L615 引用 `v4_upgrade.auth.service`） |

### 2.4 生产数据库

| 项目 | 状态 | 值 |
|------|------|-----|
| `data/monitor.db` | EXISTS | SQLite，**53 张表**（非 agent-hint 中所述 38 张） |
| 核心表行数 | — | notes=957, events=427, event_mentions=562, note_review_history=8,327, daily_reports=33, daily_digest=7, collection_logs=499, ai_filter_log=827, topic_campaign_notes=120, web_topics=96, web_mentions=79, brand_industry_monitor=198, brand_knowledge=103 |
| 最高保护层字段 | EXISTS | `notes.publish_datetime`（database.py L185 migration）、`notes.captured_at`（database.py L186 migration），app.py L775/L782 写入 |
| 空表 | EXISTS | app_evidence_records=0, notification_config=0, review_logs=0, review_samples=0, review_tickets=0, swire_notes=0 |

### 2.5 配置与文档

| 项目 | 状态 | 说明 |
|------|------|------|
| `.env` | EXISTS（敏感，已打码） | 7,079 B，含密钥/Token，**不在本文档中暴露内容** |
| `.env.example` | EXISTS | 3,799 B 模板 |
| `requirements.txt` | EXISTS | 873 B Python 依赖 |
| `package.json` | EXISTS | 274 B Node 依赖 |
| `pytest.ini` | EXISTS | 711 B 测试配置 |
| `Dockerfile` / `docker-compose.yml` | EXISTS | 容器化配置 |
| `AGENTS.md` | EXISTS | 13,546 B 项目 AI 指令 |
| `ARCHITECTURE.md` | EXISTS | 17,212 B 架构文档 |
| `CURRENT_BASELINE.md` | EXISTS | 7,324 B 当前基线 |
| `README.md` | EXISTS | 41,588 B |
| `CHANGELOG.md` | EXISTS | 48,907 B |
| `docs/` | EXISTS | 411 份文档（含 PRODUCTION_BASELINE、CAPABILITY_BASELINE、FEATURE-GAP-REGISTER 等） |

### 2.6 ZBC Git 状态

| 指标 | 值 |
|------|-----|
| Tracked 文件总数 | 1,378 |
| Untracked 文件 | 0（全部已 tracked 或被 .gitignore 排除） |
| Modified 文件 | 1（`tools/development-command-console` 子模块） |
| 根目录 .py 源码 | ~90 份（全部 tracked） |
| 备份文件 | `app.py.bak_p0_20260902_094442`(275KB)、`app_backup_v589.py`(257KB) — 历史备份，非当前运行代码 |

---

## 三、Tracked vs Untracked vs 历史归档 汇总

### OSAI

| 类别 | Tracked | Untracked | 历史归档 |
|------|---------|-----------|----------|
| 根目录 01–22 对账文档 | 22 | 0 | 是（历史参考） |
| 根目录 README/CHANGELOG/.gitignore | 3 | 0 | 否 |
| components/ 下文档（部分） | 6 | ~100+ | 否 |
| components/ 下源码（.py/.js/.html/.css） | 0 | ~55 份 | 否 |
| archive/ | 0 | 全部 | 是（desktop-legacy + repo-audit） |
| config/ / docs-wps/ / reconciliation/ | 0 | 全部 | 否 |

### ZBC

| 类别 | Tracked | Untracked | 历史归档/运行时 |
|------|---------|-----------|-----------------|
| 根目录 .py 源码（~90 份） | 全部 | 0 | 否 |
| 根目录 .bak / backup 文件 | 0 | 0 | 是（app.py.bak、app_backup_v589.py） |
| 子目录源码（collector_v2/guard/platform_adapters/report_export/tests/scripts/migrations/deployment） | 全部 | 0 | 否 |
| static/ / templates/ / config/ / docs/ | 全部 | 0 | 否 |
| data/（monitor.db + 运行时数据） | 部分（.example） | 大部分 | 运行时 |
| .venv/ / node_modules/ / __pycache__/ / logs/ / .pytest_cache/ | 0 | 0（gitignore） | 运行时 |
| edge-cdp-*/ / chrome-cdp-profile/ / proxy_pool/ / backups/ | 0 | 0（gitignore） | 运行时 |
| tools/development-command-console（子模块） | 是（submodule） | modified | — |

---

## 四、关键发现

1. **OSAI 几乎无生产代码**：全部 components/ 源码（~55 份 .py/.js）均为 untracked，以 Contract/Research/学习控制台为主，无数据库、无生产运行时入口。
2. **ZBC 是完整生产系统**：1,378 tracked 文件，90 份根目录 .py 源码，53 张数据库表，203 个 Flask 路由，295 份测试。
3. **最高保护层已抽取到独立模块**：`subject_rules.py` 是 SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit()/_subject_sql_and_values() 的唯一权威来源；app.py 和 risk_engine.py 均为委托调用。
4. **`aggregate_events()` 已不存在**：全仓无 `def aggregate_events`，仅在文档/测试中被引用（docs/7版方案审计报告、tests/audit_probe_4.py、tests/_archive_blueprint.py）。
5. **无跨边界代码导入**：OSAI 侧无 import taikoo/monitor/app/database；ZBC 侧无 import osai/zachary_os。双端通过 Contract/Plan 文档和数据文件交互，无直接代码依赖。
6. **OSAI 根目录 01–22 文档为历史迁移产物**：按 SPEC 仅作参考，当前判断以本地源码为准。
7. **ZBC data/monitor.db 实际 53 张表**（agent-hint 所述 38 张已过时）。
