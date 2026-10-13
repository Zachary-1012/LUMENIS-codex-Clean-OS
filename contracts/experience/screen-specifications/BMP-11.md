# BMP-11 — 品牌基准

```yaml
screen_id: BMP-11
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-028]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs normalized comparisons with metric definitions visible beside values, while incomparable items remain explicitly withheld.
- The current benchmark uses configured/global terms rather than a selected BrandFocus and has no verified source-to-ranking chain. No rank or gap is invented locally.
- `GLOBAL_ALL` is allowed only when the returned binding explicitly grants the complete global range. Focus mode must match the selected brand ID exactly.
- The default page can therefore operate on an authorized global collection without requiring a prior brand selection; switching to `FOCUS` narrows the same workflow and never turns focused data into a global aggregate.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-11')` / `/api/experience/screen/BMP-11`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `rows[].dimension`, `definition`, `self`, `competitors[]`, `comparable`, `brand_id`, `scope_mode`, `evidence_ref`; competitor rows require the same metric definition and their own recorded source.
- This screen has no write action. It cannot promote a competitor, alter canonical data or calculate a business ranking from incomplete rows.

## 3. State and recovery

- Loading, not collected, unavailable, access denied and offline remain distinct.
- A missing definition, source or comparability flag withholds the affected value.
- Comparable rows show values only when self and competitor definitions align.
- No comparable result shows a plain pending state, never zero or a synthetic rank.

## 4. Purpose-built composition

- Desktop is a horizontally scrollable normalized comparison grid with columns for dimension, current brand and competitors, followed by a metric-definition rail and source requirement strip.
- Mobile becomes a metric-by-metric comparison list: definition first, then current brand and competitors, with an explicit withheld state for incomparable rows.
- This is a definition-led comparison workflow, not a generic KPI dashboard or card grid.

## 5. Actions, authorization and effects

- No write/effect action is presented. Refresh repeats the read only.
- Any future ranking or benchmark export requires a new canonical callable and owner decision; it is not inferred by this page.

## 6. Accessibility and localization

- The desktop grid has a linear row/column reading order and mobile provides the equivalent metric list.
- Withheld values are announced with the reason; visual color is not the only comparability signal.
- Integration key inventory: `screen.BMP-11`, `bmp11.subtitle`, `bmp11.dimension.*`, `bmp11.definition.*`, `bmp11.comparison.*`, `bmp11.withheld.*`, `bmp11.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A global/configured term without exact BrandFocus or explicit `GLOBAL_ALL` grant is rejected.
- A competitor with a different metric definition or missing source is withheld.
- Missing values are never converted to zero and no rank is generated.
- Hostile rows from another brand are filtered before display.
- Desktop and mobile preserve the same definition/comparability semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BENCHMARK_SCOPE`; canonical benchmark owner must bind source-backed BrandFocus/global-all results before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 在口径一致时比较品牌基准。
- **屏幕专属呈现：** 先展示币种/期间/口径/分母，再显示可比矩阵和差距
- **来源、范围与版本连续性：** 每格保留定义、币种、样本、来源、范围、计算版本
- **四端差异：** Web/Desktop多品牌矩阵；Mobile逐项查看口径；官网不公开客户比较
- **失败与恢复：** 不一致即待核而不排名，未知值不补零
- **补充验收：** 条件变化使旧排名stale；无可比数据明确说明。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
