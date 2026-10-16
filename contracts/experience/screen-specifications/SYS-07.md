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

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

完整目标布局与交互见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

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

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：创始人内部开发者模式（G20b）


## 6. Purpose-built mobile composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#sys-07)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

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
