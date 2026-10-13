# CTH-02 — 经营主体与关联信息

```yaml
screen_id: CTH-02
status: BLOCKED
revision: 2
owner_domain: CTH
binding_ids:
  - BACKEND-GAP-008
product_owner_approval: OVERALL_EXPERIENCE_CONSTITUTION_30_36_ONLY
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: NON_AUTHORITATIVE_EXPLORATION_ONLY
reviewer: Codex delegated CTH-02 source review
reviewed_at: 2026-09-20
approval_reference: Product Owner approval of App / Experience Constitution §§30–36; this is not CTH-02 acceptance
```

## 1. User problem and product invariant

- **Role / authorized context:** CTH operator. The CTH Subject Registry returns rows only after an authenticated account and `subject_registry` / `read` permission for CTH. That registry permission allows browsing selection metadata; it does not authorize business data for an individual Subject.
- **User task:** review the CTH business-subject list and see whether verified links to business units, brands and formats are available.
- **Completion signal for this bounded App slice:** show only the CTH list's approved basic details; label missing verified links as `资料暂缺` until their canonical owner and Evidence lineage exist.
- **Invariant:** CTH remains Subject-first. Reading the registry does not choose or switch the live Subject, alter ownership, or authorize Subject-scoped business data. Product identity, subject identity and context switching are separate concerns.
- **Out of scope:** changing current Subject, calling the CTH-02 shared screen aggregate, using `subject_context.current_scope()` as a selected Subject, inferring relationships from category distribution, using the static brand directory or brand APIs as ownership, displaying Evidence-less relationship rows, or creating/editing registry records.

## 2. Route, entry and return

- **Entry:** open from the CTH-01 Shell header action `浏览 CTH 主体登记目录`. CTH-02 is a nested CTH workflow, not a sixth top-level destination. On phone the same five destinations remain visible and CTH stays selected.
- **Required context:** the App holds a Product Core runtime session plus an account session. Runtime identity uses the existing Basic Auth contract; the account session comes from `POST /v4/auth/login` and supplies a Bearer token for this registry request. The server checks CTH `subject_registry` read permission. Subject-specific business authorization is not present in this list response.
- **Current call:** `GET /api/settings/subjects?domain_id=CTH` through `LumenisCoreClient.settingsSubjects()` and `CoreCth02Repository.loadDirectory()`, with the account Bearer token. This is a read-only selection-metadata request. There is no pagination/cancellation contract or write effect.
- **Authorization source:** `subject_registry.get_subjects()` calls `lumenis.auth.service.get_current_user()` and `account.authorization.check_dual_domain_permission(user_id, "CTH", module="subject_registry", action="read")`. A 401, 403 or permission-service 503 exposes no Subject rows in the App.
- **Exit / Trace / Return:** the Shell back action returns to CTH-01 and preserves the active CTH destination and Product Core context. No Subject selection, context switch, business-data navigation, relationship expansion or Evidence trace is implemented. Refresh rereads only the registry list.

## 3. Verified data and callable bindings

| Priority | UI field / action | Current owner | Exact source / callable | Definition and missing behavior | Binding / Evidence |
| --- | --- | --- | --- | --- | --- |
| P0 | CTH directory access | SYSTEM Account / Permission | `subject_registry.get_subjects()`; account `get_current_user()` then `check_dual_domain_permission(..., "CTH", module="subject_registry", action="read")` | 401 = no account identity; 403 = CTH registry permission denied; 503 = authorization unavailable. In all cases render no row data. | `subject_registry.py`; route-level source verified. This does not establish per-Subject business authorization. |
| P1 | Subject ID, Chinese/English name, type and industry | CTH Subject Registry | `GET /api/settings/subjects?domain_id=CTH`; response `source=lumenis_subject_registry`, `selection_only=true`, `domains[]`, `subjects[]` | App accepts only `ok=true`, `selection_only=true`, a returned CTH/CTH domain, and rows with `domain_id=CTH`. It renders `subject_id`, `name_zh` (else `name_en`), `subject_type_name`, and `industry`; excludes keywords and timestamps. Empty authorized list is an empty registry, not an access grant. | `subject_registry.py::_row_to_dict`, `get_subjects`; `BACKEND-GAP-008`; no Evidence lineage is asserted. |
| P1 | Subject → business unit ownership | CTH canonical MDM / business-unit owner | No verified relation API or source callable | Always NOT_COLLECTED. No edge, count or owner is inferred from categories or another Subject's current context. | Required relation and source owner UNKNOWN; no relation Evidence returned. |
| P1 | Business unit → brand / format ownership | CTH canonical brand/lease/format owner | No verified relation API or source callable | Always NOT_COLLECTED. Static brand directory and product-level brand lists do not establish CTH Subject ownership. | Required relation and source owner UNKNOWN; no relation Evidence returned. |
| BLOCKED | Subject-level business profile, note/category aggregation, context switch | CTH Product Core / context owner | Existing `_build_cth02()` reads current scope, category distribution and note count; it is not actor-to-selected-Subject authorized. No verified context-switch command is bound to this screen. | Do not call the shared screen endpoint or use the current-scope aggregate. Do not switch context. | `experience_screens.py::_build_cth02`; actor/Subject READ Permission and Evidence lineage unresolved. |

No fixture fields, global aggregates, static directory entries or inferred relations are used. The API's `selection_only` field limits this registry contract; it is not an App-side authorization decision.

## 4. State and recovery matrix

| State | Trigger/evidence | User-visible meaning | Available actions | Recovery | Acceptance |
| --- | --- | --- | --- | --- | --- |
| Loading | Registry GET in progress | 正在查看 CTH 经营主体名单 | None; announce busy | Keep all subject data hidden | CTH02-W-01 |
| Empty | Authenticated, CTH read permitted, response has `selection_only=true`, `domains` includes CTH and `subjects=[]` | 当前 CTH 经营主体名单中暂无主体。 | Refresh | No fixture fallback | CTH02-W-04 |
| Not collected | No relation source / lineage | 当前名单未提供已核实的主体与业务单元、品牌及业态关联资料；两项关联资料均显示“资料暂缺” | None | Show the missing source/owner boundary | CTH02-W-03 |
| Fresh | Successful registry response | 本次名单内容已显示；关联资料更新时间暂无法确认 | Refresh | Do not call this business-data freshness | CTH02-W-02 |
| Stale | No freshness policy for relationship data | 关联信息的更新时间暂不可确认 | None | Keep relation state NOT_COLLECTED | CTH02-W-03 |
| Partial | Registry entries exist but ownership graph does not | 主体基本资料可查看，关联资料暂缺 | Refresh metadata | Keep business edges hidden | CTH02-W-03 |
| Offline | Core connection failure | 暂时无法连接服务，未能读取 CTH 经营主体名单。 | Retry | Do not use cached or embedded subject rows | CTH02-W-05 |
| Sign-in required | HTTP 401 | 无法确认当前登录状态，请重新登录后查看 CTH 经营主体名单。 | Sign in, then retry | Keep all subject data hidden | CTH02-W-05 |
| List access unavailable | HTTP 403 | 当前账号无法查看 CTH 经营主体名单。名单内容未显示。 | Retry; use the account recovery surface when available | Keep all subject data hidden | CTH02-W-05 |
| Access check unavailable | HTTP 503 | 暂时无法确认您是否可以查看 CTH 经营主体名单，请稍后重试。 | Retry | Keep all subject data hidden | CTH02-W-05 |
| Error | Other HTTP or invalid contract / cross-domain row | CTH 经营主体名单暂时无法显示，请稍后重试。 (invalid response) / CTH 经营主体名单暂时无法加载，请稍后重试。 (other failure) | Retry | Keep all subject data hidden | CTH02-W-06 |
| Success / persisted | Registry GET only | 仅查看主体名单；不会保存变更或切换当前经营主体 | None | App remains on current context | CTH02-W-02 |

## 5. Purpose-built desktop composition

- **Primary hierarchy:** read-only CTH business-subject list on the left; a separate association-availability panel on the right.
- **Layout:** at 1020 logical px and wider, a 370 px registry rail and flexible ownership pane. Registry list is independently scrollable; refresh remains in the page heading.
- **Primary interaction:** none. Rows are read-only metadata, not selectors. The backend's `selection_only` contract must not be mistaken for a permissioned context-switch command.
- **Specific composition:** the list can show basic details while both association items display `资料暂缺`. Do not invent links or brand metrics.

## 6. Purpose-built mobile composition

- **Single task:** review the CTH business-subject list, then check the two missing association details.
- **Layout:** below 1020 logical px, the directory occupies the first full-width panel and the ownership state follows as separate relationship cards; list height is bounded and touch-scrollable.
- **Context and return:** no Subject selection or context mutation is offered. Back/navigation remains owned by the App Shell; refresh reloads only registry metadata.
- **Interruption:** 401 / 403 / offline states replace the directory with retryable text and reveal no cached identity data.

## 7. Actions, authorization and effects

| Action | Owner and actor/scope | Permission | Effect / lineage | Failure behavior |
| --- | --- | --- | --- | --- |
| Read CTH directory | SYSTEM Account + Subject Registry, authenticated account, requested domain CTH | Server checks `subject_registry` / `read` for product CTH | GET only; no write, context switch, Evidence emission or business-data access claim | 401/403/503 show no registry rows |
| Refresh | Same as directory read | Same server-side gate | Repeats the same GET; no idempotent mutation | Keep directory hidden while loading; then show response or failure |
| Inspect ownership availability | CTH profile UI | No business query issued | Local explanatory state only; no Evidence claim | Both relation edges remain NOT_COLLECTED |

## 8. Accessibility, motion and localization

- Business-subject rows expose name, ID, type and industry as a single screen-reader label; they are not announced as actionable controls.
- Loading is announced as a live region. Failure and retry controls have explicit labels and retain keyboard focus behavior from Material controls.
- Relation status uses the Chinese label `资料暂缺` and explanatory copy, not color alone.
- Layout changes from split to stacked based on available width; no device-orientation lock or essential animation is used.
- Chinese and English Subject names are retained from the API; long text wraps and is not truncated into a fabricated identity.

## 9. Executable acceptance

| Acceptance ID | Action / expected result | State path | Platform/input | Test layer | Evidence |
| --- | --- | --- | --- | --- | --- |
| CTH02-W-01 | Open CTH-02 while the list request is pending; no subject details appear and the screen reader announces `正在查看 CTH 经营主体名单` | Loading | Desktop/mobile | Widget | `cth02_screen_test.dart` |
| CTH02-W-02 | Return a valid CTH list; show name, ID, type and industry only, explain that list visibility does not grant access to any listed subject's business data, and do not switch the current subject | Ready | Desktop/mobile | Widget + repository | `cth02_screen_test.dart` |
| CTH02-W-03 | Show both association items with `资料暂缺`; show no inferred link or Evidence claim | Not collected | Desktop/mobile | Widget | `cth02_screen_test.dart` |
| CTH02-W-04 | Return an authorized empty CTH registry; show `当前 CTH 经营主体名单中暂无主体。` and unresolved relations | Empty | Desktop/mobile | Unit + widget | `cth02_screen_test.dart` |
| CTH02-W-05 | Return HTTP 401 / 403 / 503; show the matching sign-in, list access or access-check message above, and no subject names or IDs | Blocked | Desktop/mobile | Widget + repository | `cth02_screen_test.dart`, `cth02_repository_test.dart` |
| CTH02-W-06 | Reject `selection_only=false`, missing CTH scope, or a non-CTH row | Invalid contract | All App sizes | Unit | `cth02_screen_test.dart` |
| CTH02-W-07 | Resize between desktop and mobile | Distinct split / stacked anatomy; no overflow | 1440 px / 390 px | Widget | `cth02_screen_test.dart` |
| CTH02-W-08 | Read through the Core repository | Exactly `GET /api/settings/subjects?domain_id=CTH`; no `/api/experience/screen/CTH-02` request | Local API stub | Repository | `cth02_repository_test.dart` |
| CTH02-W-09 | Check visible text and screen-reader labels for internal system terms; ensure keywords, unused English name, timestamps, and raw server details remain hidden | All states | Desktop/mobile | Widget | `cth02_screen_test.dart` |

The above does not accept the full profile. The nested Shell entry/return and local account-auth request sequence have widget/client coverage, but authenticated acceptance against a running Product Core, per-Subject READ authorization, owner-backed relationship data, Evidence provenance, and device/runtime E2E remain unverified.

## 10. Review decision and open questions

- **Decision:** BLOCKED for full CTH-02. The implemented nested App slice is limited to a read-only CTH registry list behind the existing account/domain permission gate and explicit NOT_COLLECTED ownership states.
- **Reviewer:** Codex source review was recorded against the historical local `main` snapshot `76fbe1afcbec656fbd06c0527d011ffecf17ca75`; the current implementation change is based on `origin/main` `b4608331eacb868ff13ef74e770aa54c309ebef3`.
- **Open dependencies:** (1) authenticated App-to-Core acceptance with a real account that has CTH `subject_registry/read`; (2) the CTH-owned Subject → unit → brand/format relation model, its read Permission and Evidence lineage; (3) a separately specified and authorized context-switch workflow if the product owner wants this screen to change active Subject context.
- **Next acceptance evidence:** live authenticated API acceptance with allowed, denied and unauthenticated accounts; source-isolated relation tests after the canonical owner and callable are verified; desktop/mobile runtime E2E and Shell Trace/Return acceptance. No full CTH-02 profile data is labeled ACCEPTED / RELEASED / OPERATING by this specification.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 浏览商业主体目录与已核实关联。
- **屏幕专属呈现：** 主体列表和有证关系档案；资料暂缺不能由名称猜补
- **来源、范围与版本连续性：** 目录选择元数据不更改live Subject；正式切换经ACC-02确认
- **四端差异：** Web/Desktop列表和关系档案；Mobile搜索展开；官网不公开内部名录
- **失败与恢复：** 关系无source则资料暂缺；读权失败不推断主体不存在
- **补充验收：** 目录读与主体业务权限分开；不借静态目录授权。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

### 2026-10-09 data-to-business requirement increment — OPEN implementation/acceptance

Existing Subject selection/creation uses the real Registry and Permission; a
query alias or pending observation never creates a confirmed Subject/venue/store
relationship. Distinguish acquisition request/focus from each source's confirmed
or UNASSIGNED/PENDING entity binding. Legal pending originals stay retrievable
through their permitted source route, without populating selected-Subject business
facts or fake counts. Selecting/clearing focus preserves the existing task/return
and scope guard; cross-scope stale results remain excluded. Actual source progress,
native time, coverage/missingness and downstream CTH/BMP result use follow Global
§10 and the existing Core contracts, with unknown values shown honestly. This
updates the current screen's affected requirements, not its implementation state.
