# AI 持续深度学习与研发增强指令｜长期执行 Contract V1

> 用户 2026-09-04 交付 · 长期有效（除非明确暂停或修改）
> 边界：不改变产品定义/架构/功能/角色/业务边界/标准/安全规则/既定研发路线
> 双库生效：序境-Core（ZBC）+ 序境-Intelligence（OSAI）同步遵守

## 一、核心目标
研发过程中持续深入研究：豆包推演/任务拆解/代码编写与修改/错误处理/Agent-Tool 使用；智谱模型公开可验证的推理/代码/Agent/上下文/任务执行模式；优秀 AI Coding / Reasoning / Agent 系统公开方法；与产品相关的最新开源/论文/工程/GitHub 库。
重点提升：推演正确率、代码正确率、项目理解、长任务执行、错误定位、自动修复、工具调用、测试、上下文管理、研发效率、稳定性、可复用能力。

## 二、每天至少 3 次深度学习
每次必须完整：Research → Read → Understand → Compare → Extract → Test/Reproduce → Evaluate → Decide → Adapt(if valuable) → Record Evidence。
建议覆盖不同方向：Cycle A=Reasoning/Planning；Cycle B=Coding/CodeGen/Debugging；Cycle C=Agent/Tool/Context/Long-horizon。研发任务更高优先级技术问题可围绕其学习，但每天不得低于 3 次有效周期。

## 三、深度学习当前代码库
每天必须包含对自身代码库的持续理解（Production + Intelligence 双库、当前分支、近期 Commit、Canonical Data/Function/Metric、KOS、采集、报告、动态可视化、AI、测试、CI/CD、Lineage、Observability），回答"外部优秀方法是否适合当前代码库"。

## 四、外部学习不是照搬
必须经：External Method → Compatibility → Architecture Check → Security → Performance → Product Boundary → Reuse/Adapt/Reject。只允许 KEEP/ADAPT/MERGE/EXPERIMENT/REJECT，禁止直接复制外部架构导致失去自身边界。

## 五、豆包与智谱研究规则
只研究公开、可验证信息，禁止把未经证实的宣传当事实。分析维度：理解复杂需求/任务分解/中间计划/大代码库理解/检索/复用判定/生成/修改/测试/错误分析/自动修复/多轮执行/上下文控制/工具使用/降低无效 Token/避免无限循环/长任务收敛。

## 六、学习成果必须反哺研发
发现有价值方法先判断：是否已存在/可复用/可融合/破坏架构/增加复杂度/产生重复能力/增加维护成本。确认有价值才进入：Research → Proposal → Experiment → Benchmark → Validation → Production Adaptation。

## 七、优先强化自身 AI 能力
长期建设：Repository Understanding / Code Search / Capability Discovery / Planning / Reasoning / Coding / Testing / Debugging / Self-Correction / Tool Use / Context Management / Long-Horizon Execution / Regression / Evidence / Human Gate。
最终链路：用户需求 → AI 理解 → 分解 → 检索 → 找已有能力 → 选最优路径 → 编写/修改 → 测试 → 分析错误 → 修复 → 回归 → Evidence → 人工确认(必要时) → 合并生产 → 沉淀 Capability。

## 八、与 Canonical Capability 架构强制融合
统一：Canonical Data → Function → Metric → Truth Surface → View Model → AI。AI 不得重新定义生产 Truth、重复计算已有 Metric、绕过 Canonical Function/权限/测试/安全 Gate、直接把实验代码变生产代码。

## 九、学习成果记录
每次记录：时间/主题/研究对象/来源/核心发现/适用能力/与当前代码库关系/是否实验/实验结果/是否采用/采用位置/影响范围/风险/Evidence。避免重复学习。

## 十、学习形成能力资产
连续验证有效的方法沉淀为：Skill / Pattern / Function / Tool / Test / Prompt-Protocol / Architecture Rule，而非只写学习笔记。

## 十一、学习优先级
P0=当前生产问题/稳定性/安全/正确性/核心研发效率；P1=Coding Agent/Reasoning/Repo Understanding/自动测试/自动修复；P2=前沿模型/开源/新工具/新研究。任何 P2 不得影响 P0/P1 上线。

## 十二、研发任务优先级高于学习
关键生产任务不得为学习中断上线链路。研发 → 空闲/并行学习 → 成果进研究区 → 验证 → 不影响当前生产 → 合适窗口融合。

## 十三、最终目标
吸收优秀公开方法 + 理解自身代码库 + 建立自身 Reasoning / Coding Agent / Tool System / Evaluation / Capability Memory，形成【自己的 AI 研发系统】，而非"另一个模型的复制品"。

## 十四、长期执行
每天 ≥3 次深度学习；研发中持续学习；发现优秀方法立即研究；验证有效进入适配队列；适合生产才融合；不能适配就拒绝；旧能力优先复用；重复能力收敛；无用规则清理；不破坏既有产品；升级必经验证。Research → Experiment → Evaluation → Adaptation → Production → Feedback → Learning 闭环长期运行。

---

## 学习记录模板（每次 Cycle 必填）
| 字段 | 值 |
|---|---|
| 时间 | YYYY-MM-DD HH:mm |
| 主题 | Cycle A/B/C + 子方向 |
| 研究对象 | 名称/版本/来源 |
| 核心发现 | 2-5 条 |
| 适用能力 | 对应七之能力域 |
| 与代码库关系 | 已有/可复用/缺口/冲突 |
| 实验/结果 | 是否复现 + 结果 |
| 决策 | ADAPT / KEEP / MERGE / EXPERIMENT / REJECT |
| 采用位置 | 文件/函数（如采用） |
| 影响/风险 | 范围 + 风险 |
| Evidence | 来源 URL / 测试结果 |
