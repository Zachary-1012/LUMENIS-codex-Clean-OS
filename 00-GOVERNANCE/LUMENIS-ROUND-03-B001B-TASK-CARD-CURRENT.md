# ROUND-03-B001B — Protected candidate dependency map

> **Historical read-only task-card snapshot:** This former B001B proposal is retained as dependency evidence only. It is not the current task queue or authorization; current activation and Product Owner model/account/resource choices come only from `AGENTS.md`. This M-only preparation does not start its analysis or a code edit.

Status at the recorded snapshot: NEXT READ-ONLY TASK CARD. The current Owner Index and AGENTS control any future authorization.

| Field | Boundary |
| --- | --- |
| Base | Fetch `origin`; record current `HEAD`, `origin/main`, status, and exact diff before work. Current documented checkpoint is `d2149875` on `main`, with protected uncommitted candidates. |
| Job | Map the existing B001 candidate hunk by hunk to the Shared Database owner, its direct caller, or the adjacent Subject, Permission, Evidence, reporting, Collector, Product Core, and Experience owners. Identify the smallest dependency-closed next DB slice. |
| Read-only inputs | `database.py`, `canonical_data.py`, `lumenis/shared/database/{__init__,business_schema,migrations,scope}.py`, paired DB tests, and only the exact imports/callers needed to classify them. Root `AGENTS.md`, current Source Owner Index and ROUND 03 Charter govern. |
| Protected paths | `data/monitor.db`, `data/monitor.db-wal`, `data/monitor.db-shm` may be fingerprinted as files only; never SQLite-open, checkpoint, migrate, copy over, or remove them. No unknown work may be reset, cleaned, staged, overwritten, or moved. |
| Output | For each changed hunk: source path/line, canonical owner, behavior/contract, upstream and downstream dependency, whether independently buildable at current `origin/main`, and exact tests needed. Separate retained unique behavior from overlaps and mark unresolved dependencies `SPLIT`. Include base/final SHA, status, protected fingerprints, and no-commit/no-push declaration. |
| Stop rule | No implementation until Sol accepts a dependency-closed map and creates a new, exact allowed-file implementation card. B002 caller parity and B003 real-user E2E remain dependent on B001 acceptance. |

The current v14–v17 migrations, scope validator, root compatibility and canonical-data changes are candidate local work, not accepted production implementation. Do not classify by path alone or treat passing isolated tests as proof of Permission, Evidence or user acceptance.
