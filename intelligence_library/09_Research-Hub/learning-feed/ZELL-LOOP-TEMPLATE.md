# ZELL 闭环模板（Zachary Engineering Learning Loop）

> P0-C 施工资产：OSAI 研究侧 ZELL 闭环记录规范。每条闭环 = 一个真实任务，贯穿 9 阶段，
> 以全局唯一 `task_trace_id` 串联，产出可复跑的 Evidence 与可复用知识。
> 配套：`learning-feed/ZELL-INDEX.md`（闭环登记）· `osai_engine/metrics/engineering-metrics.jsonl`（工程度量）。

## 1. task_trace_id 规范（与 ZBC `scripts/zell_trace.py` 严格对齐）

- 格式：`ZELL-<seq>-<YYYYMMDD>-<kebab-slug>`
  - `seq`：全局递增序号（001, 002, …）
  - `YYYYMMDD`：任务发起日
  - `kebab-slug`：任务短名（小写，连字符）
- 示例：`ZELL-001-20260904-p0b-auto-reconcile`
- **双库同 ID 约定**：若任务跨生产（在 ZBC 侧有 trace），ZBC `scripts/zell_trace.py` 的 `begin <task>` 必须传入**同一 task_trace_id**；OSAI 闭环文档用同一 ID。禁止两套编号。
- **阶段映射**（OSAI 9 阶段 ↔ ZBC PHASES 8 阶段 + begin）：

  | OSAI 闭环阶段 | ZBC zell_trace.py |
  |---|---|
  | Issue | `begin <task>` 事件 |
  | Research | `phase <task> research <detail>` |
  | Architecture | `phase <task> architecture <detail>` |
  | Patch | `phase <task> code <detail>` |
  | Test | `phase <task> test <detail>` |
  | Runtime | `phase <task> runtime <detail>` |
  | Evidence | `phase <task> evidence <detail>` |
  | Evaluation | `phase <task> evaluation <detail>` |
  | Learning | `phase <task> learning <detail>`（完成时 `done <task> <outcome>`） |

- ZBC 侧已有自由文本 task（如 `P0C-001-...`）经 `scripts/zell_bridge.py` 只读反查并建议规范 ID，登记于 `learning-feed/ZELL-INDEX.md`（source=ZBC）。

## 2. 九阶段闭环记录模板

每条闭环文档 `learning-feed/ZELL-LOOP-<seq>-<slug>-<YYYYMMDD>.md` 必须包含以下 9 节：

| # | 阶段 | 必填内容 |
|---|---|---|
| 1 | Issue | 问题/需求来源（矩阵行 / 工单 / 用户指令），明确目标与完成判据 |
| 2 | Research | 依据的既有资产（reconciliation/contracts/learning-feed/开源范式），标注"复用不重造" |
| 3 | Architecture | 方案设计：涉及文件、接口、数据流、边界（不越权/不污染） |
| 4 | Patch | 实际变更：文件 + 增删行数 + commit；遵守最小变更 |
| 5 | Test | 验证方式与结果：单测/回归/静态检查/真实调用；含数字证据 |
| 6 | Runtime | 运行时核验：进程/端点/真实链路/健康状态 |
| 7 | Evidence | 证据落盘位置（research-inbox/*.md，commit id） |
| 8 | Evaluation | 效果评估：目标达成度、发现的问题、耗时、收益；**失败必须归因分层**——先判断是"规则/技能/设计内容错误"还是"执行时未遵循既有指导"（EmbodiSkill skill-aware reflection 原则），防无效重试 |
| 9 | Learning | 可复用知识：本任务沉淀的经验/教训/模式，供下一任务直接复用 |

## 3. 工程度量（P0-E）——每条闭环在 `engineering-metrics.jsonl` 追加一条

```json
{
  "task_trace_id": "ZELL-001-...",
  "ts": "2026-09-04T04:41:00",
  "domain": "reconciliation",
  "stage": "completed",
  "metrics": {
    "dev_minutes": 25,
    "regression_bugs": 0,
    "dup_code_lines": 0,
    "ai_useless_calls": 0,
    "test_cover_pct": 100,
    "self_heal": true
  },
  "method": {"raw": "git log + 源码核验", "normalized": "pct/min", "baseline": null, "sample_size": 1, "window": "2026-09-04"}
}
```

字段口径：
- `dev_minutes`：研发耗时（分钟）
- `regression_bugs`：本任务引入的回归 bug 数
- `dup_code_lines`：新建重复代码行数（复用优先，应≈0）
- `ai_useless_calls`：无效 AI 调用次数（如可规则解决却调 AI）
- `test_cover_pct`：覆盖度（新增能力被测试覆盖百分比）
- `self_heal`：任务产物是否自校验（True=产物自身可复跑验证）

## 4. 闭环索引

`learning-feed/ZELL-INDEX.md` 登记表：task_trace_id | 任务 | 状态 | Evidence | Learning 复用点。

## 5. 边界

- ZELL 闭环记录为 OSAI 研究侧资产；不修改 ZBC 生产代码（除用户显式授权）。
- task_trace_id 在 ZBC 侧仅作 request_id 复用约定，不新增日志基础设施。
- 每条闭环必须"真实任务 + 真实 Evidence"，禁止用假设任务填充。
