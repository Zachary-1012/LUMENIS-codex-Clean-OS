# LUMENIS 呈现层 ↔ ViewModel / Action 契约映射 V2.5
目的：让 Codex 只替换数据与绑定行为即可接通后端，**类名与 data-* 钩子是稳定契约，不得重命名**；新呈现层是唯一视觉真源，旧设计不回流。

## 1. 分层与唯一真源
- 数据/结构（Codex 可改）：`data/screens.js`（44 屏 ViewModel）、`data/fixtures.js`（DESIGN_ONLY）、`data/copy.js`（i18n 文案）、`data/shell.js`（导航树）。
- 渲染器（保持 section schema 不变）：`assets/sections.js`（21 个渲染器）、`components.js`（LumUI/状态）。
- 呈现层（豆包拥有，Codex 不改视觉）：fonts/tokens/base/shell/components/optical/brand/motion.css + orb/brand/launch/haptics.js。
- 证据：`PRESENTATION_HOOK_INVENTORY.json`（35 个 data 钩子、112 个 section lum-* 类）。

## 2. ViewModel 契约（每屏）
`LUM_SCREENS[id] = { id, title, eyebrow, chrome:'app'|'auth', subject?, sections:[…], actions? }`
section 由 `type` 决定渲染器（head/kpis/evidence/insight/events/risks/timeline/table/chart/filters/cards/actions/upload/runtime/ai/split/stack/tabs/steps/form/note/raw）。
**后端接入只替换 sections 内字段值，不改 type 与字段名**；新增 section 类型需同时在 sections.js 注册渲染器并登记本文件。

## 3. 行为钩子（Action Contract）
| 钩子 | 取值 | 后端含义 |
|---|---|---|
| data-action | 动作 id | 绑定处理函数；EFFECT 类必须先 confirm |
| data-act-class | NAVIGATION / QUERY / DRAFT / EFFECT | 动作风险分级；EFFECT=写操作，弹确认 |
| data-scope | 作用域（subject/global/…） | 影响范围，confirm 中展示 |
| data-target | 目标对象/路由 | 作用目标 |
| data-permission | 权限标识 | 与权限矩阵比对，不足走 permission_required 态 |
| data-risk | low/med/high | high 触发 warning 触感与更强确认 |
| data-route | 屏 id | 前端路由（LumShell.setActiveRoute） |
| data-collapse-group / data-panel / data-close / data-pick / data-val / data-group / data-day | UI 状态 | 纯前端，可保留 |

行为总线：`LumUI.bindActions(root)` 委托处理；EFFECT 弹 `.lum-modal` 显示 scope/target/permission/risk，**后端不可达时给真实错误，禁止假成功**（原型 toast key `not_wired_to_backend`）。

## 4. 数据绑定钩子（ViewModel → DOM）
| 钩子 | 用途 |
|---|---|
| data-real | 真实数值占位（替换 DESIGN_ONLY） |
| data-source | 数据来源标记；原型恒为 `prototype`，接入后写真实源 |
| data-countup / data-decimals | 数字滚动与小数位（tabular-nums） |
| data-state-slot / data-state | 13 态插槽（loading/empty/unknown/n-a/stale/error/…） |
| data-reveal | 进入视口揭示（IntersectionObserver） |
| data-i18n / data-i18n-ph | 文案与占位的 i18n key（zh/en/ko） |
| data-provenance / data-who / data-context / data-level / data-kind / data-strength / data-lum-ready / data-opt / data-status | 证据出处、主体、层级、类型、强度、就绪态、光学面、球体状态 |

## 5. 全局对象契约（window）
| 对象 | API（稳定） | 谁调用 |
|---|---|---|
| LumUI | $/$$/el/icon/toast/openModal/closeModal/openDrawer/closeDrawer/bindTabs/bindSegmented/sparkline/donut/stateBlock/skeletonRows/bindActions/init/STATE_ORDER | Codex 绑定 UI 反馈 |
| LumShell | mountShell/setActiveRoute/setContext/SubjectContext/currentSubject/renderSubject；主题 localStorage `lum-theme`；≤768 context 自动 closed | 路由/主体上下文 |
| LumOrb | mount/mountAll/setStatus(idle/processing/done/error)/_instances；canvas.lum-orb | 后端任务状态→球体 |
| LumBrand | mark/lockup/mount/favicon/word；[data-lum-brand] | 品牌，只读使用 |
| LumLaunch | play/auto/reduced/lowPower | 冷启动编排 |
| LumHaptics | impact(verb/channel)/bind/setEnabled/CHANNELS/VERBS；事件 `lum:haptic` | 动作/结果触感 |

## 6. 状态契约
13 态与 `12_contracts/STATE_REGISTRY.json` 对齐；0/NULL/UNKNOWN/N-A/STALE/ERROR 必须区分（见 STATE_SEMANTICS_V2.5）。后端缺能力 → `BACKEND_GAP.json`，前端表达 NOT_AVAILABLE，不伪造。

## 7. 主题 / 域 / 国际化
- 主题：`.lum-app[data-theme=light|dark]`（黑银/白银反相），写 localStorage `lum-theme`。
- 域方言：`.lum-app[data-realm=operational|editorial|intent|studio|system]`，由屏 id 前缀（CTH/BMP/AI/SH/SYS）映射（app.js realmOf）。
- i18n：文案全部走 copy-registry，不内联业务文案。

## 8. 旧设计不回流（LEGACY_CSS_IMPORTED=0）
扫描证据：index.html 仅 link 8 个新 CSS（fonts/tokens/base/components/shell/optical/brand/motion）；assets 内无任何 `@import`、无 legacy/old CSS 引用（grep 原始输出存档）。旧 UI 仅在 14_visual_regression 与 legacy evidence 只读存在。**Codex 接入时不得重新引入旧 CSS/旧类名/旧紫蓝配色。**

## 9. 接入步骤（建议顺序）
1. 用真实 ViewModel 替换 screens.js 的 DESIGN_ONLY（保持 type/字段），同步 data-source。
2. 按 Action Contract 绑定 data-action，EFFECT 走 confirm + 权限/风险。
3. 接 13 态与真实错误（去 fixture fallback）。
4. 任务状态驱动 LumOrb.setStatus、结果驱动 LumHaptics.impact。
5. 主题/域/i18n 保持现有机制；逐屏回归 8 断点基线。
