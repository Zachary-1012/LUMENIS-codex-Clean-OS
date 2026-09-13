# Experience Research Findings (clean-room) — 2026-09-11

> 红线 +1：每个执行步骤先研究登记源、再落地。**只抽原理，不复制任何第三方代码 / shader / 图片 / 字体 / 素材。**
> 截图取证：`13_research/source_captures/`（仅研究证据，绝不是产品 asset）。结构化登记：`experience_research_source_registry.json`。

## 研究方式（真实执行，非凭记忆）
- Liquid Glass：通过代理抓取 GitHub README 全文（12.5k 字符）+ 无头 Chromium 实拍在线 demo。
- MotionSites / Showreel / React Bits / Aceternity / Anime.js：无头 Chromium 1440×900 实拍 + 抽取标题结构。
- Uiverse：Cloudflare 403 拦截，**如实记为 BLOCKED_CLOUDFLARE**，不绕墙、不假装看过。

## 逐源结论（决策：ADOPT PRINCIPLE / EXPERIMENT / REJECT）

### ① Liquid Glass（最高优先级）— ADOPT PRINCIPLE + EXPERIMENT(surface)
- **技术管线（原理）**：场景光栅化 → 按面板矩形裁剪 → 高斯模糊 → 片元着色（折射 refraction、边缘色散 chromAberration、掠射 Fresnel、多光 Blinn-Phong 高光 specular、内描边 edgeHighlight、投影）→ 分层合成。
- **性能原理**：静态内容只捕获一次并缓存；动态内容每帧重光栅（要省着用）；按相交区域做脏标记；button 模式 hover 增亮、press 压平斜面+加深投影。
- **实拍关键证据**：demo 仅 **14 FPS**——证明光学效果必须有严格预算与强制降级；且**长正文放在近不透明白卡上**，玻璃只用于标题 pill / 控件 / 富图之上。
- **LUMENIS 落地（已自研，非引库）**：`assets/optical.js` 自写 SDF 圆角法线 + 折射 + RGB 微偏移 + Fresnel + 高光，**只暴露 7 参数**（blurAmount / refraction / chromAberration / edgeHighlight / specular / fresnel / bevel zRadius），只挂 OPT-01..04；四档降级 OPTICAL_HIGH→STANDARD→SOFT_GLASS→OPAQUE，功能 100% 保留；表格/证据/报告保持不透明。
- REJECT：不引 npm/CDN、不抄 shader、不抄 html-to-image 捕获管线、不在密集文本下用玻璃。

### ② MotionSites — ADOPT PRINCIPLE
浅色、居中粗体 hero、**单一强调色 CTA**、分段筛选（Featured/Popular/Recent）、统一圆角封面卡网格与纵向节奏。
→ PAT-FILTER-01、cards 网格节奏、每段一个主行动；间距走 `--lum-sp-*`。营销式大 hero 不用于数据工作台。

### ③ Showreel.design — ADOPT PRINCIPLE（动效叙事/节奏）
价值在转场叙事与节奏，不在组件。→ AI 任务流 INTENT→RETRIEVE→REASON→ARTIFACT 的 M09/M11 与 overview.mp4 节奏；缓动/时长 token 化、尊重 reduced-motion。不复用任何视频。

### ④ React Bits — ADOPT PRINCIPLE(行为) + EXPERIMENT(背景)
点阵底纹 + 克制极光、超大标题里**仅一个渐变词**、组件 playground（可编辑 props + 变体 tab）。
→ 组件优先（10 族）+ 变体 props；极光/点阵只在 AI Composer(OPT-01) 后做实验，绝不压在数据表上；每屏渐变强调至多一次。不引入 React、不抄组件源码/背景 shader。

### ⑤ Aceternity UI — ADOPT PRINCIPLE
极度克制：黑白、左对齐、实心主按钮 vs 描边次按钮、留白、懒加载占位。
→ 强化 70% 信息清晰：按钮三级层级、留白尺度、浮动/展开卡行为用原创 lum-card 重现；玻璃仅 Tier B 软玻璃。不引 Tailwind/Framer、不抄标记。

### ⑥ Anime.js — ADOPT PRINCIPLE（仅方法论）
实拍 hero 圆环：弧线/刻度**沿时间线依次点亮**、点 stagger。
→ 自研 LumMotion 的 timeline（T+0/80/140/260/340/420/480）、stagger（≤5 组）、countUp、observeReveal；环形序列用于 donut/runtime。**不打包 Anime.js**。

### ⑦ Uiverse — EXPERIMENT(仅原理) / 抓取被拦
Cloudflare 403。微交互（按压/loader/switch）原理已被 11 态系统 + LumMotion 覆盖；不绕墙、不造证据。

## 提炼后写进 LUMENIS 设计语言的 5 条全局规则
1. 70% 信息清晰 / 20% 空间质感 / 10% 动效惊喜，数据生产系统绝不倒置。
2. 光学只服务 OPT-01..04；密集文本/表格/证据/报告一律不透明（Liquid Glass demo 的可读性选择佐证）。
3. 每个动效必须有 semantic_reason；stagger ≤5；reduced-motion 去非必要动效；光学降级功能不丢。
4. 每段一个主动作；渐变/极光每屏至多一处；工作台背景保持中性。
5. 全部原创 Vanilla JS + WAAPI + Canvas/SVG + 自写 WebGL；零第三方运行时、零复制素材。

---

## 第二轮深度研究（2026-09-11，去模板化 / 生态级识别度）
用户反馈「太模板化、没有设计语言可讲、不能一开始就趋同」。补研 Apple / Tesla / Linear / Vercel(Geist) / Stripe 等**自有生态级产品**的视觉呈现与使用体验（clean-room，只抽原理）。

### ⑧ Apple HIG — Clarity / Deference / Depth（ADOPT PRINCIPLE）
- **Clarity**：任何字号下文字清晰、图标精确、装饰克制，功能驱动设计；**Deference**：界面不与内容争夺注意力，最小 chrome、半透明材质只是分层；**Depth**：用层叠/转场/视差表达层级而非拟物。
- 排版用语义化 text style，随设备动态字号（Dynamic Type）——字号不是固定 px，是随设备与可读性自适应。
- 材质（含 Liquid Glass）用于**控制与导航**且不遮挡内容；前景 vibrancy 从背景取色建立层次。
- → 序境落地：正文近恒定保可读、display 随视口流体；chrome 让位内容；技术内部码不上明面。

### ⑨ Tesla — Radical Subtraction（ADOPT PRINCIPLE）
- 近乎全黑白的单一画布，**唯一强调色只给主 CTA**；卡片零阴影/零渐变/零描边，深度来自全屏留白与内容本身；定制字体统一网站/App/车机；仅两个字重（400/500）；电影级、产品即内容。
- → 序境落地：暖纸/柔墨近单色基底 + 单一 Indigo 主色 + Icy 细节；卡片近扁平、靠发丝线与留白分层，而不是一堆浮起的盒子。

### ⑩ Linear / Vercel(Geist) / Stripe — Premium SaaS 的四条共性（ADOPT PRINCIPLE）
1. **字体即品牌锚点**：单一 sans（数据/ID 配 mono），系统化字阶、严格字重分工（400 正文 / 500 交互 / 600 标题，除微徽章外不用 700），不混 display 字体。
2. **近单色 + 唯一强调色**：黑白灰为主，一个色克制使用比五个色铺满更有力。
3. **加倍留白**：「感觉够了的间距，再翻倍」。
4. **display 负字距 + 表格数字 + 瑞士网格**：大标题 -0.02em 左右收紧，tabular-nums，发丝线分区（shadow-as-border）。
- → 序境落地：display/标题负字距、KPI 大数字 tabular、发丝线分区、编辑级留白；技术 ID 仅以 mono 出现在证据链/AI 过程，不进卡面。

### 反「模板化」结论：序境自己的设计语言 = 「序 · Lumen Editorial OS」
1. **以排版为骨架，而非以盒子为骨架**：层级靠字号/字重/留白/发丝线建立，卡片近扁平（`--lum-sh-flat`），不再用堆叠阴影盒子拼仪表盘。
2. **序之线（The Lumen Line）签名母题**：呼应「序=次序」，用一条 brand→icy 的极细渐变线贯穿 KPI 顶沿、导航激活态、步骤链、证据链——这是可讲述、可复用、可识别的自有母题，不是通用 SaaS 皮肤。
3. **名字优先导航**：侧栏只留业务名字，不要图标小方块、不要填充块；功能分组可折叠；领域用全称（商业运营/品牌市场），内部缩写（CTH/BMP）只留在数据/路由层。
4. **内部码隐入过程**：subject_id / domain 码 / EV: / RUNTIME: / DESIGN_ONLY 等技术字段不摆在卡面，收进 data-provenance、tooltip、证据链与 AI 推理过程；界面只说业务语言。
5. **设备流体自适应**：字号 clamp() 随视口（正文近恒定、display 缩放），页距/栏宽/侧栏宽全部流体；不是固定 px、也不是等比缩放，而是按设备重排密度。
6. **生态一致**：同一套字阶/材质/母题/动效语义贯穿 44 屏与未来生态，形成「一看就是序境」的识别度。REJECT：不抄任何一家的具体视觉/字体/着色器，不用其商标资产。
