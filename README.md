# 序境

> **中文正式产品名：序境**
> **英文正式产品名：LUMENIS**
> **AI 共享智能体系：Zachary OS AI（暂定名，未实体化）**

## 1. 产品身份

**序境是独立产品。**

GitHub Repository `Z-Brand-Core` 是序境当前生产研发仓库标识，不等同于产品名称。

序境负责真实业务生产、数据、采集、分析、风险、报告、运行与产品体验，是一个完整独立产品。

**Global Growth Intelligence 是另一个独立产品。**

它负责全球现实研究、技术/AI/商业/市场/政策研究、案例、趋势、证据、判断与增长研究，同样独立研发、独立运行、独立测试。

两个产品不是一个产品，不互相调用，不互相修改，不建立运行时依赖。

## 2. 两个产品唯一共同的智能体系

```text
                 Zachary OS AI
              （暂定名 / 无独立实体）
                         │
          ┌──────────────┴──────────────┐
          │                             │
        序境                     Global Growth
     独立产品①                    独立产品②
          │                             │
   业务生产数据/结果              全球研究数据/结果
   用户反馈/案例                  全球证据/案例
   真实运行环境                  全球现实研究环境
          │                             │
          └───────────┬─────────────────┘
                      ↓
             AI 数据 / 能力成长
       Evidence · Skill · Evaluation
       Memory · Feedback · Learning
                      ↓
             分别服务两个产品
```

### 核心定义

- **序境**：产品实体。
- **Global Growth Intelligence**：独立产品实体。
- **Zachary OS AI**：两个产品共同使用的 AI 智能能力体系；目前只是数据、模型、能力、记忆、Skill、Evaluation、Learning 等集合，不是独立产品实体。
- Zachary OS AI 当前不提前确定最终产品名、品牌名或独立产品形态。
- 两个产品可以共同推动 Zachary OS AI 成长，但不得因此合并成一个产品。

## 3. 物理与运行边界

```text
Repository A: Z-Brand-Core
        ↓
      序境

Repository B: global-growth-intelligence
        ↓
Global Growth Intelligence

Zachary OS AI：共享智能能力层
```

硬规则：

1. 两个产品保持代码仓库独立。
2. 两个产品保持运行时独立。
3. 不允许 A → B 的运行时调用。
4. 不允许 B → A 的运行时调用。
5. 不把另一个产品的业务代码复制进来。
6. 不建立跨产品数据库依赖。
7. 不把 Zachary OS AI 强行做成第三个产品。
8. AI 输出不能直接替代产品的业务事实。
9. 两个产品通过各自的数据、Evidence、Feedback、Evaluation 等推动共享 AI 能力成长；未来如需交换能力，只允许通过明确、版本化、可追溯的 Contract / Artifact 边界完成。

## 4. 当前源码级审计基线

本次审计以 **2026-09-05 main** 的线上源码事实为基线：

`Z-Brand-Core main = 0249ec8d630774752f635b8c907db61a52fee66b`

当前仓库已经具备完整的治理、架构、工程循环、AI Provider、数据真相、生产规则、测试与发布治理资产；同时仍存在需要继续推进的架构收口项，不能把“已有治理文档”直接等同于“所有运行时代码已完成”。

当前源码事实确认的重点：

- ZBC 生产核心仍为 Production Truth 权威。
- 生产业务规则与 AI 判断边界已有明确治理。
- `SUBJECT_WORDS`、`SUBJECT_EXCLUDE_WORDS`、`subject_hit()` 等核心主体边界属于保护项。
- AI Provider 已采用可替换方向，不能让 AI 成为生产系统唯一生命线。
- Engineering Loop 已形成 Contract；最新提交已明确 READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW → TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH 的治理边界。
- Commit / Push 不应成为 Agent 无审批的自主循环。
- Data Truth、Evidence、Lifecycle、Permission、Runtime、Skill 等治理方向已经进入仓库，但必须继续逐项用真实源码、测试和运行证据验收。
- 仓库中仍存在历史命名/旧架构文档，需要按照当前产品边界继续做引用、依赖与生命周期清理，不允许直接删除历史资产。

## 5. Zachary OS AI 共享能力边界

Zachary OS AI 未来重点沉淀：

```text
Model Gateway
Agent
Research
Evidence
Memory
Skill
Evaluation
Learning
Planning
Reasoning
Engineering Loop
Trace
```

这些能力的目标不是取代序境或 Global Growth Intelligence，而是让两个独立产品都能获得持续成长的智能能力。

## 6. 序境产品边界

序境自身负责：

```text
Business Truth
Data Truth
Subject Truth
Collection
Event
Risk
Analysis
Report
Runtime
Product UX
```

Zachary OS AI 可以参与分析、分类、摘要、推理、建议、研究与工程辅助，但不能直接成为生产事实最终裁判。

## 7. Global Growth Intelligence 产品边界

Global Growth Intelligence 自身负责：

```text
Global Evidence
Research
Cases
Technology Signals
Market Signals
Business Signals
Policy / Regulation
Insight
Decision Support
Outcome
Feedback
```

它不是序境的子模块，也不是序境的研发后台；它是独立产品，同时也是 Zachary OS AI 的重要现实研究训练环境。

## 8. 共同成长闭环

```text
真实任务
→ 数据 / Evidence
→ AI 分析 / Agent
→ 人类判断
→ Action
→ Outcome
→ Feedback
→ Evaluation
→ Learning
→ Skill / Memory / Rule 改进
→ 下一次任务
```

两个产品各自完成自己的闭环，再将经过验证、可复用的智能资产以标准 Contract / Artifact 形式沉淀到 Zachary OS AI 能力体系。

**不允许未经验证的产品数据、AI 输出或研究结论直接进入共享智能能力。**

## 9. 最高研发原则

```text
DISCOVER
→ REQUIREMENT
→ RESEARCH
→ EVIDENCE
→ DECISION
→ ARCHITECTURE
→ IMPLEMENT
→ TEST
→ VERIFY
→ RELEASE
→ OPERATE
→ MONITOR
→ LEARN
→ IMPROVE
→ RETIRE
```

工程执行：

```text
READ
→ AUDIT
→ ANALYZE
→ PLAN
→ PATCH PREVIEW
→ TEST
→ VERIFY
→ HUMAN APPROVAL
→ COMMIT
→ PUSH
```

坚持：**先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再交付。**

## 10. 当前完成事项与下一阶段

### 已完成 / 已建立

- 序境作为独立产品的生产边界已明确。
- Global Growth Intelligence 作为独立产品的边界已明确。
- Zachary OS AI 作为两个产品共同使用、但暂不实体化的 AI 能力体系已明确。
- 两产品不互通、不互相依赖的运行边界已明确。
- ZBC 生产真相、AI 边界、Evidence、Lifecycle、Engineering Loop 等治理基础已建立。
- Global Growth Intelligence 已完成仓库入口基线，但其源码仍处于早期建设阶段，不能虚报完成度。

### 下一阶段 P0

1. 完成 ZBC 全源码功能/依赖/运行时/生命周期逐项验收，区分“代码存在”与“真实可用”。
2. 修正所有仍使用旧产品/旧 AI 架构命名的权威文档与代码引用；先引用审计，再迁移，不直接删除。
3. 建立 Zachary OS AI 的最小共享 Contract：Evidence / Skill / Evaluation / Learning / Memory / Trace。
4. 让序境与 Global Growth Intelligence 各自通过本地边界消费共享 AI 能力，不产生跨产品运行时耦合。
5. 建立统一的 AI 成长评价：准确性、可验证性、成功率、人工修正率、复用率、成本、延迟、失败类型与真实 Outcome。

### P1

- 真实 Skill Registry 与 Evaluation。
- AI Memory / Learning 闭环。
- Agent 权限、身份、Trace 与可回放执行链。
- Evidence → Skill → Evaluation → Learning 的自动化资产沉淀。
- 两个产品分别形成稳定的 AI 使用与反馈数据集。

### P2

- Zachary OS AI 独立实体化评估。
- 独立部署、独立身份、独立权限与独立运行时。
- 在成熟度达到阈值前，不提前产品化、不提前锁定正式品牌名。

## 11. 状态声明

**序境：独立产品，持续向生产上线收口。**

**Global Growth Intelligence：独立产品，处于快速奠基与研发加速阶段。**

**Zachary OS AI：共享 AI 智能体系，暂不实体化、暂不定最终名称。**

所有“完成”必须以源码 + 测试 + 运行 + Evidence 为依据；规划项不得写成已完成能力。
