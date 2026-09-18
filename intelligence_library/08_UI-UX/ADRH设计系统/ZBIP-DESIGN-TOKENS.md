# ZBIP Design Tokens

> Z-Brand Intelligence Platform 统一设计令牌。四库共享，各产品按职责适配。
> 版本：v1.0 · 维护方：AI-D Hub · 适用：DCC / SICI / Z-Brand / AI-D

---

## 1. 颜色体系

### 1.1 中性色（主体）

| Token | Dark | Light | 用途 |
|---|---|---|---|
| `--zb-bg` | `#000000` | `#F2F2F7` | 页面背景 |
| `--zb-bg-elevated` | `rgba(28,28,30,0.72)` | `rgba(255,255,255,0.78)` | 卡片/Sheet 背景（磨砂） |
| `--zb-bg-elevated-solid` | `#1C1C1E` | `#FFFFFF` | 卡片实色背景 |
| `--zb-bg-input` | `rgba(44,44,46,0.8)` | `rgba(118,118,128,0.12)` | 输入框背景 |
| `--zb-border` | `rgba(84,84,88,0.35)` | `rgba(60,60,67,0.18)` | 边框 |
| `--zb-border-strong` | `rgba(84,84,88,0.6)` | `rgba(60,60,67,0.3)` | 强调边框 |
| `--zb-text-primary` | `#FFFFFF` | `#1C1C1E` | 主文字 |
| `--zb-text-secondary` | `#8E8E93` | `#636366` | 辅助文字 |
| `--zb-text-tertiary` | `#636366` | `#8E8E93` | 三级文字/占位 |

### 1.2 状态色（彩色只承担状态）

| Token | Dark | Light | 状态 |
|---|---|---|---|
| `--zb-accent-blue` | `#0A84FF` | `#007AFF` | 主要操作 / Active / 信息 |
| `--zb-accent-green` | `#30D158` | `#34C759` | Success / Online / Pass |
| `--zb-accent-orange` | `#FF9F0A` | `#FF9500` | Warning / Pending / 处理中 |
| `--zb-accent-red` | `#FF453A` | `#FF3B30` | Error / Risk / Fail / Offline |
| `--zb-accent-purple` | `#BF5AF2` | `#AF52DE` | AI / 指令 / 研究 |
| `--zb-accent-teal` | `#64D2FF` | `#5AC8FA` | 历史 / 辅助 / 次要信息 |

### 1.3 彩色小圆点（ZBIP 状态视觉签名）

所有产品必须使用统一的状态圆点：

```css
.zb-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.zb-dot.success { background: var(--zb-accent-green); }
.zb-dot.active  { background: var(--zb-accent-blue); }
.zb-dot.warning { background: var(--zb-accent-orange); }
.zb-dot.risk    { background: var(--zb-accent-red); }
.zb-dot.offline { background: var(--zb-text-tertiary); }
.zb-dot.processing { background: var(--zb-accent-orange); animation: zb-pulse 1.5s infinite; }
```

**禁止**：大面积渐变、廉价发光、堆叠阴影、彩色卡片背景。

---

## 2. 字体体系

| Token | 值 | 用途 |
|---|---|---|
| `--zb-font-family` | `-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif` | 正文字体 |
| `--zb-font-mono` | `"SF Mono", Menlo, Consolas, monospace` | 代码/SHA/数字 |

### 字号层级

| Token | 字号 | 字重 | 用途 |
|---|---|---|---|
| `--zb-text-h1` | 22px | 700 | 页面主标题 |
| `--zb-text-h2` | 17px | 700 | 区域标题 |
| `--zb-text-h3` | 15px | 600 | 子区域/卡片标题 |
| `--zb-text-body` | 15px | 400 | 正文 |
| `--zb-text-caption` | 13px | 400 | 辅助说明 |
| `--zb-text-label` | 11px | 700 | 标签/状态（大写，letter-spacing 0.8px） |
| `--zb-text-metric` | 24px | 700 | 关键数字/指标 |
| `--zb-text-button` | 15px | 600 | 按钮文字 |

---

## 3. 间距体系

8px 基准网格。

| Token | 值 | 用途 |
|---|---|---|
| `--zb-space-xs` | 4px | 图标内边距/紧凑元素 |
| `--zb-space-sm` | 8px | 元素间距 |
| `--zb-space-md` | 12px | 卡片内边距/行间距 |
| `--zb-space-lg` | 16px | 区域内边距/卡片间距 |
| `--zb-space-xl` | 20px | 页面边距/大卡片内边距 |
| `--zb-space-2xl` | 32px | 区域间距/Section 间距 |
| `--zb-space-3xl` | 48px | 页面顶部/底部大间距 |

---

## 4. 圆角体系

| Token | 值 | 用途 |
|---|---|---|
| `--zb-radius-sm` | 8px | 标签/小按钮/状态徽章 |
| `--zb-radius-md` | 12px | 输入框/普通按钮/列表项 |
| `--zb-radius-lg` | 16px | 卡片/Sheet/主按钮 |
| `--zb-radius-xl` | 20px | 大卡片/Modal/搜索框 |
| `--zb-radius-full` | 9999px | 圆形/胶囊/Pill |

---

## 5. 边框体系

| Token | 值 | 用途 |
|---|---|---|
| `--zb-border-width` | 1px | 默认边框 |
| `--zb-border-width-strong` | 1.5px | 强调边框/Focus |
| `--zb-border-style` | solid | 默认样式 |

**原则**：优先细边框 + 低对比度 Surface 表达层级，减少厚重阴影。

---

## 6. 阴影体系

| Token | 值 | 用途 |
|---|---|---|
| `--zb-shadow-sm` | `0 2px 8px rgba(0,0,0,0.12)` | 小元素/按钮 |
| `--zb-shadow-md` | `0 4px 24px rgba(0,0,0,0.15)` | 卡片/Sheet |
| `--zb-shadow-lg` | `0 20px 60px rgba(0,0,0,0.4)` | Modal/弹出层 |
| `--zb-shadow-accent-blue` | `0 4px 16px rgba(10,132,255,0.3)` | 主按钮蓝色阴影 |

**禁止**：多层阴影堆叠、彩色发光阴影（除主按钮外）。

---

## 7. 磨砂玻璃（Frosted Glass）

```css
.zb-frosted {
  background: var(--zb-bg-elevated);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--zb-border);
  border-radius: var(--zb-radius-xl);
}
```

| 层级 | Blur | Saturate | 用途 |
|---|---|---|---|
| 卡片 | 20px | 180% | 普通卡片 |
| 顶部导航 | 20px | 180% | Sticky Top Bar |
| Modal/Sheet | 30px | 180% | 弹出层 |
| 搜索框 | 30px | 180% | 搜索弹出 |

---

## 8. 使用规则

1. **所有产品必须引用同一套 Token**，不得自行定义颜色/字号/间距。
2. **各产品可在 Token 基础上增加产品专属变量**，但必须使用 `--zb-` 前缀的基础变量。
3. **状态色只能用于状态**，不得用于装饰性背景。
4. **双主题必须同时定义** Dark 和 Light 两套值。
5. **Token 变更必须经过 AI-D Hub 审核**，并同步更新本文档。

---

## 9. 各产品适配说明

| 产品 | 适配重点 |
|---|---|
| DCC | 已有双主题+磨砂，需提取为独立 tokens.css |
| SICI | PWA 前端，需引入 Token，适配移动端 |
| Z-Brand | 仅 Dashboard/报告页面 UI 层，不碰业务逻辑 |
| AI-D | 母规范维护方，研究工作台 UI |
