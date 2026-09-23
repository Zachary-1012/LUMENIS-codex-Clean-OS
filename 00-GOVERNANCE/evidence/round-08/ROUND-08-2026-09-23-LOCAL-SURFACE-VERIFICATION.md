# ROUND 08 — local Public Website and Web Workspace verification

Status: **PARTIAL / LOCAL AND BUILD VERIFIED; ROUND 08 NOT ACCEPTED**

Observed: 2026-09-23 11:52–12:01 Asia/Shanghai. The Flutter App/Core candidate remains dirty and uncommitted. `origin/main` contains the Public Website foundation at `77648c3b010d7f1ec1ce516f4d15ed99e7c34378`, not the current Web Workspace changes.

## Public Website

`website/` was reviewed as a separate presentation/acquisition surface under the existing Product Architecture and Experience Constitution; it does not own business state, Permission, Evidence or workflow execution. The local Chinese page was visually opened at `127.0.0.1:4321`; its editorial/trace composition, language links, clearly fictional demo and explicit preview notice rendered. The four trial/contact/help/workspace destinations remained visibly **unconfigured** rather than becoming dead or fake success actions. The temporary preview server and browser tab were stopped.

`npm test` passed all five checks in three configurations: preview with no public origin, configured origin without destinations, and configured origin with four example HTTPS destinations. The tests cover the three language routes, semantic landmarks, internal anchors, preview no-index/robots behavior, configured canonical/hreflang/sitemap and truthful destination state. `npm audit --omit=dev --audit-level=high` returned zero vulnerabilities. These are build/smoke checks, not customer acquisition, SEO ranking, form submission or deployment proof. Without real configured destinations, commercial entry remains incomplete.

## Flutter Web Workspace

The initial incremental `app/build/web/` output compiled but lacked generated `manifest.json`, `favicon.svg` and `assets/FontManifest.json`; it was **not** accepted. A fresh release build to a new OS-temp output path exited `0` and contained all three plus `index.html`, Flutter bootstrap, fonts and `main.dart.js`. The latter was 4,158,266 bytes with SHA-256 `9D02E6944F05C055FD7D65C5983431F287EC34F7A1A76A0178170EC95FB9DB9F`. This proves a clean local build path, not that every incremental/default build is complete.

`flutter test --no-pub test/navigation/lumenis_router_test.dart` passed six route/deep-link tests. `python -m pytest -q tests/test_workspace_host.py` passed seven host-contract tests with no background-thread leak. The isolated local Core used a new OS-temp database, UTF-8 process settings, staging/no-collect mode and the fresh Web build through the canonical `WorkspaceHost`; it did not access personal Mainland XHS identity or the production DB. HTTP checks returned 200 for `/healthz`, `/workspace/`, a workspace deep link, generated manifest/icon/font manifest and `/api/experience/runtime/identity`. The in-app browser opened the actual Flutter page and showed server-connected SYSTEM/SYS-01 operational status from Core.

The same real browser session showed the **current blocking contract gap**: `/api/settings/context`, CTH-01 and BMP-01 returned 401 from Core. CTH/BMP pages displayed login/unavailable states; the product-account entry said internal Beta is connected but did not provide an authenticated actor for these business requests. Web correctly did not request or expose the reusable loopback Basic header. A 200 workspace document or SYS-01 status is therefore **not** CTH/BMP business completion. Same-origin production deployment, real login/actor authorization, GLOBAL/ALL and focused context, mobile parity, trial-to-workspace transition and business E2E remain unverified. The isolated Core and browser tab were stopped after observation; port 8202 was no longer listening.

## Sol gate

Public Website foundation is committed, not commercially operational. Flutter Web compiles from the local candidate and one read-only SYSTEM page runs, while protected work cannot yet be used in browser. **REWORK/BLOCKED for business-surface acceptance** pending the canonical identity/Permission path and integrated App/Core source, followed by real actor-bound CTH/BMP jobs. Do not mark ROUND 08 or product release PASS.
