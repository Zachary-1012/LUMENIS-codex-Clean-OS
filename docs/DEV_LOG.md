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
