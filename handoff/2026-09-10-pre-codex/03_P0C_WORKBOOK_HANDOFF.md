# LUMENIS P0-C AUDIT WORKBOOK HANDOFF

Source supplied by user: workbook corresponding to `LUMENIS P0-C CODEX 审计交接清单`.

Purpose: preserve the P0-C audit structure and Codex resume meaning in Git-readable form. The original workbook is the source artifact; this Markdown records the verified workbook structure and key facts. Do not treat this summary as a replacement for source/runtime verification.

## Workbook scope

Identity recorded in workbook: READ-ONLY AUDITOR + CODEX HANDOFF PLANNER. It explicitly says it did not modify source/tests/DB/Git and did not run migration/full pytest during that audit pass.

Local audit baseline recorded by workbook:
- activity repo: `D:\LUMENIS_REBUILD\Z-Brand-Core`
- branch: `integration/p0c-test-migration-isolation-v1`
- HEAD at that audit snapshot: `79819ef18bcc127957c969acab1f5896c9ea8c6d`
- worktree snapshot: 12 modified + 8 untracked + 0 staged
- truth discipline: local worktree/diff/HEAD evidence outranks stale cached remote/docs; UNKNOWN must remain explicit

Later GitHub evidence confirms P0-C implementation was subsequently committed as `2a3be0ab2ef79cb0274c5b9a21114f3ce2e371af` (`fix: isolate P0-C database migrations and tests`). Therefore the workbook is a historical pre-implementation/hand-off audit snapshot and must be reconciled with current source before action.

## Sheets

1. `00_导读与范围` — A1:B18
2. `01_Git现场基线` — A1:D21
3. `02_FK根因_43_35_7` — A1:K26
4. `03_迁移链_v0_v12` — A1:L16
5. `04_CleanBootstrap三级Gate` — A1:F5
6. `05_连接FK策略矩阵` — A1:H10
7. `06_测试四分类` — A1:E34
8. `07_工单总板_57` — A1:U59 — 11 Epic / 57 Ticket board
9. `08_DAG与分级` — A1:C31
10. `09_Capability影响` — A1:E23
11. `10_Governance漂移` — A1:D11
12. `11_对话级Patch预览` — A1:E9
13. `12_未决与禁入` — A1:D17

## Key audited facts that must remain visible to Codex

### FK debt snapshot
The workbook distinguishes three key source/candidate DB debt counts rather than claiming FK clean:
- historical: 43 FK violations
- production candidate: 35
- clean-repo candidate: 7

Root-cause categories recorded include `content_generation_evidence.parent_evidence_id` empty-string/self-reference debt and `ai_task` orphan references. Exact source rows and decisions must be taken from current P0-C evidence/source before modification. Do not delete real historical data merely to reach zero.

### Migration truth rule
The workbook explicitly separates:
`MIGRATION_ONLY_PASS != APPLICATION_READABLE_PASS != RUNTIME_VERIFIED_PASS`.
A database reporting schema/version v12 alone is not Production PASS.

### Ticket board
`07_工单总板_57` is the P0-C resume planning board. Current Codex work must reconcile its 57 tickets with commit `2a3be0a`, current source and the newer P0-D board. Do not blindly replay tickets already implemented; classify each as CLOSED / IMPLEMENTED_BUT_UNVERIFIED / OPEN / SUPERSEDED / BLOCKED.

### No-fake discipline
The workbook explicitly requires unverified items to stay UNKNOWN / NEEDS EVIDENCE / NEEDS_CODEX_EXECUTION and forbids estimating or silently filling missing facts.

## Current reconciliation required before Codex action

Use this workbook as historical P0-C evidence, then compare against:
- commit `2a3be0a`
- current canonical `LUMENIS-codex-Clean-OS`
- current P0-D handoff
- current full-suite/runtime results

The known later P0-C implementation evidence recorded in GitHub includes focused `69 passed`, while full suite remained `4074 passed / 49 failed / 14 skipped / 1 error`. Therefore P0-C source implementation is not equivalent to whole-product verification.

## Codex instruction

Do not redo the P0-C audit from zero. Reconcile the 57-ticket board against current source and mark resolved/remaining items, then feed unresolved dependency-valid P0 items into the current master DAG.