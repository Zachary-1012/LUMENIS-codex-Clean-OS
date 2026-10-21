# BMP-04 — 品牌传播路径

## 2026-10-11 品牌分析结果优先；复用后端计算与来源合同

在真实 BMP/BrandFocus 或明确 GLOBAL 范围选择问题、市场、时间和比较对象，后端完成实际可比的传播/竞品分析与适用计算，返回有结论、来源、样本口径、不确定性和后续业务动作的结果。复用 SourceBrief 的资料与覆盖字段，但不把样本计数当品牌洞察；不得暗用 CTH Subject，亦不能从互动数虚构销售或全市场热度。

AI 增强解读、洞察与方案建议，基础计算、人工判断、Campaign 及报告保存/修订/重开/恢复不依赖模型。默认不向用户展示论文 operation、对数权重或内部任务拼装；真实业务约束可编辑、方法和参数来源可追溯。此为当前规格纠偏，非界面修复或业务验收；本段不声明窗口状态。

```yaml
screen_id: BMP-04
status: BLOCKED
revision: 1
owner_domain: BMP
binding_ids:
  - BACKEND-GAP-021
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
artifact_disposition: BOUNDED_IMPLEMENTATION_WITH_SCOPE_GUARD
reviewer: Codex bounded ROUND-12 Luna batch
reviewed_at: 2026-09-22
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not BMP-04 acceptance
```

## 0. Authority basis and artifact disposition

- Constitution basis: BMP propagation is a brand/market workflow and must preserve source-backed metric definitions, comparable windows and honest missing states.
- Product/workflow basis: channel → content → exposure → response / conversion. A raw dashboard total is not a propagation path.
- Exploration references: current Experience Constitution blueprint only; generic funnel screenshots and legacy dashboards are rejected.
- Anti-template decision: the screen uses a propagation river and channel matrix with a selected channel, not a generic KPI wall.
- Sol design decision: `DESIGN_EXPLORATION`; full acceptance remains unverified; the current backend has scoped source observations, while complete stage/model projection and App E2E remain separate.

## 1. User problem and product invariant

- **Role / context:** A BMP operator traces how a selected BrandFocus moves through channels toward response or conversion.
- **User task / completion:** compare channels over a declared window, inspect the path stages and understand which measures are observed versus unavailable. Completion requires a per-channel source, trace, unit, definition and comparable window.
- **Invariant:** BrandFocus is a distinct BMP scope. The screen must not use a Subject ID, global dashboard or missing value as a brand attribution.
- **Global rule:** `GLOBAL / ALL` is the default global universe for propagation when the response and every channel row carry explicit canonical global scope, verified lineage and `read_allowed`. Focused BrandFocus rows without those markers are rejected, never promoted.
- **Out of scope:** publishing, campaign edits, attribution claims beyond returned fields, audience identity, external effects and fabricated reach.

## 2. Route, entry, exit and return

- **Entry:** host shell opens BMP-04; read is `GET /api/experience/screen/BMP-04` through `LumenisCoreClient.screen('BMP-04')`.
- **Required context:** verified BMP/ZBMP `FOCUS`, distinct Subject and BrandFocus IDs, applied binding and allowed read, or `GLOBAL_ALL` with explicit global grant, canonical scope, verified lineage and `read_allowed`.
- **Exit / return:** channel selection is local presentation state. Back returns from channel detail to the river and restores the selected channel/window filter when possible.
- **Trace:** stage metrics preserve source, evidence trace, definition and window. No write, attribution recalculation or new Evidence is created.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime envelope and owner | Experience API adapter + BMP | `GET /api/experience/screen/BMP-04`; envelope and `truth` | Runtime-bound ZBMP/zbmp response | Mismatch blocks all flow rows | BACKEND-GAP-021 | `experience_runtime.py::screen_viewmodel`; `bmp04_snapshot.dart` |
| P0 | Focus/global read binding | SYSTEM context / Permission | `focus_context` + `focus_binding` | FOCUS exact Subject/BrandFocus; GLOBAL_ALL explicit global grant/canonical scope/verified lineage/read permission | Unknown blocks channel data | BACKEND-GAP-021 | Current _build_bmp04(binding) returns verified focus/global binding; App consumption remains separately tested |
| P1 | Propagation channel | BMP propagation owner | Future `sections[type=channels|propagation].items[]` with channel, optional BrandFocus, stage metrics, source, trace, row scope/read/lineage fields | FOCUS exact BrandFocus; GLOBAL_ALL requires explicit global scope, verified lineage and row read permission; every metric includes value, unit, definition and comparable window | Missing metric remains unavailable; direct untyped numbers are rejected | BACKEND-GAP-021 | Current `brand_propagation` output is unscoped and lacks the required contract |
| P1 | Stage relation | BMP canonical content/metric owner | channel/content/exposure/response/conversion stage fields | Path order must be explicit; no unsupported reach/conversion derivation | Partial paths show only observed stages | BACKEND-GAP-021 | `Bmp04Channel` parser is strict by design |
| P2 | Channel selector | App presentation state | `Bmp04ViewModel` local selection | No server mutation | Empty selection shows all verified channels | BMP04-UI-LOCAL | `bmp04_view_model.dart` |

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取品牌传播路径 | None; announce busy | Do not flash prior-focus metrics | BMP04-W-001 |
| Global / all blocked | Global grant/lineage/read contract is absent, or only focused rows are returned | 当前全局范围暂不能查看未核验传播路径 | Retry; return to context selector | Reject focused rows; do not relabel them global | BMP04-W-002 |
| Global / all ready | Authorized global binding plus valid global channels | 查看全球传播路径与可比窗口 | Select channel | Preserve global view | BMP04-W-003 |
| Empty | Valid focus or global scope but no verified channel | 当前范围暂无传播路径资料 | Refresh | Keep stage labels but no invented totals | BMP04-W-004 |
| Not collected / unknown | No channel collection or unknown state | 传播资料尚未采集完成 | Refresh | No zero or blank-as-zero display | BMP04-W-005 |
| Stale / partial | Stale window or missing stages | 部分传播阶段仍待核验 | Refresh; inspect observed stages | Mark unavailable stages explicitly | BMP04-W-006 |
| Offline | Transport unavailable | 暂时无法读取传播路径，请稍后重试 | Retry | No unscoped cached dashboard | BMP04-W-007 |
| Blocked / denied | Missing focus/read/lineage or 401/403 | 当前范围暂不能查看传播路径 | Retry; return | Hide all business metrics | BMP04-W-008 |
| Error | Malformed response or unsafe metric | 传播路径暂不可用，请稍后重试 | Retry | Hide raw payload | BMP04-W-009 |
| Ready | Exact-match focused channels or authorized global channels | Compare channel propagation over the same window | Select channel | Restore local channel selection | BMP04-W-010 |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- **Primary question:** Where does the selected brand's propagation path strengthen or stop, and what is actually observed?
- **Composition:** a focus/window header, a left-to-right propagation river for channel → content → exposure → response/conversion, and a channel matrix with definitions/windows. A selected channel detail panel explains unavailable stages rather than collapsing them to zero.
- **Interaction:** selecting a channel highlights its path and matrix row; no channel edit or attribution action is enabled.

### 5A. Web Workspace composition and desktop-only boundary

- Web shares the same read contract and presentation semantics. No browser-only export, campaign action or attribution operation is added.
- Host routing owns URL restoration; local selection is the only bounded state.

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Keep BrandFocus and comparison window in view. Back returns to the channel selector.
- Each stage row is touch-safe and announces when a stage is observed, unavailable, stale or not collected. No cached unscoped metrics survive an interruption.

## 7. Actions, authorization and effects

| Action | Server-side owner and actor/scope | Permission operation | Read / write / external effect | Idempotency / reversal | Evidence emitted | Failure behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Read propagation | BMP + SYSTEM context/Permission | Screen-specific read decision | Read only | Safe repeat | Existing source/trace refs | Block and retry |
| Select channel | App presentation state | None beyond read | Local only | Reversible | None | Keep focus and window |
| Change attribution / publish | No verified owner or effect contract | Unknown | Not shown | N/A | None | Omitted |

## 8. Accessibility, motion and localization

- Keyboard order is focus/window context → channel selector → river stages → matrix/detail. Selection is available by Enter/Space; focus remains visible.
- The river has a sequential table/list equivalent. Each stage announces metric value only when its unit, definition and window are present; otherwise announces unavailable/not collected.
- No decorative flow animation is required; reduced motion disables transitions. Stage meaning is not encoded by color alone.
- Shared localization integration keys for `zh-CN`, `en` and `ko`: `bmp04.title`, `bmp04.focus_label`, `bmp04.stage.channel`, `bmp04.stage.content`, `bmp04.stage.exposure`, `bmp04.stage.response`, `bmp04.stage.conversion`, `bmp04.window_label`, `bmp04.definition_label`, `bmp04.state.not_collected`, `bmp04.state.blocked`.
- Internal owner/path/provider/database vocabulary and raw errors never enter visible copy.

## 9. Executable acceptance

| Acceptance ID | User action and expected result | State / error path | Platform / input | Test layer | Current evidence / reference |
| --- | --- | --- | --- | --- | --- |
| BMP04-W-001 | Only channels matching the selected BrandFocus are available; foreign/Subject rows are rejected | Cross-focus isolation | All widths | Snapshot + widget | `app/test/features/bmp04/bmp04_screen_test.dart` |
| BMP04-W-002 | Return `GLOBAL_ALL` with focused rows or missing global binding; show blocked scope state and render no propagation metrics | Global / blocked | Desktop/mobile | Snapshot + widget | `bmp04_snapshot.dart` |
| BMP04-W-003 | Return authorized global binding plus explicitly global, lineage-verified channels; render the propagation workspace | Global / ready | Desktop/mobile | Snapshot + widget | `bmp04_snapshot.dart`; `bmp04_screen_test.dart` |
| BMP04-W-004 | Direct numbers without metric definitions/windows are rejected; missing stages stay unavailable | Partial / missing | All widths | Snapshot | `bmp04_snapshot.dart` |
| BMP04-W-005 | Desktop river and channel matrix expose comparable windows and source-backed detail | Ready / trace | Pointer + keyboard | Widget | `bmp04_screen_test.dart` |
| BMP04-W-006 | Mobile vertical funnel and selector remain usable without overflow and distinguish exposure from response | Responsive / accessibility | 1440 / 768 / 390 logical px | Widget | `bmp04_screen_test.dart` |
| BMP04-W-007 | Offline/schema failure offers retry without raw response or zero fallback | Offline / error | Desktop/mobile | Repository + widget | Core client contract; runtime remains blocked |

The real propagation API/Permission/Evidence and runtime/E2E gate is not passed by these widget fixtures; the current _build_bmp04(binding) reads read_scoped_propagation and returns focus/global_binding, observation_read_binding and source_observations; analysis_state=NOT_COMPUTED explicitly separates authorized original observations from uncomputed propagation/model analysis. Current backend binding does not prove widget/runtime field compatibility or E2E.

## 10. Review decision and open questions

- **Decision:** `BLOCKED` for full acceptance; bounded implementation remains `DESIGN_EXPLORATION`.
- **Open owners:** BMP must define stage and metric semantics; SYSTEM must return verified context/read; Shared Evidence must validate channel traces; Sol must review the river/table composition.
- **Required before acceptance:** live comparable-window data, random entity checks, runtime responsive/a11y proof and explicit rollback/observability for any future attribution capability.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand how a selected brand's content propagates through channels and where observed response begins or remains unknown.
- **REAL DELIVERY CARD:** real BrandFocus/window → scoped channel read → stage-by-stage propagation result → source-backed detail. Current backend scoped observation entry exists; complete stage result/source-backed interaction and App E2E remain unverified, so commercial readiness is `NO`.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** `GLOBAL / ALL` may show the global propagation universe only through explicit global scope/lineage/read markers; focused rows cannot become global propagation. Current endpoint supplies scoped observations, not complete analyzed channels; stage-analysis coverage and full random-sample App acceptance remain NOT RUN. Do not turn analysis_state=NOT_COMPUTED into a completed propagation graph.
- **CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION:** `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE`; the bounded slice reuses current contracts and adds no parallel attribution engine or provider.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 看品牌传播链哪些阶段实际有观测。
- **屏幕专属呈现：** 左到右渠道路径与定义矩阵，每阶段区分observed/unavailable
- **来源、范围与版本连续性：** 渠道、单位、来源、时间和品牌范围绑定；选中渠道不改归因事实
- **四端差异：** Web/Desktop河流和矩阵；Mobile逐阶段下钻；官网不呈私有数据
- **失败与恢复：** 缺阶段不为零、不同比较窗不合并；scope变化清旧缓存
- **补充验收：** 同窗口切换渠道可回位；不从相关性宣称因果。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

## 2026-10-18 研究能力采用接续（IN_PROGRESS / NOT_VERIFIED）

研究成果采用需真实BMP Primary Focus及当前权限；比较多方案、保预算/未知，内部选择、行动读回、实际结果和评价分步显示，预期收益不能变observed。

接续唯一[完整规划§1.3](../../../00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md)及[集中草图研究构图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)。当前已验证绑定及既有禁用项不由本节自动解禁；新callable由现有SourceBrief/BusinessDecisionWorkflow/Learning owner及`lumenis_app_api.py`公共注册者给出真实route/方法/输入输出后再接线，未交付保持OPEN。旧GGI API仅来源意图，不直接成为本屏客户端接口。

权限合同：服务器actor、workspace/project、任务/source/hash/父revision及当前Permission同次核验；用户填写user_id/approved_by不能授权。列表按授权→filter→pagination，避免截页后过滤假空。对象深链必须回原父任务和选区；refresh/back/forward、重复进入和乱序响应不覆盖较新工作。

状态与动作：loading不闪empty；无资料说明待补；无观测显示NO_DATA/未知；401/403不展示旧敏感内容，404不泄漏他人对象；离线/500保草稿；CAS冲突保用户编辑并提供重读/比较；cancel只停止当前任务且保已保存版本；recover需新鲜权限，不能重放审批/外部效果。来源/标题/错误按文本安全渲染，不复制旧HTML或存储型注入。成功需实际owner读回，不靠200/提示/进度条。

本地Codex/GrokBot在Web Workspace、Windows/macOS Desktop与iOS Companion分别实测适用路径；Public Website只展示核实说明与真实入口。保留原zh/en/ko、键盘/读屏、48px触控、reduced motion、原创和界面AIGC要求。每屏至少实测同scope保存/独立重开/修订，以及跨scope、陈旧版本、缺来源/权利、来源撤回、取消恢复、断网重试、重复点击与恶意文本。未构建/未运行不升级旧status或DESIGN_READY/ACCEPTED。


### 已交付业务服务字段接线（2026-10-18，有界源码证据）

公共入口维持POST `/api/experience/business-works`、GET `/api/experience/business-works/<work_id>`及POST `/api/experience/business-works/<work_id>/<operation>`；变更继续提交`submission_id/payload/expected_revision`，服务为`BusinessDecisionWorkflow.prepare/reopen/advance`。已新增`review`与`restore`意图：`restore`仅CANCELLED+非空reason，恢复记录不重启外部行动；`review`要求OUTCOME_RECORDED，assessment为useful/not_useful/inconclusive，observations非空，limitations为1..8条，next_step为retain/revise/stop，source_ids为非空且已绑定的唯一ID集合。未知/额外身份字段拒绝。

显示服务端`selected_by`，与用户可编辑责任人owner分开。`operator_review`包含reviewer、reviewed_revision、outcome_revision、outcome_state、assessment、observations、limitations、next_step、source_ids；`claim_type=OPERATOR_FEEDBACK`及`metric_value=null`必须保留，意见不画成增长分数。Shared→真实CTH/BMP资料再准入、原文SourceUse与父源撤销、业务feedback→learning已有固定版本隔离HTTP证据；本节不将这些有界证据升级成完整UI/业务效果验收。

### Shared原源到真实业务域的明确采用

POST `/api/experience/reports/source-brief/adopt-source`由`experience_runtime.adopt_research_source`→`lumenis.importer.documents.adopt_shared_research_source`，严格body为`job_id/source_id/provenance/mode`，mode为prepare/import，目标使用真实focused CTH/BMP headers。provenance需明确owner-approved rights_statement；prepare返回原Permission精确DATA_IMPORT resource，import须匹配批准。原Shared report/hash/附件字节成为live dependency，每次原Evidence读取重新核权；原源撤回或删除拒绝重开/重放，不能借已签报告绕过权益。

两域实际Shared上传→研究→明确权益→精确批准导入→domain SourceBrief→B prepare/reopen及父源撤销反例已有固定依赖版本隔离HTTP证据。`BusinessDecisionWorkflow.read_learning_material`只向C提供精确revision、已记录评价/operator_review及新鲜原源权限，不声称业务增长或因果。前端以“采用到当前业务范围”解释，并保原Shared返回锚点、来源版本和明确确认；本地页面尚需构建/验收。


## 2026-10-18 全项前端细化：本屏实际工作构图（待本地构建验收）

原frontmatter与真实绑定状态保持；下列完整终态不得缩成现有只读API，也不得以未接通按钮冒运行证据。仅使用服务端已准入字段/当前许可，具体接口沿本屏上文，所有新交互由本地原Owner接线。

### 研究采用、业务决策与实际复盘

研究结果“采用到当前业务”先显示目标CTH主体或BMP品牌聚焦、原Shared来源/版本、当前可用权益与将创建的领域资料；资料权利确认只在实际跨用途/范围动作发生时要求，普通导入不附加通用权利表。缺目标范围时回现有范围选择，不能临时伪造主体。确认关闭回原Shared段落，批准导入与B业务方案采用为独立步骤，各自有真实读回。
业务页宽屏左侧原研究依据，主区方案逐项比较（资源/约束/预期结果与未知并列），右侧当前决策与行动阶段。内部选择主按钮写“采用此方案”，不写“已经执行”；实际Action回执在独立阶段条，已有Task/Word/Artifact以可打开成果呈现。结果区分来源声称、实际产物、未知业务结果；评价区用当前真实口径，不把预计营收/任务完成换成增长。
复盘入口仅在真实结果记录后出现：useful/not_useful/inconclusive用“有帮助/无帮助/暂不能判断”，观察为主文本、1–8条限制和下一步保留/修订/停止依次填写，来源选择只列当前已绑定材料。取消只保草稿；保存反馈显示版本和OPERATOR_FEEDBACK性质，不显示自动因果结论。取消工作后的“恢复记录”确认说明不启动行动。复核/来源变更时页顶固定提示旧批准失效，对照新旧依据并显式重新采用；单点重试不得复活旧批准。
Web保研究→业务→结果深链与原Shared返回锚点；Desktop并读方案/来源并从真实产物打开，关闭应用后按原work revision恢复；iOS先方案摘要与约束→对照→确认→行动/结果，不合成一个“完成”绿勾。官网以去敏真实流程说明从研究到决策，不演示未发生的外部投放或增长。
界面AIGC可按目标建议比较列和结果解释顺序，金额、单位、未知、引用与审批控件仍固定真实数据；用户锁定的方案列/人工观察不被重写。价值是看清选择依据、执行证据和效果未知，必要时能修正而不丢历史。
生成式界面根据目标与真实比较字段提议原创方案对照和分阶段成果揭示，未执行区保空态文本而非庆祝动画；不同业务问题可用不同原生表/局部图解/证据阅读构成。用户冻结当前比较列，任何重新构图不改变已选择方案、金额、批准或结果。


## 2026-10-18 完整工作面细化：迁移、业务与内容模式

保留原状态/Owner/接口和完整终态；本文补足视觉交互，不宣称已接通或已验收。

### 合作草稿、执行批准与不明结果

从作者/活动的“建立合作草稿”进入现有业务对象，不自动创建投放。宽屏主区是可编辑目标/资源/范围/动作草稿，右侧版本与将受影响对象；下方用分开的“草稿→请求审阅→已批准→执行回执”阶段行。批准确认显示当前精确请求摘要、对象、动作、范围与版本；撤销批准为独立动作。用户看得到批准不是执行，不把客户端布尔值、legacy解锁cookie或页面隐藏当服务端Permission。
仅已注册且当前可用渠道才显示合法执行入口；未配置写“尚无可用执行渠道”，仍能保存方案。提交后由Owner读回真实执行与receipt；超时未知提示“结果待核”，提供核原请求回执和返回草稿，不自动重新发送。取消请求、撤销批准、停止当前动作分别说明效果边界，已产生的外部结果不被删除。旧scope/来源/请求变更使旧批准失效，重新预览批准；失败保原稿与历史，不显示空成功。
Web恢复原工作和请求版本，刷新不会执行；Windows/macOS窗口重开先核原执行回执，后台Core状态另示；iOS先草稿摘要→精确批准Sheet→结果页，实际禁止的执行动作保持说明并返回已存任务，既有合法审阅不因窄屏丢失。官网演示草稿/批准/真实执行的区别，不将未绑定渠道做动效假演示。界面AIGC可按任务建议行动摘要/资源比较顺序，批准与执行控制独立固定、不能生成或替点确认；用户锁定的草稿不被覆盖。价值是减少误批、误发与重复外部效果。


### 全项具体工作合同：传播网络、Hawkes/Bass与MMM

将Hawkes/Bass点估计、网络中心性、MMM非因果限定作为必显语义，不由通用“置信”字段代填。依赖未安装/样本不足/拟合失败/诊断缺失与来源版本分开。取消保输入；重开不重新训练，预算另算绑定同源版本。验收无边、HITS非唯一、少于30观察、重复时刻、无变化渠道、季度不连续/年拆季拒绝、宏观地区/截止不符、诊断NaN、依赖不可用和恢复。

传播主区“真实边图/同源边表”并列，时间模型在独立页签用观测点＋拟合线＋分期标志；方法抽屉标点估计与缺区间。MMM沿BMP-09上方数据覆盖条、中部渠道贡献/情景对比、右侧诊断与来源；区间只画Owner真实返回者。iOS先缺口/结论→同源表→方法，Desktop/Web保并读；官网只展示有证边与适用范围。UI适配在网络、时间、季度比较三种原生视图中按已存在数据提出布局，不补边、补期或臆造ROI。

具体操作与恢复：传播检查把真实观察关系与时间模型分开。图只列转发/提及/合作的已观察边，节点表同时列中心性和边覆盖；HITS无法唯一识别就显示该项不足，不使整张图失真。时间面选择事件窗/时间单位或累计采用序列，先看观测与前半训练/后半回测及简单基线，样本少、重复时刻或非单调累计明确阻断。当前Hawkes/Bass有限实现仅点估计，未量化的参数/预测不确定性不得画成区间或“预测必然峰值”。
MMM主面先核原季度、申报主体/合并范围、币种、渠道真实花费或代理、结果单位与宏观来源；给训练/留出覆盖、共线/常量渠道/依赖状态，再呈渠道贡献及预算情景。诊断不通过时隐藏看似可靠的优化结论，保诊断和输入；无因果ROI证据明确NOT_ESTABLISHED。预算变化仅计算场景，不能付款或发布。

### 原G106具体终态合同：平台原生信号与改写依据

选定创意/内容版本后，原生信号面逐行列停留、完播、重看、私发转发、评论、收藏、点赞的值/单位/期间/分母/可得状态和来源。指标优先是原方法语境，不自动变跨平台统一权重；不可得不补0。ROI区域单列成本、实际收益、归因范围及缺项，不能由点赞计算。打开“据此改写”返回该平台可编辑草稿，保事实母版并显示钩子/结构/时长/包装改变理由。

构图：左内容与平台版本，中间同字段信号表，右原生来源与改写差异；ROI与互动反馈不同区域。iOS逐平台同字段切换，不用同一柱高冒同尺度。

平台字段缺失、定义不可比、费用/收益不足、数据过期各保文字；取消保原稿，重开原信号版本，采用改写只改该平台候选，不自动发布或恢复外部权限。

Public Website仅用获准真实样例说明平台原生信号与改写依据及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按可比字段优先安排证据列，用户锁列/简洁/撤销；不造指标或把版式重排当商业回报。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。


### 2026-10-21 交互源码吸收：开发前行为边界

材料为独立审核包 `src/propagation-review.mjs` / `propagation-study.mjs`，按当前 `app/lib/features/bmp04/` Owner吸收传播阅读机制，不移植fixture数据或fixture授权。渠道→内容→曝光→响应的关系必须分清收录、来源统计对应、同窗记录；同窗绝不自动成为转化或归因。数值绑定真实brand/subject/market、source/version、单位定义、时间窗及分母；来源撤回、跨窗、不同比例分母、未知曝光不能补零或强算漏斗。

行/阶段点击打开原依据后回原筛选位置；视图/导出同版，撤权清旧内容。验收使用真实Owner记录覆盖缺分母、人数与次数不可比、不同窗、来源换版和缺边；审核包明确人工三渠道不得进入生产样例基线。此为开发前合同补全，未改变本屏实现或验收状态。
