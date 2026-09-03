# P1 UI 收敛 Evidence #06 — 启动海报(Splash)序境化重构 v4

- 日期：2026-09-04
- 范围：static/index.html（splash-content）、static/css/splash.css
- 触发：用户纠正——「芥子纳须弥」是品牌哲学/理念，不是产品主标题；UI 视觉直接用视觉模型(glm-4.6v)设计，算力不省。

## 一、问题（重构前）
1. 主标题写成「序境 · 芥子纳须弥」，把品牌哲学当成产品名主体，产品名不突出。
2. 三张状态卡用 Emoji（📡⚠️🤖），违反序境母规范「禁 Emoji 当正式 Icon，统一线性 SVG/currentColor」。
3. 顶部三个小灰块 brandmark 与主标题信息重复；轨道环/光斑偏重。

## 二、重构后信息层级（自上而下）
| 层 | 内容 | 规格 |
|---|---|---|
| 哲学 eyebrow | — 芥子纳须弥 —（两侧 1px 细线） | 12px / ls 5px / Stone-500 #78716C |
| 产品主标题 | **序境** | 46px / 600 / ls 6px / Stone-900 #1C1917（移动 34px） |
| 英文平台名 | XUJING · Z-BRAND INTELLIGENCE PLATFORM | 11px / ls 2.5px / Stone-400 |
| 产品定位 | CTH-POMS · 实时舆情 · 风险预警 · 智能报告 | 13.5px / Stone-500 |
| 状态卡 ×3 | 线性 SVG + 语义色浅底 + 语义色小圆点 | 见下 |

## 三、线性 SVG Icon（stroke 1.5 / currentColor / 21×21，替代 Emoji）
- 采集状态：信号弧（双弧 + 中心点），success #16A34A
- 风险预警：警告三角 + 感叹点，attention #D97706
- AI 引擎：芯片（本体 + 引脚），info #2563EB
- 状态点发光同步为对应语义色 0.35 透明，去除廉价高饱和。

## 四、视觉模型两轮（glm-4.6v）与人工筛选
- 审计轮：采纳「序境升主体 / 哲学降 eyebrow / Emoji 换线性 SVG / 去冗余 brandmark / 弱化轨道环」。
- 验收轮结论「基本达标」，再采纳：状态卡改暖白纸感 #FDFCFA（消除纯白 vs 暖米生硬）、进度条由死黑渐变改为 Stone-300→Stone-600(#57534E)、间距微调。
- **不采纳**并记录理由：①「微光银流动加快到 0.8s」——违背克制动效，缓慢 6s 扫光才高级；②「哲学细线改更淡 #E0E0E0」——比现状 #D6D3D1 更淡，自相矛盾。
- 保留（用户明确要求）：银色流光 / 海浪 / 柔光光斑 / 颗粒，仅降低透明度为微光（光斑 0.25→0.14、流光 0.6→0.34、轨道环 opacity 0.55、轨道点 8→6px）。

## 五、验证（playwright 真实渲染）
- 桌面 1440×900@1.5x：splash_v4_desktop.jpg，层级/线性 icon/微光达标。
- 移动 iPhone14 390×844@2x：splash_v4_mobile.jpg，标题/三卡完整居中无溢出。
- 加载时序：1.5s 海报显示(opacity=1) → 6s 自动移除、正常进入主界面；主界面 innerText 3184 字符，pageerror 0。
- 生产 8201 /healthz v5.9.9 正常；静态文件即时生效，无需重启。

## 六、协作记录（重要）
本仓存在并发施工进程（同作者、同窗口时段），splash HTML + CSS 主体重构已被其提交 542b435 / 8f633dc 一并入库（并为「芥子纳须弥」补了 data-xujing-i18n="brand.tagline" 三语标签，与本重构方向一致、无冲突）；本次提交仅补最终 8 行 tune（卡片纸感 / 进度条去黑 / 两处间距）与本 Evidence、截图。提交前已 fetch 确认本地=远程 0/0，未覆盖任何并发成果。

## 七、截图
- splash_v4_desktop.jpg（29KB）、splash_v4_mobile.jpg（54KB，JPEG q82，由 2x PNG 压缩以保持仓库精简）
