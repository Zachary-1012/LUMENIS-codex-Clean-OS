# 序境 CSS 收敛治理清单（CSS Manifest #01）

- 日期：2026-09-04 · 状态：INVENTORY-DONE · NO-BLIND-DELETE
- 依据：《序境》文件治理 + Lean Engineering（依赖收敛、token 单一来源）
- 实际：index.html 引用 **32 个 CSS**（早前估算 20 偏少），9 个文件定义 :root 变量，3 个定义 body 背景。

## 一、加载顺序与现状

| # | 文件 | KB | :root变量 | body | 判定 |
|---|------|----|----|----|------|
| 1 | tokens.css | 15.0 | 287 | False | BASE-TOKEN（早期基础，保留） |
| 2 | components.css | 31.6 | 0 | False | ACTIVE（基础组件/布局） |
| 3 | layout.css | 22.8 | 0 | False | ACTIVE（基础组件/布局） |
| 4 | style.css | 86.3 | 15 | True | LEGACY（被 zbip 覆盖，已同步侘寂令牌） |
| 5 | nomi_global_drag.css | 0.9 | 0 | False | ACTIVE（页面/组件级） |
| 6 | architecture_dashboard.css | 11.3 | 0 | False | ACTIVE（页面/组件级） |
| 7 | ui_optimized.css | 13.7 | 21 | False | LEGACY（被 zbip 覆盖，已同步侘寂令牌） |
| 8 | mobile.css | 20.0 | 0 | True | ACTIVE（移动端，含 body 覆盖） |
| 9 | case_deep_analysis.css | 12.1 | 0 | False | ACTIVE（页面/组件级） |
| 10 | v3_modules.css | 9.4 | 0 | False | ACTIVE（页面/组件级） |
| 11 | design-v8.css | 27.3 | 37 | False | LEGACY-ACTIVE（历史设计体系，部分组件仍用） |
| 12 | design-v9-gpt-codex.css | 29.7 | 30 | False | LEGACY-ACTIVE（历史设计体系，部分组件仍用） |
| 13 | tokens-minimal.css | 7.7 | 131 | False | LEGACY（131 变量，与 tokens.css 重复，待收敛登记） |
| 14 | components-minimal.css | 20.6 | 0 | False | LEGACY-ACTIVE（minimal 体系） |
| 15 | layout-minimal.css | 26.1 | 0 | False | LEGACY-ACTIVE（minimal 体系） |
| 16 | zb-theme.css | 43.6 | 73 | True | ACTIVE-LEGACY（body 强制覆盖，zbip 取代中） |
| 17 | zb-gpt-theme.css | 70.8 | 87 | True | ACTIVE（GPT 主题，87 变量） |
| 18 | zbip-tokens.css | 10.2 | 121 | False | AUTHORITATIVE（序境 Stone UI token 权威源） |
| 19 | zbip-components.css | 18.0 | 0 | False | ACTIVE（zbip 组件层） |
| 20 | zbip-theme-override.css | 5.3 | 51 | False | AUTHORITATIVE（序境主题覆盖层，最终生效） |
| 21 | zbip-shell.css | 27.3 | 0 | False | ACTIVE（zbip 组件层） |
| 22 | zbmp-workbench.css | 22.7 | 0 | False | ACTIVE（页面/组件级） |
| 23 | zbip-panels.css | 8.7 | 0 | True | ACTIVE（zbip 组件层） |
| 24 | splash.css | 10.8 | 0 | False | ACTIVE（页面/组件级） |
| 25 | resident_health.css | 11.0 | 0 | False | ACTIVE（页面/组件级） |
| 26 | internal_browser.css | 6.4 | 0 | False | ACTIVE（页面/组件级） |
| 27 | evidence_dashboard.css | 4.0 | 0 | False | ACTIVE（页面/组件级） |
| 28 | osai-shell.css | 3.6 | 0 | False | ACTIVE |
| 29 | brand_hub.css | 7.9 | 0 | False | ACTIVE |
| 30 | zbip-refine.css | 39.1 | 5 | True | ACTIVE |
| 31 | zachary-zbip.css | 5.9 | 10 | True | ACTIVE |
| 32 | ui_polish.css | 3.7 | 0 | False | ACTIVE |

## 二、token 单一来源声明（序境权威链）

1. **权威 UI token** = `zbip-tokens.css`（Stone 暖灰语义体系，121 变量）
2. **主题覆盖层** = `zbip-theme-override.css`（序境侘寂：--w-bg=#FAFAF9 米白 / --w-ink=#1C1917 墨黑 / --w-border=#E7E5E4 细线，51 变量）
3. **早期基础 token** = `tokens.css`（287 变量，被 zbip 系列覆盖，保留供非 zbip 组件引用）
4. 重复 token 体系（tokens-minimal 131 变量、design-v8/v9 等）标记 LEGACY，**不删除**，进入后续收敛队列。

## 三、收敛原则（本清单为治理层，不执行删除）

- 实际驱动首页视觉的 zbip 链已为 Stone 暖灰侘寂（Evidence #04 已截图验证）。
- 32 个 CSS 中 **LEGACY 类**（tokens-minimal / design-v8/v9 / style / ui_optimized / components-minimal / layout-minimal / zb-theme）为收敛候选，删除需逐文件人工确认（走 DOUBAO_DELETE_REVIEW）。
- 组件级硬编码色值（rgba(10,132,255,*)、#fff 等）按序境侘寂逐组件收敛（P2）。
- **加载瘦身**（登记为 P2 目标）：将 LEGACY 文件从 index.html 按条件移除/合并，先以 `?v=` 版本化保持缓存安全，再逐步卸载未引用 CSS。

## 四、验证
- 本清单为治理审计，未修改任何 CSS 引用顺序；首页渲染不受影响（Evidence #04/#05 E2E 通过）。