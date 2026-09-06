# ZBC+OSAI 双仓全量功能清单 (FULL_CAPABILITY_INVENTORY)

> 审计日期: 2026-09-07
> 审计范围: D:\Taikoo-monitor-new (ZBC) + D:\Zachary OS AI (OSAI)
> 状态标记: VERIFIED/PARTIAL/BLOCKED/NO_DATA
> 收敛分类: KEEP/MERGE/REFACTOR/DEPRECATE/DELETE/UNKNOWN
> 层级: L0基础设施/L1核心能力/L2业务能力/L3产品域/L4 API/L5 UI

---

## 一、ZBC 根目录模块审计（180个Python模块，按14领域分类）

### 领域1: AI体系（20个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | ai_analyzer.py | 34KB | AI内容分析引擎，情绪/主题/风险分类 | 间接(app.py import) | system/ai.html | test_ai.py | ACTIVE | Shared/L2 | KEEP |
| 2 | ai_api.py | 28KB | AI API端点，15+端点，任务引擎集成 | system_ai_data_bp | system/ai.html | test_ai_task_engine.py | ACTIVE | System/L4 | KEEP |
| 3 | ai_browser_api.py | 24KB | AI Browser Runtime API端点 | 间接(lumenis_bp) | system/browser.html | test_ai_browser_runtime.py | ACTIVE | System/L4 | KEEP |
| 4 | ai_browser_runtime.py | 84KB | AI Browser Runtime核心，Observe/Reason/Plan/Act/Verify | 间接 | system/browser.html | test_ai_browser_runtime.py(185) | ACTIVE | System/L2 | KEEP (C Shard交付) |
| 5 | ai_call_logger.py | 21KB | AI调用日志记录与审计 | 间接 | 无 | test_g2_ai_call_logger_audit.py | ACTIVE | Shared/L1 | KEEP |
| 6 | ai_channel.py | 27KB | AI多Provider通道管理(智谱/ARK/千问/Ollama)，6层Provider层级/fallback链/额度切换 | 间接 | 无 | test_ai_channel*.py(4个) | ACTIVE | Shared/L1 | KEEP **(J Shard处理中，REFACTOR)** |
| 7 | ai_domain_context.py | 14KB | AI域上下文，ZBMP/CTH双域隔离 | 间接 | 无 | test_ai_domain_context.py | ACTIVE | Shared/L1 | KEEP |
| 8 | ai_evaluation.py | 22KB | AI输出评估与质量评分 | 间接 | system/evaluation.html | test_ai_evaluation.py(27KB) | ACTIVE | Shared/L1 | KEEP |
| 9 | ai_filter.py | 14KB | AI内容过滤器，敏感内容过滤 | 间接(app.py import) | 无 | 无直接测试 | ACTIVE | Shared/L2 | KEEP |
| 10 | ai_governance.py | 23KB | AI治理，策略/配额/审计，Provider额度切换/fallback链 | 间接 | 无 | 无直接测试 | PARTIAL | Shared/L1 | KEEP **(J Shard处理中，REFACTOR)** |
| 11 | ai_learning_engine.py | 19KB | AI学习引擎，人工修正反馈学习 | 间接(app.py import) | 无 | test_learning_persistence.py | ACTIVE | Shared/L2 | KEEP |
| 12 | ai_resource_packs.py | 11KB | AI资源包管理 | 间接 | 无 | 无 | PARTIAL | Shared/L1 | REFACTOR |
| 13 | ai_task_engine.py | 63KB | AI任务引擎核心，任务编排/执行/追踪 | 间接 | system/ai.html | test_ai_task_engine.py(18KB) | ACTIVE | System/L2 | KEEP (B Shard交付) |
| 14 | ai_task_parser.py | 19KB | AI任务解析器，自然语言→任务计划 | 间接 | 无 | test_ai_task_engine.py | ACTIVE | System/L2 | KEEP (B Shard交付) |
| 15 | intelligence.py | 41KB | 情报分析核心，品牌情报聚合 | 间接(app.py import) | zbmp/intelligence.html | 无直接测试 | ACTIVE | ZBMP/L2 | KEEP |
| 16 | intelligence_library_api.py | 9KB | 情报库API端点 | intelligence_library_bp(已注册) | 无 | 无 | ACTIVE | Shared/L4 | KEEP |
| 17 | local_ai_client.py | 13KB | 本地AI客户端(Ollama/gpt-oss)，离线兜底 | 间接(app.py import) | 无 | test_ai_degrade.py | ACTIVE | Shared/L1 | KEEP |
| 18 | ark_llm.py | 14KB | 字节ARK LLM客户端，云端备用 | 间接 | 无 | test_llm_gateway.py | ACTIVE | Shared/L1 | KEEP |
| 19 | ai_agent_registry.py | 13KB | AI Agent注册表，Agent身份/能力注册 | 间接 | system/ai.html | test_agent_*.py(3个) | ACTIVE | System/L1 | KEEP (B Shard交付) |
| 20 | audit_ai_chain.py | 11KB | AI调用链审计工具 | 无(工具脚本) | 无 | 无 | PARTIAL | Shared/L1 | DEPRECATE(合并到ai_call_logger) |

### 领域2: 采集体系（15个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | collector.py | 29KB | 核心采集器，小红书搜索/详情/评论 | 间接(app.py import) | cth/xiaohongshu.html | test_collector_*.py(多个) | ACTIVE | CTH/L2 | KEEP(权威采集实现) |
| 2 | collector_automation.py | 53KB | 采集自动化编排，定时/调度/重试 | 间接(app.py import) | system/collector.html | test_collector_lifecycle_state.py | ACTIVE | System/L2 | KEEP |
| 3 | collector_guard_integration.py | 3KB | collector_guard集成桥接 | 间接 | 无 | test_collector_guard_integration.py | ACTIVE | System/L1 | MERGE(并入collector_guard) |
| 4 | collector_status_api.py | 6KB | 采集状态API端点 | collector_status_bp(已注册) | system/collector.html | 无 | ACTIVE | System/L4 | KEEP |
| 5 | collector_v2_integration.py | 8KB | collector_v2集成桥接 | 间接 | 无 | 无 | PARTIAL | System/L2 | MERGE(并入collector_v2) |
| 6 | collector_auto_start.py | 6KB | 采集器自动启动管理 | 间接 | 无 | 无 | PARTIAL | System/L2 | REFACTOR(并入collector_automation) |
| 7 | xhs_cdp_collector.py | 45KB | 小红书CDP采集器，Chrome DevTools Protocol | 间接 | cth/xiaohongshu.html | test_cdp_*.py(多个) | ACTIVE | CTH/L2 | KEEP |
| 8 | xhs_collection_optimizer.py | 25KB | 小红书采集优化器，去重/质量/速率 | 间接 | 无 | test_collection_quality_gate.py | ACTIVE | CTH/L2 | KEEP |
| 9 | xhs_cookie_bridge.py | 55KB | 小红书Cookie桥接，登录态管理/导入 | 间接(app.py import) | auth/cth_login.html | test_cookies_import_api.py | ACTIVE | CTH/L1 | KEEP |
| 10 | xhs_p0_orchestrator.py | 16KB | 小红书P0编排器，主链路调度 | 间接(app.py import) | 无 | 无 | ACTIVE | CTH/L2 | KEEP |
| 11 | xhs_runtime_state.py | 10KB | 小红书运行时状态管理 | 间接 | 无 | test_collect_state.py | ACTIVE | CTH/L1 | KEEP |
| 12 | weibo_login_manager.py | 11KB | 微博登录管理器 | 间接 | 无 | 无 | PARTIAL | CTH/L1 | KEEP |
| 13 | bilibili_login_manager.py | 7KB | B站登录管理器 | 间接 | 无 | test_bilibili.py | PARTIAL | CTH/L1 | KEEP |
| 14 | check_collection.py | 1.5KB | 采集检查工具 | 无(工具) | 无 | 无 | DEAD | System/工具 | DELETE(一次性脚本) |
| 15 | check_collection_detail.py | 2.1KB | 采集详情检查工具 | 无(工具) | 无 | 无 | DEAD | System/工具 | DELETE(一次性脚本) |
| 16 | import_cookies.py | 4.9KB | Cookie导入工具 | 无(工具) | 无 | 无 | PARTIAL | System/工具 | REFACTOR(并入xhs_cookie_bridge) |
| 17 | import_xhs_cookies.py | 4.3KB | 小红书Cookie导入工具 | 无(工具) | 无 | test_cookies_import_api.py | PARTIAL | System/工具 | MERGE(并入import_cookies) |

### 领域3: 数据体系（12个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | canonical_data.py | 43KB | 规范数据模型，Platform Raw→Normalized→Canonical | 间接 | cth/data_center/ | test_canonical_data_t4.py(19KB) | ACTIVE | Shared/L0 | KEEP (F Shard交付) |
| 2 | canonical_metrics.py | 12KB | 规范指标计算引擎 | 间接 | 无 | test_canonical_metrics.py | ACTIVE | Shared/L1 | KEEP |
| 3 | database.py | 71KB | 数据库核心，125表管理/连接/查询 | 间接(app.py import) | system/database.html | test_database.py | ACTIVE | Shared/L0 | KEEP |
| 4 | database_migrations.py | 24KB | 数据库迁移管理，向后兼容迁移 | 间接 | 无 | test_alembic_migration.py | ACTIVE | Shared/L0 | KEEP |
| 5 | data_boundary.py | 11KB | 数据边界，双域数据隔离 | 间接 | 无 | test_subject_context_isolation.py | ACTIVE | Shared/L1 | KEEP |
| 6 | data_center_api.py | 12KB | 数据中心API端点 | data_center_bp(已注册) | cth/data_center/ | test_platform_data_dict_v1.py | ACTIVE | Shared/L4 | KEEP (F Shard交付) |
| 7 | data_feedback_loop.py | 16KB | 数据反馈闭环，人工修正→规则更新 | 间接 | 无 | test_data_feedback.py | ACTIVE | Shared/L2 | KEEP |
| 8 | data_quality_gate.py | 9KB | 数据质量门控，完整性/准确性检查 | 间接 | 无 | test_data_quality_gate.py | ACTIVE | Shared/L1 | KEEP |
| 9 | data_query_api.py | 7KB | 数据查询API | 无(未注册蓝图) | 无 | 无 | PARTIAL | Shared/L4 | REFACTOR(并入data_center_api) |
| 10 | schema_registry.py | 7KB | Schema注册表，数据字典管理 | 间接 | 无 | test_schema_registry.py | ACTIVE | Shared/L0 | KEEP |
| 11 | historical_data_importer.py | 19KB | 历史数据导入器 | 无(工具) | 无 | test_historical_data.py(16KB) | ACTIVE | Shared/工具 | KEEP |
| 12 | migrate_notes_time_fields.py | 4KB | 笔记时间字段迁移工具 | 无(工具) | 无 | 无 | DEAD | Shared/工具 | DELETE(一次性迁移脚本) |

### 领域4: 业务核心（12个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | daily_report.py | 41KB | 日报生成引擎，publish_datetime口径 | 间接(app.py import) | cth/reports.html | test_daily_report_redline.py | ACTIVE | CTH/L2 | KEEP |
| 2 | risk_engine.py | 38KB | 风险引擎，主体过滤/风险规则/分级 | 间接(app.py import) | cth/risk.html | test_risk_engine*.py(4个) | ACTIVE | Shared/L2 | KEEP(P0核心) |
| 3 | event_graph.py | 27KB | 事件图谱，营销/传播/舆情事件关系 | 间接 | zbmp/evaluation.html | test_event_graph_relations.py | ACTIVE | Shared/L2 | KEEP |
| 4 | brand_propagation.py | 22KB | 品牌传播分析，传播主体/路径/贡献 | 间接 | zbmp/brand.html | 无直接测试 | ACTIVE | ZBMP/L2 | KEEP |
| 5 | brand_report_generator.py | 18KB | 品牌报告生成器 | 间接 | zbmp/reports.html | test_brand_report_master_model.py | ACTIVE | ZBMP/L2 | KEEP |
| 6 | brand_knowledge_base.py | 8KB | 品牌知识库 | 间接 | 无 | test_brand_library.py | ACTIVE | ZBMP/L2 | KEEP |
| 7 | brand_stats_recompute.py | 6KB | 品牌统计重算工具 | 无(工具) | 无 | 无 | PARTIAL | ZBMP/工具 | REFACTOR(并入brand_propagation) |
| 8 | public_opinion_cases.py | 63KB | 舆情案例库，案例管理/检索/分析 | 间接 | zbmp/content.html | 无直接测试 | ACTIVE | Shared/L2 | KEEP |
| 9 | pr_case_engine.py | 11KB | 公关案例引擎 | 间接 | 无 | 无 | PARTIAL | Shared/L2 | MERGE(并入public_opinion_cases) |
| 10 | pr_case_integration.py | 28KB | 公关案例集成API | pr_case_bp(已注册) | 无 | 无 | ACTIVE | Shared/L4 | KEEP |
| 11 | alert_engine.py | 24KB | 预警引擎，风险预警/通知 | 间接 | cth/risk.html | 无直接测试 | ACTIVE | Shared/L2 | KEEP |
| 12 | swire_group.py | 27KB | 太古集团模块，集团级品牌管理 | 间接(app.py import) | 无 | 无 | PARTIAL | CTH/L2 | REFACTOR(确认是否CTH域专用) |

### 领域5: KOS体系（12个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | kos_engine.py | 67KB | KOS引擎核心，KOS识别/画像/分析 | 动态(kos_routes) | zbmp/kos.html | test_kos_*.py(多个) | ACTIVE | ZBMP/L2 | KEEP |
| 2 | kos_metrics.py | 31KB | KOS指标计算，传播/互动/转化指标 | 动态 | zbmp/kos.html | test_g3_kos_metrics_config.py | ACTIVE | ZBMP/L1 | KEEP |
| 3 | kos_attribution.py | 15KB | KOS归因分析 | 动态 | zbmp/kos.html | test_kos_attribution.py/test_g1 | ACTIVE | ZBMP/L2 | KEEP |
| 4 | kos_intel.py | 15KB | KOS情报，KOS内容/趋势分析 | 动态 | zbmp/kos.html | 无直接测试 | ACTIVE | ZBMP/L2 | KEEP |
| 5 | kos_interest_graph.py | 30KB | KOS兴趣图谱 | 动态 | zbmp/kos.html | test_kos_interest_graph.py(14KB) | ACTIVE | ZBMP/L2 | KEEP |
| 6 | kos_ops.py | 15KB | KOS运营，KOS互动/回复管理 | 动态 | zbmp/kos.html | test_kos_ops.py | ACTIVE | ZBMP/L2 | KEEP |
| 7 | kos_paid.py | 10KB | KOS付费合作管理 | 动态 | zbmp/kos.html | test_kos_paid.py | ACTIVE | ZBMP/L2 | KEEP |
| 8 | kos_professional.py | 9KB | KOS专业度评估 | 动态 | zbmp/kos.html | 无直接测试 | PARTIAL | ZBMP/L2 | KEEP |
| 9 | kos_report.py | 29KB | KOS报告生成 | 动态 | zbmp/kos.html | 无直接测试 | ACTIVE | ZBMP/L2 | KEEP |
| 10 | kos_routes.py | 45KB | KOS API路由，动态注册 | 动态import(已注册) | zbmp/kos.html | test_kos_*.py | ACTIVE | ZBMP/L4 | KEEP |
| 11 | kos_scenarios.py | 6KB | KOS场景管理 | 动态 | 无 | 无 | PARTIAL | ZBMP/L2 | REFACTOR(并入kos_engine) |
| 12 | kos_execution.py | 7KB | KOS执行引擎 | 动态 | 无 | 无 | PARTIAL | ZBMP/L2 | REFACTOR(并入kos_ops) |
| 13 | kol_analysis.py | 3KB | KOL分析工具 | 无(未注册) | 无 | test_kol_analysis.py | PARTIAL | ZBMP/L2 | REFACTOR(并入kos_engine) |

### 领域6: 内容制作（15个模块）— H Shard正在激活，标注状态不重复修复

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | topic_campaign.py | 64KB | 话题活动管理，活动创建/监测/分析 | 间接(app.py import) | zbmp/content.html | test_topic_*.py(3个) | ACTIVE | ZBMP/L2 | KEEP (H Shard) |
| 2 | topic_snapshot.py | 3KB | 话题快照工具 | 无(工具) | 无 | test_topic_snapshot.py | PARTIAL | ZBMP/工具 | KEEP (H Shard) |
| 3 | topic_monitor_policy.py | 3KB | 话题监测策略 | 无 | 无 | 无 | PARTIAL | ZBMP/L2 | KEEP (H Shard) |
| 4 | topic_note_detail_backfill.py | 10KB | 话题笔记详情回填 | 无(工具) | 无 | 无 | PARTIAL | ZBMP/工具 | KEEP (H Shard) |
| 5 | web_topic_discovery.py | 5KB | 网页话题发现 | 无 | 无 | 无 | PARTIAL | ZBMP/L2 | KEEP (H Shard) |
| 6 | video_intelligence.py | 4KB | 视频情报分析 | 无 | 无 | test_video_intelligence.py | PARTIAL | ZBMP/L2 | KEEP (H Shard) |
| 7 | case_ai_evaluate.py | 6KB | 案例AI评估 | 无 | 无 | 无 | PARTIAL | Shared/L2 | KEEP (H Shard) |
| 8 | case_deep_analysis.py | 14KB | 案例深度分析 | 无 | 无 | 无 | PARTIAL | Shared/L2 | KEEP (H Shard) |
| 9 | case_templates.py | 13KB | 案例模板库 | 无 | 无 | 无 | PARTIAL | Shared/L2 | KEEP (H Shard) |
| 10 | resource_library.py | 13KB | 资源库管理 | 无 | 无 | 无 | PARTIAL | Shared/L2 | KEEP (H Shard) |
| 11 | collection_intelligence.py | 3KB | 采集情报 | 无 | 无 | test_collection_intelligence.py | PARTIAL | Shared/L2 | KEEP (H Shard) |
| 12 | context_intelligence.py | 6KB | 上下文情报 | 无 | 无 | test_context_intelligence.py | PARTIAL | Shared/L2 | KEEP (H Shard) |
| 13 | content_generation.py | 41KB | 内容生成引擎，AI文案/脚本生成 | 无(未注册蓝图) | zbmp/content.html | test_idea_generator.py(17KB) | ACTIVE | ZBMP/L2 | KEEP (H Shard) |
| 14 | web_monitor.py | 5KB | 网页监测(旧版，reprocess.py依赖discover()/feedback_keywords()) | 间接(reprocess.py) | 无 | 无 | ACTIVE | Shared/L2 | KEEP **(非死代码，reprocess.py依赖)** |
| 15 | web_monitor_v570.py | 6KB | 网页监测(v570新版，app.py import) | 间接(app.py import) | 无 | 无 | ACTIVE | Shared/L2 | KEEP(权威版本) |
| 16 | juguang_api.py | 3KB | 巨量引擎API | 间接(kos_routes引用) | 无 | 无 | PARTIAL | ZBMP/L2 | REFACTOR(确认是否激活) |

### 领域7: 运行时（12个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | runtime_guardian.py | 51KB | 运行时守护核心，健康检查/自愈/熔断 | 间接(app.py import) | system/runtime.html | test_runtime_guardian*.py(54KB) | ACTIVE | System/L1 | KEEP(权威实现) |
| 2 | runtime_preflight.py | 15KB | 运行时预检，启动前完整性检查 | 间接(app.py import) | system/runtime.html | test_runtime_preflight.py | ACTIVE | System/L1 | KEEP |
| 3 | runtime_bin.py | 4KB | 运行时二进制工具 | 无(工具) | 无 | test_runtime_bin.py | ACTIVE | System/工具 | KEEP |
| 4 | stability_monitor.py | 19KB | 稳定性监控 | 间接(app.py import) | system/runtime.html | 无直接测试 | ACTIVE | System/L1 | KEEP |
| 5 | system_guardian.py | 9KB | 系统守护进程 | 间接 | 无 | 无 | PARTIAL | System/L1 | MERGE(并入runtime_guardian) |
| 6 | system_watchdog.py | 12KB | 系统看门狗 | 间接 | 无 | 无 | PARTIAL | System/L1 | MERGE(并入runtime_guardian) |
| 7 | resident_health.py | 17KB | 常驻健康检查 | 间接 | system/runtime.html | test_resident_health.py | ACTIVE | System/L1 | KEEP |
| 8 | auto_recovery.py | 17KB | 自动恢复引擎 | 间接 | system/runtime.html | test_auto_recovery.py | ACTIVE | System/L1 | KEEP |
| 9 | ip_risk_state_machine.py | 31KB | IP风险状态机，风控识别/熔断/冷却 | 间接 | system/security.html | test_ip_risk_state_machine.py(13KB) | ACTIVE | System/L1 | KEEP |
| 10 | monitor_pipeline.py | 1.3KB | 监控管道入口 | 无(工具) | 无 | 无 | DEAD | System/工具 | DELETE(空壳脚本) |
| 11 | run_production.py | 6KB | 生产环境运行入口 | 无(工具) | 无 | 无 | PARTIAL | System/工具 | KEEP |
| 12 | run_supervised.py | 12KB | 监督模式运行入口 | 无(工具) | 无 | 无 | PARTIAL | System/工具 | KEEP |

### 领域8: 安全权限（10个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | permission_gate.py | 44KB | 权限门控核心，6级权限矩阵 | 间接(app.py import) | system/security.html | test_permission_gate*.py(58KB) | ACTIVE | Shared/L1 | KEEP(权威实现) |
| 2 | security_boundary.py | 44KB | 安全边界，操作隔离/审计 | 间接 | system/security.html | test_security_scanner_s2.py | ACTIVE | Shared/L1 | KEEP |
| 3 | safety_boundary.py | 19KB | 安全边界(轻量版) | 间接 | 无 | test_safety_boundary.py | ACTIVE | Shared/L1 | MERGE(并入security_boundary) |
| 4 | agent_security.py | 15KB | Agent安全，AI操作安全控制 | 间接 | system/security.html | test_agent_security.py | ACTIVE | System/L1 | KEEP |
| 5 | agent_boundary.py | 20KB | Agent边界，Agent操作范围限制 | 间接 | 无 | test_skill_agent_boundary.py(33KB) | ACTIVE | System/L1 | KEEP |
| 6 | p2_action_firewall.py | 8KB | P2动作防火墙(实验) | 间接 | 无 | 无 | PARTIAL | System/L1 | DEPRECATE(实验系列) |
| 7 | security_scanner.py | 16KB | 安全扫描器，漏洞/配置扫描 | 间接 | system/security.html | test_security_scan.py | ACTIVE | System/L1 | KEEP |
| 8 | compliance_gate.py | 6KB | 合规门控 | 间接 | 无 | test_compliance_gate.py | ACTIVE | Shared/L1 | KEEP |
| 9 | agent_runtime_adapter.py | 13KB | Agent运行时适配器(OSAI桥接) | 间接 | 无 | test_osai_boundary_audit.py | ACTIVE | System/L1 | KEEP(OSAI集成) |
| 10 | production_evidence_contract.py | 6KB | 生产证据契约 | 间接 | 无 | 无 | PARTIAL | Shared/L1 | REFACTOR(并入evidence_chain) |

### 领域9: 浏览器（8个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | browser_surface.py | 55KB | 浏览器表面层，统一浏览器操作API | 间接 | system/browser.html | test_browser_surface.py(13KB) | ACTIVE | System/L2 | KEEP |
| 2 | browser_surface_api.py | 13KB | 浏览器表面API端点 | 间接(lumenis_bp) | system/browser.html | test_browser_e2e.py | ACTIVE | System/L4 | KEEP |
| 3 | browser_discovery.py | 7KB | 浏览器发现，检测可用浏览器/CDP | 间接(app.py import) | system/browser.html | 无 | ACTIVE | System/L1 | KEEP |
| 4 | browser_runtime_api.py | 3KB | 浏览器运行时API(OSAI桥接) | 无(未注册) | 无 | test_browser_runtime_zbc_compliance.py | PARTIAL | System/L4 | REFACTOR(并入browser_surface_api) |
| 5 | internal_browser.py | 24KB | 内置浏览器，系统内浏览器管理 | 间接 | system/browser.html | test_internal_browser_recovery.py | ACTIVE | System/L2 | KEEP |
| 6 | internal_browser_adapter.py | 10KB | 内置浏览器适配器 | 间接 | 无 | 无 | PARTIAL | System/L2 | MERGE(并入internal_browser) |
| 7 | internal_browser_stream.py | 11KB | 内置浏览器流处理 | 间接 | 无 | 无 | PARTIAL | System/L2 | MERGE(并入internal_browser) |
| 8 | cdp_helper.py | 20KB | CDP辅助工具，Chrome DevTools Protocol | 间接 | system/browser.html | test_cdp_*.py | ACTIVE | System/L1 | KEEP |

### 领域10: 验收评估（10个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | acceptance_evidence_chain.py | 23KB | 验收证据链，CI/Functional状态分离 | 间接 | system/evaluation.html | test_acceptance_*.py(20KB) | ACTIVE | Shared/L1 | KEEP (E Shard交付) |
| 2 | acceptance_gate.py | 12KB | 验收门控 | 间接 | system/evaluation.html | test_acceptance_gate.py | ACTIVE | Shared/L1 | KEEP |
| 3 | evaluation_system.py | 20KB | 评估系统核心 | 间接(app.py import) | system/evaluation.html | test_evaluation_system.py(32KB) | ACTIVE | Shared/L1 | KEEP |
| 4 | evaluation_dimensions.py | 31KB | 评估维度定义 | 间接 | system/evaluation.html | 无直接测试 | ACTIVE | Shared/L1 | KEEP |
| 5 | evaluation_recorder.py | 15KB | 评估记录器 | 间接 | 无 | 无 | PARTIAL | Shared/L1 | REFACTOR(并入evaluation_system) |
| 6 | evaluation_runner.py | 10KB | 评估运行器 | 间接 | 无 | 无 | PARTIAL | Shared/L1 | REFACTOR(并入evaluation_system) |
| 7 | evidence_chain.py | 45KB | 证据链核心，操作证据/追溯 | 间接 | cth/evidence.html | test_evidence_chain.py(27KB) | ACTIVE | Shared/L1 | KEEP(权威实现) |
| 8 | evidence_store.py | 24KB | 证据存储 | 间接 | cth/evidence.html | test_evidence_store.py | ACTIVE | Shared/L0 | KEEP |
| 9 | evidence_api.py | 4KB | 证据API端点 | 无(未注册蓝图) | cth/evidence.html | test_evidence_export.py | PARTIAL | Shared/L4 | REFACTOR(注册到已有蓝图) |
| 10 | app_evidence.py | 17KB | 应用证据，应用级证据记录 | 间接(app.py import) | 无 | 无 | ACTIVE | Shared/L1 | KEEP |

### 领域11: 报告导出（8个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | report_api.py | 54KB | 报告API核心，日报/周报/月报端点 | report_bp(已注册) | cth/reports.html | test_report_audit.py(24KB) | ACTIVE | Shared/L4 | KEEP |
| 2 | report_engine.py | 18KB | 报告引擎核心 | 间接(app.py import) | cth/reports.html | test_report_periods.py | ACTIVE | Shared/L2 | KEEP |
| 3 | report_artifact.py | 11KB | 报告产物管理，哈希/版本 | 间接 | cth/reports.html | test_g4_report_artifact_hash.py | ACTIVE | Shared/L1 | KEEP |
| 4 | report_filter.py | 7KB | 报告过滤器 | 间接 | 无 | 无 | PARTIAL | Shared/L2 | REFACTOR(并入report_engine) |
| 5 | export_report.py | 37KB | 报告导出，PDF/Excel/Word | export_bp(已注册) | cth/reports.html | test_report_deprecation.py | ACTIVE | Shared/L4 | KEEP |
| 6 | weekly_events.py | 2KB | 周事件工具 | 无(工具) | 无 | 无 | DEAD | Shared/工具 | DELETE(一次性脚本) |
| 7 | v4_upgrade/report_center/ | 7个py | V4报告中心 | report_center_bp(已注册) | 无 | test_report_center_route.py | ACTIVE | Shared/L4 | KEEP |
| 8 | report_export/report_engine.py | 19KB | 报告导出引擎(旧版) | 无 | 无 | 无 | DEPRECATED | Shared/L2 | DELETE(被根目录report_engine替代) |

### 领域12: 双域隔离（6个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | api_dual_domain.py | 34KB | 双域API，ZBMP/CTH路由隔离 | 间接 | 无 | test_api_dual_domain.py | ACTIVE | Shared/L4 | KEEP |
| 2 | domain_adapter.py | 15KB | 域适配器，双域能力适配 | 间接 | 无 | test_domain_adapter.py | ACTIVE | Shared/L3 | KEEP |
| 3 | domain_isolation.py | 10KB | 域隔离，数据/规则/权限隔离 | 间接 | 无 | test_domain_context_switching.py | ACTIVE | Shared/L1 | KEEP |
| 4 | subject_context.py | 11KB | 主体上下文，品牌主体管理 | 间接 | 无 | test_subject_context_isolation.py | ACTIVE | Shared/L1 | KEEP |
| 5 | subject_classifier.py | 14KB | 主体分类器 | 间接 | 无 | test_subject_dual_dimension.py | ACTIVE | Shared/L1 | KEEP |
| 6 | subject_rules.py | 12KB | 主体规则，SUBJECT_WORDS/EXCLUDE/hit() | 间接(app.py import) | 无 | test_subject_redline.py | ACTIVE | Shared/L1 | KEEP(P0红线，禁止修改) |

### 领域13: 可视化（5个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | viz_api.py | 14KB | 可视化API端点 | viz_bp(已注册) | 全局图表 | test_viz_api.py(20KB) | ACTIVE | Shared/L4 | KEEP |
| 2 | viz_data_provider.py | 32KB | 可视化数据提供者 | 间接 | 全局图表 | test_xujing_viz_integration.py | ACTIVE | Shared/L1 | KEEP |
| 3 | ui_view_model.py | 33KB | UI视图模型，数据→视图映射 | 间接 | 全局 | test_ui_view_model.py(34KB) | ACTIVE | Shared/L5 | KEEP |
| 4 | adaptive_engine.py | 14KB | Adaptive UI引擎，Container Query/重排 | 间接 | 全局 | test_adaptive_engine.py | ACTIVE | Shared/L5 | KEEP (G Shard交付) |
| 5 | ui_data_audit.py | 6KB | UI数据审计 | 无 | 无 | 无 | PARTIAL | Shared/L5 | REFACTOR(并入ui_view_model) |

### 领域14: 其他（15个模块）

| # | 模块 | 大小 | 功能描述 | API注册 | 前端入口 | 测试覆盖 | 运行状态 | 域/层级 | 收敛分类 |
|---|------|------|----------|---------|----------|----------|----------|---------|----------|
| 1 | wechat_notifier.py | 50KB | 微信通知器(用户明确跳过) | 无 | 无 | test_wechat_notifier.py | PARTIAL | Shared/L2 | DEPRECATE(标记不激活) |
| 2 | learning_collector.py | 17KB | 学习采集器，AI反馈收集 | 间接 | 无 | 无 | PARTIAL | Shared/L2 | REFACTOR(并入ai_learning_engine) |
| 3 | learning_persistence.py | 9KB | 学习持久化 | 间接 | 无 | test_learning_persistence.py | ACTIVE | Shared/L0 | KEEP |
| 4 | human_correction.py | 8KB | 人工修正管理 | 间接 | 无 | test_human_correction.py(9KB) | ACTIVE | Shared/L2 | KEEP |
| 5 | review_workflow.py | 13KB | 审核工作流 | 间接 | 无 | 无 | PARTIAL | Shared/L2 | REFACTOR(并入human_correction) |
| 6 | function_registry.py | 29KB | 函数注册表，能力注册/发现 | 间接(app.py import) | system/skill_store.html | 无直接测试 | ACTIVE | Shared/L0 | KEEP |
| 7 | provider_registry.py | 7KB | Provider注册表，AI/采集Provider | 间接 | 无 | 无 | PARTIAL | Shared/L0 | REFACTOR(并入function_registry) |
| 8 | repository_registry.py | 9KB | 仓库注册表(根目录版) | 间接 | 无 | test_repository_registry.py(17KB) | ACTIVE | Shared/L0 | MERGE(权威版为core/) |
| 9 | skill_registry.py | 13KB | Skill注册表(根目录版) | 间接(app.py import) | system/skill_store.html | test_skill_system.py | ACTIVE | Shared/L0 | KEEP(权威实现) |
| 10 | skill_execution_chain.py | 19KB | Skill执行链 | 间接 | system/skill_store.html | test_skill_system.py | ACTIVE | Shared/L1 | KEEP |
| 11 | lumenis_agg_api.py | 20KB | LUMENIS聚合API | lumenis_bp(已注册) | lumenis/ | test_lumenis_*.py(多个) | ACTIVE | System/L4 | KEEP |
| 12 | lumenis_frontend.py | 25KB | LUMENIS前端路由 | lumenis_bp+domain_api_bp | lumenis/ | test_lumenis_frontend_foundation.py | ACTIVE | System/L5 | KEEP |
| 13 | lumenis_skill_adapter.py | 13KB | LUMENIS Skill适配器 | 间接 | system/skill_store.html | test_lumenis_skill_invoke.py | ACTIVE | System/L1 | KEEP |
| 14 | ci_cd.py | 13KB | CI/CD工具 | 无(工具) | 无 | 无 | PARTIAL | System/工具 | DEPRECATE(运维脚本) |
| 15 | code_quality_report.py | 21KB | 代码质量报告工具 | 无(工具) | 无 | test_code_quality.py(15KB) | PARTIAL | System/工具 | KEEP |

---

## 二、ZBC 子目录审计（18个目录，约250个py）

### 1. account/ (15个py) — 账号体系

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| api.py | 27KB | 账号API，account_bp+compat_bp(已注册) | ACTIVE | KEEP |
| models.py | 11KB | 账号数据模型 | ACTIVE | KEEP |
| service.py | 15KB | 账号服务层 | ACTIVE | KEEP |
| security.py | 8KB | 账号安全 | ACTIVE | KEEP |
| authorization.py | 5KB | 授权管理 | ACTIVE | KEEP |
| totp.py | 11KB | TOTP两步验证 | ACTIVE | KEEP |
| verification.py | 14KB | 验证管理 | ACTIVE | KEEP |
| workspace_keys.py | 7KB | 工作区密钥 | ACTIVE | KEEP |
| skills.py | 12KB | 账号Skill关联 | ACTIVE | KEEP |
| product_protection.py | 5KB | 产品保护 | ACTIVE | KEEP |
| nav_config.py | 5KB | 导航配置 | ACTIVE | KEEP |
| audit.py | 3KB | 账号审计 | PARTIAL | KEEP |
| compat.py | 3KB | 兼容性层 | ACTIVE | KEEP |
| __init__.py | 3KB | 包初始化 | ACTIVE | KEEP |

### 2. account_keepalive/ (2个py)

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| (2个py) | - | 账号保活 | PARTIAL | REFACTOR(并入account/) |

### 3. ad_intelligence/ (4个py) — 广告智能

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| base.py | 4KB | 广告智能基础 | ACTIVE | KEEP |
| platform_registry.py | 15KB | 广告平台注册(4平台+CTR+特征+策略) | ACTIVE | KEEP |
| permission_gate.py | 6KB | 广告域专用权限门(Domain-Specific) | ACTIVE | KEEP(域专用，不合并全局) |
| __init__.py | 1KB | 包初始化 | ACTIVE | KEEP |

### 4. browser_runtime/ (4个py)

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| contract.py | 10KB | 浏览器运行时契约 | ACTIVE | KEEP |
| policy.py | 8KB | 浏览器运行时策略 | ACTIVE | KEEP |
| router.py | 4KB | 浏览器运行时路由 | PARTIAL | REFACTOR(并入browser_surface) |
| __init__.py | 1KB | 包初始化 | ACTIVE | KEEP |

### 5. collector_guard/ (15个py) — 采集守护

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| guard.py | 7KB | 采集守护核心 | ACTIVE | KEEP |
| risk_engine.py | 15KB | 采集风险引擎(域专用) | ACTIVE | KEEP(域专用) |
| task_queue.py | 9KB | 任务队列 | ACTIVE | KEEP |
| metrics.py | 7KB | 采集指标 | ACTIVE | KEEP |
| rate_limiter.py | 6KB | 速率限制 | ACTIVE | KEEP |
| dlq_replay.py | 6KB | 死信队列重放 | ACTIVE | KEEP |
| schedule_adapter.py | 5KB | 调度适配器 | ACTIVE | KEEP |
| resource_guard.py | 5KB | 资源守护 | ACTIVE | KEEP |
| analyzer.py | 5KB | 采集分析器 | ACTIVE | KEEP |
| queue_worker.py | 3KB | 队列工作器 | ACTIVE | KEEP |
| runtime_switch.py | 5KB | 运行时切换 | ACTIVE | KEEP |
| checkpoint.py | 3KB | 检查点 | ACTIVE | KEEP |
| state.py | 2KB | 状态管理 | ACTIVE | KEEP |
| runtime_guardian.py | 3KB | 运行时守护(简化版，基于队列) | ACTIVE | MERGE(改为import根目录权威版) |
| __init__.py | 1KB | 包初始化 | ACTIVE | KEEP |

### 6. collector_v2/ (7个py) — 采集器V2

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| official_info_scraper.py | 25KB | 官方信息采集器 | ACTIVE | KEEP |
| browser_session.py | 6KB | 浏览器会话管理 | ACTIVE | KEEP |
| base.py | 3KB | V2基础类 | ACTIVE | KEEP |
| run_profile.py | 3KB | 运行配置 | PARTIAL | KEEP |
| run_live_engine.py | 2KB | 实时引擎运行 | PARTIAL | KEEP |
| run_xhs_live.py | 1KB | 小红书实时运行 | PARTIAL | KEEP |
| __init__.py | 0.4KB | 包初始化 | ACTIVE | KEEP |

### 7. intelligence_library/ (61个py) — 情报库

| 状态 | 说明 |
|------|------|
| ACTIVE | 情报库核心，多平台情报聚合/检索/分析 |
| 收敛分类 | KEEP(整体保留，intelligence_library_bp已注册) |

### 8. platform_adapters/ (32个py + scheduling/ 7个) — 全平台适配器(F Shard交付)

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| platform_naming.py | 35KB | 平台命名规范(数据字典核心) | ACTIVE | KEEP (F Shard) |
| safe_collection.py | 14KB | 安全采集契约 | ACTIVE | KEEP |
| base.py | 4KB | 适配器基类 | ACTIVE | KEEP |
| xhs.py | 4KB | 小红书适配器 | ACTIVE | KEEP |
| weibo.py | 7KB | 微博适配器 | ACTIVE | KEEP |
| bilibili.py | 7KB | B站适配器 | ACTIVE | KEEP |
| douyin.py | 7KB | 抖音适配器 | ACTIVE | KEEP |
| zhihu.py | 6KB | 知乎适配器 | ACTIVE | KEEP |
| instagram.py | 11KB | Instagram适配器 | ACTIVE | KEEP |
| facebook.py | 6KB | Facebook适配器 | ACTIVE | KEEP |
| x_platform.py | 5KB | X(Twitter)适配器 | ACTIVE | KEEP |
| youtube.py | 2KB | YouTube适配器 | PARTIAL | KEEP |
| tiktok.py | 2KB | TikTok适配器 | PARTIAL | KEEP |
| reddit.py | 2KB | Reddit适配器 | PARTIAL | KEEP |
| linkedin.py | 2KB | LinkedIn适配器 | PARTIAL | KEEP |
| github.py | 3KB | GitHub适配器 | PARTIAL | KEEP |
| channels.py | 2KB | 渠道管理 | ACTIVE | KEEP |
| config.py | 4KB | 适配器配置 | ACTIVE | KEEP |
| registry.py | 1KB | 适配器注册表 | ACTIVE | KEEP |
| multi_platform_import.py | 7KB | 多平台导入 | ACTIVE | KEEP |
| evidence_exporter.py | 9KB | 证据导出 | ACTIVE | KEEP |
| health_center.py | 9KB | 健康中心 | ACTIVE | KEEP |
| rednote_policy.py | 7KB | 小红书策略 | ACTIVE | KEEP |
| xhs_app_topic.py | 9KB | 小红书APP话题 | ACTIVE | KEEP |
| scheduling/ (7个) | - | 调度子系统 | ACTIVE | KEEP |

### 9. podcast/ (0个py顶层，9个py在子目录)

| 状态 | 说明 |
|------|------|
| ACTIVE | 播客模块，podcast_routes动态注册，zbmp/podcast.html |
| 收敛分类 | KEEP |

### 10. proxy_pool/ (7个py) — 代理池

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| manager.py | 6KB | 代理池管理 | ACTIVE | KEEP |
| loader.py | 2KB | 代理加载 | ACTIVE | KEEP |
| config.py | 2KB | 代理配置 | ACTIVE | KEEP |
| models.py | 2KB | 代理模型 | ACTIVE | KEEP |
| health.py | 1KB | 代理健康检查 | ACTIVE | KEEP |
| adapters.py | 1KB | 代理适配器 | ACTIVE | KEEP |
| __init__.py | 1KB | 包初始化 | ACTIVE | KEEP |

### 11. v4_upgrade/ (65个py) — V4升级

| 子模块 | 文件数 | 功能 | 状态 | 收敛分类 |
|--------|--------|------|------|----------|
| adapters/ | 27 | V4平台适配器(18平台搜索采集) | ACTIVE | KEEP |
| report_center/ | 7 | V4报告中心(report_center_bp已注册) | ACTIVE | KEEP |
| ai_hub/ | 4 | V4 AI中心 | ACTIVE | KEEP |
| auth/ | 6 | V4认证 | ACTIVE | KEEP |
| importer/ | 4 | V4导入器 | ACTIVE | KEEP |
| version_center/ | 4 | V4版本中心 | ACTIVE | KEEP |
| data_cleanup/ | 2 | V4数据清理 | PARTIAL | KEEP |
| collect/ | 2 | V4采集 | ACTIVE | KEEP |
| console/ | 2 | V4控制台 | PARTIAL | KEEP |
| settings/ | 2 | V4设置 | ACTIVE | KEEP |
| blueprint.py | 17KB | V4蓝图(create_v4_blueprint已注册) | ACTIVE | KEEP |
| config.py | 4KB | V4配置 | ACTIVE | KEEP |
| global_bil.py | 2KB | 全局BIL | ACTIVE | KEEP |
| unified_logger.py | 7KB | 统一日志 | ACTIVE | KEEP |

### 12. vendor/ (47个py，顶层为空，在子目录)

| 状态 | 说明 |
|------|------|
| PARTIAL | 第三方依赖/供应商模块 |
| 收敛分类 | KEEP(按需保留) |

### 13. scripts/ (88个py) — 工具脚本

| 分类 | 代表模块 | 状态 | 收敛分类 |
|------|----------|------|----------|
| 内容生成 | idea_generator.py(58KB), video_script.py, pitch_parser.py | ACTIVE | KEEP(H Shard) |
| 数据迁移 | migrate_historical_data.py(39KB), init_database_data.py | ACTIVE | KEEP |
| 营销日历 | marketing_calendar.py(32KB) | ACTIVE | KEEP |
| 运维工具 | backup_db.py, daily_git_sync.py, start_resident_browsers.py | ACTIVE | KEEP |
| 一次性脚本 | p1c_part*.py, _*.py(多个下划线前缀) | DEAD | DELETE(一次性/调试脚本) |
| 审计工具 | osai_module_graph_shardB.py, production_baseline_check.py | PARTIAL | KEEP |

### 14. core/ (2个py)

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| repository_registry.py | 11KB | 仓库注册表(权威实现) | ACTIVE | KEEP(权威版，根目录版改为import) |
| __init__.py | 1KB | 包初始化 | ACTIVE | KEEP |

### 15. report_export/ (2个py)

| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| report_engine.py | 19KB | 报告导出引擎(旧版) | DEPRECATED | DELETE(被根目录report_engine替代) |
| app_report_api_patch.py | 1KB | API补丁 | DEAD | DELETE(一次性补丁) |

### 16. 00-GOVERNANCE/ (36个py) — 治理文档/脚本

| 状态 | 说明 |
|------|------|
| ACTIVE | 项目治理脚本/文档生成器 |
| 收敛分类 | KEEP |

### 17. 08-AUDIT/ (1个py) + audit/ (40个py) — 审计目录

| 状态 | 说明 |
|------|------|
| ACTIVE | 审计脚本/报告 |
| 收敛分类 | KEEP(本任务输出也在此) |

### 18. 其他目录(alembic/backups/contracts/data/deployment/docs/evaluation/migrations/nodejs)

| 目录 | 说明 | 收敛分类 |
|------|------|----------|
| alembic/ | 数据库迁移 | KEEP |
| backups/ | 备份 | KEEP |
| contracts/ | 契约定义 | KEEP |
| data/ | 数据文件(含monitor.db 125表) | KEEP(P0禁止删除) |
| deployment/ | 部署配置 | KEEP |
| docs/ | 文档 | KEEP |
| evaluation/ | 评估 | KEEP |
| migrations/ | 迁移 | KEEP |
| nodejs/ | Node.js工具(58个py) | KEEP |

---

## 三、ZBC 前端审计（44个HTML页面 + 25个JS + 8个CSS）

### HTML页面（44个，非33个）

#### ZBMP域 (11个)
| 页面 | 大小 | API绑定 | Adaptive UI | 状态 | 收敛分类 |
|------|------|---------|-------------|------|----------|
| zbmp/overview.html | 43KB | /api/zbmp/* | 已接入base.html | ACTIVE | KEEP |
| zbmp/brand.html | 23KB | /api/zbmp/brand | 已接入 | ACTIVE | KEEP |
| zbmp/competition.html | 22KB | /api/zbmp/competition | 已接入 | ACTIVE | KEEP |
| zbmp/content.html | 31KB | /api/zbmp/content | 已接入 | ACTIVE | KEEP(H Shard激活中) |
| zbmp/kos.html | 32KB | /api/kos/* | 已接入 | ACTIVE | KEEP |
| zbmp/reports.html | 24KB | /api/report/* | 已接入 | ACTIVE | KEEP |
| zbmp/risk.html | 23KB | /api/zbmp/risk | 已接入 | ACTIVE | KEEP |
| zbmp/podcast.html | 18KB | /api/podcast/* | 已接入 | ACTIVE | KEEP |
| zbmp/evaluation.html | 5KB | /api/evaluation | 已接入 | PARTIAL | REFACTOR(内容较少) |
| zbmp/intelligence.html | 5KB | /api/intelligence | 已接入 | PARTIAL | REFACTOR(内容较少) |
| zbmp/launch.html | 6KB | 启动页 | 已接入 | ACTIVE | KEEP |

#### CTH域 (10个)
| 页面 | 大小 | API绑定 | Adaptive UI | 状态 | 收敛分类 |
|------|------|---------|-------------|------|----------|
| cth/overview.html | 37KB | /api/cth/* | 已接入 | ACTIVE | KEEP |
| cth/xiaohongshu.html | 37KB | /api/cth/xhs | 已接入 | ACTIVE | KEEP |
| cth/realtime.html | 22KB | /api/cth/realtime | 已接入 | ACTIVE | KEEP |
| cth/events.html | 21KB | /api/cth/events | 已接入 | ACTIVE | KEEP |
| cth/reports.html | 25KB | /api/report/* | 已接入 | ACTIVE | KEEP |
| cth/risk.html | 26KB | /api/cth/risk | 已接入 | ACTIVE | KEEP |
| cth/evidence.html | 5KB | /api/evidence | 已接入 | PARTIAL | REFACTOR(内容较少) |
| cth/brands.html | 5KB | /api/cth/brands | 已接入 | PARTIAL | REFACTOR(内容较少) |
| cth/industries.html | 5KB | /api/cth/industries | 已接入 | PARTIAL | REFACTOR(内容较少) |
| cth/kos.html | 5KB | /api/kos/* | 已接入 | PARTIAL | REFACTOR(内容较少) |
| cth/launch.html | 6KB | 启动页 | 已接入 | ACTIVE | KEEP |
| cth/data_center/index.html | 7KB | /api/data-center/* | 已接入 | ACTIVE | KEEP(F Shard) |
| cth/data_center/platform.html | 10KB | /api/data-center/* | 已接入 | ACTIVE | KEEP(F Shard) |

#### System域 (11个)
| 页面 | 大小 | API绑定 | Adaptive UI | 状态 | 收敛分类 |
|------|------|---------|-------------|------|----------|
| system/ai.html | 36KB | /api/system/ai | 已接入 | ACTIVE | KEEP |
| system/browser.html | 34KB | /api/system/browser | 已接入 | ACTIVE | KEEP |
| system/collector.html | 23KB | /api/collector-status | 已接入 | ACTIVE | KEEP |
| system/database.html | 18KB | /api/system/db | 已接入 | ACTIVE | KEEP |
| system/evaluation.html | 12KB | /api/evaluation | 已接入 | ACTIVE | KEEP |
| system/runtime.html | 23KB | /api/system/runtime | 已接入 | ACTIVE | KEEP |
| system/security.html | 21KB | /api/system/security | 已接入 | ACTIVE | KEEP |
| system/settings.html | 70KB | /api/settings | 已接入 | ACTIVE | KEEP |
| system/skill_store.html | 11KB | /api/skills | 已接入 | ACTIVE | KEEP |
| system/adaptive_demo.html | 14KB | Adaptive演示 | 已接入 | ACTIVE | KEEP(G Shard) |

#### Auth域 (3个)
| 页面 | 大小 | API绑定 | 状态 | 收敛分类 |
|------|------|---------|------|----------|
| auth/zbmp_login.html | 10KB | /api/auth | ACTIVE | KEEP |
| auth/cth_login.html | 6KB | /api/auth | ACTIVE | KEEP |
| auth_recovery_modal.html | 14KB | /api/auth-recovery | ACTIVE | KEEP |

#### 基础模板 (2个)
| 页面 | 大小 | 说明 | 收敛分类 |
|------|------|------|----------|
| base.html | 22KB | 基础模板(adaptive-engine.js已接入) | KEEP |
| (lumenis/路由由lumenis_frontend.py动态渲染) | - | LUMENIS前端 | KEEP |

### JS文件（25个）
| 文件 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| adaptive-engine.js | 14KB | Adaptive UI引擎(G Shard) | ACTIVE | KEEP |
| adaptive-motion.js | 14KB | Adaptive Motion(G Shard) | ACTIVE | KEEP |
| lumenis-global-design.css相关 | - | 设计系统(A Shard) | ACTIVE | KEEP |
| lumenis-core.js | 9KB | LUMENIS核心 | ACTIVE | KEEP |
| lumenis-data.js | 15KB | LUMENIS数据 | ACTIVE | KEEP |
| lumenis-motion-engine.js | 16KB | LUMENIS Motion(A Shard) | ACTIVE | KEEP |
| lumenis-icons.js | 6KB | LUMENIS图标 | ACTIVE | KEEP |
| browser.js | 39KB | 浏览器交互 | ACTIVE | KEEP |
| feature-modules.js | 36KB | 功能模块 | ACTIVE | KEEP |
| settings.js | 59KB | 设置页交互 | ACTIVE | KEEP |
| zbmp-entry.js | 25KB | ZBMP入口 | ACTIVE | KEEP |
| zbmp-podcast.js | 27KB | 播客交互 | ACTIVE | KEEP |
| ai-assistant.js | 18KB | AI助手 | ACTIVE | KEEP |
| domain-context.js | 15KB | 域上下文 | ACTIVE | KEEP |
| i18n.js | 11KB | 国际化 | ACTIVE | KEEP |
| xujing-viz.js | 16KB | 可视化 | ACTIVE | KEEP |
| skill-store.js | 11KB | Skill商店 | ACTIVE | KEEP |
| badge-manager.js | 8KB | 徽章管理 | ACTIVE | KEEP |
| carousel.js | 8KB | 轮播 | ACTIVE | KEEP |
| keyboard-shortcuts.js | 15KB | 快捷键 | ACTIVE | KEEP |
| settings-dropdown.js | 8KB | 设置下拉 | ACTIVE | KEEP |
| settings-keyboard.js | 5KB | 设置键盘 | ACTIVE | KEEP |
| skill-home.js | 2KB | Skill首页 | PARTIAL | KEEP |
| terminology.js | 4KB | 术语表 | ACTIVE | KEEP |

### CSS文件（8个）
| 文件 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| lumenis-global-design.css | 21KB | 全局设计(A Shard) | ACTIVE | KEEP |
| adaptive-layout.css | 20KB | Adaptive布局(G Shard) | ACTIVE | KEEP |
| adaptive-components.css | 17KB | Adaptive组件(G Shard) | ACTIVE | KEEP |
| zbc-design-v1.1.css | 45KB | ZBC设计v1.1 | ACTIVE | KEEP |
| zbc-layout-v1.1.css | 21KB | ZBC布局v1.1 | ACTIVE | KEEP |
| xujing-core.css | 24KB | 旭景核心样式 | ACTIVE | KEEP |
| fonts/fonts.css | 18KB | 字体 | ACTIVE | KEEP |
| fonts/google-fonts.css | 457KB | Google字体 | ACTIVE | KEEP |

---

## 四、OSAI 审计（osai_engine/ 55个py + components/ 17个py）

### osai_engine/ 核心模块（55个）

#### Agent体系 (5个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| orchestrator.py | 24KB | Agent编排器 | agent_runtime_adapter桥接 | ACTIVE | KEEP |
| agent.py | 8KB | Agent核心 | 桥接 | ACTIVE | KEEP |
| agent_identity.py | 8KB | Agent身份 | 桥接 | ACTIVE | KEEP |
| agent_integration.py | 10KB | Agent集成 | 桥接 | ACTIVE | KEEP |
| engineering_loop.py | 8KB | 工程循环 | 桥接 | ACTIVE | KEEP |

#### Skill体系 (9个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| skill_invocation.py | 19KB | Skill调用 | lumenis_skill_adapter | ACTIVE | KEEP |
| skill_manifest.py | 12KB | Skill清单 | 桥接 | ACTIVE | KEEP |
| skill_registry.py | 7KB | Skill注册表(OSAI版) | 与ZBC skill_registry并存 | ACTIVE | MERGE(ZBC为权威，OSAI改为import) |
| canonical_skill_registry.py | 7KB | 规范Skill注册表 | 桥接 | ACTIVE | KEEP |
| skill_selector.py | 9KB | Skill选择器 | 桥接 | ACTIVE | KEEP |
| skill_execution_contract.py | 8KB | Skill执行契约 | 桥接 | ACTIVE | KEEP |
| skill_sync.py | 10KB | Skill同步 | 桥接 | ACTIVE | KEEP |
| skills/source_skills.py | 17KB | 源Skill | 桥接 | ACTIVE | KEEP |
| skills/__init__.py | 1KB | 包初始化 | - | ACTIVE | KEEP |

#### AI体系 (3个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| ai_gateway.py | 5KB | AI网关 | ai_channel桥接 | ACTIVE | KEEP |
| llm.py | 3KB | LLM客户端 | local_ai_client/ark_llm桥接 | ACTIVE | KEEP |
| config.py | 1KB | 配置 | - | ACTIVE | KEEP |

#### 权限安全 (8个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| permission_gate.py | 7KB | 权限门(OSAI版) | ZBC permission_gate为权威 | ACTIVE | MERGE(改为import ZBC权威版) |
| permission_contract.py | 4KB | 权限契约 | 桥接 | ACTIVE | KEEP |
| action_firewall.py | 5KB | 动作防火墙 | p2_action_firewall桥接 | ACTIVE | KEEP |
| effect_fence.py | 6KB | 效果围栏 | 桥接 | ACTIVE | KEEP |
| obo_jit.py | 7KB | OBO JIT权限 | 桥接 | ACTIVE | KEEP |
| delegation.py | 10KB | 委托权限 | 桥接 | ACTIVE | KEEP |
| release_safety.py | 5KB | 发布安全 | 桥接 | ACTIVE | KEEP |
| runtime_contract.py | 3KB | 运行时契约 | 桥接 | ACTIVE | KEEP |

#### 运行时 (8个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| engine_runtime.py | 17KB | 引擎运行时 | runtime_guardian桥接 | ACTIVE | KEEP |
| engine_layer.py | 9KB | 引擎层 | 桥接 | ACTIVE | KEEP |
| harness_runtime.py | 11KB | Harness运行时 | 桥接 | ACTIVE | KEEP |
| runtime_guardian.py | 6KB | 运行时守护(OSAI版) | ZBC为权威(51KB) | ACTIVE | MERGE(改为import ZBC权威版) |
| checkpoint_resume.py | 5KB | 检查点恢复 | 桥接 | ACTIVE | KEEP |
| context_runtime.py | 11KB | 上下文运行时 | 桥接 | ACTIVE | KEEP |
| observability.py | 11KB | 可观测性 | 桥接 | ACTIVE | KEEP |
| rules.py | 3KB | 规则 | 桥接 | ACTIVE | KEEP |

#### 数据 (4个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| canonical_data.py | 8KB | 规范数据(OSAI版) | ZBC canonical_data为权威(43KB) | ACTIVE | MERGE(改为import ZBC权威版) |
| capability_registry.py | 19KB | 能力注册表 | 与ZBC function_registry(29KB)并存 | ACTIVE | MERGE(ZBC function_registry为权威) |
| repository_registry.py | 5KB | 仓库注册表(OSAI版) | ZBC core/为权威 | ACTIVE | MERGE(改为import ZBC权威版) |
| repository_contract.py | 3KB | 仓库契约 | 桥接 | ACTIVE | KEEP |
| contract_persistence.py | 5KB | 契约持久化 | 桥接 | ACTIVE | KEEP |

#### Evidence (4个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| evidence_chain.py | 8KB | 证据链(OSAI版) | ZBC evidence_chain为权威(45KB) | ACTIVE | MERGE(改为import ZBC权威版) |
| evidence.py | 2KB | 证据基础 | 桥接 | ACTIVE | KEEP |
| evidence_graph.py | 5KB | 证据图谱 | 桥接 | ACTIVE | KEEP |
| (ZBC acceptance_evidence_chain) | 23KB | 验收证据链 | E Shard交付 | ACTIVE | KEEP |

#### Evaluation (2个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| evaluation_contract.py | 4KB | 评估契约 | 桥接 | ACTIVE | KEEP |
| trace_evaluation.py | 5KB | 追踪评估 | 桥接 | ACTIVE | KEEP |

#### 浏览器 (2个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| browser_capability.py | 10KB | 浏览器能力 | browser_surface桥接 | ACTIVE | KEEP |
| browser_executor.py | 9KB | 浏览器执行器 | ai_browser_runtime桥接 | ACTIVE | KEEP |

#### 研究 (2个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| research.py | 4KB | 研究基础 | intelligence_library桥接 | ACTIVE | KEEP |
| research_pipeline.py | 11KB | 研究管道 | 桥接 | ACTIVE | KEEP |

#### 其他 (10个)
| 模块 | 大小 | 功能 | ZBC集成 | 状态 | 收敛分类 |
|------|------|------|----------|------|----------|
| decision_action_outcome.py | 6KB | 决策-动作-结果 | 桥接 | ACTIVE | KEEP |
| impact_analysis.py | 6KB | 影响分析 | 桥接 | ACTIVE | KEEP |
| learning_record_contract.py | 4KB | 学习记录契约 | learning_persistence桥接 | ACTIVE | KEEP |
| lifecycle_contract.py | 3KB | 生命周期契约 | 桥接 | ACTIVE | KEEP |
| memory_lifecycle.py | 4KB | 内存生命周期 | 桥接 | ACTIVE | KEEP |
| task_contract.py | 4KB | 任务契约 | ai_task_engine桥接 | ACTIVE | KEEP |
| tools.py | 4KB | 工具 | 桥接 | ACTIVE | KEEP |
| trace_contract.py | 4KB | 追踪契约 | ai_call_logger桥接 | ACTIVE | KEEP |
| ui_state_contract.py | 4KB | UI状态契约 | ui_view_model桥接 | ACTIVE | KEEP |
| __init__.py | 3KB | 包初始化 | - | ACTIVE | KEEP |

### components/ (17个py)

#### AI-Development-Research-Hub/ (9个py + tests 7个)
| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| contracts/research_record.py | 10KB | 研究记录契约 | ACTIVE | KEEP |
| contracts/safe_collection.py | 16KB | 安全采集契约 | ACTIVE | KEEP |
| shared/capability_registry.py | 6KB | 能力注册表(组件版) | ACTIVE | MERGE(OSAI capability_registry为权威) |
| shared/shadow_lifecycle.py | 4KB | 影子生命周期 | ACTIVE | KEEP |
| adapters/ddc_research_adapter.py | 2KB | DDC研究适配器 | ACTIVE | KEEP |
| tools/research_id.py | 3KB | 研究ID工具 | ACTIVE | KEEP |
| tools/runtime_preflight.py | 7KB | 运行时预检(组件版) | ACTIVE | MERGE(ZBC runtime_preflight为权威) |
| tools/secret_scan.py | 3KB | 密钥扫描 | ACTIVE | KEEP |
| tests/ (7个) | - | 组件测试 | ACTIVE | KEEP |

#### Development-Command-Console/ (6个py + tests 5个)
| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| tools/research_learning.py | 10KB | 研究学习 | ACTIVE | KEEP |
| tools/learning_promote.py | 8KB | 学习提升 | ACTIVE | KEEP |
| tools/platform_inspection.py | 6KB | 平台检查 | ACTIVE | KEEP |
| tools/capability_delta.py | 6KB | 能力增量 | ACTIVE | KEEP |
| tools/learning_cycle.py | 4KB | 学习循环 | ACTIVE | KEEP |
| tools/research_registry.py | 2KB | 研究注册表 | ACTIVE | KEEP |
| tests/ (5个) | - | 控制台测试 | ACTIVE | KEEP |

#### SICI-Core/ (3个py)
| 模块 | 大小 | 功能 | 状态 | 收敛分类 |
|------|------|------|------|----------|
| upgrade_modules/base_adapter_enhanced.py | 14KB | 基础适配器增强 | ACTIVE | KEEP |
| upgrade_modules/dual_pool.py | 15KB | 双池 | ACTIVE | KEEP |
| upgrade_modules/unified_logger.py | 6KB | 统一日志 | ACTIVE | MERGE(v4_upgrade/unified_logger为权威) |
| shadow_run/ (2个测试) | - | 影子运行测试 | ACTIVE | KEEP |

---

## 五、统计汇总

### ZBC根目录模块收敛分类统计
| 分类 | 数量 | 占比 |
|------|------|------|
| KEEP | ~130 | 72% |
| MERGE | ~18 | 10% |
| REFACTOR | ~16 | 9% |
| DEPRECATE | ~5 | 3% |
| DELETE | ~8 | 4% |
| UNKNOWN | ~3 | 2% |

### 重复模块权威实现确认
| 功能 | 权威实现 | 待合并版本 |
|------|----------|------------|
| runtime_guardian | 根目录runtime_guardian.py(51KB) | collector_guard/(3KB), osai_engine/(6KB) |
| permission_gate | 根目录permission_gate.py(44KB) | ad_intelligence/(6KB,域专用保留), osai_engine/(7KB) |
| evidence_chain | 根目录evidence_chain.py(45KB) | osai_engine/(8KB) |
| repository_registry | core/repository_registry.py(11KB) | 根目录/(9KB), osai_engine/(5KB) |
| skill_registry | 根目录skill_registry.py(13KB) | osai_engine/(7KB) |
| canonical_data | 根目录canonical_data.py(43KB) | osai_engine/(8KB) |
| report_engine | 根目录report_engine.py(18KB) | report_export/(19KB,旧版) |
| capability/function_registry | 根目录function_registry.py(29KB) | osai_engine/capability_registry(19KB) |

### 确认删除清单(无依赖)
| 模块 | 原因 | Dependency Trace |
|------|------|-----------------|
| web_monitor.py | 被web_monitor_v570.py替代 | app.py已import v570 |
| check_collection.py | 一次性脚本 | 无import/API/前端/测试引用 |
| check_collection_detail.py | 一次性脚本 | 无引用 |
| monitor_pipeline.py | 空壳脚本 | 无引用 |
| weekly_events.py | 一次性脚本 | 无引用 |
| migrate_notes_time_fields.py | 一次性迁移 | 无引用 |
| report_export/report_engine.py | 旧版被替代 | 无引用 |
| report_export/app_report_api_patch.py | 一次性补丁 | 无引用 |
| scripts/_*.py(多个下划线前缀) | 调试/一次性脚本 | 需逐个确认 |
| zbc_phase11_audit.py | 一次性审计脚本 | 仅自引用 |

### API蓝图注册状态(22个已注册)
| 蓝图 | 来源模块 | 状态 |
|------|----------|------|
| system_health_bp | system_health_api.py | ACTIVE |
| architecture_bp | architecture_api.py | ACTIVE |
| badge_bp | badge_api.py | ACTIVE |
| system_ai_bp | system_ai_data_api.py | ACTIVE |
| settings_bp | settings_module.py | ACTIVE |
| export_bp | export_report.py | ACTIVE |
| pr_case_bp | pr_case_integration.py | ACTIVE |
| system_features_bp | system_features_api.py | ACTIVE |
| auth_recovery_bp | auth_recovery_api.py | ACTIVE |
| report_bp | report_api.py | ACTIVE |
| viz_bp | viz_api.py | ACTIVE |
| data_center_bp | data_center_api.py | ACTIVE |
| intelligence_library_bp | intelligence_library_api.py | ACTIVE |
| collector_status_bp | collector_status_api.py | ACTIVE |
| lumenis_bp | lumenis_frontend.py | ACTIVE |
| domain_api_bp | lumenis_frontend.py | ACTIVE |
| v4 blueprint | v4_upgrade/create_v4_blueprint | ACTIVE |
| account_bp | account/api.py | ACTIVE |
| compat_bp | account/compat.py | ACTIVE |
| report_center_bp | v4_upgrade/report_center | ACTIVE |
| kos_routes(动态) | kos_routes.py | ACTIVE |
| ic_routes(动态) | ic_routes.py | ACTIVE |
| podcast_routes(动态) | podcast_routes.py | ACTIVE |

### 未注册API的模块(需补注册或标记DEPRECATED)
| 模块 | 建议 |
|------|------|
| data_query_api.py | 并入data_center_api |
| browser_runtime_api.py | 并入browser_surface_api |
| evidence_api.py | 注册到lumenis_bp或新建evidence_bp |
| content_generation.py | H Shard处理中，归入lumenis_bp或content_bp |

---

*审计状态: PARTIAL (Inventory完成，收敛执行进行中)*
*下一步: 执行CONVERGENCE_PLAN中的MERGE和DELETE操作*
