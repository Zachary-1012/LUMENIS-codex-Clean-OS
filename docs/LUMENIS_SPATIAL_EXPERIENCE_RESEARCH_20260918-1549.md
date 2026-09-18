# LUMENIS Spatial Experience Research · 2026-09-18 15:49

本记录是本轮前端增量的研究锚点，不替代生产契约、ViewModel 或 Evidence 真相。

## 研究边界

- 以最新 `核对.docx`（Spatial Lumen OS）为生产视觉边界；保留 Lumen Axis、Editorial Serif、Evidence-first、四种 realm dialect。
- 不复制 Apple Liquid Glass、韩国品牌视觉或第三方组件库；只提炼可验证的交互规律，落到现有 Vanilla ESM/CSS 设计系统。
- 不改 CTH/BMP/Shared/SYSTEM 的产品归属、路由 ID、Production Truth 或 Evidence 主契约。

## 外部研究结论

1. Apple Human Interface Guidelines 将 Material 定义为建立前景/背景之间的层次与深度；Material 应按语义用途选择，而不是按颜色装饰。空间布局要求深度有意义，文字不做漂浮立体化。来源：
   - https://developer.apple.com/design/human-interface-guidelines/foundations
   - https://developer.apple.com/jp/design/human-interface-guidelines/materials
   - https://developer.apple.com/jp/design/human-interface-guidelines/spatial-layout
2. Toss 的交互设计实践把跨 iOS/Android/Web 的 easing、spring、timeline 统一成平台语言，并建议先将 easing token 化，让设计、开发、QA 使用同一套可验收词汇。来源：
   - https://toss.tech/article/interaction
   - https://tossmini-docs.toss.im/tds-react-native/
3. ADERERROR 的官方定位是 Post-Minimal，并把服装延伸到 design、art、space；可借鉴的是“系统一致、局部意外、跨触点延续”，不是把品牌装饰搬进产品。来源：
   - https://adererror.com/en/introduce
4. 关于 Gentle Monster 的韩国设计研究强调沉浸空间、艺术化与数字互动的平衡；对 LUMENIS 的可落地转译是让证据/任务成为主角，用空间层次与叙事节奏增强投入感，而不是增加装饰组件。来源：
   - https://www.kisd.or.kr/data/thesisData/17460191411.pdf
5. W3C 建议用 `prefers-reduced-motion` 让用户关闭由交互触发的动画；因此 Lumen Beam、进入/退出、Orb 反馈必须有静态降级。来源：
   - https://www.w3.org/WAI/WCAG21/Techniques/css/C39.html

## LUMENIS 转译规则

| 研究规律 | LUMENIS 实现 | 禁止事项 |
| --- | --- | --- |
| 语义材质 | M0 Truth 不透明；M1 Structure；M2 Rail/Toolbar/Drawer；M3 只给 AI Composer、Active Task、Orb、Command Dock | 全屏玻璃、卡片墙、透明遮蔽事实 |
| 空间层次 | Z0–Z5、单层 edge light、低强度 material tint、上下文 rail 作为前景层 | 给每个卡片加阴影/光晕、把文字做成 3D |
| 方向性光 | Lumen Beam 只在 primary action、active task、selected evidence、focus/critical state 使用 | 彩虹渐变、持续流光、装饰性蓝紫 |
| 韩国后极简 | 大留白 + 局部高密度事实 + 一个非预期的轴/材质细节；四 realm 共享一套语法 | 堆叠海报、模板 SaaS Bento、复制品牌页面 |
| 交互语言 | `touch / open / trace / shift / settle / return`；easing 以 token 命名 | 无业务意义的 bounce、无限 loading、自动发布 |
| 适配与可及性 | 8 个视口、弱设备 M3→M2→M1、reduced-motion 静态降级 | 只在 33% 缩放可用、固定宽度、依赖 GPU/WebGL |

## 本轮执行切面

- 只增量修改现有 `tokens.css`、`base.css`、`components.css`、`shell.css` 与 shell 路由层。
- 先改善 AI-01、CTH-01、BMP-01 的“主角—证据—行动”节奏，再由公共 token/primitive 传播到其他屏幕。
- 视觉完成不等于生产闭环完成；真实数据、权限、Runtime、Evidence 和发布状态继续以真实接口和验收 Gate 为准。
