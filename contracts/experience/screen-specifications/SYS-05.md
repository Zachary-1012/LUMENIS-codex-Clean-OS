# SYS-05 — Device appearance

```yaml
screen_id: SYS-05
status: DESIGN_READY
revision: 3
owner_domain: SYSTEM Settings
binding_ids:
  - BACKEND-GAP-040 (read-only SYS-05 screen snapshot)
product_owner_approval: Device-local appearance direction recorded in the Experience Constitution
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
presentation_design_decision: DESIGN_READY
reviewer: Root (presentation review); Sol owns remaining runtime acceptance
reviewed_at: 2026-09-24
presentation_reviewed_by: root
presentation_reviewed_at: 2026-09-24
approval_reference: Device-local appearance direction in the Experience Constitution
implementation_state: SOURCE_PRESENT_LOCAL_ONLY
runtime_acceptance: PENDING
local_preference_owner: Sys05AppearanceController via SharedPreferencesAsync
```

## 0. Authority and evidence status

- This screen follows the Experience Constitution's device-local appearance direction and §§31–36. The Constitution remains the only design authority.
- `design_decision: DESIGN_READY` records the source-backed interaction contract. `presentation_design_decision: DESIGN_READY` records root's task-specific composition review on 2026-09-24. Neither field claims whole-product acceptance.
- The frontend candidate is prepared for co-publication in the forthcoming frontend commit with the Round 08 evidence. This supersedes the earlier stale source/hash and untracked-file observation; no commit, remote publication, or release is asserted by this specification.
- Root completed source review and a bounded guarded-Web pass. The browser checks and remaining platform limits are recorded below. Appearance-modal ghosting still has a final visual fix under work, so this is not a claim that the latest modal revision is visually final.
- Source review and a bounded Web pass do not pass the whole Round or the full product. Overall runtime acceptance remains `PENDING`.
- Design intent: one global device-local appearance editor, with the existing `LumenisTheme` remaining the owner of shared semantic contrast roles. Reuse the existing product palette and controls; do not add a second design system.

## 1. User job and invariant

The user changes how the current LUMENIS workspace is presented, then returns to the same work with the same route, scroll position, selection, and unsaved draft. Appearance changes affect presentation only. They do not change business data, Subject, Evidence, Permission, account settings, or server state.

User-owned wallpaper bytes remain local. Selecting, previewing, persisting, or removing an image must never create Evidence or upload the image as a side effect. If local persistence or a native material operation fails, report that failure and do not describe the preference as saved or the operating-system effect as applied.

## 2. Entry, visible surface, and source bindings

| Concern | Current owner/source evidence |
| --- | --- |
| Six modes, preference keys, restore/write/error flow | `app/lib/features/system/sys05/sys05_appearance_controller.dart:8,15-17,55-201` |
| Editor entry, picker, mode and preference controls | `app/lib/features/system/sys05/sys05_appearance_editor.dart:8-35,63-80,119-316` |
| App-level controller, theme application and scope | `app/lib/product/lumenis_app.dart:30-61,69-136` |
| SYS-05 route fetch and local-editor branch | `app/lib/features/system/sys05/sys05_screen.dart:22-48` |
| Existing read-only SYS-05 repository call | `app/lib/features/system/sys05/sys05_repository.dart:8-16` |
| Native material support boundary | `app/lib/platform/lumenis_window_material_io.dart:11-40`; Web/other stub: `app/lib/platform/lumenis_window_material_stub.dart:1-6` |

- The workspace shell exposes `Sys05AppearanceButton`; it opens the same scrollable editor as a constrained bottom sheet (maximum width 620 px). The SYS-05 route uses the shared editor when `Sys05AppearanceScope` is present. The editor itself is local and global to the app instance.
- `LumenisApp` owns one `Sys05AppearanceController`, starts `restore()` at app initialization, listens for changes, and provides the controller through `Sys05AppearanceScope`. The existing `LumenisTheme` still supplies light/dark semantic roles; the app composes those roles with the selected canvas/surface treatment.
- Local preference persistence is owned by `Sys05AppearanceController` through `SharedPreferencesAsync`, using `lumenis.sys05.appearance.v1` for the appearance record and `lumenis.sys05.wallpaper.v1` for the selected image. The image is base64-encoded in the same local preference store. This is device/app-profile persistence on native platforms and origin/profile-scoped browser `localStorage` through the installed web adapter. It is not account synchronization, a server write, or guaranteed cross-device backup.
- `file_selector` opens the user's local image picker. On Web the installed adapter uses the browser's file-selection flow; the selected bytes are then stored locally through the web preference adapter. A bounded Web pass verified wallpaper choose/reload/remove; browser storage quota and failure recovery remain unverified.
- `BACKEND-GAP-040` remains the read-only `GET /api/experience/screen/SYS-05` metadata/snapshot binding through `CoreSys05Repository`. It is not the owner of the appearance values and no preference write is verified. Current source starts the `Sys05ViewModel.refresh()` request in `Sys05Screen.initState()` even when the global appearance scope exists; in that case the screen renders the local appearance editor and does not render the fetched settings snapshot. This read/UI binding redundancy is an implementation follow-up, not permission to add a second settings owner or infer a server write.
- The older no-scope fallback in `Sys05Screen` still contains session-only theme/optical/density/motion/locale fields and `saveLocal()`. `LumenisApp` supplies the appearance scope, so that fallback is not the visible app route in the current root composition. The global shell locale switcher remains the locale control; this editor does not persist or own locale.

## 3. Appearance modes and controls

The editor presents six mutually exclusive backdrop modes. Their names and availability must match the effect that is actually active.

| Mode | Intended visible result | Current source behavior and constraint |
| --- | --- | --- |
| Frosted | Soft in-app optical field, with translucent surfaces | Draws the in-app optical field and applies the shared surface opacity. User can choose light/dark treatment, blur, and panel opacity. |
| Wallpaper | User-selected local image with in-app blur and translucent surfaces | Accepts PNG, JPG/JPEG, or WebP. The editor checks a 3 MiB file limit; the controller checks non-empty bytes, the same byte limit, maximum 8192 px per edge and maximum 32 million pixels. Blur and panel opacity remain adjustable. |
| Desktop material | Native host window material, where the adapter supports it | Current adapter reports support only for non-Web Windows and macOS. Windows calls `flutter_acrylic` acrylic; macOS calls `macos_window_utils` material/brightness APIs. Linux, mobile and Web report unsupported, and the mode control is disabled there. API completion cannot prove the OS rendered the requested effect. |
| White | Opaque white workspace canvas | Uses the light semantic palette. |
| Black | Opaque black workspace canvas | Uses the dark semantic palette. |
| Solid color | One opaque user-selected color | Provides six presets and a six-hex-digit custom color field. Foreground roles switch to black/white based on color luminance. |

Glass modes share `darkGlass`, blur (0–48), and panel opacity (.65–1.0); the desktop material mode omits the in-app blur slider. Compact density, reduced motion and a 13–18 px base UI text-size preference (default 14) are global controls in every mode. The text-size control includes a clearly labelled appearance sample, not sample business records. The App composes this factor with the operating system's text scaler, including nonlinear accessibility scaling. `reducedMotion` sets the theme transition duration to zero and combines with the operating system's `MediaQuery.disableAnimations` preference.

Web cannot expose the operating-system desktop behind a browser. Web therefore uses the chosen local wallpaper with in-page frosting, or the in-app optical field, and does not offer the desktop material mode. A native material failure is surfaced as `appearance.nativeFailed`; the in-app optical field remains the visual fallback. Unsupported effects must never be described as active.

## 4. Persistence, restore, and failure semantics

Appearance controls update the in-memory theme immediately and asynchronously write the local preference record. Writes are serialized so rapid slider changes do not let an older write overtake a newer one. The editor distinguishes saving, remembered, and preview-only/error states. “Remembered” means the local preference adapter completed; it does not mean server sync or cross-device durability.

| Condition | Required honest behavior | Current source behavior |
| --- | --- | --- |
| Initial restore | Keep the editor in a loading state until local preferences are read; then use the restored values. | The editor shows a progress indicator while `loaded` is false. App surfaces initially build from controller defaults while restore is pending; verify whether this is perceptible at runtime. |
| Missing preferences | Use documented safe defaults. | Frosted, light glass, standard density, motion enabled, blur 24, opacity .9, UI base size 14 px, default solid color. |
| Corrupt preference/image data or storage read failure | Use safe defaults, show a localized restore failure, and do not claim restoration succeeded. | `restore()` catches errors, resets controller fields, clears the in-memory wallpaper and sets `appearance.restoreFailed`. It does not delete the corrupt stored value, so the failure can recur on a later launch. |
| Wallpaper mode without a stored image | Do not imply that a wallpaper is active; offer file selection or fall back visibly to frosted mode. | Restore changes this mode to frosted. Selecting Wallpaper opens the image picker before changing mode; cancellation preserves the previous mode and image. The mode changes only after valid selected image bytes are accepted by the existing controller. Mode chips are disabled while picking. |
| Invalid/oversized image or decode failure | Reject it, preserve the previously selected image, and show the localized validation error. | Controller returns `appearance.invalidImage`; size, dimensions and pixel area are bounded. |
| File-picker failure/cancel | Cancel makes no change; a picker exception shows a localized failure. | Cancel returns without mutation; exceptions set the editor-local `appearance.chooseFailed`. |
| Preference write/quota failure | Keep the immediate preview if already applied, clearly mark it preview-only, and do not claim durable local save. Preserve the old image if persisting a replacement fails before it is installed. | Main preference writes surface `appearance.saveFailed`. Image bytes are stored before replacing the in-memory wallpaper. A later preference-record failure can leave new bytes stored while the new mode is preview-only; recovery behavior needs runtime/failure testing. |
| Native call failure | Show an explicit native failure; use in-app fallback and do not claim system material. | The app reports `appearance.nativeFailed`; `LumenisWindowMaterial.apply()` can report only adapter completion, not rendered OS appearance. |
| Remove wallpaper | Remove the local image and return to a truthful non-wallpaper mode. | Removes the wallpaper key then updates to frosted. If the following preference write fails, the mode and stored image may diverge; verify recovery. |

Do not turn any local-storage failure into a successful server save. Do not send image bytes to Flask or the Product Core.

## 5. Composition and responsive behavior

- Entry is a shell palette button, with a tooltip and semantic label. It opens one purpose-built appearance editor, not a generic settings dashboard.
- The editor uses a scrollable, maximum-620-px sheet. On narrow screens the mode chips wrap; the wallpaper/color controls appear only for the selected mode; sliders and switches remain in the same task flow; the bottom sheet accounts for keyboard insets and safe areas. On wider surfaces it stays a focused preference sheet rather than adding a repeated card grid.
- The active workspace is the live preview: changing mode, compact density, motion, opacity or blur updates the current application theme/backdrop. The typography sample demonstrates actual body copy. Representative CTH/BMP workflow appearance is checked on the actual guarded screens; no fictitious business records are introduced into the preview.
- A palette choice must preserve the caller's route, unsaved form text, selected entity, scroll position and other draft state. A bounded guarded-Web run preserved the dirty draft across the appearance change. Native desktop and broader route/scroll preservation remain unverified; repeat those checks before overall runtime acceptance. The mobile viewport check below covers the appearance editor layout, not every route's state.
- Do not create a navigation reset, route replacement, keyed subtree, or account/server write to apply a local theme.

## 6. Keyboard, accessibility, motion and localization

- Mode chips expose selected state. Preset colors have semantic labels. The custom color text field is keyboard-editable and validates exactly six hexadecimal digits before applying. File selection, remove, controls and modal dismissal remain reachable by keyboard and touch.
- Validation and persistence errors use a live-region semantic; use text alongside color for success, unavailable, saving and failure states.
- All visible strings use the current zh-CN/en/ko localization keys. Locale choice remains with the shell locale switcher and is not written into the appearance preference record.
- Reduced motion applies immediately; preserve OS-level motion reduction even when the user has not enabled the app preference. Blur/image rendering cost and text contrast over wallpaper need real-device inspection at low-power and high-contrast conditions.

## 7. Acceptance matrix — overall acceptance pending

| ID | Acceptance assertion | Full acceptance evidence (bounded checks below do not close the row) |
| --- | --- | --- |
| SYS05-MODE-01 | All six modes report the active effect honestly; desktop material is disabled outside supported Windows/macOS hosts; Web uses only in-page materials. | Current source review plus Web, Windows and macOS runtime captures; actual OS render check for native material. |
| SYS05-LOCAL-01 | Appearance and wallpaper restore from the correct local preference owner after restart without a server write or cross-device claim. | Isolated preference test plus app restart on Web and at least one native platform; verify browser origin/profile scope. |
| SYS05-FAIL-01 | Corrupt preferences, rejected images, browser quota/write failure, picker failure and native failure show their correct state and retain or fall back to valid prior appearance. | Existing targeted tests reviewed/run by owner plus controlled adapter failures and runtime recovery; include partial image/prefs write case. |
| SYS05-DRAFT-01 | Changing appearance leaves the active route, dirty form draft, selection and scroll position intact and returns to that same work. | Real Web Workspace and native desktop E2E with a real screen and local unsaved draft. |
| SYS05-A11Y-01 | Mode/color/file controls are keyboard/touch operable and announced; reduced motion and readable contrast hold across wallpaper and solid colors. | Keyboard and screen-reader check, reduced-motion run, contrast sampling on actual surfaces. |
| SYS05-REAL-USER-01 | A user changes a local appearance preference, sees the workspace update, restarts to restore it, and can distinguish local persistence from server/account state. | Root-owned real runtime flow and state-preservation evidence; no synthetic fixture or HTTP success substitutes. |

### Root presentation review and bounded evidence — 2026-09-24

| Check | Result | Limit |
| --- | --- | --- |
| Task-specific appearance editor composition reviewed against current source and guarded browser pages | `DESIGN_READY` | Presentation review only; no overall workflow or round acceptance |
| Web wallpaper choose, reload, and remove | `PASS` | Bounded browser path; quota/error recovery and other browser profiles remain unverified |
| Base-font path 14→15 and 18→14 keyboard check | `PASS` | Does not replace OS accessibility scaling or full text enlargement coverage |
| Pure-black appearance | `PASS` | No claim for every custom color or wallpaper contrast condition |
| Reduced-motion behavior | `PASS` | Native reduced-motion parity remains unverified |
| Dirty draft preserved across appearance change | `PASS` | Guarded Web path only; native desktop and broader route/scroll coverage remain unverified |
| Mobile 390×844 at 18 px with no horizontal overflow | `PASS` | This viewport only |
| Windows build | `PASS` | Build evidence only; it does not prove the OS rendered system material |
| Windows native material effect | `UNVERIFIED` | Requires actual native visual verification |
| macOS, iOS and Android runtime | `UNVERIFIED` | No platform runtime result is claimed |
| Appearance-modal readability and live black/light adaptation | `PASS` | Final Web build inspected; near-opaque modal surface keeps workspace text from interfering |

## 8. Cross-cutting impact and decision

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none. Presentation preferences do not alter commercial, brand or Guangzhou Taikoo Hui coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable to local appearance; no entity sample is required.
- Permission/Evidence/effect: no business permission, Evidence, external action or server write is owned by this screen. Wallpaper remains local and is never Evidence.
- Canonical owner: SYSTEM Settings owns device appearance preferences; `LumenisTheme` remains the shared semantic color-role owner; `SharedPreferencesAsync` is only the persistence adapter.
- Design decision: `DESIGN_READY` for the source-backed interaction and state contract; presentation design is separately `DESIGN_READY` after root review. The frontend candidate is scheduled to co-publish with Round 08 evidence. Overall runtime/visual, native-effect and real-user acceptance remain `PENDING`; this document does not claim a whole-round PASS, release, or commercial readiness.
