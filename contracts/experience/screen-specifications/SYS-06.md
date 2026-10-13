# SYS-06 — Internal browser capability

## 2026-10-11 当前目标：业务任务中的真实内置浏览器

用户从原帖/引用/研究任务进入真实网页，能看到安全网址、当前页面和操作状态，进行获准导航与网页操作、独占接管、停止并返回原任务。默认在序境内呈现，外部浏览器由用户明确选择；无AI也可正常浏览。自动采集保持后台无头，不占用桌面焦点。

既有 SYSTEM worker 执行网页；Core 核验 actor/task/scope/session、每次动作和来源用途；SYS-06只呈现真实画面与可用操作。不得用iframe失败、静态截图、raw CDP前端直连或另开桌面应用替代。方法参考公开浏览器会话/动作与画面原理，具体安全传输必须真实实现，不能宣称已复制GPT私有架构。

通用操作系统、任意本机软件/键鼠与远程电脑控制已经撤出产品范围，相关历史要求已删除，不再要求GUI worker才能完成本屏。既有浏览器任务绑定、支持的网页动作、受控文件传输、权限、来源保存与重开恢复缺口仍需实际验收；文档更正不能将其记为通过。本规格不声明当前窗口派工状态。

```yaml
screen_id: SYS-06
status: IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED
revision: 7
owner_domain: SYSTEM Browser / CDP
binding_ids:
  - BACKEND-GAP-041
product_owner_approval: DIRECT_IMPLEMENTATION_SCOPE_2026-10-05
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
reviewer: M bounded implementation review
reviewed_at: 2026-10-05
approval_reference: Product Owner direct internal-browser repair approval
```

## 0. Authority basis and artifact disposition

- Constitution basis: controlled internal browser blueprint, separate personal browsing boundary, provenance and §36.
- Product contract: SYSTEM browser capability supports controlled acquisition; it is not a user personal browser and does not authorize collection effects.
- References: `KEEP_AS_EXPLORATION`; no external browser UI is copied.
- Anti-template check: normal-browser use (address bar, back/forward/refresh, tabs, collapsible, modeled on OpenAI in-app browser) over server-owned sessions plus an optional view-original external jump; not a generic dashboard.
- Current source decision: the bounded reader below is implemented; runtime,
  full accessibility and whole-screen real-user acceptance remain open. Revision 7
  has the bounded local-Web manual-note runtime evidence described below.

## 0.1b Current revision-7 source delta — 2026-10-09

Manual research notes use the existing Shared SavedWork owner: choose an explicit
CTH/BMP context, write a note while viewing an authorized public page, save,
list/reopen and revise with server Artifact SHA and parent-version checks.
No model is required. Automatic locator metadata keeps only the site origin;
credentials, paths, queries and fragments are omitted. Notes have empty citations,
NOT_IMPORTED / NOT_VERIFIED source status and UNBOUND task status. They are user
writing, not captured Source/Evidence or a completed Task/Run binding.

Existing scope/Permission and effect fences reauthorize every operation. A changed
context or stale async response cannot silently replace the current draft. An
unconfirmed save reuses its request ID; revisions preserve the earlier Artifact.
The UI can reopen saved notes after the browser session ends. The binary transport
retains all three server viewport headers required for safe human frame binding.
Malformed frame metadata is a preview failure, not an invalid user URL.

The isolated Browser-outcome startup profile permits only existing manual Browser
and Shared SavedWork endpoints alongside the safe Workspace reads. It requires a
new OS-temp DB, loopback/non-production port and no automatic product services.
An explicitly selected OS-temp Web artifact avoids overwriting the live build.
This is a development acceptance entry, not deployment or a Permission bypass.
Runtime evidence and any remaining failures are recorded in the existing round-15
M-20261009-TOOLS-BROWSER-AI-OPTIONAL-DELIVERY record; full SYS-06 remains OPEN.

Observed local-Web outcome: real allowed Bing page and visible frame, manual note
v1, reopen, revisions v2/v3, explicit browser stop, full Web reload, reopen v3 and
unchanged v1. The actual Shared SavedWork service persisted all versions in a fresh
temporary database. No model, mock or production database was used. UI automation
initially appended text during replacement; actual Ctrl+A editing corrected it in
v3 without deleting v2. This proves manual-note continuity only, not imported
Source/Evidence, Task binding, arbitrary page control or production acceptance.

## 0.1a Current revision-6 source delta — 2026-10-09

The current source adds server-owned short-lived exclusive human control and
frame/target/page-revision/viewport binding. SYS-06 exposes only actions actually
advertised by the server: navigate, back, forward, reload and remote scroll.
Local image pan/zoom remains different from remote page scroll. Click, input,
select, upload and download are not implemented by this delta; the complete
approved interaction target in §0.3 remains OPEN, not reduced.

Acquire control before a human action; a lease blocks competing Agent actions.
Each action uses the current server frame binding and refreshes after success.
Stale frames, expired leases, denied actions and stopped sessions are explicit
failures. Stop and Return-to-task remain separate. A failed stop retains the
control token for retry; a failed readback attempts release without claiming it
succeeded. Task/run association is BOUND only with server verification; client
IDs alone stay UNBOUND/UNVERIFIED and are not published as task Evidence.

No model is required for these deterministic/manual controls. The optional
Browser Use route stays UNAVAILABLE until Task/Source-use/Gateway/egress/action
bridges are bound; it must not disable the manual path. General computer/OS control was withdrawn on 2026-10-11 and is not a delivery dependency; Agent Zero GUI is out of product scope.

The loopback guard remains until secure remote actor/session transport exists.
Remote Web use, session-result SavedWork/Artifact save/reopen/recovery and
actual browser runtime/user acceptance remain OPEN. Source/static
verification does not establish these outcomes or any full four-surface closure.
Revision-4/5 observations below are historical. Targeted unit/integration
regressions were restored on 2026-10-10; they do not replace real user acceptance.

## 0.1 Historical source binding — 2026-10-05

This section records the implemented revision-4 reader contract for current SYS-06 source. The approved revision-5 interaction target in §0.3 extends it; read-only and no-external-option statements here describe current implementation, not final restrictions. It
supersedes the capacity-only behavior in the revision-2 sections below wherever
they conflict; those sections remain historical provenance and explain why the
reader has its present boundaries.

- **Entry and return.** `SYS-06` is a real Web Workspace/Desktop/Mobile route,
  not an unavailable-route boundary. It opens as a focused return layer above
  the originating workspace task, so Browser Back returns to the preserved task
  and its local draft. Direct links still show a normal workspace shell.
- **Existing owner only.** `Sys06Screen` uses the existing SYSTEM Browser API:
  `POST /api/browser/sessions`, `GET session`, `GET frame`, `POST navigate`,
  `POST reload action`, and `POST stop`. It does not add a Browser owner,
  WebView, client browser runtime, profile, extension, or parallel Evidence
  store.
- **Actor boundary.** The product client deliberately sends neither Core Basic
  credentials nor business context headers to these routes. The server can issue
  only its fixed `workspace:local` principal on an explicitly open loopback
  workspace with no Authorization, Cookie or forged identity headers. Account
  sessions retain their existing Browser ownership path.
- **Readable result.** A user explicitly opens the controlled reader, enters a
  credential-free `http` or `https` public address, then sees only the current
  server-filtered title/address and a short-lived authorised PNG page preview.
  After navigation, the input is replaced with the server-filtered address.
- **Preview boundary.** The preview is labelled read-only. Local pan/zoom is
  allowed; it cannot click, type into, or scroll the remote page. The UI accepts
  a frame only when both opaque target identity and page revision match the
  current server session. It clears stale, denied, expired and failed frames.
- **No sensitive projection.** No account, Cookie, session ID, profile, port,
  WebSocket endpoint, filesystem path or raw query/fragment is rendered.
  Capacity collision names no other user and never steals or closes another
  session.
- **State truth.** A pending frame, empty frame, denied scope, occupied
  capacity, invalid address, unavailable runtime and an explicitly ended session
  are separate visible states. The revision-4 reader has no external-opening option;
  §0.3 requires an explicit safe option and forbids automatic external fallback.
  Failed frames never become source/Evidence/collection success.

### Current source evidence

- Browser API owner/session isolation and forged-identity rejection:
  `tests/test_ai_browser_default_engine.py` and `tests/test_browser_e2e.py`.
- Flutter normal path, stale-frame discard, invalid-address failure and explicit
  session stop: `app/test/features/system/sys06_reader_test.dart`.
- Deep link, focused-return draft preservation and 320px/200% text route path:
  `app/test/navigation/lumenis_router_test.dart`.
- Shell canonical-screen mapping and four-surface composition regression:
  `app/test/shell/lumenis_workspace_shell_test.dart`.

### Remaining acceptance

This source binding is not a live browser, acquisition, Evidence, collection,
semantic accessibility, native-device or Product Owner user-job acceptance.
`SYS06-ENTRY-02`, `SYS06-SCOPE-02`, `SYS06-FRAME-02`, `SYS06-ACTION-02`,
`SYS06-RETURN-02`, `SYS06-A11Y-02` and `SYS06-TRUTH-02` remain open until the
actual permitted runtime can supply their required evidence.

## 0.2 Approved platform-recovery role — 2026-10-07

SYS-06 is the controlled browser capability used by the shared platform-recovery flow when a platform requires an interactive login or human verification step that cannot be completed by a QR-only surface. It does not become a platform-account manager and does not own `PlatformSession`.

```text
LumenisPlatformRecoverySheet
→ PlatformSession says LOGIN_FORM_REQUIRED or VERIFY
→ invoke permitted SYS-06 controlled browser capability
→ user completes the legitimate platform step
→ return browser result/state to SYSTEM session owner
→ PlatformSession rechecks real auth/verification/risk health
→ RecoverySheet resumes the exact pending Collector task only after healthy readback
→ Return to the originating CTH/BMP/Shared/SYSTEM context
```

QR-capable recovery remains in the shared RecoverySheet and need not open SYS-06. BLOCKED/IP-risk/cooldown states do not open a browser merely to simulate progress. SYS-06 never exposes Cookie/token/profile/CDP details, never performs social writes, and never converts “browser opened” or “login form completed” into “session healthy” without the PlatformSession owner readback.

When multiple platforms require attention, SYS-06 serves only the one active recovery item selected by the single RecoverySheet queue; platform-specific browser windows or stacked modal recovery surfaces are forbidden.

## 0.3 Approved interactive browser target — revised 2026-10-11

The Product Owner supplied `ScreenRecording_10-08-2026 06-26-05_1.mp4` and directly
originally requested computer control; the 2026-10-11 correction withdraws that
OS scope and retains the in-product controlled browser on iOS,
Desktop and Web, with explicit optional external opening. M reviewed the 12.34s
visual flow. Experience §11/§38 remains the design authority. The existing
DESIGN_READY/source decision applies to the implemented reader; the following
interaction target is approved, with runtime/action bindings still OPEN. Sections
0.1 and 11 record the old read-only/source limits, not a prohibition on completing
this target. Do not enable UI actions until the existing owner advertises and
enforces their real contract; implement that owner gap instead of removing scope.

| Element | Complete required behavior | Owner/binding condition |
|---|---|---|
| Mobile task-to-browser | Open from current task to safe URL/title and real viewport; keep Return and draft/context; touch/keyboard/insets/landscape work | Existing router + SYS-06, same task/session/target |
| Browser control | Visible Agent action, current real frame, human takeover, stop; click/input/scroll/select/history when supported | Existing Browser actions; exclusive input owner, fresh frame/revision, Permission/Firewall/Fence |
| Live/history | Live only while fresh connected observation exists; event review shows actual earlier time; Return to live explicit | Existing Task/Trace/action observations; do not invent a second event store |
| Desktop/Web | View and operate controlled browser inside workspace, adapting panels to available room | Existing SYSTEM worker, secure actor/session API; no arbitrary iframe or browser-private device access |
| External option | User chooses safe external opening; no automatic popout; failed/unsupported internal path stays honestly unfinished | Existing SourceTarget URL/use/Return validation; migrate modes with existing callers |
| Product scope | General OS/desktop control is removed, not deferred or accepted | Preserve old source/research; do not build a GUI worker for product closure |
| Takeover/return | Grant exclusive control before input; Agent cannot race human; close view/stop task/end session remain separate | Same server-owned task/session/lease and action receipts |

Fresh session/target/frame/revision/viewport binding is required for coordinate
actions. Revoke/expiry clears protected content and prevents new effects. Local
pan/zoom is not remote page scrolling. An old frame is neither live nor input
authority. Real non-loopback Core use requires secure deployment/actor/session
binding; deleting `_requireLocalBrowserEndpoint` alone is not a repair. Unknown
capability stays unavailable while its owner implements the required path.

SourceTarget v1's current external launch action is a compatibility implementation,
not the new default presentation. Source opening never silently captures Evidence,
collects, copies sessions or performs writes. Preserve its existing return semantics.
Review adds no arbitrary desktop permission, paid worker or protected-account access.

Acceptance extends the existing SYS06-ENTRY/SCOPE/FRAME/ACTION/RETURN/A11Y/TRUTH
checks and Overlay J1/J7/J8: real in-product phone/Web/Desktop operation, explicit
external option, exclusive takeover, stale frame rejection, stop/revoke/reconnect,
unchanged task context and actual browser result. General OS operation is no
longer required under the direct 2026-10-11 scope correction.
All new implementation/runtime/user acceptance remains OPEN until actually proved.

## Historical capacity-only specification — revision 2 provenance

The following sections preserve the former safe capability-panel design and its
research basis. They are not a second current execution contract. Current source
behavior is defined by §0.1 and the exact source/API contracts it names.

## 1. User problem and product invariant

- Authorized context: SYSTEM operator allowed to read a filtered capability report.
- Real task: know whether controlled browser capacity is available and what read-only capability is bound.
- Completion signal: aggregate counts and safe instance states are shown; identity material remains hidden.
- Out of scope: personal browsing, credential/profile/session/port/path display, arbitrary CDP commands, social write actions and login automation.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-06` → `experience_screens._build_sys06()` → `browser_surface.capability_report()`.
- Current source may return identity/port fields; the Flutter projection reads only KPI values and state.
- Exit/return: originating SYSTEM route; no browser tab or snapshot action is bound.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Safety behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Controlled instances / online / read-only capability counts | KPI ids `sys06.instances`, `sys06.online`, `sys06.capabilities` | Ready integer only; unknown/offline is unavailable | BACKEND-GAP-041; `sys06_snapshot.dart` |
| P0 | Instance state | table row `state/状态` only | Account, port, profile, session and path fields are discarded | Browser Surface owner |
| P1 | Capability boundary | feature-local copy and current report state | No new-tab/snapshot/extract action is inferred | `browser_surface.py`; current builder |

The capability-report binding is not an authorized viewport binding. Published
Browser prerequisites through `6cf66ce8463a98effc99d05f806d6136f0c0a4ec` include
Actor/login ownership checks, same-login session reuse, an explicit single-session
capacity limit and execution on the browser's dedicated thread. Those changes do
not make the legacy report or SYS-06 operable. Published frame responses now carry
target/revision, safe metadata and the advertised navigation/reload/frame scope;
real product Actor entry, frontend binding and authenticated product-user E2E
remain open. The app's Basic transport credential is not a product Actor session.

Current routing also matters: `lumenis_workspace_routes.dart` excludes SYS-06 from
`workspaceScreenIds`. The host navigation correction reviewed under ACC-03's
`DESIGN_READY` contract presents a browser-unavailable boundary on every surface,
and preserves an originating task for Return. It does not instantiate the capacity
widget or a viewport. Opening a native desktop build does not remove that boundary.

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | capability report pending | Wait or leave |
| Empty | no controlled instance returned | Show no-instance state; never show identity placeholder |
| Partial | aggregate counts or instance state missing | Keep unavailable distinct; refresh |
| Offline/error | report unavailable or malformed | Retry bounded read; clear old snapshot |
| Blocked | 401/403 or session scope denied | Follow access flow; no browser action |
| Ready | safe counts/states returned | Read only |

## 5. Purpose-built desktop and web composition

- Desktop/Web: capability summary sits beside filtered instance states; a boundary explanation names allowed read scope and unbound operations.
- Tablet/mobile stack summary and instance states; state text remains beside each instance.
- No browser viewport, credential inspector, port list or action toolbar is rendered.
- Any future browser action needs explicit target authorization, Permission, audit and Effect Fence.

## 6. Purpose-built mobile composition

- Single active task: inspect controlled capacity.
- Summary first, instance states second, safety boundary always visible.
- Back/return does not open a personal browser; refresh re-reads capability only.

## 7. Actions, authorization and effects

| Action | Owner/effect | Current behavior |
| --- | --- | --- |
| Read capability | Browser Surface GET; actor/session scope currently unverified | Safe projection only; 401/403/offline distinct |
| Open/snapshot/extract | Future Browser owner + Permission/effect fence | No control; unavailable/unbound |
| Social or account write | Explicitly out of scope | Never rendered or invoked |

## 8. Accessibility, motion and localization

- Aggregate metrics have semantic labels; instance state uses text, icon and color.
- Hidden sensitive fields are not present in the widget tree; screen reader cannot discover them.
- No browser visual capture or chart is shown.
- zh-CN/en/ko boundary copy wraps; reduced motion suppresses decorative state transitions.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS06-LEAK-01 | Account, port, profile, session and path fields never render | Adversarial snapshot/widget tests |
| SYS06-STATE-01 | Empty/offline capability does not become online or zero | Snapshot/widget tests |
| SYS06-BOUNDARY-01 | No personal browsing or write action is exposed | Source/widget review |
| SYS06-REAL-USER-01 | Authorized operator reads a real capability report and can distinguish controlled read scope from unbound action | Authenticated runtime E2E required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; browser capacity is infrastructure, not global entity coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no business entity sample, count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: the bounded reading-surface exploration below adapts return, focus and state presentation through existing owners. Browser action binding remains gated. Future acquisition improvements must preserve Source/Evidence/Canonical lineage and rollback.
- Decision: `DESIGN_EXPLORATION`; Sol must verify the browser authorization boundary and prohibited identities remain untouched.

## 11. Controlled reading surface — bounded design refinement, 2026-09-27

This section defines the proposed next composition under Constitution §§11,
30–36. Sections 2–9 describe the existing, unaccepted capacity candidate; they do
not describe an implemented viewport. This reading-surface proposal authorizes no
viewport route, API, owner, Permission, identity or release change. The independent
host unavailable/Return correction is governed by ACC-03. Review decision remains
`DESIGN_EXPLORATION / IMPLEMENTATION BLOCKED ON BINDINGS`.

### 11.1 Real task and completion boundary

The user opens an allowed source while working on a CTH/BMP/Shared task, reads it
in a LUMENIS-owned surface and returns to the same task and focus. Reading does
not assert collection, a saved source, Canonical Evidence or a business conclusion.
Public source content remains untrusted. Existing Hong Kong/international
collection identities stay behind their registered owner; no personal profile,
Mainland account or arbitrary CDP connection is offered.

The first bound slice may use one authorized active page. Multiple tabs, personal
browser synchronization, extensions and a new local browser runtime are outside
this slice. Pin/Trace to Evidence appears only after the canonical Evidence owner
returns a real scoped receipt; legacy BrowserEvidenceStore IDs cannot satisfy it.

### 11.2 Desktop and Web Workspace

- Keep the originating task name and an explicit **Return to task** at the top.
  Page-history Back is a different action with a different accessible name.
- Use one compact source toolbar: permitted history controls, a labelled address
  field with explicit Go, permitted reload and page details. Enter submits only
  from that field. Typing never navigates or persists visited addresses globally.
- Give the source reading area the remaining width and height. Its opaque page
  surface preserves the source's legibility; the surrounding LUMENIS chrome uses
  the existing adaptive wallpaper, contrast and typography rules.
- Keep engine/session availability and observation time in a quiet status row.
  Details open on demand beside the source on wide windows. Narrow desktop
  windows use the same reversible details sheet as tablet, not a squeezed rail.
- Source title/address are server-filtered, escaped data. No account, Cookie,
  profile path, port, WebSocket endpoint or session token is displayed or logged.
- Web Workspace presents the remote controlled page inside its own workspace.
  It never promises to embed or control the user's installed personal browser.
  Native platform support requires its own verification over the same owner.
- A read-only frame has explicit **Page preview / Updated at …** semantics; it is
  not styled as an interactive DOM. Zooming the preview is local; clicking or
  scrolling it sends no remote command without a separately verified capability.

### 11.3 Mobile Companion

- One full-screen source reader: top Return to task, source title and details;
  reading area in the middle; compact allowed navigation below with safe insets.
  Do not copy the desktop inspector into a permanent narrow second column.
- Tapping the address opens a focused address editor. Cancel preserves the
  current page; submit waits for authorized navigation. The keyboard must not
  cover Go, Cancel or the explanation of a denied URL.
- Details use a sheet with a fixed title and Close. Hardware/browser back first
  closes the local editor/details layer, then returns to the originating task.
  It never silently becomes the remote page-history command.
- Actions have at least 48 logical pixels of touch area and visible focus.
  At 320 px and 200% text, controls may wrap and details may scroll; Return and
  Close remain visible. Landscape and keyboard-open states are separate checks.
- Return restores the originating route, Subject/Brand focus, selection, filter,
  draft and source position through existing navigation/state owners. A direct
  deep link with no saved origin returns to the existing workspace directory.

### 11.4 Binding requirements — fields below are requirements, not a new API

| Existing owner | Required safe contract | Failure behavior |
| --- | --- | --- |
| SYSTEM Browser + Permission | Verified Actor/login owns the opaque session; server validates every read/action again | 401/403 clears the displayed frame; no local permission substitute |
| SYSTEM Browser | Explicit engine label, session state, checked time and supported actions | Missing action capability stays unavailable; no inference from engine availability |
| SYSTEM Browser page | Opaque target identity and page revision, safe title/address, or a proven equivalent single-target contract | Page switch/navigation invalidates old metadata/frame before loading its replacement |
| SYSTEM Browser frame | Authorized bytes plus frame ID, capture time and positive dimensions, bound to session, target and page revision | No shared cache or persistent wallpaper/image cache; discard on logout, expiry, navigation or target change |
| Existing client/ViewModel | Request generation scoped to current session/target/revision; discard late success and failure after disposal or scope change | An earlier frame/error must never overwrite the newer page, including same-target navigation |
| SYSTEM Browser actions | Explicit navigate/history/reload/stop capability and server permission, URL policy and error contract | Unsupported controls absent or disabled with a concise reason; no successful toast on rejected effect |
| SYSTEM Browser input | Frame ID, target identity and viewport dimensions validated atomically for any coordinate action | No remote pointer, keyboard or scrolling until this contract and effect policy pass |
| Shared Evidence | Canonical scoped receipt and source/lineage returned through its existing owner | Reading, screenshot bytes and legacy IDs never enable Save as Evidence |

Opaque IDs stay in memory and are not product labels or authorization on their
own. Exact methods and response fields must be reconciled with the backend owner
before `DESIGN_READY`; this table creates neither an endpoint nor a parallel DTO
authority. Single-login session reuse is server-owned. Closing this UI returns to
the task; an explicit permitted End session action is required to stop the engine.

Backend-owner fields published at `6cf66ce8`, rechecked as source in this review:
`engine_label`, opaque `target_id`, integer `page_revision`, filtered
`current_title/current_url` and `allowed_actions = [navigate, reload, frame]`.
The authenticated frame response adds `X-LUMENIS-Target-Id` and
`X-LUMENIS-Page-Revision` alongside frame ID/time/dimensions. Navigation returns
the current target and new revision. The eventual client must compare both
target and revision, and invalidate pending reads as soon as navigation begins.
Back/Forward and coordinate input remain unadvertised. The backend probe used a
test Actor/Permission stub; recheck real Actor entry and responses before accepting
these names as an operable frontend binding. On 401/403, never substitute Basic
transport access or a locally generated Actor; show unavailable and keep Return.

### 11.5 State and recovery additions

| State | Visible result and permitted recovery |
| --- | --- |
| Starting / navigating / reading frame | Show the actual pending step; retain editable input but prevent duplicate effects; Return remains available |
| Pending frame (`202 BROWSER_FRAME_PENDING`, backend published at `3ccc8307`) | Keep the reading/loading state with bounded retry; do not decode the response as PNG or classify it as empty, failed or complete. A retained preview must match the same target/revision and remain labelled with its original observation time |
| Empty frame (`503 BROWSER_FRAME_EMPTY`) | End the pending state and offer Retry/Return; never decode the error response as PNG or keep retrying indefinitely |
| No page yet | Address entry only when navigation is supported; no fabricated start page or example screenshot |
| Capacity occupied (`409 BROWSER_CAPACITY_OCCUPIED`) | Explain another active use occupies capacity; Retry/Return, without identifying the other user or stealing/closing that session |
| Navigation rejected | Keep the attempted address locally editable and show the safe reason; no destination-success state |
| Frame unavailable / offline | Replace obsolete frame with a reading-unavailable state and explicit retry; do not call the session offline merely because one frame failed |
| Session expired / permission revoked | Clear frame and metadata immediately; explain that access needs to be restored; Return stays available |
| Fresh read-only frame | Display observation time and read-only status; no claim of live interaction or saved Evidence |
| Missing metadata / partial result | Name the unavailable field; never substitute zero, a title from the previous target or an inferred online badge |
| Closed | Clear view-owned bytes, pending requests and source metadata; Return restores the originating task |

### 11.6 Executable acceptance for promotion

| ID | Required assertion | Current evidence |
| --- | --- | --- |
| SYS06-ENTRY-02 | Actual shell/deep-link entry on each promised surface reaches the approved surface or a truthful capability boundary, never an unconditional misleading desktop redirect | NOT RUN; route change gated |
| SYS06-SCOPE-02 | Another login cannot read/control the session or obtain frame bytes; revoke/expire clears visible content | Backend contract + authenticated runtime E2E required |
| SYS06-FRAME-02 | Navigate A→B while A's read is pending; A's later frame/error cannot render in B; leaving prevents late updates | ViewModel regression + real runtime required |
| SYS06-ACTION-02 | Each enabled operation has a real capability/Permission binding; absent/denied operations issue no effect; 409 does not stop another session | API/widget + runtime required |
| SYS06-RETURN-02 | Open source from a real task, open/close details, return, and retain exact draft/context/selection; distinguish local Return from remote history | Web/desktop/phone E2E required separately |
| SYS06-A11Y-02 | Keyboard/touch can enter, read status, close layers and return at 320 px/200% text and in landscape; no focus hidden by fixed chrome | Widget + keyboard + assistive-technology runtime required |
| SYS06-TRUTH-02 | Preview is announced as a snapshot; screenshot-only content is not reported as fully accessible or Canonical Evidence | Accessibility review; semantic reading alternative remains a gap |
| SYS06-RECOVERY-03 | RecoverySheet invokes SYS-06 only for the current LOGIN_FORM/VERIFY item; QR and BLOCKED/COOLDOWN do not open a browser | Future widget + Browser/PlatformSession integration test |
| SYS06-RECOVERY-04 | Completing browser interaction does not mark the connector healthy; PlatformSession health readback must pass before the exact pending task resumes | Future backend/runtime E2E |
| SYS06-MULTI-03 | Multiple affected platforms share one RecoverySheet queue and SYS-06 serves one active recovery item without stacked browser/modal sessions | Future multi-platform recovery E2E |

Real user-work card: **ENTRY** originating task → **REAL INPUT** an allowed public
source URL → **PATH** permission → navigation → current authorized read → details →
Return → **RESULT** source inspected and exact work restored → **RECOVERY** denied,
expired, capacity occupied and failed frame. **EVIDENCE / ACCEPTANCE ASSERTION**:
not yet executed; current design is not a Round 14 PASS. Commercial readiness and
global entity coverage are unchanged. No synthetic entity population is added.

### 11.7 Bounded research and review

Accessed 2026-09-27: W3C WCAG 2.2 Understanding
[Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)
and [Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).
**ADAPT** visible focus around fixed toolbars/sheets and non-disruptive status
announcements into this Constitution-owned surface. These are informative W3C
guidance under its linked document-use terms; no code, assets, dependency or visual
layout is copied. No third-party browser UI is adopted. Screenshot-only content
does not supply the source page's accessible semantics; the Browser owner must
provide an authorized semantic reading path before that accessibility claim.

Sol review: composition and explicit limits recorded; **DESIGN_EXPLORATION** is
retained. Next owners: SYSTEM Browser resolves target/frame/capability contract;
Experience reconciles actual fields and reviews implementation entry; Permission
and Evidence retain their existing gates. Source and runtime verification, rather
than this document, determine promotion and delivery.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 在原任务授权范围内读取和操作受控来源，完成必要的验证并返回原任务。
- **屏幕专属呈现：** 按真实 capability 显示地址、当前来源、页面与允许操作；RecoverySheet 需要 LOGIN_FORM/VERIFY 时承接受控交互，再交还 PlatformSession 健康复核；不露账号/profile/port/path
- **来源、范围与版本连续性：** 保留 Task/来源/target/page revision，返回恢复草稿和选择；来源保存经既有 Evidence owner，浏览画面不自动成为 Evidence；不接触私人 profile
- **四端差异：** Web/Desktop 承接授权浏览与原 Task；Mobile 适配已批准的阅读/验证/返回流程，能力不具备时保留 OPEN 而非永久只读；官网不执行内部浏览
- **失败与恢复：** 不可用即明确提示，不用外部个人浏览器伪装；人机验证走现有受控流程
- **补充验收：** 不泄密、无未绑定动作；验证完成仍需 Session 健康回读；跨来源不得显示旧帧；成功/失败均返回原 Task 保留上下文。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

### 2026-10-09 acquired-original return increment — OPEN implementation/acceptance

Opening an actual permitted original post from its source/result preserves the
same task/Brief/scope/version and provides a controlled in-product browser plus
return to that work. External opening remains an explicit choice, not a fallback
that silently loses context. Source target/native identity, access state and task
state come from the existing SYSTEM Browser/Permission owners. Platform challenge,
session loss, access restriction and cooldown remain distinct recoverable states;
no protected personal account or unauthorized fallback is used. Returning resumes
only the still-permitted source/result action, not a fabricated capture/analysis
success. Verify this real running Web operation with the data-to-business chain;
this requirement increment alone is not browser implementation or acceptance.


### 2026-10-09 visible-link navigation increment

The current frame can expose up to 40 visible, policy-approved hyperlinks through
the existing human-control lease. A server-issued opaque link ID binds the
choice to the session, lease, target, revision and displayed frame. Core
re-resolves the anchor and validates the destination before using the existing
navigation action; no DOM click handler, form submission or arbitrary selector
is executed. Changed page identity, changed links or expired leases require an
honest refresh. Link selection checks frame/target/revision/viewport and the live
anchor identity; unrelated animation pixels alone do not invalidate this
non-coordinate action. Other controls retain their existing strict screenshot
checks. Main-document redirects are checked before sending the next request;
this does not claim complete subresource/WebSocket egress isolation.

SYS-06 presents a localized, keyboard-accessible page-link chooser with link text
and a redacted destination. Opening a link stays in the same product session;
the existing manual note save/revise/reopen and return controls remain. This
source increment does not close Task/Source bindings, arbitrary page control,
remote Web transport or intelligent Browser Use. General computer operation
was withdrawn by PO and is no longer an acceptance gap. Actual
operation and limits are recorded in the existing M delivery evidence.
