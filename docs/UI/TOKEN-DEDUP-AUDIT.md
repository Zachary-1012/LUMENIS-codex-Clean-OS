# ZBIP 设计令牌去重审计（P2）· 2026-09-03

> 只读审计，未修改任何 CSS。目标：量化重复，确立单一权威 token 源（Canonical Token Source），为后续视觉收敛提供数据基础。

## 一、量化总览

| 指标 | 数值 |
|---|---|
| CSS 文件数 | 34 |
| token 定义总数 | 1315 |
| 唯一 token 名 | 755 |
| 跨文件重复定义的 token 名 | 395（52%） |
| 同名不同值(冲突) token 名 | 350 |

## 二、重复最多的 token（top 12）

| token | 定义次数 | 取值(去重前3) |
|---|---|---|
| --topbar-height | 8 | 48px<br>52px<br>56px |
| --sidebar-width | 8 | 200px<br>220px<br>232px |
| --shadow-sm | 7 | 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)<br>0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)<br>0 1px 3px rgba(0, 0, 0, 0.08) |
| --shadow-md | 7 | 0 4px 12px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.03)<br>0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)<br>0 4px 12px rgba(0, 0, 0, 0.1) |
| --shadow-lg | 7 | 0 8px 24px rgba(0, 0, 0, 0.08), 0 4px 8px rgba(0, 0, 0, 0.04)<br>0 8px 24px rgba(0, 0, 0, 0.12)<br>0 8px 24px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.06) |
| --bg-primary | 6 | #1d1d1f<br>#FFFFFF<br>#ffffff |
| --bg-secondary | 6 | #000000<br>#F2F2F7<br>#f5f5f7 |
| --bg-tertiary | 6 | #2c2c2e<br>#FFFFFF<br>#f0f0f2 |
| --text-primary | 6 | #1C1C1E<br>#1a1a1a<br>#1d1d1f |
| --text-secondary | 6 | #57606a<br>#636366<br>#6b6b6b |
| --text-tertiary | 6 | #6e7781<br>#86868b<br>#8E8E93 |
| --shadow-xs | 6 | 0 1px 2px rgba(0, 0, 0, 0.03)<br>0 1px 2px rgba(0, 0, 0, 0.04)<br>0 1px 2px rgba(0,0,0,0.04) |

## 三、冲突 token 示例（top 20）

| token | 不同取值 |
|---|---|
| --ios-blue | #007AFF(1)<br>var(--w-accent)(1) |
| --ios-green | #34C759(1)<br>var(--w-ok)(1) |
| --ios-red | #FF3B30(1)<br>var(--w-danger)(1) |
| --ios-orange | #FF9500(1)<br>var(--w-warn)(1) |
| --ios-yellow | #FFCC00(1)<br>#D9A414(1) |
| --ios-purple | #AF52DE(1)<br>var(--w-ai)(1) |
| --ios-pink | #FF2D55(1)<br>#E0699A(1) |
| --ios-teal | #5AC8FA(1)<br>#18A0A0(1) |
| --ios-indigo | #5856D6(1)<br>#5B6FE8(1) |
| --ios-mint | #00C7BE(1)<br>#23B3A6(1) |
| --ios-cyan | #32ADE6(1)<br>#2FA8C9(1) |
| --ios-brown | #A2845E(1)<br>#A07E5C(1) |
| --ios-label | #000000(1)<br>#FFFFFF(1)<br>var(--w-ink)(1) |
| --ios-secondary-label | rgba(60, 60, 67, 0.6)(1)<br>rgba(235, 235, 245, 0.6)(1)<br>var(--w-ink-2)(1) |
| --ios-tertiary-label | rgba(60, 60, 67, 0.3)(1)<br>rgba(235, 235, 245, 0.3)(1)<br>var(--w-ink-3)(1) |
| --ios-quaternary-label | rgba(60, 60, 67, 0.18)(1)<br>var(--w-ink-4)(1) |
| --ios-system-background | #FFFFFF(1)<br>#000000(1)<br>var(--w-surface)(1) |
| --ios-secondary-system-background | #F2F2F7(1)<br>#1C1C1E(1)<br>var(--w-surface-2)(1) |
| --ios-tertiary-system-background | #FFFFFF(1)<br>#2C2C2E(1) |
| --ios-system-grouped-background | #F2F2F7(1)<br>#000000(1)<br>var(--w-bg)(1) |

## 四、收敛建议（未执行，需设计确认）

1. 确立 static/css/zbip-tokens.css 为 **Canonical Token Source**（对齐 ZBIP-DESIGN-SYSTEM）。
2. 冲突 token 按语义分组合并（尺寸/颜色/阴影/间距各一组），同语义唯一值。
3. 其余 CSS 的重复定义逐步改为 ar(--xxx) 引用，删除本地覆盖。
4. 改样式为视觉变更，需在 E2E 截图对比 + 全量回归后分批落地。
