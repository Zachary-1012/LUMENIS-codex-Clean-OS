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

## 5. Purpose-built desktop and web composition

- Desktop/Web: inventory is the primary inspection panel; trace correlation and structured records are separate review surfaces.
- Tablet/mobile stack inventory → trace boundary → records.
- No throughput, error-rate or waterfall chart is rendered without a time-series/trace callable.
- Export remains visibly unavailable until actor-scoped Permission and effect Evidence exist.

## 6. Purpose-built mobile composition

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

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; logs do not establish Global Commercial, Brand or Guangzhou coverage.
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
