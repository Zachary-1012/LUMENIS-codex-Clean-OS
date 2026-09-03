# UI_AUDIT_05 — 数据驱动实时动效引擎 + 假数据清除 + 装饰彩色收敛

- 日期：2026-09-03（PDT）
- 范围：ZBC 序境-Core 前端（index.html / 动效引擎 / KOS / frontend_enhancement）
- 基线：HEAD ad1acf1；生产 8201；设计真相层 static/css/zbip-tokens.css
- 原则（用户指令 + 零号序列）：**动效底层逻辑必须由代码建立函数计算，有数据导入形成表格、表格转代码、进而形成实时动效**；动态 UI 必须绑定真实数据，禁止无数据假循环、禁止假数据。

## 一、架构：数据 → 函数 → 绑定表 → 动效（不出现无来源动画/错误）

```
/api/dashboard/all（app.js load，60s，既有统一总线，引擎零新增请求/零新增定时器）
  → window.__TAIKOO_POLL__ + 全局事件 'taikoo-poll'（复用，不另造）
  → zbip_motion.js · MotionTable（声明式绑定表：新增数据动效只加一行）
  → 纯函数层 toNum/rate/trendOf/compact（归一化/占比/带死区趋势/紧凑数值，可单测）
  → render：数值真变才触发一次性微光 .zb-value-flash；持续状态按真实在线挂 .is-live 呼吸
```

健壮性：逐绑定 try/catch；null/NaN/缺字段/除 0 一律保留占位不造假；选择器缺失即跳过；
首帧只填值不闪光；趋势带死区防抖；单例；暴露 `_fn/_table` 供单测与审计。

## 二、改动清单

| 文件 | 改动 |
|---|---|
| static/js/zbip_motion.js（新增） | 数据驱动动效引擎：MotionTable + 纯函数 + 数值/文本两类绑定 + 真实状态呼吸 |
| static/css/zbip-motion.css（新增） | 数据驱动动效层：一次性数据微光、真实状态呼吸、真实按压/hover/首挂载/真实加载骨架；**不提供无数据无限循环**；prefers-reduced-motion 全关 |
| static/index.html | ①右侧 4 个写死假指标(65%/9.8%/22/448K)→data-k 真实绑定，占位—；②两段写死洞察文案(65.0%/22条/评分83/编造话题)→data-k 文本绑定由真实 stats 生成，知识库段去假数字；③撤回上一版写死的 topbar 假流光/在线点假呼吸，改由引擎按真实状态驱动；④引入引擎；⑤remove_zap 三处闪电换非闪电语义图标 |
| static/js/kos_dashboard.js | TOP KOS 分层 S红/A橙/B蓝/C灰 高饱和 → Stone 灰阶（S#1C1917/A#44403C/B#78716/C#A8A29E），标签+进度条统一中性 |
| static/js/frontend_enhancement.js | 12 处 iOS 装饰蓝 #0a84ff 全部 Stone 化（按钮/数字/链接/选中态/业态卡边/分析块），**错误红 #ff3b30、成功绿 #34c759、风险红等语义色保留** |
| static/js/case_deep_analysis.js | search-std「外部增强结果」闪电图标 → 线性地球（remove_zap 收尾） |

## 三、刻意保留（经母规范过滤，不被视觉模型带偏）

- 正面 success 绿 / 负面 danger 红 / 高风险 attention 橙 / 风险·错误·NO_REPLY 红 / 在线·成功绿点：**数据语义色，保留**，仅用于关键状态。
- 主操作按钮 stone-900 近黑（不采纳视觉模型「改浅灰」）；圆角体系 r-sm/md/lg 不改 2px。
- 🔴🟡🟢 option 为绑定入库的风险等级数据值，不动；技术标识（Zachary 命名的 id/class/函数/资源名/btoa）不动。

## 四、验证 Evidence（真实测试，非自述）

1. 引擎纯函数单测 9/9 PASS：toNum 数字/空值、rate 占比/除0防护、trend 死区 up/down/flat、compact K/万/亿、pct1 空值。
2. Playwright 1440×900 真实 8201（Basic Auth）：
   - 4 指标由真实 stats 填充：正面 59.8%、负面 9.2%、高风险 23、总互动 46.1万(=461041)；首帧 data-trend=flat（不闪）。
   - 洞察文案真实生成：「正面 59.8%、负面 9.2%，共监测 1052 条」「高风险 23、中风险 80」——写死假值清零。
   - sysLive/aiLive 按真实 system_status/ai_status 挂 is-live=true。
   - KOS S 标签 computed background=rgb(28,25,23)=Stone-900，进度条黑条灰轨。
   - frontend_enhancement #0a84ff 残留=0；真实 pageerror=0（已过滤 credentials 噪声）。
3. node --check：zbip_motion.js / frontend_enhancement.js / kos_dashboard.js 全部通过。

## 五、Backlog（不在本批）

- MotionTable 目前绑定右侧 6 项；后续把趋势图/采集卡/KOS 卡等真实数据逐步登记进同一张表（加行即可，不重写）。
- frontend 动态块内 🌐💬🔗 emoji、index 剩余 24 个 emoji（登录/面板标题/平台品牌）按后续批次线性化；🔴🟡🟢 数据值不动。
- LEGACY 主题 CSS（design-v8/v9、*-minimal、zb-theme 等 33 link 层叠）逐页迁移回归后退役，不直接删。
- 数值环比趋势（较上周 ±%）需后端提供上周期真实数据后再启用，当前不编造。
