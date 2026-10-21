# SYS-05 — Device appearance

```yaml
screen_id: SYS-05
status: DESIGN_READY
revision: 6
owner_domain: SYSTEM Settings
binding_ids:
  - BACKEND-GAP-040 (read-only SYS-05 screen snapshot)
product_owner_approval: Device-local appearance direction recorded in the Experience Constitution
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
presentation_design_decision: DESIGN_READY
reviewer: Root (presentation review); Sol owns remaining runtime acceptance
reviewed_at: 2026-09-27
presentation_reviewed_by: root
presentation_reviewed_at: 2026-09-27
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
- `BACKEND-GAP-040` remains the read-only `GET /api/experience/screen/SYS-05` metadata/snapshot binding through `CoreSys05Repository`. It is not the owner of the appearance values and no preference write is verified. The source now checks `Sys05AppearanceScope` before mounting the remote settings branch. With the global local-preference owner present, opening or rebuilding the appearance route makes no SYS-05 snapshot request. Without that scope, the existing read-only repository and session-only fallback remain available; leaving that branch disposes its view model. This is a bounded lifecycle repair, not a new settings owner or server write. Automated checks are recorded in the owning Round 14 evidence; current runtime acceptance remains pending.
- The older no-scope fallback in `Sys05Screen` still contains session-only theme/optical/density/motion/locale fields and `saveLocal()`. `LumenisApp` supplies the appearance scope, so that fallback is not the visible app route in the current root composition. The global shell locale switcher remains the locale control; this editor does not persist or own locale.

## 3. Appearance modes and controls

The editor presents six mutually exclusive backdrop modes. Their names and availability must match the effect that is actually active.

| Mode | Intended visible result | Current source behavior and constraint |
| --- | --- | --- |
| Frosted | Soft in-app optical field, with translucent surfaces | Draws the in-app optical field and applies the shared surface opacity. User can choose light/dark treatment, blur, and panel opacity. |
| Wallpaper | Built-in preset or user-selected local image with in-app blur and translucent surfaces | Built-in presets and user images share the same local `setWallpaper` path and wallpaper key. User images accept PNG, JPG/JPEG, or WebP. The editor checks a 3 MiB file limit; the controller checks non-empty bytes, the same byte limit, maximum 8192 px per edge and maximum 32 million pixels. Blur and panel opacity remain adjustable. |
| Desktop material | Native host window material, where the adapter supports it | Current adapter reports support only for non-Web Windows and macOS. Windows calls `flutter_acrylic` acrylic; macOS calls `macos_window_utils` material/brightness APIs. Linux, mobile and Web report unsupported, and the mode control is disabled there. API completion cannot prove the OS rendered the requested effect. |
| White | Opaque white workspace canvas | Uses the light semantic palette. |
| Black | Opaque black workspace canvas | Uses the dark semantic palette. |
| Solid color | One opaque user-selected color | Provides six presets and a six-hex-digit custom color field. Foreground roles switch to black/white based on color luminance. |

Glass modes share `darkGlass`, blur (0–48), and panel opacity (.65–1.0); the desktop material mode omits the in-app blur slider. Compact density, reduced motion and a 13–18 px base UI text-size preference (default 14) are global controls in every mode. The text-size control includes a clearly labelled appearance sample, not sample business records. The App composes this factor with the operating system's text scaler, including nonlinear accessibility scaling. `reducedMotion` sets the theme transition duration to zero and combines with the operating system's `MediaQuery.disableAnimations` preference.

Two built-in wallpaper choices, Crimson Sunset and Cobalt Dusk, remain visible in every backdrop mode between the mode chips and base-font controls. Their localized, keyboard-operable buttons load the original bundled asset bytes and pass them through the existing `setWallpaper` validation and local persistence path. They do not create a preset identifier, a second storage key, or a network request; the current image preview shows the selected bytes. A bundle-load failure preserves the current appearance and reports the existing wallpaper-choice error.

Web cannot expose the operating-system desktop behind a browser. Web therefore uses the chosen local wallpaper with in-page frosting, or the in-app optical field, and does not offer the desktop material mode. A native material failure is surfaced as `appearance.nativeFailed`; the in-app optical field remains the visual fallback. Unsupported effects must never be described as active.

## 4. Persistence, restore, and failure semantics

Appearance controls update the in-memory theme immediately and asynchronously write the local preference record. Writes are serialized so rapid slider changes do not let an older write overtake a newer one. The editor distinguishes saving, remembered, and preview-only/error states. “Remembered” means the local preference adapter completed; it does not mean server sync or cross-device durability.

| Condition | Required honest behavior | Current source behavior |
| --- | --- | --- |
| Initial restore | Keep the editor in a loading state until local preferences are read; then use the restored values. | The editor shows a progress indicator while `loaded` is false. App surfaces initially build from controller defaults while restore is pending; verify whether this is perceptible at runtime. |
| Missing preferences | Use documented safe defaults. | Frosted, light glass, standard density, motion enabled, blur 24, opacity .9, UI base size 14 px, default solid color. |
| Corrupt preference/image data or storage read failure | Use safe defaults and show a localized restore failure. Never delete local preferences automatically. Offer a user-triggered reset that clears only the appearance and wallpaper keys; report partial storage failure and keep the action available for retry. | `restore()` keeps the corrupt keys and sets `appearance.restoreFailed`. Ordinary appearance edits preserve the recovery action. The active editor offers `appearance.resetLocal`; reset waits for in-flight wallpaper operations and preference writes before attempting both key removals. Defaults become active only when both removals complete, and a partial failure remains visible as `appearance.resetLocalFailed` for retry. |
| Wallpaper mode without a stored image | Do not imply that a wallpaper is active; offer file selection or fall back visibly to frosted mode. | Restore changes this mode to frosted. Selecting Wallpaper opens the image picker before changing mode; cancellation preserves the previous mode and image. The mode changes only after valid selected image bytes are accepted by the existing controller. Mode chips are disabled while picking. |
| Invalid/oversized image or decode failure | Reject it, preserve the previously selected image, and show the localized validation error. | Controller returns `appearance.invalidImage`; size, dimensions and pixel area are bounded. |
| File-picker failure/cancel | Cancel makes no change; a picker exception shows a localized failure. | Cancel returns without mutation; exceptions set the editor-local `appearance.chooseFailed`. |
| Preference write/quota failure | Keep the immediate preview if already applied, clearly mark it preview-only, and do not claim durable local save. Preserve the old image if persisting a replacement fails before it is installed. | Main preference writes surface `appearance.saveFailed`. Image bytes are stored before replacing the in-memory wallpaper. A later preference-record failure can leave new bytes stored while the new mode is preview-only; recovery behavior needs runtime/failure testing. |
| Native call failure | Show an explicit native failure; use in-app fallback and do not claim system material. | The app reports `appearance.nativeFailed`; `LumenisWindowMaterial.apply()` can report only adapter completion, not rendered OS appearance. |
| Remove wallpaper | Remove the local image and return to a truthful non-wallpaper mode. | Removes the wallpaper key then updates to frosted. If the following preference write fails, the mode and stored image may diverge; verify recovery. |

Do not turn any local-storage failure into a successful server save. Do not send image bytes to Flask or the Product Core.

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-05)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：视觉风格 · Logo · 五位角色（闭环内，PO 2026-10-14）


**4. States：正常 / 加载 / 素材缺失（显示占位名字，不用他人素材）。**


**9. Acceptance**
- 切换主题后路由、滚动、选择、未保存草稿不变（SYS-05 原合同）。
- Logo/角色图为自有矢量稿，许可清楚；AI 草图生成的素材标注来源。
- 200% 字号与减少动态效果下全部屏可用。

### Existing contract — Composition and responsive behavior

- Entry is a shell palette button, with a tooltip and semantic label. It opens one purpose-built appearance editor, not a generic settings dashboard.
- The editor uses a scrollable, maximum-620-px sheet. On narrow screens the six mode choices remain in one horizontally scrollable row; wallpaper/color controls appear only for the selected mode; sliders and switches remain in the same task flow; the bottom sheet accounts for keyboard insets and safe areas. On wider surfaces it stays a focused preference sheet rather than adding a repeated card grid.
- The two built-in wallpaper buttons sit immediately after the backdrop mode choices in a two-column thumbnail layout, with 12–16 px corners, visible localized labels, keyboard/touch activation and button semantics. The presets remain available in every backdrop mode. In Wallpaper mode, the active image preview and choose/remove controls follow the presets before the appearance-adjustment settings.
- The active workspace is the live preview: changing mode, compact density, motion, opacity or blur updates the current application theme/backdrop. The typography sample demonstrates actual body copy. Representative CTH/BMP workflow appearance is checked on the actual guarded screens; no fictitious business records are introduced into the preview.
- A palette choice must preserve the caller's route, unsaved form text, selected entity, scroll position and other draft state. A bounded guarded-Web run preserved the dirty draft across the appearance change. Native desktop and broader route/scroll preservation remain unverified; repeat those checks before overall runtime acceptance. The mobile viewport check below covers the appearance editor layout, not every route's state.
- Do not create a navigation reset, route replacement, keyed subtree, or account/server write to apply a local theme.



### 三语状态文案

| Key | zh-CN | en | ko |
|---|---|---|---|
| loading | 加载中 | Loading | 불러오는 중 |
| missing | 数据缺失 | Data unavailable | 데이터 없음 |
| unavailable | 暂不可用 | Currently unavailable | 현재 사용할 수 없음 |
| denied | 无权执行此操作 | This action is not permitted | 이 작업 권한이 없습니다 |
| retry | 重试 | Retry | 다시 시도 |
| cancel | 取消 | Cancel | 취소 |
| save | 保存 | Save | 저장 |
| revise | 修订 | Revise | 수정 |
| reopen | 重新打开 | Reopen | 다시 열기 |
| recover | 恢复 | Recover | 복구 |
| return | 返回原任务 | Return to task | 원래 작업으로 돌아가기 |

全部新增标签、说明、确认及读屏名称须沿现有三语键实现；上表仅通用状态，不证明全产品翻译/运行完成。逐屏验收覆盖 zh-CN/en/ko、200%字号、键盘/读屏和减少动态。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：视觉风格 · Logo · 五位角色（闭环内，PO 2026-10-14）

保留原任务与状态。

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：视觉风格 · Logo · 五位角色（闭环内，PO 2026-10-14）

Web：偏好控件与真实预览按宽度重组；键盘/200%字号可操作，减少动态和用户原选择即时可见并持久读回，不改业务数据。 手机纵排，预览改为整页实时生效。


### Existing contract — Keyboard, accessibility, motion and localization

- Mode chips expose selected state. Preset colors have semantic labels. The custom color text field is keyboard-editable and validates exactly six hexadecimal digits before applying. File selection, remove, controls and modal dismissal remain reachable by keyboard and touch.
- Validation and persistence errors use a live-region semantic; use text alongside color for success, unavailable, saving and failure states.
- All visible strings use the current zh-CN/en/ko localization keys, including `appearance.resetLocal`, `appearance.resetLocalComplete`, and `appearance.resetLocalFailed`. Locale choice remains with the shell locale switcher and is not written into the appearance preference record.
- Reduced motion applies immediately; preserve OS-level motion reduction even when the user has not enabled the app preference. Blur/image rendering cost and text contrast over wallpaper need real-device inspection at low-power and high-contrast conditions.
- Wallpaper mode automatically computes the minimum light/dark protective scrim from the active text and primary-action colors, with a raster rounding margin. It uses the worst possible image region, rather than a photo-specific value or an average-color sample that could miss a highlight or dark edge. The existing Theme owner strengthens small secondary text and adjusts domain/status tones toward readable ink only as needed; normal text, text buttons and semantic status text must retain at least 4.5:1 contrast over white, black, saturated and mixed regions. AI-01's decorative glows yield to the selected wallpaper so they cannot repaint the protected backdrop. Mode selection and panel opacity remain local controls; source image bytes are unchanged.
- Wallpaper theme colors and the protective backdrop switch together without interpolating through low-contrast middle colors. Other modes retain their existing theme motion; reduced-motion preference still applies.

## 7. Acceptance matrix — overall acceptance pending

| ID | Acceptance assertion | Full acceptance evidence (bounded checks below do not close the row) |
| --- | --- | --- |
| SYS05-MODE-01 | All six modes report the active effect honestly; desktop material is disabled outside supported Windows/macOS hosts; Web uses only in-page materials. | Current source review plus Web, Windows and macOS runtime captures; actual OS render check for native material. |
| SYS05-LOCAL-01 | Appearance and wallpaper restore from the correct local preference owner after restart without a server write or cross-device claim. | Isolated preference test plus app restart on Web and at least one native platform; verify browser origin/profile scope. |
| SYS05-RESET-01 | After a corrupt restore, the user can explicitly remove only the two local appearance keys, return to defaults, and retry if either removal fails. | Controller and active-editor tests prove no automatic deletion, waiting for pending wallpaper and preference storage operations, truthful partial failure, retry, and successful default restoration. |
| SYS05-PRESET-01 | A user can choose either bundled wallpaper preset from any backdrop mode; the original bytes use the existing local wallpaper owner and restore after reopening. | Active-editor asset-tap test verifies the bundled bytes reach the existing controller and reopen from local preferences; no separate preset state or server request is introduced. |
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
| macOS and iOS native runtime | `UNVERIFIED` | No platform runtime result is claimed |
| Android native runtime (historical, outside current target) | `UNVERIFIED` | Historical status retained; it is not a current native delivery gate |
| Appearance-modal readability and live black/light adaptation | `PASS` | Final Web build inspected; near-opaque modal surface keeps workspace text from interfering |

### R14 mobile and desktop composition review — 2026-09-27

- Within the existing `DESIGN_READY` device-local appearance workflow, the editor order is mode choice → preset choice → active wallpaper preview and file actions when Wallpaper is selected → mode-specific appearance controls → separated typography, density and motion preferences.
- The six mode choices use one horizontal row on narrow widths instead of wrapping into multiple chip rows. Presets keep their original bundled bytes and existing controller path; their rectangular thumbnails use explicit 14 px corners, readable localized labels and at least a 48 px action target. The type sample is unboxed and reflects the selected base size.
- The SYS-05 route maximum width remains 760 px. Opening appearance from a phone retains a visible strip of the originating task behind a safe-area sheet, capped at 92% of available height. At 768 px and wider, appearance opens in a 460 px right-side panel so the original workspace remains visible while preferences change. Both use the same controller and editor, keep the title/close action fixed while settings scroll, and return to the unchanged caller on close/Escape.
- The Product Owner's 47.367-second phone recording was reviewed on 2026-09-27 (20 keyframes plus transition sampling; source SHA-256 `a621b320ff76dff07ff6ed7f2b8974a91f78234ae21ce087f1da960950e970e1`). ADAPT only the principles of persistent return, grouped readable controls and a visible underlying task. Its account data, product features, logos and exact screen layouts are not product inputs. The root approves the bounded composition above under the existing Experience Constitution; the recording grants no account or browser automation authority.
- This is a presentation-only source adjustment. No controller, preference, Theme, API, business state, localization key or effect boundary changes. The `DESIGN_READY` interaction/business contract and overall `PENDING` runtime acceptance are unchanged. The scoped widget regression is added but was not run in this batch; no browser or device evidence is claimed.

## 8. Cross-cutting impact and decision

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none. Presentation preferences do not alter commercial, brand or registered-subject coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable to local appearance; no entity sample is required.
- Permission/Evidence/effect: no business permission, Evidence, external action or server write is owned by this screen. Wallpaper remains local and is never Evidence.
- Canonical owner: SYSTEM Settings owns device appearance preferences; `LumenisTheme` remains the shared semantic color-role owner; `SharedPreferencesAsync` is only the persistence adapter.
- Design decision: `DESIGN_READY` for the source-backed interaction and state contract; presentation design is separately `DESIGN_READY` after root review. The frontend candidate is scheduled to co-publish with Round 08 evidence. Overall runtime/visual, native-effect and real-user acceptance remain `PENDING`; this document does not claim a whole-round PASS, release, or commercial readiness.


### 原动效、成果揭示与物理参数（原要求落屏，未验部分保持OPEN）

沿唯一规划§4.1/4.2及J29、总草图§1.2/1.3，原外观/字体/密度控件保留。在本屏原“动效”分组增加对应既有目标的三层：全局原动效偏好；新成果揭示的完整/跟随系统/关闭及立即跳过；可展开物理预览与真实参数。不要用新的结果揭示替换原动效，也不把这两者等同UI自身AIGC。

参数按原语义分“质量/刚度/阻尼”“磁吸范围/强度/脱离阈值”“释放速度/摩擦/回弹”及已批准拾起/倾角/翻面反馈；控件同时有标签、当前值/单位、可访问数值输入和恢复原默认。只有确已接计算与合法对象的参数可用，未接说明OPEN，不用空滑杆造功能。预览是同一可操作示例对象和合法落点：拖动/松手/重抓/取消可见实际轨迹变化；键盘有等价移动/选择，普通鼠标不冒真实压力。

Web/Windows/macOS预览与参数主辅并读，窄Web/iOS先预览后参数分组，标题/取消/采用/恢复默认可达；iOS触控、桌面鼠标/触控板分别验，官网只公开演示而不读取用户私有偏好。试调只影响预览，采用按原本地Settings保存读回，失败明确仅本次或未保存；取消回原偏好和工作锚点。减少动态/关闭即时给同信息动作，不改Timeline时码/业务值/权限。新成果仅真实持久读回+字体/布局就绪后揭示一次，导航/缩放/取消/版本变化清理旧几何，可立即跳过。验参数实际改变轨迹、低帧/后台返回/重抓中断、保存重启/撤销、三语/200%文字/读屏和各表面实机；历史Web局部PASS不能外推本新增接线已通过。

## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 调整设备外观并返回相同工作状态。
- **屏幕专属呈现：** 本地偏好预览/对照/撤销，配色和壁纸只影响本端呈现
- **来源、范围与版本连续性：** 保持route/scroll/selection/draft；偏好使用现有本地owner，不变业务数据
- **四端差异：** Web按网页本端；Desktop适配窗口；Mobile适配触摸；官网使用公开品牌视觉而非用户私有壁纸
- **失败与恢复：** 持久化失败不称已保存；撤销回旧偏好；壁纸不上传、不写Evidence
- **补充验收：** 四端偏好不串scope，预览保存重启恢复分别可验证。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


### 全项具体工作合同：本地成品语音与朗读的区分

字段由实际toolchain/voice owner返回，无工具、语言不支持、文本过长、超时、取消、音频校验失败、产物待归档分开。取消清本任务临时文件并保稿/原音轨，换文本版本使旧试听待重做；重开读取实际输出hash，不自动再生成。验收Flite语言边界、eSpeak可用性、合法WAV、试听停止、取消、不自动入轨、失败保旧版及Web/Windows/macOS/iOS单独核质量。

BMP-08配音页保原稿、实际引擎/语种/音色能力和试听/停止/采用素材；候选声轨与原音轨AB对照，标合成方式及未验质量。SYS-05仅保朗读语言/速率和当前会话控制，入口文案避免两者混淆。Web/Desktop/iOS各显示真实本机/已绑定Core可用能力，手机不因服务器支持便宣称离线合成；官网只述已核范围。UI适配根据是否已有可试听候选重组稿/播放器，不替用户换音色或把合成声音当UI创新。

具体操作与恢复：本地语音制作作为既有可选配音动作，先显示实际已安装引擎/音色/支持语言、输入文本和本次输出限制。当前Flite只支持英语和有限已安装音色；eSpeak NG共振峰适配接受中/韩/英，质量与各端仍未验，不冒自研模型或人物声音克隆。用户明确生成后得到可试听WAV候选，确认采用才作为新素材进入工程；不默认下载工具/权重、不换外部API。系统Read Aloud仍只是当前文本的本机试听，不保存成品、不自动入轨。


### 原创可爱加载反馈与不中断工作（G14/G116）

在真正等待数据/保存/分析/渲染的原结果位置，允许有轻量、可爱且原创的序境小动作：例如已有品牌语汇中的纸角轻展、笔尖短促点动、柔和小形状探头；不模仿外部品牌外观，不增加产品角色/人格或强迫使用者互动。状态文字、正在处理的对象、已得部分结果、允许取消/返回始终比动画清楚。动作表达“正在等”，不代表内部步骤数、百分比、剩余时间或成功；有真实进度回执才显示其定义及数值，未知时明确未知。

加载不设为了看完动效的最低等待时间，已有结果立即可读；数据回来即按真实状态收束，不先播放庆祝。保存失败、拒绝、离线、取消请求/实际停止和结果待核各就地呈现，不让可爱表情淡化问题或藏错误。请求停止后仍可能在等待安全边界，动画可减弱但不能展示整个动作已撤回。部分结果出现不挤走选字、编辑焦点或读屏位置；重试只作用原Owner允许的失败对象，未知效果先核回执。

SYS-05原外观/动态设置增加可发现的等待动效开关，服从系统减少动态/低功耗与用户选择：可用静态小图形和状态文字，完全关闭仍功能齐全。未有设置持久回执只说明本次会话生效，不能伪称跨端已同步。装饰不进入读屏重复播报，状态用受控礼貌播报，失败/必要确认仍可达；不闪烁，不不断旋转抢注意，不抢输入，不播放未请求音效。后台、不可见或页面销毁时停动画资源，真实任务继续状态由Owner读回。

官网只为真实页面资源/用户提交的等待或明确标示的演示呈现；Web保浏览器返回和慢网，Windows/macOS各验窗口遮挡/休眠/冷开，iOS紧邻当前对象显示小动作且不遮键盘/主要控件。布局和效果可由界面自身AIGC按真实任务、可用表现与设备提出原创可编辑方案，但事实字段/权限/取消仍由原控件承接；用户可锁定/撤销、使用稳定基础布局。加载小动画既不替代原200以上交互/物理要求，也不等同界面本身AIGC能力已经实现。

采用价值以减少不确定、少误点和少返工验证：记录首个可操作结果时间、等待期间重复提交/误取消、关键控件可达性、帧/能耗及无障碍表现；同任务同设备比较开/关动效，未测不编加速或节省数字。现只交原Owner事件与前端合同，实际可爱动效、偏好持久化和四端呈现由本地构建验收。


### 2026-10-21 交互源码吸收：开发前行为边界

材料：[独立审核包](../../../research/engineering/documentation-evidence/reports/product_research_deadline_20261018/interaction_equivalent_20261017/README.md)，静态对读 `src/appearance-preferences.mjs、file-preferences.mjs、local-persistence.mjs、experience-policy.mjs、physics.mjs、physical-drawer.mjs、drawer-study.mjs、app.mjs`。这里只吸收适用行为与反例，不执行、移植或发布审核包，不改变本屏既有实现/验收状态。

外观保持 `app/lib/features/system/sys05/sys05_appearance_controller.dart` 的现有偏好键、串行写入及原产品选项，不复制审核包的localStorage键、默认色或新增平行设置库。当前控制器update会持久化；审核包“预览后显式保存”不能被文档当作当前产品已存在行为。凡界面提供预览，必须与已保存状态分开；写入后精确读回，异常标“未确认保存”并保工作值，不能推断一定未写入或盲重试。重置只清本设置已声明键，逐键核读回并报告部分失败；壁纸来源与实际持久方式按现有Owner，不把演示内存URL写入产品。

抽屉/可拖对象保pointer所有权、重抓位置速度连续、取消/失焦/离开/尺寸变化失效旧回调；CSS px与Flutter logical px和秒制速度显式换算。媒体播放头不加弹簧。现有 `app/lib/core/generated_result_reveal.dart` 才是Flutter揭示Owner：新结果读回、稳定已注册字体与真实布局后一次播放，跳过/字体未就绪/换版取消不阻内容；不得以JS离线动画替换它。复用 `app/test/core/generated_result_reveal_test.dart` 并补对应真机操作，demo参数/单帧图不是30/60/120Hz及无障碍通过。
