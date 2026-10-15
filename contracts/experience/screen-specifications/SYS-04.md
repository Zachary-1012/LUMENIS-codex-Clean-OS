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

已批准目标来源：`SYS-04-ADD-keys-compliance.md`, `SYS-04-ADD-user-developer-mode.md`。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：密钥与数据合规（G19，闭环内）

```
安全与权限 › 密钥与合规
密钥
  我的 API Key    ••••3f2a  安全存储 ✓  [轮换] [删除]
  连接器令牌      GitHub ✓  MCP×2 ✓      [逐个撤销]
  平台登录会话    小红书 ✓  抖音 已过期 → [重新登录]（内置浏览器弹窗）
数据合规
  采集来源清单    按用途列出，每条可查看来源与重构记录
  保留期限        [90 天 ▾]（用户选择）
  个人信息处理    默认脱敏 ✓    [查看处理日志]
  [导出合规报告]
```

**4. State additions**
Ready / Loading / 数据缺失 / 会话过期（提示重新登录，不切换来源）/ 权限不足。

**9. Executable acceptance**
- 所有密钥不明文落盘，日志不出现明文；撤销立即生效。
- 合规报告不依赖账号体系即可生成。

### 草图增补：用户开发者模式（G20a）

```
设置 › 开发者 › 用户开发者模式           [ 关 ○ ]
开启前（必须逐项勾选，[我同意并开启] 才可点）：
┌ 风险与责任协议 v1 ──────────────────────────────┐
│ □ 自行开发/修改的代码拥有与序境相同的权限，        │
│   仅在现有授权范围内读写文件、联网与调用获准能力         │
│ □ 由此造成的数据丢失、账号封禁、违法违规后果       │
│   由我本人承担，责任边界按经审核适用条款说明，不以勾选框免除法定义务                 │
│ □ 修改后的版本不享受官方更新保证，问题需先恢复     │
│ □ 开启前已备份账号数据   [立即备份]               │
│ [查看完整条款]   [取消]   [我同意并开启]           │
└──────────────────────────────────────────────────┘
开启后：
  顶部常驻条：⚠ 开发者模式 · 已修改 3 处   [关闭并恢复]
  本地扩展   [加载本地文件夹]  列表：名称/版本/权限/[停用]
  修改记录   每次修改的文件与时间，可逐条撤销
  本地 API   http://127.0.0.1:xxxx  令牌 •••• [复制][重置]
  调用日志   最近 100 次（脱敏）
  备份/恢复  [备份账号数据] [从备份恢复] 列表：时间/大小
  协议记录   v1 · 2026-10-14 同意 · [撤回同意=关闭模式]
```

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

### 草图增补：密钥与数据合规（G19，闭环内）

Web Workspace composition
Web：权限/协议/备份按步骤展示，敏感确认可取消并回原任务；刷新复核服务端许可，浏览器能力不足明确提示，不虚构本机端口控制。

### 草图增补：用户开发者模式（G20a）

Web：权限/协议/备份按步骤展示，敏感确认可取消并回原任务；刷新复核服务端许可，浏览器能力不足明确提示，不虚构本机端口控制。 本地 API 不提供（浏览器无本机端口）。


## 6. Purpose-built mobile composition

### 草图增补：密钥与数据合规（G19，闭环内）

Purpose-built mobile composition
分组卡片纵排，操作收进「…」菜单。

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
