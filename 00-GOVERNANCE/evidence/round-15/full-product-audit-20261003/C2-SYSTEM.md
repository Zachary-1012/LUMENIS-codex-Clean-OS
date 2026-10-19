# C2 + SYSTEM 执行链只读审计

日期：2026-10-03
范围：C2/W2 的 AI Gateway、owned training/inference、Agent/Skills、Memory/Context、Evaluation/Learning、MCP，以及 SYSTEM 的 Core/API、startup/recovery、Permission、Action Firewall、Effect Fence。
边界：未运行测试；未访问数据库、启动/重启进程、调用模型/GPU/浏览器、下载资源或执行 Git 操作。本文只记录定向源码阅读和已有回执，不代表完整仓库或线上验收。

## 判断

后续运行回执已更新先前状态：Core reload 和新 review routes 已成功验证；original12 的真实审阅/导出已完成。旧的 reload access denied 与 live 404 只是更早的历史观察，不再是当前下一步，也不应要求 W6 重做。

当前可见源码有单一 AI Gateway、训练授权/回执接口、训练审阅与导出路由，以及 Agent/Skill 的 Permission、Firewall、Effect Fence 和 Evidence 组合。执行状态分层如下：

1. original12 的审阅/导出运行回执记录 8 条 training、4 条 held-out，12 条已导出，另有 24 条 rights/review 关联；review-submissions 与 review-exports 均为 200。training_started=false、GPU_started=false、费用为零，所以它证明真实材料审阅/导出，不证明训练已启动。
2. W2 MatPool Blackwell 冻结候选中存在 RTX 5090 recipe、checkpoint producer/recovery 源码和相应 source pins。该 candidate manifest 将 5090 标为 APPROVED_COMPATIBILITY_NOT_LIVE_VERIFIED；execution request 未确认资源或训练。其 checkpoint 源码要求的 recovery policy registry 不在该 candidate 固定的 ai-owned-foundation manifest 中，仍有 manifest binding 缺口。候选源码不等于主线集成或实际训练。
3. 先前审阅的当前仓库路径 owned_training.py 只有 T4、H100、4090 recipe，未见 5090；由于本审计不运行 Git，不能把这份本地字节独立归属到 a684 main。应分别记录为“本地当前源码未见”与“冻结候选已有”，避免说全无或说主线已支持。
4. 当前 Gateway owned inference 状态仍为 NOT_BOUND，candidate loader 的服务绑定不等于产品调用；未找到 Core/API/Agent 到 load_owned_inference 的产品调用。
5. 当前 trainer 仍无物理 checkpoint/resume 实际执行证据。训练阶段 signer public config receipt 已生成；M 记录 pause 后没有实际 phase retry，因此当前 phase runtime permission/receipt 仍未验证，不能继续旧的 route-recovery 工作或推定阶段执行。
6. 原始训练材料审阅/导出已完成；后续训练批准、真实 GPU 训练、独立 held-out 质量、owned inference 服务、用户可见结果与失败恢复仍是不同验收层。现有回执明确 C2 未接受。

源码、候选和运行回执能证明上述各自层级，不能互相替代，也不能把历史技术测试或 GPU 租用当作 C2 完成。
## 源码与调用链覆盖

| 领域 / 唯一 owner | 定向查看的源码与调用点 | 已有测试 / 回执（本次未运行） | 当前可证明层级与断点 |
|---|---|---|---|
| AI Gateway / provider routing | lumenis/system/ai_gateway/providers.py:23-28,102-129,189-227；core.py:49-55,136-141,171-180；调用方 ai_task_engine.py:2950-3021 | tests/test_ai_gateway.py、tests/test_ai_gateway_result_status.py；owned-training source-evidence receipt | 源码把 Zhipu、Ollama、LM Studio、llama.cpp 标为 retired，并在 availability/probe 路径跳过它们。AI_PROVIDER=auto 也在早期 guard 下不可用；因此 ALLOW_CLOUD_AI 后备分支在默认 auto 路径不可达。rule/unavailable 状态有显式标记，不能视为 owned-model 推理。实际环境变量、provider binding 和运行调用未检查。 |
| Owned training / phase callback | lumenis/system/ai_gateway/owned_training.py:19-22,254-293,296-349,417-457；owned_training_phases.py:1-5,24-53,166-204 | tests/test_owned_ai_training.py、tests/test_owned_training_callback_v3.py、tests/test_owned_training_phase_http_v2.py；c433 callback source-evidence receipt | 预检默认 execute=False，只返回 VALIDATED_LOCAL_INPUTS_NOT_PRODUCTION_ACCEPTANCE。执行要求 verifier、精确 TrainingPhaseClient、authorize、model permit 复核及 current receipt。phase client 的 transport 由调用方提供；搜索到的构造点仅在测试，未找到生产 caller。历史 receipt 可读但标为不可用于授权执行。 |
| Owned inference / candidate evaluation | owned_inference.py:27-56,68-76；owned_evaluation.py:131 | tests/test_owned_candidate_evaluation.py；MatPool 与冻结候选回执 | 状态缺省 available=false、service_binding=NOT_BOUND、NOT_PROMOTED。只有候选评估前置调用，没有发现 Core/API/Agent 产品服务调用。加载器只接受 T4 recipe。没有实际模型加载、服务绑定或推理结果证据。 |
| GPU recipe / 5090 | 本地当前源码 owned_training.py:19-22,254-269 未见 5090（未以 Git 确认归属 a684）；冻结 W2 candidate 在 C:\Users\private-user-121dcc385158\AppData\Local\Temp\lumenis-w2-training-blackwell-4863724-v3-20261003 的 owned_training.py:23-48,316-337 与 config/ai-owned-foundation.json:117-151 有 RTX 5090 / SM120 / CUDA 12.8 recipe | work/w2-owned-ai-20261002/matpool-blackwell-20261003/CANDIDATE-INPUTS.json、ACTUAL-EXECUTION-REQUESTS.json、EXPENSE-CLEANUP-PAUSED.json | 候选 recipe 状态 APPROVED_COMPATIBILITY_NOT_LIVE_VERIFIED；请求 confirm=false、confirmed_resource=null、GPU_started=false；实例 ZDLYrY 已释放，0 steps、未加载模型、无 adapter/checkpoint、held-out/inference 未运行。候选有 recipe 源码，不能据本地当前源缺失说所有工作不存在，也不能称主线/运行已支持。 |
| Training review / Evidence admission API | experience_runtime.py:983-1053,1090-1178；training_review.py、training_cases.py；app.py:551-557,1522-1523,1623-1642 | work/w6-integration-20261002/training-review-runtime-20261003/actual-20261003T091921Z/ACTUAL-RECEIPT.json；tests/test_owned_training_review.py、tests/test_owned_training_cases.py（本次未运行） | 实际审阅/导出完成：8 training、4 held-out、12 real_exported_records、24 rights/review 关联；两路由 200，training_started=false、GPU_started=false。证明 original12 审阅与导出，不启动训练。Core reload receipt state=NEW_CORE_AND_REVIEW_ROUTES_VERIFIED；旧 access denied/live 404 是历史状态，不构成当前重载任务。 |
| Checkpoint / recovery | 主线工作区 owned_training.py:417-457、owned_training_phases.py:166-204；W2 冻结候选 owned_training_checkpoints.py:211+,290+,557+,605+ 与 owned_training_runtime.py:1286-1312 | work/w2-owned-ai-20261002/matpool-blackwell-20261003/CANDIDATE-INPUTS.json；work/m-controller-20261002/training-checkpoint-recovery-m-decision-20261003.md | 本地当前 trainer 仍 save_strategy=no、无 resume checkpoint。Blackwell 冻结候选有 checkpoint policy/adapter/runtime 源码与 source hashes；但其固定 config/ai-owned-foundation.json 未含 checkpoint_recovery_policies registry，而 load_recovery_policy 要求该 registry。候选 recovery source 有实现内容但 manifest binding 未闭合；无物理保存/重载/恢复的 GPU 执行证据。 |
| Agent runtime / durable task state | agent_runtime/loop.py、durable_adapter.py、planner.py；agent_memory/working.py:118,125-126,181-229；ai_task_engine.py:2950-3021 | tests/agent_runtime/*、tests/agent_memory/* | durable adapter 将 canonical AI TaskEngine checkpoint 作为恢复 owner；working-memory observation 明确不等同可恢复 checkpoint。该链连接 task execution，不会因此绑定 owned inference。实际生产恢复/用户任务未在本审计运行。 |
| Skills / agent effect path | lumenis/shared/agents/skills/execution.py:694-819；registry.py、lifecycle.py、package_runtime.py；agent_capability/router.py、formation.py | tests/test_agent_security.py、tests/test_ai_permission_matrix.py（本次未运行）；M 确认 lifecycle.py 当前 tracked | 源码顺序包含 Permission → Action Firewall → Effect Fence → execute → Evidence/evaluation/trace；effectful action 要求 Evidence。Fence complete() 异常在执行路径被吞掉（782-788），实际影响未由本审计运行验证。lifecycle.py 当前 tracked，因此不能沿用有关该文件缺失的旧观察。未证明 Skill 调用了 owned inference。 |
| MCP | mcp_discovery.py:338-420；mcp_skill_runtime.py:173-215 | tests/test_mcp_skill_runtime.py | stdio 调用校验 process/tool/human approval、scope、reviewed allowlist 和 read-only 元数据；注册工具调用嵌在 Skill 执行链。发现代码从已注册 metadata 设置部分许可标记；安全有效性依赖外层真实 Permission/Firewall/Evidence。未检查 live 注册、未发 MCP 调用。 |
| Memory / Learning | lumenis/shared/learning/memory.py:94-127,187-267,271-346；loop.py:177-197,199-249,314-350；feedback.py、persistence.py | 相关共享学习/记忆测试未运行；既有 source receipts | 源码有 raw→reviewed→validated→promoted 流程。但 persistence 异常会被静默吞掉；promote 可先改内存状态，DB 读失败时 get_promoted_rules 可回落到内存记录。静态上存在 durability/status 可观测性风险；本审计未读 DB，不能判断实际数据或运行表现。 |
| Context / Evaluation | subject_context.py；lumenis/shared/evaluation/{recorder,runner,ai,trajectory,multimodal}.py；shared/learning/loop.py | evaluation/learning 目标测试未运行；既有候选/训练回执 | 定向确认 Context 是请求线程上下文，不能取代单独 Permission。可见 learning/evaluation 调用链；没有证明 held-out 执行、有效目标 admission、promoted owned model 或生产 Context/Permission binding。具体所有调用方与 lineage 闭合仍 UNKNOWN。 |
| Core/API routes | app.py:507-509,551-557；ai_api.py:301-312,446；app.py:2361；lumenis_app_api.py、lumenis/blueprint.py | tests/test_permission_gate_app_integration.py、runtime route checks in existing receipt；M runtime amendment | AI API 与 Experience blueprint 由 Core 静态注册。源码同时在 ai_api.py blueprint 与 app.py 声明 /api/ai/tasks GET/POST，后者调用 run_execution_chain；有效路由优先级未以运行态确认，是需 W6 核对的路由歧义。API 存在不证明训练/推理服务绑定。 |
| Permission / Firewall / Effect Fence | lumenis/system/security/permission.py、action_firewall.py、effect_fence.py；training callback boundary above；skill execution above | tests/test_permission_gate.py、tests/test_permission_gate_app_integration.py、tests/test_ai_permission_matrix.py；callback receipts | 当前训练意图需要 review/确认/Permission 与分阶段回执；Skill 路径显式执行安全链。此任务只静态追链，未验证 live policy、token freshness、revocation、deny-side-effect 或持久审计。源文件 hashes 与 c433 旧 receipt 不同（见下）；不得将旧测试结果移植到当前字节。 |
| Startup / supervised runtime | scripts/start_production.ps1、run_supervised.py、app.py | work/w6-integration-20261002/core-admin-reload-20261003/actual-20261003T181603641/verify.json；M 的当前状态回报 | 2026-10-03 18:16:07 receipt state=NEW_CORE_AND_REVIEW_ROUTES_VERIFIED、admin=true。Core reload 已成功，review routes 已验证。早先 reload 被拒与新路由 404 只保留为历史观察，不作为现状或下一步。此回执证明该时点路由验证，不证明训练执行、GPU、owned inference 或 C2 完成。 |

## 基线、脏树与候选证据边界

- a6844a98032ed1ffa0be8f99c40f7b99ba14d453 是任务上下文提供的 main 基线。本审计按指示不运行 Git，因此不能独立确认当前 HEAD、工作区 dirty delta，或逐文件把本地观察分类为该 SHA 的源。
- 与较早 c433a5579abccd17aeee618926daf529cdce3c8f source-evidence receipt 比较：owned_training.py、owned_training_phases.py、training_receipts.py 的本地字节 hash 与 receipt 一致；app.py、experience_runtime.py、ai_task_engine.py、permission.py、effect_fence.py 不一致。此比较只说明与 c433 receipt 的差异，不能归因到 a684 或当前 dirty work。
- W2 冻结候选 e5903ec... / base d73e807... 是独立候选，记录为 AMENDED_SOURCE_REVIEW_ACCEPTED_INTEGRATION_PENDING，20 个文件；不能当作当前 main 源码。
- W2 Blackwell 冻结候选另有独立 pinned source：CANDIDATE-INPUTS.json 指向 base 4863724...、rule_revision a6844a98... 与本机 Temp 候选，并固定 owned_training_runtime.py、owned_training_checkpoints.py、owned_training.py、config/ai-owned-foundation.json 的哈希。候选 config 中 RTX 5090 recipe 位于 training_recipes，状态 APPROVED_COMPATIBILITY_NOT_LIVE_VERIFIED；训练源声明 BLACKWELL_RECIPE，支持 SM120/CUDA 12.8。checkpoint 源有 CheckpointPolicy、TrainingCheckpointAdapter 与 runtime save/load 代码，但固定 config manifest 缺 checkpoint_recovery_policies；ACTUAL-EXECUTION-REQUESTS 也记录 confirmed_resource=null、confirm=false，CANDIDATE-INPUTS 记录 GPU_started=false、cost_cny=0。它是存在的候选源，不是 main 集成、有效 checkpoint policy binding 或运行训练证明。
- 另一个 d92 后续候选的 35-path publication receipt 记录曾在 HEAD/origin 4e674a... 完成发布与远端回读，后来 c433 receipt 修正文档哈希。该 receipt 明确 runtime_mounted=false、cloud_accessed=false、formal_db_touched=false、C2_accepted=false、C6_accepted=false。历史发布事实不能替代当前 a684 基线确认。
- matpool-blackwell/verification-1.json 记录 304 个技术测试通过；verification-2.json 记录 16 个技术测试。二者都记录 actual_model_run=null / actual_gpu_training=NOT_RUN，属于各自候选 SHA 的技术证据。本审计没有复跑它们。
- 00-GOVERNANCE/evidence/round-07/owned-training-phase-callback-20261003/source-evidence.json 记录早先 343 个用例中 331 pass、12 errors；仅修复的 12 个用例之后复跑通过，并非一次 343 全绿运行。回执同样不接受 C2、不证明实际训练、owned inference、runtime loaded、USER_VERIFIED、RELEASED 或 OPERATING。
- W2 original12/GPU authorization 与 RTX5090 amendment 证明人的授权/硬件选择边界；它们不证明源权利入库、实际训练、held-out 质量或服务可用。

## 最小闭环缺口与建议验证次序

1. Core reload、review routes 与 original12 审阅/导出已有成功回执；不要重复重载或重做材料审阅。SIGNER-PUBLIC-CONFIG-RECEIPT.json 已生成，但 M 记录 pause 后无实际 phase retry；本报告只将其记为尚无 phase runtime 执行证据。
2. RTX 5090 recipe 已存在于 W2 Blackwell frozen candidate；此前 inspected 本地当前源没有该 recipe，且本审计不以 Git 将该字节归属到 a684 main。若进入集成阶段，复用并审查这个候选，不另造 recipe；candidate 自身仍是 compatibility-not-live-verified。
3. checkpoint/recovery source 也存在于 Blackwell candidate，但固定 manifest 缺 recovery policy registry。闭环需在授权集成后统一源/manifest binding，并取得真实 save、load、resume 证据；当前没有 GPU checkpoint 运行证据。
4. original12 的 review/export 已完成并覆盖 8 training、4 held-out、24 rights/review 关联。仍未证明真实训练、独立 held-out 评估结果、owned inference binding、用户可见结果及失败恢复；遵守当前 pause，不由本只读报告触发 phase retry。

本报告覆盖表中定向模块与关键调用点。Core reload 与 review/export 运行结论引用指定时点的 receipt；未检查之后的进程状态。未确认当前实际权限/phase retry、GPU 执行、模型推理或用户 E2E。a684 是任务给定的 main 基线，Git 操作被禁止，所以本地当前源码与该 SHA 的逐文件映射仍 UNKNOWN；候选 receipt 独立列示，不冒充 main。
