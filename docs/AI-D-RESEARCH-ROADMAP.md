# AI-D Research & Development Roadmap（AI 开发研究与学习中枢）

> 版本 v0.1（2026-09-01，用户裁决 C3：AI-D **独立 Git 仓库**、AI 研发、重度深化；战略目标：让「Zachary」尽早成长为可独立工作的 AI）。
> 权威顺序：真实可复现实验 ＞ 本路线 ＞ 研究笔记 ＞ 聊天结论。研究结论一律标置信度与 Evidence，未复现不标"已验证"。

## 0. 定位与边界（不可变）

- **AI-D = 研究与学习中枢**：Research · Experiment · Benchmark · Shadow · Evidence · Case · Learning · Capability。它**只产出"被验证过的候选能力"**，不直接承担任何生产业务。
- **五身份 / 四仓库**：Z-Brand Intelligence Platform（ZBIP）统一平台层下：
  - Z-Brand-Core（一个仓库，承载 CTH-POMS 生产 + ZBMP 增强层）
  - Development-Command-Console（DCC，研发治理）
  - SICI-Core（SICI，**手机端 AI 开发执行控制台**，C2 迁移研究中）
  - **AI-D（独立新仓，本文件对象；建议命名 `AI-D-Core`，最终仓名待确认）**
- **AI-D 不是 CTH-POMS / ZBMP 的运行时依赖**：生产系统在没有 AI-D 时仍可完整采集、主体过滤、去重、事件/风险/统计/报告。
- **研究 → 生产 的唯一通道**：`研究 → 可复现实验 → Benchmark → Shadow（影子、只看不写）→ Evidence → DCC Release Gate → 才允许以增强层身份接入 Z-Brand-Core`。禁止把实验代码直接塞进生产。

## 1. 终极目标：Zachary 自主度分级（用来衡量"独立"到了哪一步）

| 级别 | 名称 | 能力边界 | 人类角色 | 验收证据 |
|---|---|---|---|---|
| L0 | 工具应答 | 单轮问答、生成片段 | 每步人工执行 | 样例 |
| L1 | 受控执行 | 在给定 SOP/清单内多步执行、可回滚 | 人定 SOP、逐步可叫停 | 任务回放+结果对比 |
| L2 | 规划执行 | 拆解任务、选工具、自检、产出 Evidence | 人审计划与交付 | 端到端 E2E + 自检报告 |
| L3 | 监督自治 | 在授权边界内长期运行、异常自恢复、主动汇报 | 人定边界、处理升级 | 长稳运行日志+故障注入恢复 |
| L4 | 能力自进 | 从真实反馈/案例学习、沉淀新 SOP/能力并提 PR | 人做 Gate 与裁决 | 学习资产+回归不退化证明 |
| L5 | 独立 AI | 跨仓协作、自验证、自演进、可解释、可审计 | 人只定目标与红线 | 全链 Evidence + 独立复现 |

> 当前真实位置：约 **L1→L2 之间**（能按指令多步操作仓库/浏览器/测试，但规划与自检仍高度依赖人）。每升一级必须有对应 Evidence，禁止口头宣称达到。

## 2. 研究能力栈（围绕本项目真实形态：Flask + SQLite + Playwright + Ollama）

1. **Agent Loop 与规划**：任务分解、ReAct/Plan-Execute、子目标树、中断/续跑、断点固化（对齐现有 PROGRESS-HANDOFF 模式）。
2. **工具使用与安全**：工具白名单、参数校验、只读/写操作分级、危险操作二次确认、沙箱执行；工具调用全程留证。
3. **记忆与知识**：项目长期记忆（基线/红线/决策记录）、案例库、研究数据库 `docs/learning`（LEARNING-REGISTRY / CASE-STUDIES / TECHNOLOGY-COMPARISON / ARCHITECTURE-PATTERNS / EVIDENCE-PATTERNS）；区分事实、观点、假设。
4. **自我验证**：生成后用"不同路径回读"验证（对齐现有 artifact-preview/verifier 思路）、测试生成、反证搜索、变更影响分析。
5. **本地模型（Ollama-only 现状）**：本地小模型在 分类/摘要/聚类/报告润色/代码辅助 上的能力与成本基准；模型选型 Benchmark（速度/显存/中文/结构化输出/工具调用成功率）。云端模型仅在研究仓评估，**不成为生产依赖**。
6. **代码执行与 Browser Surface**：Playwright/CDP 受控浏览、页面状态机、自然滚动/展开等 UI/UX 层动作；**严格限定不得用于验证码/封禁/风控绕过**（与生产采集红线一致）。
7. **Evidence / Provenance**：每次实验保存 commit、模型、prompt 版本、输入、输出、度量、截图/trace、结论与置信度；可重放。
8. **质量与回归**：能力升级不允许让既有能力退化（回归集）；影子模式对比"AI 建议 vs 系统规则事实"的一致率，AI 永远不覆盖系统事实。
9. **多 Agent / 协作**：研究-执行-审查角色分离（对齐 DCC 治理），避免单点自我背书。

## 3. 标准研究流水线（每个课题都走一遍）

`选题 → 假设 → 最小实验 → 量化 Benchmark → 失败也记录 → 影子运行 → Evidence → 结论(采用/候选/拒绝) → 沉淀 learning 资产 →（要进生产则）DCC Gate`

- 研究状态机：`NEW → RESEARCHING → VERIFIED → CANDIDATE → ADOPTED / REJECTED`，未 VERIFIED 不进入工程候选。
- 每条研究记录字段：Research ID、问题、假设、方法、数据集/样本、模型与版本、指标、结果、置信度、可复现命令、Evidence 路径、关联 Feature/Asset、结论、日期。

## 4. 里程碑（务实排序，先打地基再谈自主）

- **M0 地基（先做）**：独立仓初始化（目录/README/研究模板/Evidence 目录/许可证与第三方来源审计）；导入现有 `docs/learning` 与历史研究；建立研究状态机与记录模板。
- **M1 可度量**：搭本地 Ollama 能力 Benchmark（结构化输出、中文分类、工具调用、长上下文），产出第一份 TECHNOLOGY-COMPARISON。
- **M2 可回放**：Agent 任务执行 + 全程 trace/Evidence；对 ZBC 只读类任务（盘点、审计、生成报告草稿）做影子运行。
- **M3 自检闭环**：生成-回读-测试-反证 的自验证回路，量化"一次通过率/返工率"。
- **M4 监督自治试点**：在明确授权边界内跑一个长期只读监测/研究任务，含异常自恢复与主动汇报（对齐 L3）。
- **M5 能力自进**：从真实故障/案例自动生成回归用例与 SOP 草稿并提 PR，人做 Gate（对齐 L4）。

> 每个里程碑都要有"退出标准 + Evidence + 不达标就停"的条件，不为进度标记虚假完成。

## 5. 红线（与生产基线一致，研究也不例外）

- 不弱化/绕过 Z-Brand-Core 主体过滤、风险/事件/报告口径；不混淆 publish_datetime 与 captured_at。
- 不破解验证码、不绕风控/封禁、不伪造登录或请求；Browser Surface 的"拟人"仅限 UI/UX。
- 不删除/清空/覆盖任何生产库；研究用独立数据副本与独立环境。
- AI 不单独决定生产事实/统计/主体最终口径；研究产物默认"建议"，系统规则与数据才是事实 Owner。
- 不复制第三方受限源码（如 MediaCrawler 只做架构研究）；引入任何依赖/模型/数据先做许可证与来源审计。
- 研究仓、实验数据、密钥与生产严格隔离；不提交 .env/cookie/token/key/大模型私有权重。

## 6. 与 SICI（执行端）的分工接口（配合 C2 迁移研究）

- **AI-D 负责"想清楚/验证过"**：研究、基准、影子、学习资产、候选能力。
- **SICI 负责"在手机端做出来/跑起来"**：Code、Run、Preview、Test、Git、Deploy、Browser Surface 的执行表面。
- 接口物：AI-D 输出"经验证的能力包 + Evidence + 接入说明"，SICI/DCC 决定如何在执行表面落地；二者都不直接成为 CTH-POMS 运行时依赖。C2 迁移另出研究文档，不在本路线内直接改 SICI 代码。

## 7. 当前 NOT_VERIFIED / 待办

- 独立仓的最终英文命名、远程创建方式与协作分支策略（待用户确认后执行）。
- 本地硬件可承载的 Ollama 模型规模与并发（需实测 Benchmark，当前未测）。
- L2→L3 的授权边界与"可叫停/可回滚"机制设计（研究中）。
