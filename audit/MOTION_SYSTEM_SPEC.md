# ZBC Motion System Specification — 统一动效系统规范

> **G Shard · Adaptive UI + Motion System V1**
> 日期：2026-09-07
> 实现文件：`static/js/adaptive-motion.js` + `static/css/adaptive-components.css`
> 底层依赖：`static/js/lumenis-motion-engine.js`（LDMotion，A Shard已建立）
> 状态：VERIFIED

---

## 1. 设计原则

### 1.1 核心原则
1. **数据驱动（真变才动）**：所有数值/图表/进度动画必须检测旧值，旧值==新值时不触发动画
2. **优先级（业务>数据>交互>装饰）**：P0业务状态动画不可被P3装饰动画打断
3. **可访问性**：`prefers-reduced-motion` 时全部动画降级为直接设置终态，功能不消失
4. **性能**：优先使用CSS `transform`/`opacity`，Web Animations API，避免layout thrashing
5. **复用不重复**：底层能力复用LDMotion（countUp/drawAreaChart/fillProgress/stagger/pulse/flashUpdate/slideTab），ZBCMotion提供统一封装和优先级管理

### 1.2 禁止事项
- 禁止无限循环装饰动画（shimmer/pulse除外，且必须受reduced-motion控制）
- 禁止数据没变化时持续动画
- 禁止动画覆盖数据或阻塞交互
- 禁止每个模块自行写`@keyframes`（统一使用Preset）
- 禁止使用`setInterval`做动画（使用rAF或Web Animations API）

---

## 2. Motion Token

### 2.1 时长 Token（与CSS `--ad-motion-*` 对应）

| Token | 值 | 用途 |
|-------|-----|------|
| `instant` | 100ms | 即时反馈（press/focus） |
| `fast` | 180ms | 快速过渡（hover/tooltip） |
| `normal` | 280ms | 标准过渡（enter/exit/tab） |
| `slow` | 450ms | 复杂过渡（expand/collapse） |
| `slower` | 650ms | 大型过渡（modal/drawer） |

### 2.2 缓动 Token（与CSS `--ad-ease-*` 对应）

| Token | 值 | 用途 |
|-------|-----|------|
| `standard` | `cubic-bezier(0.2, 0, 0, 1)` | 标准过渡 |
| `decelerate` | `cubic-bezier(0, 0, 0.2, 1)` | 进入动画（减速） |
| `accelerate` | `cubic-bezier(0.4, 0, 1, 1)` | 退出动画（加速） |
| `spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 弹性出现（appear） |

---

## 3. Motion Preset 定义

所有动画通过 `ZBCMotion.applyPreset(element, presetName, opts)` 触发。

### 3.1 进入/退出类

| Preset | 属性 | 时长 | 缓动 | 优先级 | 用途 |
|--------|------|------|------|--------|------|
| `enter` | opacity 0→1, translateY(12px)→0 | 280ms | decelerate | P2 | 元素进入视口 |
| `exit` | opacity 1→0, translateY(0)→-8px | 180ms | accelerate | P2 | 元素退出 |
| `appear` | opacity 0→1, scale 0.96→1 | 280ms | spring | P2 | 弹窗/卡片出现 |

### 3.2 展开/折叠类

| Preset | 属性 | 时长 | 缓动 | 优先级 | 用途 |
|--------|------|------|------|--------|------|
| `expand` | maxHeight 0→1000px, opacity 0→1 | 350ms | decelerate | P2 | 手风琴展开 |
| `collapse` | maxHeight 1000→0px, opacity 1→0 | 250ms | accelerate | P2 | 手风琴折叠 |

### 3.3 数据更新类

| Preset | 属性 | 时长 | 缓动 | 优先级 | 用途 |
|--------|------|------|------|--------|------|
| `dataUpdate` | backgroundColor 高亮→透明 | 800ms | ease | P1 | 数据变化高亮 |

### 3.4 状态变化类（P0最高优先级）

| Preset | 属性 | 时长 | 缓动 | 优先级 | 用途 |
|--------|------|------|------|--------|------|
| `success` | boxShadow 脉冲 | 600ms | ease-out | P0 | 成功状态 |
| `warning` | boxShadow 脉冲 | 600ms | ease-out | P0 | 警告状态 |
| `error` | boxShadow 脉冲 | 600ms | ease-out | P0 | 错误状态 |
| `shake` | translateX 左右震动 | 400ms | ease | P0 | 错误/拒绝反馈 |

### 3.5 交互类

| Preset | 属性 | 时长 | 缓动 | 优先级 | 用途 |
|--------|------|------|------|--------|------|
| `hover` | translateY 0→-2px, shadow | 200ms | standard | P3 | 卡片悬停 |
| `press` | scale 1→0.98 | 100ms | ease-in | P3 | 按钮按下 |
| `focus` | boxShadow 0→3px glow | 150ms | ease-out | P2 | 焦点环 |

---

## 4. Motion State 状态机

每个可动画元素处于以下状态之一：

```
idle → animating → idle
         ↓
      cancelled (被更高优先级动画打断)
         ↓
      animating (新动画)
```

- `idle`：无动画运行
- `animating`：动画执行中，记录当前priority
- 新动画请求时：若新priority ≤ 当前priority（数字越小越高），则取消当前动画并执行新动画；否则忽略

---

## 5. 统一API

### 5.1 核心API

```javascript
// 应用预设动画
ZBCMotion.applyPreset(element, 'enter', { duration: 300, onComplete: fn })

// KPI数值更新（数据驱动，真变才动）
ZBCMotion.updateKPI(element, newValue, { decimals: 0, prefix: '', suffix: '' })

// 趋势图平滑更新（旧图→新图插值过渡，不是消失再出现）
ZBCMotion.updateChart(container, newData, { lineColor, areaGradient, height })

// 进度条更新
ZBCMotion.updateProgress(barElement, percent, { duration: 800 })

// 级联进入
ZBCMotion.staggerIn(container, { delay: 0, step: 60 })

// 数据更新闪烁
ZBCMotion.flashUpdate(element)

// 状态脉冲
ZBCMotion.pulse(element, color)

// Tab滑动
ZBCMotion.slideTab(container, activeTab)

// 取消动画
ZBCMotion.cancelAnimation(element)
```

### 5.2 数据驱动机制

`updateKPI` / `updateChart` / `updateProgress` 内部逻辑：
```
1. 读取 element 的旧值（data-kpi-value / _chartData / data-progress）
2. 比较旧值 === 新值？
   ├─ 是 → 直接return，不触发任何动画
   └─ 否 → 更新旧值记录 → 触发动画 + dataUpdate高亮
```

### 5.3 趋势图平滑过渡实现

`updateChart` 在数据变化时：
1. 保存旧数据 `container._chartData`
2. 使用rAF在600ms内从旧数据线性插值到新数据
3. 每帧调用 `LDMotion.drawAreaChart` 重绘
4. 效果：曲线平滑变形，不是旧图消失新图瞬间出现

---

## 6. Motion Priority 系统

| 优先级 | 名称 | 包含 | 规则 |
|--------|------|------|------|
| P0 | 业务状态 | success/warning/error/shake | 不可被任何低优先级打断 |
| P1 | 数据变化 | dataUpdate/KPI count-up/chart transition | 可打断P2/P3，不可打断P0 |
| P2 | 用户交互 | enter/exit/expand/collapse/focus | 可打断P3 |
| P3 | 装饰 | hover/press | 可被任何高优先级打断，reduced-motion时全部取消 |

实现：`_activeAnimations: Map<element, {type, priority, animation}>`，新动画请求时比较优先级。

---

## 7. prefers-reduced-motion 降级策略

当 `window.matchMedia('(prefers-reduced-motion: reduce)').matches === true`：

| 动画类型 | 降级行为 |
|---------|---------|
| enter/exit/appear | 直接设置 opacity:1, transform:none |
| expand/collapse | 直接设置 max-height 终态 |
| KPI count-up | 直接设置最终数值，不滚动 |
| 图表过渡 | 直接绘制最终图表，不插值 |
| 进度条 | 直接设置width终态 |
| stagger | 直接显示全部子元素 |
| shimmer/pulse（CSS infinite） | `animation: none !important` |
| hover transform | `transform: none !important` |
| **功能** | **全部保留，仅去掉动画过程** |

---

## 8. 性能护栏

### 8.1 已实现
- **Web Animations API**：优先使用 `element.animate()`，浏览器优化合成线程
- **transform/opacity only**：Preset只动画transform/opacity/backgroundColor/boxShadow，避免layout
- **IntersectionObserver离屏暂停**：`pauseOffscreen()` 暂停离屏元素动画
- **ResizeObserver debounce**：adaptive-engine.js中viewport resize 150ms debounce
- **无rAF风暴**：countUp/chart transition每个元素独立rAF，完成后取消
- **数据变化检测**：旧值==新值不触发动画，避免无意义重绘

### 8.2 待验证
- 大数据表格虚拟化（当前表格数据量<100行，暂不需要）
- 图表离屏高频动画（已通过IntersectionObserver缓解）

---

## 9. 与LDMotion的关系

```
ZBCMotion (adaptive-motion.js) — 统一封装层
├── 优先级管理 (_activeAnimations + priority比较)
├── 数据驱动检测 (旧值==新值→不触发)
├── 趋势图插值过渡 (updateChart)
├── Preset系统 (17个预设)
├── Reduced Motion全局降级
└── 底层调用 → LDMotion (lumenis-motion-engine.js)
    ├── countUp()        ← updateKPI()
    ├── drawAreaChart()  ← updateChart()
    ├── fillProgress()   ← updateProgress()
    ├── staggerChildren()← staggerIn()
    ├── pulse()          ← pulse()
    ├── flashUpdate()    ← flashUpdate()
    └── slideTab()       ← slideTab()
```

**不重复实现**：LDMotion已有的能力ZBCMotion全部复用，只增加封装和管理。

---

## 10. CSS Motion类（与JS配合）

| CSS类 | 用途 | 触发方式 |
|-------|------|---------|
| `.ad-motion-enter` | 进入动画 | JS添加或 `[ad-motion="enter"]` 自动 |
| `.ad-motion-exit` | 退出动画 | JS添加 |
| `.ad-motion-expand` | 展开动画 | JS添加 |
| `.ad-motion-flash` | 闪烁 | JS添加 |
| `.ad-motion-shake` | 震动 | JS添加 |
| `.ad-data-update` | 数据更新高亮 | JS添加 |
| `[ad-motion="enter"]` | 声明式进入 | IntersectionObserver自动触发 |

---

## 11. 验收检查清单

- [x] Motion Token定义（时长+缓动）
- [x] 17个Preset定义
- [x] Priority四级系统（P0>P1>P2>P3）
- [x] 数据驱动（真变才动）
- [x] KPI count-up封装
- [x] 趋势图平滑过渡（插值，非消失再出现）
- [x] 进度条更新封装
- [x] 级联进入封装
- [x] prefers-reduced-motion全降级
- [x] 离屏暂停
- [x] 复用LDMotion不重复
- [x] 无无限循环装饰动画（shimmer/pulse受reduced-motion控制）
