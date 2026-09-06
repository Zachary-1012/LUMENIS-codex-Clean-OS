# OSAI 学习进化 · 2026-09-02 · Contract 更新建议（给 Z Brand Core）

> 双子星边界：本文档为 OSAI 研究侧产出的 Contract 更新建议，**仅提供 Contract，不修改 ZBC 生产代码**。
> 由 Z Brand Core / Carter 负责 Audit → Implementation → Test → E2E → Evidence → Commit。
> 来源：`learning-feed/learning-20260902.md` + `ai-os-research/09/10` 学习进化更新（commit d8f4ea7 / 10468fa）。

---

## 1. 更新背景

2026-09-02 学习进化发现 Agent 安全实证研究出现重大结论：

- **StakeBench**（NTU/ST Engineering/IBM/UIUC）：3,160 次攻击，GPT-5/Gemini 驱动 web agent **无一种攻击场景被一致阻断**；直接注入成功率 >79%，间接注入 42%-68%。
- **StepJack**（arXiv 2608.06477）：多步间接注入新攻击类别（子步骤分散在导航链）。
- **ClawSafety**：Chat safety ≠ Agent safety；**scaffold 选择本身可移动 ASR 达 8.6pp**。

**核心结论**：输入过滤不可作为独立安全边界；安全必须上移到运行时/工具层（沙箱 + Task-bound 权限 + 人工确认）。

---

## 2. Contract 更新清单

### CTR-SEC-P0-01：安全防御层级重排

```yaml
Contract:
  contract_id: "CTR-SEC-P0-01"
  version: "1.1"
  status: "draft"
  requirement:
    title: "安全防御层级重排：输入过滤降级为辅助层"
    description: >
      将 ZBC Runtime/Browser/Collector 中基于 LLM 输入的过滤逻辑从"独立安全边界"
      降级为"辅助层"；沙箱 + Task-bound 权限升级为唯一硬门槛。
    background: "StakeBench 实证：GPT-5/Gemini web agent 对直接注入成功率>79%，输入过滤不可单独依赖。"
    success_criteria:
      - "所有 Agent 交互路径均经过 Task-bound Permission 校验"
      - "浏览器/代码执行均在沙箱中"
      - "输入过滤仅作为辅助层保留"
  osai_deliverables:
    - research_report: "ai-os-research/09-safety-permission-sandbox.md（2026-09-02 更新）"
    - architecture_design: "沙箱+Task-bound Permission 为硬门槛"
  zbc_execution:
    assigned_team: "Z Brand Core"
    implementation_steps:
      - "审计所有 Agent 交互路径的权限校验覆盖"
      - "将输入过滤标记为辅助层"
      - "确保沙箱覆盖所有代码/浏览器执行"
  acceptance_criteria:
    security:
      - "StakeBench 风格红队评测通过"
      - "沙箱逃逸次数 = 0"
    evidence_required: ["安全审计报告"]
  security_constraints:
    permission_scope: "Task-bound"
    sandbox_required: true
    no_production_access: true
  lifecycle:
    created_by: "OSAI"
    executed_by: "ZBC"
    verified_by: "OSAI+ZBC"
```

### CTR-SEC-P0-02：每步权限校验（应对 StepJack 多步注入）

```yaml
Contract:
  contract_id: "CTR-SEC-P0-02"
  version: "1.0"
  status: "draft"
  requirement:
    title: "多步操作每步权限校验"
    description: >
      Browser/Workflow 类 Agent 在**每一步**操作均做权限校验，
      而非仅入口校验（应对 StepJack 多步间接注入）。
    success_criteria:
      - "每个 Tool Call 均携带有效 Permission Ticket"
      - "越权 Tool Call 被硬阻断并记录"
  zbc_execution:
    implementation_steps:
      - "在 Tool Adapter 层加入 per-step 权限校验"
      - "权限校验失败时记录 Evidence 并触发 HITL"
  acceptance_criteria:
    security: ["StepJack 红队评测通过"]
  lifecycle:
    created_by: "OSAI"
    executed_by: "ZBC"
```

### CTR-SEC-P0-03：ClawSafety 对齐（scaffold 即安全边界）

```yaml
Contract:
  contract_id: "CTR-SEC-P0-03"
  version: "1.0"
  status: "draft"
  requirement:
    title: "Scaffold 即安全边界对齐"
    description: >
      依据 ClawSafety 实证（scaffold 选择可移动 ASR 8.6pp），
      将安全设计从 prompt 层上移到运行时/工具层（scaffold 层）。
    success_criteria:
      - "安全策略集中在 Runtime/Tool 层而非 prompt"
      - "scaffold 变更必须过安全评审"
  zbc_execution:
    implementation_steps:
      - "梳理当前 scaffold 中的安全策略位置"
      - "将关键策略迁移到工具层"
  lifecycle:
    created_by: "OSAI"
    executed_by: "ZBC"
```

---

## 3. 已更新基线文档索引

| 文档 | 更新内容 | Commit |
|------|---------|--------|
| `ai-os-research/09-safety-permission-sandbox.md` | 输入过滤证伪、沙箱硬门槛升级、新增攻击面 | d8f4ea7 |
| `ai-os-research/10-evaluation-framework.md` | 安全/记忆评测项扩充 | 10468fa |
| `ai-os-research/05-experience-engine.md` | HORMA/ReasoningBank/记忆基准化 | a95264e |
| `ai-os-research/08-proactive-intelligence.md` | Proactive 验证基准 | 8aad452 |

---

## 4. 待 ZBC 决策/执行项

- [ ] ZBC Audit：当前安全防御层级与权限校验覆盖
- [ ] ZBC 执行：CTR-SEC-P0-01/02/03 实现
- [ ] ZBC 提供：StakeBench/StepJack 红队评测结果
- [ ] OSAI 复核：评测证据回收后更新基线

*本 Contract 不包含任何 Cookie/Token/Session/密钥。双子星边界保持。*
