# J1 — existing public maintenance runtime upgraded

Status: **PINNED RUNTIME UPDATED / REAL SCHEDULED EVALUATION VERIFIED**.
J1 remains PARTIAL. No Global coverage, full operation, Round or release acceptance.

The existing `LUMENIS-Prelaunch-Maintenance-5m` task used an extracted `55b90b3c`
source archive. A bounded dependency comparison confirmed its examined files
matched that commit. It lacked the later scheduler handling of a verified
`NO_NEW_DATA` outcome: an unchanged refresh could be misclassified as failure.
This is not a new scheduler or a change to end-user MANUAL/AUTO policy.

## Upgrade and recovery

- Created a fresh Git archive of accepted `3d6e0924dd883a23616ba2f63a01962e10b76e1e`
  outside the product checkout. Verified all 2,676 extracted files against it.
  Archive SHA-256: `c602b38d56cbd79813f31c746f66291147546d45ced4fc84176cb706a9baeb03`.
- SQLite online backup preserved a WAL-consistent rollback copy in ignored
  `data/private/maintenance-upgrade-6ithkrvh/monitor-rollback.db`; schema 18,
  integrity ok and zero foreign-key violations. A separate disposable copy was
  used for the archived runner's isolated invocation; exit 0, 195 not due.
- Saved the existing task XML; retained the old archive. Changed only its
  `CommittedSourceRoot` action argument. Verified executable, arguments, working
  directory, triggers, principal and settings. The task is enabled.
- The first update attempt rejected an absent optional working directory before
  the action was changed; the original action/enabled state was restored. The
  retry omitted that optional argument and passed exact configuration checks.
  Rollback is restoring the saved action and old archive, not restoring business
  data or deleting the current database.
- At **2026-09-30 00:06:02 +08**, the actual task ran the new pinned runtime;
  its 00:06:17 safe log returned COMPLETED/exit 0, 195 deferred, zero due,
  zero succeeded/failed. This is a real scheduled evaluation, not 195 fetches.

## Source state and limits

The signed `prelaunch-public-baseline-20260928-v2` plan was READY: 195 sources,
12 daily, 82 weekly and 101 monthly. Read-only history held 207 successes and
117 historical failures. The latest inspected actual success was 2026-09-29
13:06:14 +08; a historical Pampers RATE_LIMITED outcome subsequently recovered
at 13:06:09. The next inspected due source is Le Labo's official Violette 30
page at 2026-09-30 10:24:38 +08. These observations do not claim a future run
has happened. An immediate second due-only invocation correctly defers it.

The plan, private service settings, source authorizations and cadence were not
changed. No account, Cookie, personal browser, production migration, data purge
or forced recrawl was used. Coverage and source quality remain separately
qualified. End-user AUTO remains off unless explicitly enabled.

## REAL DELIVERY CARD / 真实用户工作闭环验收

Job: the product checks its approved public baseline independently of Codex,
refreshes only due sources and reports actual failures/no-change states.
Entry: existing installed maintenance task. Input: signed public plan and the
actual product DB. Result this Batch: current runner installed and one real
scheduled evaluation; no source was due. Evidence: archive verification, private
task XML backup, SQLite backup checks and safe scheduled log. Recovery: prior
action/archive retained and restoration executed during the rejected first
update. Two real source refreshes, downstream freshness display and complete
J1 acceptance are not replaced by this idle evaluation.

GLOBAL UNIVERSE / DATA MATURITY IMPACT: Global Commercial Coverage and Global
Brand Coverage remain NO / NOT VERIFIED; Taikoo Hui depth PARTIAL.
FULL_UNIVERSE_READY, RELEASED, OPERATING and COMMERCIAL_READY remain NO.
CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: reuse the existing signed,
due-only owner and accepted no-change semantics; no dependency added.
COMMERCIAL OVERLAY IMPACT: scheduling proof does not grant source data rights.
