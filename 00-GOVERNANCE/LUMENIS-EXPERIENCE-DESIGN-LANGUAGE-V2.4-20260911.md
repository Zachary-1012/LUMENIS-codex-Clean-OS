# LUMENIS / 序境 Experience Design Language v2.4 — Production Execution Supplement

> Status: **P0 EXPERIENCE EXECUTION AUTHORITY / SPECIFIC VISUAL-LANGUAGE SUPPLEMENT**  
> Effective: 2026-09-11  
> Scope: new `experience_v2/**` production presentation and all user-visible Experience migration work.  
> Does not override: Source / Runtime / Data / Permission / Evidence / Security / Production Truth.

## Authority relationship

This document is the Product Owner-approved **more-specific execution supplement** to `LUMENIS-EXPERIENCE-DESIGN-AUTHORITY-V2-20260911.md`. The older Design Authority remains authoritative for product structure, Experience boundaries, clean-room rules, responsive requirements, motion semantics, state truth and backend separation.

For **visual-language details only**, where older guidance conflicts with the latest v2.4 language, this supplement governs the new Experience. In particular: purple/indigo product chrome and generic SaaS/sans-only visual treatment are superseded by the v2.4 black-silver / white-silver editorial system.

## Non-negotiable redline

The Doubao/Trae Experience package is an **input scaffold, not a visual acceptance waiver**. Codex MUST NOT preserve a screen merely because it was delivered or validated structurally. If it still looks templated, generic, derivative, card-wall-heavy, or inconsistent with 序境, Codex must optimize the presentation before production propagation.

### LUMENIS recognition test

Mask the logo and product name. A production screen must still be recognizably 序境 through:
- editorial serif display hierarchy + readable sans body;
- `Lumen Axis / 序轴` and node/trace grammar;
- `Strata / 境层` spatial order;
- de-boxed information architecture using whitespace + hairlines before cards;
- black/silver light mode and silver/black dark mode;
- metallic inverse primary action;
- Icy Cyan restricted to data/state;
- Evidence/trace-first structures and restrained semantic motion;
- original, self-developed AI orb language rather than sparkles/stars/template AI iconography.

If this test fails, Experience acceptance fails even when the HTML renders.

## Propagation rule

Codex MUST calibrate **AI-01 + CTH-01** first. Both must pass:
1. latest repository drift audit;
2. real ViewModel/API/Permission/Evidence binding;
3. v2.4 anti-template visual review;
4. 360–1920 responsive semantics;
5. light/dark and reduced-motion;
6. critical E2E and evidence trace.

Only then propagate the proven grammar to the remaining screens. This exists to spend Codex quota on optimization/integration, not re-discovery or redesign-from-zero.

## Canonical implementation source

The detailed design language copied below is also present at `experience_v2/04_design_system/LUMENIS_DESIGN_LANGUAGE.md`; the two must remain semantically aligned.

---

# LUMENIS / 序境 — Design Language「序 · Editorial Lumen OS」v2.4

> 这份文档回答「序境的设计语言是什么、为什么不趋同」。它是 44 屏与未来生态共同遵守的**可讲述的设计主张**，不是组件清单（组件见 `05_components`，token 见 `design-tokens.json`）。
> 研究依据（clean-room，只抽原理不复制资产）见 `13_research/RESEARCH_FINDINGS.md`：Liquid Glass / MotionSites / Showreel / React Bits / Aceternity / Anime.js + Apple HIG / Tesla / Linear / Vercel Geist / Stripe。
>
> 版本脉络：v2.0 44 屏骨架 → v2.1 纸感/光学 → v2.2 流体字阶与纯名字导航 → **v2.3 黑银 / 白银金属单色 + 混沌球体（去紫）** → **v2.4 形态层：serif 编辑排印 + 序轴 + 境层 + 去盒子化（本版重点，解决"模板化"）**。

## 0. 一句话主张
**用编辑级的排印与一条贯穿全局的「序轴」，把"上下文 → 概览 → 分析 → 证据 → 决策 → 行动"像排版一卷证据之书一样组织起来；金属单色的克制造就可信，宋体级大标题与文学性留白造就序境自己的气质。**
序境不是又一个卡片仪表盘：它的识别不靠品牌色，而靠**排印、序轴、发丝线分层与金属质感**共同构成的语法——遮住 logo，仍然一看就是序境。

## 1. 五个设计原则（优先级从上到下，冲突时上面赢）
1. **Content over Chrome（内容优先，界面让位）**——参考 Apple Deference / Tesla Radical Subtraction：去掉一切不承担信息的装饰；v2.4 进一步**去盒子化**，外层区块是开放"境层"，只有实体物证（证据条目等）才落为实面。
2. **Typography is the Architecture（排版即架构）**——层级首先由 serif display / sans 正文的强对比、字重、留白、发丝线建立。**页面大标题与 KPI 数字用 serif display（中文宋体级 / 英文 Georgia），正文与控件用 sans**，形成"编辑级"签名；数字 tabular + lining。
3. **The Lumen Axis（序轴，签名母题）**——由 v2.2 的一条线升级为**贯穿系统的轴语言**：①桌面主区页边一条纵向序轴，整页内容"挂"在轴上；②侧栏目录是一条连续序轴，激活=轴上实心金属节点、未激活=空心节点；③KPI 顶沿、步骤链、证据链、阶段进度统一为"节点 + 序之线"。它是"次序 / 可追溯"的视觉化身。
4. **Internal Stays Internal（内部隐入过程）**——`subject_id / domain 码 / EV: / RUNTIME: / DESIGN_ONLY` 等技术字段不出现在业务卡面；只以 mono 出现在证据链、AI 推理过程、`data-provenance`/tooltip。界面只说业务语言；领域用全称「商业运营 / 品牌市场」，`CTH/BMP` 永不上明面。
5. **One Accent, Used Sparingly（单一强调，克制使用）**——**金属近单色**：主行动永远是"画布反相"（浅色=近黑铬、深色=银白，银按钮上用深字）；Icy Cyan 降级为**仅数据可视化与状态**，不做任何 chrome 填充；语义色只给状态点/数值。

## 2. 视觉基底（Material）——黑银 / 白银，互为反相
- **Light＝黑银（Black-on-Silver）**：银雾画布（`#ECEDEF` + 极淡境层基线网格）、珍珠面、近黑柔墨字（`#16181D`），主色=近黑金属 `#1B1D23`，金属渐变 `#3A3D45→#17191E→#05060A` + 顶部 sheen。
- **Dark＝白银（Silver-on-Black，与浅色相反）**：近黑画布 `#07080A`、银面、银白字（`#F1F2F4`），主色=银白 `#E9EBEF`，银渐变 `#FFF→#D7DAE0→#A9AFB9`；银白主按钮上文字用反相深色 `--lum-text-invert` 保证可读。
- **去紫红线**：全产品不存在 indigo/紫色 chrome；紫色只可能是历史遗留，发现即清。主行动=金属反相，不靠彩色。
- **层级来自留白与发丝线，不来自重阴影/彩色盒**：外层 `.lum-card` 透明近扁平、无阴影、1px 发丝线；内层实体 `.lum-card-solid` 才用珍珠面 + 极轻顶光；浮层/drawer/OPT 光学件才用 glass/sh-2/sh-3。
- **境层（Strata）**：主背景叠极淡的纵向栏位线（每 320px）与横向基线（每 88px），像版心网格/建筑图纸，提供"系统秩序"的潜意识底座，opacity 极低不抢内容。
- 几何：圆角收紧为精密仪器级（xs3 / sm6 / md10 / lg14 / xl18，胶囊除外），去软萌。
- 比例红线不变：**70% 信息清晰 / 20% 空间质感 / 10% 动效惊喜**。

## 3. 字体排印（Type，设备流体）——serif × sans 双声
- **双字族**：`--lum-font-display`（"Songti SC"/STSong/Noto Serif SC/SimSun + Georgia/Times，serif）只给**页面大标题（.lum-display/.lum-h1/.lum-h2）、区块编辑标题、KPI 大数字**；其余一律 `--lum-font-sans`；`--lum-font-mono` 给证据 ID / 技术 trace / eyebrow 索引 / 数字代码。
- 字重分工：serif display 用 600（宋体级不加到 700，保留书卷气）；sans 400 正文 · 450 密集/导航 · 600 交互与小标题。
- **流体字阶（clamp，360→1440+）**：正文近恒定保可读，display 随视口缩放：

| token | 360 | 1440 | 字族 | 用途 |
| --- | --- | --- | --- | --- |
| fs-2xs…lg | 11→15 | 11.5→16.5 | sans / mono | 标签/正文/eyebrow 索引 |
| fs-xl/2xl/3xl | 16/19/23 | 19/24/30 | sans（区块内）/ serif（编辑区块） | 小标题/区块 |
| fs-4xl/5xl(display) | 28/32 | 38/48 | **serif** | 页面主标题/KPI 大数字 |

- display 负字距（display -0.022em、标题 -0.012em）、行高紧（display 1.08）；正文行高放松（1.6）、描述限 72ch，形成**文学性留白**。
- **eyebrow = 编辑索引**：mono、大字距 .18em、大写，前置 22px 序之线短划（不是彩色小方块）。
- **页头（masthead）**：serif 大标题下用一条贯通发丝线 + 88px 序之线收尾重音，像报刊刊头。

## 4. 空间与栅格（Fluid Architecture + 序轴）
- 页距 `--lum-page-pad: clamp(16px,2.1vw+9px,40px)`；**区块间隙用 `--lum-editorial-gap: clamp(22px,2vw+14px,44px)`（比 v2.2 更松，文学留白）**；侧栏 `--lum-rail-w: clamp(208px,15.4vw,248px)`。
- **桌面（≥1025）主区左侧 26px 处落一条纵向序轴**（.lum-page::before，brand→发丝→透明），整页挂轴；无壳页（登录 chrome=none）居中、不显示序轴与额外缩进；≤1024 不显示页边轴。
- 加倍留白：感觉够的间距再放大一档；桌面舒展、手机紧凑，密度随设备重排（re-flow，非整体缩放）。
- 分区用 1px 发丝线（section-head 序之线收尾），不用第二只盒子去包盒子。

## 5. 导航范式（Index-catalog Navigation）
- 侧栏是**目录/索引**而非菜单：分组标题用 mono 大字距编辑小标题（可折叠 + chevron）；一条连续细轴贯穿整组，每个名字是轴上的条目。
- **只留业务名字**：无图标小方块、无填充块；未激活=轴上空心节点，激活=轴上实心金属节点（带极细 ring）+ 墨色名字；hover 微缩进。
- 领域用**全称**：商业运营 / 品牌市场；`CTH/BMP` 只作为内部 domain code 存在于数据与路由。
- ≤1024 保留纯文字侧栏；≤768 侧栏收为底部 dock；dock 中央是**混沌球体 AI 入口**（见 §7）。

## 6. 组件范式（Component Doctrine）
- **KPI（编辑年鉴式）**：**serif 大数字**（tabular lining）+ 顶沿 2px 序之线，卡面近扁平、标签三级灰无图标方块，delta 小胶囊，来源码入 `data-provenance`/title。
- **卡（去盒子化）**：外层 `.lum-card` 透明/极淡面、无阴影、10px 圆角、1px 发丝线、hover 仅加深发丝线；内层"实体物证" `.lum-card-solid` 才用实面 + 极轻顶光，形成"开放境层 → 实体物证"的纵深。
- **证据链 / 步骤链 / 时间线**：统一为"节点 + 序轴连接"，是"可追溯"叙事的主舞台；技术 ID 允许在此以 mono 出现。
- **AI 过程**：INTENT→RETRIEVE→REASON→ARTIFACT 用 M09/M11 分步状态表达；AI 标记统一用中性 `orb` 图标（**不再用星星/sparkles**），内部检索/字段在过程里可见、在结果卡面收敛。
- 每段一个主动作；主按钮=画布反相金属（浅近黑铬 / 深银白），次按钮描边、文字三级；银按钮上文字走 `--lum-text-invert`。

## 7. 签名件：混沌球体 AI Orb
- 全局 AI 入口（移动 dock FAB、AI 头像、AI 工具标记）统一为**自渲染 canvas 球体**（`assets/orb.js`，零依赖 vanilla canvas）：**球内**多层星云/流体沿轨道持续流转（像被封在金属珠里的混沌），**绝无外露星标**；金属高光 + 边缘 rim + 下影，抛光黑珍珠（浅）/ 银珠（深）。
- 球体颜色随**状态**变化：idle 银雾、processing 加速流转、success/warning/danger 语义色；`prefers-reduced-motion` 收敛为单帧；rAF 在不可见时暂停；DPR 自适应。

## 8. 动效语言（Motion）
- 轻量、有意义、语义化（每个动效带 semantic_reason，见 `06_motion` M01–M15）；stagger ≤5；`prefers-reduced-motion` 收敛终态。
- 签名动效＝序轴/序之线的"依次点亮/流动" + 球体内星云流转（自研 WAAPI / canvas，无第三方运行时）；不做无意义炫技位移。

## 9. 反模板检查清单（每屏交付前自问）
- [ ] 大标题/KPI 是否是 serif 编辑级，且与 sans 正文形成强对比？
- [ ] 层级是否主要由排版/留白/发丝线建立，而不是又一层浮起的彩色盒子？
- [ ] 桌面是否能看到页边序轴、侧栏是否为"轴 + 节点"目录，且全产品一致？
- [ ] 是否彻底无紫、主行动是否为金属反相（浅黑铬/深银白且银按钮深字可读）？
- [ ] Icy 是否只出现在图表/状态，没有任何 chrome 填充？
- [ ] AI 球体是否球内流转、无星星、状态色正确？
- [ ] 卡面是否还有内部码/英文技术缩写明摆？（应收进过程）
- [ ] 字号/间距在 360 与 1440 下是否都舒适（流体，而非两套死值）？
- [ ] 把品牌 logo 遮住，它是否仍然"一看就是序境"？

## 10. 明确不做（Non-goals）
- 不抄 Apple/Tesla/Linear/Aceternity 等任何具体视觉、字体、shader、资产；不引第三方 UI/动效运行时（orb/动效均自研 vanilla）。
- 不做拟物堆砌、不做重玻璃铺满数据、不用多色高饱和仪表盘、不用通用 SaaS 模板皮肤、不用紫色品牌 chrome。
- 不为"看起来高级"加无意义动效或大留白牺牲生产效率；serif 只用于 display 层级，正文保持 sans 的高可读性。
