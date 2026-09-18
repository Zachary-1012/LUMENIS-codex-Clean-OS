# LUMENIS Design Ecosystem Changelog — v2.4 → v2.5
增量演进，不推翻 v2.4；记录真实发生的呈现层变化（基线 HEAD ab67612）。

## Added
- **Foundations/Tokens V2.5**：tokens.css 重写——真银无色相斜坡、黑银/白银精确反相、流体 clamp 字号、表面阶梯、发丝优先、仅浮层阴影、realm 方言变量；`DESIGN_TOKEN_SYSTEM_V2.5.json` 从 CSS 确定性提取。
- **Lumen Core（orb.js 重写）**：零依赖原生 WebGL1 GLSL 球内混沌流转（simplex+fbm 域扭曲）、左上定向光+fresnel 金属边、黑铬/白银反相、状态机、无星星；修复 WebGL1 不支持 fwidth 导致整球透明的问题（改固定像素 AA）、compile/link 错误上浮、preserveDrawingBuffer 便于验证。
- **品牌系统**：brand.js（standard/korean(서경)/symbol 三版本 SVG、favicon、MutationObserver 自动挂载）、brand.css、launch.js（完整/短版启动、locale、reduced-motion、与数据加载解耦）。
- **触感层 haptics.js**：语义通道 + navigator.vibrate + `lum:haptic` CustomEvent 具身硬件桥、总开关、reduced-motion 降级、事件委托自动绑定。
- **Field System**：`section.lum-grid-N > article.lum-card` 全局字段化（透明/顶部发丝/hover 起雾/图标去框），取代能力卡墙。
- **V2.5 治理资产 14 件**（本目录）与四域方言（operational/editorial/intent/studio/system）。
- 可变字体 Geist / Geist Mono / Fraunces 本地 vendor（woff2，拉丁 unicode-range，CJK 回退系统）；GSAP/ScrollTrigger/Lenis vendor。

## Changed
- base.css：移除重复网格背景与三层光晕，改为单束顶光+一角衰减+极弱 grain；display 改文学衬线；eyebrow 去引导横线；卡片发丝无阴影。
- shell.css：去左上 logo「序」小方块与 bell 红色 badge-dot、去 nav ::before 轴点（改 active 短墨条）、品牌 lockup 纵排、纯名导航（无 CTH/BMP 缩写后缀）、功能组可折叠、dock 中央球体 FAB 在 390 可见、按钮选择器提升到 `.lum-app .x` 修复 color:inherit 压字。
- components.css：全量覆盖渲染器产出的 lum-* 类；修复发送按钮「黑底黑字」（特异性）；risk 去左侧色条改 level dot+meter；evidence Trace、event Point-on-Axis、insight 衬线、table 发丝行、AI 工作区状态。
- optical.css：关闭 WebGL 玻璃折射 GL 层（OPT 类名契约保留给 Codex），四 OPT 面改平整金属发丝面，解决无头/GPU 下玻璃雾发脏。
- shell.js / app.js / index.html：最小改动——换品牌 lockup、去 badge、写 data-realm、按序加载 brand/haptics/launch；section 渲染器、screens 数据、契约钩子不动。

## Removed / Deprecated
- 旧 #665CFF / 紫靛 AI 模板配色、紫蓝英雄渐变、渐变文字（旧 Logo Brief 的 Opal Lilac/Indigo/Gold 彩色域随旧方案归档，不沿用，映射到单色金属+唯一 icy Point）。
- 白卡墙、装饰竖线/轴点、bell 红点、logo 小方块、旧 .nm 字标块。

## Fixed（自检迭代链，均有截图/像素证据）
1. composer 玻璃雾发脏 → 关 GL 层、改金属面。
2. 发送按钮黑底黑字 → 选择器特异性修正。
3. 球体 390 灰饼/空环 → 片元改抛光黑铬+定向光；定位并修复 WebGL1 fwidth 编译失败。
4. 能力卡墙 → Field System。
5. dark 漏 --lum-text-invert → tokens dark 补 #0d0e11。

## Unchanged（契约稳定，供 Codex 直接绑定）
sections.js / components.js / motion.js / optical.js / icons.js / i18n.js 的对外契约；data/screens.js(44 屏 ViewModel)、copy.js、fixtures.js、shell 导航数据；全部 data-*/aria 钩子；全局对象 API。

## Verification
44 屏在 1440 light / 1440 dark / 390 light 批量渲染，console 错误 = 0；两母版 AI-01/CTH-01 多轮出图校准；详见 09_QA 与 04_VISUAL_BASELINES。
