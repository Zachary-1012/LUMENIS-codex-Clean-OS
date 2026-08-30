# DEV_LOG.md

> Long-term engineering log. Record facts, decisions, tests and unresolved risks; do not write speculative completion claims.

## 2026-08-30

### Governance
- Confirmed ChatGPT main development window as architecture/review/decision coordinator.
- Confirmed other chat windows as auxiliary research windows whose useful conclusions must be consolidated here or in GitHub.
- Confirmed GitHub as the durable project knowledge and handoff layer.

### AI architecture
- Production direction is Ollama-first / external-cloud-AI-optional.
- Core business loop must remain functional without any external AI API key.
- AI Shadow Mode is required before replacing system-native judgments.

### Research layer
- Added integrated Web/GitHub/browser research guidance.
- Public crawler/anti-bot research is allowed for engineering understanding; bypassing CAPTCHA, access controls or platform security is not a project objective.

### Auth / crawler direction
- Cookie/session expiration must be handled by a global in-system auth state and modal rather than an unconditional redirect.
- Modal should expose platform/account/status/reason, and the normal QR/login/verification entry when legitimately available, plus pause/defer/recovery actions.
- Platform risk must never become a silent zero-data result.

### Scheduling recovery (P0, unattended operation)
- Root cause of the missing 16:05 auto collection: `scheduler_loop` / weekly scheduler threads had been commented out since commit b69b68f (05:23, "temporarily disable scheduler while investigating a crash"), so no running instance performed fixed-window auto collection.
- Re-enabled `scheduler_loop` in app.py. Fixed clock points now act as wake-up checkpoints; the existing `xhs_cookie_bridge` account rate protection is retained. The weekly scheduler thread stays disabled pending separate review.
- Added fail-open shadow evaluation: at each wake-up, the independent decision of `platform_adapters.scheduling` (dynamic interval / state-driven cooldown / next_run_at) is recorded into `schedule_decisions`; any shadow error never blocks production collection. Replacing the fixed clock with dynamic gating stays deferred until shadow comparison and explicit sign-off (sidecar-before-cutover).
- `app.run` is `debug=False` (no reloader); exactly one scheduler thread runs per logical app process.

### Dynamic scheduling layer
- `platform_adapters/scheduling` (policy/state_map/decision/store/planner) is tracked; fixed `ScheduleDecider._deny` and preserved network/cooldown/recovery backoff intervals from being incorrectly raised by `min_interval`. 29 unit tests pass.
- `schedule_decisions` is an additive sidecar table (IF NOT EXISTS); collection_logs/notes row counts and DB integrity are unchanged.

### Process supervision / unattended resilience
- Clarified the apparent "double supervisor / double app": the venv `python.exe` is a virtualenv launcher that re-execs the base Python313 interpreter, so each logical process appears as a launcher + base pair. Logical topology is 1 supervisor + 1 app, not duplication.
- Hardened `scripts/start_production.ps1` with triple idempotency: Global mutex (no concurrent launchers) + existing-process guard + healthz, preventing genuine duplicate chains during the "starting but port not yet ready" window.
- ZBrand-HealthGuard scheduled task runs every 5 minutes under Task Scheduler (independent of any interactive session) and idempotently re-raises 8201 + 9222.

### Tests / regression
- Added `tests/test_subject_redline.py` (12 assertions: positive hits, exclude-word veto, negatives, exclude-precedence, subject SQL generation).
- Added `scripts/run_core_regression.py`; core regression is 10/10 green (database, six-state, guard wiring, risk engine, event date, report periods, safety boundary, title fallback, scheduling, subject redline).
- Restarted 8201 on v5.8.6 as a single logical chain, healthz ok; APP_VERSION aligned to 5.8.6.

### 2026-08-30 ~17:53 - Dynamic scheduling closed loop + global health center (shadow, non-gating)
- Scheduling feedback closed loop: the real per-task outcome is written back to the planner.
  - platform_adapters/scheduling/__init__.py adds process-level singleton get_planner(); the scheduler wake-up
    evaluation and the collector result feedback now share one in-memory state (no state-file overwrite race).
  - app.py _get_shadow_planner() delegates to that singleton.
  - xhs_cookie_bridge.py adds _shadow_record_result(): the task-level state (SUCCESS/EMPTY/PARTIAL_BLOCKED/
    BLOCKED/CAPTCHA/AUTH_FAILED/NETWORK_ERROR) is canonicalized and planner.record_result is called once per task.
    Fail-open; never gates or affects collection; AI takes no part in the decision.
- state_map.py: AUTH_FAILED -> SESSION_EXPIRED (class A auth, not COLLECT_ERROR); PARTIAL_BLOCKED -> RISK_WARNING
  (partial throttling lowers frequency rather than tripping the circuit or showing 0). Scheduling tests now 31/31.
- Global health center backend (data foundation for the home health dots and the unified in-app Auth Modal):
  - platform_adapters/health_center.py build_platform_health(): per-platform isolated status, triage A/B/C,
    session validity, risk/cooldown/next_run/current interval/recovery streak, last batch. IDLE (enabled, no run yet)
    is distinguished from DISABLED (extension slot); neither is a failure or "0 notes". Read-only, no network, no gating.
  - app.py: new read-only route GET /api/platform-health (takes effect after the next 8201 restart).
  - tests/test_health_center.py: 13 assertions (three-class split, platform isolation, no fake-zero).
- Core regression is now 11/11 (added test_health_center); scheduling 31/31; health center 13/13.
- Committed/pushed: b013305 (closed loop + state mapping), 484de8e (health center backend).

### 2026-08-30 18:05-18:32 - Auto-collection E2E observed; rotated-cookie root cause found and recovered
- 18:05 wake-up fired the first real auto task after re-enabling the scheduler: task xhs-20260830180503-219;
  shadow decision logged (allow=FIRST_RUN). This confirms the scheduling P0 fix end-to-end (trigger path).
- The task returned 20/20 BLOCKED IP_RISK_OR_CAPTCHA: the headless channel was redirected to
  website-login/error?type=51 ("安全限制") before any search API call (api_calls=0, no error_code 300012).
  Six-state logging was correct (BLOCKED, never "0 notes"); circuit tripped at 18:18 (20/20) until 19:18;
  the per-task feedback wrote the real BLOCKED back and overwrote the trigger-time state, proving the
  scheduling closed loop and cooldown/next_run computation.
- Root cause (NOT an IP ban, NOT a captcha): the headless channel injects a static cookie header exported
  2026-08-29 07:26; the 9222 human persistent profile had since rotated its session (web_session valid to
  2027 but different; a1/webId/gid also differed). The stale session was rejected at the web routing layer.
- Fix / recovery:
  * New reusable tool scripts/sync_xhs_cookie_from_cdp.py merges FRESH 9222 http cookies (rotating login
    state) with stable non-http account fields inherited from the previous header / latest .bak
    (x-user-id-pro whitelist, customerClientId). No cookie values are printed; private file, timestamped backup.
  * After sync, a single light probe returned SUCCESS with 40 real notes; a 2-keyword recovery sync through
    the full production chain returned SUCCESS/SUCCESS (69 unique, 6 inserted, 30 updated). Circuit cleared;
    planner entered the prescribed recovery path (recovery_streak=1, low-freq 1800s probe, not full rate).
  * verify_account() now passes again (x-user-id-pro matches whitelist).
- Removed the trigger-time optimistic SUCCESS feedback in app.py scheduler: a created task is not a success;
  only the real per-task six-state outcome (xhs_cookie_bridge._shadow_record_result) writes back.
- health_center fixes: corrected `import db` to `import database` (the swallowed import had hidden the last
  batch and produced a false SESSION_EXPIRED); overall now resolves OK / IDLE / DISABLED correctly.
  tests/test_health_center.py extended to 15 assertions.
- Tests: core regression 11/11; scheduling 31/31; health center 15/15.
- Follow-up: cookie rotation is a recurring operational event; next step is auto-detecting type=51 and wiring
  the one-click 9222 sync into the unified Auth Recovery Modal (class A), instead of a manual script run.

### 2026-08-30 ~18:55 - Global in-page Auth Recovery & collection-health widget (no page jump)
- Goal: the unified Auth Recovery must trigger on ANY v4 page (desktop + mobile), not only the console,
  and never navigate the user to a separate/stranger login page.
- v4 parent blueprint now serves a shared static folder (/v4/static/<file>).
- New self-contained v4_upgrade/static/auth_global.js (no dependencies, no credentials):
  * polls GET /api/platform-health every 20s (pauses when tab hidden, silent on 401, never redirect-loop);
  * floating health pill + panel listing every platform with its REAL state; disabled platforms show
    "未启用" explicitly (never "0 notes"/failure);
  * auto-opens a global Auth Modal only when a platform needs human action; "稍后处理" snoozes it;
  * three-class separation in the modal: A login-expired (legal login/QR via persistent profile),
    B human/security verification (manual, never bypassed), C IP/platform risk such as 300012 (cooldown
    only, QR cannot solve it); re-check calls /v4/adapters/recovery/start|check|cancel;
  * if a page already ships its own #authMask + window.openAuthModal (console), the widget DELEGATES to it
    instead of duplicating the modal; mobile (<=640px) renders as a bottom sheet.
- Wired into collect / console / settings / version_center templates with one script tag each (login page
  intentionally excluded).
- Browser E2E (real, logged-in): static JS 200; /api/platform-health polled ok; pill reads "采集健康";
  panel lists 7 platforms (xhs 正常, other six 未启用); no modal auto-popped while healthy; verified on
  BOTH /v4/console/ and /v4/version-center/ (cross-page global). A/B/C forced-failure modal text not yet
  driven live (requires a real incident) -> marked 未实测 for the auto-popup branch.

### Unresolved / not yet tested
- The 18:05 wake-up is the first real end-to-end observation of the re-enabled auto collection + shadow decision; until observed in collection_logs / schedule_decisions it remains "not yet E2E verified".
- Dynamic scheduler is shadow-only; production gating cutover awaits explicit sign-off.
- Port 8200 still runs several duplicate legacy v5.8.4 instances; cleanup and v5.8.6 cutover await explicit user authorization. 8200 was not touched.

### Next audit targets
- Verify current repository contents against PROJECT_STATUS.md.
- Verify AI/Ollama call chain and Shadow Mode implementation.
- Verify Auth modal integration across all platform collectors.
- Verify database migrations and data isolation for the two product releases.
- Verify test coverage and startup paths.
