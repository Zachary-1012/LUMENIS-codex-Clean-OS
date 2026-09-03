# 序境 CSS 收敛治理清单（CSS Manifest #02）

- 日期：2026-09-04 · 状态：EXECUTED + VERIFIED · 上游：CSS_CONVERGENCE_AUDIT_01.md
- 范围：#01 清单（index.html 引用的 32 个 CSS）之外的**零引用死样式归档**，以及被引用文件中**高饱和蓝紫渐变的 Stone 化**。
- 原则：NO-BLIND-DELETE（零引用才归档，归档不删除）；增量收敛不推翻；拟物角色美术不在本轮自行改动。

## 一、零引用死样式 → ARCHIVE（git mv，保留历史）

三重扫描确认零引用：① 全部 21 个 HTML 的 `<link>`；② 全部 JS 内 `.css` 动态加载；③ 全部 CSS `@import`。

| 文件 | 三重扫描 | 动作 | 目的地 |
|---|---|---|---|
| apple-ui.css（含 5 处 iOS 彩色渐变） | 零引用 | ARCHIVE | 99-ARCHIVE/static/css/ |
| compat.css（命中仅 three.min.js 压缩子串巧合） | 零引用 | ARCHIVE | 同上 |
| ui_dashboard.css | 零引用 | ARCHIVE | 同上 |
| ui_modern.css | 零引用 | ARCHIVE | 同上 |
| zachary_robot.css（样式已由 zachary_robot.js 内联 `<style>` 取代；引用的是同名 .js 非 .css） | 零引用 | ARCHIVE | 同上 |

均以 `R`（rename）入库，0 内容改动，git 历史保留；index.html 本就未引用，无需改 HTML。

## 二、被引用 CSS 的高饱和渐变 Stone 化

权威色板取自 zbip-tokens.css：Stone-900 `#1C1917`（主操作/深色容器）、Stone-600 `#57534E`、Stone-500 `#78716C`、Stone-400 `#A8A29E`、Stone-100 `#F5F5F4`；语义 success `#16A34A` / attention `#D97706` / info `#2563EB` / risk `#DC2626`。

| 文件 | 收敛点 | 前 → 后 |
|---|---|---|
| resident_health.css | 概览条/主按钮/弹窗头/二维码图标/4 状态条/spinner | 紫渐变 #6d28d9·#4f46e5 → Stone-900；状态条去渐变改语义纯色；cdp_degraded 紫 → info 蓝 |
| style.css | nomi 与 zachary 两套聊天 header/头像/用户气泡/发送/focus；export/report-icon 四色；metric-icon 五色；action.primary/secondary、side-item.active、cat-bar、bar、status-tag.multi、brand-bar、死变量 --purple | 蓝 #0a84ff·#5ac8fa、蓝紫 #007aff·#5856d6 渐变 → Stone-900/600；分类图标去渐变统一中性；侧栏选中改 Stone 浅底黑字 |
| evidence_dashboard.css | ev-chip.active / hover | 紫渐变 #6d5df0·#8b7bff → Stone-900；紫边 → Stone-500 |
| v3_modules.css | br 生成按钮 / 报告徽章 / 表单 focus | 蓝紫渐变 → Stone-900 |
| zbip-refine.css | ai-gov-bar 进度条；smart-icon 与 link-option-icon | 进度条绿渐变 → success 纯色；功能小图标双色渐变 → 极浅单色底（去渐变、保留功能分类色） |
| ui_interactions_v5.8.0.js / zachary_robot.js / auth_recovery_poller.js | JS 内联注入样式（按钮/趋势柱/聊天气泡/授权弹窗） | #667eea·#764ba2、#7c3aed·#4f46e5 → Stone-900/600 |

## 三、刻意保留（不自行改动，记录依据）

1. **nomi / zachary 拟人形象的拟物渐变**（nomi-head/body/antenna、zachary-body/ear/hat/headset/gloss/face）：属角色立体美术而非 UI 配色，改动等同重新设计形象，归 Zero Sequence「核心 UI/UX 原则」，需本人确认后再处理。
2. **语义状态变量** --green/--red/--amber：success/risk/attention，符合序境状态色规范，保留。
3. **功能小图标的极浅分类单色底**（API Key 黄 / AI 资源包蓝 / 小红书粉 / 搜索绿，40px、浅底深线性 icon）与 topic_campaign 的 type-tag 七类内容标签：属信息编码而非装饰色块，去渐变、保留色相以维持识别。
4. **LEGACY token 层**（tokens-minimal / design-v8/v9 / zb-theme 等）：按 #01 逐页渲染回归后再停用，本轮不改变量定义，避免连锁。

## 四、Evidence（真实验证）

- CSS 括号配平：style 977/977、evidence 40/40、v3_modules 94/94、zbip-refine 319/319，全配平。
- 3 个被改 JS `node --check` 全通过。
- Playwright 1440 真实渲染（首页 dashboard / 浮动 AI 助手 / 驻场智能能力中心）：computed style 扫描高饱和蓝紫元素 = 0；助手 header 实测 rgb(28,25,23)=Stone-900；smart-icon 渐变 backgroundImage=none；真实 pageerror = 0（仅既有 URL 内嵌 Basic Auth 的 credentials 提示，非本轮引入）。
- 生产 8201 `/healthz` = `{"ok":true,"version":"5.9.9"}`，静态样式改动无需重启、对生产零中断。
- 敏感扫描：本批提交不含密码/密钥/token。

## 五、剩余 BACKLOG（不在本轮）

- 拟物机器人形象是否灰度化/线性化：待本人决策。
- LEGACY CSS（#01 标注 8 个）逐页渲染回归 → 确认被 zbip 覆盖后停用并归档。
- design-v8/v9、tokens-minimal 旧变量层与 zbip-tokens 权威源的最终并轨。
- Emoji 作正式 icon 的线性 SVG 替换巡检（auth_recovery 弹窗 ⚠ 等）。
