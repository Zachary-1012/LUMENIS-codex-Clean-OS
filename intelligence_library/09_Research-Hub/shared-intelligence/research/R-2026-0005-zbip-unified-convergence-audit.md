# R-2026-0005 — ZBIP 四库统一收敛：Phase1 事实审计 + Phase2 落地一致性审查

- Research ID: R-2026-0005
- AI Agent: 豆包（Engineering Execution，只读审计 + 收敛建议）
- Owner: AI-D Hub
- 类型: 研究 / 审计（research）。本轮**不修改任何产品仓库代码、不重构、不删文件**。
- 任务来源: 用户「ZBIP 四产品统一架构/规则/UI视觉/交互收敛指令」（母规范 + 各产品按职责适配；4 仓库 / 5 产品身份）。
- 永久基线（只增不减）: 三方反哺、互相验证、边界不破、能力共享、责任分明。

---

## 0. 任务边界

本研究严格执行用户指令的 Phase 1（读取）与 Phase 2（收敛 Map），**停在写代码之前**：

- 只以 GitHub 当前事实为准（当前 Commit SHA / 当前代码 / 当前 README / 当前 Protocol），不凭聊天历史或旧 SHA 下结论。
- AI-D 已存在的 `design-system/` 五份母文档（Architecture Map / Feature Ownership / Design Tokens / Icon / Motion）**复用，不重写**；本研究只做「母文档 ↔ 四仓真实代码」的落地一致性（gap / conflict）审查。
- 发现冲突按指令 STOP：记录【冲突位置 / 当前实现 / 基线要求 / 影响 / 建议】，不自行扩大修改。
- 母规范是「一个设计系统 + 四套产品信息架构」，不是把四库做成相同页面。

---

## 1. Observed SHAs（含审计过程中的停机重读）

审计开始与进行中，四库被并行会话持续推进。按「GitHub 唯一事实源」规则两次停机重读，最终以以下 HEAD 为准：

| 仓库 | 最终 observed HEAD | 其上紧邻提交 | 备注 |
|---|---|---|---|
| AI-Development-Research-Hub | `1069c80` docs(design-system): ZBIP-MOTION-TOKENS v1.0 | `1fb645f` ZBIP-ICON-SYSTEM v1.0 | 本轮 R-0004 收尾 HEAD 为 `5b38902`，其后新增 `design-system/` 5 份母文档 |
| Z-Brand-Core | `06fd0c8` 弹窗精简补丁 modal_simplify | `ebb9a0a` scoped ZBIP mobile design token layer | 两条分别由不同端推送 |
| SICI-Core | `cb13e57` scoped ZBIP mobile design token layer | `bb22dfa` ZBIP unified baseline | |
| Development-Command-Console | `cd1b2ec` scoped ZBIP mobile design token layer | `a430ba9` primary buttons accent blue | |

> 事实校验：本地 `git clone` 走 https 被网络重置（Connection reset），故全部代码事实通过 GitHub MCP `get_file_contents / get_commit(stats)` 只读获得；DDC index.html 因结果超长下载到本地 `_audit/ddc_index.html`（53,350 bytes）做结构提取。

---

## 2. Phase 1 — 四仓现状快照（真实代码）

### 2.1 总览

| 维度 | Z-Brand-Core（CTH-POMS + ZBMP 同仓） | SICI-Core（SICI） | DCC | AI-D（Hub） |
|---|---|---|---|---|
| 形态 | Python 生产后端 + 两套前端并存 | 纯静态 PWA | 静态单页 + Node 本地 Bridge | 研究/契约库，无生产前端 |
| 后端 | Flask 风格（app.py 等，根目录约 150 文件） | 无（Pyodide 前端跑 Python、localStorage） | `server/` 8 个 Node 模块，127.0.0.1:8787 | Python `src/contracts` |
| 前端入口 | ① `templates/` Jinja 5 页；② `static/index.html` 独立 SPA | 单 `index.html` + `css/style.css` | 单 `index.html`（**内联** `<style>`，无独立 css 目录） | 无（研究工作台 UI 待建） |
| 样式文件数 | `static/css/` **25 个**（多代叠加，含 `.bak_011101` 备份入库） | 1 个 style.css | 内联于 index.html | design-system 母文档 |
| 构建/依赖 | package name `taikoo-monitor` v5.6.2，npm 仅 playwright | 无 package.json、无构建 | package v0.5.0，node>=18 | 离线 unittest |
| 测试 | tests/（生产回归） | 手动 / 浏览器 | `node --test` 7 个 + python 4 个 | 101 pass / 0 fail（离线） |
| 部署 | 生产服务器 + Docker | PWA | 本地 Bridge | 公开（严格脱敏） |

### 2.2 Z-Brand-Core —— CTH-POMS / ZBMP 同仓双身份

- **Flask templates（CTH-POMS 生产驾驶舱）**：`base.html` 顶部标题写死「广州太古汇舆情监测系统 v5.8.9」，横向导航 = 仪表盘 / 舆情笔记 / 舆情事件 / 报告中心 / 品牌业态 / 案例库 / 负面审核；模板 5 个：base/index/events/notes/report。
- base.html 实际 `<link>` 仅 4 个 CSS：`style.css`、`zachary_robot.css`、`architecture_dashboard.css`、`ui_optimized.css`；实际加载 9 个 JS。
- **第二套前端**：`static/index.html`（SPA），`06fd0c8` 在此引入 `static/js/modal_simplify.js`（206 行，笔记/事件/案例三弹窗「核心外露、次要折叠」，含 Light/Dark + 768px 响应式）。即 Z-Brand 前端是「Flask 模板 + static SPA」**双轨**。
- **生产红线文件在位**：`subject_rules.py` / `subject_classifier.py`（SUBJECT_WORDS / subject_hit / _subject_sql_and_values）、`daily_report.py` / `report_engine.py`（aggregate_events / build_daily_report）。本轮未触碰，后续 UI 收敛也禁止削弱。
- **样式多代并存（头号技术债）**：`static/css/` 25 文件，可辨多代体系：`style.css`(80KB)+`style.css.bak_011101`(75KB 备份)、`design-v8.css`、`design-v9-gpt-codex.css`、`zb-theme.css`/`zb-gpt-theme.css`(44/70KB)、`ui_modern/ui_optimized/ui_dashboard`、`apple-ui`、`components(-minimal)`、`layout(-minimal)`、`tokens.css`/`tokens-minimal.css`、以及新一代 `zbip-tokens.css`/`zbip-components.css`。
- **版本号不一致（事实冲突，记录不擅改）**：package.json = 5.6.2，页面标 v5.8.9。
- 根目录扁平、备份/版本文件入库（app_backup_v589.py、web_monitor_v570.py、video_part_*.jpg 等）——工程整洁度归 DDC 治理范畴，本任务只登记，遵循只增不减、不删除。
- **ZBMP 身份入口待最终定位**：同仓的「品牌传播/市场情报」界面疑似在 static SPA / `zb-preview.html` / `topic_campaign.*`，本轮未逐页确认，标 NOT VERIFIED，不在此臆断。

### 2.3 SICI-Core —— 手机端开发执行控制台（PWA）

- 单 `index.html`，6 个 view：home / code / test / github / deploy / settings（左侧栏导航：首页、代码运行、测试·E2E、GitHub、部署管理、设置）。
- 组件已较齐：login、sidebar、topbar、suggestion-grid、card、segmented-control、editor/output、context-menu、**bottom action-sheet**、modal、toast、toggle、swipe 删除、haptic；`@media(max-width:768px)` 抽屉侧栏 + `env(safe-area-inset-*)`；PWA manifest + apple-mobile meta 齐全。
- `css/style.css` 已自带一套 token：`:root` 浅色（白底/深灰粗边 #333、radius 10/14/20、状态 green#10a37f/blue#007AFF/red#FF3B30/orange#FF9500）+ `[data-theme=dark]`；Apple 弹簧 cubic-bezier；**是四库中自有设计系统成熟度最高、可作交互母版参考的一个**。
- 问题：① `js/` 有 8 个模块但 index.html 只引 6 个——**`research-learning.js`、`three-repository-verifier.js` 悬空未接入**；② 设置-关于页仓库名是占位 `Zachary-1012/--Zachary`（应为 SICI-Core），版本 v2.0.0；③ 导航/操作图标用 Unicode 字符（◉ ▶ ✓ ⌥ ☁ ⚙ ☰ ↗ ⧉），与母 Icon System「Linear 单色 SVG、禁用 emoji/字符做正式图标」不符。

### 2.4 Development-Command-Console —— 工程治理控制台

- 单 `index.html`（53KB），**内联** `<style>`，默认 **Dark** 的 iOS 风（#000 + frosted glass 毛玻璃、Apple 系统六彩 blue/green/orange/purple/red/teal、rgba 细边、`[data-theme=light]`）。
- 页面为单页纵向 section 流：task / contract / cmd / level / audit / bridge（含 tab-row），前端逻辑薄（`js/github-audit.js`），治理重在 `server/`（config/change-plan/evidence-bundle/learning-store/security/shadow-learning/snapshot/server）。
- 测试最完整：`npm test`（node --test 7 个）+ `test:python`（research_registry / learning_cycle / capability_delta / promotion_gate）。

### 2.5 AI-Development-Research-Hub —— 研究学习中枢（本仓）

- 无生产前端 / 无 Runtime；`src/contracts`（research_record / safe_collection）+ research / cases / data / benchmarks。
- `design-system/` 已存在 5 份母文档（v1.0，2026-08-31）：ARCHITECTURE-MAP（六层架构 + 四库职责/Owner/数据流/成熟度）、FEATURE-OWNERSHIP（DS/EG/RL/PB/MB 能力唯一 Owner 注册）、DESIGN-TOKENS、ICON-SYSTEM、MOTION-TOKENS。**这是 Phase 2 的既有产出，R-0005 不重复编写，只审查其与真实代码的一致性。**

---

## 3. 核心发现：设计 Token 已出现「四套并存、两张皮」

收敛刚开始，规范与各仓实现已经分叉，若不现在钉死唯一真相（SSOT），会演化成新一代 N 套 token。逐值对比如下（均来自真实文件）：

| 维度 | A. 母 `DESIGN-TOKENS.md` | B. 母 `ICON/MOTION.md` 用词 | C1. SICI/DDC `ZBIP_DESIGN_TOKENS.css`（blob `2210afc`，两仓逐字节相同） | C2. Z-Brand 根 `ZBIP_DESIGN_TOKENS.css`（blob `137a6f0`） | D. Z-Brand `static/css/zbip-tokens.css`（更早一版） |
|---|---|---|---|---|---|
| 变量命名 | `--zb-text-primary` `--zb-accent-blue` | `--zb-blue` `--zb-green` | `--zb-text-2` `--zb-success`（短名） | 同 C1 短名 | `--zb-stone-*` `--zb-text` `--zb-success` |
| 中性色板 | iOS 灰 #000/#F2F2F7 + rgba 磨砂 | — | 冷灰 #0a0a0a/#fff | 冷灰（同 C1 值） | Stone 暖灰阶（#FAFAF9…#1C1917） |
| 默认主题 | Dark/Light 并列、未钉死默认 | — | **默认 Dark**（:root 深底，light 靠 [data-theme=light]） | **默认 Light**（:root 浅底，dark 靠 [data-theme=dark]） | 默认浅（仅定义变量） |
| 状态色数量 | 6 彩 + dot 6 态（success/active/warning/risk/offline/processing 带 pulse） | blue/green/orange/red/purple/teal | **4 态** success/warning/danger/info | 4 态 | **6 语义** success/info/attention/risk/danger/unknown（fg/bg/border 三件套） |
| 状态色值 | green #30D158/#34C759、red #FF453A/#FF3B30 | — | green **#22c55e**、danger **#ef4444**、warning #f59e0b、info #60a5fa（Tailwind 风） | green **#16a34a**、danger **#dc2626**、warning #d97706、info #2563eb | 同 C2（#16a34a/#dc2626…） |
| 圆角 | sm8 / md12 / lg16 / xl20 | — | sm10 / md14 / lg20 | 同 C1 | sm4 / md6 / lg8 / xl12（偏小、高密度） |
| 间距 | xs4/sm8/md12/lg16/xl20/2xl32/3xl48（语义名） | — | space-1..6 = 4/8/12/16/20/24（数字名，缺 32/48） | 同 C1 | sp-1..8 = 4/8/12/16/24/32/40/48 |
| 动效时长 | （MOTION 母文档）fast100/normal180/slow280/slower420 | duration-fast100… | fast**140**/normal**220**/slow**360** | 同 C1 | dur-micro120/state220/page320 |
| 状态圆点 | `.zb-dot` **10px**、6 态含 processing pulse | 状态优先用圆点 | `.zb-status-dot` **8px**、4 态 | 同 C1 | 未定义组件类 |
| Frosted | `.zb-frosted` blur20 saturate180 | — | 无 | 无 | 不主张 |
| 字号阶梯 | h1 22/h2 17/h3 15/body15/caption13/label11/metric24/button15 | — | **未含字号变量** | 未含 | fs-12..30（另一套档位） |
| 是否被页面引用 | 规范层 | 规范层 | **未被任何 index.html `<link>` 引用（悬空）** | base.html 未引用（悬空） | base.html 未引用（悬空） |

结论：
1. **同名 `--zb-success` 在不同仓是不同色值**（#22c55e / #16a34a），同名 `--zb-radius-sm` 是不同值（10 / 8 / 4），同名时长 fast 是 100/140/120——跨库视觉不可能一致。
2. **默认主题策略相反**：SICI/DDC 落深色，Z-Brand 落浅色。
3. **三仓 scoped 文件目前全部悬空**：SICI `<head>` 只 link `css/style.css`；DDC 样式内联；Z-Brand base.html 只链 4 个老 CSS。新增 token 层「零视觉影响」是对的安全做法，但意味着**尚未真正接入，正适合在此刻统一后再接入**。
4. 母文档自身命名也未完全统一（DESIGN-TOKENS 用 `--zb-accent-blue`，ICON/MOTION 用 `--zb-blue`）。
5. Z-Brand 单仓内部即有 D / C2 两套新 token，再加 25 个老 CSS，是收敛复杂度最高的仓库。

---

## 4. 其他一致性 / 工程问题清单（只登记）

| # | 位置 | 事实 | 影响 | 处置建议 |
|---|---|---|---|---|
| I1 | SICI/DDC/ZB 根 | `ZBIP_DESIGN_TOKENS.css` 均未被页面引用 | token 层悬空 | 统一 SSOT 后再按仓接入，先组件后页面 |
| I2 | ZB `static/css/zbip-tokens.css` | 注释自称「唯一视觉真相层 SSOT」，但与根 `ZBIP_DESIGN_TOKENS.css`、母文档三处取值不同 | 一个仓内出现两个「SSOT」 | 只保留一个 SSOT 来源，其余改为消费层 |
| I3 | SICI `js/` | research-learning.js、three-repository-verifier.js 未被 index.html 引入 | 死代码/能力未接线 | 核实是否计划内；不删，先标注 |
| I4 | SICI 设置页 | 仓库名占位 `--Zachary` | 事实错误 | 改为 SICI-Core（低风险文案） |
| I5 | SICI/DDC/ZB 图标 | Unicode 字符 / 内联 SVG 混用，无统一 icon 组件 | 不符合 Icon System | 按母 ICON-SYSTEM 出 SVG 图标集后逐替 |
| I6 | ZB | package 5.6.2 vs 页面 v5.8.9 | 版本事实不一致 | 由 ZB Owner 核对，不在 UI 收敛中顺手改 |
| I7 | ZB | 双前端（templates + static SPA） | 同一产品两套 UI 入口，收敛路径不同 | Ownership Map 明确两者关系，分别适配 |
| I8 | ZB `static/css` | 25 CSS 多代叠加 + .bak 入库 | 层叠冲突、体积大 | 只增不减：新页面只用统一 token，老文件逐页迁移回归后标 deprecated，不删 |
| I9 | 状态语义 | 母规范要 Success/Active/Warning/Risk/Offline/Processing；实现只有 4 态 | 状态表达不全 | 统一状态枚举与 dot 类名 |
| I10 | DCC | 样式内联于 index.html，无独立 tokens 文件 | 与母规范「DCC 需提取独立 tokens.css」一致缺口 | 提取为独立文件再接入统一 token |

---

## 5. 冲突 STOP —— 需 ChatGPT / Human 拍板的设计决策（AI 给推荐，不擅自定）

- **D1 中性色板路线**：iOS 系统灰（母 DESIGN-TOKENS / DDC 现状）vs 冷灰（SICI/scoped）vs Stone 暖灰（ZB zbip-tokens）。推荐：以母 DESIGN-TOKENS 的 iOS 中性灰为跨库 SSOT（与 DDC 现状、Apple 取向一致），ZB Stone 作为产品级局部变量消费，不并列成第二套全局 token。
- **D2 默认主题**：SICI/DDC 落 Dark、ZB 落 Light。推荐：**不强制全平台同一默认**，但统一「同一套 token 同时定义 dark/light、默认值由产品在自己根节点声明」；生产驾驶舱 CTH-POMS（长时间盯盘、信息密度高）建议默认 Light，SICI/DDC（开发工具）可默认 Dark——这属于「信息架构/产品职责差异」，token 本身必须双主题齐备。需 Human 确认。
- **D3 圆角/密度**：母 8/12/16/20 vs scoped 10/14/20 vs ZB Stone 4/6/8/12。推荐：采用母档 8/12/16/20 为 SSOT；CTH 高密度诉求通过间距/信息密度而非另一套圆角表达。
- **D4 状态色与语义集合**：统一为母档 6 彩 + dot 6 态（success/active/warning/risk/offline/processing），色值用 iOS 系统色（Dark/Light 两值），废弃 #22c55e/#16a34a 等各自取值；`risk` 与 `danger` 是否合并需明确（母档 red 同时承担 Error/Risk/Fail，ZB Stone 又拆 risk/danger 两档）。推荐：保留 6 态 dot，语义层级在文档里给一张 risk=danger 映射表。
- **D5 Token 命名 SSOT**：统一一套命名（推荐母 DESIGN-TOKENS 的长语义名 `--zb-text-primary/--zb-accent-*`，可读性最好），母 ICON/MOTION 中的 `--zb-blue` 等改为引用统一名；scoped 短名文件在接入时改写为 SSOT 名。
- **D6 scoped 作用域**：现文件用 `:root` 定义全局变量却命名 scoped。推荐：变量（:root）属全局 token、只放一份；`.zb-surface/.zb-interactive/.zb-dot` 等 class 才是可叠加的 scoped 组件层，二者在文档里分层说明，避免「scoped」误解为可各写一份全局变量。

> 以上 6 项一旦拍板，应先回写母 DESIGN-TOKENS / ICON / MOTION（AI-D Owner），再让各仓消费，避免边改页面边改标准。

---

## 6. Phase 2 复用：母文档已覆盖项 + 把其「NOT_VERIFIED」转为已核实

`design-system/` 五份 Map 已覆盖六层架构、Owner 矩阵、数据流、Token/Icon/Motion 规范，**R-0005 不再另起 Map**。母文档自列的待确认项，据本轮真实读取更新如下：

| 母文档原 NOT_VERIFIED | 本轮真实读取结论 |
|---|---|
| SICI 双主题/设计系统现状未读 index 确认 | 已读：单 PWA、6 view、自带浅/深双主题 token + bottom sheet + safe-area；图标为 Unicode；2 个 JS 悬空（见 2.3 / I3 / I5） |
| Z-Brand 完整能力清单目录被截断 | 已列根目录与 static/css、templates；确认双前端 + 25 CSS + 生产红线在位（见 2.2） |
| DCC 需提取独立 tokens.css | 确认：样式内联在 53KB index.html，确需外提（I10） |
| SICI Icon 待确认 | 已确认：Unicode 字符，未用线性 SVG（I5） |
| AI-D src/tools 未读 | 本研究使用并实跑 src/contracts（research_record / safe_collection），离线测试在 |
| Failure Learning Record  Planned | 仍为规划，本轮不实现 |

---

## 7. 分仓收敛建议（每仓只做自己部分；严格顺序）

统一顺序（遵循用户指令，禁止跳阶段）：
**先 Token（Color/Typography/Icon/Spacing/Radius/Border/Motion/Light-Dark）→ 再 Navigation/Layout/Components/States → 最后具体页面**。每个产品只换「信息架构/密度/布局」，不换 token。

1. **AI-D（先动，标准方）**：据 D1–D6 拍板结果回写 3 份母 token 文档，产出**一份**跨库 `ZBIP_DESIGN_TOKENS`（CSS 变量 + JSON 双形态）与 SVG 图标集（母 ICON 第 8 节待办）；仍是研究/标准产物，不进生产 Runtime。
2. **DCC**：把内联样式外提为独立 tokens.css → 接入统一 token（保留其 Dark 默认与磨砂，属产品差异）→ 组件 → 页面；全程 `npm run test:all` 回归。
3. **SICI**：以其成熟交互为母版参考，但 token 换成统一 SSOT；补接或标注 2 个悬空 JS、修 `--Zachary` 占位、Unicode 图标逐步换线性 SVG；PWA 手动 + 浏览器验证。
4. **Z-Brand（最谨慎）**：新页面/补丁只允许引用统一 token；templates 与 static SPA 两条线分别适配；**25 个老 CSS 只增不减、逐页迁移回归后标 deprecated，不删**；`SUBJECT_WORDS/subject_hit/_subject_sql_and_values/aggregate_events/build_daily_report` 等生产红线与主体过滤逻辑一行不动，任何改动先说明影响并走 DDC gate + 人工批准。
5. **CTH-POMS / ZBMP 同仓差异**：CTH 走「高密度、风险优先、状态清晰的驾驶舱」，ZBMP 走「工作台化、探索/关系/分析」；共用 token，不共用页面布局。

---

## 8. Evidence（本轮真实读取，可追溯）

- 母规范：Hub `ZBIP_UNIFIED_README.md`（blob `914df45`）；`design-system/` DESIGN-TOKENS（`3c5c82d`）、ARCHITECTURE-MAP（`f8ce6bd`）、FEATURE-OWNERSHIP（`01e9305`）、ICON-SYSTEM（`3490677`）、MOTION-TOKENS（`cb28849`）。
- 三仓 scoped token：SICI/DDC blob `2210afc`（逐字节相同，默认 Dark）；Z-Brand blob `137a6f0`（默认 Light）。
- Z-Brand：`templates/base.html`（`e6682a0`）、`static/css/zbip-tokens.css`（`793d033`）、`static/css` 25 文件清单、package.json（`15ff3e18`，taikoo-monitor 5.6.2）；commits `ebb9a0a` / `06fd0c8`(stats)。
- SICI：`index.html`（`ede4d2c`）、`css/style.css`（`0e273e1`）、`js/` 8 文件清单；commit `cb13e57`。
- DDC：`index.html`（`29f969b`，本地 `_audit/ddc_index.html` 53,350B）、package.json（`e80e5cd`，v0.5.0）、js/server 目录；commit `cd1b2ec`。
- 提交统计：Hub `1fb645f`(+239 ICON) / `1069c80`(+320 MOTION) 均为单文件新增。

## 9. NOT VERIFIED（如实保留）

- Z-Brand `style.css`(80KB) 等 4 个被 base.html 实际加载的老 CSS 的完整层叠/覆盖关系与是否含 Dark，未逐行审。
- ZBMP 在 Z-Brand 仓内的确切前端入口与页面集合（static SPA / zb-preview / topic_campaign 的归属）。
- DDC index.html 的全部 body 交互细节（已下载本地，仅提取了 section 骨架与 head token）。
- SICI/DDC/ZB 三份 `ZBIP_UNIFIED_README.md` 与 Hub 源头是否逐字一致（仅确认都存在）。
- 四库真实启动 / 浏览器 E2E / 视觉回归：本地 git https 被重置、无法起服务，本轮未做，绝不以「预计通过」替代。
- D1–D6 六项设计决策在 ChatGPT/Human 拍板前不落地为代码。

## 10. Lifecycle & NEXT

- 状态：research（豆包自审见 records；不自动晋级）。本研究是「只读审计 + 收敛建议」，不改三产品、不复制核心代码、不把 AI 判断当 Evidence。
- NEXT FOR CHATGPT：独立复核本审计，重点裁决 D1–D6（尤其默认主题是否允许产品差异、状态语义 risk/danger 是否合并、token 命名 SSOT 选哪套）；并确认「母文档先行回写、各仓再消费」的顺序。
- NEXT（裁决后，R-2026-0006 候选）：AI-D 产出统一 SSOT token 文件 + SVG 图标集草案（研究产物）→ 再按 DCC→SICI→Z-Brand 顺序分仓小步接入，每仓独立 commit / 测试 / Evidence。
- 并行主线：R-2026-0004 的 AccountPlan / CookieHealth / TopicIndex / Sentiment 离线纯逻辑实现仍在排队，养号期不联网、不批量；本 R-0005 按用户指示优先。
