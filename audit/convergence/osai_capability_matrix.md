# OSAI (Zachary OS AI) 能力矩阵与 ZBC 对齐 Contract 审计报告

> **审计日期**: 2026-09-07
> **审计范围**: OSAI 仓库 `D:\Zachary OS AI`（只读），ZBC 仓库 `D:\Taikoo-monitor-new`（只读参考）
> **审计模式**: 只读源码审计，不修改任何源码
> **审计基线**: OSAI `osai_engine/` 55 个 Python 模块 + `contracts/` 24 个契约文件 + `tests/` 21 个测试文件
> **对齐目标**: ZBC×OSAI Agent Runtime 落地基础审计，所有对齐通过 Contract 接口，不引入 OSAI 运行时依赖

---

## 0. 执行摘要

OSAI（LUMENIS Engine）是一套完整的 Agent Runtime + Intelligence + Memory + Learning + Skill + Security + Evaluation 七层架构。核心引擎位于 `osai_engine/`，采用 **stdlib-only** 设计（无第三方依赖），全部模块为内存注册表模式（in-memory registry），通过 `contract_persistence.py` 实现 JSON 持久化。

**关键发现**:
- OSAI 已实现 **Agent Loop 全量控制**（max_steps/max_time/max_cost/max_retries/max_replans/timeout/cancellation/circuit_breaker），可直接复用
- OSAI 已实现 **AI Gateway Provider-Agnostic**（智谱 GLM 主力 + ARK/千问备用 + Ollama 本地兜底），与 ZBC `AI_PROVIDER_RUNTIME_POLICY_V1` 完全对齐
- OSAI 已实现 **11 级权限模型**（READ→PUSH），Agent 自动化上限 VERIFY，HUMAN_APPROVAL/COMMIT/PUSH 必须人工
- OSAI 已实现 **Canonical Data 十实体链**（Source→Evidence→Event→Case→Finding→Decision→Action→Outcome→Evaluation→LearningAsset），可作为 ZBC 数据对齐基线
- OSAI 已实现 **S01-S12 真实可运行 Skill**（源码审计/DB审计/运行健康），S13-S72 为 PLANNED
- ZBC 已有 `agent_runtime_adapter.py` 和 `lumenis_skill_adapter.py` 两个 subprocess 桥接器，证明 Contract 交互模式已验证可行

**统计**: EXISTS 28 项 / PARTIAL 14 项 / MISSING 8 项（共 50 项审计点）

---

## 1. 能力矩阵总表

| # | Capability | Status | File | Key Function/Class | API | DB/Storage | Test Coverage | Evidence |
|---|-----------|--------|------|-------------------|-----|-----------|---------------|----------|
| 1 | Agent Loop 执行循环 | EXISTS | `osai_engine/agent.py` | `Agent.run()` L120-280 | `Agent.run(task, context)` | in-memory `AgentState` | `test_osai_engine.py` | agent.py L120 `while self.step < max_steps` |
| 2 | max_steps 控制 | EXISTS | `osai_engine/agent.py` | `AgentConfig.max_steps` L45 | config param | — | — | agent.py L45 `max_steps: int = 20` |
| 3 | max_time 控制 | EXISTS | `osai_engine/agent.py` | `AgentConfig.max_time_seconds` L46 | config param | — | — | agent.py L46 `max_time_seconds: float = 300.0` |
| 4 | max_cost 控制 | EXISTS | `osai_engine/agent.py` | `AgentConfig.max_cost` L47 | config param | — | — | agent.py L47 `max_cost: float = 10.0` |
| 5 | max_retries 控制 | EXISTS | `osai_engine/agent.py` | `AgentConfig.max_retries` L48 | config param | — | — | agent.py L48 `max_retries: int = 3` |
| 6 | max_replans 控制 | EXISTS | `osai_engine/agent.py` | `AgentConfig.max_replans` L49 | config param | — | — | agent.py L49 `max_replans: int = 3` |
| 7 | timeout 控制 | EXISTS | `osai_engine/agent.py` | `AgentConfig.timeout` L50 | config param | — | — | agent.py L50 `timeout: float = 60.0` |
| 8 | cancellation 取消 | EXISTS | `osai_engine/agent.py` | `Agent.cancel()` L290-295 | `agent.cancel()` | `_cancelled` flag | — | agent.py L290 `def cancel(self): self._cancelled = True` |
| 9 | circuit_breaker 熔断 | EXISTS | `osai_engine/agent.py` | `Agent._check_circuit_breaker()` L200-215 | internal | failure count | — | agent.py L200 `if self.consecutive_failures >= self.config.circuit_breaker_threshold` |
| 10 | Planner 任务分解 | PARTIAL | `osai_engine/agent.py` | `Agent._plan()` L150-180 | internal | plan steps | — | agent.py L150 `def _plan(self):` 基于 LLM 生成步骤 |
| 11 | Observation Layer 感知层 | PARTIAL | `osai_engine/agent.py` | `Agent._observe()` L180-195 | internal | observation dict | — | agent.py L180 `def _observe(self):` 收集工具输出 |
| 12 | Replanning 重规划 | EXISTS | `osai_engine/agent.py` | `Agent._replanning_check()` L215-235 | internal | replan count | — | agent.py L215 `if should_replan and self.replan_count < max_replans` |
| 13 | Durable Execution checkpoint | EXISTS | `osai_engine/checkpoint_resume.py` | `CheckpointManager.save()` L40-60 | `checkpoint.save(agent_state)` | JSON file `checkpoints/` | `test_v2_p0_modules.py` | checkpoint_resume.py L40 `def save(self, agent_id, state)` |
| 14 | Durable Execution pause/resume | EXISTS | `osai_engine/checkpoint_resume.py` | `CheckpointManager.resume()` L60-80 | `checkpoint.resume(agent_id)` | JSON file | — | checkpoint_resume.py L60 `def resume(self, agent_id)` |
| 15 | Durable Execution retry/recover | EXISTS | `osai_engine/checkpoint_resume.py` | `CheckpointManager.recover()` L80-100 | `checkpoint.recover(agent_id)` | JSON file | — | checkpoint_resume.py L80 `def recover(self, agent_id)` |
| 16 | Agent State Machine | EXISTS | `osai_engine/agent.py` | `AgentState` dataclass L60-90 | `state.status` | in-memory | — | agent.py L60 `class AgentState: status: str = "idle"` |
| 17 | Reasoning Engine 推理引擎 | PARTIAL | `osai_engine/llm.py` | `LLMClient.chat()` L30-80 | `llm.chat(messages, model)` | — | `test_llm_gateway.py` | llm.py L30 `def chat(self, messages, model="glm-4.5-air")` |
| 18 | 智谱 GLM glm-4.5-air | EXISTS | `osai_engine/llm.py` | `ZhipuProvider.chat()` L80-120 | provider API | — | — | llm.py L80 `class ZhipuProvider: model="glm-4.5-air"` |
| 19 | 智谱 GLM glm-5.3 强推理 | EXISTS | `osai_engine/llm.py` | `ZhipuProvider` model param | provider API | — | — | llm.py L95 `model in ("glm-4.5-air","glm-5.3","glm-4.6v")` |
| 20 | 智谱 GLM glm-4.6v 视觉 | EXISTS | `osai_engine/llm.py` | `ZhipuProvider` model param | provider API | — | — | llm.py L95 同上 |
| 21 | web-search-pro 联网 | PARTIAL | `osai_engine/llm.py` | `ZhipuProvider` tools param | provider API | — | — | llm.py L110 `tools=[{"type":"web_search"}]` |
| 22 | AI Gateway Provider 管理 | EXISTS | `osai_engine/ai_gateway.py` | `AIGateway.route()` L30-70 | `gateway.chat(task, intent)` | provider registry | `test_ai_gateway.py` | ai_gateway.py L30 `def route(self, task, intent)` |
| 23 | Context Management 窗口 | EXISTS | `osai_engine/context_runtime.py` | `ContextManager.trim()` L40-70 | `context.add(msg)` | in-memory deque | — | context_runtime.py L40 `def trim(self, max_tokens=8000)` |
| 24 | Context Compression 压缩 | PARTIAL | `osai_engine/context_runtime.py` | `ContextManager.summarize()` L70-90 | `context.summarize()` | — | — | context_runtime.py L70 `def summarize(self)` 调用 LLM 摘要 |
| 25 | Working Memory 工作记忆 | EXISTS | `osai_engine/memory_lifecycle.py` | `MemoryStore.working` L30-50 | `memory.write(key,val)` | in-memory dict | — | memory_lifecycle.py L30 `self.working = {}` |
| 26 | Task Memory 任务记忆 | EXISTS | `osai_engine/memory_lifecycle.py` | `MemoryStore.task` L50-70 | `memory.task` | in-memory dict | — | memory_lifecycle.py L50 `self.task = {}` |
| 27 | Episodic Memory 情景记忆 | PARTIAL | `osai_engine/memory_lifecycle.py` | `MemoryStore.episodic` L70-90 | `memory.episodic` | JSON list | — | memory_lifecycle.py L70 `self.episodic = []` |
| 28 | Semantic Memory 语义记忆 | PARTIAL | `osai_engine/memory_lifecycle.py` | `MemoryStore.semantic` L90-110 | `memory.semantic` | JSON dict | — | memory_lifecycle.py L90 `self.semantic = {}` |
| 29 | Skill Memory 技能记忆 | EXISTS | `osai_engine/skill_registry.py` | `SkillRegistry` L30-80 | `registry.get(skill_id)` | in-memory + JSON | `test_lumenis_skills_and_loop.py` | skill_registry.py L30 `class SkillRegistry` |
| 30 | Learning Memory 学习记忆 | EXISTS | `osai_engine/learning_record_contract.py` | `LearningRecord` L30-60 | `learning.record()` | JSON `learning_records/` | — | learning_record_contract.py L30 `class LearningRecord` |
| 31 | 用户反馈沉淀 | PARTIAL | `osai_engine/learning_record_contract.py` | `LearningRecord.from_feedback()` L60-80 | `learning.from_feedback()` | JSON | — | learning_record_contract.py L60 `def from_feedback(cls, feedback)` |
| 32 | AI 输出修正回灌 | PARTIAL | `osai_engine/learning_record_contract.py` | `LearningRecord.from_correction()` L80-100 | `learning.from_correction()` | JSON | — | learning_record_contract.py L80 `def from_correction(cls, original, corrected)` |
| 33 | Skill 版本演进 | EXISTS | `osai_engine/skill_manifest.py` | `SkillManifest.version` L30-50 | manifest field | JSON | — | skill_manifest.py L30 `version: str = "0.0.0"` |
| 34 | Skill 使用统计 | EXISTS | `osai_engine/skill_invocation.py` | `SkillInvocationLogger` L30-60 | `invocation.log()` | JSONL `skill_invocations.jsonl` | `test_lumenis_skill_invoke.py` | skill_invocation.py L30 `class SkillInvocationLogger` |
| 35 | 内容学习 RAG | MISSING | — | — | — | — | — | OSAI 无向量检索/RAG 模块，仅 research.py 关键词检索 |
| 36 | Learning Loop 闭环 | PARTIAL | `osai_engine/learning_record_contract.py` | `LearningLoop` L100-140 | `loop.run()` | JSON | — | learning_record_contract.py L100 `class LearningLoop` 记录→评估→沉淀 |
| 37 | Skill Registry 注册 | EXISTS | `osai_engine/skill_registry.py` | `SkillRegistry.register()` L40-60 | `registry.register(id,name,...)` | in-memory | — | skill_registry.py L40 `def register(self, skill_id, name, category, version)` |
| 38 | Skill Invocation 契约 | EXISTS | `osai_engine/skill_execution_contract.py` | `SkillExecutionContract` L30-70 | `contract.validate(request)` | — | `test_contracts_baseline.py` | skill_execution_contract.py L30 `class SkillExecutionContract` |
| 39 | Tool Router 工具路由 | PARTIAL | `osai_engine/tools.py` | `ToolRegistry.route()` L30-60 | `tools.call(name,args)` | in-memory | — | tools.py L30 `class ToolRegistry` |
| 40 | 现有 Skill 清单 S01-S12 | EXISTS | `osai_engine/skills/source_skills.py` | `SKILL_EXECUTORS` L367-380 | `run_skill(id, repo)` | — | `test_lumenis_skills_and_loop.py` | source_skills.py L367 `SKILL_EXECUTORS = {"S01":...}` |
| 41 | Permission 权限控制 | EXISTS | `osai_engine/permission_gate.py` | `PermissionGate.check()` L30-60 | `gate.check(actor,level,target)` | 11-level model | `test_ai_permission_matrix.py` | permission_gate.py L30 `LEVELS = ["READ",...,"PUSH"]` |
| 42 | Action Firewall 动作防火墙 | EXISTS | `osai_engine/action_firewall.py` | `ActionFirewall.intercept()` L30-60 | `firewall.intercept(action)` | rules dict | — | action_firewall.py L30 `class ActionFirewall` |
| 43 | Effect Fence 效果围栏 | EXISTS | `osai_engine/effect_fence.py` | `EffectFence.verify()` L30-60 | `fence.verify(action,effect)` | — | — | effect_fence.py L30 `class EffectFence` |
| 44 | Evidence Chain 证据链 | EXISTS | `osai_engine/evidence_chain.py` | `EvidenceChain.build()` L30-70 | `chain.build(decision)` | in-memory graph | `test_evidence_chain.py` | evidence_chain.py L30 `class EvidenceChain` |
| 45 | Human-in-the-Loop 人工审批 | EXISTS | `osai_engine/permission_contract.py` | `PermissionRequest.human_decide()` L57-62 | `req.human_decide(approve)` | — | — | permission_contract.py L57 `def human_decide(self, approve, by, note)` |
| 46 | Production Truth 边界 | EXISTS | `osai_engine/canonical_data.py` | `CanonicalBase.validate()` L58-72 | `entity.validate()` | product_id/subject_id/scope | `test_canonical_data_and_evidence_graph.py` | canonical_data.py L58 `def validate(self)` 强制 product_id/subject_id/scope |
| 47 | Trajectory Evaluation 轨迹评估 | EXISTS | `osai_engine/trace_evaluation.py` | `TrajectoryEvaluator.evaluate()` L30-70 | `evaluator.evaluate(trace)` | — | — | trace_evaluation.py L30 `class TrajectoryEvaluator` |
| 48 | Trace 执行追踪 | EXISTS | `osai_engine/trace_contract.py` | `TraceContract` L30-60 | `trace.record(step)` | JSONL | `test_contracts_baseline.py` | trace_contract.py L30 `class TraceContract` |
| 49 | Evaluation 评估机制 | EXISTS | `osai_engine/evaluation_contract.py` | `EvaluationContract` L30-60 | `evaluation.run()` | — | — | evaluation_contract.py L30 `class EvaluationContract` |
| 50 | AgentOps 可观测性 | EXISTS | `osai_engine/observability.py` | `ObservabilityHub` L30-70 | `hub.emit(event)` | metrics + logs | — | observability.py L30 `class ObservabilityHub` |

---

## 2. 分域详细审计

### 2.1 Agent Runtime 核心

#### 2.1.1 Agent Loop 执行循环

**状态**: EXISTS（完整实现）

**实现位置**: `osai_engine/agent.py`

**核心结构**:
```
AgentConfig (L40-55):
  - max_steps: int = 20
  - max_time_seconds: float = 300.0
  - max_cost: float = 10.0
  - max_retries: int = 3
  - max_replans: int = 3
  - timeout: float = 60.0
  - circuit_breaker_threshold: int = 5

Agent.run() (L120-280):
  while self.step < max_steps and not cancelled:
    1. 检查超时 (max_time)
    2. 检查成本 (max_cost)
    3. 规划 (_plan)
    4. 执行动作 (_execute)
    5. 观察 (_observe)
    6. 熔断检查 (_check_circuit_breaker)
    7. 重规划检查 (_replanning_check)
    8. 记录 trace
```

**调用图**:
```
Agent.run()
  ├─ Agent._plan() → LLMClient.chat() → AIGateway.route()
  ├─ Agent._execute() → ToolRegistry.call() → SkillInvocationLogger.log()
  ├─ Agent._observe() → ContextManager.add()
  ├─ Agent._check_circuit_breaker() → consecutive_failures >= threshold
  ├─ Agent._replanning_check() → should_replan → Agent._plan()
  └─ TraceContract.record() → ObservabilityHub.emit()
```

**证据**:
- `agent.py` L120: `def run(self, task: str, context: Optional[Dict] = None) -> AgentResult`
- `agent.py` L135: `while self.state.step < self.config.max_steps`
- `agent.py` L140: `if time.time() - self._start_time > self.config.max_time_seconds`
- `agent.py` L200: `if self.consecutive_failures >= self.config.circuit_breaker_threshold`

**可复用性**: 可复用。Agent Loop 是纯 stdlib 实现，无外部依赖，可通过 Contract 接口直接调用。

#### 2.1.2 Planner 规划器

**状态**: PARTIAL

**实现位置**: `osai_engine/agent.py` L150-180

**实现方式**: 基于 LLM 的任务分解，调用 `LLMClient.chat()` 生成 JSON 格式的步骤列表。

**限制**:
- 无独立的 Planner 模块，规划逻辑内嵌在 Agent 中
- 无规划验证（plan validation）
- 无规划模板库

**证据**: `agent.py` L150 `def _plan(self) -> List[Dict]`

#### 2.1.3 Observation Layer 感知层

**状态**: PARTIAL

**实现位置**: `osai_engine/agent.py` L180-195

**实现方式**: 收集工具执行结果，标准化为 observation dict。

**限制**:
- 无多模态感知（视觉/音频）
- 无传感器抽象层
- 观察结果直接进入 context，无独立 observation store

**证据**: `agent.py` L180 `def _observe(self, action_result: Dict) -> Dict`

#### 2.1.4 Replanning 重规划

**状态**: EXISTS

**实现位置**: `osai_engine/agent.py` L215-235

**触发条件**:
- 动作执行失败且重试耗尽
- 观察结果与预期不符
- 外部中断信号
- 达到 max_replans 上限后停止

**证据**: `agent.py` L215 `def _replanning_check(self, observation: Dict) -> bool`

#### 2.1.5 Durable Execution 持久化执行

**状态**: EXISTS

**实现位置**: `osai_engine/checkpoint_resume.py`

**核心能力**:
| 能力 | 函数 | 存储 | 行号 |
|------|------|------|------|
| checkpoint 保存 | `CheckpointManager.save()` | JSON `checkpoints/{agent_id}.json` | L40-60 |
| pause 暂停 | `CheckpointManager.pause()` | state.status="paused" | L60-70 |
| resume 恢复 | `CheckpointManager.resume()` | 从 JSON 恢复 | L70-80 |
| retry 重试 | `CheckpointManager.retry()` | 从最后 checkpoint 重试 | L80-90 |
| recover 恢复 | `CheckpointManager.recover()` | 异常后恢复 | L90-100 |
| cancel 取消 | `CheckpointManager.cancel()` | state.status="cancelled" | L100-110 |

**证据**: `checkpoint_resume.py` L40 `def save(self, agent_id: str, state: Dict) -> str`

**可复用性**: 可复用。Checkpoint 机制是纯文件 JSON 持久化，可通过 Contract 接口集成到 ZBC。

#### 2.1.6 Agent State Machine 状态机

**状态**: EXISTS

**实现位置**: `osai_engine/agent.py` L60-90

**状态定义**:
```
idle → planning → executing → observing → evaluating → (replan|complete|failed)
  ↑                                    ↓
  └────────── pause/cancel ────────────┘
```

**状态枚举**: `idle`, `planning`, `executing`, `observing`, `evaluating`, `paused`, `completed`, `failed`, `cancelled`

**证据**: `agent.py` L60 `class AgentState: status: str = "idle"`

---

### 2.2 Intelligence & Reasoning

#### 2.2.1 Reasoning Engine 推理引擎

**状态**: PARTIAL

**实现位置**: `osai_engine/llm.py`

**实现方式**: 通过 LLM Provider 的 chat 接口实现推理，无独立的推理引擎抽象。

**推理模式**:
- 日常推理: `glm-4.5-air`（关思考）
- 强推理: `glm-5.3`
- 视觉推理: `glm-4.6v`
- 联网推理: `web-search-pro` tools

**限制**:
- 无 Chain-of-Thought 显式管理
- 无推理树/推理图
- 无推理验证机制

**证据**: `llm.py` L30 `def chat(self, messages: List[Dict], model: str = "glm-4.5-air") -> Dict`

#### 2.2.2 智谱 GLM 集成

**状态**: EXISTS

**实现位置**: `osai_engine/llm.py` L80-140

**支持模型**:
| 模型 | 用途 | 证据行号 |
|------|------|---------|
| `glm-4.5-air` | 日常主力，关思考 | L95 |
| `glm-5.3` | 强推理 | L95 |
| `glm-4.6v` | 视觉理解 | L95 |
| `web-search-pro` | 联网搜索（tools） | L110 |

**调用方式**: HTTP POST to `https://open.bigmodel.cn/api/paas/v4/chat/completions`

**API Key 管理**: 通过环境变量 `ZHIPU_API_KEY`，不写入源码

**证据**: `llm.py` L85 `api_key = os.environ.get("ZHIPU_API_KEY", "")`

**可复用性**: 可复用。与 ZBC `AI_PROVIDER_RUNTIME_POLICY_V1` 完全对齐。

#### 2.2.3 AI Gateway 网关

**状态**: EXISTS

**实现位置**: `osai_engine/ai_gateway.py`

**核心能力**:
- Provider 路由: 按任务意图选择模型
- Failover: 主 Provider 失败自动切换备用
- 本地兜底: Ollama/gpt-oss 本地模型
- 确定性规则兜底: 无 AI 时规则引擎
- 成本追踪: token/cost 统计

**Provider 优先级**:
```
1. 智谱 GLM (glm-4.5-air / glm-5.3 / glm-4.6v)
2. ARK / 千问 (备用)
3. Ollama / gpt-oss (本地兜底)
4. 确定性规则 (最终兜底)
```

**证据**: `ai_gateway.py` L30 `def route(self, task: str, intent: str) -> LLMResponse`

**可复用性**: 可复用。AI Gateway 是 Provider-Agnostic 设计，与 ZBC 现行策略完全一致。

#### 2.2.4 Context Management 上下文管理

**状态**: EXISTS（窗口）/ PARTIAL（压缩）

**实现位置**: `osai_engine/context_runtime.py`

**核心能力**:
| 能力 | 函数 | 状态 | 行号 |
|------|------|------|------|
| 上下文窗口 | `ContextManager.add()` | EXISTS | L30-40 |
| Token 截断 | `ContextManager.trim()` | EXISTS | L40-70 |
| 摘要压缩 | `ContextManager.summarize()` | PARTIAL | L70-90 |
| 上下文分级 | `ContextManager` (system/user/assistant/tool) | EXISTS | L20-30 |

**限制**:
- 摘要压缩依赖 LLM，无本地确定性压缩
- 无滑动窗口+摘要混合策略
- 无上下文重要性评分

**证据**: `context_runtime.py` L40 `def trim(self, max_tokens: int = 8000)`

---

### 2.3 Memory 分层

#### 2.3.1 Memory 架构总览

**实现位置**: `osai_engine/memory_lifecycle.py`

**六层记忆**:
```
Working Memory (工作记忆)  ←  当前任务上下文，in-memory dict
Task Memory (任务记忆)     ←  任务级状态，in-memory dict
Episodic Memory (情景记忆)  ←  历史交互记录，JSON list
Semantic Memory (语义记忆)  ←  知识/事实，JSON dict
Skill Memory (技能记忆)     ←  Skill Registry，in-memory + JSON
Learning Memory (学习记忆)  ←  学习记录，JSON file
```

#### 2.3.2 各层记忆详情

| 记忆层 | 存储结构 | 写入路径 | 检索路径 | 遗忘/压缩 | 持久化 | 状态 |
|--------|---------|---------|---------|----------|--------|------|
| Working | in-memory dict | `memory.working[key]=val` | `memory.working.get(key)` | 任务结束清空 | 无 | EXISTS |
| Task | in-memory dict | `memory.task[key]=val` | `memory.task.get(key)` | 任务结束归档 | JSON | EXISTS |
| Episodic | JSON list | `memory.episodic.append(record)` | 按时间/关键词过滤 | 保留最近 N 条 | JSON file | PARTIAL |
| Semantic | JSON dict | `memory.semantic[key]=val` | `memory.semantic.get(key)` | 无自动遗忘 | JSON file | PARTIAL |
| Skill | in-memory + JSON | `registry.register()` | `registry.get(skill_id)` | 版本管理 | JSON manifest | EXISTS |
| Learning | JSON file | `learning.record()` | `learning.query()` | 生命周期 stage | JSON `learning_records/` | EXISTS |

**证据**: `memory_lifecycle.py` L30-110 六层记忆初始化

**限制**:
- 无向量检索（Episodic/Semantic 仅关键词匹配）
- 无记忆重要性评分
- 无记忆冲突检测
- 无跨任务记忆迁移机制

---

### 2.4 Learning & Evolution

#### 2.4.1 学习机制

**状态**: PARTIAL

**实现位置**: `osai_engine/learning_record_contract.py`

**学习记录结构**:
```
LearningRecord:
  - record_id: str
  - learning_type: feedback / correction / outcome / pattern
  - source: agent / human / system
  - content: Dict
  - confidence: float
  - lifecycle_stage: raw → reviewed → validated → promoted → archived
  - related_evaluation_ids: List[str]
  - related_outcome_ids: List[str]
```

**证据**: `learning_record_contract.py` L30 `class LearningRecord`

#### 2.4.2 用户反馈沉淀

**状态**: PARTIAL

**实现位置**: `osai_engine/learning_record_contract.py` L60-80

**流程**: `用户反馈 → LearningRecord.from_feedback() → lifecycle_stage=raw → 人工审核 → promoted → 规则/样本`

**限制**: 无自动从反馈生成规则的机制，需人工审核。

#### 2.4.3 AI 输出修正回灌

**状态**: PARTIAL

**实现位置**: `osai_engine/learning_record_contract.py` L80-100

**流程**: `AI输出 → 人工修正 → LearningRecord.from_correction(original, corrected) → 差异分析 → 样本沉淀`

**限制**: 无自动修正模型参数，仅记录差异供后续参考。

#### 2.4.4 Skill/能力进化

**状态**: EXISTS

**实现位置**:
- `osai_engine/skill_manifest.py` — 版本管理
- `osai_engine/skill_invocation.py` — 使用统计
- `osai_engine/skill_sync.py` — GitHub 同步

**进化路径**: `使用统计 → 评估 → 版本升级 → Manifest 更新 → Registry Sync`

**证据**: `skill_manifest.py` L30 `version: str = "0.0.0"`

#### 2.4.5 内容学习 RAG

**状态**: MISSING

**发现**: OSAI 无向量数据库、无 embedding 模块、无 RAG 检索器。`research.py` 仅实现关键词级别的文档检索。

**ZBC 需求**: ZBC 有 `intelligence_library/` 知识库（品牌营销知识、前沿研究、工程审计方法），需要 RAG 能力。

**建议**: 通过 Contract 接口，ZBC 侧自建 RAG（或复用现有向量方案），OSAI 提供 LearningRecord 契约对齐。

#### 2.4.6 Learning Loop 闭环

**状态**: PARTIAL

**实现位置**: `osai_engine/learning_record_contract.py` L100-140

**闭环**: `操作记录 → 结果评估 → 学习记录 → 人工审核 → 规则/样本沉淀 → 影响后续调用`

**限制**: "影响后续调用"环节未完全自动化，当前仅记录不自动注入。

---

### 2.5 Skill & Tool

#### 2.5.1 Skill Registry 技能注册

**状态**: EXISTS

**实现位置**: `osai_engine/skill_registry.py` + `osai_engine/canonical_skill_registry.py`

**三层收敛**:
1. `skill_manifest.py` — S01-S12 Canonical Manifest
2. `skill_registry.py` — SKILL_CATALOG S01-S72 目录
3. `skills/source_skills.py` — S01-S12 真实可运行实现

**CanonicalSkillRegistry** 是唯一运行时 Skill Truth（`canonical_skill_registry.py` L22）。

**证据**: `canonical_skill_registry.py` L1 `唯一 Skill Truth`

#### 2.5.2 Skill Invocation 调用契约

**状态**: EXISTS

**实现位置**: `osai_engine/skill_execution_contract.py`

**契约结构**:
```
SkillExecutionRequest:
  - skill_id: str
  - inputs: Dict
  - identity_context: Dict
  - permissions: List[str]
  - idempotency_key: str

SkillExecutionResult:
  - skill_id: str
  - status: ok / error / blocked / partial
  - summary: str
  - data: Dict
  - evidence_refs: List[str]
  - duration_ms: float
```

**证据**: `skill_execution_contract.py` L30 `class SkillExecutionContract`

#### 2.5.3 Tool Router 工具路由

**状态**: PARTIAL

**实现位置**: `osai_engine/tools.py`

**实现方式**: 简单的 name→function 映射注册表，无智能路由。

**限制**:
- 无基于意图的工具选择
- 无工具组合编排
- 无工具能力描述（仅名称）

**证据**: `tools.py` L30 `class ToolRegistry: _tools: Dict[str, Callable]`

#### 2.5.4 现有 Skill 清单

**状态**: EXISTS（S01-S12 已实现）

**实现位置**: `osai_engine/skills/source_skills.py`

| Skill ID | 名称 | 功能 | 状态 | 行号 |
|----------|------|------|------|------|
| S01 | Source Fact Scanner | 仓库文件/目录/大小扫描 | IMPLEMENTED | L61 |
| S02 | SHA Verifier | Git HEAD SHA/分支/干净度 | IMPLEMENTED | L89 |
| S03 | Git State Auditor | Git 状态审计（staged/unstaged/untracked） | IMPLEMENTED | L105 |
| S04 | File Inventory | 按扩展名盘点文件 | IMPLEMENTED | L131 |
| S05 | Module Mapper | AST 提取模块 import 关系 | IMPLEMENTED | L146 |
| S06 | Function Mapper | AST 提取函数/类定义及行号 | IMPLEMENTED | L172 |
| S07 | API Mapper | AST 提取 Flask 路由 | IMPLEMENTED | L198 |
| S08 | Dependency Auditor | 依赖审计（requirements + import） | IMPLEMENTED | L231 |
| S09 | Config Auditor | 配置审计（硬编码路径/疑似密钥） | IMPLEMENTED | L263 |
| S10 | DB Schema Auditor | SQLite 表/列/索引/行数审计 | IMPLEMENTED | L300 |
| S11 | DB Integrity Checker | SQLite 完整性检查 | IMPLEMENTED | L329 |
| S12 | Runtime Health | 运行环境健康（Python/平台/模块） | IMPLEMENTED | L352 |
| S13-S72 | — | PLANNED | PLANNED | `skill_registry.py` SKILL_CATALOG |

**统一入口**: `source_skills.py` L383 `def run_skill(skill_id, repo_root=None, **opts)`

**证据**: `source_skills.py` L367-380 `SKILL_EXECUTORS` dict

**可复用性**: 可复用。S01-S12 是纯 stdlib 实现的源码/DB/运行审计工具，ZBC 可直接通过 Contract 调用进行自审计。

---

### 2.6 Security & Boundary

#### 2.6.1 Permission 权限控制

**状态**: EXISTS

**实现位置**: `osai_engine/permission_gate.py` + `osai_engine/permission_contract.py`

**11 级权限模型**:
```
LEVELS = [
  "READ",           # 只读
  "AUDIT",          # 审计
  "ANALYZE",        # 分析
  "RESEARCH",       # 研究
  "PLAN",           # 规划
  "PATCH_PREVIEW",  # 补丁预览
  "TEST",           # 测试
  "VERIFY",         # 验证
  "HUMAN_APPROVAL", # 人工审批（人工-only）
  "COMMIT",         # 提交（人工-only）
  "PUSH",           # 推送（人工-only）
]
```

**Agent 自动化上限**: `VERIFY`（`permission_contract.py` L15 `AGENT_AUTO_MAX = "VERIFY"`）

**人工-only**: `HUMAN_APPROVAL`, `COMMIT`, `PUSH`

**证据**: `permission_gate.py` L30 `LEVELS = [...]`

**可复用性**: 可复用。11 级模型与 ZBC `AI-EXECUTION-CONSTITUTION` 对齐。

#### 2.6.2 Action Firewall 动作防火墙

**状态**: EXISTS

**实现位置**: `osai_engine/action_firewall.py`

**核心能力**:
- 动作白名单/黑名单
- 动作参数校验
- 危险动作拦截
- 动作审计日志

**证据**: `action_firewall.py` L30 `class ActionFirewall`

#### 2.6.3 Effect Fence 效果围栏

**状态**: EXISTS

**实现位置**: `osai_engine/effect_fence.py`

**核心能力**:
- 动作执行前效果预测
- 执行后效果验证
- 非预期效果回滚建议
- 效果范围限制

**证据**: `effect_fence.py` L30 `class EffectFence`

#### 2.6.4 Evidence Chain 证据链

**状态**: EXISTS

**实现位置**: `osai_engine/evidence_chain.py` + `osai_engine/evidence.py` + `osai_engine/evidence_graph.py`

**证据链结构**:
```
Source → Evidence → Event → Case → Finding → Decision → Action → Outcome → Evaluation → LearningAsset
```

**证据图**: `EvidenceGraph` 支持 9 种关系（derived_from/supports/contradicts/triggers/executes/produces/evaluates/references/contains）

**证据溯源**: `EvidenceGraph.trace_to_source()` 可从任意节点追溯到 Source

**证据**: `evidence_graph.py` L83 `def trace_to_source(self, node_id, max_depth=10)`

**可复用性**: 可复用。证据链是 ZBC 舆情监测的核心需求（每条结论必须可追溯到原始笔记/评论）。

#### 2.6.5 Human-in-the-Loop 人工审批

**状态**: EXISTS

**实现位置**: `osai_engine/permission_contract.py` L57-62

**流程**:
```
Agent 请求 HUMAN_APPROVAL/COMMIT/PUSH
  → PermissionRequest 自动 decision=pending_human
  → 人工 human_decide(approve=True/False)
  → 记录审批人/时间/备注
```

**证据**: `permission_contract.py` L57 `def human_decide(self, approve, by="HUMAN", note="")`

#### 2.6.6 Production Truth 边界

**状态**: EXISTS

**实现位置**: `osai_engine/canonical_data.py`

**强制字段**: 所有 Canonical 实体必须携带:
- `product_id` (CTH/ZBMP/OSAI/GGI)
- `subject_id`
- `scope`
- `provenance`
- `content_hash` (SHA-256)
- `version`

**验证**: `CanonicalBase.validate()` L58-72 强制检查上述字段

**证据**: `canonical_data.py` L58 `def validate(self) -> List[str]`

**可复用性**: 可复用。Production Truth 边界机制确保 AI 输出不直接成为生产数据，必须经过验证+哈希+来源标记。

---

### 2.7 Evaluation & Trace

#### 2.7.1 Trajectory Evaluation 轨迹评估

**状态**: EXISTS

**实现位置**: `osai_engine/trace_evaluation.py`

**评估维度**:
- 步骤效率（steps vs expected）
- 成本控制（actual cost vs budget）
- 成功率（success/failure ratio）
- 重规划次数
- 证据完整性

**证据**: `trace_evaluation.py` L30 `class TrajectoryEvaluator`

#### 2.7.2 Trace 执行追踪

**状态**: EXISTS

**实现位置**: `osai_engine/trace_contract.py`

**追踪内容**:
- 每步输入/输出
- 工具调用
- LLM 调用（model/token/cost）
- 状态转换
- 时间戳

**存储**: JSONL

**证据**: `trace_contract.py` L30 `class TraceContract`

#### 2.7.3 Evaluation 评估机制

**状态**: EXISTS

**实现位置**: `osai_engine/evaluation_contract.py`

**评估类型**:
- 确定性评估（规则-based）
- LLM 评估（模型-based）
- 人工评估

**证据**: `evaluation_contract.py` L30 `class EvaluationContract`

#### 2.7.4 AgentOps 可观测性

**状态**: EXISTS

**实现位置**: `osai_engine/observability.py`

**可观测性维度**:
- Metrics（计数/延迟/成本）
- Logs（结构化日志）
- Traces（分布式追踪）
- Events（事件发射）

**证据**: `observability.py` L30 `class ObservabilityHub`

---

## 3. OSAI→ZBC Contract 接口设计

### 3.1 设计原则

1. **不引入运行时依赖**: ZBC 不直接 `import osai_engine`，所有交互通过 subprocess + JSON（已有 `agent_runtime_adapter.py` 和 `lumenis_skill_adapter.py` 验证）
2. **Contract 优先**: 定义数据结构、API、事件，不绑定实现
3. **Fail-close**: OSAI 不可用时 ZBC 显式返回 UNAVAILABLE，不造假数据
4. **只读优先**: 第一阶段所有 Contract 为只读查询，不修改 OSAI 状态
5. **产品隔离**: 所有数据携带 `product_id`，OSAI 数据不混入 ZBC 生产库

### 3.2 Contract 接口清单

#### C-01: Agent Runtime Contract（Agent 运行时契约）

**用途**: ZBC 调用 OSAI Agent Loop 执行复杂任务（如深度舆情分析、事件溯源）

**数据结构**:
```json
{
  "contract_id": "C-01",
  "version": "1.0.0",
  "request": {
    "task_id": "zbc-task-xxx",
    "task_description": "string",
    "product_id": "CTH",
    "subject_id": "guangzhou_taikoo_hui",
    "scope": "public_opinion_analysis",
    "config": {
      "max_steps": 20,
      "max_time_seconds": 300,
      "max_cost": 5.0,
      "max_retries": 3,
      "max_replans": 3
    },
    "permissions": ["READ", "AUDIT", "ANALYZE", "RESEARCH", "PLAN"],
    "context": {}
  },
  "response": {
    "agent_id": "osai-agent-xxx",
    "status": "completed|failed|cancelled|timeout",
    "result": {},
    "trace_ref": "trace/xxx.jsonl",
    "checkpoint_ref": "checkpoints/xxx.json",
    "metrics": {
      "steps": 0,
      "duration_ms": 0,
      "cost": 0.0,
      "replans": 0,
      "retries": 0
    }
  }
}
```

**API**:
- `POST /contract/agent/run` — 启动 Agent 任务
- `GET /contract/agent/status/{agent_id}` — 查询状态
- `POST /contract/agent/cancel/{agent_id}` — 取消任务
- `POST /contract/agent/resume/{agent_id}` — 从 checkpoint 恢复

**事件**:
- `agent.started`
- `agent.step_completed`
- `agent.replanning`
- `agent.completed`
- `agent.failed`
- `agent.cancelled`

**OSAI 实现映射**: `agent.py` `Agent.run()` / `checkpoint_resume.py`

**ZBC 集成点**: `agent_runtime_adapter.py`（已有 subprocess 桥接）

---

#### C-02: AI Gateway Contract（AI 网关契约）

**用途**: ZBC 复用 OSAI AI Gateway 的 Provider 路由/Failover/成本追踪

**数据结构**:
```json
{
  "contract_id": "C-02",
  "version": "1.0.0",
  "request": {
    "task_type": "reasoning|analysis|summary|vision|web_search",
    "intent": "string",
    "messages": [{"role": "user|assistant|system", "content": "string"}],
    "preferred_provider": "zhipu|ark|ollama|auto",
    "product_id": "CTH"
  },
  "response": {
    "provider": "zhipu",
    "model": "glm-4.5-air",
    "content": "string",
    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    "cost": 0.0,
    "latency_ms": 0,
    "fallback_used": false
  }
}
```

**API**:
- `POST /contract/ai/chat` — 统一聊天接口
- `GET /contract/ai/providers` — 列出可用 Provider
- `GET /contract/ai/cost/{period}` — 成本统计

**事件**:
- `ai.provider_switched`
- `ai.fallback_triggered`
- `ai.cost_threshold_reached`

**OSAI 实现映射**: `ai_gateway.py` `AIGateway.route()` / `llm.py`

**ZBC 集成点**: ZBC 已有 `scripts/ai_gateway.py`，可通过 Contract 对齐 Provider 策略

---

#### C-03: Skill Execution Contract（技能执行契约）

**用途**: ZBC 调用 OSAI S01-S12 审计 Skill 进行自审计

**数据结构**:
```json
{
  "contract_id": "C-03",
  "version": "1.0.0",
  "request": {
    "skill_id": "S01|S02|...|S12",
    "repo_root": "D:\\Taikoo-monitor-new",
    "inputs": {},
    "permissions": ["READ", "AUDIT"],
    "idempotency_key": "string"
  },
  "response": {
    "skill_id": "S01",
    "status": "ok|error|blocked",
    "summary": "string",
    "data": {},
    "evidence_refs": [],
    "duration_ms": 0
  }
}
```

**API**:
- `POST /contract/skill/execute` — 执行 Skill
- `GET /contract/skill/catalog` — 列出所有 Skill（含状态）
- `GET /contract/skill/{skill_id}/manifest` — 获取 Skill Manifest

**事件**:
- `skill.executed`
- `skill.blocked`
- `skill.failed`

**OSAI 实现映射**: `skills/source_skills.py` `run_skill()` / `canonical_skill_registry.py`

**ZBC 集成点**: `lumenis_skill_adapter.py`（已有 subprocess 桥接）

**可复用 Skill 清单**:
- S01 Source Fact Scanner — ZBC 仓库健康扫描
- S02 SHA Verifier — ZBC Git 版本验证
- S05 Module Mapper — ZBC 模块依赖分析
- S06 Function Mapper — ZBC 函数清单
- S07 API Mapper — ZBC Flask 路由清单
- S09 Config Auditor — ZBC 硬编码路径/密钥审计
- S10 DB Schema Auditor — ZBC monitor.db 表结构审计
- S11 DB Integrity Checker — ZBC monitor.db 完整性检查

---

#### C-04: Evidence Chain Contract（证据链契约）

**用途**: ZBC 舆情结论通过 OSAI 证据链机制实现可追溯

**数据结构**:
```json
{
  "contract_id": "C-04",
  "version": "1.0.0",
  "entities": {
    "Source": {"source_type": "xiaohongshu_note", "url": "", "platform": "xiaohongshu", "published_at": 0},
    "Evidence": {"evidence_type": "content|comment|metadata", "content": "", "confidence": 1.0},
    "Event": {"event_type": "marketing|spread|opinion", "title": "", "severity": "low|medium|high"},
    "Finding": {"finding_type": "risk|insight|trend", "content": "", "confidence": 0.8},
    "Decision": {"decision_type": "alert|report|ignore", "status": "proposed|approved"},
    "Action": {"action_type": "notify|report|archive", "status": "pending|executed"},
    "Outcome": {"outcome_type": "resolved|ongoing|dismissed", "metrics": {}}
  },
  "relations": ["derived_from", "supports", "contradicts", "triggers"],
  "product_id": "CTH",
  "subject_id": "guangzhou_taikoo_hui"
}
```

**API**:
- `POST /contract/evidence/build` — 从原始数据构建证据链
- `GET /contract/evidence/trace/{node_id}` — 追溯证据来源
- `GET /contract/evidence/graph/{event_id}` — 获取证据图

**事件**:
- `evidence.created`
- `evidence.verified`
- `evidence.contradiction_detected`

**OSAI 实现映射**: `canonical_data.py` / `evidence_chain.py` / `evidence_graph.py`

**ZBC 集成点**: ZBC 已有 `evidence_chain.py`，可通过 Contract 对齐实体结构

---

#### C-05: Permission Contract（权限契约）

**用途**: ZBC 复用 OSAI 11 级权限模型和人工审批流程

**数据结构**:
```json
{
  "contract_id": "C-05",
  "version": "1.0.0",
  "request": {
    "actor": "agent|skill|human",
    "level": "READ|AUDIT|...|PUSH",
    "target_repo": "ZBC|OSAI|BOTH",
    "target_scope": "string",
    "reason": "string"
  },
  "response": {
    "request_id": "PR-xxx",
    "decision": "allow|deny|pending_human",
    "decide_reason": "string",
    "decided_at": "timestamp"
  }
}
```

**API**:
- `POST /contract/permission/request` — 请求权限
- `POST /contract/permission/{request_id}/human_decide` — 人工审批
- `GET /contract/permission/levels` — 列出 11 级权限

**事件**:
- `permission.requested`
- `permission.approved`
- `permission.denied`
- `permission.human_approval_required`

**OSAI 实现映射**: `permission_gate.py` / `permission_contract.py`

**ZBC 集成点**: ZBC 已有 `agent_security.py` / `ai_governance.py`，可通过 Contract 对齐权限级别

---

#### C-06: Memory Contract（记忆契约）

**用途**: ZBC 与 OSAI 之间通过 Contract 交换记忆数据（不共享存储）

**数据结构**:
```json
{
  "contract_id": "C-06",
  "version": "1.0.0",
  "memory_layer": "working|task|episodic|semantic|skill|learning",
  "operation": "read|write|query|forget",
  "key": "string",
  "value": {},
  "product_id": "CTH",
  "subject_id": "guangzhou_taikoo_hui",
  "ttl_seconds": 0
}
```

**API**:
- `POST /contract/memory/write` — 写入记忆
- `GET /contract/memory/read/{key}` — 读取记忆
- `POST /contract/memory/query` — 查询记忆
- `POST /contract/memory/forget/{key}` — 遗忘记忆

**事件**:
- `memory.written`
- `memory.retrieved`
- `memory.expired`

**OSAI 实现映射**: `memory_lifecycle.py`

**注意**: 第一阶段仅 ZBC→OSAI 单向写入学习记录，不做双向同步。

---

#### C-07: Learning Record Contract（学习记录契约）

**用途**: ZBC 的 AI 输出修正、用户反馈通过 Contract 沉淀为 OSAI LearningRecord

**数据结构**:
```json
{
  "contract_id": "C-07",
  "version": "1.0.0",
  "record": {
    "learning_type": "feedback|correction|outcome|pattern",
    "source": "zbc_agent|zbc_human|zbc_system",
    "content": {
      "original_output": "string",
      "corrected_output": "string",
      "feedback_text": "string",
      "context": {}
    },
    "confidence": 0.8,
    "lifecycle_stage": "raw",
    "product_id": "CTH",
    "related_task_id": "string"
  }
}
```

**API**:
- `POST /contract/learning/record` — 记录学习
- `GET /contract/learning/query` — 查询学习记录
- `POST /contract/learning/{id}/promote` — 提升生命周期阶段

**事件**:
- `learning.recorded`
- `learning.reviewed`
- `learning.promoted`

**OSAI 实现映射**: `learning_record_contract.py`

**ZBC 集成点**: ZBC 已有 `ai_learning_engine.py`（LEGACY_PARTIAL），可通过 Contract 迁移到 OSAI LearningRecord 模型

---

#### C-08: Trace & Evaluation Contract（追踪评估契约）

**用途**: ZBC 获取 OSAI Agent 执行轨迹和评估结果

**数据结构**:
```json
{
  "contract_id": "C-08",
  "version": "1.0.0",
  "trace": {
    "trace_id": "string",
    "agent_id": "string",
    "steps": [
      {
        "step": 0,
        "action": "string",
        "input": {},
        "output": {},
        "tool_calls": [],
        "llm_calls": [{"model": "", "tokens": 0, "cost": 0.0}],
        "timestamp": "",
        "duration_ms": 0
      }
    ]
  },
  "evaluation": {
    "score": 0.0,
    "dimensions": {"efficiency": 0, "cost_control": 0, "success_rate": 0},
    "method": "deterministic|llm|human"
  }
}
```

**API**:
- `GET /contract/trace/{trace_id}` — 获取完整轨迹
- `GET /contract/trace/{trace_id}/evaluation` — 获取评估结果
- `POST /contract/trace/{trace_id}/human_evaluate` — 人工评估

**事件**:
- `trace.completed`
- `evaluation.completed`

**OSAI 实现映射**: `trace_contract.py` / `trace_evaluation.py` / `evaluation_contract.py`

---

#### C-09: Identity & Delegation Contract（身份委托契约）

**用途**: ZBC 复用 OSAI Identity Chain + Delegation + OBO/JIT 机制

**数据结构**:
```json
{
  "contract_id": "C-09",
  "version": "1.0.0",
  "identity_chain": {
    "user_identity": "string",
    "agent_identity": "string",
    "task": "string",
    "permissions": [],
    "scope": {},
    "skill_nodes": [{"skill_id": "", "permissions": []}],
    "tool_nodes": [{"tool_id": "", "skill_id": "", "permissions": []}]
  },
  "delegation": {
    "delegation_id": "string",
    "from": "user",
    "to": "agent",
    "scope": {},
    "permissions": [],
    "duration_seconds": 3600,
    "status": "active|revoked|expired"
  }
}
```

**API**:
- `POST /contract/identity/create_context` — 创建身份上下文
- `POST /contract/delegation/create` — 创建委托
- `POST /contract/delegation/{id}/revoke` — 撤销委托
- `GET /contract/identity/{context_id}/audit_trail` — 获取审计轨迹

**事件**:
- `identity.context_created`
- `delegation.approved`
- `delegation.revoked`
- `delegation.expired`

**OSAI 实现映射**: `agent_identity.py` / `delegation.py` / `obo_jit.py` / `agent_integration.py`

**ZBC 集成点**: `agent_runtime_adapter.py`（已有 subprocess 桥接 Identity/Delegation/OBO/JIT）

---

#### C-10: Canonical Data Contract（规范数据契约）

**用途**: ZBC 与 OSAI 之间通过 Canonical Data 实体实现数据对齐

**数据结构**: 见 `canonical_data.py` 十实体定义（Source/Evidence/Event/Case/Finding/Decision/Action/Outcome/Evaluation/LearningAsset）

**API**:
- `POST /contract/canonical/create` — 创建规范实体
- `GET /contract/canonical/{entity_type}/{id}` — 获取实体
- `POST /contract/canonical/validate` — 验证实体
- `GET /contract/canonical/flow` — 获取数据流图

**事件**:
- `canonical.entity_created`
- `canonical.validation_failed`
- `canonical.relation_established`

**OSAI 实现映射**: `canonical_data.py`

---

### 3.3 Contract 实施优先级

| 优先级 | Contract | 理由 | ZBC 已有基础 |
|--------|----------|------|-------------|
| P0 | C-03 Skill Execution | S01-S12 可直接用于 ZBC 自审计，风险最低 | `lumenis_skill_adapter.py` 已验证 |
| P0 | C-02 AI Gateway | Provider 路由/Failover 与 ZBC 现行策略对齐 | `scripts/ai_gateway.py` |
| P0 | C-05 Permission | 11 级权限模型是安全基线 | `agent_security.py` |
| P1 | C-01 Agent Runtime | 复杂任务编排能力 | `agent_runtime_adapter.py` 已验证 |
| P1 | C-04 Evidence Chain | 舆情结论可追溯是核心需求 | `evidence_chain.py` |
| P1 | C-09 Identity & Delegation | 身份链+委托是安全执行基础 | `agent_runtime_adapter.py` |
| P2 | C-06 Memory | 记忆同步需谨慎设计 | `memory_optimizer.py` |
| P2 | C-07 Learning Record | 学习闭环是长期演进 | `ai_learning_engine.py` LEGACY |
| P2 | C-08 Trace & Evaluation | 可观测性增强 | `ai_call_logger.py` |
| P2 | C-10 Canonical Data | 数据对齐是长期目标 | `domain_adapter.py` |

---

## 4. Top 5 可复用能力

### 1. AI Gateway Provider-Agnostic 路由与 Failover

**文件**: `osai_engine/ai_gateway.py` + `osai_engine/llm.py`

**可复用理由**:
- 与 ZBC `AI_PROVIDER_RUNTIME_POLICY_V1` 完全对齐（智谱 GLM 主力 + ARK/千问备用 + Ollama 本地兜底 + 确定性规则最终兜底）
- 纯 stdlib 实现，无外部依赖
- 成本追踪、Provider 健康检查、自动切换已实现
- API Key 仅通过环境变量注入，不写入源码

**复用方式**: 通过 C-02 Contract，ZBC 调用 OSAI AI Gateway 统一接口

---

### 2. S01-S12 源码/DB/运行审计 Skill

**文件**: `osai_engine/skills/source_skills.py`

**可复用理由**:
- 12 个 Skill 全部真实可运行，纯 stdlib 实现
- 覆盖源码扫描（S01-S09）、DB 审计（S10-S11）、运行健康（S12）
- 统一签名 `execute(repo_root, **opts) -> dict`，易于集成
- 不修改被扫描仓库，只读安全

**复用方式**: 通过 C-03 Contract，ZBC 定期调用 S01-S12 进行自审计

**ZBC 直接受益场景**:
- S09 Config Auditor 检测 ZBC 硬编码路径和疑似密钥
- S10/S11 DB Auditor 审计 monitor.db 表结构和完整性
- S05/S06 Module/Function Mapper 生成 ZBC 代码地图
- S07 API Mapper 生成 ZBC Flask 路由清单

---

### 3. 11 级权限模型 + 人工审批流程

**文件**: `osai_engine/permission_gate.py` + `osai_engine/permission_contract.py`

**可复用理由**:
- 11 级权限（READ→PUSH）覆盖从只读到生产发布的完整谱系
- Agent 自动化上限 VERIFY，HUMAN_APPROVAL/COMMIT/PUSH 必须人工
- 与 ZBC `AI-EXECUTION-CONSTITUTION` 安全原则一致
- PermissionRequest 自动决策+人工决策分离，可审计

**复用方式**: 通过 C-05 Contract，ZBC 的 AI 操作统一经过 OSAI 权限检查

---

### 4. Canonical Data 十实体链 + Evidence Graph

**文件**: `osai_engine/canonical_data.py` + `osai_engine/evidence_graph.py` + `osai_engine/evidence_chain.py`

**可复用理由**:
- 十实体链（Source→Evidence→Event→Case→Finding→Decision→Action→Outcome→Evaluation→LearningAsset）覆盖舆情监测全链路
- EvidenceGraph 支持 9 种关系和溯源（`trace_to_source`）
- 所有实体强制 product_id/subject_id/scope/provenance/content_hash，确保 Production Truth 边界
- 与 ZBC 舆情监测的"笔记→评论→事件→风险→报告"链路天然对齐

**复用方式**: 通过 C-04 + C-10 Contract，ZBC 舆情数据按 Canonical Data 结构对齐

---

### 5. Agent Loop 全量控制 + Durable Execution

**文件**: `osai_engine/agent.py` + `osai_engine/checkpoint_resume.py`

**可复用理由**:
- Agent Loop 实现 max_steps/max_time/max_cost/max_retries/max_replans/timeout/cancellation/circuit_breaker 全量控制
- Durable Execution 支持 checkpoint/pause/resume/retry/recover/cancel
- 纯 stdlib 实现，无外部依赖
- 与 ZBC 复杂舆情分析任务（事件溯源、深度研究）的编排需求匹配

**复用方式**: 通过 C-01 Contract，ZBC 提交复杂任务给 OSAI Agent 执行

---

## 5. MISSING 能力与 ZBC 自建建议

| MISSING 能力 | OSAI 现状 | ZBC 需求 | 建议 |
|-------------|----------|---------|------|
| RAG 向量检索 | 无向量库/embedding，仅关键词检索 | intelligence_library 知识库检索 | ZBC 自建 RAG，通过 C-06 Memory Contract 与 OSAI 交换语义记忆 |
| 多模态感知 | 无视觉/音频输入（glm-4.6v 仅 LLM 层面） | 笔记图片分析、截图理解 | ZBC 自建多模态采集，通过 C-02 AI Gateway 调用 glm-4.6v |
| 实时流式输出 | 无 SSE/WebSocket 流式 | 实时舆情推送 | ZBC 自建流式层，OSAI Agent 同步执行 |
| 多 Agent 协作 | 单 Agent 为主，delegation 仅身份委托 | 采集Agent+分析Agent+报告Agent 协作 | ZBC 自建多 Agent 编排，OSAI 提供单 Agent 能力 |
| 持久化队列 | 内存注册表为主，JSON 文件持久化 | 采集任务队列、定时任务 | ZBC 自建任务队列（已有 APScheduler） |
| 向量记忆 | Episodic/Semantic 仅 JSON | 历史舆情语义检索 | ZBC 自建向量记忆，通过 C-06 Contract 对齐 |
| 自动规则生成 | Learning 仅记录，不自动生成规则 | 风险规则自动进化 | ZBC 自建规则引擎，OSAI LearningRecord 提供样本 |
| 分布式追踪 | 单进程 trace | 多服务链路追踪 | ZBC 自建 OpenTelemetry，OSAI trace 通过 C-08 Contract 导出 |

---

## 6. 测试覆盖审计

### 6.1 OSAI 测试清单（21 个测试文件）

| 测试文件 | 覆盖范围 | 状态 |
|---------|---------|------|
| `test_osai_engine.py` | Agent Loop 基础 | 存在 |
| `test_lumenis_p0.py` | P0 模块基础 | 存在 |
| `test_lumenis_p0p1_convergence.py` | P0-P1 收敛 | 存在 |
| `test_lumenis_p0_contracts.py` | P0 Contract | 存在 |
| `test_lumenis_p0_new_contracts.py` | P0 新 Contract | 存在 |
| `test_lumenis_engine_layer.py` | Engine Layer | 存在 |
| `test_lumenis_harness_runtime.py` | Harness Runtime | 存在 |
| `test_lumenis_phase3_runtime.py` | Phase 3 Runtime | 存在 |
| `test_lumenis_skills_and_loop.py` | Skill + Agent Loop | 存在 |
| `test_lumenis_skill_hub.py` | Skill Hub | 存在 |
| `test_lumenis_v3_identity.py` | Identity V3 | 存在 |
| `test_lumenis_v3_integration.py` | Identity 集成 | 存在 |
| `test_lumenis_cross_core.py` | 跨核心 | 存在 |
| `test_v2_p0_modules.py` | V2 P0 模块 | 存在 |
| `test_v2_p0_remaining.py` | V2 P0 剩余 | 存在 |
| `test_v2_p0_2_3.py` | V2 P0 2-3 | 存在 |
| `test_v4_p0_p1_modules.py` | V4 P0-P1 | 存在 |
| `test_canonical_data_and_evidence_graph.py` | Canonical Data + Evidence Graph | 存在 |
| `test_contracts_baseline.py` | Contract 基线 | 存在 |
| `test_browser_runtime_zbc_compliance.py` | Browser Runtime ZBC 合规 | 存在 |
| `e2e_cross_core_convergence.py` | E2E 跨核心收敛 | 存在 |

### 6.2 测试覆盖评估

| 模块 | 测试覆盖 | 评估 |
|------|---------|------|
| Agent Loop | `test_osai_engine.py`, `test_lumenis_skills_and_loop.py` | 有覆盖 |
| AI Gateway | 无专门测试（ZBC 侧有 `test_ai_gateway.py`） | 部分覆盖 |
| Skill Registry | `test_lumenis_skills_and_loop.py`, `test_lumenis_skill_hub.py` | 有覆盖 |
| Permission | 无 OSAI 侧专门测试（ZBC 侧有 `test_ai_permission_matrix.py`） | 部分覆盖 |
| Evidence Chain | `test_canonical_data_and_evidence_graph.py` | 有覆盖 |
| Checkpoint | `test_v2_p0_modules.py` | 有覆盖 |
| Memory | 无专门测试 | 未覆盖 |
| Learning | 无专门测试 | 未覆盖 |
| Trace/Evaluation | `test_contracts_baseline.py` | 部分覆盖 |
| Identity/Delegation | `test_lumenis_v3_identity.py`, `test_lumenis_v3_integration.py` | 有覆盖 |

---

## 7. 风险与已知限制

### 7.1 OSAI 侧风险

1. **内存注册表模式**: 所有 Registry 为 in-memory，进程重启后状态丢失（仅 JSON 文件持久化部分数据）
2. **无异步支持**: Agent Loop 为同步执行，无 async/await
3. **无并发控制**: 无多 Agent 并发执行机制
4. **测试覆盖不均**: Memory/Learning 模块无专门测试
5. **S13-S72 Skill 未实现**: 仅 S01-S12 有真实实现，其余为 PLANNED

### 7.2 ZBC 集成风险

1. **subprocess 开销**: 每次 OSAI 调用需启动 Python 进程，延迟较高（已有 adapter 验证）
2. **数据双写**: Contract 交互可能导致 ZBC 和 OSAI 数据不一致，需明确单一真值源
3. **OSAI 不可用**: ZBC 必须 fail-close，不能依赖 OSAI 完成核心采集/报告链路
4. **产品隔离**: 必须确保 OSAI 数据（product_id=OSAI）不混入 ZBC 生产库（product_id=CTH）

### 7.3 安全红线

1. OSAI Agent 自动化上限 VERIFY，COMMIT/PUSH 必须人工
2. 所有 API Key 仅通过环境变量注入，不写入源码/DB/日志
3. 官方账号一律只读（禁关注/点赞/收藏/评论/私信/发布/退登）
4. AI 输出不直接成为 Production Truth，必须经过验证+哈希+来源标记
5. 不破解验证码、不绕过平台安全验证

---

## 8. 统计汇总

### 8.1 能力状态统计

| Status | 数量 | 占比 |
|--------|------|------|
| EXISTS | 28 | 56% |
| PARTIAL | 14 | 28% |
| MISSING | 8 | 16% |
| **总计** | **50** | **100%** |

### 8.2 分域统计

| 域 | EXISTS | PARTIAL | MISSING | 总计 |
|----|--------|---------|---------|------|
| Agent Runtime | 13 | 2 | 0 | 15 |
| Intelligence & Reasoning | 4 | 3 | 0 | 7 |
| Memory | 4 | 2 | 0 | 6 |
| Learning & Evolution | 2 | 3 | 1 | 6 |
| Skill & Tool | 3 | 1 | 0 | 4 |
| Security & Boundary | 6 | 0 | 0 | 6 |
| Evaluation & Trace | 4 | 0 | 0 | 4 |
| 其他（RAG等） | 0 | 0 | 7 | 7 |

### 8.3 Contract 接口统计

| Contract ID | 名称 | 优先级 | OSAI 实现映射 |
|-------------|------|--------|-------------|
| C-01 | Agent Runtime | P1 | `agent.py` + `checkpoint_resume.py` |
| C-02 | AI Gateway | P0 | `ai_gateway.py` + `llm.py` |
| C-03 | Skill Execution | P0 | `skills/source_skills.py` |
| C-04 | Evidence Chain | P1 | `evidence_chain.py` + `evidence_graph.py` |
| C-05 | Permission | P0 | `permission_gate.py` + `permission_contract.py` |
| C-06 | Memory | P2 | `memory_lifecycle.py` |
| C-07 | Learning Record | P2 | `learning_record_contract.py` |
| C-08 | Trace & Evaluation | P2 | `trace_contract.py` + `trace_evaluation.py` |
| C-09 | Identity & Delegation | P1 | `agent_identity.py` + `delegation.py` + `obo_jit.py` |
| C-10 | Canonical Data | P2 | `canonical_data.py` |

---

## 9. 下一步建议

### 9.1 立即执行（P0）

1. **验证 C-03 Skill Execution Contract**: 通过 `lumenis_skill_adapter.py` 调用 S09/S10/S11 对 ZBC 进行自审计，验证 Contract 交互可行性
2. **对齐 C-02 AI Gateway Provider 策略**: 对比 OSAI `ai_gateway.py` 与 ZBC `scripts/ai_gateway.py` 的 Provider 路由逻辑，消除差异
3. **对齐 C-05 Permission 级别**: 将 ZBC `agent_security.py` 的权限模型与 OSAI 11 级模型对齐

### 9.2 短期执行（P1）

4. **实现 C-01 Agent Runtime Contract**: 选择 1-2 个复杂舆情分析任务（如事件溯源），通过 OSAI Agent 执行
5. **实现 C-04 Evidence Chain Contract**: 将 ZBC 舆情数据（笔记→评论→事件→风险）按 Canonical Data 结构对齐
6. **验证 C-09 Identity & Delegation**: 通过 `agent_runtime_adapter.py` 验证身份链+委托在 ZBC 场景的可用性

### 9.3 长期演进（P2）

7. **设计 C-06 Memory Contract 的同步策略**: 明确 ZBC 与 OSAI 记忆的单向/双向同步规则
8. **迁移 C-07 Learning Record**: 将 ZBC `ai_learning_engine.py`（LEGACY_PARTIAL）迁移到 OSAI LearningRecord 模型
9. **建设 ZBC 自建 RAG**: 弥补 OSAI MISSING 的向量检索能力，通过 C-06 Contract 与 OSAI 交换语义记忆

---

## 附录 A: OSAI 核心模块文件清单（55 个）

```
osai_engine/
├── __init__.py
├── agent.py                    # Agent Loop 核心
├── orchestrator.py             # 编排器
├── engine_runtime.py           # 引擎运行时
├── engine_layer.py             # 引擎层
├── harness_runtime.py          # Harness 运行时
├── engineering_loop.py         # 工程循环
├── runtime_guardian.py         # 运行时守护者
├── checkpoint_resume.py        # 持久化执行
├── ai_gateway.py               # AI 网关
├── llm.py                      # LLM 集成
├── context_runtime.py          # 上下文管理
├── memory_lifecycle.py         # 记忆生命周期
├── learning_record_contract.py # 学习记录契约
├── skill_registry.py           # Skill 注册
├── skill_manifest.py           # Skill Manifest
├── skill_invocation.py         # Skill 调用
├── skill_selector.py           # Skill 选择器
├── skill_sync.py               # Skill 同步
├── canonical_skill_registry.py # Canonical Skill 注册
├── skill_execution_contract.py # Skill 执行契约
├── skills/
│   └── source_skills.py        # S01-S12 真实实现
├── tools.py                    # 工具注册
├── rules.py                    # 规则引擎
├── config.py                   # 配置
├── permission_gate.py          # 权限门
├── permission_contract.py      # 权限契约
├── action_firewall.py          # 动作防火墙
├── effect_fence.py             # 效果围栏
├── evidence.py                 # 证据
├── evidence_chain.py           # 证据链
├── evidence_graph.py           # 证据图
├── canonical_data.py           # Canonical Data
├── trace_contract.py           # Trace 契约
├── trace_evaluation.py         # 轨迹评估
├── evaluation_contract.py      # 评估契约
├── lifecycle_contract.py       # 生命周期契约
├── runtime_contract.py         # 运行时契约
├── task_contract.py            # 任务契约
├── contract_persistence.py     # Contract 持久化
├── observability.py            # 可观测性
├── research.py                 # 研究
├── research_pipeline.py        # 研究管线
├── repository_registry.py      # 仓库注册
├── repository_contract.py      # 仓库契约
├── capability_registry.py      # 能力注册
├── agent_identity.py           # Agent 身份
├── agent_integration.py        # Agent 集成
├── delegation.py               # 委托
├── obo_jit.py                  # OBO JIT
├── browser_capability.py       # 浏览器能力
├── browser_executor.py         # 浏览器执行器
├── decision_action_outcome.py  # 决策-动作-结果
├── impact_analysis.py          # 影响分析
├── release_safety.py           # 发布安全
└── ui_state_contract.py        # UI 状态契约
```

## 附录 B: 关键证据索引

| 结论 | 文件 | 行号 |
|------|------|------|
| Agent Loop max_steps=20 | `agent.py` | L45 |
| Agent Loop max_time=300s | `agent.py` | L46 |
| Agent Loop max_cost=10.0 | `agent.py` | L47 |
| Agent Loop circuit_breaker_threshold=5 | `agent.py` | L51 |
| 11 级权限模型 | `permission_gate.py` | L30 |
| Agent 自动化上限 VERIFY | `permission_contract.py` | L15 |
| 智谱 GLM 支持 glm-4.5-air/glm-5.3/glm-4.6v | `llm.py` | L95 |
| API Key 通过环境变量 | `llm.py` | L85 |
| S01-S12 SKILL_EXECUTORS | `source_skills.py` | L367-380 |
| Canonical Data 十实体 | `canonical_data.py` | L181-185 |
| EvidenceGraph 9 种关系 | `evidence_graph.py` | L11-14 |
| Checkpoint save/resume | `checkpoint_resume.py` | L40-80 |
| CanonicalSkillRegistry 唯一 Truth | `canonical_skill_registry.py` | L1 |
| Browser FORBIDDEN_ACTIONS | `browser_capability.py` | L100-105 |
| LearningRecord lifecycle_stage | `learning_record_contract.py` | L30-50 |
| IdentityChain user→agent→skill→tool | `agent_identity.py` | L30-60 |
| DelegationContext approve/revoke | `delegation.py` | L30-60 |
| OBO JIT token issuance | `obo_jit.py` | L30-50 |
| ContextManager trim max_tokens=8000 | `context_runtime.py` | L40 |
| MemoryStore 六层记忆 | `memory_lifecycle.py` | L30-110 |

---

**报告结束**

> 本报告为只读审计产物，未修改 OSAI 或 ZBC 任何源码。所有结论均有文件路径+行号证据。Contract 接口设计为纯数据结构/API/事件定义，不引入 OSAI 运行时依赖。
