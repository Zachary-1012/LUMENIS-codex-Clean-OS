# LUMENIS App

This is the repository's **single canonical Flutter app target** and the only intended user-facing app implementation for 序境 / LUMENIS. The five Golden Pages have source-backed Flutter slices. CTH-02 is reachable as a nested, read-only CTH registry workflow; the full 44-screen product is not yet accepted or released.

## Current implementation status

- The launch surface loads Product Core runtime identity and then the account-scoped CTH Subject Registry. The five Golden Pages call their existing `GET /api/experience/screen/<screen_id>` owner contracts. A returned Subject or a bound ViewModel does not establish actor-to-Subject authorization by itself.
- The login surface shows the four `ProductDomain` ownership definitions and Agent Groups as an information-only product map. It does not choose the active domain; runtime context is read from Product Core identity.
- The shell's neutral `启动身份已读取` label reports that the runtime identity request returned; it is not a continuous Core health check.
- CTH-02 opens from CTH-01 as `浏览 CTH 主体登记目录`; it does not add a sixth top-level destination or change the active Subject/context. It displays only metadata returned by the account-authorized registry endpoint. Subject → business unit → brand/format ownership remains `NOT_COLLECTED`; the full profile remains blocked until its owner, read permission and Evidence lineage are verified.
- BMP BrandFocus is shown only when Core returns both `domain=zbmp` and `subject.product=ZBMP`; a CTH `brand_key` is not a BMP brand context. CTH remains Subject-first, BMP remains Brand/Market-first, Shared retains source-domain lineage, and SYSTEM remains infrastructure.
- The five Golden Page slices use screen-specific mappings and compositions. Their presence does **not** mean the Experience contracts or full workflows are accepted. The repository defines 44 screen-specific UX blueprints and 54 truth-binding rows. The binding registry constrains data/API/actor/permission/Evidence truth; legacy `sectionTypes` do not prescribe layouts, and a generic renderer is prohibited.
- Windows and Android Release compilation have been verified locally. The Windows packaged binary also passed a launch smoke with the expected window title and a responsive process; this does not establish authenticated Product Core or screen-workflow acceptance. Android device acceptance and macOS/Linux/iOS packaging/runtime remain open.

Do not invent UI data, backend behavior, permission results or successful actions to make an unbound screen appear complete. Keep `UNKNOWN`, `NOT_AVAILABLE`, `NOT_COLLECTED`, `STALE`, `BLOCKED` and `ERROR` distinct. A contract or fixture is not proof of a working endpoint or feature.

## Product Core connection

Default Core URL: `http://127.0.0.1:8201`

Override for an authorized device/build:

```text
--dart-define=LUMENIS_CORE_URL=<authorized-core-url>
```

Product Core integration contracts:

```text
GET /api/experience/runtime/identity
GET /api/experience/screen/<screen_id>
GET /api/settings/subjects?domain_id=CTH
POST /v4/auth/login
POST /v4/auth/logout
```

### Runtime and account sessions

- Runtime identity uses the existing Basic Auth contract at `GET /api/experience/runtime/identity`. After that succeeds, the App obtains the account session through `POST /v4/auth/login` and uses its Bearer token for the account-scoped CTH registry request.
- Basic Auth credentials and the account token stay in memory only. The App does not write them to files, preferences, restoration state or logs. Logout clears both locally and attempts `POST /v4/auth/logout` for the account token.
- Credentials are sent only over HTTPS or loopback HTTP (`localhost`, loopback IP addresses); authenticated requests do not follow redirects. Remote HTTP is rejected before credentials are sent.
- HTTP 403 remains a distinct access-denied state, not an invalid-password result. Registry access requires the server-side CTH `subject_registry/read` permission. That permission covers selection metadata only; it does not authorize business data for each Subject.

The App consumes LUMENIS Product Core. It must not create a second Evidence, Canonical Data, Metric, Permission, Runtime or business-truth owner. `GET /api/experience/subjects` is not used for the account-scoped registry flow.

## Required development authority

Follow `../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §§30–36 for app architecture, the 44 screen-specific UX blueprints, CTH/BMP/Shared/SYSTEM ownership, desktop/mobile composition, accessibility, motion and originality boundaries, ordered implementation and acceptance. That Constitution is the sole UI/UX and interaction authority. Do not create another visual design specification or copy historical web UI.

The 44 screen-specific UX blueprints are not implemented screens. The product owner accepted this architecture and Experience Constitution §§30–36 on 2026-09-20; App implementation is now proceeding through reviewed screen specifications and source-backed vertical slices. That approval does not make a route, contract row or fixture proof of a working feature, and it does not permit generic screen templates.

Bind each screen/action to its current source owner, API/ViewModel, Permission, Evidence lineage, real states and acceptance evidence before implementing it. Preserve these domain boundaries:

- **CTH:** authorized Subject first; changing context must not rewrite original data ownership or Evidence.
- **BMP:** Brand/Market focus first, with market, competitor, creator and content relationships retained; it is not a relabeled CTH page.
- **Shared Capability:** supports CTH and BMP while preserving its source domain and object context.
- **SYSTEM:** permission-gated product infrastructure, not a third business domain.

Implement and accept the five Golden Pages, then migrate remaining screens by workflow family as required by §§25, 34 and 36. Each screen receives its own information hierarchy and interaction path. Do not remove an existing capability until its behavior is preserved and accepted in its canonical owner.

## Flutter implementation architecture and delivery standard

This section governs the App code structure and engineering sequence. The Experience Constitution remains the sole authority for product interaction and screen composition.

- **Start from the shipped stack:** the current app is Flutter with no routing, state-management, networking or code-generation package installed. Do not add a parallel framework or reorganize the bootstrap wholesale. Select a dependency only when an accepted vertical slice demonstrates the need and the target platforms are confirmed.
- **Keep ownership visible:** group presentation code by the CTH/BMP capability that owns the task. Keep API DTOs and transport in data adapters, expose typed owner models to presentation, and put business orchestration in a use case only when it is non-trivial or reused. Promote code into `core` only when it has real stable use across owners. Views render; view models coordinate UI state; repositories/services call the existing Product Core contract. The App never becomes a second database, Evidence, Permission, Metric or business-truth owner.
- **Route through canonical contracts:** every screen action resolves through the current API Owner Map and the binding registry. Keep authentication, domain scope, action permission, Evidence lineage, side effects, compatibility and error states explicit. A route or mock response is not proof of a working capability.
- **Compose for available space, not device labels:** use Flutter layout constraints to decide when the task needs a desktop workspace, an intermediate split view, or a focused mobile flow. Do not shrink a PC page to phone width or switch only on “phone/tablet” hardware labels. Each reviewed screen specification must describe its own PC and mobile hierarchy, navigation, information density and return path. Preserve desktop keyboard/mouse behavior and mobile touch/focus behavior.
- **Keep navigation deliberate:** plan direct links, browser history and persistent navigation branches from the accepted route inventory. A declarative router such as `go_router` is a candidate if those requirements call for it; it is not installed or authorized by this plan alone.
- **Use references within their limits:** [`motion-web`](https://github.com/Zachary-1012/motion-web) is research reading only. Its CC BY-NC 4.0 license bars commercial use of its Skill, prompts, cases and derivative workflows; do not bring its code, assets, cases, parameters, verification recipes or derivative workflows into LUMENIS. Define motion from LUMENIS state transitions and define acceptance from LUMENIS contracts and user tasks. For Korean product craft, the public [Toss Design System guide](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components) may be studied for documentation clarity and consistency practices, but its UI Kit materials are limited to the Apps in Toss service. Do not reuse its components, assets, visual patterns or screen layouts. For every external reference, record the named flow, source, abstract principle, LUMENIS workflow it informs and a distinct LUMENIS composition. Do not clone a surface or impose one template across the 44 screens.

### Ordered engineering gates

1. **Plan acceptance:** the product owner accepts this architecture and §§30–36. Until then, no feature-screen implementation.
2. **Capability and owner mapping:** for the chosen workflow, reconcile existing behavior against its canonical module, route, fields, actor, scope, permission, Evidence, effects and regression tests. Record unresolved source claims as blocked; do not infer equivalence from filenames or a ViewModel.
3. **Screen specification:** create one reviewed specification from `../contracts/experience/screen-specifications/SCREEN_SPEC_TEMPLATE.md`. It must resolve owner and callable, entry/return paths, information priority, PC/mobile composition, state matrix, accessibility, side effects and executable acceptance.
4. **Vertical slice:** implement one end-to-end workflow in its owning feature, reusing stable shared primitives only. Keep CTH Subject-first, BMP Brand/Market-first, Shared cross-domain, and SYSTEM infrastructure boundaries.
5. **Acceptance before expansion:** verify source/auth behavior (allowed, denied, missing, stale and error), ViewModel/repository behavior, PC and mobile layouts at representative window widths, keyboard/mouse/touch input, focus/contrast/reduced motion, Evidence traceability, and regression of the preserved capability. Review the actual running app before marking the screen accepted.
6. **Release gate:** only supported platforms with a real build and runtime acceptance may be listed as supported. Keep failed, skipped and unrun checks distinct in the release evidence.

This is a staged delivery plan, not a claim that all 44 planned screens are implemented. Complete and review the first five Golden Pages per screen before expanding to dependent workflow families.

## Verified development checks — 2026-09-20

- Toolchain: Flutter 3.47.5, Dart 3.13.4, Android API 36 / Build Tools 36, JDK 21.
- `flutter analyze`: passed with no issues.
- `flutter test --no-pub`: 75 tests passed, including 1440 px / 390 px Shell and screen-layout coverage.
- `py -3.13 -m pytest tests/test_experience_runtime.py tests/test_subject_registry.py tests/test_shared_database_migrations.py`: 48 passed; no background-thread leaks. The cookie-route test isolates the unrelated app-startup migration from its file/identity assertions.
- Backend capability/permission regressions across BMP truth isolation, AI intent, App permission integration, Shared skills, RuntimeGuardian, login and dual-domain gates: 298 passed; no background-thread leaks.
- `flutter build windows --release --no-pub`: succeeded; `build/windows/x64/runner/Release/lumenis_app.exe` launched locally with title `序境 - LUMENIS` and `Responding=True`.
- `flutter build apk --release`: succeeded; `build/app/outputs/flutter-apk/app-release.apk`, 50,150,362 bytes, SHA-256 `F33E1F471343A0625EC3126FF40B78D895608997E880768DD821E8E22B0E6317`.
- These results prove analysis, tests, compilation and the stated Windows launch smoke only. The APK currently uses the Flutter scaffold's debug signing key. Live authenticated Product Core acceptance, Windows screen-workflow E2E, Android device runtime, store signing, and macOS/Linux/iOS builds remain unverified.

Run Flutter checks from `app/`; run the focused Python suite from the repository root. Keep each failed, skipped and unrun release check distinct. Never report a build as a screen acceptance or platform release.
