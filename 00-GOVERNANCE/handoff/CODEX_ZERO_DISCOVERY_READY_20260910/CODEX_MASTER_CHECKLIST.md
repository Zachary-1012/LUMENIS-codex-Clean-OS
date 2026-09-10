# CODEX MASTER CHECKLIST — GitHub text index

The source Excel workbook has 13 sheets. For Git/Codex efficiency, the workbook is represented by this index plus the JSON truth files in the same directory. No binary XLSX is required for Codex execution.

| Sheet | Rows | Canonical Git text source |
|---|---:|---|
| 00_总览导航 | 16 | CODEX_START_HERE.md / CODEX_RESUME_PACK.json |
| 01_指令覆盖矩阵 | 56 | CODEX_START_HERE.md + CODEX_ONLINE_VERIFICATION_20260910.md |
| 02_五仓Baseline | 7 | CODEX_FIVE_REPO_RELATIONSHIP_MAP.json |
| 03_Canonical能力37 | 38 | CODEX_CROSS_REPO_CAPABILITY_DIFF.*.json |
| 04_DB连接地图 | 302 | CODEX_DB_CONNECTION_MAP.part*.json |
| 05_测试失败矩阵60 | 61 | CODEX_TEST_FAILURE_MATRIX.part*.json |
| 06_Codex工单40 | 41 | CODEX_TICKETS.part*.json (updated to 41 after RUNTIME-ENTRY-1) |
| 07_依赖DAG | 62 | CODEX_DEPENDENCY_DAG.json |
| 08_ProductionTruth | 18 | CODEX_PRODUCTION_TRUTH_MAP.json |
| 09_Runtime路由 | 10 | CODEX_RUNTIME_MANIFEST.json / CODEX_ROUTE_CONTRACT_MATRIX.json |
| 10_Subject_UI_Sec_Env | 16 | SUBJECT/UI/SECURITY/ENV files |
| 11_能力找回队列 | 31 | CODEX_CROSS_REPO_CAPABILITY_DIFF.capability_recovery_queue.part*.json |
| 12_Gate与回传状态 | 12 | CODEX_RESUME_PACK.json / CODEX_START_HERE.md |

## Supersession
- Workbook field `GIT-001=UNKNOWN/BLOCKED` is superseded: GitHub online compare verified fc75d879→ab676123 is documentation-only; GIT-001 is CLOSED_VERIFIED.
- Any workbook/runtime field treating `run_production.py:8200` as canonical is superseded: online source proves canonical launcher is `scripts/start_production.ps1` → `run_supervised.py --port 8201`; its hard-coded old root is ticket RUNTIME-ENTRY-1.
- Original workbook remains an audit artifact in the local ZIP; Git source-of-truth for Codex is the text package here.

## Why split files
Large matrices are intentionally split into small JSON parts so Codex can load only the exact ticket/test/DB/capability evidence it needs. This is lossless at the row level and avoids spending context/compute on unrelated evidence.