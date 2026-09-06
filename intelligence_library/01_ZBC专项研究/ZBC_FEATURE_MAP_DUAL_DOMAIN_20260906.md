# ZBC 功能映射表 - 双域隔离（团队盘点，2026-09-06）

> 来源：执行团队 lumenis-dual-domain-v3 @ 8ae4d3f 分支盘点
> 盘点范围：线上main + 本地feat全部源码（130+根模块 + 170+子包模块 + 62张表 + 150+API路由 + 20个前端页面）
> 用途：完整功能地图，防止遗漏；与 ZBC_FEATURE_GAP_AUDIT_20260906.md 合并使用

---

## 汇总统计

| 类别 | 总数 | 已接入 | 部分接入 | 需新建 |
|---|---|---|---|---|
| 根目录核心模块 | 130+ | ~90 | ~35 | ~5 |
| 子包模块 | 170+ | ~100 | ~60 | ~10 |
| API路由 | 150+ | 150 | 0 | 3个域前缀 |
| 前端页面 | 20 | 20 | 0 | 3个(ZBMP/CTH Dashboard+切换器) |
| 数据库表 | 62 | 60 | 2 | 0 |
| **合计** | **530+** | **420 (79%)** | **97 (18%)** | **18 (3%)** |

---

## 关键"已存在未用"清单（必须接入）

| 模块 | 问题 | 优先级 |
|---|---|---|
| ui_view_model.py (32KB) | 零外部调用，函数驱动动态可视化未接入 | **P0** |
| runtime_guardian.py (46.5KB) | 零外部调用，Worker/Lease/Heartbeat未接入采集 | **P0** |
| permission_gate.py (38.9KB) | 仅2处调用，写操作未全面接入 | **P0** |
| /api/zbmp/* /api/cth/* /api/system/* | 域前缀API不存在 | **P0** |
| ZBMP Dashboard / CTH Dashboard | 双域独立Dashboard不存在 | **P0** |
| 产品切换器 | ZBMP↔CTH切换不存在 | **P0** |
| ai_channel.py CircuitBreaker | 与runtime_guardian重复 | P1 |
| safety_boundary.py | 与security_boundary.py重复 | P1 |
| collector_v2/ (25模块) | 部分未接入主链路 | P1 |
| kos_metrics.py / kos_attribution.py | 固定公式需改为平台规则驱动 | P1 |
| v4_upgrade/ (64模块) | 大量平台采集器未接入主链路 | P2 |

---

## 需新建清单

| 模块 | 域 | 说明 |
|---|---|---|
| 竞品/竞争模块 | ZBMP | 需从brand-industry扩展 |
| 品牌增长模块 | ZBMP | 需新建 |
| ZBMP风险策略 | ZBMP | 需新建 |
| /api/zbmp/* 域前缀API | ZBMP | 需新建 |
| /api/cth/* 域前缀API | CTH | 需新建 |
| /api/system/* 域前缀API | System | 需新建 |
| ZBMP Dashboard | ZBMP | 双域独立Dashboard |
| CTH Dashboard | CTH | 双域独立Dashboard |
| 产品切换器 ZBMP↔CTH | Shared | 切换时重载Domain Context |

---

## 部分接入需完善清单（P1/P2）

### 采集层
- collector_v2/ (25模块, 130KB) — 部分未接入主链路
- platform_adapters/ (24模块, 150KB) — 部分未接入
- v4_upgrade/ (64模块, 500KB) — 大量平台采集器未接入主链路
- weibo_login_manager.py / bilibili_login_manager.py — 部分接入

### 数据层
- data_quality_gate.py (9.3KB) — 部分接入
- schema_registry.py (6.9KB) — 部分接入
- function_registry.py (9.3KB) — 部分接入

### ZBMP域
- brand_knowledge_base.py (8.2KB) — 部分接入
- brand_stats_recompute.py (5.9KB) — 部分接入
- brand_report_generator.py (18KB) — 部分接入
- ad_intelligence/ (17模块, 100KB) — 部分接入（4平台API待实现）
- pr_case_integration.py (24.4KB) / pr_case_engine.py (10.7KB) — 部分接入

### AI层
- ai_learning_engine.py (18.8KB) — 部分接入
- ark_llm.py (13.6KB) — Legacy

### Risk层
- v4_upgrade/risk_controller.py (10.3KB) — 部分接入

### Report层
- v4_upgrade/report_generator.py (22.1KB) — 部分接入

### KOS层
- kos_metrics.py (16.3KB) — 固定公式需改平台规则驱动
- kos_attribution.py (8.4KB) — 固定公式需改

### Runtime层
- runtime_guardian.py (46.5KB) — 零外部调用，P0

### Security层
- security_boundary.py (44.3KB) — 部分接入
- safety_boundary.py (19.1KB) — 重复需收敛
- v4_upgrade/security.py (5.1KB) — 部分接入

### Skill/Agent层
- agent_runtime_adapter.py (13KB) — 部分接入
- context_intelligence.py (6.4KB) — 部分接入
- learning_collector.py (16.9KB) — 部分接入
- learning_persistence.py (8.6KB) — 部分接入
- data_feedback_loop.py (15.9KB) — 部分接入
- memory_optimizer.py (11.6KB) — 部分接入

### Evaluation层
- evaluation/ (2模块, 3KB) — 部分接入

---

## 各层详细映射（摘要）

### 一、采集层（18模块）
- ✅ 已接入：xhs_cdp_collector(44.8KB), collector.py(25.5KB), collector_automation.py(51.5KB), xhs_collection_optimizer, xhs_p0_orchestrator, xhs_runtime_state, xhs_cookie_bridge(55KB), collector_guard/(15模块,85KB), proxy_pool/, account_keepalive/, browser_runtime/, internal_browser.py, browser_surface.py
- ⚠️ 部分接入：collector_v2/(25模块,130KB), platform_adapters/(24模块,150KB), v4_upgrade/(64模块,500KB), weibo_login_manager, bilibili_login_manager

### 二、数据层（14模块/表）
- ✅ 已接入：database.py(70.7KB), database_migrations.py, canonical_data.py(32.8KB), zbc_canonical_data(表), canonical_metrics.py, data_boundary.py, data_query_api.py, metric_snapshots(表), historical_data_importer.py, subject_classifier.py, subject_context.py
- 🔴 红线保护：subject_rules.py (SUBJECT_WORDS 18词/EXCLUDE 20词)
- ⚠️ 部分接入：data_quality_gate.py, schema_registry.py, function_registry.py

### 三、CTH太古汇专项域
- 🔴 红线保护：subject_rules.py, BRAND_PROFILES(199品牌9业态)
- ✅ 已接入：v4_upgrade/cth_phrases.py, xhs_cdp_collector+collector.py, public_opinion_cases.py, risk_engine.py, daily_report.py, event_graph.py, topic_campaign.py(64.2KB), swire_notes/events/projects(表), swire_group.py, domain_isolation.py(assert_cth_protection)

### 四、ZBMP品牌智能域
- ✅ 已存在/接入：v4_upgrade/zbmp_phrases.py, api/brand-industry(4路由), api/brands(4路由), kos_*(200KB)
- ⚠️ 部分接入：brand_knowledge_base.py, brand_stats_recompute.py, brand_report_generator.py, ad_intelligence/(17模块), pr_case_integration.py, pr_case_engine.py
- ❌ 需新建：竞品/竞争模块, 品牌增长模块

### 五、AI层（14模块/表）
- ✅ 已接入：intelligence.py(40.6KB), ai_analyzer.py(34.1KB), ai_api.py, ai_governance.py, ai_evaluation.py, ai_call_logger.py, ai_filter.py, ai_resource_packs.py, local_ai_client.py, provider_registry.py, ai_call_logs(表), ai_filter_log(表)
- ⚠️ 部分接入/Legacy：ai_channel.py(CircuitBreaker重复), ai_learning_engine.py, ark_llm.py(Legacy)

### 六、Risk层（9模块/表）
- ✅ 已接入：risk_engine.py, collector_guard/risk_engine.py, alert_engine.py(24KB), alert_configs/alert_records(表), api/negative(4路由), api/negative-review(2路由), compliance_gate.py
- ⚠️ 部分接入：v4_upgrade/risk_controller.py
- ❌ 需新建：ZBMP风险策略

### 七、Evidence层（7模块/表）
- ✅ 全部已接入：evidence_chain.py(40.4KB), evidence_store.py, app_evidence.py, production_evidence_contract.py, platform_adapters/evidence_exporter.py, zbc_evidence(表), app_evidence_records(表), audit_ai_chain.py

### 八、Report层（15模块/表/路由）
- ✅ 已接入：report_api.py(45.9KB), daily_report.py, export_report.py(37.2KB), report_engine.py, report_export/report_engine.py, report_artifact.py, report_filter.py, kos_report.py(29.2KB), v4_upgrade/word_pdf_export.py, daily_reports/daily_digest(表), api/reports(2), api/special-report(2), api/weekly(2)
- ⚠️ 部分接入：brand_report_generator.py(ZBMP), v4_upgrade/report_generator.py

### 九、KOS层（12模块/8表）
- ✅ 已接入：kos_engine.py(56.6KB), kos_routes.py(44.5KB), kos_report.py, kos_intel.py, kos_ops.py, kos_execution.py, kos_paid.py, kos_professional.py, kos_scenarios.py, 8张表全部有数据
- ⚠️ 需改：kos_metrics.py(固定公式), kos_attribution.py(固定公式) → 平台规则驱动

### 十、Runtime层（13模块/4表）
- ✅ 已接入：stability_monitor.py, system_watchdog.py, system_guardian.py, auto_recovery.py, resident_health.py, runtime_preflight.py, collector_auto_start.py, cache_manager.py, network_adaptive.py, tunnel_guardian.py, 4张表
- ⚠️ P0：runtime_guardian.py(46.5KB) 零外部调用，需接入采集主链路

### 十一、Security/Permission层（12模块/7表）
- ✅ 已接入：security_scanner.py, agent_security.py, agent_boundary.py, auth_recovery_center.py, dev_exec_core.py, domain_isolation.py, repository_registry.py+core/, 7张v4表
- ⚠️ P0：permission_gate.py(38.9KB) 仅2处调用，需全面接入写操作
- ⚠️ 部分接入/重复：security_boundary.py, safety_boundary.py(重复), v4_upgrade/security.py

### 十二、Evaluation层（6模块/表）
- ✅ 已接入：evaluation_system.py, evaluation_dimensions.py(30.9KB), evaluation_recorder.py, evaluation_runner.py, case_ai_evaluate.py, case_deep_analysis.py, evaluation_records(表)
- ⚠️ 部分接入：evaluation/(2模块,3KB)

### 十三、Skill/Agent层（8模块/表）
- ✅ 已接入：skill_registry.py, lumenis_skill_adapter.py, zbc_lifecycle_tracking(表)
- ⚠️ 部分接入：agent_runtime_adapter.py, context_intelligence.py, learning_collector.py, learning_persistence.py, data_feedback_loop.py, memory_optimizer.py

### 十四、API层（150+路由，40+前缀）
- ✅ 全部已有前缀已接入：/api/xhs(15), /api/cases(10), /api/event-graph(9), /api/case-analysis(9), /api/web(8), /api/pr(7), /api/config(5), /api/creative(5), /api/ai-resource-packs(5), /api/brand-industry(4), /api/weibo(4), /api/notes(4), /api/brands(4), /api/event-review(4), /api/negative(4), 等
- ❌ P0需新建：/api/zbmp/*, /api/cth/*, /api/system/* 域前缀API（用Domain Adapter+Compatibility Layer，不机械重命名）

### 十五、UI层（20页面+3需新建）
- ✅ 已接入20页：Home, Intelligence Workspace, Skill Hub, Agent Center, Evaluation, Models/AI Gateway, Evidence, Production Overview, Monitoring, Public Opinion, Risk, Cases, Reports, Research Workspace, Findings, Runtime, Permissions, Repository
- ❌ P0需新建：ZBMP Dashboard, CTH Dashboard, 产品切换器(ZBMP↔CTH)
- ⚠️ P0需接入：ui_view_model.py(32KB) 零调用，函数驱动动态可视化

### 十六、数据库表（62张）
- ✅ 60张有数据/已接入
- ⚠️ 2张空表：podcast_ai_runs, podcast_entities

---

## 与 ZBC_FEATURE_GAP_AUDIT_20260906.md 的合并对齐

本映射表（团队盘点）与主代理缺口审计（59项）合并后，P0执行项统一为：

### P0 第一批（立即执行）
1. 数据精准性红线10项（KOS平台规则化、全平台100%精准、缺失值显式标记、时间口径分离、采集五步质量门禁、全链路可追溯、精准去重、评论详情失败不静默、AI与原始数据分离）
2. ui_view_model.py 函数驱动动态可视化接入前端（xujing-viz.js绑定真实数据）
3. runtime_guardian.py 接入采集主链路（Worker/Lease/Heartbeat/Checkpoint/Reaper/Retry/DLQ/Resume）
4. permission_gate.py 全面接入写操作（deny-by-default）
5. /api/zbmp/* /api/cth/* /api/system/* 域前缀API（Domain Adapter+Compatibility Layer）
6. ZBMP Dashboard + CTH Dashboard 双域独立Dashboard
7. 产品切换器 ZBMP↔CTH（切换重载Domain Context/指标/数据/权限/报告）
8. /api/risks/active 断链确认修复
9. Track C 39个测试失败收敛

### P1 第二批
10. IC-021 EMV指标、IC-039 跨文化本地化、IC-040 KOS兴趣图谱（已定契约未实施）
11. IC-035 OWASP Agentic安全清单（高优先级）
12. Track A ai_api拆分收尾、Track B 智谱24h保活
13. kos_metrics.py / kos_attribution.py 固定公式→平台规则驱动
14. ai_channel.py CircuitBreaker 与 runtime_guardian 去重
15. safety_boundary.py 与 security_boundary.py 收敛
16. collector_v2/ (25模块) 接入主链路
17. ad_intelligence 4平台API接入或明确BLOCKED
18. brand_knowledge_base/brand_stats_recompute/brand_report_generator 完善
19. PROJECT_STATUS P0项（300012状态机、Auth Recovery Modal、公网HTTPS）

### P2 第三批
20. v4_upgrade/ (64模块) 平台采集器接入
21. 待Contract IC项（IC-044耸动信号、IC-048可视化质量门、IC-029 NPS、IC-033情绪唤醒度等）
22. Podcast 前端接入确认
23. 函数注册表缺口补齐（情感分析双真相、话题热度、事件传播链、Campaign效果、报告聚合）
24. PROJECT_STATUS P1/P2项
25. ZBMP需新建模块（竞品/竞争、品牌增长、ZBMP风险策略）
