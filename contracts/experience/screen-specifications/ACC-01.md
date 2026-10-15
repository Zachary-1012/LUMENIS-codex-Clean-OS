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

- The screen follows the Experience Constitution's quiet identity / entry surface. It includes optional sign-in/account settings through the existing identity owner, with direct workspace entry retained.
- Product account onboarding and settings are in-loop. Core transport authorization, product account identity and media-session authorization remain separate.
- The composition is purpose-built: one calm entry/status surface plus a separate boundary explanation, not a generic dashboard or repeated card template.
- Historical mockups and screenshots are non-authoritative and are not copied into the implementation.

## 1. User problem and route

- User job: confirm that the internal-beta workspace entry is available and continue through the host-provided route.
- Read route: `GET /api/experience/runtime/identity`, via `LumenisCoreClient.runtimeIdentity()`.
- Email verification and free Google sign-in use the account owner; Apple requires developer-account activation. No password collection or account wall is introduced.
- Continue is a host callback only. If the host does not supply a route, the button remains visibly unavailable; the page never claims navigation succeeded.

## 2. Verified fields and allowlist

| UI field | Source | Allowlist / missing state |
| --- | --- | --- |
| Entry status | `ok`, `runtime_guardian.overall` | `connected`/`healthy`, `degraded`, `unavailable`, `unknown`; `ok=true` alone never means connected |
| Current view label | `focus_context.display_name` | safe display text only; path, secret and provider-like values are discarded |
| Generated time | `generated_at` | bounded safe text; omitted when absent |
| Product account boundary | product policy | optional sign-in/settings, independent of Core transport authorization |

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
- Keyboard order is heading → status → host continue → boundary statement. Focus enters optional sign-in only on user choice; dismissal returns to the originating task.

## 5. Purpose-built desktop composition

已批准目标来源：`ACC-01-ADD-account-settings.md`, `ACC-01-ADD-sign-in.md`。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：账号设置 rev3（类 ChatGPT）

```
设置                                                      [×]
┌────────────┬────────────────────────────────────────────┐
│ 通用       │ 主题 · 语言 · 时区 · 通知 · 减少动态效果    │
│ 账号       │ 头像 显示名 邮箱[更改]                      │
│            │ 登录方式：邮箱✓ Apple[关联] Google[关联]    │
│            │  （至少保留一种）                           │
│ 安全       │ 设备与会话：设备/位置/最近活动 [退出]       │
│            │  当前会话标「当前」                         │
│            │  [退出所有设备]（含本机，二次确认）         │
│            │  新设备登录邮件提醒 ✓                       │
│ 模型与API  │ (●) 自有模型 ( ) 我的 API → AI-05           │
│ 连接器     │ GitHub / MCP → AI-04 · 平台登录 → SYS-06    │
│ 用量       │ 模型调用 · 采集任务 · 存储；未统计=数据缺失 │
│ 数据控制   │ 改进模型 [允许/不允许]（首次使用时你选的）  │
│            │ [导出全部数据] 完成后通知，链接限时有效     │
│            │ [备份账号数据] [从备份恢复]                 │
│            │ [删除全部对话]                              │
│            │ [删除账号] 输入邮箱确认 → 30 天内可撤销     │
│ 开发者     │ 用户开发者模式 → SYS-04（需先接受协议）     │
│ 关于       │ 版本 · 条款 · 隐私    [退出登录]            │
└────────────┴────────────────────────────────────────────┘
未登录：账号/安全显示「未登录 · [登录或注册]」；其余分区照常可用（本地导出/备份）。
```

**4. States**
正常 / 加载 / 数据缺失（不补 0/50）/ 账号服务不可用（账号、安全只读并说明原因，其他正常，无自动回退）/ 导出或备份中（进度，可取消）/ 删除待生效（剩余 N 天 + [撤销删除]）/ 会话状态未知（显示「状态未知」，可用退出所有设备）。

**9. Acceptance**
- 三种方式可互相关联/解除，最后一种不可解除。
- 删除：30 天内重新登录或点撤销即恢复；满 30 天彻底清除（写入 G19 合规）。
- 导出含资料、主体、采集数据、报告、对话；同账号限时下载。
- 自带 API Key 仅本机安全存储；三语；无主体写死。

Apple 未启用时各端不显示可用登录按钮；改进使用数据选择不自动授予模型训练或受限资料使用权限。验证码重发间隔取实际服务端值。

### 草图增补：登录/注册（邮箱 · Apple · Google）rev3

```
┌──────────────── 序境 LUMENIS ────────────────┐
│             登录或创建账号                    │
│  [ Apple 登录 ]   [ Google 登录 ]             │
│  ─────────── 或 ───────────                  │
│  邮箱 [ name@example.com ]  [继续]            │
│   → 6 位验证码（无密码）                      │
│  [ 先不登录，直接使用 ] ← 始终可见            │
│  条款 · 隐私 · 中文 / English / 한국어        │
└───────────────────────────────────────────────┘
验证码页：xx@xx [□□□□□□] [重新发送 59s] [换个邮箱]
首次进入（登录或不登录都问一次）：
┌ 是否允许用你的使用数据改进序境模型？ ┐
│ [允许]  [不允许]   之后可在 设置›数据控制 修改 │
└──────────────────────────────────────┘（无预选项）
```

**4B. Apple 按钮启用条件：取得 Apple Developer 账号（$99/年）前不显示 Apple 按钮，仅显示 Google 与邮箱验证码；两者均为免费方式。启用后布局如上图。**


**4. States**
正常 / 加载（可取消）/ 验证码错或过期（行内提示+重发）/ 第三方取消授权（回本页不弹错）/ 登录服务不可用（「登录暂不可用，可先不登录继续使用」，不自动换方式）/ 同邮箱已有账号（核验现有账号控制权后询问关联，不自动合并）/ Apple 隐藏邮箱（提示继续用 Apple 或在设置关联真实邮箱）/ 删除待生效账号登录（「账号将于 N 天后删除」[恢复账号] [继续删除]）。

**9. Acceptance**
- 不登录全部主流程可用；本地数据登录后由用户选「合并 / 保持本地」。
- 经服务端核实邮箱与现有账号控制权后，由用户确认关联方式；新设备登录发邮件提醒。
- 改进模型询问无预选，未回答前按「不允许」处理且再次询问。
- 三语；无主体写死；不存明文密码。

Apple 未启用时各端不显示可用登录按钮；改进使用数据选择不自动授予模型训练或受限资料使用权限。验证码重发间隔取实际服务端值。

### Existing contract — Authorization, effects, and accessibility

- Read authorization remains Core-owned. The screen does not interpret transport success as customer identity or business permission.
- `Enter` activates Continue only when the host callback exists; Escape / hardware Back returns to the host shell.
- Screen readers receive status labels and the account-boundary statement as text, not color alone. Long labels wrap at enlarged text sizes.
- Reduced motion uses immediate state changes.



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

### 草图增补：账号设置 rev3（类 ChatGPT）

Web：同桌面，会话含浏览器会话。


### 草图增补：登录/注册（邮箱 · Apple · Google）rev3

Web：设置分区按宽度切换侧栏/二级页；保留浏览器会话状态、前进返回和未保存偏好；授权取消/成功均返回原任务。 Apple/Google 授权后回原页，工作不丢。


## 6. Purpose-built mobile composition

### 草图增补：账号设置 rev3（类 ChatGPT）

Mobile：一级列表 → 二级页；删除账号在数据控制底部（红色）。


### 草图增补：登录/注册（邮箱 · Apple · Google）rev3

Mobile：Logo → Apple（iOS 置顶）→ Google → 邮箱 → 继续 → 底部「先不登录」。


### Existing contract — Localization integration key list

Existing shared keys: `screen.ACC-01`, `common.refresh`.

Feature integration keys to register with the canonical l10n owner: `acc01.betaEntry`, `acc01.entryStatus`, `acc01.currentView`, `acc01.productAccountBoundary`, `acc01.enterWorkspace`, `acc01.hostReturnPath`, `acc01.optionalSignIn` for `zh-CN`, `en`, and `ko`. The current bounded slice uses an explicit three-locale fallback map because shared l10n files are outside scope.

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

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
