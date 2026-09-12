# LUMENIS Design Engineering Acceptance V2.5
给 Codex 的设计→工程接入验收。呈现层是唯一视觉真源；类名与 data-* 钩子稳定，后端只绑数据与行为，不改视觉契约。

## 1. 边界
- 豆包（Experience Layer Owner）拥有：HTML 结构呈现、CSS/tokens、组件呈现、动效/触感、原型交互、设计注册资产。
- Codex（Production Code Owner）拥有：后端、DB、Runtime、Collector、Permission、Evidence/Metric 引擎、真实 API、测试与生产闭环。
- 禁止两个 AI 同改一个文件；其他模型仅 Advisory。呈现层需要但后端没有的能力 → BACKEND_GAP，不伪造。

## 2. 稳定契约（不得重命名/删除）
- 行为钩子：`data-action` `data-act-class`(NAVIGATION/QUERY/DRAFT/EFFECT) `data-scope` `data-target` `data-permission` `data-risk` `data-route` `data-collapse-group`。
- 数据钩子：`data-real` `data-source=prototype` `data-countup` `data-decimals` `data-state-slot` `data-reveal` `data-i18n` `data-i18n-ph` `data-evidence-id`。
- 状态/可达：`aria-pressed/selected/current/expanded` `role`；主题 `.lum-app[data-theme=light|dark]`；方言 `.lum-app[data-realm]`；品牌 `[data-lum-brand]`。
- 全局对象：`LumUI`、`LumShell`、`LumOrb`(mount/mountAll/setStatus)、`LumBrand`、`LumLaunch`、`LumHaptics`。
- 浮层类名：`.lum-overlay/.lum-modal(__head/__body/__foot)/.lum-drawer/.lum-toast-stack/.lum-toast[data-tone]`。

## 3. 接入步骤（Codex）
1. 用真实 ViewModel 替换 `data/screens.js` 的 DESIGN_ONLY 数据，保持 section schema（type/字段）不变。
2. Action 绑定走 data-*；EFFECT 必须经 confirm（scope/target/permission），后端不可达时给真实错误，禁止假成功。
3. 主题：写 `localStorage['lum-theme']` 或 `.lum-app.dataset.theme`；方言由路由前缀映射 data-realm。
4. Orb：在状态变化处调 `LumOrb.setStatus(idle|processing|done|error)`；不要在业务里重建 WebGL。
5. Haptics：在关键动作/结果处调 `LumHaptics.impact(channel)` 或派发 `lum:haptic`（未来硬件绑定）。
6. i18n：文案走 copy-registry / data-i18n，不在组件里硬编码业务文案。

## 4. 硬性验收门（全部 PASS 才过）
| 门 | 判定 | 证据/命令 |
|---|---|---|
| NO_SECOND_DESIGN_SYSTEM | 只存在一套 tokens/组件源 | 无重复 design-system 目录；tokens 单一来源 |
| EXPERIENCE_V2_REUSED | 复用而非重做 | git diff 呈现层为增量演进 |
| AI_01_CALIBRATED / CTH_01_CALIBRATED | 两母版达标 | 基线截图 + 本校准文档 |
| DESIGN_TOKEN_CONSISTENCY | 无魔法值 | 颜色/间距/半径/字号全部引用 token（扫描报告） |
| COMPONENT/PATTERN_DUPLICATION | CONTROLLED | 注册表唯一原语，域差异走 Variant |
| RESPONSIVE | 8 断点无横溢/重叠 | 44 屏×8 断点截图 |
| STATE_SYSTEM | 0/null/unknown 区分 | STATE_SEMANTICS + 走查 |
| MOTION_SYSTEM | 只动 opacity/transform、reduced-motion | CSS 扫描无 transition:all |
| ACCESSIBILITY | 对比/焦点/aria/触控 | axe + 键盘走查 |
| LEGACY_BOUNDARY | 旧 UI 只读、不回流 | LEGACY_CSS_IMPORTED=0 扫描 |
| PRODUCTION_TRUTH_NOT_FABRICATED | 无假接口/假数据/假状态 | unknown-bindings/BACKEND_GAP 完整 |
| GENERIC_SAAS / CARD_WALL / PURPLE_AI_TEMPLATE | 反模板检查 | 无 #665CFF 残留、无白卡墙、无英雄渐变 |

## 5. 明令禁止
紫/靛蓝 AI 配色、渐变文字、卡墙、阴影+边框叠加、侧边色条、默认玻璃、`transition:all`、默认 Inter、
用 mock 冒充 runtime、把 route/文件存在当能力完成、为绿灯删测试/删数据、两个 AI 同改一文件。

## 6. LEGACY_CSS_IMPORTED=0 检查
构建前扫描：新呈现层不得 `@import`/`<link>` 任何旧版 CSS；旧资产仅在 14_visual_regression / legacy evidence 中只读存在。扫描脚本与原始输出进 09_QA。
