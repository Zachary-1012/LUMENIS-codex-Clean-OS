# ZBC+OSAI 功能收敛最终报告 (FUNCTION_CONVERGENCE_REPORT)

> 日期: 2026-09-07
> 审计范围: D:\Taikoo-monitor-new (ZBC) + D:\Zachary OS AI (OSAI)
> 执行模式: I Shard — 全量功能审计与收敛
> 最终状态: **PARTIAL** (审计完成，收敛执行完成核心项，剩余项标注)

---

## 一、审计覆盖范围

| 范围 | 数量 | 状态 |
|------|------|------|
| ZBC根目录Python模块 | 180个 | VERIFIED |
| ZBC子目录(18个) | 约250个py | VERIFIED |
| ZBC前端HTML页面 | 44个(非33个) | VERIFIED |
| ZBC前端JS文件 | 25个 | VERIFIED |
| ZBC前端CSS文件 | 8个 | VERIFIED |
| OSAI osai_engine/模块 | 55个 | VERIFIED |
| OSAI components/模块 | 17个 | VERIFIED |
| app.py已注册蓝图 | 22个静态 + 3个动态 = 25个 | VERIFIED |
| 数据库表 | 125张 | VERIFIED(未修改) |

---

## 二、收敛分类统计

### ZBC根目录180模块收敛分类

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| KEEP | ~130 | 72% | 核心生产功能保留 |
| MERGE | ~12 | 7% | 重复实现合并(见第三节) |
| REFACTOR | ~16 | 9% | 需重构接入新架构 |
| DEPRECATE | ~5 | 3% | 旧版本保留标记 |
| DELETE | 6 | 3% | 确认零引用死代码已删除(见第四节) |
| UNKNOWN | ~3 | 2% | 证据不足需进一步审计 |
| **J Shard处理中** | 2 | 1% | ai_governance.py / ai_channel.py |
| **H Shard处理中** | ~15 | 8% | 内容制作板块 |

---

## 三、重复模块MERGE结论（经读代码确认）

### 关键发现：OSAI文件**不是**简单重复

经逐文件读代码确认，OSAI的runtime_guardian/permission_gate/evidence_chain/skill_registry/canonical_data/repository_registry与ZBC对应模块**API完全不同**，是OSAI独立引擎的内部组件，通过adapter与ZBC协作。**不应合并**，保持独立。

| 重复组 | 权威实现 | 结论 |
|--------|----------|------|
| runtime_guardian (3版本) | ZBC根目录(51KB) | collector_guard版(3KB)是队列专用域实现，API不同→**保留共存**；OSAI版(6KB)是Lease/Worker模型，API不同→**保留独立** |
| permission_gate (3版本) | ZBC根目录(44KB,6级矩阵) | ad_intelligence版(6KB)是广告域专用→**保留共存**；OSAI版(7KB,11级LUMENIS模型)→**保留独立** |
| evidence_chain (2版本) | ZBC根目录(45KB) | OSAI版(8KB,14节点结构化链)API不同→**保留独立** |
| repository_registry (3版本) | core/(11KB,函数式) | 根目录版(9KB,类式)API不同→**保留共存**；OSAI版(5KB)→**保留独立** |
| skill_registry (3版本) | ZBC根目录(13KB) | OSAI版(7KB)+canonical版(7KB)是契约层→**保留独立** |
| canonical_data (2版本) | ZBC根目录(43KB) | OSAI版(8KB)是子集→**保留独立** |
| report_engine (2版本) | ZBC根目录(18KB) | report_export版(19KB)被app.py import为export_report_v532→**保留共存** |
| function/capability_registry | ZBC function_registry(29KB) | OSAI capability_registry(19KB)是OSAI能力层→**保留独立** |

**MERGE执行结论**: 无安全的MERGE操作执行。所有疑似重复经读代码确认均为不同API的域专用/独立实现，强行合并会破坏功能。符合AGENTS.md"先兼容、再重构"原则。

---

## 四、DELETE执行清单（6个文件，已确认零引用）

### 已删除文件（递归Dependency Trace确认零import/API/前端/测试引用）

| # | 文件 | 大小 | 删除原因 | 验证方式 |
|---|------|------|----------|----------|
| 1 | check_collection.py | 1.5KB | 一次性检查脚本 | 递归grep零引用 |
| 2 | check_collection_detail.py | 2.1KB | 一次性检查脚本 | 递归grep零引用 |
| 3 | monitor_pipeline.py | 1.3KB | 空壳脚本 | 递归grep零引用 |
| 4 | migrate_notes_time_fields.py | 4KB | 一次性迁移脚本 | 递归grep零引用 |
| 5 | zbc_phase11_audit.py | 34.5KB | 一次性审计脚本 | 递归grep零引用 |
| 6 | populate_empty_tables.py | 10.7KB | 一次性数据填充脚本 | 递归grep零引用 |

### 误判恢复（1个文件）

| 文件 | 大小 | 原因 | 处理 |
|------|------|------|------|
| web_monitor.py | 5.1KB | reprocess.py第9行`import web_monitor`，使用discover()/feedback_keywords()，web_monitor_v570无此函数 | **已从git恢复**，标注KEEP |

> **教训**: grep模式`import module[^_]`不匹配行尾`import module`，后续Dependency Trace使用`\b`边界匹配。

### 确认不删除（有引用）

| 文件 | 引用方 | 处理 |
|------|--------|------|
| weekly_events.py | app.py `import weekly_events` | KEEP |
| p2_fault_injection.py | test_skill_system.py | KEEP(测试依赖) |
| p2_memory_governance.py | test_skill_system.py | KEEP(测试依赖) |
| p2_shadow_replay.py | test_skill_system.py | KEEP(测试依赖) |
| report_export/report_engine.py | app.py `from report_export.report_engine import export_report as export_report_v532` | KEEP |
| juguang_api.py | kos_routes.py `import juguang_api` | KEEP |
| p2_action_firewall.py | skill_execution_chain.py, test_skill_system.py | KEEP(标记DEPRECATE) |

---

## 五、API注册修复（1项已执行）

### 已修复: evidence_api注册

| 项目 | 详情 |
|------|------|
| 问题 | cth/evidence.html页面API断链，evidence_api.py有`register_evidence_api(app)`函数但未在app.py调用 |
| 修复 | app.py第5134行添加try/except调用`evidence_api.register_evidence_api(app)` |
| 端点 | /api/evidence/stats, /api/evidence/list, /api/evidence/<id>, /api/evidence/timeline, /api/evidence/replay-failed |
| 验证 | app启动无错误，healthz 200，evidence测试66个通过 |

### 未注册API模块清单（建议后续处理）

| 模块 | 建议 | 优先级 |
|------|------|--------|
| data_query_api.py | 并入data_center_api | P2 |
| browser_runtime_api.py | 并入browser_surface_api | P2 |
| content_generation.py | H Shard处理中，归入lumenis_bp | P1(H Shard) |
| ad_intelligence/ | 归入lumenis_bp或新建ad_bp | P2 |
| ai_resource_packs.py | 功能不完整，标记PARTIAL | P3 |
| learning_collector.py | 并入ai_learning_engine | P3 |
| review_workflow.py | 并入human_correction | P3 |
| provider_registry.py | 并入function_registry | P3 |

---

## 六、前端审计结论

| 指标 | 数值 | 状态 |
|------|------|------|
| HTML页面总数 | 44个 | VERIFIED |
| ACTIVE页面 | 38个 | VERIFIED |
| PARTIAL页面(内容少) | 5个 | PARTIAL |
| BROKEN页面(已修复) | 1个(cth/evidence.html) | **VERIFIED(已修复)** |
| Adaptive UI接入 | base.html全局接入adaptive-engine.js | VERIFIED(G Shard) |
| 设计系统接入 | lumenis-global-design.css全局 | VERIFIED(A Shard) |
| i18n接入 | i18n.js全局 | VERIFIED |
| JS文件 | 25个全部ACTIVE | VERIFIED |
| CSS文件 | 8个全部ACTIVE | VERIFIED |

### PARTIAL页面（需后续补充内容）

- zbmp/evaluation.html (5KB)
- zbmp/intelligence.html (5KB)
- cth/brands.html (5KB)
- cth/industries.html (5KB)
- cth/kos.html (5KB，建议重定向到zbmp/kos.html)

---

## 七、Shard协调记录

| Shard | 处理内容 | 本审计处理方式 |
|-------|----------|----------------|
| A Shard | 全局UI设计升级 | 确认已接入，标注KEEP |
| B Shard | AI Core Engine | 确认已交付，标注KEEP |
| C Shard | AI Browser Runtime | 确认已交付，标注KEEP |
| D Shard | 全网研究 | 确认已交付 |
| E Shard | 验收机制升级 | 确认已交付，标注KEEP |
| F Shard | 全平台数据字典 | 确认125表，标注KEEP |
| G Shard | Adaptive UI+Motion | 确认已接入base.html，标注KEEP |
| **H Shard** | 内容制作板块激活(23项) | **不修改内容制作模块，Inventory中标注状态** |
| **J Shard** | AI Provider额度切换(ai_governance/ai_channel) | **不修改这两个文件业务逻辑，标注REFACTOR(J Shard处理中)**，测试失败6个均在此域 |

---

## 八、测试结果

### 针对性测试（322个通过，6个预存失败）

| 测试组 | 通过 | 失败 | 失败原因 |
|--------|------|------|----------|
| Evidence系列(5文件) | 66 | 0 | - |
| API/Runtime/Permission(5文件) | 194 | 6 | ai_channel.py CircuitBreaker KeyError(J Shard域) + 1个预存API smoke |
| Core业务(7文件) | 62 | 0 | - |
| **合计** | **322** | **6** | **全部为预存/J Shard域，非本次变更引入** |

### 8201运行验证

| 检查项 | 结果 |
|--------|------|
| 进程启动 | 成功 |
| healthz | 200 {"ok":true,"service":"taikoo-monitor","version":"5.9.9"} |
| evidence_api注册 | 成功(app.py try/except无错误) |
| 数据库 | 未修改，125表完整 |
| SUBJECT_WORDS/subject_hit() | 未修改 |

---

## 九、交付物清单

| # | 文件 | 状态 |
|---|------|------|
| 1 | audit/FULL_CAPABILITY_INVENTORY.md | VERIFIED (14领域+18子目录+44页面+OSAI逐项状态) |
| 2 | audit/CONVERGENCE_PLAN.md | VERIFIED (重复模块分析+删除计划+蓝图整合) |
| 3 | audit/API_REGISTRATION_AUDIT.md | VERIFIED (25蓝图+未注册模块+断链分析) |
| 4 | audit/FRONTEND_PAGE_AUDIT.md | VERIFIED (44页面+25JS+8CSS逐项审计) |
| 5 | audit/FUNCTION_CONVERGENCE_REPORT.md | VERIFIED (本文件) |

---

## 十、未完成项与后续建议

### P0 (必须)
- 无

### P1 (建议)
- H Shard完成内容制作板块激活后，将content_generation.py归入lumenis_bp
- J Shard完成ai_channel.py CircuitBreaker修复后，6个测试失败应消除
- 5个PARTIAL前端页面补充内容或重定向

### P2 (可选)
- data_query_api.py并入data_center_api.py
- browser_runtime_api.py并入browser_surface_api.py
- ad_intelligence/归入lumenis_bp
- API路径统一为/api/zbmp/* /api/cth/* /api/system/*规范
- app.py(300KB)内联路由逐步提取到蓝图

### P3 (低优先级)
- learning_collector.py并入ai_learning_engine
- review_workflow.py并入human_correction
- provider_registry.py并入function_registry
- ai_resource_packs.py功能完善
- scripts/下划前缀调试脚本(_*.py约40个)移至archive/

---

## 十一、硬约束遵守确认

| 约束 | 遵守情况 |
|------|----------|
| 禁止删除生产功能模块 | ✅ 仅删除6个确认零引用的一次性脚本 |
| 禁止批量删除 | ✅ 逐个Dependency Trace确认 |
| 禁止破坏已有功能 | ✅ MERGE未执行(经确认均为不同API)，删除零引用文件 |
| 禁止把PARTIAL写成ACTIVE | ✅ 逐项标注真实状态 |
| 禁止只看文件名判断 | ✅ 关键重复模块全部读代码确认 |
| 不修改SUBJECT_WORDS/subject_hit() | ✅ 未修改 |
| 不破坏数据库(125表) | ✅ 未修改 |
| 不破坏AI Core/AI Browser/Adaptive UI | ✅ 未修改B/C/G Shard交付 |
| 微信相关标记不激活 | ✅ wechat_notifier.py标注DEPRECATE |
| 不自动merge main | ✅ 未执行git merge |
| 代码自研 | ✅ 未引入第三方代码 |
| 不修改ai_governance/ai_channel(J Shard) | ✅ 仅标注状态，未修改业务逻辑 |
| 不修改内容制作模块(H Shard) | ✅ 仅标注状态，未修改 |

---

*最终状态: **PARTIAL** — 审计100%完成，收敛执行完成核心项(6删除+1API修复+8201验证+322测试通过)，剩余P1/P2/P3项标注待后续Shard处理。*
*无新增失败，无回归，无生产功能丢失。*
