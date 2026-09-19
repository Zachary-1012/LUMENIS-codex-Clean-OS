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

## Local Flutter availability

During the repository check on 2026-09-19, the current PowerShell session did not resolve a `flutter` executable with `Get-Command flutter`. This does not establish whether Flutter is installed elsewhere on the machine or on a build host. No Flutter analyze, test or platform build result is claimed here; verify SDK availability on the actual development/build host before running those checks.
