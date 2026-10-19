# BMP-02 — 品牌组合与竞品谱系

```yaml
screen_id: BMP-02
status: BLOCKED
revision: 1
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-019
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-02 acceptance
```

## 0. Authority basis and artifact disposition

- Constitution basis: BMP is Brand/Market-first; responsive composition must recompose at the approved desktop, tablet and mobile widths.
- Product/workflow basis: BrandFocus → market position → competitor set → source-backed comparison. A CTH Subject is never a BrandFocus substitute.
- Exploration references: the current Experience Constitution blueprint only. No PDF, screenshot, Figma frame or historical UI is copied into this slice.
- Anti-template decision: the desktop view is a constellation of owned, sub-brand and competitor entities with one selected profile; it is not a KPI wall or swapped-title card grid.
- Sol design decision: `DESIGN_EXPLORATION`; implementation is a bounded scope-guard slice and remains blocked for full acceptance until the callable returns verified BrandFocus rows.

## 1. User problem and product invariant

- **Role / context:** A BMP operator compares one authorized BrandFocus with its owned brands, sub-brands and competitor entities.
- **User task / completion:** choose or confirm a BrandFocus, or inspect the default global product universe, understand the portfolio relationship, and inspect one source-backed entity profile. FOCUS completion requires exact `brand_focus_id`; GLOBAL_ALL completion requires explicit global scope, verified lineage and row read permission, plus source and item-level trace.
- **Invariant:** `subject_id` identifies the selected context only; `brand_focus_id` is a distinct BMP business scope. The screen must never infer brand ownership from a Subject, author, source or display name.
- **Global rule:** `GLOBAL / ALL` is the default full-universe view. It may show real global portfolio rows only when the response and every row carry explicit canonical global scope, verified lineage and `read_allowed`; a focused BrandFocus row without those markers is rejected, never promoted.
- **Out of scope:** changing context, creating a brand, editing competitor sets, CTH records, publishing, reports and any write or external effect.

## 2. Route, entry, exit and return

- **Entry:** the canonical App Shell may open BMP-02; this batch does not alter shell routing. The screen reads `GET /api/experience/screen/BMP-02` through `LumenisCoreClient.screen('BMP-02')`.
- **Required context:** either a server-returned `FOCUS` context for `domain_id=BMP`, `product_id=ZBMP`, a non-empty `subject_id`, a distinct `brand_focus_id`, `focus_binding.applied=true` and an allowed read decision, or `GLOBAL_ALL` with the explicit global grant, canonical scope, verified lineage and `read_allowed` contract above. The route cannot grant authorization.
- **Exit / return:** entity selection is local presentation state. Return restores the selected entity, search query and role filter when the host keeps the screen alive. No context mutation occurs.
- **Trace position:** the selected entity dossier retains its source and trace reference in the response-backed view model; a future trace route is not invented here.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Envelope and product identity | Experience API adapter + BMP | `GET /api/experience/screen/BMP-02`; `ok`, `screen`, `bound`, `source`, `truth.product_id`, `truth.domain_id` | Must be runtime-bound and exactly `ZBMP` / `zbmp` | Mismatch blocks all business rows | BACKEND-GAP-019 | `experience_runtime.py::screen_viewmodel`; `bmp02_snapshot.dart` |
| P0 | BrandFocus context and read decision | SYSTEM context / Permission + BMP scope | `focus_context` and `focus_binding` in the response | `FOCUS` requires distinct Subject/BrandFocus; `GLOBAL_ALL` requires `scope_verified=true`, `global_all_granted=true`, `evidence_lineage=verified`, canonical global scope and `read_allowed=true` | Unknown or denied blocks entity rows | BACKEND-GAP-019 | Current BMP-02 builder does not return a verified focus/global binding |
| P1 | Portfolio entities | BMP canonical owner | Future `sections[type=brands|portfolio].items[]` with `id`, optional `brand_focus_id`, `name`, `role`, `source`, `evidence_ref`, `read_allowed`, `scope_mode`, `canonical_scope`, `lineage` | FOCUS rows require exact BrandFocus; GLOBAL_ALL rows require explicit global scope, verified lineage and row read permission | Missing, focused-without-global-markers or cross-focus rows are omitted, never reassigned | BACKEND-GAP-019 | `_build_bmp02()` currently returns a curated directory without BrandFocus/global lineage |
| P1 | Selected entity profile | BMP canonical owner + Shared Evidence | Same entity row plus optional typed metrics, category, capture time and window | Each value remains source-backed and scope-matched | Null stays unavailable; no missing→0 conversion | BACKEND-GAP-019 | `Bmp02Brand` parser and dossier are bounded to verified rows |
| P2 | Search and role filter | App presentation state | `Bmp02ViewModel` local filters | No server mutation | Empty filter state keeps the focus banner and offers clear filter | BMP02-UI-LOCAL | `bmp02_view_model.dart` |

Local filter recovery semantics: role options come from the complete verified in-memory portfolio; the highlighted row always matches the visible dossier; filtering may temporarily show a fallback without replacing the user's explicit selection; and the filtered-empty state offers one action that clears the query and role filter locally.

The current backend builder is intentionally treated as unscoped. A successful HTTP response or a curated brand directory does not satisfy this table.

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取品牌组合 | None; announce busy | Keep selected focus context; show no stale rows | BMP02-W-001 |
| Global / all blocked | `GLOBAL_ALL` lacks global grant/lineage/read contract, or only focused rows are returned | 当前全局范围暂不能显示未核验的品牌组合 | Retry; return to host context selector | Reject focused rows; do not relabel them global | BMP02-W-002 |
| Global / all ready | Authorized global binding plus at least one valid global row | 查看全球品牌产品宇宙与组合关系 | Search, role filter, local selection | Preserve global view; selection does not create BrandFocus | BMP02-W-003 |
| Empty | Bound focused or global payload has no valid entity rows and no rejected rows | 当前范围暂无品牌组合资料 | Refresh; clear filters | Keep scope visible | BMP02-W-004 |
| Not collected | `truth.data_state=NOT_COLLECTED` | 品牌组合资料尚未采集 | Refresh | Preserve unavailable metrics; never show zero | BMP02-W-005 |
| Stale / partial | Data state is stale or some rows lack lineage | 部分品牌资料仍待核验 | Refresh; inspect verified rows only | Hide invalid rows and keep source note | BMP02-W-006 |
| Offline | Transport unavailable | 暂时无法读取品牌组合，请稍后重试 | Retry | Do not substitute cached unscoped data | BMP02-W-007 |
| Blocked / denied | Missing focus, wrong owner, 401/403 or read denied | 当前范围暂不能查看品牌组合 | Retry; return | No business rows or internal diagnostics | BMP02-W-008 |
| Error | Malformed or unexpected response | 品牌组合暂不可用，请稍后重试 | Retry | Hide raw response text | BMP02-W-009 |
| Ready | Focus exact-match rows or authorized global rows pass all checks | Compare the selected focus or global portfolio and competitor set | Search, role filter, local selection | Restore local selection only | BMP02-W-010 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Primary question:** Which entities belong to this BrandFocus, and how does the selected entity relate to the portfolio?
- **Composition:** a compact focus/context rail, a broad constellation field with owned/sub-brand/competitor grouping, and a selected entity dossier with source/time window. The constellation is a relationship view, not a repeated metric-card surface.
- **Interaction:** clicking or keyboard-selecting one entity updates only the dossier. Search and role chips filter the local list; they never change BrandFocus authorization.

### 5A. Web Workspace composition and desktop-only boundary

- Web uses the same Product Core response and ViewModel semantics. Browser URL/deep-link restoration is host-owned and not invented in this batch.
- No desktop-only effect or export exists. Unavailable actions remain absent rather than appearing as disabled fake affordances.

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Keep the selected BrandFocus visible, followed by a searchable portfolio list. The selected profile expands below the list and competitor entities are represented as explicit chips/rows, not a miniature desktop constellation.
- Touch targets are at least 48 logical pixels. Back returns to the host shell; it does not switch Subject or BrandFocus.
- On interruption, retry the same read and preserve only local filter/selection state. Do not show stale rows from another focus.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read portfolio | BMP + SYSTEM context/Permission | Screen-specific read decision required | Read only | Safe repeat | Existing source/trace refs only | Block and offer retry |
| Search / role filter | App presentation state | None | Local only | Reversible | None | Show filtered empty state |
| Select entity | BMP presentation state | None beyond the already-authorized read | Local only | Reversible | None | Keep current focus; no context mutation |
| Edit portfolio / add competitor | No verified write owner in this slice | Unknown | Not shown | N/A | None | Omitted, never simulated |

## 8. Accessibility, motion and localization

- Keyboard order is focus context → search → role filters → entity list → dossier. Enter/Space selects an entity; focus remains visible after filtering.
- Each entity exposes one semantic label containing its name, relationship role and selection state. Constellation visuals have a list equivalent.
- No decorative animation is required; reduced motion removes any selection transition. Color is never the only role signal.
- The shared localization owner receives semantic keys, not feature-local dictionaries. Required integration keys are declared for `zh-CN`, `en` and `ko`: `bmp02.title`, `bmp02.focus_label`, `bmp02.role.owned`, `bmp02.role.sub_brand`, `bmp02.role.competitor`, `bmp02.state.not_collected`, `bmp02.state.blocked`, `bmp02.source_label`, `bmp02.trace_label`.
- Machine IDs, source paths and internal diagnostics are not user copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP02-W-001 | Parse a focused response and render only rows whose `brand_focus_id` equals the selected BrandFocus | Cross-focus / compatibility rows rejected | All widths | Snapshot + widget | `app/test/features/bmp02/bmp02_screen_test.dart` |
| BMP02-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no rows | Global / blocked | Desktop and mobile | Snapshot + widget | `bmp02_snapshot.dart` |
| BMP02-W-003 | Return authorized global binding plus explicitly global, lineage-verified rows; render the same portfolio workspace | Global / ready | Desktop and mobile | Snapshot + widget | `bmp02_snapshot.dart`; `bmp02_screen_test.dart` |
| BMP02-W-004 | Return `NOT_COLLECTED`, `UNKNOWN` or null metrics; preserve explicit unavailable state and never render zero | Not collected / unknown | All widths | Snapshot | `bmp02_snapshot.dart` |
| BMP02-W-005 | Select an entity; dossier keeps source, window and trace-backed fields and reveals no internal vocabulary | Ready | Desktop / keyboard | Widget | Purpose-built dossier test |
| BMP02-W-006 | Narrow to mobile width; list, search, filters and dossier recompose without overflow | Responsive / accessibility | 1440 / 768 / 390 logical px | Widget | `bmp02_screen_test.dart` |
| BMP02-W-007 | Transport or malformed response offers retry without echoing raw server text | Offline / error | Desktop and mobile | Repository + widget | Core client contract; runtime binding still blocked |

The real Product Core/API/Permission/Evidence acceptance is blocked until the backend returns verified BrandFocus rows. Fixtures prove parser and rendering isolation only; they do not prove production completion.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; the bounded renderer is `DESIGN_EXPLORATION` with a fail-closed implementation.
- **Open owners:** BMP must define the canonical portfolio/competitor response and metric lineage; SYSTEM must return the actor/read decision; Shared Evidence must validate item traces; App Shell must later bind the host BrandFocus selector.
- **Changes required before DESIGN_READY / ACCEPTED:** a current callable with per-record BrandFocus, Permission and Evidence proof; live runtime/E2E on desktop/web/mobile; and Sol review of this screen-specific composition.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand the selected brand's portfolio position and competitor set well enough to choose the next market-intelligence drill-in.
- **REAL DELIVERY CARD:** real BrandFocus input → scoped portfolio read → visible entity relationship and source-backed profile → local selection return. Current callable fails the scoped-read entry gate, so commercial completion is blocked.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** `GLOBAL / ALL` is the default global product universe when the explicit global contract is present; focused rows are never promoted. Current endpoint lacks that contract, so global coverage remains blocked. Random entity acceptance is `NOT RUN / current canonical scoped population unavailable`.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` for this bounded slice. The Experience Constitution and current Product Core are sufficient references; no third-party dependency or alternate data owner is introduced.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 理解品牌组合、子品牌与竞品关系。
- **屏幕专属呈现：** 带来源关系图加选中实体档案，明确已核实/推断/未知
- **来源、范围与版本连续性：** 每条边保留BrandFocus、entity ID、关系来源和版本
- **四端差异：** Web/Desktop图和档案；Mobile可展开关系列表；官网不展示私有谱系
- **失败与恢复：** 跨焦点、来源缺失或过期关系不显示为事实
- **补充验收：** GLOBAL/FOCUS授权分别成立；本地选择不改谱系/授权。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


### 全项具体工作合同：排序、实体候选、主题、分类评价与新颖度

保持这些计算各归既有Reporting/Entity/主题Owner；展示状态包括样本不足、依赖不可用、语言不支持、训练测试分离未知、待核身份、未知分类、未见历史类别及向量版本不一致。保存是派生分析，撤销不改源档案；来源变动生成新比较。验收零试验组、并列/小样本、同名跨平台不合并、三语分报与弃答分母、主题离群、KL无穷、零向量/模型错版和取消重开。

各子任务嵌原屏：BMP-05比较表加样本/原始/收缩/区间列；BMP-02左右档案＋待核依据；BMP-03主题列表→文档与离群项；SH-05按语言的评价表和新旧分布并读。Desktop/Web保来源侧读，iOS逐项候选与同字段比较，官网仅有证例。UI自身AIGC依样本不足、身份歧义、主题离群或分布断点选择强调区域；只重排真实字段，不能把未知实体线、空主题或向量距离变成事实。

具体操作与恢复：排序结果先保每项成功数/试验数和样本不均，展示原始比率与收缩后估计/区间，并说明小样本变动；不能把排名当因果效果或真实人口覆盖。实体匹配显示左右原档案、匹配/不匹配证据、待复核候选和分离测试指标，低把握保持待核，用户审阅不自动合并Canonical身份。
主题探索以同语种实际文档集为输入，展示主题词、样本文档和离群项，词法TF-IDF/SVD不能叫神经语义理解；缺依赖或样本保原文列表。情感/立场评价按中英韩分别给保留集、混淆表/F1与弃答覆盖，不让未知混入比例。新颖度面并读当前/历史类别分布和相同模型版本向量距离；新类别导致无穷散度要直接说明，不能截成漂亮有限分；距离不当语义原创或商业价值证明。


### 全项具体工作合同：财务采集目标、主体研究档案和候选审查

保持目标、捕获、导入、分析与研究档案版本的各自回执；保存审查不等Registry变更。状态包括凭证未配、捕获未知、字节不符、原件变更、scope不匹配、陈旧父版、身份来源不足、待更多证据及注册未执行。验收捕获成功但未导入、解析失败、同名主体、签名有效但断言未核、注册建议改侧/名字、取消及重开原选择。

SYS-02内以来源阶段条＋当前目标详情显示采集/捕获/导入，不新建采集中心；SH-02档案预览为来源/断言并读；BMP-02候选审查为左右实体、引文侧栏和底部三个命名决定。Desktop/Web并读，iOS一侧一屏可同字段切换并返回，注册等敏感决定沿原确认；官网只用公开例。UI适配将待核字段和来源冲突提出到前侧，保未改档案位置，不能自动把候选涂成已注册。

具体操作与恢复：财务来源流程将“准备目标→获准采集→捕获字节待导入→导入→解析成果”分别显示，目标标识、官方路径、当前身份/用途及所选字段可核。生成OpenDART请求描述不等已配置密钥或已抓取；不在前端收集或回显秘密。每阶段失败保原任务/材料，未知完成先查原回执，不再发一次采集。
主体研究档案按已确定领域/主体范围导入，先预览来源清单、研究断言、父版本与审阅记录；签名只说明完整性，断言仍是研究推断且底层出版权利未知。实体候选审查从准确分析版本打开左右原档案/引文，选择“保留分开、需更多证据、提出注册建议”并记录理由。注册建议必须明确取哪一侧身份及名字，再进入既有Registry的独立批准；本审查不会合并或直接注册。


### 主体身份与市场关系的有据编辑（U01–U03）

从ACC-02“查看当前主体”或CTH-02/BMP-02对象名称旁“身份与市场关系”进入，顶栏固定原始官方名称、稳定身份和当前查看范围；别名搜索结果逐行显示实体类型、地点与来源，不因同名自动合并。主面按“对象本身—场所/门店归属—市场关系”三层排列：场所、门店、租户、品牌分别列卡，关系行显示类型、起止日期、依据和待核/已核/冲突；点击关系打开原资料Reader，不能把同品牌全部门店静默纳入场所监测。

“市场关系”不是一个国家下拉框：来源国、总部所在地、法律主体/司法辖区、经营市场、营销/活动市场及具体地点分别有独立标签、证据和日期；可多值，未知留空并显示未知，不能把总部国家自动填入其余字段。右侧“本次工作范围”仅预览当前选择会包含的确切实体/市场，GLOBAL默认和清除聚焦保留；新增、修订关系及聚焦各是不同动作，选择永不授予采集或业务权限。

有当前Owner真实编辑能力及Permission时，用户逐行选择关系类型、目标对象、有效时间和依据；保存前并排显示旧/新值、受影响后续引用与本次作用对象，取消保未提交稿且不改服务器事实。缺依据、同名歧义、重叠有效期、当前版本冲突、撤权与保存失败逐行标出；先补证/重新读当前版本，不能自动重试覆盖另一人的修改。已保存关系可按当前权限读历史；撤回/恢复只用真实Owner动作，不能在界面造“修正事实”。不存在callable时保持可核只读并明确能力缺口，原要求仍待实现，不移除字段或伪造保存。

Web/Windows/macOS宽屏左侧身份与关系清单、中间选中关系、右侧依据及范围预览；窄Web顺序展开并保原选中关系。iOS从对象详情逐层打开“关系”与“依据”Sheet，编辑单条并在键盘上方固定取消/保存，回原任务保范围；两桌面系统分别验证多窗口冲突。官网仅用公开获准示意说明不同关系，不列私有主体。价值是避免错误实体归属和市场口径污染后续分析。界面自身AIGC可按已知关系密度提出原创可编辑关系阅读构图，图中只连有据边；未知关系用缺口文字，不生成国旗归属、地图定位或推断关联。可切回同源列表、锁定布局、撤销、低动效和无AI基础操作。

### 原G139具体终态合同：平台与主体话题词条库

从当前主体/品牌档案的既有话题资料进入词条库，顶部平台×主体/市场范围，行列原词、归一化/别名、任务语义、适用期、来源和词条版本；候选/已采用/退役与热度/rank未知分开。新增/修订词条先保真实来源及任务语境，版本化扩充，原种子数量不等热榜或全平台覆盖。选择用于采集只预填原Collector任务范围，执行另按原权限。

构图：左平台/主体过滤，中词条列表，右语境/原文与修订稿，底部保存新版/用于当前任务；iOS词条→原文/别名→保存，返回保过滤及未提交词。

无热度证据留UNKNOWN，不转0；同词跨平台语义冲突、过期活动、源撤回和版本冲突各提示。取消保原库，采用不篡改旧查询，重开绑定原版本和scope。

Public Website仅用获准真实样例说明平台与主体话题词条库及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可依据真实语境分组词条并显示别名歧义，不能生成热榜/排序事实；锁定、手工列表和撤销可用。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。
