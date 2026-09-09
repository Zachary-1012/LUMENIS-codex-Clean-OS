# B. Asset Coverage Matrix

说明：领域标签允许交叉，一个 Blob 可同时属于 Platform、Xiaohongshu、KOS、Evidence 等多个域。各域 Unique Blob 合计为 6,865，包含 1,416 次跨域重复标记，不能与全局去重后的 5,449 相加或比较。完整机器可读矩阵见 `_inventory/ASSET_COVERAGE_MATRIX.csv`。

| Domain | Path×Blob | Unique Blob | Current Exact | Same Path/Diff | No Exact | Historical-only | Semantic Pending |
|---|---:|---:|---:|---:|---:|---:|---:|
| AI / Agent | 1,741 | 909 | 529 | 140 | 240 | 372 | 171 |
| Data / Metrics | 199 | 101 | 43 | 30 | 28 | 78 | 0 |
| Decision Memory | 34 | 19 | 10 | 1 | 8 | 2 | 0 |
| Domain Methodology | 1,233 | 563 | 293 | 141 | 129 | 364 | 6 |
| Engineering | 2,991 | 1,342 | 987 | 164 | 191 | 411 | 90 |
| Evidence / Contract | 1,172 | 567 | 342 | 31 | 194 | 194 | 6 |
| Korean | 32 | 16 | 11 | 4 | 1 | 5 | 1 |
| KOS/KOL/KOC | 295 | 137 | 57 | 57 | 23 | 127 | 7 |
| Platform | 1,067 | 536 | 273 | 206 | 57 | 321 | 8 |
| Podcast | 132 | 61 | 45 | 5 | 11 | 17 | 0 |
| Regression Memory | 1,284 | 683 | 346 | 169 | 168 | 282 | 1 |
| UI / UX | 3,731 | 1,819 | 595 | 244 | 980 | 1,768 | 9 |
| Xiaohongshu | 267 | 112 | 64 | 43 | 5 | 86 | 0 |

优先复核域：UI/UX、AI/Agent、Engineering、Evidence/Contract。原因是 Pending 规模大或直接影响当前产品边界；优先不等于自动 Promotion。
