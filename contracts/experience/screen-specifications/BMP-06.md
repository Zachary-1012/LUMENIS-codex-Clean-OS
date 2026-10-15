# BMP-06 — 内容生产台

```yaml
screen_id: BMP-06
status: OWNER_REVIEW
revision: 1
owner_domain: BMP
binding_ids: [BACKEND-GAP-023]
product_owner_approval: APPROVED_OVERALL_EXPERIENCE_CONSTITUTION_30_36
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: BLOCKED
artifact_disposition: SOURCE_BACKED_SCOPE_BLOCKED_IMPLEMENTATION
reviewer: Bounded ROUND-13 implementation worker
reviewed_at: 2026-09-22
approval_reference: ROUND-13-BMP-CREATION-UI
```

## 1. User problem and product invariant

- A brand operator needs to move an approved content idea through drafting, review and authorized release while retaining version and source context.
- BMP owns the brand/market workflow. A current BrandFocus or explicitly granted global range, actor read access, content lineage and action-specific approval are required before content is shown or released.
- Scope modes are explicit: an authorized `GLOBAL_ALL` response may show a global brand collection with verified lineage; `FOCUS` must match the selected BrandFocus. One mode is never presented as the other.
- Current backend gap `BACKEND-GAP-023` is unscoped and cannot supply a verified brand read. The implementation therefore renders only a scope guard until that contract exists.
- Out of scope: inferring a brand from a source record, showing product-wide content counts, directly publishing, or treating an AI draft as approved content.

## 2. Route, entry, exit and return

- Read callable: `LumenisCoreClient.screen('BMP-06')`, corresponding to `/api/experience/screen/BMP-06`.
- Required response envelope: `ok`, `screen`, `bound`, `source`, `focus_context`, `binding`, `truth`, and allowlisted `assets`.
- Display gate: `binding.scope_read_evidence_version` and `binding.evidence_lineage_version` must both be `v2`, `binding.read_access` must be `ALLOWED`, and `binding.scope_mode` must match the returned context. `FOCUS` requires the exact selected `brand_id`; `GLOBAL_ALL` requires a null `brand_id` plus `global_read=ALL_GRANTED`. Legacy self-reported scope/permission booleans are not accepted.
- Exit and restoration remain Shell-owned. The page does not invent content deep links or a local brand selector.
- Current backend response is not sufficient for a real delivery loop; no content is displayed as brand truth until the binding is verified.

## 3. Verified data and callable bindings

| Field/action | Owner | Current contract | Missing behavior | Binding |
| --- | --- | --- | --- | --- |
| Asset title, kind, state | BMP Content | `assets[].title`, `kind`, `state` | Hide records without verified brand scope and lineage | BACKEND-GAP-023 |
| Version/review status | BMP Content | `version`, `review_state`, `approval_state` | Keep review and release distinct | BACKEND-GAP-023 |
| Source relationship | Shared source/content owner | `evidence_ref` is required as a gate, never shown as an implementation identifier | Withhold asset if absent | BACKEND-GAP-023 |
| New content | BMP Content | `content:draft` action contract | Save a local content draft only; do not write | BACKEND-GAP-023 |
| Submit review | BMP Content | `content:submit` action contract | Save a local review-request draft only; do not submit | BACKEND-GAP-023 |
| Publish | BMP Content + effect fence | `content:publish`, high-risk confirmation | Save a local publishing-request draft only; no effect without the canonical executor and result | BACKEND-GAP-023 |

## 4. State and recovery matrix

| State | User-visible behavior | Recovery |
| --- | --- | --- |
| Loading | Keep the production task identity and announce loading | Wait or refresh |
| Not collected | Explain that no source-backed content is ready | Refresh; do not show zero assets |
| Scope blocked / denied | Explain that the selected brand cannot be confirmed | Return through Shell context or retry |
| Offline / error | Explain that content production is temporarily unavailable | Retry without stale business records |
| Ready | Show only verified assets; review and publish remain separate | Refresh |
| Action staged | Confirm a local request draft was saved; nothing was written or published | Wait for the canonical executor, approval and action result |

## 5. Purpose-built desktop composition

已批准目标来源：`BMP-06-ADD-video-editing-studio.md`。本次入库不提升原实现/设计/验收状态；未接通项为 OPEN。图中数值、日期、版本及状态是布局例子，运行取真实结果。动作复用既有 Owner/权限/版本，保存、修订、重开和中断恢复逐项验收。

### 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G183/G64/G170/G171）

```
内容生产台 › 视频 · 《标题》                  画幅 [9:16 ▾ 16:9 1:1 4:5] [导出] [工程交换 ▾]
Brief ✓  分镜 6 镜  审核：READY / NEEDS_REVISION / BLOCKED / NOT_VERIFIED
┌ 素材浏览（独立预览，不动播放头）┬ 预览（安全区线）────────┬ 检查器 ───────────┐
│ clip01 0:42 SHA✓ 30fps 版权未知 │   ┌────────┐            │ 字幕 样式/每行≤14字 │
│ clip02 1:10 VFR⚠                │   │ 字幕区 │            │ 响度 实测/目标      │
│ [自动粗剪提议] [镜头检测]       │   └────────┘            │ B-roll 候选(已授权) │
├ 逐词稿（删词即剪）──────────────┴──────────────────────────┤ 封面 3 候选          │
│ 今天带你看……~~呃~~……这家店的木门是……                         │ AI 标注 含 AI 内容   │
├ 时间线：V1 ▇▇▇|▇▇ ｜ 字幕 ▭▭▭ ｜ 人声 ▅▅ ｜ BGM ▁▁(ducking) ▶ 00:00:18 ───────┤
└──────────────────────────────────────────────────────────────────────────────┘
工程交换预检：⚠ 2 项损失（ducking 无对应、dissolve 不支持）· 时基 UNKNOWN → [查看] [仍导出为新版本] [取消]
```

**4. States**
空 / 探测中 / 转写中 / 模型不可用（手动剪辑可用）/ 提议待确认 / 渲染中（可取消）/ 渲染失败（原因+重试）/ 版权未知 / 数据缺失 / 权限不足。

**9. Acceptance**
- 素材 100% 有哈希/时长/时基；VFR 标注；序列化无绝对路径。
- 字幕同步 ≤100ms；多画幅不拉伸、字幕在安全区；16:9 与 9:16 分别重排。
- 自动粗剪只是提议，确认后才改 Timeline；词内零切。
- 成片可播放、可重开；工程交换先预检，取消不改项目。
- 产品演示片必须来自真实操作录屏；封面文案兑现正文；AI 素材标注。

**增补（2026-10-14）**
- 预览与播放头分离：悬停临时预览不改时间线、不进撤销栈；切点以播放头为准并在界面标明。
- 参考片学习面板（E12）：全帧数 / 已看帧数 / 峰值时码列表 / 镜头表；未看完显示「部分」。
- 演示片模式（E10）：镜头表每行写「操作→状态→结果」；短版按动作闭环自动建议切点。
- 导出前预检条：逐项损失列表，取消即不改项目。

### Existing contract — Purpose-built desktop composition

- Use an editorial production board with six distinct lifecycle swimlanes: brief, draft, review, approved, scheduled and released. A version inspector sits beside the board for the selected asset.
- The primary question is “what is the next authorized production step for this brand asset?” The page is not a KPI dashboard and does not reuse a generic card grid.
- A compact action rail exposes “save ... draft” controls with the matching approval state; each control visibly remains local and non-executing.
- At narrow widths the board becomes a single production queue followed by the selected version detail; it is not a shrunken desktop board.



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

### 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G183/G64/G170/G171）

Web：稿件、预览、时间线按宽度重组；浏览器文件选择/上传与草稿分别呈现进度，支持刷新后恢复已保存工程，不虚报未上传素材可用。 大文件上传分片续传。


## 6. Purpose-built mobile composition

### 草图增补：内容生产台 · 视频剪辑（规划 §14 E1–E11、G183/G64/G170/G171）

Mobile：竖屏优先；逐词稿编辑 + 简化时间线；画幅切换与导出可用；工程交换仅桌面。


### Existing contract — Actions, authorization and effects

- `content:draft`: save a local draft of the request; no content is created.
- `content:submit`: save a local review-request draft; no review is submitted.
- `content:publish`: save a local publishing-request draft. Until the canonical server executor, Permission/effect fence and Evidence-bearing result exist, no publish effect is attempted or reported.

## 7. Accessibility and localization

- Keyboard order is heading, scope context, lifecycle queue, selected version, then action rail. Each lane has a meaningful label.
- Screen-reader copy describes brand content status and next business step, not implementation diagnostics.
- Table/queue content has a linear mobile equivalent and action state announcements.
- Integration key inventory: `screen.BMP-06`, `bmp06.subtitle`, `bmp06.lane.*`, `bmp06.asset.*`, `bmp06.action.*`, `bmp06.state.*`, `bmp06.recovery.*` for `zh-CN`, `en`, and `ko`.

## 8. Executable acceptance

- An unscoped backend payload renders the scope guard and none of its asset titles, states or counts.
- A verified BrandFocus payload renders the six-lane workflow and preserves distinct draft/review/approval/release states.
- Missing lineage removes only the affected asset; it never becomes an empty success or zero count.
- A denied publish action remains blocked; an enabled local-draft action shows a non-executed state and never claims a successful write or publish.
- Desktop, compact and mobile widths expose the same state semantics with the purpose-built compositions above.

Current decision: `IMPLEMENTED / BLOCKED_FOR_BRAND_SCOPE`; backend owner must provide actor-to-BrandFocus read and action result contracts before real-user E2E acceptance.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 把授权素材和内容想法推进为可审阅版本。
- **屏幕专属呈现：** Draft→Review→Approved→Delivered专属编辑流程，来源/rights贴近正文
- **来源、范围与版本连续性：** 继承同Brief/Evidence/品牌/语言；修改保存子版本和受影响片段
- **四端差异：** Web/Desktop正文与证据并读；Mobile聚焦待审与修订；官网不编辑内部稿件
- **失败与恢复：** rights未知/授权不足时阻止对应动作，离开保留草稿
- **补充验收：** 真实brief到修订子版本再重开；AI草稿不标批准或已发布。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
