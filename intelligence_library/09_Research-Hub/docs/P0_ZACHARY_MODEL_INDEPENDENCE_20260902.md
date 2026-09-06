# P0｜Zachary Model Independence / AI Runtime 独立性

日期：2026-09-02
状态：P0 / NEXT AUDIT + IMPLEMENTATION

## 1. 决策

将“Zachary Model Independence / AI Runtime 独立性”提升为下一轮双子库第一梯队施工项。

目标不是现在训练一个新的基础大模型，而是先让 Zachary 在**系统层独立于任何单一模型供应商**：Zachary 自己拥有 Runtime、Context、Memory、Resource、Task、Tool、Evaluation、Learning Signal 和 Provider Routing；底层模型只是可替换的推理 Provider。

## 2. GitHub / 全网研究结论（2026-09-02）

近期公开开源实践显示，Model Routing、Local-first、Provider-agnostic Runtime、Tool/Agent routing、Verification-aware escalation 已成为实际工程方向，而不是单纯概念。

参考方向：

- Autohand Routes：provider-agnostic、policy-driven model routing，覆盖本地模型、Ollama、llama.cpp、vLLM及云端 Provider，并把 capability/cost/latency/privacy/provider health 纳入路由决策。
- RouteLabs Router：local-first + cloud fallback + verification-aware escalation + privacy-aware routing + MCP-style tool traces，并支持 Ollama、llama.cpp、LM Studio、vLLM 等本地运行时。
- Talu：single-binary local-first inference runtime，提供 structured output、embeddings/vector search、tool calling、persistent sessions，并能通过统一 API 路由远程 OpenAI-compatible endpoint。
- AgentWeave：强调在模型推理前先做 policy/permission/task-aware routing，减少工具决策空间，并显式保留 provenance、recovery 和 execution policy。
- LLMRouter：将模型路由做成可测试、可评测的独立层，支持多种 routing 策略。
- Ollama Structured Outputs：结构化 JSON Schema 输出可用于可靠的数据提取和系统级结果约束。
- 当前开源模型趋势：Qwen3、Gemma、Phi、Devstral 等提供不同规模的本地/开放权重选择；大型 agentic coding 模型更适合 Provider 层，不应被写死为 Zachary 的身份。

行业趋势亦显示模型路由正在成为降低成本、提高隐私和减少单一供应商依赖的重要架构层。

## 3. Zachary 新目标架构

```text
                    ZACHARY AI RUNTIME
                           │
       ┌───────────────────┼───────────────────┐
       ↓                   ↓                   ↓
   Context Core        Resource Core       Memory Core
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ↓
                    Task / Planner
                           ↓
                    Policy Engine
                           ↓
                  Tool / Skill Runtime
                           ↓
                   Provider Router
              ┌────────────┼────────────┐
              ↓            ↓            ↓
          Local AI      Cloud AI     Future AI
              │            │            │
       Ollama/llama.cpp   APIs       自有模型
              └────────────┼────────────┘
                           ↓
                    Verification
                           ↓
                      Evidence
                           ↓
                    Learning Signal
```

## 4. P0 必须实现的独立性

### P0-A Provider Independence

- ZBC 不得直接绑定豆包/云智/Ollama/任何具体模型。
- ZBC 通过 Zachary Contract 请求能力。
- Zachary 通过 Provider Adapter / Router 决定实际模型。
- Provider 必须可插拔。

### P0-B Runtime Independence

即使所有模型 Provider 暂时不可用，Zachary Runtime 仍应能够启动并管理：

- Resource
- Context
- Memory metadata
- Task
- Tool registry
- Provider health
- Evaluation records
- Evidence metadata
- Learning Signal queue

高级自然语言推理可以降级，但 Runtime 不得整体死亡。

### P0-C Local-first / Policy-aware Routing

路由至少考虑：

- task type
- privacy classification
- model capability
- latency
- cost
- provider health
- context size
- structured-output/tool-call requirements

默认策略：敏感/本地可处理任务优先本地；复杂任务在 Policy 允许时升级云端；Provider 失败可按策略 fallback。

### P0-D Verification-aware Escalation

模型输出不得直接成为生产事实。

```text
Model Output
 → Schema Validation
 → Policy Validation
 → Evidence Check
 → Optional Second Model / Rule Verification
 → Accepted Result
```

### P0-E Context Isolation

每次任务必须显式携带：

- `product_context`
- `tenant_context`
- `task_context`
- `permission_scope`

Resource 可共享；Product Truth 不共享。

## 5. 第一阶段不做什么

- 不训练自有基础模型。
- 不替换当前生产模型后立即切换。
- 不允许 Agent 获得 unrestricted filesystem/browser/production write。
- 不让模型自动修改 ZBC 核心规则。
- 不删除当前已验证 Provider。
- 不因“模型独立”破坏现有 ZBC 生产能力。

## 6. 与当前 ZBC 的连接

目标链路：

```text
ZBC
 ↓
Zachary Contract
 ↓
Zachary Runtime
 ↓
Resource / Context / Task / Policy
 ↓
Provider Router
 ↓
Local / Cloud / Future Model
 ↓
Verification
 ↓
ZBC Production Result
```

ZBC 仍然拥有生产业务真相；Zachary 是通用 AI 能力中枢。

## 7. 验收标准

必须通过：

1. Provider 插拔测试
2. Local-only 测试
3. Cloud-only 测试
4. Local unavailable fallback 测试
5. Cloud unavailable degradation 测试
6. Privacy routing 测试
7. Structured output/schema 测试
8. Tool permission 测试
9. Context isolation 测试
10. Evidence/provenance 测试
11. ZBC 不直连具体 Provider 的代码扫描
12. Runtime 无模型启动测试
13. 24h 稳定性测试（能力成熟后）

## 8. 当前推荐 Provider 研究池

只作为 Benchmark/Provider 候选，不等于直接接入：

- Qwen3 系列：本地、多语言、Agent/Reasoning候选
- Gemma 系列：本地轻量/多模态候选
- Phi 系列：低资源候选
- Devstral：代码 Agent 候选
- Kimi / GLM / DeepSeek 等开放权重/开放模型：高能力 Agent/Coding Provider 候选，必须逐项核对当前版本、许可证、部署成本和商业使用条件

模型选择必须通过 Benchmark 决定，不允许按“名气”写死。

## 9. 下一轮施工顺序

```text
P0-1 Audit current AI provider call graph
 ↓
P0-2 Define Provider Contract
 ↓
P0-3 Build Provider Adapter / Registry
 ↓
P0-4 Build Policy-aware Router
 ↓
P0-5 Add structured output + verification
 ↓
P0-6 Add Context Isolation
 ↓
P0-7 Disconnect-test ZBC from direct providers
 ↓
P0-8 Runtime / fallback / evidence tests
 ↓
P0-9 Dual-repo cross-audit
 ↓
P0-10 Release Gate
```

## 10. 关闭条件

本项只有在**代码已施工、测试已通过、Runtime 已验证、Evidence 已记录、双子库交叉审计通过**后才可关闭。

核心原则：

`Zachary ≠ Model`

`Provider ≠ Zachary`

`Model can change; Zachary Runtime must remain.`

`Resource ≠ Product Truth`

`Learning ≠ Permission`

`Style ≠ Business Rule`
