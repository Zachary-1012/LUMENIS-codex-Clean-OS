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
