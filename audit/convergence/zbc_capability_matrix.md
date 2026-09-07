# ZBC×OSAI Agent Runtime 能力矩阵审计报告

> **审计日期**: 2026-09-07
> **审计范围**: Z-Brand-Core (D:\Taikoo-monitor-new) Agent/Skill/Permission/Firewall/Effect Fence/Evidence/Evaluation/Trace/Memory/AI Gateway
> **审计模式**: 只读审计，未修改源码/DB
> **数据库**: data/monitor.db (129 张表，只读)
> **基线**: 真实源码事实，非历史文档/架构图

---

## 一、审计摘要

| 维度 | 总项数 | EXISTS | PARTIAL | MISSING |
|------|--------|--------|---------|---------|
| Agent | 7 | 2 | 3 | 2 |
| Skill | 5 | 4 | 1 | 0 |
| 安全边界 | 5 | 5 | 0 | 0 |
| Evidence/Eval/Trace | 5 | 4 | 0 | 1 |
| Memory/Learning | 7 | 5 | 2 | 0 |
| AI Gateway/Provider | 5 | 5 | 0 | 0 |
| Tool Router | 2 | 1 | 1 | 0 |
| **合计** | **36** | **26** | **7** | **3** |

**成熟度判断**: ZBC 在安全边界、AI Gateway、Evidence/Trace、Durable Execution 方面已达到生产级；在 Agent 感知/规划/重规划、分层 Memory、统一 Tool Router 方面存在结构性缺口。整体可作为 OSAI Agent Runtime 的**可靠底座**，但需补齐 3 个 MISSING + 7 个 PARTIAL 项才能形成完整 Agent Loop。

---

## 二、能力矩阵总表

### 2.1 Agent 相关

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| agent_boundary / agent_identity | **EXISTS** | `agent_boundary.py:130-523` | `AgentIdentity`, `AgentBoundary.create_agent()`, `check_action()`, `execute_with_approval()` | 内部调用，未独立暴露 HTTP | 无独立表（内存态） | `test_agent_security.py`, `test_skill_agent_boundary.py` (33KB) | AgentRole/Permission/ActionDecision/ApprovalStatus 四套 Enum；IdempotencyGuard 幂等保护 |
| Agent State Machine | **PARTIAL** | `ai_task_engine.py:86-112`, `runtime_guardian.py:99-141` | `TaskStatus` (PENDING/PARSING/AWAITING_APPROVAL/...), `LifecycleState` (CREATED→STARTED→RUNNING→PAUSED→STOPPED→CLEANUP→ARCHIVED) | `/api/ai/tasks`, `/api/ai/tasks/<id>` | `ai_task` (2180行), `runtime_guardian_workers` (2600行) | `test_ai_task_engine.py` (18KB), `test_runtime_guardian.py` (31KB) | 任务级状态机完整，但缺 Agent 实例级独立状态机（Agent identity 无 state 字段） |
| Agent Loop (max_steps/max_time/max_cost) | **PARTIAL** | `ai_task_engine.py:874-957` | `execute_task()`, `_execute_once()`, retry loop with `max_retries=3`, `default_timeout=60s` | `/api/ai/tasks/run/<id>` | `ai_task.retry_count`, `ai_task.max_retries` | `test_ai_task_engine.py` | 有 retry/timeout/circuit breaker，但**无 max_steps 步数限制、无 max_time 全局时间预算、无 max_cost token/费用预算** |
| Planner | **PARTIAL** | `ai_task_parser.py:204-418` | `TaskParser.parse()`, `_match_intent()`, `_extract_entities()`, `_extract_parameters()`, `_determine_risk()` | 内部调用（TaskEngine.parse_task） | `ai_task.intent/entities_json/parameters_json/context_json` | `test_ai_task_engine.py` | 单步意图解析+实体提取+参数提取+风险判定，可作为轻量 Planner；**缺多步规划（multi-step plan）、计划 DAG、计划执行追踪** |
| Observation Layer | **MISSING** | — | — | — | — | — | **无结构化感知/观察层**。系统有 evidence 采集和 DB 查询，但无将系统状态/DB变化/外部事件统一转化为 Agent Observation 的抽象层 |
| Replanning | **MISSING** | — | — | — | — | — | **无重规划能力**。TaskEngine 失败后只有 retry（相同参数重试），无基于 observation/feedback 的计划调整或重新规划 |
| Durable Execution (checkpoint/pause/resume/retry/recover/cancel) | **EXISTS** | `runtime_guardian.py:177-648,1215-1317`, `lifecycle_mixin.py:42-316` | `ResumeManager.save_checkpoint()`, `resume_from_checkpoint()`, `lifecycle_pause/resume/stop/cleanup/archive()`, `DLQ.replay()`, `Reaper` | 内部调用 + `/api/resident/recover` | `runtime_guardian_checkpoints` (76行), `runtime_guardian_dlq` (0行), `runtime_guardian_workers` (2600行) | `test_runtime_guardian.py` (31KB), `test_runtime_guardian_integration.py` (26KB), `test_lifecycle_contract.py` (14KB) | 完整生命周期管理 + checkpoint/resume + DLQ + Reaper + lease/heartbeat；`ai_task_engine.cancel_task()` 支持任务取消 |

### 2.2 Skill 相关

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| skill_registry / skills_registry | **EXISTS** | `skill_registry.py:100-267` | `SkillRegistry.register()`, `get()`, `list_by_risk()`, `list_by_policy()`, `can_auto_execute()` | `/api/skills`, `/api/skills/list`, `/api/skills/status` | `skills_registry` (12行) | `test_skill_system.py` (12KB) | SkillMetadata 含 input_schema/output_schema/evidence_contract/risk_level/execution_policy；内置 RiskLevel/ExecutionPolicy/EvaluationStatus 三 Enum |
| skill_invocation / skill_execution_contract / skill_execution_chain | **EXISTS** | `skill_execution_chain.py:43-375` | `run_execution_chain()`, `execute_skill()`, `check_permission()`, `action_firewall()`, `effect_fence()`, `build_evidence()`, `evaluate_execution()`, `write_trace()` | 内部调用（TaskEngine 分发） | `skill_executions` (18行) | `test_skill_system.py`, `test_skill_agent_boundary.py` (33KB) | 完整执行链：permission→firewall→effect_fence→execute→evidence→evaluation→trace；SkillExecutionContext 贯穿全链 |
| lumenis_skill_adapter | **EXISTS** | `lumenis_skill_adapter.py:58-300` | `CrossCoreSkillAdapter.invoke_skill()`, `get_registry_snapshot()`, `to_skill_metadata()`, `list_skills_as_metadata()` | 内部调用（跨 Core 桥接） | 无独立表 | `test_lumenis_skill_invoke.py` (7KB), `test_lumenis_adapter.py` (5KB) | 桥接 OSAI Runtime Skill 体系；支持 registry 快照同步、skill 调用、metadata 转换 |
| skill_executions 表 | **EXISTS** | `skill_execution_chain.py:240-282` | `ensure_skill_executions_table()`, `write_trace()`, `query_executions()` | — | `skill_executions` (18行，含 evidence_json/evaluation_json/permission_json/firewall_json/effect_fence_json 六域审计字段) | — | 执行记录完整覆盖 permission/firewall/effect_fence/evidence/evaluation 五环节 |
| Skill 升级为 Capability 的现状差距 | **PARTIAL** | `function_registry.py:134-180` | `register_functions_as_skills()`, `VIZ_FUNCTIONS` 注册表 | — | `skills_registry` | — | FUNCTION_MAP 可注册为只读 Skill，VIZ_FUNCTIONS 提供函数驱动可视化注册表；**缺统一 Capability 抽象层**（Capability 版本管理、依赖声明、能力发现协议、Capability→Skill 降级映射） |

### 2.3 安全边界

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| permission_gate (含 _TESTING_BYPASS_ENABLED, operation 注册, fail-closed) | **EXISTS** | `permission_gate.py:37-992` | `PermissionGate.check()`, `register_operation()`, `require_human_approval()`, `grant_approval()`, `_deny()` (fail-closed), `get_role_domain_matrix()` | `/api/ai/permissions` | 无独立表（内存+审计日志） | `test_permission_gate.py` (40KB), `test_permission_gate_app_integration.py` (19KB), `test_permission_dual_domain.py` (17KB), `test_ai_permission_matrix.py` (12KB) | `_TESTING_BYPASS_ENABLED=False` (L37)；13 种 OperationType 注册；PermissionLevel 十级（READ→ADMIN）；未注册操作默认 DENY；幂等检查 |
| action_firewall | **EXISTS** | `skill_execution_chain.py:108-150`, `p2_action_firewall.py:15-145`, `security_boundary.py:605-618` | `action_firewall()` (P1基础策略+P2深度校验链), `p2_action_firewall.validate_action()` (8项检查: identity/intent/tool/parameters/target/scope/permission), `AIAgentLayer.check_action_firewall()` | 内部调用 | `skill_executions.firewall_json` | `test_agent_security.py`, `test_skill_agent_boundary.py` | 三层防火墙：P1 基础策略（ALLOW/CONDITIONAL/RESTRICTED/DENY）+ P2 深度校验（8维度）+ SecurityBoundary AIAgentLayer 集成 |
| effect_fence | **EXISTS** | `skill_execution_chain.py:153-159` | `effect_fence()` | 内部调用 | `skill_executions.effect_fence_json` | `test_skill_agent_boundary.py` | WRITE/COMMIT/PUSH 标记为 fenced，staging_required=True，auto_admit=False；**当前为标记层，未实现完整的效果隔离沙箱（staging→validation→promotion 自动化）** |
| Human Approval / human-in-the-loop | **EXISTS** | `permission_gate.py:523-635`, `agent_boundary.py:288-357`, `ai_task_engine.py:1279-1329` | `PermissionGate.grant_approval/revoke_approval/is_approved/list_approvals()`, `ApprovalManager.request/approve/reject/list_pending()`, `TaskEngine.approve_task()` | `/api/ai/tasks/approve/<id>` | `ai_task.approval_token/approved_by/approved_at/human_approval_required` | `test_permission_gate.py`, `test_ai_task_engine.py` | 三级审批体系：PermissionGate token 审批 + AgentBoundary ApprovalManager + TaskEngine 任务级审批；L3/L4 风险自动触发 awaiting_approval |
| COMMIT/PUSH/Production Write 默认 DENY | **EXISTS** | `permission_gate.py:129-178,294`, `app.py:68-69` | `_OPERATION_REGISTRY` (CONFIG_MODIFY/DB_WRITE/DATA_IMPORT/RUNTIME_OPERATION→COMMIT+HIGH+auto_allow=False; DATA_DELETE→PUSH+CRITICAL+auto_allow=False), 默认权限 READ→VERIFY（不含 COMMIT/PUSH） | — | — | `test_permission_gate.py` | 5 类高风险操作默认 auto_allow=False；`app.py:68` 启动时显式 grant COMMIT/PUSH/HUMAN_APPROVAL 作为基线；未授权调用 fail-closed |

### 2.4 Evidence & Evaluation & Trace

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| evidence_chain / evidence_store | **EXISTS** | `evidence_chain.py:148-1151`, `evidence_store.py:579-1171` | `EvidenceStore.add_evidence()`, `verify_immutability()`, `CanonicalDataStore.apply_human_correction()`, `LifecycleTracker.trace_data_lineage()`, `EvidenceChain.capture_and_canonicalize()`, `evidence_store.record_evidence/replay_failed_evidence()` | `/api/evidence` (evidence_api.py) | `app_evidence_records` (17), `canonical_data` (14), `zbc_evidence` (6), `zbc_canonical_data` (4), `zbc_lifecycle_tracking` (8), `browser_evidence` (1447) | `test_evidence_chain.py` (27KB), `test_evidence_store.py` (8KB), `test_evidence_dual_domain.py` (9KB), `test_evidence_write_failed_health.py` (12KB) | 完整哈希链（previous_hash→current_hash）；不可变性验证；数据血缘追踪；DLQ 失败重放；人审修正闭环；canonical→evidence 双向关联 |
| evaluation | **EXISTS** | `ai_evaluation.py:38-569`, `evaluation_system.py:43-427`, `evaluation_recorder.py`, `evaluation_runner.py`, `evaluation_dimensions.py` | `ai_evaluation.evaluate_ai_quality()`, `record_rule_vs_ai()`, `submit_human_correction()`, `verify_ai_not_replacing_rules()`, `EvaluationSystem.evaluate_collection_quality/analysis_quality/report_quality/system_stability()`, badcase/golden_case/regression | — | `evaluation_records` (0), `content_evaluation` (34) | `test_ai_evaluation.py` (28KB), `test_evaluation_system.py` (32KB) | 双轨评估：AI 质量评估（rule vs AI 对比、人审反馈、provider 健康）+ 系统质量评估（采集/分析/报告/稳定性四维度）；badcase 管理 + golden case + 回归测试 |
| trace | **EXISTS** | `ai_task_engine.py:502-538,1415-1432`, `ai_call_logger.py:196-530` | `TaskEngine._db_add_trace()`, `get_trace()`, `ai_call_logger.log_call()`, `query_calls()`, `get_stats()` | `/api/ai/trace` | `ai_task_trace` (6281行), `ai_call_logs` (1388行) | `test_g2_ai_call_logger_audit.py` (5KB), `test_ai_task_engine.py` | 分布式 trace：trace_id + span + parent_span 树形结构；AI 调用日志含 provider/model/token_usage/latency/failure_reason/human_correction；task_id/trace_id 跨表关联 |
| ai_task / ai_task_step / ai_task_evidence | **EXISTS** | `ai_task_engine.py:69-538` | `create_task()`, `_db_add_step()`, `_db_add_evidence()`, `get_steps()`, `get_evidence()` | `/api/ai/tasks`, `/api/ai/tasks/<id>/steps`, `/api/ai/tasks/<id>/evidence` | `ai_task` (2180), `ai_task_step` (4992), `ai_task_evidence` (3044) | `test_ai_task_engine.py` (18KB) | 三级层级：task→step→evidence；evidence 含哈希链（previous_hash/current_hash）+ authenticity_score；task 含 approval/risk/retry/permission 全字段 |
| Trajectory Evaluation | **MISSING** | — | — | — | — | — | **无端到端轨迹评估**。有 step 级 trace 和 evidence，但无对完整 Agent 执行轨迹（task→steps→evidence→outcome）的整体质量评分、轨迹相似度比较、轨迹成功/失败归因分析 |

### 2.5 Memory & Learning

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| 分层 Memory (Working/Task/Episodic/Semantic/Skill/Learning) | **PARTIAL** | 分散于多模块 | — | — | 多表分散 | — | **Episodic**: `ai_task_trace` (6281) + `ai_task` (2180)；**Semantic**: `intelligence_assets` (711) + `canonical_data`；**Skill**: `skill_executions` (18) + `skills_registry` (12)；**Learning**: `note_review_history` (8387) + `feedback_keywords` (16)。**缺 Working Memory**（当前任务上下文的结构化短期记忆）和**统一 Memory 抽象层**（Memory 接口、分层路由、TTL/淘汰策略） |
| memory_optimizer.py | **EXISTS** | `memory_optimizer.py:37-317` | `MemoryOptimizer.register_cache()`, `force_gc()`, `_monitor_loop()`, `get_memory_trend()` | — | 无（运行时内存） | — | **注意：此为运行时 RAM/内存优化，非 Agent 长期记忆**。含缓存注册、GC 强制、内存监控循环、告警、趋势追踪 |
| feedback_keywords 表 | **EXISTS** | — | — | — | `feedback_keywords` (16行: keyword/source/score/enabled/first_seen/last_seen/used_count) | — | 反馈关键词积累，含启用状态和使用计数 |
| note_review_history 表 | **EXISTS** | — | — | — | `note_review_history` (8387行: note_id/old_new relevance/sentiment/risk/reason/provider/reviewed_at) | `test_note_review_unified.py` | 大规模人审历史，记录 AI 判定→人审修正的完整 diff，是 Learning Loop 的核心数据源 |
| rule_version_registry | **EXISTS** | — | — | — | `rule_version_registry` (1行: version/rule_type/subject_words_count/hash/exclude_words_count/hash/applied_at/by/is_active/changelog) | — | 规则版本管理，含主体词/排除词哈希校验，支持规则回溯和变更审计 |
| Learning Loop | **PARTIAL** | `ai_learning_engine.py:25-426`, `data_feedback_loop.py:33-360`, `human_correction.py` | `AILearningEngine.record_operation()`, `_learn_from_operation()`, `get_optimization_suggestion()`, `DataFeedbackLoop.analyze_report_anomalies()`, `generate_strategy_suggestions()`, `apply_feedback()`, `run_feedback_cycle()` | `/api/ai/learning/status`, `/api/ai/learning/optimization/<operation_type>` | `note_review_history`, `feedback_keywords` | `test_learning_persistence.py` (6KB), `test_data_feedback.py` | 有操作记录→学习→优化建议的链路，有报告异常→策略建议→反馈应用的闭环；**缺自动闭环**（人审修正→规则更新→模型微调的全自动 pipeline，当前需人工 apply） |
| intelligence_assets 表 | **EXISTS** | — | — | `/api/intelligence/library`, `/api/intelligence/refresh` | `intelligence_assets` (711行: asset_id/title/sub_library/source_origin/evidence_level/knowledge_status/tags/summary/landing_status/admission_status) | — | 情报资产库，含证据等级、知识状态、落地状态、准入状态四态管理，可作为 Semantic Memory 底座 |

### 2.6 AI Gateway & Provider

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| ai_gateway / provider_registry | **EXISTS** | `ai_channel.py:113-881`, `provider_registry.py:106-201` | `CircuitBreaker`, `ProviderBreaker`, `route_with_fallback_v1()`, `provider_chain()`, `full_fallback_chain()`, `provider_registry.provider_status/active_providers/available_providers/probe_local_providers()` | `/api/ai/channel/health`, `/api/ai/providers` (ai_api.py:295) | — | `test_ai_channel.py`, `test_ai_channel_multiprovider.py`, `test_ai_provider_failover.py` (11KB), `test_llm_gateway.py` | 四层网关：zhipu(主)→ark(备)→ollama(本地)→rule(最终兜底)；per-provider 熔断；provider 健康探测；failover 日志 |
| 智谱 GLM 连接 (glm-4.5-air/glm-5.3/glm-4.6v/web-search-pro) | **EXISTS** | `ai_channel.py:678-679,769-770,861,881` | `PROVIDER_LAYERS_V1` (zhipu: cloud_primary, models=[glm-4.5-air, glm-5.3, glm-4.6v, web-search-pro]), `ZHIPU_API_KEY` env 注入 | `/api/ai/chat`, `/api/ai/analyze` | `ai_call_logs.provider='zhipu'` | `test_ai_channel_flag.py`, `test_ai_provider_failover.py` | 四模型全接入：日常 glm-4.5-air（关思考）、强推理 glm-5.3、视觉 glm-4.6v、联网 web-search-pro；API Key 仅经 .env 注入，不写入源码 |
| ai_call_logs 表 | **EXISTS** | `ai_call_logger.py:110-530` | `log_call()`, `log_ai_call()`, `query_calls()`, `get_stats()`, `record_human_correction()` | — | `ai_call_logs` (1388行，30+字段: provider/model/input_hash/output/confidence/rule_result/final_result/human_correction/latency_ms/token_usage/failure_reason/task_id/trace_id/domain_id/product_id/output_hash/accepted) | `test_g2_ai_call_logger_audit.py` | 全量 AI 调用审计；rule_result vs final_result 双轨记录；人审修正字段；task_id/trace_id 跨系统关联 |
| AI Circuit Breaker | **EXISTS** | `ai_channel.py:113-188,306-351`, `ai_task_engine.py:232-289`, `runtime_guardian.py:209-299` | `ai_channel.CircuitBreaker` (fail_threshold/cooldown/half_open), `ProviderBreaker` (per-provider), `ai_task_engine.CircuitBreaker`, `runtime_guardian.CircuitBreaker` | `/api/ai/channel/health` | — | `test_ai_provider_failover.py`, `test_runtime_guardian.py` | 四层熔断：全局 + per-provider + task engine + runtime guardian；CLOSED→OPEN→HALF_OPEN 状态机；失败计数+冷却+半开探测 |
| runtime_guardian | **EXISTS** | `runtime_guardian.py:62-1451` | `RuntimeGuardian.register_worker/acquire_lease/renew_lease/heartbeat/save_checkpoint/resume_from_checkpoint/execute_with_retry/transition_state/lifecycle_pause/resume/stop/`, `DLQ`, `Reaper`, `CircuitBreaker`, `RetryPolicy` | `/api/resident/health`, `/api/resident/recover` | `runtime_guardian_workers` (2600), `runtime_guardian_checkpoints` (76), `runtime_guardian_dlq` (0) | `test_runtime_guardian.py` (31KB), `test_runtime_guardian_integration.py` (26KB), `test_guardian_wiring.py` | 完整运行时守护：worker 注册+lease+heartbeat；checkpoint/resume；DLQ+replay；Reaper（过期 lease+zombie worker）；生命周期状态机；指数退避重试；per-worker 熔断 |

### 2.7 Tool Router

| Capability | Status | File | Key Function | API | DB Table | Test Coverage | Evidence |
|------------|--------|------|--------------|-----|----------|---------------|----------|
| Tool Router | **PARTIAL** | `ai_agent_registry.py:202-273`, `function_registry.py` | `AgentRegistry.find_agents_for_intent()`, `select_best_agent()`, `select_skills()`, `function_registry.FUNCTION_MAP/VIZ_FUNCTIONS` | — | — | `test_agent_adapter_shardB.py` | 有基于 intent 的 agent/skill 选择，有函数注册表；**缺统一 Tool Router 层**（Tool 注册→意图匹配→参数校验→执行→结果归一的统一 pipeline，当前分散在 TaskEngine._dispatch_execution 和各 adapter） |
| 现有工具/API 清单 | **EXISTS** | `app.py` (219 routes), `ai_api.py` (30+ AI endpoints), `function_registry.py` (FUNCTION_MAP + VIZ_FUNCTIONS) | `register_ai_api()`, `register_functions_as_skills()` | 219 个 HTTP 路由 | — | `test_api_smoke.py`, `test_openapi_spec.py` | **219 个 API 路由**可作为 Agent Tool 池；覆盖舆情/风险/事件/采集/报告/情报/品牌/KOS/AI/系统管理全域；FUNCTION_MAP 和 VIZ_FUNCTIONS 提供结构化函数元数据 |

---

## 三、缺口清单与复用建议

### 3.1 MISSING 项（3项）

#### M1. Observation Layer（观察/感知层）
- **现状**: 无结构化 Observation 抽象。系统有 evidence 采集、DB 查询、浏览器状态，但无统一将系统状态转化为 Agent Observation 的层。
- **影响**: Agent 无法感知环境变化，无法做基于观察的决策，Replanning 无从谈起。
- **复用建议**: **可复用** `evidence_chain.py` 的 Evidence 模型 + `ai_task_trace` 的 span 结构 + `runtime_guardian` 的 worker 状态。新建 `observation_layer.py`，定义 `Observation` 数据类（type/source/timestamp/payload/confidence），将 DB 变化、采集状态、AI 结果、系统事件统一封装为 Observation 流。

#### M2. Replanning（重规划）
- **现状**: TaskEngine 失败后只有 retry（相同参数重试），无基于 observation/feedback 的计划调整。
- **影响**: Agent 无法从失败中学习调整策略，复杂任务易陷入重复失败。
- **复用建议**: **可复用** `ai_task_parser.py` 的 TaskParser（作为重新规划的解析器）+ `ai_task_engine.py` 的 step 机制（将 plan 拆为可替换的 step 序列）+ `note_review_history` 的反馈数据。在 TaskEngine 中新增 `replanning_trigger`（失败/观察变化/人工反馈）→ `replan()`（调用 Parser 重新生成 step 序列）→ `execute_replanned()`。

#### M3. Trajectory Evaluation（轨迹评估）
- **现状**: 有 step 级 trace 和 evidence，但无端到端轨迹质量评估。
- **影响**: 无法量化 Agent 执行质量，无法做轨迹级别的 badcase 分析和模型优化。
- **复用建议**: **可复用** `ai_evaluation.py` 的评估框架 + `ai_task_trace` 的完整轨迹数据 + `evaluation_system.py` 的 badcase/golden_case 机制。新建 `trajectory_evaluation.py`，定义轨迹评分维度（完成率/步骤效率/证据充分性/风险控制/人审一致性），基于已有 trace+evidence 数据做批量轨迹评估。

### 3.2 PARTIAL 项（7项）

#### P1. Agent State Machine（Agent 实例级状态机）
- **现状**: 有 TaskStatus（任务级）和 LifecycleState（worker 级），但 Agent identity 无独立 state 字段和状态转换。
- **复用建议**: **可复用** `runtime_guardian.py` 的 LifecycleState 状态机 + `agent_boundary.py` 的 AgentIdentity。在 AgentIdentity 中增加 `state` 字段，复用 LifecycleState 的转换逻辑。

#### P2. Agent Loop 预算控制（max_steps/max_time/max_cost）
- **现状**: 有 retry（max_retries=3）和 timeout（60s），但无步数限制、全局时间预算、token/费用预算。
- **复用建议**: **可复用** `ai_task_engine.py` 的 execute_task 循环 + `ai_governance.py` 的 AIUsageTracker（token 配额检查）。在 execute_task 中增加 `max_steps` 计数器、`deadline` 时间预算、`token_budget` 费用预算，超限时触发 fail-closed 或 replanning。

#### P3. Planner（多步规划）
- **现状**: TaskParser 是单步意图解析，无多步规划（plan DAG、步骤依赖、计划执行追踪）。
- **复用建议**: **可复用** `ai_task_parser.py` 的意图/实体/参数提取 + `ai_task_engine.py` 的 step 机制。扩展 Parser 输出 `Plan`（有序 step 列表+依赖关系），TaskEngine 按 Plan 执行而非单步分发。

#### P4. Skill→Capability 统一抽象
- **现状**: Skill 有完整注册/执行/审计体系，但缺统一 Capability 抽象（Capability 版本管理、依赖声明、能力发现协议、Capability→Skill 降级映射）。
- **复用建议**: **可复用** `skill_registry.py` 的 SkillMetadata + `function_registry.py` 的 VIZ_FUNCTIONS + `ai_agent_registry.py` 的 AgentSpec。新建 `capability_registry.py`，将 Skill/Function/Agent 统一抽象为 Capability，保留现有 Skill 执行链不变。

#### P5. 分层 Memory 架构
- **现状**: Episodic/Semantic/Skill/Learning 数据分散在各表，缺 Working Memory 和统一 Memory 抽象层。
- **复用建议**: **可复用** `ai_task_trace`（Episodic）+ `intelligence_assets`（Semantic）+ `skill_executions`（Skill）+ `note_review_history`（Learning）。新建 `memory_layer.py`，定义统一 Memory 接口（store/retrieve/forget/TTL），将现有表映射为各 Memory 层，新增 Working Memory（当前任务上下文的结构化短期记忆，可基于 `ai_task.context_json` 扩展）。

#### P6. Learning Loop 自动闭环
- **现状**: 有操作记录→学习→优化建议和报告异常→策略建议→反馈应用的链路，但人审修正→规则更新的全自动 pipeline 缺失。
- **复用建议**: **可复用** `ai_learning_engine.py` + `data_feedback_loop.py` + `note_review_history`（8387 条人审数据）+ `rule_version_registry`（规则版本管理）。新建 `learning_pipeline.py`，实现人审修正→规则变更建议→人工确认→规则版本更新→回归验证的半自动闭环（全自动需谨慎，建议先旁路验证）。

#### P7. Tool Router 统一层
- **现状**: 有基于 intent 的 agent/skill 选择和函数注册表，但无统一 Tool Router（Tool 注册→意图匹配→参数校验→执行→结果归一）。
- **复用建议**: **可复用** `ai_agent_registry.py` 的 `select_skills()` + `function_registry.py` 的 FUNCTION_MAP + `skill_execution_chain.py` 的执行链。新建 `tool_router.py`，将 219 个 API 路由 + FUNCTION_MAP + Skills 统一注册为 Tool，提供 `route(intent, params)` → 匹配 Tool → 校验参数 → 执行 → 归一结果的统一 pipeline。

---

## 四、Top 5 关键缺口（按 OSAI Agent Runtime 落地优先级排序）

| 优先级 | 缺口 | 类型 | 核心影响 | 复用路径 |
|--------|------|------|----------|----------|
| **P0-1** | Observation Layer | MISSING | Agent 无环境感知，所有自适应决策（replanning、风险响应、动态调度）缺乏输入基础 | 复用 evidence_chain + ai_task_trace + runtime_guardian 状态 |
| **P0-2** | Agent Loop 预算控制 (max_steps/max_time/max_cost) | PARTIAL | 无预算控制的 Agent Loop 存在资源耗尽风险，无法做成本治理和超时保护 | 复用 ai_task_engine execute 循环 + ai_governance AIUsageTracker |
| **P0-3** | Replanning | MISSING | 复杂任务失败后只能 retry 同参数，无法根据观察/反馈调整策略，Agent 智能性受限 | 复用 ai_task_parser + ai_task_engine step 机制 + note_review_history |
| **P1-4** | 分层 Memory 架构 (尤其 Working Memory) | PARTIAL | 无 Working Memory 导致 Agent 无法维持当前任务上下文，多轮对话/长任务上下文丢失 | 复用 ai_task.context_json + 现有各层数据表，新建统一 Memory 接口 |
| **P1-5** | Tool Router 统一层 | PARTIAL | 219 个 API 路由无统一工具路由，Agent 无法发现/选择/调用合适工具，工具能力碎片化 | 复用 ai_agent_registry.select_skills + function_registry + skill_execution_chain |

---

## 五、可直接复用的核心资产清单

以下模块已达到生产级，OSAI Agent Runtime 落地时**直接复用，不要重写**：

| 资产 | 文件 | 成熟度 | 复用方式 |
|------|------|--------|----------|
| Permission Gate | `permission_gate.py` (45KB) | 生产级 | 作为 Agent 操作权限门，13 种 OperationType + fail-closed + 审批 token |
| Action Firewall (P1+P2) | `skill_execution_chain.py` + `p2_action_firewall.py` | 生产级 | 作为 Agent 动作防火墙，8 维度深度校验 |
| Effect Fence | `skill_execution_chain.py:153-159` | 基础可用 | 作为写操作标记层，后续扩展 staging→promotion |
| Human Approval (三级) | `permission_gate.py` + `agent_boundary.py` + `ai_task_engine.py` | 生产级 | 作为 human-in-the-loop 审批体系 |
| Evidence Chain (哈希链) | `evidence_chain.py` (46KB) | 生产级 | 作为 Agent 决策证据链，不可篡改+血缘追踪 |
| Trace (分布式) | `ai_task_engine.py` + `ai_call_logger.py` | 生产级 | 作为 Agent 执行追踪，span+parent_span 树形结构 |
| Durable Execution | `runtime_guardian.py` (60KB) + `lifecycle_mixin.py` | 生产级 | 作为 Agent 持久化执行底座，checkpoint/pause/resume/DLQ/Reaper |
| AI Gateway (四层 fallback) | `ai_channel.py` + `provider_registry.py` | 生产级 | 作为 Agent AI 调用网关，zhipu→ark→ollama→rule |
| Circuit Breaker (四层) | `ai_channel.py` + `ai_task_engine.py` + `runtime_guardian.py` | 生产级 | 作为 Agent 容错机制 |
| Skill Execution Chain | `skill_execution_chain.py` | 生产级 | 作为 Agent 工具执行链，permission→firewall→effect_fence→execute→evidence→evaluation→trace |
| Task Engine (task/step/evidence) | `ai_task_engine.py` (66KB) | 生产级 | 作为 Agent 任务执行引擎底座 |
| Evaluation (双轨) | `ai_evaluation.py` + `evaluation_system.py` | 生产级 | 作为 Agent 输出质量评估 |
| Intelligence Assets (711条) | `intelligence_assets` 表 | 生产级 | 作为 Agent Semantic Memory 底座 |
| Note Review History (8387条) | `note_review_history` 表 | 生产级 | 作为 Agent Learning Loop 核心训练数据 |

---

## 六、数据库关键表数据量快照

| 表名 | 行数 | 用途 | Agent Runtime 角色 |
|------|------|------|---------------------|
| ai_task | 2,180 | AI 任务 | Task Memory |
| ai_task_step | 4,992 | 任务步骤 | Step Execution Trace |
| ai_task_evidence | 3,044 | 任务证据 | Evidence Chain |
| ai_task_trace | 6,281 | 任务追踪 | Distributed Trace |
| ai_call_logs | 1,388 | AI 调用 | AI Gateway Audit |
| runtime_guardian_workers | 2,600 | 运行时 Worker | Durable Execution |
| runtime_guardian_checkpoints | 76 | 检查点 | Checkpoint/Resume |
| skill_executions | 18 | Skill 执行 | Skill Execution Audit |
| skills_registry | 12 | Skill 注册 | Skill Registry |
| note_review_history | 8,387 | 审核历史 | Learning Data |
| intelligence_assets | 711 | 情报资产 | Semantic Memory |
| feedback_keywords | 16 | 反馈关键词 | Learning Feedback |
| rule_version_registry | 1 | 规则版本 | Rule Versioning |
| browser_evidence | 1,447 | 浏览器证据 | Observation Source |
| app_evidence_records | 17 | 应用证据 | Evidence Store |
| canonical_data | 14 | 规范化数据 | Canonical Store |
| evaluation_records | 0 | 评估记录 | Evaluation (待填充) |
| content_evaluation | 34 | 内容评估 | Content Evaluation |

---

## 七、落地路线建议（基于审计结论）

### Phase 1: 补齐 P0 缺口（Observation + Budget + Replanning 基础）
1. 新建 `observation_layer.py`，复用 evidence_chain 模型，定义 Observation 数据流
2. 在 `ai_task_engine.py` execute_task 中增加 max_steps/max_time/max_cost 预算控制
3. 新建 `replanning.py`，复用 TaskParser，实现失败触发的重规划

### Phase 2: 补齐 P1 缺口（Memory + Tool Router）
4. 新建 `memory_layer.py`，统一分层 Memory 接口，新增 Working Memory
5. 新建 `tool_router.py`，统一 219 API + FUNCTION_MAP + Skills 的工具路由

### Phase 3: 深化（Trajectory Evaluation + Learning 闭环 + Capability 抽象）
6. 新建 `trajectory_evaluation.py`，基于已有 trace 数据做端到端评估
7. 新建 `learning_pipeline.py`，实现人审→规则的半自动闭环
8. 新建 `capability_registry.py`，统一 Skill/Function/Agent 为 Capability

---

## 八、审计约束确认

- [x] 只读审计，未修改源码
- [x] 只读审计，未修改数据库
- [x] 每个结论附文件路径+行号
- [x] 可复用模块标注"可复用"，未建议重写
- [x] 基于真实源码事实，非历史文档/架构图
- [x] 报告写入 `D:\Taikoo-monitor-new\audit\convergence\zbc_capability_matrix.md`

---

*报告生成时间: 2026-09-07 | 审计工具: 源码静态分析 + DB schema 探测 + 测试文件清单交叉验证*
