# LUMENIS — Current Codex Handoff (2026-09-13)

> Point-in-time takeover evidence for the **current local production workspace**. Current source/runtime/tests always outrank this file.
>
> This file supersedes the earlier remote-only blocker snapshot from the same date.

## 1. Canonical repository and local workspace

Remote repository:

```text
Zachary-1012/LUMENIS-codex-Clean-OS
```

Long-lived remote development truth:

```text
main
```

Current remote main observed before this handoff refresh:

```text
7cf0e8add51c4be32e4a50ab5c8be3434d252467
```

Canonical local production-development workspace on the current Windows machine:

```text
D:\LUMENIS_REBUILD
```

This path is a workstation locator, not a portable runtime requirement. On another machine, resolve the repository root with `git rev-parse --show-toplevel`.

## 2. Critical sync truth

The local workspace has progressed **beyond the earlier remote-only CI blocker snapshot**. Do not restart from the old remote blocker list.

Before changing code, compare:

```text
local HEAD / working tree / unpushed commits
vs
origin/main
```

Preserve valid local work. If local implementation is ahead of remote, converge that work into `main`; do not overwrite it with the remote tree.

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

Do not redo this work unless current source proves it was lost during convergence.

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

This is the current takeover point.

## 5. Immediate execution order

```text
A. Protect local work and establish local-vs-origin diff
B. Finish canonical production DB/config convergence
C. Verify the 3 reload/type/path identity repairs with targeted tests
D. Run final full regression
E. Prove protected production/candidate DB unchanged by tests
F. If 0 failed / 0 errors: close Cleanup phase permanently
G. Converge valid local commits/changes into latest main
H. Production startup / health / supervisor qualification
I. CTH / BMP / Shared Capability / SYSTEM critical E2E
J. Shared Capability × Collector closed-loop acceptance
K. Security / Recovery / Rollback
L. Release Candidate / Launch-Ready gate
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

## 9. Remote/main convergence

`main` remains the only long-lived remote development truth.

However, valid unpushed local production work in `D:\LUMENIS_REBUILD` must be preserved and converged into `main` before the remote tree can be considered current.

Do not let old remote code overwrite newer verified local fixes.

Convergence pattern:

```text
preserve local work
→ fetch latest origin/main
→ compare by content/contract/tests
→ adapt/resolve semantic conflicts
→ targeted regression
→ final full regression where required
→ coherent commits
→ push/merge to main
```

## 10. Next product phase after repository/test convergence

Once local and remote are synchronized and the full regression is green, immediately move to real product acceptance:

```text
Production Startup
→ /healthz
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

Do not remain in CI/test-infrastructure cleanup after this gate.

## 11. Completion semantics

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

## 12. Rules for the next Codex executor

- Start from `D:\LUMENIS_REBUILD` on this workstation.
- Verify repository identity before acting.
- Preserve valid local modifications and unpushed commits.
- Do not restart from the old remote-only blocker clusters unless current code/tests reproduce them.
- Do not redo branch archaeology; remote repository convergence is already complete.
- Do not rediscover historical local paths.
- Do not rerun full-suite tests after every leaf edit.
- Prefer `reuse → adapt → bind → verify`.
- Keep one DB truth, one Permission truth, one Evidence truth, one Runtime truth and one long-lived `main`.
- After final regression passes, immediately continue to production startup and E2E rather than continuing cleanup indefinitely.
- Clean CI alone never proves launch readiness.
