# SYS-04 — Security and permission

```yaml
screen_id: SYS-04
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Permission
binding_ids:
  - BACKEND-GAP-039
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: SYS-04 actor × product/domain × operation/risk boundary and §36.
- Product contract: UI displays posture only; the service Permission owner authorizes every consequential operation.
- References: `KEEP_AS_EXPLORATION`; raw policy expressions and enum metadata are not a second authority.
- Anti-template check: the composition is a permission matrix plus audit boundary, not a settings dashboard or effect console.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: operator permitted to inspect a safe security posture.
- Real task: understand the visible permission level and whether an audit decision is available without seeing policy internals.
- Completion signal: safe labels and scope states are readable; no screen action grants access.
- Out of scope: token/cookie/key/session display, policy expression display, permission mutation, and effect execution.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-04` → `experience_screens._build_sys04()`; current source enumerates `PermissionLevel`/`OperationType` metadata but does not return an actor-specific decision.
- Exit: return to SYSTEM context; no operation target route is bound.
- Return: preserve shell context only. Changing Subject context, if later provided by the shell, must not grant permission.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing/safety behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Safe access level | table row `权限级别/level`; allowlisted READ/TASK/AUDIT/WRITE/DEPLOY | Unknown values become “unconfirmed”; raw policy names are discarded | BACKEND-GAP-039; `sys04_snapshot.dart` |
| P0 | User-visible scope | row scope only as controlled/unknown state | Raw scope text is never echoed | Permission boundary |
| P1 | Operation count | `truth.operation_types` length only | Missing count is unavailable; operation names are not shown | Current SYS-04 builder |
| P1 | Audit availability | `truth.audit_available` only when explicit boolean true | Missing/false stays unavailable | BACKEND-GAP-039 |

The actual actor/target/risk Permission decision is unresolved in the current screen response and must not be inferred.

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | Posture read pending | Wait or leave |
| Empty / unknown | No safe permission row or decision returned | Show binding-unavailable/unknown |
| Partial | Some levels returned but audit or scope is absent | Read-only refresh; no authorization inference |
| Offline / error | Response unavailable or malformed | Retry bounded read; clear old state |
| Blocked | 401/403 | Follow access flow; do not expose policy internals |
| Ready | Safe posture fields are returned | No write/effect action |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-04)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：密钥与数据合规（G19，闭环内）


**4. State additions**
Ready / Loading / 数据缺失 / 会话过期（提示重新登录，不切换来源）/ 权限不足。

**9. Executable acceptance**
- 所有密钥不明文落盘，日志不出现明文；撤销立即生效。
- 合规报告不依赖账号体系即可生成。

### 草图增补：用户开发者模式（G20a）


**4. States**
关闭 / 协议未完成 / 开启 / 扩展出错（自动停用该扩展并显示原因，不影响主程序）/ 备份中 / 恢复中 / 数据缺失 / 权限不足。

**9. Acceptance**
- 未逐项同意不能开启；同意记录（版本、时间）随账号保存并可导出。
- 关闭后所有用户扩展停用但保留在磁盘，可一键恢复官方状态。
- 备份可在另一台设备恢复；不需要登录也能本地备份。
- 关闭时不监听端口；令牌不明文落盘。

### Existing contract — Purpose-built desktop and web composition

- Desktop: a two-column matrix shows safe level/scope pairs; an audit panel explains server revalidation and operation count.
- Web Workspace shares the same safe projection; no effect control is shown.
- Tablet/mobile stack the matrix and audit explanation, keeping the scope label beside each level.
- No raw policy drawer, token inspector or operation button exists.



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

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：密钥与数据合规（G19，闭环内）

Web Workspace composition
Web：权限/协议/备份按步骤展示，敏感确认可取消并回原任务；刷新复核服务端许可，浏览器能力不足明确提示，不虚构本机端口控制。

### 草图增补：用户开发者模式（G20a）

Web：权限/协议/备份按步骤展示，敏感确认可取消并回原任务；刷新复核服务端许可，浏览器能力不足明确提示，不虚构本机端口控制。 本地 API 不提供（浏览器无本机端口）。


## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-04)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：密钥与数据合规（G19，闭环内）


### 草图增补：用户开发者模式（G20a）

Mobile：只读（状态、修改记录、备份列表）；开启/加载扩展需桌面端。


### Existing contract — Purpose-built mobile composition

- One task: read the current access posture and its boundary.
- Each row pairs a level with controlled/unknown scope; audit availability follows.
- Back returns to the originating SYSTEM route; refresh re-reads without changing permission.

## 7. Actions, authorization and effects

| Action | Server owner and operation | Read/write/external effect | Evidence/failure |
| --- | --- | --- | --- |
| Read posture | SYSTEM Permission; existing GET currently has only global auth gap | Read only | 401/403/offline/error are distinct |
| Execute protected operation | Existing canonical Permission decision + effect fence, not this screen | Not implemented here | No control; no fake success |

## 8. Accessibility, motion and localization

- Matrix headers and row scope states have semantic labels; status is not color-only.
- Screen readers hear “access level” and “user-visible scope”, never raw policy expressions.
- No chart alternative is required; reduced motion avoids decorative transitions.
- zh-CN/en/ko copy must not expose implementation terms or secrets and must wrap on mobile.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS04-SAFE-01 | Unknown permission names are projected to unconfirmed | Snapshot/widget tests |
| SYS04-LEAK-01 | Secret/token/policy material does not reach rendered text | Adversarial snapshot/widget tests |
| SYS04-AUTH-01 | UI cannot turn context selection or enum metadata into authorization | Source review; backend Permission acceptance pending |
| SYS04-REAL-USER-01 | Authorized operator reads current safe posture and sees unknown where actor-specific decision is absent | Authenticated runtime E2E required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; permission posture is not business coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no Subject/Brand entity sample is displayed, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade to the incomplete actor/target decision binding. Any future control requires canonical Permission, Approval, Effect Fence, Audit and rollback.
- Decision: `DESIGN_EXPLORATION`; Sol must verify server-side authorization before acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 安全理解允许范围和审计可用性。
- **屏幕专属呈现：** allowlisted安全级别、控制化scope与audit状态，不显示策略细节
- **来源、范围与版本连续性：** 真实permission仍按Actor/scope/operation服务端判定，本页不授予权限
- **四端差异：** Web/Desktop访问姿态+审计；Mobile逐行展示；官网不露策略
- **失败与恢复：** scope未知为未确认；鉴权错不泄漏敏感原因；不提供写操作
- **补充验收：** 任何画面交互均不改变权限；无证据不显示audit ready。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。

## Current projection and approved complete target (OPEN)

本节补充已批准的安全、商业操作与用户开发模式目标，保留当前 SYS-04 只读 posture；不改 frontmatter、Permission Owner、现有 route 或实现状态。集中视觉规划输入（不替代本屏现行合同）：[SYS-04完整草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-04)。

- **当前投影（保持）：** 当前读取仍为 GET /api/experience/screen/SYS-04 → experience_screens._build_sys04()；只列 PermissionLevel/OperationType 元数据，不返回 actor-specific 决策。不得显示 token/cookie/key/session、原始 policy，亦不得把元数据或 Subject 上下文当作授权。
- **完整目标与既有 Owner（OPEN）：** SYSTEM Permission/effects 与既有安全凭据、配置及开发工具 Owner 继续持有实际授权和副作用。产品计划 G19/G20 与 SYS-04 草图要求完整呈现并允许受控管理商业合规/来源保留/脱敏报告、凭据安全存储/轮换/撤销，以及用户显式开启的产品内开发者模式。用户可在已审核的风险与法律责任协议约束下开发/修改产品；协议上线前须经法务审核，未审核不得启用。依G20a还要保留账号数据备份/恢复、关闭开发者模式后恢复受限状态；SYS-04草图中的数据导出/删除/恢复必须遵循原账户、Permission与Effect Fence Owner。不得扩展为OS控制，不新增secret vault、Permission引擎或第二运行时。
- **输入、结果与权限：** 输入为当前请求的实际 actor/身份状态（可未登录；逐项由既有 Owner 判定是否需认证）、精确产品/工作区/目标、操作、凭据或扩展版本、用途、已审核协议版本与明确同意；数据控制操作仅限原 Owner 返回的账号数据范围。账号登录不是产品入口前提，本地备份仍可不登录；需账号身份的动作仅按其现有 Owner 合同认证。用户逐项同意并只授权所见范围；服务端在每项 consequential action 前重新核对 Permission、Approval 与 Effect Fence。输出是脱敏的授权/运行/合规状态、来源保留和脱敏配置版本、密钥轮换/撤销、账号数据导出/删除/恢复、备份结果或扩展版本状态，不返回秘密明文。扩展读取/分析外部材料时另遵循既有 SourceUse。
- **版本、保存、返回与恢复：** 合规设置和获准开发者配置按既有 owner/version 保存、修订、重开并可追踪 actor 与批准；关闭开发者模式应停止该模式可调用能力、保留扩展/用户资料，并提供既有 owner 的官方状态恢复路径。凭据撤销后旧凭据不可继续使用；失败/中断状态须可辨识，返回原任务不产生新的授权或副作用。具体恢复只采用既有 owner 已支持的操作。
- **未绑定与验收：** 当前 builder 不含 actor-specific Permission，也没有上述写操作绑定。每个实际 key/retention/masking/developer-mode callable、Permission decision、审批与结果回读若未由现有 owner 提供，均保持 OPEN/UNBOUND，相关操作禁用，不臆造 API。完整验收须覆盖用户同意与拒绝、协议法务审核、作用域不扩张、凭据不回显/日志泄露、轮换/撤销生效、账号数据备份/导出/删除/恢复、扩展失败隔离、关闭后不可调用、受限官方状态恢复、保存重开和真实目标表面 E2E。
