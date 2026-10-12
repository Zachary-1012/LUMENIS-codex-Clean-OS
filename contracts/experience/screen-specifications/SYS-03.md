# SYS-03 — Database and truth chain

```yaml
screen_id: SYS-03
status: DESIGN_EXPLORATION
revision: 1
owner_domain: SYSTEM / Canonical Data
binding_ids:
  - BACKEND-GAP-038
product_owner_approval: PENDING
design_authority: 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md
design_decision: DESIGN_EXPLORATION
reviewer: Sol review required
reviewed_at: UNKNOWN
approval_reference: UNKNOWN
```

## 0. Authority basis and artifact disposition

- Constitution basis: SYS-03 database/truth-chain blueprint and §36 gates.
- Product contract: `Source → Evidence → Canonical Data → Metric/ViewModel`; version presence is not readability or completeness.
- Historical visual references: `KEEP_AS_EXPLORATION`; the implementation is purpose-built and source-led.
- Anti-template check: the page uses a validation spine, staged chain and check list, not a dashboard grid.
- Sol design decision: `DESIGN_EXPLORATION`.

## 1. User problem and product invariant

- Authorized context: SYSTEM reader with permitted access to a read-only system screen.
- Real task: understand which schema/check/chain facts are returned and which facts remain unknown.
- Completion signal: schema version, integrity checks, application readability and chain stages remain separate.
- Out of scope: migration, repair, database path disclosure, data rewrite and business metric editing.

## 2. Route, entry, exit and return

- Read route: `GET /api/experience/screen/SYS-03` → `experience_screens._build_sys03()` → `canonical_data.self_check()` and `get_schema_versions()`.
- Exit: return to the originating SYSTEM route. No migration or recovery destination is bound.
- Return: shell origin, selected context and scroll state only; no business selection changes.

## 3. Verified data and callable bindings

| Priority | UI field | Source | Missing-data behavior | Binding / evidence |
| --- | --- | --- | --- | --- |
| P0 | Schema versions | KPI `sys03.schema_versions` | Numeric value only with `ready`; no zero fallback | BACKEND-GAP-038; `experience_screens.py::_build_sys03` |
| P0 | Integrity checks | table rows `检查项/结果/state` | Empty/malformed rows remain unknown/not returned | Canonical self-check owner |
| P0 | Truth stages | optional `truth.truth_chain` or timeline section | Absent stages show that the endpoint did not return them | `sys03_snapshot.dart` |
| P1 | Readability | `truth.application_readability` / `readability_state` | Absent is `notreturned`, not healthy | BACKEND-GAP-038 |
| P1 | DB identity/isolation | `truth.db_identity` state only | No path/connection detail is echoed | Security boundary |

No migration, write, repair, pagination or Evidence emission contract is verified.

## 4. State and recovery matrix

| State | Meaning | Recovery |
| --- | --- | --- |
| Loading | Checks pending | Wait or leave |
| Empty / not collected | No checks or chain stages returned | Show binding-unavailable copy |
| Partial | Schema exists but readability/chain is absent, or checks are mixed | Refresh; do not promote version to healthy |
| Offline / error | Read failed or envelope invalid | Retry bounded GET; clear old snapshot |
| Blocked | 401/403 | Follow shell access flow; no migration control |
| Ready | Specific returned checks are displayed | Read-only; no persisted success claim |

## 5. Purpose-built desktop and web composition

- Desktop: a validation spine anchors schema, integrity and readability; a separate horizontal truth-chain panel shows only returned stages; checks and identity boundary sit beside it.
- Web Workspace shares the same ViewModel and state semantics; no desktop-only database capability is claimed.
- Tablet stacks spine, chain and checks; mobile turns each stage into a readable vertical step.
- No schema/health chart is rendered because no time series is bound.

## 6. Purpose-built mobile composition

- Keep the validation spine visible first, then chain, then checks.
- Each unavailable stage retains its label and unknown state.
- Back/return goes to the originating SYSTEM location; refresh re-reads and clears stale values.

## 7. Actions, authorization and effects

| Action | Boundary | Failure behavior |
| --- | --- | --- |
| Read checks | Existing GET; SYSTEM reader authorization remains a backend gap | Distinguish access denial, offline and malformed data |
| Migration/repair | Not bound | No control is rendered; do not fake authorization or completion |

## 8. Accessibility, motion and localization

- Screen-reader order follows the validation spine and truth-chain stages.
- Stage state is textual and not color-only; unknown/not returned is announced.
- No chart alternative is needed.
- zh-CN/en/ko labels wrap and preserve long check descriptions; reduced motion is supported by the host preference.

## 9. Executable acceptance

| ID | Acceptance | Test/evidence |
| --- | --- | --- |
| SYS03-TRUTH-01 | Schema version does not imply application readability | Snapshot/widget tests |
| SYS03-CHAIN-01 | Missing chain stages remain unknown/not returned | Snapshot/widget tests |
| SYS03-SAFE-01 | Database path and connection details are never displayed | Adversarial widget test + source review |
| SYS03-REAL-USER-01 | Operator reads a real self-check result and can identify an absent stage without treating it as pass | Authenticated runtime E2E required |

## 10. Cross-cutting gates and review

- GLOBAL UNIVERSE / DATA MATURITY IMPACT: none; schema/integrity state is infrastructure evidence and does not count Global Commercial, Brand or Guangzhou coverage.
- RANDOM ENTITY DATA ACCEPTANCE: not applicable; no entity rows are displayed, sample count zero.
- CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION: research complete; no justified upgrade beyond the canonical self-check binding. Recovery/migration requires a separate versioned contract and Permission/Evidence gate.
- Decision: `DESIGN_EXPLORATION`; Sol review and runtime verification remain pending.


## Intelligent UI 逐屏采用项（2026-10-08）

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

> 本节是屏幕专属设计补充，沿用本规范已有 owner、绑定、权限、状态与审查结论；不改变 frontmatter 状态，也不自动提升 DESIGN_READY。未知绑定继续 UNKNOWN/BLOCKED。

- **真实任务与完成信号：** 核对schema、integrity、readability与Truth chain层次。
- **屏幕专属呈现：** 分别呈schema、自检、应用读取、链路阶段，不给总绿灯掩盖缺口
- **来源、范围与版本连续性：** 绑定实际check/time/chain ref；不泄漏DB路径/业务行
- **四端差异：** Web/Desktop分层检查；Mobile阻断优先；官网不呈系统诊断
- **失败与恢复：** 数据库不可读或检查失败只读报告，不执行迁移
- **补充验收：** PASS/UNKNOWN/ERROR各自有证据；无误报健康。

- **交互与视觉约束：** 按本屏任务组合文字、图形、可编辑对象和局部操作；只使用上文已绑定字段/动作。AI建议可检查、编辑或拒绝，服务端Owner/Permission决定是否执行。彩绘用于图标及适合的局部元素，有功能含义的线性控件继续保留；整体空间、层级、动效与交互依唯一Experience和真实任务设计，不固定为二维或三维风格；颜色可丰富但不过量，不单独表达真假/权限/状态。不得复制社交平台页面或套统一卡片模板；真实角色按用户Brief/脚本描述创作，不复制参考人物；原研究的采用范围、素材权利与任务完整性继续保留。

### 可编辑设计到源码映射（2026-10-08 审计采用）

本屏设计/源码映射沿用现有 Experience 与 ScreenSpec 合同；本段不改变设计、实现或验收状态：

- **设计资产：** Figma file key / node ID / revision / 可编辑访问状态 = `NOT_VERIFIED`（本轮未连接核实，不能推断不存在）。复用获授权既有工程；需要新建时先取得必要访问及 PO 认可，不上传私有生产资料。
- **源码与动作：** 本屏原有 Flutter Screen/Component → Repository/ViewModel → Action → Core/Permission/状态；逐项回读真实路径，不复制旧绑定表里的状态。
- **变量和变体：** LumenisTheme / 语义颜色与字号 → Figma Variables/Variants/Auto Layout/Prototype；记录对应名称与版本。Website Astro/CSS共享设计语义，不硬共用不兼容实现。
- **覆盖：** 四端职责、中文/英文/韩文、明暗模式、宽度/字号、键盘/读屏、加载/空/未知/拒绝/离线/错误/恢复；必要长内容可滚动，其余避免无意义整页上下滚动。
- **变更及验收：** 设计 diff → 受影响组件/Token/Action → 原状态/焦点/路由/任务连续性回归 → 实际操作证据及回退。只修对应部分，不重生成全 App；源码/设计/测试状态分别记录。
- **完成边界：** 当前 Figma 链和真实四端操作证据未核实，不提升本屏状态。PNG、伪造 .fig、44张示意图、路由存在或 Widget 可显示都不能代替可编辑设计和真实用户结果。
