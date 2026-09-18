# LUMENIS Motion System V2.5
动效表达层级、连续性、因果、转场、反馈、状态变化、焦点、进度、出处（provenance）——不做装饰。

## 1. 品牌动效动词（Brand Research V1）
| 动词 | 语义 | 典型 |
|---|---|---|
| Touch | 触碰确认，物理感 | 按钮 active scale .97 / 100–150ms |
| Open | 展开一个境层 | 抽屉/面板自方向滑入 + 背景同步淡入 |
| Trace | 沿证据路径行进 | Claim→Evidence→Source 的 1px icy 描线 |
| Shift | 焦点/视图切换 | tab 指示滑动 + 内容交叉淡入 |
| Settle | 落定、归位 | 数值 count-up 后 settle、toast 归位 |
| Return | 回到主体/归点 | drill-down 返回的反向位移 |

## 2. Token（tokens.css motion）
- duration：instant 120 / fast 200 / base 320 / slow 480 / morph 520；reduced-motion 全部降 1ms。
- easing：standard `cubic-bezier(.2,.7,.2,1)`、emphasized `(.2,0,0,1)`、exit `(.4,0,1,1)`、spring `(.34,1.4,.5,1)`。
- 只动 `opacity / transform`；禁止 `transition:all`、禁止动 width/height/padding/margin/top/left。
- 时长选择：微交互 100–200；内容切换 200–300；布局/页面 250–400；>400ms 必须有叙事或空间理由。高频重复操作再减半。

## 3. M01–M15 Motion Source（交付 05_motion/source）
| ID | 名称 | 属性 | 时长 | 曲线 | reduced-motion |
|---|---|---|---|---|---|
| M01 | button-press | transform scale .97 | 120 | standard | 瞬切 |
| M02 | chip/toggle | opacity+translateY(2→0) | 160 | standard | 瞬切 |
| M03 | tab-shift | indicator transform + content opacity | 220 | emphasized | 瞬切 |
| M04 | page-enter | translateY(8)+opacity 0→1 stagger | 320 | emphasized | 直接显示 |
| M05 | section-reveal | data-reveal IntersectionObserver, opacity+Y | 300 | standard | 直接显示 |
| M06 | modal-in | opacity + translateY(12)，backdrop 同步 | 260 | emphasized | 直接显示 |
| M07 | drawer-in | translateX 自边缘 | 300 | emphasized | 直接显示 |
| M08 | toast-in | 自底/侧滑入 | 200 | standard | 直接显示 |
| M09 | evidence-trace | stroke-dashoffset 沿线描绘（icy 1px） | 480 | standard | 直接全显 |
| M10 | metric-countup | 数字 tween + tabular-nums | 480 | emphasized | 直接终值 |
| M11 | ai-step | 步骤状态点/行依次进入 | 220/步 | standard | 直接全显 |
| M12 | orb-flow | Lumen Core 球内 fbm 流动（idle 慢/processing 快+icy） | 连续 | — | 单帧静态 |
| M13 | launch-standard | 启动动画完整版 ~2.1s（S0–S7） | 2100 | emphasized | 静态 logo .7s |
| M14 | launch-short | 短版 0.6–0.9s | 800 | emphasized | 静态 |
| M15 | hover-sheen | raised 面顶部 1px 捕光 opacity | 160 | standard | 无 |

Motion Source 以 GSAP 3.15（已 vendor）+ 原生 CSS/RAF 实现；Lenis 惯性滚动仅用于长页且可被 reduced-motion 关闭。不引入 three.js 做 UI 动效。

## 4. AI 过程状态（不是转圈）
understanding → retrieving（证据检索）→ reasoning（不暴露私有思维链，只给阶段标签）→ tool（工具调用状态）→ artifact → completed / failed / needs-review。
每阶段有明确进入/退出动效与可中断；失败有内联、可行动反馈，不静默。

## 5. Lumen Core 球体动效
idle：fbm 缓慢沿序轴流动（speed .55）；processing/thinking/running：speed 1.7 并微混 icy；done：一次 settle；error：转语义色但不闪烁。reduced-motion / 低性能（hardwareConcurrency≤4）出单帧。

## 6. 性能
transform/opacity GPU 合成；滚动/连续动画用 rAF + DPR≤2；IntersectionObserver 离屏暂停 orb/reveal；尊重 `prefers-reduced-motion`；不阻塞主线程、不阻塞数据加载（启动动画与加载解耦）。
