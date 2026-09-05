# 序境

> **中文正式产品名：序境**
> **Repository：Z-Brand-Core**
> **共享智能体系：Zachary OS AI**

## 1. 产品定位

序境是独立、可独立运行的生产产品，负责真实业务生产、数据、采集、分析、风险、报告、运行与产品体验。

序境不依赖 Global Growth Intelligence，也不依赖 Zachary OS AI 才能启动或完成核心生产流程。

## 2. 三仓关系

```text
                  Zachary OS AI
             共享智能成长层 / 能力层
                         ▲
              Contract / Artifact
                         │
          ┌──────────────┴──────────────┐
          │                             │
        序境                  Global Growth Intelligence
      独立产品①                     独立产品②
          │                             │
     Production Truth             Research / Growth Truth
```

三仓保持物理、代码、运行时与数据边界独立。

- 序境不调用 Global Growth Intelligence。
- 序境不把 Zachary OS AI 作为生产关键依赖。
- 不共享生产数据库。
- 不复制另一产品的业务代码。
- 共享智能只通过明确、版本化、可追溯的 Contract / Artifact 边界进行。
- OSAI 不拥有序境 Production Truth，也不能直接修改生产事实。

## 3. 序境生产边界

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

AI 可参与分析、分类、摘要、推理、建议与工程辅助，但不能替代核心生产事实与确定性业务规则。

核心主体边界 `SUBJECT_WORDS`、`SUBJECT_EXCLUDE_WORDS`、`subject_hit()` 等属于保护项；生产数据、账号/会话、凭据与核心业务规则不得被共享智能层接管。

## 4. 共享智能边界

序境产生的可复用经验只有在经过本地验证、脱敏、评价与正式 Contract / Artifact 边界后，才允许作为共享智能成长输入。

```text
真实任务
→ Evidence / Result
→ Evaluation
→ Human Feedback
→ Contribution
→ Validation
→ Generalization
→ Admission
→ Shared Learning Asset
```

共享智能输入不是生产数据库复制，也不是生产运行时同步。

OSAI 不可用、贡献失败或共享智能升级时，序境核心生产流程仍必须正常运行。

## 5. 工程与生命周期

产品研发遵循：

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

工程执行遵循：

```text
READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW
→ TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH
```

坚持：**先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再交付。**

## 6. Runtime / Test 收口状态

**2026-09-05：三仓 Runtime & Test Audit 已完成并收口，相关报告已推送仓库正式留档。**

本事项的三仓边界、贡献机制、非阻塞原则与测试基线以已推送版本为准。

后续不再重复开展已经完成的架构收口工作；只有真实 Bug、安全问题或明确产品需求才重新打开相关范围。

## 7. 当前研发阶段

序境进入下一阶段：**产品实际可用 → 商业化交付 → 真实用户验证 → 收入闭环。**

研发重点回到产品本身：

- 核心用户场景
- 核心功能完整可用
- 数据与分析结果
- 趋势 / 风险 / 决策信息
- 报告与交付
- 产品体验
- 权限与额度
- 商业化能力
- 真实用户反馈

不得为了共享智能机制重新改动已经收口的生产边界，不得让 OSAI 阻塞序境后续研发、测试、部署或上线。

## 8. 状态声明

**序境：独立产品 · Runtime/Test 收口完成 · 持续进入产品与商业化研发。**

所有“完成”仍必须以源码 + 测试 + 运行 + Evidence 为依据。
