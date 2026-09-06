# LUMENIS Evidence Contract — 序境证据契约（P0-06）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Intelligence OS / Shared Contracts
> 依据源码事实：`osai_engine/evidence.py`（既有证据记录）

## 1. 目的
任何结论/决策/变更必须能追溯到证据（文件、函数、测试、SHA、Lifecycle）。

## 2. 证据链
```
Research → Evidence → Finding → Internal Proposal → Human Review → Implementation
```
外部研究禁止直接进 Core：必须先 Evidence，再 Finding，经 Human Review 才实现。

## 3. 证据记录字段
```json
{
  "round_id": "YYYYMMDD-HHMMSS",
  "task": "任务描述",
  "repo": "ZBC|OSAI",
  "stages": [{"stage": "...", "status": "ok|warn|failed|denied|skipped", "detail": "..."}],
  "result": "ok|failed|awaiting_approval|skipped",
  "git_sha": "前12位",
  "llm_calls": 0
}
```

## 4. 规则
- ACTIVE 状态必须带时间戳健康/集成证据（provider/model/endpoint/result/失败原因，无密钥）。
- 失败必须显式：禁止把失败静默成 0 条 / PASS。
- 密钥、Token、Cookie 不得进入证据、日志、Git。

## 5. 落点
- OSAI `evidence/`（每次回合一个证据文件）+ `approvals.json`（权限痕迹）
- ZBC 证据体系沿用既有 `evidence_store.py`，本契约统一字段语义。
