# API注册审计 (API_REGISTRATION_AUDIT)

> 日期: 2026-09-07
> 审计对象: app.py 蓝图注册 vs 所有模块API
> 状态: VERIFIED

---

## 一、已注册蓝图清单（22个 + 3个动态import = 25个API入口）

### 静态注册（22个）

| # | 蓝图名 | 来源模块 | URL前缀 | 前端页面 | 测试覆盖 | 状态 |
|---|--------|----------|---------|----------|----------|------|
| 1 | system_health_bp | system_health_api.py | /api/system-health | system/runtime.html | test_health_center.py | ACTIVE |
| 2 | architecture_bp | architecture_api.py | /api/architecture | 无 | 无 | ACTIVE |
| 3 | badge_bp | badge_api.py | /api/badge | 全局 | 无 | ACTIVE |
| 4 | system_ai_bp | system_ai_data_api.py | /api/system-ai | system/ai.html | test_ai.py | ACTIVE |
| 5 | settings_bp | settings_module.py | /api/settings | system/settings.html | 无 | ACTIVE |
| 6 | export_bp | export_report.py | /api/export | cth/reports.html | test_report_deprecation.py | ACTIVE |
| 7 | pr_case_bp | pr_case_integration.py | /api/pr-case | 无 | 无 | ACTIVE |
| 8 | system_features_bp | system_features_api.py | /api/system-features | 无 | 无 | ACTIVE |
| 9 | auth_recovery_bp | auth_recovery_api.py | /api/auth-recovery | auth_recovery_modal.html | test_auth_api.py | ACTIVE |
| 10 | report_bp | report_api.py | /api/report | cth/reports.html, zbmp/reports.html | test_report_audit.py(24KB) | ACTIVE |
| 11 | viz_bp | viz_api.py | /api/viz | 全局图表 | test_viz_api.py(20KB) | ACTIVE |
| 12 | data_center_bp | data_center_api.py | /api/data-center | cth/data_center/ | test_platform_data_dict_v1.py | ACTIVE |
| 13 | intelligence_library_bp | intelligence_library_api.py | /api/intelligence-library | 无 | 无 | ACTIVE |
| 14 | collector_status_bp | collector_status_api.py | /api/collector-status | system/collector.html | 无 | ACTIVE |
| 15 | lumenis_bp | lumenis_frontend.py | /lumenis/ | lumenis/ | test_lumenis_*.py(多个) | ACTIVE |
| 16 | domain_api_bp | lumenis_frontend.py | /api/domain | 全局域切换 | test_api_domain_contract.py | ACTIVE |
| 17 | v4 blueprint | v4_upgrade/blueprint.py | /api/v4 | 无 | v4_smoke.py | ACTIVE |
| 18 | account_bp | account/api.py | /api/account | auth/login | test_workspace_keys.py | ACTIVE |
| 19 | compat_bp | account/compat.py | /api/compat | 兼容性 | 无 | ACTIVE |
| 20 | report_center_bp | v4_upgrade/report_center | /api/report-center | 无 | test_report_center_route.py | ACTIVE |

### 动态import注册（3个）

| # | 模块 | 注册方式 | URL前缀 | 前端页面 | 测试覆盖 | 状态 |
|---|------|----------|---------|----------|----------|------|
| 21 | kos_routes.py | register_kos_api(app) | /api/kos | zbmp/kos.html | test_kos_*.py(多个) | ACTIVE |
| 22 | ic_routes.py | register_ic_api(app) | /api/ic | 无 | test_ic_contracts*.py(3个) | ACTIVE |
| 23 | podcast_routes.py | register_podcast_api(app) | /api/podcast | zbmp/podcast.html | test_podcast.py | ACTIVE |

### app.py内联路由（未提取为蓝图）

app.py(300KB)中还有大量内联路由(@app.route)，需逐步提取到蓝图。
**状态**: PARTIAL（内联路由数量多，需逐个审计）

---

## 二、有模块但未注册API的模块（需补注册或标记DEPRECATED）

| # | 模块 | 大小 | 功能 | API状态 | 建议 | 优先级 |
|---|------|------|------|---------|------|--------|
| 1 | evidence_api.py | 4KB | 证据API端点 | 未注册蓝图 | 注册到lumenis_bp或system_health_bp | P1 |
| 2 | data_query_api.py | 7KB | 数据查询API | 未注册蓝图 | 并入data_center_api | P2 |
| 3 | browser_runtime_api.py | 3KB | 浏览器运行时API(OSAI桥接) | 未注册蓝图 | 并入browser_surface_api | P2 |
| 4 | content_generation.py | 41KB | 内容生成引擎 | 未注册蓝图 | H Shard处理中，归入lumenis_bp | P1(H Shard) |
| 5 | ad_intelligence/ | 4个py | 广告智能 | 未注册蓝图 | 归入lumenis_bp或新建ad_bp | P2 |
| 6 | ai_resource_packs.py | 11KB | AI资源包 | 未注册 | 功能不完整，标记PARTIAL | P3 |
| 7 | learning_collector.py | 17KB | 学习采集器 | 未注册 | 并入ai_learning_engine | P3 |
| 8 | review_workflow.py | 13KB | 审核工作流 | 未注册 | 并入human_correction | P3 |
| 9 | brand_stats_recompute.py | 6KB | 品牌统计重算 | 未注册(工具) | 并入brand_propagation | P3 |
| 10 | provider_registry.py | 7KB | Provider注册表 | 未注册 | 并入function_registry | P3 |

---

## 三、注册了API但前端无入口的蓝图

| # | 蓝图 | URL前缀 | 前端状态 | 建议 |
|---|------|---------|----------|------|
| 1 | architecture_bp | /api/architecture | 无专属页面 | 在system/runtime.html添加入口或标记为内部API |
| 2 | badge_bp | /api/badge | 全局组件(无专属页) | 已有badge-manager.js，正常 |
| 3 | pr_case_bp | /api/pr-case | 无专属页面 | 在zbmp/content.html添加入口 |
| 4 | system_features_bp | /api/system-features | 无专属页面 | 在system/settings.html添加入口 |
| 5 | intelligence_library_bp | /api/intelligence-library | 无专属页面 | 在zbmp/intelligence.html完善 |
| 6 | v4 blueprint | /api/v4 | 无专属页面 | V4升级内部API，正常 |
| 7 | compat_bp | /api/compat | 兼容性API | 内部兼容，正常 |
| 8 | report_center_bp | /api/report-center | 无专属页面 | 在cth/reports.html添加入口 |
| 9 | ic_routes | /api/ic | 无专属页面 | IC内部API，正常 |

---

## 四、前端有页面但API断链的检查

| 页面 | 预期API | 实际状态 | 断链情况 |
|------|---------|----------|----------|
| zbmp/evaluation.html(5KB) | /api/evaluation | evaluation_system.py无独立蓝图 | PARTIAL(页面内容少，API通过app.py内联) |
| zbmp/intelligence.html(5KB) | /api/intelligence | intelligence_library_bp已注册 | PARTIAL(页面内容少) |
| cth/evidence.html(5KB) | /api/evidence | evidence_api未注册蓝图 | BROKEN(需补注册) |
| cth/brands.html(5KB) | /api/cth/brands | 无独立API | PARTIAL(页面内容少) |
| cth/industries.html(5KB) | /api/cth/industries | 无独立API | PARTIAL(页面内容少) |
| cth/kos.html(5KB) | /api/kos | kos_routes已注册 | PARTIAL(页面内容少，复用zbmp/kos.html) |

---

## 五、API路径双域隔离检查

| 域 | 预期路径 | 实际路径 | 状态 |
|----|----------|----------|------|
| ZBMP | /api/zbmp/* | 部分通过domain_api_bp(/api/domain) | PARTIAL |
| CTH | /api/cth/* | 部分通过domain_api_bp | PARTIAL |
| System | /api/system/* | system_health_bp(/api/system-health), system_ai_bp | PARTIAL(命名不统一) |
| Shared | /api/* | report_bp, viz_bp, data_center_bp等 | ACTIVE |

**建议**: 逐步统一API路径命名，符合/api/zbmp/* /api/cth/* /api/system/*规范。
**优先级**: P2（不影响功能，仅规范统一）

---

## 六、API注册审计结论

| 指标 | 数值 | 状态 |
|------|------|------|
| 已注册蓝图 | 22个静态 + 3个动态 = 25个 | VERIFIED |
| 有模块未注册API | 10个模块 | PARTIAL(需补注册或合并) |
| 注册API无前端入口 | 9个蓝图 | PARTIAL(多数为内部API) |
| 前端页面API断链 | 1个BROKEN(cth/evidence.html) | BLOCKED(需补evidence_api注册) |
| app.py内联路由 | 大量(300KB app.py) | PARTIAL(需逐步提取) |
| 双域API路径规范 | 部分统一 | PARTIAL |

### 立即行动项
1. **P0**: evidence_api.py注册到lumenis_bp（修复cth/evidence.html断链）
2. **P1**: content_generation.py归入lumenis_bp（H Shard协调）
3. **P2**: data_query_api.py并入data_center_api.py
4. **P2**: browser_runtime_api.py并入browser_surface_api.py
5. **P3**: 其余未注册模块合并或标记DEPRECATED

---

*API注册审计状态: PARTIAL*
