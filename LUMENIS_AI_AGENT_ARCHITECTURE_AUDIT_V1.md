# LUMENIS AI / Agent 架构审计 V1

状态：第 9 类“AI / Agent 架构审计”交付物  
审计基线：`78c469d81905568350338f9d01e2ce5baf3c6c67`  
原则：AI 是增强层；Agent 不能拥有 Production Truth、Production Data Ownership 或最终 Business Rule。

## 1. 目标架构

```text
User
  ↓
Orchestrator
  ↓
Specialist Agents
  ↓
Tools
  ↓
Evidence
  ↓
Evaluation
  ↓
Human Approval
  ↓
受控 Action / Production Admission
```

生产写入必须经过：

`Task → Permission → Action Firewall → Effect Fence / Idempotency → Execute → Evidence → Evaluation → Trace`

## 2. 当前真实实现

### Agent Boundary

`agent_boundary.py` 已实现：

- `AgentRole`、`Permission`、`ActionDecision`、`ApprovalStatus`。
- Agent 默认权限受限，禁止 Agent 使用 `COMMIT`、`PUSH`、`DELETE` 等高风险权限。
- Agent 不能创建 `SUPER_ADMIN` 身份，超级管理员限定为人工。
- AgentIdentity 包含 permission scope、tool allowlist、denylist。
- ActionFirewall 进行动作、工具、参数、权限检查。
- ApprovalManager 支持人工审批、拒绝、过期和待处理查询。
- IdempotencyGuard 防止短窗口重复动作。

### Skill Execution Chain

`skill_execution_chain.py` 明确实现：

`Task → Permission → Agent → Skill → Tool → Action Firewall → Effect Fence → Execute → Evidence → Evaluation → Trace`

真实函数包括 `check_permission()`、`action_firewall()`、`effect_fence()`、`execute_skill()`、`build_evidence()`、`evaluate_execution()`、`record_execution_evidence()` 和 `write_trace()`。

它将执行证据桥接到 `evidence_chain.EvidenceStore` / `zbc_evidence`，并记录 permission、firewall、effect_fence、evaluation 和 execution trace。

### Action Firewall

`p2_action_firewall.py` 进一步执行：

`Identity → Intent → Tool → Parameter → Target → Scope → Risk → Permission → Action`

明确硬拒绝生产数据库直接写入，并对 push、deploy、write、export 等动作设置风险或人工审批要求。

### Production Evidence Contract

`production_evidence_contract.py` 已实现：

- Evidence 类型。
- verified_by、ai_assisted、human_approved。
- AI 辅助保护操作需要人工审批。
- 非 VERIFIED 证据不能进入生产变更。
- `can_execute_production_change()` 进行生产准入检查。

### AI Provider / Gateway

`ai_channel.py` 提供 provider chain、breaker、retry、health monitor、fallback、provider switch trace；`provider_registry.py` 提供 provider status、availability、active provider 和本地探测。

当前 API 状态曾显示 Ollama provider 与 `qwen2.5-coder:7b-agent`，但配置/状态不等于每条生产业务链已经完成真实调用验证。

### Evaluation

`evaluation_system.py` 提供 collection、analysis、report、system stability 评估、badcase、golden case、regression 和 trace_id；但评估系统本身是否成为所有 Agent 生产动作的强制门禁，当前源码证据不足。

## 3. 并行实现与边界风险

### `agent_security.py`

该模块自身声明为 Legacy/互补防护，负责 Prompt Injection、工具白名单、参数检查和输出过滤；它不能替代 `permission_gate.py`、`security_boundary.py` 或 `agent_boundary.py`。

风险：如果旧调用方直接使用 `agent_security.validate_tool_call()`，可能绕过新 Agent Boundary 的身份、审批、幂等和 Evidence 语义；必须通过调用链逐个确认。

### Permission 层并行

当前至少存在 `permission_gate.py`、`security_boundary.py`、`agent_boundary.py`、`agent_security.py` 和 `p2_action_firewall.py`。它们可能分别承担应用权限、AI 工具安全、Agent 身份和动作防火墙，但尚未形成唯一入口的运行证据。

### Orchestrator / Specialist Agents

仓库有 `ai_task_engine.py`、`ai_task_parser.py`、Agent registry、Skill registry 和多个 Agent 相关目录，但本轮没有证据证明所有用户任务都由一个 Orchestrator 统一编排，也没有证据证明所有 Specialist Agent 都只能通过统一 Tool Contract 执行。

### Evidence / Trace 并行

执行链写入 `zbc_evidence`，AI 调用写入 `ai_call_logs`，另有 `app_evidence_records`、BrowserEvidenceStore 和 OSAI 侧 Evidence 资产。跨仓只能通过版本化 Contract/Artifact，不能共享生产数据库或让 AI 侧直接持有 LUMENIS 生产真相。

## 4. AI 不得拥有的权力

以下边界已作为目标红线固定：

- 不得决定 Subject 归属。
- 不得改写原始 Evidence。
- 不得单独决定统计口径、发布时间、数量和最终风险边界。
- 不得直接写入 Production Truth。
- 不得直接执行生产数据库变更。
- 不得自行授予 Permission、提升 Agent 权限或关闭 Audit。
- 不得用自然语言输出替代 Human Approval、Evaluation 或 Trace。

AI 可以做：发现、分类、摘要、解释、推理、建议、内容辅助和工程辅助；结果必须保留原始输出、规则结果、人工修正和最终决策的分离关系。

## 5. 当前证据缺口

1. 用户输入到唯一 Orchestrator 的全量调用链尚未证明。
2. Specialist Agent 到 Tool 的 allowlist、权限、目标范围和审计映射尚未形成统一注册表。
3. `agent_security`、`permission_gate`、`security_boundary`、`agent_boundary`、`p2_action_firewall` 的唯一优先级尚未由运行时证据确认。
4. Effect Fence 的 `writes_production` 与实际生产写入入口尚未完成端到端验证。
5. Evidence、Evaluation、Human Approval、Trace 虽有实现，但不是所有 Agent 任务都已证明强制经过。
6. AI provider fallback 机制存在，但当前生产业务链仍没有完整 provider failure → fallback → evidence → final result 证据。
7. Agent 输出与 Canonical Data 的隔离在模块级存在，尚需证明所有写入口都不能覆盖 Production Truth。

## 6. 目标收敛方案

### 唯一编排入口

所有用户任务统一进入 Orchestrator，由它生成 task_id、trace_id、domain_id、product_id、permission context 和 execution plan。

### 专家 Agent

Specialist Agent 只负责受限的分析或建议，例如 Collection Analyst、Evidence Analyst、Event Analyst、Risk Analyst、Content Analyst、Evaluation Analyst；Agent Groups 仍是跨产品执行层，不成为产品线。

### 工具准入

每个 Tool 必须注册：输入 schema、输出 schema、读写属性、允许域、允许产品、权限、风险等级、Evidence 要求、测试和回滚语义。

### 生产动作

生产动作默认 staged/read-only；需要写入时必须经过 Action Firewall、Effect Fence、幂等、Evidence、Evaluation 和 Human Approval。AI 只能提出候选，不能自行放行。

### 跨仓边界

OSAI、GGI、LUMENIS Command 不得成为 LUMENIS 生产运行时依赖，不共享生产数据库、生产凭据或未经验证的生产事实；只通过版本化 Contract/Artifact 交换。

## 7. 七项验收

| 验收项 | 结果 | 依据 |
|---|---|---|
| Source | PASS | AI channel、provider、task、agent、permission、firewall、evidence、evaluation、skill 源码已读取 |
| Call Graph | PARTIAL | Skill 执行链清晰；全量用户任务到唯一 Orchestrator 未证明 |
| Data / API | PARTIAL | Evidence/Trace 字段和桥接存在；多套证据存储并行 |
| Frontend / Consumer | PARTIAL | AI/Evidence 页面存在；页面展示不等于动作已获批或执行 |
| Runtime | PARTIAL | provider/fallback/guardian 机制存在；生产 Agent 全链路未验证 |
| Tests | PASS / PARTIAL | Agent、Permission、Evidence、Skill、AI 测试资产存在；缺少全量生产动作回放证据 |
| Production Evidence | FAIL | 尚未证明所有 Agent 任务强制经过统一 Permission、Approval、Evaluation、Trace |

## 8. 本类结论

第 9 类 AI / Agent 架构审计完成，状态：`CONTROL DESIGN EXISTS / PRODUCTION ADMISSION NOT VERIFIED`。

当前可以确认系统已经具备较完整的安全控制构件，但不能宣称 Agent System 已经形成唯一、强制、端到端的生产控制链。下一步必须优先做 Agent 任务回放、权限拒绝、生产写入阻断、Evidence 生成、人工审批和 Trace 完整性的组合测试。

