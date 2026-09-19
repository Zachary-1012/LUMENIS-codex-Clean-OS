# LUMENIS App

This is the repository's **single canonical Flutter app target** and the only intended user-facing app implementation for 序境 / LUMENIS. Its current implementation is a **bootstrap**, not a complete product app.

## Current implementation status

- The launch surface requests the Product Core runtime identity and subjects. This client does not establish that subject authorization is verified end to end.
- The Core client also exposes `GET /api/experience/screen/<screen_id>`, but the current launch surface does not call it.
- These bootstrap requests do **not** mean the Experience contracts are implemented. The repository defines 44 screen-specific UX blueprints and 54 truth-binding rows. Screen composition is bespoke per workflow; the binding registry constrains only data/API/actor/permission/Evidence truth. Legacy `sectionTypes` do not prescribe layouts, and a generic renderer is prohibited.
- The app has not been verified as a build or release target for Windows, macOS, Linux, Android or iOS. Those are product target intentions, not claims of current platform support. Platform builds and runtime behavior require acceptance on the respective hosts/devices.

Do not invent UI data, backend behavior, permission results or successful actions to make an unbound screen appear complete. Keep `UNKNOWN`, `NOT_AVAILABLE`, `NOT_COLLECTED`, `STALE`, `BLOCKED` and `ERROR` distinct. A contract or fixture is not proof of a working endpoint or feature.

## Product Core connection

Default Core URL: `http://127.0.0.1:8201`

Override for an authorized device/build:

```text
--dart-define=LUMENIS_CORE_URL=<authorized-core-url>
```

Bootstrap GET contracts:

```text
GET /api/experience/runtime/identity
GET /api/experience/subjects
GET /api/experience/screen/<screen_id>
```

The app consumes LUMENIS Product Core. It must not create a second Evidence, Canonical Data, Metric, Permission, Runtime or business-truth owner.

## Required development authority

Follow `../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §§30–36 for app architecture, the 44 screen-specific UX blueprints, CTH/BMP/Shared/SYSTEM ownership, desktop/mobile composition, accessibility, motion and originality boundaries, ordered implementation and acceptance. That Constitution is the sole UI/UX and interaction authority. Do not create another visual design specification or copy historical web UI.

The 44-screen designs are planning specifications, not implemented screens. Feature implementation begins only after the product owner accepts this architecture and screen-by-screen UX plan. Until then, keep work limited to repository truth/owner cleanup, contract repair and acceptance scaffolding; do not build generic screens or claim feature parity.

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
- **Use references as principles, never templates:** the linked [`motion-web` repository](https://github.com/Zachary-1012/motion-web) is a creative-web motion reference, not a LUMENIS screen library. Borrow only causal, state-explaining motion and demonstrable interaction checks; do not copy its cases, layouts, code or web-only effects into Flutter. Korean app references are evaluated per workflow for a specific interaction principle, then re-composed around LUMENIS's CTH/BMP semantics, evidence and visual identity. Do not clone a Korean app's surface or impose one visual template across the 44 screens.

### Ordered engineering gates

1. **Plan acceptance:** the product owner accepts this architecture and §§30–36. Until then, no feature-screen implementation.
2. **Capability and owner mapping:** for the chosen workflow, reconcile existing behavior against its canonical module, route, fields, actor, scope, permission, Evidence, effects and regression tests. Record unresolved source claims as blocked; do not infer equivalence from filenames or a ViewModel.
3. **Screen specification:** create one reviewed specification from `../contracts/experience/screen-specifications/SCREEN_SPEC_TEMPLATE.md`. It must resolve owner and callable, entry/return paths, information priority, PC/mobile composition, state matrix, accessibility, side effects and executable acceptance.
4. **Vertical slice:** implement one end-to-end workflow in its owning feature, reusing stable shared primitives only. Keep CTH Subject-first, BMP Brand/Market-first, Shared cross-domain, and SYSTEM infrastructure boundaries.
5. **Acceptance before expansion:** verify source/auth behavior (allowed, denied, missing, stale and error), ViewModel/repository behavior, PC and mobile layouts at representative window widths, keyboard/mouse/touch input, focus/contrast/reduced motion, Evidence traceability, and regression of the preserved capability. Review the actual running app before marking the screen accepted.
6. **Release gate:** only supported platforms with a real build and runtime acceptance may be listed as supported. Keep failed, skipped and unrun checks distinct in the release evidence.

This is a staged delivery plan, not a claim that the bootstrap or the 44 planned screens have been implemented. Start with the five Golden Pages only after plan and per-screen gates pass; then sequence dependent workflows by verified ownership, not by a 44-screen batch.

## Local Flutter availability

During the repository check on 2026-09-19, the current PowerShell session did not resolve a `flutter` executable with `Get-Command flutter`. This does not establish whether Flutter is installed elsewhere on the machine or on a build host. No Flutter analyze, test or platform build result is claimed here; verify SDK availability on the actual development/build host before running those checks.
