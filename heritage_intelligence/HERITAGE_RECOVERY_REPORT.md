# A. LUMENIS Heritage Recovery Report

日期：2026-09-09
范围：知识资产回收；Production Runtime 零侵入

## 结论

本轮完成五仓全部可发现远程分支和可达提交的来源扫描，建立文件级谱系总账、当前等价分类、重复候选和 Pending Ledger。没有删除分支、旧文件或数据库；没有复制旧 Runtime、生产代码或生产数据进入纯净库；Promotion 数为 0。

## 真实统计

| 指标 | 结果 |
|---|---:|
| Repositories Scanned | 5 |
| Branches Scanned | 130 |
| Unique Branch-tip Commits | 51 |
| Reachable Commits Scanned | 2,986 |
| Files Inspected | 191,010 branch×file observations |
| Unique-tip File Observations | 70,246 |
| Knowledge Path×Blob Versions | 11,209 |
| Unique Knowledge Blobs / Assets Indexed | 5,449 |
| Text Blobs Read | 4,752 |
| Text Blobs Decoded | 4,750 |
| Decode Failures | 2 |
| Exact Duplicate Groups | 4,530 |
| Exact Duplicate Extra Versions | 5,760 |
| Normalized-content Duplicate Groups | 9 |
| Semantic Near-duplicate Candidates | 376（待人工核验） |
| Current Exact-equivalent Unique Blobs | 2,678 |
| Same-path Different-content Unique Blobs | 1,101 |
| No Exact Current Equivalent Unique Blobs | 1,670 |
| Pending Current-equivalent / Semantic Review | 2,771 |
| Promoted to Production | 0 |
| Production DB / Runtime Changes | 0 |

`Assets Verified` 不能用“当前存在相同 Blob”替代。2,678 只证明内容精确存在于当前纯净库，不证明业务、Runtime 或 Production 状态；Collection 级人工结论记录在 Registry，剩余项明确保持 Pending。

## 覆盖率

- 来源索引覆盖率：`5,449 / 5,449 = 100%`。
- 可读文本解码率：`4,750 / 4,752 = 99.96%`。
- 当前精确内容等价率：`2,678 / 5,449 = 49.15%`。
- 待当前等价或语义复核率：`2,771 / 5,449 = 50.85%`。

100% 只表示已发现唯一知识 Blob 均进入来源总账，不表示 100% 已验证、采用或上线。

## 证据文件

- `_inventory/ASSET_PROVENANCE_LEDGER.csv`：5,449 个唯一 Blob 的来源、分支、路径、SHA 与当前等价聚合。
- `_inventory/PENDING_VERIFICATION_LEDGER.csv`：2,771 个待验证条目。
- `_inventory/historical_asset_versions.csv`：11,209 个历史路径×Blob 版本。
- `_inventory/ASSET_COVERAGE_MATRIX.csv`：领域覆盖。
- `_inventory/history_compare/semantic_duplicate_candidates.csv`：376 个机器候选，不等于已确认重复。
