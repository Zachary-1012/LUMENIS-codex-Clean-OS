# 序境前沿研究简报（2026-09-07）

> 来源：全网 + GitHub 开源项目实时检索。只提炼可落地、与 ZBC 现有架构方向一致或需补强的点，不堆砌、不重写。

## 1. 小红书 / RedNote 采集（对标 2026 主流开源）

参考项目：yangsijie666/xiaohongshu-crawler、nodite/rednote-mcp、iFurySt/RedNote-MCP、Apify RedNote API、socai 7 工具源码评测。

| 主流做法 | ZBC 现状 | 结论 |
|---|---|---|
| Playwright/CDP 真实浏览器 + stealth 指纹补丁（navigator.webdriver、browserforge 真实指纹） | CDP 9222/9223 真人持久 Edge + cookie 桥接 | 方向一致；可补指纹自检（检测 navigator.webdriver 是否泄漏） |
| 住宅代理区域与账号区域一致 | 9222 大陆 / 9223 港版分通道 | 已对齐；**严禁跨区混用代理** |
| maxConcurrency=1 低并发、详情按需（先列表后详情） | CollectorGuard 资源守卫 + 核心词深采/扩展词浅采 | 已对齐 |
| 仿人鼠标轨迹 + settle/scroll/read 随机停顿 | human_cadence 占位（NOT_VERIFIED） | 保守占位正确，上线前需真人数值校准，不编默认值 |
| 登录态持久化、失效显式 NEED_VERIFY | 八态状态机 + Auth 全局弹窗 | 已对齐且更完整 |
| xsec_token 导航失败、隐藏元素点击是高频 bug | rednote_collector.cjs 已处理 | 持续回归 |

**落地结论**：不引入新框架（不复制第二套采集器）。仅补一项「采集前指纹自检」：CDP 页面 evaluate `navigator.webdriver`，若为 true 记录 RISK_WARNING（不阻断，只观测），符合"不破解风控、只做可观测"红线。

## 2. AI Browser 对标 Safari（用户明确：对标 Safari 非 Chrome）

关键参考：**achiya-automation/safari-mcp**（97 工具，原生 WebKit / Apple Silicon 比 Chrome 省约 60% CPU / 复用真实浏览器登录态 / 后台运行不抢焦点 / 不依赖 Puppeteer/Playwright/WebDriver）；ntegrals/openbrowser（停滞检测、成本追踪、replay 录制、沙箱资源限制）；pixqc/agent-browser（Action Policy 静态文件门控危险动作 + 子资源域名白名单）；Skyvern（vision-first 抗 DOM 改版）。

可吸收的 Safari 式产品理念（落到我们自研 browser_surface，不换内核、不引依赖）：
1. **真实会话复用、后台不抢焦点**：采集/AI 浏览在后台 tab 进行，不把用户当前窗口顶到前台（对齐官方账号只读红线）。
2. **原生般克制的交互**：标签/书签/阅读器/前进后退，界面克制，不做花哨 Chrome 式重型 UI。
3. **Action Policy = 我们的 Action Firewall**：危险动作静态门控 + 子资源/域名白名单（internal host 白名单已有 `_is_internal_host`，扩展到导航外跳需用户同意）。
4. **Replay 录制 = 我们的 Evidence/Trace**：每步 before/after state + 截图 + verification，已在 Browser Evidence 字段要求中。
5. **停滞检测（stall detection）**：页面 N 秒无变化判定卡死 → 恢复，而非无限等待。
6. **vision-first 兜底**：DOM 选择器失效时用截图+可访问性树判断，不盲目重试坐标。

**落地结论**：browser_surface 补标准化 `observe()`（snapshot+a11y tree+url+readyState 一体）与 `verify_action(expected)`（Expected vs Actual State），以及 `stall_detect()`；内核继续用现有 CDP，不切 WebKit（Windows 生产环境、三通道已稳定，换内核=重复造轮子，违背宪法）。

## 3. 品牌智能 / 社媒聆听（ZBMP 领域跟进，不落后）

2026 主流能力（Brand24 / Sprout / Meltwater / Brandwatch / Phyllo / merciv）：
- **AI 提及监测**：品牌在 ChatGPT/Claude/Gemini 回答中的提及 = 新型"声量/backlinks"（新趋势，列 P2 观察，不本轮强上）。
- **视觉提及识别**：图片/视频里的品牌露出（依赖多模态，glm-4.6v 已配，可作 ZBMP 远期能力）。
- **每条洞察带来源归因 + 置信度分**（source attribution + confidence）——与 ZBC Evidence/置信度体系完全一致，继续强化。
- 竞品 share of voice / 情感分布 / influencer 识别 / 24 个月历史归档 / 布尔检索。
- ZBMP Competition 独立入口方向正确；Growth 作为跨模块结果指标并入 Overview+Brand Tab 的决策与主流一致（增长是结果不是独立功能）。

**落地结论**：ZBMP 指标体系方向不落伍；本轮不新增重型模块，把"每条指标可回溯来源/函数/时间/置信度"做扎实（数据展示链 Source→Evidence→Canonical→Function→Metric→View Model→动态可视化）。

## 4. 三仓协议（线上 origin/main 权威，非自编）

取自 `00-GOVERNANCE/LUMENIS-PRODUCT-CONVERGENCE-MASTER-V1` 第 4 节与 `LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0`：
- ZBC 序境=独立生产产品；OSAI=独立 Intelligence/Capability Core（**即用户所说"自研 AI=未命名 OSAI"**）；GGI=独立 Research/Growth 产品；LUMENIS Command=研发控制侧车。
- 铁律：不跨仓运行时硬依赖、不共享生产 DB、不复制另一产品业务代码；共享只能经**明确、版本化、可追溯的 Contract/Artifact**。
- 融合面：Contract + Skill + Evidence + Evaluation + Lifecycle + AI Gateway + Trace；两 Core 永不物理合并。
- 学习数据流：ZBC 产经验证经验（Task→Result→Evidence→Evaluation→Feedback）→ Validated Artifact → OSAI Admission；未验证=CANDIDATE 不回写生产。
- 自研 AI 持续学习：全网学习（S33 Web Research / S35 Technology Scout / S40 Research-to-Product）+ 过往资料库学习（intelligence_library 711 assets），学习结果走 Contract 回灌，不直接改 Production Truth。

## 5. 本轮直接行动项（已做 / 待做）

- [x] rednote(9223 intl)/小红书(9222 cn) 交替轮番 + KOS 强制 intl（commit 3fde2f6，45 测试通过）
- [x] 确认 KOS 采集已走 XHS_RETINAUT(9223 rednote.com)，不重开发
- [ ] browser_surface 补 observe/verify_action/stall_detect（团队进行中）
- [ ] 采集前 navigator.webdriver 指纹自检（只观测记录，不破解）
- [ ] AI 提及监测、视觉提及识别列 P2 观察池，本轮不实现
