# 序境 UI 视觉收敛 Evidence #04（辅助层令牌同步）

- 日期：2026-09-04
- 范围：static/css/style.css + static/css/ui_optimized.css 设计令牌
- 验证方式：playwright 截图 8201 首页 + computedStyle 采样

## 一、审计结论（实际驱动层已收敛）

首页（SPA static/index.html）实际视觉由 **zbip 系列** 驱动（引用顺序：style.css → ui_optimized.css → ... → zbip-tokens.css → zbip-components.css → zbip-theme-override.css 为最终覆盖层）。

- `zbip-tokens.css`：121 个 Stone 暖灰令牌（--zb-stone-*）
- `zbip-theme-override.css`（最终覆盖层）：已是完整序境侘寂体系
  - `--w-bg = #FAFAF9`（米白） / `--w-surface = #FFFFFF` / `--w-surface-2,3 = #F5F5F4`（暖灰）
  - `--w-border = #E7E5E4`（细线） / `--w-ink = #1C1917`（墨黑）
  - `--w-accent = #1C1917`（炭黑品牌强调）/ 语义色 danger/ok/info 保留为状态签名
- `zb-theme.css` 含 `body{background:var(--w-bg)!important;background-image:none!important}` 强制覆盖

**截图验证**：首页 body 采样 #FAFAF9 / header #F5F5F4 / div #FAFAF9，均为 Stone 暖灰；「序境·芥子纳须弥」「Z Brand Intelligence Platform」「序境·本地AI」品牌完全生效；中英文双语已呈现。→ **首页侘寂视觉已达成（并行会话 zbip 层贡献）**

## 二、本轮执行（辅助层同步，非实际驱动层）

`zb-theme.css` 之前（zbip 覆盖）的辅助层 `style.css`（iOS 蓝白）与 `ui_optimized.css`（GitHub 蓝白）令牌已同步为序境侘寂值（仅改 :root 值、不改变量名）：

| 文件 | 改动 |
|---|---|
| style.css | --bg→#F4F1EC、--surface→暖白、--text→#1B1917、--blue→#2A2622（炭黑）、--blue-soft→#ECE8E1、shadow→暖系；body 径向渐变白→米白（#FCFBF9/#F4F1EC/#ECE8E1）；语义色 green/red/amber/purple 保留 |
| ui_optimized.css | --primary-color→#2A2622、--primary-hover→#3A342C、--text-primary→#1B1917、--bg-primary→#FCFBF9、--bg-secondary→#F4F1EC、--bg-tertiary→#ECE8E1、--border-color→#E4E0D8；语义色保留 |

> 说明：这两层被 zbip 覆盖层最终接管，改动用于「非 zbip 区域一致化 + 旧组件渐变收敛」，不影响首页实际渲染（已截图确认首页渲染正常）。

## 三、后续收敛对象（登记，非本次）

- index.html 引用 **20 个 CSS 文件**叠加，为 P1 视觉收敛的核心治理项（收敛为 token 单一来源 + 按需加载）。
- 组件级残留硬编码 `rgba(10,132,255,*)`（旧 --blue）与纯白 #fff，按序境「低装饰」逐组件收敛（P1/P2）。

## 四、验证

- CSS 服务 200 + 侘寂令牌确认（#F4F1EC 命中）
- playwright 首页截图正常（暖灰+序境品牌+中英）
- 未改动 zbip 实际驱动层 → 无回归风险
