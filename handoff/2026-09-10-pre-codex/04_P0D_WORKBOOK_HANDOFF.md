# LUMENIS P0-D → PRE-PRODUCTION WORKBOOK HANDOFF

Source supplied by user: workbook titled `LUMENIS P0-D → PRE-PRODUCTION CODEX HANDOFF`.

Purpose: preserve the P0-D read-only audit/resume state in Git-readable form so Codex knows where the project stopped and which evidence already exists. This is not a claim that runtime or production acceptance passed.

## Workbook baseline recorded at audit time

- role: READ-ONLY AUDITOR + Evidence Builder + Closure Planner + Codex Handoff Planner
- local activity repo: `D:\LUMENIS_REBUILD\Z-Brand-Core`
- local branch snapshot: `integration/p0d-capability-recovery-v1`
- local HEAD snapshot: `2a3be0a` (`fix: isolate P0-C database migrations and tests`)
- workbook recorded dirty work including `app_evidence.py` plus P0-D audit/runtime evidence artifacts
- cached online canonical at audit time was older (`fc75d87`) and explicitly marked online latestness UNKNOWN because that audit did not fetch

Current package creation re-verified online `LUMENIS-codex-Clean-OS/main` at `ab67612367c172ced2dff62b44e98de86469d1e6`. Therefore Codex must treat the workbook's remote snapshot as historical and reconcile only the drift.

## Sheets

1. `00_导读与范围` — A1:B16
2. `01_基线与Drift` — A1:E18
3. `02_阻塞_DAG_Waves` — A1:E19
4. `03_DB路径隔离图` — A1:I39
5. `04_运行时_Route_前端` — A1:E71
6. `05_注册路由全量` — A1:C817 — workbook contains 815 runtime route rows plus headers/title context
7. `06_前端API引用全量` — A1:C182 — workbook records 180 distinct frontend API references plus headers/title context
8. `07_能力缺口矩阵` — A1:I39
9. `08_工单总板_P0D` — A1:Z24 — 22-ticket P0-D execution board plus title/header rows
10. `09_CarryOver_P0C` — A1:F18
11. `10_NO_GO_六Gate` — A1:D20
12. `11_证据矩阵_Git边界` — A1:D18
13. `12_Top10_ResumePack` — A1:C29
14. `13_源码证据索引` — A1:F37
15. `14_全文件可达性983` — A1:L985 — 983 Python-file reachability inventory plus title/header context
16. `15_未决_禁入_安全` — A1:C29

## Core blockers recorded in workbook

### BLK1 — P0 Blocking
DB path isolation not closed. The workbook records an in-flight `app_evidence.py` fix plus runtime-reachable hard-coded/by-pass DB paths that do not consistently obey the isolation contract. These must be re-verified against current source and resolved before trusted runtime verification.

### BLK2 — P0 Blocking
Real isolated server runtime was not proven. The workbook records test-client reachability but also 404s including `/api/runtime/identity` and `/lumenis/bmp/overview`. A Flask test client or page shell is not final runtime evidence.

### BLK3 — P0 Blocking
P0-C carry-over remained: Evidence parent empty-string→NULL behavior, canonical DB connection ownership, migration/Alembic relationship and full-suite isolation/failure closure.

### BLK4 — P1 Before RC
Runtime-registered routes versus static declarations had not been fully reconciled at blueprint-prefix/duplicate/fallback level. Workbook evidence differentiates real registered routes from static declaration counts.

### BLK5 — P1 Before RC
Evidence / Canonical / Metric ownership remained MULTIPLE/unsettled and requires KEEP/MERGE/ADAPTER/DEPRECATE-LATER decisions based on producer/consumer/runtime evidence.

### BLK6 — P1 Before RC
Local branch/governance drift and local-only in-flight work created a single-point risk. Current branch/HEAD state must be protected before implementation.

## Recorded dependency spine / waves

Workbook DAG starts with Git protection, then DB isolation, runtime, route/API/frontend truth, Evidence/Canonical ownership, capability convergence, security/recovery/governance, production acceptance, release/rollback and final audit. Subject Context implementation is deliberately deferred until DB/runtime serial blockers are closed; Developer Settings remains post-launch unless current governance explicitly changes.

## Important evidence inventories already present

- registered runtime route inventory
- frontend API reference inventory
- P0-D DB path/isolation map
- runtime/route/frontend evidence map
- capability gap matrix
- P0-C carry-over matrix
- six NO-GO gate matrix
- evidence/Git-boundary matrix
- Top-10 / Resume Pack
- source evidence index
- 983-file Python reachability inventory

Codex should reuse these only when their source HEAD still matches. If the canonical or work branch drifted, update only affected entries.

## PASS discipline from workbook

`file exists != pass`
`route declaration != pass`
`README says complete != pass`

Capability advancement requires appropriate source/call-graph + DB/API + tests + runtime + E2E/evidence. UNKNOWN and UNREACHED must remain explicit.

## Codex starting action

1. Verify current work branch, HEAD and dirty state.
2. Verify online canonical HEAD.
3. Protect any in-flight P0-D work.
4. Reconcile drift from this workbook snapshot to current source only.
5. Start the first dependency-valid DB-isolation/P0 ticket from the current ticket board.
6. Do not restart broad Subject Context/UI work inside unresolved DB/runtime P0 closure.
7. Do not claim Production Ready until all six gates in the master instruction pass.