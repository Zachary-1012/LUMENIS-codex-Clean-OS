# FINAL_CODEX_EXECUTION_REPORT — Experience Blueprint → Production Wiring

- Date: 2026-09-13
- Branch: `codex/production-experience-wiring`
- HEAD: `edf6d2b8fa08d00d1e8a90cdb3e73925e1a97a19`
- Base: `origin/main` @ `49c325f` (PR#1 `handoff/frontend-gpt-v24-20260911-codex-ready`) — **fully merged, 0 behind / 10 ahead**
- Scope: ONE-SHOT — turn Experience V2 blueprint into runnable Flask production
  wiring reusing the existing stack (no React/Vue rewrite, no second design system).

## Headline result

| Item | Result |
|---|---|
| AI-01 | **PASS** — real conversation/evidence/gateway/permission-context binding; composer POST runs the real `skill_execution_chain` |
| CTH-01 | **PASS** — real subject→events/risks/canonical/daily-report binding |
| Screens migrated | **38 / 44** real backend-bound builders (36 in `experience_screens.SCREEN_BUILDERS` + CTH-01/AI-01 in `experience_runtime`) |
| Backend binding rows | **42 BOUND / 3 INTENTIONALLY_NOT_APPLICABLE / 9 BLOCKED-rows** (`unknown-bindings.json`) |
| Actions bound | **66 / 66** concluded in `ACTION_REGISTRY.json` (no UNBOUND/UNKNOWN left) |
| Prototype/mock remaining | **4 screens with real external gaps + 2 empty placeholder slots** (honest, not faked) |
| Remote integration | **DONE** — two remote merges integrated cleanly (`f1eb53b`, `edf6d2b`); backups `backup/pre-remote-merge-20260913`, `backup/pre-remote2-merge-20260913` |
| PRODUCTION_READY | **NO** — see blocking list |

## 44-screen terminal classification

- **38 bound (real read-only production sources):** CTH-01..10 (10), AI-01..05 (5),
  SYS-01/02/03/04/05/07/08 (7), SH-02/03/04/05/06 (5), ACC-02/03 (2),
  BMP-01/02/03/04/06/07/08/09/10 (9).
- **4 BLOCKED_BY_EXTERNAL_DEPENDENCY (real gaps, kept honest — no fake data):**
  - `BMP-05` 创作者 KOS — `kos_engine.get_kol_tier_summary(authors, config)` needs an
    `authors` input; no zero-arg read source exists.
  - `BMP-11` 对标竞品 — no read getter exists in the production source.
  - `SH-01` Content Studio — write-heavy composer; write actions are not implemented.
  - `SYS-06` 内部浏览器 — security-sensitive (CDP/browser session); deliberately not surfaced.
- **2 INTENTIONALLY_NOT_APPLICABLE:** `ACC-01`, `ACC-04` are `chrome=none` empty
  placeholder slots (no title/desc/data contract), not deliverable screens.

## Gate results (evidence-based; no result without a real run)

| Gate | Result | Evidence (post-merge HEAD `edf6d2b`) |
|---|---|---|
| G1 Repository/Source | PASS | two remote PRs merged with zero production-overlap conflicts; single frontend/contract stack; tracked tree clean; 0 behind / 10 ahead |
| G2 Backend — API | PASS | full app imports & serves on isolated 127.0.0.1:8211; **7 `/experience` routes**; real HTTP 200 on identity/subjects/8 sampled screens |
| G2 Backend — DB | PASS | every builder calls a real zero-arg read source via canonical `database.get_db()` / module getters; isolated TEMP DB |
| G2 Backend — Evidence | PASS | composer POST → real `run_execution_chain` → `execution_id`, `status=completed`, `evidence_recorded=true`, `ai_is_derivative=true`; evidence pills/lineage rendered; no CoT/system-prompt/cookie/CDP leak |
| G2 Backend — Permission | PARTIAL | backend `permission_gate` exists; composer honors domain/context; **per-screen write-action→permission→approval POST chain not exhaustively exercised** |
| G2 Backend — Metrics | PASS | canonical/daily_report/evaluation/propagation metrics read live; UI never recomputes; 0/NULL/UNKNOWN distinguished (e.g. BMP-03 missing table → `value=None`+`notcollected`, never fake 0) |
| G3 Frontend — reachable | PASS | robust CDP sweep (waits for `[data-screen=id]` match) of **all 38 bound screens, dark 1440 AND light 1440**: every screen `match=true`, `data-source=runtime`, **0 overflow / 0 undefined / 0 prototype-banner / PAGE_ERRORS=[]** |
| G3 Frontend — light/dark | PASS | black-silver light + white-silver dark; `data-theme` verified per screen; titles aligned 1:1 |
| G3 Frontend — responsive | PASS | real mobile emulation (`setDeviceMetricsOverride mobile:true`) 390 on AI-01(orb)/CTH-01/BMP-02(table)/SH-02/SYS-01: single-column, **zero horizontal overflow** |
| G3 Frontend — no fake | PASS | blocked screens keep honest `BLOCKED_BY_EXTERNAL_DEPENDENCY`; missing source → `notcollected`+`None`; real 0 only when the query genuinely returns 0 |
| G4 Integration | PASS (core) / PARTIAL (full) | real full-app HTTP chain frontend→blueprint→builder→isolated DB proven (identity/subjects/screens/composer); **all-screen write-action E2E and production-candidate-copy E2E not run** |
| G5 Tests — experience suite | **PASS** | `tests/test_experience_runtime.py` **28 test functions, exit 0**, re-run after both merges |
| G5 Tests — touched-file compile | PASS | `experience_screens.py`/`experience_runtime.py`/`app.py` `py_compile` exit 0; `tests/test_evidence_store.py` also compiles at this HEAD (CI-reported syntax error does not reproduce locally) |
| G5 Tests — full legacy suite | NOT-RUN-HERE | pre-existing historical failures + `evidence_api` duplicate-blueprint warning are out of this minimal-change scope; handed to Codex |
| G6 Security | PASS (slice) / PARTIAL (full) | secret scan on every slice file: no real Zhipu key, no hardcoded secret; no tracked `*.db`; **full-repo git-diff secret scan still owed** |
| G6 Recovery / isolation | PARTIAL → contained | found a real **DB-isolation contract gap** (see issue #4); the verification run's own 2 leaked rows were removed with a guarded transaction and isolation was re-proven (real DB mtime frozen); crash/recovery drill still owed |

## Known pre-existing issues (not introduced, not fixed by minimal change)

1. `evidence_api` blueprint duplicate-registration warning at app import — self-caught,
   non-blocking, but makes a bare import process exit 1. Hand to Codex.
2. Two same-named `app_evidence_records` schemas (`app_evidence` vs `evidence_store`/tests) —
   potential owner conflict; isolation seeds the `evidence_store` DDL deliberately. Hand to Codex.
3. `intelligence_library_api.DB_PATH` hardcodes `<repo>/data/monitor.db`, bypassing
   `ZBC_DB_PATH`; BMP-03 deliberately reads via canonical `database.get_db()` instead. Hand to Codex.
4. **Non-unified DB-isolation env contract (newly evidenced this round).** The repo uses three
   override names: `ZBC_DB_PATH` (25 sites), `ZBC_EVIDENCE_DB_PATH` (only `evidence_chain.py:38`,
   writer of `zbc_evidence`) and `ZBC_RUNTIME_GUARDIAN_DB` (only `runtime_guardian.py:41`).
   Setting only `ZBC_DB_PATH` therefore does **not** redirect evidence-chain writes / guardian
   worker registration — the first isolated full-app run appended 1 `zbc_evidence` row and 1
   `runtime_guardian_workers` row to the local gitignored `data/monitor.db`. They were removed
   with a row-count-guarded transaction (restored to 0 / 8 = pre-session state), the harness was
   fixed to set all three env names, and re-proof showed the real DB mtime frozen while rows
   landed only in the TEMP DB. **Codex action:** make `ZBC_DB_PATH` the single canonical override
   (or document/fan-out the others) so tests and staging cannot touch the default DB. Other
   hardcoded paths with no env override at all: `ai_task_engine.py`, `app_evidence.py`, `ark_llm.py`.

## Remote / network

- Network restored. Two remote integrations completed on-branch (no main modification, no force-push):
  1. `origin/main` `ab67612 → 959b15b` (12 docs/brand/governance commits) merged as `f1eb53b`.
  2. `origin/main` → `49c325f` (PR#1, 21 commits / 692 files, frozen frontend prototype under
     `handoff/frontend-gpt-v24-20260911-final/PACKAGE_*`, a separate path from the live
     `experience_v2/10_prototype` — no double runtime truth) merged as `edf6d2b`.
- Post-merge regression all green: compile exit 0, 28 tests exit 0, 36 SCREEN_BUILDERS + 2 samples,
  7 experience routes, live prototype assets intact. README auto-merged (keeps both the 682-file
  remote baseline and the local experience anchor).
- All work remains **local, 10 commits ahead, 0 behind, not pushed**.

## Blocking issues (why PRODUCTION_READY = NO)

1. 4 screens still depend on real external inputs / write-side / security decisions (above).
2. Per-screen write-action→permission→approval POST chain; critical E2E on a read-only
   production-candidate DB copy; full-repo secret scan; crash/recovery drill — all remain.
3. Issue #4 canonical DB-isolation env unification (tests/staging safety) remains for Codex.
4. P2 GPT/MCP allowlisted adapter not started this round.
5. Local commits not pushed (await remote-branch decision; never force-push, never touch main).

## Commit lineage (branch only, main untouched)

1. `a5a720a` foundation + AI-01/CTH-01
2. `43cc46c` + `6ceeb6d` first propagation wave (19) + label fix
3. `d56d482` batch2 (9) + curated-events/int helpers
4. `b3d2547` batch3 (6)
5. `aea7e74` batch4 (ACC-02/03, BMP-03/04; terminal 38/44)
6. `afae28f` first final report
7. `2372daf` external auto-watch archive commit (docs/handoff only; no production .py touched)
8. `f1eb53b` merge remote PR batch #1 (backup `backup/pre-remote-merge-20260913`)
9. `edf6d2b` merge remote PR#1 (backup `backup/pre-remote2-merge-20260913`)

## Codex next actions (ordered)

1. Unify the DB-isolation env contract (issue #4) so `ZBC_DB_PATH` redirects **every** writer;
   add a regression test asserting no connection resolves to the default DB under isolation.
2. Close the 4 blocked screens only when their real source/write/security path exists;
   keep BLOCKED banner until then — never fabricate.
3. Exercise write-action→permission→approval POST; run critical E2E on a read-only
   production-candidate DB copy; run full legacy suite and triage.
4. Resolve pre-existing issues #1–#3; run full-repo git-diff secret scan; crash/recovery drill.
5. Decide remote branch strategy and push the integration branch (no force-push, no direct main).
6. P2 GPT/MCP allowlisted adapter; only then run the six Production Acceptance Gates toward RC.
