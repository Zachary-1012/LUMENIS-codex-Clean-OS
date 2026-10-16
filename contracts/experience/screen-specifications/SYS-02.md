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
- Current slice binds one optional manual-collect button (`POST /api/collect`, human-confirmed; default stays AUTO for all registered subjects in the system background); cookie/session inspection, retry/stop/compensation actions and business truth stay out of scope. The approved final target in §0.1 may expose only those controls whose existing owners later provide real callables, Permission and durable receipts.

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

No pagination, write action, idempotency key, Evidence emission or cancellation contract is verified.

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

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

完整目标布局与交互见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

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

## 5A. Web Workspace composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 采集模式与动作边界（目标布局见唯一草图）

Web Workspace composition
Web：范围、实际进度与失败恢复逐项可见；后台状态刷新不抢焦点，返回保留筛选与选择。完整手动/批量操作目标在唯一草图保留，接通真实Owner动作后须显式请求、Permission与幂等/恢复核验，不得因浏览器刷新重复启动；当前只读切片不发起该效果。

## 6. Purpose-built mobile composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-02)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

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
