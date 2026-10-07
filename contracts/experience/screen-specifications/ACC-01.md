# ACC-01 — Workspace entry and account boundary

```yaml
screen_id: ACC-01
status: DESIGN_READY
revision: 2
owner_domain: SYSTEM / Experience entry
binding_ids:
  - CODEX-ACC01-RUNTIME-IDENTITY
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
artifact_disposition: REVIEWED_BOUNDED_ENTRY_NAVIGATION
reviewer: Sol root integration review
reviewed_at: 2026-09-26
approval_reference: ROUND-14A bounded implementation Task Card
```

## 0. Authority and invariant

- The screen follows the Experience Constitution's quiet identity / entry surface. It is not a product-account sign-in page and does not create a new auth owner.
- Product account onboarding is deferred until after internal beta. Core transport authorization, product account identity and media-session authorization remain separate.
- The composition is purpose-built: one calm entry/status surface plus a separate boundary explanation, not a generic dashboard or repeated card template.
- Historical mockups and screenshots are non-authoritative and are not copied into the implementation.

## 1. User problem and route

- User job: confirm that the internal-beta workspace entry is available and continue through the host-provided route.
- Read route: `GET /api/experience/runtime/identity`, via `LumenisCoreClient.runtimeIdentity()`.
- No account creation, password, credential reset or external effect is exposed here.
- Continue is a host callback only. If the host does not supply a route, the button remains visibly unavailable; the page never claims navigation succeeded.

## 2. Verified fields and allowlist

| UI field | Source | Allowlist / missing state |
| --- | --- | --- |
| Entry status | `ok`, `runtime_guardian.overall` | `connected`/`healthy`, `degraded`, `unavailable`, `unknown`; `ok=true` alone never means connected |
| Current view label | `focus_context.display_name` | safe display text only; path, secret and provider-like values are discarded |
| Generated time | `generated_at` | bounded safe text; omitted when absent |
| Product account boundary | product policy | fixed statement that account is deferred; not inferred from Core auth |

The client never displays API paths, database names, server paths, tokens, cookies, provider/model identifiers or raw errors.

## 3. State and recovery matrix

| State | Meaning | Action |
| --- | --- | --- |
| Loading | Runtime entry is being read | Wait |
| Healthy / degraded | Runtime guardian explicitly reports the state | Continue only through host callback; refresh is host-owned |
| Unknown | Identity envelope is valid but the guardian does not explicitly report connectivity | Show unconfirmed state; do not infer a ready entry |
| Unavailable | Runtime did not confirm the entry | Retry the read; do not create a local account |
| 401 / 403 | Transport or screen access is not confirmed | Show the access-specific recovery copy; do not turn it into a product-account wall |
| Offline / error | Read failed or response was malformed | Retry; preserve no fabricated workspace state |

## 4. Desktop and mobile composition

- Desktop: bounded two-region surface, entry status first and the account boundary beside it; maximum width 1180px.
- Mobile: one vertical entry surface followed by the boundary explanation; controls remain full width and touch-sized.
- Keyboard order is heading → status → host continue → boundary statement. Focus is not moved into a nonexistent login form.

## 5. Authorization, effects, and accessibility

- Read authorization remains Core-owned. The screen does not interpret transport success as customer identity or business permission.
- `Enter` activates Continue only when the host callback exists; Escape / hardware Back returns to the host shell.
- Screen readers receive status labels and the account-boundary statement as text, not color alone. Long labels wrap at enlarged text sizes.
- Reduced motion uses immediate state changes.

## 6. Localization integration key list

Existing shared keys: `screen.ACC-01`, `common.refresh`.

Feature integration keys to register with the canonical l10n owner: `acc01.betaEntry`, `acc01.entryStatus`, `acc01.currentView`, `acc01.productAccountBoundary`, `acc01.enterWorkspace`, `acc01.hostReturnPath`, `acc01.accountAfterBeta` for `zh-CN`, `en`, and `ko`. The current bounded slice uses an explicit three-locale fallback map because shared l10n files are outside scope.

## 7. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC01-READ-01 | Parse only the runtime identity allowlist and preserve unknown/unavailable states; `identity.ok` alone cannot connect the runtime | `acc01_feature_test.dart` |
| ACC01-BETA-01 | Render the internal-beta entry without a global product-account wall | `acc01_feature_test.dart` widget test |
| ACC01-SAFE-01 | Hostile display metadata never reaches visible text | `acc01_feature_test.dart` |
| ACC01-REAL-01 | From a real App entry, read the live identity, continue through the host route, and observe the returned shell state | Not run in this bounded batch; runtime/E2E required |

## 8. REAL USER WORK E2E ACCEPTANCE / delivery card

- `REAL USER JOB`: internal-beta user opens the App, confirms the actual entry state, and enters the already authorized workspace without creating a product account.
- `REAL INPUT`: live Core identity response and the host's real continuation callback.
- `END-TO-END PATH`: App Shell → ACC-01 → runtime identity → ACC-03 launch map → chosen existing workspace; existing shell navigation returns to ACC-01.
- `USER-VISIBLE RESULT`: real status, explicit account boundary, and a real returned workspace or an honest unavailable state.
- `FAILURE/RECOVERY`: distinguish 401, 403, offline, malformed response and missing host route.
- `EVIDENCE`: current commit, live response, callback return, and no product-account side effect.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`; widget/parser evidence is not commercial acceptance.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0 in this UI-only batch; no registry data fabricated.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: entry surface does not claim global data maturity; all data coverage fields remain not applicable.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` until live entry/return and all target surfaces are verified.

## 9. Continuous frontier research / capability evolution

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` for this bounded slice. Local Flutter 3.47.5 and the repository's existing responsive/accessibility patterns were inspected on 2026-09-22; no dependency or alternate auth surface is justified.
- Decision: `ADAPT` the existing Core client, `LayoutBuilder`, Material semantics and three-locale fallback; do not add a second account or runtime owner.
- Any future account capability must be versioned by the canonical identity/Permission owner and pass a new screen review, effect fence, E2E and rollback gate.

## 10. Review decision

The existing quiet entry composition is reviewed as `DESIGN_READY` for bounded
host navigation. The mounted shell supplies Continue to ACC-03, the existing
workspace launch map; this does not require ACC-02 selection or product login.
From the map, the user chooses an existing CTH/BMP/AI entry. Runtime status
remains visible and navigation does not attest health or business permission.
An unmounted screen without a host callback retains its unavailable button.
Runtime and target-surface acceptance remain separate and unaccepted until
recorded in the owning Round evidence. No product-account wall is authorized.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 确认内部工作区入口可用并继续宿主指定目标。
- **屏幕专属呈现：** 显示入口状态与宿主提供的继续动作；无 callback 不伪造路由或账户流程
- **来源、范围与版本连续性：** 传递宿主实际 route 与原任务位置，失败时保留入口
- **四端差异：** Web接浏览器route；Desktop回原窗口；Mobile恢复原任务；官网只说明公开入口
- **失败与恢复：** 身份失败、离线、callback缺失分别标识；重试仅读取identity
- **补充验收：** 有/无真实callback分别验证；只有真实导航成功才报告继续。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。保留序境二维手绘水彩/版画色彩语言与有功能含义的线性控件；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，只借鉴手绘平面笔触与色彩，不复制参考人物、不用3D质感。

### 可编辑设计到源码映射（2026-10-08 审计采用）

F 在 Product Owner 明确恢复后，在本屏现有规范中补齐同一条链；本轮只更新规则，不创建或修改 Figma 工程：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
