# ACC-03 — Product home

```yaml
screen_id: ACC-03
status: DESIGN_READY
revision: 7
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
- ACC-03 owns composition/navigation only. It embeds the existing AI-01
  conversation owner directly in the workspace, using the shared Core client.
  AI-01 retains the separate analysis/draft/file tools; no second chat store.
  Opening Home reads history but never creates a conversation or calls a model.
  Explicit Send creates a conversation if needed, persists the original message,
  then uses the existing Gateway response contract. Unknown writes are reconciled
  before retry; navigation does not replay them.
- CTH remains commercial Subject-first and BMP brand/market-first in their
  business domains. That does not force a focus at the product entry.
- Shell owns navigation, current scope, leave decisions and remembered route.
  W6 owns server redirect and the four desktop entry targets.
- Home never implies Commerce is selected. Return to Home does not clear a
  valid focus, start collection, submit a task or write business data.

## 3. Source and binding table

| Field/action | Existing owner/binding | Truth rule |
| --- | --- | --- |
| Conversation input | Ai01ConversationPanel(embedded: true), Ai01ConversationViewModel / CoreAi01ConversationRepository; existing `/v4/ai/conversations` APIs | Shell supplies the same scoped draft; explicit send only; server-authored conversation/turn identity, readback, recovery and Permission remain unchanged |
| Analysis and draft/file tools | Existing AI-01 entry and owner | Direct reachable action; no model/algorithm selection required to enter basic business workflows |
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
The main conversation occupies one comfortable reading width up to 940 logical
pixels. With no selected conversation, a concise work prompt, input and direct
business/research/creation actions form the opening workspace. With a conversation,
show actual messages and their states with the input at the bottom. History is a
reversible view, not a separate modal required before writing. No marketing hero,
KPI cards, repeated product title or developer-status inspection CTA.
Wide layouts provide the existing work routes in a persistent left rail. Narrow
layouts keep the existing reversible navigation. Context inspectors are optional,
closed initially; readable content retains its space and current user appearance.

Four compact destinations use a small original glyph and a concise label, with
shared edges and visible focus/pressed state. They are navigation controls,
not four descriptive cards. Show the actual last-opened page only when present.
No permanent right-hand business inspector or duplicate AI panel.

## 5. Web and mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#acc-03)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

The same owner contracts apply in Web Workspace, Desktop and Mobile Companion.
On phone, prioritize the editor and wrap the compact destination controls while
preserving >=48 px targets. Avoid decorative vertical space and nested scroll.
The conversation uses the available height with a reachable input. The empty
work prompt and actions scroll only when keyboard, low height or 200% text requires
it; an open conversation scrolls messages independently of its input.

The Public Website is a separate approved surface and does not become an editor.
Native mobile file saving remains limited by the actual existing file owner;
offer real Open/Copy behavior instead of a fake Save success.

## 6. State, failure and recovery

| State | Behavior | Recovery |
| --- | --- | --- |
| No focus | GLOBAL_ALL; editor and existing navigation remain available | Optional exact focus through existing Shell only |
| Conversation history pending/error | Preserve typed draft and independent business/navigation actions; show the actual read failure | Retry the existing history read; do not invent empty history or model output |
| Analysis not integrated | State analysis service is not yet connected | Existing AI/Core owners connect real submit/result path; do not suggest choosing a Subject |
| Actual permission refusal | Keep distinct from offline/no data/missing adapter | Respect server decision; no new account wall |
| No last page | Omit the row | Never display a fake empty recent-work card |
| Invalid remembered route | Suppress it | Existing route/return owner |
| Missing host callback | Affected navigation unavailable | No fake navigation success |

File chooser cancel, invalid input, concurrent edits, save failure and expanded
editor return preserve the existing AI-01 safeguards at its direct entry. Explicit
conversation Send retains existing persistence/response semantics; opening Home
and switching work never submit text or start inference. Navigation to a business page and back, or between Home
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
| ACC03-TASK-01 | Home uses the existing AI-01 conversation owner; explicit send, persistence, history readback and uncertain-write recovery work; analysis/draft/file tools remain reachable through AI-01 |
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


### 舒展工作空间与跨能力直接继续

五个架构分工是产品内部能力、数据和Owner边界，不是用户完成一件事必须依次打开的五层页面。首页以“我想做什么/继续哪件工作”为入口：选择研究、写作、制作、经营或品牌问题后直接进入该任务的具体工作面，并带当前合法材料、已保存版本和可用上下文；不要求先选架构、再选模块、再重新录同一问题。必要主体/市场/执行范围在使用该动作时就地说明和选择；当前范围明确且仍获授权则复用，歧义或跨域采用须明确核对，不能靠少点一步绕过Permission或复制跨域数据。

工作面默认舒展：一个清楚的主要编辑/阅读区域、少量必要即时操作、可按需展开的上下文/依据。留白用于区分任务层级与当前焦点，不用巨大装饰把正文挤到屏外；有创意的非对称构成、尺度对比和阶段揭示围绕真实对象展开，不把每个字段塞进紧密小卡。现各专属合同的左/中/右描述是信息关系和宽度足够时的可选并读，不代表默认三栏全部常开；桌面也先保主工作舒展，用户决定何时并读。密集表格/多窗仅在当前任务确需且用户选择时展开，可回舒适阅读；不删除字段、功能或完整比较能力来换留白。200%字体、三语长文本、窄窗和键盘出现时仍可到达主操作。

跨能力继续工作优先就地展开或直接带上下文跳转并保返回锚点：来源旁记要点、结论回原文、错误直达需修输入、当前稿查看影响、通知回待决定处。返回不经过首页重新找对象，不重复要求已合法保存的输入；多个真实任务可各自保稿和版本，系统不会因切面自动停止任务或重新发送外部动作。现有路由/Owner缺接线时明确缺项并保原工作，不能用假浮窗模拟后端已完成。便利操作适用于所有能够复用同一真实合同的能力，不限随手记；当前有用的小巧思纳入既有Owner/本地前端实施范围，而不是减少原能力或再造一套快捷操作服务。

官网以工作故事、真实成果与可控演示舒展叙事，不把架构图当必经导航；Web和Windows/macOS保直接任务入口、原位置返回和用户选择的并读；iOS以一个主工作面、可逆Sheet与清楚回链呈现，不层层堆弹窗。底部便笺、加载小动作和AI表达不能遮挡原稿、重要错误或确认。界面自身AIGC可以提出符合当前任务的原创空间/视觉构图和交互呈现，采用前可预览，用户锁定/撤销有效；不复制参考品牌皮肤、人物或叙事，不把规则重排或静态插画冒实时生成。

验收用完整任务路径对照：从首页合法输入到首次有用编辑/阅读、跨来源核对后回原选区、转用成果而不重复录入、切任务再继续、失败后原位恢复。分别记录导航层数、返回/复制/重复输入次数、首个有用结果耗时、错误和工作丢失；未知未测不填漂亮数字。减步骤不能跳掉必要确认/证据，视觉舒展不能牺牲信息可找性；现仍是设计与接口合同，实际四端布局和可用性由本地同版构建验证。

本轮新增品牌视觉参考范围限定为Miu Miu、Prada、YEARPLAN、Le Labo、观夏及韩国品牌；韩国品牌先从已给参考核实，不自行扩大名单。已有视频/品牌产品研究继续复用，新的官方来源核验只补这个范围。关注布局、留白、字体、材质叙事和交互节奏如何服务真实工作，最终转化为序境原创表达；未核官方页面/实际画面时只列待核，不能宣称研究完成或复制外观。此限定不阻塞已明确的舒展布局、直接继续和可逆交互合同；后续证据附回本章而非另建产品规划。

### 便利操作合同：CV03 继续最新稿与精确工作位置

适用工作与省步目标：已保存创作/研究成果/笔记、可恢复Task；不将历史只读报告当可继续执行任务。

原Owner与真实接口边界：现GET /api/experience/saved-work、/<artifact_id>和source-brief/tasks列表/读取可重开；现GET /saved-work?latest_only=true已交有界测试，默认false兼容旧检索；游标绑定模式/actor/scope/筛选，条目resume含artifact_id/work_id/expected_sha256/expected_draft_digest/version，execution=not_started。失效当前版verification_complete=false，不回退可读旧版冒最新；重开后写仍复核CAS。光标、选区、面板、滚动及离线草稿是本地工作位置合同，现delivery_preferences字段不支持的状态不能硬塞服务端或伪称跨端同步。

控件位置与四表面操作：首页“继续工作”直接显示当前范围最新对象和真实状态，行内“继续编辑/查看历史”分开；Web/桌面回原页和字段，iOS恢复同一对象阅读锚点及可逆编辑Sheet，官网展示匿名可控样例不读取历史。免去先找架构、翻全历史和重新定位。

持久化、权限与错误恢复：最新权限读回后才加载；已撤权只保不泄内容的原因/返回入口。旧本地稿遇新服务端版本先并读保两份；任务进行中回状态而不自动resume；无本地持久记录时不承诺退出后光标恢复。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。


### 2026-10-21 交互源码吸收：开发前行为边界

材料：[独立审核包](../../../research/engineering/documentation-evidence/reports/product_research_deadline_20261018/interaction_equivalent_20261017/README.md)，静态对读 `src/navigation.mjs、navigation-study.mjs、command-palette.mjs、command-study.mjs、object-menu.mjs、menu-study.mjs、route-access.mjs`。这里只吸收适用行为与反例，不执行、移植或发布审核包，不改变本屏既有实现/验收状态。

首页导航/命令入口沿 `app/lib/shell/lumenis_workspace_shell.dart` 现有路由，不创建演示路由。切换时分别保当前草稿、选区、滚动和对象身份；未保存稿的“保留后切换”若仅内存会话，必须这样标注，不能叫已保存或跨端恢复。命令搜索保留查询和焦点；已有模态层时快捷键不抢占另一模态。对象菜单捕获对象/版本/当前可执行动作，切换对象、来源撤权或关闭后旧菜单回调不得执行。隐藏/权限未核入口不得成为可用命令。

验收：编辑中切换后返回、Esc关闭最内层再回触发控件、菜单打开后对象变化、键盘与触控等价；导航样例不是全编辑器持续状态已实现证明。
