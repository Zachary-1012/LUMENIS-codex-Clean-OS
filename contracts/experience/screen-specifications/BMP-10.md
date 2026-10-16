# BMP-10 — 品牌风险响应

```yaml
screen_id: BMP-10
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-027]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to see which brand-risk incidents need attention, how severity/spread/recency affect triage, and what response step is next.
- BMP BrandFocus risk is not interchangeable with CTH Subject events. The current builder reuses CTH rows, so those rows must not be relabeled as BMP risk.
- `BACKEND-GAP-027` blocks display until a canonical BrandFocus or global risk source and lineage are returned.
- Scope modes are explicit: globally scoped `GLOBAL_ALL` incidents are allowed only with the complete global grant and source lineage; `FOCUS` incidents must match the selected BrandFocus, and CTH Subject rows remain invalid in either mode.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-10')` / `/api/experience/screen/BMP-10`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `risks[].title`, `severity`, `spread`, `recency`, `status`, `brand_id`, `evidence_ref`, and `events[]` with response timeline fields.
- `creator:hold` saves a local high-risk hold-request draft. `response:draft` saves a local response proposal and does not send or publish it.
- CTH Subject event rows are invalid for this screen even when their shape looks similar.

## 3. State and recovery

- Loading retains the risk-response identity.
- Not collected says no BrandFocus risk record is ready; it does not say risk is zero.
- Unscoped/CTH-sourced rows are withheld with a plain brand-range explanation.
- Offline/error supports retry with no stale risk action state.
- Hold/draft actions remain blocked or explicitly local until the matching executor, approval and Evidence-bearing result exists.

## 4. Purpose-built composition

> 本屏完整布局、层级、控件位置、视觉交互与多表面重组见唯一前端规划：[视觉规划](../../../00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md#bmp-10)。本规范保留 Owner、调用、Permission、SourceUse、字段、效果、状态、恢复与验收合同。

- Desktop uses an incident field: severity queue on the left, spread/recency detail in the center, and a response timeline on the right.
- Mobile uses a triage queue first, then the selected incident timeline and response controls. It is not a generic dashboard or alert-card grid.
- The primary question is “what needs a brand response now, and what has already happened?”

## 5. Actions, authorization and effects

- `creator:hold` saves a local high-risk hold draft; until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, it cannot pause a partnership.
- `response:draft` saves a local response draft; it cannot send, publish or change a risk record.
- No CTH fallback, automatic severity change or external communication is allowed.

## 6. Accessibility and localization

- Risk queue labels include severity, spread and recency; timeline events are announced in chronological order.
- Mobile preserves the selected incident heading while moving from queue to timeline.
- Integration key inventory: `screen.BMP-10`, `bmp10.subtitle`, `bmp10.severity.*`, `bmp10.spread.*`, `bmp10.recency.*`, `bmp10.timeline.*`, `bmp10.action.*`, `bmp10.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- CTH Subject events are never rendered as BMP BrandFocus risks.
- Missing BrandFocus or source lineage withholds the incident and does not produce a healthy/zero state.
- A high-risk hold cannot succeed from a local click; a local draft is not sent, published or treated as a hold result.
- Severity queue and response timeline remain distinct at desktop and mobile widths.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BRANDFOCUS_RISK`; BMP risk owner must supply a canonical BrandFocus source before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 按严重性、扩散和时效处理有证据的品牌风险。
- **屏幕专属呈现：** 风险队列、原始依据、派生判断、后续状态分开
- **来源、范围与版本连续性：** 绑定品牌scope、Evidence、判断版本与决策receipt
- **四端差异：** Web/Desktop队列和详情；Mobile先风险依据和原文；官网不呈私有风险
- **失败与恢复：** 笔记不升级成事件；来源撤回保留历史并停止当前效果
- **补充验收：** 观察与判断分开；无批准/Effect receipt不称已响应。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
