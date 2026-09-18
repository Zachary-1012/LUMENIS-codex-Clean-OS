# ZBIP UI/UX 动效与视觉升级蓝图（素材深度剖析 + GitHub 研究 + glm-4.6v 诊断）

> Research ID：LRN-UI-20260903-01
> 素材：3 段录屏（87 帧）+ 24 张参考图；GitHub：emilkowalski/skills、Motion、View Transitions；视觉顾问：glm-4.6v（4576 tokens）
> 定位：**只沉淀方法论与可执行参数，不直接改业务代码**；所有色值以 ZBIP 既有 Stone 暖灰 Token 为准，外部色值仅作参考。
> 日期：2026-09-03

---

## 0. 素材资产清单与分类

| 来源 | 数量 | 内容 | 可吸收点 |
|---|---|---|---|
| 视频 8db404ab（51 帧） | Mac 录屏 | emilkowalski/skills 日/夜开关动效全过程 | **动效词汇表 Stagger/Follow-through/Float/Keyframes**（用户最喜欢的"模块滑动"方法论源头） |
| 视频 53ba967a（25 帧） | iPhone | AI 旅行助手界面（Good morning→对话→富士山卡→东京夜景全屏→深色地图） | 全屏卡片流、玻璃拟态浮层、模块错峰滑入、圆形/胶囊按钮 |
| 视频 6858aa2b（11 帧） | 微信内教学 | UI 亲密性/间距/对比原则 | 14 技巧的视频版佐证 |
| PNG ×5（咪噗设计"夏日电子梦"） | 金融/日历/Goals | 超大圆角、极光渐变、超大数字、黑色胶囊工具栏 | 视觉质感与排版层级 |
| JPG ×19（UX Planet/Lalaa） | 14 个逻辑驱动 UI 技巧 | Before/After 对照 | 布局/对比/对齐/一致性硬规则 |

---

## 1. 动效体系（最高优先级 · Emil Kowalski 权威规则）

> 源：github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md（58 规则/8 类），配套开源库 Sonner（toast，13M+/周）、Vaul（drawer），均 MIT。

### 1.1 动效词汇表（视频里的"模块滑动"本质）
- **Stagger 错峰级联**：相关多元素依次进入，彼此小延迟，形成 cascade；**只对"一组相关卡片"用，不相关元素一起动**；每组 **3–7 个**，超过最后一个等太久；间隔 **30–80ms**；绝不阻塞交互。
- **Follow-through 余动**：主动作停止后，局部继续运动再 settle，产生重量感。
- **Float 失重漂浮**：落位后轻柔、连续、不同相位/幅度/周期的上下漂移，让静态元素"有生命"；不是规则直线、不是整片一起动。
- **Keyframes 多段关键帧**：0%/50%/100% 定义，浏览器补间；星星沿**各不相同方向**漂入。

### 1.2 缓动曲线（自定义，禁用内置 ease / 禁用 ease-in）
```css
--ease-out:      cubic-bezier(0.23, 1, 0.32, 1);   /* 进/出场：快速起，响应感 */
--ease-in-out:   cubic-bezier(0.77, 0, 0.175, 1);  /* 屏内移动/变形：自然加减速 */
--ease-drawer:   cubic-bezier(0.32, 0.72, 0, 1);  /* iOS 式抽屉 */
/* 决策：进入退出→ease-out；屏内移动→ease-in-out；hover/颜色→ease；跑马灯/进度条→linear；UI 绝不用 ease-in（起手慢=迟钝） */
```

### 1.3 时长表（UI 动画一律 < 300ms）
| 元素 | 时长 |
|---|---|
| 按钮按压反馈 | 100–160ms |
| tooltip / 小 popover | 125–200ms |
| 下拉 / 选择 | 150–250ms |
| 模态 / 抽屉 | 200–500ms |
| 快捷按钮 stagger | 30ms/个 |
| 卡片组 stagger | 40–60ms/个 |
| 侧栏菜单 stagger | 20ms/个 |

### 1.4 硬性规则（直接进 Code Review 清单）
1. 按钮 `:active{transform:scale(.97)}`（0.95–0.98），必须有按压反馈。
2. **绝不从 scale(0) 入场**，从 `scale(.95)+opacity:0`（真实世界不会凭空出现）。
3. popover 从触发器缩放 `transform-origin:var(--transform-origin)`；**modal 例外保持居中**。
4. **只动画 transform 和 opacity**（走 GPU，跳过 layout/paint）；不动画 padding/margin/height/width。
5. 快速触发场景（toast/tab）用 **CSS transition 可中断**，不用 keyframes（被打断会从 0 重启）。
6. **非对称时长**：进入可慢、退出要快（如按住 2s linear、松手 200ms ease-out）。
7. **频率决策**：100+ 次/天（快捷键/命令面板）→ 绝不动画（Raycast 开关无动画即最优）；数十次/天（hover）→ 极短；偶尔（modal/toast）→ 标准；首次/庆祝 → 可加惊喜。**键盘触发的动作不动画。**
8. 转场交叉处别扭时加 `filter:blur(2px)`（<20px，Safari 昂贵）桥接两态。
9. `prefers-reduced-motion`：减少而非归零——保留 opacity/颜色，移除位移。
10. hover 动画必须包 `@media (hover:hover) and (pointer:fine)`（触屏 tap 会误触发 hover）。
11. 背景先动、前景最后：Backdrop→container→content→actions。
12. 退出反向（LIFO）或全体同时，不做正向 stagger 退出。

### 1.5 技术选型（我们是原生 JS，不用 React/Framer Motion）
- **确定性、可预定动画 → 纯 CSS**（离主线程，加载时不掉帧；Vercel 仪表盘从 Framer 切 CSS 才解决加载掉帧）。
- **程序化、可中断 → WAAPI**（`element.animate(keyframes,{duration,easing,fill})`，兼具 CSS 性能与 JS 控制，无需库）。
- **共享元素转场（卡片→详情"飞过去"）→ View Transitions API**（Chrome/Edge 已支持，`document.startViewTransition` + `view-transition-name`，原生 FLIP，无需 React）。
- 不引入 framer-motion / GSAP 大库；不新增远程字体/动画库（符合既有性能红线）。

---

## 2. "夏日电子梦"视觉语言（PNG ×5 提炼）

> 用于在**不破坏黑白灰侘寂主基调**前提下，提升精致度、时尚感与状态表达。克制使用，仅在需要"温度/层次/庆祝"的局部。

| 维度 | 参考做法 | ZBIP 落地方式 |
|---|---|---|
| 圆角 | 卡片 24–32px 超大圆角 | 桌面卡片维持 12–16px（工程密度），**移动卡片/浮层可到 20–24px**；同一组件圆角必须统一（14 技巧#12） |
| 渐变 | 极光低饱和（蓝→粉→米黄）；Morning 浅绿/Afternoon 浅蓝/Night 深灰蓝做**分组底色** | 仅用 Stone 同色系极弱渐变（#FAFAF9→#F5F5F4）做分组；语义分组用 4% 透明度的语义色底，**不彩色化** |
| 超大数字 | 0.00321 BNB / 2026 / 21°C 数字远大于标签 | KPI 数字用 28–40px tabular-nums，标签 12px muted，强化"数字优先" |
| 黑色胶囊工具栏 | 黑底 + 线性白 icon + 圆形分隔 | 选中态工具栏/主操作条可用 `#1C1917` 胶囊 + 1.5px 线性白 icon |
| 圆形侧按钮 | `<`、`+`、箭头均为圆形 | 浮动操作、步进、导航统一 36–40px 圆形钮 |
| 彩色小状态点 | 蓝星/橙点/绿+/选中日黑色圆 | **保留并强化**：状态点统一 8px、语义色、必须配文字/icon（14 技巧#7） |
| 头像堆叠 | H 圆 + 真人 + +6 重叠 -8px | 责任人/协作人场景用堆叠，+N 用灰圆 |
| 大小字层级 | Goals / For today；Meeting / Product Launch UX | 页面 H1 700 + 副标题 12–13px muted，间距 4px（亲密性） |
| 玻璃拟态 | topbar/浮层 backdrop-filter 模糊 | 沿用毛玻璃：`backdrop-filter:blur(12px) saturate(1.4)` + 半透白底 + 1px 内描边 |

---

## 3. 14 个逻辑驱动 UI 技巧（UX Planet，硬规则 → ZBIP 自检）

| # | 规则 | ZBIP 落地/自检 |
|---|---|---|
| 01 | **亲密性分组**：关联越近间距越小；8pt 网格、精细处 4pt；间距随元素尺寸增大 | 全部间距走 4/8/12/16/24/32 Token，禁止魔法数字；卡片内 8、卡片间 16、分组间 24–32 |
| 02 | 界面元素（按钮/icon/边框）对比 ≥ **3:1** | 次级按钮必须有足够边框，浅灰填充不能像 disabled；icon 用 Stone-600 不用 Stone-300 |
| 03 | **单一主按钮**：主/次/三级权重，一屏不出现多个实心黑主按钮 | 每个视图最多一个 `.btn-primary`，其余描边/幽灵 |
| 04 | 触控目标 ≥ **48×48pt**，按钮间隔 ≥ 8pt | 移动端导航/列表操作行高 ≥44px；桌面紧凑按钮 ≥32px |
| 05 | **重要内容可见**：别把高频操作藏进 `···` 菜单 | 分享/导出/刷新等高频操作直接露出 icon |
| 06 | 大标题减小字符间距（字越大减越多） | H1 `letter-spacing:-0.02em`，正文 0，全大写小标签 +0.05em |
| 07 | **不只靠颜色**：选中 tab 加下划线/字重/形状 | 状态=颜色点+文字+icon 三冗余；选中 tab 加 2px 下划线/底色 |
| 08 | 避免多重对齐：一个组件坚持单一基线（统一左对齐） | 卡片内标题/值/操作统一左对齐，tab 不居中 |
| 09 | 文本对比：小文本(≤18px) ≥**4.5:1**，大文本 ≥3:1 | muted 文字最低 Stone-500 (#78716C)，不用 Stone-400 做正文 |
| 10 | **移除多余容器**：分组 4 法——同容器/空间紧密/外观相似/对齐成线，已分组就别再套卡片 | 清理"卡片套卡片"，用间距+分隔线+标题代替多余 Card |
| 11 | 只用 regular / bold 两个字重 | 全局字重收敛 400/500/600（数字/标题 600–700），删除 300 细体 |
| 12 | **保持一致**：图片圆角与按钮圆角统一 | 建立 Radius Token：控件 8、卡片 12–14、浮层 16、移动大卡 20–24，禁止混用 |
| 13 | 不混淆极简与简单：极简是精炼不是缺信息 | 首页可干净，但关键状态/操作不能为了"空"而缺失 |
| 14 | 平衡 icon 与文字：视觉突出性一致 | 底部导航 icon 与文字同色同权重，文字达 4.5:1 |

---

## 4. glm-4.6v 视觉顾问诊断（去噪后，以 ZBIP Token 为准）

> 消耗 prompt 2015 + completion 2561 = 4576 tokens。注：模型建议的 #f5f5f5/#333 为冷灰，**不采用**，统一回 Stone 暖灰；以下只保留结构性与动效结论。

**值得采纳：**
1. 首页主标题视觉居中、输入框与快捷按钮间距收紧到 16px，形成"标题→输入→快捷操作"垂直流。
2. 字号三级明确：H1 24–28/700、输入提示 14/400、快捷按钮 13/500。
3. 输入框聚焦：边框 Stone-500 + `box-shadow:0 0 0 3px rgba(120,113,108,.12)`（我们已在 v4 设置页用此模式，推广到全局输入）。
4. 入场动效序列（ease-out 曲线、stagger 30–50ms、按钮 scale .98）——与 Emil 规则一致，可直接落地。
5. 模块滑动：`opacity+translateX/Y` 错峰滑入，落位后 `float`（translateY ±2px、3s ease-in-out infinite、不同相位）。
6. 阴影统一柔和化：`0 1px 2px rgba(28,25,23,.04),0 2px 8px rgba(28,25,23,.05)`，删除生硬 0 1px 3px 黑阴影。

**不采纳：** 冷灰色值、把语义状态点改灰（违背"语义色小状态点"签名）、压缩侧栏到 180px（我们导航项多，保持现状但内部滚动）。

---

## 5. "模块滑动 + 轻微漂浮"落地实现（纯 CSS/原生 JS，可直接用）

```css
/* 5.1 错峰滑入：父容器加 .stagger-in，子项自动错峰 */
.stagger-in > *{
  opacity:0;
  transform:translateY(10px) scale(.98);          /* 不从0开始 */
  animation:zb-in 280ms cubic-bezier(0.23,1,0.32,1) forwards;
}
.stagger-in > *:nth-child(1){animation-delay:0ms}
.stagger-in > *:nth-child(2){animation-delay:45ms}
.stagger-in > *:nth-child(3){animation-delay:90ms}
.stagger-in > *:nth-child(4){animation-delay:135ms}
.stagger-in > *:nth-child(5){animation-delay:180ms}
.stagger-in > *:nth-child(6){animation-delay:225ms}
.stagger-in > *:nth-child(n+7){animation-delay:270ms} /* 3-7项后不再加，避免末项等太久 */
@keyframes zb-in{to{opacity:1;transform:translateY(0) scale(1)}}

/* 5.2 落位后轻微漂浮（仅装饰性状态卡/徽标，非数据区） */
.zb-float{animation:zb-float 3.6s ease-in-out infinite}
.zb-float:nth-child(2n){animation-duration:4.2s;animation-delay:-1.2s} /* 不同相位/周期 */
.zb-float:nth-child(3n){animation-duration:4.8s;animation-delay:-2.1s}
@keyframes zb-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}

/* 5.3 按压 + 可中断过渡 */
.zb-pressable{transition:transform 140ms cubic-bezier(0.23,1,0.32,1),background-color 160ms ease}
.zb-pressable:active{transform:scale(.97)}
@media (hover:hover) and (pointer:fine){.zb-pressable:hover{background:var(--zb-surface-raised)}}

/* 5.4 尊重 reduced motion */
@media (prefers-reduced-motion:reduce){
  .stagger-in>*{animation-duration:1ms;animation-delay:0ms}
  .zb-float{animation:none}
}
```
```js
// 5.5 动态列表/路由切换时重放：进入视图再触发（IntersectionObserver，once）
const io=new IntersectionObserver((es)=>es.forEach(e=>{
  if(e.isIntersecting){e.target.classList.add('stagger-in');io.unobserve(e.target)}
}),{threshold:.08});
document.querySelectorAll('[data-stagger]').forEach(el=>io.observe(el));
```
- 共享元素"飞行动效"（列表卡→详情）后续用 View Transitions API 单独做，不在本次范围。

---

## 6. 对 ZBIP 各产品的落地优先级

| 优先级 | 落地项 | 影响面 |
|---|---|---|
| P0 | 全局 Motion Token（3 条缓动曲线 + 时长表 + reduced-motion 兜底） | 全站动效有统一标尺 |
| P0 | 首页 stagger-in 错峰入场 + 按钮 scale .97 按压 + 输入聚焦环 | 第一印象、用户最喜欢的"模块滑动" |
| P1 | Radius/字重/阴影/间距 Token 收敛（对应 14 技巧 #10/#11/#12） | 精致度、一致性 |
| P1 | 状态点统一 8px + 三冗余（点+文字+icon）、tab 选中下划线 | 可读性、无障碍 |
| P1 | 内置浏览器：CDP 截图流外壳对齐豆包/Chrome（标签栏/工具栏/外部打开已做），后续评估真 iframe 内嵌 | 用户明确要"像豆包内部打开" |
| P2 | 装饰性状态卡 zb-float 微漂浮、View Transitions 共享元素转场 | 高级感、流畅度 |
| P2 | 移动端 48pt 触控、Bottom Sheet、移动大卡 20–24px 圆角 | 手机端 |
| LATER | 极光渐变仅用于空状态/庆祝时刻，日常保持 Stone 侘寂 | 时尚调性点缀 |

## 7. DO NOT（红线）
- 不引入 React/Framer-Motion/GSAP/远程字体/大型动画库。
- 不动画 transform/opacity 之外的属性做高频动画；不动画键盘高频操作。
- 不把黑白灰主基调改成彩色/深色；语义色只做小状态点。
- 不为动效而阻塞交互、不在低端机掉帧；reduced-motion 必须兜底。
- 不改业务逻辑/API/DB，本蓝图仅指导 UI 层。

---
*研究素材原件留存于微信临时目录与本次抽帧（%TEMP%/ui_ref，87 帧）；glm-4.6v 原始诊断 _glm46v_diagnosis.md。*
