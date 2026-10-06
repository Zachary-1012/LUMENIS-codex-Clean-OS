# LUMENIS local repair batch — CI triggers, Windows UTF-8, hang diagnostics, collector state — 2026-10-07

> Status: **PUBLISHED** with the mainline commit carrying this evidence file (Product Owner approved 2026-10-07).
> Base: local = origin/main = live `main` `751f442b59cd847cee19c0ea1b8f0be52697e005`.
> Scope: the six confirmed P0/P1 findings only; no product, owner, data or experience scope change.

## 1. Confirmed findings

1. **Hosted gates stopped running.** `platform-verify.yml` and `app-verify.yml`
   triggered only on `pull_request` and `workflow_dispatch`. After the last
   dispatch run on `373d846a`, 51 commits including `751f442b` had zero hosted
   gate runs.
2. **Windows code-page crashes.** On 2026-10-07 02:22:08 the startup preflight
   raised `UnicodeEncodeError: 'gbk' codec can't encode character '\u2713'`
   when printing its `✓` summary; older logs show the same class aborting the
   canonical migration on `📊`. The launcher already exported
   `PYTHONUTF8`/`PYTHONIOENCODING`, so the repair removes dependence on launcher
   inheritance.
3. **False-alive stalls.** Supervisor logged kills at 2026-10-06 16:26:07 and
   2026-10-07 02:21:50, with mid-stall recoveries at 17:31:14, 01:47:27 and
   02:05:13. Lifetime totals at inspection: 36 false-alive kills, 65 exit-1
   restarts. `[Stability] watchdog异常: 'errors'` reproduced a real KeyError.
4. **XHS circuit / tracked runtime state.** `schedule_state.json` showed
   `BLOCKED`, `consecutive_risk=3`, `in_recovery=true`; 69 consecutive
   `XHS session lost` warnings were logged 00:57–00:59. The file lives in the
   tracked source tree and is rewritten by the runtime.
5. **C5 local candidate.** The selected-preview-row → Canonical-child
   implementation remained uncommitted while CURRENT item 59 still described
   partial selection as rejected.
6. **Owned AI remains `NOT_BOUND`.** No zero-cost training chain has run; this
   is a resource-gated workstream, not a local patch.

## 2. Repairs in this candidate

- Added `push: branches: [main]` to both gates (App Gate keeps its path filter).
- `app.py`, `run_supervised.py` and standalone `runtime_preflight.py` force
  UTF-8 stdio with `errors="replace"` before any diagnostic output.
- `run_supervised.spawn()` passes `-X utf8` plus explicit
  `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` to every Core child.
- `app.py` enables bounded periodic all-thread faulthandler dumps (120 s) and a
  90 s no-completed-request stall dump into `logs/faulthandler.log`.
- `stability_monitor.py` initializes the `memory.errors` counter that caused
  `[Stability] watchdog异常: 'errors'`.
- The scheduling planner seeds once from the legacy tracked
  `lumenis/system/collector/data/schedule_state.json` and persists runtime state
  to the ignored `data/runtime/collector/schedule_state.json`; the legacy file is
  preserved as migration/history input.
- No change to the XHS session/guard/risk logic: read-only status at 03:08
  showed `session_ok=true`, `heartbeat_fails=0`, `resident_mode=RESIDENT_ACTIVE`,
  CDP 9223 reachable (Edge/155). The 69-fail streak ended with the 02:22 restart.

## 3. Local verification

- `py_compile` PASS for every edited Python file; workflow YAML parses.
- `runtime_preflight.py` run with `PYTHONIOENCODING=gbk` and redirected stdout:
  exit 0, zero `UnicodeEncodeError`, summary prints `✓` (`logs/_preflight_gbk_check.out`).
- Supervisor spawn capture: args include `-X utf8`; env carries
  `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.
- Scheduling path check: planner state file resolves to
  `data/runtime/collector/schedule_state.json`; `git check-ignore` matches
  `.gitignore:120`.
- Stability check: `_check_all_modules()` completes; `memory.errors=0`.
- `pytest tests/test_saved_document_workflow.py tests/test_markitdown_importer.py
  tests/test_openapi_spec.py` on an OS-temporary seed: 57 passed, 2 skipped,
  no background-thread leaks.
- Gates: AI-native constitution PASS; Codex takeover governance OK; database
  authority PASS; Only-One/multi-surface PASS; current configuration PASS.
- Runtime read-only: `/healthz` 200 (database ok), Runtime Guardian healthy,
  `GLOBAL_ALL` identity.

## 4. Limits

- False-alive root cause remains UNVERIFIED; the next occurrence must produce
  the new faulthandler/stall dumps before the supervisor kills the tree.
- The XHS 69-fail episode is pre-restart evidence; current session is healthy.
- Owned AI stays `UNAVAILABLE / NOT_BOUND`; the zero-cost training chain needs
  an actually available GPU resource and its own authorized run.
- Publication is the commit/push carrying this file; this batch performed no
  runtime restart, deployment, production-DB write, model/GPU execution or
  external effect.
