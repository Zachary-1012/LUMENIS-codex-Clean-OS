# Heritage Migration Status

本文件记录历史知识资产的回收与当前状态，不代表 Production Runtime 迁移。

| Area | Source | Status | Next Action |
|---|---|---|---|
| Korean / K-drama / Fansub / Translation / i18n | Z-Brand-Core research branches | INDEXED | 已完成 40 分支谱系与 16 唯一 Blob 索引；1 语义候选及模型许可待验证 |
| Historical Learning Registry | Z-Brand-Core docs/learning | VERIFIED | 映射全部 Research ID 到当前状态 |
| Platform Intelligence | Z-Brand-Core docs/research + intelligence_library | INDEXED | 536 唯一 Blob；按任务逐项核验时效、合规和当前等价 |
| KOS DFS tables & metrics | Z-Brand-Core audit/contracts/code/evidence | VERIFIED | 建立 Data Baseline + Contract-first Decision Memory |
| Podcast | Z-Brand-Core podcast/research/Research Hub | INDEXED | 61 唯一 Blob；Promotion 前验证授权、Entity、Evidence 与产品归属 |
| Evidence / Truth / Contracts | Z-Brand-Core + GGI + Command | INDEXED | 567 唯一 Blob；已标识精确等价，语义与 Runtime 等价待核验 |
| UI/UX Design Research | Z-Brand-Core learning/ui + governance | VERIFIED | 保留原则与采用/拒绝结论，剥离旧视觉强绑定 |
| AI / Agent Intelligence | Zachary-OS-AI | INDEXED | 909 唯一 Blob；只做知识回收，不回接历史 Runtime |
| Engineering Governance | lumenis-command | VERIFIED | 索引 Audit/ADR/Evidence/Verification/Boundary |
| Regression Memory | old tests/audits/evidence | INDEXED | 683 唯一 Blob；继续形成故障→根因→测试→防回归条目 |
| Decision Memory | audits/dev logs/contracts | INDEXED | 19 唯一 Blob；已提取主要被替代方向与 Do Not Regress |

## 2026-09-09 全量回收快照

- 5 repositories / 130 branches / 2,986 reachable commits
- 11,209 knowledge path×Blob versions
- 5,449 unique knowledge Blobs indexed
- 2,771 current-equivalent or semantic reviews pending
- 0 Production promotions / 0 Runtime changes / 0 database changes

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
