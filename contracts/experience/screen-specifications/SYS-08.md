# SYS-08 — Observability and logs

```yaml
screen_id: SYS-08
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM Observability
binding_ids:
  - BACKEND-GAP-043
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: trace waterfall/log/error separation, safe observability and §36 acceptance.
- Product contract: operational logs remain distinct from frontend logs, Evidence and business truth.
- References: `KEEP_AS_EXPLORATION`; no generic monitoring dashboard is authoritative.
- Anti-template check: inventory, trace boundary and structured records are intentionally separate; no unsupported time-series chart.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: SYSTEM operator permitted to read a sanitized observability summary.
- Real task: understand whether logs/trace records are available without exposing credentials, sessions or absolute paths.
- Completion signal: real returned inventory/records display; absent trace remains unavailable.
- Out of scope: arbitrary log download, destructive cleanup, credential inspection, path disclosure and fabricated throughput/error-rate metrics.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-08` → `experience_screens._build_sys08()` → `logger.get_log_summary()`.
- Current backend returns sanitized filename/count summary only; no verified Trace waterfall or user-scoped log permission is present.
- Return: originating SYSTEM route; no export route is bound.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing/safety behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Total files/size | KPI ids `sys08.files`, `sys08.size_mb` | Ready numeric only; offline/null is unavailable | BACKEND-GAP-043; `logger.py`; `sys08_snapshot.dart` |
| P1 | Filename/modified summary | table rows `文件/大小MB/修改` | Path-like values are redacted; file content is never shown | Current SYS-08 builder |
| P0 | Structured records | No current builder records | Empty state; no synthetic rows | SYSTEM Observability |
| P0 | Trace waterfall | No current callable | Explicit unavailable; do not draw chart | BACKEND-GAP-043 |

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | summary pending | Wait or leave |
| Empty | no file/record/trace returned | Show no data, not zero health |
| Partial | inventory exists but records/trace absent | Keep each boundary visible |
| Offline/error | logger summary unavailable/malformed | Retry bounded read; clear stale data |
| Blocked | 401/403 | Follow access flow; no export |
| Ready | sanitized source fields returned | Read only; no effect claim |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-08)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：运营与工作区生命周期（G19，闭环内）


**4. State additions**
Ready / Loading / 数据缺失（指标未采到显示缺失）/ 不可用（显示原因）。

**9. Executable acceptance**
- 备份可在另一台设备恢复；删除工作区前强制提示导出。
- 指标缺失不显示 0；检查表每项链接到证据。

### Existing contract — Purpose-built desktop and web composition

- Desktop/Web: inventory is the primary inspection panel; trace correlation and structured records are separate review surfaces.
- Tablet/mobile stack inventory → trace boundary → records.
- No throughput, error-rate or waterfall chart is rendered without a time-series/trace callable.
- Export remains visibly unavailable until actor-scoped Permission and effect Evidence exist.



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

### 崩溃诊断线索的可见边界（S06）

从失败任务/当前运行异常打开本屏：主层发生/观测时点、影响工作和已保存成果；次层只读诊断可用性/安全引用，raw堆栈、路径、会话及私人正文不投影。原fault_diagnostics支持reload-safe fatal/periodic线索，不保证全部原生死锁可捕获；现logger摘要GET不自动具备这些字段，无Owner安全投影保持OPEN。

用户可查看受控诊断范围、经原权限预览/导出包、返回任务或执行已绑定合法恢复；导出、取消、恢复请求、实际恢复和保存读回分开，不把日志存在/handler已装作为健康。Web/Windows/macOS异常+成果主辅面，iOS先影响和保留工作再可逆详情；官网不暴露内部拓扑，两OS文件交接分别验。自身智能UI只据真实trace/影响选择清单或关系，不补因果；简洁/三语/读屏保留全部关键状态。验诊断缺失、部分失败、重载/关闭线索不误报、受控导出取消、原任务继续与独立重开，不能直接开放任意日志下载或重启。

## 5A. Web Workspace composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：运营与工作区生命周期（G19，闭环内）

Web 同桌面，保留原任务与状态。

## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-08)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：运营与工作区生命周期（G19，闭环内）


Web：运行/工作区检查按任务分区，折叠细节保留关键错误与恢复入口；刷新读取真实状态，破坏性操作需现有Permission及明确确认。 手机纵排，检查表折叠。

### Existing contract — Purpose-built mobile composition

- One active task: determine what operational evidence is actually viewable.
- Keep inventory values and trace-unavailable state above optional records.
- Back/refresh is read-only; no cleanup or export action is exposed.

## 7. Actions, authorization and effects

| Action | Owner/effect | Current behavior |
| --- | --- | --- |
| Read summary | SYSTEM Observability GET; per-user scope is a backend gap | Sanitized projection only |
| Export/clear logs | Observability + Permission/effect fence | No control; unavailable |

## 8. Accessibility, motion and localization

- Inventory values and unavailable states have semantic labels; structured records, when present, are text-first.
- Absolute paths, credentials and session material are absent from the accessibility tree.
- No chart alternative is needed while trace/time series is unavailable.
- zh-CN/en/ko copy wraps; reduced motion avoids animated monitoring effects.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS08-SAFE-01 | Path-like names and sensitive log values are not rendered | Snapshot/widget adversarial tests |
| SYS08-TRUTH-01 | Missing metrics do not become zero; no trace does not become a chart | Snapshot/widget tests |
| SYS08-BOUNDARY-01 | Export/clear controls are absent without Permission/effect contracts | Source/widget review |
| SYS08-REAL-USER-01 | Operator reads a real sanitized log summary and sees trace unavailable honestly | Authenticated runtime E2E plus actor-scope decision required |

## 10. Cross-cutting gates and review

- SUBJECT SCOPE / TASK DATA QUALITY IMPACT: none; logs do not establish successful task acquisition or business-data completeness.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no business entity sample, count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified chart/export upgrade until trace, actor authorization, audit and rollback are canonical.
- Decision: `DESIGN_EXPLORATION`; Sol review and live observability acceptance remain pending.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 查看脱敏日志目录和可追溯Trace。
- **屏幕专属呈现：** 仅呈实际inventory/时间/结构化trace；无trace不画假图
- **来源、范围与版本连续性：** trace绑定合法Task/run ID后回原任务；路径和秘密在投影前脱敏
- **四端差异：** Web/Desktop摘要与trace；Mobile按Run查看；官网不公开日志
- **失败与恢复：** 文件损坏/权限不足不导出原始日志；旧数据标stale；不清理
- **补充验收：** 真实trace存在才呈现且可回Task；无绝对路径/秘密。

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

本节把只读日志/可观测性投影与已批准的工作区/租户生命周期分开；不改 frontmatter、当前 GET、SYSTEM Observability Owner 或当前能力状态。集中视觉规划输入（不替代本屏现行合同）：[SYS-08完整草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-08)。

- **当前投影（保持）：** 当前读取仍为 GET /api/experience/screen/SYS-08 → experience_screens._build_sys08() → logger.get_log_summary()，仅安全摘要；trace、结构化记录和 actor-scoped Permission 尚未绑定。保留现有禁止任意日志下载/清理、credential inspection、绝对路径与虚构指标的合同。
- **完整目标与既有 Owner（OPEN）：** G19 工作区/tenant 生命周期、运营指标/告警/诊断包沿既有 SYSTEM workspace/account、运行监控与 Shared Database/backup/Permission Owner；诊断包必须脱敏且有范围，不能包含任意原始日志或凭据。Observability 仍只拥有日志与运行可观测性，不能借 SYS-08 变成工作区业务 Owner。现有 Source Owner Index 未给出这些生命周期操作的本屏 callable，因此 exact workspace owner/callable 需沿既有 Owner Index 确认；未确认前保持 OPEN/UNBOUND，不设新 Owner。
- **输入、结果与权限：** 对工作区功能，输入为当前请求的实际 actor/身份状态（可未登录，具体动作是否需认证由既有 Owner 判定）、精确 tenant/workspace、成员操作或 backup/version 及用户确认；输出为真实成员/生命周期状态、所选备份版本、恢复结果和审计回执。每项读取/成员调整/备份/恢复/归档/删除均由既有 workspace 与 Permission Owner 核对 actor、scope、Approval 和 Effect Fence。来源资料或派生内容若被工作区内任务使用，另遵循既有 SourceUse。安全日志摘要继续使用当前 redaction，绝不以 workspace backup 授权读取原始日志或凭据。
- **保存、返回与恢复：** 用户可按既有业务要求创建/保留备份、恢复到获准设备、归档或管理成员；删除工作区前须提供明确后果和所需的可恢复备份/导出选择。每次成功操作保存 owner-defined version/receipt，返回原 workspace/task 并可重开核对；失败/中断维持准确状态并按现有 backup/restore rollback 语义恢复，不将缺失视为健康或删除成功。
- **未绑定与验收：** 当前 SYS-08 GET 不实现也不授权上述生命周期动作；无精确既有 owner callable、Permission、确认和恢复读回时，相关控件保持 OPEN/UNBOUND 并禁用。原始日志 Export/Clear 仍 unavailable，不能被生命周期目标误解为可用；G19的诊断包是另一项受控、可预览、经脱敏/范围裁剪的导出，须等既有 owner callable、Permission、Effect Fence 与目标路径确认后才可用。完整验收须在隔离且经授权的真实 workspace 中验证成员权限、备份内容/版本、跨设备恢复、归档/删除前导出提示、取消、操作回执与失败恢复；另验证真实指标/告警和诊断包不含路径/秘密/私人材料且证据范围明确。各端仅展示其真实可用状态。


### 原要求具体工作合同：工作区成员与角色变更的具体影响

在原工作区生命周期内，成员管理先读取当前工作区、当前操作者与已获准成员清单，显示成员的安全名称、当前角色、有效/待生效/已撤销状态及来源时间；没有完整清单说明覆盖未知。用户选择成员后只能看到既有Owner允许的角色/动作。变更前并读当前与拟改权限范围、受影响工作以及是否能撤销，明确确认当前成员与工作区，不把角色名称当已获权。成员变更、数据删除、账号删除是不同动作，不连带删除其作品。

SYS-08“成员”页签为左侧成员列表、中心所选成员、右侧角色变化与影响预览，底部取消/确认本次变更；备份/删除不混在同一主按钮。窄Web和iOS依列表→成员→变更预览，键盘上方保取消；Windows/macOS核多窗口陈旧版本；官网不公开成员。UI可按真实影响数选择列表或分组对照，不生成角色/权限或替用户勾选；固定表单与无AI操作保留。

仅已绑定Owner动作可提交；保留输入直到回执与独立成员状态读回，超时先查原请求，不能重复授予/撤销。当前成员权限撤回、角色表变更、最后管理能力等限制均按Owner具体结果说明，不在前端猜规则。验双人并发、取消、无权/未知、部分回执、误切工作区和冷开；无真实callable保持OPEN。

### 原G111/G127具体终态合同：真实通知偏好与只建议的主动提示

在SH-06原通知中心打开偏好：区分真实新成果、重要异常、必要决定与普通进度；静默/聚合设置不能抑制必要审批。通知详情保触发观察/时间窗、任务/结果版本、接收范围及投递状态；失败“重试通知”只作用原投递，不能重跑业务。主动提示另标建议，逐项呈观察事实、相关性推测、局限和“查看依据/回原任务/忽略”；没有用户授权不能执行所建议恢复。

构图：左三lane/过滤，中间当前通知及真实结果摘要，右“为何提示/投递记录”，偏好为可取消Sheet；重要审批固定可达，普通片段不刷满主工作。iOS通知列表→原因→原任务，返回保选中。

未送达/已送达/已读不等工作完成；静默、过期、取消后迟到、源撤回、投递未知分别标。偏好保存失败保选择并回原值，重试前核同接收范围和幂等键，避免重复通知或群组泄漏。

Public Website仅用获准真实样例说明真实通知偏好与只建议的主动提示及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可按真实重要性整理成聚合摘要和证据面，不发明告警因果或代点决定；用户可固定/关闭建议布局。价值是少打扰且不漏必要决定。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。
