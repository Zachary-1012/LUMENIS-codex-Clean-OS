# 双子星审计与 README 融合调整 — 任务清单（tasks.md）

> 对应 Spec: `dual-repo-audit-20260902/spec.md`
> 语言: 中文
> 映射原则: 每个 Task 都映射到 1 个或多个父 AC；每个 TR（Task-level Test Requirement）继承父 AC 的 rule/rubric 类型，不能降级。

---

## 全局依赖图

```
Task 1 (ZBC README 母体) ─┐
                          ├─► Task 5 (联合修复 + 交叉链接 + 术语一致) ─► Task 6 (独立 Review)
Task 2 (ZBC 清单 + 矩阵) ─┤                                              │
                          │                                              │
Task 3 (ZOSAI README 母体)┼──────────────────────────────────────────────┘
                          │
Task 4 (ZOSAI 清单/矩阵/归档+gitignore)─┘
```

并行关系：Task 1 与 Task 2 可串/并行；Task 3 与 Task 4 可串/并行。A、B 两侧（Task1+2 vs Task3+4）完全可并行。Task 5 依赖 1-4 都完成或至少草稿可用。Task 6 依赖 5 完成。

---

## Task 1：Z-Brand-Core README 顶层 12 节母体重写

- **Status**: pending
- **Priority**: high
- **Owner & Scope**: 修改 `D:\Taikoo-monitor-new\README.md`，不碰 Python 源码/模板/静态/子模块/数据库。
- **父 AC**: AC-R001、AC-R003、AC-R005、AC-R011、AC-S001、AC-S003
- **前置**: 无（Task 0 已经完成 Spec 审批通过后即开始）

### 实现内容

将现有 v5.9.7 README 的 22 节内容（真实存在）重排并扩展为 **12 节统一母体**，保留原有所有生产信息、版本、测试快照，**不得删除任何既有业务要点**（只能重排、加节、合并同义、补缺失节、加交叉引用）。

12 节统一母体（顺序固定）：
1. 一句话定位 × 产品标记（📊）+ 当前最新版本号（v5.9.7）
2. 双子产品关系与边界（含 B 仓交叉引用 URL+元信息，含 FR-001 硬文本）
3. 本仓子产品（CTH-POMS / ZBMP）说明 + 双模式表格对比
4. 子产品/子组件 × Owner × 是否允许跨库复制 表格
5. 架构主图 + 四层业务模型数据流 + AI 增强路径（复用当前第 2 节与 AI 节的图）
6. 当前真实版本进度（保留当前第 4 节 v5.9.7 要点 + 端到端 42 项结果）
7. AI 原则（Ollama-first / 可退出 / Shadow Mode / AI 不能独自决定 6 项 + 审计链）
8. 数据模型（WHO/WHAT/WHAT HAPPENED/SO WHAT 四层 + 传播主体 6 维 + 三类事件 + 事件关系 4 种 + 时间口径两字段 8 枚举一致校验）
9. 允许 / 禁止 / 受控 四层矩阵（本次只加节标题和层结构占位，**具体矩阵行填入由 Task 2 负责**，避免 Task 1 与 Task 2 写同一文件冲突）
10. P0 / P1 / P2 当前任务（保留当前第 17 节的 4 类 P0/P1/P1P2/P2）
11. 关键文档索引（保留当前第 21 节并新增 3 条跨仓链接：ZOSAI README 产品关系段 / ZOSAI DCC README 13 ZBC 职责 / ZOSAI AI-DRH Capability Registry）
12. 协作与变更门禁（保留当前第 20 节一句话工程原则 + AGENTS.md 链接 + 当前第 19 节权威性冲突处理链）

### Task-local 测试要求（TRs）

| TR | 类型 | 通过条件 | 证据 |
|---|---|---|---|
| T1-TR01 | rule | README 一级标题 12 个，文字顺序严格等于上方 1-12（可加编号或不加，文字内容必须一一对应） | `grep "^# " README.md` 与父清单对照 diff |
| T1-TR02 | rule | 第 2 节存在 FR-001 硬文本：`CTH-POMS / ZBMP 生产运行绝对不依赖 Zachary-OS-AI 任何组件。` | grep 精确匹配 |
| T1-TR03 | rule | 第 2 节包含跨仓 URL 链接到 ZOSAI 仓库 README 对应段落，且附带 (repo=Zachary-1012/Zachary-OS-AI, branch=main, section=双子产品关系) 三元元信息（放在链接下方一行小字或括号里） | 手动打开链接确认跳转 |
| T1-TR04 | rule | 当前 README 所有既有业务要点（22 节中除重排外的所有数字、版本、测试数量、主体红线）在新 12 节母体中**仍然存在**（不得丢失 v5.9.7、42 项、Auth Recovery 闭环、6 态、主体分离等核心声明） | 人工要点清单 30 条逐条核对 |
| T1-TR05 | rule | `git diff --stat README.md` 只显示 README.md，不出现 .py / .html / .js / .db | `git diff --stat` 输出 |
| T1-TR06 | rubric | 长段结构化率：4+ 行无结构长段 0 段=2 分；1-2 段=1；≥3 段=0 | README 段落行数自动统计 |
| T1-TR07 | rubric | 交叉引用完整性（本 Task 只负责 A 侧，第 2/11 节至少 2 处跨仓链接存在且元信息齐 + Owner 声明无冲突 → 2 分；缺 1 处=1；2 处都缺=0） | 人工核对清单 |

### 完成证据字段
- 修改文件：`README.md`（单文件）
- 父 AC：AC-R001, AC-R003, AC-R005, AC-R011, AC-S001, AC-S003

---

## Task 2：Z-Brand-Core 资产清单 × 允许禁止矩阵 × 架构错误修复（README 后半）

- **Status**: pending
- **Priority**: high
- **Owner & Scope**: 继续修改 `D:\Taikoo-monitor-new\README.md`（第 9 节填内容 + 第 9.5 节资产清单 + 修复 E-001/E-002/E-003/E-004/E-009）
- **父 AC**: AC-R006, AC-R008, AC-R009(E-001~004, E-009), AC-R013, AC-R014, AC-S002, AC-S004
- **前置**: 建议在 Task 1 完成后开始（第 9 节和文档索引已占位）；亦可 Task 1 先把内容给 Task 2，串行。

### 实现内容

**A. README 第 9 节：允许 / 禁止 / 受控 四层矩阵填实**

- 9.1 产品层矩阵：填入 spec.md FR-003 产品层 A 侧对应内容（8 行 × 3 列）。每行加依据标签 `[AGENTS §x]` `[BASE-xxx]`。
- 9.2 仓库层矩阵：填入 spec.md FR-003 ZBC 仓库层（12 行）。每行加依据标签。
- 9.3 组件层：9 项组件逐项建表。组件列表：
  1. `collector.py / collector_v2 / xhs_cookie_bridge`（采集服务）
  2. `risk_engine.py`（风险引擎）
  3. `ai_analyzer.py / ai_gateway_v570.py / ai_filter.py`（AI 分析）
  4. `daily_report.py / report_engine.py / weekly_events.py`（报告）
  5. `Auth Recovery Center` 模块（前端+后端）
  6. 事件关系图谱模块（`event_mentions` + 前端页）
  7. 品牌知识库（影子板块，80 条 7 大类）
  8. 案例深度拆解（20 个 11 维 + 58 方法论 + 77 系统启示）
  9. 品牌分析报告生成器（6 维度）
  - 对每项组件列出：路径/模块、Owner（= ZBC main 主仓库 Owner）、变更门槛（P0=禁止非最小修改；P1=旁路+验证后入；P2=蓝图化 20% 内）、跨仓使用权限（允许读/禁止复制/允许 Evidence 导出等，按 FR-003 Owner 唯一规则）、依据标签。
- 9.4 研发流程层：填入 spec.md FR-003 研发流程层 9 行矩阵（允许/禁止/受控）。每行加依据标签。

**B. README 新增第 9.5 节：本仓资产清单（8 大类）**

建表，字段=类别/路径/数量估/Owner/是否备份/允许进 Git。8 行：
1. 源码主模块（列出 app.py 264KB, 蓝图/前端/采集器；数量≈21,656 源码文件估）
2. 数据库（data/monitor.db + schema_version v8 + migrations 路径）
3. 数据资产（collection_logs / ai_filter_log 370 条 / note_review_history 7135 条 / daily_reports 13 份 / event_mentions 180 条 + backups 目录）
4. 文档（README×5 份 + AGENTS + ARCHITECTURE + PROJECT_STATUS + CHANGELOG + DEPLOY + RELEASE_POLICY + DOUBAO_* 等，当前实际文件清单需 `ls *.md docs/*.md` 抽样）
5. 测试（pytest tests/ + test_e2e + ci_cd + 安全扫描，~55+ pytest + 42 E2E）
6. 子模块（tools/development-command-console：pinned SHA，标注"升级必须经 DCC RC + Core 兼容性回归+人工批准"）
7. 凭证与配置（.env.example 可入；.env / data/private/ / system_config 表中的敏感项不入库 / 邮件 SMTP 配只允许环境变量）
8. 静态/媒体（templates/ + static/（lucide/three.js）+ screenshots/ + Zachary three.js 模型 —— 允许入 Git，但大二进制 >10MB 优先外部化）

**C. README 架构错误修复（9 项中 Task 2 负责 A 侧 5 项）**

- 修 E-001：README §1 或相关位置把"三仓体系"措辞改为"四库体系（ZBC + SICI + DCC + AI-DRH）"，AI-DRH 定位=研究与学习权威。
- 修 E-002：在 §2 双子关系硬文本处（Task 1 已加）补上 AGENTS.md §2 的链接（一句"依据 AGENTS.md §2：一套 Core，两种 Release 产物；绝不复制两套 Core 源码长期维护"）。
- 修 E-003：就是本 Task B 部分。
- 修 E-004：就是本 Task A 部分。
- 修 E-009：在 §2 和 §11 两处跳转链接各补 URL 元信息三元。

### Task-local 测试要求（TRs）

| TR | 类型 | 通过条件 | 证据 |
|---|---|---|---|
| T2-TR01 | rule | 资产清单 8 大类全部在表中，6 字段每行齐 | 人工 8×6 表格巡检 |
| T2-TR02 | rule | 允许/禁止矩阵四层齐全（4 层各 1 表），每层依据标签覆盖率≥90% | 4 表行数统计与标签覆盖率 |
| T2-TR03 | rule | E-001 修复：README 全文 grep 不再出现"三仓体系"或"三个仓库"作为正式架构描述（历史引用保留但必须标注"旧称=现四库"） | grep 精确+抽样语境 |
| T2-TR04 | rule | E-002 修复：README 中 §2 硬文本旁有 AGENTS.md §2 超链接/引用 | 手工点链 |
| T2-TR05 | rule | E-009 修复：§2 和 §11 两处跳转链接均附三元元信息格式正确 | 格式对照 |
| T2-TR06 | rule | 7 项硬枚举全部与源码一致：① subject_type 7 枚举 ② content_type 枚举 ③ publish_datetime/captured_at 两字段 ④ 三类事件×4 关系 ⑤ 采集状态 8 枚举 ⑥ DCC 权限 5 枚举（含 DENY）⑦ Evidence 5 结果枚举（含 NOT_VERIFIED<PASS）⑧ D0-D7 8 态。每项抽样读源码 1 处与 README 枚举序、值、数量一致 | 源码 vs README 枚举 diff |
| T2-TR07 | rule | 禁止项未弱于 AGENTS.md + IMMUTABLE BASE：人工对比 A 仓库"禁止"×24 条（AGENTS §1/2/3/4/5/7/13 + BASE 相关），不存在 "原禁止但新文档允许" 的单行 | 交叉对照表 |
| T2-TR08 | rubric | 允许禁止矩阵完备度评分：四层齐全+组件级≥80% 覆盖+依据标签→2 分；组件级<80% 但≥60%→1；否则 0。本任务目标=得 2 分 | 覆盖率统计（组件 9 项实填数 / 9） |
| T2-TR09 | rubric | 跨仓术语一致性（Owner/四库/Evidence/Shadow/Preflight/Effective Rules/Reusable/Capability/Contract/三向验证 共 10 词）× A 仓 README 内部抽样：0 处不一致=3；1 处=2；2-3 处=1；≥4=0。目标≥2 | 术语 grep 对照 |

### 完成证据字段
- 修改文件：`README.md`（Task 1 同文件，串行施工防冲突）
- 父 AC：AC-R006, AC-R008, AC-R009, AC-R013, AC-R014, AC-S002, AC-S004

---

## Task 3：Zachary-OS-AI README 顶层 12 节母体重写

- **Status**: pending
- **Priority**: high
- **Owner & Scope**: 修改 `D:\Zachary OS AI\README.md`（GitHub 现有收敛审计 README）。**不改动 components/ 三大组件源码 / 22 份矩阵原文 / archive / docs-wps / config**。
- **父 AC**: AC-R002, AC-R004, AC-R005, AC-R012, AC-S001, AC-S003
- **前置**: 无（可与 Task 1 并行）

### 实现内容

将当前 ZOSAI README（四库收敛审计说明 + 总览）重排并扩展为与 ZBC 相同 12 节统一母体：
1. 一句话定位 × 产品标记（🤖）+ 当前版本（收敛审计 v1.0 / 门禁 NOT_READY）
2. 双子产品关系与边界（含 A 仓交叉引用 URL+元信息；含 FR-001 B 侧硬文本）
3. 本子产品/子组件（SICI / DCC / AI-DRH）说明 + 三组件表格对比（职责 / 技术栈 / 端口 / 成熟度 / Owner / 是否是运行时依赖）
4. 子组件 × Owner × 是否允许跨仓复制 表格（与 Ownership Matrix 10 一致）
5. 架构主图（三方反哺图 IMMUTABLE §16 + ZBC 两端反馈环全局反馈环图，两图并列）
6. 当前真实进度（收敛 22 矩阵结论 + 门禁 NOT_READY(OPEN) + 5 HIGH 安全 + 10 Human Gate 冲突 + 12 周 4 阶段总览摘要）
7. AI 原则（Zachary AI 独立身份分离 + Evidence-first + Shadow 优先 + AI 依赖递减 + AI 不升级 WRITE 权限）
8. 数据模型（四库 Ownership 模型 / 11 Contract 共享类型表 / 三层共享 L1/L2/L3 / 8 状态 Capability / 21 字段 Evidence 5 结果 / D0-D7）
9. 允许 / 禁止 / 受控 四层矩阵（只占位，具体内容由 Task 4 填）
10. P0/P1/P2 当前任务（Phase B0 4 周 / Phase B1 4 周 / Phase B2+ 持续，对应 §4.2 四阶段）
11. 关键文档索引（22 份收敛矩阵核心 9 份链接 + 三组件关键基线文档 12 份链接 + 3 条跨仓反链：ZBC README 双子关系段 / ZBC AGENTS §17 交付格式 / ZBC function_registry.py 链接）
12. 协作与变更门禁（Before/Change/After Gate + 三向验证 + 9 阶段 ChatGPT Intervention Protocol + 7 阶段 Shadow Lifecycle + Dual-Repo Release Policy 8 条硬边界 + 10 条 XHS App BLOCK 红线摘要）

### Task-local 测试要求（TRs）

| TR | 类型 | 通过条件 | 证据 |
|---|---|---|---|
| T3-TR01 | rule | README 一级标题 12 个，文字顺序=上述 1-12 | grep "^# " 对照 |
| T3-TR02 | rule | 第 2 节存在 FR-001 B 侧硬文本精确版 | grep 精确匹配 |
| T3-TR03 | rule | 第 2 节包含 A 仓交叉 URL + (repo=Zachary-1012/Z-Brand-Core, branch=main, section=双子产品关系) 三元元信息 | 手工跳转 |
| T3-TR04 | rule | 当前 ZOSAI README 的核心声明（四库定义 / 22 IMMUTABLE / 三方反哺 / 门禁 NOT_READY / 5 HIGH / 10 冲突 / 12 周计划）全部保留在新 12 节中，不得丢失 | 要点清单 20 条核对 |
| T3-TR05 | rule | `git diff --stat` 只出现 README.md（和可能的 .gitignore 等后续），不出现 components/ 下 .py/.js/.html 核心实现文件修改 | git diff 输出检查 |
| T3-TR06 | rubric | 长段结构化率（4+ 行无结构长段 0=2 分；1-2=1；≥3=0） | 段落行数统计 |
| T3-TR07 | rubric | 交叉引用完整性（第 2/11 节至少 2 处跨仓回链 ZBC + Owner 声明无冲突 → 2 分；1 处=1；0 处=0） | 人工清单 |

### 完成证据字段
- 修改文件：`README.md`（Zachary OS AI 根）
- 父 AC：AC-R002, AC-R004, AC-R005, AC-R012, AC-S001, AC-S003

---

## Task 4：Zachary-OS-AI 资产清单 × 允许禁止矩阵 × 归档声明 + .gitignore 同步

- **Status**: pending
- **Priority**: high
- **Owner & Scope**: 修改 `D:\Zachary OS AI\README.md` 第 9 节填实 + 新增 9.5 资产清单 + 修 E-005/006/007/008/009；**同时修改 `.gitignore`**（B 仓专属文件，NFR-009 要求）
- **父 AC**: AC-R007, AC-R008, AC-R009(E-005~009), AC-R010, AC-R012, AC-R013, AC-R014, AC-S002, AC-S004
- **前置**: Task 3 完成后开始

### 实现内容

**A. 第 9 节：允许/禁止/受控 四层矩阵（B 侧）**

- 9.1 产品层：FR-003 产品层 B 侧 9 行（8 行共用 + 1 行身份分离专项）。每行依据标签。
- 9.2 仓库层：FR-003 ZOSAI 仓库层 13 行（IMMUTABLE 系列 + WRITE DENY / NOT_VERIFIED 冒充 / Release Gate / XHS BLOCK 红线 / Hub 六条铁律 / 禁止新建能力注册副本 等）。每行依据标签。
- 9.3 组件层：23 项组件逐项建表。列表：
  - SICI（16 个 JS 模块：core / effective-rules / preflight / capability-registry / zbc-evidence-adapter / tool-registry / three-repo-verifier + 其他 9 个）
  - DCC（11 服务端：server.js 40+API / task contract / snapshot / change-plan state machine / evidence-bundle / learning 引擎×3 / shadow-learning / effective-rules / supplements / capabilities + DCC docs 三库矩阵 / 双库发布 / 事实基线 共 14 项）
  - AI-DRH（GLOBAL-BASELINE / PLATFORM-BASELINE / AI-COLLAB / CHATGPT-INTERVENTION 9 阶段 / SHADOW-LEARNING / THREE-VALIDATION / CAPABILITY-REGISTRY / CRD 持续研发 共 8 协议；+ src 工具：research-id-generator / shadow-lifecycle / ddc-research-adapter / secret-scanner / preflight 7 项 / JSONL ledger / capability_delta 共 8 工具）
  - 每项组件：路径 / Owner / 变更门槛（IMMUTABLE=永不改；P0=DCC WRITE 永 DENY；P1=流程改需 9 阶段）/ 跨仓使用权限 / 依据标签。
- 9.4 研发流程层：与 A 仓完全相同的 9 行（研发流程层属于跨仓对齐，可以共享版本，文本 100% 一致）。

**B. README 9.5 节：本仓资产清单（7 大类）**

字段同 A 仓表。7 行：
1. 收敛矩阵文档（22 份 .md 根目录 / 核心 9 份 Inventory+Ownership+Contract+Capability+Duplicate+Research+Evidence+Baseline+Final）
2. SICI-Core 组件（components/SICI-Core 16 JS + index.html + PWA）
3. DCC 组件（components/Development-Command-Console server + docs）
4. AI-DRH 组件（components/AI-Development-Research-Hub 8 协议 + 8 reusable + src）
5. 归档资产（docs-wps/ 2 docx + config/codex/ 2 文件 + archive/desktop-legacy 两子目录 + archive/repo-audit/SICI-Core 快照 = 明确标记："仅本地保存 / 不 push 主分支 / 归档用途 不纳入 Release"）
6. 文档索引与跨仓基线（根 README + 三组件各 README + PLATFORM_README 交叉）
7. 配置与忽略（.gitignore / 本地 Python/Node 依赖 / 未来可能的 data/learning/ 目录——说明依赖文件绝对不进 Git）

**C. 架构错误修复（E-005~009 B 侧）**

- E-005：README §1+§2 明确声明 "Zachary-OS-AI 是四库（ZBC+SICI+DCC+AI-DRH）的治理/审计/收敛/研究枢纽；ZBC 业务源码仍在独立仓 Z-Brand-Core，不重复存储于本仓"。
- E-006：就是本 Task §2 交叉引用段（Task 3 已占位，Task 4 填实跳转链接）。
- E-007：README §9.5 归档资产类加一句 "docs-wps/*.docx / archive/desktop-legacy/** / config/codex/* 三类永久不 push 主分支，见 .gitignore"。
- E-008：检查三组件 README（SICI §16/DCC §18/AI-DRH PLATFORM_BASELINE）三方反哺描述，统一术语"四库"而不是"三仓"。不一致的地方在各自 README 的修改作为子步骤（E-008 修 1-2 处文字重写；**仍属于文档不碰代码**，不算 NFR-012 违规）。
- E-009：§2/§11 两处跳 ZBC 链接加三元元信息。

**D. .gitignore 同步（B 仓）**

在现有 .gitignore 基础上追加：
```gitignore
# ====== Zachary-OS-AI 本地归档专用（不 push 主分支） ======
docs-wps/*.docx
docs-wps/*.doc
archive/desktop-legacy/**
archive/repo-audit/**
config/codex/*

# ====== 高风险通用 ======
**/data/*.db
**/data/private/
*.env
.env.*
!.env.example
**/node_modules/
**/__pycache__/
**/.venv/
**/venv/
*.zip
*.rar
*.7z
```

### Task-local 测试要求（TRs）

| TR | 类型 | 通过条件 | 证据 |
|---|---|---|---|
| T4-TR01 | rule | 资产清单 7 大类 6 字段齐全 | 7×6 巡检 |
| T4-TR02 | rule | 四层矩阵齐全+依据标签覆盖率≥90% | 覆盖率统计 |
| T4-TR03 | rule | E-005 修复：grep 到精确声明句 | grep |
| T4-TR04 | rule | E-007 修复：README §9.5 有归档声明且 .gitignore 含 docs-wps/archive 条目 | 双处检查 |
| T4-TR05 | rule | E-008 修复：components/ 三份 README 三方反哺段都用"四库"不用"三仓" | grep 三份 README |
| T4-TR06 | rule | 7 硬枚举与 ZBC Task 2 T2-TR06 结果一致（跨仓一致） | 对比 |
| T4-TR07 | rule | 禁止项未弱于 IMMUTABLE BASE 22 条 + Dual-Repo 8 硬边界 + Hub 六条铁律。单行核查无放宽 | 交叉表 |
| T4-TR08 | rule | `git check-ignore` 抽样 10 条高风险路径（3 docx, 3 archive legacy, 2 .db, 2 .env）全部被成功 ignore | git check-ignore 输出 |
| T4-TR09 | rule | `git diff --stat` 只出现 README.md + .gitignore + 最多 3 个 components 下 README 文档（E-008 修复），绝对不出现 .py/.js/.html 核心实现文件 modify | git diff 检查 |
| T4-TR10 | rubric | 允许禁止矩阵完备度：四层齐全+组件级≥80%+依据标签→2；否则 1/0。目标 2 | 23 组件填充率 |
| T4-TR11 | rubric | 跨仓术语一致性（10 核心词 × B 仓内部 + 与 A 仓交叉）：与 A 仓 0 差异=3；1 差异=2；2-3=1；≥4=0。目标≥2 | 术语表 10×2 仓 grep |

### 完成证据字段
- 修改文件：`README.md`（ZOSAI 根）+ `.gitignore`（ZOSAI）+ 最多 3 份 components 下 README 文档（E-008）
- 父 AC：AC-R007, AC-R008, AC-R009, AC-R010, AC-R012, AC-R013, AC-R014, AC-S002, AC-S004

---

## Task 5：联合修复 + 交叉链接 URL 元信息 + 术语一致性最终对齐 + 依据溯源表

- **Status**: pending
- **Priority**: high
- **Owner & Scope**: 跨两仓、纯文档收尾、不碰业务代码。
- **父 AC**: AC-R005, AC-R009(complete E-001~009), FR-005(版本化交叉引用), NFR-004(依据溯源), NFR-007(术语一致), AC-S001, AC-S004
- **前置**: Task 1 + Task 2 + Task 3 + Task 4 至少完成可用草稿。

### 实现内容

1. **跨仓跳转 URL 手工验证**：两仓共至少 4 条 URL（ZBC §2 到 ZOSAI；ZBC §11 到 ZOSAI 三文档；ZOSAI §2 到 ZBC；ZOSAI §11 到 ZBC AGENTS + function_registry）全部用真实浏览器打开并确认：
   - 能跳
   - 段落锚点能定位（若 GitHub anchor 不稳定则段落标题+手动搜索定位方案说明）
   - 三元元信息 repo/branch/section 与实际一致
2. **版本化交叉引用补齐（FR-005）**：对每条跨仓引用在元信息后再加 `last_verified_sha=` 字段，取两仓当前 git rev-parse HEAD 的短 SHA。
3. **术语一致性最终对齐（10 核心词 × 2 仓 × 每仓 10 处抽样）**：
   - 扫词清单：Owner / 四库 / Evidence / Shadow Mode / Preflight / Effective Rules / Reusable Capability / Capability Registry / Contract / 三向验证（Three-Way Verification）
   - 检查点：① 缩写大小写一致 ② 不出现同一概念多套词（如"能力注册中心"不能有时叫"注册中心"有时叫"注册表"有时叫"登记处"——统一叫"能力注册中心"，Owner=AI-DRH）③ 英文原词首次出现时中文译名固定（首次出现处可在 README 用括号注明）
   - 任何不一致之处在本 Task 中就地修 README 文字。
4. **依据溯源表输出**（一份独立文档，放在 `.trae/specs/dual-repo-audit-20260902/evidence-traceability.md`，不在两仓 README 内部——避免 README 过长）：
   - 对两仓允许/禁止矩阵全部行（预计 A 仓 40+ 行，B 仓 55+ 行）建立一张大表：行号 / 文本 / 依据标签原文 / 真实依据文件路径（绝对路径）/ 文档段落号 / 当前版本 SHA。
   - 本 Task 输出这份表，用于独立 Reviewer 直接点击打开文件查。
5. **9 项架构错误（E-001~E-009）最终验收清单**：列出 9 项 × 每项在 Task 1/2/3/4 中已被修的文件位置 + 修复前/后说明，形成 Close-Out Log。

### Task-local 测试要求（TRs）

| TR | 类型 | 通过条件 | 证据 |
|---|---|---|---|
| T5-TR01 | rule | 跨仓 4 条跳转 URL 全部真实打开成功（本地 env 允许时用浏览器实际点；若 env 无浏览器则记为"URL 格式正确 + repo 存在 + 段落标题存在"，并记该 NOT_VERIFIED 条目） | URL 打开截图或报告 |
| T5-TR02 | rule | 4 条 URL 都附了 last_verified_sha= 短 SHA，且 SHA 与当前 HEAD 匹配 | git rev-parse --short HEAD 对比 |
| T5-TR03 | rule | 术语 10 词 × 2 仓各抽样 10 处：0 处不一致（完全一致） | grep 对照表 diff=0 行 |
| T5-TR04 | rule | 依据溯源表 evidence-traceability.md 覆盖≥95% 的矩阵行，每行 6 字段完整 | 覆盖率统计 |
| T5-TR05 | rule | 9 项架构错误 Close-Out Log 中每项 status=Closed，并附"修复所在 Task 编号 + 文件绝对路径 + 段落锚点" | Close-Out Log 9×6 表 |
| T5-TR06 | rubric | 交叉引用完整性（最后一关）：URL+元信息+SHA 全齐 + 无 Owner 声明冲突 = 3 分；缺元信息但链接 OK=2；1 条链接坏=1；≥2 条坏=0。目标 ≥ 2 | 打分卡 |
| T5-TR07 | rubric | 跨仓术语一致性最终分：10 词×2 仓 0 差异=3；1 处=2；2-3 处=1；≥4 处=0。目标 ≥ 2 | 打分卡 |

### 完成证据字段
- 修改文件：两仓 README.md（微量文字修复）+ 新增 `evidence-traceability.md` + 新增 `E-001~E-009_close-out.md`
- 父 AC：AC-R005, AC-R009, FR-005, NFR-004, NFR-007, AC-S001, AC-S004

---

## Task 6：独立 Review（Review Gate）

> 注意：按 TRAE-spec-mode 规范，真正的 Review 阶段在 Implement 队列 drain 后另行做独立审查。本 Task 只是 Implement 阶段内"自测+预演独立 Review 清单"，真正的 review.md 文件在进入 Review 阶段时创建。
- **Status**: pending（Implement 阶段只做自测清单；独立 Review 后补正式 Review History）
- **Priority**: medium
- **Owner & Scope**: 自审 + 独立 Reviewer（按 TRAE-spec-mode 要求，独立 Review 必须是 fresh context，Implementer 自审不得替代）
- **父 AC**: 全部 14 rule AC + 全部 5 rubric AC
- **前置**: Task 1-5 全部 Status=completed

### 实现内容（Implementer 自测）

1. 重读 `spec.md` 全部 14 条 rule AC，逐条给 pass/fail + 证据截图/文件路径。
2. 重读 5 条 rubric AC，每条打分 + 理由 + 证据。
3. 生成一张"AC 覆盖总表"：每个 Rule AC → 哪个 Task 提供了对应 TR / 什么证据；每个 Rubric AC → 最终分 / 理由 / 是否过阈值。
4. **NOT_VERIFIED 声明**：如果当前环境无法跑真实 E2E / 浏览器打开 URL / 真实 git push，则在每个相应条目下明确写 NOT_VERIFIED，并写"恢复可执行环境条件后应立即补测"。

### Task-local 测试要求（TRs）

| TR | 类型 | 通过条件 | 证据 |
|---|---|---|---|
| T6-TR01 | rule | 14 条 rule AC 逐条有 pass/fail 判定+证据来源；0 条 fail（若有则必须回 Implement 生成新 remediation task，不得在本 Task 上直接记 pass） | AC 覆盖总表 |
| T6-TR02 | rule | 5 条 rubric AC 都达到其各自及格阈值（2/2/1/2/2），每条有分+理由+证据 | AC 覆盖总表 rubric 栏 |
| T6-TR03 | rule | 任何 NOT_VERIFIED 条目明确标注，并附后续补测条件。NOT_VERIFIED 未记作 PASS。 | 清单检查 |
| T6-TR04 | rubric | 自测的工作流保真度（参考 TRAE-spec-mode 总规则 rubric）：五阶段边界+Artifact 边界遵守=2；轻微错=1；否则 0。目标 ≥ 2 | 审阅 Spec Mode 工作流保真度自评 |

### 完成证据字段
- 修改文件：`.trae/specs/dual-repo-audit-20260902/self-review-checklist.md`
- 父 AC：全 AC

---

## AC-TR 覆盖总表（自动汇总）

> 供独立 Reviewer 快速验证：每个 AC 是否有至少 1 个 TR 直接覆盖。

| AC | 覆盖 TR（Task 编号） | 覆盖度 |
|---|---|---|
| AC-R001 | T1-TR01 (Task1) | ✅ 完全 |
| AC-R002 | T3-TR01 (Task3) | ✅ 完全 |
| AC-R003 | T1-TR02 (Task1) | ✅ 完全 |
| AC-R004 | T3-TR02 (Task3) | ✅ 完全 |
| AC-R005 | T1-TR03 + T3-TR03 + T5-TR01+TR02 | ✅ 完全 |
| AC-R006 | T2-TR01 (Task2) | ✅ 完全 |
| AC-R007 | T4-TR01 (Task4) | ✅ 完全 |
| AC-R008 | T2-TR02 + T4-TR02 | ✅ 完全 |
| AC-R009 (E-001~009) | T2-TR03/TR04/TR05 + T4-TR03/TR04/TR05 + T5-TR05 (9/9 全部覆盖) | ✅ 完全 |
| AC-R010 | T4-TR08 (Task4) | ✅ 完全 |
| AC-R011 | T1-TR05 (Task1) + T2 不碰代码确认 | ✅ 完全 |
| AC-R012 | T3-TR05 + T4-TR09（核心 .py/.js 不改） | ✅ 完全 |
| AC-R013 | T2-TR07 + T4-TR07 | ✅ 完全 |
| AC-R014 | T2-TR06 + T4-TR06 + T5-TR03（跨仓对齐） | ✅ 完全 |
| AC-S001 | T1-TR07 + T3-TR07 + T5-TR06 | ✅ 完全 |
| AC-S002 | T2-TR08 + T4-TR10 | ✅ 完全 |
| AC-S003 | T1-TR06 + T3-TR06 | ✅ 完全 |
| AC-S004 | T2-TR09 + T4-TR11 + T5-TR07 | ✅ 完全 |
| AC-S005 | **未分配独立 TR（随 T1~T5 各"审计支撑"点实现）→ 在 T6 独立 Review 阶段按每条打分声明出处补验证** | ⚠️ 需要 T6 补独立验证 |

---

## 未完成项总览（本 tasks.md 不解决，留给后续 Spec/Owner 裁决）

对应 spec.md §8.4 开放问题（OQ 1-6）+ 10 Human Gate 冲突 + 5 HIGH 安全发现，全部保留未在本轮 tasks 中解决：

1. OQ-1~OQ-6（6 项 Owner 决策）
2. ZBC 7 张表差异（Human Gate #10）
3. 四重能力注册分裂（#1）、4 Preflight 独立实现（#2）、Effective Rules 重复（#3）、Design Tokens 分歧（#4）、Learning 碎片化（#5）、Evidence 流缺自动化（#6）、SICI Persistence Bridge（#7）、DCC Learning Store（#8）、无跨库事件总线（#9）—— 共 9 项冲突
4. 5 HIGH 安全：API 无认证无版本 / 加密证据链 0 / DCC 内存失 / SICI localStorage / Contract 测试套件缺失
5. .gitignore 只在 B 仓补；A 仓也要同步一份高风险 ignore（A 仓已有 .gitignore 但可能覆盖不全——留给下一周期小 Task）

---

## 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| Task 1 & Task 2 同时写 README.md 产生冲突 | 中 | 串行执行：T1 完成→提交暂存→T2 再开 |
| Task 3 & Task 4 同时写 ZOSAI README | 中 | 同上串行 |
| 术语统一 10 词 × 2 仓可能出现"越修越多错" | 中 | T5 用先建"标准术语表.md"再逐个替换方式 |
| E-008 需修 components/ 下 3 份 README → 可能碰源码 | 低 | 严格只修 README 文档行不改 .py/.js；提交前 diff 过滤 |
| 归档类 400+ MB 文件如果不小心进 git add | 中 | 先配 .gitignore 再任何 git add 动作；.gitignore 先 commit 单独一次 |

---

*End of tasks.md. 所有任务优先级：P0=立即（Approve 后即开）；本 tasks 全为 high（最高非阻塞）。*
