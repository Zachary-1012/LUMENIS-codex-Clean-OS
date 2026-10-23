# SYS-06 — Internal browser capability

## Current page-context outcome — 2026-10-23

User need → same authorized page/target/revision → relevant live context → grounded answer or editable result → existing save/revise/reopen/recovery. This is the priority outcome; a generic crawler or manual note alone cannot close it. User refresh or a named task triggers acquisition; page entry/navigation alone does not collect the registry.

The current bounded change connects `阅读网页 / Read page / 웹페이지 읽기` to the existing session extraction endpoint. It reads current loaded visible DOM, preserves source/time and partial coverage, rejects changed targets/revisions and human-control conflicts, and reuses Shared's lexical context window. The excerpt is explicitly source text, not an analyzed answer or a semantic-accuracy claim. Model generation, Source-use admission and question-to-saved-result binding remain OPEN until actually connected and operated. No parallel Browser/Collector/Truth owner, personal browser access or external inference is enabled.

The recorded reference uses a fixed question entry, concise activity messages and an editable inline deliverable with source/actions. Adopt these operations and original OEVIRA visual treatment; do not copy personal content, email or query tokens. Existing motion preferences and four-surface acceptance remain required.

The browser is a full working surface: compact real-page tabs and address/history controls, an uninterrupted page viewport and an optional opaque question/result pane. It must not inherit a dashboard card frame, selected-chip tab styling, an always-open inspector or overlapping translucent text. Narrow layouts switch between page and question without losing either state. Wide layouts reserve the majority of space for the actual page. The global route remains reachable through the compact workspace navigation rather than a second permanent sidebar. An actual result has its own readable body, sources and local actions; a DOM excerpt stays explicitly an excerpt until the analysis and saved-result contracts are connected. UI composition and backend completion are separate required checks; neither substitutes for the other.


## 2026-10-11 当前目标：业务任务中的真实内置浏览器

用户从原帖/引用/研究任务进入真实网页，能看到安全网址、当前页面和操作状态，进行获准导航与网页操作、独占接管、停止并返回原任务。默认在序境内呈现，外部浏览器由用户明确选择；无AI也可正常浏览。自动采集保持后台无头，不占用桌面焦点。

既有 SYSTEM worker 执行网页；Core 核验 actor/task/scope/session、每次动作和来源用途；SYS-06只呈现真实画面与可用操作。不得用iframe失败、静态截图、raw CDP前端直连或另开桌面应用替代。方法参考公开浏览器会话/动作与画面原理，具体安全传输必须真实实现，不能宣称已复制GPT私有架构。

通用操作系统、任意本机软件/键鼠与远程电脑控制已经撤出产品范围，相关历史要求已删除，不再要求GUI worker才能完成本屏。既有浏览器任务绑定、支持的网页动作、受控文件传输、权限、来源保存与重开恢复缺口仍需实际验收；文档更正不能将其记为通过。本规格不声明当前窗口派工状态。

```yaml
screen_id: SYS-06
status: IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED
revision: 8
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
- Current source decision: revision 8 replaces the card-based reader composition
  and binds current-page extraction. Full browser actions, grounded answers,
  accessibility and whole-screen real-user acceptance remain open. Revision 7's
  local-Web manual-note evidence below is historical and does not accept revision 8.

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

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-06)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：内置浏览器：标签/地址栏/前进后退/折叠/查看原文


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 外部打开永不自动触发、永不采集；无 Edge/9222；书签/历史/阅读模式可选。

会话失效先保存任务并在产品内请求人工操作；自动采集不打开桌面窗口。恢复须服务端身份、权限、健康及租约核验，不绕过挑战/冷却。

### 草图增补：产品内登录失效弹窗 LumenisPlatformRecoverySheet


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。

会话失效先保存任务并在产品内请求人工操作；自动采集不打开桌面窗口。恢复须服务端身份、权限、健康及租约核验，不绕过挑战/冷却。

### Existing contract — Purpose-built desktop and web composition

- Desktop/Web: capability summary sits beside filtered instance states; a boundary explanation names allowed read scope and unbound operations.
- Tablet/mobile stack summary and instance states; state text remains beside each instance.
- No browser viewport, credential inspector, port list or action toolbar is rendered.
- Any future browser action needs explicit target authorization, Permission, audit and Effect Fence.



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

### 正文/结构捕获与来源快照（B01–B05）

既有Browser Runtime的extract/capture_command/snapshot_for_source是同一受控页面能力；前端使用原已注册合同，不能从这些函数名臆造route。新增可见工作面在本屏原“收集资料”内：结构导航、可信正文、选择区、覆盖/截断/缺失、原任务与必要控制权；原网页可逆返回。Web/Windows/macOS主辅并读，窄Web逐层，iOS页面→预览→选段→保存读回，固定取消/返回；官网仅公开去敏例。

能力回读为preview/select/discard时仅开放这些真实动作；保存笔记、source_prepare/source_import/source_use_prepare沿各原Owner实际准入，不凭capabilities宣称已接通。capture为SESSION_EPHEMERAL，Source snapshot非原资源字节，original_resource_sha256缺失保未知。笔记、来源接收、SourceUse与Canonical核验分开；没有正式回执不能显示已入资料库。持久后回SH-02同来源/版本并可独立重开。

SESSION/target/page revision、捕获TTL、request身份和当前权限由服务器校验。人工控制必须结束后才可捕获，不自动释放；导航/重启/到期/撤权使预览失效并拒旧选段，跨页迟到结果不得显示。discard只放弃预览，UNKNOWN写入先查同request证据回执，COMMITTED不重复提交。HTML/标题/错误安全文本渲染，不暴露会话token/端点/路径；缺页正文不以模型补写。

自身智能UI可按真实结构选目录/正文/选段并读，保原选区、滚动锚和简洁路径；状态/权限/准入用原生控件，不能被生成图替换。验正文/结构部分覆盖、重复文本选段、Unicode、人工接管排除、过期/同target新revision、请求超时三持久化结果、取消迟到、source读回、跨actor与SourceUse拒绝；四表面适用流程及zh/en/ko/读屏分别验，不提升旧frontmatter。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：内置浏览器：标签/地址栏/前进后退/折叠/查看原文


### 草图增补：产品内登录失效弹窗 LumenisPlatformRecoverySheet


## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-06)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：内置浏览器：标签/地址栏/前进后退/折叠/查看原文


### 草图增补：产品内登录失效弹窗 LumenisPlatformRecoverySheet


### Existing contract — Purpose-built mobile composition

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


### 原要求具体工作合同：免费来源数据类别与聚光未配置边界

原来源任务范围内，按平台注册的广告/流量、创作者中心、公开内容等实际对象显示当前合法取得路径与可得字段。每行分别列免费/费用未知/需额外许可、公开路径/获准自有会话/已授API、身份条件与实际最近结果；“平台注册”不等“免费可采全部”。缺某类数据保其他可用材料，不能以公开视频替广告账户观测或把零条当成功。
聚光为来源/活动当前任务的一项：未配置专业号、授权未知/失效、字段未取得分别写具体原因；未配置保持UNAVAILABLE，用户可跳过继续当前规划，不强制开通或付费。KFS的F“24h互动>20再投”只列方法假设及适用性，旁边明确“未执行投放”，不能据此出现自动充值/投放成功。

SYS-02平台lane详情“本任务数据”表列数据类别→字段→取得路径→费用/许可条件→实际状态，选行打开具体限制和原来源；BMP-07在所选活动的数据依据中显示聚光可用性及方法说明，不另建广告管理器。Web/Windows/macOS表与详情并读，iOS一类别一详情并保原lane/活动，官网只公开验证过路径。UI可据实际缺项聚焦解释，不生成授权、专业号或预算执行；简洁同源列表可锁。

选择来源/类别不自动登录、请求付费API或外发；恢复依原Source/Session/Permission明确动作。验每平台注册字段缺失、免费但未获权、授权但无数据、聚光专业号未配置、授权撤回、零条与未知、取消和重开；完整平台注册范围逐项运行仍OPEN，不能以一来源示例验全部。

### 原G188具体终态合同：书签、历史、搜索与策略说明

原浏览器地址栏旁“书签/历史/搜索”打开同一SYS-06侧面；书签列表可按原Owner支持动作查看/保存/移除，历史按真实访问时间列当前权限可读项及上限1000的实际截断说明，列表搜索不冒完整无限历史。多引擎搜索显示当前实际可用引擎与查询去向，选择后由原安全导航执行，不泄漏原任务私有正文。当前strict/allowlist/open模式用可读限制说明与被阻断原因呈现，open不表示关闭SSRF/安全门；未经原授权不提供切换安全策略控件。Reader元数据/正文与A11y结构仍沿已补捕获/阅读工作面，不把截图等于DOM。

构图：标签条/地址与导航固定，正文为主；侧面分书签、历史、搜索三个任务页签，选中项保安全地址/时间和回原任务；iOS页→单侧面列表→返回，长列表虚拟化不丢选中。

历史缺失/超上限、书签失效、引擎不可用、URL被拒、权限撤销/页面过期分别显示；取消搜索保原页，返回不重新采集，重开核当前任务/target和安全权限。保存/删除书签须真实回执，未绑定保持OPEN。

Public Website仅用获准真实样例说明书签、历史、搜索与策略说明及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按真实历史密度提出列表分组/Reader层级，保稳定地址栏、锁定和无AI基础导航；不生成页面/历史/搜索成功状态。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 同账号浏览器任务连续与有界并行（原Owner接续）

用户本轮提出的浏览器目标是：同一已授权账号保持登录连续，多项获准工作可各用自己的tab推进，少反复登录和手动切换。Muse并行能力仅记为用户观察，未经本轮独立实测；不能把观察当序境已经具备的功能或把外部产品行为当供应商API。原G82/G83/G115/G123/G133/G188继续由原Browser/Collector/Task/Permission Owner承接，不建第二浏览器或任务队列。

具体工作面：SYS-06顶部保当前产品浏览器会话与账号状态（不显cookie/凭据），下方按原Task列工作标签和所属tab；AI-02每个任务卡显示“观察中/待批准动作/执行中/核验结果/结果不明/等待限流/需要人控/取消待安全边界”等实际状态，点击直接回该任务tab与最近已确认结果。SYS-02只呈同账号/平台共享限额和真实采集进度，不把多个任务数当可并发额度。Web/桌面可按需并读任务tab，默认主工作面舒展；iOS以单任务浏览与可逆任务切换Sheet保返回位置，不要求复制桌面分屏；官网仅有权公开的受控演示说明同账号多任务，未接通功能明确标目标。切任务保原稿、任务身份及观察位置，不自动取消、重发或共享不同任务的业务scope。

登录context由原服务端账号/BrowserSession Owner管理，任务只租赁自己的tab。复用已获授权的登录不等新授权：每次动作仍核当前actor、task/run、tab、目标与原Permission/effect fence；跨actor/账号、别的任务tab或过期run禁止操作。单页同一时刻单写者，人控lease优先，弹窗也必须确定所属任务；结束/取消A只释放A的tab，不能关闭兄弟任务或整个共享context。共享context的生命周期和Playwright调用仍由原单线程Owner/正式调度维护，不把对象跨独立worker直接共用。当前这些共享context/tab dispatcher接线尚未完成，界面不得先显示“同登录并行已启用”。

每个动作之前观察当前document/frame/revision，定位用当前DOM/截图；文档变化使旧引用失效，页面文本不能扩大权限或变成系统指令。动作后必须观察并核明确预期结果，元素/计数/加载状态缺失保持未知，真实0和空输入依实际观察区分；不能把“请求发出”“返回200”或动画结束当目标达成。定位失败先再观察和重新定位，不扩大到任意脚本或用户其他App。外部副作用是否发生不明时保UNKNOWN及最后已确认结果，先读回核对，不盲重试click/input/提交；只有明确幂等读操作才按原Owner允许次数有限重试。迟到成功回执仍归原task/run，不覆盖新工作。

同账号/平台的所有适用任务遵守原Collector限额，使用同一账号/平台限流Owner；429/Retry-After、冷却、配额未知分别显示，等待可取消且不会绕限额换账号/会话。每任务详情/评论游标独立，来源按原Evidence/Canonical键去重并保scope，不跨域复制。当前rate修复只证明同实例放行间隔，不证明跨进程或所有任务已共用实例。暂停/取消呈请求→安全边界→真实终态，已派发外部效果不可回滚；恢复先新观察/新frame，新run重新取得sealed admission，不复用旧DOM或批准。登录/CAPTCHA/敏感步骤沿原人工接管入口，人控结束后重新核状态，不偷偷代填凭据。

当前实现事实：ActionVerifier状态核验、未知副作用恢复、同实例限流与内部Task admission→Browser绑定桥已有独立候选及隔离测试；原tab策略已有边界检查。这不是Task工具dispatcher已接通，更不是同登录多tab端到端完成。当前start仍每runtime新context，原manager同owner异task限制仍存在；不能为迎合并行直接删隔离锁。尚待同版证明的最小纵向链是：真实队列任务→获准Registry/Skill版本及明确browser effect→原工具dispatcher→一个产品tab→真实Observation/Evidence/Task checkpoint→实际结束，再扩同登录两任务tab。HTTP自报task/run不可替代内部封装准入，内部桥本身不算全链。

验收先用合成测试站和真实Chromium证明一次登录两任务连续、tab隔离/弹窗归属、一个取消不影响另一个、同账号429等待、动作超时已生效/未生效分别恢复、进程/lease回收及撤权；不得用真实用户凭据做单测。真实外站、多账号和各平台覆盖尚未验证；云端浏览器socket受限时如实记环境阻塞，不绕过，不把纯mock当真浏览器通过。四表面实际前端构建与有权本地产品浏览器验收继续分账。主任务预算、界面自身AIGC原创表达和200以上交互要求保留，便利不省略必要批准/成功核验。

官方参考（2026-10-18已核文本）：[OpenAI Computer use](https://developers.openai.com/api/docs/guides/tools-computer-use)、[browser drivers](https://developers.openai.com/api/docs/guides/tools-computer-use-sdk-drivers)支持动作后观察、过期引用与不明效果恢复的工程参考；[Grok Bot computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)描述共享登录、分屏单任务与人控。这些是机制参考，不构成新模型调用/供应商接入，也未证明序境或Muse端到端能力。


### 2026-10-21 交互源码吸收：开发前行为边界

材料：[独立审核包](../../../research/engineering/documentation-evidence/reports/product_research_deadline_20261018/interaction_equivalent_20261017/README.md)，静态对读 `src/recovery.mjs、recovery-study.mjs`。这里只吸收适用行为与反例，不执行、移植或发布审核包，不改变本屏既有实现/验收状态。

现有 `app/lib/features/system/sys06/sys06_view_model.dart` / `sys06_browser_repository.dart` 与受控浏览器恢复Sheet消费真实Owner状态。恢复队列按source/task及attempt关联；切换恢复种类即废弃旧轮观察。dismiss只关Sheet，defer释放当前队列占用，均不标任务恢复。登录入口不能解除BLOCKED/IP_RISK/COOLDOWN；只有当前轮真实会话健康读回才允许原任务继续，不重放其他任务。

验收：来源A核验迟到不能恢复B；等待中种类改为冷却后旧verified无效；关闭、暂缓、撤权、路由离开保原任务暂停及可追溯原因。demo的health注入不是会话验证器，不引入OS执行器或验证码绕过。
