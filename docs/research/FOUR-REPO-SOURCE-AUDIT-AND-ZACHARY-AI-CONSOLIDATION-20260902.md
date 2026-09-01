# 四库源码级拆解与 Zachary AI 整合蓝图

> TASK: ZBC-FOUR-REPO-AUDIT-001 ｜ 日期: 2026-09-02 ｜ 方法: 本地克隆/主树源码实测 + 远程 `ls-remote` 交叉核对，非文档转述
> 权威顺序: 当前源码 / 数据库 / 运行时实测 > 基线文档 > 开发记录 > 聊天结论
> 命名基线首次出现用全称: 品牌业务生产平台(Z-Brand Business Production Platform, ZBP)；广州太古汇舆情监测系统(CorTech Lab·Guangzhou Taikoo Hui Public Opinion Monitoring System, CTH-POMS)；Z-Brand 品牌监测平台(Z-Brand Monitoring Platform, ZBMP)；研发工程治理中枢(Development Command Console, DCC)；智能研究学习中枢(Intelligent Research & Learning Hub, SICI)；自主智能研发体(Autonomous Intelligence Development, AI-D)。

---

## 0. 结论先行（TL;DR）

1. 四个仓库本地已全部就位并实测：ZBC 主树 `D:\Taikoo-monitor-new`、SICI `D:\SICI-Core`、DCC `D:\Development-Command-Console`（本轮克隆）、AI-D `D:\AI-Development-Research-Hub`（本轮克隆）。
2. **生产只有一个：ZBC。** DCC / SICI / AI-D 都不是 CTH-POMS 运行时依赖——ZBC 生产可独立启动、独立出数，符合"产品独立化、可独立生存"基线。
3. 因此"除 ZBC 外三个整合进 zachary ai 仓库"**不会给生产引入强耦合**，工程上可行。推荐 **monorepo + workspace 分包**（治理 / 研究中枢 / 移动操作面），共享契约与设计令牌，三者仍各自可独立运行、独立发布。
4. ZBC 当前最大内部技术债不是功能，而是 **app.py 单体(258KB/195 路由)** 与 **前端 29 CSS + 25 JS 层叠污染**（用户反复反馈"越改越乱"的根因实证）。
5. 发现命名漂移：SICI / AI-D 部分文档把 DCC 写成 "DDC"，整合时统一为 **DCC**。

---

## 1. 四库事实卡（源码实测）

### 1.1 ZBC — Z-Brand-Core（生产真相）

| 项 | 实测值 |
|---|---|
| 本地路径 / 分支 | `D:\Taikoo-monitor-new` / main |
| 远程 | github.com/Zachary-1012/Z-Brand-Core（私有，匿名 API 不可见） |
| 定位 | 业务/生产真相；内含 CTH-POMS（主力生产/客户交付）+ ZBMP（内部母平台增强能力层） |
| 技术栈 | Flask + SQLite + Playwright(主，33 处在用) + 原生 JS/CSS 单页；Selenium 0 真实 import（DEPRECATED 候选） |
| 规模 | 699 个 .py（排除 venv/archive/staging）、约 13.69 万行；`app.py` 258KB、**195 个 @app.route**；tests 48 个 test_*.py、全量 155 用例当前全绿 |
| 生产库 | `data\monitor.db` 6.4MB、**53 张表**（notes/comments/note_comments/events/event_mentions/daily_reports/daily_digest/web_*/collection_counters/collector_quality_log/event_insights/v4_* 等）；`staging\monitor.staging.db` 为同构独立副本（隔离正确） |
| 前端 | 主界面 `static/index.html` 77KB 单页 + templates 5 个小壳；**CSS 29 个、JS 25 个** |
| 核心业务域 | 采集(xhs_cdp_collector 真人层/topic_campaign/collector_automation/web 源)、主体过滤(subject，红线)、风险(risk_engine，红线)、事件(event_graph)、报告(daily_report/export_report)、AI(ai_analyzer/intelligence，本地优先+云端脱敏)、知识库与案例(public_opinion_cases/pr_case_integration)、v4 认证、system_health |

**ZBC 技术债（实测，按影响排序）**
- T1 `app.py` 258KB/195 路由单体：改一处回归面大，是"互相覆盖"的结构性来源。建议按 blueprint 渐进抽取，**不重写**。
- T2 前端层叠污染：CSS 同时存在 style(79KB)/zb-gpt-theme(70KB)/zb-theme(43KB)/ui_modern(36KB)/components(31KB)/ui_dashboard(31KB)/design-v8/design-v9/appple-ui/minimal 系列等 29 份；JS 有 app(113KB)/frontend_enhancement(54KB)/zbmp-workbench(52KB)/zachary_robot+enhanced(重复) 等 25 份。需 UI 收敛到唯一 token + 唯一主题层（用户已要求 UI 方向，本轮先登记不施工）。
- T3 根目录冗余：`app_backup_v589.py`(251KB) 等备份文件，应归 backups/ 并标 LEGACY（不直接删）。
- T4 `topic_campaign.py`(60KB) 仍含固定时钟(9/11/13/15/17/19)调度，待收口进 Dynamic Scheduler（既往结论，未做）。
- T5 data\backups、data\cache 有 20+ 份历史快照（本地保留、不入库、不进运行时）。

### 1.2 DCC — Development Command Console（工程控制）

| 项 | 实测值 |
|---|---|
| 本地 / 远程 | `D:\Development-Command-Console`（本轮 depth1 克隆）/ main `b0de3c5` + 分支 security/runtime-preflight-hardening |
| 定位 | 审计、验证、变更契约、Evidence、Release Gate、工程学习基建；**无业务、无产品 UI、无生产数据** |
| tools（Python） | research_learning / learning_cycle / learning_promote / research_registry / capability_delta / platform_inspection（+各自测试） |
| tests | JS: bridge/change-plan/effective-rules/evidence-bundle/github-audit/learning-store/shadow-learning/snapshot/startup-preflight/supplement-protocol；Py: capability_delta/learning_cycle/promotion_gate/research_registry |
| CI | platform-five-inspections（每日 5 次只读巡检）、reusable-verify、test、pages |
| docs（24 份治理协议） | V0.4/V0.41 变更契约、V041-EVIDENCE-SCHEMA、THREE_REPOSITORY_SYSTEM_MATRIX、PRODUCTION-GATE-XHS-APP、PLATFORM-VERIFICATION-RUNTIME、PRE_CHANGE_THREE_REPO_CHECKLIST、RESEARCH-LEARNING-* 等 |
| 形态判断 | 纯"工程治理引擎 + CI + 协议库"，最适合作为 zachary ai 的 **governance 包** |

### 1.3 SICI — Intelligent Research & Learning Hub（移动操作面）

| 项 | 实测值 |
|---|---|
| 本地 / 远程 | `D:\SICI-Core` / main `8e724e1` / SICI-Core.git |
| 定位（PLATFORM_README 实测） | **mobile-first creation surface**：把复杂平台能力在手机上变成可用操作；明确"不是业务智能核心、不是工程控制面" |
| 形态 | 纯前端 **PWA**：index.html(18KB) + manifest.json + sw.js + 11 个 JS(app 31KB/effective-rules 12KB/tester 11KB/preflight 10KB/runner/deploy/github/capability-registry/research-learning/storage/three-verifier) + ZBIP_DESIGN_TOKENS |
| Python | shadow_run（pyresilience/yyds_logger 韧性实验 + 两份报告）、upgrade_modules（base_adapter_enhanced/dual_pool/unified_logger，**供反哺到生产的候选模块**，附接入指南） |
| 边界 | 无自有业务库/无服务端运行时；浏览器 E2E 为**模拟**（文档明确真实 E2E 需受控后端执行器） |
| 形态判断 | 面向用户的移动 Web App，适合作为 zachary ai monorepo 的 **apps/mobile-surface** |

### 1.4 AI-D — Autonomous Intelligence Development（共享研发/学习中枢）

| 项 | 实测值 |
|---|---|
| 本地 / 远程 | `D:\AI-Development-Research-Hub` / `930c646` / AI-Development-Research-Hub.git（公开） |
| 定位（README 实测） | 三产品**共享**的 Research / Experiment / Shadow Learning / Case Library / Benchmark / Evidence Index / Capability Registry；**非生产 Runtime，产品不依赖它运行**；"不是第四个产品" |
| src | contracts(research_record/safe_collection)、adapters(ddc_research_adapter，**复用而非复制 DCC schema**)、shared(capability_registry/shadow_lifecycle) |
| tools | research_id / runtime_preflight / secret_scan；tests 6 个 |
| research | R-2026-0002…0008 + content-intelligence 案例 |
| architecture（12 份 ADR） | ZACHARY-AI-GROWTH-MODEL、MEMORY-LIFECYCLE、DOMAIN-ADAPTER-CONTRACT、LEARNING-PROMOTION-ENGINE、INTERNAL-MATURATION-AND-DOMAIN-ISOLATION、CAPABILITY-BENCHMARK 等——**这是"Zachary 最终独立成一个 AI"的成长模型主阵地** |
| CI | research-validation |
| 形态判断 | 研究/学习/能力成熟度引擎，适合作为 zachary ai 的 **packages/research-hub**（核心） |

---

## 2. 唯一能力归属（Owner 唯一性，消除重复实现）

| 能力 | 唯一 Owner | 其他仓角色 | 重复/冲突实测 |
|---|---|---|---|
| 业务/生产数据与口径（主体/风险/事件/报告） | **ZBC** | 只读引用 | SICI/AI-D 不得内置业务判断（基线一致） |
| 变更契约 / Release Gate / Evidence Schema / CI 巡检 | **DCC** | AI-D 用 adapter 复用、SICI 只发起不裁决 | AI-D 已正确复用（ddc_research_adapter），无重复 |
| Research/Shadow/案例库/能力晋级/AI 成长模型 | **AI-D** | DCC 提供 learning_* 基建，AI-D 扩展 | learning_cycle/promote 在 DCC，研究记录在 AI-D，边界清晰 |
| 移动交互/真机工作流反馈 | **SICI** | 反馈经 DCC 转任务、ZBC 定业务有效性 | 无重复 |
| 设计令牌 Design Tokens | **共享层**（ZACHARY/ZBIP tokens） | 各产品消费 | SICI 有 ZBIP_DESIGN_TOKENS，ZBC 前端 token 分散（T2） |
| 真人采集/适配器 | **ZBC** | AI-D 只做安全采集研究(R-2026-0003/safe_collection 契约) | 无生产重复 |

---

## 3. Zachary AI 整合蓝图（DCC + SICI + AI-D → 一个仓库）

### 3.1 为什么这样合不违反"产品独立化"
- 产品独立化要求的是**运行时不强耦合**：CTH-POMS 离开其他三个仍能跑——实测成立（ZBC 自带 Flask/DB/采集/报告）。
- DCC/SICI/AI-D 三者本就是研发/治理/学习/操作侧，合并的是**代码托管与协作边界**，不是把它们焊进生产链路。
- 合并后仍通过 workspace 边界保证每个包可独立测试、独立发布、未来可再拆出。

### 3.2 推荐目标结构（monorepo + workspaces）
```text
zachary-ai/                       # 新整合仓库（研发/治理/学习/移动面，非生产）
├── packages/
│   ├── governance/               # ← DCC 全量（tools/tests/workflows/docs 协议）
│   ├── research-hub/             # ← AI-D 全量（src/research/architecture/ADR/cases/benchmarks）
│   └── contracts/                # 抽取共享：Task/Risk/Permission/Evidence/Research/SafeCollection
├── apps/
│   └── mobile-surface/           # ← SICI 全量（PWA: index/js/css/manifest/sw）
├── design/
│   └── design-tokens/            # 唯一 ZBIP/Zachary 设计令牌源（SICI 现有 token 迁入为基线）
├── docs/                         # 跨包基线、命名基线、整合说明、迁移记录
├── .github/workflows/            # 合并 CI：governance 巡检 + research 验证 + mobile 构建，分路径触发
└── README.md
```
- 每个 package/app 保留自己原有的 README、tests、提交历史（用 `git filter-repo` 或 subtree 合并保留 history，不丢提交）。
- ZBC **不进入**该仓库，继续独立生产仓库，只通过 `packages/contracts` 的稳定契约与 Evidence 弱协作。

### 3.3 整合步骤（建议，不在本轮擅自动手）
1. 建 `zachary-ai` 空仓 + 上述骨架 + 根 README/CODEOWNERS（governance/research/mobile 三块 owner）。
2. 用 subtree/filter-repo 分别把 DCC、AI-D、SICI 导入对应目录，**保留各自 git 历史与 commit SHA 映射表**。
3. 统一命名：全文 "DDC"→"DCC"；首次出现统一"中文全称+英文全称+简称"。
4. 抽共享契约到 packages/contracts，把 AI-D 的 ddc_research_adapter 改为引用同仓 contracts（跨包 import 走 workspace，不复制代码）。
5. CI 合并为按路径触发的三套 workflow，互不阻塞；保留 DCC 每日 5 次只读巡检。
6. 整合后分别跑：DCC 工具测试、AI-D 6 测试、SICI 3 JS 测试 + PWA 构建，全部绿才打整合 tag。
7. 旧三仓设为归档只读、README 指向新仓（保留可回退窗口，不立即删）。

### 3.4 不建议的做法
- 不建议把 ZBC 也并进去（会让生产背上研发/学习面，违反独立化与最小爆炸半径）。
- 不建议合并成"一个大程序"——必须保留包边界与各自可运行。
- 不建议在整合同时重写任何模块（整合=搬家+统一契约，不做功能重构）。

---

## 4. 与本轮在途工作的衔接

| 在途项 | 与四库整合的关系 / 下一步 |
|---|---|
| 浅色莫兰迪启动系统 zbp-hub（本轮已完成标杆，commit 816a025） | 属 ZBC 生产前端；design-tokens 稳定后反向同步到 zachary-ai/design 作为共享源 |
| 真人采集拟人化（本轮 human-2.1：秒退/浅读/正常/深读 + 赞藏评享计数） | 属 ZBC 生产；AI-D R-2026-0003/safe_collection 作为研究侧记录，不反向耦合 |
| 本地 AI（Ollama qwen2.5:7b，下载 95%）+ 云端脱敏 | ZBC 本地优先；AI 成长模型/记忆生命周期主阵地在 AI-D（research-hub） |
| ZBC 前端 29CSS/25JS 收敛（T2） | 等 UI 蓝图拍板后在 ZBC 内独立施工，不与仓库整合同批做，避免双变量 |
| DCC 每日巡检 / Release Gate | 整合后继续作为 zachary-ai/packages/governance 的 CI 职责 |

---

## 5. 待用户拍板项（不自行决定）

1. **整合仓库名**：建议 `zachary-ai`（或你指定的正式英文名，AI-D 正式英文名此前也标注为暂定）。
2. **整合时机**：是否在 CTH-POMS 生产上线窗口后再执行（推荐），还是现在就建仓搬目录。
3. **历史保留方式**：subtree 保留三仓完整历史（推荐，仓库略大）还是只导当前快照（更小但丢历史）。
4. **SICI 移动面归属**：作为 zachary-ai 内 `apps/mobile-surface`（推荐），还是保持独立仓只做契约共享。
5. DCC 远程为私有、ZBC 为私有，整合仓私有/公开需你定（建议私有）。

---

## 6. 本轮 Evidence

- 四库本地路径与 HEAD：ZBC main(工作树)、SICI `8e724e1`、DCC `b0de3c5`、AI-D `930c646`。
- ZBC 量化：699 py / 13.69 万行 / app.py 195 路由 / 48 测试文件 / data\monitor.db 53 表 / 29 CSS / 25 JS（脚本 `staging\zbc_inventory.py`，可复跑）。
- 远程核对：`git ls-remote` 确认 DCC=Development-Command-Console（DCC-Core 不存在）；GitHub API（走代理）确认 AI-Development-Research-Hub 公开存在。
- 本文件只做盘点与蓝图，**未修改任何生产代码、未移动任何仓库、未写生产库**。
