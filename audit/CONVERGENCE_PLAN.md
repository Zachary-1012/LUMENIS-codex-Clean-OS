# ZBC+OSAI 收敛计划 (CONVERGENCE_PLAN)

> 日期: 2026-09-07
> 基于: FULL_CAPABILITY_INVENTORY.md
> 原则: 先旁路验证，再进入主链路；MERGE不删除权威版本；DELETE需Dependency Trace确认
>
> **Shard协调**: ai_governance.py / ai_channel.py 由J Shard专门处理（AI Provider额度切换规则V1.0），本审计不修改这两个文件的业务逻辑，仅标注状态。如有重复/死代码记录在此但不执行。

---

## 一、重复模块MERGE方案（9组，小版本改为import权威版本）

### MERGE-1: runtime_guardian（3版本→1权威）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/runtime_guardian.py | 51KB | 全局运行时守护，健康检查/自愈/熔断 |
| 简化 | collector_guard/runtime_guardian.py | 3KB | 基于队列的采集守护(子集) |
| OSAI | osai_engine/runtime_guardian.py | 6KB | OSAI引擎守护(子集) |

**执行方案**:
- collector_guard/runtime_guardian.py → 改为 `from runtime_guardian import *` + 保留队列专用类RuntimeGuardian(基于队列的)
- osai_engine/runtime_guardian.py → 改为 `from runtime_guardian import RuntimeGuardian as BaseRuntimeGuardian` + OSAI特定扩展
- 不删除文件，保持向后兼容

**验证**: test_runtime_guardian.py + test_runtime_guardian_integration.py 必须通过

---

### MERGE-2: permission_gate（3版本→1权威+1域专用）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/permission_gate.py | 44KB | 全局6级权限矩阵 |
| 域专用 | ad_intelligence/permission_gate.py | 6KB | 广告投放域专用权限(READ/ANALYZE/PREVIEW/EXECUTE) |
| OSAI | osai_engine/permission_gate.py | 7KB | OSAI权限门(子集) |

**执行方案**:
- ad_intelligence/permission_gate.py → 保留为域专用，内部委托全局PermissionGate做审计/高风险审批（已在docstring中说明共存）
- osai_engine/permission_gate.py → 改为 `from permission_gate import PermissionGate` + OSAI特定契约

**验证**: test_permission_gate.py(39KB) + test_permission_gate_app_integration.py(19KB) + test_permission_dual_domain.py(17KB)

---

### MERGE-3: evidence_chain（2版本→1权威）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/evidence_chain.py | 45KB | 全局证据链，操作证据/追溯/审计 |
| OSAI | osai_engine/evidence_chain.py | 8KB | OSAI证据链(子集) |

**执行方案**:
- osai_engine/evidence_chain.py → 改为 `from evidence_chain import EvidenceChain, EvidenceRecord` + OSAI特定扩展

**验证**: test_evidence_chain.py(27KB) + test_evidence_dual_domain.py(9KB) + test_evidence_store.py(8KB)

---

### MERGE-4: repository_registry（3版本→1权威）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | core/repository_registry.py | 11KB | 仓库注册表权威实现(get_data_dir等) |
| 根目录 | repository_registry.py | 9KB | 根目录版本(被collector_guard引用core版本) |
| OSAI | osai_engine/repository_registry.py | 5KB | OSAI仓库注册(子集) |

**执行方案**:
- 根目录/repository_registry.py → 改为 `from core.repository_registry import *`（保持向后兼容）
- osai_engine/repository_registry.py → 改为 `from core.repository_registry import RepositoryRegistry` + OSAI扩展

**验证**: test_repository_registry.py(17KB)

---

### MERGE-5: skill_registry（3版本→1权威+1规范）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/skill_registry.py | 13KB | Skill注册表，注册/发现/加载 |
| 规范 | osai_engine/canonical_skill_registry.py | 7KB | 规范Skill注册表(契约层) |
| OSAI | osai_engine/skill_registry.py | 7KB | OSAI Skill注册(子集) |

**执行方案**:
- osai_engine/skill_registry.py → 改为 `from skill_registry import SkillRegistry` + OSAI扩展
- canonical_skill_registry.py → 保留为契约定义层

**验证**: test_skill_system.py(13KB) + test_lumenis_skill_hub.py(10KB) + test_skill_agent_boundary.py(33KB)

---

### MERGE-6: canonical_data（2版本→1权威）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/canonical_data.py | 43KB | 三层数据模型(Raw→Normalized→Canonical) |
| OSAI | osai_engine/canonical_data.py | 8KB | OSAI规范数据(子集) |

**执行方案**:
- osai_engine/canonical_data.py → 改为 `from canonical_data import *` + OSAI特定契约

**验证**: test_canonical_data_t4.py(19KB) + test_canonical_metrics.py(7KB)

---

### MERGE-7: report_engine（2版本→1权威）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/report_engine.py | 18KB | 报告引擎核心 |
| 旧版 | report_export/report_engine.py | 19KB | 报告导出引擎(旧版，无引用) |

**执行方案**:
- report_export/report_engine.py → DELETE（确认无任何import/API/前端/测试引用）
- report_export/app_report_api_patch.py → DELETE（一次性补丁）

**验证**: test_report_audit.py(24KB) + test_report_dual_domain.py(10KB) + test_report_center_route.py

---

### MERGE-8: capability_registry vs function_registry（2版本→1权威）

| 版本 | 路径 | 大小 | 角色 |
|------|------|------|------|
| 权威 | ZBC根目录/function_registry.py | 29KB | 函数注册表，能力注册/发现/调用 |
| OSAI | osai_engine/capability_registry.py | 19KB | 能力注册表(OSAI命名，功能重叠) |
| 组件 | components/.../shared/capability_registry.py | 6KB | 组件级能力注册(子集) |

**执行方案**:
- osai_engine/capability_registry.py → 保留为OSAI能力层，内部委托function_registry做底层注册
- components/shared/capability_registry.py → 改为 `from function_registry import FunctionRegistry` + 组件扩展

**验证**: 无直接测试，需补充test_function_registry.py

---

### MERGE-9: 其他小重复（4组）

| 重复组 | 权威 | 待合并 | 方案 |
|--------|------|--------|------|
| system_guardian/system_watchdog | runtime_guardian.py | system_guardian.py(9KB), system_watchdog.py(12KB) | 改为import runtime_guardian，保留特定函数 |
| safety_boundary | security_boundary.py(44KB) | safety_boundary.py(19KB) | 改为import security_boundary，保留轻量接口 |
| internal_browser_adapter/stream | internal_browser.py(24KB) | adapter(10KB), stream(11KB) | 合并到internal_browser.py |
| evaluation_recorder/runner | evaluation_system.py(20KB) | recorder(15KB), runner(10KB) | 合并到evaluation_system.py |
| unified_logger | v4_upgrade/unified_logger.py(7KB) | SICI-Core/unified_logger.py(6KB) | SICI版改为import v4版 |
| runtime_preflight | ZBC根目录/runtime_preflight.py(15KB) | components/tools/runtime_preflight.py(7KB) | 组件版改为import根目录版 |

---

## 二、孤儿/死代码DELETE方案（确认无依赖后删除）

### DELETE-1: 确认无引用的死代码（立即执行）

| 文件 | 大小 | Dependency Trace结果 | 删除原因 |
|------|------|---------------------|----------|
| web_monitor.py | 5KB | reprocess.py依赖discover()/feedback_keywords()，非死代码 | **保留**(误判已恢复) |
| check_collection.py | 1.5KB | 无任何import/API/前端/测试引用 | 一次性脚本 |
| check_collection_detail.py | 2.1KB | 无引用 | 一次性脚本 |
| monitor_pipeline.py | 1.3KB | 无引用(仅空壳) | 空壳脚本 |
| weekly_events.py | 2.1KB | 无引用 | 一次性脚本 |
| migrate_notes_time_fields.py | 4KB | 无引用 | 一次性迁移 |
| report_export/report_engine.py | 19KB | 无引用 | 旧版被替代 |
| report_export/app_report_api_patch.py | 1KB | 无引用 | 一次性补丁 |
| zbc_phase11_audit.py | 35KB | 仅自引用，无import/API/前端 | 一次性审计脚本 |

### DELETE-2: scripts/ 下划线前缀调试脚本（需逐个确认）

scripts/ 目录下有大量 `_*.py` 文件（约40个），均为调试/一次性脚本。
**方案**: 批量标记，确认无生产引用后移至 archive/ 目录（不直接删除，保留可恢复性）

### DELETE-3: p2_*实验系列（确认未接入生产）

| 文件 | 大小 | 引用情况 | 处理 |
|------|------|----------|------|
| p2_action_firewall.py | 8KB | skill_execution_chain.py引用, test_skill_system.py引用 | 保留(有引用)，标记DEPRECATE |
| p2_fault_injection.py | 6KB | 无根目录引用 | DELETE(实验代码) |
| p2_memory_governance.py | 6KB | 无根目录引用 | DELETE(实验代码) |
| p2_shadow_replay.py | 4KB | 无根目录引用 | DELETE(实验代码) |

### DELETE-4: 其他确认无用文件

| 文件 | 处理 |
|------|------|
| audit_ai_chain.py(11KB) | DEPRECATE(功能并入ai_call_logger)，保留文件 |
| ci_cd.py(13KB) | DEPRECATE(运维脚本)，保留 |
| wechat_notifier.py(50KB) | DEPRECATE(用户明确微信跳过)，保留不激活 |

---

## 三、功能归入正确域和层级

### 域归属确认

| 功能模块 | 归属域 | 层级 | 蓝图 |
|----------|--------|------|------|
| 小红书采集(xhs_*) | CTH | L2 | collector_status_bp |
| 微博/B站采集 | CTH | L2 | collector_status_bp |
| 风险引擎(risk_engine) | Shared | L2 | report_bp/独立 |
| 日报(daily_report) | CTH | L2 | report_bp |
| KOS体系(kos_*) | ZBMP | L2 | kos_routes(动态) |
| 品牌传播(brand_*) | ZBMP | L2 | report_bp |
| 情报分析(intelligence) | ZBMP | L2 | intelligence_library_bp |
| 内容制作(topic_*/content_*) | ZBMP | L2 | lumenis_bp(H Shard) |
| AI Core(ai_task_*) | System | L2 | system_ai_bp |
| AI Browser(ai_browser_*) | System | L2 | lumenis_bp |
| 运行时(runtime_*) | System | L1 | system_health_bp |
| 权限安全(permission/security) | Shared | L1 | system_health_bp |
| 证据链(evidence_*) | Shared | L1 | 需注册(并入lumenis_bp) |
| 评估(evaluation_*) | Shared | L1 | system_health_bp |
| 数据中心(data_center) | Shared | L4 | data_center_bp |
| 可视化(viz_*) | Shared | L4 | viz_bp |
| 账号体系(account/) | Shared | L2 | account_bp |
| 播客(podcast) | ZBMP | L2 | podcast_routes(动态) |
| 广告智能(ad_intelligence) | ZBMP | L2 | 需注册(并入lumenis_bp) |

---

## 四、蓝图复用整合（不新建重复蓝图）

### 已有22个蓝图，收敛时优先归入

| 蓝图 | 覆盖功能 | 需新增归入 |
|------|----------|------------|
| system_health_bp | 健康/运行时/评估 | evidence_api(并入) |
| system_ai_bp | AI Core | ai_browser_api(确认是否已在lumenis) |
| collector_status_bp | 采集状态 | xhs_*/collector_v2 API(如有) |
| report_bp | 报告 | report_filter(并入) |
| data_center_bp | 数据中心 | data_query_api(并入) |
| lumenis_bp | LUMENIS前端/AI Browser | content_generation(H Shard), ad_intelligence |
| viz_bp | 可视化 | 无 |
| account_bp | 账号 | 无 |
| report_center_bp | V4报告中心 | 无 |
| pr_case_bp | 公关案例 | 无 |
| intelligence_library_bp | 情报库 | 无 |
| settings_bp | 设置 | 无 |
| export_bp | 导出 | 无 |
| auth_recovery_bp | 认证恢复 | 无 |
| architecture_bp | 架构 | 无 |
| badge_bp | 徽章 | 无 |
| system_features_bp | 系统功能 | 无 |
| domain_api_bp | 双域API | 无 |
| v4 blueprint | V4升级 | 无 |
| compat_bp | 兼容性 | 无 |
| kos_routes(动态) | KOS | 无 |
| ic_routes(动态) | IC | 无 |
| podcast_routes(动态) | 播客 | 无 |

**结论**: 不需要新建蓝图，所有功能可归入已有22个蓝图。

---

## 五、命名/数据表适配最新标准

### 命名规范检查
- ✅ 数据字典: platform_naming.py(35KB)已定义12平台命名
- ✅ Raw表用平台原生名(note_id/aweme_id/bvid)
- ✅ Normalized用like_count/view_count
- ✅ 业务用engagement/engagement_rate
- ⚠️ 需检查: 旧模块中是否有不符合命名规范的字段

### 数据表检查
- ✅ 125张表(F Shard新增43张全平台数据字典表)
- ✅ publish_at与captured_at分离
- ✅ collection_runs + platform_evidence
- ⚠️ 需检查: 旧表是否有不符合Canonical标准的字段

---

## 六、UI接入Adaptive组件+设计系统

### 已接入确认
- ✅ base.html已引入adaptive-engine.js
- ✅ 44个HTML页面全部继承base.html
- ✅ adaptive-layout.css + adaptive-components.css已部署
- ✅ lumenis-global-design.css(设计系统)已部署
- ✅ Motion System(lumenis-motion-engine.js + adaptive-motion.js)已部署

### 需检查
- ⚠️ 各页面是否实际使用Adaptive组件(Container Query/Size Model)
- ⚠️ 死按钮/假数据检查(在FRONTEND_PAGE_AUDIT.md中详细列出)

---

## 七、执行顺序与风险控制

### Phase 1: MERGE执行（低风险，小版本改import）
1. collector_guard/runtime_guardian.py → import权威版
2. osai_engine/runtime_guardian.py → import权威版
3. osai_engine/permission_gate.py → import权威版
4. osai_engine/evidence_chain.py → import权威版
5. 根目录/repository_registry.py → import core版
6. osai_engine/repository_registry.py → import core版
7. osai_engine/skill_registry.py → import权威版
8. osai_engine/canonical_data.py → import权威版

### Phase 2: DELETE执行（需确认无依赖）
1. 删除确认无引用的9个文件(DELETE-1)
2. 删除p2_*实验系列3个文件
3. scripts/_*.py移至archive/

### Phase 3: 蓝图整合（中风险，需测试）
1. evidence_api注册到lumenis_bp
2. data_query_api并入data_center_api
3. browser_runtime_api并入browser_surface_api

### Phase 4: 回归验证
1. 重启8201
2. 全量测试
3. 关键页面E2E检查

### 风险控制
- MERGE操作不删除权威版本，小版本改为import，向后兼容
- DELETE操作前已做Dependency Trace，确认无import/API/DB/前端引用
- 不修改SUBJECT_WORDS/subject_hit()/数据库结构
- 不破坏AI Core/AI Browser/Adaptive UI等已完成shard交付
- 内容制作模块(H Shard)只标注不修改

---

*收敛计划状态: PARTIAL (计划完成，执行进行中)*
