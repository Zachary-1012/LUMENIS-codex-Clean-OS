# 02 · AI / Agent / Reasoning / Memory / Robotics / Embodied AI / OS / Research

> 知识库条目规范：`**[条目]** 证据等级 / 状态 / 语言文化 / 时间版本 / 来源`
> 本模块跟踪 AI/具身/Agent 前沿，为序境-Intelligence 与未来产品能力提供研究输入。**研究输入不自动等于生产能力**，进入生产前须过 Contract/Test/Evidence/Audit/Release。

## 1. 具身智能（Embodied AI / Embodied Intelligence）

**[具身智能定义]** E3 / VERIFIED / 中英 / 2025 / 人民日报(2025-03)；The Innovation (2025)
- 具身智能 = 有物理载体的智能体；智能体通过身体与环境的动态交互实现感知、决策、行动的闭环，实现自主学习和进化。
- 三要素：Intelligence（计算/模型） + Embodiment（物理或仿真身体） + Environment（环境）；行为涌现于三者交互，且环境被行动改变后回馈感知，形成闭环。
- 与序境：**感知→决策→行动→反馈→学习→演化** 生命循环的具身版；"跨端 Renderer"可视为 Embodiment 的一种数字载体（CONCEPT）。

**[Embodied AGI 五级路线（L1–L5）]** E3 / VERIFIED / 英 / 2025-05 / arXiv:2505.14235
- L1 单任务 → L2 组合任务 → L3 条件通用 → L4 开放任务 → L5 全开放人类级；四维能力：全模态、类人认知、实时响应、泛化。
- 结论：当前业界处于 L1–L2，距 L3+ 仍有显著缺口。**序境不应高估现成模型成熟度**，用于设定产品能力边界预期。

**[VLA 范式（Vision-Language-Action）]** E3 / VERIFIED / 中英 / 2025-2026 / RT-2-X, OpenVLA, Gemini Robotics, Pi0 等
- VLA 取代模块化管线，端到端统一视觉感知+语言指令+动作生成；具身推理初现（Gemini Robotics / GPT-4o 具身版）。
- 具身推理 RL 化：ERA（具身前验+在线 RL，3B 超 GPT-4o，arXiv:2510.12693）、Robot-R1（GRPO 多选重构，7B 超越 GPT-4o 低层动作推理，OpenReview 2025）。
- 与序境：Agent 的"plan→ground→execute"分层（GR-ER 编排 + 动作模型执行）是未来机器人能力参考架构。

**[NJF 神经雅可比场（身体自省）]** E3 / VERIFIED / 英 / 2025-07 / MIT CSAIL, Nature 2025-06
- 仅凭单目相机+随机运动，机器人自学习"自身几何+控制敏感性"（自建内部身体模型），无需传感器/人工模型；软体、异形机器人可零预建模控制。
- 意义：**从"编程机器人"到"教学机器人"**——与序境"最小变更+自学习"、以及"AI 自省/自我模型"理念同构（CONCEPT）。

**[多体转移（Motion Transfer）]** E3 / VERIFIED / 英 / 2025-10 / Gemini Robotics 1.5 (arXiv:2510.03342)
- 跨本体零样本技能迁移；"Thinking VLA" 在动作前显式推理（Instruction→Thinking Trace→Action），提供可解释性与失败恢复。
- 与序境：**统一能力、多端适配**——"同一业务逻辑跨端仅做终端适配"的机器人版。

## 2. Agent / Reasoning / Memory

**[Agent 分层编排]** E3 / VERIFIED / 英 / 2025 / GR-ER 1.5 orchestrator + GR 1.5 action model
- 高层规划/成功判定/空间理解由专用推理模型承担；低层动作由策略模型执行；错误检测与自适应重规划。
- 与序境：Agent 权限边界（Registry→Permission→Policy→Execute→Verify→Evidence→Audit）与之呼应，**编排≠越权**。

**[Reasoning 前沿：RL 强化推理]** E3 / VERIFIED / 英 / 2024-2025 / DeepSeek-R1 → Robot-R1 / GRPO
- 强化学习采样推理轨迹并按正确性强化，优于纯 SFT；缓解灾难性遗忘、提升泛化。
- 与序境：自研 AI 的训练/微调路径可评估 RL 路线（ADAPT/EVALUATE），但不急于替换现网。

**[Memory 维度]** E1-CONCEPT / CONCEPT / 英 / v1.0 2026-09-04 / 本库 + Embodied AGI 综述 §4
- 具身认知强调程序性记忆/记忆再巩固（memory reconsolidation）；序境记忆体系应区分：事实记忆（Evidence）、程序记忆（工作流/规则）、情景记忆（任务历史/时间轴）。

## 3. OS / Research / 未来扩展

**[Agentic OS]** E1 / CONCEPT / 英 / v1.0 2026-09-04 / 本库
- 序境未来 OS/平台层候选语义应覆盖：编排、记忆、多体、安全边界；命名不得与既有 Agent/OS 产品冲突（见 05 命名文件）。

**[Research 方法]** E3 / VERIFIED / 通用 / 2026-09-04 / 本库
- 研究=证据分级（E0–E4）+ 状态机（FACT/VERIFIED/…）+ 可追溯来源；**研究不得绕过 Gate 进入 Production Truth**。

---

**本模块待补**：开源模型月度榜单（Gemini 5 / GPT / Claude / Qwen / DeepSeek / GLM）、Memory 框架（MemGPT/Letta 等）、多模态评测基准、安全对齐最新进展。
