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

## 0. Authority basis and artifact disposition

- Constitution basis: BMP creator intelligence is Brand/Market-first and must preserve source lineage, risk semantics and responsive reading order.
- Product/workflow basis: BrandFocus → creator fit/authenticity/contribution/risk → content/propagation evidence. A creator profile is not a global account directory.
- Exploration references: current Experience Constitution blueprint only; generic social graphs and copied influencer dashboards are rejected.
- Anti-template decision: the page combines a creator relationship graph, tiered roster and one source-backed dossier; it is not a generic profile card wall.
- Sol design decision: `DESIGN_EXPLORATION`; current creator builders are cross-brand and therefore block full acceptance.

## 1. User problem and product invariant

- **Role / context:** A BMP operator evaluates creators relevant to one authorized BrandFocus across KOS, KOL, KOC and UGC tiers.
- **User task / completion:** compare creator fit and contribution, inspect risk and source evidence, and decide which creator analysis deserves a later workflow handoff. Completion requires same-focus profile data, typed metrics with definitions/windows, source and trace.
- **Invariant:** a Subject ID cannot authorize or identify a creator's BrandFocus. A creator row with another focus or compatibility identity is hidden.
- **Global rule:** `GLOBAL / ALL` is the default global creator universe when the response and every profile row carry explicit canonical global scope, verified lineage and `read_allowed`. Focused BrandFocus profiles without those markers are rejected, never promoted.
- **Out of scope:** contacting creators, publishing, campaigns, payments, identity matching, automated recommendations and any external effect.

## 2. Route, entry, exit and return

- **Entry:** host shell opens BMP-05; read is `GET /api/experience/screen/BMP-05` through `LumenisCoreClient.screen('BMP-05')`.
- **Required context:** server-returned focused BMP/ZBMP context with distinct Subject/BrandFocus IDs, applied binding and allowed read, or `GLOBAL_ALL` with explicit global grant, canonical scope, verified lineage and `read_allowed`.
- **Exit / return:** creator selection, tier filter and risk filter are local presentation state. Return restores the selected dossier when the host preserves the screen; no context mutation occurs.
- **Trace:** the dossier retains creator source, evidence trace, metrics definition and window. No creator record or campaign is written.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition / units / window | Freshness and missing behavior | Binding ID | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Runtime envelope and owner | Experience API adapter + BMP | `GET /api/experience/screen/BMP-05`; envelope and `truth` | Runtime-bound ZBMP/zbmp response | Mismatch blocks all profiles | BACKEND-GAP-022 | `experience_runtime.py::screen_viewmodel`; `bmp05_snapshot.dart` |
| P0 | Focus/global read binding | SYSTEM context / Permission | `focus_context` + `focus_binding` | FOCUS exact Subject/BrandFocus; GLOBAL_ALL explicit global grant/canonical scope/verified lineage/read permission | Unknown blocks creator rows | BACKEND-GAP-022 | Current `_build_bmp05()` reads cross-brand creator stats |
| P1 | Creator roster | BMP creator ecosystem owner | Future `sections[type=creators|creator_roster].items[]`: id, optional BrandFocus, name, tier, platform, source, trace, row scope/read/lineage fields | FOCUS exact BrandFocus; GLOBAL_ALL explicit global scope/verified lineage/read permission; tier is KOS/KOL/KOC/UGC | Invalid/cross-focus row omitted | BACKEND-GAP-022 | `Bmp05Creator` strict parser |
| P1 | Fit/contribution/risk metrics | BMP + Shared Evidence | typed metrics with value, unit, definition, window; risk level/label/score | Values are observed within the declared window; no missing→0 | Missing metric remains unavailable | BACKEND-GAP-022 | Current stats/profile outputs lack verified focus/lineage |
| P2 | Tier/risk filters | App presentation state | `Bmp05ViewModel` local filters | No server mutation | Filtered empty state is explicit | BMP05-UI-LOCAL | `bmp05_view_model.dart` |

## 4. State and recovery matrix

| State | Trigger / evidence | User-visible meaning | Available actions | Recovery / return behavior | Acceptance ID |
| --- | --- | --- | --- | --- | --- |
| Loading | Initial read or refresh | 正在读取创作者生态 | None; announce busy | No previous-focus rows flash | BMP05-W-001 |
| Global / all blocked | Global grant/lineage/read contract is absent, or only focused rows are returned | 当前全局范围暂不能查看未核验创作者资料 | Retry; return to context selector | Reject focused rows; do not relabel them global | BMP05-W-002 |
| Global / all ready | Authorized global binding plus valid global profiles | 查看全球创作者生态与分层资料 | Tier/risk filters; select creator | Preserve global view | BMP05-W-003 |
| Empty | Valid focus or global scope with no verified creators | 当前范围暂无创作者资料 | Refresh | Keep focus visible | BMP05-W-004 |
| Not collected / unknown | No creator collection or unknown state | 创作者资料尚未形成可核验记录 | Refresh | No zero metrics | BMP05-W-005 |
| Stale / partial | Stale data or missing metrics/lineage | 部分创作者资料仍待核验 | Refresh; inspect verified fields | Keep missing values explicit | BMP05-W-006 |
| Offline | Transport unavailable | 暂时无法读取创作者生态，请稍后重试 | Retry | No unscoped cached profiles | BMP05-W-007 |
| Blocked / denied | Missing binding, 401/403 or invalid lineage | 当前范围暂不能查看创作者资料 | Retry; return | Hide all profiles | BMP05-W-008 |
| Error | Malformed/unsafe response | 创作者生态暂不可用，请稍后重试 | Retry | Hide raw response | BMP05-W-009 |
| Ready | Exact-match focused profiles or authorized global profiles | Compare tiers, fit and risk, then inspect one dossier | Tier/risk filters; select creator | Restore local selection | BMP05-W-010 |

## 5. Purpose-built desktop composition

已批准目标来源：`BMP-05-ADD-kos-funnel.md`。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：KOS 三阶漏斗与合规留资

```
曝光 → 互动 → 留资  （每阶：值｜区间｜缺失标注）
CPL / 成本：—（缺失）或数值
[生成评论回复草稿]（不自动发送）
```

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

- Web uses the same Product Core response, parser and ViewModel. Browser deep-link restoration remains host-owned.
- No browser-only creator contact, export or campaign effect is exposed.

### Adopted Web additions

### 草图增补：KOS 三阶漏斗与合规留资

Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition

### 草图增补：KOS 三阶漏斗与合规留资

Purpose-built mobile composition
纵排。

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
- **Open owners:** BMP must define creator fit/contribution/risk semantics and source contract; SYSTEM must return verified read binding; Shared Evidence must validate profile traces; Sol must review the graph/roster/dossier composition.
- **Required before acceptance:** live BrandFocus run, random entity acceptance, responsive/a11y runtime proof and an explicit boundary for any future creator contact or campaign effect.

## 11. Real delivery and data-maturity overlay

- **REAL USER JOB:** understand which creators fit a selected brand and what contribution/risk evidence supports that view.
- **REAL DELIVERY CARD:** real BrandFocus → scoped creator roster → selected creator dossier → source/metric trace. Current source fails the scoped entry gate; commercial readiness is `NO`.
- **GLOBAL UNIVERSE / DATA MATURITY IMPACT:** `GLOBAL / ALL` may show the global creator universe only through explicit global scope/lineage/read markers; focused profiles cannot become global roster truth. Current endpoint lacks that contract, so coverage remains blocked. Random sample acceptance is `NOT RUN / canonical scoped creator population unavailable`.
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
