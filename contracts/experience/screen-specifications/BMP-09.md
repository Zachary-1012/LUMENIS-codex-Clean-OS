# BMP-09 — 品牌评估

```yaml
screen_id: BMP-09
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-026]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to understand movement by evaluation dimension, confidence and source coverage using actual observed results.
- Evaluation is derivative: it cannot rewrite the recorded result, replace its source or become a new truth store. Subjective generated text is not an evaluation result.
- `BACKEND-GAP-026` currently returns unfiltered evaluation records and drops source references; the page remains blocked until exact BrandFocus or global range and result lineage are available.
- Scope modes are explicit: authorized `GLOBAL_ALL` evaluation aggregates may be shown with global result lineage; `FOCUS` dimensions must match the selected BrandFocus. Focus data is never relabeled as global.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-09')` / `/api/experience/screen/BMP-09`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `dimensions[].name`, `score`, `movement`, `confidence`, `evidence_coverage`, `source`, `brand_id`, `evidence_ref`, and `reports[]`.
- A report control uses `report:write` only to save a local report-request draft; it remains non-executing until the canonical owner returns a result.
- Only `actual_result` or `verified_result` sources are accepted by the view-model.

## 3. State and recovery

- Loading, not collected, offline and access-denied states are distinct.
- Unscoped or lineage-incomplete dimensions are hidden rather than shown with zero or a generated score.
- Ready shows score, movement, confidence and coverage together; reports remain separate from dimensions.
- Report request blocked/local-draft states never claim a report was generated or written.

## 4. Purpose-built composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Desktop uses a score matrix beside a report shelf, preceded by a BrandFocus line and an actual-result qualifier.
- This is a scorecard/evidence-coverage workflow, not a generic trend dashboard or repeated metric-card renderer.

## 5. Purpose-built desktop composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

完整目标布局与交互见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：公开数据营销组合与归因


**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 数据同权、按用途、重构；不使用付费源。

### Existing contract — Actions, authorization and effects

- `report:write` saves a local evaluation-report draft only when exact read/action permission is present. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no report is generated or written.
- No score recalculation, source correction or learning promotion is performed by the screen.



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

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：公开数据营销组合与归因


## 6. Purpose-built mobile composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-09)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

### 草图增补：公开数据营销组合与归因


### Existing contract — Accessibility and localization

- Each score row announces dimension, score, movement, confidence and source coverage in one linear label.
- Mobile list is the non-visual equivalent of the desktop matrix; no chart-only meaning.
- Integration key inventory: `screen.BMP-09`, `bmp09.subtitle`, `bmp09.scorecard.*`, `bmp09.report.*`, `bmp09.movement.*`, `bmp09.confidence.*`, `bmp09.coverage.*`, `bmp09.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A subjective or AI-only score is rejected by the source allowlist.
- A record without selected BrandFocus or source lineage is not displayed.
- A missing score remains unavailable rather than zero.
- Report request is blocked or explicitly local-only without a write result; no generated/written success is shown.
- Wide and narrow layouts preserve actual-result-only semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_EVALUATION_SCOPE`; canonical evaluation owner must restore source references and brand filtering before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 理解品牌评估变化、置信和覆盖情况。
- **屏幕专属呈现：** 维度、真实Outcome、置信、分母和方法并列，文本意见不冒充分数
- **来源、范围与版本连续性：** 绑定原Outcome/Evidence/评估方法与版本，不改写源事实
- **四端差异：** Web/Desktop可比较维度和周期；Mobile逐维度和来源；官网只发布审核结果
- **失败与恢复：** 未评估/样本不足为UNKNOWN；历史版本保留但可标stale
- **补充验收：** 分数可回样本和方法，结果变化生成新版本，不自动Promotion。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
