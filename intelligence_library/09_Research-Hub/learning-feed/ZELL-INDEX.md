# ZELL 闭环索引（Zachary Engineering Learning Loop Index）

> 登记所有 ZELL 闭环。每条闭环 = 真实任务，9 阶段贯穿，`task_trace_id` 全局唯一。
> 模板见 `learning-feed/ZELL-LOOP-TEMPLATE.md`；ZBC 侧 trace 经 `scripts/zell_bridge.py` 只读对齐。

## OSAI 研究侧闭环（source=OSAI）

| task_trace_id | 任务 | 状态 | Evidence | Learning 复用点 | 日期 |
|---|---|---|---|---|---|
| ZELL-001-20260904-p0b-auto-reconcile | P0-B Capability↔源码自动对账 | ✅ 完成 | AUTO-RECONCILE-P0B-20260903.md | skills-registry 目录省略解析/符号抽样/只读对账姿势 | 2026-09-04 |

## ZBC 生产侧 trace 任务（source=ZBC，经 zell_bridge 反查登记）

| ZBC task（自由文本） | 建议规范 ID | 状态 | 说明 |
|---|---|---|---|
| `P0-B/P0-C/P0-D` | ZELL-002-20260904-p0-b-p0-c-p0-d | 🟡 进行中 | Capability Registry + ZELL Trace + Observatory 数据源（并行线） |
| `P0-A~E 今夜闭环` | ZELL-003-20260904-p0-a-e | ✅ done | 全量回归 EXIT=0，382+ 基线 |
| `P0C-001-backlog-reconciliation` | ZELL-004-20260904-p0c-001 | ✅ done | backlog 对账 |
| `P0C-002-daily-report-golden` | ZELL-005-20260904-p0c-002 | 🟡 进行中 | 日报 Golden 数据 |
| `P0C-003-ai-gateway-fix` | ZELL-006-20260904-p0c-003 | 🟡 进行中 | AI 网关修复 |
| `P0C-004-collector-dual-time` | ZELL-007-20260904-p0c-004 | 🟡 进行中 | 采集双时间 |
| `P0C-005-ui-design-consistency` | ZELL-008-20260904-p0c-005 | 🟡 进行中 | UI 设计一致性 |

---

## 闭环推进规则
- 新闭环：先在本表登记，再写 `ZELL-LOOP-<seq>-<slug>-<YYYYMMDD>.md`，最后追加工程度量。
- 双库同 ID：跨生产任务须在 ZBC `zell_trace.py` 用同一 task_trace_id（`begin/phase/done`），OSAI 闭环文档同步。
- 复用优先：新任务必须引用相关旧闭环的 Learning 复用点（防重复劳动）。
- ZBC 侧新增 trace 任务：运行 `python scripts/zell_bridge.py` 重生成对齐报告并更新本表。
