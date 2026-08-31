# Step4 · Z-Brand Core 工作台外壳 IA（GPT/Codex 式）v1.0

> 阶段：UI 一次性施工 · Step4（仅 `ui/staging-foundation` 分支，Staging 8301 旁路，验收前不合 main）
> 依据：用户 2026-09-01 指令 + 12 张 ChatGPT Work/Codex/设置参考图（`docs/reference/ui-research/ref-20260901-step4/ref01..12.png`）
> 原则：只加可回滚的 Shell 层（`zbip-shell.css` + `zbip-shell.js`），**不改业务/后端/数据库/采集/主体口径，不删任何源 DOM 与能力**。

## 1. 顶层定位（对齐用户口径）
- 系统打开即 **Z-Brand Core**（工作台外壳），不是直接掉进满屏 KPI。
- 左上角「工作区切换器」在两个产品工作区间切换（对应 GPT 的 Work / Codex，ref04）：
  - **CTH-POMS**：广州太古汇舆情监测，生产、默认进入、免密钥（当前唯一落地工作区）。
  - **ZBMP**：Z-Brand 品牌监测，**必须密钥**；点击先弹密钥门（ref 无直接对应，按用户"必须加密钥"）。当前为**前端门禁占位**（非空即记 localStorage 通过标记），**后端鉴权未接（未实测，待补）**，不硬编码真实密钥。
- DCC / SICI 不进此外壳（三仓独立，用户已令不动）。

## 2. 12 张参考图 → 实现映射
| 参考 | GPT/Codex 事实 | Z-Brand Core 落地 |
|---|---|---|
| ref01/05 | Work 主页：浅灰侧栏+白主区、工作切换、分组、居中"我们要做什么?" | 左栏 stone-100/主区白/外层 stone-200 窄留白色差；Home 居中"你今天想知道什么？" |
| ref04 | "工作⌄"弹 ChatGPT Work / Codex 双选+✓ | `.zb-ws-switch` 弹 CTH-POMS(✓)/ZBMP(锁·密钥) |
| ref02 | 项目卡：名称/任务数/仓库路径/本地路径/编辑 | 登记为后续"项目上下文卡"，本轮未做（ZBMP 单项目，非必需） |
| ref03 | 输入框下 chip：项目选择/新建/不在项目 | Home 输入框下快捷 chip：驾驶舱/今日高风险/最新事件/生成日报 |
| ref08 | Codex 侧栏：hover 行内线性操作 icon | 侧栏项 hover 态已做；行内重命名/归档后续按需（本系统无会话归档概念） |
| ref07 | 纯黑圆角小 tooltip"归档聊天" | `.zb-tip` 黑胶囊组件（全局 toast 复用同款） |
| ref09 | 账户浮层：API 密钥登录/显示宠物/设置 Ctrl+,/退出 | `.zb-account-btn` 浮层：邮箱通知/Zachary 助手/设置 Ctrl+,/退出登录 |
| ref10 | 设置页：同构侧栏+搜索框+分组+白卡行 | 侧栏搜索框已加；设置页同构侧栏为 Step7（当前设置仍走原 page-settings） |
| ref12 | 外观：主题/前景#1A1C1F/字号 14·13/对比度 | Token 已锁 stone-900 #1C1917、字号阶 12/13/14…，本轮外壳沿用 |
| ref11 | 颜色圆点色板（灰蓝绿黄粉橙紫黑） | `.zb-dot` 六语义小圆点（success/info/attention/risk/danger/muted）表重要度 |
| ref06 | 项目 AGENTS 悬浮卡 | 不适用（无多项目），跳过 |

## 3. 21 项导航 → 6 分组（运行时包裹，源 DOM 不删不改顺序外结构）
| 分组 | 功能（data-page） |
|---|---|
| 总览 | 舆情驾驶舱(overview，原"首页概览"改名) |
| 监测 | 舆情监测 monitor、风险预警 alerts、负面确认 negative、笔记搜索 notes、官方动态 official、话题监测端口 topic-campaign、热门话题 topics |
| 分析 | 数据分析 analysis、事件中心 events、事件关系图谱 event-graph、舆情日历 calendar |
| 品牌资产 | 品牌业态 brands、品牌营销案例库 swire、案例库 cases、案例深度拆解 case-analysis、品牌知识库 knowledge-base、品牌分析报告 brand-report、App 证据 app-evidence |
| 产出 | 报告中心 reports |
| 系统 | 系统设置 settings |

- 全部沿用既有**线性内联 SVG 图标**（stroke 1.8），外壳统一 16px/stone-500/极轻 drop-shadow，不引入图标库。
- 侧栏：宽 248、项高 32、圆角 6、active=stone-200 胶囊+600 字重；内部独立滚动；旧 side-footer/architecture-panel 在外壳下隐藏（Step3 塌陷根因的根治延续，DOM 保留）。

## 4. Home（默认落地）与视图层级
- 默认进入显示 `#zbHome`：居中标题 + Zachary 提问框（复用现有 `#zacharyInput`/`sendZacharyMsg()`/`toggleZacharyChat()`，**不新造 AI**）+ 4 快捷 chip + 副标。
- 点任意侧栏功能 / chip → 收起 Home，进入对应现有 page-view；**现有 overview 6 KPI + 风险/事件/话题/日历完整保留为"舆情驾驶舱"二级页**（实测出数 957/622/241/94/22/448,410）。
- 双击左上工作区名回 Home。
- 旧乱飘 `#zacharyFloat` 在外壳下 `display:none`（功能收进 Home 与账户入口，源 DOM 保留）。

## 5. 账户层级（对齐用户）
底部账户按钮（Z 头像 + Zachary + 本地账户·工作区）→ 浮层：
- 邮箱通知（→设置，邮箱配置在 page-settings）
- Zachary 助手（打开既有 Zachary 聊天面板）
- 设置 Ctrl+,（→ page-settings）
- 退出登录（本地单机暂无账号体系，点击 toast 如实说明"待接入"）

## 6. 已实测（8301，2026-09-01）
- 结构：shellOn、6 分组、工作区切换/搜索/账户/Home 注入、21 项全保留、乱飘 float=none、无新增 console error（仅既有 three.js deprecation warning）。
- 交互：工作区浮层 CTH/ZBMP 双项 ✓；ZBMP 密钥门开关 ✓；搜索"事件"→仅显 2 项/隐 19，清空恢复 21 ✓；账户浮层 4 行 ✓；账户→设置跳 page-settings ✓；chip→驾驶舱且 KPI 真实出数 ✓；双击回 Home ✓。
- 视口：桌面 1241/1385 单份正常；390 移动默认侧栏 translateX(-260) 抽屉、汉堡滑出、Home 标题 24px。
- Evidence：`docs/UI/evidence/step4-home-desktop.png`、`step4-cockpit-desktop.png`。

## 7. 未实测 / 遗留（登记，不冒充完成）
- **未实测** 430/768/1024/1280/1440 断点（CDP emulate 宽度与真实窗口不一致、DSF 合成左右残影，属工具限制；DOM 断言单份，需真机/手动补图）。
- ZBMP 密钥门为前端占位，**后端鉴权/密钥来源未定（需用户拍板：本地配置项 or API Key 体系）**，通过后 ZBMP 工作区页面本身尚未建。
- 设置页"同构侧栏"（ref10/12）为 Step7，当前仍用原 page-settings。
- 常规搜索当前只过滤侧栏功能；后续可与既有 `#commandPalette`（Ctrl+K）合并为统一命令搜索。
- 驾驶舱 KPI 卡的 metric-icon 弱底、sparkline 多色为 Step5 精修项；右侧 AI 洞察面板写死假数据（65%/9.8%/22/448K）仍待接真实数据。
- 顶栏 `.top-actions`（采集/AI/导出）保留；Home 下是否进一步弱化待视觉验收。
- 回滚：删除 index.html 中两行 `[STAGING ONLY]` 引用即完全卸载，无其他残留。
