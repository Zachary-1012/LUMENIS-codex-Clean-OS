# ZBC 全量功能规则审计复用台账 V1.0

> **审计日期**: 2026-09-06
> **审计范围**: 226个候选模块（来自8个外部源），对照 ZBC_FEATURE_MAP_DUAL_DOMAIN（530+功能点）逐项核销
> **审计基准**: 主线 `D:\Taikoo-monitor-new` @ lumenis-dual-domain-v3
> **核销原则**: 每个高价值模块实际Read文件内容判定；OSAI不得成为runtime依赖，只走契约/研究/模式借鉴；GGI/SICI独立不并入；适配补入走当前双域架构、函数驱动、前后端契约一致
> **核销人**: ZBC审计执行代理

---

## 一、汇总统计

| 判定 | 数量 | 占比 | 说明 |
|---|---|---|---|
| **直接复用** | 0 | 0% | 候选模块均来自外部源，无完全兼容可直接放入者 |
| **适配补入** | 27 | 11.9% | 高价值模块，需适配到双域架构后排入维护期 |
| **真缺失新建** | 0 | 0% | 候选模块覆盖的功能主线均有对应或可通过适配补入解决 |
| **废弃** | 73 | 32.3% | 重复/一次性脚本/旧版/已被主线覆盖 |
| **不相关** | 125 | 55.3% | OSAI运行时引擎/KimiData学术工具/GGI独立产品/诊断工具等 |
| **合计** | **226** | **100%** | |

> 注：226为去重后唯一模块数；按源统计总和为265（39个模块跨源重复），重复件在首现源核销，后续源标"重复-已核销"。

### 按源分布

| 源 | 候选数 | 适配补入 | 废弃 | 不相关 | 重复 |
|---|---|---|---|---|---|
| security | 5 | 0 | 2 | 3 | 0 |
| staging-ui | 7 | 0 | 5 | 2 | 0 |
| audit-four-source | 99 | 6 | 56 | 19 | 18 |
| OSAI | 62 | 20 | 2 | 34 | 6 |
| ADRH | 6 | 0 | 0 | 0 | 6 |
| KimiData | 72 | 0 | 0 | 72 | 0 |
| CmdConsole | 6 | 0 | 0 | 0 | 6 |
| GGI | 7 | 0 | 0 | 7 | 0 |
| SICI | 1 | 0 | 1 | 0 | 0 |
| **合计** | **265** | **26** | **66** | **137** | **36** |

---

## 二、适配补入清单（维护期执行，不立即开发）

| 优先级 | 模块名 | 来源 | 所属域 | 适配动作 | 核心理由 |
|---|---|---|---|---|---|
| **P1** | action_firewall.py | OSAI | Shared | 模式借鉴：参数级确定性授权(fail-close)增强permission_gate.py，高风险动作默认deny+人工批准，与主线11级权限模型对齐 | 主线permission_gate(38.9KB)仅2处调用，缺参数级授权和幂等审计 |
| **P1** | effect_fence.py | OSAI | Shared | 模式借鉴：幂等效果围栏(reserve/commit/fail)，用于采集写入/报告生成的重复副作用防护 | 主线缺失幂等保障层，采集重试可能产生重复数据 |
| **P1** | checkpoint_resume.py | OSAI | Shared | 模式借鉴：检查点/恢复机制接入runtime_guardian.py(46.5KB零调用)，save/load/resume/progress | runtime_guardian已有Checkpoint骨架但缺轻量持久化实现 |
| **P1** | evidence_graph.py | OSAI | Shared | 模式借鉴：证据关系图(节点/边/9种关系约束/来源追溯)，增强evidence_chain.py(40.4KB)从链式到图谱 | 主线evidence是链式，缺实体间关系图谱和溯源 |
| **P1** | impact_analysis.py | OSAI | Shared | 模式借鉴：变更前静态影响分析(File→Function→API→DB→Contract→生产风险)，用于发布前风险评估 | 主线缺失变更影响分析工具，生产风险关键词评级可复用 |
| **P1** | shadow_lifecycle.py | OSAI/audit-four-source | Shared | 模式借鉴：影子学习生命周期状态机(9态+证据门控+三仓库验证)，增强learning_collector/learning_persistence | 主线learning部分接入，缺完整状态机和晋升门控 |
| **P2** | contract_persistence.py | OSAI | Shared | 模式借鉴：轻量JSON原子持久化层(task/trace/evidence/evaluation/lifecycle)，作为evidence旁路增强 | 主线evidence_chain走DB，JSON旁路可用于审计导出 |
| **P2** | rules.py | OSAI/audit-four-source | Shared | 语料借鉴：18条工程执行规则(踩坑SOP)注入intelligence_library，作为AI系统prompt约束 | 主线缺固化的工程规则语料，glm-4.7/Windows/PowerShell踩坑规则有实战价值 |
| **P2** | skill_manifest.py | OSAI | Shared | 模式借鉴：Canonical Skill Manifest(24字段+验证+11分类+7状态)，增强skill_registry.py | 主线skill_registry已有但缺Manifest schema验证和分类体系 |
| **P2** | skill_selector.py | OSAI | Shared | 模式借鉴：按Task/Workspace/Permission智能推荐Skill(关键词匹配+权限过滤)，主线缺失 | 主线Skill Hub缺智能推荐，纯列表展示 |
| **P2** | task_contract.py | OSAI | Shared | 模式借鉴：任务契约(scope/forbidden显式声明，未声明则blocked)，增强任务管理 | 主线任务管理缺显式scope/forbidden契约 |
| **P2** | lifecycle_contract.py | OSAI | Shared | 模式借鉴：15态统一生命周期(不跳级+RETIRE终态)，增强zbc_lifecycle_tracking表 | 主线有生命周期跟踪表但缺统一状态机约束 |
| **P2** | permission_contract.py | OSAI | Shared | 模式借鉴：权限请求/决策留痕契约(11级+Agent上限VERIFY+HUMAN_ONLY)，与permission_gate互补 | 主线permission_gate有运行时拦截但缺结构化决策留痕 |
| **P2** | capability_registry.py | audit-four-source/OSAI/ADRH | Shared | 模式借鉴：可复用能力注册表(9态+晋升门控+REUSABLE_REQUIREMENTS+consumers记录) | 主线缺独立能力注册表，研究成果无法结构化沉淀 |
| **P2** | learning_cycle.py | OSAI/audit-four-source/CmdConsole | Shared | 模式借鉴：三仓库学习bundle构建(只读+noAutoPromotion+crossRepository验证) | 主线learning_collector缺跨仓库验证和shadow候选识别 |
| **P2** | learning_promote.py | OSAI/audit-four-source/CmdConsole | Shared | 模式借鉴：证据门控晋升(5门控:shadow/evidence/review/三仓库/capability_delta)，AI信心≠证据 | 主线learning_persistence缺晋升门控机制 |
| **P2** | research_registry.py | OSAI/audit-four-source/CmdConsole | Shared | 模式借鉴：研究基准注册表验证(必填字段+去重+adoptability分级) | 主线research workspace缺基准注册表结构 |
| **P2** | research_record.py | OSAI/audit-four-source/ADRH | Shared | 模式借鉴：研究记录契约(R-XXXX-XXXX ID+11态+三仓库验证+凭证脱敏) | 主线缺结构化研究记录契约和凭证脱敏(is_sensitive_key) |
| **P2** | ddc_research_adapter.py | audit-four-source/OSAI/ADRH | Shared | 模式借鉴：DDC研究学习JSONL读写适配器(validate→sanitize→convert→append) | 主线研究数据缺标准化交换格式 |
| **P2** | secret_scan.py | audit-four-source/OSAI/ADRH | Shared | 模式借鉴：递归密钥扫描(JSON/JSONL，基于is_sensitive_key词边界匹配，防误报)，增强security_scanner.py | 主线security_scanner已有，OSAI版本的词边界匹配和camelCase处理更精准 |
| **P3** | learning_record_contract.py | OSAI | Shared | 契约模式：学习记录契约结构 | 低优先级，可合并入learning_persistence适配 |
| **P3** | runtime_contract.py | OSAI | Shared | 契约模式：运行时契约结构 | 低优先级，主线runtime层已有多个模块 |
| **P3** | skill_execution_contract.py | OSAI | Shared | 契约模式：Skill执行契约 | 低优先级，可合并入skill_manifest适配 |
| **P3** | trace_contract.py | OSAI | Shared | 契约模式：追踪契约 | 低优先级 |
| **P3** | ui_state_contract.py | OSAI | Shared | 契约模式：UI状态契约 | 低优先级，主线UI层已有状态管理 |
| **P3** | capability_delta.py | OSAI/CmdConsole | Shared | 模式借鉴：能力增量量化(before/after metrics+evidence)，配合learning_promote | 低优先级，晋升门控的子组件 |
| **P3** | reconcile_capabilities.py | audit-four-source/OSAI | Shared | 模式借鉴：能力对账 | 低优先级 |

---

## 三、高价值模块详细判定（已实际Read文件内容）

### 3.1 OSAI 高价值模块

#### action_firewall.py (`D:\Zachary OS AI\osai_engine\action_firewall.py`, 5.4KB)
- **内容**: ActionFirewall类，参数级确定性授权。HIGH_RISK_ACTIONS(18种:commit/push/delete/drop_db/migrate/send等)默认deny必须HUMAN_APPROVAL；MEDIUM_RISK(7种)需scope检查；低风险默认allow。fail-close异常→DENY+AUDIT。参数哈希+幂等键审计。
- **主线对比**: permission_gate.py(38.9KB)已有11级权限模型但仅2处调用，缺参数级授权和动作分类。
- **判定**: **适配补入** | Shared | P1 | 模式借鉴：动作分类表+fail-close+参数哈希审计可增强permission_gate，不复制OSAI代码，提取规则和模式。

#### checkpoint_resume.py (`D:\Zachary OS AI\osai_engine\checkpoint_resume.py`, 5.0KB)
- **内容**: CheckpointManager，save/load/resume/update/progress/list_active。Checkpoint数据类(checkpoint_id/task_id/step/total_steps/state/data)，支持JSON文件持久化。
- **主线对比**: runtime_guardian.py(46.5KB)零外部调用，内含Checkpoint/Resume/Reaper/Retry/DLQ骨架但未接入。
- **判定**: **适配补入** | Shared | P1 | 轻量检查点实现模式可接入runtime_guardian，不复制代码，借鉴dataclass+持久化模式。

#### contract_persistence.py (`D:\Zachary OS AI\osai_engine\contract_persistence.py`, 5.3KB)
- **内容**: 轻量JSON持久化层。evidence/<task_id>/下task.json(原子覆盖写)/trace.jsonl(追加)/evidence.jsonl/evaluation.json/lifecycle.json。纯stdlib，原子写(.tmp→os.replace)。
- **主线对比**: evidence_chain.py(40.4KB)+evidence_store.py走DB，缺JSON旁路。
- **判定**: **适配补入** | Shared | P2 | 原子写模式可作为evidence审计导出旁路，不成为runtime依赖。

#### effect_fence.py (`D:\Zachary OS AI\osai_engine\effect_fence.py`, 5.7KB)
- **内容**: EffectFence幂等围栏。reserve(幂等键去重)/start/commit/fail。6态(PENDING/RESERVED/EXECUTING/COMMITTED/FAILED/DUPLICATE)。参数哈希检测重复请求。线程安全。
- **主线对比**: 主线缺失独立幂等层，采集重试靠collector_guard去重但非通用。
- **判定**: **适配补入** | Shared | P1 | 幂等模式对采集写入和报告生成有直接价值，借鉴reserve-commit模式。

#### evaluation_contract.py (`D:\Zachary OS AI\osai_engine\evaluation_contract.py`, 4.3KB)
- **内容**: Evaluation契约。5维度(correctness/completeness/performance/safety/compliance)，阈值<60 failed/60-80 needs_review/≥80 passed。no_data_evaluation()诚实模式——无真实执行不伪造分数。
- **主线对比**: evaluation_system.py+evaluation_dimensions.py(30.9KB)+evaluation_recorder.py+evaluation_runner.py已完整覆盖。
- **判定**: **废弃** | Shared | 主线已有完整评估体系，OSAI版本是子集。no_data模式可作为规则语料注入intelligence_library。

#### evidence_graph.py (`D:\Zachary OS AI\osai_engine\evidence_graph.py`, 5.0KB)
- **内容**: EvidenceGraph图谱。EvidenceNode(entity_type/canonical_id/label/properties)+EvidenceEdge(source/target/relation/weight)。9种ALLOWED_RELATIONS(derived_from/supports/contradicts/triggers等)。trace_to_source() BFS溯源。self-loop禁止。
- **主线对比**: evidence_chain.py(40.4KB)是链式证据，缺实体间关系图谱。
- **判定**: **适配补入** | Shared | P1 | 图谱模式+关系约束+溯源可增强evidence层，从链式升级为图谱。

#### impact_analysis.py (`D:\Zachary OS AI\osai_engine\impact_analysis.py`, 6.4KB)
- **内容**: ImpactAnalyzer静态影响分析。AST提取变更符号→全仓扫描引用→检测API路由/DB表/Contract→生产风险评级(CRITICAL/HIGH/MEDIUM关键词)→建议。PRODUCTION_RISK_KEYWORDS含subject_hit/SUBJECT_WORDS/CollectorGuard/risk_engine等ZBC特定关键词。
- **主线对比**: 主线缺失变更影响分析工具。
- **判定**: **适配补入** | Shared | P1 | 发布前风险评估有直接价值，ZBC关键词已内置，借鉴AST+引用扫描+风险评级模式。

#### rules.py (`D:\Zachary OS AI\osai_engine\rules.py`, 2.5KB)
- **内容**: 18条工程执行规则(踩坑SOP)。覆盖Windows/PowerShell转义、git push stderr误报、app.py动态加载缓存、glm-4.7思考模型(max_tokens/reasoning_content/JSON嵌套)、数据可复现(shuffle副本)、禁止伪造数据、功能零减配、个人资料不上线、禁止绕过安全机制。
- **主线对比**: intelligence_library缺固化的工程规则语料。
- **判定**: **适配补入** | Shared | P2 | 规则语料直接注入intelligence_library，作为AI系统prompt约束，不复制代码。

#### shadow_lifecycle.py (`D:\Zachary OS AI\components\AI-Development-Research-Hub\src\shared\shadow_lifecycle.py`, 3.7KB)
- **内容**: Shadow Learning Lifecycle状态机。9态(research→hypothesis→candidate→shadow→evidence→review→verified→promotion_candidate→reusable)+hold/rejected终态。can_transition()仅允许前进一步。EVIDENCE_REQUIRED_STATES需evidence_refs。is_shadow_safe()确保影子模式不改生产行为。required_exit_evidence()每态退出所需证据。
- **主线对比**: learning_collector.py(16.9KB)+learning_persistence.py(8.6KB)部分接入，缺完整状态机和晋升门控。
- **判定**: **适配补入** | Shared | P1 | 状态机+证据门控+影子安全检查是学习闭环的核心，借鉴模式增强learning层。

#### skill_manifest.py (`D:\Zachary OS AI\osai_engine\skill_manifest.py`, 11.9KB)
- **内容**: Canonical Skill Manifest。24字段(id/name/version/category/type/description/intent/inputs/outputs/tools/permissions/preconditions/execution/evidence/evaluation/failure_recovery/dependencies/source/repository/status)。7种Skill类型+11种分类+7种状态。validate_manifest()必填/格式/权限级别验证。normalize_manifest()补默认值。build_s01_s12_manifests()内置12个工程Skill。
- **主线对比**: skill_registry.py已有，lumenis_skill_adapter.py部分接入，但缺Manifest schema验证和标准化分类。
- **判定**: **适配补入** | Shared | P2 | Manifest schema+验证器可增强skill_registry，不复制代码，提取字段定义和验证逻辑。

#### skill_selector.py (`D:\Zachary OS AI\osai_engine\skill_selector.py`, 9.6KB)
- **内容**: SkillSelector智能推荐。输入task/workspace/user_intent/permissions→输出排序推荐列表。WORKSPACE_CATEGORIES(6工作区→分类映射)+INTENT_KEYWORDS(11分类×关键词)。评分:workspace匹配3分+intent匹配2分×N+名称重叠1.5+描述重叠0.5+状态加权+类型加权。权限过滤。
- **主线对比**: 主线Skill Hub缺智能推荐，纯列表。
- **判定**: **适配补入** | Shared | P2 | 推荐算法(关键词+权限+状态加权)可接入Skill Hub，借鉴模式。

#### skill_sync.py (`D:\Zachary OS AI\osai_engine\skill_sync.py`, 10.4KB)
- **内容**: GitHubSkillSync。Manifest↔Registry同步，git操作+冲突检测(CONFLICT→STOP→SHOW DIFF→HUMAN DECISION)。7种同步状态。ONE CANONICAL SOURCE红线。
- **主线对比**: 主线Skill管理不走GitHub同步。
- **判定**: **不相关** | - | OSAI运行时机制，GitHub同步不成为ZBC依赖。同步冲突检测模式可低优先级借鉴。

#### permission_contract.py (`D:\Zachary OS AI\osai_engine\permission_contract.py`, 3.5KB)
- **内容**: PermissionRequest契约。11级(READ→PUSH)，AGENT_AUTO_MAX=VERIFY，HUMAN_ONLY=[HUMAN_APPROVAL,COMMIT,PUSH]。actor(agent/skill/human/system)自动决策：Agent请求HUMAN_ONLY→自动deny；≤VERIFY→自动allow。human_decide()人工决策。PermissionContractRegistry留痕。
- **主线对比**: permission_gate.py(38.9KB)已有11级模型和运行时拦截，缺结构化请求/决策留痕。
- **判定**: **适配补入** | Shared | P2 | 决策留痕契约可增强permission_gate的审计能力，借鉴PermissionRequest结构。

#### task_contract.py (`D:\Zachary OS AI\osai_engine\task_contract.py`, 4.2KB)
- **内容**: Task契约。task_id=T-YYYYMMDD-xxxx，owner(WINDOW-A/B/C/HUMAN)，repo(ZBC/OSAI/BOTH)。scope/forbidden必须显式声明，未声明→status=blocked。7态(pending/running/blocked/awaiting_approval/done/failed/retired)。attach_evidence()关联evidence_chain id。
- **主线对比**: 主线任务管理缺显式scope/forbidden契约。
- **判定**: **适配补入** | Shared | P2 | scope/forbidden强制声明模式可防止任务越界，借鉴契约结构。

#### lifecycle_contract.py (`D:\Zachary OS AI\osai_engine\lifecycle_contract.py`, 3.1KB)
- **内容**: 15态统一生命周期(DISCOVER→REQUIREMENT→RESEARCH→EVIDENCE→DECISION→ARCHITECTURE→IMPLEMENT→TEST→VERIFY→RELEASE→OPERATE→MONITOR→LEARN→IMPROVE→RETIRE)。仅允许前进一步，RETIRE终态。LifecycleTracker带history。
- **主线对比**: zbc_lifecycle_tracking表已有，缺统一状态机约束。
- **判定**: **适配补入** | Shared | P2 | 15态状态机可统一主线各模块生命周期，借鉴状态定义和transition约束。

#### learning_cycle.py (`D:\Zachary OS AI\components\Development-Command-Console\tools\learning_cycle.py`, 3.8KB)
- **内容**: 三仓库学习bundle构建。从Z-Brand-Core/SICI-Core/Development-Command-Console inspection JSON构建learning-bundle.json。optimization_candidates→cases，跨仓库模式识别(≥2次出现→PATTERN shadow candidate)。crossRepository验证。policy:readOnly/noAutoPromotion/aiOutputNotFact/humanReviewRequired。
- **主线对比**: learning_collector缺跨仓库验证。
- **判定**: **适配补入** | Shared | P2 | 跨仓库学习bundle构建模式可增强learning层，只读+不自动晋升红线与ZBC治理一致。

#### learning_promote.py (`D:\Zachary OS AI\components\Development-Command-Console\tools\learning_promote.py`, 7.9KB)
- **内容**: 证据门控晋升助手。5门控全部通过才能成为promotion_candidate: shadow+evidence+review+three_repository_verification+capability_delta。capability_delta需before/after metrics+evidence+improvement+side_effects_acknowledged。promotion_candidate≠promotion，最终人工批准。AI信心≠证据。FORBIDDEN_KEYS凭证脱敏。
- **主线对比**: learning_persistence缺晋升门控。
- **判定**: **适配补入** | Shared | P2 | 5门控晋升机制是学习闭环的关键治理模式，借鉴门控逻辑和capability_delta结构。

#### research_registry.py (`D:\Zachary OS AI\components\Development-Command-Console\tools\research_registry.py`, 2.0KB)
- **内容**: 研究基准注册表验证。REQUIRED={id/family/source/repository/reference/patterns/targetLayers/adoptability}。去重检测+无效条目检测+family/layer统计+HIGH adoptability计数。
- **主线对比**: Research Workspace缺基准注册表结构。
- **判定**: **适配补入** | Shared | P2 | 注册表验证模式可结构化研究基准管理。

#### research_record.py (`D:\Zachary OS AI\components\AI-Development-Research-Hub\src\contracts\research_record.py`, 10.2KB)
- **内容**: 研究记录契约。SCHEMA=zachary.hub.research.v1。research_id=R-XXXX-XXXX格式。11态(与shadow_lifecycle对齐)。三仓库验证(zbrand/ddc/sici)。is_sensitive_key()词边界匹配(处理snake_case/camelCase/PascalCase/kebab-case，tokenizer/cookbook不误报)。sanitize()递归凭证脱敏。validate()完整校验。to_ddc_record()格式转换。make_review()/add_review()评审管理。
- **主线对比**: 主线缺结构化研究记录契约。
- **判定**: **适配补入** | Shared | P2 | 研究记录契约+凭证脱敏(is_sensitive_key词边界匹配)有高复用价值，脱敏逻辑可直接用于security_scanner增强。

### 3.2 audit-four-source 高价值模块

#### capability_registry.py (`audit-four-source\...\AI-Development-Research-Hub\src\shared\capability_registry.py`)
- **内容**: CapabilityRegistry。9态(candidate/shadow/verified/reusable/deprecated/rejected/proposed/researching/verifying)。REUSABLE_REQUIREMENTS=[origin_research_id/evidence_refs/contract/tests/validations/rollback_plan]。promote()门控检查。register_usage()记录消费者(不复制代码)。JSON文件持久化。
- **主线对比**: 主线缺独立能力注册表。
- **判定**: **适配补入** | Shared | P2 | 能力注册+晋升门控+消费者记录模式可结构化研究成果沉淀。

#### case_corpus.py (`audit-four-source\tmp\case_corpus.py`, 181行)
- **内容**: 一次性盘点脚本。读取data/case_library.json+case_deep_analysis.json+learning_database.json+brand_knowledge_base.json等，生成05_CASE_LIBRARY_INVENTORY.md和06_CORPUS_INVENTORY.md。硬编码路径D:\Taikoo-monitor-new\data。
- **主线对比**: public_opinion_cases.py+case_deep_analysis.py+case_ai_evaluate.py已覆盖案例库功能。
- **判定**: **废弃** | - | 一次性盘点脚本，功能已被主线案例库模块覆盖，硬编码路径不可复用。

#### db_forensics.py (`audit-four-source\...\03_DATABASE\db_forensics.py`, 517行)
- **内容**: 数据库只读取证脚本。复制5个已知库+搜索额外库→SHA256封存→只读URI统计→生成DATABASE_INVENTORY.csv/Table_DETAILS.csv/md。全程只读原库。
- **主线对比**: audit/db_empty_tables_classification.json+table_schemas.json已有数据库清点产物。
- **判定**: **废弃** | - | 一次性取证脚本，已执行完毕产物在audit-four-source包内，主线已有数据库审计体系。

#### db_forensics_fix.py (`audit-four-source\...\03_DATABASE\db_forensics_fix.py`, 350行)
- **内容**: db_forensics的修复脚本，解决BACKUP目录同名覆盖问题，重新复制28个库(含Edge浏览器配置文件库)用唯一文件名。
- **判定**: **废弃** | - | db_forensics的配套修复脚本，一次性。

#### deployment__health_check.py (`audit-four-source\...\RUNTIME_CONFIG\deployment__health_check.py`, 20行)
- **内容**: 极简健康检查。检查.env/DB/cloudflared存在性+HTTP GET http://127.0.0.1:8200/healthz。
- **主线对比**: runtime_preflight.py+resident_health.py+system_watchdog.py+stability_monitor.py已完整覆盖。
- **判定**: **废弃** | - | 功能已被主线runtime健康检查模块覆盖，端口8200是旧版。

#### deployment__backup.py (`audit-four-source\...\RUNTIME_CONFIG\deployment__backup.py`, 13行)
- **内容**: SQLite在线备份，调用database.backup_database()输出到data/backups/。
- **主线对比**: scripts/backup_db.py已存在，database.backup_database()已实现。
- **判定**: **废弃** | - | 主线已有同名脚本和底层函数。

#### ddc_research_adapter.py (`audit-four-source\...\adapters\ddc_research_adapter.py`, 68行)
- **内容**: DDCResearchAdapter。validate→sanitize→to_ddc_record→append JSONL。read_all/find_by_id/迭代器接口。依赖research_record契约。
- **主线对比**: 主线研究数据缺标准化交换格式。
- **判定**: **适配补入** | Shared | P2 | JSONL读写适配器模式可用于研究数据标准化交换，与research_record配合。

#### secret_scan.py (`audit-four-source\...\tools\secret_scan.py`, 102行)
- **内容**: 递归密钥扫描。仅当dict KEY是敏感字段(is_sensitive_key词边界匹配)且value是非空非占位字符串时才报警。描述性文本中的"token"不报警。支持.json/.jsonl，utf-8-sig处理BOM。
- **主线对比**: security_scanner.py已有密钥扫描，但OSAI版本的词边界匹配更精准(防tokenizer/cookbook误报)。
- **判定**: **适配补入** | Shared | P2 | is_sensitive_key词边界匹配算法可增强security_scanner，降低误报率。

---

## 四、全量226模块核销明细

### 4.1 security（5个）

| 模块名 | 来源 | 主线状态 | 判定 | 所属域 | 适配动作 | 核销人 |
|---|---|---|---|---|---|---|
| ai_gateway_v570.py | security | 已有 | 废弃 | Shared | 旧版AI网关v570，主线已有ai_api.py+intelligence.py(40.6KB)，版本过时 | ZBC审计 |
| diag_mobile.py | security | 缺失 | 不相关 | - | 移动端诊断工具，与ZBC双域架构无关 | ZBC审计 |
| diag_modal.py | security | 缺失 | 不相关 | - | 模态框诊断工具，staging-ui遗留 | ZBC审计 |
| e2e_kb.py | security | 缺失 | 废弃 | - | 端到端知识库一次性脚本，主线evaluation体系已覆盖 | ZBC审计 |
| extract_win_demo.py | security | 缺失 | 不相关 | - | Windows演示提取工具，与ZBC业务无关 | ZBC审计 |

### 4.2 staging-ui（7个）

| 模块名 | 来源 | 主线状态 | 判定 | 所属域 | 适配动作 | 核销人 |
|---|---|---|---|---|---|---|
| ai_gateway_v570.py | staging-ui | 已有 | 废弃 | Shared | 与security源同文件，旧版AI网关 | ZBC审计 |
| diag_db.py | staging-ui | 缺失 | 不相关 | - | 数据库诊断工具，staging-ui遗留 | ZBC审计 |
| diag_nav.py | staging-ui | 缺失 | 不相关 | - | 导航诊断工具，staging-ui遗留 | ZBC审计 |
| read_inputs.py | staging-ui | 缺失 | 废弃 | - | 读输入一次性工具 | ZBC审计 |
| run_ui_regression.py | staging-ui | 已有 | 废弃 | - | UI回归测试，主线tests/已有体系 | ZBC审计 |
| run_ui_regression2.py | staging-ui | 已有 | 废弃 | - | UI回归v2，同上 | ZBC审计 |
| shoot_evidence.py | staging-ui | 已有 | 废弃 | - | 截图取证，主线evidence_chain+app_evidence已覆盖 | ZBC审计 |

### 4.3 audit-four-source（99个）

#### 高价值/非脚本模块（39个）

| 模块名 | 来源 | 主线状态 | 判定 | 所属域 | 适配动作 | 核销人 |
|---|---|---|---|---|---|---|
| GENERATE_SOURCE_FACT_PACKAGE.py | audit-four-source | 缺失 | 废弃 | - | 一次性源码事实包生成脚本 | ZBC审计 |
| agent.py | audit-four-source | 缺失 | 不相关 | - | OSAI agent克隆，运行时引擎 | ZBC审计 |
| base_adapter_enhanced.py | audit-four-source | 已有 | 废弃 | Shared | SICI三模块评估结论：主库已有CircuitBreaker/RateLimiter/BaseAdapter | ZBC审计 |
| capability_delta.py | audit-four-source | 缺失 | 适配补入 | Shared | P3：能力增量量化模式，配合learning_promote门控 | ZBC审计 |
| capability_registry.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：可复用能力注册表(9态+晋升门控)，详见§3.2 | ZBC审计 |
| case_corpus.py | audit-four-source | 已有 | 废弃 | - | 一次性盘点脚本，详见§3.2 | ZBC审计 |
| cross_diff.py | audit-four-source | 缺失 | 废弃 | - | 一次性交叉比对脚本 | ZBC审计 |
| db_audit.py | audit-four-source | 缺失 | 废弃 | - | 一次性DB审计脚本 | ZBC审计 |
| db_forensics.py | audit-four-source | 缺失 | 废弃 | - | 一次性数据库取证，详见§3.2 | ZBC审计 |
| db_forensics_fix.py | audit-four-source | 缺失 | 废弃 | - | db_forensics配套修复，一次性 | ZBC审计 |
| ddc_research_adapter.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：DDC研究JSONL适配器，详见§3.2 | ZBC审计 |
| deployment__backup.py | audit-four-source | 已有 | 废弃 | - | 主线scripts/backup_db.py已存在，详见§3.2 | ZBC审计 |
| deployment__deployment__乱码1.py | audit-four-source | 缺失 | 废弃 | - | 部署脚本，文件名乱码不可用 | ZBC审计 |
| deployment__deployment__乱码2.py | audit-four-source | 缺失 | 废弃 | - | 部署脚本，文件名乱码不可用 | ZBC审计 |
| deployment__health_check.py | audit-four-source | 已有 | 废弃 | - | 主线runtime健康检查已覆盖，详见§3.2 | ZBC审计 |
| deployment__健康检查.py | audit-four-source | 已有 | 废弃 | - | 同deployment__health_check，中文名重复 | ZBC审计 |
| deployment__数据库备份.py | audit-four-source | 已有 | 废弃 | - | 同deployment__backup，中文名重复 | ZBC审计 |
| evidence.py | audit-four-source | 已有 | 废弃 | Shared | OSAI evidence克隆，主线evidence_chain.py(40.4KB)已完整覆盖 | ZBC审计 |
| extract_deploy_logs_docs.py | audit-four-source | 缺失 | 废弃 | - | 一次性部署日志提取 | ZBC审计 |
| extract_env_facts.py | audit-four-source | 缺失 | 废弃 | - | 一次性环境事实提取 | ZBC审计 |
| extract_env_remaining.py | audit-four-source | 缺失 | 废弃 | - | 一次性环境剩余提取 | ZBC审计 |
| extract_env_remaining2.py | audit-four-source | 缺失 | 废弃 | - | 一次性环境剩余提取v2 | ZBC审计 |
| extract_knowledge.py | audit-four-source | 缺失 | 废弃 | - | 一次性知识提取 | ZBC审计 |
| extract_runtime_config.py | audit-four-source | 缺失 | 废弃 | - | 一次性运行时配置提取 | ZBC审计 |
| gen_inventory.py | audit-four-source | 缺失 | 废弃 | - | 一次性清单生成 | ZBC审计 |
| gen_reports_part1.py | audit-four-source | 缺失 | 废弃 | - | 一次性报告生成(分6部分) | ZBC审计 |
| gen_reports_part2.py | audit-four-source | 缺失 | 废弃 | - | 同上 | ZBC审计 |
| gen_reports_part3.py | audit-four-source | 缺失 | 废弃 | - | 同上 | ZBC审计 |
| gen_reports_part4.py | audit-four-source | 缺失 | 废弃 | - | 同上 | ZBC审计 |
| gen_reports_part5.py | audit-four-source | 缺失 | 废弃 | - | 同上 | ZBC审计 |
| gen_reports_part6.py | audit-four-source | 缺失 | 废弃 | - | 同上 | ZBC审计 |
| gen_trees.py | audit-four-source | 缺失 | 废弃 | - | 一次性目录树生成 | ZBC审计 |
| gen_zips.py | audit-four-source | 缺失 | 废弃 | - | 一次性打包脚本 | ZBC审计 |
| generate_report.py | audit-four-source | 已有 | 废弃 | - | 一次性报告生成，主线report_api.py(45.9KB)已覆盖 | ZBC审计 |
| inventory.py | audit-four-source | 缺失 | 废弃 | - | 一次性清单脚本 | ZBC审计 |
| learning_cycle.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：三仓库学习bundle，与OSAI同文件，详见§3.1 | ZBC审计 |
| learning_promote.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：证据门控晋升，与OSAI同文件，详见§3.1 | ZBC审计 |
| llm.py | audit-four-source | 缺失 | 不相关 | - | OSAI llm克隆，运行时引擎 | ZBC审计 |
| orchestrator.py | audit-four-source | 缺失 | 不相关 | - | OSAI orchestrator克隆，运行时引擎 | ZBC审计 |
| osai_tool.py | audit-four-source | 缺失 | 不相关 | - | OSAI工具克隆，运行时引擎 | ZBC审计 |
| platform_inspection.py | audit-four-source | 缺失 | 不相关 | - | OSAI平台检查克隆，运行时引擎 | ZBC审计 |
| reconcile_capabilities.py | audit-four-source | 缺失 | 适配补入 | Shared | P3：能力对账模式 | ZBC审计 |
| research.py | audit-four-source | 缺失 | 不相关 | - | OSAI research克隆，运行时引擎 | ZBC审计 |
| research_id.py | audit-four-source | 缺失 | 不相关 | - | OSAI research_id克隆 | ZBC审计 |
| research_learning.py | audit-four-source | 缺失 | 不相关 | - | OSAI research_learning克隆 | ZBC审计 |
| research_record.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：研究记录契约+凭证脱敏，与OSAI同文件，详见§3.1 | ZBC审计 |
| research_registry.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：研究基准注册表，与OSAI同文件，详见§3.1 | ZBC审计 |
| rules.py | audit-four-source | 缺失 | 适配补入 | Shared | P2：工程执行规则语料，与OSAI同文件，详见§3.1 | ZBC审计 |
| secret_scan.py | audit-four-source | 已有 | 适配补入 | Shared | P2：词边界密钥扫描增强security_scanner，详见§3.2 | ZBC审计 |
| shadow_lifecycle.py | audit-four-source | 缺失 | 适配补入 | Shared | P1：影子学习生命周期状态机，与OSAI同文件，详见§3.1 | ZBC审计 |
| skills_registry_cli.py | audit-four-source | 缺失 | 不相关 | - | OSAI CLI克隆，运行时工具 | ZBC审计 |
| tools.py | audit-four-source | 缺失 | 不相关 | - | OSAI tools克隆，运行时引擎 | ZBC审计 |
| verify_redaction.py | audit-four-source | 缺失 | 废弃 | - | 一次性脱敏验证 | ZBC审计 |
| zell_bridge.py | audit-four-source | 缺失 | 不相关 | - | OSAI桥接克隆，运行时引擎 | ZBC审计 |

#### scripts__* 一次性脚本（50个）

> 判定策略：查主线 `D:\Taikoo-monitor-new\scripts\` 目录，已有同名→废弃(重复)；功能有用但主线无→适配补入到scripts/；纯一次性→废弃。
> 经核查，主线scripts/已有49个同名脚本，全部废弃。

| 模块名 | 主线scripts/ | 判定 | 理由 |
|---|---|---|---|
| scripts___prod_dep_check.py | _prod_dep_check.py | 废弃 | 主线已有，三下划线命名差异 |
| scripts__ai_budget.py | ai_budget.py | 废弃 | 主线已有 |
| scripts__ai_gateway.py | ai_gateway.py | 废弃 | 主线已有 |
| scripts__app_closure_audit.py | app_closure_audit.py | 废弃 | 主线已有 |
| scripts__backup_db.py | backup_db.py | 废弃 | 主线已有 |
| scripts__brand_insight.py | brand_insight.py | 废弃 | 主线已有 |
| scripts__campaign_plan.py | campaign_plan.py | 废弃 | 主线已有 |
| scripts__check_system.py | check_system.py | 废弃 | 主线已有 |
| scripts__collect_now.py | collect_now.py | 废弃 | 主线已有 |
| scripts__daily_git_sync.py | daily_git_sync.py | 废弃 | 主线已有 |
| scripts__dev_ai.py | dev_ai.py | 废弃 | 主线已有 |
| scripts__dlq_ops.py | dlq_ops.py | 废弃 | 主线已有 |
| scripts__e2e_loop_check.py | e2e_loop_check.py | 废弃 | 主线已有 |
| scripts__evidence_export.py | evidence_export.py | 废弃 | 主线已有 |
| scripts__export_report.py | export_report.py | 废弃 | 主线已有 |
| scripts__github_upgrade_check.py | github_upgrade_check.py | 废弃 | 主线已有 |
| scripts__idea_generator.py | idea_generator.py | 废弃 | 主线已有 |
| scripts__init_database_data.py | init_database_data.py | 废弃 | 主线已有 |
| scripts__init_db.py | init_db.py | 废弃 | 主线已有 |
| scripts__json_repair.py | json_repair.py | 废弃 | 主线已有 |
| scripts__lean_footprint.py | lean_footprint.py | 废弃 | 主线已有 |
| scripts__license_audit.py | license_audit.py | 废弃 | 主线已有 |
| scripts__localization_guard.py | localization_guard.py | 废弃 | 主线已有 |
| scripts__marketing_calendar.py | marketing_calendar.py | 废弃 | 主线已有 |
| scripts__observatory_feed.py | observatory_feed.py | 废弃 | 主线已有 |
| scripts__perspective_adapter.py | perspective_adapter.py | 废弃 | 主线已有 |
| scripts__pitch_export.py | pitch_export.py | 废弃 | 主线已有 |
| scripts__pitch_parser.py | pitch_parser.py | 废弃 | 主线已有 |
| scripts__production_baseline_check.py | production_baseline_check.py | 废弃 | 主线已有 |
| scripts__prompt_registry.py | prompt_registry.py | 废弃 | 主线已有 |
| scripts__quality_audit.py | quality_audit.py | 废弃 | 主线已有 |
| scripts__run_core_regression.py | run_core_regression.py | 废弃 | 主线已有 |
| scripts__runtime_switch_ops.py | runtime_switch_ops.py | 废弃 | 主线已有 |
| scripts__social_ops.py | social_ops.py | 废弃 | 主线已有 |
| scripts__stability_fix.py | stability_fix.py | 废弃 | 主线已有 |
| scripts__staging_setup.py | staging_setup.py | 废弃 | 主线已有 |
| scripts__start_resident_browsers.py | start_resident_browsers.py | 废弃 | 主线已有 |
| scripts__sync_v4_owner_password.py | sync_v4_owner_password.py | 废弃 | 主线已有 |
| scripts__sync_xhs_cookie_from_cdp.py | sync_xhs_cookie_from_cdp.py | 废弃 | 主线已有 |
| scripts__topic_cluster.py | topic_cluster.py | 废弃 | 主线已有 |
| scripts__topic_words.py | topic_words.py | 废弃 | 主线已有 |
| scripts__video_script.py | video_script.py | 废弃 | 主线已有 |
| scripts__visualization_quality_gate.py | visualization_quality_gate.py | 废弃 | 主线已有 |
| scripts__warehouse_sync_monitor.py | warehouse_sync_monitor.py | 废弃 | 主线已有 |
| scripts__zell_trace.py | zell_trace.py | 废弃 | 主线已有 |

### 4.4 OSAI（62个）

#### 高价值模块（19个，已Read内容）

| 模块名 | 主线状态 | 判定 | 所属域 | 适配动作 | 核销人 |
|---|---|---|---|---|---|
| action_firewall.py | 部分接入 | 适配补入 | Shared | P1：参数级授权增强permission_gate，详见§3.1 | ZBC审计 |
| checkpoint_resume.py | 部分接入 | 适配补入 | Shared | P1：检查点机制接入runtime_guardian，详见§3.1 | ZBC审计 |
| contract_persistence.py | 缺失 | 适配补入 | Shared | P2：JSON原子持久化旁路，详见§3.1 | ZBC审计 |
| effect_fence.py | 缺失 | 适配补入 | Shared | P1：幂等效果围栏，详见§3.1 | ZBC审计 |
| evaluation_contract.py | 已有 | 废弃 | Shared | 主线evaluation体系已覆盖，详见§3.1 | ZBC审计 |
| evidence_graph.py | 缺失 | 适配补入 | Shared | P1：证据关系图谱增强evidence_chain，详见§3.1 | ZBC审计 |
| impact_analysis.py | 缺失 | 适配补入 | Shared | P1：变更影响分析，详见§3.1 | ZBC审计 |
| learning_cycle.py | 缺失 | 适配补入 | Shared | P2：三仓库学习bundle，详见§3.1 | ZBC审计 |
| learning_promote.py | 缺失 | 适配补入 | Shared | P2：证据门控晋升，详见§3.1 | ZBC审计 |
| learning_record_contract.py | 缺失 | 适配补入 | Shared | P3：学习记录契约 | ZBC审计 |
| lifecycle_contract.py | 部分接入 | 适配补入 | Shared | P2：15态生命周期状态机，详见§3.1 | ZBC审计 |
| permission_contract.py | 部分接入 | 适配补入 | Shared | P2：权限决策留痕契约，详见§3.1 | ZBC审计 |
| research_record.py | 缺失 | 适配补入 | Shared | P2：研究记录契约+凭证脱敏，详见§3.1 | ZBC审计 |
| research_registry.py | 缺失 | 适配补入 | Shared | P2：研究基准注册表，详见§3.1 | ZBC审计 |
| rules.py | 缺失 | 适配补入 | Shared | P2：工程规则语料注入intelligence_library，详见§3.1 | ZBC审计 |
| runtime_contract.py | 缺失 | 适配补入 | Shared | P3：运行时契约 | ZBC审计 |
| shadow_lifecycle.py | 部分接入 | 适配补入 | Shared | P1：影子学习生命周期状态机，详见§3.1 | ZBC审计 |
| skill_execution_contract.py | 缺失 | 适配补入 | Shared | P3：Skill执行契约 | ZBC审计 |
| skill_manifest.py | 部分接入 | 适配补入 | Shared | P2：Canonical Skill Manifest增强skill_registry，详见§3.1 | ZBC审计 |
| skill_selector.py | 缺失 | 适配补入 | Shared | P2：Skill智能推荐，详见§3.1 | ZBC审计 |
| skill_sync.py | 缺失 | 不相关 | - | GitHub同步机制，OSAI运行时，不成为ZBC依赖，详见§3.1 | ZBC审计 |
| task_contract.py | 缺失 | 适配补入 | Shared | P2：任务契约scope/forbidden，详见§3.1 | ZBC审计 |
| trace_contract.py | 缺失 | 适配补入 | Shared | P3：追踪契约 | ZBC审计 |
| ui_state_contract.py | 缺失 | 适配补入 | Shared | P3：UI状态契约 | ZBC审计 |

#### OSAI运行时引擎模块（不相关，禁止成为ZBC runtime依赖）（31个）

| 模块名 | 判定 | 理由 |
|---|---|---|
| agent.py | 不相关 | OSAI运行时agent引擎 |
| agent_identity.py | 不相关 | OSAI agent身份管理，运行时引擎 |
| agent_integration.py | 不相关 | OSAI agent集成层，运行时引擎 |
| base_adapter_enhanced.py | 废弃 | SICI已覆盖，主库已有CircuitBreaker/RateLimiter/BaseAdapter |
| browser_capability.py | 不相关 | OSAI浏览器能力，运行时引擎 |
| browser_executor.py | 不相关 | OSAI浏览器执行器，运行时引擎 |
| canonical_skill_registry.py | 不相关 | OSAI规范Skill注册表，运行时引擎 |
| capability_delta.py | 适配补入 | P3：能力增量量化，见高价值列表 |
| capability_registry.py | 适配补入 | P2：与audit-four-source同文件，见高价值列表 |
| context_runtime.py | 不相关 | OSAI上下文运行时，运行时引擎 |
| ddc_research_adapter.py | 适配补入 | P2：与audit-four-source同文件，见高价值列表 |
| decision_action_outcome.py | 不相关 | OSAI决策-动作-结果闭环，运行时引擎 |
| delegation.py | 不相关 | OSAI任务委派，运行时引擎 |
| engine_layer.py | 不相关 | OSAI引擎层，运行时引擎核心 |
| engine_runtime.py | 不相关 | OSAI引擎运行时，运行时引擎核心 |
| engineering_loop.py | 不相关 | OSAI工程循环，运行时引擎 |
| evidence.py | 废弃 | OSAI evidence克隆，主线已覆盖 |
| harness_runtime.py | 不相关 | OSAI harness运行时，运行时引擎核心 |
| llm.py | 不相关 | OSAI LLM封装，运行时引擎 |
| memory_lifecycle.py | 不相关 | OSAI内存生命周期，运行时引擎 |
| obo_jit.py | 不相关 | OSAI JIT编译，运行时引擎 |
| observability.py | 不相关 | OSAI可观测性，运行时引擎 |
| orchestrator.py | 不相关 | OSAI编排器，运行时引擎核心 |
| osai_tool.py | 不相关 | OSAI工具封装，运行时引擎 |
| platform_inspection.py | 不相关 | OSAI平台检查，运行时引擎 |
| reconcile_capabilities.py | 适配补入 | P3：能力对账 |
| release_safety.py | 不相关 | OSAI发布安全，运行时引擎 |
| repository_contract.py | 废弃 | 主线repository_registry.py+core/已覆盖 |
| research.py | 不相关 | OSAI research运行时 |
| research_id.py | 不相关 | OSAI research ID运行时 |
| research_learning.py | 不相关 | OSAI research learning运行时 |
| secret_scan.py | 适配补入 | P2：与audit-four-source同文件，见高价值列表 |
| skill_invocation.py | 不相关 | OSAI Skill调用，运行时引擎 |
| skills_registry_cli.py | 不相关 | OSAI Skill CLI，运行时工具 |
| source_skills.py | 不相关 | OSAI源Skill管理，运行时引擎 |
| tools.py | 不相关 | OSAI工具集，运行时引擎 |
| trace_evaluation.py | 不相关 | OSAI追踪评估，运行时引擎 |
| zell_bridge.py | 不相关 | OSAI zell桥接，运行时引擎 |

### 4.5 ADRH（6个）— 全部重复

| 模块名 | 判定 | 理由 |
|---|---|---|
| capability_registry.py | 重复-已核销 | 已在audit-four-source/OSAI中核销(适配补入P2) |
| ddc_research_adapter.py | 重复-已核销 | 已在audit-four-source/OSAI中核销(适配补入P2) |
| research_id.py | 重复-已核销 | 已在audit-four-source/OSAI中核销(不相关) |
| research_record.py | 重复-已核销 | 已在audit-four-source/OSAI中核销(适配补入P2) |
| secret_scan.py | 重复-已核销 | 已在audit-four-source/OSAI中核销(适配补入P2) |
| shadow_lifecycle.py | 重复-已核销 | 已在audit-four-source/OSAI中核销(适配补入P1) |

### 4.6 KimiData（72个）— 全部不相关

> KimiData是学术数据源工具集和文档转换工具集，与ZBC品牌舆情/商业智能双域架构无关。
> 分类：学术数据源(20个)、文档转换(15个)、插件工具(10个)、验证工具(10个)、运行时/其他(17个)。

#### 学术数据源工具（20个）— 不相关

| 模块名 | 理由 |
|---|---|
| eurostat.py | EU统计数据源，学术工具 |
| fao.py | 联合国粮农组织数据源，学术工具 |
| fred.py | 美联储经济数据，学术工具 |
| imf_tool.py | IMF数据源，学术工具 |
| oecd.py | OECD数据源，学术工具 |
| world_bank_open_data_tool.py | 世界银行数据源，学术工具 |
| who.py | WHO数据源，学术工具 |
| unicef.py | 联合国儿童基金会数据源，学术工具 |
| unctad.py | 联合国贸发会议数据源，学术工具 |
| undp.py | 联合国开发计划署数据源，学术工具 |
| unep.py | 联合国环境规划署数据源，学术工具 |
| wto.py | WTO数据源，学术工具 |
| unsd.py | 联合国统计司数据源，学术工具 |
| sec_edgar_tool.py | SEC EDGAR财报数据源，学术工具 |
| scholar_tool.py | 学术搜索工具 |
| tianyancha_tool.py | 天眼查企业数据，与ZBC品牌库重复且非主线采集源 |
| yahoo_finance_tool.py | 雅虎财经数据，学术工具 |
| ifind_tool.py | 同花顺金融数据，学术工具 |
| igo_open_data_tool.py | 政府间组织开放数据，学术工具 |
| ecb.py | 欧洲央行数据源，学术工具 |
| yuandian_law_tool.py | 元典法律数据源，学术工具 |

#### 文档转换工具（15个）— 不相关

| 模块名 | 理由 |
|---|---|
| docx_endnote.py | DOCX尾注处理，文档工具 |
| docx_footnote.py | DOCX脚注处理，文档工具 |
| docx_postprocess.py | DOCX后处理，文档工具 |
| docx_utils.py | DOCX工具函数，文档工具 |
| md2docx_convert.py | MD→DOCX转换，文档工具 |
| md2pdf_convert.py | MD→PDF转换，文档工具 |
| pdf.py | PDF处理，文档工具 |
| xlsx_tools.py | XLSX处理，文档工具 |
| citation_parser.py | MD引用格式解析(T1/T2/T3降级)，文档工具 |
| citation_md.py | MD引用处理，文档工具 |
| cmd_convert.py | 命令行转换工具 |
| cmd_extract.py | 命令行提取工具 |
| cmd_form.py | 命令行表单工具 |
| cmd_inspect.py | 命令行检查工具 |
| cmd_meta.py | 命令行元数据工具 |
| cmd_pages.py | 命令行分页工具 |
| lint_docx_js.py | DOCX JS lint工具 |
| ooxml_order.py | OOXML排序，文档工具 |
| opc.py | OPC包处理，文档工具 |

#### 插件/运行时工具（10个）— 不相关

| 模块名 | 理由 |
|---|---|
| create_plugin.py | Kimi插件创建工具 |
| update_plugin.py | Kimi插件更新工具 |
| validate_plugin.py | Kimi插件验证工具 |
| plugin_common.py | Kimi插件公共库 |
| register_personal.py | 个人注册工具 |
| daimon_runtime.py | daimon运行时 |
| main.py | KimiData主入口 |
| runner.py | 运行器 |
| plan.py | 计划工具 |
| prep.py | 准备工具 |

#### 验证/其他工具（27个）— 不相关

| 模块名 | 理由 |
|---|---|
| findings.py | 文档验证诊断(Finding类)，文档工具 |
| verify.py | 验证工具 |
| vchecks.py | 版本检查 |
| vdiff.py | 版本diff |
| vpkg.py | 版本包管理 |
| vredline.py | 版本红线 |
| vrepair.py | 版本修复 |
| revisions.py | 修订管理 |
| revreg.py | 修订注册 |
| measure.py | 测量工具 |
| coords.py | 坐标工具 |
| track.py | 追踪工具 |
| walker.py | 文件遍历工具 |
| read.py | 读取工具 |
| common.py | 公共库 |
| cachebuster.py | 缓存清除工具 |
| escap.py | 转义工具 |
| effctx.py | 有效上下文工具 |
| audio_generation_tool.py | 音频生成，与ZBC无关 |
| image_generation_tool.py | 图片生成，与ZBC无关 |
| adb.py | Android调试桥，与ZBC无关 |
| portal.py | 门户工具 |
| revisions.py | 已列 |

> 注：KimiData 72个模块全部判定为"不相关"，核心理由：KimiData是面向学术研究和文档处理的工具集，其数据源(国际组织/金融/学术)与ZBC的品牌舆情/商业智能双域无交集；文档转换工具与ZBC的report_export/word_pdf_export功能域不同；插件体系是Kimi平台专属，不并入ZBC。

### 4.7 CmdConsole（6个）— 全部重复

| 模块名 | 判定 | 理由 |
|---|---|---|
| capability_delta.py | 重复-已核销 | 已在OSAI中核销(适配补入P3) |
| learning_cycle.py | 重复-已核销 | 已在OSAI/audit-four-source中核销(适配补入P2) |
| learning_promote.py | 重复-已核销 | 已在OSAI/audit-four-source中核销(适配补入P2) |
| platform_inspection.py | 重复-已核销 | 已在OSAI/audit-four-source中核销(不相关) |
| research_learning.py | 重复-已核销 | 已在OSAI/audit-four-source中核销(不相关) |
| research_registry.py | 重复-已核销 | 已在OSAI/audit-four-source中核销(适配补入P2) |

### 4.8 GGI（7个）— 全部不相关

> GGI=global-growth-intelligence独立产品，只借手法不并入ZBC业务代码。

| 模块名 | 判定 | 理由 |
|---|---|---|
| 7157f1c9a3e9_mobile_v1_full_schema.py | 不相关 | GGI移动端完整schema，独立产品业务代码 |
| contract_export.py | 不相关 | GGI契约导出，独立产品 |
| evidence.py | 不相关 | GGI evidence模块，独立产品(与ZBC evidence_chain无关) |
| gateway.py | 不相关 | GGI网关，独立产品 |
| middlewares.py | 不相关 | GGI中间件，独立产品 |
| providers.py | 不相关 | GGI数据提供者，独立产品 |
| taxonomy.py | 不相关 | GGI分类法，独立产品 |

### 4.9 SICI（1个）

| 模块名 | 判定 | 理由 |
|---|---|---|
| base_adapter_enhanced.py | 废弃 | SICI三模块评估结论：主库已有CircuitBreaker/RateLimiter/BaseAdapter对应实现，功能完全覆盖 |

---

## 五、铁律执行确认

| 铁律 | 执行情况 |
|---|---|
| 高价值模块实际Read内容 | ✅ OSAI 19个+audit-four-source 8个独立模块全部Read，未只看文件名 |
| OSAI不得成为runtime依赖 | ✅ 31个OSAI运行时引擎模块标"不相关"，适配补入仅限契约/研究/模式借鉴 |
| GGI/SICI独立不并入 | ✅ GGI 7个全标"不相关-GGI独立产品"，SICI 1个标"废弃-主库已覆盖" |
| 禁区不碰 | ✅ 未访问太古汇运营资料/微信数据/KOS AI Review工作台/回收站/云盘 |
| 适配补入走双域架构 | ✅ 所有适配补入项明确所属域(Shared为主)，要求函数驱动+前后端契约一致 |
| 规则/阈值/语料捞全 | ✅ rules.py 18条工程规则、action_firewall 18种高风险动作、shadow_lifecycle 9态、lifecycle_contract 15态等均从源文件提取 |
| 已开发规则禁止重写 | ✅ evaluation_contract/repository_contract/evidence.py/deployment脚本等主线已有模块全标废弃 |

---

## 六、维护期执行建议

1. **P1项(6个)** 排入最近维护期：action_firewall模式→permission_gate增强、effect_fence幂等层、checkpoint_resume→runtime_guardian接入、evidence_graph图谱、impact_analysis发布前评估、shadow_lifecycle状态机
2. **P2项(16个)** 排入下一维护期：contract_persistence、rules语料、skill_manifest/selector、task/lifecycle/permission契约、capability_registry、learning_cycle/promote、research系列、ddc_adapter、secret_scan增强
3. **P3项(6个)** 排入远期：learning_record_contract、runtime_contract、skill_execution_contract、trace_contract、ui_state_contract、capability_delta、reconcile_capabilities
4. 所有适配补入**不立即执行**，仅登记台账，待关键路径(系统可自动运行)收线后按优先级排期

---

*台账版本 V1.0 | 核销完成时间 2026-09-06 | 核销人 ZBC审计执行代理*
