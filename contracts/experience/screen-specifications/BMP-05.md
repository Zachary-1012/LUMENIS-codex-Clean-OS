# BMP-05 — 创作者生态

```yaml
screen_id: BMP-05
status: BLOCKED
revision: 1
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-022
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-05 acceptance
```

## 当前实现读回与历史审计范围

当前后端读回（2026-10-18）：`_build_bmp05(binding=...)`调用`kos_engine.read_scoped_profiles(binding)`，返回授权范围profiles及source_refs，并按canonical_scope给global_binding或focus_binding。旧cross-brand builder观察不再是当前实现；作者跨平台保持不同身份，启发式tier/score不升级成已校准价值或转化效果。App字段适配、GLOBAL_ALL/FOCUS各实测和四端E2E仍须验证，当前后端有scope不自动构成完整界面ACCEPTED。

下面原首轮slice的“current/当前”实现观察、Widget测试和未接线结论保留为历史记录，不能覆盖本节新后端事实；其中有效产品目标/安全/布局要求继续有效。冲突的旧实现观察以本节为准，完整前端验收仍未由源码读回证明。

## 0. Authority basis and artifact disposition

- Constitution basis: BMP creator intelligence is Brand/Market-first and must preserve source lineage, risk semantics and responsive reading order.
- Product/workflow basis: BrandFocus → creator fit/authenticity/contribution/risk → content/propagation evidence. A creator profile is not a global account directory.
- Exploration references: current Experience Constitution blueprint only; generic social graphs and copied influencer dashboards are rejected.
- Anti-template decision: the page combines a creator relationship graph, tiered roster and one source-backed dossier; it is not a generic profile card wall.
- Sol design decision: `DESIGN_EXPLORATION`; the earlier creator builders were cross-brand; the current scoped backend is described above, while full front-end acceptance remains unverified.

## 1. User problem and product invariant

- **Role / context:** A BMP operator evaluates creators relevant to one authorized BrandFocus across KOS, KOL, KOC and UGC tiers.
- **User task / completion:** compare creator fit and contribution, inspect risk and source evidence, and decide which creator analysis deserves a later workflow handoff. Completion requires same-focus profile data, typed metrics with definitions/windows, source and trace.
- **Invariant:** a Subject ID cannot authorize or identify a creator's BrandFocus. A creator row with another focus or compatibility identity is hidden.
- **Global rule:** `GLOBAL / ALL` is the task-relevant creator results for the current authorized brand directory when the response and every profile row carry explicit canonical actor/task scope, verified lineage and `read_allowed`. Focused BrandFocus profiles without those markers are rejected, never promoted.
- **Out of scope:** contacting creators, publishing, campaigns, payments, identity matching, automated recommendations and any external effect.

## 2. Route, entry, exit and return

- **Entry:** host shell opens BMP-05; read is `GET /api/experience/screen/BMP-05` through `LumenisCoreClient.screen('BMP-05')`.
- **Required context:** server-returned focused BMP/ZBMP context with distinct Subject/BrandFocus IDs, applied binding and allowed read, or `GLOBAL_ALL` with explicit actor-directory read grant, canonical scope, verified lineage and `read_allowed`.
- **Exit / return:** creator selection, tier filter and risk filter are local presentation state. Return restores the selected dossier when the host preserves the screen; no context mutation occurs.
- **Trace:** the dossier retains creator source, evidence trace, metrics definition and window. No creator record or campaign is written.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime envelope and owner | Experience API adapter + BMP | `GET /api/experience/screen/BMP-05`; envelope and `truth` | Runtime-bound ZBMP/zbmp response | Mismatch blocks all profiles | BACKEND-GAP-022 | `experience_runtime.py::screen_viewmodel`; `bmp05_snapshot.dart` |
| P0 | Focus/global read binding | SYSTEM context / Permission | `focus_context` + `focus_binding` | FOCUS exact Subject/BrandFocus; GLOBAL_ALL explicit actor-directory read grant/canonical scope/verified lineage/read permission | Unknown blocks creator rows | BACKEND-GAP-022 | Historical cross-brand observation superseded by current read_scoped_profiles(binding) |
| P1 | Creator roster | BMP creator ecosystem owner | Future `sections[type=creators|creator_roster].items[]`: id, optional BrandFocus, name, tier, platform, source, trace, row scope/read/lineage fields | FOCUS exact BrandFocus; GLOBAL_ALL actor/task scope/verified lineage/read permission; tier is KOS/KOL/KOC/UGC | Invalid/cross-focus row omitted | BACKEND-GAP-022 | `Bmp05Creator` strict parser |
| P1 | Fit/contribution/risk metrics | BMP + Shared Evidence | typed metrics with value, unit, definition, window; risk level/label/score | Values are observed within the declared window; no missing→0 | Missing metric remains unavailable | BACKEND-GAP-022 | Current stats/profile outputs lack verified focus/lineage |
| P2 | Tier/risk filters | App presentation state | `Bmp05ViewModel` local filters | No server mutation | Filtered empty state is explicit | BMP05-UI-LOCAL | `bmp05_view_model.dart` |

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取创作者生态 | None; announce busy | No previous-focus rows flash | BMP05-W-001 |
| Global / all blocked | Actor-directory scope/lineage/read contract is absent, or only focused rows are returned | 当前全局范围暂不能查看未核验创作者资料 | Retry; return to context selector | Reject focused rows; do not relabel them global | BMP05-W-002 |
| Global / all ready | Authorized global binding plus valid global profiles | 查看当前任务相关的创作者资料 | Tier/risk filters; select creator | Preserve global view | BMP05-W-003 |
| Empty | Valid focus or global scope with no verified creators | 当前范围暂无创作者资料 | Refresh | Keep focus visible | BMP05-W-004 |
| Not collected / unknown | No creator collection or unknown state | 创作者资料尚未形成可核验记录 | Refresh | No zero metrics | BMP05-W-005 |
| Stale / partial | Stale data or missing metrics/lineage | 部分创作者资料仍待核验 | Refresh; inspect verified fields | Keep missing values explicit | BMP05-W-006 |
| Offline | Transport unavailable | 暂时无法读取创作者生态，请稍后重试 | Retry | No unscoped cached profiles | BMP05-W-007 |
| Blocked / denied | Missing binding, 401/403 or invalid lineage | 当前范围暂不能查看创作者资料 | Retry; return | Hide all profiles | BMP05-W-008 |
| Error | Malformed/unsafe response | 创作者生态暂不可用，请稍后重试 | Retry | Hide raw response | BMP05-W-009 |
| Ready | Exact-match focused profiles or authorized global profiles | Compare tiers, fit and risk, then inspect one dossier | Tier/risk filters; select creator | Restore local selection | BMP05-W-010 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-05)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：KOS 三阶漏斗与合规留资


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
-

### Existing contract — Purpose-built desktop composition

- **Primary question:** Which creators fit the selected BrandFocus, what do they contribute, and what risk or evidence should be reviewed?
- **Composition:** a focus/context header, a relationship graph grouped by KOS/KOL/KOC/UGC, a tiered creator roster, and a selected creator dossier with platform, metrics, risk, window and source. The graph has a roster equivalent and is not decorative.
- **Interaction:** selecting a node or row updates only the dossier; tier/risk filters change the local roster. No outreach or campaign action is present.
- **Resize:** desktop graph and roster share the primary region with dossier alongside; tablet stacks dossier below; the composition does not degrade into uniform cards.

#

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

## 5A. Web Workspace composition and desktop-only boundary

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Web uses the same Product Core response, parser and ViewModel. Browser deep-link restoration remains host-owned.
- No browser-only creator contact, export or campaign effect is exposed.

### Adopted Web additions

### 草图增补：KOS 三阶漏斗与合规留资

Web Workspace composition
Web：创作者比较表与漏斗按宽度切换摘要/详情；保留过滤、选择、来源钻取和原任务返回，表格提供键盘等价操作。

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-05)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：KOS 三阶漏斗与合规留资


### Existing contract — Purpose-built mobile composition

- Recompose into a tier/risk filter row, creator cards/rows and a focused dossier. The graph is summarized as relationship/tier labels rather than a shrunken desktop canvas.
- Keep BrandFocus and creator tier visible. Back returns from the dossier to the roster without changing context.
- Touch targets are at least 48 logical pixels; screen readers receive creator name, tier, platform, risk and available metric states. No unscoped cached roster is retained after interruption.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read creator ecosystem | BMP + SYSTEM context/Permission | Screen-specific read decision | Read only | Safe repeat | Existing source/trace refs | Block and retry |
| Filter / select creator | App presentation state | None beyond read | Local only | Reversible | None | Keep focus and filters |
| Contact / brief / campaign | No verified effect owner or approval contract | Unknown | Not shown | N/A | None | Omitted |

## 8. Accessibility, motion and localization

- Keyboard order is focus header → tier/risk filters → creator roster/graph equivalent → dossier. Enter/Space selects; Escape returns to the roster.
- The graph has a semantic roster equivalent. Each creator announces name, tier, platform, risk state, available metrics and source; unavailable fields are spoken as unavailable, not zero.
- No decorative animation; reduced motion disables graph transitions. Risk is conveyed by text/icon as well as color.
- Shared localization integration keys for `zh-CN`, `en` and `ko`: `bmp05.title`, `bmp05.focus_label`, `bmp05.tier.kos`, `bmp05.tier.kol`, `bmp05.tier.koc`, `bmp05.tier.ugc`, `bmp05.fit_label`, `bmp05.contribution_label`, `bmp05.risk_label`, `bmp05.state.not_collected`, `bmp05.state.blocked`, `bmp05.source_label`, `bmp05.trace_label`.
- Internal database/provider/path/permission vocabulary and raw source identifiers never enter visible copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP05-W-001 | Only creators matching the selected BrandFocus appear; cross-focus and Subject-shaped identities are rejected | Cross-focus / compatibility isolation | All widths | Snapshot + widget | `app/test/features/bmp05/bmp05_screen_test.dart` |
| BMP05-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no creator roster | Global / blocked | Desktop/mobile | Snapshot + widget | `bmp05_snapshot.dart` |
| BMP05-W-003 | Return authorized global binding plus explicitly global, lineage-verified profiles; render the creator workspace | Global / ready | Desktop/mobile | Snapshot + widget | `bmp05_snapshot.dart`; `bmp05_screen_test.dart` |
| BMP05-W-004 | Missing engagement/conversion remains unavailable; valid metrics retain definitions/windows | Partial / missing | All widths | Snapshot | `bmp05_snapshot.dart` |
| BMP05-W-005 | Desktop graph/roster selection opens a source-backed dossier without internal vocabulary | Ready / trace | Pointer + keyboard | Widget | `bmp05_screen_test.dart` |
| BMP05-W-006 | Mobile roster and dossier remain touch-safe and overflow-free; hostile text is dropped | Responsive / accessibility | 1440 / 768 / 390 logical px | Widget | `bmp05_screen_test.dart` |
| BMP05-W-007 | Offline/schema failure offers retry and hides raw response | Offline / error | Desktop/mobile | Repository + widget | Core client contract; runtime remains blocked |

The real creator API/Permission/Evidence and runtime/E2E gate remains blocked until the backend returns Focus-scoped or explicitly global profiles with traceable metrics. Widget fixtures are not production proof.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; bounded renderer remains `DESIGN_EXPLORATION`.
- **Open owners:** BMP must define creator fit/contribution/risk semantics and source contract; SYSTEM must return verified read binding; Shared Evidence must validate profile traces; the currently authorized frontend reviewer must review the graph/roster/dossier composition.
- **Required before acceptance:** live BrandFocus run, random entity acceptance, responsive/a11y runtime proof and an explicit boundary for any future creator contact or campaign effect.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand which creators fit a selected brand and what contribution/risk evidence supports that view.
- **REAL DELIVERY CARD:** real BrandFocus → scoped creator roster → selected creator dossier → source/metric trace. Current source fails the scoped entry gate; commercial readiness is `NO`.
- **SUBJECT SCOPE / TASK DATA QUALITY IMPACT:** `GLOBAL / ALL` may show the current task creator results only through explicit actor/task scope, lineage and read markers; focused profiles cannot become global roster truth. Current endpoint lacks that contract, so coverage remains blocked. Random sample acceptance is `NOT RUN / canonical scoped creator population unavailable`.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`; current governance and Product Core are reused, with no alternate creator data owner or provider.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 比较创作者匹配度和风险依据。
- **屏幕专属呈现：** 按已返回KOS/KOL/KOC/UGC类别呈列表和来源档案
- **来源、范围与版本连续性：** 指标定义、时间、BrandFocus、来源及评估版本进入后续任务
- **四端差异：** Web/Desktop列表与档案；Mobile先理由后样本；官网仅授权案例
- **失败与恢复：** 同名和跨焦点隔离，样本不足未知；无联系/支付动作
- **补充验收：** 候选逐项可追来源，切scope后旧档案不残留。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

## Current projection and approved complete target (OPEN)

本节区分当前创作者资料读取与已批准的完整创作者工作目标；原§1所列联系、发布、campaign、付款和外部效果排除项继续有效，此次补入的回复草稿仅供用户检查/改写；既有完整创作者目标仍保留，不把草稿当作自动联系或自动推荐。不更改 frontmatter、BMP/SYSTEM Owner、现有只读绑定或当前状态。集中视觉规划输入（不替代本屏现行合同）：[BMP-05完整草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-05)。

- **当前投影（保持）：** 当前读取仍为 GET /api/experience/screen/BMP-05，经 LumenisCoreClient.screen('BMP-05')；沿 BACKEND-GAP-022、现有 focus_context/focus_binding 和 Permission 约束展示真实资料。未知 scope、未验证 lineage、缺少后端资料不生成创作者、指标或候选动作。
- **完整目标与既有 Owner（OPEN）：** BMP/C3 继续拥有创作者业务语义、筛选、比较和用户决策；SYSTEM Context/Permission 继续拥有焦点范围与授权。完整目标包括按 KOS/KOL/KOC/UGC tier 筛选，比较受众证据、作品内容、合作历史与成本，以及有来源和时间窗的真实性/贡献/风险线索；风险线索不作定论，查看创作者来源/作品及曝光→互动→留资三阶漏斗和同源分母；CPL/成本只显示真实值/区间/缺失，分母缺失或来源/市场混用不得计算转化率。AI发现/内容共现与观测事实分层，粉丝/点赞不等于 ROI。用户保存 shortlist 与合作 Brief 时保留选择理由；创作者档案标签、合作方式、报价来源/适用期、合作笔记/状态/待办及相似候选理由仍由 BMP-05/BMP-07 对应既有 Owner 承接，Campaign 生命周期留 BMP-07，不因本屏只读 slice 或回复草稿而从完整目标消失；按主稿适配 Web 比较、iOS 选中档案/比较。批准草图还允许生成待审评论回复草稿；创作/保存沿现有 BMP/Shared SavedWork/Artifact Owner，不新设回复服务或调用方。
- **输入、结果与权限：** 输入是当前允许的 Subject/BrandFocus 或明确授权 GLOBAL / ALL 上下文，以及具有真实 source/trace/lineage、同一市场范围、时间窗、单位和分母的创作者、作品、受众、合作历史、费用与评论资料。输出为可筛选/可比较的创作者档案和真实三阶漏斗/CPL状态；用户可保存 shortlist/合作 Brief 与选择理由，并按批准目标生成注明来源与版本的可编辑回复草稿。不把AI发现写成 Canonical 事实，不伪造评论、受众或创作者关系。读取需当前 screen-specific Permission，引用/派生使用另满足 SourceUse。
- **效果、保存、返回与恢复：** 草稿永不自动发送；评论/私信在专业号或企业授权未具备时明确不可用。不联系创作者、不发布、不执行 campaign、不付款、不匹配身份，也不触发任何外部效果。用户可按现有 BMP/Shared SavedWork Owner 保存、修订、重开 shortlist、合作 Brief、选择理由与回复草稿，并返回同一创作者与 BrandFocus/Subject 上下文；若无精确保存 callable，保存保持 OPEN/UNBOUND。来源失效或撤权时阻止继续使用该来源，已写入的用户草稿依既有版本合同保留并标示引用失效。
- **未绑定与验收：** 当前读取与 BG-022 尚未提供评论回复生成或保存 callable；对应操作保持 OPEN/UNBOUND，不能以只读资料、按钮或 mock 结果宣称完成。真实验收须以允许使用且可追溯的真实输入完成筛选/比较、查看作品、核对同源分母、风险线索来源/时间窗及缺失状态、保存/重开 shortlist 与合作 Brief 并保留选择理由、起草/编辑/保存/重开回复、撤权/源失效提示与返回；确认未授权时评论/私信不可用、浏览器/网络侧没有自动发送或其他写入，并在对应 Web/Desktop/Mobile 实际路径验收。


## 2026-10-18 完整工作面细化：迁移、业务与内容模式

保留原状态/Owner/接口和完整终态；本文补足视觉交互，不宣称已接通或已验收。

### 作者、传播与同口径品牌比较

作者入口复用BMP-05三阶漏斗，左侧当前品牌/平台/时间范围，中间作者列表，右侧单作者证据检查器。账号按平台分行，不将相似昵称合并成同一人；层级标“启发式分层”，具体采用条件/未知在详情，不用统一达人价值分数。评论从明确父笔记进入，顶栏保父帖与样本窗口；传播读回按真实事件顺序，互动数、已观测事件和未知触达分别标注。
BMP-11比较区只并列当前BrandFocus授权样本与可比时间窗，列标题带定义/分母/覆盖；采样缺口占独立说明区，不用柱高宣称市场冠军。BMP-09指标可从手工导入或实际专业号来源进入，值旁显示“人工录入/平台读回”、单位/日期/版本，零分母或缺项显示未知；编辑手工值先保原值与修改理由/来源，预览后形成新版本，不改平台观测。
筛选切换时保当前已看作者/比较选择但重验scope；跨品牌、撤源、旧签名或专业号未配置时停止受限动作并清敏感预览，保合法草稿。加载与无匹配分开，取消编辑回原指标，保存失败保输入；恢复先读当前来源，不用本地cookie或界面开关声明授权。Web比较可锁列并深链回原作者/笔记；Windows/macOS可并读资料与指标并从实际文件导入，失链保上次合法可读状态；iOS按范围→作者/指标→依据/比较两两切换，横向表提供逐列读屏，不挤成缩略图。官网只展示去敏样本口径，不声称平台完整覆盖或商业收益。
界面AIGC按用户问题建议作者证据列、评论主题分组或可比样本对照，事实指标/分母不让模型补零，用户可锁列和撤销重排；未知保持可见。价值是知道哪些比较可信，减少跨平台身份和样本口径误用。

### 合作草稿、执行批准与不明结果

从作者/活动的“建立合作草稿”进入现有业务对象，不自动创建投放。宽屏主区是可编辑目标/资源/范围/动作草稿，右侧版本与将受影响对象；下方用分开的“草稿→请求审阅→已批准→执行回执”阶段行。批准确认显示当前精确请求摘要、对象、动作、范围与版本；撤销批准为独立动作。用户看得到批准不是执行，不把客户端布尔值、legacy解锁cookie或页面隐藏当服务端Permission。
仅已注册且当前可用渠道才显示合法执行入口；未配置写“尚无可用执行渠道”，仍能保存方案。提交后由Owner读回真实执行与receipt；超时未知提示“结果待核”，提供核原请求回执和返回草稿，不自动重新发送。取消请求、撤销批准、停止当前动作分别说明效果边界，已产生的外部结果不被删除。旧scope/来源/请求变更使旧批准失效，重新预览批准；失败保原稿与历史，不显示空成功。
Web恢复原工作和请求版本，刷新不会执行；Windows/macOS窗口重开先核原执行回执，后台Core状态另示；iOS先草稿摘要→精确批准Sheet→结果页，实际禁止的执行动作保持说明并返回已存任务，既有合法审阅不因窄屏丢失。官网演示草稿/批准/真实执行的区别，不将未绑定渠道做动效假演示。界面AIGC可按任务建议行动摘要/资源比较顺序，批准与执行控制独立固定、不能生成或替点确认；用户锁定的草稿不被覆盖。价值是减少误批、误发与重复外部效果。


### 全项具体工作合同：多准则、组合、排期及人员配置

新增业务可编辑字段及Owner结果映射，不暴露任意JSON、内部算法参数或论文选择器。状态至少：需补单位/币种、判断不一致、不可行约束、预算/时限耗尽、已有可行但未证最优、完整枚举失败、计划待采用、保存冲突。采用计划/配置只保存Decision/Brief，联系/采购/发布另获原授权。验收预算变动、必选与互斥冲突、资源重叠、未知覆盖不求和、等数/规模限制、无可行配置、取消后重开、旧计算晚到不盖新约束。

CTH-09上部目标与约束，中部方案同字段并列，右侧取舍解释；不一致判断行就地高亮并有文字。BMP-05候选列表旁固定预算/覆盖，选中组合与备选在同一比较层。BMP-07排期条上方资源/时窗，底部冲突清单可定位，拖拽另有起止时间键盘输入。人员配置为“人×岗位”可勾选矩阵＋完整方案清单，iOS逐人选择岗位并审阅冲突，不缩小矩阵。Web/Desktop可并读；官网真实例；iOS只开已支持约束编辑/方案审阅，复杂排期续接同版本。UI适配按目标提出取舍表、预算组合或资源排期视图，不改变权重/资格/约束，锁定比较维度与选中项。

具体操作与恢复：方案比较有三种已有业务输入面。取舍比较：逐项编辑指标值/单位、越高越好或成本方向及“更看重哪项”的成对判断，显示权重、判断不一致位置与排序敏感性；不要求用户操作AHP/TOPSIS名词。创作者组合：预算、每项真实成本、声明效益单位、必须覆盖、候选纳入/排除并读，显示选中组合/替代与未满足约束；效益相加假设不冒独立触达。排期：开始时点/时区、时段长度、资源、任务时长/窗口、强制任务、先后关系和互斥可编辑，冲突定位具体资源/时段，改变约束后只提新计划，不执行活动。
人员到岗位的有限配置另以等数人员/岗位和明确可任职配对矩阵呈现，当前每侧最多12。只展示可行完整配置和等权情景下配对占比，不称录用概率、最佳成本排班或业务适配事实。源资料只保上下文，资格由用户声明；不在界面自动推断。达到预算上限不能展示截断枚举为完整分布；取消/资源不足保矩阵及旧成果。


### 全项具体工作合同：排序、实体候选、主题、分类评价与新颖度

保持这些计算各归既有Reporting/Entity/主题Owner；展示状态包括样本不足、依赖不可用、语言不支持、训练测试分离未知、待核身份、未知分类、未见历史类别及向量版本不一致。保存是派生分析，撤销不改源档案；来源变动生成新比较。验收零试验组、并列/小样本、同名跨平台不合并、三语分报与弃答分母、主题离群、KL无穷、零向量/模型错版和取消重开。

各子任务嵌原屏：BMP-05比较表加样本/原始/收缩/区间列；BMP-02左右档案＋待核依据；BMP-03主题列表→文档与离群项；SH-05按语言的评价表和新旧分布并读。Desktop/Web保来源侧读，iOS逐项候选与同字段比较，官网仅有证例。UI自身AIGC依样本不足、身份歧义、主题离群或分布断点选择强调区域；只重排真实字段，不能把未知实体线、空主题或向量距离变成事实。

具体操作与恢复：排序结果先保每项成功数/试验数和样本不均，展示原始比率与收缩后估计/区间，并说明小样本变动；不能把排名当因果效果或真实人口覆盖。实体匹配显示左右原档案、匹配/不匹配证据、待复核候选和分离测试指标，低把握保持待核，用户审阅不自动合并Canonical身份。
主题探索以同语种实际文档集为输入，展示主题词、样本文档和离群项，词法TF-IDF/SVD不能叫神经语义理解；缺依赖或样本保原文列表。情感/立场评价按中英韩分别给保留集、混淆表/F1与弃答覆盖，不让未知混入比例。新颖度面并读当前/历史类别分布和相同模型版本向量距离；新类别导致无穷散度要直接说明，不能截成漂亮有限分；距离不当语义原创或商业价值证明。


### 原要求具体工作合同：Persona六字段、角色任务和四类回复

在当前账号/品牌或独立项目上下文中编辑Persona：受众、内容支柱、口吻、禁区、商业边界、CTA风格六项分别有原值、用户改动、来源/假设与版本；每条Brief明确采用哪一版。KOS/KOL/KOC/UGC为当前任务角色与适用约束，不因账号昵称或粉丝数自动赋类。修改Persona先列受影响未交付作品与已批准回复，用户选择采用范围，不改已发历史。
评论回复沿原Owner四类定义逐项显示实际类别名、原评论及必要上文、对应Persona约束和待审回复；四类定义尚缺时保持待接线，不临时换一套类型。Risk命中指出原文位置和原因并转人工，内容仍可手改保存，不能暗发或一键跳过人审。

BMP-06上下文边栏用六项折叠表单，顶部显示Persona版本和本Brief采用状态；BMP-05评论区为原评论→类别→回复草稿→风险与所用Persona的纵向阅读，主动作保存草稿/提交既有人工审阅。Web/Windows/macOS原评论与回复并读，iOS一条评论/回复与Persona Sheet，返回保未发稿；官网只授权去敏例。智能UI可按实际冲突把相关Persona字段与句子并读，不推断个人属性、不改角色/风险或自动代发。

状态区分Persona未保存、Brief未采用新版、角色未知、类别定义缺失、待人工、拒绝、草稿保存和外部未发送。当前没有真实回复executor时只给草稿动作；取消保原Persona/回复，旧审阅不能跟随改稿。验四角色、四类别、六字段完整、跨品牌拒绝、Risk转人工、改版影响、同一评论重复请求和冷开未发稿。

### 原G106具体终态合同：平台原生信号与改写依据

选定创意/内容版本后，原生信号面逐行列停留、完播、重看、私发转发、评论、收藏、点赞的值/单位/期间/分母/可得状态和来源。指标优先是原方法语境，不自动变跨平台统一权重；不可得不补0。ROI区域单列成本、实际收益、归因范围及缺项，不能由点赞计算。打开“据此改写”返回该平台可编辑草稿，保事实母版并显示钩子/结构/时长/包装改变理由。

构图：左内容与平台版本，中间同字段信号表，右原生来源与改写差异；ROI与互动反馈不同区域。iOS逐平台同字段切换，不用同一柱高冒同尺度。

平台字段缺失、定义不可比、费用/收益不足、数据过期各保文字；取消保原稿，重开原信号版本，采用改写只改该平台候选，不自动发布或恢复外部权限。

Public Website仅用获准真实样例说明平台原生信号与改写依据及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按可比字段优先安排证据列，用户锁列/简洁/撤销；不造指标或把版式重排当商业回报。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G107具体终态合同：播客五力与六种合作选择

在嘉宾/合作Brief旁打开合作比较：影响力、内容力、人群力、矩阵力、变现力五列分别有观察/来源/窗口/未知，不压成万能分。合作模式按原方法列冠名贴片、节目定制、播客联合营销、品牌自有播客、整合营销“声音+”、线下活动/IP联名；选择后比较适用目标、所需资源、真实报价/权益、可交付内容和待确认条件。五力资料与模式建议分层，选题关联真实营销节点，选择只保存Brief不联系/采购。

构图：顶部当前品牌可选上下文与选题，中央播客/嘉宾同字段五力表，右侧六模式详情，底部选择理由/待补条件与保存Brief；iOS先单对象五力再两两比较和模式Sheet。

缺受众/播放/报价不补分，模式适配待核或权益未知标明；改节点/预算后列影响，取消保原Brief，保存/重开核同版本；外联和付款不由选择触发。

Public Website仅用获准真实样例说明播客五力与六种合作选择及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按用户目标提出五力证据对照和模式取舍构图，保原始来源、锁定/撤销；不能生成合作事实或擅替用户定模式。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G119具体终态合同：KOS合规、矩阵差异与留资边界

三阶漏斗旁按选中内容/账号展开合规检查，保CPL、真实成本与场景分层来源。矩阵内容相似度>50%显示待审搬运预警及实际对照文本/方法，不直接判侵权；错峰与行为差异展示计划时间/平台规则和可编辑建议，不自动操纵账号。强监管绝对化用语逐处定位并给替换候选，原文保留。实际AI参与的披露按适用平台显示“AI辅助生成”说明/相应话题，可调整合规表达但不可删去必要披露；未参与不假打标。评论/私信只保存草稿；私信通仅在企业号及当前授权/合同真实可用时显示选择，缺条件说明未启用。

构图：创作者档案/漏斗为主，右侧选中内容的相似片段、风险词与披露检查器；计划表单与回复草稿编辑分别打开，底部保“仅草稿/未发送”。iOS单问题逐项修订，不把全部风险揉成总分。

缺费用/分母/平台规则/授权、检测失败、待人审和过期内容分开；改稿后相关检查失效，取消保原稿，保存/重开保披露与版本。没有真实执行合同绝不发评论/私信。

Public Website仅用获准真实样例说明KOS合规、矩阵差异与留资边界及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按需突出冲突片段和缺授权说明，保用户锁选区/撤销；不自动删除披露或把警告淡化成批准。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G172具体终态合同：创作者到AI引用观测链

在选中创作者档案“AI发现观测”中按Creator→Content→AI引用/推荐观察列三层真实对象，每条边标direct/source/thematic/unknown及对应原文/时点/查询范围。直接链接、来源关系和主题共现分开，未知不转Missing；创作者/内容/AI观测各自指标及分母分别显示，不合成“AI影响力”单分，不从共现推因果或收入。

构图：主区三列链路表及等价关系图，右选中观察的原始证据，底部范围/未知；iOS从作者→内容→一次AI观察逐层，返回保边和原档案。

无实际观测、查询未核、引用内容不可读、关系未知、重复观察或来源变更单列；筛选不改原观察，取消保档案，保存分析引用准确观测版，重开可核原链。

Public Website仅用获准真实样例说明创作者到AI引用观测链及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按真实边的层级组织路径阅读，不补虚线当事实；可锁边/切线性表/撤销，不由图大小暗示因果。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。
