# BMP-03 — 市场情报与机会雷达

```yaml
screen_id: BMP-03
status: BLOCKED
revision: 2
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-020
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
presentation_design_decision: DESIGN_READY_BOUNDED_SIGNAL_BRIEF_RETURN
presentation_reviewer: M / Codex GPT-6 Astra
presentation_reviewed_at: 2026-10-03
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-03 acceptance
```

## 0. Authority basis and artifact disposition

- Constitution basis: BMP market intelligence must be BrandFocus-first, source-aware and responsive across the approved surfaces.
- Product/workflow basis: BrandFocus → market signal → opportunity interpretation → source brief. `GLOBAL / ALL` is also a compatibility mode for the current actor-authorized China-operating directory, but a directory-level signal must carry the exact canonical actor/task scope, verified lineage and `read_allowed`.
- Exploration references: current Experience Constitution blueprint only; historical dashboards and screenshots are rejected as implementation inputs.
- Anti-template decision: the page is a momentum/confidence radar paired with a ranked signal feed and source brief, not a generic KPI wall.
- Sol design decision: `DESIGN_EXPLORATION`; full acceptance is blocked because the current builder is global/unscoped.
- M's 2026-10-03 presentation review approves the bounded reading and return behavior in §5B over already authorized typed fields. This leaves the whole-screen design/binding/acceptance state above unchanged. Review provenance is `work/m-controller-20261002/content-reading-m-decision-20261003.md`; the scope of approval is recorded here so implementation does not depend on a working artifact as a second authority.

## 1. User problem and product invariant

- **Role / context:** A BMP operator needs to identify market opportunities for one authorized BrandFocus and understand why each opportunity is present.
- **User task / completion:** inspect a ranked signal, compare momentum with confidence, and read its source-backed brief. Completion requires a same-focus signal with a valid source, time window and trace.
- **Invariant:** Subject context is not brand scope. `brand_focus_id` must match the selected focus on every visible signal.
- **Global rule:** `GLOBAL / ALL` may render real global market signals when the response and each row pass the global scope/lineage/read contract. Focused BrandFocus signals without those markers are rejected, never promoted.
- **Out of scope:** automatic recommendations, action execution, reports, provider selection, hidden source identifiers and invented scores.

## 2. Route, entry, exit and return

- **Entry:** host shell opens BMP-03 and the screen reads `GET /api/experience/screen/BMP-03` through `LumenisCoreClient.screen('BMP-03')`.
- **Required context:** verified BMP/ZBMP `FOCUS` with distinct Subject and BrandFocus IDs, applied binding and allowed read, or `GLOBAL_ALL` with explicit actor-directory read grant, canonical scope, verified lineage and `read_allowed`. The route cannot grant access.
- **Exit / return:** signal selection is local. Return restores selected signal and kind filter if the host preserves the screen; no context change or workflow write occurs.
- **Trace:** the source brief keeps the signal's source, capture time/window and item-level trace as the return anchor. A future evidence-reader route remains unbound.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime envelope and owner | Experience API adapter + BMP | `GET /api/experience/screen/BMP-03`; envelope and `truth` fields | Runtime-bound, exactly ZBMP/zbmp | Any mismatch blocks signals | BACKEND-GAP-020 | `experience_runtime.py::screen_viewmodel`; `bmp03_snapshot.dart` |
| P0 | BrandFocus/global read binding | SYSTEM context / Permission | `focus_context` + `focus_binding` | FOCUS requires exact Subject/BrandFocus; GLOBAL_ALL requires actor-directory read grant, canonical scope, verified lineage and `read_allowed` | Unknown blocks the feed | BACKEND-GAP-020 | Current `_build_bmp03()` has no verified BrandFocus/global binding |
| P1 | Market signal | BMP intelligence owner | Future `sections[type=signals|intel|opportunities].items[]`: id, optional BrandFocus, title, kind, confidence, momentum, source, evidence ref, row scope/read/lineage fields | FOCUS rows exact-match BrandFocus; GLOBAL_ALL rows require explicit actor/task scope, verified lineage and row read permission | Missing score remains unavailable; no zero fallback | BACKEND-GAP-020 | Current builder reads global intelligence assets without the required contract |
| P1 | Source brief | BMP + Shared Evidence | signal summary, source, captured time, time window, trace | Source position must explain the signal | Invalid lineage hides the signal | BACKEND-GAP-020 | `Bmp03Signal` parser preserves source fields only when safe |
| P2 | Kind filter | App presentation state | `Bmp03ViewModel` | Local filter only | Empty filter state keeps focus and source context | BMP03-UI-LOCAL | `bmp03_view_model.dart` |

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取市场情报 | None; announce busy | No previous-focus rows flash | BMP03-W-001 |
| Global / all blocked | Actor-directory scope/lineage/read contract is absent, or only focused rows are returned | 当前全局范围暂不能查看未核验市场情报 | Retry; return to context selector | Reject focused rows; do not relabel them global | BMP03-W-002 |
| Global / all ready | Authorized global binding plus valid global signals | 查看当前范围的市场机会与来源 | Kind filter; select signal | Preserve global view | BMP03-W-003 |
| Empty | Valid focused or global response with no valid signals and no rejected rows | 当前范围暂无市场机会信号 | Refresh | Keep explicit empty state | BMP03-W-004 |
| Not collected / unknown | Data state says not collected or unknown | 市场情报尚未形成可核验记录 | Refresh | Do not translate unknown to zero | BMP03-W-005 |
| Stale / partial | stale data or dropped rows | 部分市场情报仍待核验 | Refresh; read verified rows | Show data freshness wording without claiming live | BMP03-W-006 |
| Offline | Transport unavailable | 暂时无法读取市场情报，请稍后重试 | Retry | No stale unscoped feed | BMP03-W-007 |
| Blocked / denied | Missing focus/Permission/lineage, 401/403 | 当前范围暂不能查看市场情报 | Retry; return | Hide all business records | BMP03-W-008 |
| Error | Contract failure or malformed values | 市场情报暂不可用，请稍后重试 | Retry | Hide raw payload/error | BMP03-W-009 |
| Ready | Exact-match focused signals or authorized global signals | Review ranked opportunities and their source brief | Kind filter; select signal | Restore local selection | BMP03-W-010 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-03)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Primary question:** Which market signal deserves attention, and what source-backed evidence explains its confidence and momentum?
- **Composition:** a focus header, a compact radial opportunity field using confidence/momentum axes, a ranked signal feed and a right-side source brief. The radar has a list/table equivalent and is not a decorative chart.
- **Interaction:** selecting a signal updates the source brief; kind filters affect the local feed only. No signal is promoted into a decision or action.

### 5A. Web Workspace composition and desktop-only boundary

- Web shares the same screen response, parser and ViewModel. URL restoration of a selected signal is host-owned and not added here.
- No browser-only effect, export or report action is exposed.

### 5B. Approved bounded signal reading and return

- **Task hierarchy:** scan an already authorized signal's title, kind and source; select it; read the supplied source brief; return to the same filtered signal set and selected item. The first view stays concise while the selected reading area gives supplied material enough space.
- **Compact/mobile:** show the signal feed first; explicit selection enters one focused brief with an always-reachable return action. Return restores the kind filter, invoking row, browse position and keyboard focus. With large text or a short window, allow local scrolling without clipping controls or trapping focus.
- **Material semantics:** `Bmp03Signal.summary` is optional returned material. Do not label it as AI-generated, a full original article or an independently verified conclusion when method/full-body metadata is absent. Show the existing source, capture time and time window only under their actual meanings. No derived topic clustering, new source request or media preview is authorized here.
- **Metric integrity:** confidence and momentum remain distinct supplied measures. Missing or malformed momentum must not fall back to confidence, zero or an invented chart coordinate. Current `Bmp03Signal.fromJson` parses both measures independently as nullable values; unknown values remain unknown in the text and are omitted from chart coordinates. This source correction is not full-screen runtime acceptance. Keep authorized text material readable where its contract permits it.
- **Lifecycle:** filter/selection/return are local presentation actions. A new scope, denied read or changed source snapshot must not replay a previously selected signal under a different scope. No new persistence, stable ID, reader route, external source-open action or effect is introduced.
- **Brand and usability:** preserve a restrained content-first composition. Use movement only to explain entry/return; honor reduced motion. Explicit selection, status, source labels, reachable back and focus recovery carry the Nielsen requirements in this slice.

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-03)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Recompose to a ranked signal feed first, with supplied momentum/confidence labels in each row and the focused source-brief drill-in defined in §5B.
- Keep BrandFocus and time window visible. Back returns from the source brief to the feed; it never changes context.
- Use 48 px touch targets, announce filter changes, and preserve no stale signal after an interrupted read.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read signals | BMP + SYSTEM scope/Permission | Screen-specific read decision | Read only | Safe repeat | Existing trace refs | Block and retry |
| Filter / select | App presentation state | None beyond read | Local only | Reversible | None | Keep source context |
| Create recommendation / decision | No verified owner in this slice | Unknown | Not shown | N/A | None | Omitted |

## 8. Accessibility, motion and localization

- Keyboard order is focus header → kind filter → ranked feed → source brief. Enter/Space selects a signal; Escape returns from brief.
- Radar has a semantic ranked-list equivalent. Each signal announces title, kind, confidence, momentum, freshness and source in plain language.
- No decorative animation; reduced motion removes chart transitions. Confidence and momentum use text as well as position/color.
- Shared localization integration keys for `zh-CN`, `en` and `ko`: `bmp03.title`, `bmp03.focus_label`, `bmp03.kind.opportunity`, `bmp03.kind.risk`, `bmp03.kind.trend`, `bmp03.confidence_label`, `bmp03.momentum_label`, `bmp03.source_brief`, `bmp03.state.not_collected`, `bmp03.state.blocked`, `bmp03.trace_label`.
- Internal terms, raw source URLs and untrusted identifiers remain hidden from user copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP03-W-001 | Only signals matching the selected BrandFocus appear; Subject-shaped and other-focus rows are rejected | Cross-focus / compatibility isolation | All widths | Snapshot + widget | `app/test/features/bmp03/bmp03_screen_test.dart` |
| BMP03-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no signals | Global / blocked | Desktop/mobile | Snapshot + widget | `bmp03_snapshot.dart` |
| BMP03-W-003 | Return authorized global binding plus explicitly global, lineage-verified signals; render the market workspace | Global / ready | Desktop/mobile | Snapshot + widget | `bmp03_snapshot.dart`; `bmp03_screen_test.dart` |
| BMP03-W-004 | Unknown, not collected and missing numeric values remain explicit states, never zero | Unknown / not collected | All widths | Snapshot | `bmp03_snapshot.dart` |
| BMP03-W-005 | Desktop radar selection opens a source brief without internal implementation vocabulary | Ready / trace | Keyboard + pointer | Widget | `bmp03_screen_test.dart` |
| BMP03-W-006 | Mobile ranked feed and source brief recompose without overflow; hostile text is dropped | Responsive / hostile input | 1440 / 768 / 390 logical px | Widget | `bmp03_screen_test.dart` |
| BMP03-W-007 | Offline/schema failure offers retry and hides raw response | Offline / error | Desktop/mobile | Repository + widget | Core client contract; runtime remains blocked |

Real API/Permission/Evidence and runtime/E2E acceptance remain blocked because the current builder has neither the Focus nor the explicit global contract. Widget fixtures prove both-scope isolation, not production readiness.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; `DESIGN_EXPLORATION` bounded slice only.
- **Open owners:** BMP must provide Focus-scoped signal fields and definitions; SYSTEM must return actor/read binding; Shared Evidence must validate signal traces; the currently authorized frontend reviewer must review the screen composition before DESIGN_READY.
- **Required before acceptance:** live BrandFocus run, source-reader trace resolution, responsive/a11y runtime checks and random entity data acceptance.

### Bounded presentation acceptance added 2026-10-03

- Select a real authorized signal after filtering and scrolling. Read its supplied brief, then return with filter, selection, position and focus intact. Cover pointer, keyboard and mobile controls; do not require a gesture as the only return path.
- Cover a supplied summary, an absent summary and conflicting/missing metric fields. Assert no invented summary, generation method, score or source-open action; confidence must never become missing momentum.
- Check short and long briefs, narrow/short windows, 200% text and all three locales. Keep content, source and return controls reachable with local scrolling.
- Change scope and simulate a denied/failed read through the existing contracts. Old unauthorized content must not remain visible; recovery must not falsely imply a source was opened or a new result saved.
- These are pending acceptance requirements. The 2026-10-03 approval is source/spec review only; no real API, UI, business E2E or full-screen acceptance is claimed. The currently frozen editor v4 inputs remain unchanged until their safe validation boundary.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand which market opportunity matters for a selected brand and why.
- **REAL DELIVERY CARD:** real BrandFocus → scoped signal retrieval → ranked signal → source brief. Current entry lacks scoped signal retrieval, so commercial readiness is `NO`.
- **SUBJECT SCOPE / TASK DATA QUALITY IMPACT:** `GLOBAL / ALL` may expose the current task market results only through explicit actor/task scope, lineage and read markers; focused signals cannot be relabeled. Current endpoint lacks that contract, so current task-scope read acceptance remains unverified. Random sample acceptance is `NOT RUN / scoped population unavailable`.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`; current Experience Constitution and Product Core are reused, with no alternate intelligence provider or owner.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 识别需要进一步验证的机会信号。
- **屏幕专属呈现：** 置信/动量图、排序清单和来源简报并置，解释排名依据
- **来源、范围与版本连续性：** 信号ID/来源/窗口/scope/评分版本随同一Brief传给提案
- **四端差异：** Web/Desktop图、列表、简报并读；Mobile排序原因后详情；官网仅公开审定案例
- **失败与恢复：** 窗口不可比不画坐标，失效候选保留旧版并提示复核
- **补充验收：** 信号回源且不执行推荐；无owner动作不新增提案。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。


### 2026-10-08 existing candidate source reconciliation

Existing section 5B signal reading and return candidate is reconciled into current source. No missing source summary or confidence/momentum value is fabricated. Current authorization and actual scoped-signal/Evidence acceptance remain independent; this source recovery does not promote the whole-screen status.
Historical module-test rows above are preserved evidence only under the current
formal PO verification policy; they are not instructions to run those suites.

## 2026-10-18 研究能力采用接续（IN_PROGRESS / NOT_VERIFIED）

市场/平台/政策资料供研究检索，原年份/地区类型/来源/权利明确；政策关键词只提示可能相关原文，平台API描述不改变Collector能力或账号权利。

接续唯一[完整规划§1.3](../../../00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md)及[集中草图研究构图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)。当前已验证绑定及既有禁用项不由本节自动解禁；新callable由现有SourceBrief/BusinessDecisionWorkflow/Learning owner及`lumenis_app_api.py`公共注册者给出真实route/方法/输入输出后再接线，未交付保持OPEN。旧GGI API仅来源意图，不直接成为本屏客户端接口。

权限合同：服务器actor、workspace/project、任务/source/hash/父revision及当前Permission同次核验；用户填写user_id/approved_by不能授权。列表按授权→filter→pagination，避免截页后过滤假空。对象深链必须回原父任务和选区；refresh/back/forward、重复进入和乱序响应不覆盖较新工作。

状态与动作：loading不闪empty；无资料说明待补；无观测显示NO_DATA/未知；401/403不展示旧敏感内容，404不泄漏他人对象；离线/500保草稿；CAS冲突保用户编辑并提供重读/比较；cancel只停止当前任务且保已保存版本；recover需新鲜权限，不能重放审批/外部效果。来源/标题/错误按文本安全渲染，不复制旧HTML或存储型注入。成功需实际owner读回，不靠200/提示/进度条。

本地Codex/GrokBot在Web Workspace、Windows/macOS Desktop与iOS Companion分别实测适用路径；Public Website只展示核实说明与真实入口。保留原zh/en/ko、键盘/读屏、48px触控、reduced motion、原创和界面AIGC要求。每屏至少实测同scope保存/独立重开/修订，以及跨scope、陈旧版本、缺来源/权利、来源撤回、取消恢复、断网重试、重复点击与恶意文本。未构建/未运行不升级旧status或DESIGN_READY/ACCEPTED。


研究参考资料当前有界实现：I04 `match_rule_references`已接日期/地区/行业/业务/平台参数与显式未知适用性；I05 `reference_work`将场景编辑参数保存为用户声明版本，续接Task→Report→SavedWork；I06同一SavedWork当前版本/CAS/更新/撤回/恢复已接，旧引用与撤回下游被拒，102版本回归有证据；I07 `intelligence_library_api`在同一事务写签名Library RAW/REFERENCE binding并读回，失败回滚有证据。完整细节与HTTP字段见原screen合同。政策未命中不等合法、匹配不建立现行法律真相，案例期望不等观测结果；最终合并门禁与四表面用户验收仍分别待核，不能把限定测试当完整产品通过。

### 研究参考的实际版本化接口（2026-10-18最终Owner交接）

统一前缀`/api/experience/reports/source-brief`，均为序境Shared研究能力。POST `/references/match-rules`由`experience_runtime.research_match_rules`→`agent_research.reference_assets.match_rule_references`，严格body为`content`及可选`regions/industry/business/platform/as_of`；返回历史参考、日期/匹配依据与未知适用性，不提供合法/安全裁决。

GET/POST `/reference-work`由`research_reference_work`→`reference_work.list_reference_work/adopt_reference_asset`；采用body为`asset_id/request_id`及可选`edits`。GET/POST `/reference-work/<artifact_id>`由`research_reference_version`→`read_reference_work/revise_reference_work`；更新body为`request_id/expected_sha256/operation`及可选`edits`，operation为update/withdraw/restore。场景edits是用户声明的inputs/work/goal；新研究的`reference`绑定`artifact_id/sha256/work_id/version`，旧版本或撤回引用拒绝，不静默覆盖历史。场景→Task→Report→SavedWork、102版本/CAS/撤回下游拒与事务回滚已有隔离HTTP/service证据。

GET/POST `/reference-library`及GET `/reference-library/<int:evidence_id>`由`research_reference_library`→`intelligence_library_api.adopt_reference_library_asset/discover_reference_library_sources/read_reference_library_source`。POST同`asset_id/request_id/edits?`，签名binding与SavedWork同事务提交；RAW/REFERENCE、license UNKNOWN及原来源日期保留。更新/撤回使依赖旧task/report/saved result/library引用失效，新版须显式选用。前端显示版本与受影响状态、保留旧稿，禁止将102测试版本或36资料数当覆盖率或产品限制。

前端仍由本地Codex/GrokBot按原四表面职责实现并实测，以上证据未证明浏览器、桌面或iOS页面已构建。所有界面使用序境的研究/参考资料/版本/采用语义，GGI只在按需来源追溯显示。


## 2026-10-18 全项前端细化：本屏实际工作构图（待本地构建验收）

原frontmatter与真实绑定状态保持；下列完整终态不得缩成现有只读API，也不得以未接通按钮冒运行证据。仅使用服务端已准入字段/当前许可，具体接口沿本屏上文，所有新交互由本地原Owner接线。

### 来源阅读与判断层级

入口为任务“来源”与结论行引用。宽屏左侧资料目录，中间Reader原文，右侧按需来源抽屉，抽屉首屏依次为标题/原日期、来源与当前可读范围、精确页/段/时间位置、表示版本及未知项；签名/hash详细技术字段折叠。结论旁以文本区分“来源声称/整理发现/待核假设/人工决策”，不靠颜色或完整性勾选伪称事实已核。只展示实际来源→报告→显式采用关联，不画未实现的任意洞见因果图。
导入批次逐文件显示接收/解析/可读/失败，URL只有链接时写“尚未取得原文”。原来源日期与本次导入/核验时间分行；地区未知不补国家。跨范围或当前无权读取时清旧敏感预览，以“当前不可读取”替代他人对象是否存在；引用不属本任务时停止采用，保当前用户可读稿件与返回锚点。来源读失败仅折叠失败区，重新选资料不清已有材料。
Web列表/Reader按宽度并读，刷新以来源版本及精确引用位置恢复；Desktop支持原文件打开与应用Reader切换，外部程序失败留Reader；iOS先原文与高亮，再底部来源详情，返回保持段落与用户选区。官网仅用授权去敏材料展示原文与结论区别，不透出私有引用/内部ID。
界面AIGC按资料类型建议“逐份阅读/同口径对照/矛盾并读”，不生成来源真实性标签；用户可保留原排版和锁定选区。价值是能回到证据并知道结论边界，不让复杂工程字段占据主操作。
原创视觉可围绕当前选中段落构成有出处的纸层对读和引用连线，连线仅表示已知引用关系而非因果；可按任务生成适合的局部图形与层次，不复制参考站页面。用户可关闭空间效果、锁原文及采用纯文本阅读，模型不可用不阻引用定位。

### 历史参考筛选与规则相关提示

入口在SH-02资料目录“研究参考”分组及BMP-03资料抽屉。目录以市场/平台/政策/场景分栏或标签，显示7/12/14/3仅为历史种子条数，不作市场覆盖。宽屏上方一行检索与类型/地区，列表每行题名、原日期/时间口径、适用地/市场区域、权利待核；中部阅读命中片段，侧栏原来源与未知适用性。市场值必须同屏带单位/年份，平台资料不出现登录凭据或“已接通”标志。
政策“查相关参考”在当前内容旁展开输入面板：待核内容为主文本；地区、行业、业务、平台、截至日期按可选折叠字段排列。提交前展示所用日期与筛选范围，返回结果逐条给命中依据/原日期与“适用性未知”；零结果写“没有匹配到当前历史资料”，不出现“合规/安全”通行章。取消匹配不清内容或筛选；旧响应按请求版本隔离，离线/错误保输入，改日期后标旧结果待重查。
Web以可共享的非敏感筛选状态恢复目录，内容不写URL；Desktop可从当前稿选区填入待核内容并锁原选区；iOS先输入/筛选Sheet再逐条结果，来源详情单页返回原结果位置。官网说明“历史参考相关提示、须复核时效”，仅公开可授权示例，按钮进入同一资料入口。
界面AIGC可将多条匹配建议为按地区/日期对照表或长文对读，真实命中条目、日期和未知状态不可模型重写；用户可切回列表、固定列与撤销重排。价值是快速找应核资料，不提供自动法律裁决。
原创构成按用户问题选择时间带、地区分组或正文对读，节点来自真实历史条目与日期，不绘未证覆盖地图；允许局部生成解释性图标/构图并保标准控件可操作。用户锁定筛选与结果位置，缩减动效或无AI时退回同口径列表，未知适用性仍置顶。

### 场景参数编辑与研究续接

入口是参考场景“用作我的研究草稿”。宽屏左侧保原场景只读，中列为“我的声明参数”：输入/工作/目标三个分区，预算如存在必须带币种，未知数保持空值，右侧显示相对原件变化与来源版本。原示例期望和用户填写目标分开，不写已发生收益。底部主操作为“保存我的版本”，保存读回后才出现“用此版本开始研究”。Task摘要持续显示采用的具体参考版本，改稿不静默替换已提交任务引用。
取消编辑回原参考而保已存版本；未保存离开提示保存或放弃本地改动。冲突保两版差异，当前版本撤回或变更时禁止按旧引用开研究，并提供重读后明确重新采用。新任务创建失败保已存场景，重试原请求先查原Task，不重复新建。
Web同页原件/参数/差异可重排，刷新只确认已存版本；Desktop可并开场景与真实任务，文件保存由现有SavedWork；iOS按“原场景→参数表单→变更核对→已存版本”前进，键盘不遮保存与取消。官网用声明式示例演示调整目标，不把案例目标当业务证明。
界面AIGC根据用户目标建议参数分组/简洁或完整表单；不得替用户编预算、填空事实或自动开始任务，布局切换保输入与焦点。价值是复用起点但明确成为自己的可修订研究。
UI可按声明参数生成原创的“目标—约束—待研究问题”可调结构，输入变化先局部更新其对应说明，不能生成假收益曲线。原件、用户声明和保存版本为稳定层；用户可拒绝提案并固定普通表单，当前编辑值/选区与撤销栈不变。

### 研究采用、业务决策与实际复盘

研究结果“采用到当前业务”先显示目标CTH主体或BMP品牌聚焦、原Shared来源/版本、当前可用权益与将创建的领域资料；资料权利确认只在实际跨用途/范围动作发生时要求，普通导入不附加通用权利表。缺目标范围时回现有范围选择，不能临时伪造主体。确认关闭回原Shared段落，批准导入与B业务方案采用为独立步骤，各自有真实读回。
业务页宽屏左侧原研究依据，主区方案逐项比较（资源/约束/预期结果与未知并列），右侧当前决策与行动阶段。内部选择主按钮写“采用此方案”，不写“已经执行”；实际Action回执在独立阶段条，已有Task/Word/Artifact以可打开成果呈现。结果区分来源声称、实际产物、未知业务结果；评价区用当前真实口径，不把预计营收/任务完成换成增长。
复盘入口仅在真实结果记录后出现：useful/not_useful/inconclusive用“有帮助/无帮助/暂不能判断”，观察为主文本、1–8条限制和下一步保留/修订/停止依次填写，来源选择只列当前已绑定材料。取消只保草稿；保存反馈显示版本和OPERATOR_FEEDBACK性质，不显示自动因果结论。取消工作后的“恢复记录”确认说明不启动行动。复核/来源变更时页顶固定提示旧批准失效，对照新旧依据并显式重新采用；单点重试不得复活旧批准。
Web保研究→业务→结果深链与原Shared返回锚点；Desktop并读方案/来源并从真实产物打开，关闭应用后按原work revision恢复；iOS先方案摘要与约束→对照→确认→行动/结果，不合成一个“完成”绿勾。官网以去敏真实流程说明从研究到决策，不演示未发生的外部投放或增长。
界面AIGC可按目标建议比较列和结果解释顺序，金额、单位、未知、引用与审批控件仍固定真实数据；用户锁定的方案列/人工观察不被重写。价值是看清选择依据、执行证据和效果未知，必要时能修正而不丢历史。
生成式界面根据目标与真实比较字段提议原创方案对照和分阶段成果揭示，未执行区保空态文本而非庆祝动画；不同业务问题可用不同原生表/局部图解/证据阅读构成。用户冻结当前比较列，任何重新构图不改变已选择方案、金额、批准或结果。


### 全项具体工作合同：财报原件到字段核对

在原资料核对子视图增加原件格式、主体范围、原生期间、单位、字段定位、缺失原因、定点更正链与匹配待核的显示合同；原Source/Importer负责真值，前端不能把文件名/字符串匹配写成身份确认。输入变更只作新分析请求，保存需要原SavedWork读回。验证SEC/XBRL/人工与区域披露各一条已支持正常路径、同名主体、重复字段、未知币种、年报不可拆季、原件撤回、取消后重开及四端原字段返回；不存在callable保持OPEN/UNBOUND。

财报核对：顶部“主体/范围 · 期间 · 币种/单位 · 当前原件版本”；左侧已保留原件列表，中间字段核对表，右侧原文定位。表上只有“改比较范围、查看原值/更正、保存核对、用于当前分析”，非算法选择。Web窄宽用字段列表→原文抽屉；Desktop保并读与键盘下一字段；iOS先字段值与缺失原因，再逐项口径/原文和待核选择；官网仅用有证据公开例展示这一链。UI适配遇到更正/口径冲突时建议原值/更正双栏，平时收起；不改表内数值，不把内容生成算UI能力。

具体操作与恢复：在原财报资料入口选择已保留原件后，先显示识别格式、申报主体/合并范围、财政期间、币种与单位；SEC companyfacts、XBRL、人工原文标注及已支持区域披露分别标真实解析范围。主区为“字段—值/缺失—期间—口径—原件定位”核对表，右侧固定原页/原文。点一行只定位其引文；人工标注可选原文范围、字段含义与期间，另存派生记录，不改原件。未知主体通过名称/标识原文并读请求核对，候选匹配不自动合并实体。重复值/总计分部/定点更正单列，不自动加总。
财报季度选择另列原生季度、累计、半年、全年；没有完整季度不能均分造数。花费代理以刊例价、曝光及相应假设逐项显示输入出处和区间，明确不是实支。解析完成、待核对、缺失、口径冲突、来源变化、保存待读回分开；取消解析保原件与已核字段，重开回原件/字段选区。用户得到可追溯、可比较的数据而非一个自动可信分数。
OpenDART请求配置只描述公司/年/报告/报表类型与凭证是否可用；凭证未配显示待连接，不填入聊天或把配置生成称采集成功。


### 全项具体工作合同：排序、实体候选、主题、分类评价与新颖度

保持这些计算各归既有Reporting/Entity/主题Owner；展示状态包括样本不足、依赖不可用、语言不支持、训练测试分离未知、待核身份、未知分类、未见历史类别及向量版本不一致。保存是派生分析，撤销不改源档案；来源变动生成新比较。验收零试验组、并列/小样本、同名跨平台不合并、三语分报与弃答分母、主题离群、KL无穷、零向量/模型错版和取消重开。

各子任务嵌原屏：BMP-05比较表加样本/原始/收缩/区间列；BMP-02左右档案＋待核依据；BMP-03主题列表→文档与离群项；SH-05按语言的评价表和新旧分布并读。Desktop/Web保来源侧读，iOS逐项候选与同字段比较，官网仅有证例。UI自身AIGC依样本不足、身份歧义、主题离群或分布断点选择强调区域；只重排真实字段，不能把未知实体线、空主题或向量距离变成事实。

具体操作与恢复：排序结果先保每项成功数/试验数和样本不均，展示原始比率与收缩后估计/区间，并说明小样本变动；不能把排名当因果效果或真实人口覆盖。实体匹配显示左右原档案、匹配/不匹配证据、待复核候选和分离测试指标，低把握保持待核，用户审阅不自动合并Canonical身份。
主题探索以同语种实际文档集为输入，展示主题词、样本文档和离群项，词法TF-IDF/SVD不能叫神经语义理解；缺依赖或样本保原文列表。情感/立场评价按中英韩分别给保留集、混淆表/F1与弃答覆盖，不让未知混入比例。新颖度面并读当前/历史类别分布和相同模型版本向量距离；新类别导致无穷散度要直接说明，不能截成漂亮有限分；距离不当语义原创或商业价值证明。


### 全项具体工作合同：有分母的比例、声量、情感、问卷与销售份额

必须显示真实分母和NO_DATA；统计置信、样本代表性、原始值真实性分开。修改筛选只改变新分析，不覆盖旧结论。验收零分母、0成功、有未知标签、SOV重叠提及、重复问卷ID/缺答、非推荐问题、同口径销售缺失/币种错配、取消/重开。缺业务输入仍保允许来源阅读，不能要求用户选Wilson/NPS计算器。

指标解释在主值旁常驻“多少/总共多少 · 窗口 · 覆盖”；展开后同源计数表/区间及排除原因。问卷结果用0–10响应分布＋三组计数＋缺答，净情感用标签计数＋未知，销售份额用分子/市场总量与口径表。Desktop/Web可固定两种指标并看，iOS逐项解释和可访问计数表；官网案例直写观察范围。UI按计数/问卷/金额选择语义准确的图表，未知保留文字空态；不把无数据补0，不用光影暗示置信。

具体操作与恢复：指标以业务问题进入，先呈分子、分母、计数规则、时间/地区/平台和缺失量。负面率或转化率按明确可比试验计数显示Wilson区间，重复事件不能偷换独立试验；区间不修复选择偏差。声量份额只针对互斥已观察提及总量，范围缺口与平台覆盖常驻，不命名总体市场份额。
净情感用已知正/中/负标签作分母并单列未知数；推荐调查必须有真实0–10“愿意推荐”问卷定义、调查/样本范围和响应，推荐者/中立者/贬损者及缺答分别列，不能从情感推NPS。销售份额只读用户提供的同口径销售金额或件数：主体、市场定义、地区、品类、期间、币种/单位并读；缺总额、分子大于总额、货币或定义不一致不计算。两类份额和两类态度结果可并读但不能揉成总分。

### 便利操作合同：CV05 从错误直达可修字段，保留其余工作

适用工作与省步目标：研究任务编辑、业务选项采用、创作版本与配置表单；不可撤外部效果不归一般表单重试。

原Owner与真实接口边界：source-brief/tasks/<id> PATCH以expected_revision+changes改可编辑稿；POST cancel/restore及resume由任务实际状态约束。business-works/<id>/<operation>沿choose/adopt/action/outcome等原Owner；没有字段级错误定位返回时前端按已知校验schema定位，未知错误保完整提示，后端字段path补充须另验。

控件位置与四表面操作：原工作面错误摘要可点击定位对应输入，修正后预览影响和过期结果；Web/桌面保其他栏内容，iOS聚焦字段且不遮键盘，官网仅提交表单/演示应用相同恢复原则。省掉回首页重建、重填已正确字段。

持久化、权限与错误恢复：只重试原Owner允许的失败对象；外部UNKNOWN先核回执。点击取消先显示请求中/等待安全边界，收到实际终态才显示停止；restore回可审状态，不暗自执行或复用已失效批准。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。
