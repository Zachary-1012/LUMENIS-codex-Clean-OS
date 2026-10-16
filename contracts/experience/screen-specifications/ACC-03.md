# ACC-03 — Product home

```yaml
screen_id: ACC-03
status: DESIGN_READY
revision: 6
owner_domain: SYSTEM / Shared Capability presentation
binding_ids: []
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: M, after explicit Product Owner correction
reviewed_at: 2026-10-03
approval_reference: Current F/M thread decision for task-first Home, GLOBAL_ALL default and reuse of the AI-01 editor
```

## 1. User task and product invariant

Open the product and begin real work: write or open a task draft, continue an
actually visited page, or open an existing business/creation workflow. This is
an operating product entry, not a marketing landing page or a system checklist.

No selection means GLOBAL_ALL. Subject/BrandFocus selection only narrows the
view. There is no account, login, password or mandatory focus design here.
Canonical server Permission and Effect Fence still protect actual reads and
effects. A single-target consequential action may request its real target at
that action; it cannot gate the whole product or global research/creation.

This revision supersedes the rejected large slogan, introduction columns,
destination descriptions and View entry details sheet. They are removed from
the current design rather than retained as alternative layouts.

## 2. Owner, route, entry and return

- Default / and /workspace resolve to /workspace/ACC-03 through the existing
  route owner. Exact CTH, BMP, Shared and other deep links keep their meaning.
- ACC-03 owns composition/navigation only. It embeds the existing AI-01 editor
  using the shared Core client; AI-01 owns draft/file/analysis behavior.
- CTH remains commercial Subject-first and BMP brand/market-first in their
  business domains. That does not force a focus at the product entry.
- Shell owns navigation, current scope, leave decisions and remembered route.
  W6 owns server redirect and the four desktop entry targets.
- Home never implies Commerce is selected. Return to Home does not clear a
  valid focus, start collection, submit a task or write business data.

## 3. Source and binding table

| Field/action | Existing owner/binding | Truth rule |
| --- | --- | --- |
| Task editor | Ai01Screen(client, embedded: true), Ai01ViewModel and Ai01DraftActions; Shell supplies the existing editor controller | One session draft shared by Home and AI-01 in the same scope; no separate Home AI service/store |
| Analysis availability | Existing AI-01 service/submit contract | Present actual unavailable/failure reason; missing focus is not a reason |
| Four destinations | Existing shell onOpen routes | CTH-01, BMP-01, SH-02 and SH-01; navigation only |
| Continue last page | Actual Shell in-memory/restorable valid prior route | No invented job, artifact, timestamp or claim of project recovery; clear on confirmed context/client change |
| Theme/wallpaper/locale | Existing shared owners | Preserve contrast, zh-CN/en/ko, text scaling and reduced motion |
| GLOBAL_ALL/FOCUS | Existing Core context and request headers | Default global; selected focus only narrows; no synthetic grant |

No recent projects, counts, feed, artwork or success state is fabricated to fill
space. Real collected records will use their existing reviewed ViewModels.
The historical ACC03 repository/model remains separately testable; its optional
entry-state fetch is not a prerequisite for the editor or host navigation.

## 4. Desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#acc-03)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

Use the existing wallpaper-aware Shell with its restrained brand and controls.
The content area has one reading/editing width around 820 logical pixels. A
small functional New task heading is optional at about 18–20 px. The reusable
task field and its real local file actions form the main content. No large
hero, slogan, repeated product name, introduction text or status-inspection CTA.

Four compact destinations use a small original glyph and a concise label, with
shared edges and visible focus/pressed state. They are navigation controls,
not four descriptive cards. Show the actual last-opened page only when present.
No permanent right-hand business inspector or duplicate AI panel.

## 5. Web and mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#acc-03)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

The same owner contracts apply in Web Workspace, Desktop and Mobile Companion.
On phone, prioritize the editor and wrap the compact destination controls while
preserving >=48 px targets. Avoid decorative vertical space and nested scroll.
The embedded AI-01 body takes natural height; Home supplies a single bounded
page scroll when keyboard, low height or 200% text makes it necessary.

The Public Website is a separate approved surface and does not become an editor.
Native mobile file saving remains limited by the actual existing file owner;
offer real Open/Copy behavior instead of a fake Save success.

## 6. State, failure and recovery

| State | Behavior | Recovery |
| --- | --- | --- |
| No focus | GLOBAL_ALL; editor and existing navigation remain available | Optional exact focus through existing Shell only |
| AI screen read pending/error | Preserve local draft and file controls; actual AI status beside it | Explicit safe retry; clear stale remote data |
| Analysis not integrated | State analysis service is not yet connected | Existing AI/Core owners connect real submit/result path; do not suggest choosing a Subject |
| Actual permission refusal | Keep distinct from offline/no data/missing adapter | Respect server decision; no new account wall |
| No last page | Omit the row | Never display a fake empty recent-work card |
| Invalid remembered route | Suppress it | Existing route/return owner |
| Missing host callback | Affected navigation unavailable | No fake navigation success |

File chooser cancel, invalid input, concurrent edits, save failure and expanded
editor return preserve the existing AI-01 safeguards. No automatic persistence
or inference is added. Navigation to a business page and back, or between Home
and AI-01, preserves task text and selection within the same window and scope.
A confirmed scope/client change starts a separate draft; a temporary scope-read
failure does not erase it. Closing/refreshing still requires saving or copying.
Use a compact actual scope label with optional-focus help on demand, while the
real unavailable-action reason remains findable. Local drafting is not a saved
business result. M accepted this recovery correction on 2026-10-03; runtime
verification remains separate.

## 7. Accessibility, localization and motion

Chinese, English and Korean labels share the same functional meaning. Use body
text around 14–16 px, 16 px editable text and 16–20 px glyphs within accessible
targets. Support keyboard traversal/Enter/Space, labelled icon actions, visible
focus, error announcement and explicit close/back/focus return in reused dialogs.
200% text may create scrolling but must not clip controls. Existing white,
black, solid and wallpaper modes retain their own contrast behavior; test the
two user-supplied vivid wallpapers. No new shader, copied asset or motion owner.

## 8. Acceptance

| ID | Required result |
| --- | --- |
| ACC03-ENTRY-01 | Default route opens neutral Home; explicit deep links remain exact |
| ACC03-GLOBAL-01 | No Subject/BrandFocus keeps GLOBAL_ALL, local editor and navigation available; no subject-selection lock |
| ACC03-TASK-01 | Home uses the real AI-01 draft/file owner; editable text, expansion/return and actual failure recovery work |
| ACC03-DRAFT-01 | Home -> business page -> Home and Home -> AI-01 retain text/selection in the same window/scope; confirmed scope/client change isolates the new draft; no claim of refresh/close persistence |
| ACC03-NAV-01 | All four destinations call their exact host route without business writes |
| ACC03-RETURN-01 | Valid last page returns correctly; invalid/absent and changed context/client do not fabricate history |
| ACC03-UX-01 | No rejected slogan, introduction cards or entry-status sheet; functional hierarchy at desktop/phone |
| ACC03-A11Y-01 | zh/en/ko, 390x844, 360x560, large desktop, 200% text and reduced motion preserve usable controls |
| ACC03-LIVE-01 | Exact W6-mounted Web/Windows bundle: Home -> task/file or real business page -> Return; four launch entries verified separately |

Keep existing safe-model/repository tests for malformed identity/context and
unknown health semantics; they are not Home layout requirements. Run affected
Flutter tests and the three Experience gates plus constitution gate at the
final source. Static/widget/build evidence does not prove real user completion.

## 9. Real delivery and limits

REAL USER JOB: start work from one product entry. ENTRY: actual launcher or
workspace root. REAL INPUT: a user task text or available business record, not a
fixture. END-TO-END PATH: Home -> existing owner operation -> real result/return.
USER-VISIBLE RESULT: usable draft/file or actual target screen. FAILURE/RECOVERY:
preserved text and honest independent service/read states. EVIDENCE: pinned source,
tests and operated runtime. ACCEPTANCE ASSERTION: LIVE_NOT_VERIFIED until that
exact artifact is mounted and used. COMMERCIAL OVERLAY IMPACT: no release claim.
GLOBAL UNIVERSE / DATA MATURITY IMPACT: routing measures no market coverage;
Global Commercial, Global Brand and Guangzhou reference coverage stay separate.

## 10. Research and review

ADAPT the supplied task-entry recording's editing priority, controlled density
and reversible layers under the sole Experience Constitution. Its frame evidence
is work/frontend-2026-10-03/ai-entry-video-frames.json; the review does not cover
every historical video. Original vectors are existing shared primitives.
No new third-party dependency or second design system. M accepted the Product
Owner's task-first correction; exact candidate/live acceptance remains separate.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 从首页开始真实工作或继续原任务。
- **屏幕专属呈现：** 以任务、草稿、已访问页面和既有工作流组织，不做KPI营销模板
- **来源、范围与版本连续性：** 恢复Task/Brief/scope/Artifact版本，建议只开草稿不触发效果
- **四端差异：** Web多区并读；Desktop快捷续接；Mobile突出一个待续任务；官网只作公开介绍
- **失败与恢复：** 空、失效链接、离线、权限过期独立呈现，保留原任务状态
- **补充验收：** 新建/续接/空记录三路径；不会强迫选择焦点或误报恢复。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
