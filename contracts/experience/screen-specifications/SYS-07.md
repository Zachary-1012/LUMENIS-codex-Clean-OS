# SYS-07 — Evaluation and acceptance

```yaml
screen_id: SYS-07
status: DESIGN_EXPLORATION
revision: 2
owner_domain: SYSTEM Security / AI Gateway
binding_ids:
  - BACKEND-GAP-042
product_owner_approval: APPROVED_FINAL_RELEASE_TARGET_2026-10-07
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: M target-convergence review
reviewed_at: 2026-10-07
approval_reference: Product Owner-approved final product closure requires same-SHA Product/App/Critical E2E, packaging/runtime/user-repeat/release evidence; current builder remains incomplete
```

## 0. Authority basis and artifact disposition

- Constitution basis: evaluation/acceptance blueprint and six-gate truth semantics; registration/configuration is not acceptance.
- Product contract: real result → Evidence → evaluation; PARTIAL/UNKNOWN cannot become PASS.
- References: `KEEP_AS_EXPLORATION`; fixture gates are not production evidence.
- Anti-template check: evidence posture, gates and returned checks form a review sequence, not a scorecard dashboard.
- Sol design decision: `DESIGN_EXPLORATION`; the current builder remains a bounded read-only slice.

## 0.1 Approved final release-evidence target — 2026-10-07

SYS-07's final product role is to make release truth legible. It consumes existing C6/M release evidence and does not itself run acceptance actions or change release state.

Final evidence order:

```text
candidate source SHA
→ source/config/DB/Experience checks
→ Product Gate
→ App Gate
→ Critical E2E
→ package/build artifact where promised
→ loaded runtime identity matches the accepted release composition
→ rollback/recovery evidence
→ Product Owner repeats the core job
→ RELEASED
→ real elapsed operating evidence
→ OPERATING
```

Each stage reports PASS / FAIL / NOT_RUN / UNKNOWN / STALE with exact evidence, time and SHA when available. An earlier green stage never hides a later missing stage. Evidence from different SHAs stays visibly separate until the accepted release composition proves them compatible. Source presence, a build, or an HTTP response alone is not release.

Public Website, Web Workspace, Desktop and Mobile keep distinct release roles. Only actually published/supported packages are shown as downloadable; unavailable packages remain explicitly unavailable.

## 1. User problem and product invariant

- Authorized context: SYSTEM/security operator reading returned evaluation checks.
- Real task: see which checks actually returned and whether evidence-backed production gates are complete.
- Completion signal: unknown/incomplete posture stays visible; no acceptance pass is claimed from registered skills or OWASP count alone.
- Out of scope: executing tests, promoting skills, changing AI policy, autonomous approval, or declaring release.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-07` → `experience_screens._build_sys07()` → `ai_governance.get_owasp_security_status()` and `get_skills_light_status()`.
- Current source returns enabled checks and skill light status, not a complete production gate record.
- Return: originating SYSTEM route; no promotion or release route is bound.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing-data behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Returned OWASP checks | table rows from `checks_enabled` | Empty remains no verifiable check; no pass inference | BACKEND-GAP-042; `ai_governance.py` |
| P1 | OWASP/skill counts | KPI ids `sys07.owasp_checks`, `sys07.skills` | Only `ready` numeric state displays a value; empty 0 is not fabricated | Current SYS-07 builder |
| P0 | Acceptance gates | No current verified gate section in builder | Screen stays UNKNOWN until real gate + evidence rows arrive | Evaluation owner |
| P1 | Evidence reference | Only explicit safe reference fields | Missing evidence is not a pass | `sys07_snapshot.dart` |

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | checks pending | Wait or leave |
| Empty | no checks/gates returned | Show unknown/no data |
| Partial | checks returned but gates/evidence incomplete | Keep “no PASS conclusion”; refresh or follow evidence workflow outside this page |
| Offline/error | read failed or malformed | Retry bounded GET; clear old state |
| Blocked | 401/403 | Follow access flow; no promotion action |
| Ready | checks returned | Still not production acceptance until complete gate evidence exists |

## 5. Purpose-built desktop composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：创始人内部开发者模式（G20b）


**4. States**
空闲 / 上传中 / 测试中 / 测试失败（阻止发布）/ 待发布 / 分批中 / 已暂停 / 已回滚 / 指标缺失（显示「数据缺失」，不显示 0，缺失时不自动扩大批次）。

**9. Acceptance**
- 非创始人账号看不到入口，接口拒绝。
- 测试未全绿、未签名均无法发布。
- 用户端自动更新校验签名；可在 设置›通用 选择「自动更新 / 仅提醒」。
- 回滚后所有批次用户在下次检查时得到稳定版。

复用现有发布 Owner；检查全绿只是必要条件，实际发布仍须当前授权与适用 Gate。示例版本/百分比/报错数不充当遥测。

### Existing contract — Purpose-built desktop and web composition

- Desktop/Web: posture rail makes the acceptance boundary explicit; returned checks and evidence-backed gates occupy separate review panels.
- Tablet/mobile stack posture → gates → checks; no pass badge is shown from count alone.
- No score, release button or trend chart is rendered without a canonical callable.



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

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：创始人内部开发者模式（G20b）


## 6. Purpose-built mobile composition

> 集中视觉规划输入（不替代本屏现行合同）：[对应草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：创始人内部开发者模式（G20b）

 Mobile：只看状态，可[暂停][回滚]，不可上传。


### Existing contract — Purpose-built mobile composition

- One active question: “what evidence is actually present, and what remains unknown?”
- Posture stays first; every gate/check shows state and evidence reference or not returned.
- Back/refresh is safe and read-only; no evaluation mutation occurs.

## 7. Actions, authorization and effects

| Action | Owner/effect | Current behavior |
| --- | --- | --- |
| Read checks | SYSTEM Security / AI Gateway GET | Read only; access failures are distinct |
| Approve/promote/release | Evaluation/Permission owner, not this screen | No control; no autonomous effect |

## 8. Accessibility, motion and localization

- Unknown, partial and ready states are textual and semantically announced.
- Evidence references are readable text; no chart alternative is needed.
- Long check names wrap; zh-CN/en/ko copy keeps the “not PASS” boundary explicit.
- Reduced motion avoids animated pass-like celebrations.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS07-UNKNOWN-01 | Missing acceptance gate evidence remains UNKNOWN | Snapshot/widget tests |
| SYS07-NO-PASS-01 | OWASP/skill registration does not become production acceptance | Snapshot/widget/source tests |
| SYS07-EVIDENCE-01 | A gate is not complete without explicit evidence and ready/pass result | Future contract test; current screen fails closed |
| SYS07-REAL-USER-01 | Operator reviews a real check and sees exactly why production acceptance remains incomplete | Authenticated runtime E2E plus evaluation Evidence required |
| SYS07-SHA-02 | Product/App/Critical/runtime/package evidence carries its actual SHA/version; different SHAs remain visibly separate until an accepted release composition proves compatibility | Future release-evidence contract + widget test |
| SYS07-LADDER-02 | PASS/FAIL/NOT_RUN/UNKNOWN/STALE are shown for every promised release stage; an earlier PASS never hides a missing later stage | Future widget/contract test |
| SYS07-RELEASE-02 | RELEASED requires the accepted release composition plus applicable package/runtime/rollback and Product Owner repeat evidence; OPERATING requires later real operating evidence | Future same-release E2E + Product Owner acceptance |
| SYS07-SURFACE-02 | Public Website/Web/Desktop/Mobile show only their actually promised package/runtime state; an unavailable installer is not fabricated or borrowed from another surface | Future cross-surface release E2E |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; evaluation posture does not assert commercial/brand/Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no entity values, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade from registered-status display to acceptance. Promotion remains versioned, evaluated, approved, observable and reversible.
- Decision: `DESIGN_EXPLORATION`; Sol review and real Evidence-backed acceptance are pending.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 检查实际Evaluation gate证据和未完成项。
- **屏幕专属呈现：** check→scope→run version→Evidence→状态，分开blocked/unknown/pass
- **来源、范围与版本连续性：** 关联实际Evaluation版本；审批推广由相应owner执行
- **四端差异：** Web/Desktop检查与证据；Mobile先阻断；官网只讲真实验证能力
- **失败与恢复：** 无样本/证据不足非通过；本页不启动测试或发布
- **补充验收：** 状态可追到证据；空清单不显示pass。

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

本节区分当前评估/安全状态读模型与已批准的内部开发者发布工作流；不更改 frontmatter、Evaluation 或 C6/M release Owner、当前读取或验收状态。集中视觉规划输入（不替代本屏现行合同）：[SYS-07完整草图](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。

- **当前投影（保持）：** 当前读取仍为 GET /api/experience/screen/SYS-07 → experience_screens._build_sys07() → 既有 OWASP 与 Skills posture 查询。它不运行测试、不批准、不晋升版本、不发布，也不证明 RELEASED/OPERATING；各状态必须依本规范已有证据合同显示。
- **完整目标与既有 Owner（OPEN）：** SYSTEM Evaluation 继续拥有评估证据；C6/M 与既有发布/部署、签名、审批及回滚 Owner 拥有 G20b 开发者内部发布流程。已批准目标为创始人专用内部发布：上传同一版本的代码更新，运行约定的构建/单元/集成/真实端到端/安全检查，任一失败即停止；测试全绿并满足签名/批准/资源/回滚条件后发布，签名后按已批准策略分批自动更新。缺少指标时不得扩大批次；可以按既有 Owner 授权暂停或回滚至验证过的稳定包/数据恢复方案。所有步骤仍经既有 Permission/Approval/effect owner；它不能扩大为未经批准的公网部署。
- **输入、结果与权限：** 输入是确切 artifact/package hash、源版本、测试与签名证据、批准者和目标发布阶段。输出逐项展示 PASS/FAIL/NOT_RUN/UNKNOWN/STALE 及其证据版本、当前审批与真实发布阶段；unit test green 不构成发布许可。非创始人不得看到内部上传入口且服务端须拒绝。每个上传、测试运行、签名、stage/advance、pause、rollback 动作均需既有 Owner 的精确 Permission、Approval、Effect Fence 和目标环境授权；iOS只呈现审阅状态及原权限允许的暂停/回滚，不上传。评价/模型结果仍是派生数据，原始 Evidence 不被覆盖。
- **版本、保存、返回与恢复：** 所有检查与状态绑定同一 source/artifact/package SHA 和 release stage，保留通过、失败与缺失 Evidence；用户返回原任务可继续检查同一候选版本。中断、拒绝或失败显示准确阶段和恢复依据；只可经既有 owner 的批准/回滚机制回到已知稳定版本，不能自动重试发布或把旧 PASS 复用到新 SHA。
- **未绑定与验收：** 当前 SYS-07 screen binding 仅供读取，产品计划中的 G20b 动作没有由本屏证明 callable。上传/签名/发布/回滚均保持 OPEN/UNBOUND，直至既有 C6/M release owner 提供真实 route、角色/Permission、Approval 和 readback；不得新增接口、自动批准或将测试状态升级为发布状态。验收须在被授权的内部目标环境完成同版审查、非创始人拒绝、测试未全绿或未签名阻断发布、签名校验、真实分批状态、指标缺失不扩批、暂停/回滚与重开读回，并分别证明 RELEASED 与 OPERATING 的适用门槛；本补丁本身不启动任何发布。

### 原G110/G125具体终态合同：受控能力晋升与真实增益审阅

原Learning/Evaluation的“能力晋升”与本地参考采用/运输分设对象页签。候选详情固定旧版/候选版本、相同预算、保留集与真实新任务来源；分别显示delta.improvement、Learning Lift、规则命中、投毒检查、Safety与局限。原Safety<30阻断和delta为空不晋升明确显示触发项；影子评估、待审、拒绝、已晋升、回滚请求及实际回滚读回不同。晋升按钮只沿原Owner有权动作，先列影响任务/当前生产版与可回滚版本，不能由本地reference ADOPTED升格。

构图：左能力与版本历史，中间旧/候选同预算评价表，右侧独立风险/缺证据，底部原Owner晋升或回滚确认；普通用户看到是否影响当前工作，不常驻训练参数。

不足只保候选，失败不改生产版；取消审阅保理由。回滚≤5s是待实测目标，显示实际开始/确认完成及耗时，未读回不能写已恢复。跨端重开先读当前生产版本和未决动作，不能重复部署。

Public Website仅用获准真实样例说明受控能力晋升与真实增益审阅及未核范围，不展示内部资料；Web按窗口宽度保主对象与可逆检查器、刷新读回原版本；Windows/macOS分别验证文件/窗口冷开和同版恢复；iOS按本组对象清单→单对象→检查/确认顺序重组，复杂编辑续接同版本，合法轻改不因窄屏丢失。三语、200%文字、键盘/读屏及48px触控均保关键字段和取消/返回。

UI可把增益与风险两个轴安排成可解释对照，不生成优胜分或一键自动批准；保稳定表格、锁定/撤销。价值是看清何时该采纳改进及如何恢复。

沿本屏现有Owner/Permission/SourceUse/版本/回执接线；缺callable保持OPEN并禁对应效果，不猜route，不改既有当前实现/验收状态。此段补全旧要求的可执行设计，不证明实现通过。
