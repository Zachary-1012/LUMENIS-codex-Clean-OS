# LUMENIS Intelligence OS · 序境双核架构 v1.0

> **SUPERSEDED / HISTORICAL ONLY（2026-10-13 标注）**：ZBC+OSAI 双核、Linux 端与通用 OS/电脑控制已移出产品范围；仓库为单一 LUMENIS-codex-Clean-OS。 当前执行规则以 `AGENTS.md`、`LUMENIS-CODEX-TAKEOVER-CURRENT.md` 与 `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md` 为准；本文件的“最高/权威/CANONICAL”表述不再有效。

> **文档地位**：序境项目最终融合架构权威基线。取代此前"双库揉合""双子库""ZBC+OSAI"等过程叫法。
> **基准**：以线上两个 main 分支真实源码事实为准，不以旧版本/旧聊天/旧文档覆盖当前源码。
> **生效**：2026-09-05 · 状态：CANONICAL
> **铁律**：两仓不合并；ZBC 生产核心不删除；subject_hit() 不可绕过；AI 不是业务事实最终裁判；所有改变必须可追溯到 Evidence。

---

## 一、最终总命名

品牌母体：**序境**（中文正式品牌名，保留）

英文品牌统一为 **LUMENIS**（非直译，品牌语义：让复杂信息显现结构，让事实形成判断，让判断进入行动）。

不再使用 Xujing / Xujing Intelligence 作为正式英文名。

| 层级 | 中文正式名称 | 英文正式名称 |
|---|---|---|
| 母品牌 | 序境 | LUMENIS |
| 整体平台 | 序境智能平台 | LUMENIS Intelligence Platform |
| 生产系统 | 序境生产中枢 | LUMENIS Production Core |
| 智能系统 | 序境智能中枢 | LUMENIS Intelligence Core |
| Skill 系统 | 序境能力中心 | LUMENIS Skill Hub |
| 研发系统 | 序境研发中枢 | LUMENIS Engineering |
| 数据系统 | 序境事实中心 | LUMENIS Fact Center |
| 证据系统 | 序境证据中心 | LUMENIS Evidence Center |
| 研究系统 | 序境研究中心 | LUMENIS Research |

韩文品牌 서경 保留为国际化语言包。正式产品 UI 内部语言规则：中文为产品主语言；英文为系统/API/代码正式语言；韩文作为国际化语言包。

---

## 二、两个仓库最终命名

**不合并成一个 Git Repository。定死。**

### ZBC — Production Core

- 原仓：Z-Brand-Core（GitHub 名保留，避免无意义 Rename）
- 产品层名称：Production Core
- 职责：

```
Production Core
├── Business Truth
├── Data Truth
├── Subject Truth
├── Collector
├── Event
├── Risk
├── Analysis
├── Report
└── Runtime
```

### OSAI — Intelligence Core

- 原仓：Zachary-OS-AI（GitHub 名保留）
- 产品层名称：Intelligence Core
- 职责：

```
Intelligence Core
├── Agent
├── Orchestrator
├── Research
├── Evidence
├── Evaluation
├── Learning
├── Skill
└── Engineering Loop
```

---

## 三、最终总架构

正式名称：**序境双核架构** / LUMENIS Dual-Core Architecture

```
                          序境
                           │
                  LUMENIS Intelligence
                           │
              ┌────────────┴────────────┐
              │                         │
       Production Core           Intelligence Core
             ZBC                       OSAI
              │                         │
       生产事实与执行              智能与研发决策
              │                         │
              └────────────┬────────────┘
                           │
                    Shared Contracts
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
       Skills           Evidence         Evaluation
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                      AI Gateway
                           │
              ┌────────────┼────────────┐
              │            │            │
           Local        Cloud       External
          Models       Models       Models
```

两个 Core 永远不直接物理合并。融合的是：Contract + Skill + Evidence + Evaluation + Lifecycle + AI Gateway + Trace。

---

## 四、五层正式架构

整个系统统一采用 5-Layer Architecture：

### L0 — Experience Layer（序境体验层）
用户看到的一切：Web / Desktop / Mobile / API / Command / Dashboard

### L1 — Intelligence Layer（序境智能层）
AI Gateway / Model Router / Agent / Skill Router / Reasoning / Planning / Research / Evaluation / Learning

### L2 — Capability Layer（序境能力层）
Skills 统一存放：Source Scanner / SHA Verifier / Git Auditor / Database Auditor / API Auditor / Runtime Health / Research / Evidence / Report / KOS / KOL / KOC ...

### L3 — Domain Layer（序境领域层）
业务层：Production / Brand / Public Opinion / Content / Event / Risk / KOS/KOL/KOC / Campaign / Case / Report。ZBC 的业务真相在这一层。

### L4 — Foundation Layer（序境基础层）
Data / Database / Storage / Runtime / Auth / Config / Logging / Queue / Cache / Network / Observability

---

## 五、Skill 不再属于某个业务

Skill 是横向能力，不是 ZBC Skill / OSAI Skill 的割裂方式。

```
LUMENIS Skill Hub
    │
    ├── Source Skills
    ├── Data Skills
    ├── AI Skills
    ├── Research Skills
    ├── Engineering Skills
    ├── Governance Skills
    ├── Business Skills
    └── Operations Skills
```

Skill 通过 Contract 调用 ZBC / OSAI。

---

## 六、72 Skills 正式层级

### S01–S12｜Source & Engineering
S01 Source Fact Scanner / S02 SHA Verifier / S03 Git State Auditor / S04 File Inventory / S05 Module Mapper / S06 Function Mapper / S07 API Mapper / S08 Dependency Auditor / S09 Config Auditor / S10 DB Schema Auditor / S11 DB Integrity Checker / S12 Runtime Health

### S13–S22｜Data
S13 Data Profiler / S14 Data Quality / S15 Duplicate Detector / S16 Schema Diff / S17 Migration Checker / S18 Data Lineage / S19 Retention Auditor / S20 Backup Validator / S21 SQLite Health / S22 Data Reconciliation

### S23–S32｜AI
S23 Model Router / S24 Prompt Auditor / S25 Context Builder / S26 Agent Planner / S27 Agent Executor / S28 AI Evaluator / S29 AI Confidence / S30 AI Cost Manager / S31 AI Fallback / S32 AI Trace

### S33–S40｜Research
S33 Web Research / S34 Literature Research / S35 Technology Scout / S36 Competitor Research / S37 Evidence Extractor / S38 Evidence Validator / S39 Finding Generator / S40 Research-to-Product

### S41–S52｜Engineering
S41 Engineering Loop / S42 Code Planner / S43 Patch Generator / S44 Patch Validator / S45 Unit Test / S46 Regression Test / S47 Runtime Test / S48 Performance Test / S49 Security Test / S50 Visual QA / S51 Functional QA / S52 Release Validator

### S53–S60｜Governance
S53 Lifecycle Tracker / S54 Requirement Trace / S55 Change Impact / S56 Permission Gate / S57 Approval Gate / S58 Evidence Chain / S59 Risk Register / S60 Retirement Manager

### S61–S66｜Business
S61 Subject Intelligence / S62 Brand Intelligence / S63 Public Opinion / S64 Event Intelligence / S65 KOS/KOL/KOC Intelligence / S66 Campaign Intelligence

### S67–S72｜Operations
S67 System Monitor / S68 Collector Monitor / S69 Alert Manager / S70 Security Monitor / S71 Deployment Validator / S72 Disaster Recovery

---

## 七、AI Gateway 正式命名

**LUMENIS AI Gateway**。OSAI 不再直接绑死某个模型。

```
AI Gateway
├── Local Provider
│   └── Ollama / gpt-oss
├── Zhipu Provider
├── OpenAI-compatible Provider
└── Future Providers
```

模型选择：Task → Model Router → Cost / Latency / Capability / Availability → Model

智谱不删除，gpt-oss 也不替代智谱。这是 **Provider-Agnostic AI Architecture**。

---

## 八、Engineering Loop 正式变成系统级研发能力

```
Engineering Loop
├── INSPECT
├── PLAN
├── EXECUTE
├── VERIFY
├── REPAIR
├── VERIFY
├── EVIDENCE
├── EVALUATE
└── HUMAN APPROVAL
```

然后才：COMMIT → PUSH

**Commit / Push 不属于 Agent 自主 Loop。** 必须经过 Permission Gate。

当前线上 OSAI `tools.py` 已存在直接 `git_commit_push()`——这是本次融合必须首先处理的架构红线。

---

## 九、Repository Registry

把 OSAI 中 `D:\Taikoo-monitor-new` 这种硬编码彻底升级为 Repository Registry：

```
Repository Registry
├── Production Core
│   ├── repo
│   ├── branch
│   ├── SHA
│   ├── runtime
│   └── permissions
└── Intelligence Core
    ├── repo
    ├── branch
    ├── SHA
    ├── runtime
    └── permissions
```

Windows / macOS / Linux / Cloud Server 统一。线上 OSAI 当前 `config.py` 的 Windows 硬编码是必须解决的问题。

---

## 十、Evidence 正式命名

所有 AI / Skill / Agent / Research / Engineering 行为最终进入 **LUMENIS Evidence Chain**：

```
Task → Requirement → Skill → Agent → Action → File → Function
→ Data → Test → Result → Evidence → Decision → Commit → Lifecycle
```

最终形成 Decision Trace：为什么系统做了这个动作，可以一路查回来。

---

## 十一、生命周期正式统一

```
DISCOVER → REQUIREMENT → RESEARCH → EVIDENCE → DECISION
→ ARCHITECTURE → IMPLEMENT → TEST → VERIFY → RELEASE
→ OPERATE → MONITOR → LEARN → IMPROVE → RETIRE
```

这是整个序境最高级别的生命周期标准。

---

## 十二、前端正式架构

**LUMENIS Experience System**。不是传统后台管理系统。

核心原则：**一个工作台，而不是几十个菜单。**

---

## 十三、Web 一级 IA

左侧一级：

```
INTELLIGENCE
PRODUCTION
RESEARCH
```

下面：HOME

然后：

**Intelligence**：Overview / AI Workspace / Agents / Skills / Evidence / Evaluation / Learning

**Production**：Overview / Subjects / Brands / Content / Public Opinion / Events / Risk / KOS/KOL/KOC / Cases / Reports

**Research**：Research / Discoveries / Technology / Evidence / Findings / Decisions

**Operations**（系统级入口，不做业务一级）：System / Runtime / Tasks / Logs / Security / Settings

---

## 十四、首页正式命名

**Command Home**。不是 Dashboard。

它不是给人"看数据"的，而是告诉用户：现在发生什么、为什么发生、下一步做什么。

首页六区：
1. System State
2. Intelligence Pulse
3. Active Risks
4. Active Tasks
5. Recent Evidence
6. Recommended Actions

---

## 十五、AI Workspace

正式名称：**Intelligence Workspace**

结构：Input → Context → Retrieval → Reasoning → Analysis → Evidence → Decision → Action

右侧不再永久塞 Context Panel，只有需要的时候打开。

---

## 十六、Case Library

正式名称：**Case Intelligence**（不是简单的"案例库"）

内部：Cases / Brands / Accounts / Events / Content / Public Opinion / KOS / KOL / KOC / Relations / Tags / Classification

统一入口 ≠ 合并底层数据表。

---

## 十七、生产工作台

正式名称：**Production Workspace**

里面：Subject / Brand / Content / Public Opinion / Event / Risk / Campaign / Report

调用 ZBC 的真实生产能力。

---

## 十八、Research Workspace

正式名称：**Research Workspace**

核心链：Research → Finding → Evidence → Decision → Product Improvement

外部研究绝对不能：网上发现 → 复制 → 直接进入 Core。

必须：Research → Evidence → Finding → Internal Proposal → Human Review → Implementation

---

## 十九、Skill 页面

正式名称：**Skill Hub**

首页：All Skills / My Skills / Recommended / Running / Evaluations / Skill Factory

每个 Skill 页面统一：Skill Name / Purpose / Input / Output / Permissions / Dependencies / Version / Success Rate / Usage / Cost / Evidence / Lifecycle

---

## 二十、Agent 页面

正式名称：**Agent Center**（不是"机器人列表"）

每个 Agent：Agent → Mission → Skills → Permissions → Tasks → Execution → Evidence → Evaluation

---

## 二十一、视觉系统

正式纳入：**LUMENIS UI Standard**

核心：Apple-inspired + 序境原来的"微光银"视觉精神 + 专业情报工作台 + Liquid Glass restrained

英文品牌已更换，视觉标准不再出现 XUJING 作为产品名。

---

## 二十二、颜色体系

基础：Neutral Base / Micro Silver / White / Graphite / Deep Neutral

状态色：Success / Warning / Danger / Info（遵循 Apple-style semantic colors）

---

## 二十三、Glass 使用规则

只允许：Navigation / Floating Layer / Transient Context

禁止：Glass Card + Glass Card + Glass Background（不允许玻璃套玻璃）

---

## 二十四、组件系统

正式：**LUMENIS Component System**

基础：Button / Input / Select / Tabs / Badge / Status / Card / Table / List / Drawer / Modal / Toast / Timeline / Metric / Chart / Command / Search / Filter / Navigation

统一圆角：8 / 12 / 16 / 20 / 9999

---

## 二十五、图标

正式规定：24×24 / 1.5px / currentColor / Line Icon

禁止 emoji 作为正式 UI icon。

---

## 二十六、动效

统一时长：120ms / 180ms / 240ms / 320ms / 420ms

最重要一条：**Data-driven Motion**。没有真实数据变化，不动画。

禁止：假实时 / 假绿色 / 假增长 / 无限循环 / 视觉欺骗。

---

## 二十七、页面布局

统一：

```
┌────────────────────────────────────────────┐
│ Global Header                              │
├──────────┬─────────────────────────────────┤
│          │                                 │
│ Sidebar  │        Workspace                │
│          │                                 │
│          │                                 │
│          │                                 │
└──────────┴─────────────────────────────────┘
```

原则：不无限下滑。重要信息必须在一个完整 Workspace 内完成。

---

## 二十八、手机端

**LUMENIS Mobile**。不是重新做一个手机版产品。

架构：Mobile → API → Experience Gateway → Skill Router → OSAI → ZBC

手机主要做：查看 / 查询 / 分析 / 启动任务 / 审批 / 查看 Evidence / 查看风险。

不是直接拿手机操作 Git 仓库。

---

## 二十九、最终权限模型

统一 11 级动作：

```
READ → AUDIT → ANALYZE → RESEARCH → PLAN → PATCH_PREVIEW
→ TEST → VERIFY → HUMAN_APPROVAL → COMMIT → PUSH
```

- READ → VERIFY：Agent 可以自动化
- HUMAN_APPROVAL：必须人工
- COMMIT / PUSH：必须受 Permission Gate 控制

---

## 三十、最终系统命名树

```
序境 LUMENIS
│
└── LUMENIS Intelligence Platform
    │
    ├── Experience Layer
    │   ├── Web
    │   ├── Desktop
    │   └── Mobile
    │
    ├── Intelligence Layer
    │   ├── AI Gateway
    │   ├── Agent Center
    │   ├── Skill Router
    │   ├── Research
    │   ├── Evaluation
    │   └── Learning
    │
    ├── Capability Layer
    │   └── Skill Hub
    │
    ├── Domain Layer
    │   ├── Production
    │   ├── Brand
    │   ├── Content
    │   ├── Public Opinion
    │   ├── Event
    │   ├── Risk
    │   ├── KOS/KOL/KOC
    │   ├── Campaign
    │   └── Case Intelligence
    │
    └── Foundation Layer
        ├── Data
        ├── Evidence
        ├── Runtime
        ├── Security
        ├── Logging
        ├── Storage
        └── Repository Registry
```

---

## 三十一、两个 Core 放在哪里

```
LUMENIS
├── Production Core
│   └── Z-Brand-Core
└── Intelligence Core
    └── Zachary-OS-AI
```

仓库不合并。产品体验统一。能力统一。Contract 统一。Evidence 统一。Lifecycle 统一。Skill 统一。

---

## 三十二、融合第一阶段（P0）

**不是先改 UI，也不是先生成 72 Skill。**

### P0 — Dual-Core Convergence Foundation

一次完成：
1. Repository Registry
2. Permission Gate
3. Cross-platform Resolver
4. Task Contract
5. Trace Contract
6. Evidence Contract
7. Evaluation Contract
8. Lifecycle Contract
9. Skill Contract
10. AI Gateway Contract
11. Engineering Loop Adapter
12. Agent Permission Boundary

然后：
- P1 → Skill Hub → 12 Core Skills → Evaluation → 72 Skills
- P2 → Frontend → Command Home → Intelligence Workspace → Production Workspace → Research Workspace → Skill Hub → Agent Center

---

## 三十三、最终融合红线（10 条，写进系统 Contract）

1. 不合并两个 Git Repository
2. 不删除 ZBC 生产业务核心
3. `subject_hit()` / Subject Authority 不允许被 Skill 私自绕过
4. AI 永远不是业务事实最终裁判
5. Skill 不允许自己拥有无限权限
6. Agent 不允许绕过 Human Approval
7. 不允许无限 Engineering Loop
8. 不允许静默删除数据
9. 不允许文档代替源码事实
10. 所有改变必须能追溯到 Evidence

---

## 三十四、正式总称

以后内部不再叫：双子库 / 双库 / ZBC+OSAI / 四源 / 五层 Skill 系统（这些是研发过程叫法）。

**正式产品架构名称：序境 · 智能操作系统 / LUMENIS Intelligence OS**

它下面是：
- LUMENIS Experience
- LUMENIS Intelligence
- LUMENIS Skills
- LUMENIS Production Core
- LUMENIS Evidence
- LUMENIS Research
- LUMENIS Engineering

定位：不是一个舆情系统，不是一个 AI 聊天机器人，不是一个 Agent 工具箱，而是一套由事实、智能、能力、证据和工程闭环组成的智能操作系统。

ZBC 和 OSAI 不需要推倒重来，分别成为 Production Core + Intelligence Core。

---

*本文档为 LUMENIS Intelligence OS 双核架构的唯一权威基线。修改须经 Human Approval 并更新 Lifecycle。*
*基于线上两个 main 分支真实源码事实制定。旧版本/旧聊天/旧文档不得覆盖本文档。*
