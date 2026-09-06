# LUMENIS Trace Contract — 序境追踪契约（P0-05）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Intelligence OS / Shared Contracts

## 1. 目的
所有 AI / Skill / Agent / Research / Engineering 行为可全链路追踪，形成 Decision Trace：
"为什么系统做了这个动作，可以一路查回来。"

## 2. 统一追踪链
```
Task → Requirement → Skill → Agent → Action → File → Function → Data
    → Test → Result → Evidence → Decision → Commit → Lifecycle
```

## 3. 追踪字段（每步必须携带）
- `ts`（时间戳）、`actor`（agent/human/skill）、`action`、`target`（文件/函数/数据）、
- `result`、`evidence_ref`、`sha_before` / `sha_after`、`lifecycle`。

## 4. 实现落点
- OSAI：`osai_engine/engineering_loop.py`（阶段机）+ `evidence/`（证据文件）+ `evidence/approvals.json`（批准痕迹）
- 后续：Trace 事件可进入统一 Trace Store（P2），本契约先保证"每个行为有记录"。

## 5. 红线
- 禁止无痕执行：任何修改必须可回答"谁、何时、改了什么、依据什么、如何验证"。
- 禁止伪造追踪：时间戳/结果必须真实，不得补造。
