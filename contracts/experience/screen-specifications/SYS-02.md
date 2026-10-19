# SYS-02 — Collector status

```yaml
screen_id: SYS-02
status: DESIGN_EXPLORATION
revision: 2
owner_domain: SYSTEM Collector
binding_ids:
  - BACKEND-GAP-037
product_owner_approval: APPROVED_FINAL_TARGET_2026-10-07
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: M target-convergence review
reviewed_at: 2026-10-07
approval_reference: Product Owner-approved Universal Platform Acquisition / PlatformManifest / PlatformSession convergence; current implementation remains read-only until bindings pass
```

## 0. Authority basis and artifact disposition

- Constitution basis: SYSTEM collector blueprint, truthful state semantics, responsive recomposition, accessibility and §36 executable acceptance.
- Product contract: `SYSTEM Collector → Source/Evidence → Canonical Data`; this screen reports operational collection state only.
- External sketches, screenshots and taskbooks: `KEEP_AS_EXPLORATION`; none authorize layout or capability.
- Anti-template check: the primary composition is a platform-lane inspection with an ingestion-boundary explanation, not a generic KPI dashboard.
- Sol design decision: `DESIGN_EXPLORATION`; the current implementation is a bounded read-only candidate. Product Owner approval below defines the final target, not implementation proof.

## 0.1 Approved final-target extension — 2026-10-07

SYS-02 is the operational projection of the one SYSTEM Collector. It must not become a platform-admin dashboard or a second collector. The final target consumes the shared `PlatformManifest`, `PlatformSession` and durable Collector task/result owners instead of maintaining local platform lists or session truth.

The user-visible final target distinguishes:

```text
Platform capability
→ declared / implemented / registered / configured / session-verified / live-verified

PlatformSession
→ READY
→ AUTH_REQUIRED
→ VERIFY
→ BLOCKED / COOLDOWN
→ WORKER_UNAVAILABLE
→ NOT_CONFIGURED
→ UNKNOWN

Collector task
→ planned / queued / running / partial / waiting-recovery / completed / failed / cancelled
→ query continuation is separate from platform-native content/comment/media cursors
→ terminal replay never appears as a new run
```

Desktop/Web may show plan, execution and platform lanes in parallel. Mobile shows one task or platform lane at a time with the same semantics. User-facing rows describe what data can actually be obtained, what remains unavailable and what recovery is required; Cookie files, CDP ports, profile paths, lease IDs and completion tokens never render.

Final actions may include explicit manual run, an already-authorized schedule, pause/cancel/resume and recovery entry only when the existing Collector/Scheduler/Permission owners supply a real callable and receipt. One affected platform must not block other eligible platform lanes. `LumenisPlatformRecoverySheet` is the shared recovery surface; SYS-02 links into it rather than creating platform-specific login dialogs.

## 1. User problem and product invariant

- Authorized context: SYSTEM operator permitted to read the current screen envelope.
- Real task: determine which collection lanes are verified, partial, missing or blocked, and whether a record may cross into Evidence/Canonical Data.
- Completion signal: the returned platform states and counts are visible with their source state; missing values stay unavailable.
- This screen’s verified slice remains the read envelope in §3. The backend has a human-confirmed `POST /api/collect`; its existence is not evidence that this screen’s manual action, background AUTO for every registered subject, or durable scheduling has passed end-to-end acceptance. The final-target controls in §0.1 remain conditional on their actual Owner, current Permission and receipts.

## 2. Route, entry, exit and return

- Entry: App shell route for SYS-02; shell authentication remains the caller boundary.
- Read binding: `GET /api/experience/screen/SYS-02` → `experience_screens._build_sys02()` → `collector_status_api.get_all_status()`.
- Exit: return to the originating SYSTEM route; no drilldown route is verified.
- Return state: preserve shell origin and scroll position only; no Subject/Brand selection is changed.

## 3. Verified data and callable bindings

| Priority | UI field | Owner / source | Missing-data behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Active/partial/missing/blocked counts | `truth.summary`; KPI ids `sys02.active`, `sys02.partial`, `sys02.missing`, `sys02.blocked` | Numeric value only when KPI state is `ready`; otherwise unavailable | BACKEND-GAP-037; `experience_screens.py::_build_sys02`; `sys02_snapshot.dart` |
| P0 | Platform lane | `sections[type=table].rows` fields `平台/状态/解析记录/说明` | Unknown status and unavailable record count remain explicit | BACKEND-GAP-037 |
| P1 | Ingestion boundary note | `sections[type=note]` | If absent, show binding-unavailable copy; do not infer Evidence acceptance | Collector closed-loop contract |

No write action is verified through this screen’s current read binding. Separately, `app.api_collect` implements a bounded human request (`operator=human|human_ui`, `confirm_read_only=true`), server-derived scope/Permission and admission rechecks, a task_id and current status reads. Its current in-memory task contract returns `resume_supported=false`; this is not durable cross-restart recovery, an idempotency key or a verified cancel control. No unconditional AUTO-for-all-subjects guarantee, screen-level write binding, durable schedule, or end-to-end Evidence emission is established by this screen specification. Timeout/unknown results must query the known task rather than silently resubmit; when no task_id was received, show unknown and do not invent deduplication.

## 4. State and recovery matrix

| State | Meaning and UI | Action / recovery |
| --- | --- | --- |
| Loading | Reading current collector state; no placeholder counts | Wait or leave |
| Empty / not collected | No platform lane or metric returned | Read boundary explanation; do not show zero |
| Partial | Some lanes/counts returned, others unavailable | Refresh read route |
| Offline / error | Connection, malformed envelope or server failure | Retry only when the failure is retryable; clear stale snapshot |
| Blocked / permission denied | 401/403 access state | Return to authentication/access flow; no collector operation |
| Ready | Current returned states are shown | Read only; `ACTIVE` is not inferred from registration |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 采集模式与动作边界（目标布局见唯一草图）


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 只显示Collector/Scheduler Owner读回的真实模式与范围：未来用户MANUAL默认、AUTO需显式opt-in；PO已批准内部连续程序的AUTO范围覆盖全部已登记主体，无单主体硬编码。当前只读切片不执行模式写入、手动采集或取消；依赖动作在真实callable/Permission/幂等恢复合同接通前保持OPEN。身份、来源权益、Permission及Effect Fence始终执行，界面不自行关闭安全边界。

### Existing contract — Purpose-built desktop and web composition

- Desktop: header and summary strip first; platform lanes occupy the primary inspection plane; ingestion boundary is a separate explanatory panel.
- Web Workspace: same Core/ViewModel semantics and keyboard navigation; no desktop-only capability is claimed.
- At tablet width, stack lanes and boundary; at phone width, keep one platform lane per row and preserve state/detail pairing.
- No charts are rendered because the endpoint supplies no time series.



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

### 平台适配与队列结果的专属投影（B06）

原lane详情采用“此次取得/待处理或失败/身份与来源”页内分组，真实provider、内容原生身份与父关系、查询窗口、Source版本和字段缺失随材料可核。只展示原Collector/PlatformManifest/队列安全投影，昵称相同不合并身份；客户端无权限可读取的旧行不从缓存补回。现status聚合没有的字段保持OPEN，不能在UI制造假健康或完整覆盖。

每个未完成子项显示原状态/原因/已试时间及实际可执行恢复；停止请求、实际取消、冷却、来源失效与结果未知分开，已提交回执能打开而不自动重做。身份/Source/查询版本不符停止旧checkpoint续跑。Web/Windows/macOS矩阵+单lane详情，窄Web/iOS任务→lane→失败子项→回原筛选；官网只去敏真实范围。UI自身AIGC可按真实字段选择清单/表，但不能生成缺失值、身份或成功；键盘/读屏等价。验部分成功、失败子集恢复、重复排队/重启、身份冲突/撤权、原生评论父子绑定、零与缺失、三语和各端冷开；保持当前绑定状态不自动提升。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 采集模式与动作边界（目标布局见唯一草图）

Web Workspace composition
Web：范围、实际进度与失败恢复逐项可见；后台状态刷新不抢焦点，返回保留筛选与选择。完整手动/批量操作目标在唯一草图保留，接通真实Owner动作后须显式请求、Permission与幂等/恢复核验，不得因浏览器刷新重复启动；当前只读切片不发起该效果。

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 采集模式与动作边界（目标布局见唯一草图）


### Existing contract — Purpose-built mobile composition

- One active question: “what is the current collection state, and can it enter the truth chain?”
- Order: summary → platform lanes → ingestion boundary.
- Touch targets are provided by the shell/refresh affordance; no destructive action exists.
- Offline/error recovery returns to the same page and clears old values.

## 7. Actions, authorization and effects

| Action | Permission/effect | Evidence and failure |
| --- | --- | --- |
| Load current state | Existing screen GET; read only | No persisted Evidence; distinguish 401, 403, offline and malformed response |
| Retry read | Same GET only when retryable | No collector mutation and no fake success |

## 8. Accessibility, motion and localization

- Keyboard order follows summary, platform lane, state/detail and boundary explanation.
- Status uses text, icon and color; live failure/loading regions have semantic labels.
- No chart alternative is required; every metric has a textual unavailable state.
- zh-CN/en/ko copy must wrap at narrow widths; reduced motion suppresses non-essential transitions.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS02-STATE-01 | Ready zero is rendered as zero; offline/null is not zero | Flutter snapshot/widget tests |
| SYS02-BOUNDARY-01 | Registration/status does not become Evidence or Canonical acceptance | source binding review + widget test |
| SYS02-RESP-01 | Desktop, tablet and phone use distinct lane composition | Flutter widget tests |
| SYS02-RECOVERY-01 | 401/403/offline/malformed response show safe bounded states | ViewModel/widget tests; live HTTP still pending |
| SYS02-REAL-USER-01 | Operator opens SYS-02, reads one real returned lane, and can distinguish not-collected from zero | Requires authenticated runtime E2E at current commit |
| SYS02-MANIFEST-02 | A clean runtime projects the same canonical platform identity/capability truth as PlatformManifest without import-order registration tricks or a second UI list | Future manifest/registry contract + clean-runtime test |
| SYS02-SESSION-02 | READY/AUTH_REQUIRED/VERIFY/BLOCKED_COOLDOWN/WORKER_UNAVAILABLE/NOT_CONFIGURED/UNKNOWN are visually distinct and recovery opens the one shared RecoverySheet | Future PlatformSession API + widget + runtime E2E |
| SYS02-TASK-02 | Query continuation, native cursor and durable receipt are distinct; terminal replay returns prior result or explicit terminal state and never appears as a new run | Future task/receipt contract + concurrency/replay test |
| SYS02-ISOLATE-02 | One blocked/recovering platform lane does not block eligible platform lanes and retained partial results stay visible | Future multi-platform runtime E2E |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; this page does not select a business entity or report Global/Brand/Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; entity sample count is zero and no entity value is fabricated.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete for this slice; no justified upgrade beyond the existing Collector closed-loop contract. Any future retry/effect must be versioned behind Permission, Evidence, observability and rollback.
- Decision: `DESIGN_EXPLORATION`; Sol must review the spec, verify the screen route and complete authenticated runtime acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 查Collector各平台lane和进入Evidence的真实状态。
- **屏幕专属呈现：** 平台manifest/lane/attempt/receipt显示configured/active/partial/blocked
- **来源、范围与版本连续性：** 关联真实Collector task与Source/Evidence receipt，不伪造覆盖率
- **四端差异：** Web/Desktop矩阵和单lane详情；Mobile按平台读；官网只讲验证过能力
- **失败与恢复：** 挑战/身份/限流阻断单lane，刷新失败标stale
- **补充验收：** 读出与receipt一致；页面不查看Cookie或触发无绑定重试。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

## Topic/time and truthful missing dimensions — 2026-10-08

Follow Global §10 and Experience §38's latest correction. Collection is subject/topic/task driven with no universal start date; explicit task dates still apply. Distinguish publication/event/capture time, group unknown dates honestly, and preserve precision/timezone. Required dimension definitions remain visible even without values: display “—” with accessible reason/state/last verified time, never zero-fill, hide required columns or invent chart continuity. Real zero remains zero. A source limitation requires actual collection-chain evidence; missing code, skipped execution, parsing failure or expired authorization stays an owner defect/blocker. No requirement for every data value to be obtainable, no automatic acceptance of collector capability. C1/C6 still need to migrate the pinned old date literal; this specification does not activate them or promote design/runtime acceptance.


### 全项具体工作合同：财务采集目标、主体研究档案和候选审查

保持目标、捕获、导入、分析与研究档案版本的各自回执；保存审查不等Registry变更。状态包括凭证未配、捕获未知、字节不符、原件变更、scope不匹配、陈旧父版、身份来源不足、待更多证据及注册未执行。验收捕获成功但未导入、解析失败、同名主体、签名有效但断言未核、注册建议改侧/名字、取消及重开原选择。

SYS-02内以来源阶段条＋当前目标详情显示采集/捕获/导入，不新建采集中心；SH-02档案预览为来源/断言并读；BMP-02候选审查为左右实体、引文侧栏和底部三个命名决定。Desktop/Web并读，iOS一侧一屏可同字段切换并返回，注册等敏感决定沿原确认；官网只用公开例。UI适配将待核字段和来源冲突提出到前侧，保未改档案位置，不能自动把候选涂成已注册。

具体操作与恢复：财务来源流程将“准备目标→获准采集→捕获字节待导入→导入→解析成果”分别显示，目标标识、官方路径、当前身份/用途及所选字段可核。生成OpenDART请求描述不等已配置密钥或已抓取；不在前端收集或回显秘密。每阶段失败保原任务/材料，未知完成先查原回执，不再发一次采集。
主体研究档案按已确定领域/主体范围导入，先预览来源清单、研究断言、父版本与审阅记录；签名只说明完整性，断言仍是研究推断且底层出版权利未知。实体候选审查从准确分析版本打开左右原档案/引文，选择“保留分开、需更多证据、提出注册建议”并记录理由。注册建议必须明确取哪一侧身份及名字，再进入既有Registry的独立批准；本审查不会合并或直接注册。


### 连接配置与实际核验分层

GitHub连接卡在来源连接列表中依次显示配置状态、最近实际核验时间/结果和可用动作。只有token配置时显示“已配置，尚未核验”，对应PROVIDER_UNAVAILABLE / NOT_VERIFIED / HEALTH_CHECK_REQUIRED，不显示绿色已连接；读取状态不偷偷外呼，也不缓存一次授权替代当前权限。用户点击原有“核验连接”并明确执行后，只有真实/user探测返回非空login的成功回执才能显示CONNECTED；失败保配置、显示原因和重试入口，取消不重新探测。OAuth回调接线仍为OPEN，不能用token存在代替OAuth闭环。

Web与Windows/macOS为连接列表—选中连接详情—显式核验确认，iOS用连接详情Sheet显示同一未核验/失败/成功事实及时间；官网只展示去敏示意和能力边界。重试前核当前权限，迟到回执不得覆盖已切换连接；撤权后隐藏敏感详情。用户价值是避免把配置存在误当服务可用。UI自身AIGC可依据真实核验缺项组织排错阅读顺序，支持原创但可撤销的诊断布局，不生成成功状态、账号事实或自动发起核验；手工布局、锁定与无AI状态常驻。


### 原要求具体工作合同：每来源用途、频率和撤回影响的就地查看

从具体资料或采集lane的“使用范围”进入，读取这份来源/版本在当前身份和任务下的许可依据、允许字段、用途、保留/刷新频率、到期、转载/训练/外部处理状态。明确区分有原合同证据、用户声明、待核、拒绝和不可用，不由前端解释成统一许可。普通自有/获准资料上传保持原无通用用途表单入口，只在实际额外用途或敏感动作前呈所需确认。
许可撤回/到期时列当前受影响的读取、衍生分析、导出和已知成果引用，保允许的用户原稿及合法历史；不能把停止当前用途等同删除全部资料或撤回已外发。合法恢复需原SourceUse/Permission读回，不能靠重新点同意自行变绿。

Reader右侧“本来源使用范围”按身份/字段→用途→频率与期限→受影响作品四层；每行状态有文字及依据链接，点击返回准确原资料位置。SYS-02 lane只显示当前采集动作相关的频率/冷却与缺项，SYS-04合规报告引用相同事实。Web/Windows/macOS并读，iOS从资料详情开Sheet逐用途阅读，官网只公开真实支持边界。UI可按本次动作突出相关限制，不隐藏拒绝、不生成许可；同源普通表可锁定。

返回/关闭详情不改许可；只有既有Owner的合法刷新/恢复/撤回动作可用。验同来源不同用途/身份、许可未知、期限过期、撤回后下游仍可编辑但禁止相应导出、冷却不重试、source版本变化和跨端重开。任何条目缺原字段保持UNKNOWN/OPEN，禁止凭URL可访问授转载训练权。


### 原要求具体工作合同：免费来源数据类别与聚光未配置边界

原来源任务范围内，按平台注册的广告/流量、创作者中心、公开内容等实际对象显示当前合法取得路径与可得字段。每行分别列免费/费用未知/需额外许可、公开路径/获准自有会话/已授API、身份条件与实际最近结果；“平台注册”不等“免费可采全部”。缺某类数据保其他可用材料，不能以公开视频替广告账户观测或把零条当成功。
聚光为来源/活动当前任务的一项：未配置专业号、授权未知/失效、字段未取得分别写具体原因；未配置保持UNAVAILABLE，用户可跳过继续当前规划，不强制开通或付费。KFS的F“24h互动>20再投”只列方法假设及适用性，旁边明确“未执行投放”，不能据此出现自动充值/投放成功。

SYS-02平台lane详情“本任务数据”表列数据类别→字段→取得路径→费用/许可条件→实际状态，选行打开具体限制和原来源；BMP-07在所选活动的数据依据中显示聚光可用性及方法说明，不另建广告管理器。Web/Windows/macOS表与详情并读，iOS一类别一详情并保原lane/活动，官网只公开验证过路径。UI可据实际缺项聚焦解释，不生成授权、专业号或预算执行；简洁同源列表可锁。

选择来源/类别不自动登录、请求付费API或外发；恢复依原Source/Session/Permission明确动作。验每平台注册字段缺失、免费但未获权、授权但无数据、聚光专业号未配置、授权撤回、零条与未知、取消和重开；完整平台注册范围逐项运行仍OPEN，不能以一来源示例验全部。

### 原G123/G140/G178具体终态合同：到期维护、自立路径与分层健康

在现platform lane详情保“本任务能取得什么”并展开原6平台×12能力及后续全部登记能力的路径表；逐格列公开页/RSS/开放文件/自主解析或实际获权路径、可得字段、当前约束和真实入库回执。自立度排序只按已声明准入/依赖，不把免费/HTTP200当成功。原17×19矩阵继续保全，两者不同清单不可互相顶替。
维护列表按真实到期项列最近有效更新、下一到期/实际计划运行、失败原因、退避/Retry-After、checkpoint和恢复状态；未知调度时点不以倒计时造持续运行。三层健康用“服务可达/页面连接/平台会话”读懂L1/L2/L3，保HEALTHY/NEEDS_LOGIN/CDP_DEGRADED/DOWN及检查时点，不显示端口/CDP地址/凭据。429是软限流并遵原Owner退避，不反复弹登录。

构图：左lane及到期过滤，中间能力路径/更新清单，右选中项的三层检查与失败子项；原恢复Sheet是唯一人工登录入口。iOS一个lane→一项能力/到期项→原因与合法恢复。

未到期不重复处理；已提交资料先读回而不重新采。服务不可用/页面降级/需登录/冷却分别给允许动作，重启恢复按原checkpoint，取消保已得合法资料。缺真实排程与运行证据标NOT_VERIFIED，不由界面动画报持续运行。

Public Website仅用获准真实样例说明到期维护、自立路径与分层健康及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按待恢复/将到期/已取得任务组织清单和检查器，不能生成健康、覆盖率或登陆事实；可锁筛选、无AI线性表和撤销。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 原G179具体终态合同：来源分工与正文提取质量

来源详情清楚分开“这份资料可支持什么”：官方/媒体身份事实与社媒传播/消费者表达按原来源及主张列依据，资料类型不是自动可信评级。正文提取核对面并读原页/原文、实际抽取正文与截断/缺段；Trafilatura与既有解析的小样对照作为评测记录，不能因库名显示正文合格。按平台/字段列实际有会话/无会话取得值、观察时间、缺失原因与合法取得方式，未知不变可得或0。

构图：来源清单→主张/用途与正文对读→选中字段的采集条件；宽屏原件与抽取旁排，移动原文/抽取切换保同段。评测详情按需开，不要求普通上传者填通用用途表。

只有摘要、页面失效、解析失败、版权未知、会话不可用或未测试条件分开；人工校正存派生版，取消保原件，来源变化使旧质量结论过期。无权路径不能通过换会话绕过。

Public Website仅用获准真实样例说明来源分工与正文提取质量及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按真实缺段与字段冲突提议对照阅读，不能补正文或画“官方即可信”；保原文锁定/简洁/撤销。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。

### 便利操作合同：CV07 通知直回决定处，连接失败仍可继续本地工作

适用工作与省步目标：当前成果通知、待确认任务、模型/工具不可用的编辑工作；不将通知点击作为执行授权。

原Owner与真实接口边界：GET /api/experience/saved-work/notifications及preferences复用现字段；深链读取原对象后再核当前actor/Permission。连接状态按实际health/probe回执区分已配置未验证和已连接，不靠token亮绿灯；返回锚点及通知消费状态缺持久字段时只作本机状态，不新增平行消息存储。

控件位置与四表面操作：通知行直接标任务/对象/待决定事项，点击落具体字段并保返回通知位置；失败状态就近提供“继续编辑/查看材料/保存当前稿”。Web/桌面保现窗口，iOS回原scope单一页面，官网只处理公开服务/表单状态。省掉首页搜索与重建稿，通知不自动切断当前输入。

持久化、权限与错误恢复：迟到通知先读当前版本，已经处理则解释并看结果；撤权不显示敏感摘要。模型不可用仍能手动写和合法保存；重新连接是显式动作，读取状态不偷偷外呼。键盘焦点与未提交稿保持，安全拒绝不能被便利操作绕过。

验收以同一真实任务记录原路径/新路径的操作、切换、重复录入、失误与恢复；没有实测前不填写节约秒数或成功率。便利界面与接线仍须本地构建，后端只按实际Owner测试证据判断，不能用本段规划声称已完成。

### 同账号浏览器任务连续与有界并行（原Owner接续）

用户本轮提出的浏览器目标是：同一已授权账号保持登录连续，多项获准工作可各用自己的tab推进，少反复登录和手动切换。Muse并行能力仅记为用户观察，未经本轮独立实测；不能把观察当序境已经具备的功能或把外部产品行为当供应商API。原G82/G83/G115/G123/G133/G188继续由原Browser/Collector/Task/Permission Owner承接，不建第二浏览器或任务队列。

具体工作面：SYS-06顶部保当前产品浏览器会话与账号状态（不显cookie/凭据），下方按原Task列工作标签和所属tab；AI-02每个任务卡显示“观察中/待批准动作/执行中/核验结果/结果不明/等待限流/需要人控/取消待安全边界”等实际状态，点击直接回该任务tab与最近已确认结果。SYS-02只呈同账号/平台共享限额和真实采集进度，不把多个任务数当可并发额度。Web/桌面可按需并读任务tab，默认主工作面舒展；iOS以单任务浏览与可逆任务切换Sheet保返回位置，不要求复制桌面分屏；官网仅有权公开的受控演示说明同账号多任务，未接通功能明确标目标。切任务保原稿、任务身份及观察位置，不自动取消、重发或共享不同任务的业务scope。

登录context由原服务端账号/BrowserSession Owner管理，任务只租赁自己的tab。复用已获授权的登录不等新授权：每次动作仍核当前actor、task/run、tab、目标与原Permission/effect fence；跨actor/账号、别的任务tab或过期run禁止操作。单页同一时刻单写者，人控lease优先，弹窗也必须确定所属任务；结束/取消A只释放A的tab，不能关闭兄弟任务或整个共享context。共享context的生命周期和Playwright调用仍由原单线程Owner/正式调度维护，不把对象跨独立worker直接共用。当前这些共享context/tab dispatcher接线尚未完成，界面不得先显示“同登录并行已启用”。

每个动作之前观察当前document/frame/revision，定位用当前DOM/截图；文档变化使旧引用失效，页面文本不能扩大权限或变成系统指令。动作后必须观察并核明确预期结果，元素/计数/加载状态缺失保持未知，真实0和空输入依实际观察区分；不能把“请求发出”“返回200”或动画结束当目标达成。定位失败先再观察和重新定位，不扩大到任意脚本或用户其他App。外部副作用是否发生不明时保UNKNOWN及最后已确认结果，先读回核对，不盲重试click/input/提交；只有明确幂等读操作才按原Owner允许次数有限重试。迟到成功回执仍归原task/run，不覆盖新工作。

同账号/平台的所有适用任务遵守原Collector限额，使用同一账号/平台限流Owner；429/Retry-After、冷却、配额未知分别显示，等待可取消且不会绕限额换账号/会话。每任务详情/评论游标独立，来源按原Evidence/Canonical键去重并保scope，不跨域复制。当前rate修复只证明同实例放行间隔，不证明跨进程或所有任务已共用实例。暂停/取消呈请求→安全边界→真实终态，已派发外部效果不可回滚；恢复先新观察/新frame，新run重新取得sealed admission，不复用旧DOM或批准。登录/CAPTCHA/敏感步骤沿原人工接管入口，人控结束后重新核状态，不偷偷代填凭据。

当前实现事实：ActionVerifier状态核验、未知副作用恢复、同实例限流与内部Task admission→Browser绑定桥已有独立候选及隔离测试；原tab策略已有边界检查。这不是Task工具dispatcher已接通，更不是同登录多tab端到端完成。当前start仍每runtime新context，原manager同owner异task限制仍存在；不能为迎合并行直接删隔离锁。尚待同版证明的最小纵向链是：真实队列任务→获准Registry/Skill版本及明确browser effect→原工具dispatcher→一个产品tab→真实Observation/Evidence/Task checkpoint→实际结束，再扩同登录两任务tab。HTTP自报task/run不可替代内部封装准入，内部桥本身不算全链。

验收先用合成测试站和真实Chromium证明一次登录两任务连续、tab隔离/弹窗归属、一个取消不影响另一个、同账号429等待、动作超时已生效/未生效分别恢复、进程/lease回收及撤权；不得用真实用户凭据做单测。真实外站、多账号和各平台覆盖尚未验证；云端浏览器socket受限时如实记环境阻塞，不绕过，不把纯mock当真浏览器通过。四表面实际前端构建与有权本地产品浏览器验收继续分账。主任务预算、界面自身AIGC原创表达和200以上交互要求保留，便利不省略必要批准/成功核验。

官方参考（2026-10-18已核文本）：[OpenAI Computer use](https://developers.openai.com/api/docs/guides/tools-computer-use)、[browser drivers](https://developers.openai.com/api/docs/guides/tools-computer-use-sdk-drivers)支持动作后观察、过期引用与不明效果恢复的工程参考；[Grok Bot computer and apps](https://docs.x.ai/grok-bot/computer-and-apps)描述共享登录、分屏单任务与人控。这些是机制参考，不构成新模型调用/供应商接入，也未证明序境或Muse端到端能力。
