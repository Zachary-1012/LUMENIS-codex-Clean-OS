# LUMENIS — Current Codex Handoff (2026-09-13)

> Point-in-time takeover evidence for the **current local production workspace**. Current source/runtime/tests always outrank this file.
>
> This file supersedes earlier remote-only blocker snapshots from the same date.

## 1. Canonical repository and local workspace

Remote repository:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

Long-lived remote development truth:

```text
main
```

Canonical local production-development workspace on the current Windows machine:

```text
D:\LUMENIS_REBUILD
```

This path is the only active local LUMENIS workspace on the current machine. It is a workstation locator, not a portable runtime requirement. On another machine, resolve the repository root with `git rev-parse --show-toplevel`.

## 2. Mandatory local-to-main sync gate

The local workspace has progressed beyond the earlier remote-only CI blocker snapshot.

Therefore the first action of the next Codex session is **not** to restart from remote blockers and **not** to pull/reset over the local tree.

First establish:

```text
LOCAL HEAD
LOCAL working tree
LOCAL unpushed commits
vs
origin/main
```

State must be classified as one of:

```text
LOCAL_EQUAL
LOCAL_AHEAD_VALID
REMOTE_AHEAD
DIVERGED_NEEDS_SEMANTIC_CONVERGENCE
UNKNOWN
```

If valid local implementation is ahead of remote:

```text
preserve local work
→ fetch latest main
→ compare by source/contract/test
→ adapt/resolve semantic conflicts
→ targeted regression
→ required full regression
→ coherent commit(s)
→ converge into main
```

Do **not** overwrite verified local fixes with the remote tree.

Until this comparison/convergence is complete:

```text
REMOTE_CODE_CURRENT = NOT VERIFIED
SYNC_REQUIRED = YES
```

Once valid local production/test fixes are represented in latest `main` and the working tree/commits are reconciled:

```text
SYNC_REQUIRED = NO
main = current remote production-candidate truth
```

## 3. Local work already completed — do not rediscover

The previous Codex session on `D:\LUMENIS_REBUILD` already completed the following:

- limited cleanup only to LUMENIS-related duplicates/cache/temp assets proven unused by dependency, Git, database and runtime checks;
- no deletion of Windows, Program Files, user profile data, business spreadsheets, WeChat data or unrelated personal/system data;
- FlClash/system proxy facts established for Git connectivity: `127.0.0.1:7890`; Git local proxy/HTTP 1.1 was configured and GitHub push was verified;
- full-suite isolation diagnosis proved that many previous failures came from forcing all modules onto an empty DB before pytest collection;
- session-level temporary database copies and temporary output paths were introduced so tests do not write the protected candidate database or repository staging paths;
- old hard-coded `D:\Taikoo-monitor-new` test paths were removed from affected tests;
- a focused isolation regression of 119 tests passed with protected database SHA-256 unchanged;
- full suite improved from `89 failed + 5 errors` to `62 failed + 0 errors` after isolation fixes;
- missing ad prediction/feature-engineering implementation was added as a deterministic, explainable, read-only enhancement layer;
- AI provider fatal authentication/parameter failures were changed to stop invalid fallback attempts;
- Cookie tests were changed to explicit `MISSING`/valid-structure semantics instead of requiring sensitive credentials in the repository;
- credential/data-boundary false positives for naming configuration and redacted reports were corrected without weakening real Cookie/Token/DB/private-key protections;
- the second full regression reached:

```text
4120 passed
3 failed
15 skipped
0 errors
```

- the final 3 failures were diagnosed as Python module reload type/path identity drift rather than product-domain behavior failures;
- those three were repaired through serialized/public contract semantics and module-owned/canonical database-path handling.

Do not redo this work unless current local source proves it was lost.

## 4. Exact continuation point

The previous Codex session stopped while entering this step:

```text
canonical production DB/config convergence
→ backup the protected canonical data path
→ point production config to the single protected path
→ remove/isolate the ignored repository DB copy polluted by old tests
→ verify no silent fallback to stale/duplicate DB paths
→ rerun targeted identity regressions
→ run final full regression
```

This is the current takeover point **after** the local-to-main sync assessment.

## 5. Immediate execution order

```text
A. Start at D:\LUMENIS_REBUILD
B. Protect local work and establish local-vs-origin diff
C. Preserve/converge valid local work without resetting it
D. Finish canonical production DB/config convergence
E. Verify the 3 reload/type/path identity repairs with targeted tests
F. Run final full regression
G. Prove protected production/candidate DB unchanged by tests
H. If 0 failed / 0 errors: close Cleanup phase permanently
I. Ensure all valid local implementation is in latest main
J. Start the production system
K. Verify /healthz + supervisor + core runtime
L. Run CTH / BMP / Shared Capability / SYSTEM critical E2E
M. Run Shared Capability × Collector closed-loop acceptance
N. Security / Recovery / Rollback
O. Release Candidate / Launch-Ready gate
```

## 6. DB/config hard rules

Use one canonical DB-path owner. Do not create another resolver.

Tests/staging must remain isolated/disposable and must never silently fall back to the protected production/candidate DB.

Before removing any DB copy, prove:

```text
identity
hash
schema
row-count relevance
Git status/history relevance
runtime references
configuration references
```

Only delete/move a LUMENIS DB copy when it is proven to be a polluted/duplicate/test artifact and the canonical protected path is backed up and verified.

## 7. Final full-regression gate

After the targeted identity regressions pass, execute the same official full-suite entrypoint used for the `4120 / 3 / 15 / 0` run.

Required result:

```text
FAILED = 0
ERRORS = 0
```

All skips must be explicitly classified as expected online/platform/environment conditions; no unknown skip is acceptable.

Do not obtain green by deleting tests, weakening assertions, adding broad skips, expanding environment exclusions, or using `continue-on-error`.

## 8. After full green — stop cleanup

When final regression is genuinely green:

```text
CLEANUP_PHASE = CLOSED
```

Do not resume old-path archaeology or duplicate-repository cleanup unless new evidence proves a concrete production problem.

Create a clean production baseline recording at least:

```text
HEAD
branch
canonical DB identity/hash
configuration identity
full-regression result
```

## 9. Mainline convergence

`main` is the only long-lived remote development truth.

No valid production implementation may remain only in a local-only commit or a long-lived side branch.

Convergence pattern:

```text
preserve local work
→ fetch latest origin/main
→ compare by content/contract/tests
→ adapt/resolve semantic conflicts
→ targeted regression
→ full regression where required
→ coherent commits
→ push/merge to main
→ verify local-vs-main equivalence for the completed work
```

Do not force-push `main`.

## 10. Production startup is mandatory after green regression

Once local/remote are synchronized and the final full regression is green, immediately start the real local production candidate:

```powershell
Set-Location D:\LUMENIS_REBUILD
powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
```

Expected core health endpoint:

```text
http://127.0.0.1:8201/healthz
```

Qualification chain:

```text
Production Startup
→ /healthz
→ supervisor stability
→ Runtime / Scheduler / Evidence / Permission / AI Gateway
→ CTH E2E
→ BMP E2E
→ Shared Capability E2E
→ SYSTEM E2E
→ Shared Capability × Collector closed loop
→ Security
→ Recovery
→ Rollback
→ Release Candidate
```

Do not remain in CI/test-infrastructure cleanup after the regression gate.

External browser/platform login availability must be reported separately from core application health.

## 11. User-operable completion rule

A feature is not complete because a page, route or test exists.

For important user-operable capabilities prove:

```text
UI Entry
→ User Action
→ API / Service
→ Permission
→ Canonical Read/Write
→ Real Result
→ Evidence / Trace
→ Honest Error State
→ Automated Test
→ E2E
```

## 12. Completion semantics

```text
IMPLEMENTED = code exists
TESTED      = scoped automated tests pass
VERIFIED    = runtime/E2E proves behavior
RELEASED    = production/security/recovery/rollback gates pass
OPERATING   = real operation produces required live evidence
```

Until production startup, domain/closed-loop E2E, security, recovery and rollback are all evidenced:

```text
PRODUCTION_READY = NO
RELEASED = NO
OPERATING = NO
```

## 13. Rules for the next Codex executor

- Start from `D:\LUMENIS_REBUILD` on this workstation.
- Verify repository identity before acting.
- Preserve valid local modifications and unpushed commits.
- Perform the local-to-main sync assessment before new feature work.
- Do not restart from old remote-only blocker clusters unless current local code/tests reproduce them.
- Do not redo branch archaeology.
- Do not rediscover historical local paths.
- Do not rerun the full suite after every leaf edit.
- Prefer `reuse → adapt → bind → verify`.
- Keep one DB truth, one Permission truth, one Evidence truth, one Runtime truth and one long-lived `main`.
- After final regression passes, start the system and continue through runtime + E2E; do not stop at green tests.
- Clean CI alone never proves launch readiness.
