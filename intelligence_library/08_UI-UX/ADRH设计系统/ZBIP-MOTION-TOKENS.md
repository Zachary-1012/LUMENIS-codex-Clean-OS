# ZBIP Motion Tokens

> Z-Brand Intelligence Platform 统一动效令牌。所有产品共享此动效体系，确保交互反馈一致、物理感统一、性能可控。
>
> 版本：v1.0 · 维护者：AI-D Hub · 最后更新：2026-08-31

---

## 1. 核心原则

1. **动效只服务于反馈、层级、状态、空间关系、物理感** — 不做无意义装饰动画
2. **快速响应** — 用户操作后 100ms 内必须有视觉反馈
3. **性能优先** — 低端手机必须 60fps，不使用导致重排的动画属性
4. **物理感** — 使用 Spring 模拟自然物理运动，不使用机械的线性动画
5. **可中断** — 所有动画必须可被用户操作中断，不锁定界面
6. **尊重系统设置** — 尊重 `prefers-reduced-motion`，用户关闭动效时禁用非必要动画

---

## 2. 时长令牌

### 2.1 标准时长

| Token | Duration | 用途 | 示例 |
|---|---|---|---|
| `--zb-duration-fast` | 100ms | 快速反馈 | 按钮按下、hover 状态变化 |
| `--zb-duration-normal` | 180ms | 普通状态转换 | 主题切换、卡片展开、标签切换 |
| `--zb-duration-slow` | 280ms | 页面/面板转换 | 页面切换、Bottom Sheet 弹出 |
| `--zb-duration-slower` | 420ms | 大面板/Modal | Modal 弹出、大尺寸 Bottom Sheet |

### 2.2 时长范围

| 类别 | 范围 | 说明 |
|---|---|---|
| 微交互 | 100–180ms | 按钮、开关、标签、hover |
| 状态转换 | 180–280ms | 主题切换、卡片展开、内容加载 |
| 空间转换 | 280–420ms | 页面切换、Modal、Bottom Sheet、导航 |
| 强调动画 | 420–600ms | 成功庆祝、重要状态变化（谨慎使用） |

**禁止**：
- ❌ 超过 600ms 的非必要动画
- ❌ 低于 80ms 的动画（人眼无法感知）
- ❌ 线性时长（linear）用于 UI 交互

---

## 3. 缓动函数

### 3.1 标准缓动

| Token | Value | 用途 |
|---|---|---|
| `--zb-ease-standard` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | 标准状态转换（进入+退出） |
| `--zb-ease-decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | 元素进入（减速） |
| `--zb-ease-accelerate` | `cubic-bezier(0.4, 0.0, 1, 1)` | 元素退出（加速） |
| `--zb-ease-sharp` | `cubic-bezier(0.4, 0.0, 0.6, 1)` | 快速响应（微交互） |

### 3.2 使用规则

| 场景 | 缓动 | 时长 |
|---|---|---|
| 按钮按下/释放 | `--zb-ease-sharp` | `--zb-duration-fast` |
| Hover 状态 | `--zb-ease-standard` | `--zb-duration-fast` |
| 主题切换 | `--zb-ease-standard` | `--zb-duration-normal` |
| 卡片展开/收起 | `--zb-ease-decelerate` (展开) / `--zb-ease-accelerate` (收起) | `--zb-duration-normal` |
| Modal 弹出 | `--zb-ease-decelerate` | `--zb-duration-slower` |
| Modal 关闭 | `--zb-ease-accelerate` | `--zb-duration-slow` |
| Bottom Sheet 弹出 | `--zb-spring-standard` | `--zb-duration-slow` |
| 页面切换 | `--zb-ease-standard` | `--zb-duration-slow` |
| 进度条变化 | `--zb-ease-decelerate` | `--zb-duration-normal` |
| 搜索框展开 | `--zb-ease-decelerate` | `--zb-duration-normal` |

---

## 4. Spring 物理动画

### 4.1 Spring 配置

Spring 用于需要物理感的交互：Bottom Sheet、开关、面板拖拽、卡片展开。

| Token | Stiffness | Damping | Mass | 用途 |
|---|---|---|---|---|
| `--zb-spring-standard` | 300 | 30 | 1 | 标准面板/Sheet |
| `--zb-spring-bouncy` | 400 | 25 | 1 | 强调/弹性效果（谨慎） |
| `--zb-spring-smooth` | 200 | 35 | 1 | 平滑/大面板 |
| `--zb-spring-snappy` | 500 | 35 | 1 | 快速响应/开关 |

### 4.2 CSS Spring 近似

```css
/* Spring 标准近似（CSS 不支持物理 Spring，用 cubic-bezier 近似） */
--zb-spring-standard-ease: cubic-bezier(0.16, 1, 0.3, 1);

/* 使用示例 */
.bottom-sheet {
  transition: transform 280ms cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 4.3 JavaScript Spring（如需精确物理模拟）

```javascript
// 推荐使用 spring 动画库（如 framer-motion / react-spring）
// 或手写 spring 物理公式：
const spring = {
  stiffness: 300,
  damping: 30,
  mass: 1,
};
```

---

## 5. 变换属性

### 5.1 推荐动画属性（GPU 加速，不触发重排）

| 属性 | 用途 | 性能 |
|---|---|---|
| `transform: translate()` | 位移 | ✅ 最佳 |
| `transform: scale()` | 缩放 | ✅ 最佳 |
| `transform: rotate()` | 旋转 | ✅ 最佳 |
| `opacity` | 透明度 | ✅ 最佳 |
| `filter: blur()` | 模糊（磨砂） | ⚠️ 中等 |

### 5.2 避免动画的属性（触发重排，性能差）

| 属性 | 原因 | 替代方案 |
|---|---|---|
| `width` / `height` | 触发重排 | 使用 `transform: scale()` 或 max-height 技巧 |
| `top` / `left` / `right` / `bottom` | 触发重排 | 使用 `transform: translate()` |
| `margin` / `padding` | 触发重排 | 使用 transform 或调整布局策略 |
| `display: none → block` | 无法动画 | 使用 opacity + visibility |
| `box-shadow` | 触发重绘 | 使用伪元素或 opacity 过渡 |

---

## 6. 交互动效规范

### 6.1 按钮

```css
button {
  transition: background 150ms var(--zb-ease-sharp),
              opacity 150ms var(--zb-ease-sharp),
              transform 100ms var(--zb-ease-sharp),
              border-color 150ms var(--zb-ease-sharp);
}
button:active {
  transform: scale(0.97);
}
button.primary:active {
  transform: scale(0.98);
}
```

### 6.2 卡片

```css
.card {
  transition: border-color 200ms var(--zb-ease-standard),
              transform 200ms var(--zb-ease-standard);
}
.card:hover {
  border-color: var(--zb-border-strong);
}
```

### 6.3 Modal / Bottom Sheet

```css
/* Modal 背景 */
.modal-overlay {
  opacity: 0;
  transition: opacity 280ms var(--zb-ease-standard);
}
.modal-overlay.active {
  opacity: 1;
}

/* Modal 内容 */
.modal-content {
  transform: translateY(-20px) scale(0.98);
  opacity: 0;
  transition: transform 320ms cubic-bezier(0.16, 1, 0.3, 1),
              opacity 280ms var(--zb-ease-standard);
}
.modal-overlay.active .modal-content {
  transform: translateY(0) scale(1);
  opacity: 1;
}
```

### 6.4 进度条

```css
.progress-fill {
  transition: width 400ms var(--zb-ease-decelerate);
}
```

### 6.5 主题切换

```css
body {
  transition: background 300ms var(--zb-ease-standard),
              color 300ms var(--zb-ease-standard);
}
```

---

## 7. 加载状态动效

### 7.1 Skeleton（骨架屏）

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--zb-bg-input) 25%,
    var(--zb-bg-elevated) 50%,
    var(--zb-bg-input) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
}
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### 7.2 Spinner（加载指示器）

```css
.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--zb-border);
  border-top-color: var(--zb-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### 7.3 进度条闪光（已在 DCC 实现）

```css
.progress-fill::after {
  content: '';
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 20px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4));
  animation: progress-shine 2s infinite;
}
```

---

## 8. reduced-motion 支持

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 9. 性能检查清单

- [ ] 所有动画使用 `transform` / `opacity`，不使用 `width` / `top` / `margin`
- [ ] 动画时长不超过 600ms（非必要）
- [ ] 低端设备（iPhone SE / 中端 Android）测试 60fps
- [ ] 尊重 `prefers-reduced-motion`
- [ ] 动画可被用户操作中断
- [ ] 不使用导致页面整体重排的动画
- [ ] 磨砂玻璃 (`backdrop-filter`) 动画限制在小区域

---

## 10. 各仓库实现状态

| 仓库 | 动效实现状态 | 说明 |
|---|---|---|
| AI-D | ✅ 本文件为母规范 | 待产出 CSS token 文件 |
| DCC | ⚠️ 部分实现 | 有基础 transition / 进度条闪光 / 搜索弹出动画，无统一 token |
| SICI | ⚠️ 待确认 | 未读取确认动效实现 |
| Z-Brand-Core | ⚠️ 待确认 | Dashboard 动效待确认 |

---

## 11. 反模式（禁止）

| 反模式 | 正确做法 |
|---|---|
| ❌ 无意义的装饰动画 | ✅ 动效只服务反馈/层级/状态 |
| ❌ 超过 1秒的动画 | ✅ 控制在 100-420ms |
| ❌ 线性缓动 (linear) | ✅ 使用 cubic-bezier 或 spring |
| ❌ 动画 width/top/margin | ✅ 使用 transform/opacity |
| ❌ 忽略 reduced-motion | ✅ 尊重系统设置 |
| ❌ 动画锁定界面不可中断 | ✅ 所有动画可中断 |
| ❌ 堆叠多层同时动画 | ✅ 错开动画时序 |
| ❌ 廉价发光/闪烁效果 | ✅ 克制使用强调动画 |

---

*本文件由 AI-D Hub 维护，动效变更需经过性能测试和 Cross-Repository Validation。*
