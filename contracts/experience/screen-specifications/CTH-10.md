# CTH-10 — 报告与运营简报工作台

## 2026-10-11 业务报告优先；数学与分析归后端

用户选择业务范围、期间和要解决的问题，打开的是已有结果或提交正常报告任务。后端 CTH/Shared 选用有真实输入与适用假设的方法，交付包含结论、证据、指标/比较、限制和行动建议的报告；来源样本统计只作为覆盖说明，不是报告本身。缺失资料仅限制相应结论，不阻断其他可完成部分。

默认界面不得要求用户挑论文/operation、输入对数权重、粘贴内部 Task ID 或先跑数学情景才能取得报告。业务预算/资源/约束可编辑；计算方法、参数来源、样本和误差可展开核对。AI 可辅助解释与写作，但无 AI 时确定性分析、人工判断、报告编辑及保存/修订/重开/恢复必须可用。

来源详情按 Experience 的真实资料呈现，并支持 Trace → Open Original（默认在产品内 SYS-06 打开实际网页；外部浏览器只作用户可选的查看原文跳转，不采集）→ Return。不能把改规则或隐藏入口当作后端分析已完成。当前前端纠偏尚未实现/验收；本屏完整出口保持 OPEN。

```yaml
screen_id: CTH-10
status: BLOCKED
revision: 3
owner_domain: CTH / Shared Capability Reporting
binding_ids:
  - BACKEND-GAP-017
product_owner_approval: M_BOUNDED_SOURCE_BRIEF_INCREMENT_2026_10_02
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
design_ready_scope: SOURCE_BRIEF_START_STATUS_RESUME_JOB_READBACK_ONLY
artifact_disposition: BOUNDED_SOURCE_BRIEF_INCREMENT_FULL_SCREEN_BLOCKED
reviewer: M / Sol / 序境12
reviewed_at: 2026-10-02
approval_reference: M approved the bounded SourceBrief increment on 2026-10-02; period, weekly report, export and owned business quality remain BLOCKED; no ACCEPTED claim
```

## 1. User problem and product invariant

- **Role / context:** CTH operator in `GLOBAL / ALL` or an authorized focused CTH Subject.
- **User task:** choose a verified period, inspect a report/brief as a paged artifact, follow each conclusion to its source trail, and understand the methodology and action/outcome status before any export.
- **Completion signal for this bounded slice:** start a scoped source brief, inspect actual task state, then reopen the saved Job with its verified source list. This is not completion of a period/weekly business report.
- **Invariant:** a report is not a screenshot of a dashboard. The storyboard keeps narrative, methodology, source trail and action/outcome implications separate.
- **Current limitation:** the legacy `_build_cth10()` aggregate remains unsuitable as scoped report data. Existing SourceBrief task/job APIs provide a separate actor- and scope-checked incremental binding; period/weekly/export and owned business quality remain unclosed.

## 2. Route, entry and return

- **Entry:** nested CTH reporting workflow from the CTH work surface or a completed Case/Decision trace. Shared shell routing is outside this batch.
- **Required read binding:** legacy report payload still requires valid context plus `binding.actor_scope=verified`, matching `context_mode`, `domain=CTH`, `evidence_lineage=verified`, and report-level `scope_verified=true`. SourceBrief instead uses the exact task/job contract below, with server-issued principal, exact registered scope and verified source snapshot. Focus mode must echo `subject_id`.
- **Exit / Trace / Return:** select a report section or source locally; Return restores the storyboard page and selected source. No report write, export, file creation or share effect is enabled.

## 3. Verified data and callable bindings

| Priority | UI field / action | Source / callable | Definition and missing behavior | Binding |
| --- | --- | --- | --- | --- |
| P0 | Report catalog | Existing CTH/Shared Reporting owner | Requires `reports[]` with stable ID, period, state and scope; no cross-scope rows | `BACKEND-GAP-017`, currently unscoped |
| P0 | Brief storyboard / preview | Same report owner | Requires narrative blocks with definition/window and status; do not invent numbers or conclusions | Unknown until scoped report contract exists |
| P0 | Source trail | Shared Evidence owner | Each displayed reference must be trusted and related to the selected report | Current query has no actor/Subject/origin filtering |
| DRAFT | Generate weekly brief | `report:write` | No backend result contract in this batch | Disabled |
| EXPORT | Export PDF/Excel | `report:export` plus permission/effect/audit result | No real report export endpoint is bound | Disabled |

Source references are admitted by actual Canonical source identity, exact scope,
source snapshot integrity and matching `evidence_id` / `scope_evidence_ref` checked
by the existing reporting/Evidence owners. There is no fixed frontend EV-ID
allowlist. `canonical_ref` does not imply a valid `source_id`. Unknown, foreign,
malformed, hostile or unverified references remain withheld; replacing the old
fixture allowlist does not relax their rejection.

### 3.1 M-approved SourceBrief increment — 2026-10-02

The full screen remains `BLOCKED`. Only this increment is `DESIGN_READY`, approved
by M=序境12 under the sole Experience Constitution, for F implementation and W6
integration. These APIs already exist at source base `a85c35ee619ae75052f91b3b924e467bd8bc1622`;
source existence does not establish runtime or screen acceptance.

| Action | Exact existing API | Field/state and effect contract |
| --- | --- | --- |
| Generate source brief | `POST /api/experience/reports/source-brief/start` | JSON `limit` (1–100), optional `source_ids`, `business_question` (4–1500 characters), `image_source_ref`; server validates actor/scope and source IDs. A `revision` request is inherited parent input only and is outside this incremental UI action. HTTP 202 is task admission. |
| Inspect task | `GET /api/experience/reports/source-brief/tasks/<task_id>` | Envelope `task`; keep `task_id` and `job_id` distinct. `pending/running/succeeded/failed/interrupted` are actual execution states. |
| Resume interrupted task | `POST /api/experience/reports/source-brief/tasks/<task_id>/resume` | Body exactly `{}`; a new request revalidates current principal, exact scope, Permission and effect boundary before execution/commit. HTTP 202 remains admission. |
| Reopen saved result | `GET /api/experience/reports/source-brief/jobs/<job_id>` | Envelope `result`; canonical `daily_reports` readback rechecks actor, scope, source selection, Evidence and hashes. Never substitute an in-memory request or the legacy aggregate. |
| Save as editable research | `POST /api/experience/reports/source-brief/jobs/<job_id>/save` | Body exactly `{request_id,title}`. The server reopens the job under the current actor/scope and generates the SavedWork text, source reference and payload. The client reuses one request ID for uncertain retries and accepts success only after exact artifact/version/scope linkage and a separate SavedWork readback. |
| Reopen saved research | `GET /api/experience/saved-work/<artifact_id>` | Reopens the committed `research` artifact through the existing SavedWork reader with the same CTH/BMP context. Verify artifact ID/hash, title, request ID, source job/hash and scope before showing the saved text. Permission or source-reference failure remains an explicit unavailable state. |

CoreClient sends `X-Domain-Id: CTH`, `X-Product-Id: CTH` and explicit
`X-Lumenis-Context-Mode: GLOBAL_ALL/FOCUS`; focused requests have the exact
`X-Subject-ID`, and GLOBAL requests have no Subject/BrandFocus selector. Headers
select context; they do not grant Permission. The Core resolves the sealed local
workspace principal or authenticated actor, canonical registry and module `reports`
read/write scope, then requires `REPORT_GENERATE` Permission/effect/audit before
task admission, execution and artifact commit.

Saving is an explicit user action after a verified SourceBrief result. The
client sends no markdown, actor identity, citations or scope override: the
existing save route derives the research document from the immutable job and
its current source/review state. It then independently reopens the SavedWork
artifact under the same context. A newly saved result is editable through the
existing SavedWork revision contract; this does not mutate or append to the
immutable SourceBrief job. The interface reports a save only after both the
save receipt and the independent readback agree.

On success, read `job_state`, `artifact_outcome`, `source_brief.records`,
`business_analysis.state`, `operator_review`, `evaluation` and `review_status`
independently. `job_state=completed` plus
`artifact_outcome=persisted_and_reopened_verified` proves the source brief was
saved/reopened at its `report_id/artifact_hash/source_count`; it does not prove
business analysis or quality approval. `review_status=HUMAN_PENDING` remains
pending. Current owned inference is not service-bound; do not label unavailable
analysis successful. No period or export is supplied by this increment, and
`publish_status=not_performed` never becomes publication.

## 3.2 Task continuity, language and recovery

- Keep the source brief task/result region distinct from the blocked period-report
  storyboard. Show submission, running, saved-source-result, interrupted, denied,
  unavailable and failed states in business language. Export/weekly controls stay
  blocked until their own contracts close.
- Capture domain/context/Subject and a request generation at submission. On focus
  change, Clear, navigation or retry, invalidate outstanding responses. A late
  result cannot overwrite the new scope or make an old result appear current.
- Reopen uses `job_id` through the actual GET API after returning/reloading. Keep
  useful error recovery and return to the prior task/source selection. An empty
  registry/source result stays honest; never fabricate report prose or zeros.
- A transient local Read Aloud preview may read only the analysis/question text
  already rendered from this reopened result and bound to the exact scope,
  `report_id` and `artifact_hash`. Use an installed device voice in zh-CN,
  en-US or ko-KR; no translation, remote voice, server call, audio file or
  saved Artifact. Replacing the result/scope or leaving the screen stops it.
- Chinese, English and Korean must cover actions, pending/running/saved/interrupted/
  denied/unavailable/error copy and accessibility announcements. Raw provider,
  exception or private path details are not user copy.
- At 1440px, use the existing report/source composition with one clearly identified
  task result; at 390px, recompose into task/result then source trail. Keyboard,
  screen reader labels, focus recovery and overflow require actual checks at both
  widths; a passing widget fixture is not live user acceptance.

## 4. State and recovery matrix

| State | Trigger | User-visible meaning | Available action | Acceptance |
| --- | --- | --- | --- | --- |
| Loading | Context/report read pending | 正在读取报告与运营简报 | None | CTH10-W-001 |
| Empty | Bound report catalog is empty | 当前范围内暂无报告。 | Refresh | CTH10-W-002 |
| Not collected | No scoped report/storyboard | 报告资料尚未接入，暂不能生成运营简报。 | Refresh | CTH10-W-003 |
| Partial | Report exists but source trail is incomplete | 报告可见范围有限，未核验来源不会显示。 | Inspect safe blocks; retry | CTH10-W-004 |
| Blocked | Scope/lineage/export binding missing; 401/403 | 当前范围暂不能查看报告资料。 | Retry; return | CTH10-W-005 |
| Offline / Error | Transport or malformed response | 暂时无法读取报告资料，请稍后重试。 | Retry | CTH10-W-006 |
| Ready | Bound catalog + storyboard + trusted references | Show outline, page preview, source trail and action/outcome status | Local selection only | CTH10-W-007 |

## 5. Purpose-built composition

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#cth-10)。

- Keep the period/window and scope visible in the header.
- **Accessibility:** page/section/source order is explicit; source references include title and observed fact; loading and blocked states are live regions; keyboard can move from outline to preview to source rail.

## 6. Actions, authorization and effects

| Action | Required proof | UI behavior |
| --- | --- | --- |
| Select period/section/source | Bound read response | Local selection only |
| Generate brief | Exact `report:write` Permission, Effect Fence, idempotent result and report Evidence | Disabled; no optimistic draft or success |
| Export PDF/Excel | Exact `report:export` Permission, effect/audit result and real file response | Disabled; no fake download |
| Generate/reopen/resume source brief | Server actor/exact scope; `REPORT_GENERATE` and audit/effect checks for writes; verified Job readback | Enabled only within §3.1; task admission, source-result save and business quality remain distinct |

## 7. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer |
| --- | --- | --- | --- | --- |
| CTH10-W-001 | Pending read hides report rows and announces loading | Loading | All widths | Widget |
| CTH10-W-002 | Bound empty catalog is empty and does not use the fixture | Empty | Desktop/mobile | Widget |
| CTH10-W-003 | Missing report/storyboard is not-collected and Generate stays disabled | Not collected | All widths | Widget |
| CTH10-W-004 | Unknown source IDs and hostile fields never render | Partial / hostile input | All widths | Widget |
| CTH10-W-005 | Missing scope/lineage blocks report data; Generate and Export are disabled | Blocked | Desktop/mobile | Widget + repository |
| CTH10-W-006 | 401/403/offline/malformed response hides server detail and offers retry | Error | Desktop/mobile | Widget |
| CTH10-W-007 | Storyboard/preview/source rail recompose at desktop, tablet and mobile widths; Trace/Return preserves selection | Ready | 1440 / 900 / 390 logical px | Widget |
| CTH10-SB-001 | Valid scoped start returns actual task admission, then polls to a persisted result; no optimistic saved/analysis success | Pending → running → source result | Real Canonical inputs; 390 / 1440; zh/en/ko | Repository + widget + live E2E |
| CTH10-SB-002 | Interrupted task resumes through a fresh permission check; denied/revoked scope performs no forbidden write | Interrupted → resume or denied | Actual task/principal/scope | Integration + live recovery |
| CTH10-SB-003 | Reopen result after navigation/Core recovery verifies same Job/source/hash and keeps HUMAN_PENDING | Saved → reopened | Actual saved Job | Integration + live E2E |
| CTH10-SB-004 | Clear/focus change drops late result; foreign/unknown/hostile source identities are withheld | Any → GLOBAL/new focus | 390 / 1440; keyboard and screen reader | Widget + repository + live E2E |

新增成果揭示遵循Experience §19，保留本屏原有动效：只有本次请求产生的真实新版本（不是接收回执/旧成果重开）在字体和最终布局就绪后播放一次完整点阵线框。等待使用普通骨架；用户独立选择完整/随减少动态偏好/关闭，可立即跳过；交互、来源、保存、修订和返回不被动效阻挡，不显示内部推理或虚构生成日志。

## 8. Review decision and open dependencies

- **Decision:** full CTH-10 remains BLOCKED; §3.1–3.2 SourceBrief increment is M-approved DESIGN_READY, not IMPLEMENTED/ACCEPTED evidence. Period/weekly/export controls remain blocked.
- **Required before DESIGN_READY / ACCEPTED:** actor-to-Subject report read binding, filtered Evidence query, report/storyboard owner, report generation contract, export endpoint, Permission/effect/audit result and runtime/E2E evidence.
- **Current disposition:** the existing aggregate report/Evidence builder is not exposed as App data.

### 8.1 M acceptance of the source-only main flow — 2026-10-02

M reviewed the frozen fourteen App source/test files, 75 affected tests and actual
same-origin browser operation, and accepted this bounded flow: GLOBAL CTH source
brief creation, real task completion, 29 Canonical source records with the returned
Evidence references, saved Job/hash readback, leave/reload/reference reopen,
offline result hiding/reconnect, foreign Focus denial and Clear back to GLOBAL.
The owning evidence is `00-GOVERNANCE/evidence/round-06/APP-WORKFLOW-VERIFICATION-2026-10-02.md`.

The actual task is `rbrief_ab54bb81-8feb-467c-9c0f-2458821909f1`, Job/Report
`brief-fb2192a3e5784d18a68ed0186b49733b`, artifact SHA256
`59b5efb3a98623106b35883a533b1b4d9a73576a3f02a79af6df082e438acff6`.
Evaluation rows 131–133 record the material workflow, not business usefulness.
Analysis was not requested; human review remains pending. The fourteen source/test
hashes remain frozen; the six Website files were published separately.

W6 verified the four API callables and their scope/context helpers match current
main; the Task/Job modules and `lumenis_app_api.py` also match main. Source-only
execution does not enter the local, unaccepted owned-business adapter. Other
Collector, AI, Skill, Memory and business candidates are excluded from this
publication. Genuine interrupted-task resume and operating-system clipboard
transfer remain `LIVE_NOT_VERIFIED` / `NOT_VERIFIED`. Full CTH-10, owned analysis,
full C3, native surfaces, Product Owner repeat operation and release remain open.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 创建或重开有来源的运营简报并检查结论。
- **屏幕专属呈现：** 正文/方法/引用/Action-Outcome分页阅读；从同一SourceBrief Job重开
- **来源、范围与版本连续性：** 沿用job/report/hash/brief/evidence/scope/父版；源失效局部复核
- **四端差异：** Web/Desktop正文与来源栏；Mobile逐页返回；官网仅审批公开版；朗读限当前绑定文本
- **失败与恢复：** ACK丢失查询同ID；无导出回执不称导出成功；换scope/hash停止朗读
- **补充验收：** 保存重开后逐条回源；段落修改成子版本，不丢方法引用。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

### 2026-10-09 source-to-result acceptance increment — OPEN implementation/acceptance

Consume the same actual SourceBrief/report job, source refs, actor/scope and
source/Artifact versions through existing Core APIs. Present returned verified source-count,
selection/truncation/method and semantic-interpretation limits separately from the
useful report; metadata or a title is not full source/media reading. UNASSIGNED
pending raw observations are accessible only through their allowed source-review
path, not assertions about a confirmed commercial Subject. Consumer opinion,
source statements and verified operating facts remain distinct. The running Web
flow must create a useful result from at least one real acquired permitted source,
save, close, reopen, revise, trace original source, recover interruption and keep
parent/history; revoked use stops dependent reading. Reports may give honest
partial results, never fabricated trends, conversion or causal claims. Existing
SourceBrief sample/analysis metadata must be bound into the actual reader when
implemented; this requirement does not claim the current UI already shows it.

The existing `business_analysis.sample.available_brief_count` is the number of
verified records returned by this particular limited/filtered query, not all
sources available in the scope. Label that denominator explicitly. Keep the
original SourceBrief intake sample separate from its actual analysis sample;
empty-body records can be returned without being analyzed. Display actual
returned/analyzed/omitted, selection, truncation and PARTIAL fields when supplied;
candidate/scanned/rejected/withheld counts and platform/time ranges retain their
own returned definitions and missing states. Do not fabricate missing metadata,
infer semantic evaluation from lexical matches, or label a query sample as full
market coverage. Save/reopen/revision must preserve the same result metadata.


## 2026-10-09 来源样本统计：实际无 AI 操作增量

本轮保持 CTH-10 全页 BLOCKED 和周期/周报/导出缺口，不把来源简报增量冒称整页完成。
历史实现记录：当时在已保存简报内增加「统计并保存来源样本」，消费现有 TaskEngine 的显式
`source_statistics` 操作，复用同一 CoreClient/Scope/Permission/Reporting Owner；没有第二分析器或数据真相。
服务端确定 actor 与 SourceBrief hash，界面不得自报身份或 verified。客户端重新读取来源和已提交 Task，
核对同一 Job/hash、`SOURCE_BRIEF_SAMPLE_ANALYSIS` 独立 Owner 结果与 finished_at 后展示统计。
仅显示本样本去重来源数、平台分布和真实原生发布时间已知/未知计数，不推断情绪、需求、因果或全量覆盖。
无需 AI；业务解释/AI 增强仍保持各自状态。中英韩、键盘/语义操作、现有 generation/scope/disposal 保护保留。

历史实现曾允许复制 `task_...` 统计任务编号重开。2026-10-11 当前要求改为从已保存报告/任务历史中选择并恢复同一成果，无需重新计算或复制内部编号；Task ID 仅作为内部/诊断/兼容元数据，普通用户不承担拼装。新交互尚待实际实现和验收。
新 Scope/新版本不能消费旧结果；失败不伪造零值或成功，现有错误/重开途径继续适用。
实际本机 Web 证明：30 条来源、28 个已知时间、2 个未知，保存后离开页面并重开同一任务。
完整截图/任务及构建 pins 留在现有私有 work 回执；正式 CI 和整页/跨域用户验收独立记录。

## 2026-10-18 研究能力采用接续（IN_PROGRESS / NOT_VERIFIED）

研究成果显式采用到选定CTH Subject后比较方案/预算/资源，内部选择不授权外部执行；实际行动owner读回后才能记录结果，未知与SOURCE_CLAIM/内部Artifact分开。

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

## 2026-10-22 SourceBrief 保存与共享成果接线

可选业务问题沿现有 SourceBrief start contract 传给后端。完成任务后先独立读回并核验来源简报，再提供同域保存/成果历史、原版本重开，以及基于明确父版本和 expected hash 的不可变修订。修订冲突或结果未知时保留原草稿与稳定 request ID；不得覆盖旧版本或因迟到响应清空用户后续输入。

跨域保存复用现有 `POST /api/experience/saved-work` 和 Shared SavedWork owner。prepare 只返回服务端核验的目标标题、精确资源、引用数、来源数和绑定；界面展示这些内容并等待用户明确确认。apply 使用同一个 request ID 和 `confirmed_resource`，不接收客户端 actor、scope、正文、引用或 Permission token。服务端重读来源、权益和当前范围并完成精确导出审批；保存后通过 `GET /api/experience/saved-work/<artifact_id>` 独立重开、比对 artifact/hash/版本/范围/来源绑定。原 CTH/BMP 来源简报保持不变，不对外发布。连接结果未知时用同一 request ID/resource 幂等重试，再读回既有成果，不创建重复版本。

界面使用普通业务语言说明另存到共享成果、来源与引用数量、保存后的打开位置及不对外发布；不展示内部任务编号、资源令牌或算法说明。弹出确认期间当前 scope、简报任务或简报版本改变时立即关闭确认；撤权、旧资源、来源变化、读回不一致和网络失败均保持未完成并允许安全恢复。

实现范围为 SourceBrief VM/Panel、现有 CoreClient、三语文案及本屏同域历史/修订/跨域采用接线。该有界源码结果不构成完整 CTH-10 视觉、四端运行或全产品用户验收；适用的当前构建和真实用户操作证据仍按实际执行状态单独记录。
