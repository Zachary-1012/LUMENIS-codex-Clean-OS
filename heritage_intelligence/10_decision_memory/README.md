# Decision Memory

用于保存产品与研发中的关键纠偏和长期不可回归规则。

统一结构：
- Decision ID
- Context
- Original Direction
- Observed Problem
- Evidence
- Correction
- Reason
- Final Decision
- Current Status
- Supersedes
- Do Not Regress

## DM-001 — Contract-first Business Tables

Context: 历史 KOS / DFS 数据呈现。

Original Direction: 先按页面/视觉设计业务表格，再补字段。

Observed Problem: 页面字段方向可能偏离真实业务研究与数据口径。

Correction: 业务表必须以经过研究和验证的 Contract / Metric Definition 为 Canonical，前端负责呈现，不自行创造业务字段。

Final Decision:
`Research / Evidence → Contract → Data Model → UI`

Do Not Regress:
禁止退回 `UI → 猜字段 → 补数据` 的开发方式。
