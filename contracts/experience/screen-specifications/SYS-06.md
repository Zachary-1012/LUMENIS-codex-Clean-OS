# SYS-06 — Internal browser capability

```yaml
screen_id: SYS-06
status: DESIGN_EXPLORATION
revision: 2
owner_domain: SYSTEM Browser / CDP
binding_ids:
  - BACKEND-GAP-041
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: controlled internal browser blueprint, separate personal browsing boundary, provenance and §36.
- Product contract: SYSTEM browser capability supports controlled acquisition; it is not a user personal browser and does not authorize collection effects.
- References: `KEEP_AS_EXPLORATION`; no external browser UI is copied.
- Anti-template check: capability boundary + safe instance state composition, not a browser tab clone or generic dashboard.
- Sol design decision: `DESIGN_EXPLORATION`.

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
Browser prerequisites at `6a23ddc4a17d4680658c0c7f209267f47a6029ec` include
Actor/login ownership checks, same-login session reuse, an explicit single-session
capacity limit and execution on the browser's dedicated thread. Those changes do
not make the legacy report or SYS-06 operable. Target/frame ownership, safe public
metadata, action capabilities and authenticated product-user E2E remain required
for the new surface. A local frame endpoint candidate is not an accepted contract.

Current routing also matters: `lumenis_workspace_routes.dart` excludes SYS-06 from
`workspaceScreenIds`; `lumenis_router.dart` returns the desktop-required boundary
without testing the running platform. The capacity widget exists as source but is
not an accepted PC, Web or mobile destination. Opening a native desktop build does
not by itself remove that route boundary.

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
not describe an implemented viewport. This revision changes no route, API, owner,
Permission, identity or release state. Review decision remains
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

Backend-owner candidate reported during this review (not yet published/accepted):
`engine_label`, opaque `target_id`, integer `page_revision`, filtered
`current_title/current_url` and `allowed_actions = [navigate, reload, frame]`.
The authenticated frame response adds `X-LUMENIS-Target-Id` and
`X-LUMENIS-Page-Revision` alongside frame ID/time/dimensions. Navigation returns
the current target and new revision. The eventual client must compare both
target and revision, and invalidate pending reads as soon as navigation begins.
Back/Forward and coordinate input remain unadvertised. Recheck the published
source and real response before accepting these names as a binding.

### 11.5 State and recovery additions

| State | Visible result and permitted recovery |
| --- | --- |
| Starting / navigating / reading frame | Show the actual pending step; retain editable input but prevent duplicate effects; Return remains available |
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
