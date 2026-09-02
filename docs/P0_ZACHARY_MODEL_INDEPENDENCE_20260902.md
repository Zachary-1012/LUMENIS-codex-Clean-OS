# P0｜Zachary Model Independence / ZBC 解耦施工基线

日期：2026-09-02
状态：P0 / NEXT AUDIT + IMPLEMENTATION

## 1. 决策

将 Zachary 的 Model Independence / AI Runtime 独立性列入下一轮双子库第一梯队。

ZBC 不再直接依赖任何具体模型 Provider。生产业务通过 Zachary Contract 获取 AI 能力；Zachary 决定 Provider，Provider 可替换。

目标是“AI 系统独立”，不是现在训练一个基础大模型。

## 2. 研究依据

2026 年近期 GitHub/开源实践显示，provider-agnostic routing、local-first、verification-aware escalation、policy-aware tool routing 已成为成熟方向。

重点参考：

- Autohand Routes：provider-agnostic、policy-driven model routing，支持本地与云端 Provider，并考虑能力、成本、延迟、隐私、Provider 健康。
- RouteLabs Router：local-first、cloud fallback、verification-aware escalation、privacy-aware routing，兼容 Ollama、llama.cpp、LM Studio、vLLM 等。
- Talu：local-first inference runtime，统一提供 structured output、embeddings、vector search、tool calling、persistent sessions 和远程 endpoint routing。
- AgentWeave：先做 policy/permission/task routing，再交给模型推理，避免工具空间无限膨胀。
- LLMRouter：独立模型路由与评测层。
- Ollama Structured Outputs：JSON Schema 约束模型输出，提高系统可靠性。
- 开源模型研究池：Qwen3、Gemma、Phi、Devstral，以及 Kimi/GLM/DeepSeek 等开放权重模型，均作为 Provider Benchmark 候选，不写死为 Zachary。

## 3. ZBC 必须变成

```text
ZBC
 ↓
Zachary Contract
 ↓
Zachary Runtime
 ↓
Provider Router
 ↓
Local / Cloud / Future Model
```

禁止：

```text
ZBC → 豆包
ZBC → Ollama
ZBC → 某个固定模型
```

## 4. P0 施工要求

### P0-A Provider Contract

ZBC 只请求标准能力，例如：

- classify
- summarize
- extract
- generate
- reason
- tool_call
- structured_output

不得依赖具体 Provider 名称。

### P0-B Provider Registry / Adapter

Provider 由 Zachary 统一登记和健康检查：

- local provider
- cloud provider
- future provider

Provider 挂掉不得导致 ZBC Runtime 整体不可用。

### P0-C Policy-aware Routing

至少考虑：

- task type
- privacy
- capability
- latency
- cost
- provider health
- context window
- structured output / tool-call requirement

### P0-D Verification

模型输出必须经过 Schema / Policy / Evidence 验证后才能进入 ZBC 生产流程。

模型 confidence 不等于 Evidence。

### P0-E Context Isolation

调用 Zachary 必须携带：

`product_context` / `tenant_context` / `task_context` / `permission_scope`

ZBC 的业务规则、主体口径、风险口径和数据库真相不能被 Zachary 或其他产品上下文覆盖。

## 5. Runtime 独立性

当所有模型 Provider 暂时不可用时，Zachary Runtime 应仍可运行；ZBC 至少保持非 AI 生产能力和安全降级。

不能出现：

`AI Provider unavailable → ZBC entire system unavailable`

必须存在：

`AI Provider unavailable → controlled degradation / queue / retry / fallback`

## 6. 不得做

- 不训练基础模型作为本轮目标
- 不立即替换现有生产 Provider
- 不删除当前可用 AI Provider
- 不让模型直接修改 ZBC 生产规则
- 不让 Agent unrestricted 写生产 DB / 文件系统 / 浏览器
- 不改变 `SUBJECT_WORDS`、`SUBJECT_EXCLUDE_WORDS`、`subject_hit()` 等生产真相，除非独立 Change Plan + Review + Evidence

## 7. 验收测试

必须执行：

1. Provider 插拔
2. Local-only
3. Cloud-only
4. Local failure fallback
5. Cloud failure degradation
6. Privacy routing
7. Structured output
8. Tool permission
9. Context isolation
10. Evidence/provenance
11. ZBC direct-provider code scan
12. Zachary Runtime no-model startup
13. 生产非AI路径安全降级

## 8. 第一梯队施工顺序

```text
Audit current ZBC AI call graph
 ↓
Provider Contract
 ↓
Zachary Adapter / Registry
 ↓
Policy Router
 ↓
Verification
 ↓
Context Isolation
 ↓
Remove direct model coupling
 ↓
Fallback / degradation tests
 ↓
Runtime Evidence
 ↓
双子库交叉审计
 ↓
Release Gate
```

## 9. 关闭条件

只有代码、测试、Runtime、Evidence 和双子库交叉审计全部完成，才能关闭 P0。

硬原则：

`Zachary ≠ Model`

`Provider ≠ Zachary`

`Model can change; Zachary Runtime remains.`

`AI is enhancement, not ZBC's production truth.`
