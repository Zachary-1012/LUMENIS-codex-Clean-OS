# LUMENIS App

This is the repository's **single canonical Flutter app target** for Web Workspace,
Desktop and Mobile. Public Website is separately implemented under `website/`.
The approved Product Architecture defines the complete outcome scope; historical
Golden Pages and route counts are compatibility/evidence, not a product limit.
Current implementation and acceptance state is read from CURRENT and exact source.

## Retained implementation observations — not current acceptance

- **Approved pre-beta boundary:** the LUMENIS product account is deferred until after internal beta and does not block App entry. Core's existing transport authentication remains separate from a product account. Media-platform Cookie/session/browser authorization is separate and remains in the existing SYSTEM collector path.
- The launch surface reads the existing `GET /api/auth/config` transport configuration, then Product Core runtime identity. It does not call `/v4/auth/login` or load the account-scoped CTH Subject Registry at startup. The five Golden Pages call their existing `GET /api/experience/screen/<screen_id>` owner contracts. A returned Subject or a bound ViewModel does not establish actor-to-Subject authorization by itself.
- The former login surface showed the four `ProductDomain` ownership definitions and Agent Groups as an information-only product map. Runtime context continues to come from Product Core identity; the removed login prompt did not choose the active domain.
- The shell's neutral `启动身份已读取` label reports that the runtime identity request returned; it is not a continuous Core health check.
- CTH-02 opens from CTH-01 as `浏览 CTH 主体登记目录`; it does not add a sixth top-level destination or change the active Subject/context. It requests metadata from the existing server-protected registry only when opened. A server denial is shown locally on CTH-02 and does not eject the user from the App. Subject → business unit → brand/format ownership remains `NOT_COLLECTED`; the full profile remains blocked until its owner, read permission and Evidence lineage are verified.
- BMP BrandFocus is shown only when Core returns both `domain=zbmp` and `subject.product=ZBMP`; a CTH `brand_key` is not a BMP brand context. CTH remains Subject-first, BMP remains Brand/Market-first, Shared retains source-domain lineage, and SYSTEM remains infrastructure.
- The five Golden Page slices use screen-specific mappings and compositions. Their presence does **not** mean the Experience contracts or full workflows are accepted. The repository defines 44 screen-specific UX blueprints and 54 truth-binding rows. The binding registry constrains data/API/actor/permission/Evidence truth; legacy `sectionTypes` do not prescribe layouts, and a generic renderer is prohibited.
- Windows and Android Release compilation have been verified locally. The Windows packaged binary also passed a launch smoke with the expected window title and a responsive process; this does not establish authenticated Product Core or screen-workflow acceptance. Android device acceptance and macOS/Linux/iOS packaging/runtime remain open.

Do not invent UI data, backend behavior, permission results or successful actions to make an unbound screen appear complete. Keep `UNKNOWN`, `NOT_AVAILABLE`, `NOT_COLLECTED`, `STALE`, `BLOCKED` and `ERROR` distinct. A contract or fixture is not proof of a working endpoint or feature.

## Product Core connection

Default Core URL: `http://127.0.0.1:8201` on native clients; the current page's
origin on Web Workspace. A browser installation must not silently send its
requests to the visitor's localhost.

Override for an authorized device/build:

```text
--dart-define=LUMENIS_CORE_BASE_URL=<authorized-core-url>
```

`LUMENIS_CORE_BASE_URL` is the canonical define. Existing builds that still
provide `LUMENIS_CORE_URL` remain compatible during migration; when both are
present, `LUMENIS_CORE_BASE_URL` wins. Product Core requests do not follow HTTP
redirects, so Subject/BrandFocus context headers cannot be forwarded to a
different origin by a redirect response.

Product Core integration contracts:

```text
GET /api/experience/runtime/identity
GET /api/experience/screen/<screen_id>
GET /api/settings/subjects?domain_id=CTH
GET /api/auth/config
```

### Core transport and product account boundary

- For a loopback Core on native platforms only, the App reads the existing Core Basic Auth header from `GET /api/auth/config` when Core authentication is enabled and keeps it in process memory. This is technical transport authentication, not a LUMENIS product account. If Core auth is disabled, the App sends no authorization header. Web builds never request or retain this reusable local credential.
- The App never requests the reusable Basic header from a remote Core and never sends it to a non-loopback host. This avoids exposing the global Core credential through the unauthenticated configuration route. An authenticated remote Core requires its existing deployment-side transport path; the App does not replace that with a product-account prompt. Authenticated local requests do not follow redirects.
- The pre-beta App does not call `/v4/auth/login` or `/v4/auth/logout`, persist product-account credentials, or block the workspace on product-account state. The account-backed CTH registry route remains the existing server Permission owner. CTH-02 presents a local denial state if that route refuses access; it does not substitute another registry endpoint or expose business data.
- Registry access requires the server-side CTH `subject_registry/read` Permission. That Permission covers selection metadata only; it does not authorize business data for each Subject.

The App consumes LUMENIS Product Core. It must not create a second Evidence, Canonical Data, Metric, Permission, Runtime or business-truth owner. `GET /api/experience/subjects` is not used as a substitute for the protected CTH registry.

## Web Workspace build and host contract

Build the same Flutter product target with
`flutter build web --release --no-web-resources-cdn`. The source-owned bootstrap
also resolves CanvasKit from the document base URL, so deep links use the bundled
renderer without requiring access to Google's CDN. Deploy the complete
`build/web/` directory, including `canvaskit/`; this does not make backend reads
or AI execution available offline. The
canonical Flask adapter in `lumenis/system/runtime/workspace_host.py` serves the
generated artifact and rewrites extensionless `/workspace/*` document requests
to `index.html`. Missing asset files remain 404; missing builds remain
unavailable. This adapter does not own Product Core APIs or restore a legacy
template frontend. No vendor-specific deployment is selected here.

Verify the generated manifest, icon and font assets as well as `main.dart.js`.
A source file under `app/web/` does not prove that the current build contains it.
Same-origin routing, TLS, access control and complete user journeys still need
deployment-specific acceptance.

### Windows builds from the canonical Unicode checkout

The local MSVC/Flutter toolchain can misinterpret the Unicode checkout path.
Use an unused, checked `subst` drive pointing to the **same** canonical checkout
when this occurs, and run the build from that drive's `app/` directory. This is
a path alias, not another repository or production data directory. Never
overwrite an existing drive mapping. CMake caches retain the build path, so
re-establish the same checked mapping before the next incremental build.
Build outputs remain under the canonical checkout's `app/build/` directory.

## Required development authority

Follow `../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §§30–36 for app architecture, the current task-specific screen contracts, CTH/BMP/Shared/SYSTEM ownership, desktop/mobile composition, accessibility, motion and originality boundaries, ordered implementation and acceptance. That Constitution is the sole UI/UX and interaction authority. Do not create another visual design specification or copy historical web UI.

The repository execution router is `../AGENTS.md`; the fixed lookup map is
`../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`. C1-C6 retain all R01-R15
acceptance dependencies and J/U outcomes. They do not impose fifteen serial
development stages. Current user reference directions and Experience govern
design; examples cannot remove capabilities or authorize copying a vendor UI.

The historical 44 route IDs preserve compatibility; they are neither a page quota nor a layout template. Compose the experience around the user job and current owner contracts. The product owner accepted this architecture and Experience Constitution §§30–36 on 2026-09-20; App implementation is now proceeding through reviewed screen specifications and source-backed vertical slices. That approval does not make a route, contract row or fixture proof of a working feature, and it does not permit generic screen templates.

Bind each screen/action to its current source owner, API/ViewModel, Permission, Evidence lineage, real states and acceptance evidence before implementing it. Preserve these domain boundaries:

- **CTH:** authorized Subject first; changing context must not rewrite original data ownership or Evidence.
- **BMP:** Brand/Market focus first, with market, competitor, creator and content relationships retained; it is not a relabeled CTH page.
- **Shared Capability:** supports CTH and BMP while preserving its source domain and object context.
- **SYSTEM:** permission-gated product infrastructure, not a third business domain.

Complete the user workflow and real bindings assigned by the current owner,
preserving all mapped capabilities. Each screen has its own hierarchy and
interaction path. A historical five-page milestone is not a new prerequisite.
Do not remove a capability before its behavior is preserved in its current owner.

## Flutter implementation architecture and delivery standard

This section governs the App code structure and engineering sequence. The Experience Constitution remains the sole authority for product interaction and screen composition.

- **Start from the shipped stack:** the current app is one Flutter codebase. `go_router` owns URL/deep-link presentation state and `http` supplies the browser-safe Core transport; neither may become a second Product Core, Permission, Evidence or workflow owner. Do not add a parallel framework or reorganize the bootstrap wholesale. Select another dependency only when an accepted vertical slice demonstrates the need and the target platforms are confirmed.
- **Keep ownership visible:** group presentation code by the CTH/BMP capability that owns the task. Keep API DTOs and transport in data adapters, expose typed owner models to presentation, and put business orchestration in a use case only when it is non-trivial or reused. Promote code into `core` only when it has real stable use across owners. Views render; view models coordinate UI state; repositories/services call the existing Product Core contract. The App never becomes a second database, Evidence, Permission, Metric or business-truth owner.
- **Route through canonical contracts:** every screen action resolves through the current API Owner Map and the binding registry. Keep authentication, domain scope, action permission, Evidence lineage, side effects, compatibility and error states explicit. A route or mock response is not proof of a working capability.
- **Compose for available space, not device labels:** use Flutter layout constraints to decide when the task needs a desktop workspace, an intermediate split view, or a focused mobile flow. Do not shrink a PC page to phone width or switch only on “phone/tablet” hardware labels. Each reviewed screen specification must describe its own PC and mobile hierarchy, navigation, information density and return path. Preserve desktop keyboard/mouse behavior and mobile touch/focus behavior.
- **Keep navigation deliberate:** canonical workspace URLs are `/workspace/CTH-01`, `/workspace/CTH-01/CTH-02`, `/workspace/BMP-01`, `/workspace/AI-01`, `/workspace/SH-01` and `/workspace/SYS-01`. `go_router` synchronizes those URLs with shell selection. Unknown routes fail safely, and browser entry to a Desktop-only capability shows a truthful Desktop-required state rather than emulating local execution.
- **Use references within their limits:** [`motion-web`](https://github.com/Zachary-1012/motion-web) is research reading only. Its CC BY-NC 4.0 license bars commercial use of its Skill, prompts, cases and derivative workflows; do not bring its code, assets, cases, parameters, verification recipes or derivative workflows into LUMENIS. Define motion from LUMENIS state transitions and define acceptance from LUMENIS contracts and user tasks. For Korean product craft, the public [Toss Design System guide](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components) may be studied for documentation clarity and consistency practices, but its UI Kit materials are limited to the Apps in Toss service. Do not reuse its components, assets, visual patterns or screen layouts. For every external reference, record the named flow, source, abstract principle, LUMENIS workflow it informs and a distinct LUMENIS composition. Adapt the Product Owner-supplied references through the current Experience Constitution; do not impose one template across unrelated jobs.

### Ordered engineering gates

1. **Plan lock:** the product owner accepted this architecture and §§30–36 on 2026-09-20. Continue implementation without requesting overall-plan approval again; this approval is not per-screen acceptance.
2. **Capability and owner mapping:** for the chosen workflow, reconcile existing behavior against its canonical module, route, fields, actor, scope, permission, Evidence, effects and regression tests. Record unresolved source claims as blocked; do not infer equivalence from filenames or a ViewModel.
3. **Screen specification:** create one reviewed specification from `../contracts/experience/screen-specifications/SCREEN_SPEC_TEMPLATE.md`. It must resolve owner and callable, entry/return paths, information priority, PC/mobile composition, state matrix, accessibility, side effects and executable acceptance.
4. **Vertical slice:** implement one end-to-end workflow in its owning feature, reusing stable shared primitives only. Keep CTH Subject-first, BMP Brand/Market-first, Shared cross-domain, and SYSTEM infrastructure boundaries.
5. **Acceptance before expansion:** verify source/auth behavior (allowed, denied, missing, stale and error), ViewModel/repository behavior, PC and mobile layouts at representative window widths, keyboard/mouse/touch input, focus/contrast/reduced motion, Evidence traceability, and regression of the preserved capability. Review the actual running app before marking the screen accepted.
6. **Release gate:** only supported platforms with a real build and runtime acceptance may be listed as supported. Keep failed, skipped and unrun checks distinct in the release evidence.

This is an implementation and acceptance path, not a completed-product claim.
Preserve all fifteen mapped acceptance requirements; execution and pause state
come only from AGENTS. Historical screen counts do not constrain reconstruction.

## Workspace asset updates

The source-owned `web/flutter_bootstrap.js` uses the installed Flutter loader
without registering its deprecated generated service worker. Retain the SDK's
generated legacy-worker cleanup stub at the same deployed path for existing
clients. Do not clear unrelated browser storage or origin registrations.
The canonical Workspace host must revalidate non-hashed bootstrap/runtime files;
immutable caching is appropriate only for content-hashed assets. This frontend
commit alone does not publish the separately owned Flask Workspace host binding.

Current frontend evidence, including typography, local appearance, Web and
Windows builds and remaining platform/business gates, is in
[`ROUND-08-REFERENCE-ADAPTATION-2026-09-24.md`](../00-GOVERNANCE/evidence/round-08/ROUND-08-REFERENCE-ADAPTATION-2026-09-24.md).

## Historical development checks — 2026-09-20

- Toolchain: Flutter 3.47.5, Dart 3.13.4, Android API 36 / Build Tools 36, JDK 21.
- `flutter analyze`: passed with no issues.
- `flutter test --no-pub`: 75 tests passed, including 1440 px / 390 px Shell and screen-layout coverage.
- `py -3.13 -m pytest tests/test_experience_runtime.py tests/test_subject_registry.py tests/test_shared_database_migrations.py`: 48 passed; no background-thread leaks. The cookie-route test isolates the unrelated app-startup migration from its file/identity assertions.
- Backend capability/permission regressions across BMP truth isolation, AI intent, App permission integration, Shared skills, RuntimeGuardian, login and dual-domain gates: 298 passed; no background-thread leaks.
- `flutter build windows --release --no-pub`: succeeded; `build/windows/x64/runner/Release/lumenis_app.exe` launched locally with title `序境 - LUMENIS` and `Responding=True`.
- `flutter build apk --release`: succeeded; `build/app/outputs/flutter-apk/app-release.apk`, 50,150,362 bytes, SHA-256 `F33E1F471343A0625EC3126FF40B78D895608997E880768DD821E8E22B0E6317`.
- These results prove analysis, tests, compilation and the stated Windows launch smoke only. The APK currently uses the Flutter scaffold's debug signing key. Live authenticated Product Core acceptance, Windows screen-workflow E2E, Android device runtime, store signing, and macOS/Linux/iOS builds remain unverified.

Run Flutter checks from `app/`; run the focused Python suite from the repository root. Keep each failed, skipped and unrun release check distinct. Never report a build as a screen acceptance or platform release.
