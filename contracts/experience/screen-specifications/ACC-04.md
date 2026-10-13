# ACC-04 — Guard and recovery

```yaml
screen_id: ACC-04
status: DESIGN_READY
revision: 2
owner_domain: SYSTEM Permission / recovery boundary
binding_ids:
  - CODEX-ACC04-GUARD
product_owner_approval: APPROVED
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_READY
artifact_disposition: REVIEWED_RETURN_ONLY_BOUNDARY
reviewer: Sol root integration review
reviewed_at: 2026-09-26
approval_reference: ROUND-14A bounded implementation Task Card
```

## 0. User task and invariant

- User job: understand why a protected workspace action is unavailable and choose an honest recovery path.
- ACC-04 never issues credentials, grants access, retries a write, resets a session or invents a successful permission decision.
- Product-account deferral remains visible and distinct from Core transport auth and business Permission.

## 1. Route and fields

- Read route: `GET /api/experience/screen/ACC-04` via `CoreAcc04Repository`.
- Current runtime reports this target as unbound; the page must show unavailable rather than use AI-01, CTH or another screen as a permission bypass.
- Allowlist: `bound`, `source`, `guard.recovery_paths`, `guard.reason` and `generated_at`, all bounded and sanitized.

## 2. Recovery matrix

| State | Meaning | Permitted action |
| --- | --- | --- |
| Loading | guard read pending | Wait |
| Available | real guard contract returned | Use only returned host recovery callbacks |
| Unavailable / unbound | no screen contract | Recheck or return; no local grant |
| Blocked | server denied the guard read | Show denial and return/switch context if host supplies it |
| Offline / malformed | no trustworthy guard | Retry read; do not infer permission |

`retry`, `switch_context`, `request_access`, and `return` are labels only until a host callback and canonical Permission owner are provided.

## 3. Desktop/mobile and accessibility

- Desktop: guard explanation is primary, recovery paths are a clear secondary rail.
- Mobile: explanation first, recovery actions stack in server-returned order with 44px+ targets.
- Focus order, announcements and text labels distinguish unavailable, blocked and product-account-deferred; reduced motion is immediate.

## 4. Localization integration key list

Existing shared key: `screen.ACC-04`, `common.refresh`.

Feature keys: `acc04.guardUnavailable`, `acc04.guardBlocked`, `acc04.productAccountDeferred`, `acc04.recheck`, `acc04.switchContext`, `acc04.requestAccess`, `acc04.returnToWorkspace` for `zh-CN`, `en`, and `ko`. Local fallback copy is used in this bounded slice.

## 5. Executable acceptance

| ID | Acceptance | Current evidence |
| --- | --- | --- |
| ACC04-GUARD-01 | Preserve unbound guard as unavailable and sanitize reason | `acc04_feature_test.dart` |
| ACC04-EFFECT-01 | No recovery action creates a local grant or fake success | source review; host callbacks are optional and side-effect-free here |
| ACC04-REAL-01 | Hit a real denial, choose a real host recovery path and verify the protected route remains protected | Not run; requires live Permission/E2E |

## 6. REAL USER WORK / global / commercial overlay

- `REAL USER JOB`: a user encounters a real protected boundary, understands it and recovers through an authorized context or return path.
- `REAL INPUT`: live Permission/guard response and actual host recovery callbacks.
- `END-TO-END PATH`: protected route → ACC-04 → real denial/recovery → server recheck → return.
- `USER-VISIBLE RESULT`: honest blocked/unavailable/recovered state; never a fake grant.
- `FAILURE/RECOVERY`: preserve denial across retries and distinguish transport/auth from product Permission.
- `EVIDENCE`: guard response, permission audit and protected-route recheck.
- `ACCEPTANCE ASSERTION`: `BLOCKED_PENDING_LIVE_RUNTIME_E2E`.
- `RANDOM ENTITY DATA ACCEPTANCE`: sample count 0; no access decisions fabricated.
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`: none; this page reports authorization state only.
- `COMMERCIAL OVERLAY IMPACT`: `COMMERCIAL_READY=NO` until denied and recovered real flows pass.

## 7. Continuous frontier research / review decision

- `RESEARCH COMPLETE / NO JUSTIFIED UPGRADE` on 2026-09-22. Existing guard/Permission owners and explicit callback boundaries are sufficient; no new auth or recovery dependency is justified.
- On 2026-09-26, root reviewed the existing explanation/recovery composition as
  `DESIGN_READY` for return-only host navigation. The shell supplies Return to
  ACC-03 without changing the guard state, making a permission grant, retrying
  a write or exposing access-request/context-switch actions. Recheck remains
  the same guard GET. The guard binding and real authorized recovery flow stay
  `BLOCKED_PENDING_LIVE_RUNTIME_E2E`; returning to the map is not recovery proof.


2026-10-08 current target clarification: the September return-to-ACC-03 implementation above is historical source behavior. Return must restore the trusted originating route/Task and permitted context when available; ACC-03 is the fallback when no safe origin exists. Neither Return nor a UI retry is proof of permission recovery. F/W6 must bind this continuity through the existing owner; this new target remains OPEN. `CODEX-ACC04-GUARD` names the ScreenSpec slice over registry `BACKEND-GAP-004`, not a new owner.

## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 理解一项真实阻断并沿已有恢复路径返回。
- **屏幕专属呈现：** 展示发生了什么、影响哪个任务、已绑定的恢复路径
- **来源、范围与版本连续性：** 关联原Task、请求scope、operation与恢复receipt，保留未提交内容
- **四端差异：** Web/Desktop并列工作与受控说明；Mobile按阻断→影响→恢复；官网不显示内部诊断
- **失败与恢复：** unbound明确unavailable，不跳到AI或其他页绕权限
- **补充验收：** 拒绝、重试、恢复后均回原任务；无receipt不称恢复。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
