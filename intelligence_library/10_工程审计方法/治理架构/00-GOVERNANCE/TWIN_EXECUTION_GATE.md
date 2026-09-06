# 序境双子库 · Twin Execution Gate

## Purpose

This document defines the minimum gate for cross-repository work between Xujing-Core and Xujing-Intelligence.

## Boundary

- Core owns production truth, production data, collectors, runtime, reports, release and operational safety.
- Intelligence owns research, AI/Agent research, knowledge, evaluation, evidence and implementation specifications.
- Neither repository becomes the other's uncontrolled writer.
- No third core repository is created.

## Required mapping

Every new or changed capability must map to:

`Product → Subsystem → Module → Page → Function → API/Command → Data → Runtime → Policy → Evidence → Audit`

A capability without an owner, permission, runtime, policy or evidence path is not release-ready.

## Cross-repository flow

`Research → Evidence → Contract → Implementation Specification → Core Implementation → Test → Evidence → Audit → Release`

## Collector safety gate

Automatic collection is limited to the approved schedule: 00:00 and 12:00 daily, two runs per day, with an explicit enable/disable control. Other collection remains manual, with a 30-minute session limit. Legitimate account/API adapters are allowed only through an explicit policy boundary.

Any risk signal requires `STOP → COOLDOWN → HUMAN REVIEW`.

No new module may silently start a collector, create a new collection schedule, bypass an adapter/policy, or alter account/session safety controls.

### Authorized exception — TopicCampaign independent quota (2026-09-03, owner sign-off)

By explicit owner authorization (2026-09-03), the TopicCampaign module (topic_campaign.py) maintains an independent collection schedule as an approved exception to the daily 2-run limit above: fixed hours [9, 11, 13, 15, 17, 19] (6 runs/day, staggered 5-10 min), daily cap of 8 runs including manual, counted on its own counter and NOT consuming the main public-opinion quota. This exception applies only to TopicCampaign; the main public-opinion collector remains governed by the ShadowPlanner gate (dynamic decision, GAP-05 sign-off 2026-09-02). Any future change to this exception requires re-authorization by the owner.

## UI gate

Web, App and Mini Program are presentation surfaces over the same canonical capability model. Do not create separate business logic trees for each surface.

Use the shared Design Language: restrained typography, small line icons, clear hierarchy, responsive layout, accessible states and data-first visualization. No oversized logo/icon or poster-like module dominates a page.

## Agent orchestration decision（编排模式判据，2026-09-04, from P0 research Round 3, updated Round 4）

**当前基线（Round 4 源码审计确认）**：ZBC 当前处于**任务调度层，非多 Agent 编排**——
- `PlatformSchedulePlanner`（platform_adapters/scheduling/planner.py）：per-platform `ScheduleDecider` + `shadow_evaluate` 影子评估
- `v4_upgrade/ai_hub/shadow.py`：ShadowPlanner 建议表（add_suggestion → human decide），AI 建议门控，非编排器
- `Scheduler` / `TaskQueue` / `RecoveryTask`：任务调度/队列/恢复

即：单进程多任务调度 + AI 建议门控。本判据是**未来 Agent Council（多 Agent 编排层）的演进路线图**，不是当前状态描述。

**演进阶梯（不跳级）**：
1. **任务调度层（当前）**：多任务调度 + 建议门控，无需编排器
2. **Supervisor 编排（建立 Agent Council 时）**：hub-and-spoke，3-8 agent 确定性工作流，70% 生产首选；序境若建 Agent Council 从此起步
3. **Hierarchical（触发任一条件才升级）**：
   - agent 数量 > 6；
   - 出现需隔离的异质域（舆情 / 营销 / 合规 / 工程），每域独立 sub-orchestrator（Microsoft：层级核心价值=隔离，避免同域 worker 共享上下文污染顶层状态）；
   - 工作流跨域依赖上一步结果。

**Hierarchical 落地要点（Round 4 深化，E2/E3）**：
- **有向树 + 状态隔离**：通信仅 parent↔child；每个域 supervisor 拥有自己子树的 state（分层作用域状态隔离，Augment Code）；root orchestrator 路由到域 supervisor（如舆情/营销/合规/工程），每域 3-5 specialist workers
- **域自治闭环**：每个自治域保留独立闭环管理（IETF cross-domain agent architecture），Orchestrator 只做跨域任务分发/状态同步/进程调度，不干预域内执行
- **subagent 严格隔离**：subagent 仅 local memory/state、mission-scoped、用完即弃（SubAgenticAI FLA），防上下文污染父级
- **健康指标（可监控）**：supervisor 输出 token / workers 输出 token 比值健康区 **0.2-0.3**；>0.4 说明 supervisor 在做 worker 该做的推理（router 退化），需下放任务（channel.tel 2026）
- **实现参考**：LangGraph 多级=compile supervisor 嵌套 / subagents 模式（flatten 或 nest tool calls）；CrewAI hierarchical=manager 动态分配

未触发不升级；升级需 owner 签字 + Release Gate + 回归。当前 agent 化模块数量 ≈ 0（无自治多 Agent），距离阈值尚远，**不得提前引入编排复杂度**。

Source: P0-AGENT-ORG Research Map T1 (OSAI), E2/E3 (MetaCTO/QubitTool/Microsoft Learn/Augment Code/IETF/SubAgenticAI/channel.tel orchestration guidance 2026).

## Change rule

Zero Sequence is the governing change-control rule. Changes to product identity, twin-repository boundary, production-truth ownership, security rules or canonical naming require explicit authorization before execution.

## Evidence

Every production change must leave a traceable record of scope, owner, reason, test result and commit.

Status: ACTIVE
