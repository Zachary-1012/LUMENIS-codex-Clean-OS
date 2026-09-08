# Heritage Migration Status

本文件记录历史知识资产的回收与当前状态，不代表 Production Runtime 迁移。

| Area | Source | Status | Next Action |
|---|---|---|---|
| Korean / K-drama / Fansub / Translation / i18n | Z-Brand-Core research branches | DISCOVERED | 分支级去重、提炼统一 Collection、建立文件级索引 |
| Historical Learning Registry | Z-Brand-Core docs/learning | VERIFIED | 映射全部 Research ID 到当前状态 |
| Platform Intelligence | Z-Brand-Core docs/research + intelligence_library | DISCOVERED | 按平台拆分，补平台机制/指标/合规/采集/案例索引 |
| KOS DFS tables & metrics | Z-Brand-Core audit/contracts/code/evidence | VERIFIED | 建立 Data Baseline + Contract-first Decision Memory |
| Podcast | Z-Brand-Core podcast/research/Research Hub | DISCOVERED | 汇总 Research→Entity→Intelligence→SOP→UI Data |
| Evidence / Truth / Contracts | Z-Brand-Core + GGI + Command | DISCOVERED | 跨仓语义去重，标识 Current Equivalent |
| UI/UX Design Research | Z-Brand-Core learning/ui + governance | VERIFIED | 保留原则与采用/拒绝结论，剥离旧视觉强绑定 |
| AI / Agent Intelligence | Zachary-OS-AI | DISCOVERED | 提炼 Architecture/Memory/Learning/Evaluation/Policy |
| Engineering Governance | lumenis-command | VERIFIED | 索引 Audit/ADR/Evidence/Verification/Boundary |
| Regression Memory | old tests/audits/evidence | DISCOVERED | 形成故障→根因→测试→防回归条目 |
| Decision Memory | audits/dev logs/contracts | DISCOVERED | 形成纠偏记录和 Do Not Regress 规则 |

## Status meanings
- DISCOVERED: 已确认资产族存在，尚未完成文件级去重与完整索引
- INDEXED: 已建立文件级索引
- VERIFIED: 已核验来源与用途
- DEDUPED: 已完成重复/镜像/同步副本识别
- PROMOTED: 已提升为当前可复用知识基线
- REFERENCE_ONLY: 仅供参考，不应驱动当前实现
- SUPERSEDED: 已有当前版本完全替代，但保留历史关系
- ARCHIVED: 历史归档
- REJECTED_WITH_REASON: 明确不采用且保留原因

## Hard rule
任何 `DISCOVERED` 资产都不能被视为“已完整迁移”。完成状态必须有 Source Repo + Branch + Path + SHA + Current Equivalent 证据。