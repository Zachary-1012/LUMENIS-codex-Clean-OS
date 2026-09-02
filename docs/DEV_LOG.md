# DEV_LOG.md

> Long-term engineering log. Record facts, decisions, tests and unresolved risks; do not write speculative completion claims.

## 2026-08-31

### v5.9.9 — wabi-sabi authoritative theme layer + mobile blank/stacked-page root-cause fix (real dual-end E2E)
- Added `static/css/zb-theme.css` as the single authoritative visual layer, loaded LAST in index.html (rollback = remove that one `<link>`). It (a) defines the wabi-sabi design tokens (neutral #F7F7F8/#FFF/#ECECF1 surfaces, four-step ink scale, low-saturation status colors used only as small dots/line-icons/links, 8–14 radii, near-flat shadows, 130–340ms motion); (b) aliases every legacy variable namespace (style.css `--bg/--text/--blue`, apple-/ios-/gpt-* and semantic `--text-*/--bg-*/--border-*`) onto the one palette so all 14 stacked legacy skins recolour without editing them; (c) reskins shell/components: GPT-style light-grey selected pill (not blue), near-black primary button, white metric cards with white-bg thin colored line-icons (replaced saturated gradient tiles), flat cards/hairline borders, de-glassed panels.
- MOBILE BLANK-SCREEN root cause (real): layout-minimal.css sets `.app-shell{height:100vh;overflow:hidden}` + `.layout{flex;overflow:hidden}` + `.sidebar{position:relative}` for desktop with no mobile unwinding; because it loads after style.css its relative sidebar won the cascade even inside style.css's mobile query — the off-canvas translated sidebar still occupied 788px in flow and pushed `.content` to top=842 (below the 844 viewport), and the locked shell made it unreachable by scroll. Fixed in zb-theme ≤768: app-shell/layout become block auto-height visible, sidebar becomes `position:fixed` drawer (no flow occupancy), content returns to top=54 and the whole page scrolls; desktop right-Inspector hidden on mobile until its P1 bottom-sheet.
- MOBILE STACKED-PAGES root cause (real): design-v8.css has `#page-overview{display:flex!important}` (id specificity 1,0,0) which kept the home page rendered under every other page (settings sat at top≈2954), so users saw "home everywhere / data missing / endless scroll". A class-level hide loses to that id; fixed with `.content #page-overview:not(.active){display:none!important}` (1,2,0). Verified only the active page-view renders and it starts at top=68.
- Empty black button root cause: a global mobile `.action{font-size:0}` (meant to keep only the topbar glyph) also swallowed inline emoji+text buttons (e.g. hero "导出日报"), leaving a blank black rounded block. Content-area buttons now keep 13px labels; only the topbar collect button stays a round glyph.
- Other reskin fixes: filled document metric-icon now `fill:none` 1.8px line like the other five; `.monitor-item/.settings-grid` multi-line values no longer overlap (forced line-height 1.5 / auto height at matching specificity); JS-injected architecture panel buttons de-saturated (`.arch-refresh-btn` near-black, `.arch-health-btn` neutral) instead of iOS blue; metric sparkline separated from its caption.
- Real E2E (Playwright, real running 8201, Basic auth): desktop 1440 pages overview/monitor/events/settings/notes and mobile 390 pages monitor/events/settings — every page-view active id correct, horizontal overflow = 0 on all, zero first-party console/page errors, mobile content.top=54. KPI 957/622/241/94/22/448,410 render; metric grid 2-col and home cards 1-col on mobile. A transient thin top loading bar can flash for <1s during page transition and is gone when settled (no such element in stable DOM, P2 polish).
- Scope/safety: no business markup restructure, no DB/schema/migration, no change to SUBJECT_WORDS/subject_hit/report口径, publish_datetime vs captured_at untouched; legacy skin files kept on disk (only cascade order used). XHS collection remains user-paused (search captcha risk) independently of this UI work.

### v5.8.9 — dual-end layout fix + topic-campaign collection chain root-cause repair (tested with real data)
- User reported both mobile and desktop "display clipped + functional data missing". Root causes were stacked across front-end and the collection chain; fixed without touching production 8200 (all work on 8201 sidecar).
- Front-end (tested, real browser 390 mobile / 1440 desktop): `#modal` was reused by two legacy `.modal` rule-sets and got center-cropped on mobile; mobile.css now forces full-screen container + bottom sheet + elastic scroll; measured panel [0,141,390,844] full-width, bottom flush, scrollable. Home/topic cards wrap to full width, long error text no longer clipped, Zachary robot docks at 52px on narrow screens, mobile notice bar removes itself before expanding the sheet (no overlap). Desktop keeps original modal behavior. Zero horizontal overflow and zero first-party JS errors on both widths; six KPI numbers render (957/620/243/94/22/448,410 at test time).
- Collection chain — four stacked root causes, all fixed:
  1. Edge/Chromium 111+ needs `--remote-allow-origins=*` or ws handshake hangs; added at 8 launch points.
  2. `xhs_campaign_monitor.js` success path never called process.exit (ws/service worker kept the loop alive, subprocess waited the full 50-min timeout, snapshot never landed); added explicit exit(0), 150s hard timeout, 5s race-guarded close.
  3. connectOverCDP hangs ~30s when attaching to a heavy existing XHS page; added pure-HTTP target reset (`reset_cdp_targets` in cdp_helper.py and `resetCdpTargets` in node: PUT /json/new?about:blank then close non-blank pages/workers) before connecting; connect drops to ~0.15s after reset.
  4. Cold navigation to search_result hangs (must warm up via /explore first, ~1.2s); note search API upgraded to /api/sns/web/v2/search/notes so matcher changed v1 -> v\d+; DOM fallback rewritten self-contained because the old one referenced a node-side clean() inside page.evaluate (ReferenceError silently swallowed, fallback never ran).
- Two additional server-side bugs surfaced only after node started returning real notes: (a) `_run_collector` defaulted XHS_CDP_URL to empty so the sidecar process launched a headless, logged-out persistent profile instead of attaching to 9222 — now defaults to http://127.0.0.1:9222 (env overridable); (b) `_save_notes` INSERT declared 15 columns but supplied 14 bindings (missing first_seen_at) -> sqlite3 ProgrammingError aborted the save — fixed, no schema change / no migration.
- Anti-risk pacing: topics previously ran back-to-back with zero gap; added humanized random inter-topic gap (12–28s) with exponential backoff on consecutive "ok-but-zero-notes" streaks (cap 90s). Dense back-to-back searches trigger a platform soft-empty window (no error, no CAPTCHA, just transient empty results) — confirmed by single rerun of a broad term right after a dense batch also returning 0; this is pacing protection, not a failure, and is never reported as an error.
- Real E2E (tested): manual single topic "太古汇" = EXIT 0 in 19.6s, 60 real notes with complete fields; via 8201 POST /api/topic-campaign/run, all 7 topic snapshots landed with empty error, each exiting in 24–26s (no more connectOverCDP timeout), hot topics #广州太古汇十五周年 / #广州太古汇15周年 each persisted 60 real notes into topic_campaign_notes (120 total, author/like/comment/collect/url present). Cold long-tail terms returned 0 inside the dense soft-empty window (recheck after cooldown; not faked).
- Regression (tested): subject red-line 24/24; security scan ALL_PASS; API smoke ALL_PASS; core regression 16/16 after re-running test_auth_api once the sidecar was idle (earlier ReadTimeout was collection contention, not logic).
- Risk-control P0 (tested). The dense batch was first misread as a platform "soft-empty window"; a focused diagnostic proved the real cause: XHS 302-redirects the search page to /website-login/captcha (verifyType=124, "scan the QR with the logged-in XHS app"). The node collector had been returning ok=true with 0 notes on that page — a red-line violation (risk shown as zero). Fix: node `detectRisk` recognizes captcha/login URL, scan/slider/security-verify text and frequency/IP/300012 text, stops at once and emits structured risk_status NEED_VERIFY/IP_RISK with dedicated exit codes 3/4 (tested: ~9.8s, exit 3, structured payload, no scrolling). Server: snapshot status split into success/need_verify/blocked/error; the run loop trips and breaks on risk (no further topics), writes data/private/topic_campaign_circuit.json (NEED_VERIFY persists until manual recovery; IP_RISK half-opens after a 45-min cooldown); run_campaign and POST /run reject while the circuit is open (HTTP 423, no node spawned — tested), GET /status exposes `circuit`. New POST /api/topic-campaign/recover performs a real CDP health probe (explore must not redirect to a verify page) and only then clears the circuit — it never bypasses platform verification. Topic-detail UI shows an in-page circuit banner (no redirect) with platform/status/reason/opened-at and an "I've verified, re-check" button; need_verify cards are amber and labelled "circuit open, not counted as zero"; tested at 390 and 1440 with zero horizontal overflow and zero first-party JS errors. Inter-topic humanized gap 12–28s + exponential backoff on consecutive empty results (cap 90s) lowers the chance of tripping risk.
- LIVE STATE NOTE: the 9222 session is currently tripped to NEED_VERIFY because of this session's own dense diagnostic runs; it is intentionally left tripped and must be recovered by a genuine human scan in the logged-in browser (no automated bypass). Core main-feed collection (the production xhs path) is separate and was verified SUCCESS earlier; the topic-campaign circuit file is independent.
- Version unified to v5.8.9 across VERSION/app.APP_VERSION/waitress ident/version_center fallback/header/footer/static cache-bust/startup print (40+ sites).
- Untested / open: browse_count/discussion_count topic-card metrics stay 0 on the note-search page (they live on the topic-aggregation page, not crawled yet — not faked); long-tail terms' behavior across the soft-empty window needs spaced observation; trycloudflare hostname is ephemeral, stable hostname needs a named-tunnel token. No DB schema change, no migration, 8200 production untouched.

## 2026-08-30

### Release Gate V1.0 baseline audit (sidecar, no production rewrite)
- Ran the 22-step release gate from the global code-level baseline V1.0 against real main source / DB / runtime, read-only first. No production chain replaced; `collector.py`, both existing registries and subject red-lines preserved.
- Entry audit: single `app.py` Flask app (13 blueprints / 303 routes); production WSGI chain = `scripts/start_production.ps1` -> `run_supervised.py` -> `run_production.py` (Waitress). Four collector generations classified; two registries intentionally kept; DCC has zero files (Experimental). Output: `docs/CAPABILITY_BASELINE.md`.
- Subject red-line: `subject_rules.py` is the single authoritative adjudicator; `risk_engine.py` is a compatibility forwarder; the nested `subject_hit` in app.py worker calls rule `subject_hit` first (AI does not decide subject). Extended `tests/test_subject_redline.py` 12 -> 24 assertions. **24/24 PASS (tested).**
- DB: copied `data/monitor.db` -> `data/backups/monitor-pre-baseline-20260830-215836.db` (quick_check ok, rollback-ready, gitignored). Live db quick_check ok, 45 tables, notes=905/events=413/collection_logs=353. No DROP/rebuild, no migration executed.
- 20:05 auto-collection window (real DB, tested): 20 keywords ALL SUCCESS, 40 each, 800 raw, 0 BLOCKED; schedule_decisions xhs-auto result=SUCCESS items_found=179, dynamic interval 3600s, next 21:09; no circuit file. Proves cookie-sync + dynamic scheduling + subject filter end-to-end recovery.
- Core regression `scripts/run_core_regression.py`: **11/11 PASS (tested)** after all edits.

### Unified auth contract (minimal, security not weakened)
- Gap found: root-level `/api/platform-health` & `/api/xhs/collect-health` were guarded only by HTTP Basic while `/v4/*` uses token sessions; a mobile v4-only session would get 401 and the global health dot could not load.
- Fix in `app.py::_basic_auth`: Basic retained; additionally accept a valid v4 session (Bearer / same-name cookie); anonymous/invalid still 401. `tests/test_api_smoke.py`: 10 endpoints 200 with v4 session, anonymous still 401, healthz open. **ALL_PASS (tested).**

### Security hardening
- Removed hard-coded credential in `system_watchdog.py` (now reads TAIKOO_AUTH_* env, Basic header only when configured); compiles; repo-wide re-scan = 0 hard-coded password.
- New `tests/test_security_scan.py`: no real cookie/session ticket in tracked source, `.env`/db/`data/private` ignored, zero high-severity source findings (excluding untracked IDE `.trae-cn` and scanner self-strings). **ALL_PASS (tested).**
- Bulk scanner hits are false positives (IDE minified libs, JS `.exec(`, legitimate list-form Popen / sandboxed exec); no shell=True with user input. Old password remains in earlier git history (history NOT rewritten, rollback-safe); recommend out-of-band credential rotation.

### Browser E2E / JS scan (tested)
- Restarted 8201; console/collect/settings/version-center all show global health dot, `/api/platform-health` ok under v4 session, zero first-party JS console errors after filtering third-party/restart noise.

### Public boundary
- No cloudflared running; 8200/8201 listen on 0.0.0.0; tunnel NOT started without explicit sign-off. Local gate green; public HTTPS health check is the single user-authorized pending item (untested, not claimed done).

### Version unification + public tunnel (tested)
- Unified runtime-facing version to v5.8.8: VERSION file, app.APP_VERSION, waitress ident, version_center fallback, header/footer, static cache-busting query, startup print; daily_git_sync commit title now reads VERSION dynamically. Historical "introduced in vX.Y.Z" comments and real filenames intentionally kept. VERSION had been reset to 5.8.5 by the main dev window while app ran 5.8.6 and footer showed 5.8.0 — now single value.
- Fixed start_tunnel.py (it hard-coded a non-existent legacy project path); now uses project root and TUNNEL_PORT (default 8201). Started a cloudflared quick tunnel to 8201; public /healthz returned 5.8.8 three times, protected routes return 401 without credentials, /v4/ redirects to /v4/settings/login and the login page renders (account+password / access-key tabs), real-browser public E2E passed. Only one edge connection registered because local DNS cannot resolve some argotunnel.com feature hosts (non-fatal; quick tunnel serves traffic). Temporary trycloudflare hostname; a stable hostname needs a named tunnel with account token. Tunnel points at the 8201 sidecar; 8200 production is untouched pending user sign-off.

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

---

## 2026-08-31 · Consolidation-002 ②–⑥ 资产身份/架构/Owner/Feature/UI地图 + 素材核对（只读治理，业务代码零改动）

对齐 MASTER TASK `ZBC-UNIFIED-PRODUCTION-CONSOLIDATION-001` 与"先收敛、再 UI"顺序；本轮不施工视觉、不搬目录、不删码、不碰生产库与运行服务。

### 产出（docs/governance/consolidation-002/）
- 新增只读生成器 `scripts/inventory/build_asset_registry.py`（消费① module_graph，不重算依赖；只读提路由/表/前端/依赖），产出 **ASSET-REGISTRY.md（②）**。
- **ARCHITECTURE-MAP.md（③）** 分层映射；**CAPABILITY-OWNERSHIP.md（④）** 唯一 Owner 初判；**FEATURE-REGISTRY.md（⑤）** FEATURE-CTH/ZBMP 总账；**UI-FEATURE-MAP.md（⑥）** 信息架构/页面/交互/组件（不含视觉）。

### 真实数字（已实测，与①对齐）
- Python 400（非测试 220 / 测试 180），app 静态可达 84；不可达非测试 136 = 孤立候选 53 + 独立入口 34 + 新一代在建 23 + 旁路引用 26（①口径"孤立61"=53+collector_v2 内 8，已在文档对账）。
- 路由：app.py 内 **189**（与既有口径精确一致），全仓合计 363（含 v4 蓝图）；数据库表 **51**；CSS 23 / JS 22 / 模板 10；requirements 15。
- 生产库只读：notes 957 / events 427 / collection_logs 477 / event_graph_events 16；未做任何写入。

### 素材核对（SHA256 铁证，零重复上传）
- 本轮重发 9 段录屏经 SHA 比对全部=已上 LFS 的 7 段（38613e1f=25031310…=LFS03；4d230a36=3E951E45…=LFS08），**未重复传视频**。
- 参考图 14→16（仅新增 01712291、cd9009bc）；归集 Word《z-Brand Core UI视觉&交互逻辑1.0.docx》到 reference-docs/；004120 在 MANIFEST 定死为"交互&动效参考基准之一"。

### 关键裁定（④，只标记不删除）
- 红线 Owner 锁：subject_rules / aggregate_events / daily_report.build_daily_report / 根 risk_engine，口径不得改。
- AI：intelligence(规则兜底,Ollama-only 正式)+ai_analyzer(执行器) ACTIVE；ark/ai_gateway/local_ai 云端 Legacy 默认关。
- 采集：collector.py 链为唯一生产事实来源；collector_v2(23) DEVELOPING 未接管；高危运行代码 3 入口标 MIGRATION_REQUIRED；Selenium/httpx/xlsxwriter/colorama/tqdm 0 引用仅登记。

### 命名冲突（待用户拍板，未自行改名）
- 本地 PRODUCT_NAMING_BASELINE 钉「品牌业务生产平台 ZBP」；本轮口头材料出现「Z-Brand Intelligence Platform」。按权威顺序暂用 ZBP，冲突登记于 ASSET-REGISTRY §0。

### 未实测 / 遗留
- ④为源码事实下的 Owner 初判，最终人工签字；DUPLICATE/LEGACY 退出须走引用→替代→回归门槛，本轮未删任何文件。
- UI 视觉(⑨)继续暂停；AUTH-01 主 SPA 挂 auth_global、SCHED-01 影子转门控、DIM-01 双维度落库、EVT-01 三类事件四关系、P0-FIX-1 版本号括号 bug 均登记待办，本轮不改。
- 生产 8201/9222 全程未触碰。

---

## 2026-08-31 · 命名层级决议（只修层级认知，无业务改动）

- 决议：最顶层统一平台层 = **Z-Brand Intelligence Platform**（不缩写）；其下 **ZBP（品牌业务生产平台）/ DCC / SICI 三者并列**，共同属于该顶层；**ZBP 不是整个母平台/最顶层**。CTH-POMS、ZBMP 继续归属于 ZBP。
- 收口上一条"命名冲突待拍板"：原口头「Z-Brand Intelligence Platform」并非与 ZBP 二选一，而是 ZBP 之上的统一平台层。
- 仅改命名/架构文档：PRODUCT_NAMING_BASELINE（权威重写）、THREE_REPOSITORY_MATRIX_POINTER、UNIFIED_PRODUCTION_ARCHITECTURE_v1.0、consolidation-002 五份治理文档与其只读生成器 build_asset_registry.py（重跑，数字不变 400/84/136、189/363、51）。
- 未改任何业务代码 / 数据库 / 采集器 / UI / API / Runtime / Feature / Owner 判断，未删文件；历史日志条目不改写，仅追加本决议。

---

## 2026-08-31 · 三仓同步审计 + GitHub 深度研究（只审计/研究/沉淀，不改生产）

- 三仓 HEAD 实测：ZBC `8fda223`（本地=远程 0/0）；DCC 本地 `77dd1e4` 落后远程 `023e2ba` **27**、领先 0，工作区脏 3 文件（package.json/learning-store.js/persistence.js，非本任务产生，未整合）；SICI 本地原未克隆，本次只读克隆到 ZBC 外 `D:\repo-audit\SICI-Core`，远程 main `64eb6a7`（纯静态站点，0 py）。
- Feature 全链路（新增只读脚本 scripts/inventory/feature_crosscheck.py，py_compile 通过）：34 条；真实路由 341（app.py 内 189）、表 51；**声明的 DB 表 100% 命中、登记 .py 的 Owner 100% 存在、无虚假 ACTIVE**；6 条 API"缺失"经人工甄别 4 条为蓝图 url_prefix 嵌套误报（auth-recovery/v4.auth/version-center/settings 真实存在），2 条为登记前缀不精确（schedule/circuit，P3）。
- GitHub 研究：33 条 Research（LR-20260831-001..033，star/license 为 08-31 GitHub API 一手），沉淀 docs/learning/ 8 份；结论=保持 Flask+SQLite+Playwright+APScheduler，Windows 生产 WSGI 选 waitress（gunicorn/supervisor 不支持 Windows），迁移候选 Alembic，学习库候选 sqlite-vec，测试 pytest+Playwright trace；不采用 Celery/Nx/Scrapy/独立向量库。
- 问题分级：**无新增 P0**；P1=AUTH-01 主 SPA 挂弹窗/三套运行代码高危入口收口/SCHED-01 待签字/统一 pytest L0-L10/DIM-01/EVT-01/DCC 整合；P2=并行基线 ADR 收敛/Alembic/API 契约版本化/重复能力按门槛退/Evidence 体系；P3=跨仓 ZBIP 缩写对齐/2 处 API 登记/8200 重复实例/.trae-cn 忽略等。OPT-001..010 + OPT-API/DOC 只登记不施工。
- 报告：docs/governance/consolidation-002/CROSS-REPO-AUDIT-RESEARCH-2026-08-31.md。全程未改业务代码/DB/采集/UI/API/Runtime、未删文件；生产 8201/8200 v5.9.9、9222 在线，小红书保持 BLOCKED 熔断未触发。

---

## 2026-08-31 · Feature Final Verification 2.0（只验证/登记/文档，不改生产）

- 产出：docs/FEATURE-FINAL-VERIFICATION-MATRIX.md（34 条全链矩阵+A–I 分组）、docs/FEATURE-GAP-REGISTER.md（GAP-01..22）、docs/UI-FINAL-CAPABILITY-MAP.md（含未完成占位）、docs/TECHNOLOGY-OPTIMIZATION-BACKLOG.md（P0–P3）；只读脚本 scripts/inventory/feature_final_verify.py（py_compile 通过）。
- **真实测试证据（本轮实跑，非假设）**：36 个 test_*.py 中仅 5 个含 `def test_`（test_ai/api/database/e2e/llm_gateway），合计 **50 用例 50 passed in 16.06s**，覆盖主体过滤/风险等级/事件聚合/日报/DB 结构与完整性/认证/LLM 兜底；其余 31 个为脚本式（无 def test_），且统一 `pytest tests` 被 test_api_smoke.py 顶层 sys.exit 打成 INTERNALERROR（仅收集 26）→ GAP-01/18。
- 红线直接测试缺口（GAP-02，实测）：test_risk_engine.py 实际 import collector_guard、test_report_periods 实际测 export_report；根 risk_engine / aggregate_events / build_daily_report 仅 test_e2e 集成级覆盖，缺函数级直接单测。
- Evidence：app_evidence_records 为外部抓取表且 0 行，无统一测试/运行 Evidence 落库 → GAP-08。
- 状态保持 Registry 原值不擅改：ACTIVE21/DEVELOPING6/EXPERIMENTAL2/PLANNED4/RESERVED1，NOT_VERIFIED/DUPLICATE/MIGRATION_REQUIRED/LEGACY 的 Feature 级均 0（重复在实现层以 DUPLICATE_CANDIDATE 登记 GAP-04/09/10）；ASSET_MISSING=0。
- 结论：P0=0；UI 信息架构/占位已覆盖全部 34 功能，具备一次性施工的映射条件，但建议先做 GAP-03（主 SPA 挂 Auth Modal）+ CSS Token 单层收敛两个前置并在 Staging 施工；是否开工由用户拍板。全程未改业务/DB/采集/UI/API/Runtime、未删文件。

---

## 2026-08-31 · ZBIP 统一 UI/UX 设计工程启动（只定设计规范与地图，不写页面代码）

- 阶段切换：从审计转入设计工程，纪律=先设计系统→页面地图→组件→最后代码；本轮**未改 static/ 与任何业务代码**（git 无 static/*.py 改动，已核）。
- 现状根因实测：static/css 共 22 个 CSS 约 1.7 万行，index.html 串行 link 17 个样式层层覆盖、多套 token 并存（tokens/tokens-minimal/zb-theme/zb-gpt-theme/design-v8/v9），是“新 UI 被旧样式覆盖/风格不一”的机制根因；设计系统规定 zbip-tokens 为唯一真相并给出旧层 ACTIVE/DUPLICATE/LEGACY 退役策略（本轮只定策略不删文件）。
- 产出 docs/UI/：ZBIP-DESIGN-SYSTEM.md（哲学/三层 Color Token/字体/栅格/间距/圆角/阴影/图标/六语义状态/动效时长与 z-index/旧 CSS 收敛/无障碍性能，含可直接施工的具体 token 值）、COMPONENT-SYSTEM.md（Atom/Molecule/Overlay/State/Pattern 组件地图与规格）、UI-EVIDENCE-PROCESS.md（七步门禁+UI Evidence 字段+防覆盖）、page-maps 四份（CTH 驾驶舱/ZBMP 分析工作台/DCC 工程控制台/SICI 实验工作台，每页含目标/用户/数据/组件/交互/状态/权限，未完成功能占位）。
- 学习资产 docs/learning/ui/：UI-DESIGN-RESEARCH.md（Primer/Linear/Vercel/OpenAI/Anthropic/Stripe/Datadog/Sentry 八标杆取舍，LR-034..041 已登记进 LEARNING-REGISTRY）、MOTION-INTERACTION-PATTERNS.md（100/200/300ms 动效标尺、状态叙事、⌘K、四态、移动差异、性能红线）。
- 视觉定调：侘寂黑白灰（Stone 暖灰）为底，六语义色仅状态/关键操作，状态=点+文字+图标三重、颜色不作唯一信息；动效目的优先并支持 prefers-reduced-motion；六断点 390/430/768/1024/1280/1440。
- 下一步开发顺序（待用户确认开工）：① GAP-03 主 SPA 挂 Auth Modal；② Staging(8301) 建 zbip-tokens/components 单层并按组件地图实现；③ CTH 总览/采集/事件优先，ZBMP 随后，DCC/SICI 仅冻结 IA；逐组件/页面走 UI Evidence 七步门禁。生产 8201 与后端在 UI 施工期冻结、不改业务。

---

## 2026-08-31 · UI 施工 Step 1（Staging 8301 隔离环境 + GAP-03 主SPA挂Auth + ZBIP Token 单层落地）

- 隔离方式（先旁路验证再切换，生产零影响）：`git worktree add D:\Taikoo-staging-ui (ui/staging-foundation@5a80b3d)`，用主 venv 以 `TAIKOO_PORT=8301 / ZBC_DB_PATH=staging\monitor.staging.db（在线一致备份，notes957/events427/logs477）/ XHS_CDP_URL=空 / TAIKOO_WEB_DISCOVERY=0 / host=127.0.0.1` 起独立 Staging；主目录 8200/8201 生产全程未改文件、未重启，持续 v5.9.9。
- GAP-03（主 SPA 缺统一 Auth 弹窗）：static/index.html 末尾引入 `/v4/static/auth_global.js`（与 console/collect/settings/version_center 四个 v4 子页同一实现，不新写逻辑）。实测 8301：#zaFab 已挂载，读到 /api/platform-health 并显示“需处理 1”（小红书 BLOCKED/C_RISK 被正确识别为风控，而非 0 条）。
- ZBIP Token 单层：新增 static/css/zbip-tokens.css（设计系统 v1.0 全部 --zb-* 令牌：Stone 暖灰阶/六语义/字号/4px间距/小半径/三级弱阴影/动效时长缓动/z-index/布局尺寸/prefers-reduced-motion）。**本文件只定义 :root 变量、无任何元素选择器**，故对存量页面零视觉影响；在 index.html 所有旧 CSS 之后最后引入。实测 getComputedStyle：--zb-stone-900=#1C1917、--zb-r-md=6px 生效。
- 验证（已实测）：HTTP /、/static/css/zbip-tokens.css、/v4/static/auth_global.js 均 200；浏览器 DOM 断言 tokenLinked/authLinked/fabExists=true、21 个侧栏项与总览数据正常渲染、页面未崩。未取得：browser-use 截图接口两次 COMMAND_TIMEOUT（工具侧），像素级视觉对比待补，已用 DOM 断言 + a11y snapshot 替代；后端 pytest 本轮未改 .py 故未重跑。
- 范围：仅 static/index.html(+4) 与 static/css/zbip-tokens.css(新)，无 .py/.db/.env/采集/主体口径/API 变更，无 DB 迁移。下一步 Step 2：zbip-components 基础组件（Button/Input/StatusDot/Table/Modal/Drawer/四态/⌘K）仅在 Staging 实现。

---

## 2026-08-31 · UI 施工 Step 2（ZBIP 基础组件层 + 隔离组件预览页，纯新增零引用）

- 新增 static/css/zbip-components.css：Button(4 variant×3 size×disabled/loading)、IconButton、Form(Input/Select/Textarea/Search/错误/禁用)、StatusDot+Badge 六语义、Tabs、高密度 Table(tabular-nums)、Panel/Card、Toolbar、四态(Empty/Loading/Error/Success)、Kbd/Skeleton/Divider；统一 focus-visible 焦点环、prefers-reduced-motion 降级、移动端触控。**全部 .zb- 前缀、只用 --zb-* 令牌、不覆盖任何存量 class**。
- 新增 static/zb-preview.html 隔离组件画廊（不挂任何现有页面、不加后端路由，/static/zb-preview.html 直达），覆盖组件×全状态，作为视觉验收与 UI Evidence。
- 实测（8301，已实测）：两资源 200；浏览器 DOM 断言 13 按钮/10 badge/4 表格行/4 态/4 tab；主按钮背景 rgb(28,25,23)=#1C1917 近黑、圆角 6px、危险点 #DC2626、数字格 font-variant-numeric=tabular-nums、画布底 #FAFAF9；截图证据 docs/UI/evidence/step2-components-top.png、-bottom.png（侘寂黑白灰、语义色仅状态，达标）。
- 零影响论证：本步不修改 index.html / 任何现有模板，新文件无任何生产页面引用，故合入 main 也不改变运行界面；Modal/Drawer/CommandMenu/AIChatDrawer 与首个真实页面迁移放 Step 3，**改真实页面 DOM 时只在 Staging 分支验收后才合 main**。
- 范围：仅新增 static/css/zbip-components.css、static/zb-preview.html、2 张 evidence 与 DEV_LOG；无 .py/.db/.env/采集/API/主体口径变更，无 DB 迁移。

---

## 2026-08-31 · UI 施工 Step 3（旧总览令牌重映射换肤 + 侧栏塌陷修复，仅 Staging，暂不合 main）

- 新增 static/css/zbip-theme-override.css（Strangler 适配层，最后加载、只重定义 zb-theme 暴露的 --w-* 底层令牌，不改 DOM/布局/旧 CSS）：冷灰 #F7F7F8→Stone 暖灰 #FAFAF9、主操作去蓝 #3B82F6→近黑 #1C1917（信息蓝保留给 --w-info/链接）、六语义对齐 zbip-tokens（success#16A34A/info#2563EB/attention#D97706/danger#DC2626，AI 去紫转中性）、圆角 8/10/12/14→4/6/6/8/12、阴影更弱暖黑、侧栏 248→240、动效时长对齐；并把硬编码大色块 .metric-icon 降为弱底+语义色、#globalError 苹果红收敛到 danger。
- 过程中修复一个自身 bug：override 文件头注释里 `--w-r-*/` 的 `*/` 提前闭合块注释，导致 :root 整块被浏览器丢弃（首验变量未生效）；改为中文描述后 :root 正常生效（教训：CSS 注释内不得出现 */，已 30/30 配对校验）。
- 【真实问题修复】侧栏 21 个导航项被压成 0.58px：根因是侧栏底部 JS 注入的 side-footer(324px)+architecture-panel(375px) 挤占，flex column 下 .side-nav 仅剩 69px，导航项被 flex-shrink 压缩（禁用 override 后依旧，证明非换肤引入，属既有 IA/布局问题）。override 层补偿：.sidebar 内部滚动、.side-nav/side-item flex:none 且定高 36px，导航完整恢复；长期应把非导航状态卡移出侧栏（登记 IA 优化，本步不做结构改动）。
- 实测（8301，已实测）：桌面 1066：:root 变量生效（--w-bg#FAFAF9/--w-ink#1C1917/--w-accent#1C1917/--w-danger#DC2626/圆角8/侧栏240），21 导航完整、active 高亮，6 KPI 真实出数 957/622/241/94/22/448,410，风险预警/事件中心(方所闭店29、OLE投诉63)/热门话题/日历齐全，右下 Auth fab“需处理1”正常，证据 step3-overview-desktop-1066.png。移动 390（CDP Emulation，mobile=true）：layout=block、KPI 2 列、单顶栏、6 KPI 全出数、fab 正常，证据 step3-overview-mobile-390.png。两视口下 /api/* 均 status=ok。
- 未实测/登记：① 430/768/1280/1440 断点本轮未稳定取到（CDP emulate 在 mobile=false 时未可靠改宽且截图有合成残影，非真实 DOM 重复——已核 DOM 仅 1 个 .topbar），留待下轮补证；② .action.primary 计算色为 rgb(0,0,0)（旧层硬编码）与 #1C1917 有极微差，待统一；③ sparkline 折线仍为蓝/绿/红/紫数据色，暂保留（数据可视化语义色），后续决定是否降饱和；④ 侧栏状态/架构卡片移出属 IA 改造，登记不擅改。
- 决策：Step3 改变真实页面外观，按“验收前生产冻结”只在 ui/staging-foundation 提交，**不 FF 到 main、不动 8201 生产**；待用户确认视觉方向后再合入。范围仅 override.css、index.html（+1 link）、2 张 evidence、DEV_LOG；无 .py/.db/.env/采集/API/主体口径变更，无 DB 迁移。回滚 = 删除 index.html 中 override 的 link。

---

## 2026-09-01 · UI 施工 Step 4（GPT/Codex 式工作台外壳：工作区切换/分组侧栏/干净 Home/账户层级，仅 Staging）

- 触发：用户 12 张 ChatGPT Work/Codex/设置参考图 + 新 IA 口径（系统打开叫 Z-Brand Core；左上工作区切换 CTH-POMS/ZBMP，ZBMP 必须密钥；Home 像 GPT 一样干净、Zachary 收进中央输入不再乱飘；加常规搜索框；四周窄留白色差；线性 icon；重要度用彩色小圆点；账户→设置层级；设置页同构侧栏）。12 图全部精读，对照见 docs/UI/STEP4-WORKBENCH-IA.md。
- 改了什么（纯增量 Shell 层，可整层回滚）：
  1. 新增 static/css/zbip-shell.css（v1.0.1）：body.zb-shell-on 作用域；外层 stone-200 衬底+主区白圆角内面形成窄留白色差；侧栏 248 stone-100、分组标题、项高 32/圆角 6/active stone-200 胶囊、线性 icon 统一；工作区切换器/搜索/通知槽；账户槽；浮层 .zb-pop（白圆角弱阴影）、黑胶囊 .zb-tip、ZBMP 密钥门 .zb-modal；Home 居中提问（标题/圆角输入/黑圆发送钮/胶囊 chip）；隐藏乱飘 #zacharyFloat；顶栏去渐变并弱化旧 .brand/.top-center/.clock（保留 .top-actions 采集/AI/导出）；六语义 .zb-dot；≤760 侧栏抽屉化、reduced-motion。
  2. 新增 static/js/zbip-shell.js（v1.0.1）：运行时把 21 个 .side-item 按 总览/监测/分析/品牌资产/产出/系统 6 组包裹（源 DOM 不删、顺序保留，overview 改名“舆情驾驶舱”）；注入工作区切换器（CTH-POMS 默认✓ / ZBMP 锁·密钥）、整宽搜索框（输入即时过滤功能）、通知、底部账户；工作区浮层/账户浮层（邮箱/Zachary/设置 Ctrl+,/退出）；ZBMP 密钥门 modal（前端占位，非空记 localStorage，不硬编码密钥，文案标注后端鉴权待接）；注入 #zbHome（标题“你今天想知道什么？”+复用既有 #zacharyInput/sendZacharyMsg/toggleZacharyChat，不新造 AI+4 快捷 chip）；点侧栏/chip 收 Home 进具体页、双击工作区名回 Home；移动端驱动既有 #menuToggle 抽屉。
  3. static/index.html 仅 +4 行（head 1 link、body 末 1 script，均标 [STAGING ONLY]）。
- 为什么：用户要 GPT 式干净落地页与清晰层级，且明确“现有能力一个不丢、不做大重构”。用 Strangler Shell 层运行时重组外观与 IA，业务路由/数据/采集/主体口径全部不经手，回滚只需删 2 行引用。
- 数据库：无变化、无迁移；Staging 仍连只读副本 staging/monitor.staging.db，生产 data/monitor.db 未碰。
- 测试（8301，已实测）：① 结构断言 shellOn/6 分组/切换器/搜索/账户/Home 全在、21 项全保留、#zacharyFloat=display:none、无新增 console error（仅既有 three.js r150 deprecation warning）；② 工作区浮层 CTH-POMS(✓)/ZBMP(锁·密钥) 正常；③ ZBMP 密钥门开/取消正常；④ 搜索“事件”→仅显事件中心/事件关系图谱、隐 19，清空恢复 21；⑤ 账户浮层 4 行，账户→设置正确跳 page-settings；⑥ chip“进入舆情驾驶舱”→Home 收起、page-overview active，6 KPI 真实出数 957/622/241/94/22/448,410，风险 8 行/事件 8 行(方所闭店29)/话题 7 行/2026年9月日历齐全（能力零丢失回归通过）；⑦ 双击工作区名回 Home；⑧ 390 移动：侧栏默认 translateX(-260) 抽屉、汉堡滑出 translateX(0)、Home 标题 24px、21 项在、底部账户槽在。Evidence：docs/UI/evidence/step4-home-desktop.png、step4-cockpit-desktop.png。
- 过程运维：发现 Staging 8301 后台进程已退出（连接拒绝；生产 8201 正常 v5.9.9），按隔离参数（TAIKOO_PORT=8301/ZBC_DB_PATH=只读副本/XHS_CDP_URL=''/TAIKOO_WEB_DISCOVERY=0）重新后台拉起，healthz 200 后再测，未动 8201。
- 未实测/遗留（如实登记）：① 430/768/1024/1280/1440 断点未稳定取到（CDP emulate mobile=false 改宽不可靠、DSF 致截图左右合成残影；DOM 断言 topbar/sidebar/ws 均=1 证明非真实重复），需真机或手动补图；② ZBMP 密钥门为前端占位，密钥来源/后端鉴权方式待用户拍板，ZBMP 工作区页面本身未建；③ 设置页同构侧栏（ref10/12）留 Step7；④ 常规搜索当前只过滤侧栏，后续与既有 commandPalette(Ctrl+K) 合并；⑤ 驾驶舱 KPI metric-icon 弱底、sparkline 多色、右侧 AI 洞察写死假数据(65%/9.8%/22/448K) 留后续精修/接真实数据；⑥ 顶栏 .top-actions 在 Home 下是否进一步弱化待验收。
- 决策：Step4 改变 IA 与真实外观，继续只在 ui/staging-foundation 提交并 push 该分支备份，**不合 main、不动 8201**；待用户对 Step3+Step4 整体视觉点头后统一合 main。范围仅 zbip-shell.css/js、index.html(+4)、STEP4 文档、2 张 evidence、DEV_LOG；无 .py/.db/.env/采集/API/主体口径/时间口径变更，无 DB 迁移。回滚 = 删除 index.html 中两行 [STAGING ONLY] 引用。

---

## 2026-09-01 · UI 施工 Step 5a（CTH 细节微调 + Home 竞态根治 + 手机适配，仅 Staging）

- 触发：用户确认外壳方向 OK（75 分基线），点名四处微调：① 左上顶栏图标还是 emoji/方块、要线性化；② 状态栏（侧栏）图标与文字太远、字号偏小；③ 隐藏 brand 后左上空一大片；④ 必须做手机适配。另把旧文案“话题监测端口”规范为“话题监测”。
- 改了什么（仍只动 Shell 层 zbip-shell.css/js + index.html 版本号，业务/后端/DB 零改动）：
  1. 顶栏线性化：zbip-shell.js 新增 linearizeTopbar()，运行时把 commandPaletteBtn/alertBellBtn/refreshBtn/reviewBtn/reportBtn 的 emoji .svgicon 替换为内联线性 SVG（搜索/铃/刷新/四向星/文档，stroke 2、16px）；CSS 统一 .action 高 34、圆角 7、图标 16。
  2. 修左上留白：隐藏 .brand/.top-center 后给 .top-actions 设 margin-left:auto，操作整体靠右（实测计算剩余 155.6px，左侧不再空洞）。
  3. 侧栏收紧：.side-item 项高 32→34、gap 10→7、字号 13→13.5px，navicon 18→17，图标与文字更聚合、更易读。
  4. 【真实 bug 根治】Home 加载竞态：主 app 初始化会程序化 .click() 默认页 page-overview（isTrusted=false），该合成点击冒泡到 nav 误触发 hideHome，且 #zbHome 原 absolute 跟随被各 page 撑高的 .content（实测被撑到 2992px，居中内容跑到视口外显示空白）。修复：(a) nav 点击仅认 e.isTrusted 真实用户点击，新增 userNavigated 标志，屏蔽初始化合成点击；(b) window load + 450ms 两次兜底 showHome；(c) #zbHome 由 absolute 改 fixed（top56/left248/right0/bottom0，手机 left0），永远相对视口居中，不被内容撑高。
  5. 文案：normalizeNavLabels() 用 TreeWalker 递归（兼容翻译标记包裹层）把“话题监测端口”展示文本改为“话题监测”，源 DOM/路由不动。
  6. 手机适配（≤760）：顶栏隐藏 .btn-label 只留线性图标、间距收紧；Home 输入框 textarea min-height 46px 避免 placeholder 两行被裁；chip/ask 圆角与间距适配。
- 数据库：无变化、无迁移；Staging 连只读副本，生产库未碰。
- 测试（8301，已实测）：桌面 1706——顶栏 5 按钮全部 svg=1、操作靠右无空洞，侧栏 gap7/13.5px、6 分组、话题监测文案正确，Home show/top56/高=视口高居中；进驾驶舱回归：page-overview active、6 KPI 真实出数 957/622/241/94/22/448,410、风险预警（高风险83/81/62/61）、事件中心（方所闭店29/OLE投诉63/餐饮81）、热门话题、2026年9月日历全在，能力零丢失。390 移动：侧栏默认 translateX(-260) 抽屉、顶栏纯线性图标无文字、Home 标题24/输入框46px/chip 2×2、Home 稳定显示（竞态修复后不再空白）。Evidence：step5a-home-desktop.png、step5a-home-mobile-390.png、step5a-cockpit-regress.png。
- 过程问题：browser-use 抓帧通道在旧 target 连续超时（bu.js 正常、screenshot/CDP 卡，页面 three.js/sparkline 持续重绘叠加多次 CDP attach 所致），新开 target 后恢复；属测试工具问题非页面 bug。另：负面确认角标在不同刷新时序偶发显示 0/31（既有 badge_manager 异步取数，非本轮引入，登记）。
- 未实测/遗留：430/768/1024/1280/1440 断点仍未逐档取图（CDP 改宽不稳，需真机）；顶栏线性图标在超窄 320px 的折行未测；ZBMP 密钥门仍为前端占位（用户已拍板用正式 API Key+用户体系，转 Step5b 后端实施）。
- 决策：继续只在 ui/staging-foundation 提交 push，**不合 main、不动 8201**；用户已确认 Step3+Step4 方向，Step5a 微调协和后，待 Step5b ZBMP 地基一并验收再统一合 main。回滚 = 删除 index.html 两行 [STAGING ONLY] 引用。

---

## 2026-09-01 · Step 5b（ZBMP 正式 API Key + 用户体系，仅 Staging）

- 触发：用户在「本地口令 vs 正式 API Key+用户体系」中拍板选方案②（正式体系、允许动后端）。先审计既有 v4_upgrade/auth（models/security/service/config/blueprint），确认已有完整用户/会话/限流/PBKDF2/owner 体系与 login_by_key，故**复用而非新造**，只加“工作区级密钥授权”薄层。
- 改了什么：
  1. 新增 `v4_upgrade/auth/workspace.py`：幂等建 v4_workspace_keys / v4_workspace_grants 两表；签发（明文仅返回一次、库存 PBKDF2 hash）、校验（active+未过期、命中回写 last_used）、列表（不含 hash/明文）、吊销（连带失效 grant）、会话 grant、session_can_access、无会话时以 owner 建立本地会话。
  2. `v4_upgrade/blueprint.py`：导入 g 与 workspace 函数，新增 5 端点（status / unlock / keys GET·POST / keys/revoke），owner 才能签发吊销；unlock 无会话时自动以 owner 建会话并 Set-Cookie + 12h grant。
  3. `v4_upgrade/config.py`：新增 WORKSPACE_CONFIG；**修复 Staging 隔离漏洞**——v4 DB_PATH 原只读 MONITOR_DB_PATH（未设则回落生产库），改为 ZBC_DB_PATH→MONITOR_DB_PATH→默认生产；生产不设 ZBC_DB_PATH，行为不变。
  4. 前端 `static/js/zbip-shell.js`：密钥门从“非空即 localStorage 占位”改为真实 fetch unlock；点 ZBMP 先 GET status，已授权直接进、未授权弹门；错钥留 CTH 并报错，对钥进入；sessionStorage 仅 UI 提示，权威为后端 cookie+grant。index.html shell 引用 bump v=1.0.7。
  5. 新增 tests/test_workspace_keys.py（6 用例）与 docs/ZBMP-WORKSPACE-AUTH.md。
- 数据库：新增 2 张独立表（CREATE IF NOT EXISTS，向后兼容、不删不改既有表/数据）；**无既有表结构变更、无数据迁移**；Staging 全程连只读副本，生产库未碰。
- 测试（已实测）：
  - 单元：tests/test_workspace_keys.py 6/6 passed（临时库）。
  - HTTP 全链路 8301：匿名 status=CTH true·ZBMP false·未登录；owner 登录 200+Set-Cookie；签发 200 明文仅一次；错钥 401；对钥 200 自动建会话+12h grant；再查 status ZBMP=true·logged_in=true；列表只回 prefix 无 hash；吊销 200。
  - 浏览器 E2E：未授权点 ZBMP 弹门；错钥 mask 保持、提示“工作区密钥无效或已吊销/过期”、仍 CTH-POMS；对钥 mask 关闭、工作区=ZBMP；切回 CTH 再点 ZBMP 凭后端授权直接进入不弹门。
  - 回归：test_ai/test_api 主体 + 新测共 33 passed；6 项失败为 Staging 既有 ENV（test_database 写死相对 data/monitor.db、TestAuthAPI 两例依赖开启 HTTP Basic），与本改动无关（已核对 test_database 不经 v4 config）。
- 未实测/遗留：① 密钥“签发/列表/吊销”管理 UI 未做（接口已就绪，并入 Step7 设置页同构）；② ZBMP 工作台页面本体未建（下一步按手机录屏范式做网页适配=Step5c）；③ 生产 .env 是否设 ZBC_DB_PATH 已确认不设（生产行为不变），但合 main 前需在主 worktree 再跑一次导入/healthz 验证；④ grant 目前 12h 固定，续期/多设备管理后续做。
- 决策：仍只在 ui/staging-foundation 提交 push，**不合 main、不动 8201**。回滚 = 删 workspace.py + blueprint 内 workspace 段落与 import + 前端密钥门退回；两张新表独立，保留不影响既有功能。

---

## 2026-09-01 · 阶段收尾断点（Step1–5b 完成，暂停休息）

- 收尾时真实状态（已核对）：
  - Staging worktree `D:\Taikoo-staging-ui`，分支 `ui/staging-foundation`，HEAD=**a9ab157**，工作区干净，本地=origin 0/0（已推）。
  - 主 worktree `D:\Taikoo-monitor-new`，main HEAD=**e1bf094**（02:08 自动巡检提交，非本窗口操作），本地=origin/main 0/0；本窗口全程未改主 worktree 源码。
  - 进程：生产 8201 LISTENING（v5.9.9，冻结未动）；Staging 8301 LISTENING（后台 task 3a628867，重启后 pid 以 netstat 为准）。
- 已完成里程碑：Step1 统一 Auth 弹窗+令牌注入(bd8e7e7，已在 main) → Step2 基础组件层+组件画廊(d16d000，已在 main) → Step3 旧总览令牌重映射换肤+侧栏塌陷修复(dcae19a，仅分支) → Step4 GPT/Codex 式工作台外壳(9515767，仅分支) → Step5a CTH 微调+Home 竞态根治+390 适配(df4f523，仅分支) → Step5b ZBMP 正式 API Key+用户体系(a9ab157，仅分支)。
- **下次精确续接 = Step5c：ZBMP 工作台页面本体**（只在 Staging）：
  1. 重读 docs/reference/ui-research/ref-20260901-step5/frames/f001..f031.png（手机 ChatGPT 录屏每 5s 抽帧，已精读，范式见 Step5 研究笔记）与 docs/UI/ZBIP-DESIGN-SYSTEM.md、COMPONENT-SYSTEM.md。
  2. 用侘寂黑白灰做**网页适配**（不照抄深色/手机尺寸）：分组设置卡（浅灰底+白圆角卡+每行线性 icon/标题/右值或 toggle/行间细分隔线）、二级页头（圆形返回+居中标题）、半屏 sheet（大圆角+遮罩+全宽主胶囊+取消）、连接器/插件列表、搜索分类胶囊 Tab、全屏引导 Modal。
  3. 实现弹层「微光」：柔和边缘光晕 + 淡入上移（micro120/state220/page320，cubic-bezier(.16,1,.3,1)），动效只表达状态、不炫技。
  4. 密钥「签发/列表/吊销」管理 UI 并入设置页同构侧栏（Step7，接口已就绪：/v4/auth/workspace/keys*）。
  5. 断点补测：430/768/1024/1280/1440 逐档取图（CDP 改宽不稳，优先真机/新 target 截图）。
- 合 main 决策（待用户验收）：Step3+4+5a+5b 目前都只在 ui/staging-foundation；因 Step5b 含后端新表/端点，合 main 前需在主 worktree 跑一次 import + healthz + 主体口径回归，确认生产不设 ZBC_DB_PATH 时行为不变，再 FF/merge、切 8201。
- 体验入口：8301 左上工作区切换器→ZBMP，Staging 测试密钥存于副本库（browser-e2e label），生产合入后由 owner 经设置页签发、明文仅一次。
- 红线不变：不改/弱化主体口径与 subject_hit/_subject_sql_and_values/aggregate_events/build_daily_report；publish_datetime≠captured_at；不删清覆盖生产库；AI=Ollama-only 增强层；小红书风控只识别-熔断-合法人工验证-恢复；不提交 .env/*.db/cookie/token/profile；DCC 子模块指针不 add；一任务一 commit，先旁路 Staging 验证再合 main。

### 用户验收结论（2026-09-01 休息前确认）
- **当前 8301 这页风格 OK、整体 OK**：Step3 换肤 + Step4 工作台外壳 + Step5a 微调的黑白灰侘寂/GPT 式方向获用户确认通过，下次不再推翻视觉基调，只做精修与模块接入。
- **下次开工主线 = 在已确认的外壳里接入真实模块**（不再重做风格/布局）：把现有真实功能按 6 分组逐块接进外壳与导航，ZBMP 侧同步建工作台页面；接入一个、在 8301 实测一个、再接入下一个。

### 【已完成】（Step1–5b，均在 ui/staging-foundation；Step1/2 已在 main）
1. Step1 全局 Auth 恢复弹窗挂主 SPA + ZBIP 设计令牌注入（纯变量零视觉影响，bd8e7e7，已在 main）。
2. Step2 .zb- 基础组件层 + 隔离组件画廊 /static/zb-preview.html（d16d000，已在 main）。
3. Step3 旧总览令牌重映射换肤（冷灰蓝→Stone 暖黑白灰、主按钮近黑、圆角/阴影收敛）+ 修复侧栏 21 项被压到 0.58px 的塌陷 bug（dcae19a，仅分支）。
4. Step4 GPT/Codex 式工作台外壳：左上工作区切换器(CTH-POMS/ZBMP 密钥门)、21 项归 6 分组线性侧栏、干净居中 Home「你今天想知道什么？」+Zachary、账户浮层、常规搜索、窄留白色差（9515767，仅分支）。
5. Step5a CTH 微调：顶栏 5 按钮 emoji→线性 SVG、操作靠右修左上留白、侧栏字距字号收紧、Home 加载竞态根治(isTrusted+fixed 居中+两次兜底)、「话题监测端口」→「话题监测」、390 手机适配（df4f523，仅分支）。
6. Step5b ZBMP 正式 API Key+用户体系：复用 v4 auth，新增 workspace 密钥签发/校验/吊销/12h grant（5 端点+2 幂等表）、修复 v4 DB_PATH 的 Staging 隔离、前端密钥门接真实 unlock；6 单测 + HTTP 全链路 + 浏览器 E2E 全部实测通过（a9ab157，仅分支）。
7. 治理/研究资产：docs/UI 设计系统/组件/页面地图、docs/learning、FEATURE-FINAL-VERIFICATION-MATRIX(34 Feature 九态)、FEATURE-GAP-REGISTER(GAP-01..22)、UI-FINAL-CAPABILITY-MAP、TECHNOLOGY-OPTIMIZATION-BACKLOG、资产扫描矩阵、UI 研究素材(12 参考图+31 抽帧+LFS 源视频)。
8. 生产安全：全程 8201 v5.9.9 冻结未动、生产库未碰；每次只 add 指定路径并做敏感反查；分支本地=远程 0/0。

### 【未完成 / 下次做】
- P0-接入（用户已令下次开始）：在已确认外壳内逐模块接入真实功能（总览/监测/分析/品牌资产/产出/系统 6 分组），替换占位、接通真实 API 与数据；ZBMP 侧建工作台页面本体（Step5c，范式用 ref-20260901-step5 31 帧做网页适配：分组设置卡/二级页头/半屏 sheet/连接器列表/搜索分类 Tab/全屏引导 Modal）。
- 弹层「微光」动效（柔和边缘光晕+淡入上移，120/220/320ms）尚未写进 CSS。
- 密钥「签发/列表/吊销」管理 UI 未做（后端接口已就绪，并入设置页同构侧栏 Step7）；grant 续期/多设备管理未做。
- 响应式断点 430/768/1024/1280/1440 未逐档取图（CDP 改宽不稳，需真机/新 target）；超窄 320 折行未测。
- 合 main：Step3/4/5a/5b 仍只在分支；合前需在主 worktree 跑 import+healthz+主体口径回归（确认生产不设 ZBC_DB_PATH 时行为不变），用户已确认视觉，可在接入首批模块稳定后择机合并并切 8201。
- 既有 GAP（择期，不阻塞接入）：GAP-01 统一 pytest 入口、GAP-04 三套 run-code 收口、GAP-05 调度影子转门控、GAP-06 双维度落库(禁 user_type=UGC)、GAP-07 事件三类四关系、#rightPanel 假数据接真实、侧栏搜索与 Ctrl+K 合并、253 条空正文补抓、8 条脏相对时间归一。
- 环境/运维遗留：8200 legacy 重复实例清理待授权；cloudflared 临时公网当前未开；固定域名/服务器与 Docker 落地未定；小红书当前 BLOCKED 熔断、按用户令暂停采集，恢复时点待定。

---

## Step5c｜ZBMP 工作台视图架构 + 统一交互组件层（2026-09-01，仅 ui/staging-foundation，未合 main）

### 目标（用户指令）
"先把整体大系统 UI 视觉交互架构搞定"：风格用户已验收 OK 不推翻；本轮立起双工作区视图架构 + ZBMP 工作台 IA 骨架 + 统一交互组件层；模块先用诚实占位（下轮接真实数据），CTH 业务 DOM 不碰。ZBMP 全程对标手机录屏 ca72d2a…raw.mp4 的流程质感做**网页适配**（不照抄深色/手机尺寸）。

### 改了什么 / 哪些文件（新增 2、改 2）
1. **新增 static/css/zbmp-workbench.css（v1.0.2，约 14.6KB）**：双工作区切换（body[data-workspace=zbmp] 隐藏 CTH .side-nav、显示 .zbmp-nav；#zbmpView 独立 fixed 主区）、ZBMP 独立侧栏、二级页头（圆形返回+标题+副述，sticky 毛玻璃）、Home 工作台（logo+整宽搜索+分组 tile 网格 auto-fill minmax218）、分组设置卡 .zb-group/.zb-card/.zb-row、iOS 风格 .zb-switch（开 success 绿/关 stone）、分段 .zb-seg、连接器 .zb-connector、诚实空状态 .zb-empty、右侧半屏 .zb-sheet（遮罩+大圆角抽屉+全宽主/次胶囊按钮）、微光动效 @keyframes zbHalo（弹层边缘光晕+淡入）/zbFadeUp（页面淡入上移 260ms）、@760 手机适配（主区 left0、tile 两列、sheet 全屏）。
2. **新增 static/js/zbmp-workbench.js（v1.0.0，约 22.5KB）**：IIFE 防重；ZBMP 6 分组 IA（概览/品牌[品牌资产·竞品监控·案例库]/监测[内容监测·话题战役]/洞察[事件中心·事件关系·AI 评估]/产出[报告中心]/系统[连接器·工作区设置]）；注入独立侧栏与 #zbmpView；内部路由（侧栏/tile→模块、圆形返回→Home）；连接器页真实平台适配器范式（小红书 PRIMARY 橙点"暂停/熔断保护中"、抖音 SECONDARY disabled、微博/B站/快手知乎贴吧 future 灰点）；设置页 4 分组卡（外观/通用/安全与访问/关于）+ toggle 交互；**密钥管理 Sheet 接 Step5b 真实后端**（GET keys 列表含有效/已吊销状态点、POST 签发明文仅一次、revoke 吊销）；其余未接入模块统一 .zb-empty 诚实占位（"Core 能力已具备·正在接入工作台"/"规划中"，不展示任何编造数字）。
3. **改 static/js/zbip-shell.js（v1.0.7→1.0.8）**：setWorkspace 内新增 `window.dispatchEvent(new CustomEvent('zb:workspace'))`，作为外壳→工作台的唯一切换信号（仅 +1 行逻辑，不改 CTH 任何行为）。
4. **改 static/index.html**：在 shell 层后引入 zbmp-workbench.css/js（均标 [STAGING ONLY]、注明回滚=删引用），shell 引用 bump 1.0.8。
- 回滚：删除 index.html 两行引用即完全恢复，不改源 DOM 顺序/后端/DB。

### 为什么（机制）
沿用 Strangler 增量层路线：CTH 业务视图与 ZBMP 工作台**物理共存、按 data-workspace 显隐**，进入 ZBMP 时 #zbmpView 不透明覆盖 .content、返回即恢复 CTH 原状态，因此不重写、不拼旧选择器、零业务 DOM 改动；组件全部只引用 --zb-* token，不新增随意颜色。

### 数据库 / 迁移
**无变化、无迁移**。本轮纯前端；密钥 Sheet 仅读取/调用 Step5b 已建的 v4_workspace_keys/v4_workspace_grants（a9ab157），Staging 副本库未改结构，生产库未碰。

### 测试与真实结果（已实测，浏览器真实加载 + DOM 断言 + 双视口截图）
- 双工作区切换：初始 body[data-workspace]=cth、zbmpView/nav 已注入但隐藏、CTH side-nav flex；已授权会话点 ZBMP→data-workspace=zbmp、zbmpView flex、CTH side-nav none、独立 zbmp-nav flex、Home 标题与 11 tile/11 侧栏项正确（未授权会话弹密钥门为 Step5b 既有行为，本轮复测一致）。
- 内部路由：连接器 5 平台行、设置 4 分组 9 行 2 toggle、toggle aria-checked true→false 可切、events 等未接入模块显示诚实空状态与标签、圆形返回回 Home 恢复 11 tile。
- **密钥 Sheet 真实打通后端**：打开后从副本库读到 2 把 key——#2 browser-e2e 有效（绿点）、#1 http-smoke 已吊销（灰点），含 key_prefix/最近使用/#编号/吊销按钮，证明 Step5b 后端与新管理 UI 闭环（未在本轮新签发，避免产生多余测试 key）。
- 自修 1 个真实样式 bug：设置行右值"跟随系统/14/13"被 flex 压缩成 56×56 逐字竖排（inline-flex 内匿名 CJK 文本节点的 flexbox 断行坑），定位到 flex:0 0 auto 仍因匿名 item 被压后，改 .rv 为 inline-block+nowrap，复测全部右值单行（offsetHeight 19–20、首个 71px 宽）水平对齐。
- 返回闭环：ZBMP→设置→"返回 CTH-POMS 工作区"→data-workspace 回 cth、zbmpView none、CTH side-nav flex、CTH 业务视图/KPI 仍在（CTH 零破坏）。
- 手机 390（CDP setDeviceMetricsOverride 实测后已 clear）：汉堡顶栏、整宽搜索、tile 两列、分组标题、状态点、无横向溢出。
- 静态/健康：node --check 两个 JS 均 OK；8301 /healthz ok v5.9.9；**8201 生产 /healthz 全程 ok v5.9.9 冻结未动**。
- 证据截图：docs/UI/evidence/step5c-home.png、step5c-settings.png（修复后）、step5c-keysheet.png、step5c-connectors（页面已实测）、step5c-home-390.png。

### 未实测 / 遗留（如实）
- 430/768/1024/1280/1440 断点未逐档取图（本轮仅桌面 1066 与 390）；超窄 320 未测；连接器页未单独存图。
- 设置页外观组（主题/强调色/字号）目前是范式静态行（弹层选择器下轮做），高密度/微交互两个 toggle 仅本地态、尚未持久化到配置。
- 除连接器/设置外 9 个模块均为诚实占位，**下轮主线=逐块接真实 API/数据**（接入一个实测一个）。
- ZBMP 下顶栏仍露出 CTH 全局操作按钮（采集数据/AI 分析/导出报告），下轮按工作区做显隐/语义区分。
- Step5b 遗留不变：grant 固定 12h、续期/多设备管理未做。

### Git
- 本轮提交见本次 commit（ui/staging-foundation）；生产 main 与 8201 全程未动；合 main 仍待用户验收 + 主 worktree import/healthz/主体口径回归。
- 红线自检：未碰 SUBJECT_WORDS/EXCLUDE/subject_hit/_subject_sql_and_values/aggregate_events/build_daily_report/risk_engine；未混淆 publish_datetime/captured_at；未改 DB；AI 仍 Ollama-only 增强层；未提交 .env/*.db/cookie/token/profile。

---

## Step5d｜ZBIP 统一收敛母规范同步 + Design Token 双主题/动效/Icon 增量（2026-09-01，仅 ui/staging-foundation，未合 main）

### 触发与性质
用户下发《ZBIP 四产品统一「架构/规则/UI视觉/交互」收敛指令》：一套母规范 + 各产品按职责适配（不是做成一样）；明确为 **4 仓库 / 5 身份**（CTH-POMS、ZBMP 同处 Z-Brand-Core；DCC；SICI=手机执行端；新增 AI-D=研究学习中枢）；六阶段（读取→收敛 Map→Design Token→开发→测试→交付），禁止跳过架构收敛直接大改 UI。用户既有指令 DCC/SICI 本轮不动，只做 Z-Brand-Core 内属于 CTH/ZBMP 的部分。

### 改了什么 / 文件（新增 1 文档、改 3 前端、2 证据）
1. **新增 docs/ZBIP-UNIFIED-CONVERGENCE-BASELINE.md（母规范 v1.0）**：4仓5身份与职责、统一六层架构、六阶段、UI母规范（色彩/字/圆角/边框/线性Icon/**Light-Dark**/Mobile-first/交互语言/Motion 区间）、WHO-WHAT-WHY-ACTION 页面架构、五产品布局差异、生产/AI/采集/Browser Surface 红线、ZBC 落地映射、Evidence 固定字段、**登记 4 项命名/结构冲突待用户拍板（不自行全局替换）**、本轮范围声明。
2. **改 static/css/zbip-tokens.css（v1.0→v1.1.0）**：
   - 新增 **Dark 主题语义别名层** `:root[data-theme="dark"]`：primitive Stone 色阶不动，只重映射 bg/surface/border/text/brand 与六语义（前景提亮、弱底弱边改半透明）、深色阴影、color-scheme；**默认无 data-theme=Light，零视觉变化**；切换 = documentElement 设 data-theme。
   - Motion 增补（不改已验收现值）：--zb-dur-quick 140ms（快速100-180）、--zb-dur-sheet 360ms（Sheet280-420）、--zb-ease-spring 轻物理弹簧；reduced-motion 同步关闭。
   - 线性 Icon Token：--zb-icon-stroke 1.75px / size sm14·md18·lg20 / cap·join round。
   - Mobile-first：--zb-safe-*（env safe-area-inset）与 --zb-bottomnav-h 56。
3. **改 static/zb-preview.html**：组件画廊加 Light/Dark 切换（localStorage 记忆），作为双主题隔离验证面，不碰业务页；tokens 引用 bump 1.1.0。
4. **改 static/index.html**：主站 tokens 引用 bump 1.1.0（默认仍 Light、零外观变化）。
5. 证据：docs/UI/evidence/step5d-gallery-dark.png、step5d-gallery-light.png。

### 为什么（机制与边界）
- 母规范要求"先 Token 再页面"。本轮只在**唯一 token 真相层**增量，不重写组件、不改业务页；Dark 只重映射语义别名，故只有"全程引用 --zb-* 语义别名"的组件自动跟随，写死颜色的旧组件不强行套 Dark（逐组件迁移、回归后启用），避免一次性变色风险，回滚=移除 data-theme / 还原 tokens。
- 命名结构差异（ZBP 中间层去留、SICI 职责迁移、AI-D 归属）按指令"冲突先 STOP 登记"处理，**未改 PRODUCT_NAMING_BASELINE、未做全局替换**。

### 数据库 / 迁移
无变化、无迁移；生产库与 Staging 副本库均未改结构。

### 测试与真实结果（已实测）
- 画廊默认无 data-theme=Light：--zb-bg #FAFAF9 / text #1C1917 / surface #FFFFFF（与验收基线一致）。
- 点 Dark：data-theme=dark，--zb-bg #171411 / text #F5F5F4 / surface #211D1A / brand #F5F5F4；主按钮计算背景 rgb(245,245,244)（黑底近白），body 渲染 rgb(23,20,17)；六语义状态点在深底清晰；新 token icon-stroke 1.75px / sheet 360ms / safe-bottom 0px 均生效。
- 点 Light 完整恢复 #FAFAF9；主站 8301 默认无 data-theme、--zb-bg #FAFAF9、data-workspace=cth，**Step5c 工作台 Light 零回归**。node 侧无 JS 改动。
- **如实登记（NOT_VERIFIED/后续）**：components.css 中 disabled/loading/icon-btn 等少量组件在 Dark 下仍呈浅色（写死色值、未全用语义别名），本轮按"不扩大范围"不强改，登记为 Dark 逐组件迁移项；业务旧页面未套 Dark（符合设计）。
- **运维（非代码改动，如实记录）**：开机/休眠后 8301 与 8201 的 Python 进程均已退出（9222 生产浏览器 profile 仍活）。按隔离环境重启 Staging 8301（独立副本库、XHS_CDP_URL 空、WEB_DISCOVERY 关）；按生产方式用 run_supervised.py 恢复 8201（主 worktree、不设 ZBC_DB_PATH=生产库、0.0.0.0:8201）。恢复后双口 healthz 均 ok v5.9.9 且稳定共存；8200 legacy 两实例按约定未动。启动时序上 8201 supervised 拉起瞬间曾使先起的 8301 退出一次，清理残留后重启 8301 即稳定（记录为环境注意项）。

### 未实测 / 遗留
- Dark 仅在隔离组件画廊实测；**业务页 Dark 未启用也未逐页取图**（需先完成组件写死色迁移 + 业务页语义别名化，属后续任务）。
- 430/768/1024/1280/1440 断点、Bottom Nav/Sheet/Swipe 等 Mobile 交互仍待逐页落地（本轮只补 token）。
- 4 项命名冲突（C1 ZBP 中间层去留 / C2 SICI 职责迁移 / C3 AI-D 仓库归属 / C4 ZBMP 中文定名）待用户裁决，裁决前以现命名基线为准。
- Step5c 遗留不变：9 模块仍为诚实占位，下轮逐块接真实 API。

### Git / 生产安全
- 本轮提交见本次 commit（ui/staging-foundation）；生产 main 未动；8201 恢复后 v5.9.9、主体口径/采集/AI/DB 全部未碰；不提交 .env/*.db/cookie/token/profile/日志。

---

## Step5e｜ZBMP 模块接入第一批（事件中心/内容监测真实数据）+ 五身份命名裁决 + AI-D 研究路线（2026-09-01，仅 ui/staging-foundation，未合 main）

### 用户裁决（命名）
- C3：**AI-D 独立 Git 仓库**做 AI 研发、重度深化，目标让 Zachary 尽早独立为 AI；C2：SICI 转手机执行端、研究职能移交 AI-D，**同步研究但暂不改 SICI 代码**；C4：ZBMP 中文名固定「Z-Brand 品牌监测平台」；C1：先盘点 ZBP 功能面再定去留（已在母规范附完整盘点 + 建议保留为逻辑分组，待最终确认，未全局改名）。

### 改了什么 / 文件
1. static/js/zbmp-workbench.js（v1.0.0→v1.0.3）：新增 renderEvents / renderContent，复用 Core 现有 `/api/events`、`/api/notes`（**不新增后端**）；通用 esc 转义（笔记为用户内容，防 XSS）、riskMeta 风险映射、骨架屏加载、失败显式错误态（**不伪装 0 条**）、小结条；Home 中 events/content 状态 core→live。
2. static/css/zbmp-workbench.css（v1.0.2→v1.0.4）：新增 .zb-statstrip/.zb-stat、.zb-list/.zb-li 数据列表、.zb-mini-tag、骨架屏 shimmer；修页头窄屏标题换行（h2 nowrap、sub ellipsis）。
3. static/index.html：bump workbench css/js 版本。
4. docs/ZBIP-UNIFIED-CONVERGENCE-BASELINE.md：§9 冲突段改为「用户裁决」，补 ZBP 功能盘点与 4 仓 5 身份关系。
5. 新增 docs/AI-D-RESEARCH-ROADMAP.md：AI-D 定位/边界、Zachary 自主度 L0-L5、研究能力栈、研究流水线、M0-M5 里程碑、红线、与 SICI 分工。
6. 证据：step5e-events.png / step5e-content.png / step5e-events-390.png。

### 为什么
按"接入一个、实测一个"推进，先接 Core 数据最现成的事件与内容；只在 ZBMP 工作台层渲染既有 API，不碰 CTH 业务 DOM、不改后端/DB/采集/主体口径，回滚=移除这两个 render 分支。

### 数据库 / 迁移
无变化、无迁移；只读调用现有 API，Staging 副本库与生产库结构均未改。

### 测试与真实结果（已实测，8301）
- 事件中心：小结 事件总数 50 / 活跃 50 / 高中风险 **3/41** / 已证实 50；50 条真实事件（方所闭店、OLE 员工投诉、餐饮安全等），高风险红点、中风险橙点、日期/提及/来源/状态/证实标签齐全。
- 过程自抓自修 1 个真 bug：riskMeta 正则用 "mid" 未匹配到 "medium"（medium 不含连续子串 mid），中风险被误判灰点且显示英文原文；补 "med" 后复测 3/41、橙点、文案"中风险"正确。
- 内容监测：命中总量 **604**、本页/总页 1/21、负面/官方 0/0、本页互动 1627；30 条真实小红书笔记，**时间取 publish_datetime（如 2026-08-30），缺失标"发布时间未知"，绝不用 captured_at 顶替**；互动数按"线性 icon、正式 UI 不用 emoji"要求由 ♥💬★ 改为"赞/评/藏"文字；外链 target=_blank rel=noopener；用户笔记原文自带 emoji 属真实内容予以保留（已 HTML 转义）。
- 390 手机（CDP，测后清除）：小结 2×2、列表卡片全宽、无横向溢出（scrollWidth==innerWidth）、页头标题单行（h2 高 20px）副标题省略。
- node --check 通过；8301 healthz v5.9.9。

### 未实测 / 遗留
- 430/768/1024/1280/1440 断点未逐档取图（本轮 1066 与 390）；内容分页交互（翻到第 2 页）、服务端筛选/排序尚未接（当前仅首 30 条展示）。
- 其余 7 个 ZBMP 模块仍为诚实占位（竞品/案例库/话题战役/事件关系/AI 评估/报告中心等），下一批建议接 报告中心 + 事件关系（event_graph 已有 16 事件/1 关系）。
- C1 ZBP 中间层最终命名、AI-D 仓英文命名与远程创建待用户确认；C2 SICI 迁移仅研究、未改代码。
- components.css 少量写死色组件的 Dark 迁移仍挂起（Step5d 遗留）。

### Git / 生产安全
- 本轮提交见本次 commit（ui/staging-foundation）；生产 main 未动；8201 v5.9.9 正常、主体口径/采集/AI/DB 未碰；不提交 .env/*.db/cookie/token/profile/日志。

---

## Step5f｜feat/zb-runtime-preflight 合 main + 回归自动巡检修复 + ZBMP 第二批模块接入（事件关系/报告中心）（2026-09-01）

### A. 特性分支 feat/zb-runtime-preflight 安全合并 main（用户点名）
- 三 worktree 布局确认：MAIN(D:\Taikoo-monitor-new, main)、STAGING(D:\Taikoo-staging-ui, ui/staging-foundation)、SECURITY(D:\Taikoo-security, feat/zb-runtime-preflight)。
- 合并前独立审查：该分支 3 commit、**纯增量 874 行/0 删除**（runtime_preflight.py 335 + data_boundary.py 224 + tests 153 + 2 份治理文档 + app.py 仅 +11）。app.py 接入点为启动时 try/except 调 run_preflight()，**默认只记录 Attestation 不阻断**，仅 ZBC_PREFLIGHT_ENFORCE=1 且存在 P0 才 SystemExit；新模块 subprocess 仅用于只读 `git rev-parse`，写操作只涉及自建临时探针与 attestation，无删库/DROP/网络外发/eval。
- 合并前主 worktree 基线：healthcheck EXIT=0、ok=true、主体 gz_hit/sh_excluded=true、notes 957（首次 exit 1 系 `Select -Last` 截断管道 BrokenPipe，非测试失败，无截断重跑 EXIT=0 证实）。
- `git merge --no-ff` 成功（merge commit **ccd22b6**，ort 策略无冲突）。
- 合并后主 worktree 回归：py_compile app.py+2 新模块 EXIT=0；pytest test_runtime_preflight **24 passed**；实跑 run_preflight=总体 PASS/P0 阻断 0/警告 0、data_boundary 扫 1042 跟踪文件无凭证/DB 入库；healthcheck 回归 EXIT=0 主体口径仍 true。
- 隔离冷启动：临时 8302 + Staging 副本库 + 不设 ENFORCE，真实启动打印整块预检（8 项全 ✓，正确识别 DB=ISOLATED_STAGING、XHS_PRODUCTION=False）、healthz 200 后关闭；**现网 8201 全程在线零影响**（合并只改磁盘文件，不重启在跑进程）。
- 已 push origin main，main=origin=**ccd22b6** 0/0，敏感反查空。特性分支 feat/zb-runtime-preflight 保留（未删，本地在 SECURITY worktree 检出、远程保留）。

### B. 回归自动巡检在 Staging 的两个修复（确认生效，非本窗口改动）
- 7368944（DB 连接统一 db.DB_PATH）：此前登记的 Staging 4 个 500（/api/negative/pending、/api/negative/stats、/api/export/preview?period=weekly）本轮复测**全部 200**，ENV 问题闭环。
- 448e611（单模态收敛，负面待确认改非阻断 toast、待审写侧栏 badge，bump ui_interactions 8.0.1）：代码已在分支，未改业务口径。
- 自动巡检另补 GPT-iOS 逐帧分析素材（analysis-0901-gpt transA-F/frames3s）与 launch-screens（CTH/ZBMP 桌面+移动启动页原型），仅研究/原型资产。

### C. ZBMP 第二批模块接入（事件关系 graph、报告中心 reports）
- static/js/zbmp-workbench.js（v1.0.3→v1.0.5）：新增 renderGraph / renderReports，复用现有 `/api/event-graph/stats|events|types`、`/api/reports`、`/api/report/v2/stats`（**不新增后端**）；通用 getJSON/typeChips；GROUPS 中 graph/reports 状态 core→live。
- **严守不造假**：Staging 副本库 event_graph 与 reports 均为空（生产库才有 16 节点/1 关系与历史报告），两模块不灌假数据——事件关系展示真实「三类事件（营销/传播/舆情）× 四关系（触发/衍生/继发/并行）」字典 + 统计条，节点空则诚实标注"Staging 副本未同步、生产已有，切生产即出图"；报告中心展示真实统计指标（负面确认率 14.3%、已确认/待确认 1/3、今日纳入 0）+ 报告口径卡（daily_filter/age_classification/negative_confirmation/logic_explanation 真实系统规则，含"负面须 negative_confirmed=1 才进报告"），报告列表空则诚实标注，**不自动 POST 生成**。
- 已实测（8301）：事件关系 4 stat（节点0/连线0/类型3/关系4）+7 chips + 诚实空态；报告中心 4 真实指标 + 4 类型 chip + 口径卡（536 字符真实规则）+ 诚实空态；node --check 通过；三接口 200。证据 step5f-graph.png / step5f-reports.png。

### 未实测 / 遗留
- 事件关系的真实图谱**可视化（节点-连线画布）**尚未做：当前是类型体系+列表框架，等接入生产 event_graph 数据后再做力导向/关系图渲染（Staging 无数据无法验证画布，不提前造假图）。
- 报告列表 item 字段因 Staging 无报告未在真实数据上验证渲染（已做保守字段兜底，生产出报告后复核）。
- 430/768/1024/1280/1440 断点本批未逐档取图（桌面 1066 已测）。
- 剩余 ZBMP 占位：品牌资产/竞品/案例库/话题战役/AI 评估（竞品 planned，其余 core）；下一批建议 品牌资产 + 话题战役（topic_campaign_notes 生产有 120 条，数据现成）。

### Git / 生产安全
- main 线：ccd22b6 已推（含预检安全增强）；Staging 线本次 commit 见下；生产 8201 v5.9.9 全程未重启、主体口径/采集/AI/DB 未碰；不提交 .env/*.db/cookie/token/profile/日志。

---

## Step5g｜新增 Codex 式「底部只读终端 + 右侧文件树 + 视图菜单」（2026-09-01，用户参考图驱动）

### 需求（用户给 3 张 Codex 截图，黑框圈定）
- 下方新增**终端面板**（打开终端 Ctrl+`、切换底部面板 Ctrl+J，标签+新建+关闭+Alt 数字切标签）；右侧新增**文件树面板**（切换文件树 Ctrl+Shift+E，打开文件/筛选/目录树/文件数）；统一从**视图菜单**进入。随后继续推进 2→1→3。

### 后端：新增两个**纯只读、安全白名单**路由（app.py，纯增量，不改任何现有路由/DB/主体口径）
- `GET /api/workspace/file-tree?path=`：限定项目根、防路径穿越（resolve 后必须在根内，越界 403）、过滤敏感（.env/.venv/.git/node_modules/__pycache__/cookie/token/secret/*.db/*.key/profile 等），返回真实目录/文件/大小与「目录数·文件数」。
- `POST /api/workspace/term`：**只读 Web 终端**。白名单 ls/pwd/whoami/help/clear/python --version/git{status,log,diff,branch,rev-parse,show,remote,ls-files,count-objects}；shell=False、list 参数、cwd 锁定项目根、15s 超时；拒绝管道/重定向/命令替换/`..`、拒绝写命令与非只读 git 子命令（403 blocked）。**明确不复用**现有三套高危 run-code（/api/dev/run-code 直接 exec 任意 Python，属 GAP-04 待收口，不拿它做终端）。
- **自抓自修 1 个真 bug**：Staging 是 git linked-worktree，其内 `.git` 是**文件**而非目录，初版用 `is_dir` 门控隐藏集合导致 `.git` 文件漏出；改为「名称命中隐藏集合即隐藏，不区分文件/目录」后，.git/.venv/*.db 全隐藏、.github 正常保留（193 项）。

### 前端（纯增量，不覆盖旧 class，全 token）
- static/css/zbip-panels.css（v1.0.0）：右上视图工具条+下拉菜单、底部深色 Stone 只读终端（等宽、绿 prompt/白输出/橙拒绝语义色、标签栏、spring 上移）、右侧文件树（线性 folder/file icon、chevron 展开、大小、底部文件数）、面板打开时主内容自动让位、≤760px 抽屉化、prefers-reduced-motion 兜底。
- static/js/zbip-panels.js（v1.0.0）：轮询挂载到 #zbmpView（仅 ZBMP 生效，CTH 视图不触发）；文件树懒加载子目录+当前层筛选+真实文件数；终端多标签会话、Alt+数字切换、回车走后端白命令；快捷键 Ctrl+`/Ctrl+J 终端、Ctrl+Shift+E 文件树、Esc 关菜单、外部点击关菜单。
- static/index.html：各 +1 行 link/script（panels css/js 跟在 workbench 之后）。

### 已实测（8301，证据 step5g-files/term/files-390.png）
- 文件树：根 20 目录/173 文件/193 项；static 懒加载展开出 css/img/js/launch-screens 与文件大小；data 层 *.db/cookies 被过滤；路径穿越 ../../../Windows → 403。
- 终端：help 出帮助；git rev-parse 真实返回 33aca48；ls 真实列目录（[D] 标目录）；python --version=3.13.15；git push / rm -rf / 管道 / python -c / npm i / cd .. 全部 403 拒绝（前端橙色提示，不执行）；新建标签/Alt 切换/clear 正常。
- 视图菜单三项+快捷键正确；主内容自动让位无遮挡；390 无横向滚动、面板抽屉化。
- 回归：tests/healthcheck.py ok=true、9 模块 ok、主体 gz_hit/sh_excluded=true；/healthz、/api/overview、/api/event-graph/types 全 200；node --check 通过；py_compile app.py 通过。
- **未实测/遗留**：终端暂不支持多命令历史上下键（↑↓）与自动补全；文件树递归总文件数（当前为"当前层"计数，非全仓递归，避免大目录开销）；文件点击仅展示、未做只读文件内容预览（下一批评估，仍需过滤敏感）；430/768/1024/1280/1440 断点未逐档。

### Git / 生产安全
- 本次为 Staging 分支 commit（见下），新增后端路由为纯只读增量，合 main 前将在主 worktree 再跑 import+healthz+主体回归；生产 8201 v5.9.9 全程未动；不提交 .env/*.db/cookie/token/profile/日志。

---

## Step5h｜事件关系升级为「三列分层关系画布」（②号任务，2026-09-01）

### 改动（纯前端，不新增后端、不改 DB）
- static/js/zbmp-workbench.js（v1.0.5→v1.0.8）：renderGraph 节点列表替换为自研 drawGraphCanvas——营销/传播/舆情三列分层定坐标，SVG 底层画带箭头关系连线 + 关系名胶囊标签，HTML 节点卡（类型左边框色、标题两行截断、event_time、risk 小标、关系数）；跨列贝塞尔连线、**同列垂直连线**（自抓自调：唯一真实关系为同列，初版绕边走线不佳，改为底→顶直线+下箭头）；四关系语义色（触发 danger/衍生 info/继发 stone/并行 attention），颜色之外同时有中文关系名（颜色非唯一信息）；暴露 window.__zbDrawGraphCanvas 只读渲染钩子用于真实数据验证。无第三方图形库。
- static/css/zbmp-workbench.css（v1.0.4→v1.0.5）：.zb-graph-* 画布/列头/节点卡/边标签/图例/风险标，全部走 token，≤760 横向滚动。
- static/index.html：bump workbench css/js。

### 已实测（真实数据，证据 step5h-graph-canvas-real.png）
- Staging 副本 event_graph 为空：正式页面仍显示**诚实空状态**（不回归、不造假，文案提示切生产即出图）。
- 为真实验证画布算法，以 **mode=ro 只读**连接生产库导出 16 节点/1 关系（传播13·舆情2·营销1）为临时 JSON，仅在浏览器 console 调渲染钩子验证后即弃，**不写入任何库、不提交该 JSON**（git status 已反查无 eg_real/_eg_export 痕迹）。
- 实测：16 节点全部绘制、三列列头与计数正确（营销1/传播13/舆情2）、1 条 trigger 路径与"触发"标签正确、risk low/medium 标签、图例四关系齐全；node --check 通过。
- **登记 1 条源数据质量问题（非 UI bug）**：营销列唯一节点 title 在生产库中本身为 `?????15???????` 乱码（event_time 亦为完整时间戳 2026-08-31 07:20:29），画布如实呈现；建议后续在数据治理侧排查该条 import 编码，不在 UI 层掩盖。

### 未实测/遗留
- 生产真实页面出图需等 UI 合 main 切 8201（或同步 event_graph 到 Staging 副本）后截图归档；画布拖拽/缩放/节点点击下钻（跳事件详情）未做，下一批；跨多列复杂网状关系（当前生产仅 1 条边）布局压力未充分验证。

### Git/生产安全
- Staging 分支 commit（见下）；app.py/DB/采集/主体口径本轮零改动；生产 8201 v5.9.9 未动；不提交 .env/*.db/cookie/token/profile/日志与生产业务数据。

---

## Step5i｜品牌资产 + 话题战役真实接入（①号任务，2026-09-01）

### 改动（纯前端，不新增后端、不改 DB）
- static/js/zbmp-workbench.js（v1.0.8→v1.1.0）：GROUPS 中 brands/campaign 由 core 占位改 live；render() 增分发；新增两个真实渲染：
  - renderBrands：并取 /api/brands + /api/brand-stats + /api/brand-knowledge/stats。statStrip（场内品牌/业态分类/太古汇在场/知识库条目）+ 业态分布 chips + 品牌知识库分类 chips + 品牌列表（中文名/英文名/品类/楼层铺号/在场标）；brand_cn 为 '-' 占位时 fallback 到 brand_en（自抓自修）。
  - renderCampaign：并取 /api/topic-campaign/{status,campaigns,topics,stats,notes}。statStrip（战役笔记/总互动 w 缩写/监测话题/平均主体命中率）+ 当前战役卡（名称/周期/状态/间隔/最近采集）+ 分话题表现（主体命中 x/y、命中率%、完整证据、风险、运行）+ 最新战役笔记（作者、正文摘要、赞评藏）。新增 fmtEng 数字缩写。
- static/index.html：bump workbench.js。

### 已实测（真实数据，证据 step5i-brands / step5i-campaign / step5i-campaign-390）
- 品牌资产（1066）：场内品牌 50、业态分类 9、太古汇在场 50、品牌知识库 103 条；业态 chips（女装48/珠宝钟表35/餐饮41…）、知识库分类（品牌案例40/危机公关14/品牌营销21…合计103）、品牌列表含路易威登/迪奥/古驰等真实楼层铺号；'-' 占位 fallback 后无破折号标题。
- 话题战役（1066）：战役笔记 120、总互动 6.1w、监测话题 7、平均主体命中率 49.2%；战役「广州太古汇十五周年 2026-08-28~10-07 paused 间隔240分」；分话题 #广州太古汇15周年 28/60(46.7%)、#广州太古汇十五周年 31/60(51.7%)，完整证据 49/45；最新笔记 Koieee/Chelseaci/半斤佳(赞4118) 等真实正文与赞评藏。
- 390 手机（CDP）：两模块 stat 两列、无横向滚动（scrollWidth 不超 390）、'-' 标题归零。
- node --check 通过；不新增后端路由。

### 未实测/遗留
- 品牌列表未做分类筛选/搜索/分页（当前 50 条一次渲染可接受，品牌增多后补）；品牌健康度/画像详情下钻未做；战役笔记正文 comments_json 未展开（仅摘要）；战役 run/recover 等写操作未接（只读优先）；390 顶部「终端/文件/视图」工具条与页标题略挤，列入全局交互精修（窄屏收进溢出菜单）。

### Git/生产安全
- Staging 分支 commit（见下）；app.py/DB/采集/主体口径零改动（分话题主体命中率直接展示 Core 主体过滤结果，不重算不改写）；生产 8201 v5.9.9 未动；不提交 .env/*.db/cookie/token/profile/日志。

---

## Step5j｜③全局交互精修第一批 + 修复 Step5g 遗留 CSS 截断 bug（2026-09-01）

### 关键 bug 自抓自修（重要）
- 现象：390 窄屏面板工具条始终显示「终端/文件/视图」文字，窄屏规则不生效。
- 定位过程：禁缓存/换 query/重启 8301 均复现 → 浏览器 CSSOM 枚举发现 **zbip-panels.css 解析到 `.zb-tree-row .sz`（行73）后整段中断，其后规则（.zb-tree-children/.zb-files-foot/面板打开让位/两个 @media）全部未进入 CSSOM**。
- 根因：行73 `color:var(--zb-text-muted,#A8A29E` **漏写右括号 `)`**，浏览器进入未闭合 var() 后把后续全部内容当函数参数吞到文件尾。此前自检脚本只统计花括号/注释、未统计圆括号故漏检（圆括号扫描确认该文件 balance=1，修复后归零；另两份 CSS 平衡）。
- 影响面：这是 **Step5g 即存在**的问题——文件树展开/收起、footer、面板打开主内容让位、≤820 抽屉化、prefers-reduced-motion 实际一直未生效（Step5g 当时部分能力靠 JS 内联呈现，误判为通过）。本轮补 `)` 后全部恢复，并补一个圆括号平衡检查脚本以防复发。

### 本批精修（纯前端）
- ZBMP 工作区隐藏 CTH-POMS 生产按钮：body[data-workspace=zbmp] 下 #refreshBtn/#reviewBtn/#reportBtn/#rednoteBtn display:none（搜索/预警保留）；切回 CTH 自动恢复。已实测。
- ZBMP 页面切换轻量淡入上移（220ms，遵循 reduced-motion 关闭）。
- 侧栏项/列表链接/节点卡 :focus-visible 焦点环（键盘可达）；导航项 active 微反馈。
- ≤820（原760 上调）面板工具条只留 34×30 线性图标方形按钮（id 级特异性 + font-size:0 双保险压过历史 CSS 层）、statStrip 强制两列、页头收紧。
- 文件：zbip-panels.css(v1.0.0→v1.0.3)、zbmp-workbench.css(v1.0.5→v1.0.6)、index.html bump。

### 已实测（证据 step5j-desktop-files / step5j-files-drawer-390）
- 桌面 1066：工具条正常带文字；文件树打开并展开 static（css/img/js/launch-screens + 文件大小），footer「目录20·文件173·共193」，主内容让位不遮挡；ZBMP 下采集/AI分析/导出按钮隐藏、搜索保留；Home 模块状态点（可用/规划中/接入中）正确。
- 390（CDP，先开页后模拟）：matchMedia820=true、.lbl computed display=none、按钮 34px、CSSOM 820 媒体块=1、.zb-tree-children 规则恢复=1；文件树为 84vw 抽屉；stat 两列、无横向滚动。
- node --check 通过；三 CSS 圆括号/花括号平衡归零。

### 未实测/遗留
- 430/768/1024/1280/1440 断点仍未逐档取图；顶部 topbar 在 ZBMP 仍显示 CTH 系统标题（纯文本，下批按工作区分发标题）；终端 ↑↓ 历史/Tab 补全、文件点击只读预览、侧栏搜索与 Ctrl+K 命令面板合并仍挂起；CDP mobile 截图偶发重绘叠影（模拟器合成问题，DOM 断言为准）。

### Git/生产安全
- Staging 分支 commit（见下）；app.py/DB/采集/主体口径零改动；排查中仅重启过 8301 Staging（标准副本库 env），**生产 8201 四进程全程未动**（重启前后 healthz 均 ok v5.9.9）；不提交 .env/*.db/cookie/token/profile/日志。


---

## 2026-09-01 17:55 · UI 线并入 main + Feature 矩阵刷新（阶段1/2）

### 本次做了什么
1. **ui/staging-foundation(Step1–Step5j) 并入 main**：合并前基线 74 passed；merge 仅 static/index.html 一处冲突（app.js 版本号 + main 独有 modal_simplify.js，两者都保留），app.py 自动合并。期间自动巡检以线性快照带入合并内容，补 `-s ours` merge commit 记录拓扑（零内容改动）。
2. **合并后回归**：规范用例 **80 passed**（50 + runtime_preflight 24 + workspace_keys 6），tests/test_css_balance.py CSS 结构平衡全绿，py_compile/191 路由通过。
3. **8301 合并版实测**（ISOLATED_STAGING 副本库，生产 8201 未重启）：Preflight 总体 PASS/P0=0/DB 隔离；CTH Home 侘寂壳与完整线性导航正常；ZBMP 密钥门解锁成功；话题战役 120/6.1w；事件关系 16 节点三列（营销1/传播13/舆情2）四关系图例真实渲染；file-tree/term 两只只读路由命中；main 的键盘快捷键/预检与 staging UI 共存无冲突。
4. **三线对齐**：main = ui/staging-foundation = origin/main = `580c2cf`（0/0），长期分叉消除。
5. **FEATURE-FINAL-VERIFICATION-MATRIX 刷新**：34 → **44 条**（补登 ZBMP API Key、ZBMP 六组工作台、ZBIP 设计系统、只读工程面板、runtime_preflight、unified_logger、键盘快捷键、适配器基座、report_center、Global BIL）；计数 ACTIVE25/DEVELOPING11/EXPERIMENTAL4/PLANNED3/RESERVED1；GAP-03 标 RESOLVED、GAP-05 标已签字施工中。

### 云端 AI（ark/ai_gateway）评估结论（用户已同意）
保持 Legacy 默认关、不全局开启。后续按 AI Provider 化做可选通道：默认 Ollama，仅公开非敏感内容可手动单次切云端（脱敏+审计），客户敏感数据永不过云。登记 Backlog，本轮不打开。

### 数据库
无 schema 变更、无迁移；全程使用 staging 副本库，生产 data/monitor.db 未触碰。

### 下一步（阶段3 P1，按序）
GAP-04 三套 run-code 安全收口 → GAP-01 统一 pytest 入口 / GAP-02 红线函数级单测 → GAP-06 双维度落库 → GAP-07 事件三类四关系 → GAP-05 调度门控（已签字，feature flag 灰度+回滚）。


---

## 2026-09-01 18:10 · GAP-04 三套 run-code 安全收口（P1 安全）

### 问题（审计实测）
- `/api/developer/run` 本已硬编码 403（安全）；
- `/api/config/run-code` 用 `exec()` 服务端执行，给全量 `__builtins__/os/db`，且黑名单可被前端传 `allow_dangerous=true` 绕过=高危 RCE；
- `/api/dev/run-code` 同样 `exec()` + 备份写盘，其 javascript 分支直接把代码**追加写入 static/js/dev_custom.js**=持久化脚本注入，且无鉴权门。

### 收口（最小改动、不删路由、不削本地能力）
- 新增统一闸门 `_dev_exec_guard()`：生产默认（无 `ZBC_DEV_EXEC`）一律 403 `DEV_EXEC_DISABLED`，不 exec、不写盘、不写 static；仅本地显式 `ZBC_DEV_EXEC=1` 放行，且危险正则（import/exec/eval/文件写/网络/反射/__dunder__）仍拦 400 并打审计行。
- 三端点统一接入；移除 allow_dangerous 绕过；路由全部保留（前端得明确 403 契约而非 404）。

### 测试（已实测）
- 新增 `tests/test_dev_exec_guard.py` **9 用例全过**：生产三端点+危险 payload+JS 写文件全 403 且无副作用；开发态危险构造 400、安全算术 200（验证本地热更能力保留）。
- 全量回归 **89 passed**；8301 黑盒：三端点 + JS 分支生产态均 403。

### 数据库/生产
无 schema 变更；生产 8201 未重启；不弱化任何红线。


---

## 2026-09-01 18:30 · GAP-01 统一测试入口 + GAP-02 红线函数级单测（P1）

### GAP-01 统一 pytest 入口
- 根因：`tests/test_api_smoke.py` 顶层 `sys.exit()` 在 pytest 收集(import)阶段抛 SystemExit，导致 `pytest tests` INTERNALERROR（仅收集 26）；另有 32 个纯脚本式 test_ 文件在 import 期有真实平台/网络副作用。
- 治理（不删脚本、两种运行方式都保留）：
  1. test_api_smoke 改造为规范 `def test_` 用例（保留 `__main__` 直跑）；
  2. conftest 增加 `pytest_ignore_collect`：**全文无 `def test_` 的纯脚本默认不收集**（不 import、不执行副作用），仍可 `python tests/xx.py` 手动跑；
  3. 新增 `pytest.ini`（testpaths/markers/redline 标记）与 `tests/run_all.py` 分层统一入口（默认规范用例；`--scripts` 子进程隔离跑脚本；`--online` 放开真实平台用例）。
- 结果（已实测）：`pytest tests` 由 INTERNALERROR → **110 passed**。

### GAP-02 红线函数级直接单测
- 新增 `tests/test_redline_units.py` **19 用例全过**（0.17s，纯函数不连库）：
  - subject_hit：广州/太古汇正向命中、**上海/兴业/北京三里屯/成都远洋/深圳/香港太古汇、太古城等跨城同名一票否决**、正向+异地混合时排除优先、多字段/列表/大小写、空输入；
  - _subject_sql_and_values：正向 OR + AND NOT 排除、`?` 占位符与参数一一对应、175 LIKE=(17 正向+18 排除)×5 字段、alias 前缀、历史别名兼容；
  - build_daily_report 入口委托契约稳定。
- 残余（已登记）：aggregate_events/build_daily_report 连库段仍以集成级为主，纯函数拆分后续补。

### 数据库/生产
无 schema 变更；生产 8201 未重启；不弱化任何主体/时间/风险红线。


---

## 2026-09-01 19:10 · GAP-06 传播主体/内容双维度落库（P1，向后兼容）

### 改了什么（纯增量，5 处注入 + 1 迁移 + 6 测试）
1. `subject_classifier.py` 新增 `enrich_note_types()`：惰性单例调用现有 classifier，返回 (subject_type, content_type)，**任何异常兜底空串、绝不向采集链抛出**（不伪造类型、不影响出数）。
2. `database.py` NOTE_MIGRATIONS 幂等加 `subject_type`/`content_type` 两列（DEFAULT ''）；`migrations/010_notes_subject_content_type.sql` 留档。
3. `insert_note` 在不改动既有 INSERT 列清单的前提下，沿用现有「后置 UPDATE 补 body」同模式补双维度（新值非空才写，保护人工标注）。
4. `_apply_filters` 增加双维度**固定枚举白名单**筛选（主体 7 值 / 内容 7 值），非法值/注入串一律忽略；不接受旧 `user_type=UGC` 写法。
5. `/api/notes` 透传 `?subject_type=&content_type=`。

### 数据库 / 红线
- 仅向后兼容 ADD COLUMN，无删除、无回填、无 schema 破坏；生产库未执行（8201 冻结），**Staging 副本 init_db 两次幂等成功（67 列）、957 条历史双维度默认空串、计数不变**。
- 不触碰 subject_hit/_subject_sql_and_values/风险/统计/时间口径；双维度为纯增强标注层。

### 测试（已实测）
- 新增 `tests/test_subject_dual_dimension.py` 6 用例全过（纯函数/异常兜底/迁移幂等/落库/白名单筛选与注入忽略/主体红线不回归）。
- 统一入口 `pytest tests`：**116 passed**。

### 残余（登记）
classifier 现仅按主体类型映射 content_type_hint；review/experience/complaint/event 等基于正文的细分内容识别为后续增强，本轮不扩分类器。


---

## 2026-09-01 19:50 · GAP-07 事件三类四关系补全（P1，不伪造）

### 事实
- 字典层本就完整：EVENT_TYPES 三类（营销/传播/舆情）、RELATION_TYPES 四类（trigger/derive/follow/parallel）；缺口是 `import_from_existing_events` 只导节点、**不建任何关系**，故 16 事件仅 1 条手工 trigger。

### 落地（event_graph.py + app.py + 5 测试）
1. 新增保守推断器 `EventGraph.infer_and_link_relations()`：**时间 + 标题主题词双证据**。
   - parallel：|Δt|≤36h 且主题相关；derive：0<Δt≤21d 且强主题延续(≥3 共享 bigram)；follow：先后弱相关(1-2)；
   - **trigger 属强因果，不自动生成，保留人工/直接证据**；时间不可比或无主题重叠一律不连边。
   - 自动关系 evidence 以 `[auto]` 开头，重算只清自动、保留手工；(source,target,type) UNIQUE 幂等。
2. 主题证据**只用 title**：真实数据验证发现 description 是自动摘要样板（“事实/仅能/仍需”套话）会造成 78 条伪全相连；同时先整体剔除“广州太古汇/太古汇”全域通用名、扩充样板停用 bigram，消除“州太/汇啦”跨界噪声。
3. 新增 `POST /api/event-graph/rebuild-relations`（参数校验、只读统计回传）。

### 真实结果（Staging 副本，已实测；生产库未碰）
- 修正前 78 条伪并行 → 修正后 **16 事件仅 3 条有证据并行**：IWC进驻↔新店启幕IWC(iwc)、会员服务讨论↔会员看过来(会员)、济州岛漂亮饭↔打卡漂亮饭(漂亮)；加原手工 trigger 共 4 关系；**117 对无证据不连**；方所跨年(2026-01↔2026-08)超 21 天窗正确不连。derive/follow 因当前无跨天强延续真实数据而为 0（不伪造，后续有数据自然补）。

### 测试（已实测）
新增 tests/test_event_graph_relations.py 5 用例（字典完整/derive+parallel+不伪造/follow/停用词防全相连/重算幂等且保手工）全过；统一入口 `pytest tests` **121 passed**。


---

## 2026-09-01 20:20 · GAP-05 动态调度影子→门控（P1，已签字；默认 shadow 零行为变化）

### 事实
- `platform_adapters/scheduling` 决策器本已完备（平台独立 policy/decider/state，决策审计落 schedule_decisions），但生产话题调度 `topic_campaign.py` 触发点写死「固定触发=YES」，只 shadow 调 decide 打印 allow、**不用 allow 门控**。

### 落地（只加一层可回滚开关，不改既有熔断/时钟）
1. 新增 `platform_adapters/scheduling/gate.py`：
   - `ZBC_SCHED_GATE_MODE` 三态：**shadow（默认，只评估+落审计，不阻断）/ canary（仅 ZBC_SCHED_GATE_PLATFORMS 名单内平台按 allow 门控）/ enforce（全平台按 allow 门控）**；
   - 铁律 **只收紧不放松**：门控态 `should_run = hard_allow AND decision.allow`，既有活动窗口/让行/熔断/冷却等 hard_allow 上游逻辑一律不动，本层绝不可能把「上游不跑」变成「跑」；
   - 门控器自身异常 fail-open 回 hard_allow（新组件故障不卡死既有调度）；非法模式回退 shadow；
   - **回滚零代码**：变量改回 shadow（或删除）即恢复固定时钟。
2. `topic_campaign.py` 话题触发点由 shadow 打印改为经 `gate_should_run`：门控态 allow=False 时打印原因并 continue（冷却/风险窗不撞），shadow 态行为与原先完全一致。
3. `.env.example` 登记两个开关（真实 .env 未碰）。

### 测试（已实测）
新增 tests/test_schedule_gate.py 6 用例（默认 shadow 不门控 / enforce 按 allow / canary 仅名单门控 / hard_allow=False 任何模式不放松 / 门控器异常 fail-open / 非法值回退）全过；统一入口 `pytest tests` **127 passed**。
### 运维路径（未执行，待逐步开）
默认 shadow 上线 → 先 canary 对低风险平台（如 web/bilibili）灰度观察 schedule_decisions → 稳定后再纳入 xhs → 最终 enforce；任一步异常改回 shadow 即回滚。生产 8201 未重启，当前仍跑旧进程。


---

## 2026-09-01 21:00 · 新增能力接管①：report_center 标准化报告只读旁路预览（阶段4）

### 事实
- `v4_upgrade/report_center`（ReportGenerator：cth/zbmp 双话术、日/周/月/年/专报、18 节结构化）代码入库但 app.py 无路由 = EXPERIMENTAL 旁路；它通过 `import database` 取数，天然尊重 DB_PATH（Staging 可重定向到副本，不硬编码生产库）。

### 落地（只加只读新前缀，不碰既有报告 Owner）
- 新增 `GET /api/v2/report-center/preview?period=&brand_mode=&start_date=&end_date=`：
  period∈{daily,weekly,monthly,yearly,event}、brand_mode∈{cth,zbmp} 白名单，日期严格 YYYY-MM-DD 校验，非法 400；**只读、不写库、不导出文件、不自动发送**；响应 note 显式标注「不替代既有报告 Owner（GAP-10 边界）」；内部异常不向前端泄堆栈。
- 不改 daily_report/brand_report_generator 与任何既有 /api/reports、/api/report/* 路由。

### 真实结果（Staging 副本 + Flask test_client，已实测；生产库/8201 未碰）
- cth 日报、zbmp 周报均 HTTP200、各 18 节（周报取近7天=98 条有效舆情、正/负面占比、执行摘要齐全）；非法 period/brand/日期均 400；无 Basic 401；默认参数回落到当日日报。
- 新增 tests/test_report_center_route.py 7 用例全过；统一入口 `pytest tests` **134 passed**。
### 未接管（登记）
ReportExporter 的 Word/PDF 导出与自动发送仍旁路；12 条旧报告路由的收敛仍属 GAP-10 剩余，导出接管前须先与 RPT-001/002 Owner 对齐，避免双写/双发。


---

## 2026-09-01 21:20 · 新增能力接管②：adapter 韧性层（熔断/限流/双池）单测验证（阶段4b）

### 事实与边界
- `v4_upgrade/adapters/base.py`（CircuitBreaker/RateLimiter/AdapterMetrics/BaseAdapter.safe_collect）与 `dual_pool.py`（Cookie/Proxy 池 + DualPoolManager）为增强层，**主采集链当前不经过它们**；本轮只做行为验证，不把它们接入生产主链、不改任何现有采集器。

### 落地（仅新增测试，零业务代码改动）
新增 tests/test_adapter_resilience.py 9 用例：熔断器 阈值熔断→冷却半开→成功复位；令牌桶 burst 耗尽即限流；指标 success_rate/avg/p95/to_dict；**safe_collect 永不抛异常**；Cookie 300012/验证码直接冷却且到期自愈、普通失败 SUSPECT→FAILED 递进、成功复位；Proxy 冷却→失败递进；CookiePool tmp 隔离 add/get/冷却摘除/get_stats；DualPoolManager 凭证装配 + 失败触发 risk_callback + health_check。

### 结果（已实测）
9 用例全过；统一入口 `pytest tests` **143 passed**。结论：韧性增强层行为正确、可作为后续采集 Adapter 化的可靠底座；是否真正接入主采集链仍按「先旁路验证再切换」另行评估，本轮不接管。


---

## 2026-09-01 21:40 · 新增能力接管③：Global BIL research-stage 只读接管（阶段4c）

### 事实
- Global BIL 此前仅有 13 篇 docs + 3 个 seed JSON（data/global_bil_*_v1.json）+ migrations/009 隔离迁移，**无任何 Python/路由**；009 明确 staging-only，不得对生产库执行。

### 落地（只读取研究 seed，不建表/不写库/不联网）
1. 新增 `v4_upgrade/global_bil.py`：白名单只读 loader（benchmarks/mechanisms/cases），mtime 缓存 + overview 概览；非法资源名 KeyError。
2. 新增只读路由 `GET /api/v2/global-bil/overview` 与 `/api/v2/global-bil/<resource>`：resource 白名单、未就绪 404、非法 400、无 Basic 401；响应标注 `stage=research`，**不参与任何生产统计/主体/风控口径**。

### 真实结果（已实测，真实 seed 计数）
overview：benchmarks **19** 条、mechanisms **16** 条、cases **10** 条（version 1.0/1.0/2026.09.01，status=research_seed）。新增 tests/test_global_bil_read.py 4 用例全过；统一入口 `pytest tests` **147 passed**。
### 未接管（登记）
bi_* 关系表仅在 ZBC_DB_PATH 隔离库经 009 建表、不触碰生产 monitor.db；BIL 与生产 notes/events 的关联分析、前端研究工作台仍属后续 research 任务。


---

## 2026-09-01 22:00 · 阶段5①：RedNote 运行策略 SoT 落地（三端开关/香港为主/真人频率占位，默认不自动跑）

### 审计事实（只读）
- 真实采集引擎是根目录 `rednote_collector.cjs`（Node + Playwright connectOverCDP 9222），Python 侧 `collector_v2/xhs/live_engine.py` 封装；**cjs 搜索入口当前硬编码国内 `www.xiaohongshu.com/search_result`（L96）**，滚动/详情为固定 waitForTimeout(2s/3s)，无三端区分、无每日登录保活；风控识别（300012/验证码/加载失败）已如实返回不显 0。
- 话题端另有 feature flag `XHS_APP_TOPIC_ENABLED`（platform_adapters/xhs_app_topic.py，默认 false）。

### 落地（纯策略层，零真实平台动作）
新增 `platform_adapters/rednote_policy.py` 作为暂行策略唯一 SoT：primary_region=intl（RedNote 香港/国际为主）、cn_paused=True（国内暂停不撞）；三端白名单 topic=True / public_opinion=True / event=False（事件笔记暂不开）；daily_login_keepalive=once_per_day；**auto_run 与自动保活总闸默认 False**，须显式 env 授权；真人节奏用保守占位且显式标 `NOT_VERIFIED`。新增 tests/test_rednote_policy.py 4 用例（默认符合拍板/未知 kind 默认拒/env 显式覆盖/真人频率未实测标记）全过；统一入口 **151 passed**。

### 待实测阻塞（未做，禁止凭空伪造，需真实浏览器窗口）
1. **rednote.com 国际/香港站 DOM 选择器**与国内站是否一致（note-item/detail-desc 等）未验证——入口从 xiaohongshu.com 切到 rednote.com 前必须真实加载验证；
2. **最新真人频率实测数值**未定位/未取得，当前为保守占位（NOT_VERIFIED），需按真人测试结果覆盖 HUMAN_CADENCE；
3. **每日登录保活的自动调度**未接线（默认关），需在 9222 会话与登录态确认后、经一次手动成功保活再开自动。
以上三项具备真实窗口后按「先旁路验证再切换」推进；国内熔断维持不撞不绕。


---

## 2026-09-02 13:05 · P0-1 事件聚合唯一权威收口（对账 GAP-P0-01，不重写、零口径变更）

### 只读调用链定位（先证据后改）
- 全仓无 def aggregate_events（对账据此判 MISSING）；events 写入=database.upsert_event，唯一上游聚合实现是 reprocess.build_cross_platform_events()：生产采集后由 xhs_cookie_bridge 异步调用、app.py 两端点（采集主任务 L701/手动分析 L2379）、full_refresh 共用，无第二套实现。
- 口径核对（健康，未弱化）：只取 db.get_notes(verified=True)+已验证 web；_event_key 语义+14 天窗分组；risk_score 取组内 max、负面计数定 risk_level；intelligence.summarize_event 仅摘要/翻译增强（ai_enabled=False 照样聚合）；first/last_seen 发布时间优先、采集时间兜底，未混淆 publish_datetime/captured_at。
- 结论：能力完好，是旧名 aggregate_events 重构更名迁走、基线未回写导致的误判，非真实缺失。

### 最小收口
- reprocess.py 恢复受保护兼容名 aggregate_events(limit=100) → 转发 build_cross_platform_events（同一实现，docstring 钉死唯一 Owner 与三条口径红线，严禁另写一套）。
- 新增 tests/test_event_aggregation_authority.py 3 测：兼容名转发同一权威并透传 limit；静态扫描全仓两处定义均只在 reprocess.py（单一 Owner）；monkeypatch 隔离 db/intelligence 验证风险来自数据（max=70→high、mention_count=2）、AI 关闭仍聚合、上游只取 verified。
- 结果：3 测全过；统一入口 161 passed（158→161）。运行旁证：回归日志见 [Gate:shadow][TopicCampaign] allow=True，GAP-05 门控 shadow 真实在线。
- DB：零变更；生产 8201 未重启未碰。


---

## 2026-09-02 13:15 · P0-4 依赖声明收尾（AST 全仓对账，主链无硬缺失）

- AST 扫生产代码第三方 import vs requirements.txt（排除 .venv/.trae-cn/IDE skill/backups/tests）：waitress/beautifulsoup4 已由前序提交补齐。
- 项目内剩余“import 未声明”逐项定性：**aiohttp**（collector_v2/xhs/client.py 方法内 try import，ImportError 自动降级 requests 同步，当前 venv 未装也正常跑）、**yyds-logger**（unified_logger try import，缺省回退标准 logging，本 venv 0.8.1 已装并实际生效）、docx2pdf/pypdf（仅 v4_upgrade 报告导出/导入器旁路，未接管）。**结论：生产启动主链无硬依赖缺失，不阻断 run_production/collector_v2。**
- 收尾：requirements.txt 增“可选增强”分组，显式声明 aiohttp / yyds-logger（注释写明内置降级与 win32-setctime、docx2pdf/pypdf 适用范围），不把可选变强制，保持“无重依赖全链可跑”。
- 证据：tests/healthcheck.py 只读（副本库）ok=true，subject_guard gz_hit/sh_excluded 均 true，has_publish_datetime/has_captured_at 均 true；统一入口 161 passed 不变。DB 零变更、生产 8201 未碰。


---

## 2026-09-02 13:24 · P1-4 风险权威归属校正（零运行时变更，文档与实现对齐）

### 只读审计事实
- 根 risk_engine.py 是历史兼容层（转发 daily_report / subject_rules），但其旧声明把“采集风险权威”写成 collector_guard/risk_engine.py 的 RiskEngine。
- 运行时实测：采集主链 collector.py:62 默认启用 CollectorGuard，现役风险/熔断由 state.CollectState 七态 + analyzer.ResponseAnalyzer + rate_limiter.AdaptiveRateLimiter（连续失败 3 次→动态降频→冷却封顶 30min→熔断→恢复）承担；**全仓无任何 RiskEngine( 实例化**，它是“已实现 + tests/test_risk_engine.py 7 用例覆盖、但未接管”的备用连续分评分器。
### 最小收尾（不改现役熔断、不强行接线）
- 校正根 risk_engine.py 职责声明：现役权威=CollectorGuard 七态；RiskEngine 标注为已实现/已测/未接管的增强件，未来须旁路验证后再接入；报告口径=daily_report/report_engine。
- 新增 tests/test_risk_authority_wiring.py 3 测：现役 Guard 持有四件套且不实例化 RiskEngine（源码层 guard.py 不 import risk_engine）；根兼容层纯转发（subject_sql_and_values 结果一致、build_daily_report 走 daily_report 哨兵验证）；备用评分器模块独立可导入。
- 结果：新增 3 测全过、既有 7 测不重复；统一入口 164 passed（161→164）。DB 零变更、生产 8201 未碰、现役熔断行为零变化。


---

## 2026-09-02 13:34 · P1-7 guardian 三模块接线锁定 + 安全收口复核（零运行时改动）

### P1-7 只读审计事实
- system_guardian.py(226)/auto_recovery.py(453)/data_feedback_loop.py(379) 均为实质实现；app.py 启动主路径（app.run 之前）已在 ZBC_GUARDIAN_ENABLED 默认 1 下受控接入：auto_recovery 60s 后台监控（app 层 _p17_started 幂等，引擎自身每次起线程故必须由接线层防重复）、data_feedback_loop daemon 6h、system_guardian.health_check()；三模块各自 try/except，任一失败只打印不阻断启动。
- 运行中 8201 为冻结旧进程（接入前启动），日志暂无 [Guardian] 行属预期，重启生效；本次不重启。
- 收尾：新增 tests/test_guardian_wiring.py 3 测（不重复 test_auto_recovery/test_data_feedback 模块内部测试）：静态锁定默认启用/可关/三模块导入/三处失败隔离/幂等标志/接线先于 app.run；三单例与入口可调用；复刻 app 层幂等守卫连进两轮只起一次监控。
### 安全收口复核（GAP-04 / 对账 GAP-P1-12 / OSAI CTR-SEC-P0）
- 三套 run-code（/api/developer/run、/api/config/run-code、/api/dev/run-code）确认全部经 _dev_exec_guard：生产 ZBC_DEV_EXEC 默认 0 一律拒绝（deny-by-default 硬门槛，比 CTR-SEC「Task-bound 为唯一硬门槛」更保守，生产无服务端执行面），开发态 opt-in 仍拦危险构造、JS 分支不写 static/js；tests/test_dev_exec_guard.py 9 测复跑全绿。结论：该项已真实闭环，无需新增代码；OSAI 提议的「沙箱 + Task-bound」属开发态纵深防御，登记 BACKLOG 不在本轮打开。
- 结果：统一入口 167 passed（164→167）。DB 零变更、生产 8201 未碰。


---

## 2026-09-02 13:46 · P1-3 safe_collection 无公害采集契约层落地（旁路新增，零网络/不改现役采集）

### 决策
- 对照 OSAI CASE-2026-0013 / src/contracts/safe_collection.py（学契约不复制代码，schema 独立为 zbc.collection-audit.v1），选择「ZBC 落地合规采集契约」而非放宽账号/代理池：dual_pool 只允许 internal/侧端，public_web 下池化/写入被 policy 硬拦截。
### 新增（platform_adapters/safe_collection.py，纯离线、import 无副作用、不串现役主链）
- PII 脱敏 redact_text/redact_record（字段级 + 手机/邮箱/微信/QQ 文本级，深拷贝不改原、note_id 内容标识保留、价格短号不误伤）+ sanitize 递归剔除 cookie/token/api_key 等凭证键。
- CollectionHygienePolicy（默认只读/单本机账号/禁双池/≥2s 限速/日上限 200/批 20/写入需人工，validate/is_safe）+ RateGovernor（不 sleep、时钟可注入的 permit/daily_cap/batch，assess_risk_signal 与 collector_guard 七态信号对齐：300012/验证码/登录过期→stop）。
- build/validate_collection_audit（provenance：audit_id/策略快照/计数/状态，凭证不搭车，非人工触发须 automation_justification）+ run_offline_pipeline（限速判定→脱敏→审计，遇风控停止不伪装成正常 0 条）。
### 测试
- 新增 tests/test_safe_collection_contract.py 10 测全过；统一入口 177 passed（167→177）。
- 边界：本层不替代 collector_guard 在线熔断（互补：在线熔断 vs 离线合规/证据）；当前为旁路，真实采集链接管须先旁路验证 + Release Gate；详情/评论级与大批量稳定性仍 NOT_VERIFIED。DB 零变更、生产 8201 未碰。


---

## 2026-09-02 13:58 · P1-5 单一权威 DB Schema 源建立（只读反射，零 DDL/零迁移/不改库）

### 只读盘点事实（生产库 mode=ro）
- 实际 **52 表 / 0 视图**（旧基线口径 51/53 以本次实测 52 为准）；database.py 直接 CREATE 15 表，其余分散在各模块/database_migrations，bi_* 16 表为 Global BIL migration009 隔离（生产当前不建，设计如此）。
- 唯一无 CREATE 声明的实际表 `industry_stats`（8 行旧数据）：现役 /api/brand-industry/* 真正查的是 brand_industry_monitor，web_monitor_v570 为旧文件 → 定性 LEGACY 遗留，**保留不删**，登记待人工确认。
### 落地（不重写 database.py、不动建表逻辑）
- 新增 schema_registry.py：mode=ro 只读反射表/列/索引/行数 + 全仓 CREATE 声明来源映射 + 状态分类（DECLARED/LEGACY_NO_DECL/MIGRATION_ISOLATED/MISSING_SOURCE），生成 docs/DATABASE-SCHEMA-REGISTRY.md（52 表：51 DECLARED + 1 LEGACY，**无主未登记=0**，含 publish_datetime/captured_at 红线列核对）。
- 新增 tests/test_schema_registry.py 5 测：临时库验证反射结构与只读、声明来源定位、四类分类、已生成清单 0 无主且红线时间列齐备（未来新增无主表测试即红）。
- 结果：182 passed（177→182）。**未执行任何 DDL/DML、无迁移、生产库与 8201 全程未碰**；industry_stats 清理与 Alembic 正式迁移另列 BACKLOG，不在本轮做破坏性动作。


---

## 2026-09-02 14:09 · P1-2 357→364 路由 OpenAPI 单一清单（url_map 自动反射，零端点改动）

- 只读 import app（Staging 副本库，不起服务、不碰生产）反射 url_map：非 static **364 规则 / 350 去重 path**（对账时 357，另一窗口新增至 364）；/api 296、/v4 63；GET 226/POST 141/DELETE 5/PUT 1；含路径参数 46。
- 新增 openapi_spec.py：Flask `<conv:name>`→OpenAPI `{name}`，operation 带 operationId/tags/path 参数；认证标注严格对齐 app.before_request：/healthz public(1)、/v4/* 独立 v4Auth(65)、其余 httpBasic 或 v4 会话(306)。
- 产物：docs/API-OPENAPI-SPEC.json（标准 OpenAPI 3.0.3 + securitySchemes）、docs/API-ROUTE-MATRIX.md（人类可读矩阵）。新增 tests/test_openapi_spec.py 5 测：最小 Flask 验证转换/认证映射、真实 app spec 与 url_map 完全一致（一条不漏）、产物合法。
- 结果：187 passed（182→187）。未新增/修改/删除任何端点，DB 零变更、生产 8201 未碰；请求/响应 schema 细化与 12 旧报告路由收敛另列 BACKLOG。


---

## 2026-09-02 14:28 · P1-1 OSAI 25 契约逐项决策台账 + 版本单一权威对齐

- 通读 OSAI reconciliation/06_CONTRACT_RECONCILIATION.md（25 契约 + V-01~07 + I-01~10），在 ZBC 侧逐项给决策，产出 docs/CONTRACT-DECISION-LEDGER.md，无 UNKNOWN 悬挂：
  - safe_collection 的 PII/audit/离线管线/速率 = ADOPT-BYPASS（本轮 P1-3 已旁路实现，10 测，待采集后处理接入）；风险即停 CLOSED（现役 collector_guard 七态）。
  - V-01/02 多账号/代理池「违规」= REVISE-SCOPE：契约定位低风险人工 QR 单账号，ZBC 以 deployment_target 分级化解（internal 受控、public_web 硬禁，已实现并测），回写 OSAI 建议补 scope，非 ZBC 违规。
  - research_record/AI 协作/CAPABILITY 等 = NOT-APPLICABLE（OSAI 研究侧职责）；I-01 API 契约 CLOSED（P1-2 OpenAPI）、I-03 DB 契约 CLOSED（P1-5 registry）、I-02 主体口径 ZBC-OWNS；P1-8 证据流转/production_unchanged/Capability Delta 登记 BACKLOG。
- 版本对齐（06 称 VERSION 5.9.9 vs package.json 5.6.2 不一致，实测另一窗口已统一为 5.9.9，06 滞后）：仅 models.py 文件头 v5.8.0 与 __main__ 打印 v5.8.9 两处过时注释/打印统一为 v5.9.9（纯文本零逻辑）。
- 新增 tests/test_version_consistency.py 2 测锁定 VERSION=package.json=app.APP_VERSION=5.9.9 且 models.py 无旧版本残留（VERSION 带 BOM，用 utf-8-sig 读）。
- 结果：189 passed（187→189）。DB/采集/主体口径零变更，生产 8201 未碰。


---

## 2026-09-02 14:55 · P1-8 ZBC→OSAI 只读证据自动流转（旁路、增量、可审计）

- 新增 platform_adapters/evidence_exporter.py：源库强制 mode=ro（物理不可写生产）；只导已核准证据——notes 必须 is_taikoo_verified=1（过主体口径）、events 取 fact_status in (confirmed, partially_confirmed)、daily_reports 全量；白名单字段投影，剔除 author_id/nickname/avatar/xsec_token/cover，url 剥离凭证 query；复用 safe_collection.redact_text 做联系方式脱敏（返回 (text,hits)）；按各表 id 增量水位幂等；产物 JSONL + manifest（schema zbc.evidence-export.v1、counts、sha256、production_unchanged=true 回应契约 V-06、approval_basis、record_ids）；默认写本仓 outbox，不直写 OSAI 仓库（解耦），零网络。
- 新增 tests/test_evidence_exporter.py 3 测：只导核准+脱敏+剔除凭证字段；增量水位只取新增；端到端 manifest/sha256/源库行数不变（只读证明）/二次导出为 0。
- 真实冒烟（Staging 副本，未碰生产库）：608 verified notes + 7 confirmed/partially_confirmed events + 29 daily_reports = 644 条，redacted=0（真实正文无联系方式），二次增量 0。
- 结果：192 passed（189→192，exit=0）。DB/采集/主体口径零变更，生产 8201 未碰；导出器未接入定时调度（BACKLOG，等用户确认后接）。


---

## 2026-09-02 14:25 · 国内采集恢复 + 自适应调度门控上线（GAP-05 enforce，生产 8201 已重启）

- **用户指令**：国内采集不再暂停；不用固定时间采集，启动不定时根据状态确定采集数量的自适应调度；功能不依靠 VPN，任何网络可用。
- **VPN 确认**：10808 仅用于 git push（GitHub 直连被重置），系统运行（Flask/采集/数据库/healthz）完全不依赖代理；proxy_pool 可插拔默认关闭，关闭时等同直连。
- **熔断/暂停**：xhs_circuit.json 实测 state=SUCCESS（冷却期已过，已清除）；用户暂停文件不存在（未手动暂停）。
- **rednote_policy**：CN_PAUSED True→False（国内采集恢复），primary_region 仍 intl（香港为主，国内并行）；三端策略不变（话题开/舆情笔记开/事件笔记关）。
- **scheduler_loop 自适应门控**：去掉固定时间点（auto_collect_hours）硬触发，改为每 20 秒循环问 ShadowPlanner「此刻是否该采」；gate_should_run enforce 模式（只收紧不放松，异常 fail-open）；max_scroll 由 adaptive_engine.get_current_params() 动态决定（当前 normal=6，风险升高会自动降）；账号频率保护 check_rate_limit（60 分钟最小间隔）和熔断全部保留在上游。
- **生产验证**：8201 已重启（pid 16428→29168），healthz ok v5.9.9；日志确认 gate=enforce should_run=True code=RUN_DUE，频率保护合理拦截（距上次运行不足 60 分钟，约 14:51 自动触发）；9222/9223 CDP 双驻场在线。
- **测试**：test_rednote_policy 期望同步更新（cn_paused=False）；全量 exit=0。DB/主体口径/红线函数零变更。


---

## 2026-09-02 14:55 · adaptive_engine 采集结果回写闭环 + 熔断冻结时长动态化

- **回写闭环**：xhs_cookie_bridge worker 完成/异常双路径接入 adaptive_engine.report_collection_result（成功/失败、notes_count、duration、error），滑动窗口最近10次成功率经 update_metrics→_evaluate_risk_and_strategy 自动升降级（normal/cautious/conservative/suspended），采集参数（delay/并发/max_scroll）随之动态变化；任何回写异常 fail-open 不阻断采集。
- **动态冻结**：新增 _adaptive_cool_minutes()，熔断冷却时长随策略递增 normal60→cautious90→conservative180→suspended360 分钟（越失败冻结越久），异常回退60；_trip_circuit 调用点改为动态 cool_minutes。
- **与既有 network_adaptive 区别**：L555/576/743/779/787 的 network_adaptive 是单次请求网络层自适应，本闭环是任务级策略自适应，两者互补。
- **测试**：新增 tests/test_adaptive_feedback.py 4 测（策略→冷却映射/fail-open/连续失败升级/连续成功保持normal）；全量 exit=0。DB/红线零变更。
