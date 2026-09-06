# LUMENIS Task Contract — 序境任务契约（P0-04）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Intelligence OS / Shared Contracts
> 依据源码事实：`osai_engine/orchestrator.py` / `osai_engine/agent.py`

## 1. 目的
统一跨核（Production Core / Intelligence Core）的任务定义、登记、执行与验收，杜绝"口头任务无证据"。

## 2. 任务结构（Task Schema）
```json
{
  "task_id": "T-YYYYMMDD-xxxx",
  "title": "一句话任务",
  "owner": "WINDOW-A|WINDOW-B|WINDOW-C|HUMAN",
  "repo": "ZBC|OSAI|BOTH",
  "scope": "允许修改的文件/模块白名单",
  "forbidden": "禁止触碰的模块/数据/口径",
  "acceptance": "可验证的验收标准",
  "lifecycle": "DISCOVER",
  "evidence_ref": []
}
```

## 3. 规则
- 任务必须显式声明 `scope` 与 `forbidden`；未声明视为 UNKNOWN，禁止动手。
- 修改必须最小化：只改任务点名范围，不静默重构/删除/扩大。
- 每步执行必须追加 `evidence_ref`（文件/函数/测试/SHA 可回溯）。
- 任务状态：DISCOVER → REQUIREMENT → … → RELEASE（见 Lifecycle Contract）。

## 4. 验收
- 验收标准必须可执行（测试/命令/可观测输出），不写"应该可以"。
- 验收未过 = 任务未完成，必须如实记录 failed 原因，不得伪装 PASS。

## 5. 红线
- 未授权不得改 ZBC 业务规则、主体口径（subject_hit）、数据库事实、统计口径。
- 未授权不得 Merge/Push 到 main（见 Permission Gate Contract）。
