# LUMENIS Lifecycle Contract — 序境生命周期契约（P0-08）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Intelligence OS / Shared Contracts

## 1. 统一生命周期（最高标准）
```
DISCOVER → REQUIREMENT → RESEARCH → EVIDENCE → DECISION → ARCHITECTURE
    → IMPLEMENT → TEST → VERIFY → RELEASE → OPERATE → MONITOR
    → LEARN → IMPROVE → RETIRE
```

## 2. 适用范围
所有任务、Skill、Agent、功能、组件、契约、产品 Release 统一采用。

## 3. 工程域映射（Engineering Loop）
```
INSPECT → PLAN → EXECUTE → VERIFY → REPAIR(≤2) → VERIFY
    → EVIDENCE → EVALUATE → HUMAN_APPROVAL → COMMIT → PUSH
```
- REPAIR 硬上限 2 次：禁止无限 Engineering Loop（红线⑦）。
- COMMIT/PUSH 不在 Agent 自主 Loop 内：必须 Permission Gate（红线⑥）。

## 4. 状态机纪律
- 任何 Agent 不得跳过关键阶段（如无证据直接 COMMIT）。
- 阶段迁移必须可追溯（谁、何时、依据）。
- RELEASE 前必须双 QA（Visual QA + Functional QA）。

## 5. 落点
- `osai_engine/engineering_loop.py`（工程域阶段机）
- 统一 Lifecycle Tracker（S53）为治理 Skill 入口。
