# BMP-07 — 活动工作台

```yaml
screen_id: BMP-07
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-024]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to connect an activity objective to audience, channel milestones and observed outcomes without confusing a plan with a result.
- BMP owns the brand/market activity. A verified BrandFocus or explicitly granted global range and canonical activity source are required; topic quota or cooldown is process context, not campaign truth.
- Scope modes are explicit: an authorized `GLOBAL_ALL` campaign collection is valid when globally scoped and sourced; `FOCUS` is limited to the selected BrandFocus. The page does not force a brand selection before a granted global read.
- `BACKEND-GAP-024` currently exposes no verified per-campaign BrandFocus activity list. The page must not invent campaigns or ROI.

## 2. Route and bindings

- Read callable: `LumenisCoreClient.screen('BMP-07')` / `/api/experience/screen/BMP-07`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Expected fields: `campaigns[].goal`, `stage`, `kpis`, `timeline`, `outcome`, plus verified brand/source context.
- `campaign:write` saves a local campaign-content request draft; `campaign:close` saves a local close-request draft and must not imply a close result.
- No activity deep link, campaign selector or outcome calculation is invented locally.

## 3. State and recovery

- Loading preserves the selected brand context.
- Not collected says no campaign result is available; missing activity is not zero activity.
- Unscoped or denied data shows a brand-range guard and hides goals, timeline, ROI and channel totals.
- Offline/error offers retry and clears transient business data.
- Staged actions say “local request draft saved”; they never say launched, closed or measured.

## 4. Purpose-built composition

- Desktop composition is an objective strip followed by a five-step lifecycle: planned, budgeted, launched, observed and measured. A milestone timeline, channel mix and outcome plan-vs-actual section remain separate regions.
- The primary question is “what was planned, what actually happened, and what can be measured?” Planned and actual values never share one undifferentiated status.
- Mobile becomes a guided lifecycle with one milestone at a time, then a separate outcome section and channel details. It is not a dashboard card grid.

## 5. Purpose-built desktop composition

已批准目标来源：`BMP-07-ADD-marketing-calendar.md`。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：营销日历与热点建议

```
月视图：日期格内 节点/热点徽标
右侧：热点建议（依据▸ 置信区间）[加入计划] [忽略]
```

**4. State additions**
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

**9. Executable acceptance**
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 建议可忽略，用户决定。

### Existing contract — Actions, authorization and effects

- `campaign:write` saves a local request draft for authorized content activity; no campaign write is sent or persisted.
- `campaign:close` saves a local campaign-close draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no close effect is attempted or reported.
- Quota/cooldown can be shown only as a process notice and cannot be relabeled as ROI, reach or outcome.



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

### 草图增补：营销日历与热点建议

Web Workspace composition
同桌面布局；无额外差异。

## 6. Purpose-built mobile composition

### 草图增补：营销日历与热点建议

Purpose-built mobile composition
周列表。

### Existing contract — Accessibility and localization

- Lifecycle steps are announced in order with planned/actual distinctions in each label.
- Timeline milestones have a linear list equivalent; color is not the only stage signal.
- Integration key inventory: `screen.BMP-07`, `bmp07.subtitle`, `bmp07.lifecycle.*`, `bmp07.milestone.*`, `bmp07.channel.*`, `bmp07.outcome.*`, `bmp07.action.*`, `bmp07.recovery.*` for `zh-CN`, `en`, and `ko`.

## 7. Executable acceptance

- A topic quota response alone cannot render a campaign, ROI or measured outcome.
- A verified campaign keeps planned, launched, observed and measured states distinct.
- BrandFocus leakage from another campaign is rejected by the view-model allowlist.
- Close/write actions remain blocked or save an explicitly local draft when exact approval/result fields are absent; no close or write success is shown.
- Desktop, compact and mobile widths preserve lifecycle and outcome semantics.

Current decision: `IMPLEMENTED / BLOCKED_FOR_CAMPAIGN_SCOPE`; the BMP owner must bind canonical activity results before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 连接活动目标、预算、里程碑和实际结果。
- **屏幕专属呈现：** 目标→受众→渠道→预算→Outcome时间线；估算/承诺/实支各自分层
- **来源、范围与版本连续性：** 预算/日期变化定位受影响活动段、素材、资源和日程，父版可回滚
- **四端差异：** Web/Desktop编辑计划和影响预览；Mobile逐项审预算；官网仅公开示例
- **失败与恢复：** 无真实活动不造ROI；预算变化不触发付款/发布，冲突可回父版
- **补充验收：** 修改后只有受影响内容变化，新旧版本可重开比较。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
