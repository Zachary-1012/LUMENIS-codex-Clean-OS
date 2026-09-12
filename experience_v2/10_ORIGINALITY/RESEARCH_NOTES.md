# LUMENIS Clean-room Research Notes V2.5
方法：只吸收方法论与机制，绝不复制任何外部产品的视觉、代码、图标、字体轮廓或动效曲线数值。所有 LUMENIS 呈现资产为为本产品原创。

## 研究到决策的映射（机制级）
- **Apple（HIG）**：层级靠字号/权重/留白而非描边框；触感分 Impact/Notification/Selection；材料克制、内容优先。→ 落到 Field System（去卡墙）、haptics 通道、金属面分层。
- **Tesla**：最少控件 + 明确「到位」反馈；仪表盘黑底高对比、数据当主角。→ 黑银/白银、EFFECT 动作双脉冲确认、球体状态即系统状态。
- **Linear**：高频操作动效近隐形、命令面板、密度可控。→ realm 方言密度、微交互 100–200ms、键盘/命令语义。
- **Nothing（Glyph）**：一个 Glyph 贯通光/声/震，跨媒介传递状态。→ Lumen Core 球体 + lum:haptic 事件 + icy 状态色三者同源；图标族统一 1.5 线。
- **Gentle Monster / Tamburins（韩系世界观）**：世界观先于单品；抽象概念环境化。→ 六传播原语（Point/Axis/Boundary/Strata/Trace/Return）成为贯穿 logo/球体/层级/动效的统一语法，而非每季换皮。
- **ADERERROR（Post-minimal）**：极简中保留一个「意外」。→ 每页一个焦点 + 序轴/发丝线等克制的个性化签名。
- **Teenage Engineering（图形即功能）**：状态图形直接映射系统状态。→ 球体流纹速度/颜色=idle/processing/done/error；donut/sparkline 直接映射数据。
- **GitHub Primer / IBM Carbon**：品牌必须工程化为 tokens/icons/components/responsive。→ 14 件 V2.5 治理资产 + 69 原创 lum-icon + 8 断点 + 契约映射。
- **29CM / Toss / 韩系奢牌**：编辑式留白、克制、信任。→ BMP Editorial Realm 大留白与衬线 display。
- **用户红线 7 站（Aceternity/React Bits/Motion Sites/Anime.js/Universe/Showreel/Liquid Glass）**：仅学习组件化与动效组织；明确不采用其玻璃/渐变/紫蓝视觉，Liquid Glass 教程图只作原理理解，光学层最终选择平整金属面（WebGL 玻璃在跨 GPU 下不稳定，已关闭）。

## 明确不做（反趋同）
- 不用紫/靛 AI 渐变、不用通用 SaaS 卡墙、不用默认 Inter、不用彩虹渐变按钮/渐变文字。
- 不照抄任何品牌 logo 外形；旧 LUMENIS 液态水滴海/Opal Lilac 彩色方案仅作历史证据，不沿用。
- 外部库只做底层动效/滚动工具（GSAP/Lenis），不引入其主题或组件外观。

## 原创性自检
- 球体：原生 WebGL1 GLSL（Ashima simplex 为公开噪声算法，片元着色、光照、配色、状态为原创编排）。
- Logo/图标：几何原创，currentColor 线性族，非任何品牌外形。
- 配色：黑银/白银金属单色系 + 唯一 icy 语义青，为本产品定义。
