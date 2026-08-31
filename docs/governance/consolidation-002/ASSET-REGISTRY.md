# ASSET-REGISTRY · 资产身份登记总账（Consolidation-002 / ②）

> 生成器：`scripts/inventory/build_asset_registry.py`（只读，可重复运行）。
> 数据源：① `raw/module_graph.json`（依赖/可达性，不重算）+ 路由只读提取 + `monitor.db` 只读 + 前端/依赖清单。
> **本总账只登记与打状态标签，不删除、不移动、不改写任何业务代码**；状态为机器初判，④Owner 阶段人工钉死。

## 0. 口径与数字（与①对齐）

- Python 资产：**400**（非测试 220 / 测试 180）；app 静态可达 **84**。
- 状态初判（非测试）：ACTIVE=84，DEPRECATED?=53，RESERVED=34，NOT_VERIFIED=26，DEVELOPING=23
- 完全孤立 DEPRECATED? 候选 **53**；独立入口 RESERVED **34**；新一代在建 DEVELOPING **23**；旁路 NOT_VERIFIED **26**。
- 不可达非测试 136 对账：孤立候选 53 + 独立入口 34 + 新一代在建 23 + 旁路引用 26 = 136（与①一致；①口径“孤立61”=本表 53 + collector_v2 内 8 个纯孤立，已统一并入 DEVELOPING 视角）。
- 路由：app.py 内 **189**（对齐既有约189口径），全仓合计 **363**（含 v4 蓝图/子系统 register 路由）；数据库表 **51**；CSS 23 / JS 22 / 模板 10；requirements 依赖 15。
- 十状态：ACTIVE / DEVELOPING / PLANNED / RESERVED / EXPERIMENTAL / LEGACY / DEPRECATED / DUPLICATE / MIGRATION_REQUIRED / NOT_VERIFIED。

> **命名层级（已决议，以 PRODUCT_NAMING_BASELINE 为准）**：最顶层统一平台层 = **Z-Brand Intelligence Platform**；其下 **ZBP（品牌业务生产平台，本仓库）/ DCC / SICI 三者并列**；
> ZBP 不是最顶层母平台，CTH-POMS 与 ZBMP 隶属于 ZBP。本总账登记范围为 ZBP（仓库 Z-Brand-Core）内资产。

## A. Core 运行时资产（app 静态可达 = ACTIVE）

| ASSET-ID | 模块 | 行 | 层 | 业务域 | 被依赖 | 依赖 | 红线 | 状态 |
|---|---|--:|---|---|--:|--:|:--:|:--:|
| ASSET-PY-0001 | `adaptive_engine.py` | 382 | Core根模块 | AI/大模型 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0002 | `ai_analyzer.py` | 659 | Core根模块 | AI/大模型 | 13 | 1 |  | ACTIVE |
| ASSET-PY-0003 | `ai_filter.py` | 363 | Core根模块 | AI/大模型 | 2 | 3 |  | ACTIVE |
| ASSET-PY-0004 | `ai_gateway_v570.py` | 208 | Core根模块 | AI/大模型 | 2 | 1 |  | ACTIVE |
| ASSET-PY-0005 | `ai_learning_engine.py` | 449 | Core根模块 | AI/大模型 | 1 | 1 |  | ACTIVE |
| ASSET-PY-0006 | `app.py` | 5074 | Core根模块 | Web核心/装配 | 3 | 57 | 🔴 | ACTIVE |
| ASSET-PY-0007 | `app_evidence.py` | 381 | Core根模块 | 证据/评审流 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0008 | `architecture_api.py` | 409 | Core根模块 | Web核心/装配 | 1 | 4 |  | ACTIVE |
| ASSET-PY-0009 | `ark_llm.py` | 362 | Core根模块 | AI/大模型 | 4 | 0 |  | ACTIVE |
| ASSET-PY-0010 | `auth_recovery_api.py` | 129 | Core根模块 | 恢复/守护/稳定 | 1 | 2 |  | ACTIVE |
| ASSET-PY-0011 | `auth_recovery_center.py` | 332 | Core根模块 | 恢复/守护/稳定 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0012 | `auto_recovery.py` | 473 | Core根模块 | 恢复/守护/稳定 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0013 | `bilibili_login_manager.py` | 193 | Core根模块 | Cookie/登录/Auth | 2 | 0 |  | ACTIVE |
| ASSET-PY-0014 | `brand_knowledge_base.py` | 206 | Core根模块 | 品牌/案例/知识 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0015 | `brand_report_generator.py` | 310 | Core根模块 | 报告/导出 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0016 | `brand_stats_recompute.py` | 124 | Core根模块 | 数据库/迁移 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0017 | `browser_discovery.py` | 32 | Core根模块 | 平台适配 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0018 | `cache_manager.py` | 305 | Core根模块 | 缓存/内存 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0019 | `case_deep_analysis.py` | 307 | Core根模块 | 品牌/案例/知识 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0020 | `cdp_helper.py` | 519 | Core根模块 | 平台适配 | 8 | 0 |  | ACTIVE |
| ASSET-PY-0021 | `collector.py` | 320 | Core根模块 | 采集器 | 9 | 2 |  | ACTIVE |
| ASSET-PY-0022 | `collector_auto_start.py` | 184 | Core根模块 | 采集器 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0023 | `collector_automation.py` | 565 | Core根模块 | 采集器 | 3 | 4 |  | ACTIVE |
| ASSET-PY-0024 | `collector_guard/analyzer.py` | 111 | 子系统包 | 采集器 | 1 | 1 |  | ACTIVE |
| ASSET-PY-0025 | `collector_guard/checkpoint.py` | 84 | 子系统包 | 采集器 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0026 | `collector_guard/guard.py` | 135 | 子系统包 | 采集器 | 3 | 5 |  | ACTIVE |
| ASSET-PY-0027 | `collector_guard/metrics.py` | 61 | 子系统包 | 采集器 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0028 | `collector_guard/rate_limiter.py` | 111 | 子系统包 | 采集器 | 1 | 1 |  | ACTIVE |
| ASSET-PY-0029 | `collector_guard/state.py` | 45 | 子系统包 | 采集器 | 8 | 0 |  | ACTIVE |
| ASSET-PY-0030 | `collector_v2/official_info_scraper.py` | 578 | 子系统包 | 采集器 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0031 | `config.py` | 351 | Core根模块 | 配置/设置 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0032 | `daily_report.py` | 657 | Core根模块 | 报告/导出 | 4 | 4 | 🔴 | ACTIVE |
| ASSET-PY-0033 | `data_feedback_loop.py` | 380 | Core根模块 | 其他/待归类 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0034 | `database.py` | 960 | Core根模块 | 数据库/迁移 | 27 | 1 | 🔴 | ACTIVE |
| ASSET-PY-0035 | `evaluation_system.py` | 460 | Core根模块 | 评测/验证 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0036 | `event_graph.py` | 520 | Core根模块 | 事件 | 1 | 0 | 🔴 | ACTIVE |
| ASSET-PY-0037 | `export_report.py` | 732 | Core根模块 | 报告/导出 | 2 | 1 |  | ACTIVE |
| ASSET-PY-0038 | `function_registry.py` | 122 | Core根模块 | 其他/待归类 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0039 | `intelligence.py` | 200 | Core根模块 | AI/大模型 | 11 | 0 |  | ACTIVE |
| ASSET-PY-0040 | `local_ai_client.py` | 232 | Core根模块 | AI/大模型 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0041 | `memory_optimizer.py` | 333 | Core根模块 | 缓存/内存 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0042 | `models.py` | 319 | Core根模块 | 数据库/迁移 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0043 | `network_adaptive.py` | 212 | Core根模块 | 网络/代理/隧道 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0044 | `platform_adapters/__init__.py` | 25 | 子系统包 | 平台适配 | 9 | 0 |  | ACTIVE |
| ASSET-PY-0045 | `platform_adapters/config.py` | 52 | 子系统包 | 配置/设置 | 3 | 0 |  | ACTIVE |
| ASSET-PY-0046 | `platform_adapters/health_center.py` | 204 | 子系统包 | 平台适配 | 2 | 5 |  | ACTIVE |
| ASSET-PY-0047 | `platform_adapters/scheduling/state_map.py` | 170 | 子系统包 | 平台适配 | 5 | 0 |  | ACTIVE |
| ASSET-PY-0048 | `pr_case_engine.py` | 286 | Core根模块 | 品牌/案例/知识 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0049 | `pr_case_integration.py` | 579 | Core根模块 | 品牌/案例/知识 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0050 | `proxy_pool/__init__.py` | 17 | 子系统包 | 平台适配 | 3 | 1 |  | ACTIVE |
| ASSET-PY-0051 | `proxy_pool/config.py` | 36 | 子系统包 | 配置/设置 | 6 | 0 |  | ACTIVE |
| ASSET-PY-0052 | `proxy_pool/health.py` | 24 | 子系统包 | 平台适配 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0053 | `proxy_pool/loader.py` | 42 | 子系统包 | 平台适配 | 3 | 3 |  | ACTIVE |
| ASSET-PY-0054 | `proxy_pool/manager.py` | 159 | 子系统包 | 平台适配 | 4 | 3 |  | ACTIVE |
| ASSET-PY-0055 | `proxy_pool/models.py` | 50 | 子系统包 | 数据库/迁移 | 4 | 0 |  | ACTIVE |
| ASSET-PY-0056 | `public_opinion_cases.py` | 522 | Core根模块 | 品牌/案例/知识 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0057 | `report_engine.py` | 91 | Core根模块 | 报告/导出 | 2 | 4 | 🔴 | ACTIVE |
| ASSET-PY-0058 | `report_export/report_engine.py` | 370 | 子系统包 | 报告/导出 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0059 | `report_filter.py` | 209 | Core根模块 | 报告/导出 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0060 | `reprocess.py` | 158 | Core根模块 | 数据库/迁移 | 2 | 4 |  | ACTIVE |
| ASSET-PY-0061 | `safety_boundary.py` | 435 | Core根模块 | 恢复/守护/稳定 | 2 | 0 |  | ACTIVE |
| ASSET-PY-0062 | `security_scanner.py` | 367 | Core根模块 | 其他/待归类 | 3 | 0 |  | ACTIVE |
| ASSET-PY-0063 | `settings_module.py` | 321 | Core根模块 | 配置/设置 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0064 | `stability_monitor.py` | 446 | Core根模块 | 恢复/守护/稳定 | 2 | 1 |  | ACTIVE |
| ASSET-PY-0065 | `subject_classifier.py` | 371 | Core根模块 | 主体/分类 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0066 | `subject_rules.py` | 98 | Core根模块 | 主体/分类 | 15 | 0 | 🔴 | ACTIVE |
| ASSET-PY-0067 | `swire_group.py` | 448 | Core根模块 | 品牌/案例/知识 | 2 | 1 |  | ACTIVE |
| ASSET-PY-0068 | `system_features_api.py` | 220 | Core根模块 | 其他/待归类 | 1 | 4 |  | ACTIVE |
| ASSET-PY-0069 | `system_health_api.py` | 541 | Core根模块 | 评测/验证 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0070 | `topic_campaign.py` | 1224 | Core根模块 | 采集器 | 3 | 5 |  | ACTIVE |
| ASSET-PY-0071 | `v4_upgrade/__init__.py` | 22 | ZBMP增强层(共用Core) | v4增强层 | 15 | 1 |  | ACTIVE |
| ASSET-PY-0072 | `v4_upgrade/adapters/auth_recovery.py` | 438 | ZBMP增强层(共用Core) | 平台适配 | 2 | 2 |  | ACTIVE |
| ASSET-PY-0073 | `v4_upgrade/adapters/human_browser.py` | 331 | ZBMP增强层(共用Core) | 平台适配 | 4 | 1 |  | ACTIVE |
| ASSET-PY-0074 | `v4_upgrade/adapters/risk_controller.py` | 246 | ZBMP增强层(共用Core) | 风险 | 4 | 1 |  | ACTIVE |
| ASSET-PY-0075 | `v4_upgrade/auth/models.py` | 122 | ZBMP增强层(共用Core) | 数据库/迁移 | 5 | 2 |  | ACTIVE |
| ASSET-PY-0076 | `v4_upgrade/auth/security.py` | 140 | ZBMP增强层(共用Core) | Cookie/登录/Auth | 4 | 2 |  | ACTIVE |
| ASSET-PY-0077 | `v4_upgrade/auth/service.py` | 330 | ZBMP增强层(共用Core) | Cookie/登录/Auth | 1 | 3 |  | ACTIVE |
| ASSET-PY-0078 | `v4_upgrade/config.py` | 80 | ZBMP增强层(共用Core) | 配置/设置 | 12 | 0 |  | ACTIVE |
| ASSET-PY-0079 | `web_monitor.py` | 72 | Core根模块 | 采集器 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0080 | `web_monitor_v570.py` | 183 | Core根模块 | 采集器 | 1 | 1 |  | ACTIVE |
| ASSET-PY-0081 | `weekly_events.py` | 31 | Core根模块 | 事件 | 1 | 0 |  | ACTIVE |
| ASSET-PY-0082 | `weibo_login_manager.py` | 303 | Core根模块 | Cookie/登录/Auth | 1 | 0 |  | ACTIVE |
| ASSET-PY-0083 | `xhs_cookie_bridge.py` | 564 | Core根模块 | 采集器 | 7 | 6 |  | ACTIVE |
| ASSET-PY-0084 | `xhs_runtime_state.py` | 255 | Core根模块 | 采集器 | 1 | 0 |  | ACTIVE |

## B. 在建 / 旁路子系统（DEVELOPING / NOT_VERIFIED，主链暂不可达）

### B.1 collector_v2 新一代采集（DEVELOPING，未接管生产，生产仍走 collector.py）

| 模块 | 行 | 业务域 | 被依赖 | 状态 |
|---|--:|---|--:|:--:|
| `collector_v2/__init__.py` | 11 | 采集器 | 0 | DEVELOPING |
| `collector_v2/base.py` | 112 | 采集器 | 3 | DEVELOPING |
| `collector_v2/browser_session.py` | 165 | 采集器 | 0 | DEVELOPING |
| `collector_v2/pipeline/__init__.py` | 15 | 采集器 | 0 | DEVELOPING |
| `collector_v2/pipeline/deduplicate.py` | 173 | 采集器 | 3 | DEVELOPING |
| `collector_v2/pipeline/normalize.py` | 211 | 采集器 | 3 | DEVELOPING |
| `collector_v2/pipeline/persist.py` | 202 | 数据库/迁移 | 1 | DEVELOPING |
| `collector_v2/pipeline/spam_filter.py` | 129 | 采集器 | 1 | DEVELOPING |
| `collector_v2/pipeline/subject_filter.py` | 148 | 主体/分类 | 2 | DEVELOPING |
| `collector_v2/run_live_engine.py` | 28 | 采集器 | 0 | DEVELOPING |
| `collector_v2/run_xhs_live.py` | 14 | 采集器 | 0 | DEVELOPING |
| `collector_v2/scheduler/__init__.py` | 5 | 采集器 | 0 | DEVELOPING |
| `collector_v2/scheduler/collector_job.py` | 246 | 采集器 | 1 | DEVELOPING |
| `collector_v2/session/__init__.py` | 4 | 采集器 | 0 | DEVELOPING |
| `collector_v2/session/browser_session.py` | 101 | 采集器 | 0 | DEVELOPING |
| `collector_v2/weibo/__init__.py` | 5 | 采集器 | 0 | DEVELOPING |
| `collector_v2/weibo/collector.py` | 262 | 采集器 | 0 | DEVELOPING |
| `collector_v2/xhs/__init__.py` | 6 | 采集器 | 0 | DEVELOPING |
| `collector_v2/xhs/client.py` | 219 | 采集器 | 1 | DEVELOPING |
| `collector_v2/xhs/collector.py` | 234 | 采集器 | 2 | DEVELOPING |
| `collector_v2/xhs/live_engine.py` | 75 | 采集器 | 2 | DEVELOPING |
| `collector_v2/xhs/models.py` | 28 | 数据库/迁移 | 2 | DEVELOPING |
| `collector_v2/xhs/parser.py` | 206 | 采集器 | 0 | DEVELOPING |

### B.2 被旁路引用但主链不可达（NOT_VERIFIED，需在③架构映射核实去留）

| 模块 | 行 | 业务域 | 被谁引用(截断) | 状态 |
|---|--:|---|---|:--:|
| `platform_adapters/base.py` | 103 | 平台适配 | platform_adapters/douyin.py, platform_adapters/registry.py, platform_adapters/xhs.py | NOT_VERIFIED |
| `platform_adapters/registry.py` | 35 | 平台适配 | platform_adapters/douyin.py, platform_adapters/xhs.py, platform_adapters/xhs_app_topic.py | NOT_VERIFIED |
| `platform_adapters/scheduling/decision.py` | 247 | 平台适配 | platform_adapters/scheduling/planner.py | NOT_VERIFIED |
| `platform_adapters/scheduling/policy.py` | 92 | 平台适配 | platform_adapters/scheduling/decision.py, platform_adapters/scheduling/planner.py | NOT_VERIFIED |
| `platform_adapters/scheduling/store.py` | 110 | 平台适配 | platform_adapters/scheduling/planner.py | NOT_VERIFIED |
| `v4_upgrade/adapters/baidu_search.py` | 52 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/base.py` | 130 | 平台适配 | v4_upgrade/adapters/baidu_search.py, v4_upgrade/adapters/bing_search.py, v4_upgrade/adapters/dianping.py | NOT_VERIFIED |
| `v4_upgrade/adapters/bing_search.py` | 41 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/collector_service.py` | 197 | 采集器 | tests/test_collect_pipeline.py, v4_upgrade/blueprint.py | NOT_VERIFIED |
| `v4_upgrade/adapters/cookie_vault.py` | 265 | 平台适配 | v4_upgrade/adapters/douyin.py, v4_upgrade/adapters/instagram.py | NOT_VERIFIED |
| `v4_upgrade/adapters/dianping.py` | 45 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/doubao_search.py` | 87 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/douyin.py` | 291 | 平台适配 | tests/_adapter_live.py, tests/test_douyin_adapter.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/google.py` | 225 | 平台适配 | v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/instagram.py` | 234 | 平台适配 | v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/persist.py` | 218 | 数据库/迁移 | tests/test_collect_pipeline.py, v4_upgrade/adapters/collector_service.py | NOT_VERIFIED |
| `v4_upgrade/adapters/registry.py` | 113 | 平台适配 | tests/_audit_misc.py, tests/test_collect_pipeline.py, tests/test_instagram_adapter.py | NOT_VERIFIED |
| `v4_upgrade/adapters/smzdm.py` | 35 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/sogou_search.py` | 346 | 平台适配 | v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/sogou_wechat.py` | 43 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/adapters/zhihu.py` | 51 | 平台适配 | tests/_adapter_live.py, v4_upgrade/adapters/registry.py | NOT_VERIFIED |
| `v4_upgrade/ai_hub/service.py` | 245 | AI/大模型 | v4_upgrade/ai_hub/routes.py | NOT_VERIFIED |
| `v4_upgrade/ai_hub/shadow.py` | 114 | AI/大模型 | v4_upgrade/ai_hub/routes.py | NOT_VERIFIED |
| `v4_upgrade/importer/analyzer.py` | 219 | v4增强层 | tests/v4_smoke.py, v4_upgrade/importer/service.py | NOT_VERIFIED |
| `v4_upgrade/importer/parser.py` | 184 | v4增强层 | v4_upgrade/importer/analyzer.py, v4_upgrade/importer/service.py | NOT_VERIFIED |
| `v4_upgrade/version_center/git_manager.py` | 415 | 版本/部署 | scripts/daily_git_sync.py, tests/_test_version_center.py, v4_upgrade/version_center/routes.py | NOT_VERIFIED |

## C. 完全孤立资产（53，DEPRECATED? 候选 —— 未删，须引用/替代/回归全过才准退）

| 模块 | 行 | 业务域 | 状态 |
|---|--:|---|:--:|
| `_reanalyze.py` | 43 | 其他/待归类 | DEPRECATED? |
| `check_collection.py` | 44 | 采集器 | DEPRECATED? |
| `check_collection_detail.py` | 53 | 采集器 | DEPRECATED? |
| `check_db_dates.py` | 38 | 评测/验证 | DEPRECATED? |
| `check_empty_tables.py` | 20 | 评测/验证 | DEPRECATED? |
| `check_logs.py` | 43 | 评测/验证 | DEPRECATED? |
| `check_system.py` | 41 | 评测/验证 | DEPRECATED? |
| `check_warnings.py` | 39 | 评测/验证 | DEPRECATED? |
| `collector_guard/__init__.py` | 32 | 采集器 | DEPRECATED? |
| `collector_guard/risk_engine.py` | 125 | 风险 | DEPRECATED? |
| `collector_v2_integration.py` | 240 | 采集器 | DEPRECATED? |
| `deployment/backup.py` | 13 | 版本/部署 | DEPRECATED? |
| `deployment/health_check.py` | 22 | 评测/验证 | DEPRECATED? |
| `docs/reference/apple-ui-reference/raw/build_catalog.py` | 42 | 其他/待归类 | DEPRECATED? |
| `docs/reference/apple-ui-reference/raw/build_db.py` | 267 | 其他/待归类 | DEPRECATED? |
| `evaluate_system_timing.py` | 259 | 评测/验证 | DEPRECATED? |
| `import_cookies.py` | 149 | Cookie/登录/Auth | DEPRECATED? |
| `import_xhs_cookies.py` | 116 | 采集器 | DEPRECATED? |
| `platform_adapters/douyin.py` | 57 | 平台适配 | DEPRECATED? |
| `platform_adapters/scheduling/__init__.py` | 37 | 平台适配 | DEPRECATED? |
| `platform_adapters/scheduling/planner.py` | 123 | 平台适配 | DEPRECATED? |
| `platform_adapters/xhs.py` | 103 | 采集器 | DEPRECATED? |
| `platform_adapters/xhs_app_topic.py` | 248 | 采集器 | DEPRECATED? |
| `proxy_pool/adapters.py` | 29 | 平台适配 | DEPRECATED? |
| `quick_check.py` | 50 | 其他/待归类 | DEPRECATED? |
| `read_docx.py` | 34 | 其他/待归类 | DEPRECATED? |
| `report_export/app_report_api_patch.py` | 17 | 报告/导出 | DEPRECATED? |
| `review_workflow.py` | 355 | 证据/评审流 | DEPRECATED? |
| `risk_engine.py` | 15 | 风险 | DEPRECATED? |
| `scripts/inventory/asset_scan.py` | 225 | 运维/脚本工具 | DEPRECATED? |
| `start_tunnel.py` | 86 | 恢复/守护/稳定 | DEPRECATED? |
| `system_guardian.py` | 227 | 恢复/守护/稳定 | DEPRECATED? |
| `topic_monitor_policy.py` | 76 | 其他/待归类 | DEPRECATED? |
| `v4_upgrade/adapters/__init__.py` | 15 | 平台适配 | DEPRECATED? |
| `v4_upgrade/ai_hub/__init__.py` | 14 | AI/大模型 | DEPRECATED? |
| `v4_upgrade/ai_hub/routes.py` | 73 | AI/大模型 | DEPRECATED? |
| `v4_upgrade/auth/__init__.py` | 19 | Cookie/登录/Auth | DEPRECATED? |
| `v4_upgrade/auth/audit.py` | 91 | Cookie/登录/Auth | DEPRECATED? |
| `v4_upgrade/blueprint.py` | 336 | v4增强层 | DEPRECATED? |
| `v4_upgrade/collect/__init__.py` | 5 | 采集器 | DEPRECATED? |
| `v4_upgrade/collect/routes.py` | 29 | 采集器 | DEPRECATED? |
| `v4_upgrade/console/__init__.py` | 5 | v4增强层 | DEPRECATED? |
| `v4_upgrade/console/routes.py` | 29 | v4增强层 | DEPRECATED? |
| `v4_upgrade/data_cleanup/__init__.py` | 5 | v4增强层 | DEPRECATED? |
| `v4_upgrade/importer/__init__.py` | 7 | v4增强层 | DEPRECATED? |
| `v4_upgrade/importer/service.py` | 164 | v4增强层 | DEPRECATED? |
| `v4_upgrade/settings/__init__.py` | 5 | 配置/设置 | DEPRECATED? |
| `v4_upgrade/settings/routes.py` | 229 | 配置/设置 | DEPRECATED? |
| `v4_upgrade/version_center/__init__.py` | 13 | 版本/部署 | DEPRECATED? |
| `v4_upgrade/version_center/routes.py` | 100 | 版本/部署 | DEPRECATED? |
| `v4_upgrade/version_center/watcher.py` | 43 | 版本/部署 | DEPRECATED? |
| `verify_system.py` | 73 | 评测/验证 | DEPRECATED? |
| `verify_system_e2e.py` | 332 | 评测/验证 | DEPRECATED? |

## D. 独立入口 / 运维脚本（34，RESERVED，含 __main__，多为手动工具）

| 模块 | 行 | 业务域 |
|---|--:|---|
| `app_refactor_blueprint.py` | 289 | 其他/待归类 |
| `ci_cd.py` | 461 | 评测/验证 |
| `database_migrations.py` | 518 | 数据库/迁移 |
| `deployment/deployment/µò░µì«σ║ôσñçΣ╗╜.py` | 153 | 版本/部署 |
| `deployment/deployment/σüÑσ║╖µúÇµƒÑ.py` | 180 | 版本/部署 |
| `deployment/健康检查.py` | 180 | 版本/部署 |
| `deployment/数据库备份.py` | 153 | 版本/部署 |
| `logger.py` | 319 | 其他/待归类 |
| `monitor_pipeline.py` | 29 | 采集器 |
| `monitoring.py` | 590 | 其他/待归类 |
| `populate_empty_tables.py` | 294 | 数据库/迁移 |
| `run_production.py` | 136 | 其他/待归类 |
| `run_supervised.py` | 195 | Web核心/装配 |
| `scripts/backup_db.py` | 118 | 运维/脚本工具 |
| `scripts/check_system.py` | 160 | 评测/验证 |
| `scripts/collect_now.py` | 94 | 采集器 |
| `scripts/daily_git_sync.py` | 131 | 运维/脚本工具 |
| `scripts/export_report.py` | 133 | 报告/导出 |
| `scripts/github_upgrade_check.py` | 121 | 运维/脚本工具 |
| `scripts/init_database_data.py` | 412 | 数据库/迁移 |
| `scripts/init_db.py` | 347 | 运维/脚本工具 |
| `scripts/license_audit.py` | 62 | 运维/脚本工具 |
| `scripts/run_core_regression.py` | 53 | 运维/脚本工具 |
| `scripts/stability_fix.py` | 273 | 恢复/守护/稳定 |
| `scripts/staging_setup.py` | 52 | 运维/脚本工具 |
| `scripts/sync_xhs_cookie_from_cdp.py` | 115 | 采集器 |
| `system_watchdog.py` | 278 | 恢复/守护/稳定 |
| `topic_note_detail_backfill.py` | 273 | 其他/待归类 |
| `tunnel_guardian.py` | 251 | 恢复/守护/稳定 |
| `update_reference.py` | 236 | 其他/待归类 |
| `v4_upgrade/data_cleanup/fix_publish_date.py` | 209 | v4增强层 |
| `web_topic_discovery.py` | 187 | 采集器 |
| `wechat_notifier.py` | 985 | 通知 |
| `xhs_cdp_collector.py` | 273 | 采集器 |

## E. 测试资产（180，按目录聚合，不逐条）

| 目录 | 数量 |
|---|--:|
| `tests/__init__.py` | 1 |
| `tests/_adapter_live.py` | 1 |
| `tests/_append_log.py` | 1 |
| `tests/_append_log10.py` | 1 |
| `tests/_append_log11.py` | 1 |
| `tests/_append_log6.py` | 1 |
| `tests/_append_log7.py` | 1 |
| `tests/_append_log8.py` | 1 |
| `tests/_append_log9.py` | 1 |
| `tests/_archive_blueprint.py` | 1 |
| `tests/_audit_data.py` | 1 |
| `tests/_audit_misc.py` | 1 |
| `tests/_audit_system.py` | 1 |
| `tests/_audit_time2.py` | 1 |
| `tests/_audit_time_anomaly.py` | 1 |
| `tests/_backfill_pubdt.py` | 1 |
| `tests/_cdp_check.py` | 1 |
| `tests/_cdp_check2.py` | 1 |
| `tests/_cdp_check3.py` | 1 |
| `tests/_cdp_detach_start.py` | 1 |
| `tests/_cdp_keepalive.py` | 1 |
| `tests/_cdp_probe.py` | 1 |
| `tests/_cdp_proxy.py` | 1 |
| `tests/_check_9222_login.py` | 1 |
| `tests/_check_ai.py` | 1 |
| `tests/_chk_cdp.py` | 1 |
| `tests/_chk_empty.py` | 1 |
| `tests/_clean_brand_test.py` | 1 |
| `tests/_collect_check.py` | 1 |
| `tests/_collect_probe.py` | 1 |
| `tests/_desk_load.py` | 1 |
| `tests/_diag_black.py` | 1 |
| `tests/_diag_black2.py` | 1 |
| `tests/_diag_black3.py` | 1 |
| `tests/_diag_black4.py` | 1 |
| `tests/_diag_black5.py` | 1 |
| `tests/_diag_black6.py` | 1 |
| `tests/_diag_cdp_subproc.py` | 1 |
| `tests/_diag_icon.py` | 1 |
| `tests/_diag_icon2.py` | 1 |
| `tests/_diag_inline.py` | 1 |
| `tests/_diag_mobile.py` | 1 |
| `tests/_diag_mobile2.py` | 1 |
| `tests/_diag_rule.py` | 1 |
| `tests/_diag_switch.py` | 1 |
| `tests/_dirty_detail.py` | 1 |
| `tests/_dup_schedule.py` | 1 |
| `tests/_empty_title.py` | 1 |
| `tests/_extract_docx.py` | 1 |
| `tests/_extract_frames.py` | 1 |
| `tests/_extract_js.py` | 1 |
| `tests/_extract_zbmp.py` | 1 |
| `tests/_fix_empty_titles.py` | 1 |
| `tests/_fix_state_order.py` | 1 |
| `tests/_fix_testpath.py` | 1 |
| `tests/_fix_title_fallback.py` | 1 |
| `tests/_health_collect.py` | 1 |
| `tests/_healthcheck.py` | 1 |
| `tests/_importer_live.py` | 1 |
| `tests/_init_schedule_table.py` | 1 |
| `tests/_inspect_tables.py` | 1 |
| `tests/_live_collect.py` | 1 |
| `tests/_mobile_probe.py` | 1 |
| `tests/_mount_check.py` | 1 |
| `tests/_notes_schema.py` | 1 |
| `tests/_patch_ai_xhs.py` | 1 |
| `tests/_patch_app.py` | 1 |
| `tests/_patch_app_feedback.py` | 1 |
| `tests/_patch_automation.py` | 1 |
| `tests/_patch_automation_noproxy.py` | 1 |
| `tests/_patch_cdp_autostart.py` | 1 |
| `tests/_patch_collect_state.py` | 1 |
| `tests/_patch_collector.py` | 1 |
| `tests/_patch_collector_cdp.py` | 1 |
| `tests/_patch_collector_pycdp.py` | 1 |
| `tests/_patch_collector_tune.py` | 1 |
| `tests/_patch_database_pubdt.py` | 1 |
| `tests/_patch_gitsafety.py` | 1 |
| `tests/_patch_guard_wiring.py` | 1 |
| `tests/_patch_logs.py` | 1 |
| `tests/_patch_norm_title.py` | 1 |
| `tests/_patch_port.py` | 1 |
| `tests/_patch_proxy_wiring.py` | 1 |
| `tests/_patch_state_func.py` | 1 |
| `tests/_patch_title_fallback.py` | 1 |
| `tests/_patch_version_nav.py` | 1 |
| `tests/_persist_rednote.py` | 1 |
| `tests/_probe9222.py` | 1 |
| `tests/_probe_cdp_nav.py` | 1 |
| `tests/_probe_db2.py` | 1 |
| `tests/_probe_explore_url.py` | 1 |
| `tests/_proxy_api_check.py` | 1 |
| `tests/_proxy_realcheck.py` | 1 |
| `tests/_read_docx.py` | 1 |
| `tests/_readiness_audit.py` | 1 |
| `tests/_repo.py` | 1 |
| `tests/_restart_9222.py` | 1 |
| `tests/_run_core.py` | 1 |
| `tests/_run_core2.py` | 1 |
| `tests/_run_core_tests.py` | 1 |
| `tests/_run_one_collect.py` | 1 |
| `tests/_shot_before.py` | 1 |
| `tests/_start_browser.py` | 1 |
| `tests/_start_cdp.py` | 1 |
| `tests/_swire_scan.py` | 1 |
| `tests/_test_auth_api.py` | 1 |
| `tests/_test_cdp_collect.py` | 1 |
| `tests/_test_collector_guard.py` | 1 |
| `tests/_test_guard_wiring.py` | 1 |
| `tests/_test_proxy_pool.py` | 1 |
| `tests/_test_risk_engine.py` | 1 |
| `tests/_test_vc_api.py` | 1 |
| `tests/_test_version_api.py` | 1 |
| `tests/_test_version_center.py` | 1 |
| `tests/_topic_run.py` | 1 |
| `tests/_topic_run2.py` | 1 |
| `tests/_ui_final.py` | 1 |
| `tests/_ui_mon.py` | 1 |
| `tests/_ui_mset.py` | 1 |
| `tests/_ui_pub_mobile.py` | 1 |
| `tests/_ui_q.py` | 1 |
| `tests/_ui_shot.py` | 1 |
| `tests/_ui_shot2.py` | 1 |
| `tests/_ui_shot3.py` | 1 |
| `tests/_v4_live.py` | 1 |
| `tests/_v4dbg.py` | 1 |
| `tests/_verify4.py` | 1 |
| `tests/_verify4b.py` | 1 |
| `tests/_verify_8201.py` | 1 |
| `tests/_verify_e2e.py` | 1 |
| `tests/_watch_1605.py` | 1 |
| `tests/_watch_auto.py` | 1 |
| `tests/_xhs_probe.py` | 1 |
| `tests/audit_probe_1.py` | 1 |
| `tests/audit_probe_2.py` | 1 |
| `tests/audit_probe_3.py` | 1 |
| `tests/audit_probe_4.py` | 1 |
| `tests/audit_probe_5.py` | 1 |
| `tests/audit_probe_6.py` | 1 |
| `tests/backfill_detail_cdp.py` | 1 |
| `tests/conftest.py` | 1 |
| `tests/github_benchmark.py` | 1 |
| `tests/healthcheck.py` | 1 |
| `tests/test_adaptive_engine.py` | 1 |
| `tests/test_ai.py` | 1 |
| `tests/test_api.py` | 1 |
| `tests/test_api_smoke.py` | 1 |
| `tests/test_auth_api.py` | 1 |
| `tests/test_auto_recovery.py` | 1 |
| `tests/test_bilibili.py` | 1 |
| `tests/test_brand_library.py` | 1 |
| `tests/test_browser_e2e.py` | 1 |
| `tests/test_collect_pipeline.py` | 1 |
| `tests/test_collect_state.py` | 1 |
| `tests/test_collection_full.py` | 1 |
| `tests/test_data_feedback.py` | 1 |
| `tests/test_database.py` | 1 |
| `tests/test_douyin_adapter.py` | 1 |
| `tests/test_e2e.py` | 1 |
| `tests/test_event_curation.py` | 1 |
| `tests/test_event_date.py` | 1 |
| `tests/test_guard_wiring.py` | 1 |
| `tests/test_health_center.py` | 1 |
| `tests/test_instagram_adapter.py` | 1 |
| `tests/test_llm_gateway.py` | 1 |
| `tests/test_llm_online.py` | 1 |
| `tests/test_negative_event_api.py` | 1 |
| `tests/test_proxy_pool.py` | 1 |
| `tests/test_report_periods.py` | 1 |
| `tests/test_risk_engine.py` | 1 |
| `tests/test_safety_boundary.py` | 1 |
| `tests/test_scheduling.py` | 1 |
| `tests/test_security_scan.py` | 1 |
| `tests/test_sentiment_engine.py` | 1 |
| `tests/test_subject_redline.py` | 1 |
| `tests/test_system.py` | 1 |
| `tests/test_title_fallback.py` | 1 |
| `tests/test_topic_port.py` | 1 |
| `tests/test_version_api.py` | 1 |
| `tests/v4_smoke.py` | 1 |

## F. API / 路由身份（app.py 189 + 子系统蓝图 = 全仓 363，按前缀分组；逐条明细以既有 Phase1 盘点为准，不重复全列）

| 路由组 | 数量 |
|---|--:|
| `/api/topic-campaign` | 15 |
| `/adapters` | 14 |
| `/api/cases` | 10 |
| `/api/pr` | 10 |
| `/` | 9 |
| `/api/settings` | 9 |
| `/api/event-graph` | 8 |
| `/api/report` | 8 |
| `/api/collector` | 8 |
| `/api/web` | 8 |
| `/api/app_evidence` | 8 |
| `/api/swire` | 8 |
| `/api/xhs` | 7 |
| `/api/boundary` | 7 |
| `/api/export` | 7 |
| `/ai` | 7 |
| `/api/case-analysis` | 6 |
| `/api/ai` | 6 |
| `/api/system` | 6 |
| `/api/config` | 6 |
| `/api/feedback` | 6 |
| `/api/evaluation` | 6 |
| `/api/notes` | 5 |
| `/api/ark` | 5 |
| `/tasks` | 5 |
| `/api/security` | 5 |
| `/api/collect` | 4 |
| `/api/brand-industry` | 4 |
| `/api/cache` | 4 |
| `/api/negative` | 4 |
| `/api/event-review` | 4 |
| `/api/brands` | 4 |
| `/api/weibo` | 4 |
| `/api/adaptive` | 4 |
| `/api/recovery` | 4 |
| `/auth` | 4 |
| `/api/users` | 4 |
| `/api/negative-review` | 3 |
| `/api/reports` | 3 |
| `/api/ai-filter` | 3 |
| `/api/alerts` | 3 |
| `/api/stability` | 3 |
| `/api/bilibili` | 3 |
| `/api/collector-v2` | 3 |
| `/api/local-ai` | 3 |
| `/data` | 3 |
| `/api/security-questions` | 3 |
| `/api/brand-knowledge` | 2 |
| `/api/subject-classifier` | 2 |
| `/api/brand-report` | 2 |
| `/api/proxy` | 2 |
| `/api/events` | 2 |
| `/api/ai-learning` | 2 |
| `/api/web-sentiment` | 2 |
| `/api/network` | 2 |
| `/api/weekly` | 2 |
| `/api/dashboard` | 2 |
| `/api/digest` | 2 |
| `/api/status` | 2 |
| `/api/official-info` | 2 |
| `/api/special-report` | 2 |
| `/api/web-topics` | 2 |
| `/health` | 2 |
| `/api/system-config` | 2 |
| `/api/brand-stats` | 1 |
| `/favicon.ico` | 1 |
| `/api/stats` | 1 |
| `/api/risk-alerts` | 1 |
| `/api/hot-notes` | 1 |
| `/api/comments` | 1 |
| `/api/web-mentions` | 1 |
| `/api/feedback-keywords` | 1 |
| `/api/hot-topics` | 1 |
| `/api/intelligence` | 1 |
| `/api/developer` | 1 |
| `/api/search` | 1 |
| `/api/function-map` | 1 |
| `/api/translate` | 1 |
| `/api/platform-health` | 1 |
| `/api/analyze` | 1 |
| `/api/note` | 1 |
| `/api/historical-notes` | 1 |
| `/api/backup` | 1 |
| `/api/trends` | 1 |
| `/remote` | 1 |
| `/healthz` | 1 |
| `/api/overview` | 1 |
| `/api/rednote` | 1 |
| `/api/test` | 1 |
| `/api/v2` | 1 |
| `/api/collection` | 1 |
| `/api/dev` | 1 |
| `/<note_id>` | 1 |
| `/search` | 1 |
| `/<event_id>` | 1 |
| `/export` | 1 |
| `/daily` | 1 |
| `/analyze` | 1 |
| `/providers` | 1 |
| `/trigger` | 1 |
| `/status` | 1 |
| `/topics` | 1 |
| `/browser-discovery` | 1 |
| `/api/health` | 1 |
| `/api/architecture` | 1 |
| `/summary` | 1 |
| `/topic-campaign` | 1 |
| `/console` | 1 |
| `/upload` | 1 |
| `/confirm` | 1 |
| `/login` | 1 |
| `/api/change-password` | 1 |
| `/api/audit-logs` | 1 |
| `/api/audit-stats` | 1 |
| `/api/history` | 1 |
| `/api/save` | 1 |
| `/api/push` | 1 |
| `/api/check` | 1 |
| `/api/pull` | 1 |
| `/api/rollback` | 1 |

> 重复路由簇（④唯一 Owner 重点）：报告 12 路由、负面两套 `/api/negative/*` 与 `/api/negative-review/*`、
> AI 多套 `/api/ai|ark|intelligence|ai-filter|ai-learning`、健康 5 套、高危运行代码 3 套 `/api/developer/run`、`/api/dev/run-code`、`/api/config/run-code`。

## G. 数据表身份（51，sqlite 只读行数）

| ASSET-ID | 表 | 行数 | 状态备注 |
|---|---|--:|---|
| ASSET-DB-001 | `ai_filter_log` | 827 |  |
| ASSET-DB-002 | `app_evidence_records` | 0 | 空表（PLANNED/RESERVED 候选） |
| ASSET-DB-003 | `auth_recovery_tasks` | 1 |  |
| ASSET-DB-004 | `brand_industry_monitor` | 198 |  |
| ASSET-DB-005 | `brand_knowledge` | 103 |  |
| ASSET-DB-006 | `case_deep_analysis` | 20 |  |
| ASSET-DB-007 | `collection_counters` | 1 |  |
| ASSET-DB-008 | `collection_logs` | 477 |  |
| ASSET-DB-009 | `collector_quality_log` | 7 |  |
| ASSET-DB-010 | `comments` | 2 |  |
| ASSET-DB-011 | `daily_digest` | 5 |  |
| ASSET-DB-012 | `daily_reports` | 25 |  |
| ASSET-DB-013 | `event_graph_events` | 16 |  |
| ASSET-DB-014 | `event_graph_relations` | 1 |  |
| ASSET-DB-015 | `event_insights` | 17 |  |
| ASSET-DB-016 | `event_mentions` | 562 |  |
| ASSET-DB-017 | `events` | 427 |  |
| ASSET-DB-018 | `feedback_keywords` | 16 |  |
| ASSET-DB-019 | `industry_stats` | 8 |  |
| ASSET-DB-020 | `note_comments` | 141 |  |
| ASSET-DB-021 | `note_review_history` | 8327 |  |
| ASSET-DB-022 | `notes` | 957 |  |
| ASSET-DB-023 | `notification_config` | 0 | 空表（PLANNED/RESERVED 候选） |
| ASSET-DB-024 | `notification_logs` | 3 |  |
| ASSET-DB-025 | `review_logs` | 0 | 空表（PLANNED/RESERVED 候选） |
| ASSET-DB-026 | `review_samples` | 0 | 空表（PLANNED/RESERVED 候选） |
| ASSET-DB-027 | `review_tickets` | 0 | 空表（PLANNED/RESERVED 候选） |
| ASSET-DB-028 | `schedule_decisions` | 81 |  |
| ASSET-DB-029 | `schema_version` | 7 |  |
| ASSET-DB-030 | `sqlite_sequence` | 41 |  |
| ASSET-DB-031 | `swire_events` | 10 |  |
| ASSET-DB-032 | `swire_notes` | 0 | 空表（PLANNED/RESERVED 候选） |
| ASSET-DB-033 | `swire_projects` | 8 |  |
| ASSET-DB-034 | `system_config` | 10 |  |
| ASSET-DB-035 | `token_stat` | 1 |  |
| ASSET-DB-036 | `topic_campaign_notes` | 120 |  |
| ASSET-DB-037 | `topic_campaign_snapshots` | 325 |  |
| ASSET-DB-038 | `topic_campaign_topics` | 7 |  |
| ASSET-DB-039 | `topic_campaigns` | 1 |  |
| ASSET-DB-040 | `v4_ai_shadow` | 2 |  |
| ASSET-DB-041 | `v4_audit_logs` | 33 |  |
| ASSET-DB-042 | `v4_login_attempts` | 26 |  |
| ASSET-DB-043 | `v4_security_questions` | 2 |  |
| ASSET-DB-044 | `v4_sessions` | 27 |  |
| ASSET-DB-045 | `v4_users` | 1 |  |
| ASSET-DB-046 | `web_events` | 20 |  |
| ASSET-DB-047 | `web_mentions` | 79 |  |
| ASSET-DB-048 | `web_runs` | 28 |  |
| ASSET-DB-049 | `web_sources` | 1 |  |
| ASSET-DB-050 | `web_topics` | 96 |  |
| ASSET-DB-051 | `weekly_events` | 30 |  |

## H. 前端资产身份

### H.1 CSS（23）—— 权威主题层为 static/css/zb-theme.css（最后加载），其余历史设计系统待④/旧UI清理

| 文件 | 行 |
|---|--:|
| `static/css/apple-ui.css` | 1015 |
| `static/css/architecture_dashboard.css` | 647 |
| `static/css/case_deep_analysis.css` | 680 |
| `static/css/compat.css` | 553 |
| `static/css/components-minimal.css` | 818 |
| `static/css/components.css` | 1298 |
| `static/css/design-v8.css` | 1162 |
| `static/css/design-v9-gpt-codex.css` | 1416 |
| `static/css/layout-minimal.css` | 1068 |
| `static/css/layout.css` | 990 |
| `static/css/mobile.css` | 181 |
| `static/css/nomi_global_drag.css` | 12 |
| `static/css/style.css` | 826 |
| `static/css/tokens-minimal.css` | 229 |
| `static/css/tokens.css` | 441 |
| `static/css/ui_dashboard.css` | 1423 |
| `static/css/ui_modern.css` | 1641 |
| `static/css/ui_optimized.css` | 654 |
| `static/css/v3_modules.css` | 148 |
| `static/css/zachary_robot.css` | 340 |
| `static/css/zb-gpt-theme.css` | 2348 |
| `static/css/zb-theme.css` | 756 |
| `static/topic_campaign.css` | 466 |

### H.2 JS（22）

| 文件 | 行 |
|---|--:|
| `static/js/app.js` | 1365 |
| `static/js/app_evidence.js` | 413 |
| `static/js/architecture_dashboard.js` | 681 |
| `static/js/auxiliary_sources.js` | 80 |
| `static/js/badge_manager.js` | 276 |
| `static/js/case_deep_analysis.js` | 414 |
| `static/js/design-v9-interactions.js` | 355 |
| `static/js/frontend_enhancement.js` | 872 |
| `static/js/nomi_global_drag.js` | 81 |
| `static/js/pr_case_integration.js` | 238 |
| `static/js/swire_group.js` | 281 |
| `static/js/system_controls.js` | 595 |
| `static/js/system_features_ui.js` | 339 |
| `static/js/ui_interactions_v5.8.0.js` | 978 |
| `static/js/v3_modules.js` | 355 |
| `static/js/vendor/three.min.js` | 8 |
| `static/js/zachary_3d.js` | 180 |
| `static/js/zachary_png_face.js` | 51 |
| `static/js/zachary_robot.js` | 963 |
| `static/js/zachary_robot_enhanced.js` | 661 |
| `static/js/zachary_system_knowledge.js` | 209 |
| `static/topic_campaign.js` | 551 |

### H.3 模板（10）—— 生产主入口为 static/index.html(SPA)；templates/*.html 为旧服务端渲染，待核实是否仍 render

- `templates/base.html`
- `templates/events.html`
- `templates/index.html`
- `templates/notes.html`
- `templates/report.html`
- `v4_upgrade/collect/templates/collect.html`
- `v4_upgrade/console/templates/console.html`
- `v4_upgrade/settings/templates/login.html`
- `v4_upgrade/settings/templates/settings.html`
- `v4_upgrade/version_center/templates/version_center.html`

## I. 依赖身份（requirements 15，0 引用仅登记不删）

| 包 | 初判 |
|---|---|
| `Flask` | 在用/传递依赖 |
| `Werkzeug` | 在用/传递依赖 |
| `pandas` | 在用/传递依赖 |
| `openpyxl` | 在用/传递依赖 |
| `xlsxwriter` | UNUSED? 移除候选（0 本地 import，Staging 回归后才准退） |
| `python-docx` | 在用/传递依赖 |
| `reportlab` | 在用/传递依赖 |
| `playwright` | 在用/传递依赖 |
| `selenium` | UNUSED? 移除候选（0 本地 import，Staging 回归后才准退） |
| `psutil` | 在用/传递依赖 |
| `requests` | 在用/传递依赖 |
| `httpx` | UNUSED? 移除候选（0 本地 import，Staging 回归后才准退） |
| `python-dotenv` | 在用/传递依赖 |
| `colorama` | UNUSED? 移除候选（0 本地 import，Staging 回归后才准退） |
| `tqdm` | UNUSED? 移除候选（0 本地 import，Staging 回归后才准退） |

## J. 衔接

- ③ ARCHITECTURE-MAP：以表 A/B 的层 + 业务域为骨架，只映射不搬目录。
- ④ CAPABILITY-OWNERSHIP：对 F 重复路由簇与 CAPABILITY-CLUSTERS 定唯一 Owner，其余标 DUPLICATE/LEGACY；🔴红线资产 Owner 唯一且口径不得改。
- ⑤ FEATURE 总账：在 ASSET-ID 之上建 FEATURE-CTH/ZBMP-NNN，绑定 UI/API/DB/Status/Evidence。
- 本文件由生成器产出，请勿手改表格体；身份修订改生成器规则后重跑。