# Z-Brand-Core 分支可回收资产矩阵（Capability-Level Selective Recovery Audit）

> 审计时间：2026-09-07
> 审计基线：main @ 46502f11（生产基线，working tree clean）
> 审计方法：git diff / git show 只读审查，未切换分支，未修改任何文件
> 审计人：豆包本地执行环境

---

## 0. 执行摘要

**核心结论：两个分支均为实验性"全量升级"分支，整体回收价值极低。main 已在所有核心维度超越两个分支。**

| 维度 | 结论 |
|------|------|
| 分支性质 | 实验性重构，非生产级增量 |
| 主要操作 | 大规模删除（1438/1586 文件）+ 核心模块瘦身 |
| 新增能力 | 仅 3 个工具脚本 + LUMENIS UI 模板/CSS + 分支1审计脚本 |
| main 状态 | 已集成更完整的 PermissionGate、双域隔离、多Provider AI、LUMENIS前端、collector_guard(15文件)、v4_upgrade(完整子目录)、246个测试 |
| 红线违反 | 分支1删除双域隔离；两分支均删除旧实现、移除DB重试、移除多区域采集 |
| 建议 | 不进行任何cherry-pick；仅参考LUMENIS UI设计和dev_exec_core安全模式 |

---

## 1. 分支概览表

| 指标 | feat/zbc-full-upgrade-v1 | origin/feat/lumenis-product-convergence |
|------|---------------------------|------------------------------------------|
| 类型 | 本地分支 | 远程分支 |
| Commits ahead | 11 | 4 |
| Merge base | 045d042 (2026-09-06 12:24, PR#24 merge) | d7236f2 (2026-09-06 04:12, v5.9.9 autosave) |
| 总文件变更 | 1595 | 1757 |
| 新增(A) | 42 | 30 |
| 修改(M) | 114 | 140 |
| 删除(D) | 1438 | 1586 |
| 重命名(R) | 1 | 1 |
| 代码增行 | +9,075 | +5,379 |
| 代码删行 | -434,002 | -586,272 |
| 净变更 | -424,927 | -580,893 |
| 关键提交 | PermissionGate接入、Evidence链、Phase11-17模块验证、Repository Registry | product convergence docs、移除硬编码auth recovery DB路径 |
| **总体风险** | **HIGH** — 删除双域隔离、大规模删除旧实现 | **CRITICAL** — 删除更多文件、移除报告artifact字段、含代码执行模块 |
| **总体回收价值** | **LOW** | **VERY LOW** |

---

## 2. 逐文件可回收矩阵

### 2.1 共同新增文件（两分支均有）

| 文件名 | 变更类型 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|----------|----------|----------|----------|----------|----------|
| check_collection.py | A | 不存在 | SQLite诊断脚本：笔记统计、采集日志、collector_stats读取 | LOW | 仅参考 | 硬编码`data/monitor.db`路径；无主体过滤；纯只读诊断 |
| check_collection_detail.py | A | 不存在 | 增强版诊断：10条最近笔记、20条采集日志、正文完整性检查 | LOW | 仅参考 | 硬编码DB路径；与main的system_health_api.py功能重叠 |
| monitor_pipeline.py | A | 不存在 | 本地pipeline包装：collector.collect_all → ai_analyzer.verify_taikoo_location → 入库 | REJECT | 不回收 | 依赖`ai_analyzer`模块(main中为ai_api.py/intelligence.py)；调用`verify_taikoo_location`非生产口径；绕过subject_hit()正式主体过滤 |
| static/css/lumenis.css | A | 不存在(main有lumenis-global-design.css) | LUMENIS设计系统主CSS | MEDIUM | 仅参考设计 | 与main的lumenis-global-design.css可能重叠；需对比类名冲突 |
| static/css/lumenis-tokens.css | A | 不存在 | LUMENIS设计token(CSS变量) | MEDIUM | 仅参考设计 | 设计参考价值；main可能已有自己的token体系 |
| static/css/lumenis-components.css | A | 不存在 | LUMENIS组件样式(card/grid/table/badge等) | MEDIUM | 仅参考设计 | UI组件设计参考 |
| static/css/lumenis-layout.css | A | 不存在 | LUMENIS布局样式 | LOW | 仅参考设计 | 与main现有布局可能冲突 |
| static/css/lumenis-motion.css | A | 不存在 | LUMENIS动画/过渡样式 | LOW | 仅参考设计 | 边际增强 |
| static/css/lumenis-reset.css | A | 不存在 | CSS reset | LOW | 不回收 | main已有base.html中的reset |
| static/css/lumenis-responsive.css | A | 不存在 | 响应式样式 | LOW | 仅参考设计 | 边际增强 |
| templates/home/command_home.html | A | 不存在 | LUMENIS命令中心首页 | LOW | 仅参考设计 | UI壳，依赖lumenis JS API |
| templates/_preview/command-home-preview.html | A | 不存在 | 命令中心预览页 | LOW | 不回收 | 预览/原型文件 |
| templates/intelligence/agent_center.html | A | 不存在 | Agent管理UI(Orchestrator/Research/Engineering) | MEDIUM | 仅参考设计 | UI壳，data-field占位；main的lumenis_frontend.py已有路由框架 |
| templates/intelligence/evaluation.html | A | 不存在 | AI评估UI | LOW | 仅参考设计 | UI壳 |
| templates/intelligence/evidence.html | A | 不存在 | 证据链UI | LOW | 仅参考设计 | main已有evidence_api.py + 前端 |
| templates/intelligence/models.html | A | 不存在 | AI模型管理UI | LOW | 仅参考设计 | UI壳 |
| templates/intelligence/skill_hub.html | A | 不存在 | Skill中心UI | LOW | 仅参考设计 | UI壳 |
| templates/intelligence/workspace.html | A | 不存在 | 智能工作台UI | LOW | 仅参考设计 | UI壳 |
| templates/operations/index.html | A | 不存在 | 运维中心首页 | LOW | 仅参考设计 | UI壳 |
| templates/operations/permissions.html | A | 不存在 | 权限与审计矩阵UI | MEDIUM | 仅参考设计 | 与main的PermissionGate Phase12可配合；但main已有自己的权限UI |
| templates/operations/repository.html | A | 不存在 | 仓库注册UI | LOW | 仅参考设计 | UI壳 |
| templates/operations/runtime.html | A | 不存在 | 运行时守护UI | LOW | 仅参考设计 | main已有runtime_guardian.py + system_health_api |
| templates/production/overview.html | A | 不存在 | 生产概览UI | LOW | 仅参考设计 | 与main现有overview重叠 |
| templates/production/monitoring.html | A | 不存在 | 生产监控UI | LOW | 仅参考设计 | 与main现有monitoring重叠 |
| templates/production/public_opinion.html | A | 不存在 | 舆情UI | LOW | 仅参考设计 | 与main现有舆情页面重叠 |
| templates/production/risk.html | A | 不存在 | 风险预警UI | LOW | 仅参考设计 | 与main现有风险页面重叠 |
| templates/production/reports.html | A | 不存在 | 报告中心UI | LOW | 仅参考设计 | 与main现有报告中心重叠 |
| templates/production/cases.html | A | 不存在 | 案例库UI | LOW | 仅参考设计 | 与main现有案例库重叠 |
| templates/research/findings.html | A | 不存在 | 研究发现UI | LOW | 仅参考设计 | UI壳 |
| templates/research/workspace.html | A | 不存在 | 研究工作台UI | LOW | 仅参考设计 | UI壳 |

### 2.2 分支1独有新增文件（feat/zbc-full-upgrade-v1）

| 文件名 | 变更类型 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|----------|----------|----------|----------|----------|----------|
| zbc_phase11_audit.py | A | 不存在 | 单文件全量模块审计：AST扫描、分类、输出module_inventory.md/json | MEDIUM | 仅参考设计 | 721行；硬编码REPO路径；分类逻辑可参考；main已有audit/目录和security_scanner.py |
| audit/_analyze_imports_browser.py | A | 不存在 | 浏览器相关import分析脚本 | LOW | 不回收 | 一次性审计脚本；硬编码路径 |
| audit/_browser_deep_check.py | A | 不存在 | 浏览器深度检查脚本 | LOW | 不回收 | 一次性审计脚本 |
| audit/_filter_batch3.py | A | 不存在 | Batch3过滤脚本 | LOW | 不回收 | 一次性审计脚本 |
| audit/_fix_blocked_csv.py | A | 不存在 | CSV修复脚本 | LOW | 不回收 | 一次性审计脚本；修改CSV数据 |
| audit/_list_partial.py | A | 不存在 | 列出PARTIAL状态模块 | LOW | 不回收 | 一次性审计脚本 |
| audit/_module_scanner.py | A | 不存在 | AST模块扫描器，生成_module_scan_raw.json | LOW | 不回收 | 硬编码`REPO = Path(r'D:\Taikoo-monitor-new')`；与zbc_phase11_audit.py功能重叠 |
| audit/_reimport_batch3.py | A | 不存在 | Batch3重新导入脚本 | LOW | 不回收 | 一次性审计脚本 |
| audit/_update_csv_status.py | A | 不存在 | CSV状态更新脚本 | LOW | 不回收 | 一次性审计脚本；修改数据 |
| audit/_verify_batch3.py | A | 不存在 | Batch3验证脚本 | LOW | 不回收 | 一次性审计脚本 |
| static/css/lumenis-core-components.css | A | 不存在 | LUMENIS核心组件样式(分支2无) | LOW | 仅参考设计 | 与lumenis-components.css可能重叠 |
| static/css/lumenis-tokens-v2.css | A | 不存在 | LUMENIS token v2(分支2无) | LOW | 仅参考设计 | 版本迭代中间产物 |

### 2.3 核心基础设施修改文件（两分支共有）

| 文件名 | 分支1变更 | 分支2变更 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-----------|-----------|----------|----------|----------|----------|----------|
| app.py | M (-586行) | M (-715行) | 生产基线 | Flask主应用 | REJECT | 不回收 | 两分支均大幅删减；main已有PermissionGate Phase12(fail-closed)、lumenis前端、双域隔离；分支版本含裸`except: pass`吞异常 |
| database.py | M (-54行) | M (-68行) | 生产基线 | SQLite数据层 | REJECT | 不回收 | 两分支均移除`_db_connect_with_retry()`指数退避；移除logging；分支2移除Phase9报告artifact字段(report_id/artifact_hash/generator_version/data_version/source_snapshot)；分支1改变publish_date回退优先级 |
| collector.py | M (-81行) | M (-152行) | 生产基线 | 采集主链路 | REJECT | 不回收 | 两分支均移除RedNote策略旁路、双CDP(9222大陆/9223港版)、region参数；分支2额外移除Runtime Guardian、CollectState集成；严重削弱多区域多通道采集能力 |
| config.py | M (-35行) | M (-103行) | 生产基线 | 配置管理 | LOW | 仅参考 | 分支2新增`get_known_config_keys()`列出已知配置键(小幅增强)；其余为删减 |
| risk_engine.py | M (-880行) | M (-880行) | 生产基线 | 风险引擎 | REJECT | 不回收 | 两分支均删除880行风险规则；分支1仅加一行docstring；严重削弱风险判断能力 |
| daily_report.py | M (-181行) | M (-191行) | 生产基线 | 日报生成 | REJECT | 不回收 | 两分支均大幅删减日报逻辑 |
| xhs_cdp_collector.py | M (-4行) | M (-17行) | 生产基线 | XHS CDP采集器 | LOW | 不回收 | 小幅修改；main版本更完整 |
| web_monitor.py | M (-89行) | M (-89行) | 生产基线 | Web监控 | REJECT | 不回收 | 大幅删减 |
| wechat_notifier.py | M (-302行) | M (-302行) | 生产基线 | 微信通知 | REJECT | 不回收 | 删除302行通知逻辑 |

### 2.4 安全与治理修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| permission_gate.py | M (-108行) | M (-991行) | 已集成Phase12 | 权限门 | REJECT | 不回收 | 分支2删除991行几乎整个权限系统；main已有更完整的PermissionGate(fail-closed、写操作拦截、OperationType/RiskLevel枚举) |
| compliance_gate.py | M (-3行) | M (-9行) | 存在 | 合规门 | LOW | 不回收 | 小幅删减 |
| security_boundary.py | M (-2行) | — | 存在 | 安全边界 | LOW | 不回收 | 几乎无变化 |
| safety_boundary.py | — | M (-4行) | 存在 | 安全边界(分支2命名) | LOW | 不回收 | 小幅删减 |
| domain_isolation.py | M (-150行) | M (-150行) | 生产基线 | 域隔离 | REJECT | 不回收 | 两分支均删除150行域隔离逻辑 |
| subject_context.py | M (-67行) | M (-172行) | 生产基线 | 主体上下文 | **REJECT(红线)** | 不回收 | **分支1删除双域隔离：移除X-Domain-Id/X-Product-Id请求头解析、DomainContext、CTH domain_id保护**；分支2删除更多；违反CTH/ZBMP双域隔离红线 |
| subject_rules.py | — | M (-10行) | 生产基线 | 主体规则 | **REJECT(红线)** | 不回收 | **分支2移除线程级SubjectContext三级优先级链(thread→env→CTH default)，弱化为单次get_subject_context()**；潜在主体口径泄漏风险 |
| agent_security.py | — | M (-12行) | 存在 | Agent安全 | LOW | 不回收 | 小幅删减 |

### 2.5 AI层修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| ai_channel.py | M (-454行) | M (-560行) | 已完整集成 | AI传输层 | REJECT | 不回收 | main已有完整多Provider故障转移(智谱主+豆包备+本地规则兜底)、ProviderBreaker独立熔断、健康监控、重试退避；分支版本大幅删减 |
| ai_governance.py | M (-313行) | M (-317行) | 存在 | AI治理 | REJECT | 不回收 | 大幅删减 |
| ai_api.py | M | M | 存在 | AI API | LOW | 不回收 | 删减 |
| ark_llm.py | M | M | 存在 | 火山方舟LLM | LOW | 不回收 | 删减 |
| local_ai_client.py | M | M | 存在 | 本地AI客户端 | LOW | 不回收 | 删减 |
| ai_call_logger.py | M | — | 存在 | AI调用日志 | LOW | 不回收 | 删减 |
| ai_resource_packs.py | M | M | 存在 | AI资源包 | LOW | 不回收 | 删减 |
| intelligence.py | M | M | 存在 | 智能层 | LOW | 不回收 | 删减 |
| ai_analyzer.py | — | M | 存在 | AI分析器 | LOW | 不回收 | 删减 |
| ai_filter.py | — | M | 存在 | AI过滤器 | LOW | 不回收 | 删减 |
| ai_learning_engine.py | — | M | 存在 | AI学习引擎 | LOW | 不回收 | 删减 |
| agent_runtime_adapter.py | M | — | 存在 | Agent运行时适配器 | LOW | 不回收 | 删减 |

### 2.6 证据与评估修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| evidence_chain.py | M (-195行) | M (-1167行) | 生产基线 | 证据链 | REJECT | 不回收 | 分支2删除1167行几乎整个证据链；main已有完整evidence_chain + evidence_api + app_evidence |
| evidence_store.py | M (-340行) | M (-914行) | 生产基线 | 证据存储 | REJECT | 不回收 | 分支2删除914行；main已有更完整版本 |
| evidence_api.py | M | M | 存在 | 证据API | LOW | 不回收 | 删减 |
| app_evidence.py | M | M | 存在 | 应用证据 | LOW | 不回收 | 删减 |
| evaluation_system.py | — | M (-12行) | 存在 | 评估系统 | LOW | 不回收 | 小幅删减 |
| data_quality_gate.py | — | M (-47行) | 存在 | 数据质量门 | REJECT | 不回收 | 删除47行数据质量检查逻辑 |
| canonical_data.py | M | — | 存在 | 规范化数据 | LOW | 不回收 | 删减 |

### 2.7 运维与运行时修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| runtime_guardian.py | M (-308行) | — | 存在 | 运行时守护 | REJECT | 不回收 | 删除308行守护逻辑 |
| runtime_preflight.py | M | M | 存在 | 运行前检查 | LOW | 不回收 | 删减 |
| resident_health.py | M | M | 存在 | 常驻健康检查 | LOW | 不回收 | 删减 |
| stability_monitor.py | M | M | 存在 | 稳定性监控 | LOW | 不回收 | 删减 |
| monitoring.py | M | M | 存在 | 监控 | LOW | 不回收 | 删减 |
| system_health_api.py | M | M | 存在 | 系统健康API | LOW | 不回收 | 删减 |
| system_guardian.py | — | M (-37行) | 存在 | 系统守护 | LOW | 不回收 | 删减 |
| system_watchdog.py | — | M (-6行) | 存在 | 系统看门狗 | LOW | 不回收 | 小幅删减 |
| auto_recovery.py | M | M | 存在 | 自动恢复 | LOW | 不回收 | 删减 |
| engineering_metrics.py | M | M | 存在 | 工程指标 | LOW | 不回收 | 删减 |
| security_scanner.py | M | M | 存在 | 安全扫描器 | LOW | 不回收 | 删减 |
| function_registry.py | M | — | 存在 | 函数注册 | LOW | 不回收 | 删减 |
| skill_registry.py | M | — | 存在 | Skill注册 | LOW | 不回收 | 删减 |

### 2.8 Collector Guard 修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| collector_guard/__init__.py | M | M | 存在(15文件完整版) | 采集守护包 | LOW | 不回收 | main有更完整版本(含metrics.py/rate_limiter.py/resource_guard.py/risk_engine.py/schedule_adapter.py/state.py) |
| collector_guard/checkpoint.py | M | M | 存在 | 检查点 | LOW | 不回收 | 删减 |
| collector_guard/dlq_replay.py | M | M | 存在 | 死信队列重放 | LOW | 不回收 | 删减 |
| collector_guard/guard.py | M | M | 存在 | 守护主逻辑 | LOW | 不回收 | 删减 |
| collector_guard/queue_worker.py | M | M | 存在 | 队列worker | LOW | 不回收 | 删减 |
| collector_guard/runtime_switch.py | M | M | 存在 | 运行时开关 | LOW | 不回收 | 删减 |
| collector_guard/task_queue.py | M | M | 存在 | 任务队列 | LOW | 不回收 | 删减 |

### 2.9 分支2独有：Collector V2 架构文件

| 文件名 | 变更类型 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|----------|----------|----------|----------|----------|----------|
| collector_v2/pipeline/normalize.py | M | 不存在此路径 | 笔记标准化器(繁简归一、空白清理、特殊字符移除) | LOW | 仅参考设计 | 硬编码繁简映射表(非OpenCC)；功能与main的canonical_data.py重叠；引用`..base`基类可能不存在 |
| collector_v2/pipeline/persist.py | M | 不存在此路径 | 笔记持久化器(去重、更新) | REJECT | 不回收 | 重复database.py已有能力；硬编码DB路径；无主体过滤 |
| collector_v2/xhs/collector.py | M | 不存在此路径 | V2 XHS采集器(异步、新账号保护、基类继承) | MEDIUM | 仅参考设计 | 架构设计可参考(采集与主体过滤分离、新账号保护模式)；但依赖XHSClient/PlatformCollector基类不存在于main；main的xhs_cdp_collector.py已是生产基线 |
| collector_v2_integration.py | M | 不存在 | V2采集集成层 | LOW | 不回收 | 集成代码，依赖不存在的V2模块 |

### 2.10 分支2独有：其他修改文件

| 文件名 | 变更类型 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|----------|----------|----------|----------|----------|----------|
| settings_module.py | M | 不存在 | 设置Blueprint(系统配置/账号管理/开发者工具/代码执行) | **REJECT(高危)** | 不回收 | **含开发者代码执行端点**；生产环境代码执行高危；配置文件硬编码路径 |
| dev_exec_core.py | M | 不存在 | 三run-code入口统一收口核心(审计+指纹+备份) | MEDIUM | 仅参考设计 | 安全加固模式可参考(代码指纹SHA256前12位、审计JSONL、备份后exec)；但代码执行本身在生产环境高危；main已有PermissionGate管控代码热更新 |
| brand_knowledge_base.py | M | 不存在 | 品牌知识库 | LOW | 不回收 | 删减/实验性 |
| case_ai_evaluate.py | M | 不存在 | 案例AI评估 | LOW | 不回收 | 实验性 |
| case_deep_analysis.py | M | 不存在 | 案例深度分析 | LOW | 不回收 | 实验性 |
| alert_engine.py | M | 不存在 | 告警引擎 | LOW | 不回收 | 删减 |
| report_export/report_engine.py | M | 不存在 | 报告导出引擎 | LOW | 不回收 | 与main的report_center/重叠 |
| export_report.py | M | 不存在 | 报告导出 | LOW | 不回收 | 与main的report_center/word_pdf_export.py重叠 |
| v4_upgrade/adapters/persist.py | M | 存在 | V4持久化适配器 | LOW | 不回收 | main已有更完整v4_upgrade/adapters/ |
| scripts/e2e_loop_check.py | M | 不存在 | E2E循环检查脚本 | LOW | 不回收 | 一次性脚本 |
| scripts/inventory/feature_crosscheck.py | M | 不存在 | 功能交叉检查 | LOW | 不回收 | 一次性审计脚本 |
| scripts/inventory/feature_final_verify.py | M | 不存在 | 功能最终验证 | LOW | 不回收 | 一次性审计脚本 |
| static/js/lumenis-core.js | M | 不存在 | LUMENIS核心JS | MEDIUM | 仅参考设计 | LUMENIS前端JS框架；与main的lumenis_frontend.py配合需评估 |
| .env.example | M | 存在 | 环境变量示例 | LOW | 仅参考 | 可能有新增配置键示例 |

### 2.11 KOS/传播主体修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| kos_attribution.py | M | M | 存在 | KOS归因 | LOW | 不回收 | 删减 |
| kos_engine.py | M | M | 存在 | KOS引擎 | LOW | 不回收 | 删减 |
| kos_metrics.py | M | M | 存在 | KOS指标 | LOW | 不回收 | 删减 |
| kos_routes.py | M | M | 存在 | KOS路由 | LOW | 不回收 | 删减 |

### 2.12 报告/事件/其他修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| report_api.py | M | M | 存在 | 报告API | LOW | 不回收 | 删减 |
| report_engine.py | M | M | 存在 | 报告引擎 | LOW | 不回收 | 删减 |
| report_artifact.py | M | — | 存在 | 报告artifact | LOW | 不回收 | 删减 |
| event_graph.py | M | M | 存在 | 事件图谱 | LOW | 不回收 | 删减 |
| topic_campaign.py | M | M | 存在 | 话题活动 | LOW | 不回收 | 删减 |
| public_opinion_cases.py | M | M | 存在 | 舆情案例 | LOW | 不回收 | 删减 |
| pr_case_integration.py | M | M | 存在 | PR案例集成 | LOW | 不回收 | 删减 |
| podcast_routes.py | M | M | 存在 | 播客路由 | LOW | 不回收 | 删减 |
| emv.py | M | M | 存在 |  earned media value | LOW | 不回收 | 删减 |
| reprocess.py | M | M | 存在 | 重处理 | LOW | 不回收 | 删减 |
| historical_data_importer.py | M | — | 存在 | 历史数据导入 | LOW | 不回收 | 删减 |
| populate_empty_tables.py | M | M | 存在 | 空表填充 | LOW | 不回收 | 删减 |
| database_migrations.py | M | M | 存在 | 数据库迁移 | LOW | 不回收 | 删减；需确认是否有新增迁移 |
| data_query_api.py | M | M | 存在 | 数据查询API | LOW | 不回收 | 删减 |
| ui_view_model.py | M | — | 存在 | UI视图模型 | LOW | 不回收 | 删减 |
| lumenis_frontend.py | M | M | 已集成 | LUMENIS前端Blueprint | LOW | 不回收 | main已有更完整版本(含domain_api_bp) |
| lumenis_agg_api.py | M | M | 已集成 | LUMENIS聚合API | LOW | 不回收 | main已有更完整版本 |
| lumenis_skill_adapter.py | M | M | 存在 | LUMENIS Skill适配器 | LOW | 不回收 | 删减 |
| browser_surface.py | M | M | 存在 | 浏览器表面 | LOW | 不回收 | 删减 |
| browser_surface_api.py | M | M | 存在 | 浏览器表面API | LOW | 不回收 | 删减 |
| internal_browser.py | M | M | 存在 | 内置浏览器 | LOW | 不回收 | 删减 |
| auth_recovery_api.py | M | M | 存在 | Auth恢复API | LOW | 不回收 | 删减；分支2提交"移除硬编码auth recovery DB路径"可能是唯一正向修改 |
| auth_recovery_center.py | M | M | 存在 | Auth恢复中心 | LOW | 不回收 | 删减 |
| provider_registry.py | M | M | 存在 | Provider注册 | LOW | 不回收 | 删减 |
| templates/base.html | M | M | 生产基线 | 基础模板 | LOW | 不回收 | 需确认是否引入lumenis CSS/JS引用 |
| static/js/lumenis-icons.js | M | M | 存在 | LUMENIS图标JS | LOW | 不回收 | 删减 |

### 2.13 平台适配器修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 能力描述 | 回收评级 | 回收方式 | 风险备注 |
|--------|-------|-------|----------|----------|----------|----------|----------|
| v4_upgrade/adapters/bilibili.py | M | M | 存在 | B站适配器 | LOW | 不回收 | main已有更完整版本 |
| v4_upgrade/adapters/cookie_vault.py | M | M | 存在 | Cookie保险库 | LOW | 不回收 | 删减 |
| v4_upgrade/adapters/registry.py | M | M | 存在 | 适配器注册 | LOW | 不回收 | 删减 |
| v4_upgrade/adapters/sogou_search.py | M | M | 存在 | 搜狗搜索 | LOW | 不回收 | 删减 |
| v4_upgrade/adapters/sogou_wechat.py | M | M | 存在 | 搜狗微信 | LOW | 不回收 | 删减 |
| v4_upgrade/adapters/weibo.py | M | M | 存在 | 微博适配器 | LOW | 不回收 | 删减 |
| v4_upgrade/adapters/x_platform.py | M | M | 存在 | X平台适配器 | LOW | 不回收 | 删减 |
| v4_upgrade/adapters/zhihu.py | M | M | 存在 | 知乎适配器 | LOW | 不回收 | 删减 |
| v4_upgrade/unified_logger.py | M | M | 存在 | 统一日志 | LOW | 不回收 | 删减 |
| platform_adapters/evidence_exporter.py | M | M | 存在 | 证据导出器 | LOW | 不回收 | 删减 |
| platform_adapters/rednote_policy.py | M | M | 存在 | RedNote策略 | LOW | 不回收 | 删减 |
| ad_intelligence/platforms/jiguang.py | M | M | 存在 | 极光广告平台 | LOW | 不回收 | main已有更完整ad_intelligence/ |
| ad_intelligence/platforms/meta_ads.py | M | M | 存在 | Meta广告 | LOW | 不回收 | 删减 |
| ad_intelligence/platforms/ocean_engine.py | M | M | 存在 | 巨量引擎 | LOW | 不回收 | 删减 |
| ad_intelligence/platforms/x_ads.py | M | M | 存在 | X广告 | LOW | 不回收 | 删减 |
| ad_intelligence/permission_gate.py | — | M | 存在 | 广告智能权限门 | LOW | 不回收 | 删减 |

### 2.14 测试文件修改

| 文件名 | 分支1 | 分支2 | main状态 | 回收评级 | 风险备注 |
|--------|-------|-------|----------|----------|----------|
| tests/test_ad_platform_collectors.py | M | M | 存在(246测试) | LOW | 删减 |
| tests/test_ai_channel_multiprovider.py | M | M | 存在 | LOW | 删减 |
| tests/test_ai_evaluation.py | M | — | 存在 | LOW | 删减 |
| tests/test_ai_gateway.py | M | M | 存在 | LOW | 删减 |
| tests/test_ai_off_shardB.py | M | — | 存在 | LOW | 删减 |
| tests/test_browser_surface.py | M | M | 存在 | LOW | 删减 |
| tests/test_collect_state.py | M | M | 存在 | LOW | 删减 |
| tests/test_event_curation.py | M | M | 存在 | LOW | 删减 |
| tests/test_kos_attribution.py | M | M | 存在 | LOW | 删减 |
| tests/test_llm_gateway.py | M | M | 存在 | LOW | 删减 |
| tests/test_lumenis_frontend_foundation.py | M | M | 存在 | LOW | 删减 |
| tests/test_negative_event_api.py | M | M | 存在 | LOW | 删减 |
| tests/test_repository_registry.py | M | — | 存在 | LOW | 删减 |
| tests/test_security_scanner_s2.py | M | M | 存在 | LOW | 删减 |
| tests/test_t2_collection_chain.py | M | — | 存在 | LOW | 删减 |
| tests/test_v2_p0_modules.py | M | M | 存在 | LOW | 删减 |
| tests/test_ai_channel_flag.py | — | M | 存在 | LOW | 删减 |
| tests/test_ai_degrade.py | — | M | 存在 | LOW | 删减 |
| tests/test_compliance_gate.py | — | M | 存在 | LOW | 删减 |
| tests/test_evidence_exporter.py | — | M | 存在 | LOW | 删减 |
| tests/test_evidence_store.py | — | M | 存在 | LOW | 删减 |
| tests/test_kol_analysis.py | — | M | 存在 | LOW | 删减 |
| tests/test_report_special.py | — | M | 存在 | LOW | 删减 |
| tests/test_resource_guard.py | — | M | 存在 | LOW | 删减 |
| tests/test_schedule_adapter.py | — | M | 存在 | LOW | 删减 |
| tests/test_topic_snapshot.py | — | M | 存在 | LOW | 删减 |

### 2.15 文档/配置/CI修改文件

| 文件名 | 分支1 | 分支2 | main状态 | 回收评级 | 风险备注 |
|--------|-------|-------|----------|----------|----------|
| .github/workflows/platform-verify.yml | M | M | 存在 | LOW | CI配置修改 |
| .gitignore | M | M | 存在 | LOW | 可能新增忽略规则 |
| CHANGELOG.md | M | M | 存在 | LOW | 变更日志 |
| 00-GOVERNANCE/feature_registry.csv | M | — | 存在 | LOW | 功能注册表 |
| 00-GOVERNANCE/feature_registry.md | M | — | 存在 | LOW | 功能注册文档 |
| README.md | — | M | 存在 | LOW | 分支2对齐product convergence |
| .env.example | — | M | 存在 | LOW | 环境变量示例 |
| THIRD_PARTY_LICENSE_AUDIT.md | — | M | 存在 | LOW | 第三方许可证审计 |
| 00-GOVERNANCE/LUMENIS-PRODUCT-CONVERGENCE-MASTER-V1-20260906.md | — | M | 不存在 | LOW | product convergence主基线文档 |
| CHANGELOG/2026-09-06-LUMENIS-PRODUCT-CONVERGENCE.md | — | M | 不存在 | LOW | product convergence变更日志 |

---

## 3. HIGH价值回收项详细说明

### 3.1 LUMENIS 设计系统与 UI 模板（评级：MEDIUM，非HIGH）

**涉及文件**：static/css/lumenis-*.css (8-11个)、templates/intelligence/*.html、templates/operations/*.html、templates/production/*.html、templates/research/*.html、static/js/lumenis-core.js (分支2)

**Diff摘要**：
- 完整的LUMENIS设计token体系(CSS变量：颜色、间距、字体、圆角、阴影)
- 组件库：card、grid、table、badge、status、metric、form等
- 18个页面模板：Agent Center、Evaluation、Evidence、Models、Skill Hub、Workspace、Permissions、Repository、Runtime、Overview、Monitoring、Public Opinion、Risk、Reports、Cases、Findings、Research Workspace、Command Home
- 所有模板使用`data-field`占位符 + `LUMENIS.i18n`国际化，依赖后端API填充

**为什么有效**：
- main已集成lumenis_frontend.py Blueprint和lumenis_agg_api.py，但前端页面模板可能不完整
- 设计系统的token和组件规范有参考价值
- Permissions页面与main的PermissionGate Phase12可形成前后端配合

**如何集成（仅参考，不cherry-pick）**：
1. 对比main的lumenis-global-design.css与分支的lumenis-tokens.css，提取缺失的CSS变量
2. 评估templates/operations/permissions.html是否可作为PermissionGate的管理前端
3. 所有模板需先在`/lumenis/`旁路路由下验证，不得进入生产路由
4. 需确认`static/js/lumenis-core.js`(分支2)与main现有JS的兼容性

**风险**：
- 模板均为UI壳，无真实数据绑定
- CSS类名可能与main现有样式冲突
- 需评估lumenis_frontend.py是否已注册这些模板路由

### 3.2 dev_exec_core.py 安全加固模式（评级：MEDIUM，仅参考设计）

**涉及文件**：dev_exec_core.py (分支2独有)

**Diff摘要**：
- 统一三个run-code入口(/api/developer/run、/api/config/run-code、/api/dev/run-code)的执行核心
- 代码指纹：仅存储长度+SHA256前12位，绝不存全文
- 审计日志：data/audit/dev_exec_audit.jsonl (JSONL格式)
- 备份后exec模式
- 端点1保持永久403禁用

**为什么有效**：
- main已有PermissionGate管控代码热更新(OperationType.RUNTIME_OPERATION, RiskLevel.CRITICAL)
- 但代码执行的审计粒度(指纹、allow/deny全记录)有参考价值
- "不存全文只存指纹"的设计符合密钥保护原则

**如何集成（仅参考设计）**：
1. 将代码指纹+审计JSONL模式融入main的PermissionGate审计层
2. 三入口统一收口的架构可参考，但main可能已不需要多入口
3. 端点1永久403的设计已在main中通过PermissionGate fail-closed实现

**风险**：
- 代码执行本身在生产环境高危，不得因参考此模块而开放执行端点
- main的PermissionGate Phase12已是更严格的管控方式

### 3.3 zbc_phase11_audit.py 模块审计方法论（评级：MEDIUM，仅参考设计）

**涉及文件**：zbc_phase11_audit.py (分支1独有, 721行)

**Diff摘要**：
- 单文件全量模块审计：AST扫描所有.py文件
- 分类体系：COLLECTOR/RISK/AI/EVIDENCE/REPORT/API/OPERATIONS/UI/SECURITY等
- 输出module_inventory.md + module_inventory.json
- 函数级统计、import分析、复杂度评估

**为什么有效**：
- main已有security_scanner.py和audit/目录，但模块级全量审计方法论可参考
- 分类体系与AGENTS.md的P0/P1/P2优先级可对应

**如何集成（仅参考设计）**：
1. 提取AST扫描+分类逻辑，融入main的audit/工具链
2. 输出格式(module_inventory)可作为功能注册表的数据源
3. 不得直接运行(硬编码路径、可能与main结构不匹配)

---

## 4. REJECT 清单及原因

### 4.1 违反生产红线的 REJECT（最高优先级）

| 文件/能力 | 分支 | 违反红线 | 具体原因 |
|-----------|------|----------|----------|
| subject_context.py | 分支1 | CTH与ZBMP双域隔离不可破坏 | **删除X-Domain-Id/X-Product-Id请求头解析、DomainContext线程上下文、CTH domain_id强制保护**；将双域(brand+domain)降为单域(brand only) |
| subject_rules.py | 分支2 | SUBJECT语义不可变 | **移除线程级SubjectContext三级优先级链**(thread context→env var→CTH default)，弱化为单次get_subject_context()；潜在主体口径泄漏 |
| database.py | 两分支 | SQLite为Production Truth / 数据精准性 | **移除_db_connect_with_retry()指数退避**，并发下易出现database is locked；分支2额外移除Phase9报告artifact字段(report_id/artifact_hash/generator_version/data_version/source_snapshot)，破坏数据溯源 |
| collector.py | 两分支 | 采集主链路P0 / 小红书官方账号只读 | **移除RedNote策略旁路、双CDP(9222大陆/9223港版)、region参数**；分支2额外移除Runtime Guardian和CollectState集成；严重削弱多区域多通道采集能力 |
| monitor_pipeline.py | 两分支 | 主体口径P0 / AI不得单独决定 | 调用`ai_analyzer.verify_taikoo_location()`替代正式`subject_hit()`主体过滤；AI验证绕过生产主体口径 |
| 全部1438/1586个删除文件 | 两分支 | 禁止删除旧实现 | 大规模删除包括account/(15文件)、ai_agent_registry.py、ai_browser_api.py、ai_browser_runtime.py、ai_domain_context.py、ai_evaluation.py、ai_task_engine.py、evidence_chain.py(分支2)、historical_data_importer.py、canonical_data.py、acceptance_evidence_chain.py、acceptance_gate.py、agent_boundary.py、api_dual_domain.py、badge_api.py、brand_propagation.py、collection_quality_gate.py、collector_status_api.py、content_generation.py、core/repository_registry.py、data_center_api.py、domain_adapter.py、dual_account_rotation.py、evaluation_dimensions.py、evaluation_recorder.py、evaluation_runner.py、human_correction.py等真实能力文件 |

### 4.2 核心模块大幅删减的 REJECT

| 文件 | 分支1删行 | 分支2删行 | 原因 |
|------|-----------|-----------|------|
| app.py | -586 | -715 | 主应用大幅删减；含裸except吞异常；main已有更完整版本 |
| risk_engine.py | -880 | -880 | 风险规则删除880行；风险判断能力严重削弱 |
| ai_channel.py | -454 | -560 | AI传输层删减；main已有完整多Provider故障转移 |
| evidence_chain.py | -195 | -1167 | 证据链几乎全删(分支2)；main已有完整版本 |
| evidence_store.py | -340 | -914 | 证据存储大幅删减 |
| permission_gate.py | -108 | -991 | 权限系统几乎全删(分支2)；main已有Phase12 fail-closed |
| runtime_guardian.py | -308 | — | 运行时守护删除308行 |
| domain_isolation.py | -150 | -150 | 域隔离删除150行 |
| daily_report.py | -181 | -191 | 日报逻辑大幅删减 |
| wechat_notifier.py | -302 | -302 | 微信通知删除302行 |
| ai_governance.py | -313 | -317 | AI治理大幅删减 |

### 4.3 高危功能 REJECT

| 文件 | 分支 | 原因 |
|------|------|------|
| settings_module.py | 分支2 | **含开发者代码执行端点**；生产环境代码执行高危；配置硬编码路径 |
| collector_v2/pipeline/persist.py | 分支2 | 重复database.py能力；无主体过滤；硬编码DB路径 |

### 4.4 重复/过时 REJECT

| 文件/能力 | 分支 | 原因 |
|-----------|------|------|
| 所有collector_guard/*.py修改 | 两分支 | main已有15文件完整版(含metrics/rate_limiter/resource_guard/risk_engine/schedule_adapter/state)，分支只有6文件删减版 |
| 所有v4_upgrade/adapters/*.py修改 | 两分支 | main已有完整v4_upgrade/子目录体系(adapters/ai_hub/auth/collect/console/data_cleanup/importer/report_center/settings/version_center/zbmp)，分支只有零散文件 |
| 所有ad_intelligence/platforms/*.py修改 | 两分支 | main已有完整ad_intelligence/(analytics/models/platforms/strategy + permission_gate.py + platform_registry.py) |
| 所有测试文件修改 | 两分支 | main已有246个测试文件，分支版本均为删减 |
| check_collection.py / check_collection_detail.py | 两分支 | 与main的system_health_api.py功能重叠；硬编码路径 |
| export_report.py / report_export/report_engine.py | 分支2 | 与main的report_center/word_pdf_export.py重叠 |

---

## 5. 建议的回收优先级排序

### 5.1 总体建议：不进行任何 cherry-pick，仅做设计参考

**理由**：
1. 两个分支均基于2026-09-06的旧基线，main已在2026-09-07演进至更完整状态
2. 所有核心模块修改均为净删除，无任何新增能力超越main
3. 存在多处生产红线违反(双域隔离删除、主体口径弱化、DB重试移除、大规模删除旧实现)
4. 新增文件均为工具脚本或UI壳，无核心业务能力

### 5.2 如确需参考，按以下优先级

| 优先级 | 项目 | 方式 | 预期工作量 | 风险 |
|--------|------|------|-----------|------|
| P1(可选) | LUMENIS设计token提取 | 人工对比lumenis-tokens.css与main的CSS变量，提取缺失项融入lumenis-global-design.css | 2-4小时 | 低(纯CSS) |
| P2(可选) | Permissions UI模板评估 | 评估templates/operations/permissions.html是否可作为PermissionGate管理前端，在/lumenis/旁路验证 | 4-8小时 | 中(需后端API配合) |
| P3(可选) | dev_exec_core审计模式 | 将代码指纹+审计JSONL模式融入main的PermissionGate审计层 | 4-6小时 | 中(不得开放执行端点) |
| P4(可选) | zbc_phase11_audit方法论 | 提取AST扫描+分类逻辑，融入main的audit/工具链 | 6-8小时 | 低(只读工具) |
| P5(不建议) | collector_v2架构参考 | 参考采集与主体过滤分离、新账号保护模式设计 | 8+小时 | 高(需重构采集主链路) |
| — | 所有其他文件 | 不回收 | — | — |

### 5.3 明确禁止的操作

1. **禁止** cherry-pick 任何分支的 app.py / database.py / collector.py / risk_engine.py / subject_context.py / subject_rules.py
2. **禁止** 恢复任何分支的删除文件(这些文件在main中仍存在，分支删除是错误操作)
3. **禁止** 引入 monitor_pipeline.py (AI验证绕过主体过滤)
4. **禁止** 引入 settings_module.py (含代码执行端点)
5. **禁止** 以任何形式将分支代码合并入main

---

## 6. 附录：审计方法与数据来源

### 6.1 审计命令

```powershell
# 分支概览
git diff --stat main..feat/zbc-full-upgrade-v1
git diff --stat main..origin/feat/lumenis-product-convergence

# 文件变更清单
git diff --name-status main..feat/zbc-full-upgrade-v1
git diff --name-status main..origin/feat/lumenis-product-convergence

# 关键文件diff
git diff main..<branch> -- <file>

# 分支内容读取(不切换分支)
git show <branch>:<file>
```

### 6.2 数据来源

- 分支1文件清单：audit/_tmp_branch1_files.txt (1595行)
- 分支2文件清单：audit/_tmp_branch2_files.txt (1757行)
- main当前状态：46502f11, working tree clean
- 所有审查通过git diff/git show只读完成，未切换分支，未修改任何文件

### 6.3 审计局限性

1. 未执行分支代码(可能存在运行时才能发现的问题)
2. 未对比每个文件的完整diff(重点关注核心模块和新增文件)
3. 模板/CSS的视觉效果未在浏览器中验证
4. 测试文件的具体断言变更未逐一分析
5. 数据库迁移脚本的具体SQL变更未逐一验证

---

*审计完成时间：2026-09-07*
*审计结论：两分支整体回收价值极低，不建议任何cherry-pick，仅可做设计参考*
